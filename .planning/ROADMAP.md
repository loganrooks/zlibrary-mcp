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

**Status:** Phase 19 completed on 2026-04-16. Phases 20-21 reviewed and revised
2026-07-24 — see [the review](../claudedocs/architecture/phase-20-21-review-2026-07-24.md)
for why, and [the health assessment](../claudedocs/architecture/repo-health-and-roadmap-2026-07-24.md)
for the wider context. Next step: `$gsdr-plan-phase 20` against the revised criteria.

- [x] **Phase 19: Structured RAG Output Contract** — Additive output contract for `process_document_for_rag` and `download_book_to_file`, with dedicated body/footnotes/metadata files and unified linking (completed 2026-04-16)
- [ ] **Phase 20: Quality Scoring Harness** — Extract and aggregate the metrics that already exist, add structure preservation, resolve the orphaned `run_rag_tests.py` (revised 2026-07-24)
- [ ] **Phase 21: CI Reporting & Regression Controls** — Scheduled quality scoring with baseline comparison and a rolling regression issue (revised 2026-07-24)

### Phase 19: Structured RAG Output Contract
**Goal**: Make the existing multi-file RAG pipeline a stable, additive contract for MCP consumers
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: RAG-01, RAG-02, RAG-03, RAG-04, RAG-05
**Success Criteria**:
  1. `process_document_for_rag` and `download_book_to_file` keep current path fields while adding structured output paths only as additive data
  2. Structured PDF processing writes deterministic body, footnotes, and metadata files with a single metadata authority describing produced outputs
  3. Metadata links related output files through relative paths rather than implicit filename guessing
  4. Existing MCP protocol, bridge, and handler tests for document processing continue passing after the contract change
**Plans:** 2/2 plans complete

### Phase 20: Quality Scoring Harness
**Goal**: Aggregate the quality metrics that already exist into a repeatable scoring run, and add the one metric that does not exist
**Depends on**: Phase 19 (output contract must be stable before scoring it)
**Requirements**: QUAL-01, QUAL-02
**Revised** 2026-07-24 after review — see [phase-20-21-review-2026-07-24.md](../claudedocs/architecture/phase-20-21-review-2026-07-24.md).
Roughly 60% of the original criteria were already implemented and unacknowledged:
`test_recall_baseline.py` computes body-text recall over 17 documents, footnote tests assert
against v3 ground truth, and `scripts/run_rag_tests.py` already emits a JSON quality report.
The phase is reframed as extraction and aggregation, not new construction.
**Success Criteria**:
  1. `scripts/run_rag_tests.py` is resolved before new work begins — retired, or its download step split from its scoring step so the scoring is reused. It currently requires live downloads (so it cannot run in CI or offline) and scores through the legacy `lib.rag_processing` facade rather than `lib.rag.orchestrator_pdf`, giving two scoring paths that can disagree. Its 25 tests are removed or repointed in the same change.
  2. Existing metrics are extracted into callable functions (`lib/rag/quality/scoring.py`) that the current tests call, rather than reimplemented alongside them — the existing tests should get shorter, not longer
  3. Structure preservation is added as a metric, including the ground truth it needs, which does not exist yet — this is the phase's real cost
  4. Local validation runs emit a machine-readable JSON report with per-document and aggregate metrics, reporting **trend-capable scores rather than pass/fail**, since quality can degrade several percent without crossing any existing threshold
  5. The report states how many documents were scored and how many were skipped with reasons, and the runner exits non-zero when the scored count falls below an expected minimum. Corpus PDFs are Git LFS objects and the suite now *skips* on unhydrated pointers, so a harness without this check would score zero documents, find no regressions, and report a clean run — a false green that is worse than no gate because it is trusted.
  6. The harness is documented well enough to regenerate or refresh the baseline intentionally rather than by accident
  7. Whether `page_analysis_map` belongs in the report is decided here, since the answer changes what the report contains
**Plans:** 0 plans

### Phase 21: CI Reporting & Regression Controls
**Goal**: Surface RAG quality regressions on a cadence without turning unstable metrics into noisy blockers
**Depends on**: Phase 20 (harness and report format must exist first)
**Requirements**: QUAL-03, QUAL-04
**Revised** 2026-07-24 after review — trigger changed from per-push to scheduled.
The full pytest suite already takes 11m43s on the runner and the corpus tests are 119 of
them; adding corpus scoring to every push grows the slowest job for a signal that is
inherently trend-shaped rather than per-commit.
**Success Criteria**:
  1. The scoring harness runs on a **schedule** with `workflow_dispatch` for on-demand runs before a release, reusing the pattern established by `.github/workflows/upstream-check.yml` — not on every push
  2. The job publishes the JSON report as an artifact and compares it against a stored baseline, making movement visible in the job output
  3. Informational-by-default is implemented as a rolling issue rather than threshold plumbing — a scheduled job that files an issue *is* informational mode, and can be promoted to blocking later without redesign
  4. The job asserts the scored document count matches the corpus size, so an LFS or checkout misconfiguration fails loudly instead of reporting a clean run over zero documents
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
| 19. Structured RAG Output Contract | v1.3 | 2/2 | Complete   | 2026-04-16 |
| 20. Quality Scoring Harness | v1.3 | 0/0 | Pending | — |
| 21. CI Reporting & Regression Controls | v1.3 | 0/0 | Pending | — |

---

_Last updated: 2026-04-16 — Phase 19 completed, Phase 20 ready for planning_
