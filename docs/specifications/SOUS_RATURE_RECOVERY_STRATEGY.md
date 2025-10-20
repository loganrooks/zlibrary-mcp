# Sous-Rature Text Recovery - Philosophical Requirements

**Date**: 2025-10-18
**Critical User Insight**: "Wouldn't we still want to recover the text that is under erasure?"
**Answer**: YES! This is philosophically ESSENTIAL.

---

## The Philosophical Problem

### What is Sous-Rature (Under Erasure)?

**Derrida's technique**:
- Write a word (e.g., "Being")
- Cross it out with X-mark
- Leave BOTH visible
- The crossing-out IS the argument

**Example from "Of Grammatology"**:
```
Original text: "the sign is that ill-named"
Derrida writes: "the sign is that ill-named"
                        ↓
                     X-mark
Meaning: "is" is both said AND unsaid simultaneously
```

**Current extraction**:
```
"the sign )( that ill-named"
         ↑
    Corrupted, unreadable
```

**What we NEED**:
```
"the sign [SOUS-RATURE]is[/SOUS-RATURE] that ill-named"
```

Or in markdown:
```
"the sign ~~is~~ that ill-named"
```

**Preserving BOTH**:
1. The word: "is"
2. The deletion: strikethrough formatting
3. The intentionality: [SOUS-RATURE] marker

---

## Current Pipeline FLAW

### What We're Doing NOW (WRONG)

```python
# Stage 2: X-marks detected
if xmark_result.has_xmarks:
    page_region.quality_flags.add('sous_rature')
    return page_region  # STOP - don't proceed to Stage 3
```

**Problem**: We preserve the CORRUPTED text ")(" but lose the original word "is"!

### What We SHOULD Do (CORRECT)

```python
# Stage 2: X-marks detected
if xmark_result.has_xmarks:
    page_region.quality_flags.add('sous_rature')
    # DON'T stop! Proceed to Stage 3 for recovery
    # But mark that this is intentional, not corruption

# Stage 3: OCR recovery (MODIFIED)
if page_region.is_strikethrough():
    # This is sous-rature - OCR to recover underlying text
    original_text = ocr_region(bbox_with_xmark)
    page_region.quality_flags.add('recovered_sous_rature')
    # Replace ")(" with "is" and apply strikethrough formatting
    apply_strikethrough_to_text(original_text)
elif page_region.is_garbled():
    # This is corruption - OCR to recover
    recovered_text = ocr_region(bbox)
    page_region.quality_flags.add('recovered_corruption')
```

---

## Revised Stage 3: Dual-Purpose Recovery

### Stage 3 Must Handle TWO Scenarios

**Scenario A: Corruption Recovery** (existing logic)
```
Garbled text (no X-marks) → OCR → Replace with clean text
Input:  "!@#$%^&*()"
Output: "the transcendental unity"
Flag:   'recovered_corruption'
```

**Scenario B: Sous-Rature Recovery** (NEW logic)
```
X-marked text → OCR → Recover + apply strikethrough
Input:  ")("
OCR:    "is"
Output: "~~is~~" (markdown strikethrough)
Flag:   'recovered_sous_rature'
```

### Implementation

```python
def _stage_3_ocr_recovery(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig,
    ocr_cache: dict = None
) -> PageRegion:
    """
    Stage 3: OCR recovery - handles BOTH corruption AND sous-rature.

    Two recovery paths:
    1. Garbled (no X-marks) → Corruption recovery → Replace text
    2. Sous-rature (has X-marks) → Intentional deletion recovery → Preserve + format
    """

    # Path A: Sous-rature recovery (recover text UNDER X-marks)
    if page_region.is_strikethrough():
        # This is INTENTIONAL deletion - still recover the text!
        logging.info(f"Stage 3: Recovering sous-rature text on page {page_num}")

        try:
            # OCR the region to recover underlying text
            original_text = ocr_region_targeted(pdf_path, page_num, page_region.bbox)

            # Update spans with recovered text + strikethrough formatting
            page_region.spans = [
                TextSpan(
                    text=original_text,
                    formatting={'strikethrough', 'sous-erasure'}  # Both markers
                )
            ]

            page_region.quality_flags.add('recovered_sous_rature')
            page_region.quality_score = 1.0  # Perfect (philosophical content preserved correctly)

            logging.info(f"Stage 3: Sous-rature recovered: '{original_text}' (will be formatted as ~~{original_text}~~)")

        except Exception as e:
            logging.error(f"Stage 3: Sous-rature recovery failed: {e}")
            page_region.quality_flags.add('recovery_failed')

        return page_region

    # Path B: Corruption recovery (garbled text, no X-marks)
    elif page_region.is_garbled():
        # This is CORRUPTION - recover and replace
        logging.info(f"Stage 3: Recovering corrupted text on page {page_num}")

        # ... existing corruption recovery logic ...

        return page_region

    # Path C: Clean text, no issues
    else:
        return page_region
```

