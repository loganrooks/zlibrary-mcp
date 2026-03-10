---
phase: 10-adaptive-resolution
plan: 01
subsystem: rag-resolution
tags: [dpi, font-analysis, tesseract, pymupdf, dataclasses]
dependency-graph:
  requires: []
  provides: [dpi-computation, font-analysis, resolution-models]
  affects: [10-02, 10-03]
tech-stack:
  added: []
  patterns: [tdd-red-green, process-pool-executor, dataclass-models]
key-files:
  created:
    - lib/rag/resolution/__init__.py
    - lib/rag/resolution/models.py
    - lib/rag/resolution/analyzer.py
    - __tests__/python/test_resolution_analyzer.py
  modified: []
decisions:
  - id: RES-DPI-FLOOR-72
    decision: "DPI floor is 72 (not quantized to 50) — preserves minimum rendering quality"
    context: "Quantization to 50 would round 72 down to 50, too low for any use"
metrics:
  duration: ~4min
  completed: 2026-02-02
---

# Phase 10 Plan 01: DPI Computation and Font Analysis Engine Summary

**TL;DR:** Adaptive DPI computation from font sizes with TDD — compute_optimal_dpi, analyze_page_fonts, analyze_document_fonts with 23 passing tests.

## What Was Built

### Models (`lib/rag/resolution/models.py`)
- `DPIDecision`: dpi, confidence, reason, font_size_pt, estimated_pixel_height
- `RegionDPI`: bbox + DPIDecision + region_type
- `PageAnalysis`: page_num, dominant/min/max sizes, has_small_text, page_dpi, regions

### Analyzer (`lib/rag/resolution/analyzer.py`)
- `compute_optimal_dpi(font_size_pt)`: Formula `28 * 72 / font_size`, quantized to 50s, clamped [72, 600]
- `analyze_page_fonts(page)`: Extracts spans from `get_text("dict")`, computes median dominant size
- `analyze_document_fonts(pdf_path, page_range)`: Sequential for <=10 pages, ProcessPoolExecutor for >10

### Key DPI Mappings
| Font Size | DPI | Pixel Height |
|-----------|-----|--------------|
| 12pt | 150 | 25.0 |
| 10pt | 200 | 27.8 |
| 7pt | 300 | 29.2 |
| 5pt | 400 | 27.8 |

## TDD Execution

- **RED:** 23 tests written, all failing (stubs only) — commit 74f964c
- **GREEN:** Implementation passes all 23 tests — commit c4484af
- **REFACTOR:** Not needed, code is clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test expectation for DPI floor**
- **Found during:** GREEN phase
- **Issue:** Test expected `dpi % 50 == 0` for 100pt font, but DPI_FLOOR=72 is not a multiple of 50
- **Fix:** Updated test to assert `dpi == 72` (floor clamp overrides quantization)
- **Commit:** c4484af

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 74f964c | test | Failing tests for DPI computation and font analysis |
| c4484af | feat | Implementation passing all 23 tests |

## Next Phase Readiness

Plan 10-02 (adaptive renderer) can proceed — it imports from `lib.rag.resolution.models` and `lib.rag.resolution.analyzer`.
