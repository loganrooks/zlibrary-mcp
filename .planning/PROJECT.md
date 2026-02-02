# Z-Library MCP — Project

## What This Is

An MCP server enabling AI assistants to search, download, and process books from Z-Library. The codebase was modernized in v1.0 with updated dependencies, decomposed Python architecture, EAPI transport layer, and comprehensive quality gates.

## Core Value

Reliable, maintainable MCP server for Z-Library book access — built on a clean foundation ready for feature development.

## Requirements

### Validated

- ✓ MCP server builds and runs — existing
- ✓ Search, download, and RAG processing functional — existing
- ✓ Retry logic with exponential backoff and circuit breaker — existing
- ✓ UV-based Python dependency management (v2.0.0) — existing
- ✓ Real PDF test corpus with ground truth validation — existing
- ✓ Comprehensive footnote system (continuation, corruption recovery) — existing
- ✓ Docker containerization — existing
- ✓ MCP protocol enhancements (outputSchema, structuredContent) — existing
- ✓ Advanced search with exact/fuzzy separation — existing
- ✓ Debug mode with verbose logging — existing
- ✓ HTTP connection pooling — existing
- ✓ Integration test harness (11 tools, recorded + live modes) — v1.0
- ✓ Docker E2E test with MCP SDK client — v1.0
- ✓ MCP SDK upgraded to 1.25.3 with McpServer class — v1.0
- ✓ Zod 3.25.x bridge + security audit (15 vulns fixed) — v1.0
- ✓ Python monolith decomposed (31 modules, backward-compatible facade) — v1.0
- ✓ Metadata tiering tool with include parameter — v1.0
- ✓ Enhanced filenames (author-title format) — v1.0
- ✓ Author/title fields in search results — v1.0
- ✓ EAPI JSON transport (bypasses Cloudflare) — v1.0
- ✓ Husky pre-commit hooks + GitHub Actions CI — v1.0
- ✓ All docs updated with Last Verified timestamps — v1.0

### Active

**Infrastructure Stability**
- [ ] Upgrade to Node 20+ (unlocks env-paths v4, modern features)
- [ ] Fill EAPI gaps (booklist browsing, full-text search alternatives)
- [ ] Remove AsyncZlib legacy download client (pure EAPI downloads)
- [ ] Fix Docker numpy/Alpine compilation issue

**Extraction Quality**
- [ ] Margin content detection & extraction (scholarly numbering, marginal notes, line numbers)
- [ ] Adaptive resolution pipeline (higher DPI for small text, footnotes, margin content)
- [ ] Body text purity (detect and separate all non-body content from markdown output)

**Expansion**
- [ ] Anna's Archive integration (research-first — fallback/alternative book source)

### Out of Scope

- Rewrite Python bridge in TypeScript — Python has better doc-processing libs
- ML-based text recovery — research task, not product scope
- OS keychain for credentials — security improvement for future milestone
- Push to 100% test coverage — 78-82% is healthy

## Current Milestone: v1.1 Quality & Expansion

**Goal:** Stabilize infrastructure (Node 20+, EAPI gaps, Docker), improve extraction quality for scholarly texts (margin content, adaptive resolution), and explore Anna's Archive as alternative source.

## Context

Shipped v1.0 with 45,231 LOC (TypeScript + Python).
Tech stack: Node.js/TypeScript MCP server, Python bridge, vendored zlibrary fork, EAPI JSON transport.
7 phases completed in 4 days: test harness → deps → SDK → decomposition → feature porting → docs → EAPI.
Known limitations: EAPI lacks booklist/full-text search endpoints (graceful degradation in place).
v1.1 focus: scholarly text extraction quality (Stephanus, Bekker, margin notes, line numbers) and infrastructure modernization.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Include get_metadata port | Valuable features never merged; 75 commits behind | ✓ Good — metadata, filenames, search fields shipped |
| Manual port over rebase | 75-commit drift makes rebase risky | ✓ Good — clean integration |
| Full scope (all audit recs) | User wanted everything addressed | ✓ Good — 28/28 requirements met |
| Zod 3.25.x bridge not full Zod 4 | Breaking changes too extensive | ✓ Good — stable, upgradeable later |
| McpServer class with server.tool() | Modern SDK pattern, cleaner than legacy Server | ✓ Good — simpler registration |
| Facade pattern for decomposition | Zero breakage to existing imports | ✓ Good — all tests passed unchanged |
| EAPI over HTML scraping | Cloudflare blocking all HTML requests | ✓ Good — restored full functionality |
| Keep AsyncZlib for downloads | EAPI download returns URL, needs legacy client | ⚠️ Revisit — technical debt |

## Constraints

- **No regressions**: All existing tests must continue passing
- **Incremental commits**: Each logical change committed separately
- **Test-first for refactoring**: Tests pass before and after each change

---
*Last updated: 2026-02-01 after v1.1 milestone start*
