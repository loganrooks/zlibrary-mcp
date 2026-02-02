# Phase 9: Margin Detection & Scholarly References - Research

**Researched:** 2026-02-02
**Domain:** PDF spatial text analysis, scholarly margin content extraction
**Confidence:** HIGH (codebase-verified), MEDIUM (algorithm design)

## Summary

Phase 9 adds margin content detection to the existing RAG pipeline. This is a **spatial classification problem**: given PyMuPDF text blocks with bounding boxes, classify which blocks are margin content vs body text, then emit typed annotations (`{{stephanus: 231a}}`, `{{bekker: 1094a1}}`, `{{line_number: 25}}`, `{{margin: content}}`).

No new libraries are needed. PyMuPDF's `get_text("dict")` already provides all spatial data (bbox per block, per line, per span). The codebase has an established detection module pattern (`lib/rag/detection/`) with footnotes, headings, page numbers, and ToC detection as precedents.

The key technical challenge is **adaptive margin zone detection** that handles diverse publisher layouts without hardcoded thresholds. The user has explicitly flagged concerns about hardcoded header/footer margins failing on scanned documents with narrow margins or scan artifacts. The recommended approach uses **statistical body-text column inference** with configurable fallback thresholds.

**Primary recommendation:** Build `lib/rag/detection/margins.py` following the established detection module pattern. Integrate into `_format_pdf_markdown` (in `lib/rag/processors/pdf.py`) by adding margin detection parameters similar to existing `written_page_*` parameters. Use `_get_cached_text_blocks` for performance consistency.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | Already installed | `get_text("dict")` for bbox data, `page.rect` for dimensions | Already the project's PDF engine; no new dependency |
| statistics (stdlib) | Python 3.9+ | median for robust body-column edge detection | Standard lib, no install |
| collections.Counter (stdlib) | Python 3.9+ | Histogram binning for edge position clustering | Already used in `headings.py` line 37 |
| re (stdlib) | Python 3.9+ | Stephanus/Bekker/line-number pattern matching | Already used throughout detection modules |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lib/rag/utils/cache._get_cached_text_blocks` | Internal | Cached block extraction (avoids 13.3x redundant extractions) | Use instead of raw `page.get_text("dict")` in margin detection |
| `lib/rag_data_models.NoteType.SIDENOTE` | Internal | Already defined enum value for margin notes | For future data model integration |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Statistical column inference | pdfplumber layout analysis | Adds dependency; PyMuPDF bbox data is sufficient |
| Custom edge clustering | scipy.stats.gaussian_kde | Overkill; Counter-based binning works for this |
| Per-page analysis only | Document-level zone learning | Per-page handles layout changes; doc-level is more stable for consistent layouts |

**Installation:** No new dependencies needed.

## Architecture Patterns

### Recommended Project Structure
```
lib/rag/detection/
├── margins.py           # NEW: Margin zone detection, body-column inference, block classification
├── margin_patterns.py   # NEW: Stephanus, Bekker, line-number regex matchers + typed classification
├── footnote_core.py     # EXISTING: Reference pattern for detection module design
├── footnotes.py         # EXISTING: Reference for re-export + facade pattern
├── footnote_markers.py  # EXISTING: Reference for marker matching helpers
├── headings.py          # EXISTING: Reference for font analysis + Counter usage
├── page_numbers.py      # EXISTING: Reference for first/last block position detection
├── toc.py               # EXISTING: Reference for document-level detection
├── front_matter.py      # EXISTING
└── __init__.py          # UPDATE: Add margin detection to re-exports
```

### Pattern 1: Detection Module Integration (VERIFIED from codebase)

**What:** New detection modules follow a specific pattern: a function called from `orchestrator_pdf.py` or `_format_pdf_markdown`, returning structured data that the formatter consumes.

**Actual integration points (verified):**

1. **`orchestrator_pdf.py` page loop** (line 322-416): Iterates pages, calls detection functions, passes results to `_format_pdf_markdown`. This is where footnote detection happens (`_detect_footnotes_in_page` at line 334). Margin detection should follow the same pattern.

2. **`_format_pdf_markdown` signature** (pdf.py line 29-41): Currently accepts these detection results as parameters:
   - `written_page_num`, `written_page_position`, `written_page_text` (from page_numbers detection)
   - `toc_entries` (from toc detection)
   - `quality_config`, `xmark_cache` (from quality pipeline)

   Add: `margin_blocks: list = None` parameter for pre-classified margin content.

3. **`_format_pdf_markdown` block loop** (pdf.py line 100-235): Iterates `blocks` (all blocks from `page.get_text("dict")`), processes text blocks sequentially. Key structure:
   ```python
   text_blocks = [b for b in blocks if b.get("type") == 0]  # line 97
   text_block_idx = 0                                        # line 98
   for block_idx, block in enumerate(blocks):                # line 100
       if block.get("type") != 0: continue                   # line 102
       analysis = _analyze_pdf_block(block, ...)              # line 108
       # ... heading/list/paragraph formatting ...
       text_block_idx += 1                                    # line 235
   ```

   **Integration approach:** Before this loop, cross-reference `blocks` against pre-classified `margin_blocks` (by bbox match). Skip margin blocks from the main loop; instead, insert them as `{{type: content}}` markers adjacent to the nearest body block.

**Example (matching actual codebase patterns):**
```python
# In orchestrator_pdf.py, inside the page loop (after line 333):
from lib.rag.detection.margins import detect_margin_content

