# Z-Library MCP Project Context

## Mission Statement
Build a robust, resilient MCP server for Z-Library integration that provides comprehensive book search, download, and RAG processing capabilities for AI assistants, with emphasis on reliability despite Z-Library's infrastructure changes.

## Core Architecture Principles

### 1. Resilience First
- **Domain Agility**: Handle Z-Library's "Hydra mode" with dynamic domain discovery
- **Graceful Degradation**: Continue operating despite partial failures
- **Error Recovery**: Automatic retry with exponential backoff
- **Circuit Breakers**: Prevent cascading failures

### 2. Abstraction Layers
```
┌─────────────────────┐
│   MCP Interface     │ ← Tools exposed to AI assistants
├─────────────────────┤
│   Service Layer     │ ← Business logic, orchestration
├─────────────────────┤
│   Adapter Layer     │ ← Z-Library EAPI abstraction
├─────────────────────┤
│   Python Bridge     │ ← Language boundary
├─────────────────────┤
│   Z-Library Client  │ ← Direct API interaction
└─────────────────────┘
```

### 3. Development Philosophy
- **Test-Driven**: Write tests first, especially for error paths
- **Observable**: Comprehensive logging and monitoring
- **Maintainable**: Clear separation of concerns
- **Documented**: Self-documenting code with extensive comments

## Current State (2025-09-30)

### Working Features ✅
- Basic search functionality
- Book downloads with bookDetails
- RAG processing (EPUB, TXT, PDF)
- Python virtual environment management

### Known Issues ⚠️
- Venv manager test warnings (ISSUE-002)
- No retry logic for failures (ISSUE-005)
- Missing fuzzy search (SRCH-001)
- No download queue management (DL-001)

### In Progress 🔄
- Branch: `feature/rag-robustness-enhancement`
- Focus: PDF quality analysis and extraction improvements

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
- Easier web scraping with BeautifulSoup

### Why Node.js Frontend?
- MCP SDK is Node.js-based
- Better TypeScript support
- Easier integration with AI assistants
- Standard for MCP servers

### Why Vendored Z-Library Fork?
- Need custom modifications for download logic
- Avoid breaking changes from upstream
- Control over authentication flow
- Custom domain handling for Hydra mode

## Integration Points

### Upstream Dependencies
- `sertraline/zlibrary` - Base Python library (vendored fork)
- `@modelcontextprotocol/sdk` - MCP protocol implementation
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
3. **Testing**: Unit → Integration → E2E
4. **Documentation**: Update relevant docs
5. **Review**: Check against DEBUGGING.md scenarios

### Branch Strategy
- `main` - Stable, production-ready
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation only

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

### Scale
- Concurrent requests: 10
- Daily downloads: 1000 (respecting limits)
- Cache hit rate: > 50%

## Security Considerations

### Credential Management
- Store in environment variables
- Never log credentials
- Rotate on compromise
- Use token-based auth where possible

### Data Privacy
- No user data persistence without consent
- Sanitize logs of personal information
- Encrypted storage for sensitive data
- Clear session data on logout

## Future Vision

### Phase 1: Stabilization (Current)
- Fix critical issues
- Add retry logic
- Improve error handling

### Phase 2: Enhancement (Next)
- Fuzzy search
- Download queue
- Advanced RAG features

### Phase 3: Scale (Future)
- Distributed architecture
- Multiple Z-Library account support
- Advanced caching strategies
- ML-based recommendations

## Key Metrics to Track

### Operational
- Request success/failure rates
- Average response times
- Domain availability
- Error frequencies by type

### Business
- Daily active users
- Books downloaded
- Search queries processed
- RAG documents generated

### Technical
- Memory usage
- CPU utilization
- Network bandwidth
- Cache effectiveness

## Support Channels

### Documentation
- CLAUDE.md - Quick start for Claude Code
- ISSUES.md - Known problems and solutions
- PATTERNS.md - Code patterns and examples
- DEBUGGING.md - Troubleshooting guide

### Monitoring
- Logs: `./logs/` directory
- Metrics: Prometheus-compatible
- Alerts: Error rate thresholds

## Environment Variables

```bash
# Required
ZLIBRARY_EMAIL=
ZLIBRARY_PASSWORD=

# Optional
ZLIBRARY_MIRROR=
LOG_LEVEL=debug|info|warn|error
CACHE_DIR=./cache
DOWNLOAD_DIR=./downloads
PROCESSED_DIR=./processed_rag_output
MAX_RETRIES=3
RETRY_DELAY_MS=1000
```

## Quick Commands

```bash
# Development
npm run dev          # Start with hot reload
npm test            # Run all tests
npm run test:watch  # Test with watch mode

# Python
source venv/bin/activate
pytest              # Run Python tests
python -m lib.python_bridge test  # Test bridge

# Debugging
npm run debug       # Start with debugger
npm run logs        # Tail logs
npm run clean       # Clean temp files
```

---

*This document is the source of truth for project context. Update when making architectural decisions.*