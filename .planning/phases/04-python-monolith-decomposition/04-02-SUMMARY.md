---
phase: 04
plan: 02
subsystem: python-rag
tags: [decomposition, refactoring, python, facade-pattern]
dependency-graph:
  requires: ["04-01"]
  provides: ["complete lib/rag/ package", "thin facade rag_processing.py"]
  affects: ["05-01", "05-02"]
tech-stack:
  added: []
  patterns: ["facade pattern", "lazy facade imports for mock compatibility"]
key-files:
  created:
    - lib/rag/quality/__init__.py
    - lib/rag/quality/analysis.py
    - lib/rag/quality/pipeline.py
    - lib/rag/ocr/recovery.py
    - lib/rag/xmark/__init__.py
    - lib/rag/xmark/detection.py
    - lib/rag/processors/__init__.py
    - lib/rag/processors/pdf.py
    - lib/rag/processors/epub.py
    - lib/rag/processors/txt.py
    - lib/rag/orchestrator.py
    - lib/rag/utils/deps.py
  modified:
    - lib/rag_processing.py
    - lib/rag/__init__.py
decisions:
  - id: "04-02-01"
    decision: "Facade-aware dependency access pattern for zero test modifications"
    rationale: "Submodules use _get_facade() to access optional deps (fitz, pytesseract, etc.) through lib.rag_processing, allowing tests that mock at the facade level to work unchanged"
  - id: "04-02-02"
    decision: "orchestrator.py at 817 lines (exceeds 500 target)"
    rationale: "process_pdf is ~470 lines of orchestration logic that cannot be meaningfully split without creating artificial abstractions. The function coordinates detection, quality, formatting, and output in a single coherent flow."
  - id: "04-02-03"
    decision: "quality/pipeline.py at 604 lines (exceeds 500 target)"
    rationale: "Contains 3 pipeline stages plus configuration class. Could be split into per-stage files but the stages are tightly coupled and read sequentially."
metrics:
  duration: "22 min"
  completed: "2026-02-01"
---

# Phase 4 Plan 2: Remaining Module Extraction and Facade Summary

**One-liner:** Extracted quality/xmark/processors/orchestrator from rag_processing.py; converted monolith to 201-line facade with facade-aware dependency access for zero test regressions.

## What Was Done

### Task 1+2: Complete Extraction and Facade Conversion

Extracted all remaining implementation from rag_processing.py (2669 lines) into domain modules:

| Module | Functions | Lines |
|--------|-----------|-------|
| quality/analysis.py | detect_pdf_quality, _analyze_pdf_block, _determine_pdf_quality_category | 369 |
| quality/pipeline.py | QualityPipelineConfig, _stage_1/2/3, _find_word_between_contexts, _apply_quality_pipeline | 604 |
| ocr/recovery.py | run_ocr_on_pdf, assess_pdf_ocr_quality, redo_ocr_with_tesseract | 310 |
| xmark/detection.py | _detect_xmarks_parallel, _detect_xmarks_single_page, _page_needs_xmark_detection_fast, _should_enable_xmark_detection_for_document | 225 |
| processors/pdf.py | _format_pdf_markdown | 261 |
| processors/epub.py | _epub_node_to_markdown, process_epub | 253 |
| processors/txt.py | process_txt | 63 |
| orchestrator.py | process_pdf, process_document, save_processed_text | 817 |
| **rag_processing.py (facade)** | imports + re-exports only | **201** |

### Key Technical Challenge: Test Mock Compatibility

Tests mock optional dependencies at `lib.rag_processing.*` (e.g., `lib.rag_processing.fitz.open`). After extraction, submodules have their own imports that aren't affected by facade-level mocks.

**Solution:** Facade-aware dependency access pattern. Submodules use `_get_facade()` to lazily import `lib.rag_processing` at call time and read optional deps from its namespace. This ensures test mocks propagate correctly with zero test file modifications.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Facade-aware dependency access for mock compatibility**
- **Found during:** Task 1
- **Issue:** Moving implementation to submodules broke 5 tests that mock at `lib.rag_processing.*`
- **Fix:** Added `_get_facade()` helper in submodules for lazy facade attribute access
- **Files modified:** quality/analysis.py, quality/pipeline.py, ocr/recovery.py, orchestrator.py, processors/epub.py

## Verification

- `uv run pytest __tests__/python/`: 695 passed, 14 failed (same 14 pre-existing failures)
- `npm test`: 138 passed, 1 failed (same pre-existing failure)
- `wc -l lib/rag_processing.py`: 201 lines (under 250 target)
- All public API functions importable from `lib.rag_processing`
- `python_bridge.py` works unchanged via `from lib import rag_processing`

## Complete lib/rag/ Package Structure

```
lib/rag/
  __init__.py
  orchestrator.py        (817 lines - main entry points)
  utils/
    __init__.py
    constants.py
    exceptions.py
    text.py
    cache.py
    header.py
    deps.py              (shared optional dependency imports)
  detection/
    __init__.py
    footnotes.py         (1176 lines - splitting deferred to 04-03)
    headings.py
    toc.py
    page_numbers.py
    front_matter.py
  quality/
    __init__.py
    analysis.py          (369 lines - PDF quality detection)
    pipeline.py          (604 lines - multi-stage quality pipeline)
  ocr/
    __init__.py
    spacing.py
    corruption.py
    recovery.py          (310 lines - OCR assessment and remediation)
  xmark/
    __init__.py
    detection.py         (225 lines - X-mark detection)
  processors/
    __init__.py
    pdf.py               (261 lines - PDF markdown formatting)
    epub.py              (253 lines - EPUB processing)
    txt.py               (63 lines - TXT processing)
```
