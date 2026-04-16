# Z-Library MCP — Project

## What This Is

An MCP server enabling AI assistants to search, download, and process books from Z-Library with scholarly text extraction (margin detection, adaptive DPI, body text purity), and Anna's Archive as alternative source with LibGen fallback. Built on Node 22 LTS with modernized dependencies, decomposed Python architecture, and EAPI JSON transport.

## Core Value

Reliable, maintainable MCP server for book access — production-ready infrastructure with high-quality scholarly text extraction.

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
- ✓ Node 22 LTS with env-paths v4 (pure ESM) — v1.1
- ✓ AsyncZlib removed, pure EAPIClient downloads — v1.1
- ✓ Docker builds fixed (opencv-python-headless) — v1.1
- ✓ EAPI booklist/full-text search improved fallbacks — v1.1
- ✓ Margin detection (Stephanus, Bekker, line numbers, marginal notes) — v1.1
- ✓ Adaptive DPI pipeline (150-400 based on content) — v1.1
- ✓ Region-level re-rendering for footnotes/margins — v1.1
- ✓ Unified body text purity pipeline with confidence scoring — v1.1
- ✓ Multi-file output (body.md + _meta.json) — v1.1
- ✓ Recall regression tests (34/34 pass) — v1.1
- ✓ Anna's Archive adapter (HTML scraping search + fast download API) — v1.1
- ✓ LibGen fallback adapter with rate limiting — v1.1
- ✓ Source router with auto selection and quota-based fallback — v1.1
- ✓ Test taxonomy, v3 ground truth schema, and fast/full CI split — v1.2
- ✓ ESLint + Prettier + lint-staged enforcement — v1.2
- ✓ Startup credential validation and baseline coverage gates — v1.2
- ✓ Public docs refresh (README, API docs, CONTRIBUTING, CHANGELOG) — v1.2
- ✓ npm packaging, Docker distribution, and tag-triggered release workflow — v1.2
- ✓ Post-release CI stabilization and dependency pinning — quick-004 / quick-005

### Active

#### Current Milestone: v1.3 RAG Pipeline Refinement

**Goal:** Normalize the structured RAG output contract and add automated quality scoring now that the production-readiness milestone is shipped and `v1.2.0` is tagged.

- [ ] Structured RAG output contract for `process_document_for_rag` and `download_book_to_file`
- [ ] Dedicated `body`, `footnotes`, and metadata outputs with unified linking
- [ ] Automated quality scoring against ground truth with machine-readable reports
- [ ] CI regression reporting for quality metrics with non-breaking rollout
- [ ] Revisit whether `page_analysis_map` should feed the quality reporting pipeline

### Out of Scope

- Rewrite Python bridge in TypeScript — Python has better doc-processing libs
- ML-based text recovery — research task, not product scope
- Push to 100% test coverage — 78-82% is healthy
- Full Zod 4 migration — Zod 3.25.x bridge works, defer until breaking changes resolved
- Anna's Archive slow downloads — blocked by DDoS-Guard, requires Playwright

## Current State

Shipped v1.2 Production Readiness across phases 13-18 and released `v1.2.0` on 2026-04-02. Post-release quick tasks on 2026-03-20 and 2026-03-27 closed the remaining audit debt and restored green CI before the release tag.

**Tech stack:**
- Node 22 LTS with TypeScript MCP server
- Python bridge with 31 decomposed modules
- Vendored zlibrary fork with EAPI JSON transport
- RAG pipeline with margin detection, adaptive DPI, unified body text purity
- Multi-source support (Z-Library + Anna's Archive + LibGen fallback)

**Key capabilities:**
- 13 documented MCP tools for search, download, metadata, and RAG processing
- Scholarly text extraction (Stephanus, Bekker, line numbers, marginal notes)
- Automatic DPI selection (150-400) with region re-rendering
- Body text purity with 6 detectors, confidence scoring, multi-file output
- Anna's Archive integration with quota-based LibGen fallback

**Planning state:** v1.3 is initialized with phases 19-21. Phase 19 now has research plus 2 execution plans under `.planning/phases/19-structured-rag-output-contract/`, and the next workflow step is `$gsdr-execute-phase 19`.

**Scope cleanup:** `search_multi_source` is already an exposed MCP tool in the server, tests, and public docs, so v1.3 does not spend milestone scope on promoting it.

**v1.2 delivery:** 6 phases, 16 plans, 99 milestone commits, plus quick-004, quick-005, and the `v1.2.0` release tag.

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
| Node 22 LTS (not Node 20) | Unlocks pure ESM deps, LTS until Apr 2027 | ✓ Good — modern runtime |
| opencv-python-headless | No GUI deps, pre-built Alpine wheels | ✓ Good — Docker builds fixed |
| AsyncZlib removal | Technical debt from hybrid download path | ✓ Good — clean EAPI-only downloads |
| Bekker regex before Stephanus | More specific pattern prevents ambiguity | ✓ Good — correct scholarly citations |
| Block midpoint for margin zone | Statistical approach, no hardcoded widths | ✓ Good — adapts to all layouts |
| Compositor recall bias to BODY | Unclaimed/low-confidence defaults safe | ✓ Good — no body text loss |
| Anna's domain_index=1 | domain_index=0 has SSL errors | ✓ Good — fast downloads work |
| LibGen as fallback only | Anna's has API key with quota | ✓ Good — quota-based fallback |
| Keep v1.3 response changes additive | `process_document_for_rag` and `download_book_to_file` already have tests and consumers expecting current path fields | — Pending |
| Treat `search_multi_source` as shipped scope | Tool is already registered, tested, and documented, so milestone time should go to RAG quality internals instead | ✓ Good — resolved during v1.3 initialization |

## Constraints

- **No regressions**: All existing tests must continue passing
- **Incremental commits**: Each logical change committed separately
- **Test-first for refactoring**: Tests pass before and after each change
- **Recall preservation**: No body text lost by unified pipeline
- **Compatibility**: `process_document_for_rag` and `download_book_to_file` response shapes must remain additive for existing MCP clients

---
*Last updated: 2026-04-16 after starting milestone v1.3*
