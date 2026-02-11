# Z-Library MCP Project Context

<!-- Last Verified: 2026-02-01 -->

## Mission Statement
Build a robust, resilient MCP server for Z-Library integration that provides comprehensive book search, download, and RAG processing capabilities for AI assistants, with emphasis on reliability despite Z-Library's infrastructure changes.

## Core Architecture Principles

### 1. Resilience First
- **Domain Agility**: Handle Z-Library's "Hydra mode" with dynamic domain discovery
- **Graceful Degradation**: Continue operating despite partial failures (e.g., booklist tools degrade when EAPI lacks endpoints)
- **Error Recovery**: Automatic retry with exponential backoff
- **Circuit Breakers**: Prevent cascading failures
- **EAPI Transport**: JSON API endpoints bypass Cloudflare browser challenges

### 2. Abstraction Layers
```
+---------------------+
|   MCP Interface     | <- 12 tools exposed to AI assistants (MCP SDK 1.25+)
+---------------------+
|   Service Layer     | <- Business logic, orchestration (TypeScript)
+---------------------+
|   EAPI Client       | <- Z-Library EAPI JSON transport (httpx)
+---------------------+
|   Python Bridge     | <- Language boundary (PythonShell)
+---------------------+
| Z-Library Client    | <- EAPIClient handles all operations
+---------------------+
| RAG Pipeline        | <- lib/rag/ domain modules (decomposed)
+---------------------+
```

### 3. Development Philosophy
- **Test-Driven**: Write tests first, especially for error paths
- **Observable**: Comprehensive logging and monitoring
- **Maintainable**: Clear separation of concerns, modules under 500 lines
- **Documented**: Self-documenting code with extensive comments

## Current State (2026-02-01)

### Working Features
- 12 MCP tools via McpServer `server.tool()` API (MCP SDK 1.25+)
- EAPI JSON transport for search, metadata, and browse operations
- Downloads via EAPIClient (handles URL resolution and file download)
- RAG processing (EPUB, TXT, PDF) with quality detection pipeline
- UV-based Python dependency management (.venv/ project-local)
- Python monolith decomposed into lib/rag/ domain modules with facade pattern
- Health check with Cloudflare detection for upstream monitoring

### Known Limitations
- Booklist tools gracefully degrade (no EAPI booklist endpoint)
- Full-text search routes through regular EAPI search (no dedicated mode)
- Terms, IPFS CIDs return empty defaults (not available via EAPI)
- Docker numpy/Alpine compilation issue (pre-existing)

### Future Direction
- **Anna's Archive**: Planned as additional/alternative book source to reduce Z-Library single-source risk
- **Source Diversification**: Architecture supports adding new backends behind the service layer

## Domain Model

### Core Entities
```typescript
interface Book {
  id: string;
  title: string;
  author: string;
  year: number;
  language: string;
  extension: string;
  size: number;
  hash: string;
  bookDetails?: BookDetails; // Required for download
}

interface BookDetails {
  downloadUrl: string;
  mirrorUrl: string;
  coverUrl?: string;
  description?: string;
  isbn?: string;
}

interface SearchParams {
  query: string;
  yearFrom?: number;
  yearTo?: number;
  languages?: Language[];
  extensions?: Extension[];
  limit?: number;
  page?: number;
}

interface RAGDocument {
  originalPath: string;
  processedPath: string;
  format: 'txt' | 'md' | 'json';
  metadata: DocumentMetadata;
  chunks?: TextChunk[];
}
```

## Technical Decisions

### Why Python Bridge?
- Z-Library community libraries are Python-based
- Better document processing libraries (PyMuPDF, ebooklib)
- Async support with asyncio
- EAPI client uses httpx for efficient HTTP

### Why Node.js Frontend?
- MCP SDK is Node.js-based (upgraded to 1.25+ with McpServer API)
- Better TypeScript support
- Standard for MCP servers

### Why Vendored Z-Library Fork?
- Need custom modifications for download logic
- Avoid breaking changes from upstream
- Control over authentication flow
- Custom EAPI client implementation (zlibrary/eapi.py)

### Why EAPI Transport?
- Cloudflare browser challenges block all HTML page requests (since Jan 2026)
- EAPI JSON endpoints bypass Cloudflare (API endpoints not challenged)
- Structured JSON responses eliminate HTML parsing fragility
- See ADR-005 for full rationale

### Why Python Decomposition?
- rag_processing.py was 4,968 lines (unmaintainable)
- Decomposed into lib/rag/ with domain modules all under 500 lines
- Facade pattern preserves backward compatibility (zero test modifications)
- See ADR-009 for full rationale

## Integration Points

### Upstream Dependencies
- `sertraline/zlibrary` - Base Python library (vendored fork with EAPI client)
- `@modelcontextprotocol/sdk` ^1.25.3 - MCP protocol (McpServer API)
- `python-shell` - Node.js to Python bridge

### Downstream Consumers
- Claude Code (primary)
- RooCode
- Cline
- Other MCP-compatible AI assistants

## Development Workflow

### Standard Flow
1. **Planning**: Review ISSUES.md, check current TODOs
2. **Implementation**: Follow patterns in PATTERNS.md
3. **Testing**: Unit (Jest/Pytest) -> Integration -> E2E
4. **Documentation**: Update relevant docs
5. **Review**: Check against DEBUGGING.md scenarios

### Branch Strategy
- `master` - Stable, production-ready (primary branch)
- `feature/*` - New features
- `fix/*` - Bug fixes
- `hotfix/*` - Emergency production fixes
- `docs/*` - Documentation only

**Note**: See `.claude/VERSION_CONTROL.md` for comprehensive Git workflow guide.

### Commit Convention
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: feat, fix, docs, style, refactor, test, chore

## Performance Targets

### Response Times
- Search: < 2s average, < 5s p99
- Download initiation: < 1s
- RAG processing: < 10s for 10MB document

### Reliability
- Uptime: 99.9% (excluding Z-Library downtime)
- Success rate: > 95% for valid requests
- Retry success: > 80% after transient failures

## Environment Variables

```bash
# Required
ZLIBRARY_EMAIL=
ZLIBRARY_PASSWORD=

# Optional
ZLIBRARY_MIRROR=
LOG_LEVEL=debug|info|warn|error
DOWNLOAD_DIR=./downloads
PROCESSED_DIR=./processed_rag_output
ZLIBRARY_DEBUG=1  # Enable verbose logging

# Retry configuration
RETRY_MAX_RETRIES=3
RETRY_INITIAL_DELAY=1000
RETRY_MAX_DELAY=30000
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60000
```

## Quick Commands

```bash
# Setup
bash setup-uv.sh        # UV-based Python setup
npm install              # Node.js deps
npm run build            # Build TypeScript

# Testing
npm test                 # All tests (Jest + Pytest)
uv run pytest            # Python tests only

# Running
node dist/index.js       # Start MCP server

# Debugging
ZLIBRARY_DEBUG=1 node dist/index.js  # Verbose mode
```

---

*This document is the source of truth for project context. Update when making architectural decisions.*
