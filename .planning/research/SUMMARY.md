# Project Research Summary

**Project:** Z-Library MCP Codebase Cleanup/Modernization
**Domain:** Technical debt remediation for MCP server infrastructure
**Researched:** 2026-01-28
**Confidence:** HIGH

## Executive Summary

This project is a **codebase modernization and technical debt cleanup** for the Z-Library MCP server, currently graded C+ due to dependency obsolescence, monolithic architecture, and scattered unmerged work. Expert cleanup follows a strict dependency-driven sequence: stabilize the foundation (dependencies), then refactor structure (Python decomposition), then recover lost work (feature porting), and finally document the result.

The recommended approach is a **6-phase sequential cleanup** starting with low-risk dependency upgrades (env-paths, Zod), followed by the high-risk MCP SDK upgrade that affects the entire type system. The Python monolith (4,968 lines) must be decomposed using a facade pattern to preserve backward compatibility while extracting 9 domain-focused modules. Feature porting from stale branches requires re-implementation rather than merging to avoid semantic conflicts. The entire process must be gated by integration testing since unit tests (78% Node, 82% Python) mock the critical Node-Python bridge and won't detect breakage.

The key risks are (1) **MCP SDK API drift** where the low-level Server class migration creates runtime failures that compile cleanly, (2) **Zod 4 schema behavior changes** that silently alter validation semantics, and (3) **Python bridge contract breakage** during decomposition that only surfaces in end-to-end testing. All three are mitigated by establishing integration smoke tests FIRST, then proceeding sequentially with full validation after each phase.

## Key Findings

### Recommended Stack

The cleanup requires upgrading three critical dependencies in strict sequence due to peer dependency coupling. The MCP TypeScript SDK (currently 1.8.0, target 1.25.3) is 17 versions behind and forces a Zod upgrade from 3.24.2 to 4.x due to internal imports from `zod/v4`. The SDK upgrade is HIGH risk due to protocol version changes, server class refactoring, and documented TypeScript compilation memory issues (OOM in CI). The Zod upgrade is MEDIUM risk with a single breaking change affecting this codebase: `z.object({}).passthrough()` must migrate to `z.looseObject({})`. The env-paths upgrade (3.0 to 4.0) is LOW risk with zero API changes, only a Node.js 20+ requirement.

**Core technologies:**
- **@modelcontextprotocol/sdk 1.25.3**: MCP server framework — 17 versions behind, protocol 2025-11-25 support, Zod 4 coupling, TypeScript memory issues documented
- **Zod 4.x**: Schema validation — breaking change in `.passthrough()` API, must upgrade before SDK due to dual-version TypeScript errors
- **env-paths 4.0.0**: Cross-platform path resolution — low-risk upgrade, Node.js 20+ only
- **zod-to-json-schema**: JSON Schema generation — must upgrade in lockstep with Zod 4, version TBD based on compatibility matrix
- **Python modular architecture**: Decompose 4,968-line monolith into 9 domain modules (utils, detection, processors, quality, ocr, xmark, orchestrator) using facade pattern

**Critical version dependencies:**
1. Node.js 20+ required (env-paths 4.0)
2. Zod upgrade MUST precede SDK upgrade (dual-version errors)
3. zod-to-json-schema upgrade MUST accompany Zod upgrade
4. Integration test harness MUST exist before any Python refactoring

### Expected Features

Cleanup completeness is defined by **7 table stakes features** that restore the codebase to a maintainable state, plus **7 differentiator features** that elevate it to quality modernization. The table stakes (T1-T7) are: dependency updates to latest compatible versions, Zod 4 migration, stale branch cleanup (6 remote branches), porting 4 valuable commits from `feature/rag-robustness-enhancement`, documentation freshness pass for 3-month-stale `.claude/` files, Python monolith decomposition to ≤500-line modules, and ISSUES.md triage of 25 open issues. The differentiators (D1-D7) add: CI/CD pipeline activation, pre-commit hooks, Python type hints with mypy, unified test infrastructure, Node.js engine version bump to >=18, ADR review, and env-paths major update.

**Must have (table stakes):**
- **T1: Dependency updates (MCP SDK, Zod)** — 17 versions behind creates security/compatibility risk, blocks future feature work
- **T4: Port get_metadata features** — 4 valuable commits (metadata scraping, enhanced filenames, author/title search) currently unmerged
- **T6: Python monolith decomposition** — 4,968-line file is unmaintainable, must extract to domain modules with facade pattern
- **T3: Stale branch cleanup** — 6 remote branches create cognitive overhead, oldest from Apr 2025
- **T5: Documentation freshness** — `.claude/*.md` reference deprecated approaches and wrong priorities
- **T7: ISSUES.md triage** — 25 open issues, some obsolete or resolved

