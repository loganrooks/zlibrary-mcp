# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-01)

**Core value:** Reliable, maintainable MCP server for Z-Library book access
**Current focus:** v1.1 Quality & Expansion — COMPLETE

## Current Position

Phase: 12 of 12 (Anna's Archive Integration)
Plan: 4 of 4 complete (12-01, 12-02, 12-03, 12-04)
Status: Phase 12 COMPLETE - v1.1 COMPLETE
Last activity: 2026-02-03 — Completed 12-04-PLAN.md (Source router)

Progress: [████████████████████] 100% (22/22 v1.1 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 44 (22 v1.0 + 22 v1.1)
- v1.1 plans completed: 22
- Total execution time: ~4 days (v1.0)

**By Phase:** (v1.1)

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 08 | 3/3 | ~13min | ~4.3min |
| 09 | 3/3 | ~12min | ~4min |
| 10 | 4/4 | ~14min | ~3.5min |
| 11 | 7/7 | ~60min | ~8.5min |
| 12 | 4/4 | ~11.5min | ~2.9min |

## Accumulated Context

### Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.
v1.1 decisions:
- INFRA-05/06 (EAPI gaps) grouped with infrastructure phase, not separate phase
- Phase 10 (adaptive DPI) sequenced after Phase 9 for focus, though technically independent
- Phase 12 (Anna's Archive) last due to highest uncertainty and legal risk
- INFRA-NODE22: Set engines >=22 (Node 22 LTS active until Apr 2027)
- INFRA-ENVPATHS4: Upgrade env-paths v3 to v4 (pure ESM, no API changes)
- INFRA-TYPES-NODE22: Upgrade @types/node from ^18 to ^22
- INFRA-OPENCV-HEADLESS: Use opencv-python-headless (no GUI deps, pre-built wheels)
- INFRA-DOCKER-SLIM: Remove gcc/python3-dev from Dockerfile.test
- INFRA-ASYNCZLIB-REMOVED: Downloads rewired from AsyncZlib to EAPIClient.download_file
- INFRA-ADVANCED-SEARCH-DEPRECATED: search_books_advanced raises NotImplementedError (no EAPI equivalent)
- INFRA-RUFF-E402: Added ruff config ignoring E402/E741 globally (pre-existing sys.path issues)
- MARG-BEKKER-FIRST: Check Bekker regex before Stephanus (more specific pattern prevents ambiguity)
- MARG-MIDPOINT-ZONE: Use block midpoint for margin-left vs margin-right classification
- MARG-CACHE-COMPAT: Block bboxes identical between get_text("dict") and get_text("dict", flags=TEXTFLAGS_DICT)
- MARG-FOOTNOTE-DEDUP-RESOLVED: Footnote bboxes now flow to margins via pipeline context (resolved in 11-03)
- RES-DPI-FLOOR-72: DPI floor is 72 (not quantized to 50) — preserves minimum rendering quality
- RES-MATRIX-RENDER: Use fitz.Matrix(dpi/72, dpi/72) for rendering instead of deprecated dpi= parameter
- RES-ADAPTIVE-DEFAULT: Adaptive DPI is default behavior (no opt-in flag); scanned PDFs auto-fallback to 300
- RES-OPTIONAL-PARAM: page_dpi_map added as optional param with None default for backward compatibility
- RES-ANALYSIS-MAP: page_dpi_map upgraded to page_analysis_map (Dict[int, PageAnalysis]) to carry region info
- PIPELINE-MODELS-STDLIB: Pipeline foundation types use stdlib only (dataclasses, enum, typing, pathlib, json)
- REGISTRY-SIMPLE-DICT: Simple dict registry with decorator pattern (no config files or dynamic loading)
- RECALL-STRUCTURAL-FILTER: Filter TOC/navigation lines from recall comparison (non-deterministic between runs)
- COMPOSITOR-RECALL-BIAS: Unclaimed blocks and low-confidence claims (<0.6) default to BODY
- COMPOSITOR-TYPE-PRIORITY: Footnote > Endnote > Margin > PageNumber > Header > Footer > TOC > FrontMatter > Citation > Heading > Body
- COMPOSITOR-OVERLAP-THRESHOLD: 50% bbox overlap threshold to consider two bboxes as same block
- PIPELINE-LAZY-IMPORT: Used __getattr__ lazy import in pipeline __init__.py to avoid circular import with detection registry
- WRITER-PAGE-BREAK: Pages separated by double newline in body text (no explicit --- separator)
- WRITER-MARGIN-APPEND: Margin annotations appended at end of their page's body text block
- ORCHESTRATOR-NOQA: Added noqa markers to ~25 re-exported imports in orchestrator.py (facade pattern API surface)
- TEST-SMALLEST-PDF: Used heidegger_pages_22-23 (smallest scholarly PDF) for integration tests — fast execution
- ANNAS-DOMAIN-INDEX-1: Use domain_index=1 for Anna's Archive fast download API (domain_index=0 has SSL errors)
- ANNAS-SCRAPE-SEARCH: Anna's Archive search via HTML scraping (no search API exists)
- ANNAS-NO-SLOW-DOWNLOAD: Do not implement slow downloads (blocked by DDoS-Guard, requires Playwright)
- LIBGEN-IMPORT: Import as `from libgen_api_enhanced import LibgenSearch` (not libgen_api)
- LIBGEN-ASYNC-THREAD: Wrap LibGen sync calls in asyncio.to_thread()
- SOURCE-ANNAS-PRIMARY: Anna's Archive is primary source (user has API key with 25/day quota)
- SOURCE-LIBGEN-FALLBACK: LibGen is fallback when Anna's quota exhausted or unavailable
- LIBGEN-RATE-LIMIT: 2.0s MIN_REQUEST_INTERVAL to avoid server blocks
- ROUTER-AUTO-SOURCE: Auto mode uses Anna's if ANNAS_SECRET_KEY set, else LibGen
- ROUTER-LAZY-INIT: Adapters created only when first needed
- ROUTER-QUOTA-FALLBACK: Zero downloads_left triggers fallback to LibGen

### Pending Todos

None.

### Blockers/Concerns

- ~~Docker numpy/Alpine compilation issue~~ RESOLVED in 08-03 (opencv-python-headless)
- ~~EAPI lacks booklist/full-text search endpoints~~ MITIGATED in 08-03 (enriched fallbacks)
- ~~AsyncZlib removal must have integration test BEFORE swap (pitfall P-01)~~ RESOLVED in 08-02
- ~~Margin detection must annotate-don't-remove to avoid breaking footnote pipeline (pitfall P-06)~~ IMPLEMENTED in 09-02 (bbox exclusion, annotations not removal)
- ~~Anna's Archive API contract unknown~~ RESOLVED in Phase 12 experiments (API works with domain_index=1)
- Pre-existing: paths.test.js has 1 failing test (requirements.txt removed in UV migration)
- Pre-existing: 2 pytest collection errors in scripts/ (import issues)

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 12-04-PLAN.md (Source router) - v1.1 COMPLETE
Resume with: N/A - v1.1 roadmap complete
Key files created in Phase 12:
- `lib/sources/__init__.py` — package exports
- `lib/sources/models.py` — UnifiedBookResult, DownloadResult, QuotaInfo, SourceType
- `lib/sources/config.py` — SourceConfig, get_source_config()
- `lib/sources/base.py` — SourceAdapter ABC
- `lib/sources/annas.py` — AnnasArchiveAdapter with HTML search and fast download API
- `lib/sources/libgen.py` — LibgenAdapter with async search/download
- `lib/sources/router.py` — SourceRouter with fallback logic
- `__tests__/python/test_source_router.py` — Router integration tests

## v1.1 Completion Summary

All 5 phases of v1.1 roadmap complete:
- Phase 08: Infrastructure Modernization (3/3 plans)
- Phase 09: Margin Detection (3/3 plans)
- Phase 10: Adaptive Resolution (4/4 plans)
- Phase 11: Pipeline Integration (7/7 plans)
- Phase 12: Anna's Archive Integration (4/4 plans)

Total: 22 plans executed, ~110.5 minutes total execution time.
