# Project Research Summary

**Project:** zlibrary-mcp v1.2 Production Readiness
**Domain:** MCP server production packaging, dual-language tooling, npm publishing infrastructure
**Researched:** 2026-02-11
**Confidence:** HIGH

## Executive Summary

The v1.2 "Production Readiness" milestone transforms an existing, functional dual-language MCP server (Node.js + Python) into a professionally publishable npm package. The project already has 11+ working MCP tools and a sophisticated RAG pipeline with 871+ tests. The focus is infrastructure, quality assurance, and developer experience rather than new end-user functionality.

The recommended approach prioritizes foundational hygiene (fix tests, clean repo) before visible features (structured output, quality scoring) before final packaging. This order respects critical dependency chains discovered in architecture analysis: green CI is the prerequisite for everything else. The dual-language nature creates unique challenges—three independent configuration systems (Jest, pytest, TypeScript) must stay synchronized, and the current npm package would ship 44 MB of test PDFs and internal documentation without intervention.

Key risks center on breaking changes during refactoring. Test reorganization can break three separate systems simultaneously (Jest paths, pytest discovery, CI workflows). Output format changes break MCP client integrations. File deletions can remove runtime dependencies hidden by dynamic Python imports. The mitigation strategy is surgical: one system per commit, comprehensive validation between changes, and explicit backward compatibility for any user-facing changes.

## Key Findings

### Recommended Stack

Five new devDependencies enable production readiness without adding production weight: TypeDoc for API documentation, Ajv for ground truth validation, knip for dead code detection, pytest-json-report for CI quality gates, and comprehensive `.npmignore` or `package.json` `files` field configuration. Notably, the research recommends AGAINST common solutions like scikit-learn (overkill for precision/recall math), Zod v4 (incompatible with MCP SDK), and semantic-release (over-engineered for manual release process).

**Core technologies:**
- **TypeDoc + typedoc-plugin-markdown**: API doc generation from Zod schemas — de facto TypeScript standard, ESM-native, GitHub-friendly Markdown output
- **Ajv**: JSON Schema validation for ground truth — fastest validator, directly handles existing draft-07 schemas without conversion
- **knip**: Dead code detection — single tool replaces depcheck + ts-prune, understands Jest/TypeScript/GitHub Actions
- **pytest-json-report**: Structured test output for CI — enables quality scoring dashboard and regression gates
- **package.json `files` field**: Whitelist for npm package — safer than `.npmignore` blacklist, prevents 44 MB bloat

**Critical constraint:** MCP SDK 1.25.3 locks Zod to 3.25.x. Attempting to use Zod v4 features (native `toJSONSchema()`) causes `w._parse is not a function` errors. This drives the Ajv recommendation for schema validation instead of Zod-based approaches.

### Expected Features

Table stakes are all about trust signals: zero failing tests, clean npm package, working CI, documented API, contributor guide. The project already passes the functionality bar—users need to trust it's maintainable. Differentiators focus on RAG quality: structured multi-file output (body + footnotes + metadata separated for selective retrieval), automated precision/recall scoring against ground truth (no other MCP server does this), and unified test taxonomy enabling fast/slow CI splits.

**Must have (table stakes):**
- Zero failing tests in CI — any published package with red CI signals abandonment
- Clean `npm test` output — warnings and collection errors confuse contributors
- `.npmignore` or `files` field excluding dev artifacts — publishing test PDFs to npm is wasteful and leaks internal tooling
- API documentation per MCP tool — users need parameter schemas, example requests, error cases
- Contributor setup guide — fork → install → test → PR flow
- No dead files at repo root — ~15 stale debug scripts and summaries signal messiness

**Should have (competitive):**
- Structured multi-file RAG output — separate body/footnotes/metadata/quality files enable selective AI retrieval (scholarly users especially benefit)
- Automated precision/recall scoring — enables regression detection at feature level, quantitative quality tracking
- Unified test taxonomy — proper pytest markers enable selective CI (fast tests on every PR, slow/real-PDF tests nightly)
- Unified ground truth schema — consolidate v1/v2/v3 into single canonical v3 schema
- Smithery/npx installation support — modern MCP distribution (zero-config `npx @smithery/cli install`)

**Defer (v2+):**
- 100% test coverage — current 78% is healthy, chasing 100% leads to brittle tests for trivial code
- Monorepo split — Python bridge makes this impractical without clear user benefit
- Web UI for quality dashboard — adds frontend build burden, quality should be CI-integrated
- Semantic chunking in RAG output — requires research into optimal chunk sizes, scope creep for v1.2

