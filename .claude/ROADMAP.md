# Project Roadmap

<!-- Last Verified: 2026-02-01 -->

**Last Updated**: 2026-02-01
**Status**: All cleanup phases complete. Codebase modernized and stable.

---

## Completed Cleanup Phases (Jan-Feb 2026)

A comprehensive 7-phase cleanup was executed to modernize the codebase, resolve critical issues, and establish a solid foundation for future development.

| Phase | Name | Plans | Completed | Key Outcomes |
|-------|------|-------|-----------|--------------|
| 1 | Integration Tests & Smoke Tests | 2 | 2026-01-29 | ESM mock patterns, Docker lib/ copy fix |
| 2 | Low-Risk Dependency Upgrades | 2 | 2026-01-29 | pip-audit clean, requires-python >=3.10 |
| 3 | MCP SDK Upgrade | 2 | 2026-01-30 | SDK 1.8 to 1.25+, McpServer API, removed zod-to-json-schema |
| 4 | Python Monolith Decomposition | 5 | 2026-01-31 | rag_processing.py split into lib/rag/ domain modules, all <500 lines |
| 5 | Feature Porting & Branch Cleanup | 3 | 2026-01-31 | Metadata/author/term tools ported, stale branches deleted |
| 6 | Documentation & Quality Gates | 2 | 2026-02-01 | Docs updated, ADRs backfilled, issues triaged |
| 7 | EAPI Migration | 6 | 2026-02-01 | All API calls via EAPI JSON, Cloudflare bypassed, health checks added |

**Total**: 22 plans executed across 7 phases.

---

## Current State

### What Works
- 12 MCP tools registered via McpServer `server.tool()` API
- EAPI JSON transport for all search/metadata operations (bypasses Cloudflare)
- Downloads via legacy AsyncZlib client (EAPI returns URL, file download needs cookies)
- RAG pipeline: EPUB, TXT, PDF extraction with quality detection
- UV-based Python dependency management (.venv/ project-local)
- Python monolith decomposed into lib/rag/ domain modules with facade pattern

### Known Limitations
- Booklist tools gracefully degrade (no EAPI booklist endpoint)
- Full-text search routes through regular EAPI search (no full-text mode)
- Terms, IPFS CIDs return empty defaults (not available via EAPI)
- Docker numpy/Alpine compilation issue (pre-existing)

---

## Future Direction

### Near-Term Opportunities
- [ ] Anna's Archive integration (broader book source coverage)
- [ ] Result caching layer (search results and metadata)
- [ ] Download queue management (DL-001)
- [ ] Performance profiling tools

### Medium-Term Features
- [ ] Semantic chunking for RAG (RAG-001)
- [ ] Multi-format support (MOBI, AZW3, DJVU)
- [ ] ML-based text recovery (sous-rature under X-marks)
- [ ] Adaptive resolution pipeline (72/150/300 DPI)

### Long-Term Vision
- [ ] Anna's Archive as primary source (Z-Library as fallback)
- [ ] Distributed architecture for scale
- [ ] Advanced caching and recommendation strategies

---

## Strategic Priorities

1. **Stability First**: Maintain working EAPI transport, monitor upstream changes
2. **Quality Pipeline**: Continue RAG improvements with real PDF TDD
3. **Source Diversification**: Anna's Archive reduces single-source risk
4. **Developer Experience**: Documentation, testing, tooling improvements

---

**Quick Links**:
- [Current Issues](../ISSUES.md) - Detailed issue tracking
- [Architecture Overview](ARCHITECTURE.md) - System structure
- [TDD Workflow](TDD_WORKFLOW.md) - Development process
- [Patterns](PATTERNS.md) - Code patterns to follow