# ... existing code ...
margin_result = detect_margin_content(page)

# Pass to _format_pdf_markdown
page_markdown = _format_md(
    page,
    # ... existing params ...
    margin_blocks=margin_result,  # NEW
)
```

### Pattern 2: Body Column Inference (Statistical)

**What:** Determine body text column boundaries from block position clustering. Uses same Counter-based binning approach as `headings.py` `_analyze_font_distribution`.

**Design (addressing user concern about hardcoded margins):**

The body column detection must NOT use hardcoded pixel/percentage thresholds for margin zones. Instead:

1. Collect left-edges (bbox[0]) and right-edges (bbox[2]) of all text blocks on the page
2. Bin edges with Counter (5pt bin size, matching PDF coordinate resolution)
3. The dominant left-edge = body column left boundary
4. The dominant right-edge = body column right boundary
5. Blocks outside these boundaries = margin candidates

**Why this handles the user's concern:**
- **Narrow margins:** If margins are narrow, the body column edges will be close to page edges. Blocks in margins will still have different x-positions than body text.
- **Scanned documents with offset:** Statistical inference adapts to wherever the majority of text actually sits, regardless of page geometry.
- **Scan artifacts:** Spurious blocks from scan noise will be outliers, not affecting the mode calculation.

**Fallback:** If <3 text blocks on page (insufficient data), use configurable percentage-based fallback (default 12% from each edge). This fallback percentage should be configurable via environment variable (e.g., `RAG_MARGIN_FALLBACK_PCT`).

```python
def _infer_body_column(text_blocks: list, page_rect, fallback_margin_pct: float = 0.12) -> tuple:
    """Infer body text column left/right boundaries."""
    if len(text_blocks) < 3:
        return (page_rect.x0 + page_rect.width * fallback_margin_pct,
                page_rect.x1 - page_rect.width * fallback_margin_pct)

    from collections import Counter
    BIN_SIZE = 5.0  # PyMuPDF coordinates are in points (1/72 inch)

    left_edges = [round(b["bbox"][0] / BIN_SIZE) * BIN_SIZE for b in text_blocks]
    right_edges = [round(b["bbox"][2] / BIN_SIZE) * BIN_SIZE for b in text_blocks]

    body_left = Counter(left_edges).most_common(1)[0][0]
    body_right = Counter(right_edges).most_common(1)[0][0]

    return (body_left, body_right)
