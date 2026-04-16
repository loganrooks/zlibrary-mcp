# Requirements: Z-Library MCP v1.3

**Defined:** 2026-04-16
**Core Value:** Reliable, maintainable MCP server for book access — production-ready infrastructure with high-quality scholarly text extraction

## v1 Requirements

Requirements for the v1.3 RAG Pipeline Refinement milestone. This scope picks up the deferred RAG-output and quality-scoring work from v1.2 without reopening already-shipped distribution work.

### Structured Output

- [ ] **RAG-01**: User can process a document into a predictable multi-file bundle that includes body text, footnotes when present, and metadata outputs.
  - *Motivation:* `deliberation: .planning/deliberations/v12-scope-and-priorities.md`
- [ ] **RAG-02**: User can read detected footnotes from a dedicated output file ordered by page and marker so footnotes are independently consumable.
  - *Motivation:* `deliberation: .planning/deliberations/v12-scope-and-priorities.md`
- [ ] **RAG-03**: User can rely on a single metadata authority that describes document metadata, processing metadata, and produced output files.
  - *Motivation:* `user: continue with next steps after v1.2 shipped`
- [ ] **RAG-04**: User can discover related output files through relative links in metadata rather than guessing filename conventions.
  - *Motivation:* `deliberation: .planning/deliberations/v12-scope-and-priorities.md`
- [ ] **RAG-05**: Existing `process_document_for_rag` and `download_book_to_file` consumers continue working through additive response changes only.
  - *Motivation:* `user: continue with next steps after v1.2 shipped`

### Quality Scoring

- [ ] **QUAL-01**: Maintainer can compute precision/recall-style quality metrics for body extraction, structure preservation, and footnotes against the ground-truth corpus.
  - *Motivation:* `deliberation: .planning/deliberations/v12-scope-and-priorities.md`
- [ ] **QUAL-02**: Maintainer can emit a machine-readable JSON quality report from the scoring harness for local validation runs.
  - *Motivation:* `user: continue with next steps after v1.2 shipped`
- [ ] **QUAL-03**: CI can publish the quality report artifact and compare it against a stored baseline so regressions are visible on every run.
  - *Motivation:* `deliberation: .planning/deliberations/v12-scope-and-priorities.md`
- [ ] **QUAL-04**: Quality regression thresholds are configurable and default to informational mode until the baseline proves stable.
  - *Motivation:* `deliberation: .planning/deliberations/v12-scope-and-priorities.md`

## v2 Requirements

Deferred beyond v1.3. Tracked now so they do not leak back into the active roadmap accidentally.

### Quality Enhancements

- **QUAL-F01**: Quality regression checks block PRs once the baseline is stable enough to trust as a hard gate
- **QUAL-F02**: CI publishes trend views over time instead of only per-run JSON artifacts
- **QUAL-F03**: Semantic chunking is added for embedding-model-ready RAG output

### RAG Diagnostics

- **RAG-F01**: `page_analysis_map`-derived diagnostics become part of the public metadata contract if quality-scoring evidence shows they help downstream consumers

## Out of Scope

| Feature | Reason |
|---------|--------|
| Promoting `search_multi_source` to a public MCP tool | Already shipped and documented; not real v1.3 work |
| Breaking response-shape changes for `process_document_for_rag` or `download_book_to_file` | Existing clients and tests already depend on the current path fields |
| PR-blocking quality gates on day one | Baseline needs to stabilize before turning informational metrics into merge blockers |
| General RAG feature expansion beyond output/scoring | This milestone is refinement, not a new capability grab-bag |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RAG-01 | Phase 19 | Pending |
| RAG-02 | Phase 19 | Pending |
| RAG-03 | Phase 19 | Pending |
| RAG-04 | Phase 19 | Pending |
| RAG-05 | Phase 19 | Pending |
| QUAL-01 | Phase 20 | Pending |
| QUAL-02 | Phase 20 | Pending |
| QUAL-03 | Phase 21 | Pending |
| QUAL-04 | Phase 21 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 after starting milestone v1.3*
