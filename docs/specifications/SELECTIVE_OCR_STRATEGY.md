# Selective OCR Strategy - Smart Per-Page Recovery

**Date**: 2025-10-18
**Context**: Quality pipeline Stage 3 implementation
**Problem**: Current OCR strategy re-processes ENTIRE PDFs, even if only a few pages corrupted

---

## Current OCR Strategy (Wasteful)

### Whole-Document Approach

```python
# Current (lib/rag_processing.py):
quality_assessment = assess_pdf_ocr_quality(file_path)  # Sample 10 pages

if quality_assessment["recommendation"] in ["redo_ocr", "force_ocr"]:
    ocr_pdf = redo_ocr_with_tesseract(file_path)  # RE-OCR ENTIRE PDF
    file_path = ocr_pdf  # Use OCR'd version for ALL pages
```

**Problems**:
- 500-page book with 5 corrupted pages → OCRs all 500 pages
- Cost: Minutes of processing time
- Wasteful: 495 pages didn't need OCR
- Overhead: ~300ms per page × 500 = 150 seconds wasted

**Example**:
```
Page 1: Clean → OCR'd (unnecessary)
Page 2: Clean → OCR'd (unnecessary)
...
Page 48: Garbled → OCR'd (necessary) ✅
Page 49: Clean → OCR'd (unnecessary)
...
Page 500: Clean → OCR'd (unnecessary)

Waste: 499/500 pages OCR'd unnecessarily
```

---

## Proposed Strategy: Selective Per-Page OCR

### Integration with Quality Pipeline

**The quality pipeline ALREADY identifies which pages need OCR**:

```
FOR EACH PAGE:
  Stage 1: Garbled Detection
    ↓
  Identifies garbled regions
    ↓
  Stage 2: X-mark Detection
    ↓
  Flags sous-rature (PRESERVE, don't OCR!)
    ↓
  Stage 3: Decide if page needs OCR
    ├─ Has garbled regions WITHOUT X-marks → Candidate for OCR
    ├─ >30% of page garbled → OCR this page
    └─ <30% garbled → Keep original, flag quality issues
```

### Decision Criteria Per Page

```python
def should_ocr_page(page_regions: List[PageRegion], threshold: float = 0.3) -> dict:
    """
    Determine if a page needs OCR based on quality pipeline results.

    Args:
        page_regions: All PageRegion objects from this page (after Stages 1-2)
        threshold: Fraction of page that must be garbled to trigger OCR (default: 30%)

    Returns:
        {
            'needs_ocr': bool,
            'reason': str,
            'garbled_ratio': float,
            'garbled_regions': List[PageRegion]
        }
    """
    total_regions = len(page_regions)
    if total_regions == 0:
        return {'needs_ocr': False, 'reason': 'No regions', 'garbled_ratio': 0.0}

    # Identify garbled regions (excluding sous-rature)
    garbled_regions = [
        r for r in page_regions
        if r.is_garbled() and not r.is_strikethrough()
    ]

    garbled_ratio = len(garbled_regions) / total_regions

    # Decision logic
    if len(garbled_regions) == 0:
        return {
            'needs_ocr': False,
            'reason': 'No garbled regions',
            'garbled_ratio': 0.0,
            'garbled_regions': []
        }

    if garbled_ratio >= threshold:
        return {
            'needs_ocr': True,
            'reason': f'{garbled_ratio:.0%} of page garbled (threshold: {threshold:.0%})',
            'garbled_ratio': garbled_ratio,
            'garbled_regions': garbled_regions
        }

    # Some garbled, but below threshold → flag but don't OCR
    return {
        'needs_ocr': False,
        'reason': f'Only {garbled_ratio:.0%} garbled (below {threshold:.0%} threshold)',
        'garbled_ratio': garbled_ratio,
        'garbled_regions': garbled_regions
    }
```

### Example Decisions

| Scenario | Garbled Regions | Total Regions | Ratio | Decision | Rationale |
|----------|----------------|---------------|-------|----------|-----------|
| Clean page | 0 | 10 | 0% | Keep original | No issues |
| Localized corruption | 2 | 10 | 20% | Keep + flag | Below threshold, mostly clean |
| Significant corruption | 5 | 10 | 50% | **OCR page** | Above 30% threshold |
| Whole page corrupted | 10 | 10 | 100% | **OCR page** | Completely garbled |
| Sous-rature (X-marks) | 2 (flagged sous-rature) | 10 | 0%* | Keep original | Intentional, exclude from ratio |

