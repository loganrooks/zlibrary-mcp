# Roadmap: Z-Library MCP

## Milestones

- ✅ **v1.0 Audit Cleanup & Modernization** — Phases 1-7 (shipped 2026-02-01)
- ✅ **v1.1 Quality & Expansion** — Phases 8-12 (shipped 2026-02-04)

## Phases

<details>
<summary>✅ v1.0 Audit Cleanup & Modernization (Phases 1-7) — SHIPPED 2026-02-01</summary>

- [x] Phase 1: Integration Test Harness (2/2 plans) — completed 2026-01-29
- [x] Phase 2: Low-Risk Dependency Upgrades (2/2 plans) — completed 2026-01-29
- [x] Phase 3: MCP SDK Upgrade (2/2 plans) — completed 2026-01-29
- [x] Phase 4: Python Monolith Decomposition (5/5 plans) — completed 2026-02-01
- [x] Phase 5: Feature Porting & Branch Cleanup (3/3 plans) — completed 2026-02-01
- [x] Phase 6: Documentation & Quality Gates (2/2 plans) — completed 2026-02-01
- [x] Phase 7: EAPI Migration (6/6 plans) — completed 2026-02-01

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### ✅ v1.1 Quality & Expansion (SHIPPED 2026-02-04)

**Milestone Goal:** Stabilize infrastructure (Node 22, EAPI gaps, Docker), improve extraction quality for scholarly texts (margin content, adaptive resolution, body text purity), and explore Anna's Archive as alternative source.

#### Phase 8: Infrastructure Modernization
**Goal**: Runtime and transport layer are current, simplified, and production-ready
**Depends on**: Phase 7 (EAPI migration complete)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06
**Success Criteria** (what must be TRUE):
  1. Project builds and all tests pass on Node 22 LTS with updated CI matrix and Dockerfile
  2. All downloads route through EAPIClient with no AsyncZlib references remaining in codebase
  3. Docker production image builds without numpy compilation errors on Alpine
  4. EAPI booklist browsing returns results beyond current graceful degradation stub
  5. EAPI full-text search returns content-aware results beyond current regular-search fallback
**Plans**: 3 plans

Plans:
- [x] 08-01-PLAN.md — Node 22 upgrade + env-paths v4 + CI/Docker updates
- [x] 08-02-PLAN.md — AsyncZlib removal (EAPIClient download + legacy cleanup)
- [x] 08-03-PLAN.md — Docker opencv fix + EAPI booklist/full-text search improvements

#### Phase 9: Margin Detection & Scholarly References
**Goal**: Scholarly margin content (Stephanus, Bekker, line numbers, marginal notes) is detected, classified, and preserved as structured annotations without polluting body text
**Depends on**: Phase 8 (clean runtime foundation)
**Requirements**: MARG-01, MARG-02, MARG-03, MARG-04, MARG-05, MARG-06, MARG-07
**Success Criteria** (what must be TRUE):
  1. PDFs with margin content produce markdown where body text contains no leaked margin artifacts (Stephanus numbers, line numbers, glosses)
  2. Stephanus references (e.g., "231a", "514b-c") and Bekker references (e.g., "1094a1", "1140b5") appear as structured annotations in output metadata
  3. Line numbers from poetry, legal texts, and critical editions are detected and separated from body text
  4. Margin zone widths adapt per document (Loeb outer margins, Oxford inner margins) without manual configuration
  5. Marginal notes and cross-references are preserved in output (not discarded)
**Plans**: 3 plans

Plans:
- [x] 09-01-PLAN.md — Margin detection engine + typed classification (margins.py, margin_patterns.py, tests)
- [x] 09-02-PLAN.md — Pipeline integration (orchestrator + formatter wiring, margin_blocks parameter)
- [x] 09-03-PLAN.md — Integration tests + phase success criteria verification

