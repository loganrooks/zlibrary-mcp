# External Integrations

**Analysis Date:** 2026-01-28

## APIs & External Services

**Z-Library (Book Search & Download):**
- Service: Z-Library EAPI (Hydra mode, multiple domains)
  - What it's used for: Book search, download links, metadata retrieval, user account management
  - SDK/Client: Vendored zlibrary fork (`./zlibrary/` directory)
  - API Type: Custom web scraping + EAPI calls (no official public API)
  - Authentication: Email/password credentials
  - Files: `src/lib/zlibrary-api.ts`, `lib/python_bridge.py`, `lib/client_manager.py`

**HTTP & Async Operations:**
- httpx 0.28.0 - Generic HTTP client for API calls
- aiohttp (via zlibrary) - Async HTTP with proxy support (SOCKS5 capable)
- BeautifulSoup4 + lxml - HTML scraping for metadata extraction

## Data Storage

**File Storage:**
- Local filesystem only
- Downloaded books: `./downloads/` directory (configurable via outputDir parameter)
- Processed RAG output: `./processed_rag_output/` directory
- Docker volume mount: `./downloads:/app/downloads` (persistent storage)

**Databases:**
- No persistent database configured
- In-memory state only: Z-Library session management via `ZLibraryClient` class
- Optional caching: Not currently implemented

**Temporary Storage:**
- OCR processing: Uses Python `tempfile` module for intermediate files
- RAG processing: Temporary files for PDF/EPUB extraction

## Authentication & Identity

**Auth Provider:**
- Custom implementation: Z-Library account credentials
- Method: Email/password authentication to Z-Library EAPI
- Location: Environment variables (external configuration)

