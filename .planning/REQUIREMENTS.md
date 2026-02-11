# Requirements: Z-Library MCP v1.2

**Defined:** 2026-02-11
**Core Value:** Reliable, maintainable MCP server for book access — production-ready infrastructure with high-quality scholarly text extraction

## v1.2 Requirements

Requirements for Production Readiness milestone. Each maps to roadmap phases.

### Bug Fixes & Test Hygiene

- [ ] **BUG-01**: All Jest tests pass without failures (fix paths.test.js assertions for UV migration)
- [ ] **BUG-02**: All pytest tests collect and pass without collection errors (fix scripts/ being collected by pytest)
- [ ] **BUG-03**: All pytest markers are registered in pytest.ini (real_world, slow, and any others used but undeclared)
- [ ] **BUG-04**: Deprecated AsyncZlib references are removed from codebase
- [ ] **BUG-05**: `npm test` and `uv run pytest` both exit green on master

### Test Infrastructure

- [ ] **TEST-01**: Complete pytest marker taxonomy defined and registered (unit, integration, slow, ground_truth, real_world, performance, e2e)
- [ ] **TEST-02**: Markers applied consistently across all Python test files
- [ ] **TEST-03**: Ground truth schemas consolidated to single v3 schema (v1 and v2 schemas deleted, all ground truth files migrated)
- [ ] **TEST-04**: Schema validation test verifies all ground truth JSON files conform to v3 schema
- [ ] **TEST-05**: CI runs fast test path (`pytest -m "not slow and not integration"`) on every PR, full suite available separately
- [ ] **TEST-06**: Scattered test files at repo root moved to proper locations (`__tests__/python/` or `scripts/`)

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

### Repo Cleanup

- [ ] **CLEAN-01**: Dead files removed from repo root (debug scripts, stale markdown, old validation artifacts)
- [ ] **CLEAN-02**: Compiled .js files removed from src/ directory (only dist/ has compiled output)
- [ ] **CLEAN-03**: Stale entry point index.js at root removed, package.json `main` corrected to dist/index.js
- [ ] **CLEAN-04**: setup_venv.sh removed (superseded by setup-uv.sh)
- [ ] **CLEAN-05**: MagicMock/, dummy_output/, and other test artifacts removed from repo root

### Documentation

- [ ] **DOCS-01**: README refreshed with badges (CI status, npm version, license), npx usage, and output format description
- [ ] **DOCS-02**: API documentation created for each MCP tool with parameters, types, example usage, and error cases
- [ ] **DOCS-03**: CONTRIBUTING.md created at repo root (setup, test, PR flow, code patterns, architecture overview)
- [ ] **DOCS-04**: Architecture diagram added (Mermaid) showing MCP client → Node.js → Python bridge → EAPI flow
- [ ] **DOCS-05**: CHANGELOG.md created with entries for v1.0, v1.1, v1.2

### Packaging & Publishing

- [ ] **PKG-01**: package.json `files` field configured as whitelist (dist/, lib/, zlibrary/, pyproject.toml, uv.lock, setup-uv.sh, README, LICENSE)
- [ ] **PKG-02**: `npm pack --dry-run` output verified to include only needed files, tarball under 10 MB
- [ ] **PKG-03**: `npx zlibrary-mcp` verified working (bin field + shebang correct)
- [ ] **PKG-04**: CI pipeline covers: lint, type-check, fast tests, npm audit, tarball size check
- [ ] **PKG-05**: Startup health check verifies Python venv exists, emits clear error if missing

## Future Requirements

Deferred to v1.3+. Tracked but not in current roadmap.

### Quality Enhancements
- **QUAL-F01**: Quality scoring gates PRs (block merge if quality drops)
- **QUAL-F02**: Per-commit quality trend graphs in CI artifacts
- **QUAL-F03**: Semantic chunking in RAG output for embedding model compatibility

### Distribution
- **PKG-F01**: Smithery manifest for MCP registry integration
- **PKG-F02**: Docker-based distribution as alternative to npm
- **PKG-F03**: postinstall script that bootstraps Python environment automatically

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
| Docker-first distribution | MCP servers run as local processes — Docker adds latency |
| semantic-release | Over-engineered for manual release cadence |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 13 | Pending |
| BUG-02 | Phase 13 | Pending |
| BUG-03 | Phase 13 | Pending |
| BUG-04 | Phase 13 | Pending |
| BUG-05 | Phase 13 | Pending |
| TEST-01 | Phase 14 | Pending |
| TEST-02 | Phase 14 | Pending |
| TEST-03 | Phase 14 | Pending |
| TEST-04 | Phase 14 | Pending |
| TEST-05 | Phase 14 | Pending |
| TEST-06 | Phase 14 | Pending |
| RAG-01 | Phase 16 | Pending |
| RAG-02 | Phase 16 | Pending |
| RAG-03 | Phase 16 | Pending |
| RAG-04 | Phase 16 | Pending |
| RAG-05 | Phase 16 | Pending |
| QUAL-01 | Phase 17 | Pending |
| QUAL-02 | Phase 17 | Pending |
| QUAL-03 | Phase 17 | Pending |
| QUAL-04 | Phase 17 | Pending |
| CLEAN-01 | Phase 15 | Pending |
| CLEAN-02 | Phase 15 | Pending |
| CLEAN-03 | Phase 15 | Pending |
| CLEAN-04 | Phase 15 | Pending |
| CLEAN-05 | Phase 15 | Pending |
| DOCS-01 | Phase 18 | Pending |
| DOCS-02 | Phase 18 | Pending |
| DOCS-03 | Phase 18 | Pending |
| DOCS-04 | Phase 18 | Pending |
| DOCS-05 | Phase 18 | Pending |
| PKG-01 | Phase 19 | Pending |
| PKG-02 | Phase 19 | Pending |
| PKG-03 | Phase 19 | Pending |
| PKG-04 | Phase 19 | Pending |
| PKG-05 | Phase 19 | Pending |

**Coverage:**
- v1.2 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after roadmap creation (traceability filled)*