*X-marked regions excluded from garbled ratio calculation

---

## Implementation: Two-Pass Architecture

### Pass 1: Quality Analysis (Current - Works Well)

```python
# First pass: Identify pages needing OCR
pages_needing_ocr = []

for page_num, page in enumerate(doc):
    # Process page with quality pipeline (Stages 1-2)
    page_regions = process_page_with_quality_pipeline(page)

    # Decide if page needs OCR
    ocr_decision = should_ocr_page(page_regions, threshold=0.3)

    if ocr_decision['needs_ocr']:
        pages_needing_ocr.append(page_num)
        logging.info(f"Page {page_num}: Flagged for OCR ({ocr_decision['reason']})")
```

### Pass 2: Selective OCR

**Option A: Sequential Selective OCR**
```python
# OCR only flagged pages
for page_num in pages_needing_ocr:
    ocr_page_text = run_ocr_on_single_page(pdf_path, page_num)
    replace_page_regions(page_num, ocr_page_text)
```

**Option B: Parallel Selective OCR** (FASTEST)
```python
# OCR flagged pages in parallel
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(run_ocr_on_single_page, pdf_path, p): p
        for p in pages_needing_ocr
    }

    for future in as_completed(futures):
        page_num = futures[future]
        ocr_text = future.result()
        replace_page_regions(page_num, ocr_text)
```

**Performance Comparison** (500-page book, 5 corrupted pages):

| Approach | Cost | Notes |
|----------|------|-------|
| **Current (whole-PDF)** | 300ms × 500 = 150s | OCRs all pages |
| **Sequential selective** | 300ms × 5 = 1.5s | Only corrupted pages |
| **Parallel selective (4 workers)** | 300ms × 5 / 4 = **0.375s** | **400× speedup!** |

---

## Integration with Quality Pipeline

### Stage 3 Implementation (Complete)

**Current Stage 3** (placeholder):
```python
def _stage_3_ocr_recovery(...):
    # TODO: Implement selective OCR recovery
    page_region.quality_flags.add('recovery_needed')
```

**Proposed Stage 3** (functional):
```python
def _stage_3_ocr_recovery(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig,
    ocr_cache: dict = None  # NEW: Page-level OCR cache
) -> PageRegion:
    """
    Stage 3: Selective OCR recovery for corrupted regions.

    Uses page-level OCR cache (populated in Pass 1) to avoid redundant OCR.
    """
    # Only recover if garbled AND no X-marks
    if not page_region.is_garbled() or page_region.is_strikethrough():
        return page_region

    # Check confidence threshold
    if page_region.quality_score > (1.0 - config.recovery_threshold):
        page_region.quality_flags.add('low_confidence')
        return page_region

    # Check if this page was OCR'd (from cache)
    if ocr_cache and page_num in ocr_cache:
        # Use OCR'd text
        ocr_text = ocr_cache[page_num]

        # Replace region text with OCR'd text
        # (Need to map region bbox to OCR'd text - complex)
        page_region.quality_flags.add('recovered_from_cache')
        page_region.quality_score = 0.8  # Improved quality

        logging.info(f"Page {page_num}: Using cached OCR recovery")
    else:
        # Flag as needing OCR (will be collected for batch OCR)
        page_region.quality_flags.add('recovery_needed')

    return page_region
```

---

## Recommended Architecture: Two-Pass with Parallel OCR

### Pass 1: Identify Pages Needing OCR

```python
def process_pdf(file_path: Path, ...) -> str:
    doc = fitz.open(file_path)

    # Phase 1: Identify corrupted pages
    pages_needing_ocr = set()
    page_quality_map = {}  # Store quality pipeline results

    for page_num, page in enumerate(doc):
        # Extract regions with quality pipeline (Stages 1-2)
        regions = extract_page_regions_with_quality(page, ...)

        # Aggregate page-level quality
        garbled_count = sum(1 for r in regions if r.is_garbled() and not r.is_strikethrough())
        garbled_ratio = garbled_count / len(regions) if regions else 0.0

        page_quality_map[page_num] = {
            'regions': regions,
            'garbled_ratio': garbled_ratio
        }

        # Decision: OCR if >30% of page is garbled (excluding sous-rature)
        if garbled_ratio >= 0.3:
            pages_needing_ocr.add(page_num)
            logging.info(f"Page {page_num}: {garbled_ratio:.0%} garbled, will OCR")

    logging.info(f"OCR decision: {len(pages_needing_ocr)}/{len(doc)} pages need recovery")
```

