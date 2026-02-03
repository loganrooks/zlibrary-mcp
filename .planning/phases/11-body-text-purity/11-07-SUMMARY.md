---
phase: 11
plan: 07
subsystem: testing
tags: [integration-tests, recall-regression, pipeline-verification]
depends_on:
  requires: ["11-02", "11-06"]
  provides: ["integration-test-suite", "recall-validation"]
  affects: ["12"]
tech-stack:
  added: []
  patterns: ["pytest-integration-markers", "xfail-for-conditional-features"]
key-files:
  created:
    - __tests__/python/test_pipeline_integration.py
  modified: []
decisions:
  - id: TEST-SMALLEST-PDF
    description: Used heidegger_pages_22-23 (smallest scholarly PDF) for integration tests
    rationale: Fast execution while still exercising full pipeline
  - id: XFAIL-REMOVED
    description: Removed xfail from front_matter_toc test since it passed
    rationale: Detection works on small test PDF, no need for conditional skip
metrics:
  duration: ~25min
  completed: 2026-02-03
---

# Phase 11 Plan 07: Pipeline Integration Tests & Recall Regression Summary

**One-liner:** 8 integration tests verifying multi-file output, confidence scores, footnote-margin dedup, and front matter stripping; 34/34 recall regression tests pass with zero body text loss.

## What Was Done

### Task 1: End-to-end integration tests
Created `__tests__/python/test_pipeline_integration.py` with 8 tests:

1. **test_scholarly_pdf_multi_file_output** — Processes PDF via `process_pdf_structured()`, writes to temp dir, verifies body.md + _meta.json
2. **test_confidence_scores_in_metadata** — Verifies confidence floats (0.0-1.0) present in all block classifications
3. **test_footnote_margin_no_duplication** — No text content appears in both footnotes and margin annotations
4. **test_front_matter_toc_stripped_from_body** — Front matter/TOC in metadata sidecar, not in body
5. **test_headings_preserved_in_body** — Headings formatted as markdown `#` prefixes
6. **test_page_numbers_stripped** — No standalone page numbers in body text
7. **test_output_sections_clearly_labeled** — Footnotes have `## Page N` headers, margins use `[margin:]` markers
8. **test_backward_compat_process_pdf** — Legacy `process_pdf()` string output overlaps with structured body

All 8 tests pass in ~3.3 seconds.

### Task 2: Recall regression validation
Ran full 34-test recall regression suite across all 17 test PDFs:
- `test_no_body_text_recall_loss`: 17/17 pass (line-level recall check)
- `test_body_text_not_shorter`: 17/17 pass (95% length threshold)
- Total time: ~20 minutes (dominated by large Derrida Of Grammatology PDF)

Zero recall loss detected. Phase 11 refactoring preserved all body text.

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| TEST-SMALLEST-PDF | Used heidegger_pages_22-23 for integration tests | Fastest execution while exercising full pipeline |
| XFAIL-REMOVED | Removed xfail from front matter test | Detection works correctly on test PDF |

## Verification

- Integration tests: 8/8 pass
- Recall regression: 34/34 pass
- Full test suite: Pre-existing failures unrelated to this plan (OCR mock issues, performance budgets)

## Next Phase Readiness

Phase 11 (Body Text Purity) is now complete. All 7 plans delivered:
- Unified detection pipeline with registry
- Compositor conflict resolution
- Writer with separated output streams
- Orchestrator integration
- Full integration test coverage and recall validation

Ready for Phase 12 (Anna's Archive).
