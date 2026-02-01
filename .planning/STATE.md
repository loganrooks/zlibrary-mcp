# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Bring the codebase to a clean, current, maintainable state so future feature development starts from a solid foundation
**Current focus:** Phase 4 in progress — Python monolith decomposition

## Current Position

Phase: 4 of 6 (Python Monolith Decomposition)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-01 — Completed 04-01-PLAN.md

Progress: [███████░░░] 70%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 5.2 min
- Total execution time: 0.6 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 2/2 | 7 min | 3.5 min |
| 2 | 2/2 | 7.5 min | 3.75 min |
| 3 | 2/2 | 10 min | 5 min |
| 4 | 1/2 | 14 min | 14 min |

**Recent Trend:**
- Last 5 plans: 5.5min, 8min, 2min, 14min
- Trend: Phase 4 plan 1 took longer (4968-line file decomposition)

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
- [04-01]: footnotes.py is 1176 lines (exceeds 700 target) — further splitting in 04-03
- [04-01]: fitz import added to headings.py (was implicit in monolith scope)

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 4: footnotes.py at 1176 lines (target was 700) — splitting deferred to 04-03

## Session Continuity

Last session: 2026-02-01
Stopped at: Completed 04-01-PLAN.md (leaf-node module extraction)
Resume file: None
