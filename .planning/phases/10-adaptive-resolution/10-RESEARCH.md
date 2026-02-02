# Phase 10: Adaptive Resolution Pipeline - Research

**Researched:** 2026-02-02
**Domain:** PDF rendering DPI optimization for OCR quality (PyMuPDF + Tesseract)
**Confidence:** HIGH

## Summary

This phase replaces the current fixed 300 DPI rendering with an adaptive pipeline that selects optimal DPI per page and per region based on measured text size. The core insight is that Tesseract's accuracy correlates with character pixel height, not DPI itself. By measuring font sizes from PyMuPDF's text layer (available without rendering) and computing the DPI needed to place characters in the optimal pixel height range, we can render text-heavy pages at lower DPI (faster, less memory) and fine-print regions at higher DPI (better accuracy).

The existing codebase already has all infrastructure needed: PyMuPDF's `get_pixmap(dpi=N, clip=rect)` supports per-region rendering at arbitrary DPI, `_calculate_page_normal_font_size()` extracts font size distributions, margin/footnote detection provides region bounding boxes, and `_detect_xmarks_parallel()` provides a proven `ProcessPoolExecutor` pattern for parallel page processing.

**Primary recommendation:** Implement a two-pass architecture: Pass 1 analyzes font sizes from PyMuPDF text dict (no rendering, fast), computes optimal DPI per page and identifies regions needing higher DPI. Pass 2 renders pages at computed DPI, with selective re-rendering of flagged regions at elevated DPI.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | >=1.26.0 | PDF rendering with `get_pixmap(dpi=N, clip=rect)` | Already in project; supports clip+DPI combo natively |
| pytesseract | (existing) | OCR execution | Already in project; Tesseract is the OCR engine |
| Pillow (PIL) | (existing) | Image handling between PyMuPDF and Tesseract | Already in project |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| concurrent.futures | stdlib | ProcessPoolExecutor for parallel page analysis | Pages are independent; pattern exists in xmark detection |
| os | stdlib | `os.cpu_count()` for auto-detecting concurrency | Already used in xmark parallel code |
| dataclasses | stdlib | DPI decision metadata structs | Clean structured output |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF text dict for font analysis | Rendering + OCR-based size estimation | Text dict is free (no rendering cost), OCR-based is expensive but works for scanned PDFs |
| ProcessPoolExecutor | asyncio | CPU-bound work (rendering) benefits from true parallelism; asyncio only helps I/O |
| Per-page analysis | Sampling (analyze every Nth page) | Sampling is faster for long docs but misses page-specific variation |

**Installation:** No new dependencies needed. Everything is already in the project.

## Architecture Patterns

### Recommended Module Structure

```
lib/rag/
├── resolution/              # NEW - Phase 10
│   ├── __init__.py
│   ├── analyzer.py          # Font size analysis, DPI computation
│   ├── renderer.py          # Adaptive rendering (page + region)
│   └── models.py            # DPIDecision, RegionDPI, PageAnalysis dataclasses
├── ocr/
│   └── recovery.py          # Modified: accept DPI parameter instead of hardcoded 300
└── orchestrator_pdf.py      # Modified: insert adaptive resolution before OCR
```

### Pattern 1: DPI Calculation from Font Size

**What:** Compute optimal DPI to place text characters in Tesseract's optimal pixel height range.

**Formula:**
```
pixel_height = font_size_pt * (dpi / 72)

Target: pixel_height in [20, 33] (Tesseract optimal x-height range)

Therefore: optimal_dpi = target_pixel_height * 72 / font_size_pt
```

**When to use:** Every page, using the dominant font size from `_calculate_page_normal_font_size()`.

