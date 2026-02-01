# Phase 4: Python Monolith Decomposition - Research

**Researched:** 2026-02-01
**Domain:** Python module refactoring and backward-compatible package decomposition
**Confidence:** HIGH

## Summary

Phase 4 decomposes the 4,968-line `lib/rag_processing.py` monolith into domain-focused modules under `lib/rag/`, while preserving 100% backward compatibility via a facade pattern. The standard approach is **incremental extraction with re-export facade** — each extraction creates a new module, replaces functions in the original file with imports, validates all tests pass unchanged, then commits. The facade ensures every existing import path (`from lib.rag_processing import X`) continues to work without test file modifications.

The key architectural decision is **dependency-driven extraction order**: utilities and constants first (zero dependencies), then detection modules, then quality/OCR, then processors, finally the orchestrator. This prevents circular imports and makes each step independently testable. The most critical technical challenge is preserving the Python bridge contract (`python_bridge.py` → `rag_processing.py` → Node.js) which is stringly-typed and will break silently if imports fail — mitigated by running integration tests after each extraction step.

**Primary recommendation:** Extract modules in 5 phases following dependency flow (utils → detection → quality/OCR → processors → orchestrator), maintain `rag_processing.py` as a thin re-export facade, validate with full test suite (`uv run pytest && npm test`) after each commit, use `__all__` exports in each module to explicitly declare public APIs, and follow Python logging convention (`logging.getLogger(__name__)`) for per-module loggers.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3.9+ | Current | Module system with type hints | Minimum version for this project |
| `__init__.py` re-exports | Built-in | Package API definition | Standard Python packaging pattern for facade creation |
| `__all__` declarations | Built-in | Explicit public API control | PEP 8 recommendation for modules, prevents wildcard import pollution |
| `logging.getLogger(__name__)` | Built-in | Per-module logging | Official Python logging best practice, creates hierarchical logger namespaces |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing module | Built-in | Type hints for public APIs | Add to 16 public API functions in facade for documentation |
| mypy | Latest | Static type checking | Optional but recommended for validation after type hints added |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Facade pattern | Direct rewrite with import path changes | Facade preserves backward compatibility; direct rewrite requires changing all 40+ test files and `python_bridge.py` |
| `__all__` declarations | Implicit exports (no `__all__`) | Explicit `__all__` documents intent and prevents accidental exports; implicit is easier but less maintainable |
| Incremental extraction | Big-bang rewrite | Incremental allows validating each step; big-bang increases risk of undetected breakage |

**Installation:**
```bash
# No new dependencies required
# Type checking (optional):
uv add --dev mypy
```

## Architecture Patterns

### Recommended Project Structure

```
lib/
  rag_processing.py          # Facade (~200 lines) - re-exports public API
  rag/
    __init__.py              # Package init, re-exports everything
    orchestrator.py          # process_pdf, process_epub, process_txt, process_document, save_processed_text
    processors/
      __init__.py
      pdf.py                 # PDF formatting functions
      epub.py                # EPUB processing
      txt.py                 # TXT processing
    detection/
      __init__.py
      footnotes.py           # Footnote detection engine (largest: ~700 lines)
      headings.py            # Heading detection
      toc.py                 # Table of contents extraction
      front_matter.py        # Front matter identification
      page_numbers.py        # Page number detection and inference
    quality/
      __init__.py
      analysis.py            # PDF quality analysis
      pipeline.py            # Quality pipeline orchestration
    ocr/
      __init__.py
      recovery.py            # OCR recovery functions
      spacing.py             # Letter spacing correction
      corruption.py          # OCR corruption detection
    xmark/
      __init__.py
      detection.py           # X-mark detection
    utils/
      __init__.py
      text.py                # Text utilities
      cache.py               # Caching utilities
      header.py              # Header generation
      constants.py           # All module constants
      exceptions.py          # Custom exceptions
```

### Pattern 1: Facade Re-Export Pattern

**What:** The original monolith file becomes a thin facade that imports and re-exports from the new package structure.

**When to use:** When decomposing a module that has many external dependents and changing import paths would break backward compatibility.

