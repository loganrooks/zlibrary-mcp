# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Bring the codebase to a clean, current, maintainable state so future feature development starts from a solid foundation
**Current focus:** Phase 4 complete — ready for Phase 5

## Current Position

Phase: 4 of 6 (Python Monolith Decomposition) — COMPLETE ✓
Plan: 5 of 5 in current phase
Status: Phase verified and complete
Last activity: 2026-02-01 — Phase 4 verified (7/7 must-haves passed)

Progress: [█████████░] 90%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 6.5 min
- Total execution time: 1.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 2/2 | 7 min | 3.5 min |
| 2 | 2/2 | 7.5 min | 3.75 min |
| 3 | 2/2 | 10 min | 5 min |
| 4 | 5/5 | 56 min | 11.2 min |

**Recent Trend:**
- Last 5 plans: 14min, 22min, 8min, 9min, 3min
- Trend: Gap closure plans were fast (well-scoped extractions)

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 4: Production Docker build (docker/Dockerfile) has pre-existing numpy/Alpine compilation issue

## Session Continuity

Last session: 2026-02-01
Stopped at: Phase 4 complete and verified (7/7 must-haves)
Resume file: None
