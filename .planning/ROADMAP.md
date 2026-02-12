# Roadmap: Z-Library MCP

## Milestones

- v1.0 Audit Cleanup & Modernization — Phases 1-7 (shipped 2026-02-01)
- v1.1 Quality & Expansion — Phases 8-12 (shipped 2026-02-04)
- v1.2 Production Readiness — Phases 13-19 (in progress)

## Phases

<details>
<summary>v1.0 Audit Cleanup & Modernization (Phases 1-7) — SHIPPED 2026-02-01</summary>

- [x] Phase 1: Integration Test Harness (2/2 plans) — completed 2026-01-29
- [x] Phase 2: Low-Risk Dependency Upgrades (2/2 plans) — completed 2026-01-29
- [x] Phase 3: MCP SDK Upgrade (2/2 plans) — completed 2026-01-29
- [x] Phase 4: Python Monolith Decomposition (5/5 plans) — completed 2026-02-01
- [x] Phase 5: Feature Porting & Branch Cleanup (3/3 plans) — completed 2026-02-01
- [x] Phase 6: Documentation & Quality Gates (2/2 plans) — completed 2026-02-01
- [x] Phase 7: EAPI Migration (6/6 plans) — completed 2026-02-01

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>v1.1 Quality & Expansion (Phases 8-12) — SHIPPED 2026-02-04</summary>

- [x] Phase 8: Infrastructure Modernization (3/3 plans) — completed 2026-02-02
- [x] Phase 9: Margin Detection & Scholarly References (3/3 plans) — completed 2026-02-02
- [x] Phase 10: Adaptive Resolution Pipeline (4/4 plans) — completed 2026-02-02
- [x] Phase 11: Body Text Purity Integration (7/7 plans) — completed 2026-02-03
- [x] Phase 12: Anna's Archive Integration (4/4 plans) — completed 2026-02-04

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### v1.2 Production Readiness (In Progress)

**Milestone Goal:** Transform the functional MCP server into a professionally publishable npm package with clean CI, structured RAG output, automated quality scoring, and comprehensive documentation. No new end-user features — this is infrastructure, quality, and developer experience.

- [x] **Phase 13: Bug Fixes & Test Hygiene** - Green CI as foundation for everything else — completed 2026-02-11
- [x] **Phase 14: Test Infrastructure** - Unified marker taxonomy, ground truth v3, fast/slow CI split — completed 2026-02-11
- [ ] **Phase 15: Repo Cleanup** - Remove dead files, fix entry points, clean repo root
- [ ] **Phase 16: Structured RAG Output** - Multi-file output with unified metadata
- [ ] **Phase 17: Quality Scoring** - Automated precision/recall against ground truth in CI
- [ ] **Phase 18: Documentation** - README refresh, API docs, contributor guide, architecture diagram
- [ ] **Phase 19: Packaging & Publishing** - Files whitelist, tarball verification, npx, CI pipeline

## Phase Details

### Phase 13: Bug Fixes & Test Hygiene
**Goal**: Both test suites pass cleanly with zero failures, zero collection errors, and no deprecated code
**Depends on**: Nothing (first phase of v1.2)
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04, BUG-05
**Success Criteria** (what must be TRUE):
  1. `npm test` exits with code 0 and all Jest assertions pass (including paths.test.js)
  2. `uv run pytest` collects all test files without errors and all tests pass
  3. Running `uv run pytest --strict-markers` succeeds (all markers registered in pytest.ini)
  4. Searching the codebase for `AsyncZlib` returns zero hits outside of git history
  5. `npm test && uv run pytest` run back-to-back both exit green on a clean checkout of master
**Plans:** 2 plans
Plans:
- [x] 13-01-PLAN.md -- Fix test configuration and stale assertions (BUG-01, BUG-02, BUG-03)
- [x] 13-02-PLAN.md -- Remove deprecated AsyncZlib references (BUG-04)

### Phase 14: Test Infrastructure
**Goal**: Tests are organized with a complete marker taxonomy, unified ground truth schema, and CI can run fast tests separately from slow ones
**Depends on**: Phase 13 (green CI required before restructuring tests)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. `pytest.ini` registers a complete marker taxonomy (unit, integration, slow, ground_truth, real_world, performance, e2e) and every test file uses at least one marker
  2. Only v3 ground truth schema files exist in the repo (v1 and v2 schemas deleted), and a validation test confirms all ground truth JSON conforms to v3
  3. `uv run pytest -m "not slow and not integration"` runs a fast subset that completes in under 30 seconds
  4. No test files exist at the repo root — all are under `__tests__/` or `scripts/`
  5. CI configuration distinguishes fast tests (every PR) from full suite (available separately)
**Plans:** 3 plans
Plans:
- [x] 14-01-PLAN.md -- Register complete marker taxonomy and apply pytestmark to all test files (TEST-01, TEST-02)
- [x] 14-02-PLAN.md -- Consolidate ground truth to v3 schema with validation test (TEST-03, TEST-04)
- [x] 14-03-PLAN.md -- Relocate root Python files and split CI into fast/full jobs (TEST-05, TEST-06)

