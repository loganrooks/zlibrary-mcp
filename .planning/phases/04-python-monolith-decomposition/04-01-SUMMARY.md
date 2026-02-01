---
phase: 04
plan: 01
subsystem: python-rag
tags: [decomposition, python, refactoring, module-extraction]
dependency-graph:
  requires: []
  provides: [lib-rag-package, utils-modules, detection-modules, ocr-modules]
  affects: [04-02, 04-03]
tech-stack:
  added: []
  patterns: [module-extraction, facade-re-export, verbatim-copy]
key-files:
  created:
    - lib/rag/__init__.py
    - lib/rag/utils/__init__.py
    - lib/rag/utils/constants.py
    - lib/rag/utils/exceptions.py
    - lib/rag/utils/text.py
    - lib/rag/utils/cache.py
    - lib/rag/utils/header.py
    - lib/rag/detection/__init__.py
    - lib/rag/detection/footnotes.py
    - lib/rag/detection/headings.py
    - lib/rag/detection/toc.py
    - lib/rag/detection/front_matter.py
    - lib/rag/detection/page_numbers.py
    - lib/rag/ocr/__init__.py
    - lib/rag/ocr/spacing.py
    - lib/rag/ocr/corruption.py
  modified:
    - lib/rag_processing.py
decisions:
  - id: DEC-04-01-01
    decision: "_extract_publisher_from_front_matter placed in header.py (needed by _generate_document_header), with re-export from detection/front_matter.py"
  - id: DEC-04-01-02
    decision: "footnotes.py is 1176 lines (exceeds 700 target) — verbatim copy of all footnote functions; further splitting deferred to 04-03"
  - id: DEC-04-01-03
    decision: "fitz import added to headings.py (was implicit in monolith scope, caused test failures)"
metrics:
  duration: 14min
  completed: 2026-02-01
---

# Phase 4 Plan 1: Extract Leaf-Node Modules Summary

**One-liner:** Extracted 16 modules from 4968-line rag_processing.py into lib/rag/ package (utils/, detection/, ocr/) with zero test regressions.

## What Was Done

Decomposed the monolithic `lib/rag_processing.py` (4968 lines) into a proper package structure under `lib/rag/`. All functions were copied verbatim with no signature changes. The original module now imports and re-exports everything from the new modules, maintaining full backward compatibility.

### Module Structure Created

```
lib/rag/
  __init__.py
  utils/
    __init__.py
    constants.py    (63 lines) - SUPPORTED_FORMATS, thresholds, STRATEGY_CONFIGS
    exceptions.py   (35 lines) - TesseractNotFoundError, FileSaveError, OCRDependencyError
    text.py         (117 lines) - _slugify, _html_to_text, _apply_formatting_to_text
    cache.py        (57 lines) - _TEXTPAGE_CACHE, _get_cached_text_blocks, _clear_textpage_cache
    header.py       (236 lines) - document header, markdown TOC, publisher extraction
  detection/
    __init__.py
    footnotes.py    (1176 lines) - marker-driven footnote detection + formatting
    headings.py     (211 lines) - font distribution analysis, heading detection
    toc.py          (248 lines) - PDF ToC extraction, text-based ToC, front matter removal
    front_matter.py (15 lines) - re-export of _extract_publisher_from_front_matter
    page_numbers.py (223 lines) - page number detection, roman numeral conversion
  ocr/
    __init__.py
    spacing.py      (122 lines) - letter spacing detection and correction
    corruption.py   (87 lines) - OCR corruption artifact detection
```

rag_processing.py reduced from 4968 to 2669 lines (46% reduction).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing fitz import in headings.py**
- Found during: Task 2 verification
- Issue: `_analyze_font_distribution` and `_detect_headings_from_fonts` use `fitz.TEXTFLAGS_DICT` — was available in monolith scope but not in extracted module
- Fix: Added conditional `import fitz` to headings.py
- Commit: a7a519e

**2. [Rule 1 - Bug] Duplicate _is_ocr_corrupted in footnotes.py**
- Found during: Task 2 extraction
- Issue: Both footnotes.py and corruption.py contained the same function (extracted from same source)
- Fix: Removed duplicate from footnotes.py, added import from ocr/corruption.py
- Commit: a7a519e

## Decisions Made

1. **_extract_publisher_from_front_matter placement**: Put in `header.py` since `_generate_document_header` calls it directly. `detection/front_matter.py` re-exports it.
2. **footnotes.py exceeds 700 lines**: At 1176 lines, it's above the 700-line target. The footnote detection functions are tightly coupled (shared marker_patterns, mutual calls). Further splitting is planned for 04-03.
3. **Missing fitz import**: Added conditional fitz import to headings.py to fix test failures caused by scope change during extraction.

## Test Results

- Python tests: 695 passed, 14 failed (all pre-existing), 6 xfailed
- Node.js tests: 138 passed, 1 failed (pre-existing paths.test.js)
- Zero test file modifications
- All imports verified: facade re-exports + cross-module imports

## Next Phase Readiness

- lib/rag/ package structure ready for 04-02 (higher-level module extraction)
- No circular imports between modules
- All modules have __all__, logger, and docstrings
