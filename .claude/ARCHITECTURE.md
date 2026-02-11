# Architecture Overview

<!-- Last Verified: 2026-02-01 -->

**Last Updated**: 2026-02-01
**Status**: Post-cleanup — all 7 phases complete, codebase modernized

---

## System Architecture

### High-Level Components

```
+-----------------------------------------------------------+
|                    MCP Client (Claude)                      |
+-----------------------------+-----------------------------+
                              | MCP Protocol (SDK 1.25+)
+-----------------------------v-----------------------------+
|              MCP Server (Node.js/TypeScript)                |
|  - 12 tools via McpServer server.tool() API                |
|  - Client communication handling (src/index.ts)            |
+-----------------------------+-----------------------------+
                              | PythonShell
+-----------------------------v-----------------------------+
|              Python Bridge (lib/)                           |
|  - EAPI client (zlibrary/eapi.py) for JSON API calls       |
|  - Tool modules (author_tools, term_tools, booklist_tools) |
|  - Document processing (lib/rag/ domain modules)           |
+-----------------------------+-----------------------------+
                              | EAPI JSON + httpx
+-----------------------------v-----------------------------+
|         Z-Library EAPI Endpoints                            |
|  - /eapi/book/search — search operations                   |
|  - /eapi/book/{id}/{hash} — book metadata                  |
|  - EAPIClient handles all operations (search, metadata, downloads) |
+-----------------------------------------------------------+
```

### Data Flow Patterns

**Search**: Client -> MCP -> Python -> EAPI JSON endpoint -> Normalized results
**Download**: Client -> MCP -> Python -> EAPIClient (search + download)
**RAG**: File -> lib/rag/ pipeline -> Quality analysis -> Extracted Markdown -> File

**Critical Design**: RAG returns **file paths**, not raw text (prevents context overflow)

---

## Current Implementation Status

### MCP Tools (12 total)
- search_books, full_text_search, get_download_history
- get_download_limits, get_recent_books, download_book_to_file
- process_document_for_rag, get_book_metadata
- search_by_term, search_by_author, search_advanced, fetch_booklist

All registered via `server.tool()` (McpServer API, MCP SDK 1.25+).

### RAG Pipeline
- Stage 1: Statistical garbled detection (complete)
- Stage 2: Visual X-mark detection (complete)
- Stage 3: OCR recovery (framework complete, ML recovery pending)
- Formatting preservation: Bold, italic, strikethrough (complete)
- Stages 4-11: Designed, not implemented

### Test Coverage
- Node.js (Jest): ESM modules with `jest.unstable_mockModule`
- Python (Pytest): Domain module tests + real PDF validation
- Integration Tests: Passing

---

## Key Design Decisions (ADRs)

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | Node.js MCP server + Python processing | Implemented |
| ADR-002 | Download via bookDetails page scraping | Superseded by EAPI |
| ADR-003 | Deprecate get_book_by_id | Implemented |
| ADR-004 | Python scripts in lib/, path resolution from dist/ | Implemented |
| ADR-005 | EAPI migration (bypass Cloudflare) | Implemented |
| ADR-006 | Quality pipeline: Statistical -> Visual -> OCR | Implemented (Stages 1-3) |
| ADR-008 | Stage 2 independence (X-mark not conditional on garbled) | Implemented |
| ADR-009 | Python monolith decomposition into lib/rag/ | Implemented |
| ADR-010 | MCP SDK upgrade to 1.25+ (McpServer API) | Implemented |

---

## Module Structure

### Python Bridge Modules (lib/)

| Module | Responsibility | Status |
|--------|---------------|--------|
| `python_bridge.py` | Main bridge: auth, search, download, EAPI init | Stable |
| `author_tools.py` | Author search via EAPI | Stable |
| `term_tools.py` | Term-based search via EAPI | Stable |
| `booklist_tools.py` | Booklist fetch (graceful degradation) | Stable |
| `enhanced_metadata.py` | Book metadata extraction via EAPI | Stable |
| `advanced_search.py` | Fuzzy match search | Stable |

### RAG Domain Modules (lib/rag/)

| Module | Responsibility |
|--------|---------------|
| `lib/rag/__init__.py` | Facade (backward compat with rag_processing.py) |
| `lib/rag/orchestrator.py` | Main processing orchestration |
| `lib/rag/orchestrator_pdf.py` | PDF-specific orchestration |
| `lib/rag/processors/epub.py` | EPUB extraction |
| `lib/rag/processors/pdf.py` | PDF extraction |
| `lib/rag/processors/txt.py` | TXT extraction |
| `lib/rag/detection/` | Footnotes, front matter, headings, ToC, page numbers |
| `lib/rag/quality/` | Quality analysis, pipeline, OCR stage |
| `lib/rag/ocr/` | Corruption detection, recovery, spacing |
| `lib/rag/xmark/` | X-mark/strikethrough detection |
| `lib/rag/utils/` | Cache, constants, deps, exceptions, header, text utils |

All modules under 500 lines. Facade pattern in `lib/rag/__init__.py` preserves backward compatibility.

### EAPI Client (zlibrary/eapi.py)

