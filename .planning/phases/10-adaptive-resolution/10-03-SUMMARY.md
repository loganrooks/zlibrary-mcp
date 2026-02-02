---
phase: 10
plan: 03
subsystem: rag-resolution
tags: [adaptive-dpi, ocr, pdf-pipeline, integration]
depends_on: ["10-01", "10-02"]
provides: ["adaptive-dpi-pipeline-integrated"]
affects: ["11-footnote-pipeline"]
tech_stack:
  added: []
  patterns: ["per-page-dpi-optimization", "optional-parameter-backward-compat"]
key_files:
  created:
    - __tests__/python/test_adaptive_integration.py
  modified:
    - lib/rag/ocr/recovery.py
    - lib/rag/quality/ocr_stage.py
    - lib/rag/orchestrator_pdf.py
decisions:
  - id: "RES-ADAPTIVE-DEFAULT"
    description: "Adaptive DPI is default behavior with no opt-in flag; scanned PDFs auto-fallback to 300"
  - id: "RES-OPTIONAL-PARAM"
    description: "page_dpi_map added as optional param with None default for backward compatibility"
metrics:
  duration: "~3min"
  completed: "2026-02-02"
  tests_added: 8
  tests_passing: 8
---

# Phase 10 Plan 03: Pipeline Integration Summary

**One-liner:** Adaptive DPI wired into PDF orchestrator, OCR recovery, and quality stage with per-page optimization and scanned-PDF fallback.

## What Was Done

### Task 1: OCR Recovery and Quality Stage (1e63aef)
- Added `page_dpi_map: dict = None` parameter to `run_ocr_on_pdf` in recovery.py
- Added `page_dpi_map: dict = None` parameter to `_stage_3_ocr_recovery` in ocr_stage.py
- Replaced hardcoded `dpi=300` with adaptive lookup from page_dpi_map (300 fallback)
- Added debug logging for per-page DPI usage
- All 17 existing OCR tests pass unchanged

### Task 2: Orchestrator Integration + Tests (55229e0)
- Imported `analyze_document_fonts` and `DPIDecision` in orchestrator_pdf.py
- Added adaptive DPI analysis block after quality detection, before OCR
- Scanned/image PDFs skip analysis and use fixed 300 DPI
- Text-layer PDFs get per-page font analysis with DPIDecision per page
- Low-confidence pages (confidence < 0.5) logged as warnings
- Pass page_dpi_map through to run_ocr_on_pdf
- Created 8 integration tests covering all scenarios

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| RES-ADAPTIVE-DEFAULT | Adaptive DPI is default (no opt-in) | Plan requirement: "PDF processing uses adaptive DPI by default" |
| RES-OPTIONAL-PARAM | page_dpi_map is optional with None default | Backward compatibility: existing callers unchanged |

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

- 8 new integration tests: all passing
- 17 existing OCR/recovery tests: all passing (no regressions)
- 31 pre-existing failures unrelated to this plan (ZeroDivisionError in xmark detection, performance budget tests, etc.)

## Next Phase Readiness

Phase 10 complete. All three plans delivered:
- 10-01: Models + analyzer (DPIDecision, PageAnalysis, analyze_document_fonts)
- 10-02: Renderer (render_page_adaptive, render_region)
- 10-03: Pipeline integration (orchestrator, recovery, quality stage)
