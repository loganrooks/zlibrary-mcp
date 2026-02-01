# Roadmap: Z-Library MCP Audit Cleanup

## Overview

This roadmap transforms the Z-Library MCP server from a C+ graded codebase into a clean, current, maintainable foundation. Six phases follow a strict dependency chain: establish integration safety net, upgrade dependencies (low-risk then high-risk), decompose the Python monolith, port unmerged features, and finally document the stable result.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Integration Test Harness** - Safety net for detecting bridge breakage across all subsequent phases
- [x] **Phase 2: Low-Risk Dependency Upgrades** - Stabilize foundation with env-paths, Zod 4, security fixes
- [x] **Phase 3: MCP SDK Upgrade** - Modernize core server framework from 1.8.0 to latest
- [x] **Phase 4: Python Monolith Decomposition** - Break 4,968-line rag_processing.py into domain modules
- [x] **Phase 5: Feature Porting & Branch Cleanup** - Recover unmerged get_metadata features, delete stale branches
- [ ] **Phase 6: Documentation & Quality Gates** - Update stale docs, activate CI/CD, install pre-commit hooks
- [x] **Phase 7: EAPI Migration** - Migrate from HTML scraping to EAPI JSON endpoints (URGENT: Cloudflare blocking all HTML requests)

## Phase Details

### Phase 1: Integration Test Harness
**Goal**: Developers can verify the Node.js-to-Python bridge works end-to-end before and after every change
**Depends on**: Nothing (first phase)
**Requirements**: TEST-01, TEST-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Running `npm run test:integration` executes a real PythonShell invocation that returns valid JSON from the Python bridge
  2. A Docker-based E2E test starts the MCP server, calls at least one tool, and receives a structured response
  3. BRK-001 (download+RAG combined workflow) status is documented with reproduction steps or confirmed resolved
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Integration tests for all 11 tools (recorded + live modes) and BRK-001 investigation
- [x] 01-02-PLAN.md — Docker E2E test with MCP SDK Client

### Phase 2: Low-Risk Dependency Upgrades
**Goal**: All non-SDK dependencies are current, security vulnerabilities are resolved, and the codebase is ready for the MCP SDK upgrade
**Depends on**: Phase 1
**Requirements**: DEP-01, DEP-02, DEP-04, DEP-05, QUAL-01, QUAL-06
**Success Criteria** (what must be TRUE):
  1. `npm list zod` shows 3.25.x (bridge version; env-paths v4 deferred — requires Node 20+, project on Node 18; full Zod 4 deferred to Phase 3)
  2. All existing tests pass with new dependency versions (zero regressions)
  3. `npm audit` and `pip-audit` report zero high/critical vulnerabilities
  4. ~~`.tsbuildinfo` is in `.gitignore` and not tracked~~ (pre-completed: already at .gitignore line 6)
  5. `booklist_tools.py:267` uses a specific exception type instead of bare `except`, and all BeautifulSoup calls specify a parser
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Upgrade Zod to 3.25.x bridge + npm/pip security audit fixes
- [x] 02-02-PLAN.md — Fix bare except handler + specify lxml parser in all BS4 calls

### Phase 3: MCP SDK Upgrade
**Goal**: The MCP server runs on the latest SDK with protocol compatibility verified against a real MCP client
**Depends on**: Phase 2
**Requirements**: DEP-03
**Success Criteria** (what must be TRUE):
  1. `npm list @modelcontextprotocol/sdk` shows latest stable version (1.25.x+)
  2. The MCP server starts, connects to Claude Desktop (or equivalent MCP client), and successfully handles a tool invocation
  3. All existing tests pass with the new SDK (zero regressions)
  4. TypeScript compilation completes without OOM errors in standard CI memory limits
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Upgrade SDK to 1.25.x+ and rewrite src/index.ts to McpServer
- [x] 03-02-PLAN.md — Update test mocks for McpServer + manual client verification

### Phase 4: Python Monolith Decomposition
**Goal**: rag_processing.py is decomposed into domain modules while all existing imports and tests continue working unchanged
**Depends on**: Phase 3
**Requirements**: QUAL-02, QUAL-03, QUAL-04, QUAL-05
**Success Criteria** (what must be TRUE):
  1. `lib/rag/` directory contains domain modules (utils, detection, processors, quality, ocr, xmark, orchestrator) each under 500 lines (footnotes.py allowed up to 700)
  2. `rag_processing.py` is a thin facade that re-exports all 16 public API functions — `from rag_processing import X` works for every existing import
  3. All Python and Node.js tests pass without any test file modifications
  4. Integration smoke test (Phase 1) passes, confirming the Node.js-to-Python bridge is intact
  5. No resolved BUG-X FIX comments remain in the codebase; DEBUG comments are converted to proper logging calls
**Plans**: 5 plans

