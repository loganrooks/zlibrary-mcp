# BUG-5 Performance Optimization Plan

**Current**: 11-28 seconds/page (188-471x over 60ms budget)
**Target**: <60ms/page
**Required Improvement**: 99.5% reduction

## Profiling Results - Bottleneck Identified

**Tesseract OCR Dominates** (90-95% of time):
- `_stage_3_ocr_recovery`: 29-64 seconds
- `pytesseract.image_to_string`: Called 13-70 times
- Per OCR call: ~2 seconds

**Other Operations** (5-10% of time):
- Footnote detection: <1 second
- Corruption recovery: <0.5 seconds
- Text extraction: <1 second

## Root Cause Analysis

**Why is OCR so dominant?**

1. **Sous-rature (strikethrough) detection** runs on every formatting block
2. **X-mark detection** triggers OCR recovery even when no X-marks found
3. **No caching**: Same page OCR'd multiple times per formatting block
4. **Runs unconditionally**: Even for footnote-only processing where we don't need text recovery

**Evidence**:
- Derrida: 26 OCR calls for 6 pages = 4.3 calls/page
- Kant 80-85: 70 OCR calls for 6 pages = 11.7 calls/page
- Each call: ~2 seconds

**Impact**: 4-12 OCR calls × 2s = 8-24 seconds per page (vs 60ms budget!)

## Optimization Phases

### PHASE 1: CONDITIONAL OCR (Target: 95% improvement, 1 day)

**Strategy**: Only run OCR when actually needed

**Quick Win #1**: Skip OCR for footnote-only mode
```python
# Current: Always runs quality pipeline
if detect_footnotes:
    page_markdown = _format_pdf_markdown(..., quality_config)

# Optimized: Skip quality pipeline for footnote-only
if detect_footnotes and not extract_full_text:
    quality_config = None  # Disable OCR pipeline
```
**Expected Impact**: 95% improvement (OCR is 95% of time)
**Risk**: Low (footnote detection doesn't need OCR text recovery)

**Quick Win #2**: Skip Stage 3 if no X-marks detected
```python
# Current: Stage 3 runs even if Stage 2 found 0 X-marks
if xmark_cache.get(page_num):  # Stage 2 results
    run_stage_3_ocr()

# Optimized: Early termination
xmarks_found = xmark_cache.get(page_num, {}).get('count', 0)
if xmarks_found == 0:
    skip_stage_3()  # No X-marks = no text to recover
```
**Expected Impact**: Eliminates 50%+ of OCR calls
**Risk**: Very low (confirmed by Stage 2)

**Quick Win #3**: Cache OCR results per page
```python
# Current: Same page OCR'd multiple times for different blocks
ocr_cache = {}  # per-page cache

if page_num in ocr_cache:
    use_cached_ocr()
else:
    ocr_result = run_tesseract()
    ocr_cache[page_num] = ocr_result
```
**Expected Impact**: Reduces redundant OCR calls by 50-70%
**Risk**: Low (page content doesn't change)

**Combined Phase 1 Impact**:
- Current: 11-28 seconds/page
- After: 0.3-1.4 seconds/page (95-98% improvement)
- Still over budget but much closer (5-23x vs 188-471x)

---

### PHASE 2: ALGORITHMIC OPTIMIZATION (Target: 80% of remaining, 2-3 days)

**After Phase 1**, remaining time will be in:
- Footnote detection: ~100-300ms/page
- Text extraction: ~50-100ms/page
- Formatting: ~50-100ms/page

**Optimization #4**: Lazy text extraction
```python
# Don't extract text until needed
# Cache PyMuPDF get_text() calls
```
**Expected Impact**: 20-30% of remaining time

**Optimization #5**: Optimize font size calculations
```python
# Pre-calculate once per page, don't recalculate per span
normal_font_size = _calculate_page_normal_font_size(blocks)
# Cache this value
```
**Expected Impact**: 10-15% of remaining time

**Optimization #6**: Regex compilation caching
```python
# Pre-compile all regex patterns once
COMPILED_PATTERNS = {
    'numeric': re.compile(r'\d+'),
    'letter': re.compile(r'[a-z]'),
    # etc.
}
```
**Expected Impact**: 5-10% of remaining time

**Combined Phase 2 Impact**:
- After Phase 1: 0.3-1.4 seconds/page
- After Phase 2: 0.06-0.3 seconds/page (60-300ms)
- Budget compliance: 🎯 APPROACHING TARGET

---

### PHASE 3: FINE-TUNING (Target: <60ms/page, 1-2 days)

**Optimization #7**: Parallel page processing
```python
# Process multiple pages concurrently
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(process_page, page) for page in pages]
```
**Expected Impact**: 2-4x speedup on multi-core systems
**Risk**: Medium (thread safety considerations)

**Optimization #8**: Early termination optimizations
```python
# Stop marker search after pattern established
# Skip continuation analysis if no incomplete footnotes
```
**Expected Impact**: 10-20% of remaining time

**Combined Phase 3 Impact**:
- After Phase 2: 60-300ms/page
- After Phase 3: 15-75ms/page
- Budget compliance: ✅ ACHIEVED (<60ms avg)

---

## Timeline Estimate

**Phase 1**: 1 day (conditional OCR)
- Disable quality pipeline for footnote-only mode
- Skip Stage 3 if no X-marks
- Add per-page OCR caching
- **Result**: 95%+ improvement

**Phase 2**: 2-3 days (algorithmic optimization)
- Lazy text extraction
- Font size caching
- Regex compilation caching
- **Result**: Additional 80% improvement

**Phase 3**: 1-2 days (fine-tuning)
- Parallel processing
- Early termination
- Final optimizations
- **Result**: Final push to <60ms/page

**Total**: 4-6 days to achieve <60ms/page target

**Confidence**: 90% (clear bottleneck, straightforward fixes)

## Success Criteria

**Must-Have**:
- Average <60ms/page across all corpora ✓
- All corpora <100ms/page ✓
- 123/124 tests still passing ✓
- All corpora still 100% detection ✓

**Should-Have**:
- Average <30ms/page (50% of budget)
- Fastest corpus <20ms/page
- 90%+ improvement from baseline

**Nice-to-Have**:
- Average <15ms/page (25% of budget)
- All corpora <30ms/page
- 99%+ improvement from baseline

## Next Actions

1. Implement Phase 1 Quick Win #1 (disable OCR for footnote-only)
2. Test on all corpora
3. Validate correctness maintained
4. Measure improvement
5. Repeat for Quick Wins #2 and #3

**Start with**: Conditional OCR disable (expected: 95% improvement)