```

### Pattern 3: Header/Footer Zone Exclusion (Robust Approach)

**What:** Exclude blocks in header/footer zones from margin classification. The user specifically asked: "Are we sure that hardcoding for the header and footer margins will be okay?"

**Answer: No. Pure percentage-based header/footer zones are NOT sufficient.** Here's why and the robust alternative:

**Problem with hardcoded zones (e.g., top/bottom 8%):**
- Scanned documents may have the text shifted up/down
- Some publishers use very large headers or very small footers
- Scan artifacts (smudges, page edges) can appear anywhere

**Robust approach: Statistical header/footer detection:**

1. **Existing page number detection** (`page_numbers.py`) already identifies header/footer text by checking first/last text lines. Leverage this.
2. **Vertical clustering:** Just as we cluster horizontal edges for body column, cluster vertical positions. Body text forms a dense cluster; header/footer blocks are isolated at extremes.
3. **Configurable threshold with smart default:** Use `RAG_HEADER_ZONE_PCT` and `RAG_FOOTER_ZONE_PCT` env vars (defaults: 0.08 each). But also cross-reference with the statistical vertical body zone — if a block is BOTH in the top percentage AND has text matching page-number/header patterns, exclude it.
4. **Safety net:** Any block that appears on >70% of pages with identical text is a running header/footer, regardless of position. This catches edge cases where headers are positioned unusually.

```python
def _classify_block_zone(block_bbox, body_left, body_right, page_rect,
                          header_zone_pct=None, footer_zone_pct=None,
                          running_headers=None):
    """Classify a block as body, margin-left, margin-right, header, footer, or running."""
    import os
    header_zone = header_zone_pct or float(os.getenv('RAG_HEADER_ZONE_PCT', '0.08'))
    footer_zone = footer_zone_pct or float(os.getenv('RAG_FOOTER_ZONE_PCT', '0.08'))

    x0, y0, x1, y1 = block_bbox
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2

    # Check running headers/footers first (most reliable)
    if running_headers:
        block_text = ...  # would need text
        if block_text in running_headers:
            return "running_header"

    # Percentage-based header/footer (configurable, not hardcoded)
    header_boundary = page_rect.y0 + page_rect.height * header_zone
    footer_boundary = page_rect.y1 - page_rect.height * footer_zone

    if center_y < header_boundary:
        return "header"
    if center_y > footer_boundary:
        return "footer"

    # Lateral classification
    tolerance = 5.0
    if x1 < body_left + tolerance:
        return "margin-left"
    if x0 > body_right - tolerance:
        return "margin-right"

    return "body"
```

### Pattern 4: Typed Classification (Stephanus, Bekker, Line Numbers)

**What:** After identifying margin blocks, classify their content using regex patterns.

**Per CONTEXT.md update:** Typed classification IS in scope. Format: `{{stephanus: 231a}}`, `{{bekker: 1094a1}}`, `{{line_number: 25}}`, `{{margin: content}}`.

```python
import re

# Stephanus: Used for Plato. Format: 3-digit number + letter a-e, optional range
STEPHANUS_RE = re.compile(r'^(\d{2,3}[a-e](?:\s*[-–]\s*[a-e])?)$')

# Bekker: Used for Aristotle. Format: 4-digit number + letter a/b + line number
BEKKER_RE = re.compile(r'^(\d{3,4}[ab]\d{1,2})$')

# Line numbers: Standalone integers 1-9999, typically in left margin of poetry/legal texts
LINE_NUMBER_RE = re.compile(r'^(\d{1,4})$')

def classify_margin_content(text: str) -> tuple:
    """Classify margin text and return (type, content).

    Returns:
        ('stephanus', '231a') or ('bekker', '1094a1') or
        ('line_number', '25') or ('margin', 'original text')
    """
    text = text.strip()

    if STEPHANUS_RE.match(text):
        return ('stephanus', text)
    if BEKKER_RE.match(text):
        return ('bekker', text)
    # Line numbers: only if purely numeric and in plausible range
    if LINE_NUMBER_RE.match(text):
        num = int(text)
        if 1 <= num <= 9999:
            return ('line_number', text)

    return ('margin', text)
