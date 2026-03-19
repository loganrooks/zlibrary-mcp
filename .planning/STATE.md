# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** Reliable, maintainable MCP server for book access — production-ready infrastructure with high-quality scholarly text extraction
**Current focus:** v1.2 Production Readiness — Phase 15: Cleanup & DX Foundation

## Current Position

Phase: 15 of 17 (Cleanup & DX Foundation) -- NOT STARTED
Plan: none yet
Status: Roadmap updated, ready to plan Phase 15
Last activity: 2026-03-19 — v1.2 scope deliberation + credential scrub from git history

Progress: [████████░░░░░░░░░░░░] 40% of v1.2 (phases 13-14 complete, 15-17 remaining)

## Milestones Shipped

| Version | Name | Phases | Plans | Shipped |
|---------|------|--------|-------|---------|
| v1.0 | Audit Cleanup & Modernization | 1-7 | 22 | 2026-02-01 |
| v1.1 | Quality & Expansion | 8-12 | 21 | 2026-02-04 |

**Total:** 12 phases, 43 plans executed (+ 2 plans in phase 13, 3 plans in phase 14)

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

**2026-03-19 (Deliberation):**
- v1.2 scope narrowed to 3 infrastructure phases (15-17), deferring RAG refinements to v1.3
- Both npm and Docker are first-class distribution channels
- All three quality gate layers required: CI regression, package integrity, doc freshness
- Credential scrub completed — password removed from all git history via filter-repo + force-push
- Commit message sanitized (removed "scrub credentials" language)
- GitHub Issue #11 identified as key validation target for Phase 17

**Phase 14:**
- Used addopts = --strict-markers instead of strict_markers = true (pytest 8.x compatibility)
- Kept existing class-level @pytest.mark decorators alongside module-level pytestmark (safe redundancy)
- Converted test_real_zlibrary.py pytestmark from skipif-only to list with integration + skipif
- Removed null corrupted_extraction from heidegger xmark data (invalid per v3 schema, field is optional)
- Used git mv for all script relocations to preserve file history
- test-fast runs on both push and PR; test-full only on push-to-master and manual dispatch
- Added --benchmark-disable to fast CI job to skip pytest-benchmark overhead

**Phase 13:**
- Used Extension (not AsyncZlib) as the canonical zlibrary import check
- Rewrote TestRealAuthentication with EAPIClient domain-based constructor
- Replaced getRequirementsTxtPath with getPyprojectTomlPath to match UV migration
- Wrapped lint-staged tsc in bash -c to prevent file argument pass-through

### Pending Todos

None.

### Blockers/Concerns

**Current:**
- 1 Jest test failing (Node 22 JSON.parse error message format change) — DX-05, will fix in Phase 15
- Large blob (74MB Kant PDF) in git history under test_downloads/ — CLEAN-05, will purge in Phase 15
- 5 compiled .js files in src/lib/ appearing as untracked — CLEAN-02/CLEAN-03, will fix in Phase 15

**Pre-existing (from v1.1, all resolved by phase 13):**
- ~~paths.test.js has 1 failing test (BUG-01)~~ RESOLVED by 13-01
- ~~2 pytest collection errors in scripts/ (BUG-02)~~ RESOLVED by 13-01
- ~~Unregistered pytest markers (BUG-03)~~ RESOLVED by 13-01
- ~~Deprecated AsyncZlib code still present (BUG-04)~~ RESOLVED by 13-02
- ~~zlib_client fixture missing from integration tests~~ RESOLVED by quick-003
- ~~booklist_tools.py discover_eapi_domain() missing argument~~ RESOLVED by quick-003

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 003 | Fix zlib_client fixture + booklist_tools discover_eapi_domain bug | 2026-02-11 | 69c7d5b | [003-fix-zlib-client-fixture](./quick/003-fix-zlib-client-fixture/) |

### Tech Debt Inventory

From v1.1 audit (addressed by v1.2 scope):
- Quality pipeline doesn't receive page_analysis_map (acceptable — only OCRs small regions)
- search_multi_source not yet wired as MCP tool (Python bridge ready, TypeScript pending — out of v1.2 scope)

## Session Continuity

Last session: 2026-03-19
Stopped at: Roadmap + requirements updated for new v1.2 scope. Ready to plan Phase 15.
Resume with: `/gsdr:plan-phase 15`

### Performance Metrics

| Phase-Plan | Duration | Tasks | Files |
|------------|----------|-------|-------|
| 13-01      | 20min    | 2     | 6     |
| 13-02      | 13min    | 2     | 12    |
| quick-003  | 1min     | 2     | 2     |
| 14-01      | 21min    | 2     | 40    |
| 14-02      | 26min    | 2     | 4     |
| 14-03      | 22min    | 2     | 11    |

---

_Last updated: 2026-03-19 after v1.2 scope deliberation (roadmap + requirements revised)_