---

## Output Format for Sous-Rature

### Current (Wrong)
```markdown
the sign )( that ill-named
         ↑
    Unreadable corruption
```

### Proposed (Correct)

**Markdown output**:
```markdown
the sign ~~is~~ that ill-named
```

**LLM-optimized output**:
```markdown
the sign [SOUS-RATURE text="is" confidence="0.95"]~~is~~[/SOUS-RATURE] that ill-named
```

**Structured JSON**:
```json
{
  "text": "the sign is that ill-named",
  "spans": [
    {"text": "the sign ", "formatting": []},
    {
      "text": "is",
      "formatting": ["strikethrough", "sous-erasure"],
      "metadata": {
        "xmark_detected": true,
        "confidence": 0.95,
        "recovered_via_ocr": true
      }
    },
    {"text": " that ill-named", "formatting": []}
  ]
}
```

**Benefits**:
- ✅ Preserves BOTH the word and the deletion
- ✅ Philosophically accurate
- ✅ Readable (not corrupted)
- ✅ Searchable (can find "is" even though crossed out)
- ✅ LLM-friendly (explicit markers)

---

## Performance Analysis: "Margins of Philosophy"

### Document Characteristics

**Margins of Philosophy** (Derrida, 1972):
- Pages: ~330 pages
- Contains: Sous-rature, complex arguments
- User's copy: + underlining + marginal handwritten notes

### Processing Time Projection

**With Current Implementation** (parallel X-mark, caching):

```
Pass 1: X-mark Detection (parallel, 4 workers)
  330 pages / 4 workers × 5ms = 0.4125s (X-mark detection)

Pass 2: Text Extraction
  330 pages × ~10ms = 3.3s (PyMuPDF extraction)

Pass 3: Sous-Rature Recovery (if 10 pages have X-marks)
  10 pages × 300ms = 3s (OCR recovery)
  OR parallel (4 workers): 10 / 4 × 300ms = 0.75s

Total: 0.4s + 3.3s + 0.75s = ~4.5 seconds
```

**BUT**: Handwritten annotations complicate this!

---

## The Handwritten Annotations Problem

### Distinguishing X-marks from Annotations

**Problem**: Handwritten notes create line art
- Underlines: Horizontal lines
- Marginal notes: Various marks
- Reader annotations: Could include X's, checks, etc.

**Current X-mark detector**:
```
Detects: Diagonal line pairs crossing at ~90°
```

**Will it false-positive on annotations?**

**Underlines**: NO
- Horizontal lines (~0° or 180°)
- Filter: Only detect diagonals (45° ± 15°)
- Underlines filtered out ✅

**Marginal annotations**: MAYBE
- If annotations include X's or crosses
- If in margin, bbox won't overlap with text
- Spatial filtering can exclude margins

**Reader marks**: POSSIBLY
- Checks (✓) have diagonal components
- Circles, arrows might trigger false positives
- Need to validate with real annotated PDF

### Mitigation Strategies

**1. Spatial Filtering** (exclude margins)
```python
def is_in_body_text(bbox, page_width):
    """Check if bbox is in body text (not margin)."""
    x_center = (bbox[0] + bbox[2]) / 2

    # Margins: typically outer 15% of page
    left_margin = page_width * 0.15
    right_margin = page_width * 0.85

    return left_margin < x_center < right_margin
```

**2. Size Filtering** (X-marks over text are small)
```python
# Sous-rature X-marks: typically 10-30 pixels
# Reader annotations: typically larger (50+ pixels)
if xmark.width > 40 or xmark.height > 40:
    # Probably annotation, not sous-rature
    skip()
```

**3. Text Overlap Requirement**
```python
# X-mark must overlap with text bbox
# Marginal annotations don't overlap body text
if xmark.bbox overlaps with text_bbox:
    likely_sous_rature = True
```

---

## Revised Architecture: Sous-Rature Recovery

### Complete Flow