**Example:**
```python
# Source: Tesseract docs + PyMuPDF font size data
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict

@dataclass
class DPIDecision:
    """Result of DPI analysis for a page or region."""
    dpi: int
    confidence: float  # 0.0-1.0
    reason: str
    font_size_pt: float
    estimated_pixel_height: float

# DPI floor/ceiling constants
DPI_FLOOR = 72
DPI_CEILING = 600
DPI_DEFAULT = 300  # fallback when analysis fails

# Tesseract optimal pixel height range
TARGET_PIXEL_HEIGHT_MIN = 20
TARGET_PIXEL_HEIGHT_MAX = 33
TARGET_PIXEL_HEIGHT_IDEAL = 28  # middle of sweet spot

def compute_optimal_dpi(font_size_pt: float) -> DPIDecision:
    """Compute DPI that places text at Tesseract's optimal pixel height."""
    if font_size_pt <= 0:
        return DPIDecision(
            dpi=DPI_DEFAULT, confidence=0.0,
            reason="invalid_font_size", font_size_pt=font_size_pt,
            estimated_pixel_height=0.0
        )

    # DPI = target_px * 72 / font_size_pt
    ideal_dpi = TARGET_PIXEL_HEIGHT_IDEAL * 72 / font_size_pt
    clamped_dpi = max(DPI_FLOOR, min(DPI_CEILING, round(ideal_dpi)))

    # Quantize to multiples of 50 for caching benefit
    quantized_dpi = round(clamped_dpi / 50) * 50
    quantized_dpi = max(DPI_FLOOR, min(DPI_CEILING, quantized_dpi))

    actual_pixel_height = font_size_pt * quantized_dpi / 72
    in_range = TARGET_PIXEL_HEIGHT_MIN <= actual_pixel_height <= TARGET_PIXEL_HEIGHT_MAX
    confidence = 1.0 if in_range else 0.7

    return DPIDecision(
        dpi=quantized_dpi,
        confidence=confidence,
        reason="computed" if in_range else "clamped",
        font_size_pt=font_size_pt,
        estimated_pixel_height=actual_pixel_height
    )
```

### Pattern 2: Page-Level Font Analysis (No Rendering Required)

**What:** Extract font size distribution from PyMuPDF text dict without rendering.
**When to use:** First pass on every page.

**Example:**
```python
def analyze_page_fonts(page: 'fitz.Page') -> Dict[str, any]:
    """Analyze font sizes on a page using text dict (no rendering)."""
    blocks = page.get_text("dict")["blocks"]
    sizes = []
    for block in blocks:
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                size = span.get('size', 0)
                if size > 0:
                    sizes.append(size)

    if not sizes:
        return {'dominant_size': 0, 'min_size': 0, 'has_small_text': False}

    # Dominant = median (robust to headers/footnotes)
    sizes.sort()
    median = sizes[len(sizes) // 2]

    return {
        'dominant_size': median,
        'min_size': min(sizes),
        'max_size': max(sizes),
        'has_small_text': min(sizes) < median * 0.7,
        'size_distribution': sizes,
    }
```

### Pattern 3: Region Re-Rendering with Clip

**What:** Re-render specific page regions (footnotes, margins) at higher DPI using PyMuPDF's clip parameter.
**When to use:** When a region contains text significantly smaller than the page dominant size.

**Example:**
```python
# Source: PyMuPDF Context7 docs - get_pixmap with clip
def render_region_at_dpi(page: 'fitz.Page', bbox: tuple, dpi: int) -> bytes:
    """Render a specific region of a page at target DPI."""
    import pymupdf
    clip_rect = pymupdf.Rect(bbox)
    pix = page.get_pixmap(dpi=dpi, clip=clip_rect)
    return pix.tobytes("png")
```

### Pattern 4: Parallel Page Analysis (Existing Pattern)

**What:** Use ProcessPoolExecutor for parallel page processing, following xmark detection pattern.
**When to use:** Document with >10 pages.

**Example:**
```python
# Pattern from lib/rag/xmark/detection.py
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

def analyze_pages_parallel(pdf_path, page_count, max_workers=4):
    cpu_count = os.cpu_count() or 4
    workers = min(max_workers, cpu_count, page_count)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(analyze_single_page, pdf_path, i): i
            for i in range(page_count)
        }
        results = {}
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                results[page_num] = future.result()
            except Exception as e:
                logging.error(f"Page {page_num} analysis failed: {e}")
                results[page_num] = None
    return results
```

### Anti-Patterns to Avoid

- **Rendering to measure text size:** PyMuPDF provides font sizes directly from the text dict. Never render a page just to measure character pixel heights.
- **Per-span DPI optimization:** Optimizing DPI for every individual text span creates too many re-renders. Use page-level dominant size + region-level exceptions.
- **Ignoring scanned PDFs:** Scanned PDFs have no text layer, so font analysis returns nothing. Must detect this case (via `detect_pdf_quality()`) and fall back to fixed 300 DPI or image-based size estimation.
- **Too-fine DPI quantization:** Rendering at 287 vs 293 DPI produces negligible quality difference but defeats caching. Quantize to multiples of 50.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font size extraction | Custom PDF parser | `page.get_text("dict")` spans' `size` field | PyMuPDF already extracts this; robust across PDF types |
| Page rendering | Manual matrix math | `page.get_pixmap(dpi=N, clip=rect)` | PyMuPDF handles DPI-to-matrix conversion since v1.19.2 |
| Region bounding boxes | New region detector | Phase 9 margin detection + existing footnote detection | Margin zones and footnote bboxes already detected |
| Parallel execution | Custom threading | `concurrent.futures.ProcessPoolExecutor` | Existing pattern in xmark detection, proven in codebase |
| Median calculation | Custom stats | Sort + index (already in `_calculate_page_normal_font_size`) | Simple, no numpy needed |

