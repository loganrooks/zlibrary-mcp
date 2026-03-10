---
phase: 04
plan: 04
subsystem: python-decomposition
tags: [refactoring, module-splitting, footnotes, quality-pipeline]
dependency-graph:
  requires: [04-01, 04-02]
  provides: [footnotes-under-700, pipeline-under-500]
  affects: [04-VERIFICATION]
tech-stack:
  added: []
  patterns: [re-export-facade, submodule-extraction]
key-files:
  created:
    - lib/rag/detection/footnote_markers.py
    - lib/rag/detection/footnote_core.py
    - lib/rag/quality/ocr_stage.py
  modified:
    - lib/rag/detection/footnotes.py
    - lib/rag/quality/pipeline.py
decisions:
  - footnotes.py split into markers (497 lines) + core (617 lines) + re-exporter (115 lines)
  - pipeline.py split into ocr_stage (341 lines) + pipeline (318 lines)
metrics:
  duration: 9min
  completed: 2026-02-01
---

# Phase 4 Plan 4: Gap Closure - Oversized Module Splitting

Split footnotes.py (1175 -> 115 lines) and pipeline.py (604 -> 318 lines) via submodule extraction with re-export facades.

## Results

| Module | Before | After | Target | Status |
|--------|--------|-------|--------|--------|
| footnotes.py | 1175 | 115 | <= 700 | PASS |
| pipeline.py | 604 | 318 | <= 500 | PASS |

## Task Summary

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Split footnotes.py into 3 files | 8a88521 | Created footnote_markers.py + footnote_core.py, slimmed footnotes.py to re-exporter |
| 2 | Extract OCR stage from pipeline.py | f868152 | Created ocr_stage.py, slimmed pipeline.py |

## Decisions Made

1. **footnote_markers.py** contains marker matching and definition finding (6 functions, 497 lines)
2. **footnote_core.py** contains detection loop, font analysis, classification (3 functions, 617 lines)
3. **ocr_stage.py** contains Stage 3 OCR recovery and word-finding helper (2 functions, 341 lines)
4. All original exports preserved via re-export in parent modules - zero import breakage

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- All original imports from `lib.rag.detection.footnotes` work unchanged
- All original imports from `lib.rag.quality.pipeline` work unchanged
- Zero test file modifications
- 696 Python tests pass (43 pre-existing failures unrelated to changes)
- 138 Node.js tests pass (1 pre-existing failure unrelated to changes)
