# Requirements: Z-Library MCP v1.1 Quality & Expansion

**Defined:** 2026-02-01
**Core Value:** Reliable, maintainable MCP server for Z-Library book access

## v1.1 Requirements

### Infrastructure

- [ ] **INFRA-01**: Upgrade to Node 22 LTS (update engines field, CI matrix, Dockerfile)
- [ ] **INFRA-02**: Update env-paths to v4.0 (unlocked by Node 22)
- [ ] **INFRA-03**: Remove AsyncZlib legacy download client (route all downloads through EAPIClient)
- [ ] **INFRA-04**: Fix Docker numpy/Alpine compilation issue in production Dockerfile
- [ ] **INFRA-05**: Improve EAPI booklist browsing (beyond current graceful degradation)
- [ ] **INFRA-06**: Improve EAPI full-text search (beyond current regular-search fallback)

### Margin Detection

- [ ] **MARG-01**: Detect margin zones in PDFs using PyMuPDF bbox coordinates
- [ ] **MARG-02**: Recognize Stephanus numbering patterns (e.g., 231a, 245b-c)
- [ ] **MARG-03**: Recognize Bekker numbering patterns (e.g., 1094a1, 1140b5)
- [ ] **MARG-04**: Detect line numbers in poetry, legal texts, and critical editions
- [ ] **MARG-05**: Detect and extract marginal notes, glosses, and cross-references
- [ ] **MARG-06**: Adapt margin zone widths across different publisher layouts
- [ ] **MARG-07**: Preserve margin content as structured annotations in markdown output

### Adaptive Resolution

- [ ] **DPI-01**: Page-level DPI selection based on content density (150/300 DPI)
- [ ] **DPI-02**: Region-level DPI targeting (higher resolution for footnotes, margin text, small fonts)
- [ ] **DPI-03**: Optimal DPI determined by text pixel height analysis (Tesseract 30-33px target)

### Body Text Purity

- [ ] **BODY-01**: Unified detection pipeline composing all detectors (footnotes, margins, headings, page numbers, TOC)
- [ ] **BODY-02**: Non-body content clearly separated in markdown output
- [ ] **BODY-03**: Confidence scoring for detection decisions

### Anna's Archive

- [ ] **ANNA-01**: Research spike determining API feasibility, endpoints, auth, rate limits, legal considerations
- [ ] **ANNA-02**: Configurable base URL for Anna's Archive (domain instability mitigation)
- [ ] **ANNA-03**: Fallback search when Z-Library is rate-limited or unavailable
- [ ] **ANNA-04**: Source indicator in search results (which source returned each result)

## v2 Requirements

Deferred to future milestone.

- **FEAT-01**: Download queue management (DL-001)
- **FEAT-02**: Search result caching layer
- **FEAT-03**: Semantic chunking for RAG pipeline
- **FEAT-04**: OS keychain for credentials
- **FEAT-05**: Unified search across both sources (merged result set)
- **FEAT-06**: PyMuPDF4LLM evaluation and potential integration

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full Anna's Archive feature parity | Too large — v1.1 is fallback only |
| Automatic source selection without user control | Users need transparency on which source |
| Rewrite Python bridge in TypeScript | Python has better doc-processing libs |
| ML-based text recovery | Research task, not product scope |
| Full Zod 4 migration | Deferred from v1.0 — Zod 3.25.x bridge works |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| INFRA-04 | — | Pending |
| INFRA-05 | — | Pending |
| INFRA-06 | — | Pending |
| MARG-01 | — | Pending |
| MARG-02 | — | Pending |
| MARG-03 | — | Pending |
| MARG-04 | — | Pending |
| MARG-05 | — | Pending |
| MARG-06 | — | Pending |
| MARG-07 | — | Pending |
| DPI-01 | — | Pending |
| DPI-02 | — | Pending |
| DPI-03 | — | Pending |
| BODY-01 | — | Pending |
| BODY-02 | — | Pending |
| BODY-03 | — | Pending |
| ANNA-01 | — | Pending |
| ANNA-02 | — | Pending |
| ANNA-03 | — | Pending |
| ANNA-04 | — | Pending |

**Coverage:**
- v1.1 requirements: 23 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 23

---
*Requirements defined: 2026-02-01*
*Last updated: 2026-02-01 after initial definition*