### Pass 2: Parallel Selective OCR

```python
    # Phase 2: OCR corrupted pages in parallel
    ocr_cache = {}

    if pages_needing_ocr and OCR_AVAILABLE:
        logging.info(f"Starting parallel OCR for {len(pages_needing_ocr)} pages...")

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(ocr_single_page, file_path, p): p
                for p in pages_needing_ocr
            }

            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    ocr_text = future.result()
                    ocr_cache[page_num] = ocr_text
                    logging.info(f"Page {page_num}: OCR complete")
                except Exception as e:
                    logging.error(f"Page {page_num}: OCR failed: {e}")
                    ocr_cache[page_num] = None

    # Phase 3: Generate output using original + OCR'd pages
    for page_num in range(len(doc)):
        if page_num in ocr_cache:
            # Use OCR'd version
            text = ocr_cache[page_num]
        else:
            # Use original extraction
            text = extract_page(doc[page_num])

        final_output.append(text)
```

---

## Per-Page OCR Function

```python
def ocr_single_page(pdf_path: Path, page_num: int, lang: str = 'eng') -> str:
    """
    OCR a single page using Tesseract.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        lang: Tesseract language (default: 'eng')

    Returns:
        OCR'd text for this page
    """
    import fitz
    from PIL import Image
    import pytesseract
    import io

    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Render page to image (300 DPI for good OCR quality)
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))

    # Run Tesseract
    ocr_text = pytesseract.image_to_string(img, lang=lang)

    doc.close()

    return ocr_text
```

---

## Performance Projections

### Scenario: 500-Page Book with 10 Corrupted Pages

| Strategy | Pages OCR'd | Time | Efficiency |
|----------|-------------|------|------------|
| **Current (whole-PDF)** | 500 | 150s | 1× (baseline) |
| **Sequential selective** | 10 | 3s | **50× faster** |
| **Parallel selective (4 workers)** | 10 | 0.75s | **200× faster** |

### Scenario: Heavily Corrupted (200/500 pages bad)

| Strategy | Pages OCR'd | Time | Efficiency |
|----------|-------------|------|------------|
| **Current** | 500 | 150s | 1× |
| **Sequential selective** | 200 | 60s | 2.5× faster |
| **Parallel selective (4 workers)** | 200 | 15s | **10× faster** |

**Even with 40% corruption, parallel selective is 10× faster!**

---

## Configuration

### Environment Variables

```bash
# OCR mode
RAG_OCR_MODE='selective'  # 'selective' | 'whole_document' | 'never'

# Selective OCR threshold (% of page that must be garbled)
RAG_OCR_PAGE_THRESHOLD=0.3  # 30% default

# Parallel OCR
RAG_PARALLEL_OCR=true
RAG_OCR_WORKERS=4

# OCR quality
RAG_OCR_DPI=300  # Higher = better quality, slower
RAG_OCR_LANGUAGE='eng'  # Tesseract language
```

### Strategy Profiles

```python
OCR_STRATEGIES = {
    'philosophy': {
        'mode': 'selective',
        'threshold': 0.5,  # Conservative (50% must be garbled)
        'priority': 'preservation'  # Prefer keeping original
    },
    'technical': {
        'mode': 'selective',
        'threshold': 0.2,  # Aggressive (20% triggers OCR)
        'priority': 'quality'  # Prefer recovery
    },
    'scan_heavy': {
        'mode': 'whole_document',  # If most pages scanned, OCR all
        'threshold': 0.1,
        'priority': 'quality'
    }
}
```

---

## Implementation Plan

### Week 1: Basic Selective OCR

**Deliverable**: Per-page OCR decision logic
```python
# Implement:
- should_ocr_page() function
- Aggregate quality flags per page
- OCR decision based on threshold
```

**Timeline**: 1-2 days
**Value**: Immediate 10-50× speedup on partially corrupted PDFs

### Week 2: Parallel OCR

**Deliverable**: Parallel page OCR
```python
# Implement:
- ocr_single_page() function
- ProcessPoolExecutor for parallel OCR
- ocr_cache for results
```