**Example:**
```python
# lib/rag_processing.py (after full extraction - becomes facade)
"""
RAG document processing - backward-compatible facade.
All implementation lives in lib/rag/ subpackages.
"""

# Public API - orchestration
from lib.rag.orchestrator import (
    process_pdf,
    process_epub,
    process_txt,
    process_document,
    save_processed_text,
)

# Public API - quality detection
from lib.rag.quality.analysis import detect_pdf_quality
from lib.rag.quality.pipeline import QualityPipelineConfig

# Public API - OCR
from lib.rag.ocr.recovery import (
    run_ocr_on_pdf,
    assess_pdf_ocr_quality,
    redo_ocr_with_tesseract,
)
from lib.rag.ocr.spacing import (
    detect_letter_spacing_issue,
    correct_letter_spacing,
)

# Semi-private API (imported by tests)
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

# Constants and exceptions
from lib.rag.utils.exceptions import (
    TesseractNotFoundError,
    FileSaveError,
    OCRDependencyError,
)
from lib.rag.utils.constants import (
    SUPPORTED_FORMATS,
    PROCESSED_OUTPUT_DIR,
)

# Preserve original module's __all__ if needed
__all__ = [
    # Orchestration
    'process_pdf',
    'process_epub',
    'process_txt',
    'process_document',
    'save_processed_text',
    # Quality
    'detect_pdf_quality',
    'QualityPipelineConfig',
    # OCR
    'run_ocr_on_pdf',
    'assess_pdf_ocr_quality',
    'redo_ocr_with_tesseract',
    'detect_letter_spacing_issue',
    'correct_letter_spacing',
    # Constants
    'SUPPORTED_FORMATS',
    'PROCESSED_OUTPUT_DIR',
    # Exceptions
    'TesseractNotFoundError',
    'FileSaveError',
    'OCRDependencyError',
]
```

