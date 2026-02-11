# Feature Research: v1.2 Production Readiness

**Domain:** MCP server production readiness, document processing quality infrastructure, npm packaging
**Researched:** 2026-02-11
**Confidence:** HIGH (based on codebase analysis + ecosystem research + MCP best practices)

## Context

This is a v1.2 milestone for an existing MCP server (zlibrary-mcp) that already has 11+ working MCP tools, a sophisticated RAG pipeline with margin detection and adaptive DPI, and multi-source book integration. The v1.2 goal is production readiness: making the repository clean, well-tested, well-documented, and publishable. The feature landscape here is NOT about new end-user functionality -- it is about infrastructure, quality, and developer experience that makes the existing functionality trustworthy and accessible.

## Feature Landscape

### Table Stakes (Users Expect These)

Features that users of a published MCP server npm package and contributors expect. Missing these makes the project feel incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Zero failing tests in CI | Any published package with red CI signals abandonment | LOW | paths.test.js (2 failures on dead `requirements.txt` path), pytest collection errors (2 scripts in wrong directories). Well-scoped fixes. |
| Registered pytest markers | `Unknown pytest.mark.real_world` and `pytest.mark.slow` warnings erode confidence; markers should be declared in pytest.ini | LOW | Add `real_world` and `slow` to existing pytest.ini `markers` section |
| Clean `npm test` output | Warnings, deprecation notices, and collection errors in test output confuse contributors | LOW | Fix the 2 pytest collection errors (test_marginalia_detection.py imports from wrong module, test_tesseract_comparison.py in scripts/archive/) |
| README with working install-and-run path | Every npm package README must show: install, configure, verify it works | MEDIUM | Current README is good but missing `npx` usage, `files` field in package.json, and has stale version references |
| `.npmignore` or `files` field that excludes dev artifacts | Publishing test files, debug scripts, `.claude/` docs, claudedocs to npm is wasteful and leaks internal tooling | LOW | Current `.npmignore` is minimal (11 lines). Need to exclude: `test_files/`, `__tests__/`, `scripts/`, `claudedocs/`, `.claude/`, `.planning/`, debug_*.py, `docs/`, `dummy_output/`, etc. |
| Working CI pipeline that gates PRs | MCP best practices (2026) require automated quality gates; current CI runs tests but does not gate merges | LOW | ci.yml exists and works; needs `uv run pytest -m "not integration"` to avoid credential-requiring tests in CI |
| API documentation for each MCP tool | Users need to know input schemas, output formats, and error cases for each of the 12 tools | MEDIUM | Current README lists tools in a table. Need: parameter descriptions, example requests/responses, error codes. Can be generated from Zod schemas. |
| Contributor setup guide | Open source projects need onboarding docs: fork, install, test, PR flow | MEDIUM | Scattered across CLAUDE.md and .claude/ files. Need a consolidated CONTRIBUTING.md at repo root |
| No dead files at repo root | Top-level `debug_*.py`, `test_*.py`, `VALIDATION_SUMMARY.md`, `BUG_5_OPTIMIZATION_PLAN.md`, `CONTINUATION_INTEGRATION_SUMMARY.md`, `DOCUMENTATION_MAP.md`, `QUICKSTART.md`, `multi_corpus_validation.py`, `performance_baseline.json`, `footnote_validation_results.json` signal messiness | LOW | Move or delete ~15 files. Estimated 30-minute task. |
| Deprecated code removed | `AsyncZlib` was removed in v1.1 but references may linger; `rag_processing.py` facade is intentional but other deprecated paths should be cleaned | LOW | Audit imports and dead code paths |

### Differentiators (Competitive Advantage)