Plans:
- [x] 04-01-PLAN.md — Extract utils, detection, and leaf OCR modules into lib/rag/
- [x] 04-02-PLAN.md — Extract quality, processors, orchestrator; finalize facade
- [x] 04-03-PLAN.md — Clean BUG-X FIX comments, convert DEBUG to logging, update Dockerfile
- [x] 04-04-PLAN.md — Gap closure: decompose oversized footnotes.py and pipeline.py into submodules
- [x] 04-05-PLAN.md — Gap closure: extract process_pdf from orchestrator.py

### Phase 5: Feature Porting & Branch Cleanup
**Goal**: Valuable unmerged features from get_metadata branch are available on master, and all stale branches are cleaned up
**Depends on**: Phase 4
**Requirements**: GIT-01, GIT-02, GIT-03, GIT-04, GIT-05, GIT-06
**Success Criteria** (what must be TRUE):
  1. A `get_metadata` MCP tool exists and returns book metadata when invoked
  2. Downloaded files use enhanced filename conventions (author-title format)
  3. Search results include author and title fields in the response
  4. `git branch -r` shows no merged/obsolete branches (the 5 merged + self-modifying-system + get_metadata are deleted)
  5. All tests pass with the ported features integrated
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Enhance metadata tool (tiered response + include param) and filename disambiguation
- [x] 05-02-PLAN.md — Enrich search results with explicit title/author fields
- [x] 05-03-PLAN.md — Delete all 7 stale remote branches

### Phase 6: Documentation & Quality Gates
**Goal**: All documentation reflects the current codebase state, and quality gates prevent future drift
**Depends on**: Phase 5
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. `.claude/ROADMAP.md`, `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, and `VERSION_CONTROL.md` reference current dependencies, phases, and dates (no references to pre-cleanup state)
  2. `ISSUES.md` has ISSUE-002 closed, ISSUE-008/009 updated, and SRCH-001/RAG-002 marked partially implemented
  3. All technical docs include a "Last Verified: YYYY-MM-DD" line
  4. `git commit` triggers pre-commit hooks (lint + test on changed files via husky/lint-staged)
  5. CI pipeline includes `npm audit` and `pip-audit` steps, and setup script checks Python version
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: EAPI Migration
**Goal**: All Z-Library operations use EAPI JSON endpoints instead of HTML scraping, restoring full MCP server functionality
**Depends on**: Phase 5 (can run before or in parallel with Phase 6)
**Requirements**: ISSUE-API-001
**Priority**: 🔴 URGENT — entire MCP server is non-functional
**Success Criteria** (what must be TRUE):
  1. `search_books` returns results via EAPI (no HTML parsing)
  2. All 12 MCP tools that depend on Z-Library API calls work end-to-end
  3. No BeautifulSoup HTML parsing remains in the search/browse/metadata hot path
  4. Automated health check detects Cloudflare challenges or page structure changes
  5. All existing tests pass with the new transport layer
**Plans**: 6 plans

**Context**:
- Z-Library added Cloudflare "Checking your browser..." JS challenge on all HTML page GET requests (discovered 2026-02-01)
- Login via `POST /rpc.php` still works
- EAPI endpoints (`POST /eapi/book/search` with JSON body `{message, limit}`) bypass Cloudflare and return JSON with `success:1`
- EAPI returns rich book objects (id, title, author, year, publisher, language, pages, cover, filesize, etc.)
- Vendored fork (`zlibrary/src/zlibrary/`) currently uses BeautifulSoup to parse HTML search results — this entire approach must be replaced

Plans:
- [x] 07-01-PLAN.md — Create EAPIClient class + response normalization (foundation)
- [x] 07-02-PLAN.md — Rewrite vendored fork (libasync, abs, profile, booklists) to use EAPI
- [x] 07-03-PLAN.md — Migrate lib/ tools (term, author, booklist, metadata) to use EAPI
- [x] 07-04-PLAN.md — Wire python_bridge, update test mocks, add health check, verify E2E
- [x] 07-05-PLAN.md — Gap closure: migrate integration tests from HTML to EAPI imports
- [x] 07-06-PLAN.md — Gap closure: add Cloudflare detection to health check

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Integration Test Harness | 2/2 | Complete | 2026-01-29 |
| 2. Low-Risk Dependency Upgrades | 2/2 | Complete | 2026-01-29 |
| 3. MCP SDK Upgrade | 2/2 | Complete | 2026-01-29 |
| 4. Python Monolith Decomposition | 5/5 | Complete | 2026-02-01 |
| 5. Feature Porting & Branch Cleanup | 3/3 | Complete | 2026-02-01 |
| 6. Documentation & Quality Gates | 0/2 | Not started | - |
| 7. EAPI Migration | 6/6 | Complete | 2026-02-01 |
