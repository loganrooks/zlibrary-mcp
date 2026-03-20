# Requirements: Z-Library MCP v1.2

**Defined:** 2026-02-11
**Revised:** 2026-03-19 (scope narrowed per [deliberation](.planning/deliberations/v12-scope-and-priorities.md))
**Core Value:** Reliable, maintainable MCP server for book access — production-ready infrastructure with high-quality scholarly text extraction

## v1.2 Requirements

Requirements for Production Readiness milestone. Focused on deployment, developer experience, and quality gates. RAG pipeline refinements deferred to v1.3.

### Bug Fixes & Test Hygiene (Phase 13 — COMPLETE)

- [x] **BUG-01**: All Jest tests pass without failures (fix paths.test.js assertions for UV migration)
- [x] **BUG-02**: All pytest tests collect and pass without collection errors (fix scripts/ being collected by pytest)
- [x] **BUG-03**: All pytest markers are registered in pytest.ini (real_world, slow, and any others used but undeclared)
- [x] **BUG-04**: Deprecated AsyncZlib references are removed from codebase
- [x] **BUG-05**: `npm test` and `uv run pytest` both exit green on master

### Test Infrastructure (Phase 14 — COMPLETE)

- [x] **TEST-01**: Complete pytest marker taxonomy defined and registered (unit, integration, slow, ground_truth, real_world, performance, e2e)
- [x] **TEST-02**: Markers applied consistently across all Python test files
- [x] **TEST-03**: Ground truth schemas consolidated to single v3 schema (v1 and v2 schemas deleted, all ground truth files migrated)
- [x] **TEST-04**: Schema validation test verifies all ground truth JSON files conform to v3 schema
- [x] **TEST-05**: CI runs fast test path (`pytest -m "not slow and not integration"`) on every PR, full suite available separately
- [x] **TEST-06**: Scattered test files at repo root moved to proper locations (`__tests__/python/` or `scripts/`)

### Cleanup & DX Foundation (Phase 15)

- [x] **CLEAN-01**: Dead files removed from repo root (debug scripts, stale markdown, old validation artifacts)
- [x] **CLEAN-02**: Compiled .js files removed from src/ directory (only dist/ has compiled output)
- [x] **CLEAN-03**: `.gitignore` updated to exclude `src/**/*.js`, `src/**/*.js.map`, and `src/**/*.egg-info/`
- [x] **CLEAN-04**: `setup_venv.sh` removed (superseded by setup-uv.sh)
- [x] **CLEAN-05**: Large binary blobs (test_downloads/ PDFs) purged from git history via filter-repo + LFS
- [x] **DX-01**: ESLint configured for TypeScript with sensible defaults (no-unused-vars, consistent-type-imports, etc.)
- [x] **DX-02**: Prettier configured for consistent formatting; both ESLint and Prettier enforced via lint-staged
- [x] **DX-03**: Server startup validates ZLIBRARY_EMAIL/ZLIBRARY_PASSWORD presence and emits clear error within 2 seconds
- [x] **DX-04**: Coverage reporting added to CI; threshold configured so coverage regressions fail the build
- [x] **DX-05**: Failing Jest test fixed (Node 22 JSON.parse error message format change in zlibrary-api.test.js)

### Documentation & Distribution (Phase 16)

- [x] **DOCS-01**: README refreshed with badges (CI status, npm version, license), npx usage, and output format description
- [x] **DOCS-02**: API documentation created for each MCP tool with parameters, types, example usage, and error cases
- [x] **DOCS-03**: CONTRIBUTING.md created at repo root (setup, test, PR flow, code patterns, architecture overview)
- [x] **DOCS-04**: Architecture diagram added (Mermaid) showing MCP client → Node.js → Python bridge → EAPI flow
- [x] **DOCS-05**: CHANGELOG.md created with entries for v1.0, v1.1, and v1.2
- [x] **DIST-01**: `package.json` `files` field configured as whitelist; `npm pack --dry-run` shows tarball under 5MB
- [x] **DIST-02**: Docker build verified working; `docker compose -f docker/docker-compose.yaml up` starts server with health check passing
- [x] **DIST-03**: npm install path documented and verified (clone → setup-uv.sh → npm install → npm run build → configure MCP client)
- [x] **DIST-04**: Docker install path documented and verified (clone → docker compose up → configure MCP client with HTTP transport)

### Quality Gates & Release Pipeline (Phase 17)

- [ ] **GATE-01**: CI runs ESLint + Prettier check on every PR (fails on violations)
- [ ] **GATE-02**: CI runs `npm pack --dry-run` and fails if tarball exceeds 10MB or contains test/dev files
- [ ] **GATE-03**: CI startup smoke test: server boots, responds to MCP initialize, exits cleanly
- [ ] **GATE-04**: CI Docker build + health check on push to master
- [ ] **GATE-05**: README tool list validated against registered MCP tools in CI (fails if they diverge)
- [ ] **GATE-06**: GitHub Actions publish workflow for npm on version tags
- [ ] **GATE-07**: GitHub Issue #11 resolved — reporter's setup path works with updated documentation

