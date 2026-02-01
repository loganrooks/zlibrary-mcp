# ADR-009: Python Monolith Decomposition

**Date:** 2026-01-31

**Status:** Accepted

## Context

The `lib/rag_processing.py` file had grown to 4,968 lines, making it difficult to navigate, test, and maintain. It contained document extraction logic, quality analysis, OCR recovery, footnote detection, heading detection, front matter handling, and formatting -- all in a single file. This violated the Single Responsibility Principle and made targeted changes risky.

## Decision

Decompose `rag_processing.py` into domain-specific modules under `lib/rag/`:

```
lib/rag/
  __init__.py           # Facade (backward compat)
  orchestrator.py       # Main processing orchestration
  orchestrator_pdf.py   # PDF-specific orchestration
  processors/           # Format extractors (epub.py, pdf.py, txt.py)
  detection/            # Footnotes, front matter, headings, ToC, page numbers
  quality/              # Quality analysis, pipeline, OCR stage
  ocr/                  # Corruption detection, recovery, spacing
  xmark/                # X-mark/strikethrough detection
  utils/                # Cache, constants, deps, exceptions, header, text
```

Use a facade pattern: `lib/rag/__init__.py` re-exports all public APIs so that existing code importing from `rag_processing` continues to work without modification.

Submodules use a `_get_facade()` pattern for cross-module dependencies, avoiding circular imports while maintaining access to shared state.

## Consequences

### Positive
- **All modules under 500 lines**: Manageable, focused files
- **Zero test modifications**: Facade preserves backward compatibility
- **Domain clarity**: Each module has a single responsibility
- **Easier maintenance**: Changes to footnote detection don't risk breaking OCR recovery

### Negative
- **Legacy facade remains**: `lib/rag_processing.py` still exists as a thin wrapper
- **Cross-module access pattern**: `_get_facade()` adds indirection for shared state
- **More files to navigate**: Developer must understand module structure

### Neutral
- **No behavior changes**: Pure structural refactor, all tests pass unchanged