### Phase 15: Repo Cleanup
**Goal**: Repository root contains only essential files, with no dead scripts, stale artifacts, or conflicting entry points
**Depends on**: Phase 14 (test file moves in phase 14 should complete before further file reorganization)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05
**Success Criteria** (what must be TRUE):
  1. No debug scripts, stale markdown summaries, or old validation artifacts exist at the repo root
  2. The `src/` directory contains zero `.js` files (only TypeScript source; compiled output lives in `dist/` only)
  3. `node -e "require('./package.json').main"` returns `dist/index.js` and `node dist/index.js --help` works (no stale root index.js)
  4. `setup_venv.sh` does not exist (only `setup-uv.sh` remains)
  5. No `MagicMock/`, `dummy_output/`, or similar test artifact directories exist at repo root
**Plans**: TBD

### Phase 16: Structured RAG Output
**Goal**: RAG pipeline produces separated, linked output files (body, footnotes, metadata) with a single unified metadata system
**Depends on**: Phase 14 (test infrastructure needed to validate new output format)
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04, RAG-05
**Success Criteria** (what must be TRUE):
  1. Processing a document produces a directory containing `body.md`, `footnotes.md`, and `metadata.json` as separate files
  2. `footnotes.md` contains all detected footnotes in reading order with markers and page references
  3. `metadata.json` is the single source of truth for document metadata (no separate competing metadata sidecar)
  4. `metadata.json` contains relative paths linking to `body.md` and `footnotes.md` in its `output_files` section
  5. Existing MCP tool callers continue working without changes — new fields are additive, `format_version` field present
**Plans**: TBD

### Phase 17: Quality Scoring
**Goal**: CI automatically computes and reports precision/recall quality scores per feature against ground truth, with regression detection
**Depends on**: Phase 14 (ground truth v3 consolidation), Phase 16 (structured output format)
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04
**Success Criteria** (what must be TRUE):
  1. Running the quality harness against ground truth produces per-feature scores (footnotes precision/recall, formatting accuracy, body text completeness)
  2. CI pipeline produces a downloadable JSON artifact containing quality scores after each run
  3. If any metric drops more than 5% below stored baseline, CI marks the quality check as failed
  4. Quality scoring failures are informational (non-blocking) by default, with a documented toggle to make them blocking
**Plans**: TBD

### Phase 18: Documentation
**Goal**: The project has professional documentation — README with badges, per-tool API docs, contributor guide, architecture diagram, and changelog
**Depends on**: Phase 15 (cleanup determines final file layout), Phase 16 (structured output must be documented)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05
**Success Criteria** (what must be TRUE):
  1. README.md includes CI status badge, npm version badge, license badge, `npx` usage instructions, and output format description
  2. API documentation exists for each MCP tool with parameters, types, example usage, and error cases
  3. CONTRIBUTING.md at repo root describes setup, test, PR flow, code patterns, and architecture overview
  4. A Mermaid architecture diagram shows the MCP client to Node.js to Python bridge to EAPI data flow
  5. CHANGELOG.md exists with entries for v1.0, v1.1, and v1.2
**Plans**: TBD

### Phase 19: Packaging & Publishing
**Goal**: The project is ready to publish to npm — clean tarball, working npx, comprehensive CI, and startup health check
**Depends on**: All previous phases (this is the final gate)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):
  1. `package.json` `files` field is a whitelist containing only dist/, lib/, zlibrary/, pyproject.toml, uv.lock, setup-uv.sh, README, and LICENSE
  2. `npm pack --dry-run` shows a tarball under 10 MB with no test files, planning docs, or dev artifacts
  3. `npx zlibrary-mcp` starts the server successfully (bin field and shebang are correct)
  4. CI pipeline runs lint, type-check, fast tests, npm audit, and tarball size check on every PR
  5. Starting the server without a Python venv emits a clear, actionable error message (not a stack trace)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Integration Test Harness | v1.0 | 2/2 | Complete | 2026-01-29 |
| 2. Low-Risk Dependency Upgrades | v1.0 | 2/2 | Complete | 2026-01-29 |
| 3. MCP SDK Upgrade | v1.0 | 2/2 | Complete | 2026-01-29 |
| 4. Python Monolith Decomposition | v1.0 | 5/5 | Complete | 2026-02-01 |
| 5. Feature Porting & Branch Cleanup | v1.0 | 3/3 | Complete | 2026-02-01 |
| 6. Documentation & Quality Gates | v1.0 | 2/2 | Complete | 2026-02-01 |
| 7. EAPI Migration | v1.0 | 6/6 | Complete | 2026-02-01 |
| 8. Infrastructure Modernization | v1.1 | 3/3 | Complete | 2026-02-02 |
| 9. Margin Detection & Scholarly References | v1.1 | 3/3 | Complete | 2026-02-02 |
| 10. Adaptive Resolution Pipeline | v1.1 | 4/4 | Complete | 2026-02-02 |
| 11. Body Text Purity Integration | v1.1 | 7/7 | Complete | 2026-02-03 |
| 12. Anna's Archive Integration | v1.1 | 4/4 | Complete | 2026-02-04 |
| 13. Bug Fixes & Test Hygiene | v1.2 | 2/2 | Complete | 2026-02-11 |
| 14. Test Infrastructure | v1.2 | 3/3 | Complete | 2026-02-11 |
| 15. Repo Cleanup | v1.2 | 0/TBD | Not started | - |
| 16. Structured RAG Output | v1.2 | 0/TBD | Not started | - |
| 17. Quality Scoring | v1.2 | 0/TBD | Not started | - |
| 18. Documentation | v1.2 | 0/TBD | Not started | - |
| 19. Packaging & Publishing | v1.2 | 0/TBD | Not started | - |

---

_Last updated: 2026-02-11 after Phase 14 execution complete_
