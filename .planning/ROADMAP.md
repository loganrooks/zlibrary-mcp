# Roadmap: Z-Library MCP

## Milestones

- v1.0 Audit Cleanup & Modernization — Phases 1-7 (shipped 2026-02-01)
- v1.1 Quality & Expansion — Phases 8-12 (shipped 2026-02-04)
- v1.2 Production Readiness — Phases 13-18 (shipped 2026-03-20, released as `v1.2.0` on 2026-04-02)
- v1.3 RAG Pipeline Refinement — Phases 19-21 (initialized 2026-04-16)

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

<details>
<summary>v1.2 Production Readiness (Phases 13-18) — SHIPPED 2026-03-20</summary>

- [x] Phase 13: Bug Fixes & Test Hygiene (2/2 plans) — completed 2026-02-11
- [x] Phase 14: Test Infrastructure (3/3 plans) — completed 2026-02-11
- [x] Phase 15: Cleanup & DX Foundation (4/4 plans) — completed 2026-03-19
- [x] Phase 16: Documentation & Distribution (3/3 plans) — completed 2026-03-20
- [x] Phase 17: Quality Gates & Release Pipeline (2/2 plans) — completed 2026-03-20
- [x] Phase 18: v1.2 Gap Closure (2/2 plans) — completed 2026-03-20

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

### v1.3 RAG Pipeline Refinement (Active)

**Milestone Goal:** Normalize the RAG pipeline output contract and add automated quality scoring without breaking existing MCP consumers. Deferred from v1.2 per [deliberation](.planning/deliberations/v12-scope-and-priorities.md) — the pipeline works (799 tests, 34/34 recall passing) but output format and scoring are internal refinements that weren't blocking deployment.

**Status:** Initialized on 2026-04-16. Next step: `$gsdr-plan-phase 19`.

- [ ] **Phase 19: Structured RAG Output Contract** — Additive output contract for `process_document_for_rag` and `download_book_to_file`, with dedicated body/footnotes/metadata files and unified linking
- [ ] **Phase 20: Quality Scoring Harness** — Ground-truth scoring runner with machine-readable reports for local validation
- [ ] **Phase 21: CI Reporting & Regression Controls** — Publish quality artifacts in CI, compare against baselines, and decide whether `page_analysis_map` belongs in the scoring/reporting path

### Phase 19: Structured RAG Output Contract
**Goal**: Make the existing multi-file RAG pipeline a stable, additive contract for MCP consumers
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04, RAG-05
**Success Criteria**:
  1. `process_document_for_rag` and `download_book_to_file` keep current path fields while adding structured output paths only as additive data
  2. Structured PDF processing writes deterministic body, footnotes, and metadata files with a single metadata authority describing produced outputs
  3. Metadata links related output files through relative paths rather than implicit filename guessing
  4. Existing MCP protocol, bridge, and handler tests for document processing continue passing after the contract change
**Plans:** 0 plans

### Phase 20: Quality Scoring Harness
**Goal**: Turn the existing ground-truth corpus into a repeatable scoring harness for RAG output quality
**Depends on**: Phase 19 (output contract must be stable before scoring it)
**Requirements**: QUAL-01, QUAL-02
**Success Criteria**:
  1. A scoring runner computes body completeness, structure preservation, and footnote metrics against the ground-truth corpus
  2. Local validation runs emit a machine-readable JSON report with per-document and aggregate quality metrics
  3. The harness is documented well enough to regenerate or refresh the baseline intentionally rather than by accident
**Plans:** 0 plans

### Phase 21: CI Reporting & Regression Controls
**Goal**: Surface RAG quality regressions in CI without turning unstable metrics into noisy blockers
**Depends on**: Phase 20 (harness and report format must exist first)
**Requirements**: QUAL-03, QUAL-04
**Success Criteria**:
  1. CI runs the scoring harness and publishes the JSON report as an artifact
  2. CI compares the latest report against a stored baseline and makes regressions visible in the job output
  3. Threshold behavior defaults to informational mode but can be promoted later without redesigning the pipeline
  4. `page_analysis_map` is either integrated into the scoring/reporting path or explicitly documented as intentionally out of scope for now
**Plans:** 0 plans

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
| 15. Cleanup & DX Foundation | v1.2 | 4/4 | Complete | 2026-03-19 |
| 16. Documentation & Distribution | v1.2 | 3/3 | Complete | 2026-03-20 |
| 17. Quality Gates & Release Pipeline | v1.2 | 2/2 | Complete | 2026-03-20 |
| 18. v1.2 Gap Closure | v1.2 | 2/2 | Complete | 2026-03-20 |
| 19. Structured RAG Output Contract | v1.3 | 0/0 | Pending | — |
| 20. Quality Scoring Harness | v1.3 | 0/0 | Pending | — |
| 21. CI Reporting & Regression Controls | v1.3 | 0/0 | Pending | — |

---

_Last updated: 2026-04-16 — v1.3 initialized and ready for Phase 19 planning_