#### Phase 10: Adaptive Resolution Pipeline
**Goal**: OCR quality improves automatically by selecting optimal DPI per page and per region based on content analysis
**Depends on**: Phase 8 (clean runtime); independent of Phase 9
**Requirements**: DPI-01, DPI-02, DPI-03
**Success Criteria** (what must be TRUE):
  1. Text-heavy pages render at lower DPI (150-200) while pages with fine print, footnotes, or margin text render at higher DPI (300)
  2. Footnote and margin regions within a page can be re-rendered at higher resolution independently of the page default
  3. DPI selection is driven by measured text pixel height analysis (targeting Tesseract 30-33px optimal range)
**Plans**: 4 plans

Plans:
- [x] 10-01-PLAN.md — DPI computation models + font analysis engine (TDD)
- [x] 10-02-PLAN.md — Adaptive page and region renderer (TDD)
- [x] 10-03-PLAN.md — Pipeline integration (orchestrator + OCR wiring + metadata)
- [x] 10-04-PLAN.md — Gap closure: wire region re-rendering into production pipeline

#### Phase 11: Body Text Purity Integration
**Goal**: All detection modules (footnotes, margins, headings, page numbers, TOC, front matter) compose into a unified pipeline that delivers clean body text with non-body content clearly separated
**Depends on**: Phase 9 (margin detection must exist to compose)
**Requirements**: BODY-01, BODY-02, BODY-03
**Success Criteria** (what must be TRUE):
  1. Processing a scholarly PDF produces markdown with clean body text and all non-body content (footnotes, margins, headings, page numbers, TOC) in separate clearly-labeled sections
  2. Each detection decision carries a confidence score accessible in output metadata
  3. No body text is lost by the unified pipeline (recall regression tests pass against ground truth corpus)
**Plans**: 7 plans

Plans:
- [x] 11-01-PLAN.md — Data models (ContentType, BlockClassification, DetectionResult, DocumentOutput) + detector registry
- [x] 11-02-PLAN.md — Recall baseline snapshot + recall regression test
- [x] 11-03-PLAN.md — Detector adapter wrappers (all 6 detectors registered with typed output)
- [x] 11-04-PLAN.md — Compositor with conflict resolution + confidence scoring (TDD)
- [x] 11-05-PLAN.md — Pipeline runner + multi-file writer
- [x] 11-06-PLAN.md — Orchestrator refactor (process_pdf_structured + backward compat)
- [x] 11-07-PLAN.md — End-to-end integration tests + recall regression verification

#### Phase 12: Anna's Archive Integration
**Goal**: Users can search and download books from Anna's Archive (primary, user has API key) with LibGen fallback, clear source attribution
**Depends on**: Phase 8 (AsyncZlib removed, source abstraction possible); independent of Phases 9-11
**Requirements**: ANNA-01, ANNA-02, ANNA-03, ANNA-04
**Success Criteria** (what must be TRUE):
  1. Anna's Archive search (HTML scraping) returns book results with MD5 hashes
  2. Anna's Archive fast download API returns working download URLs (using domain_index=1)
  3. LibGen fallback activates when Anna's quota exhausted or unavailable
  4. Search results include source indicator ('annas_archive' or 'libgen')
  5. Configuration via env vars: ANNAS_SECRET_KEY, ANNAS_BASE_URL, BOOK_SOURCE_DEFAULT
**Plans**: 4 plans

Plans:
- [x] 12-01-PLAN.md — Foundation models + configuration (UnifiedBookResult, SourceConfig, SourceAdapter)
- [x] 12-02-PLAN.md — Anna's Archive adapter (TDD: search scraping + fast download API)
- [x] 12-03-PLAN.md — LibGen adapter (TDD: search + download via libgen-api-enhanced)
- [x] 12-04-PLAN.md — Source router + python_bridge integration + end-to-end tests

## Progress

**Execution Order:**
Phases execute in numeric order: 8 → 9 → 10 → 11 → 12
(Phase 10 could run parallel with Phase 9 but sequenced for focus)

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
