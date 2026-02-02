---
phase: 11-body-text-purity
plan: 03
subsystem: detection-pipeline
tags: [detectors, registry, adapters, pipeline]
dependency-graph:
  requires: ["11-01"]
  provides: ["6 registered detector adapters bridging existing detectors to pipeline contract"]
  affects: ["11-05", "11-06", "11-07"]
tech-stack:
  added: []
  patterns: ["decorator-based registry", "adapter pattern", "pipeline context passing"]
key-files:
  created: []
  modified:
    - lib/rag/detection/footnotes.py
    - lib/rag/detection/margins.py
    - lib/rag/detection/headings.py
    - lib/rag/detection/page_numbers.py
    - lib/rag/detection/toc.py
    - lib/rag/detection/front_matter.py
decisions:
  - id: "ADAPTER-ADDITIVE"
    decision: "All adapters added as new functions, zero modifications to existing detection logic"
  - id: "SENTINEL-BBOX"
    decision: "Document-level detectors use (0,0,0,0) bbox sentinel with bbox_available=False metadata"
  - id: "MARG-FOOTNOTE-DEDUP-RESOLVED"
    decision: "Footnote bboxes flow to margins via context['footnote_bboxes'], resolving MARG-FOOTNOTE-DEDUP-DEFERRED"
metrics:
  duration: ~3min
  completed: 2026-02-02
---

# Phase 11 Plan 03: Detector Registry Adapters Summary

**One-liner:** 6 existing detectors wrapped with @register_detector adapters converting ad-hoc returns to typed DetectionResult objects with priority ordering and context-based footnote-margin dedup.

## What Was Done

### Task 1: Page-Level Detectors (footnotes + margins)
- Added `detect_footnotes_pipeline` adapter (priority=10, scope=PAGE) to `footnotes.py`
- Added `detect_margins_pipeline` adapter (priority=20, scope=PAGE) to `margins.py`
- Footnotes store bboxes in `context["footnote_bboxes"]` for margin dedup
- Margins read `context["footnote_bboxes"]` as `excluded_bboxes` parameter
- Commit: `a89da86`

### Task 2: Document-Level Detectors (headings, page_numbers, toc, front_matter)
- Added `detect_page_numbers_pipeline` (priority=5, scope=DOCUMENT) - stores `context["page_number_map"]`
- Added `detect_toc_pipeline` (priority=15, scope=DOCUMENT) - stores `context["toc_map"]`
- Added `detect_front_matter_pipeline` (priority=25, scope=DOCUMENT) - stores `context["front_matter"]`
- Added `detect_headings_pipeline` (priority=30, scope=DOCUMENT) - stores `context["headings_map"]`
- Commit: `6e8cfce`

### Priority Ordering (verified)
| Priority | Detector | Scope |
|----------|----------|-------|
| 5 | page_numbers | DOCUMENT |
| 10 | footnotes | PAGE |
| 15 | toc | DOCUMENT |
| 20 | margins | PAGE |
| 25 | front_matter | DOCUMENT |
| 30 | headings | DOCUMENT |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing fitz imports to page_numbers.py and toc.py**
- **Found during:** Task 2 commit
- **Issue:** Pre-commit ruff check failed on `fitz.Page`/`fitz.Document` type annotations without fitz import
- **Fix:** Added `try: import fitz` blocks (matching pattern in headings.py)
- **Files modified:** page_numbers.py, toc.py

**2. [Rule 3 - Blocking] Fixed style violation in toc.py**
- **Found during:** Task 2 commit
- **Issue:** `if not stripped_line: continue` on one line (E701)
- **Fix:** Split to two lines
- **Files modified:** toc.py

## Decisions Made

1. **ADAPTER-ADDITIVE**: All adapters are purely additive new functions. Zero changes to existing detection logic or signatures.
2. **SENTINEL-BBOX**: Document-level detectors that lack bbox info use `(0,0,0,0)` sentinel with `bbox_available: False` in metadata.
3. **MARG-FOOTNOTE-DEDUP-RESOLVED**: The deferred margin-footnote dedup issue is now resolved via pipeline context passing.

## Verification

- All 6 detectors register correctly with expected priorities
- Priority ordering matches success criteria
- Existing pytest suite passes (only pre-existing Z-Library auth test fails)
- Footnote bboxes flow through context to margins

## Next Phase Readiness

All 6 detector adapters are ready for the pipeline orchestrator (11-05+) to invoke via `get_registered_detectors()`. Context keys populated:
- `footnote_bboxes` (page-level, per-page)
- `page_number_map` (document-level)
- `toc_map` (document-level)
- `front_matter` (document-level)
- `headings_map` (document-level)