**Required Environment Variables:**
- `ZLIBRARY_EMAIL` - Z-Library account email (required)
- `ZLIBRARY_PASSWORD` - Z-Library account password (required)
- `ZLIBRARY_MIRROR` - Custom Z-Library mirror URL (optional, defaults to https://z-library.sk)
- `ZLIBRARY_DEBUG` - Enable debug logging (optional, set to 1/true/yes)
- `DEBUG` - Alternative debug flag (optional)

**Credential Management:**
- Files handling credentials: `lib/client_manager.py` (env var lookup), `lib/python_bridge.py` (env var lookup)
- No credential storage; read from environment at runtime
- Deprecation note: Direct `get_book_by_id` removed; always use `search_books` for reliability

## Monitoring & Observability

**Error Tracking:**
- None detected - no external error tracking service configured
- Local error logging via Python logging module (stdlib)

**Logs:**
- Python: `logging` module with configurable levels (DEBUG via ZLIBRARY_DEBUG env var)
  - Logger: `logger = logging.getLogger('zlibrary')`
  - Format: `[TIMESTAMP] [LEVEL] module:function:line - message`
  - File: `src/lib/zlibrary-api.ts` handles async file logging via `appendFile` from `fs/promises`

**Debugging:**
- Debug mode: `ZLIBRARY_DEBUG=1` or `DEBUG=1` enables verbose logging
- Function: `_configure_debug_logging()` in `lib/python_bridge.py`

## CI/CD & Deployment

**Hosting:**
- Docker container deployment
- Base image: `ghcr.io/supercorp-ai/supergateway:3.4.3` (HTTP gateway)
- Port: 8000 (HTTP via SuperGateway)
- Transport: Stdio MCP wrapped by SuperGateway for HTTP access

**CI Pipeline:**
- Not explicitly detected in codebase
- Build validation: `npm run build` with post-build Python path validation
- Health check: HTTP GET to `/health` endpoint (30s interval)

**Build Process:**
- Multi-stage Docker build
- Stage 1: Node + Python dependency resolution
- Stage 2: Runtime with minimal footprint
- Environment setup: `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy` (portable venv)

## Environment Configuration

**Required env vars:**
- `ZLIBRARY_EMAIL` - Z-Library account email
- `ZLIBRARY_PASSWORD` - Z-Library account password

**Optional env vars:**
- `ZLIBRARY_MIRROR` - Custom mirror URL (defaults: https://z-library.sk)
- `ZLIBRARY_DEBUG` - Debug logging (1/true/yes)
- `DEBUG` - Alternate debug flag

**Retry Configuration:**
- `RETRY_MAX_RETRIES` - Maximum attempts (default: 3)
- `RETRY_INITIAL_DELAY` - Initial delay ms (default: 1000)
- `RETRY_MAX_DELAY` - Maximum delay ms (default: 30000)
- `RETRY_FACTOR` - Exponential backoff multiplier (default: 2)

**Circuit Breaker Configuration:**
- `CIRCUIT_BREAKER_THRESHOLD` - Failures before circuit opens (default: 5)
- `CIRCUIT_BREAKER_TIMEOUT` - Recovery timeout ms (default: 60000)

**Secrets location:**
- Environment variables (external configuration)
- Docker: `.env` file (loaded via `env_file` in docker-compose.yaml)
- No .env.example provided (user must create .env with credentials)

## Webhooks & Callbacks

**Incoming:**
- Not applicable - this is an MCP server (request-response only)
- Tools are called synchronously by MCP clients (Claude, Roocode, Cline)

**Outgoing:**
- None detected
- No external callbacks or webhook registrations

## Tool Definitions

**Available MCP Tools:**

1. **search_books** - Primary book discovery
   - Params: query, exact, fromYear, toYear, languages, extensions, content_types, count
   - Returns: Array of book objects with metadata

2. **full_text_search** - Search within book content
   - Params: query, exact, phrase, words, languages, extensions, content_types, count

3. **get_download_history** - View user's download history
   - Params: count

4. **get_download_limits** - Check remaining download quota
   - Params: None

5. **get_recent_books** - Get recently added books
   - Params: count, format

6. **download_book_to_file** - Download with optional RAG processing
   - Params: bookDetails (object from search), outputDir, process_for_rag, processed_output_format
   - Returns: File path or processed RAG output path

7. **process_document_for_rag** - Process existing file for RAG
   - Params: file_path, output_format
   - Returns: Path to processed text file or error

## Rate Limiting & Quotas

**Z-Library Constraints:**
- Rate limiting detection: `RateLimitError` exception in `lib/client_manager.py`
- Automatic retry with exponential backoff (configurable via env vars)
- Circuit breaker: Opens after 5 failures, waits 60 seconds before retry
- Files: `src/lib/retry-manager.ts`, `src/lib/circuit-breaker.ts`

## Data Processing Pipeline

**Download Workflow:**
- Input: Book object from search results (must have 'url' or 'href')
- Process: Z-Library EAPI call via Python bridge
- Output: Downloaded file path in `./downloads/`
- File naming: `create_unified_filename()` from `lib/filename_utils.py`

**RAG Processing Workflow:**
- Input: Downloaded file (EPUB, PDF, TXT)
- Process: Text extraction via `rag_processing.py`
  - EPUB: ebooklib extraction
  - PDF: pymupdf (fitz) extraction with quality detection
  - TXT: Direct processing
- Output: Plain text file in `./processed_rag_output/`
- Metadata: JSON sidecar files for traceability

**Text Extraction Features:**
- Files: `lib/rag_processing.py`, `lib/enhanced_metadata.py`
- Footnote detection: NLTK sentence boundary + custom model
- Strikethrough detection: Regex patterns for formatting preservation
- OCR integration: Optional pytesseract for scanned PDFs
- Garbled text detection: Unicode normalization + pattern analysis

## External Dependencies

**Node.js Ecosystem:**
- @modelcontextprotocol/sdk 1.8.0 - Protocol implementation (GitHub: modelcontextprotocol/sdk)
- python-shell 5.0.0 - Python subprocess bridge (npm package)
- Zod 3.24.2 - Schema validation (JSON schema generation)
- env-paths 3.0.0 - Cross-platform path resolution

**Python Ecosystem:**
- zlibrary (vendored fork) - Custom Z-Library client
  - Original: https://github.com/sertraline/zlibrary
  - Modifications: Download logic, metadata extraction
- pymupdf >= 1.26.0 - PDF processing
- ebooklib >= 0.19 - EPUB processing
- httpx >= 0.28.0 - HTTP client
- beautifulsoup4 >= 4.14.0 - HTML parsing
- nltk >= 3.8.1 - NLP processing
- ocrmypdf >= 15.4.4 - OCR enhancement

---

*Integration audit: 2026-01-28*