```
Stage 1: Statistical Garbled Detection
  ├─ Garbled → quality_flags={'high_symbols'}
  └─ Clean → quality_flags={}

Stage 2: X-mark Detection (ALWAYS)
  ├─ X-marks found → quality_flags.add('sous_rature')
  │                  Store X-mark bboxes
  │                  DON'T STOP! (proceed to Stage 3)
  └─ No X-marks → Continue

Stage 3a: Sous-Rature Text Recovery (if has X-marks)
  ├─ OCR regions under X-marks
  ├─ Recover original text
  ├─ Apply strikethrough formatting
  └─ quality_flags.add('recovered_sous_rature')

Stage 3b: Corruption Recovery (if garbled, no X-marks)
  ├─ OCR corrupted regions
  ├─ Replace garbled text
  └─ quality_flags.add('recovered_corruption')
```

### Implementation

```python
def _stage_3_ocr_recovery(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig,
    ocr_cache: dict = None,
    xmark_locations: list = None  # NEW: X-mark bboxes from Stage 2
) -> PageRegion:
    """
    Stage 3: OCR recovery - BOTH sous-rature AND corruption.

    Critical: Sous-rature needs recovery too (to preserve the crossed-out word)!
    """

    # Priority 1: Sous-rature recovery (even on clean text!)
    if page_region.is_strikethrough() and xmark_locations:
        logging.info(f"Stage 3: Recovering sous-rature text on page {page_num}")

        for xmark_bbox in xmark_locations:
            # OCR the specific region under the X-mark
            original_text = ocr_region_targeted(pdf_path, page_num, xmark_bbox)

            # Find corresponding span and update
            for span in page_region.spans:
                if bbox_overlap(span.bbox, xmark_bbox) > 0.5:  # 50% overlap
                    # Update span with recovered text + formatting
                    span.text = original_text
                    span.formatting.add('strikethrough')
                    span.formatting.add('sous-erasure')

                    page_region.quality_flags.add('recovered_sous_rature')
                    logging.info(f"Recovered sous-rature: '{original_text}'")

        return page_region

    # Priority 2: Corruption recovery (garbled, no X-marks)
    elif page_region.is_garbled():
        # ... existing corruption logic ...
        pass

    return page_region
```

---

## Performance Projection: "Margins of Philosophy"

### Assumptions

**Document**: ~330 pages
**Content**:
- Sous-rature: ~10 instances (1 every 33 pages)
- Underlining: ~100 instances (reader markup)
- Marginal notes: ~50 instances (handwritten)

### Processing Time Breakdown

**Pass 1: X-mark Detection** (parallel, 4 workers)
```
Total pages: 330
Detection per page: ~5ms
Parallel: 330 / 4 × 5ms = 0.4125s

Expected X-marks detected:
- Sous-rature: 10 instances (TRUE POSITIVES) ✅
- Underlines: 0 (filtered by angle) ✅
- Marginal notes: ~10-20 (FALSE POSITIVES?) ⚠️
- Reader marks: ~5-10 (FALSE POSITIVES?) ⚠️

Total detected: ~25-40 X-mark candidates
```

**Pass 2: Text Extraction** (PyMuPDF)
```
330 pages × 10ms = 3.3s
```

**Pass 3: Sous-Rature Recovery** (OCR under X-marks)
```
True sous-rature: 10 regions × 300ms = 3s
Sequential: 3s
Parallel (4 workers): 0.75s
```

**Pass 4: Output Generation**
```
330 pages × 2ms = 0.66s
```

**Total Time**:
- Sequential: 0.4s + 3.3s + 3s + 0.66s = **7.4 seconds** ✅
- Parallel OCR: 0.4s + 3.3s + 0.75s + 0.66s = **5.1 seconds** ✅

**Acceptable**: ~5-7 seconds for 330-page complex document

### False Positive Handling

**Problem**: Handwritten annotations detected as X-marks

**Mitigation**:
```python
def filter_xmark_candidates(candidates, page):
    """Filter out likely false positives."""
    filtered = []

    for xmark in candidates:
        # Filter 1: Must be small (sous-rature X-marks are ~20px)
        width = xmark.bbox[2] - xmark.bbox[0]
        height = xmark.bbox[3] - xmark.bbox[1]

        if width > 50 or height > 50:
            # Too large, probably annotation
            continue

        # Filter 2: Must overlap with text
        if not overlaps_with_text(xmark.bbox, page.get_text("dict")):
            # In margin or blank space, probably annotation
            continue

        # Filter 3: Confidence threshold
        if xmark.confidence < 0.6:
            # Low confidence, might be noise
            continue

        filtered.append(xmark)

    return filtered
```

**Expected false positives after filtering**: 0-5 per document (acceptable)

---

## Alternative: Conservative Approach

### If Performance Still Concerning

**Option**: Process first 50 pages, estimate time, ask user