Features that make zlibrary-mcp stand out among MCP servers and document processing tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Structured multi-file RAG output (body + footnotes + metadata) | Most RAG tools dump everything into one file. Separate body/footnotes/metadata lets AI assistants selectively retrieve what they need without loading entire documents. Scholarly users especially benefit from separated footnote files for citation workflows. | MEDIUM | Currently outputs `body.md` + `_meta.json`. Expand to: `body.md`, `footnotes.md` (all footnotes in order with markers), `metadata.json` (enhanced), `quality.json` (extraction quality scores). Files link to each other via relative paths in metadata. |
| Automated precision/recall scoring against ground truth | Enables regression detection at the feature level: did footnote detection get worse? Did body text purity drop? Goes beyond pass/fail to quantitative quality tracking. No other MCP server does this. | MEDIUM | Ground truth schema v3 already exists with 10+ JSON files. Need: scoring harness that computes precision/recall per feature (footnotes, formatting, xmarks), CI integration that fails on regression, quality dashboard output. |
| Unified test taxonomy with labeled categories | 871 collected pytest tests + 20 Jest tests, but no consistent categorization. Proper `@pytest.mark.unit` / `@pytest.mark.slow` / `@pytest.mark.ground_truth` markers enable selective CI: fast tests on every PR, slow/real-PDF tests nightly. | MEDIUM | Register all markers. Apply consistently. Update CI to run `pytest -m "not slow and not integration"` for fast path. |
| Unified ground truth schema (consolidate v1/v2/v3) | Three schema versions exist (schema.json, schema_v2.json, schema_v3.json) with different structures. A single canonical schema simplifies test authoring and quality scoring. | LOW | Migrate all ground truth files to v3 schema. Delete v1/v2 schema files. Add schema validation to test suite. |
| Smithery / npx installation support | Modern MCP servers support `npx @smithery/cli install zlibrary-mcp --client claude` for zero-config setup. This is becoming the expected distribution channel for MCP servers in 2026. | LOW | Requires: clean `package.json` with correct `bin`, `files`, `engines` fields; `postinstall` script that runs `uv sync` if Python available; Smithery manifest (smithery.yaml). |
| Architecture diagrams in docs | Visual system architecture (MCP client -> Node.js -> Python bridge -> EAPI) helps new contributors understand the dual-language design instantly | LOW | Mermaid diagrams in README or separate ARCHITECTURE.md. ASCII art already exists in .claude/ARCHITECTURE.md but not in public docs. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 100% test coverage | Looks good on badges | 871 tests is already comprehensive. Chasing 100% leads to brittle tests for trivial code paths (error message formatting, logging). Current ~78% is healthy. | Set coverage floor at 75%, focus on quality of tests not quantity. Add coverage for untested critical paths only. |
| Auto-generated API docs from TypeScript types | Sounds like free documentation | TypeDoc/TSDoc output for MCP tools is generic and misses the MCP-specific context (how tools interact, workflow examples, error semantics). | Hand-written API docs with examples, supplemented by Zod schema exports for programmatic consumers. |
| Monorepo split (separate npm packages for server vs RAG pipeline) | Clean architecture separation | The Python bridge makes this impractical. RAG pipeline requires vendored zlibrary fork + lib/rag/ modules + Python venv. Splitting creates deployment complexity without clear user benefit. | Keep single package. Use `exports` field to expose sub-paths if needed. |
| Web UI for quality dashboard | Visual quality reporting | Adds a frontend build step, hosting requirement, and maintenance burden to what is a CLI/MCP tool. Quality should be CI-integrated, not browser-based. | JSON quality reports + GitHub Actions PR comments with quality metrics. |
| Docker-first distribution | "Just run docker pull" | MCP servers run as local processes spawned by Claude Code/RooCode. Docker adds latency and complicates credential passthrough. Docker is for CI/testing, not production MCP usage. | npm/npx for distribution. Docker for CI and testing only. |
| Semantic chunking in RAG output | LLM-optimized chunk boundaries | This is a v1.3+ feature requiring research into optimal chunk sizes for different embedding models. Mixing it into v1.2 production readiness scope creep. | Defer to v1.3. Current file-based output (body.md) is compatible with any downstream chunking strategy. |

## Feature Dependencies

```
[Fix known bugs]
    └──enables──> [Clean CI pipeline]
                       └──enables──> [npm publish readiness]

[Unified ground truth schema]
    └──enables──> [Automated precision/recall scoring]
                       └──enables──> [CI quality gates]
                                          └──enhances──> [Clean CI pipeline]

[Test taxonomy / markers]
    └──enhances──> [Clean CI pipeline]
    └──enables──> [Selective test runs (fast/slow)]

[Structured multi-file RAG output]
    └──requires──> [Current body.md + _meta.json output] (already exists)
    └──enhances──> [Automated precision/recall scoring]

[Repo cleanup]
    └──enables──> [npm publish readiness]
    └──enables──> [Documentation overhaul]

[Documentation overhaul]
    └──requires──> [Repo cleanup] (need clean file structure to document)
    └──requires──> [API docs per tool]
    └──enhances──> [npm publish readiness]

[npm publish readiness]
    └──requires──> [Clean CI pipeline]
    └──requires──> [.npmignore / files field]
    └──requires──> [README refresh]
    └──requires──> [Documentation overhaul]

[Contributor guide (CONTRIBUTING.md)]
    └──requires──> [Repo cleanup] (clean structure to describe)
    └──enhances──> [Documentation overhaul]
```