**Timeline**: 1 day
**Value**: Additional 4× speedup (with 4 workers)

### Week 3: Integration with Quality Pipeline

**Deliverable**: Complete Stage 3
```python
# Integrate:
- Stage 3 uses ocr_cache
- Replace garbled regions with OCR'd text
- Quality score improvement tracking
```

**Timeline**: 2-3 days
**Value**: Complete quality pipeline

---

## Decision Flow Diagram

```
document
  ↓
┌─────────────────────────────────────┐
│ Pass 1: Quality Analysis            │
│ (identify pages needing OCR)        │
└─────────┬───────────────────────────┘
          │
    FOR EACH PAGE:
          │
          ├─> Stage 1: Garbled detection
          │     ↓
          ├─> Stage 2: X-mark detection
          │     ↓
          └─> Aggregate: garbled_ratio
                ↓
          garbled_ratio >= 30%?
                │
       ┌────────┴────────┐
      YES               NO
       │                 │
       ▼                 ▼
  Add to            Keep original
  pages_needing_ocr  (flag quality issues)
       │
       │
┌──────┴───────────────────────────────┐
│ Pass 2: Parallel Selective OCR       │
│ (OCR only flagged pages)             │
└──────┬───────────────────────────────┘
       │
  ProcessPoolExecutor
  (4 workers)
       │
       ├─> Worker 1: OCR pages [0, 4, 8, ...]
       ├─> Worker 2: OCR pages [1, 5, 9, ...]
       ├─> Worker 3: OCR pages [2, 6, 10, ...]
       └─> Worker 4: OCR pages [3, 7, 11, ...]
       │
       ▼
  Collect results → ocr_cache
       │
       │
┌──────┴───────────────────────────────┐
│ Pass 3: Generate Final Output        │
│ (mix original + OCR'd pages)         │
└──────────────────────────────────────┘
  FOR EACH PAGE:
    if page in ocr_cache:
      use OCR'd text
    else:
      use original text
```

---

## Alternative: Region-Level OCR (More Complex)

### Per-Region OCR (Future Enhancement)

**Idea**: OCR specific bboxes within a page, not entire page

```python
def ocr_region(pdf_path: Path, page_num: int, bbox: Tuple) -> str:
    """OCR specific region within a page."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Clip to bbox
    clip_rect = fitz.Rect(bbox)
    pix = page.get_pixmap(dpi=300, clip=clip_rect)

    # OCR just this region
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    ocr_text = pytesseract.image_to_string(img)

    return ocr_text
```

**Benefits**:
- More precise (only corrupt regions)
- Preserves clean text on same page

**Challenges**:
- Complex bbox alignment
- Need to merge OCR'd regions back into page
- Text flow reconstruction
- More code complexity

**Recommendation**: Start with per-page (simpler, good enough). Add per-region later if needed.

---

## Memory and Resource Considerations

### OCR Cache Size

**500-page book**:
- Average page: 2000 chars
- Total cache: 500 × 2000 = 1MB
- **Negligible**: Very small memory footprint

### CPU Utilization

**Parallel OCR with 4 workers**:
- Utilizes multi-core CPUs efficiently
- Tesseract is CPU-bound (benefits from parallelization)
- Expected: 4× speedup with 4 workers

### Optimal Worker Count

```python
import os

# Auto-detect optimal workers
cpu_count = os.cpu_count() or 4
ocr_workers = min(
    cpu_count,  # Don't exceed CPU cores
    len(pages_needing_ocr),  # Don't spawn more workers than pages
    int(os.getenv('RAG_OCR_WORKERS', '4'))  # User override
)
```

---

## Testing Strategy

### Unit Tests

```python
def test_should_ocr_page_clean():
    """Test OCR decision on clean page."""
    regions = [clean_region1, clean_region2, clean_region3]
    decision = should_ocr_page(regions, threshold=0.3)
    assert decision['needs_ocr'] == False

def test_should_ocr_page_heavily_garbled():
    """Test OCR decision on heavily corrupted page."""
    regions = [garbled1, garbled2, clean1]  # 66% garbled
    decision = should_ocr_page(regions, threshold=0.3)
    assert decision['needs_ocr'] == True

def test_should_ocr_page_sous_rature():
    """Test OCR skips sous-rature pages."""
    regions = [garbled_with_xmarks, clean1, clean2]  # Has X-marks
    decision = should_ocr_page(regions, threshold=0.3)
    assert decision['needs_ocr'] == False  # X-marks excluded
```

