---
phase: 11
plan: 02
subsystem: testing
tags: [recall, regression, baseline, pdf, ground-truth]
depends_on: []
provides: [recall-baseline, recall-regression-test]
affects: [11-03, 11-04, 11-05, 11-06, 11-07]
tech_stack:
  added: []
  patterns: [parametrized-regression-testing, ground-truth-snapshot]
key_files:
  created:
    - test_files/ground_truth/body_text_baseline.json
    - test_files/ground_truth/baseline_texts/*.txt
    - __tests__/python/test_recall_baseline.py
    - scripts/generate_recall_baseline.py
  modified: []
decisions:
  - id: RECALL-STRUCTURAL-FILTER
    description: "Filter TOC/navigation structural lines from recall comparison (non-deterministic between runs)"
metrics:
  duration: ~25min
  completed: 2026-02-02
---

# Phase 11 Plan 02: Recall Baseline Snapshot Summary

**One-liner:** Frozen process_pdf() output for 17 test PDFs with SHA-256 hashes and line-by-line recall regression test

## What Was Done

### Task 1: Generate recall baseline snapshot
- Created `scripts/generate_recall_baseline.py` to snapshot process_pdf() output for all test PDFs
- Generated `test_files/ground_truth/body_text_baseline.json` covering 17 PDFs with char counts, line counts, SHA-256 hashes, and sample lines
- Saved full body text for each PDF in `test_files/ground_truth/baseline_texts/` for diff analysis

### Task 2: Create recall regression test
- Created `__tests__/python/test_recall_baseline.py` with two parametrized test functions:
  - `test_no_body_text_recall_loss`: line-by-line recall check ensuring no baseline lines are lost
  - `test_body_text_not_shorter`: 95% length threshold sanity check
- Added `normalize_line()` helper for whitespace-insensitive comparison
- Added `is_structural_line()` filter to exclude non-deterministic TOC/navigation lines

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Non-deterministic TOC lines caused false recall failures**
- **Found during:** Task 2 verification
- **Issue:** TOC markdown links (`* [Title](#anchor)`) vary between runs due to TOC detection non-determinism in large books (Derrida Grammatology, Heidegger Question of Being)
- **Fix:** Added `is_structural_line()` filter to exclude TOC/navigation structural lines from recall comparison. These are generated content, not body text.
- **Files modified:** `__tests__/python/test_recall_baseline.py`
- **Commit:** 6b02ed4

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| RECALL-STRUCTURAL-FILTER | Filter TOC/navigation lines from recall comparison | Non-deterministic between runs; not body text |

## Commits

| Hash | Message |
|------|---------|
| 2276499 | feat(11-02): generate recall baseline snapshot for all test PDFs |
| 6b02ed4 | feat(11-02): create recall regression test for body text baseline |