### Architecture Approach

The dual-language design has clear boundaries: Node.js handles MCP protocol and tool registration, Python owns document processing and Z-Library API interaction. The critical v1.2 changes are all Python-side or config/infra—no TypeScript layer changes needed. The architecture reveals **duplicate metadata systems** as the key refactoring opportunity: `DocumentOutput.write_files()` and `save_processed_text()` both write metadata sidecars with different schemas. Merging into a single authority eliminates confusion and enables richer structured output.

**Major components:**
1. **Test infrastructure reorganization** — Move from flat `__tests__/` to categorized `__tests__/{node/python}/{unit/integration/performance}`, consolidate ground truth from `test_files/` to `__tests__/ground_truth/`, unify schemas to v3 only. Impacts jest.config.js, pytest.ini, conftest.py.
2. **Structured RAG output** — Merge duplicate metadata systems into single `DocumentOutput.write_files()` authority. Output format: `{name}/body.md`, `{name}/footnotes.md`, `{name}/metadata.json`, `{name}/quality.json`. Changes localized to 4-5 Python modules.
3. **Quality scoring CI** — New `lib/quality/` modules (scorer, ground truth loader, report generator) + `scripts/ci/quality_score.py` entry point. Separate CI job that produces JSON artifact. Uses pytest-json-report for structured results.
4. **Repo cleanup** — Remove ~15 dead files at root (debug scripts, stale summaries), consolidate `test_files/` + `test_data/`, move `claudedocs/` to `docs/internal/`, fix conflicting entry points (`index.js` vs `dist/index.js`).
5. **npm packaging** — Add `package.json` `files` whitelist, fix `main` field, verify with `npm pack --dry-run`, add CI check that fails if tarball > 10 MB.

### Critical Pitfalls

1. **44 MB npm tarball ships test PDFs and planning artifacts** — Current `.npmignore` is minimal 15-line blacklist; `npm pack` reveals 1,017 files including 22 MB Derrida PDF, all `.claude/` and `claudedocs/` dirs. Switch to `package.json` `files` whitelist (dist/, lib/, zlibrary/, pyproject.toml, uv.lock, setup-uv.sh). Add CI check that fails if tarball > 10 MB.

2. **Test reorganization breaks CI in three independent ways** — Jest moduleNameMapper hardcodes `^../lib/`, pytest pythonpath assumes test location, CI workflow uses bare `pytest` command. Update all four configs (jest.config.js, pytest.ini, tsconfig.json, ci.yml) in SAME commit. Run both `npm test` AND `uv run pytest` locally before pushing.

3. **Breaking RAG output format without consumer migration** — Current `{filename}.processed.markdown` + `{filename}.metadata.json` is the API surface for MCP clients. Changes to path patterns or JSON structure break consumers. ADD new fields/files, do not remove/rename. Include `format_version` field. Add integration test that pins exact JSON structure.

4. **Conflicting entry points** — Three `index.js` files exist: root (legacy CJS), `dist/index.js` (compiled ESM), `src/index.js` (stale artifact). `package.json` has contradictory `"main": "index.js"` vs `"exports": "./dist/index.js"`. Remove root and src versions, set `"main": "dist/index.js"`, verify with `npx .` testing.

5. **Quality scoring creates flaky CI from non-determinism** — PDF extraction varies across PyMuPDF versions, OS encodings, renderer backends. Use score RANGES not exact thresholds (`0.75 <= score <= 1.0`), pin PyMuPDF exactly, consolidate ground truth schemas first, make scoring informational for 2 weeks before gating.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation (Bug Fixes + Test Hygiene)
**Rationale:** Everything depends on green CI. Current failures in paths.test.js (references deleted `requirements.txt`) and pytest collection errors (2 scripts in wrong locations) must be fixed before any restructuring. Fixing bugs first prevents confusion about whether test failures are from the fix or from new regressions.

**Delivers:**
- Zero test failures in both Jest and pytest
- Registered pytest markers (`real_world`, `slow`)
- Removed deprecated `AsyncZlib` references
- Clean `npm test` and `uv run pytest` output

**Addresses:**
- Table stakes: zero failing tests, clean test output
- Pitfall 8: fixing bugs breaks tests that depend on broken behavior

**Avoids:**
- Pitfall 3: test reorganization breaking already-broken CI
- Compounding failures that make root cause analysis impossible

**Research flag:** NO — bug fixes are surgical, well-understood

---