## v1.3 Requirements (Deferred)

Deferred from v1.2 per [scope deliberation](.planning/deliberations/v12-scope-and-priorities.md). The RAG pipeline works (799 tests, 34/34 recall passing) — these refine internals rather than fix deployment blockers.

### Structured RAG Output

- [ ] **RAG-01**: RAG pipeline produces multi-file output: body.md, footnotes.md, metadata.json per document
- [ ] **RAG-02**: footnotes.md contains all detected footnotes in reading order with markers and page references
- [ ] **RAG-03**: metadata.json is unified (merge current dual metadata systems into single authority)
- [ ] **RAG-04**: Output files link to each other via relative paths in metadata.json
- [ ] **RAG-05**: Existing MCP tool response format remains backward-compatible (additive changes only)

### Automated Quality Scoring

- [ ] **QUAL-01**: Quality scoring harness computes precision/recall per feature (footnotes, formatting, body text completeness) against ground truth
- [ ] **QUAL-02**: Quality scores reported as JSON artifact in CI pipeline
- [ ] **QUAL-03**: Regression detection fails CI if any metric drops >5% below stored baseline
- [ ] **QUAL-04**: Quality scoring is informational-only initially (non-blocking), with option to gate later

## Future Requirements (v1.4+)

### Quality Enhancements
- **QUAL-F01**: Quality scoring gates PRs (block merge if quality drops)
- **QUAL-F02**: Per-commit quality trend graphs in CI artifacts
- **QUAL-F03**: Semantic chunking in RAG output for embedding model compatibility

### Distribution
- **PKG-F01**: Smithery manifest for MCP registry integration
- **PKG-F02**: postinstall script that bootstraps Python environment automatically
- **PKG-F03**: Multi-platform CI testing (macOS, Windows via WSL)

### Test Expansion
- **TEST-F01**: Automated ground truth generation from annotated PDFs
- **TEST-F02**: 20+ PDF test corpus (currently 5+)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Monorepo split (separate npm packages) | Python bridge makes this impractical — single package simpler |
| Web UI for quality dashboard | MCP server is CLI tool — CI artifacts sufficient |
| Auto-generated TypeDoc HTML | Generic output misses MCP context — hand-written API docs with examples preferred |
| 100% test coverage | 78-82% is healthy — chasing 100% leads to brittle tests |
| Full Zod 4 migration | MCP SDK 1.25.3 depends on Zod 3.25.x — defer until SDK updates |
| semantic-release | Over-engineered for manual release cadence — simple tag-triggered publish workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 13 | Complete |
| BUG-02 | Phase 13 | Complete |
| BUG-03 | Phase 13 | Complete |
| BUG-04 | Phase 13 | Complete |
| BUG-05 | Phase 13 | Complete |
| TEST-01 | Phase 14 | Complete |
| TEST-02 | Phase 14 | Complete |
| TEST-03 | Phase 14 | Complete |
| TEST-04 | Phase 14 | Complete |
| TEST-05 | Phase 14 | Complete |
| TEST-06 | Phase 14 | Complete |
| CLEAN-01 | Phase 15 | Complete |
| CLEAN-02 | Phase 15 | Complete |
| CLEAN-03 | Phase 15 | Complete |
| CLEAN-04 | Phase 15 | Complete |
| CLEAN-05 | Phase 15 | Complete |
| DX-01 | Phase 15 | Complete |
| DX-02 | Phase 15 | Complete |
| DX-03 | Phase 15 | Complete |
| DX-04 | Phase 15 | Complete |
| DX-05 | Phase 15 | Complete |
| DOCS-01 | Phase 16 | Complete |
| DOCS-02 | Phase 16 | Complete |
| DOCS-03 | Phase 16 | Complete |
| DOCS-04 | Phase 16 | Complete |
| DOCS-05 | Phase 16 | Complete |
| DIST-01 | Phase 16 | Complete |
| DIST-02 | Phase 16 | Complete |
| DIST-03 | Phase 16 | Complete |
| DIST-04 | Phase 16 | Complete |
| GATE-01 | Phase 17 | Pending |
| GATE-02 | Phase 17 | Pending |
| GATE-03 | Phase 17 | Pending |
| GATE-04 | Phase 17 | Pending |
| GATE-05 | Phase 17 | Pending |
| GATE-06 | Phase 17 | Pending |
| GATE-07 | Phase 17 | Pending |

**Coverage:**
- v1.2 requirements: 33 total (30 complete + 3 pending)
- Mapped to phases: 33
- Unmapped: 0
- v1.3 deferred: 9 (RAG-01–05, QUAL-01–04)

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-03-19 (v1.2 scope narrowed, RAG/QUAL deferred to v1.3, DX/DIST/GATE requirements added)*