**Source:** [Facade Pattern in Python](https://refactoring.guru/design-patterns/facade/python/example), [Python Best Practices for `__init__.py`](https://coderivers.org/blog/python-best-practice-for-package-__init__.py/)

### Pattern 2: Explicit Module API with `__all__`

**What:** Each new module declares its public API using `__all__`, making exports explicit and preventing accidental namespace pollution.

**When to use:** In every new module created during extraction to document intended public interface.

**Example:**
```python
# lib/rag/detection/footnotes.py
"""
Footnote detection and formatting for PDF documents.

This module handles superscript marker detection, footnote content extraction,
and markdown formatting of footnotes.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    # Public functions (exported through facade)
    'detect_footnotes_in_page',
    'format_footnotes_markdown',
    'calculate_page_normal_font_size',
    'is_superscript',
]

# Implementation follows...
def detect_footnotes_in_page(page: Any, page_num: int) -> Dict[str, List[Dict[str, Any]]]:
    """Detect footnotes in a PDF page."""
    logger.debug(f"Detecting footnotes on page {page_num}")
    # ... implementation
```

**Benefits:**
- Documents module's public API without reading full implementation
- Controls wildcard imports (`from module import *`)
- Informs static analysis tools (type checkers, IDEs) about public API
- Makes re-exports in `__init__.py` explicit

**Source:** [Python's __all__: Packages, Modules, and Wildcard Imports](https://realpython.com/python-all-attribute/), [PEP 8 Style Guide](https://peps.python.org/pep-0008/)

### Pattern 3: Dependency-Driven Extraction Order

**What:** Extract modules in order of their dependencies, starting with leaf modules (no internal dependencies) and ending with root modules (depend on everything else).

**When to use:** When decomposing a monolith to prevent circular import issues.

**Example extraction order:**
```
Phase 1 (Leaf modules - no dependencies):
  utils/constants.py      → Pure data
  utils/exceptions.py     → Pure classes
  utils/text.py           → String utilities
  utils/cache.py          → Cache management
  ocr/spacing.py          → String processing
  ocr/corruption.py       → OCR validation

Phase 2 (Detection - depends on utils):
  detection/page_numbers.py    → Roman numeral conversion
  detection/headings.py        → Font analysis
  detection/toc.py             → TOC extraction
  detection/front_matter.py    → Publisher extraction
  detection/footnotes.py       → Footnote engine (700 lines)

Phase 3 (Quality/OCR - depends on detection):
  quality/analysis.py     → PDF quality detection
  quality/pipeline.py     → Multi-stage pipeline
  xmark/detection.py      → X-mark detection
  ocr/recovery.py         → Tesseract integration

Phase 4 (Processors - depends on detection + quality):
  processors/epub.py      → EPUB processing
  processors/txt.py       → TXT processing
  processors/pdf.py       → PDF formatting

Phase 5 (Orchestrator - depends on everything):
  orchestrator.py         → Main entry points
```

**Why this order works:**
- Each extraction has all its dependencies already available
- No circular imports possible
- Each step can be tested independently
- Failed extraction can be reverted without breaking earlier work

**Source:** [Python Circular Import Resolution](https://www.datacamp.com/tutorial/python-circular-import), [Untangling Circular Dependencies](https://medium.com/@aman.deep291098/untangling-circular-dependencies-in-python-61316529c1f6)

### Pattern 4: Per-Module Logging with `__name__`

**What:** Each module creates its logger using `logging.getLogger(__name__)` at module level, creating a hierarchical namespace.

**When to use:** In every new module to enable fine-grained logging control.

**Example:**
```python
# lib/rag/detection/footnotes.py
import logging

logger = logging.getLogger(__name__)  # Creates 'lib.rag.detection.footnotes' logger

def detect_footnotes_in_page(page, page_num: int):
    logger.debug(f"Detecting footnotes on page {page_num}")
    # ... implementation
    logger.info(f"Found {len(footnotes)} footnotes on page {page_num}")
```

**Benefits:**
- Logger name matches Python package namespace automatically
- Hierarchical control: can enable `lib.rag.detection` to see all detection logs
- No logger name collisions
- Standard Python practice recognized by all logging tools

**Source:** [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html), [Logging Best Practices 2026](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/), [Best Practices for Logging in Python](https://betterstack.com/community/guides/logging/python/python-logging-best-practices/)

### Anti-Patterns to Avoid

- **Anti-Pattern 1: Extracting and refactoring simultaneously** — Two changes at once make debugging failures impossible. Extract verbatim first, refactor later.
- **Anti-Pattern 2: Changing function signatures during extraction** — Breaks facade contract and all tests. Signature changes are a separate PR.
- **Anti-Pattern 3: Splitting highly coupled code across files** — Footnote detection (700 lines, 40 branches) should stay as single cohesive unit to avoid excessive cross-file coupling.
- **Anti-Pattern 4: Creating deep import chains** — Modules should import from utils and orchestrator directly, not create 4+ level chains that slow imports.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Module re-export mechanism | Custom import wrapper or `globals()` manipulation | Standard `from X import Y` + `__all__` | Standard Python packaging pattern, works with all tools (type checkers, IDEs, documentation generators) |
| Logger hierarchies | String-based logger names or manual hierarchy | `logging.getLogger(__name__)` | Automatically creates hierarchical namespace matching package structure |
| Circular import detection | Trial and error | Dependency-driven extraction order | Prevents circular imports by design rather than fixing after they occur |
| Type hint validation | Runtime type checking | mypy static analysis | Type hints are for static analysis, not runtime; mypy is standard tool |

**Key insight:** Python's built-in packaging system (`__init__.py`, `__all__`, import mechanics) already solves backward-compatible refactoring. Custom solutions create maintenance burden and break tooling expectations.

## Common Pitfalls

### Pitfall 1: Circular Imports from Shared Utilities

**What goes wrong:** Two modules need the same helper function, so they import from each other, creating a circular dependency that crashes at import time.

**Why it happens:** Not planning extraction order based on dependencies; splitting utilities across domain modules instead of centralizing in `utils/`.

**How to avoid:**
1. Extract all shared utilities to `utils/` modules FIRST (Phase 1)
2. Never import from peer modules (e.g., `detection/footnotes.py` should not import from `detection/toc.py`)
3. If two modules need to share code, extract to `utils/` or have orchestrator coordinate

**Warning signs:**
- `ImportError: cannot import name 'X' from partially initialized module`
- Tests that work individually but fail when run together
- Functions that seem like they belong in multiple places

**Source:** [Closing The Loop On Python Circular Import Issue](https://www.mend.io/blog/closing-the-loop-on-python-circular-import-issue/), [Fixing circular imports - Python Morsels](https://www.pythonmorsels.com/fixing-circular-imports/)

### Pitfall 2: Breaking Python Bridge Contract Silently

**What goes wrong:** `python_bridge.py` imports from `rag_processing.py`; Node.js calls Python via `PythonShell`. Extraction moves a function but forgets to re-export it in the facade. Import fails at runtime, but there's no compile-time error because the Node-Python boundary is stringly-typed.

**Why it happens:** No type checking across Node-Python boundary; tests mock the bridge instead of testing it.

**How to avoid:**
1. Run full integration test after EVERY extraction step
2. Never remove an export from `rag_processing.py` — only add imports from new modules
3. Use `__all__` in facade to explicitly list every exported name
4. Run `uv run pytest && npm test` after each commit before pushing

**Warning signs:**
- Python tests pass, Node tests pass, but MCP server crashes
- `ModuleNotFoundError` or `AttributeError` when server starts
- Error messages about missing Python functions from Node.js logs

**Detection:** Integration smoke test that invokes `python_bridge.py` functions from Node.js

### Pitfall 3: Test Mocks Breaking After Refactor

**What goes wrong:** Tests mock `lib.rag_processing.X`; after extraction, `X` lives in `lib.rag.quality.analysis` but is re-exported through facade. Mock path is wrong, mocks don't intercept, tests fail or pass incorrectly.

**Why it happens:** Mock targets are based on import location, not definition location. Re-exports change the resolution path.

**How to avoid:**
1. DO NOT change test files during extraction phase
2. Ensure facade re-exports every function that tests import
3. Mock paths like `lib.rag_processing.pytesseract` should continue working because facade imports `pytesseract` in its namespace

**Warning signs:**
- Tests that passed before extraction now fail
- Mocks that should trigger don't seem to activate
- Coverage reports show unmocked code paths executing

**Detection:** Run full test suite (`uv run pytest`) after each extraction step

### Pitfall 4: Forgetting Type Hints on Public API

**What goes wrong:** After extraction, facade re-exports functions but doesn't preserve type hints, breaking IDE autocomplete and static analysis.

**Why it happens:** Importing and re-exporting doesn't automatically propagate type information without explicit annotations.

**How to avoid:**
1. Add type hints to the 16 public API functions during extraction
2. Use `from __future__ import annotations` for forward references
3. Run `mypy lib/rag_processing.py` to verify facade type hints

**Warning signs:**
- IDEs show `Any` type for function parameters/returns
- mypy reports missing type information
- API documentation generators can't infer types

**Source:** [Python Type Hints Best Practices](https://typing.python.org/en/latest/reference/best_practices.html), [PEP 484 Type Hints](https://peps.python.org/pep-0484/)

### Pitfall 5: Losing Module-Level State During Extraction

**What goes wrong:** Original module has module-level caches or compiled regexes (`_TEXTPAGE_CACHE = {}`). After extraction, multiple modules try to access the cache but it's now local to one module.

**Why it happens:** Module-level globals are scoped to the defining module. Extracting code that references globals breaks the reference.

**How to avoid:**
1. Identify all module-level state BEFORE extraction (grep for `^[A-Z_]+ =` patterns)
2. Move all shared state to `utils/cache.py` or `utils/constants.py`
3. Convert module-level mutable state to function parameters or singleton pattern

**Warning signs:**
- Cache hit rates drop to zero after extraction
- Regex compilation happens repeatedly instead of once
- Performance degrades after refactor

**Detection:** Performance benchmarks, cache statistics

## Code Examples

Verified patterns from official sources:

### Incremental Extraction Pattern

```python
# Step 1: Original monolith (rag_processing.py)
def _slugify(value, allow_unicode=False):
    # ... implementation (50 lines)

def process_pdf(file_path: Path) -> str:
    filename = _slugify(file_path.stem)  # Uses _slugify
    # ... rest of implementation

# Step 2: Extract to new module (utils/text.py)
# lib/rag/utils/text.py
"""Text processing utilities."""
import logging

logger = logging.getLogger(__name__)

__all__ = ['slugify']

def slugify(value, allow_unicode=False):
    """Convert string to URL-safe slug."""
    # ... implementation (same 50 lines, verbatim)

# Step 3: Replace in original file (rag_processing.py)
from lib.rag.utils.text import slugify as _slugify  # Import with original name

def process_pdf(file_path: Path) -> str:
    filename = _slugify(file_path.stem)  # Still works!
    # ... rest of implementation

# Step 4: After all extractions, facade version
# lib/rag_processing.py (final facade)
from lib.rag.orchestrator import process_pdf
from lib.rag.utils.text import slugify as _slugify  # If tests import _slugify

__all__ = ['process_pdf']
```

**Source:** Direct application of facade pattern from [Refactoring Guru](https://refactoring.guru/design-patterns/facade/python/example)

### Package Re-Export via __init__.py

```python
# lib/rag/__init__.py
"""
RAG processing package - public API.
Import from parent facade (lib.rag_processing) for backward compatibility.
"""

# Re-export everything from submodules for direct package import
from lib.rag.orchestrator import (
    process_pdf,
    process_epub,
    process_txt,
    process_document,
    save_processed_text,
)
from lib.rag.quality.analysis import detect_pdf_quality
from lib.rag.quality.pipeline import QualityPipelineConfig
# ... etc

__all__ = [
    'process_pdf',
    'process_epub',
    'process_txt',
    'process_document',
    'save_processed_text',
    'detect_pdf_quality',
    'QualityPipelineConfig',
]

# This allows both import styles to work:
# from lib.rag_processing import process_pdf  # Via facade (backward compatible)
# from lib.rag import process_pdf              # Direct package import (new style)
```

**Source:** [The Correct Way to Re-Export Modules from __init__.py](https://www.pythontutorials.net/blog/correct-way-to-re-export-modules-from-init-py/)

### Type Hints for Public API

```python
# lib/rag_processing.py (facade with type hints)
"""RAG document processing - backward-compatible facade."""
from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any

# Import implementations
from lib.rag.orchestrator import (
    process_pdf as _process_pdf,
    process_document as _process_document,
    save_processed_text as _save_processed_text,
)

# Re-export with explicit type hints for documentation
def process_pdf(
    file_path: Path,
    output_format: str = "txt",
    book_details: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process a PDF file and extract text content.

    Args:
        file_path: Path to PDF file
        output_format: Output format (txt or markdown)
        book_details: Optional book metadata dictionary

    Returns:
        Extracted text content as string
    """
    return _process_pdf(file_path, output_format, book_details)

async def process_document(
    file_path_str: str,
    output_format: str = "txt",
    book_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process any supported document format.

    Returns:
        Dict with 'content', 'file_path', 'format' keys
    """
    return await _process_document(file_path_str, output_format, book_details)

async def save_processed_text(
    content: str,
    file_path: str,
    output_format: str = "txt",
    book_details: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Save processed text to file with metadata.

    Returns:
        Dict with 'file_path' and 'metadata_path' keys
    """
    return await _save_processed_text(content, file_path, output_format, book_details)
```

**Source:** [Annotations Best Practices — Python 3.14 Docs](https://docs.python.org/3/howto/annotations.html), [Type Hints in Python](https://realpython.com/python-type-checking/)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Monolithic modules (4000+ lines) | Domain-driven modular design (≤500 lines per module) | Python 3.x era | Improved maintainability, testability, and code navigation |
| Implicit exports (all module contents) | Explicit `__all__` declarations | PEP 8 recommendation | Better API documentation and import control |
| String-based logger names | `getLogger(__name__)` | Python 2.7+ | Automatic hierarchical namespacing |
| `z.object({}).passthrough()` | `z.looseObject({})` (Zod 4) | Zod v4 (2024) | Not directly related to Python, but mentioned in context |
| Global state in monoliths | Dependency injection or utils modules | Modern Python (3.6+) | Avoids import-time side effects and circular dependencies |

**Deprecated/outdated:**
- Direct manipulation of `sys.modules` for dynamic imports — use `importlib` instead
- `imp` module for import mechanics — replaced by `importlib` in Python 3.4+
- Relative imports without `from` statement (e.g., `import .module`) — now requires `from . import module`

## Open Questions

Things that couldn't be fully resolved:

1. **Should footnote detection module (700 lines) be split further?**
   - What we know: It's the largest single module, exceeds 500-line guideline, but has high internal cohesion (40-branch main function with 15+ helper functions)
   - What's unclear: Whether splitting would improve or harm maintainability
   - Recommendation: Extract as single unit in Phase 2, evaluate split in Phase 6 after all extractions complete. Splitting during extraction adds risk.

2. **Should we add `py.typed` marker for PEP 561 compliance?**
   - What we know: `py.typed` marker enables type checkers to use this package's type hints if installed as dependency
   - What's unclear: Whether this package will be used as a library (currently it's an MCP server)
   - Recommendation: Defer to Phase 6; not needed for internal type checking, only for external consumers

3. **What's the exact version compatibility for type hint features?**
   - What we know: Project requires Python 3.9+, type hints syntax varies by version
   - What's unclear: Whether to use 3.9 syntax (`Dict[str, Any]`) or 3.10+ syntax (`dict[str, Any]`)
   - Recommendation: Use `from __future__ import annotations` for forward compatibility, allows modern syntax on 3.9

4. **Should orchestrator module call imported modules directly or through the package __init__?**
   - What we know: Both `from lib.rag.detection.footnotes import detect_footnotes` and `from lib.rag.detection import detect_footnotes` work if `__init__.py` re-exports
   - What's unclear: Which style is preferred for internal imports
   - Recommendation: Import directly from defining module (not through `__init__`), use `__init__` only for external-facing API

## Sources

### Primary (HIGH confidence)
- [Python Logging HOWTO — Python 3.14 Docs](https://docs.python.org/3/howto/logging.html) — Official logging best practices with `getLogger(__name__)`
- [Python's __all__: Packages, Modules, and Wildcard Imports](https://realpython.com/python-all-attribute/) — Comprehensive guide to `__all__` usage
- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/) — Official Python style recommendations
- [Facade Pattern in Python](https://refactoring.guru/design-patterns/facade/python/example) — Canonical facade pattern implementation
- [Annotations Best Practices — Python 3.14 Docs](https://docs.python.org/3/howto/annotations.html) — Official type hints guide
- [Structuring Your Project — Hitchhiker's Guide to Python](https://docs.python-guide.org/writing/structure/) — Python project organization patterns
- Direct codebase analysis of `lib/rag_processing.py` (4,968 lines), test import analysis across 40+ test files

### Secondary (MEDIUM confidence)
- [Python Refactoring: Techniques, Tools, and Best Practices](https://www.codesee.io/learning-center/python-refactoring) — Modern refactoring patterns
- [Refactoring Python Applications for Simplicity – Real Python](https://realpython.com/python-refactoring/) — Practical refactoring guide
- [Python Circular Import Resolution](https://www.datacamp.com/tutorial/python-circular-import) — Circular dependency patterns
- [Fixing circular imports - Python Morsels](https://www.pythonmorsels.com/fixing-circular-imports/) — Practical solutions
- [The Correct Way to Re-Export Modules from __init__.py](https://www.pythontutorials.net/blog/correct-way-to-re-export-modules-from-init-py/) — Re-export patterns
- [Python Best Practices for `__init__.py`](https://coderivers.org/blog/python-best-practice-for-package-__init__.py/) — Package API design
- [Python Logging Best Practices 2026](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/) — Current logging patterns
- [Type Hints in Python](https://realpython.com/python-type-checking/) — Practical type hints guide

### Tertiary (LOW confidence)
- [Modular Monolith in Python](https://breadcrumbscollector.tech/modular-monolith-in-python/) — Architectural patterns (2024)
- [Using the Facade Pattern to Wrap Third-Party Integrations](https://alysivji.com/clean-architecture-with-the-facade-pattern.html) — Facade use cases

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All tools are Python built-ins with official documentation
- Architecture patterns: HIGH — Based on official Python packaging guides, PEP 8, and direct codebase analysis
- Pitfalls: HIGH — Verified with Python documentation and community best practices; circular import patterns well-documented

**Research date:** 2026-02-01
**Valid until:** 60 days (Python packaging patterns are stable; monthly review for new PEPs)