```

**Confidence note (MEDIUM):** These regex patterns are based on scholarly convention knowledge. They should be validated against real scholarly PDFs. Stephanus ranges a-e (not a-z) are standard for Plato editions. Bekker uses a/b (the two columns of the Bekker edition of Aristotle). The line number pattern is intentionally conservative (exact match only, no surrounding text).

### Pattern 5: Margin-to-Body Association and Output

**What:** Associate each margin block with the nearest body text line, then insert typed markers inline.

```python
def _associate_margin_to_body(margin_block_bbox, body_blocks) -> int:
    """Find body block index nearest to margin block by y-center overlap."""
    m_center_y = (margin_block_bbox[1] + margin_block_bbox[3]) / 2

    best_idx = 0
    best_dist = float('inf')
    for i, body in enumerate(body_blocks):
        b_y0, b_y1 = body["bbox"][1], body["bbox"][3]
        if b_y0 <= m_center_y <= b_y1:
            return i  # Direct vertical overlap
        dist = min(abs(m_center_y - b_y0), abs(m_center_y - b_y1))
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx
```

**Integration in `_format_pdf_markdown`:**

The main block loop (pdf.py line 100-235) processes blocks sequentially and appends to `markdown_lines`. The cleanest integration:

1. Before the loop: Build a `margin_map: dict[int, list[str]]` mapping body block index to list of margin annotation strings
2. During the loop: After appending body text for a block, check if `text_block_idx` is in `margin_map` and append the annotations
3. This avoids modifying the existing block processing logic

```python
# Before main loop in _format_pdf_markdown:
margin_map = {}  # body_block_idx -> list of "{{type: content}}" strings
if margin_blocks:
    body_only = [b for b in blocks if b.get("type") == 0 and b not in margin_block_set]
    for mb in margin_blocks:
        text = _extract_text_from_margin_block(mb)
        mtype, mcontent = classify_margin_content(text)
        annotation = f"{{{{{mtype}: {mcontent}}}}}"
        idx = _associate_margin_to_body(mb["bbox"], body_only)
        margin_map.setdefault(idx, []).append(annotation)

# Inside the loop, after line 231 (paragraph append) or equivalent:
if text_block_idx in margin_map:
    for annotation in margin_map[text_block_idx]:
        markdown_lines.append(annotation)
