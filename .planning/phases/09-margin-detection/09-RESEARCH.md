# Phase 9: Margin Detection & Scholarly References - Research

**Researched:** 2026-02-02
**Domain:** PDF spatial text analysis, scholarly margin content extraction
**Confidence:** MEDIUM

## Summary

Phase 9 adds margin content detection to the existing RAG pipeline. The task is fundamentally a **spatial classification problem**: given text blocks with bounding boxes on a PDF page, determine which blocks fall in margin zones vs body text zones, then annotate the output accordingly.

PyMuPDF already provides all necessary spatial data. Each text block from `page.get_text("dict")` includes `bbox` coordinates `(x0, y0, x1, y1)`. The page dimensions come from `page.rect` (width, height). No new libraries are needed — this is purely algorithmic work on top of existing infrastructure.

The main challenge is **adaptive margin zone detection** across diverse publisher layouts. Margins vary from 10% to 25%+ of page width depending on the edition. A static threshold will fail. The recommended approach is a **statistical body-text column detector** that infers the main text column boundaries from block position clustering, then classifies outliers as margin content.

**Primary recommendation:** Build a margin zone detector as a new module under `lib/rag/detection/margins.py` that analyzes block bbox positions relative to inferred body-text column boundaries, integrated into `_format_pdf_markdown` similar to how footnotes and page numbers are handled.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | Already installed | Text block extraction with bbox coordinates | Already the project's PDF engine; `get_text("dict")` provides all spatial data needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| statistics (stdlib) | Python 3.9+ | Median/mode for column detection | Body text column boundary inference |
| collections (stdlib) | Python 3.9+ | Counter for font/position frequency | Clustering block positions |
| re (stdlib) | Python 3.9+ | Stephanus/Bekker pattern matching | Future typed classification (deferred but patterns documented here) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom column detector | pdfplumber layout analysis | pdfplumber adds dependency; PyMuPDF bbox data is sufficient |
| Statistical clustering | ML-based zone detection | Overkill for this scope; scholarly PDFs have predictable layouts |
| Per-page analysis | Document-level zone learning | Per-page is simpler but less accurate for consistent layouts |

**Installation:** No new dependencies needed.

## Architecture Patterns

### Recommended Project Structure
```
lib/rag/detection/
├── margins.py           # NEW: Margin zone detection and classification
├── margin_patterns.py   # NEW: Reference pattern matchers (for future typed classification)
├── footnotes.py         # Existing: Footnote detection (similar pattern)
├── headings.py          # Existing: Heading detection (similar pattern)
├── page_numbers.py      # Existing: Page number detection (similar pattern)
└── toc.py               # Existing: ToC detection
```

### Pattern 1: Spatial Zone Classification
**What:** Classify each text block as "body" or "margin" based on its bbox position relative to inferred body column boundaries.
**When to use:** Every page during PDF processing.
**Example:**
```python
# Source: Project's existing PyMuPDF usage pattern
def detect_margin_zones(page: 'fitz.Page') -> dict:
    """Detect margin zones and classify text blocks."""
    page_rect = page.rect  # Rect(x0, y0, x1, y1) - page dimensions
    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

    # Each text block has bbox: (x0, y0, x1, y1)
    text_blocks = [b for b in blocks if b.get("type") == 0]

    # Infer body column boundaries from block position clustering
    body_left, body_right = _infer_body_column(text_blocks, page_rect)

    margin_blocks = []
    body_blocks = []
    for block in text_blocks:
        bx0, by0, bx1, by1 = block["bbox"]
        # Block center x determines classification
        center_x = (bx0 + bx1) / 2
        if center_x < body_left or center_x > body_right:
            margin_blocks.append(block)
        else:
            body_blocks.append(block)

    return {"margin": margin_blocks, "body": body_blocks}
```