**Key insight:** The hardest parts (font extraction, region detection, parallel processing, PDF rendering with clip) are all solved by existing infrastructure. This phase is primarily orchestration and DPI math.

## Common Pitfalls

### Pitfall 1: Scanned PDFs Have No Text Layer

**What goes wrong:** Font analysis returns empty/zero sizes for scanned-image PDFs.
**Why it happens:** Scanned PDFs are images, not text. `get_text("dict")` returns no spans.
**How to avoid:** Check `detect_pdf_quality()` result. If quality is "SCANNED" or "IMAGE_ONLY", skip adaptive DPI and use fixed 300 DPI (current behavior). The existing quality detection pipeline already classifies this.
**Warning signs:** `analyze_page_fonts()` returns `dominant_size: 0`.

### Pitfall 2: Mixed Font Sizes on Same Page

**What goes wrong:** Page has 12pt body text and 7pt footnotes. Optimizing for 12pt renders footnotes too small.
**Why it happens:** Single DPI per page cannot serve both sizes optimally.
**How to avoid:** Two-pass: render page at body-text DPI, then re-render footnote/margin regions at their own optimal DPI. Region detection from Phase 9 provides bounding boxes.
**Warning signs:** Large gap between median and min font sizes (ratio > 1.5x).

### Pitfall 3: Memory Explosion from High-DPI Full Pages

**What goes wrong:** Rendering full pages at 600 DPI creates huge pixmaps (A4 at 600 DPI = ~35MB uncompressed).
**Why it happens:** DPI ceiling too high, applied to full page instead of just the region.
**How to avoid:** Only use high DPI (>300) for clipped regions, never full pages. Cap full-page DPI at 300. Cap region DPI at 600.
**Warning signs:** Memory usage spikes, processing time >5s per page.

### Pitfall 4: Tesseract Accuracy Decreases at Very High DPI

**What goes wrong:** OCR accuracy drops when character pixel height exceeds ~40px.
**Why it happens:** Tesseract's LSTM model was trained on specific pixel height ranges. Too-large characters confuse the model.
**How to avoid:** Enforce DPI ceiling. For body text, target 20-33px character height. Never exceed 40px.
**Warning signs:** OCR confidence drops despite higher DPI.

### Pitfall 5: ProcessPoolExecutor with PyMuPDF Document Objects

**What goes wrong:** Passing `fitz.Document` or `fitz.Page` objects to worker processes fails.
**Why it happens:** PyMuPDF objects are not picklable (they contain C pointers).
**How to avoid:** Pass `pdf_path` (string/Path) to workers. Each worker opens its own document instance. This is the pattern used by `_detect_xmarks_single_page()`.
**Warning signs:** `PicklingError` or segfaults in worker processes.

### Pitfall 6: DPI Quantization Breaks Coordinate Mapping

**What goes wrong:** Region bounding boxes from text analysis don't map correctly to rendered pixmap coordinates.
**Why it happens:** Bounding boxes are in PDF points (72 DPI space). Pixmap is in pixel space at rendered DPI.
**How to avoid:** Use PyMuPDF's `page.rect.torect(pix.irect)` for coordinate mapping, or manually scale: `pixel_coord = pdf_coord * (dpi / 72)`.
**Warning signs:** OCR regions are offset or clipped incorrectly.

## Code Examples

### Computing DPI for Common Book Font Sizes

```python
# Typical font sizes in academic/scholarly books and their optimal DPIs:
#
# Font Size (pt) | Optimal DPI | Pixel Height @ DPI | Use Case
# 12.0           | 150         | 25.0 px            | Large body text
# 10.0           | 200         | 27.8 px            | Standard body text
# 9.0            | 200         | 25.0 px            | Compact body text
# 8.0            | 250         | 27.8 px            | Small body / notes
# 7.0            | 300         | 29.2 px            | Footnotes
# 6.0            | 350         | 29.2 px            | Fine print
# 5.0            | 400         | 27.8 px            | Micro text / marginalia
#
# Key observations:
# - Standard 10-12pt text only needs 150-200 DPI (50% savings vs fixed 300)
# - Footnotes (7pt) need approximately current 300 DPI
# - Only text below 6pt needs DPI above 300
```