```

### Anti-Patterns to Avoid
- **Fixed pixel thresholds for margins:** Page sizes vary (Letter=612x792, A4=595x842, custom sizes). Always use relative or statistical positions.
- **Hardcoded header/footer percentages without override:** The user explicitly flagged this. Always make configurable via env var.
- **Treating all small text as margins:** Position is primary; font size is secondary signal only.
- **Modifying `_analyze_pdf_block` internals:** Add margin detection as a parallel classification step, not by changing existing block analysis.
- **Ignoring the block cache:** Use `_get_cached_text_blocks` (from `lib/rag/utils/cache.py`) for consistency with footnote detection which already caches blocks.
- **Running margin detection after footnote detection without coordination:** Could cause double-detection. Margin detector should accept a set of "already-claimed" block bboxes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text block extraction | Custom PDF parser | `_get_cached_text_blocks(page, "dict")` | Already cached, consistent with footnote detection |
| Page dimensions | Manual mediabox parsing | `page.rect` | Handles rotation, cropbox automatically |
| Coordinate math | Custom geometry | PyMuPDF `Rect` class for intersection/containment | Edge cases with rotation handled |
| Block text extraction | Custom span joining | Existing `_extract_text_from_block` in `footnote_markers.py` | Already handles multi-line, multi-span blocks |
| Running header detection | Custom scan | Extend `_detect_written_page_on_page` pattern | page_numbers.py already detects first/last line content |
| Two-column detection | Custom heuristic | Check for bimodal left-edge distribution | Counter.most_common(2) gives this for free |

**Key insight:** The codebase already extracts all the spatial data needed. This phase is purely classification logic on existing data — no new PDF parsing.

## Common Pitfalls

### Pitfall 1: Two-Column Layout Misclassified as Body+Margin
**What goes wrong:** In two-column layouts, the right column gets classified as margin content.
**Why it happens:** Statistical body column detection finds only the left column's edges as dominant.
**How to avoid:** After computing body_left/body_right from Counter, check if left-edge distribution is **bimodal** (two distinct clusters). Use `Counter.most_common(2)` — if the second cluster has >30% the count of the first and is well-separated (>100pt gap), it's two-column. In that case, expand body zone to encompass both columns.
**Warning signs:** Large amounts of "margin" content with full sentences, not short references. Add a heuristic: if avg margin block text length > 50 chars, likely misclassified body text.

### Pitfall 2: Footnote/Margin Overlap
**What goes wrong:** Margin content near page bottom gets captured by both footnote and margin detectors.
**Why it happens:** Footnote detection uses bbox-based scanning (`_find_definition_for_marker` searches entire page below marker). Marginal notes near footnotes share the bottom area.
**How to avoid:** Run margin detection BEFORE footnote detection, or pass footnote block bboxes to margin detector as exclusions. The cleanest approach: margin detector returns its classified blocks, and footnote detector receives a "blocks to skip" set.
**Warning signs:** Duplicated content in both `[^marker]` footnote syntax and `{{margin:}}` annotations.

### Pitfall 3: Running Headers Classified as Top Margins
**What goes wrong:** Chapter titles, author names, or other running headers in the top zone get classified as left/right margin content.
**Why it happens:** Running headers sometimes sit at unusual x-positions (centered, right-aligned).
**How to avoid:** Implement running header detection: text appearing on >70% of pages with identical or near-identical content is a running header. Exclude these blocks before margin classification. The existing `page_numbers.py` `_detect_written_page_on_page` already detects first/last line content — extend this concept.
**Warning signs:** Same `{{margin:}}` text on every page.

### Pitfall 4: Scan Artifacts Creating False Margin Blocks
**What goes wrong:** OCR artifacts from page edges, binding shadows, or dirty scans create tiny text blocks in margin zones.
**Why it happens:** PyMuPDF may OCR noise as text with very low confidence.
**How to avoid:** Filter margin candidates by minimum text length (>1 char) and minimum block width (>10pt). Single-character blocks in margin zones are almost always noise.
**Warning signs:** Many single-character or empty `{{margin:}}` annotations.

### Pitfall 5: `_format_pdf_markdown` Uses Raw Blocks, Not Cached
**What goes wrong:** Performance inconsistency between margin detection (which should use cache) and the formatter (which calls `page.get_text("dict")` directly).
**Why it happens:** `_format_pdf_markdown` line 64 does `blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])` directly, while footnote detection uses `_get_cached_text_blocks`. These may return different data structures (the cache version doesn't pass `flags=fitz.TEXTFLAGS_DICT`).
**How to avoid:** Verify that the cache's default extraction (no explicit flags) produces the same block structure as the explicit `TEXTFLAGS_DICT` call. If different, either update the cache to accept flags or have margin detection use the same direct extraction as the formatter. **This is a real discrepancy in the current codebase that should be investigated.**
**Warning signs:** Block index mismatches between margin detection and formatter.

### Pitfall 6: Scanned Documents with Non-Standard CropBox
**What goes wrong:** `page.rect` returns the CropBox, not the MediaBox. If a scan has a tight CropBox, margin zones may be cropped out entirely.
**Why it happens:** PyMuPDF `page.rect` returns the visible area (CropBox), which may be smaller than the physical page (MediaBox). Text outside the CropBox is invisible.
**How to avoid:** PyMuPDF's `TEXT_MEDIABOX_CLIP` flag (default ON) already clips text to MediaBox boundaries. For scanned documents, if CropBox is significantly smaller than MediaBox, use `page.mediabox` instead of `page.rect` for zone calculations. Check: `if page.cropbox != page.mediabox: use mediabox`.
**Warning signs:** Margin content expected but not found; `page.rect` much smaller than expected.

## Code Examples

### Actual PyMuPDF Block Structure (verified from codebase usage)

```python
# Source: lib/rag/processors/pdf.py line 64
blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

# Text block (type==0) - VERIFIED structure from footnote_core.py, headings.py:
# {
#     "type": 0,                        # 0=text, 1=image
#     "bbox": (x0, y0, x1, y1),         # Block bounding box in points
#     "lines": [                         # List of text lines
#         {
#             "wmode": 0,                # Writing mode (0=horizontal)
#             "dir": (1.0, 0.0),         # Text direction vector
#             "bbox": (x0, y0, x1, y1),  # Line bounding box
#             "spans": [                  # List of text spans
#                 {
#                     "size": 11.0,      # Font size in points
#                     "flags": 4,        # PyMuPDF flags: 1=superscript, 2=italic, 4=serifed, 8=mono, 16=bold
#                     "font": "TimesNewRoman",
#                     "color": 0,        # Color as integer
#                     "origin": (x, baseline_y),  # Text origin point
#                     "text": "content",
#                     "bbox": (x0, y0, x1, y1)  # Span bounding box
#                 }
#             ]
#         }
#     ]
# }