### Pattern 2: Body Column Inference (Statistical)
**What:** Determine the body text column boundaries by finding the most common left/right edges among text blocks.
**When to use:** Once per page (or once per document if layout is consistent).
**Example:**
```python
def _infer_body_column(text_blocks: list, page_rect) -> tuple:
    """Infer body text column left/right boundaries from block positions."""
    if not text_blocks:
        # Fallback: assume 15% margins
        margin_pct = 0.15
        return (page_rect.x0 + page_rect.width * margin_pct,
                page_rect.x1 - page_rect.width * margin_pct)

    # Collect left edges of all text blocks
    left_edges = [b["bbox"][0] for b in text_blocks]
    right_edges = [b["bbox"][2] for b in text_blocks]

    # Body text has the most blocks at consistent positions
    # Use histogram binning (5pt bins) to find dominant positions
    from collections import Counter
    def mode_of_edges(edges, bin_size=5.0):
        binned = [round(e / bin_size) * bin_size for e in edges]
        counter = Counter(binned)
        return counter.most_common(1)[0][0] if counter else edges[0]

    body_left = mode_of_edges(left_edges)
    body_right = mode_of_edges(right_edges)

    return (body_left, body_right)
```

### Pattern 3: Margin-to-Body Line Association
**What:** Associate each margin block with the nearest body text line by y-coordinate overlap.
**When to use:** When placing `{{margin: content}}` markers inline with body text.
**Example:**
```python
def _associate_margin_to_body(margin_block: dict, body_blocks: list) -> int:
    """Find the body block index closest to this margin block (by y-overlap)."""
    m_y0, m_y1 = margin_block["bbox"][1], margin_block["bbox"][3]
    m_center_y = (m_y0 + m_y1) / 2

    best_idx = 0
    best_dist = float('inf')
    for i, body in enumerate(body_blocks):
        b_y0, b_y1 = body["bbox"][1], body["bbox"][3]
        # Check y-overlap or proximity
        if b_y0 <= m_center_y <= b_y1:
            return i  # Direct overlap
        dist = min(abs(m_center_y - b_y0), abs(m_center_y - b_y1))
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx
```

### Pattern 4: Integration into _format_pdf_markdown
**What:** Add margin detection as a pre-processing step before block iteration, similar to footnote handling.
**When to use:** In the existing PDF formatting pipeline.
**Example:**
```python
# In _format_pdf_markdown, before the main block loop:
margin_result = detect_margin_zones(page)
margin_map = {}  # body_block_index -> list of margin texts
for mb in margin_result["margin"]:
    text = _extract_margin_text(mb)
    idx = _associate_margin_to_body(mb, margin_result["body"])
    margin_map.setdefault(idx, []).append(text)

# During block iteration, after processing each body block:
if text_block_idx in margin_map:
    for margin_text in margin_map[text_block_idx]:
        markdown_lines.append(f"{{{{margin: {margin_text}}}}}")
```

### Anti-Patterns to Avoid
- **Fixed pixel thresholds:** Don't use absolute pixel values for margin detection — page sizes vary (Letter, A4, custom). Use relative positions or statistical inference.
- **Treating all small text as margins:** Small font alone doesn't indicate margin content; position is the primary classifier, font size is secondary.
- **Per-publisher configurations:** Don't build publisher-specific layout profiles; the statistical approach adapts automatically.
- **Modifying existing block processing:** Don't change `_analyze_pdf_block` internals. Add margin detection as a parallel pre-processing step.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text block extraction | Custom PDF parser | PyMuPDF `get_text("dict")` | Already used; blocks include bbox, font info, everything needed |
| Page dimensions | Manual mediabox parsing | `page.rect` | PyMuPDF handles rotation, cropbox adjustments |
| Coordinate math | Custom geometry | PyMuPDF `Rect` class | Supports intersection, containment, transforms |
| Text joining | Custom line merger | Existing `_analyze_pdf_block` logic | Already handles hyphenation, line joining |

**Key insight:** PyMuPDF provides all the spatial data. This phase is purely classification logic on top of existing extraction — no new PDF parsing needed.

## Common Pitfalls

