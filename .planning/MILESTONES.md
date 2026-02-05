# Project Milestones: Z-Library MCP

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

**What's next:** v1.2 — MCP tool wiring for search_multi_source, full Zod 4 migration, download queue management

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

**What's next:** v1.1 — feature development on clean foundation

---
