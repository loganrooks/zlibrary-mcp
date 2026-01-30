# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Bring the codebase to a clean, current, maintainable state so future feature development starts from a solid foundation
**Current focus:** Phase 3 in progress — MCP SDK upgrade

## Current Position

Phase: 3 of 6 (MCP SDK Upgrade)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-01-30 — Completed 03-01-PLAN.md

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 4.3 min
- Total execution time: 0.36 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 2/2 | 7 min | 3.5 min |
| 2 | 2/2 | 7.5 min | 3.75 min |
| 3 | 1/2 | 8 min | 8 min |

**Recent Trend:**
- Last 5 plans: 4min, 2min, 5.5min, 8min
- Trend: slight increase (SDK rewrite more complex)

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3 plan 03-02: Tests need updating for McpServer API (toolRegistry export preserved for compat)
- Phase 4 (Python Decomposition): MEDIUM risk — Footnote module granularity (700 lines vs 500 target)

## Session Continuity

Last session: 2026-01-30
Stopped at: Completed 03-01-PLAN.md (MCP SDK upgrade + index.ts rewrite)
Resume file: None