# Image block (type==1) - skip in margin detection:
# {
#     "type": 1,
#     "bbox": (x0, y0, x1, y1),
#     ...  # image data, not relevant
# }
```

### Page Geometry (verified from Context7)

```python
# page.rect returns CropBox (visible area), page.mediabox returns physical page
page_rect = page.rect          # e.g., Rect(0.0, 0.0, 595.0, 842.0) for A4
page_width = page_rect.width   # 595.0
page_height = page_rect.height # 842.0

# For scanned docs, check if CropBox differs from MediaBox
if page.cropbox != page.mediabox:
    # Use mediabox for more complete margin analysis
    page_rect = page.mediabox
```

### Cache Usage Pattern (from lib/rag/utils/cache.py)

```python
# Footnote detection uses cached blocks:
from lib.rag.utils.cache import _get_cached_text_blocks
blocks = _get_cached_text_blocks(page, "dict")  # Returns page.get_text("dict")["blocks"]

# WARNING: This does NOT pass flags=fitz.TEXTFLAGS_DICT
# While _format_pdf_markdown uses:
blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
# These may differ. Investigate before relying on cache for margin detection.
```

### Complete Margin Detection Function Skeleton

```python
"""Margin zone detection and classification for scholarly PDFs."""
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Typed classification patterns
STEPHANUS_RE = re.compile(r'^(\d{2,3}[a-e](?:\s*[-–]\s*[a-e])?)$')
BEKKER_RE = re.compile(r'^(\d{3,4}[ab]\d{1,2})$')
LINE_NUMBER_RE = re.compile(r'^(\d{1,4})$')


