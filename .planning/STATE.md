# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Bring the codebase to a clean, current, maintainable state so future feature development starts from a solid foundation
**Current focus:** Phase 7 (EAPI Migration) is URGENT — Cloudflare blocking all HTML requests, MCP server non-functional

## Current Position

Phase: 7 of 7 (EAPI Migration — URGENT)
Plan: 1 of 4 in current phase
Status: In progress
Last activity: 2026-02-01 — Completed 07-01-PLAN.md (EAPI Client Foundation)

Progress: [████████████░░░] ~80% (16/~20 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: 5.6 min
- Total execution time: 1.50 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 2/2 | 7 min | 3.5 min |
| 2 | 2/2 | 7.5 min | 3.75 min |
| 3 | 2/2 | 10 min | 5 min |
| 4 | 5/5 | 56 min | 11.2 min |
| 5 | 3/3 | ~15 min | ~5 min |
| 7 | 1/4 | ~4 min | ~4 min |

**Recent Trend:**
- Last 5 plans: ~4min, ~4min, ~4.5min, ~2min, ~4min
- Trend: Phase 7 started, EAPI client foundation complete

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 6-phase sequential cleanup following integration tests → deps → SDK → decomposition → porting → docs
- [Roadmap]: Re-implement get_metadata features (not rebase) due to 75-commit drift
- [01-01]: Use jest.unstable_mockModule for ESM mocking (required for ESM projects)
- [01-01]: BRK-001 marked "investigated, likely resolved" — code path exists, needs live test
- [01-02]: lib/ must be copied after uv sync in Docker to avoid setuptools package discovery conflicts
- [02-01]: MCP SDK vulnerability (1 high) deferred to Phase 3 — upgrade from 1.8 to 1.25+ breaks API
- [02-01]: requires-python bumped to >=3.10 (required by pdfminer.six security fix + ocrmypdf)
- [03-01]: Use server.tool() with Schema.shape for McpServer registration (ZodRawShape, not z.object())
- [03-01]: Preserve legacy toolRegistry export for test backward compat (cleaned in 03-02)
- [03-01]: Remove zod-to-json-schema — McpServer handles schema conversion internally
- [03-02]: Mock server.tool() calls to verify tool registration (McpServer API pattern)
- [03-02]: Tool count updated to 12 (including get_recent_books)
- [03-02]: Remove outputSchema assertions from tests (not in toolRegistry yet)
- [04-01]: _extract_publisher_from_front_matter placed in header.py, re-exported from detection/front_matter.py
- [04-01]: fitz import added to headings.py (was implicit in monolith scope)
- [04-02]: Facade-aware dependency access pattern for zero test modifications (submodules use _get_facade())
- [04-04]: footnotes.py split from 1175→115 lines via footnote_markers.py + footnote_core.py submodules
- [04-04]: pipeline.py reduced from 604→318 lines via ocr_stage.py extraction
- [04-05]: orchestrator.py reduced from 814→333 lines via orchestrator_pdf.py extraction
- [05-01]: Filter metadata in TypeScript (not Python) — enhanced_metadata.py already returns all fields
- [05-01]: Terms returned as flat strings (matches actual enhanced_metadata.py output)
- [05-02]: Derive title from name, author from authors[0] — additive enrichment
- [05-03]: self-modifying-system branch had only AI config (Roo/Cline), no app code — deleted without porting
- [07-01]: Lazy httpx client init with recreation on re-auth (fresh cookies after login)

### Pending Todos

None yet.

### Roadmap Evolution

- Phase 7 added: EAPI Migration — Cloudflare blocking all HTML requests, migrate to EAPI JSON endpoints (URGENT)

### Blockers/Concerns

- **ISSUE-API-001**: Z-Library Cloudflare bot protection blocking ALL HTML page requests — entire MCP server non-functional
- Phase 4: Production Docker build (docker/Dockerfile) has pre-existing numpy/Alpine compilation issue

## Session Continuity

Last session: 2026-02-01
Stopped at: Completed 07-01-PLAN.md (EAPI Client Foundation)
Resume file: None