```python
def process_pdf_with_estimation(file_path: Path, ...) -> str:
    doc = fitz.open(file_path)
    total_pages = len(doc)

    if total_pages > 100:
        # Process first 50 pages
        sample_start = time.time()
        sample_result = process_pages(doc, 0, 50)
        sample_time = time.time() - sample_start

        # Estimate total time
        estimated_total = sample_time * (total_pages / 50)

        logging.info(f"Processed 50/{total_pages} pages in {sample_time:.1f}s")
        logging.info(f"Estimated total time: {estimated_total:.1f}s ({estimated_total/60:.1f} minutes)")

        if estimated_total > 60:  # > 1 minute
            # Optionally: Ask user to continue or adjust settings
            logging.warning(f"Processing may take {estimated_total/60:.1f} minutes. "
                          "Consider disabling X-mark detection for faster processing.")

    # Continue with full processing
    return process_all_pages(doc)
```

---

## Realistic Performance Estimates

### Various Document Types

| Document | Pages | Sous-Rature | Annotations | Estimated Time | Notes |
|----------|-------|-------------|-------------|----------------|-------|
| **Clean philosophy** | 300 | 0 | 0 | ~3s | Text extraction only |
| **Margins of Philosophy** | 330 | 10 | 60 | **5-7s** | With parallel OCR |
| **Of Grammatology** | 400 | 30 | 0 | ~8s | More sous-rature instances |
| **Being and Time** | 600 | 5 | 0 | ~6s | Large but few X-marks |
| **Heavily annotated** | 300 | 10 | 200 | ~10-15s | Many false positive candidates |

**Worst case** (heavily annotated, 300 pages): ~15 seconds
**Typical** (Derrida with annotations): ~5-7 seconds

**Acceptable**: All under 15 seconds for complex 300-page documents

---

## Configuration for Different Scenarios

### Derrida with Annotations (Balanced)
```bash
export RAG_QUALITY_STRATEGY='philosophy'
export RAG_XMARK_DETECTION_MODE='auto'  # Will detect based on author
export RAG_PARALLEL_XMARK_DETECTION=true
export RAG_XMARK_WORKERS=4
export RAG_PARALLEL_OCR=true
export RAG_OCR_WORKERS=4
```

**Expected**: ~5-7 seconds for "Margins of Philosophy"

### Speed Priority (Skip Sous-Rature Recovery)
```bash
export RAG_QUALITY_STRATEGY='technical'
export RAG_XMARK_DETECTION_MODE='never'  # Skip X-mark detection entirely
```

**Expected**: ~3 seconds (just text extraction)

### Quality Priority (Full Recovery)
```bash
export RAG_QUALITY_STRATEGY='philosophy'
export RAG_XMARK_DETECTION_MODE='always'
export RAG_RECOVER_SOUS_RATURE=true  # NEW flag
export RAG_PARALLEL_XMARK_DETECTION=true
export RAG_PARALLEL_OCR=true
```

**Expected**: ~7-10 seconds (full recovery with maximum quality)

---

## Summary: Answers to Your Questions

### Q: "Wouldn't we still want to recover the text under erasure?"

**YES!** You're absolutely right. This is philosophically ESSENTIAL.

**Current flaw**: We preserve ")(" (corrupted)
**Correct approach**: OCR to recover "is" + apply strikethrough formatting
**Output**: "~~is~~" (shows both word and deletion)

**Implementation**: Modify Stage 3 to handle sous-rature recovery

---

### Q: "How long for 'Margins of Philosophy' with annotations?"

**Estimated**: ~5-7 seconds for 330 pages

**Breakdown**:
- X-mark detection (parallel): ~0.4s
- Text extraction: ~3.3s
- Sous-rature OCR (parallel): ~0.75s
- Output generation: ~0.7s
- **Total**: ~5.15 seconds

**With sequential OCR**: ~7.4 seconds

**Even with handwritten annotations**: <15 seconds worst case

**Acceptable**: Under 30 seconds for complex 300+ page documents ✅

---

## Implementation Timeline

### Week 1 (Remaining)
1. **Complete Stage 3**: Sous-rature recovery (2-3 hours)
2. **Test with annotations**: Validate false positive filtering (1 hour)

### Week 2
3. **Parallel OCR**: Implement ProcessPoolExecutor for OCR (1 day)
4. **Performance optimization**: Tune worker counts, caching (1 day)

**Result**: Production-ready selective recovery for both corruption AND sous-rature

---

**Key Insight**: Your questions revealed critical flaw in Stage 3 logic. We need to recover sous-rature text while preserving the intentionality marker!
