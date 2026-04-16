# Project Milestones: Z-Library MCP

## v1.2 Production Readiness (Shipped: 2026-03-20)

**Delivered:** Made the repo deployment-ready with clean CI pipeline (8 quality gate jobs), comprehensive documentation (README, API docs, CONTRIBUTING, CHANGELOG), dual distribution paths (npm + Docker), and automated release workflow. Closed all tech debt from milestone audit.

**Phases completed:** 13-18 (16 plans total)

**Key accomplishments:**

- Green CI with 8 quality gate jobs: lint, pack-check, smoke-test, docker, docs-check, test-fast, test-full, audit
- npm tarball reduced 99.6% (117MB → 416KB) with working Docker distribution path
- ESLint + Prettier with lint-staged enforcement, startup credential validation, coverage thresholds
- Complete documentation: README with badges + Mermaid diagram, API docs for 13 tools, CONTRIBUTING.md, CHANGELOG
- npm publish workflow with provenance support, triggered by version tags
- Test infrastructure: 7-marker taxonomy, v3 ground truth schema, fast (6s) / full (19min) CI split
- Gap closure: fixed 7 broken tests, corrected CHANGELOG links, cleaned stale docs

**Stats:**

- 456 files changed (+39,316 / -21,275 lines)
- ~19,157 lines of TypeScript/Python
- 6 phases, 16 plans, 99 commits
- 38 days from start to ship (2026-02-11 → 2026-03-20)

**Git range:** `v1.1..v1.2`

**Post-release follow-through:** quick-004 on 2026-03-20 closed the v1.2 audit debt, quick-005 on 2026-03-27 restored green 8/8 CI, and `v1.2.0` was tagged on 2026-04-02.

**What's next:** v1.3 — RAG pipeline refinement (structured output, quality scoring)

---

## v1.1 Quality & Expansion (Shipped: 2026-02-04)

**Delivered:** Stabilized infrastructure (Node 22, EAPI gaps, Docker fixes), improved scholarly text extraction quality (margin detection, adaptive resolution, body text purity pipeline), and integrated Anna's Archive as alternative book source with LibGen fallback.

**Phases completed:** 8-12 (21 plans total)

**Key accomplishments:**

- Infrastructure modernization: Node 22 LTS, env-paths v4, AsyncZlib removal (pure EAPIClient downloads), Docker opencv-python-headless fix
- Margin detection for scholarly texts: Stephanus/Bekker numbering, line numbers, marginal notes with adaptive zone widths and structured annotations
- Adaptive resolution pipeline: DPI selection (150-400) driven by text pixel height analysis, region-level re-rendering for footnotes/margins
- Unified body text purity: Compositor combining 6 detectors with conflict resolution, confidence scoring, multi-file output (body.md + _meta.json)
- Anna's Archive integration: HTML scraping search, fast download API, LibGen fallback with rate limiting, source router with auto selection

**Stats:**

- 296 files created/modified
- ~43,790 lines of TypeScript/Python (+63,019 net lines added)
- 5 phases, 21 plans, 103 commits
- 3 days from start to ship (2026-02-01 → 2026-02-04)

**Git range:** `v1.0..v1.1`

---

## v1.0 Audit Cleanup & Modernization (Shipped: 2026-02-01)

**Delivered:** Transformed codebase from C+ grade to clean, current, maintainable foundation with modernized dependencies, decomposed architecture, ported features, and EAPI migration.

**Phases completed:** 1-7 (22 plans total)

**Key accomplishments:**

- Integration test harness covering all 11 MCP tools with recorded tests + Docker E2E
- Dependency modernization: MCP SDK 1.25.3, Zod 3.25.x, 15 security vulns fixed
- Python monolith decomposition: 4,968-line file → 31 domain modules with backward-compatible facade
- Feature porting: metadata tiering, enhanced filenames, author/title search from stale branch; 7 branches deleted
- Documentation & quality gates: 7 docs updated, Husky pre-commit hooks, GitHub Actions CI
- EAPI migration: all Z-Library ops moved from HTML scraping to JSON endpoints, bypassing Cloudflare

**Stats:**

- 159 files created/modified
- 45,231 lines of TypeScript/Python
- 7 phases, 22 plans
- 4 days from start to ship (2026-01-29 → 2026-02-01)

**Git range:** `docs(01)` → `docs(07)`

---
