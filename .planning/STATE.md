# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-01)

**Core value:** Reliable, maintainable MCP server for Z-Library book access
**Current focus:** v1.1 Quality & Expansion — Phase 10 complete

## Current Position

Phase: 10 of 12 (Adaptive Resolution)
Plan: 4 of 4 in current phase (gap closure)
Status: Phase complete (all verification criteria satisfied)
Last activity: 2026-02-02 — Completed 10-04-PLAN.md (Region Re-Rendering Wiring)

Progress: [██████████░░░░░░] 91% (10/11 v1.1 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 31 (22 v1.0 + 9 v1.1)
- v1.1 plans completed: 10
- Total execution time: ~4 days (v1.0)

**By Phase:** (v1.1)

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 08 | 3/3 | ~13min | ~4.3min |
| 09 | 3/3 | ~12min | ~4min |
| 10 | 4/4 | ~14min | ~3.5min |

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
- MARG-FOOTNOTE-DEDUP-DEFERRED: Footnote bboxes not passed to detect_margin_content yet; deferred to Phase 11
- RES-DPI-FLOOR-72: DPI floor is 72 (not quantized to 50) — preserves minimum rendering quality
- RES-MATRIX-RENDER: Use fitz.Matrix(dpi/72, dpi/72) for rendering instead of deprecated dpi= parameter
- RES-ADAPTIVE-DEFAULT: Adaptive DPI is default behavior (no opt-in flag); scanned PDFs auto-fallback to 300
- RES-OPTIONAL-PARAM: page_dpi_map added as optional param with None default for backward compatibility
- RES-ANALYSIS-MAP: page_dpi_map upgraded to page_analysis_map (Dict[int, PageAnalysis]) to carry region info

### Pending Todos

None.

### Blockers/Concerns

- ~~Docker numpy/Alpine compilation issue~~ RESOLVED in 08-03 (opencv-python-headless)
- ~~EAPI lacks booklist/full-text search endpoints~~ MITIGATED in 08-03 (enriched fallbacks)
- ~~AsyncZlib removal must have integration test BEFORE swap (pitfall P-01)~~ RESOLVED in 08-02
- ~~Margin detection must annotate-don't-remove to avoid breaking footnote pipeline (pitfall P-06)~~ IMPLEMENTED in 09-02 (bbox exclusion, annotations not removal)
- Anna's Archive API contract unknown — research spike required before implementation (Phase 12)
- Pre-existing: paths.test.js has 1 failing test (requirements.txt removed in UV migration)
- Pre-existing: 2 pytest collection errors in scripts/ (import issues)

## Session Continuity

Last session: 2026-02-02
Stopped at: Completed 10-04-PLAN.md (Region Re-Rendering Wiring) — Phase 10 fully complete (3/3 verification)
Resume file: None