### Pitfall 1: Confusing Running Headers/Footers with Margin Content
**What goes wrong:** Running headers, footers, and page numbers in header/footer zones get classified as margin content.
**Why it happens:** They often appear outside the body text column boundaries.
**How to avoid:** Exclude blocks in the top/bottom 8-10% of the page from margin detection. Page numbers are already handled by `detection/page_numbers.py`. Add a vertical zone filter before lateral zone classification.
**Warning signs:** Same text appearing as `{{margin:}}` on every page (e.g., chapter titles, author names).

### Pitfall 2: Two-Column Text Misidentified as Body+Margin
**What goes wrong:** In two-column layouts, one column gets classified as margin content.
**Why it happens:** Statistical body column detection assumes a single main column.
**How to avoid:** Detect multi-column layouts by checking if block left-edges form two distinct clusters rather than one. If two-column detected, widen the body zone to encompass both columns.
**Warning signs:** Large amounts of "margin" content with full sentences rather than short references.

### Pitfall 3: Font Size Assumptions
**What goes wrong:** Using font size as a primary discriminator for margin content.
**Why it happens:** Margin references are often smaller, but so are footnotes, captions, and index entries.
**How to avoid:** Use position (bbox) as the primary classifier. Font size can be a secondary signal for disambiguation but should not be the sole criterion.
**Warning signs:** Footnotes being double-detected as both footnotes and margin content.

### Pitfall 4: Narrow Margin Content Spanning Multiple Blocks
**What goes wrong:** A single marginal reference (e.g., "231a") split across two PyMuPDF blocks.
**Why it happens:** PyMuPDF may split text that's visually contiguous if it spans lines or has font changes.
**How to avoid:** After classifying margin blocks, merge adjacent margin blocks (within 5pt vertically, same x-zone) before extracting text.
**Warning signs:** Partial references appearing as separate `{{margin:}}` markers.

### Pitfall 5: Interaction with Existing Footnote Detection
**What goes wrong:** Margin content near the page bottom gets captured by both footnote detection and margin detection.
**Why it happens:** Marginal notes near footnote areas overlap with footnote detection zones.
**How to avoid:** Run margin detection before or independently of footnote detection. Use the existing footnote detection's bbox information to exclude those blocks from margin classification. Phase 11 (Body Text Purity) will compose all detectors.
**Warning signs:** Duplicated content in both footnote and margin annotations.

## Code Examples

### PyMuPDF Block Structure (from existing codebase)
```python
# Source: Verified from lib/rag/processors/pdf.py line 64
blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

# Each text block (type==0) structure:
# {
#     "type": 0,
#     "bbox": (x0, y0, x1, y1),  # Bounding box coordinates
#     "lines": [
#         {
#             "wmode": 0,
#             "dir": (1.0, 0.0),
#             "bbox": (x0, y0, x1, y1),
#             "spans": [
#                 {
#                     "size": 11.0,
#                     "flags": 0,
#                     "font": "Helvetica",
#                     "color": 0,
#                     "origin": (x0, baseline_y),
#                     "text": "Some text",
#                     "bbox": (x0, y0, x1, y1)
#                 }
#             ]
#         }
#     ]
# }
```

### Page Dimensions
```python
# Source: PyMuPDF docs (Context7 verified)
page_rect = page.rect  # e.g., Rect(0.0, 0.0, 595.0, 842.0) for A4
page_width = page_rect.width   # 595.0
page_height = page_rect.height  # 842.0
```

### Margin Zone Detection Core Logic
```python
def _classify_block_zone(block_bbox, body_left, body_right,
                         page_rect, header_zone=0.08, footer_zone=0.08):
    """Classify a block as body, margin-left, margin-right, header, or footer."""
    x0, y0, x1, y1 = block_bbox
    center_x = (x0 + x1) / 2
    center_y = (y0 + y1) / 2

    # Header/footer exclusion
    if center_y < page_rect.y0 + page_rect.height * header_zone:
        return "header"
    if center_y > page_rect.y1 - page_rect.height * footer_zone:
        return "footer"

    # Lateral classification with tolerance
    tolerance = 5.0  # points
    if x1 < body_left + tolerance:
        return "margin-left"
    if x0 > body_right - tolerance:
        return "margin-right"

    return "body"
```