### Dependency Notes

- **Bug fixes must come first:** CI cannot be green until paths.test.js and pytest collection errors are fixed. Everything downstream depends on green CI.
- **Ground truth consolidation enables quality scoring:** Precision/recall computation needs a single schema to parse. Cannot build scoring harness against 3 different schema formats.
- **Repo cleanup before docs:** Documentation that references dead files or scattered directories will be immediately stale. Clean up first, document second.
- **Structured RAG output enhances but does not block quality scoring:** Scoring can work against current body.md + _meta.json. Richer structured output makes scoring more granular but is not a prerequisite.
- **npm publish is the final gate:** Everything else feeds into making the package publishable. This should be the last phase.

## v1.2 Scope Definition

### Phase 1: Bug Fixes and Test Hygiene (Foundation)

Must be done first. Everything else depends on a clean, green test suite.

- [x] Fix paths.test.js failures (2 tests checking for deleted `requirements.txt` and nonexistent Python scripts)
- [x] Fix pytest collection errors (move `scripts/test_marginalia_detection.py` out of pytest collection path; exclude `scripts/` from pytest or fix the import)
- [x] Register missing pytest markers (`real_world`, `slow`) in pytest.ini
- [x] Remove deprecated `AsyncZlib` references if any remain
- [x] Ensure `npm test` and `uv run pytest` are both fully green

### Phase 2: Test Infrastructure Reorganization

Build proper test taxonomy and ground truth consolidation.

- [ ] Define and register complete pytest marker taxonomy: `unit`, `integration`, `slow`, `ground_truth`, `real_world`, `performance`, `e2e`
- [ ] Apply markers consistently across all 871+ Python tests and label Jest tests with proper `describe` grouping
- [ ] Consolidate ground truth schemas to v3 only; migrate all ground truth JSON files; delete schema.json and schema_v2.json
- [ ] Add schema validation test that verifies all ground truth files conform to v3 schema
- [ ] Update CI to run `pytest -m "not slow and not integration"` for the fast path; add nightly CI job for full suite
- [ ] Organize test files: move scattered `test_*.py` scripts at repo root into `__tests__/python/` or `scripts/`

### Phase 3: Structured RAG Output and Quality Scoring

Expand output format and build automated quality measurement.

- [ ] Implement structured multi-file RAG output: `{name}_body.md`, `{name}_footnotes.md`, `{name}_metadata.json`, `{name}_quality.json`
- [ ] `footnotes.md`: All detected footnotes in reading order with markers, page references, and note source classification
- [ ] `quality.json`: Extraction quality scores (completeness, text quality, structure preservation, footnote detection precision/recall)
- [ ] Build precision/recall scoring harness that compares RAG output against ground truth v3 files
- [ ] Compute per-feature scores: footnote detection P/R, formatting detection P/R, xmark detection P/R, body text completeness
- [ ] Add regression detection: compare current scores against stored baselines, fail CI if any metric drops >5%
- [ ] Integrate quality scoring into CI pipeline (GitHub Actions step that reports scores as PR comment)

### Phase 4: Repo Cleanup

Remove dead files, consolidate scattered docs, clean directory structure.

- [ ] Remove dead top-level files: `debug_*.py` (7 files), `test_*.py` (2 files), `multi_corpus_validation.py`, `performance_baseline.json`, `footnote_validation_results.json`, `BUG_5_OPTIMIZATION_PLAN.md`, `CONTINUATION_INTEGRATION_SUMMARY.md`, `DOCUMENTATION_MAP.md`, `VALIDATION_SUMMARY.md`
- [ ] Move `QUICKSTART.md` content into README, delete the separate file
- [ ] Archive or delete `scripts/archive/`, `scripts/experiments/`, `scripts/debugging/` (dev-time utilities not needed in published package)
- [ ] Clean `docs/` directory: archive old specs (`rag-pipeline-implementation-spec.md`, `rag-robustness-enhancement-spec.md`, etc.) that are superseded by implementation
- [ ] Clean `claudedocs/` by archiving completed session notes
- [ ] Remove `MagicMock/` and `dummy_output/` directories from repo root
- [ ] Remove `setup_venv.sh` (superseded by `setup-uv.sh`)
- [ ] Remove `index.js` at repo root (compiled output should only be in `dist/`)

