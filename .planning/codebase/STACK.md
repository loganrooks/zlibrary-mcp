# Technology Stack

**Analysis Date:** 2026-01-28

## Languages

**Primary:**
- TypeScript 5.5.3 - MCP server implementation, tool registration, client communication
- JavaScript (ESM) - Build output, compiled TypeScript runtime code

**Secondary:**
- Python 3.9+ - Document processing, Z-Library API interaction, RAG pipeline

## Runtime

**Environment:**
- Node.js >= 14.0.0 (package.json engines specification)
- Python 3.9+ (pyproject.toml requirement)

**Package Manager:**
- npm (Node.js dependencies, lockfile: package-lock.json present)
- UV (Python dependencies, modern 2025 best practice, generates uv.lock)
  - Location: `.venv/` in project root (portable, moves with project)
  - Setup: `uv sync` installs all Python dependencies

## Frameworks

**Core:**
- @modelcontextprotocol/sdk 1.8.0 - MCP protocol implementation
  - Uses: `StdioServerTransport` for stdio transport
  - Location: `src/index.ts` (server entry point)

**Document Processing:**
- pymupdf (fitz) >= 1.26.0 - PDF processing and extraction
- ebooklib >= 0.19 - EPUB processing
- pytesseract >= 0.3.10 - OCR for scanned PDFs (optional, via `[ocr]` extra)

**HTTP & Async:**
- httpx >= 0.28.0 - HTTP client (used in search, booklists, advanced_search)
- aiofiles >= 24.1.0 - Async file operations
- aiohttp (vendored zlibrary dependency) - HTTP with proxy support

**HTML/XML Parsing:**
- beautifulsoup4 >= 4.14.0 - HTML parsing
- lxml >= 6.0.0 - XML/HTML parser (beautifulsoup4 backend)

**NLP & Text Analysis:**
- nltk >= 3.8.1 - Sentence boundary detection for footnote extraction
- ocrmypdf >= 15.4.4 - OCR integration for scanned PDF improvements

**Build & Dev:**
- TypeScript 5.5.3 - Type checking and compilation
- Jest 29.7.0 - Test runner (ESM with `--experimental-vm-modules` flag)
- ts-jest 29.3.2 - TypeScript support in Jest
- Zod 3.24.2 - Runtime schema validation for tool parameters
- zod-to-json-schema 3.24.5 - Convert Zod schemas to JSON schema

## Key Dependencies

**Critical:**
- @modelcontextprotocol/sdk 1.8.0 - Core MCP protocol, enables Claude integration
- python-shell 5.0.0 - Node.js ↔ Python bridge via JSON-RPC pattern
- Zod 3.24.2 - Runtime validation of tool parameters (prevents invalid requests to Python)

**Infrastructure:**
- env-paths 3.0.0 - Cross-platform directory resolution (.venv location management)
- Vendored zlibrary fork (`./zlibrary/` directory) - Modified Z-Library EAPI client
  - Handles: Domain discovery (Hydra mode), book search, download workflow
  - Dependencies: aiohttp, aiohttp_socks, httpx, beautifulsoup4, lxml, ujson

## Configuration

**Environment:**
- TypeScript: `tsconfig.json` (ES2022 target, strict mode enabled, ESM module system)
- Jest: `jest.config.js` (ESM preset, moduleNameMapper for path resolution)
- Python: `pyproject.toml` with UV source configuration
  - Vendored zlibrary installed as editable: `zlibrary = { path = "./zlibrary", editable = true }`

**Build:**
- `npm run build` → TypeScript compilation (`tsc`)
- Post-build validation: `scripts/validate-python-bridge.js` ensures Python files exist
- Output: `dist/` directory with compiled JavaScript
- Python scripts remain in source `lib/` (not copied, referenced via path resolution)

## Platform Requirements

**Development:**
- Node.js 14+ with npm
- Python 3.9+ with UV installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- System libraries for PDF processing:
  - libmupdf (for pymupdf)
  - poppler-utils (for pdf2image, optional)
  - tesseract (for pytesseract OCR, optional)

**Production:**
- Deployment: Docker container (multi-stage build in `docker/Dockerfile`)
  - Base: `node:22-alpine` (builder stage)
  - Runtime: `ghcr.io/supercorp-ai/supergateway:3.4.3` (HTTP gateway overlay)
  - Exposed: Port 8000 (HTTP via SuperGateway)
- Environment variables: `ZLIBRARY_EMAIL`, `ZLIBRARY_PASSWORD`, optional `ZLIBRARY_MIRROR`
- Volume mounts: `./downloads/` for downloaded books, `./processed_rag_output/` for RAG extraction

## Docker & Containerization

**Multi-Stage Build:**
- Stage 1 (builder): Node.js 22 Alpine + UV installation
  - Installs Python dependencies via `uv sync --frozen`
  - Installs Node dependencies via `npm ci`
  - Compiles TypeScript via `npm run build`

- Stage 2 (runtime): SuperGateway 3.4.3 base image
  - Copies compiled artifacts: `.venv/`, `dist/`, `node_modules/`, `lib/`
  - Sets up Python paths: `/app/.venv/bin`, `/app/python-bin/bin`
  - Exposes health endpoint: `/health`
  - Command: `--stdio node /app/dist/index.js` (stdio MCP wrapped via SuperGateway HTTP)

**Docker Compose:**
- Port mapping: 8000 → 8000 (HTTP)
- Health check: 30s interval, wget to `/health` endpoint
- Volume: `./downloads/` mounted for persistent book storage
- Environment: Loaded from `.env` file
- Restart policy: unless-stopped

## Configuration Files

**Key Configuration Files:**
- `tsconfig.json`: TypeScript compiler options (ES2022, strict, ESM)
- `jest.config.js`: Jest test runner configuration (ESM preset, moduleNameMapper)
- `pyproject.toml`: Python dependencies and UV configuration
- `package.json`: Node.js dependencies, npm scripts, exports
- `docker/Dockerfile`: Multi-stage containerization
- `docker/docker-compose.yaml`: Docker Compose orchestration

**Path Resolution Strategy:**
- Python scripts: Resolved at runtime from compiled `dist/lib/python-bridge.js`
- Navigation: `dist/lib/ → dist/ → project_root/ → lib/python_bridge.py`
- Helper module: `src/lib/paths.ts` provides `getPythonScriptPath()` for consistency

---

*Stack analysis: 2026-01-28*