### Stephanus/Bekker Patterns (for future typed classification, documented now)
```python
# These patterns are DEFERRED but documented for future reference
import re

# Stephanus: 231a, 245b-c, 100d, typically 3-digit + letter (a-e)
STEPHANUS_PATTERN = re.compile(r'\b(\d{2,3}[a-e](?:-[a-e])?)\b')

# Bekker: 1094a1, 1140b5, typically 4-digit + letter + digit
BEKKER_PATTERN = re.compile(r'\b(\d{3,4}[ab]\d{1,2})\b')

# Line numbers: standalone integers, often in left margin
LINE_NUMBER_PATTERN = re.compile(r'^\s*(\d{1,5})\s*$')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pdfminer layout analysis | PyMuPDF dict extraction | Already in project | PyMuPDF is faster and provides richer block-level spatial data |
| Absolute margin thresholds | Statistical column detection | Best practice | Adapts to any publisher layout without configuration |
| Separate margin extraction pass | Integrated pipeline step | Current design | Single pass through blocks with zone classification |

**Deprecated/outdated:**
- pdfplumber for this use case: PyMuPDF is already the project's engine and provides equivalent spatial data
- Rule-based publisher profiles: Statistical approach supersedes manual rules

## Open Questions

1. **Document-level vs page-level column detection**
   - What we know: Page-level is simpler and handles layout changes mid-document. Document-level is more stable for consistent layouts.
   - What's unclear: How often scholarly PDFs change layout mid-document (e.g., front matter vs body).
   - Recommendation: Start with page-level, add document-level averaging as refinement. Use the first N pages to establish a baseline, allow per-page overrides.

2. **Threshold for "margin vs narrow body text"**
   - What we know: Some scholarly texts have indented block quotes that sit between margin and body zones.
   - What's unclear: Optimal tolerance values for distinguishing indented body text from margin content.
   - Recommendation: Classify based on block width — margin content is typically very narrow (< 20% of page width), while indented quotes are wider. Combine position + width heuristics.

3. **Integration point in the pipeline**
   - What we know: `_format_pdf_markdown` is the page-level formatter. Footnote detection runs alongside it in `orchestrator_pdf.py`.
   - What's unclear: Whether margin detection should be a parameter to `_format_pdf_markdown` (like footnotes) or a separate post-processing step.
   - Recommendation: Follow the footnote pattern — detect margins before formatting, pass results into `_format_pdf_markdown` as a parameter. This keeps the architecture consistent.

4. **Interaction with existing detectors**
   - What we know: Page numbers, footnotes, headers are already detected. All use bbox coordinates.
   - What's unclear: Exact deduplication strategy when margin content overlaps with page number or footnote zones.
   - Recommendation: Run margin detection after page number and footnote detection, exclude blocks already claimed by those detectors.

## Sources

### Primary (HIGH confidence)
- `/pymupdf/pymupdf` (Context7) — Block structure, bbox format, page.rect, get_text("dict") output schema
- Project codebase: `lib/rag/processors/pdf.py` — Existing block processing pattern
- Project codebase: `lib/rag/detection/footnote_core.py` — Detection module pattern to follow
- Project codebase: `lib/rag/quality/analysis.py` — `_analyze_pdf_block` bbox handling

### Secondary (MEDIUM confidence)
- Project codebase: `lib/rag_data_models.py` — Data model patterns (PageRegion, TextSpan)
- Phase 9 CONTEXT.md — User decisions on format and scope

### Tertiary (LOW confidence)
- Stephanus/Bekker regex patterns — Based on training data knowledge of classical reference systems; patterns should be validated against real scholarly PDFs before use in future typed classification phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyMuPDF is already the project's engine; no new dependencies
- Architecture: HIGH — Follows established detection module pattern (footnotes, page numbers, headings)
- Spatial classification algorithm: MEDIUM — Statistical approach is sound but thresholds need tuning with real PDFs
- Pitfalls: MEDIUM — Based on understanding of PDF structure and existing codebase patterns

**Research date:** 2026-02-02
**Valid until:** 2026-03-04 (stable domain, 30 days)