### Phase 2: Test Infrastructure Reorganization
**Rationale:** Test structure must stabilize before changing anything tests validate. Reorganization touches three independent config systems (Jest, pytest, CI). Dependencies chain from this phase: structured output needs proper tests, quality scoring needs ground truth consolidation, repo cleanup needs test coverage to verify deletions don't break runtime.

**Delivers:**
- Categorized test structure: `__tests__/{node/python}/{unit/integration/performance}`
- Unified ground truth: migrate to v3 schema only, delete v1/v2
- Schema validation test ensuring all ground truth conforms to v3
- CI split: fast tests (`pytest -m "not slow and not integration"`) on PRs, full suite nightly
- Organized test files: no more root-level `test_*.py` scripts

**Addresses:**
- Must-haves: test taxonomy, ground truth consolidation
- Should-haves: unified test markers, selective CI runs
- Pitfall 3: test reorganization breaking CI (mitigated by updating all configs in same commit)

**Uses:**
- pytest marker registration (from pytest.ini)
- Ajv for ground truth schema validation

**Avoids:**
- Pitfall 3: breaking three systems simultaneously (by updating Jest, pytest, CI configs together)
- Pitfall 8: tests referencing wrong schema versions

**Research flag:** NO — well-documented pytest best practices, Jest moduleNameMapper is understood

---

### Phase 3: Structured RAG Output
**Rationale:** Output format must be stable before building quality scoring on top of it. Depends on Phase 2's test infrastructure to validate format changes. Changes are localized to 4-5 Python modules (merge duplicate metadata systems). This is a **breaking change** for consumers, requiring careful backward compatibility.

**Delivers:**
- Unified metadata system: single `DocumentOutput.write_files()` authority
- Multi-file output: `{name}/body.md`, `{name}/footnotes.md`, `{name}/metadata.json`, `{name}/quality.json`
- Enriched metadata schema with source, structure, output_files, quality, processing sections
- Backward-compatible transition: add `format_version` field, support old format temporarily

**Addresses:**
- Should-have: structured multi-file RAG output (competitive differentiator)
- Architecture: eliminate duplicate metadata generation anti-pattern