def detect_margin_content(
    page: Any,
    excluded_bboxes: Optional[Set[Tuple]] = None,
    header_zone_pct: Optional[float] = None,
    footer_zone_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Detect and classify margin content on a PDF page.

    Args:
        page: PyMuPDF page object
        excluded_bboxes: Set of bbox tuples already claimed by other detectors
        header_zone_pct: Override for header zone (default from RAG_HEADER_ZONE_PCT env or 0.08)
        footer_zone_pct: Override for footer zone (default from RAG_FOOTER_ZONE_PCT env or 0.08)

    Returns:
        {
            'margin_blocks': [{'bbox': ..., 'text': ..., 'type': 'stephanus'|'bekker'|'line_number'|'margin', 'content': ...}],
            'body_column': (left, right),  # Inferred body column boundaries
            'is_two_column': bool,
        }
    """
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Absolute margin thresholds | Statistical column inference | Best practice (no migration) | Adapts to any layout without configuration |
| Separate margin pass | Integrated pre-processing step | This phase design | Single block scan with zone classification |
| Generic `{{margin:}}` only | Typed `{{stephanus:}}`, `{{bekker:}}` etc. | Roadmap requirement | Structured annotations for downstream AI consumption |
| Hardcoded header/footer zones | Configurable + statistical zones | User requirement | Handles scanned docs with narrow/shifted margins |

## Open Questions

1. **Cache vs direct extraction discrepancy**
   - What we know: `_get_cached_text_blocks(page, "dict")` calls `page.get_text("dict")["blocks"]` without flags. `_format_pdf_markdown` calls `page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])` with explicit flags.
   - What's unclear: Whether `TEXTFLAGS_DICT` changes the block structure or just the default flags. PyMuPDF docs say `TEXTFLAGS_DICT` is the default for "dict" mode, so they may be identical.
   - Recommendation: Test empirically. If identical, use cache. If different, either update cache to accept flags or use direct extraction consistently.
   - **Confidence: LOW** — needs empirical validation.

2. **Running header detection scope**
   - What we know: Running headers should be excluded from margin classification.
   - What's unclear: Whether to implement running header detection in this phase or defer to Phase 11 (Body Text Purity).
   - Recommendation: Implement basic running header detection (text appearing on >70% of pages in header zone) in this phase. It's cheap and prevents false positives. A more sophisticated version can come in Phase 11.

3. **Facing pages in bound scans**
   - What we know: Bound book scans may have margin content on the inside (gutter) or outside edges, switching sides on recto/verso pages.
   - What's unclear: How common this is in the user's PDF collection.
   - Recommendation: Detect margin on BOTH sides regardless of page parity. Don't assume margin position based on even/odd pages. The statistical approach handles this naturally.

4. **Interaction ordering with other detectors**
   - What we know: Currently in `orchestrator_pdf.py`, detection order is: ToC → page numbers → footnotes → per-page formatting.
   - What's unclear: Whether margin detection should run before or after footnote detection.
   - Recommendation: Run margin detection BEFORE footnote detection. Pass margin-classified blocks as exclusions to footnote detector. This prevents footnote definitions in margin areas from being double-classified. However, this changes the orchestrator flow — may be simpler to just run independently and deduplicate in Phase 11.

5. **Stephanus/Bekker regex validation**
   - What we know: Patterns based on scholarly convention knowledge from training data.
   - What's unclear: Edge cases in real scholarly PDFs (unusual formatting, OCR errors in reference numbers).
   - Recommendation: Test against real PDFs from the user's collection before finalizing. Mark patterns as MEDIUM confidence until validated.
   - **Confidence: MEDIUM** — patterns are well-known scholarly conventions but unvalidated against this pipeline's specific PDFs.

## Sources

### Primary (HIGH confidence)
- `/pymupdf/pymupdf` (Context7) — `get_text("dict")` output structure, `page.rect` vs `page.mediabox`, `TEXT_MEDIABOX_CLIP` flag behavior, CropBox/MediaBox distinction
- `lib/rag/processors/pdf.py` — Exact `_format_pdf_markdown` signature (line 29-41), block loop structure (line 100-235), `get_text("dict", flags=fitz.TEXTFLAGS_DICT)` call (line 64)
- `lib/rag/orchestrator_pdf.py` — Page processing loop (line 322-416), detection call ordering, `_format_md` invocation pattern (line 379-391)
- `lib/rag/detection/footnote_core.py` — Detection module pattern, `_get_cached_text_blocks` usage (line 184), `_calculate_page_normal_font_size` approach (line 44-82)
- `lib/rag/detection/page_numbers.py` — Header/footer position detection pattern (first/last line), `_detect_written_page_on_page` approach
- `lib/rag/detection/headings.py` — `Counter`-based font size mode (line 75-76), font distribution analysis pattern
- `lib/rag/utils/cache.py` — Cache API, discrepancy with direct extraction flags
- `lib/rag_data_models.py` — `NoteType.SIDENOTE` already exists (line 62), `PageRegion`/`TextSpan` data model patterns

### Secondary (MEDIUM confidence)
- Phase 9 CONTEXT.md — User decisions on typed format, inline placement, configurable thresholds
- Stephanus/Bekker regex patterns — Based on classical studies conventions (Plato/Aristotle reference systems)

### Tertiary (LOW confidence)
- Running header detection threshold (70%) — Heuristic, needs tuning with real data
- Two-column detection bimodal threshold (30% count ratio, 100pt gap) — Heuristic, needs tuning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyMuPDF is the project's engine; no new dependencies; all APIs verified from codebase
- Architecture / integration points: HIGH — Verified exact line numbers, function signatures, and data flow from source code
- Spatial classification algorithm: MEDIUM — Sound approach but thresholds (bin size, tolerances) need tuning with real PDFs
- Header/footer robustness: MEDIUM — Configurable + statistical approach addresses user concern; running header detection is a heuristic
- Typed classification regex: MEDIUM — Based on scholarly conventions; unvalidated against actual pipeline PDFs
- Cache consistency: LOW — Discrepancy between cache and direct extraction needs empirical validation

**Research date:** 2026-02-02
**Valid until:** 2026-03-04 (stable domain, 30 days)