### Integration Tests

```python
def test_selective_ocr_integration():
    """Test selective OCR on mixed-quality PDF."""
    # Create test PDF:
    # - Pages 1-5: Clean
    # - Page 6: Corrupted
    # - Pages 7-10: Clean

    result = process_pdf(test_pdf, ocr_mode='selective')

    # Verify: Only page 6 was OCR'd
    assert ocr_pages_processed == [6]
```

---

## Comparison with Current Approach

| Aspect | Current (Whole-PDF) | Proposed (Selective) |
|--------|-------------------|---------------------|
| **Granularity** | Document-level | Page-level |
| **Decision** | Sample 10 pages | Analyze ALL pages with quality pipeline |
| **OCR Scope** | All pages | Only corrupted pages (30%+ garbled) |
| **Performance** | 300ms × all pages | 300ms × corrupted pages only |
| **Parallelization** | No | Yes (4× speedup) |
| **Overhead** | High (OCRs clean pages) | Low (skips clean pages) |
| **Quality** | Good | Better (preserves clean pages as-is) |

**Speedup**: 10-400× depending on corruption ratio

---

## Migration Path

### Phase 1: Implement Per-Page Decision Logic (Week 1)
- Add should_ocr_page() function
- Aggregate quality flags per page
- Log which pages would be OCR'd (dry-run mode)

### Phase 2: Implement Sequential Selective OCR (Week 1)
- Add ocr_single_page() function
- OCR only flagged pages
- Validate with test PDFs

### Phase 3: Add Parallelization (Week 2)
- Add ProcessPoolExecutor
- Parallel OCR of flagged pages
- Benchmark performance improvement

### Phase 4: Complete Stage 3 Integration (Week 3)
- Replace placeholder Stage 3
- Use ocr_cache in pipeline
- Replace garbled text with OCR'd text

**Total Timeline**: 3 weeks for complete selective OCR with parallelization

---

## Configuration Examples

### Philosophy Corpus (Conservative)
```bash
export RAG_OCR_MODE='selective'
export RAG_OCR_PAGE_THRESHOLD=0.5  # 50% must be garbled
export RAG_QUALITY_STRATEGY='philosophy'
export RAG_PARALLEL_OCR=true
export RAG_OCR_WORKERS=4
```

### Scanned Technical Docs (Aggressive)
```bash
export RAG_OCR_MODE='selective'
export RAG_OCR_PAGE_THRESHOLD=0.2  # 20% triggers OCR
export RAG_QUALITY_STRATEGY='technical'
export RAG_PARALLEL_OCR=true
export RAG_OCR_WORKERS=8  # More workers for heavy lifting
```

### High-Quality Digital PDFs (Skip OCR)
```bash
export RAG_OCR_MODE='never'  # Never OCR
# Or let quality pipeline decide:
export RAG_OCR_MODE='selective'
export RAG_OCR_PAGE_THRESHOLD=0.8  # Only if >80% corrupted
```

---

## Summary: Answer to Your Question

### How do we decide whether to run OCR?

**Per-PAGE decision based on quality pipeline results**:

1. **Stage 1** flags garbled regions
2. **Stage 2** flags sous-rature (exclude from OCR candidates)
3. **Aggregate** garbled ratio per page
4. **If garbled_ratio ≥ 30%** → OCR that page
5. **Else** → keep original, flag quality issues

### Selectively? YES ✅

**Per-page selective OCR**:
- Only OCR pages with ≥30% garbled regions
- Skip clean pages entirely
- Preserve sous-rature pages (don't OCR)

### For certain pages? YES ✅

**Quality pipeline identifies WHICH pages**:
- Page 48: 60% garbled → OCR ✅
- Page 49: 10% garbled → Keep original (flag issues)
- Page 50: Clean → Keep original

### For the whole thing? ONLY IF NECESSARY

**Whole-PDF OCR only if**:
- >80% of pages need OCR (heavily scanned document)
- User sets RAG_OCR_MODE='whole_document'
- Conservative: Default to selective for efficiency

---

**Performance**: 10-400× faster than whole-PDF OCR

**Robustness**: Uses quality pipeline results, no fragile assumptions

**Timeline**: 3 weeks to implement complete selective parallel OCR
