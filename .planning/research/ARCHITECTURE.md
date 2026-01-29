# Architecture: Decomposing rag_processing.py Monolith

**Domain:** Python monolith decomposition
**Researched:** 2026-01-28
**Overall confidence:** HIGH (based on direct codebase analysis + established Python packaging patterns)

## Current State

`lib/rag_processing.py`: 4968 lines, 55 functions, 4 classes. Three complexity hotspots:
- `process_pdf` (59 branches) - main PDF orchestrator
- `_detect_footnotes_in_page` (40 branches) - footnote detection engine
- `_analyze_pdf_block` (29 branches) - block-level analysis

### Public API Surface

Functions imported by external code (tests + `python_bridge.py`):

| Function | Importers |
|----------|-----------|
| `process_pdf` | python_bridge, 8+ test files, scripts |
| `process_epub` | python_bridge, test_rag_processing |
| `process_txt` | python_bridge, test_run_rag_tests |
| `process_document` | python_bridge (main entry) |
| `save_processed_text` | python_bridge |
| `detect_pdf_quality` | test_rag_processing |
| `run_ocr_on_pdf` | test_rag_processing |
| `QualityPipelineConfig` | test_quality_pipeline_integration, scripts |
| `_detect_footnotes_in_page` | 6 test files |
| `_is_superscript` | test_superscript_detection |
| `_calculate_page_normal_font_size` | test_superscript_detection |
| `_analyze_pdf_block` | test_rag_processing, test_phase_2_integration |
| `_extract_publisher_from_front_matter` | test_publisher_extraction |
| `_is_ocr_corrupted` | test_ocr_quality |
| `_find_definition_for_marker` | test_rag_processing |
| `_extract_and_format_toc` | test_rag_processing, test_toc_hybrid |

## Recommended Architecture

### Target Structure

```
lib/
  rag_processing.py          # Facade (~200 lines) - re-exports public API
  rag/
    __init__.py              # Package init, re-exports everything
    orchestrator.py          # process_pdf, process_epub, process_txt, process_document, save_processed_text (~500 lines)
    processors/
      __init__.py
      pdf.py                 # _format_pdf_markdown, _apply_formatting_to_text, _find_first_content_page (~300 lines)
      epub.py                # _epub_node_to_markdown, _html_to_text (~150 lines)
      txt.py                 # process_txt internals (~50 lines)
    detection/
      __init__.py
      footnotes.py           # _detect_footnotes_in_page + all footnote helpers (~700 lines)
      headings.py            # _detect_headings_from_fonts, _analyze_font_distribution (~200 lines)
      toc.py                 # _extract_toc_from_pdf, _generate_markdown_toc_from_pdf, _extract_and_format_toc, _format_toc_lines_as_markdown (~250 lines)
      front_matter.py        # _identify_and_remove_front_matter, _extract_publisher_from_front_matter (~200 lines)
      page_numbers.py        # _extract_written_page_number, _detect_written_page_on_page, infer_written_page_numbers, roman numeral helpers (~200 lines)
    quality/
      __init__.py
      analysis.py            # detect_pdf_quality, _determine_pdf_quality_category, _analyze_pdf_block (~300 lines)
      pipeline.py            # QualityPipelineConfig, _apply_quality_pipeline, _stage_1/2/3 (~400 lines)
    ocr/
      __init__.py
      recovery.py            # assess_pdf_ocr_quality, redo_ocr_with_tesseract, run_ocr_on_pdf (~250 lines)
      spacing.py             # detect_letter_spacing_issue, correct_letter_spacing (~100 lines)
      corruption.py          # _is_ocr_corrupted (~80 lines)
    xmark/
      __init__.py
      detection.py           # _detect_xmarks_parallel, _detect_xmarks_single_page, _page_needs_xmark_detection_fast, _should_enable_xmark_detection_for_document (~200 lines)
    utils/
      __init__.py
      text.py                # _slugify, _extract_text_from_block, _merge_bboxes (~80 lines)
      cache.py               # _TEXTPAGE_CACHE, _get_cached_text_blocks, _clear_textpage_cache (~50 lines)
      header.py              # _generate_document_header (~60 lines)
      constants.py           # All module-level constants, SUPPORTED_FORMATS, thresholds (~50 lines)
      exceptions.py          # TesseractNotFoundError, FileSaveError, OCRDependencyError (~20 lines)
```