### Phase 5: Documentation Overhaul

Create comprehensive public-facing documentation.

- [ ] Refresh README: add badges (CI status, npm version, license), npx usage example, output format description, Mermaid architecture diagram
- [ ] Create API documentation: one section per MCP tool with parameters, types, example usage, error cases
- [ ] Create CONTRIBUTING.md: setup, test, PR flow, code patterns, architecture overview
- [ ] Add Mermaid architecture diagram showing MCP client -> Node.js -> Python bridge -> EAPI -> Z-Library
- [ ] Create CHANGELOG.md with entries for v1.0, v1.1, v1.2
- [ ] Update .claude/ docs to reflect v1.2 changes (ARCHITECTURE.md, ROADMAP.md)

### Phase 6: Packaging and Publishing Readiness

Final gate: make the npm package publishable and installable.

- [ ] Update `package.json`: add `files` field (whitelist: `dist/`, `lib/`, `zlibrary/`, `pyproject.toml`, `uv.lock`, `setup-uv.sh`, `README.md`, `LICENSE`), verify `bin`, `exports`, `engines`
- [ ] Or update `.npmignore` to comprehensively exclude: `__tests__/`, `test_files/`, `scripts/`, `.claude/`, `.planning/`, `claudedocs/`, `docs/`, `debug_*.py`, `test_*.py`, `.benchmarks/`, `coverage/`, `.serena/`, `MagicMock/`, `dummy_output/`, `__pycache__/`
- [ ] Add `prepublishOnly` checks: `npm run build && npm test` (already partially there)
- [ ] Test `npm pack` output to verify only needed files are included
- [ ] Verify `npx zlibrary-mcp` works (bin field already set, needs testing)
- [ ] Add postinstall note or script for Python setup (`uv sync` requirement)
- [ ] Consider Smithery manifest for MCP registry integration
- [ ] Verify CI pipeline covers: lint, type-check, unit tests (fast), audit

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Phase |
|---------|------------|---------------------|----------|-------|
| Fix failing tests | HIGH | LOW | P1 | 1 |
| Register pytest markers | HIGH | LOW | P1 | 1 |
| Remove deprecated code | MEDIUM | LOW | P1 | 1 |
| Test marker taxonomy | MEDIUM | MEDIUM | P2 | 2 |
| Ground truth consolidation (v3 only) | MEDIUM | LOW | P2 | 2 |
| Schema validation test | MEDIUM | LOW | P2 | 2 |
| Selective CI test runs | HIGH | LOW | P2 | 2 |
| Structured multi-file RAG output | HIGH | MEDIUM | P2 | 3 |
| Precision/recall scoring harness | HIGH | MEDIUM | P2 | 3 |
| Quality regression detection in CI | HIGH | MEDIUM | P2 | 3 |
| Remove dead repo files | HIGH | LOW | P1 | 4 |
| Clean docs/ directory | MEDIUM | LOW | P2 | 4 |
| Archive claudedocs/ old content | LOW | LOW | P3 | 4 |
| README refresh with badges | HIGH | LOW | P1 | 5 |
| API docs per MCP tool | HIGH | MEDIUM | P1 | 5 |
| CONTRIBUTING.md | MEDIUM | MEDIUM | P2 | 5 |
| Architecture diagrams | MEDIUM | LOW | P2 | 5 |
| CHANGELOG.md | MEDIUM | LOW | P2 | 5 |
| package.json files/npmignore | HIGH | LOW | P1 | 6 |
| npm pack verification | HIGH | LOW | P1 | 6 |
| npx functionality test | MEDIUM | LOW | P2 | 6 |
| Smithery manifest | LOW | LOW | P3 | 6 |

**Priority key:**
- P1: Must have for v1.2 to be considered "production ready"
- P2: Should have, significantly improves quality
- P3: Nice to have, can defer without blocking release

## Existing Infrastructure Assessment

### What Already Works (Do Not Rebuild)