**Should have (competitive):**
- **D1: CI/CD pipeline activation** — `.claude/CI_CD.md` exists but may not be active, prevents regression
- **D2: Pre-commit hooks** — husky + lint-staged prevents new technical debt
- **D3: Python type hints + mypy** — 6k lines with no type checking hides bugs

**Defer (v2+):**
- **New MCP tools** — cleanup scope, not feature scope (DL-001 download queue, SRCH-001 fuzzy search)
- **TypeScript architecture refactor** — TS layer is thin, Python is the problem
- **Migration to different test frameworks** — Jest + Pytest work fine (78%/82% coverage)
- **Rewrite Python bridge in TypeScript** — massive scope, Python has better doc-processing libraries

### Architecture Approach

The Python monolith decomposition follows a **facade pattern with incremental extraction** to preserve backward compatibility. The target structure is 9 modules organized by domain responsibility: `utils/` (constants, exceptions, text, cache), `detection/` (footnotes, headings, toc, front_matter, page_numbers), `processors/` (pdf, epub, txt), `quality/` (analysis, pipeline), `ocr/` (recovery, spacing, corruption), and `xmark/` (detection). The original `rag_processing.py` becomes a thin facade that re-exports everything, ensuring zero changes to test files or `python_bridge.py` during extraction. Extraction order is driven by dependency flow: leaf modules first (constants, utils), then detection modules, then quality/OCR, then processors, finally the orchestrator. Each extraction is a single commit with full test validation.

**Major components:**
1. **Orchestrator** (`orchestrator.py`) — High-level entry points (`process_pdf`, `process_epub`, `process_txt`, `process_document`, `save_processed_text`), thin coordination layer
2. **Detection modules** (`detection/*`) — Domain logic for footnotes (700 lines, most complex), headings, TOC, front matter, page numbers — extracted as cohesive units
3. **Processors** (`processors/*`) — Format-specific processing (PDF, EPUB, TXT) that call detection and quality modules
4. **Quality pipeline** (`quality/*`) — PDF quality analysis (29-branch `_analyze_pdf_block`), multi-stage pipeline orchestration
5. **OCR recovery** (`ocr/*`) — OCR quality assessment, Tesseract re-OCR, letter spacing correction, corruption detection
6. **Utilities** (`utils/*`) — Pure functions (text utilities, cache, constants, exceptions) with zero cross-module dependencies
7. **Facade** (`rag_processing.py`) — Backward-compatible re-export layer, preserves all existing imports

**Key architectural constraints:**
- **No circular imports**: Dependency direction must be orchestrator → processors → detection → utils (never reverse)
- **Public API preservation**: All 16 public functions remain importable from `rag_processing.py`
- **Integration contract stability**: `python_bridge.py` entry point path never changes during decomposition
- **Module cohesion**: Footnote detection (700 lines, 40-branch complexity) extracted as single unit to avoid excessive cross-file coupling

### Critical Pitfalls

1. **MCP SDK Server Class API Drift (P1 - CRITICAL)** — The codebase uses low-level `Server.setRequestHandler()` API; SDK 1.25.x refactored to `McpServer.registerTool()`. Migration is not drop-in; staying on old API creates undocumented path. **Prevention**: Pin to intermediate version (1.12.x) first, validate with real MCP client (not just unit tests), decide upfront whether to migrate Server class or stay on legacy API. **Detection**: MCP client connection failures, capability negotiation errors.