## Extraction Order

Order is driven by: (1) fewest internal dependencies first, (2) most imported by others last.

### Phase 1: Leaf modules (no internal dependencies)

**Step 1.1: `utils/constants.py` + `utils/exceptions.py`**
- Extract: all module-level constants, threshold values, SUPPORTED_FORMATS, exception classes
- Risk: LOW. Pure data, no logic.
- Dependencies: None
- Dependents: Everything

**Step 1.2: `utils/text.py` + `utils/cache.py`**
- Extract: `_slugify`, `_extract_text_from_block`, `_merge_bboxes`, `_TEXTPAGE_CACHE`, `_get_cached_text_blocks`, `_clear_textpage_cache`
- Risk: LOW. Simple utilities.
- Dependencies: constants only

**Step 1.3: `ocr/spacing.py` + `ocr/corruption.py`**
- Extract: `detect_letter_spacing_issue`, `correct_letter_spacing`, `_is_ocr_corrupted`
- Risk: LOW. Self-contained string processing.
- Dependencies: None (pure functions)

### Phase 2: Detection modules (depend on utils)

**Step 2.1: `detection/page_numbers.py`**
- Extract: roman numeral helpers, page number detection/inference
- Risk: LOW. Self-contained with clear boundaries.
- Dependencies: utils only

**Step 2.2: `detection/headings.py`**
- Extract: `_analyze_font_distribution`, `_detect_headings_from_fonts`
- Risk: LOW. Reads PDF pages, returns data.
- Dependencies: utils only

**Step 2.3: `detection/toc.py`**
- Extract: TOC extraction and formatting functions
- Risk: LOW-MEDIUM. Some coupling to page number detection.
- Dependencies: detection/page_numbers

**Step 2.4: `detection/front_matter.py`**
- Extract: front matter identification and publisher extraction
- Risk: LOW. Self-contained analysis.
- Dependencies: utils

**Step 2.5: `detection/footnotes.py`** (LARGEST single extraction ~700 lines)
- Extract: `_detect_footnotes_in_page` + all footnote helpers (`_starts_with_marker`, `_markers_are_equivalent`, `_find_definition_for_marker`, `_find_markerless_content`, `_calculate_page_normal_font_size`, `_is_superscript`, `_footnote_with_continuation_to_dict`, `_format_footnotes_markdown`)
- Risk: MEDIUM. Highest complexity. Many internal helper calls. Most-tested module.
- Dependencies: utils/cache, utils/text, ocr/corruption
- Mitigation: Extract as a single unit. Do NOT split footnote detection further yet.

### Phase 3: Quality and OCR (depend on detection)

**Step 3.1: `quality/analysis.py`**
- Extract: `detect_pdf_quality`, `_determine_pdf_quality_category`, `_analyze_pdf_block`
- Risk: MEDIUM. `_analyze_pdf_block` is high-complexity (29 branches).
- Dependencies: utils/constants

**Step 3.2: `quality/pipeline.py`**
- Extract: `QualityPipelineConfig`, `_apply_quality_pipeline`, stages 1-3
- Risk: MEDIUM. Stages reference OCR functions.
- Dependencies: quality/analysis, ocr/

**Step 3.3: `xmark/detection.py`**
- Extract: all xmark detection functions
- Risk: LOW-MEDIUM. Parallel processing, but self-contained.
- Dependencies: quality/analysis

**Step 3.4: `ocr/recovery.py`**
- Extract: `assess_pdf_ocr_quality`, `redo_ocr_with_tesseract`, `run_ocr_on_pdf`
- Risk: LOW. External tool wrappers.
- Dependencies: utils/exceptions, utils/constants