### Integration Point: Modifying run_ocr_on_pdf

```python
# Current code (lib/rag/ocr/recovery.py line 279):
#   pix = page.get_pixmap(dpi=300)
#
# After Phase 10, this becomes:
#   dpi_decision = page_dpi_map.get(i, DPIDecision(dpi=300, ...))
#   pix = page.get_pixmap(dpi=dpi_decision.dpi)
#
# Similarly in lib/rag/quality/ocr_stage.py line 116:
#   pix = page.get_pixmap(dpi=300)
# Becomes:
#   pix = page.get_pixmap(dpi=dpi_decision.dpi)
```

### Integration Point: Orchestrator PDF Pipeline

```python
# In lib/rag/orchestrator_pdf.py, after document open and before page processing:
#
# 1. Analyze all pages for font sizes (fast, no rendering)
# 2. Compute per-page DPI decisions
# 3. Identify regions needing higher DPI
# 4. Pass DPI map to OCR functions
#
# This slots in after quality detection (line ~270) and before
# the page processing loop (line ~370).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 300 DPI for all pages | Adaptive DPI based on content | This phase | 30-50% less rendering time for text-heavy docs; better accuracy for fine print |
| Full-page OCR only | Region-specific OCR at different DPIs | This phase | Footnotes/margins get optimal resolution independently |
| No DPI metadata | Per-page DPI in output metadata | This phase | Transparency for debugging and quality assessment |

**Deprecated/outdated:**
- Fixed `dpi=300` hardcoding in `recovery.py` and `ocr_stage.py` -- replaced by adaptive pipeline

## Open Questions

1. **Scanned PDF text size estimation**
   - What we know: Scanned PDFs have no text layer; font analysis returns nothing
   - What's unclear: Whether to attempt image-based text size estimation (e.g., connected component analysis) or just use fixed 300 DPI
   - Recommendation: Use fixed 300 DPI for scanned PDFs in Phase 10. Image-based estimation is a separate complexity. The quality detection pipeline already identifies scanned PDFs.

2. **Auto-retry at higher DPI on low OCR confidence**
   - What we know: Tesseract outputs per-page confidence. Low confidence might indicate wrong DPI.
   - What's unclear: Whether re-rendering at a different DPI actually helps vs. the text just being unrecoverable
   - Recommendation: Log low-confidence pages but don't auto-retry in Phase 10. Collect data first, then decide if retry logic is worth the complexity.

3. **Phase 9 bounding box availability**
   - What we know: Phase 9 margin detection provides zone classifications and bounding boxes
   - What's unclear: Whether Phase 9 will be complete before Phase 10 implementation starts (they're independent)
   - Recommendation: Design region re-rendering to accept any bounding box source. Use footnote detection bboxes as primary (already complete), add margin bboxes when Phase 9 lands.

## Sources

### Primary (HIGH confidence)
- PyMuPDF Context7 `/pymupdf/pymupdf` - get_pixmap with dpi and clip parameters, coordinate mapping
- [Tesseract ImproveQuality docs](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) - DPI and character size recommendations
- Existing codebase: `lib/rag/ocr/recovery.py`, `lib/rag/detection/footnote_core.py`, `lib/rag/xmark/detection.py`

### Secondary (MEDIUM confidence)
- [Tesseract OCR mailing list discussion](https://groups.google.com/g/tesseract-ocr/c/Wdh_JJwnw94/m/24JHDYQbBQAJ) - Optimal capital letter height in pixels, x-height 20-30px
- [Tesseract GitHub issue #1846](https://github.com/tesseract-ocr/tesseract/issues/1846) - DPI vs pixel height distinction
- [PyMuPDF discussions](https://github.com/pymupdf/PyMuPDF/discussions/3852) - Default DPI behavior

### Tertiary (LOW confidence)
- [OCR quality research](https://aicha-fatrah.medium.com/improve-the-quality-of-your-ocr-information-extraction-ebc93d905ac4) - General OCR preprocessing tips
- DeepSeek OCR adaptive resolution modes - Different architectural approach (VLM-based, not applicable to Tesseract pipeline)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, APIs verified via Context7
- Architecture: HIGH - Two-pass pattern is straightforward; all building blocks exist in codebase
- DPI formula: HIGH - Math is simple (font_pt * dpi / 72 = pixel_height); Tesseract range well-documented
- Pitfalls: HIGH - Based on actual codebase patterns and known PyMuPDF/Tesseract behavior
- Parallel processing: HIGH - Exact pattern exists in xmark detection code

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (stable domain, unlikely to change)