| Component | State | Notes |
|-----------|-------|-------|
| 871 pytest tests + 20 Jest tests | Functional (2 collection errors, 2 Jest failures) | Fix, don't restructure |
| Ground truth schema v3 with 10+ JSON files | Functional, well-designed | Consolidate v1/v2, keep v3 as-is |
| body.md + _meta.json output format | Working, used in production | Extend, don't replace |
| GitHub Actions CI (ci.yml) | Working, runs tests and audit | Add quality scoring step, don't rewrite |
| Integration test harness with recorded responses | Working, covers all 11 tools | No changes needed |
| RAG quality framework (.claude/RAG_QUALITY_FRAMEWORK.md) | Well-documented, code samples | Implement the scoring code it describes |
| Husky pre-commit hooks | Working | No changes needed |

### What Needs Work

| Component | Current State | Target State |
|-----------|---------------|--------------|
| pytest markers | 3 registered (`integration`, `e2e`, `performance`), 2 used but unregistered (`real_world`, `slow`) | 7+ registered, consistently applied |
| Ground truth schemas | 3 versions coexist (v1, v2, v3) | Single v3 schema, all files migrated |
| RAG output | body.md + _meta.json | body.md + footnotes.md + metadata.json + quality.json |
| Quality scoring | Framework documented but not implemented as automated harness | Scoring harness computing P/R against ground truth, CI-integrated |
| CI pipeline | Runs all tests including slow ones | Fast/slow split, quality gates, PR comments |
| Top-level directory | ~15 dead files (debug scripts, old summaries) | Clean: only config files, README, LICENSE at root |
| docs/ directory | 40+ files including obsolete specs, research notes | Core docs only; archive old specs |
| .npmignore | Minimal 11-line file | Comprehensive exclusion or switch to `files` whitelist |
| README | Good but missing badges, npx, output format docs | Complete, with install/configure/verify/use flow |

## Competitor Feature Analysis

| Feature | Upstash Context7 MCP | Filesystem MCP Server | Our Approach |
|---------|----------------------|-----------------------|--------------|
| npx install | Yes (npx @upstash/context7-mcp) | Yes | Add npx support; update package.json |
| API documentation | In README, per-tool | In README, per-tool | Per-tool docs with params, examples, errors |
| Structured output | JSON responses | File paths | Multi-file RAG output (body + footnotes + metadata + quality) |
| Quality scoring | N/A (no document processing) | N/A | Automated P/R against ground truth (differentiator) |
| Test infrastructure | Standard Jest | Standard Jest | Dual-language (Jest + pytest), ground truth corpus (differentiator) |
| CI pipeline | GitHub Actions | GitHub Actions | GitHub Actions with quality gates and PR comments |
| Smithery support | Not listed | Not listed | Consider adding for discoverability |
| Architecture docs | Minimal (simple server) | Minimal | Mermaid diagrams (needed due to dual-language complexity) |

## Sources

- [MCP Best Practices Architecture & Implementation Guide](https://modelcontextprotocol.info/docs/best-practices/) -- Production readiness phasing, testing strategy, security recommendations
- [MCP Server Best Practices for 2026](https://www.cdata.com/blog/mcp-server-best-practices-2026) -- Enterprise MCP server patterns
- [MCP Best Practice GitHub](https://mcp-best-practice.github.io/mcp-best-practice/best-practice/) -- Testing layers, error handling, deployment automation
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk) -- Official SDK patterns, package structure, examples
- [npm Package Best Practices](https://reemus.dev/article/npm-package-best-practices) -- files field, exports, publishing checklist
- [package.json exports field guide](https://hirok.io/posts/package-json-exports) -- ESM/CJS dual-format exports
- [Pytest Markers Guide](https://pytest-with-eric.com/pytest-best-practices/pytest-markers/) -- Marker registration, selective test runs, CI integration
- [Smithery CLI](https://github.com/smithery-ai/cli) -- MCP server registry, npx installation patterns
- [RAG Pipeline Quality (Databricks)](https://docs.databricks.com/aws/en/generative-ai/tutorials/ai-cookbook/quality-data-pipeline-rag) -- Metadata enrichment, structured output best practices
- [Document Extraction Quality Scoring](https://arxiv.org/html/2404.04068v1) -- Precision/recall for information extraction, ground truth comparison methods
- Codebase analysis: package.json, pytest.ini, ci.yml, test file inventory, ground truth schemas, RAG output samples, top-level file listing

---
*Feature research for: zlibrary-mcp v1.2 Production Readiness*
*Researched: 2026-02-11*