**Uses:**
- Existing `DocumentOutput` dataclass (extend, don't replace)
- Ground truth schema v3 (for validating output format)

**Implements:**
- Pattern 1: Single Authority for Output Files (from ARCHITECTURE.md)

**Avoids:**
- Pitfall 4: breaking consumers without migration path (by adding format_version and supporting old format)
- Anti-pattern 1: duplicate metadata generation

**Research flag:** NO — internal refactoring, well-scoped changes

---

### Phase 4: Repo Cleanup
**Rationale:** Must come after test reorganization (both move files) but before documentation (docs should describe clean final state). Cleanup reduces noise for npm packaging phase. High file-move count but low risk since no source logic changes.

**Delivers:**
- Removed ~15 dead files at root (debug scripts, stale summaries, validation reports)
- Consolidated test data: `test_files/` + `test_data/` → `__tests__/ground_truth/pdfs/`
- Moved session notes: `claudedocs/` → `docs/internal/`
- Fixed conflicting entry points: removed root `index.js` and `src/index.js`, set `"main": "dist/index.js"`
- Clean top-level: only config files, README, LICENSE at root

**Addresses:**
- Must-haves: no dead files at root, contributor setup guide (needs clean structure to describe)
- Pitfall 2: conflicting entry points
- Pitfall 5: deleting files that are secretly imported

**Avoids:**
- Pitfall 5: runtime breakage (by creating dependency map before deletion, testing in small batches)
- Anti-pattern 2: root-level script proliferation

**Research flag:** NO — file moves and deletions, validated by test suite

---

### Phase 5: Automated Quality Scoring
**Rationale:** Depends on Phase 2 (ground truth consolidation) and Phase 3 (structured output format). Should be informational-only initially to collect baseline data before gating. Scoring reveals regressions at feature level (footnote detection, body text purity).

**Delivers:**
- Quality scoring modules: `lib/quality/{scorer.py, ground_truth_loader.py, report.py}`
- CI entry point: `scripts/ci/quality_score.py`
- GitHub Actions quality job: runs after tests pass, uploads report artifact
- Regression detection: compares scores against baselines, warns if drop > 5%
- JSON report format for CI consumption (via pytest-json-report)

**Addresses:**
- Should-have: automated precision/recall scoring (competitive differentiator)
- Pitfall 6: quality scoring flakiness

**Uses:**
- pytest-json-report for structured test results
- Ground truth schema v3 (consolidated in Phase 2)
- Structured output format (from Phase 3)

**Implements:**
- Pattern 2: Ground Truth as Test Contract
- Pattern 3: CI Quality Gate with Artifact Upload

**Avoids:**
- Pitfall 6: flaky CI from non-determinism (by using score ranges, pinning PyMuPDF, collecting data before gating)

**Research flag:** MAYBE — precision/recall computation is simple, but CI integration for non-deterministic scoring may need experimentation. Start informational, gate later.

---

### Phase 6: Documentation Overhaul
**Rationale:** Must come after cleanup (docs describe final state) and after all features stabilize. Documentation touches five locations (.claude/, claudedocs/, docs/, root-level, .planning/), requiring careful consolidation with defined ownership.

**Delivers:**
- Refreshed README: badges (CI, npm version, license), npx usage, Mermaid architecture diagram
- API documentation: generated from Zod schemas, one section per MCP tool with params/examples/errors
- CONTRIBUTING.md: setup → test → PR flow, code patterns
- CHANGELOG.md: entries for v1.0, v1.1, v1.2
- Consolidated docs structure: delete `claudedocs/`, move content to `docs/internal/`, define doc ownership

**Addresses:**
- Must-haves: API documentation, contributor guide
- Should-haves: architecture diagrams
- Pitfall 9: documentation overhaul produces stale docs

**Uses:**
- TypeDoc (considered but research recommends simpler Zod-based script)
- Custom `scripts/generate-api-docs.js` reading Zod schemas

**Avoids:**
- Pitfall 9: docs drift from code (by defining ownership, deleting session archives)
- Anti-pattern 2: scattered documentation

**Research flag:** NO — documentation is straightforward, Zod schema extraction is well-understood

---

### Phase 7: npm Publishing Readiness
**Rationale:** Final gate. Depends on all previous phases: cleanup determines what exists to publish, docs must be complete, tests must be green, output format must be stable. This phase is pure packaging—no source code changes.

**Delivers:**
- `package.json` `files` whitelist: dist/, lib/, zlibrary/, pyproject.toml, uv.lock, setup-uv.sh, LICENSE, README.md
- Fixed `main` field: points to `dist/index.js`
- Verified `npx zlibrary-mcp` works
- CI check: fails if `npm pack` tarball > 10 MB
- Postinstall note/script for Python setup (`uv sync` requirement)
- Tested install flow in clean Docker container

**Addresses:**
- Must-haves: clean npm package, npx functionality
- Pitfall 1: 44 MB tarball ships test PDFs
- Pitfall 7: npm postinstall Python bootstrap fails silently

**Uses:**
- npm builtin: `npm pack --dry-run` for pre-publish validation
- npm provenance with GitHub Actions (supply chain security)

**Avoids:**
- Pitfall 1: bloated package (by using `files` whitelist + CI size check)
- Pitfall 7: silent failure when Python missing (by startup health check + clear error)

**Research flag:** NO — npm packaging best practices are well-documented, `files` field approach is standard

---

### Phase Ordering Rationale

1. **Bug fixes first** — Cannot validate anything on broken CI. Fixes are surgical and low-risk.
2. **Test reorg second** — Everything else depends on stable test infrastructure. Ground truth consolidation enables quality scoring.
3. **Structured output third** — Needs test infrastructure to validate format changes. Must be stable before quality scoring.
4. **Cleanup in parallel with or after tests** — Both move files; can overlap if done carefully. Must precede docs (which describe final state).
5. **Quality scoring after output format** — Needs to know what format to validate. Should be informational before gating.
6. **Docs after cleanup and features** — Documents the finalized state. No sense documenting intermediate states.
7. **npm packaging last** — Everything must be stable. This is the "ship it" phase.

**Dependency chains discovered:**
- Green CI → all other phases (foundational)
- Ground truth v3 consolidation → quality scoring (scoring needs single schema)
- Test infrastructure → structured output → quality scoring (each validates the next)
- Cleanup → docs → npm packaging (each informs the next about what to document/publish)

**How this avoids pitfalls:**
- Phases 1-2 fix CI before any restructuring (avoids compounding failures)
- Phase 3 adds format_version field (avoids breaking consumers)
- Phase 4 uses dependency mapping (avoids deleting runtime files)
- Phase 5 starts informational (avoids flaky CI gating)
- Phase 6 defines doc ownership (avoids doc drift)
- Phase 7 uses `files` whitelist + CI size check (avoids 44 MB tarball)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Quality Scoring):** CI integration for non-deterministic scoring may need experimentation with thresholds and pytest-json-report parsing. Start informational, gate later after collecting baseline data.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Bug Fixes):** Surgical fixes, well-understood
- **Phase 2 (Test Reorg):** Pytest best practices well-documented, Jest moduleNameMapper understood
- **Phase 3 (Structured Output):** Internal refactoring, changes localized to 4-5 Python modules
- **Phase 4 (Cleanup):** File moves/deletions, validated by test suite
- **Phase 6 (Documentation):** Straightforward, Zod schema extraction well-understood
- **Phase 7 (npm Publishing):** npm best practices well-documented, `files` field approach standard

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | TypeDoc, Ajv, knip, pytest-json-report all verified against npm registry and official docs. Zod v3 constraint validated via MCP SDK dependency inspection. |
| Features | HIGH | Table stakes derived from npm package ecosystem standards and MCP best practices. Differentiators based on RAG quality framework already in codebase. Anti-features identified through analysis of scope creep risks. |
| Architecture | HIGH | All findings from direct codebase inspection at commit 4350456. Component boundaries, data flow, and integration points verified through source analysis. Duplicate metadata system discovered and refactoring path clear. |
| Pitfalls | HIGH | Critical pitfalls grounded in `npm pack --dry-run` output (44 MB tarball empirically measured), existing test failures, and conflicting package.json fields. Recovery strategies informed by git revert capabilities and npm unpublish time limits. |

