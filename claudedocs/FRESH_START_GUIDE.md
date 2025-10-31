# Fresh Start Guide: Fixing Production Failures

**Purpose**: Quick-start guide for resuming work with fresh context after checkpoint
**Date**: 2025-10-30
**Status**: 🔴 Critical bugs documented, ready for systematic fixing

---

## Quick Status

**Current State**:
- ✅ 180/180 tests passing
- ❌ 0/4 real PDFs working correctly
- ❌ 5 critical bugs preventing production deployment

**Goal**:
- Fix 5 bugs systematically
- Achieve production readiness
- Est: 2-4 weeks focused work

---

## Start Here

### Step 1: Load Context (15 min)
```bash
# Read these files in order:
1. claudedocs/CHECKPOINT_2025_10_30_PRODUCTION_FAILURES.md  (master checkpoint)
2. claudedocs/PRODUCTION_READINESS_REPORT.md  (detailed failures)
3. VALIDATION_SUMMARY.md  (quick reference)
4. This file (you're reading it!)
```

### Step 2: Understand Current State (15 min)
```bash
# Check git status
git status
git log --oneline -15

# Run validation to see failures firsthand
python3 multi_corpus_validation.py
```

### Step 3: Profile Performance (30 min)
```bash
# Find performance bottleneck
python3 -m cProfile -o profile.stats <script to run detection>
python3 -m pstats profile.stats
# Sort by cumulative time, identify hotspots
```

---

## The 5 Critical Bugs (Priority Order)

### 🔴 BUG-1: Corruption Recovery Not Functioning
**File**: lib/rag_processing.py
**Issue**: Integration broken, † marker not recovered
**Impact**: 50% false negative on Derrida
**First Step**: Add logging to see if apply_corruption_recovery() is called

### 🔴 BUG-2: Continuation Creates Duplicates
**File**: lib/footnote_continuation.py or lib/rag_processing.py
**Issue**: 1 footnote becomes 5 duplicates
**Impact**: 400% false positive on Kant 64-65
**First Step**: Log continuation detection events

### 🔴 BUG-3: Multi-Schema Detection Failure
**File**: lib/rag_processing.py
**Issue**: Only symbolic markers detected, numeric/alphabetic missing
**Impact**: 70% false negative on Kant 80-85
**First Step**: Log all marker detection by schema type

### 🔴 BUG-4: Deduplication Too Aggressive
**File**: lib/rag_processing.py lines 4151-4170
**Issue**: Multiple footnotes with same marker consolidated
**Impact**: 75% false negative on Heidegger
**First Step**: Review deduplication logic, add page/bbox awareness

### 🔴 BUG-5: Performance 6-10x Over Budget
**File**: Unknown (needs profiling)
**Issue**: 377-609ms per page (budget: 60ms)
**Impact**: Unusable on large documents
**First Step**: Run cProfile to find hotspots

---

## Recommended Fix Strategy

### Week 1: Bugs 1-2 (Integration Issues)
**Day 1-2**: BUG-1 (Corruption recovery)
- Add integration test showing bug
- Trace code path to find break
- Fix integration
- Validate on Derrida

**Day 3-4**: BUG-2 (Duplicates)
- Add E2E test showing duplicates
- Log continuation events
- Fix duplicate creation
- Validate on Kant 64-65

**Day 5**: Validate both fixes on all 4 corpora

### Week 2: Bugs 3-4 (Detection Logic)
**Day 1-2**: BUG-3 (Multi-schema)
- Add E2E test for each schema type
- Debug why numeric/alphabetic missing
- Fix schema detection
- Validate on Kant 80-85

**Day 3-4**: BUG-4 (Deduplication)
- Add page-aware or bbox-aware deduplication
- Test on Heidegger with repeated markers
- Validate no over-deduplication

**Day 5**: Validate on all corpora

### Week 3: Bug 5 + Optimization
**Day 1-2**: BUG-5 (Performance)
- Profile with cProfile
- Identify bottlenecks
- Optimize (cache, reduce calls, etc.)
- Target: <60ms per page

**Day 3-5**: Integration polish
- Add more E2E tests
- Test on additional corpora
- Final optimization pass

### Week 4: Final Validation & Deployment
**Day 1-2**: Multi-corpus validation
- All 4 corpora passing
- Test on 2-3 additional authors
- Expand corpus diversity

**Day 3-4**: Performance validation
- Load testing (100+ page documents)
- Memory profiling
- Stress testing

**Day 5**: Documentation and deployment
- Update docs
- Create PR
- Deploy to production

---

## Validation Commands

### Quick Validation (5 min)
```bash
# Run multi-corpus validation script
python3 multi_corpus_validation.py
```

### Full Test Suite (30 sec)
```bash
pytest __tests__/python/test_*footnote*.py \
       __tests__/python/test_note_classification.py \
       __tests__/python/test_superscript_detection.py \
       __tests__/python/test_ocr_quality.py -v
```

### Performance Check (2 min)
```bash
python3 -m cProfile -s cumulative \
  -c "from lib.rag_processing import process_pdf; process_pdf('test_files/kant_critique_pages_80_85.pdf')" \
  | head -30
```

---

## Success Criteria (All Must Pass)

- [ ] All 180 tests passing (100%)
- [ ] Derrida: 2/2 footnotes correct (0% FN, 0% FP)
- [ ] Kant 64-65: 1 multi-page footnote (no duplicates)
- [ ] Kant 80-85: ~20 footnotes all detected (all schemas)
- [ ] Heidegger: 4 footnotes all detected (page-aware dedup)
- [ ] Performance: <60ms per page on all corpora
- [ ] False positive rate: <5% globally
- [ ] False negative rate: <5% globally

**Do NOT ship without all criteria met.**

---

## Key Principles for Fresh Session

1. **One bug at a time** - Don't compound changes
2. **E2E test first** - TDD red → green → refactor
3. **Validate on all corpora** - After EVERY change
4. **Profile continuously** - Measure performance impact
5. **Question assumptions** - Don't carry forward bugs

---

## Quick Reference

**Validation Script**: `multi_corpus_validation.py`
**Ground Truth**: `test_files/ground_truth/*.json`
**Test PDFs**: `test_files/*.pdf` (4 corpora, 5 fixtures)
**Checkpoint Doc**: `claudedocs/CHECKPOINT_2025_10_30_PRODUCTION_FAILURES.md`
**Detailed Report**: `claudedocs/PRODUCTION_READINESS_REPORT.md`

**Estimated Fix Time**: 2-4 weeks
**Confidence**: Medium (bugs are fixable, but complex integration)

---

**Ready for fresh context session!**
