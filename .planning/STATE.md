# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** Reliable, maintainable MCP server for book access — production-ready infrastructure with high-quality scholarly text extraction
**Current focus:** v1.2 Production Readiness — Phase 16: CI/CD Pipeline

## Current Position

Phase: 15 of 17 (Cleanup & DX Foundation) -- COMPLETE
Plan: 4 of 4 complete
Status: Phase 15 complete, ready for Phase 16
Last activity: 2026-03-20 — 15-04 complete (credential validation + coverage thresholds)

Progress: [██████████████░░░░░░] 70% of v1.2 (phases 13-15 complete, 16-17 remaining)

## Milestones Shipped

| Version | Name | Phases | Plans | Shipped |
|---------|------|--------|-------|---------|
| v1.0 | Audit Cleanup & Modernization | 1-7 | 22 | 2026-02-01 |
| v1.1 | Quality & Expansion | 8-12 | 21 | 2026-02-04 |

**Total:** 12 phases, 43 plans executed (+ 2 plans in phase 13, 3 plans in phase 14)

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

**Phase 15 (15-01):**
- Migrated sample.pdf to LFS before running filter-repo to avoid pointer corruption
- Purged 7 specific blob SHAs identified by research phase rather than blanket size filter
- Batched all remaining large-blob cleanup into one force-push to minimize history disruption

**Phase 15 (15-02):**
- Shortened JSON.parse error regex to match stable prefix across Node versions
- Used git rm for tracked src/index.js, plain rm for untracked src/lib/*.js files

**Phase 15 (15-04):**
- Used measured coverage baselines (74.54% stmts Jest, 58% pytest) rather than research-phase values for threshold accuracy
- Set thresholds at baseline minus 5% to prevent regressions without blocking new feature work
- Credential validation skips in test mode (opts.testing) to avoid breaking Jest mocked tests

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
- ~~Large blob (74MB Kant PDF) in git history under test_downloads/ — CLEAN-05, will purge in Phase 15~~ RESOLVED by 15-01
- ~~1 Jest test failing (Node 22 JSON.parse error message format change) — DX-05~~ RESOLVED by 15-02
- ~~5 compiled .js files in src/lib/ appearing as untracked — CLEAN-02/CLEAN-03~~ RESOLVED by 15-02

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

Last session: 2026-03-20
Stopped at: Completed 15-04-PLAN.md
Resume with: `/gsdr:execute-phase 16` (Phase 15 complete, Phase 16 next)

### Performance Metrics

| Phase-Plan | Duration | Tasks | Files |
|------------|----------|-------|-------|
| 13-01      | 20min    | 2     | 6     |
| 13-02      | 13min    | 2     | 12    |
| quick-003  | 1min     | 2     | 2     |
| 14-01      | 21min    | 2     | 40    |
| 14-02      | 26min    | 2     | 4     |
| 14-03      | 22min    | 2     | 11    |
| 15-01      | 12min    | 2     | 1     |
| 15-02      | 3min     | 2     | 2     |
| 15-04      | 5min     | 2     | 6     |

---

_Last updated: 2026-03-20 after 15-04 execution (credential validation + coverage thresholds)_