**Overall confidence:** HIGH

All research based on verified sources (official documentation, npm registry, codebase analysis) rather than inference. The dual-language nature and existing 44K LOC codebase provide concrete constraints that guide recommendations. No speculative architecture—all changes have clear integration points identified.

### Gaps to Address

**Minimal gaps — research is comprehensive:**

- **pytest-json-report integration:** While the library is well-documented, the exact JSON structure for quality dashboard parsing may need adjustment during Phase 5 implementation. Start with logging full report, then extract needed fields.

- **Backward compatibility migration period:** Phase 3 (structured output) needs user communication strategy for format changes. Recommend supporting old format for one minor version (v1.2 introduces new, v1.3 deprecates old, v1.4 removes). This timeline should be validated with any known heavy users.

- **Docker clean-install testing:** Phase 7 (npm publishing) requires testing `npm install zlibrary-mcp` → `bash setup-uv.sh` → `npx zlibrary-mcp` in a clean container. Current CI uses pre-built environment. Add a separate Docker-based install test to CI during Phase 7.

- **Smithery manifest:** Phase 7 mentions considering Smithery support for MCP registry. This is LOW priority but may need investigation if npx installation proves cumbersome for users. Defer until user feedback post-v1.2 release.

**No blocking gaps identified.** All gaps are "how exactly" implementation details rather than "whether this works" architectural questions. Proceed to roadmap creation.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis at commit 4350456:** All architecture findings, component inventory, existing test structure, ground truth schemas, output format specifications
- **`npm pack --dry-run` output:** 44.4 MB tarball, 1,017 files (empirical evidence for Pitfall 1)
- **package.json, jest.config.js, pytest.ini, ci.yml:** Configuration analysis for integration points
- **TypeDoc official site (v0.28.16):** API documentation generation, ESM support, configuration
- **Ajv official docs (v8.17.1):** JSON Schema draft-07 validation, ESM compatibility
- **knip official site (v5.83.1):** Dead code detection, plugin ecosystem
- **pytest-json-report PyPI:** JSON test reporting for CI
- **npm docs: files field:** Whitelist vs blacklist approach, official recommendation
- **MCP SDK GitHub (v1.25.3):** Zod v3 peer dependency constraint verification

### Secondary (MEDIUM confidence)
- **MCP Best Practices Guide:** Production readiness phasing, testing layers, deployment automation
- **MCP TypeScript SDK examples:** Package structure conventions, tool registration patterns
- **npm package best practices (reemus.dev):** files field, exports, publishing checklist
- **Pytest Good Integration Practices:** pythonpath configuration, test discovery, marker registration
- **RAG Pipeline Quality (Databricks):** Metadata enrichment, structured output best practices
- **Document Extraction Quality Scoring (arxiv):** Precision/recall methodologies for information extraction

### Tertiary (LOW confidence)
- **Smithery CLI documentation:** MCP server registry conventions (not yet critical, can defer)
- **npm trusted publishing with Node 24+:** Requires Node 24; project on Node 22; using classic provenance instead

---
*Research completed: 2026-02-11*
*Ready for roadmap: YES*