2. **Zod 3 to 4 Schema Behavior Changes (P2 - CRITICAL)** — `z.string().default("x").optional()` returns default instead of `undefined` in Zod 4; `zodToJsonSchema()` output changes; `ZodError.errors` renamed to `ZodError.issues`. Tests that check "parsing succeeds" pass, tests that check "exact output value" may not exist. **Prevention**: Use [zod-v3-to-v4 codemod](https://github.com/nicoespeon/zod-v3-to-v4), audit every `.default()` + `.optional()` combination, snapshot-test JSON Schema output before/after migration. **Detection**: Diff JSON Schema output; test tool invocations with missing optional parameters.

3. **Python Bridge Contract Breakage (P3 - CRITICAL)** — `python_bridge.py` imports from `rag_processing.py`; Node.js `PythonShell` invokes with hardcoded script paths. Decomposing Python breaks import chains. Node.js-Python boundary is stringly-typed (no TypeScript checking). **Prevention**: Define Python bridge contract FIRST (document script paths, function signatures, JSON schemas), keep `python_bridge.py` as stable entry point, add integration tests that invoke PythonShell BEFORE decomposing, extract one module at a time with integration validation. **Detection**: Integration test failures, `PythonShell` module errors.

4. **Semantic Merge Conflicts from Stale Branch Porting (P4 - HIGH)** — `feature/rag-robustness-enhancement` is 120 commits behind master. Cherry-picking/rebasing hits merge conflicts. Dangerous case: auto-merged semantic conflicts (master refactors function signature, stale branch calls old signature, Git merges cleanly but code crashes). **Prevention**: Do NOT rebase/merge directly; read stale branch diff, understand intent, re-implement on master; create checklist per feature (goal, files changed, equivalent change on current master); run full test suite after each port. **Detection**: `git diff --stat` between branches shows overlapping file changes.

5. **Test Suite Green Doesn't Mean Integration Works (P8 - MODERATE)** — Jest tests mock Python bridge; pytest tests run independently. Neither tests actual Node.js-to-Python integration. During cleanup, both suites stay green while bridge breaks. **Prevention**: Add smoke test that runs real PythonShell invocation FIRST, manual integration test after each phase, consider Docker-based E2E test. **Detection**: Manual testing reveals failures unit tests missed, server starts but tools return errors.

## Implications for Roadmap

Based on research, suggested 6-phase structure with strict sequential dependencies:

### Phase 1: Integration Test Harness
**Rationale:** Must detect bridge breakage before refactoring begins. Unit tests are 78% Node, 82% Python but both mock the critical Node-Python bridge. P3 (bridge breakage) and P8 (test suite green despite integration failure) will go undetected without this foundation.

**Delivers:**
- Smoke test that invokes real PythonShell (not mocked)
- Manual integration test procedure documented
- Test harness that validates Node.js → Python → Z-Library → document processing → file output full stack

**Addresses:** Foundation for all subsequent phases

**Avoids:** P8 (test suite green doesn't mean integration works), provides early warning for P3 (bridge breakage)

### Phase 2: Low-Risk Dependency Upgrades
**Rationale:** Establish stable foundation before tackling high-risk MCP SDK upgrade. env-paths (3.0 → 4.0) has zero API changes, only Node.js 20+ requirement. Zod (3.24.2 → 4.x) is MEDIUM risk but MUST precede SDK upgrade due to peer dependency coupling (SDK 1.23+ uses `zod/v4` internally).

**Delivers:**
- env-paths 4.0.0 installed and validated
- Zod 4.x installed with `z.looseObject({})` migration for `DownloadBookToFileParamsSchema`
- zod-to-json-schema upgraded to compatible version
- All tests passing with new dependency versions

**Uses:** Zod 4 breaking change mitigation (STACK.md), zod-v3-to-v4 codemod (PITFALLS.md P2)

**Avoids:** P2 (Zod schema behavior changes) via snapshot testing, P9 (zod-to-json-schema incompatibility)

### Phase 3: High-Risk MCP SDK Upgrade
**Rationale:** SDK 1.8.0 → 1.25.3 is 17 versions behind with protocol version changes, server class refactoring, and TypeScript compilation memory issues. Must happen after Zod upgrade (Step 2) to avoid dual-version TypeScript errors. This is the foundational change; everything else builds on stable APIs.

**Delivers:**
- MCP SDK 1.25.3 installed with Zod 4 compatibility
- Import path migrations verified (subpath exports may have changed)
- Protocol version 2025-11-25 support
- Real MCP client validation (Claude Desktop connection test)
- TypeScript compilation memory monitoring (OOM detection)

**Uses:** MCP SDK migration steps (STACK.md), Server class decision framework (PITFALLS.md P1)

**Implements:** Core MCP server infrastructure modernization

**Avoids:** P1 (Server class API drift) via real client testing, P7 (TypeScript OOM) via memory monitoring

### Phase 4: Python Monolith Decomposition
**Rationale:** 4,968-line monolith must be decomposed now that dependencies are stable. Facade pattern preserves backward compatibility. Extraction order follows dependency flow (leaf modules first). Each extraction is single commit with full test validation. Integration test from Phase 1 catches any bridge breakage.

**Delivers:**
- 9 domain modules: utils (constants, exceptions, text, cache), detection (footnotes, headings, toc, front_matter, page_numbers), processors (pdf, epub, txt), quality (analysis, pipeline), ocr (recovery, spacing, corruption), xmark (detection), orchestrator
- Facade `rag_processing.py` preserving all 16 public API imports
- All modules ≤500 lines (footnotes.py ~700 lines as single cohesive unit)
- Zero test file changes (backward compatibility via facade)
- Integration test validation after each module extraction

**Implements:** Modular architecture from ARCHITECTURE.md extraction order

**Avoids:** P3 (bridge breakage) via stable entry point + integration testing, P10 (venv issues) via `uv sync` after structural changes

### Phase 5: Feature Porting & Branch Cleanup
**Rationale:** Port valuable work from `feature/rag-robustness-enhancement` (metadata scraping, enhanced filenames, author/title search) now that codebase is stable. Re-implement rather than merge to avoid semantic conflicts from 120-commit divergence. Clean stale branches only after extracting what's needed.

**Delivers:**
- 4 commits from get_metadata branch re-implemented on master
- Metadata scraping, enhanced filenames, author/title in search results
- All tests passing with new features
- 6 stale remote branches deleted (manifested first with tag backups)
- Branch cleanup documentation

**Addresses:** T4 (port get_metadata features), T3 (stale branch cleanup)

**Avoids:** P4 (semantic merge conflicts) via re-implementation strategy, P6 (losing unmerged work) via branch manifest and tagging

### Phase 6: Documentation & Quality Gates
**Rationale:** Document LAST since all code changes are complete. Update only docs describing stable interfaces. Add CI/CD quality gates and pre-commit hooks to prevent regression.

**Delivers:**
- `.claude/*.md` freshness pass (no references to deleted branches, current priorities)
- ISSUES.md triage (25 issues → verified current or closed)
- CI/CD pipeline activation (if `.claude/CI_CD.md` describes inactive pipeline)
- Pre-commit hooks (husky + lint-staged for lint + test on changed files)
- Python type hints on public interfaces with mypy in CI (differentiator)
- Single unified test command (`npm test` runs Jest + pytest with combined coverage)

**Addresses:** T5 (doc freshness), T7 (issue triage), D1 (CI/CD activation), D2 (pre-commit hooks), D3 (type hints), D4 (unified test infrastructure)

**Avoids:** P5 (docs drift immediately) by doing this last

### Phase Ordering Rationale

**Sequential dependency chain:** Integration tests (P1) → Low-risk deps (P2) → SDK upgrade (P3) → Python decomposition (P4) → Feature porting (P5) → Documentation (P6)

**Why this order:**
- **Integration tests first**: P3 (bridge breakage) and P8 (mock-only tests) will go undetected without this safety net
- **Zod before SDK**: SDK 1.23+ imports from `zod/v4` internally; dual Zod versions cause TypeScript TS2589 errors
- **Deps before refactoring**: Refactor against current APIs, not deprecated ones; P1 (SDK API drift) makes refactoring twice if done backwards
- **Feature porting after stabilization**: Merging into a moving target (mid-refactor) creates P4 (semantic conflicts); port onto stable foundation
- **Branch cleanup after porting**: P6 (losing unmerged work) if you delete before extracting features
- **Docs last**: P5 (docs drift) if updated while code still changing

**How this avoids pitfalls:**
- **P1 (SDK API drift)**: Phase 3 pins intermediate version first, validates with real client
- **P2 (Zod schema changes)**: Phase 2 snapshot-tests JSON Schema output, uses codemod
- **P3 (bridge breakage)**: Phase 1 creates integration test, Phase 4 validates after each extraction
- **P4 (semantic merge conflicts)**: Phase 5 re-implements instead of rebasing
- **P8 (green tests hide integration failure)**: Phase 1 foundation catches this across all phases

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (SDK Upgrade):** HIGH risk — Server class migration decision (stay on legacy `setRequestHandler` API vs migrate to `McpServer.registerTool`), import path changes in 1.25.x subpath exports, protocol negotiation behavior, TypeScript compilation memory tuning
- **Phase 4 (Python Decomposition):** MEDIUM risk — Circular import prevention strategies, footnote detection module cohesion (700 lines, should it split further?), Python package structure best practices for scientific computing libraries

Phases with standard patterns (skip research-phase):
- **Phase 1 (Integration Tests):** Standard smoke test pattern for multi-language integration
- **Phase 2 (Low-Risk Deps):** Well-documented Zod v3→v4 migration with official codemod
- **Phase 5 (Feature Porting):** Standard git workflow (re-implementation over rebase)
- **Phase 6 (Documentation):** Standard documentation audit and CI/CD activation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings based on official release notes (MCP SDK, Zod v4), verified version diffs, documented breaking changes |
| Features | HIGH | Direct codebase inspection (git branch analysis, npm outdated, line counts via wc -l), no external sources needed |
| Architecture | HIGH | Complete analysis of 4,968-line monolith, import graph analysis across all test files, established Python packaging patterns |
| Pitfalls | HIGH | Verified with official issue trackers (MCP SDK #985 TypeScript OOM, Zod #4923 dual-version errors), documented migration guides |

**Overall confidence:** HIGH

### Gaps to Address

**MCP SDK Server class migration decision**: The research identifies two paths (stay on legacy `Server.setRequestHandler` API vs migrate to new `McpServer.registerTool` API) but doesn't make the decision. **Action during Phase 3**: Evaluate migration effort (count current `setRequestHandler` call sites, estimate rewrite time), test Server class behavior with MCP SDK 1.25.x on an isolated branch, decide based on effort vs risk tradeoff.

**Optimal footnote module granularity**: ARCHITECTURE.md recommends extracting footnote detection as a single 700-line module to maintain cohesion (40-branch `_detect_footnotes_in_page` function with many local helpers). But this exceeds the ≤500-line target. **Action during Phase 4**: After extraction, analyze if footnote helpers can be further separated without creating excessive cross-file coupling. Consider sub-modules within detection/footnotes/ if natural boundaries emerge.

**zod-to-json-schema exact version**: STACK.md notes this must upgrade in lockstep with Zod but doesn't specify the target version. **Action during Phase 2**: Check zod-to-json-schema compatibility matrix after Zod 4 install, verify MCP SDK 1.25.x internal schema conversion (may make this dependency obsolete), run JSON Schema snapshot tests to validate.

**UV venv changes during Python package restructuring**: If creating formal Python subpackages (with separate `__init__.py` exports), `pyproject.toml` may need updates. **Action during Phase 4**: Run `uv sync` after each structural change, verify `setup-uv.sh` still works from scratch, test that all imports resolve correctly in fresh venv.

**Unmerged branch value assessment**: 6 stale branches may contain valuable features beyond `feature/rag-robustness-enhancement`. **Action during Phase 5**: Before cleanup, run `git log master..origin/<branch> --oneline` for all 6 branches, create manifest (purpose, unmerged commit count, decision: delete/port/archive), tag any with unmerged work worth preserving.

## Sources

### Primary (HIGH confidence)
- [MCP TypeScript SDK Releases](https://github.com/modelcontextprotocol/typescript-sdk/releases) — Breaking changes 1.8.0 → 1.25.3, Server class refactoring, protocol version updates
- [MCP Specification Changelog 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/changelog) — Protocol version requirements
- [Zod v4 Migration Guide](https://zod.dev/v4/changelog) — Complete breaking changes, `.passthrough()` deprecation
- [Zod v4 Versioning](https://zod.dev/v4/versioning) — Subpath import strategy (`zod/v4`)
- [MCP SDK TypeScript Compilation Memory Issues #985](https://github.com/modelcontextprotocol/typescript-sdk/issues/985) — Documented OOM failures
- [Zod Dual Version TypeScript Errors #4923](https://github.com/colinhacks/zod/issues/4923) — TS2589 from Zod 3 + Zod 4 in same dep tree
- Direct codebase inspection — `lib/rag_processing.py` (4,968 lines, 55 functions), `npm outdated`, `git branch -a`, test file import analysis

### Secondary (MEDIUM confidence)
- [zod-v3-to-v4 Codemod](https://github.com/nicoespeon/zod-v3-to-v4) — Automated migration tool
- [Strangler Fig Pattern](https://medium.com/@stephen.biston/practical-monolith-decomposition-the-strangler-fig-pattern-1aa49988072f) — Monolith decomposition strategy
- [Modular Monolith in Python](https://breadcrumbscollector.tech/modular-monolith-in-python/) — Python package organization patterns
- [Kraken Technologies: Python Monolith Organization](https://blog.europython.eu/kraken-technologies-how-we-organize-our-very-large-pythonmonolith/) — Domain-driven module structure
- [env-paths v4.0.0 Release](https://github.com/sindresorhus/env-paths/releases/tag/v4.0.0) — Node.js 20+ requirement
- [npm audit Documentation](https://docs.npmjs.com/cli/v9/commands/npm-audit/) — Security scanning
- [pip-audit on PyPI](https://pypi.org/project/pip-audit/) — Python security scanning

### Tertiary (LOW confidence)
- [MCP SDK V2 Discussion #809](https://github.com/modelcontextprotocol/typescript-sdk/issues/809) — Future SDK direction (not affecting current cleanup)

---
**Research completed:** 2026-01-28
**Ready for roadmap:** yes
