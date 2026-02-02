# Project Research Summary

**Project:** Z-Library MCP v1.1 Quality & Expansion
**Domain:** Scholarly document processing & multi-source book retrieval for AI consumption
**Researched:** 2026-02-01
**Confidence:** MEDIUM-HIGH

## Executive Summary

This milestone focuses on dramatically improving text extraction quality for scholarly works while expanding source diversity. The research reveals a **zero-dependency approach** — all five capabilities (margin detection, adaptive DPI, Anna's Archive integration, Node 22 upgrade, AsyncZlib removal) require no new library additions. PyMuPDF already provides spatial text analysis and variable-resolution rendering needed for quality improvements. The existing httpx client handles Anna's Archive API integration.

The recommended approach prioritizes **quality foundations before expansion**. Margin detection and adaptive resolution directly serve the core value proposition (clean text for AI consumption of academic texts). Body text purity unifies all detection modules into a cohesive pipeline. Anna's Archive adds source resilience but carries legal/technical risk worth deferring until quality pipeline is stable. The AsyncZlib removal simplifies architecture by eliminating redundant web scraping paths now that EAPI handles all operations.

**Critical risks:** (1) Margin detection false positives on multi-column layouts could lose body text, (2) AsyncZlib removal may break download flow without obvious test failures due to mocked unit tests, (3) Anna's Archive integration creates book identity model complexity across incompatible ID schemes. Mitigation requires page-level margin modeling (not fixed thresholds), adapter pattern with integration tests for download flow, and BookReference abstraction with source provenance tracking.

## Key Findings

### Recommended Stack

**No new dependencies required for any v1.1 capability.** The current stack (PyMuPDF >=1.26.0, httpx, Node.js) provides all necessary primitives. This milestone is architectural work — new detection modules, source abstraction layer, and code simplification.

**Core technologies:**
- **PyMuPDF >=1.26.0**: Spatial text analysis (`get_text("dict")` with bbox coordinates), variable DPI rendering (`get_pixmap(matrix)`), region clipping — everything needed for margin detection and adaptive resolution already exists
- **httpx**: Already vendored in zlibrary fork; handles Anna's Archive REST API with no new dependency
- **Node.js 22 LTS**: Upgrade path from 18 is straightforward (10-15% V8 perf gain, stable fetch API, security patches until April 2027); codebase uses standard APIs with minimal breaking change risk
- **EAPIClient**: AsyncZlib download path already delegates to EAPI; removing AsyncZlib web scraping simplifies to 77% less code (406→92 lines in venv-manager.ts) with zero functional loss

**Key architectural insight:** The bottleneck isn't libraries — it's detection logic quality. Existing tools provide low-level primitives (text coordinates, font metadata, DPI control). Value comes from intelligent use: page-level margin models instead of fixed thresholds, cross-page pattern analysis for running headers, per-source retry configuration.

### Expected Features

Research identified four capability clusters with clear must-have vs defer boundaries:

**Must have for v1.1 (table stakes):**
- **Margin zone detection + scholarly reference patterns** — Stephanus numbers (Plato), Bekker numbers (Aristotle), line numbers; without this, margin text leaks into body as noise
- **Body text purity pipeline** — Unified filter composing all detection modules (footnotes, headings, TOC, page numbers, margins); the integration feature that delivers clean body text
- **Anna's Archive search + download** — Second book source with configurable API key/base URL; provides source resilience when Z-Library unavailable

**Should have (differentiators):**
- **Adaptive resolution (page-level DPI selection)** — Quality improvement but not new capability; text-heavy = 150-200 DPI, fine print = 300 DPI, based on font size analysis
- **Auto-detect margin zone widths per document** — Handles varied publishers (Loeb uses outer margins, Oxford uses inner) without manual config
- **Best-format selection across sources** — Prefer EPUB over PDF when same book available from multiple sources

**Defer to v2+ (anti-features to avoid):**
- **Critical apparatus parsing** — Enormously complex (variants, sigla, nested refs); just detect and separate, don't parse
- **GROBID integration** — ML-based zone classification for academic papers; high complexity, defer until PyMuPDF4LLM integration proven insufficient
- **Open Library integration** — Legal public domain source; adds little beyond AA which aggregates it
- **Super-resolution upscaling** — Heavy ML dependency, marginal gain over simple DPI increase

**Build order (from FEATURES.md dependency analysis):**
1. Adaptive Resolution (independent, improves OCR for all downstream)
2. Margin Detection (needed by Body Text Purity)
3. Body Text Purity (composes all detectors)
4. Anna's Archive (independent but has legal/technical risk worth deferring)

### Architecture Approach

**Layered integration without structural disruption.** The existing architecture cleanly accommodates all five capabilities through targeted module additions:

**Major components:**
1. **Detection Layer** (`lib/rag/detection/`) — Add `margins.py` alongside existing `footnotes.py`, `headings.py`, `page_numbers.py`, `toc.py`, `front_matter.py`; margins runs early to annotate blocks (not remove), downstream stages filter tagged content
2. **Quality Pipeline** (`lib/rag/quality/pipeline.py`) — Adaptive resolution adds DPI calculation helper to existing `ocr_stage.py`; uses Stage 1 quality_score + Stage 2 xmark results to determine optimal DPI (no new pipeline stage)
3. **Source Abstraction** (`lib/sources/` new package) — `BookSource` protocol defines interface; `zlibrary.py` wraps existing EAPIClient; `annas_archive.py` implements same interface; `registry.py` manages routing
4. **Download Extraction** (`lib/sources/download.py`) — Extract AsyncZlib.download_book() streaming logic (~25 lines) to standalone function using EAPIClient; removes AsyncZlib dependency from 7 modules
5. **Node.js Layer** (minimal changes) — `src/index.ts` adds optional `source` parameter to Zod schemas; `src/lib/zlibrary-api.ts` passes through to Python bridge

**Key design decisions:**
- **Margin detection runs BEFORE block formatting**, not as quality pipeline stage (pipeline operates on individual PageRegions; margin detection filters which blocks become regions)
- **Annotate-don't-remove pattern** — Margin detector tags blocks but leaves them in stream; downstream stages decide inclusion based on tags
- **Source provenance tracking** — BookReference abstraction carries source identity (Z-Lib vs AA) + original ID + metadata to handle incompatible ID schemes
- **Gradual AsyncZlib removal** — Adapter first (present AsyncZlib interface, delegate to EAPIClient), then swap internals, then remove adapter (not big bang)

**Build order (from ARCHITECTURE.md dependencies):**
```
Phase A (parallel):
  - Node 20+ upgrade (package.json, types, test isolation)
  - Margin detection module + data models
  - Adaptive resolution (DPI helper in ocr_stage.py)

Phase B (extract before abstract):
  - Download extraction (AsyncZlib → standalone function)
  - AsyncZlib removal from python_bridge.py

Phase C (depends on Phase B):
  - Source abstraction layer (base, registry)
  - Z-Library adapter (wraps EAPIClient)
  - Anna's Archive adapter (research spike for API patterns)

Phase D (depends on Phase A margin detection):
  - Integrate margin detection into orchestrator_pdf.py
  - Update _format_pdf_markdown to use margin classification
```

### Critical Pitfalls

Research identified 11 pitfalls; top 5 by severity and phase relevance:

1. **Margin Detection False Positives (P-02, CRITICAL)** — Multi-column layouts, indented paragraphs, and scanned documents with skew cause bbox-based heuristics to misclassify body text as marginal. **Prevention:** Build page-level margin model (analyze x-position distribution, identify clusters) instead of fixed thresholds; test with single-column, two-column, scanned-with-skew, and legal/line-numbered documents; expose confidence scores.

2. **AsyncZlib Removal Breaks Download Silently (P-01, CRITICAL)** — `client_manager.py` and 6 other modules reference AsyncZlib API (search, fetch, download, login). EAPIClient has different method surface. Swapping import without mapping call sites produces runtime failures that unit tests (which mock clients) won't catch. **Prevention:** Map full AsyncZlib API surface across all 7 files; write adapter presenting AsyncZlib interface delegating to EAPIClient; add integration test exercising real download path; deprecate gradually (adapter → swap internals → remove adapter).

3. **Anna's Archive Book Identity Complexity (P-03, CRITICAL)** — Z-Library and AA use different ID schemes (Z-Lib ID vs MD5 hash), metadata schemas, search structures. Merging results without unified identity model creates duplicates in search, broken "download by ID" flows. **Prevention:** Design `BookReference` abstraction carrying source provenance; never expose raw source IDs to MCP tools (use composite identifier encoding source); implement deduplication at merge layer using ISBN/MD5; make source explicit in responses.

4. **Adaptive DPI Coordinate Space Confusion (P-04, HIGH)** — PyMuPDF `get_text("dict")` returns point-based coordinates (DPI-independent, 72 DPI reference), but `get_pixmap(dpi=X)` returns pixel coordinates. Mixing these breaks existing footnote detection which uses absolute values from text extraction. Changing DPI silently regresses quality metrics. **Prevention:** Audit pipeline for coordinate space assumptions; normalize ALL coordinates to point-space before detection; add regression test (process same PDF at 72, 150, 300 DPI, assert identical detection within tolerance).

5. **Margin/Footnote Pipeline Interference (P-06, HIGH)** — Both systems consume same text blocks and make spatial assumptions. If margin content stripped before footnote detection, margin footnotes are lost. If footnote detection runs first, margin annotations may be misclassified as footnote definitions. **Prevention:** Define explicit pipeline stages with documented contracts in `orchestrator_pdf.py`; margin detection ANNOTATES blocks (tags as "margin") but doesn't remove; downstream stages decide handling; integration test on PDFs with margin footnotes (common in legal/classical texts).

**Legal/TOS consideration (P-03 subset):** Anna's Archive lost multiple domains (org, se) in January 2026 due to court injunction; service availability is inconsistent. Make AA opt-in source (`ANNAS_ARCHIVE_ENABLED=true` env var) so users make their own legal determination; document landscape in ADR; graceful degradation when unavailable (return Z-Library-only results, not error).

## Implications for Roadmap

Based on research, suggested **5-phase structure** prioritizing quality foundations before expansion:

### Phase 1: Foundation Cleanup & Node Upgrade
**Rationale:** Remove technical debt and upgrade runtime before adding complexity. Node 18 is EOL (no security patches); AsyncZlib is redundant (EAPI handles all operations). Clean foundation prevents compounding issues when building detection features.

**Delivers:**
- Node 22 LTS environment with security patches until April 2027
- Simplified download flow (AsyncZlib removed, standalone EAPI download function)
- Updated type definitions and CI configuration
- 77% code reduction in venv-manager.ts (406→92 lines)

**Stack elements:** Node 22 LTS, EAPIClient (existing), download extraction pattern

**Avoids:** P-01 (AsyncZlib removal breaking downloads), P-10 (auth lifecycle mismatch), P-05 (Node upgrade ESM/Jest breakage)

**Research flag:** Standard upgrade patterns; no deep research needed. Follow Node.js 18→22 migration guides and AsyncZlib→EAPIClient API mapping.

---

### Phase 2: Margin Detection & Scholarly References
**Rationale:** Core quality feature for scholarly texts. Needed before Body Text Purity (Phase 4) can unify all detection modules. Independent of other features, can proceed after Phase 1.

**Delivers:**
- `lib/rag/detection/margins.py` module with spatial analysis
- Stephanus number pattern recognition (Plato, e.g. "514a")
- Bekker number pattern recognition (Aristotle, e.g. "1094a1")
- Line number detection (poetry, legal texts, code listings)
- Margin content metadata in output headers (preserves scholarly refs without polluting body)
- Page-level margin model (not fixed thresholds)

**Addresses:**
- FEATURES.md table stakes: margin zone detection, Stephanus/Bekker patterns, line numbers, margin exclusion from body
- ARCHITECTURE.md: Detection layer addition, annotate-don't-remove pattern

**Avoids:** P-02 (false positives on multi-column), P-06 (margin/footnote interference), P-08 (line numbers confused with page numbers)

**Research flag:** Needs research phase for Stephanus/Bekker pattern validation and margin zone width detection algorithms. Sparse documentation on automated scholarly reference extraction. Budget 3-5 days for pattern research and multi-layout testing.

---

### Phase 3: Adaptive Resolution Pipeline
**Rationale:** Independent quality improvement (doesn't block other features). Improves OCR accuracy for all downstream processing. Can run parallel with Phase 2 but sequenced for focus.

**Delivers:**
- DPI selection logic in `lib/rag/quality/ocr_stage.py`
- Page-level quality analysis determining optimal resolution
- Adaptive resolution config in `QualityPipelineConfig` (min_dpi, max_dpi, default_dpi, adaptive_resolution flag)
- Performance budget awareness (quality vs speed tradeoff)
- Text-heavy pages: 150-200 DPI; fine print/footnotes: 300 DPI; image-heavy: 300 DPI

**Stack elements:** PyMuPDF `get_pixmap(matrix=fitz.Matrix(scale, scale))`, existing quality pipeline (Stages 1-3)

**Implements:** Quality pipeline enhancement (ARCHITECTURE.md Question 2)

**Avoids:** P-04 (coordinate space confusion), P-09 (performance regression without opt-out)

**Research flag:** Standard PyMuPDF patterns; no deep research needed. Follow OCRmyPDF cookbook and Tesseract optimal DPI guidance.

---

### Phase 4: Body Text Purity Integration
**Rationale:** Depends on margin detection (Phase 2). Unifies all existing detection modules (footnotes, headings, TOC, page numbers, front matter) with new margin detection into cohesive pipeline. The integration feature delivering clean body text for AI consumption.

**Delivers:**
- Unified non-body content filter composing all detectors
- Running head removal (cross-page repeated text)
- Confidence-based inclusion/exclusion thresholds
- Structured output mode (body + metadata separately)
- Regression test suite ensuring no body text loss

**Addresses:**
- FEATURES.md table stakes: unified filter, running head removal, structured output, regression tests
- FEATURES.md differentiators: per-paragraph confidence scores, PyMuPDF4LLM integration (if proven valuable)

**Avoids:** False positive filtering (losing body text worse than including noise)

**Research flag:** Minimal research needed; primarily integration work. PyMuPDF4LLM evaluation may need 1-2 days if integration pursued.

---

### Phase 5: Anna's Archive Multi-Source Integration
**Rationale:** Defer until quality pipeline stable (Phases 2-4 complete). Source expansion adds resilience but carries legal/technical risk. Domain instability and TOS concerns make this lowest priority despite user value.

**Delivers:**
- Source abstraction layer (`lib/sources/` package with BookSource protocol)
- Anna's Archive adapter implementing search + download
- Unified search results merging Z-Library + AA
- BookReference abstraction with source provenance
- Configurable API key (`ANNAS_ARCHIVE_API_KEY`) and base URL
- Graceful degradation when source unavailable

**Stack elements:** httpx (existing), source registry pattern, REST API integration

**Addresses:**
- FEATURES.md table stakes: AA search integration, unified results, source attribution, download from AA
- FEATURES.md differentiators: automatic fallback, best-format selection, source health monitoring

**Avoids:** P-03 (book identity model complexity), P-07 (rate limit mismatch), P-11 (API instability)

**Research flag:** CRITICAL — Needs research phase for Anna's Archive API patterns (no official docs), rate limiting behavior, error response patterns, domain discovery. Study iosifache/annas-mcp reference implementation. Legal/TOS review required. Budget 5-7 days for API reverse engineering and integration spike.

---

### Phase Ordering Rationale

**Dependencies drive structure:**
- Phase 1 (cleanup) must precede everything (AsyncZlib removal unblocks source abstraction; Node upgrade prevents compounding issues)
- Phase 2 (margins) must precede Phase 4 (body purity integration)
- Phase 3 (adaptive DPI) is independent; sequenced after Phase 2 for focus but could run parallel
- Phase 5 (Anna's Archive) deferred to end due to legal/technical risk and independence from quality pipeline

**Risk mitigation:**
- Front-load foundation cleanup (Phase 1) to prevent compounding AsyncZlib issues
- Build quality features (Phases 2-4) before expansion (Phase 5) so core value is stable
- Isolate high-risk Anna's Archive work to final phase when pipeline proven

**Architecture alignment:**
- Phases 1-2 map to ARCHITECTURE.md "Phase A + B" (cleanup + new modules)
- Phase 3 maps to ARCHITECTURE.md "Phase A adaptive resolution"
- Phase 4 maps to ARCHITECTURE.md "Phase D" (integration)
- Phase 5 maps to ARCHITECTURE.md "Phase C" (source abstraction)

### Research Flags

**Phases needing deeper research during planning:**

- **Phase 2 (Margin Detection):** Scholarly reference pattern extraction is niche domain with sparse documentation. Need research phase for Stephanus/Bekker regex patterns, margin zone width detection algorithms, multi-layout testing strategies. Estimated 3-5 days.

- **Phase 5 (Anna's Archive):** No official API documentation; integration requires reverse engineering from iosifache/annas-mcp or RapidAPI wrapper. Legal/TOS landscape unclear (January 2026 domain seizures). Rate limiting and error patterns unknown. Estimated 5-7 days for API research, legal review, integration spike.

**Phases with standard patterns (skip research-phase):**

- **Phase 1 (Node Upgrade & AsyncZlib Removal):** Well-documented migration paths. Node 18→22 has official guides (Auth0, HeroDevs). AsyncZlib→EAPIClient mapping is codebase analysis, not external research.

- **Phase 3 (Adaptive Resolution):** Standard PyMuPDF pixmap rendering patterns. OCRmyPDF cookbook and Tesseract DPI guidance provide clear recipes.

- **Phase 4 (Body Text Purity):** Integration work combining existing modules. PyMuPDF4LLM evaluation may need brief research but not full research-phase invocation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Zero new dependencies; all capabilities use existing PyMuPDF/httpx/Node primitives. Research directly analyzed codebase and confirmed PyMuPDF APIs exist (get_text dict mode, get_pixmap matrix, clip parameter). |
| Features | **MEDIUM-HIGH** | Table stakes vs differentiators clear from domain analysis. Build order validated via dependency mapping. Margin detection patterns (Stephanus/Bekker) confirmed from authoritative sources (Oxford, Proofed). Anti-features identified from complexity research. |
| Architecture | **HIGH** | Based on direct codebase inspection (orchestrator_pdf.py, quality/pipeline.py, python_bridge.py, libasync.py, eapi.py). Integration points identified with line-level precision. Component boundaries map cleanly to existing structure. |
| Pitfalls | **HIGH** | Identified from codebase analysis (coordinate space assumptions, pipeline ordering, client_manager dependencies) and domain knowledge (margin detection false positives, book identity complexity). Severity ratings calibrated to actual breakage risk. |

**Overall confidence:** **MEDIUM-HIGH**

Confidence is high on stack (no new deps, existing APIs confirmed) and architecture (codebase analysis with line references). Moderate-high on features due to scholarly reference pattern research being secondary sources (Oxford, Proofed) rather than direct academic standards documents. Pitfall severity is high-confidence based on code inspection.

### Gaps to Address

**Gap 1: Anna's Archive API contract unknown**
- **Issue:** No official documentation; integration feasibility unclear until API reverse engineered
- **Handling:** Research phase (Phase 5) must precede planning. Budget 2 days for API exploration spike. If API proves unstable/unusable, pivot to Z-Library-only for v1.1 and defer AA to v1.2.
- **Decision point:** After research phase, evaluate API stability score (0-10). If <6, defer to v1.2.

**Gap 2: PyMuPDF4LLM value proposition vs custom pipeline**
- **Issue:** FEATURES.md identifies PyMuPDF4LLM as differentiator for body text purity, but unclear if it adds value over composing existing detectors
- **Handling:** Phase 4 planning includes 1-2 day evaluation spike. Test PyMuPDF4LLM on scholarly PDFs with margin content. If precision <95% or recall <90% vs custom pipeline, skip integration.
- **Decision point:** During Phase 4 planning, compare PyMuPDF4LLM output to custom pipeline on 10 test PDFs. Proceed with integration only if quality metrics superior.

**Gap 3: Margin zone width detection algorithm selection**
- **Issue:** Research identified need for page-level margin model (not fixed thresholds) but specific algorithm unclear (k-means clustering on x-positions? DBSCAN? Histogram analysis?)
- **Handling:** Phase 2 research phase must include algorithm selection. Test 3 approaches on varied layouts (single-column, two-column, narrow-margin, wide-margin). Select algorithm with highest precision on multi-layout test suite.
- **Decision point:** During Phase 2 research, compare clustering approaches and select before implementation begins.

**Gap 4: EAPIClient auth lifecycle compatibility**
- **Issue:** PITFALLS.md (P-10) flags potential auth lifecycle mismatch between AsyncZlib and EAPIClient
- **Handling:** Phase 1 planning begins with EAPIClient auth flow audit (`zlibrary/src/zlibrary/eapi.py` login method). Map to AsyncZlib's session cookie pattern. Identify gaps before adapter implementation.
- **Validation:** Integration test must exercise full auth flow (login → search → download) before AsyncZlib removal declared complete.

## Sources

### Primary (HIGH confidence)
- **Direct codebase analysis** — `lib/rag/quality/pipeline.py` (3-stage waterfall structure), `lib/rag/detection/` modules, `zlibrary/src/zlibrary/libasync.py` (AsyncZlib download delegation), `zlibrary/src/zlibrary/eapi.py` (EAPIClient API surface), `lib/python_bridge.py` (client management), `lib/client_manager.py` (AsyncZlib dependencies)
- **PyMuPDF official documentation** — [Text extraction](https://pymupdf.readthedocs.io/en/latest/app1.html) (block coordinates, dict mode), [Page API](https://pymupdf.readthedocs.io/en/latest/page.html) (clip parameter, get_pixmap), [Text recipes](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
- **Node.js release notes** — [Node 22 announcement](https://nodejs.org/en/blog/announcements/v22-release-announce), breaking changes documented
- **Scholarly reference standards** — [Oxford Scholarly Editions Bekker navigation](https://www.oxfordscholarlyeditions.com/newsitem/221/using-bekker-numbers-to-navigate-the-works-of-aristotle), [Proofed citing guide](https://proofed.com/writing-tips/citing-plato-and-aristotle-stephanus-and-bekker-numbers/)

### Secondary (MEDIUM confidence)
- **PyMuPDF community discussions** — [get_text coordinates Q&A](https://github.com/pymupdf/PyMuPDF/discussions/2128), [header/footer removal](https://github.com/pymupdf/PyMuPDF/discussions/2259)
- **Node.js migration guides** — [Auth0 Node 18→22 migration](https://auth0.com/docs/troubleshoot/product-lifecycle/deprecations-and-migrations/migrate-nodejs-22), [HeroDevs Node 18 EOL analysis](https://www.herodevs.com/blog-posts/node-js-18-end-of-life-breaking-changes-aws-deadlines-and-what-to-do-next)
- **Anna's Archive references** — [iosifache/annas-mcp GitHub](https://github.com/iosifache/annas-mcp) (reference MCP server), [RapidAPI wrapper](https://rapidapi.com/tribestick-tribestick-default/api/annas-archive-api), [SearXNG engine docs](https://docs.searxng.org/dev/engines/online/annas_archive.html)
- **OCR optimization** — [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html), [Tesseract optimal DPI discussion](https://groups.google.com/g/tesseract-ocr/c/Wdh_JJwnw94/m/24JHDYQbBQAJ)
- **PyMuPDF4LLM** — [Official documentation](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)

### Tertiary (LOW confidence, needs validation)
- **pdf_header_and_footer_detector** — [GitHub reference implementation](https://github.com/gentrith78/pdf_header_and_footer_detector) (pattern detection approach)
- **DeepSeek OCR adaptive resolution** — [Blog post](https://sparkco.ai/blog/deepseek-ocr-maximizing-pdf-text-extraction-accuracy) (single source, needs validation)

---
*Research completed: 2026-02-01*
*Ready for roadmap: yes*