| Component | Purpose |
|-----------|---------|
| `EAPIClient` | httpx-based client for /eapi/ JSON endpoints |
| `normalize_eapi_book` | Normalize EAPI response to internal Book format |
| `normalize_eapi_search_response` | Normalize search results |

### Support Modules (lib/)

| Module | Purpose |
|--------|---------|
| `rag_processing.py` | Legacy facade (delegates to lib/rag/) |
| `rag_data_models.py` | TextSpan, PageRegion data structures |
| `garbled_text_detection.py` | Stage 1 statistical analysis |
| `strikethrough_detection.py` | Stage 2 X-mark detection |
| `formatting_group_merger.py` | Span grouping for markdown |
| `footnote_continuation.py` | Multi-page footnote tracking |
| `filename_utils.py` | Unified filename creation |
| `metadata_generator.py` | YAML frontmatter generation |
| `quality_verification.py` | Quality checks and reporting |

---

## Technology Stack

**Runtime**:
- Node.js 18+ (MCP server)
- Python 3.10+ (bridge and processing)
- UV (Python dependency management)

**Key Dependencies**:
- `@modelcontextprotocol/sdk` ^1.25.3 - MCP protocol (McpServer API)
- `python-shell` - Node.js to Python bridge
- `httpx` - EAPI HTTP client
- `ebooklib` - EPUB processing
- `PyMuPDF` (fitz) - PDF extraction
- `opencv-python` - Visual X-mark detection
- `pytesseract` - OCR (optional)

**Development**:
- TypeScript, Jest (Node.js testing, ESM)
- Pytest, pytest-mock (Python testing)
- UV (dependency management, lock file)

---

## Directory Structure

```
zlibrary-mcp/
+-- src/                          # Node.js MCP server
|   +-- index.ts                  # Entry point (12 tools via server.tool())
|   +-- lib/                      # Server utilities
|       +-- zlibrary-api.ts       # Python bridge interface
|       +-- venv-manager.ts       # UV-based venv management
|       +-- retry-manager.ts      # Retry with exponential backoff
|       +-- circuit-breaker.ts    # Circuit breaker pattern
|       +-- paths.ts              # Path resolution helpers
|
+-- lib/                          # Python source
|   +-- python_bridge.py          # Main bridge (EAPI init, auth, routing)
|   +-- author_tools.py           # Author search
|   +-- term_tools.py             # Term search
|   +-- booklist_tools.py         # Booklist fetch
|   +-- enhanced_metadata.py      # Book metadata
|   +-- advanced_search.py        # Fuzzy search
|   +-- rag_processing.py         # Legacy facade
|   +-- rag/                      # Decomposed RAG pipeline
|       +-- __init__.py           # Facade (backward compat)
|       +-- orchestrator.py       # Main orchestration
|       +-- orchestrator_pdf.py   # PDF orchestration
|       +-- processors/           # Format-specific extractors
|       +-- detection/            # Footnotes, headings, ToC, etc.
|       +-- quality/              # Quality analysis pipeline
|       +-- ocr/                  # OCR recovery
|       +-- xmark/                # X-mark detection
|       +-- utils/                # Shared utilities
|
+-- zlibrary/                     # Vendored fork
|   +-- zlibrary/                 # Package
|   +-- eapi.py                   # EAPI client (EAPIClient class)
|
+-- __tests__/                    # Test suites
|   +-- *.test.js                 # Node.js (Jest, ESM)
|   +-- python/                   # Python (Pytest)
|
+-- docs/adr/                     # Architecture decisions (ADR-001 through ADR-010)
+-- .claude/                      # Development guides
```

---

## Integration Points

### Z-Library EAPI
- JSON endpoints at `/eapi/` path
- httpx client with lazy initialization and cookie-based auth
- Responses normalized to internal Book format
- Cloudflare bypass: API endpoints not subject to browser challenges

### MCP Protocol
- McpServer API with `server.tool()` registration
- JSON-RPC 2.0 communication
- Stdio transport

### Document Libraries
- ebooklib (EPUB)
- PyMuPDF (PDF)
- pytesseract (OCR, optional)
- opencv-python (image analysis)

---

## Security Architecture

### Credential Management
- Environment variables only (ZLIBRARY_EMAIL, ZLIBRARY_PASSWORD)
- Never committed to git (.env in .gitignore)
- No hardcoded credentials

### Sandboxing
- Python bridge runs in isolated .venv/ (UV-managed)
- Download directory configurable (default: ./downloads/)

### Error Handling
- Circuit breaker pattern for API failures
- Retry logic with exponential backoff
- Graceful degradation (booklists, terms, IPFS CIDs)

---

## Quick Reference

- **Add New ADR**: See [docs/adr/README.md](../docs/adr/README.md)
- **Roadmap**: See [ROADMAP.md](ROADMAP.md) for strategic plan
- **Project Context**: See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for mission and domain model

---

**Navigation**:
- [ROADMAP.md](ROADMAP.md) - Strategic planning
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) - Mission and domain model
- [PATTERNS.md](PATTERNS.md) - Code patterns to follow
