# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-01)

**Core value:** Reliable, maintainable MCP server for Z-Library book access
**Current focus:** v1.1 Quality & Expansion — Phase 11 in progress

## Current Position

Phase: 11 of 12 (Body Text Purity)
Plan: 6 of 7 in current phase (orchestrator integration done)
Status: In progress
Last activity: 2026-02-03 — Completed 11-06-PLAN.md (Orchestrator Integration)

Progress: [██████████████░░] 94% (17/18 v1.1 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 38 (22 v1.0 + 16 v1.1)
- v1.1 plans completed: 17
- Total execution time: ~4 days (v1.0)

**By Phase:** (v1.1)

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 08 | 3/3 | ~13min | ~4.3min |
| 09 | 3/3 | ~12min | ~4min |
| 10 | 4/4 | ~14min | ~3.5min |
| 11 | 6/7 | ~35min | ~6min |

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

Last session: 2026-02-03
Stopped at: Completed 11-06-PLAN.md (Orchestrator Integration)
Resume file: None