### Phase 4: Processors (depend on detection + quality)

**Step 4.1: `processors/epub.py` + `processors/txt.py`**
- Extract: EPUB and TXT processing
- Risk: LOW. Relatively independent from PDF pipeline.
- Dependencies: detection/front_matter, detection/toc, utils

**Step 4.2: `processors/pdf.py`**
- Extract: `_format_pdf_markdown`, `_apply_formatting_to_text`
- Risk: MEDIUM. Called by process_pdf orchestrator.
- Dependencies: detection/*, quality/*, ocr/*

### Phase 5: Orchestrator + Facade

**Step 5.1: `orchestrator.py`**
- What remains: `process_pdf`, `process_epub`, `process_txt`, `process_document`, `save_processed_text`
- These become thin orchestrators that call into extracted modules.
- Risk: MEDIUM. `process_pdf` is the highest complexity (59 branches). Refactor into smaller steps only after extraction stabilizes.

**Step 5.2: `rag_processing.py` becomes facade**
- Replace entire file body with re-exports from `lib/rag/`
- All existing imports (`from lib.rag_processing import X`) continue to work.

## Interface Contracts

### Pattern: Each module exports explicit public API via `__all__`

```python
# lib/rag/detection/footnotes.py
__all__ = [
    'detect_footnotes_in_page',
    'format_footnotes_markdown',
    'calculate_page_normal_font_size',
    'is_superscript',
]
```

### Pattern: Modules accept data, not module references

Functions should accept primitive data or PyMuPDF objects, never import other rag submodules at the function signature level. Cross-module dependencies go through the orchestrator.

```python
# GOOD: detection/footnotes.py accepts a fitz.Page
def detect_footnotes_in_page(page: 'fitz.Page', page_num: int) -> dict:
    ...

# BAD: detection/footnotes.py imports quality module
from lib.rag.quality.analysis import analyze_pdf_block  # creates circular risk
```

### Pattern: Shared types via utils

If multiple modules need the same type/dataclass, put it in `utils/types.py`. Currently there are no shared dataclasses, but `FootnoteWithContinuation` (if it exists as a class) would go there.

## Maintaining Public API During Transition

### The Facade Pattern (critical)

`lib/rag_processing.py` becomes a thin facade that re-exports everything:

```python
# lib/rag_processing.py (after full extraction)
"""
Backward-compatible facade. All logic lives in lib/rag/ subpackages.
"""
from lib.rag.orchestrator import process_pdf, process_epub, process_txt, process_document, save_processed_text
from lib.rag.quality.analysis import detect_pdf_quality
from lib.rag.quality.pipeline import QualityPipelineConfig
from lib.rag.ocr.recovery import run_ocr_on_pdf, assess_pdf_ocr_quality, redo_ocr_with_tesseract
from lib.rag.detection.footnotes import (
    _detect_footnotes_in_page,
    _calculate_page_normal_font_size,
    _is_superscript,
    _format_footnotes_markdown,
    _find_definition_for_marker,
    _footnote_with_continuation_to_dict,
)
from lib.rag.detection.toc import _extract_and_format_toc
from lib.rag.quality.analysis import _analyze_pdf_block
from lib.rag.detection.front_matter import _extract_publisher_from_front_matter
from lib.rag.ocr.corruption import _is_ocr_corrupted
from lib.rag.utils.exceptions import TesseractNotFoundError, FileSaveError, OCRDependencyError
from lib.rag.utils.constants import SUPPORTED_FORMATS, PROCESSED_OUTPUT_DIR
# ... all other publicly imported names
```

This means **zero changes to any test file or python_bridge.py** during extraction. Tests continue importing from `lib.rag_processing` and it works.

### Incremental Migration

Each extraction step:
1. Create new module file with extracted functions
2. Replace functions in `rag_processing.py` with imports from new module
3. Run ALL tests: `uv run pytest && npm test`
4. Commit

At no point does any external import break.

## Testing Strategy During Decomposition

### Rule 1: Never change tests during extraction

Tests validate behavior. Changing tests AND code simultaneously removes the safety net. Extraction is pure refactoring -- tests must pass without modification.

### Rule 2: Run full suite after each extraction step

```bash
uv run pytest  # All Python tests
npm test        # All Jest tests (includes python_bridge integration)
```

### Rule 3: One module per commit

Each extraction step = one commit. If something breaks, `git revert` is trivial.

### Rule 4: Add module-level tests after extraction stabilizes

Once all extractions are complete and the facade is in place, add targeted tests for each new module to verify imports work directly (not just through the facade). This is Phase 6, after the extraction is done.

### Test files that import private functions (highest risk)

These files import underscore-prefixed functions directly and are most sensitive to extraction:

| Test File | Imports |
|-----------|---------|
| test_footnote_validation.py | `_detect_footnotes_in_page` |
| test_ocr_quality.py | `_is_ocr_corrupted`, `_detect_footnotes_in_page` |
| test_inline_footnotes.py | `_detect_footnotes_in_page` |
| test_superscript_detection.py | `_is_superscript`, `_calculate_page_normal_font_size` |
| test_rag_processing.py | `_analyze_pdf_block`, `_find_definition_for_marker`, `_extract_and_format_toc` |
| test_publisher_extraction.py | `_extract_publisher_from_front_matter` |
| test_phase_2_integration.py | `_analyze_pdf_block` |
| test_toc_hybrid.py | `_extract_and_format_toc` and others |

All of these continue working because `rag_processing.py` re-exports everything.

## Risk Mitigation

| Step | Risk | Mitigation |
|------|------|------------|
| Constants extraction | Circular imports if constants import from other modules | Constants must be pure values, no imports from rag submodules |
| Footnote extraction | Largest single move (700 lines), many internal calls | Move as single unit, do not split further |
| Quality pipeline | References OCR functions | Extract OCR first (Phase 1.3), quality pipeline last in Phase 3 |
| process_pdf orchestrator | 59 branches, calls everything | Extract last. Reduce complexity only after all dependencies are extracted |
| Mock targets in tests | Tests mock `lib.rag_processing.X`; if X moves, mocks break | Facade re-exports mean the mock path `lib.rag_processing.X` still resolves correctly |
| Import path in conftest/sys.path | Some tests add `lib/` to sys.path and import `rag_processing` directly | Facade handles this; `from rag_processing import X` still works |

## Anti-Patterns to Avoid

### Anti-Pattern 1: Extracting and refactoring simultaneously
**Why bad:** Two changes at once. If tests fail, you don't know which change caused it.
**Instead:** Extract verbatim first. Refactor (rename, simplify, reduce complexity) only after extraction is stable.

### Anti-Pattern 2: Splitting footnote detection into multiple files
**Why bad:** `_detect_footnotes_in_page` (40 branches) calls many helpers that share local state/context. Splitting creates excessive cross-file coupling.
**Instead:** Keep all footnote logic in one `detection/footnotes.py` file. Consider splitting later if needed.

### Anti-Pattern 3: Changing function signatures during extraction
**Why bad:** Breaks the facade contract. Tests fail.
**Instead:** Move functions with identical signatures. Parameter changes come in a separate PR.

### Anti-Pattern 4: Creating deep import chains
**Why bad:** `orchestrator -> processors/pdf -> detection/footnotes -> utils/cache -> utils/constants` = 4 levels deep. Slow imports, hard to reason about.
**Instead:** Orchestrator imports directly from each submodule. No submodule imports from another submodule unless strictly necessary.

## Sources

- Direct codebase analysis of `lib/rag_processing.py` (4968 lines)
- Import analysis across all test files and `python_bridge.py`
- Python packaging best practices: `__init__.py` re-exports, `__all__` declarations
- Confidence: HIGH -- all findings based on actual code inspection, no external sources needed
