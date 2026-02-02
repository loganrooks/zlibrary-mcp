# Domain Pitfalls

**Project:** Z-Library MCP v1.1 Quality & Expansion
**Researched:** 2026-02-01
**Overall confidence:** HIGH (based on codebase inspection + domain knowledge)

---

## Critical Pitfalls

### P-01: AsyncZlib Removal Breaks Download Path Without Obvious Test Failures
**Severity:** CRITICAL
**Phase:** AsyncZlib deprecation / EAPIClient migration

**What goes wrong:** `client_manager.py` imports `AsyncZlib` directly. Six other modules in `lib/` reference it. The download flow (search -> fetch -> download) uses AsyncZlib's paginator and `book.fetch()` API. EAPIClient likely has a different method surface. Swapping the import without mapping every call site produces runtime failures that unit tests with mocked clients will not catch.

**Why it happens:** The vendor fork exposes both clients but they are not interface-compatible. Tests mock the client, so they pass even when the real client changes.

**Warning signs:**
- Unit tests pass but integration/manual tests fail
- `AttributeError` on EAPIClient instances at runtime
- Download works for search but fails on `fetch()` or `download()`

**Prevention:**
1. Map the full AsyncZlib API surface used across all 7 files (`client_manager.py`, `python_bridge.py`, `enhanced_metadata.py`, `booklist_tools.py`, `author_tools.py`, `term_tools.py`, `advanced_search.py`)
2. Write an adapter/shim that presents the AsyncZlib interface but delegates to EAPIClient
3. Add at least one integration test that exercises the real download path (can be skipped in CI but must exist)
4. Deprecate gradually: adapter first, then swap internals, then remove adapter

**Detection:** `grep -rn "await.*\.\(search\|fetch\|download\|login\|profile\)" lib/` to find every method call on the client object.

---

### P-02: Margin Detection Misidentifies Body Text as Marginal Content
**Severity:** CRITICAL
**Phase:** Margin/scholarly numbering detection

**What goes wrong:** Margin notes, line numbers, and scholarly apparatus appear in the same spatial regions as legitimate body text in multi-column layouts, narrow-margin academic papers, and scanned books with skew. A bbox-based heuristic (`x < threshold` = margin) produces false positives on indented paragraphs and false negatives on wide-margin annotations.

**Why it happens:** The existing detection system (`lib/rag/detection/`) uses font size and spatial position for footnotes. Extending this to margins seems straightforward but margin content has no consistent font-size differential like footnotes do.

**Warning signs:**
- First few test PDFs work perfectly, then real-world academic PDFs fail
- Paragraph first-lines get classified as margin notes
- Two-column layouts lose an entire column

**Prevention:**
1. Do NOT use a single x-coordinate threshold. Build a page-level margin model: analyze the distribution of text block x-positions across the full page, identify clusters, and define margins relative to the dominant body cluster.
2. Test with at minimum: single-column, two-column, scanned-with-skew, and legal/line-numbered documents.
3. Add a confidence score to margin detections and expose it (don't silently strip content).
4. Keep margin detection as a separate pipeline stage that can be disabled, not baked into core text extraction.

---

### P-03: Anna's Archive Integration Creates Inconsistent Book Identity Model
**Severity:** CRITICAL
**Phase:** Anna's Archive source integration

**What goes wrong:** Z-Library and Anna's Archive use different ID schemes, metadata schemas, and search result structures. Merging results from both sources without a unified book identity model leads to duplicates in search results, broken "download by ID" flows, and confused users who get different results depending on which source responded first.

**Why it happens:** It's tempting to add Anna's Archive as "another search backend" and merge results at the tool level. But book identity (ISBN, MD5 hash, Z-Lib ID, AA ID) doesn't map 1:1 across sources.

**Warning signs:**
- Same book appears twice in search results with slightly different metadata
- Download fails because the ID from search came from source A but download assumes source B
- Metadata fields are null/missing for one source but not the other

**Prevention:**
1. Design a `BookReference` abstraction that carries source provenance (which source, which ID scheme, original metadata)
2. Never expose raw source IDs to the MCP tool interface; use a composite identifier that encodes source
3. Implement deduplication at the search merge layer using ISBN or MD5 hash
4. Make the source explicit in tool responses so the AI assistant (and user) knows where a book came from

**Legal/TOS considerations:**
- Anna's Archive is a shadow library aggregator. Its legal status varies by jurisdiction.
- Accessing AA programmatically may violate its TOS -- check current TOS before implementing.
- Make AA an opt-in source (environment variable like `ANNAS_ARCHIVE_ENABLED=true`) rather than default, so users make their own legal determination.
- Document the legal landscape in an ADR so the decision is traceable.
- Consider that AA's availability is inconsistent (domain changes, Cloudflare protection) -- the integration must degrade gracefully.

---

## High Pitfalls

### P-04: Adaptive DPI Causes Silent Quality Regression in Detection Pipeline
**Severity:** HIGH
**Phase:** Variable DPI / adaptive resolution

**What goes wrong:** Implementing adaptive DPI (higher for scanned/image-heavy pages, lower for text-native) seems like a pure optimization. But PyMuPDF's rendering at different DPI values affects coordinate spaces. The existing footnote detection system (`footnote_core.py`) uses `_calculate_page_normal_font_size` and `_is_superscript` with absolute values. When DPI changes, text block bboxes from `page.get_text("dict")` remain in point-space (72 DPI), but any pixmap-based OCR path returns pixel coordinates that scale with DPI.

**Why it happens:** Mixed coordinate spaces. `get_text("dict")` returns point-based coordinates (DPI-independent), but `get_pixmap(dpi=X)` returns pixel coordinates. If any detection logic mixes these, changing DPI breaks it silently.

**Warning signs:**
- Footnote detection accuracy drops on pages processed at non-default DPI
- OCR text positions don't align with text extraction positions
- Performance improves but quality metrics regress

**Prevention:**
1. Audit the pipeline for coordinate space assumptions. Determine which APIs are DPI-sensitive (`get_pixmap`, OCR) vs DPI-independent (`get_text`).
2. Normalize ALL coordinates to point-space before any detection logic.
3. Add a quality regression test: process the same PDF at 72, 150, and 300 DPI and assert detection results are identical (within tolerance).
4. If adaptive DPI only affects OCR/image rendering and NOT text extraction, document this explicitly so future developers don't accidentally mix spaces.

---

### P-05: Node.js 18 to 20+ Upgrade Breaks ESM/Jest Setup
**Severity:** HIGH
**Phase:** Node.js upgrade

**What goes wrong:** The project uses `--experimental-vm-modules` for Jest ESM support. Node 20 changed ESM loader internals. `ts-jest` + `jest` + ESM is a notoriously fragile combination across Node versions. Additionally, `@types/node` is pinned to v18 -- type mismatches will surface.

**Why it happens:** Node 20's ESM resolution differs subtly from 18. The experimental VM modules flag behavior also changed. The combination of TypeScript compilation, Jest module mocking, and ESM creates a three-way version dependency.

**Warning signs:**
- `ERR_MODULE_NOT_FOUND` in test runs
- `jest.mock()` stops working for ESM imports
- `mock-fs` or `nock` behavior changes
- TypeScript `@types/node` errors after upgrade

**Prevention:**
1. Update `@types/node` to match target Node version FIRST, fix type errors
2. Test Jest + ESM setup in isolation before any code changes
3. Check each test dependency for Node 20 compatibility: `mock-fs@5`, `nock@13`, `sinon@17`
4. If Jest ESM breaks, consider moving to Vitest (native ESM, no experimental flags) as part of the upgrade
5. Pin exact Node version in `engines` field and any Docker/CI config

---

### P-06: Margin Detection Interferes with Existing Footnote Pipeline
**Severity:** HIGH
**Phase:** Margin/scholarly numbering detection

**What goes wrong:** `footnote_core.py` uses `_get_cached_text_blocks` and spatial analysis. Margin detection operating on the same text blocks creates ordering dependencies: if margin content is stripped before footnote detection, footnotes in margin areas are lost. If footnote detection runs first, it may misclassify margin annotations as footnote definitions.

**Why it happens:** Both systems consume the same text block data and make spatial assumptions. The pipeline in `orchestrator_pdf.py` may not enforce ordering.

**Prevention:**
1. Define explicit pipeline stages with documented input/output contracts in `orchestrator_pdf.py`
2. Margin detection should ANNOTATE blocks (tag as "margin") but NOT remove them from the block list. Downstream stages decide how to handle tagged blocks.
3. Add integration tests that run margin + footnote detection together on PDFs that have margin footnotes (common in legal and classical texts)

---

## Moderate Pitfalls

### P-07: Anna's Archive Rate Limiting and Error Handling Mismatch
**Severity:** MODERATE
**Phase:** Anna's Archive integration

**What goes wrong:** AA has different rate limits, availability patterns, and error responses than Z-Library. The existing retry/circuit-breaker logic (configured via `RETRY_*` and `CIRCUIT_BREAKER_*` env vars) is tuned for Z-Library. Reusing it for AA leads to either too-aggressive retrying (getting IP banned) or too-conservative backing off.

**Prevention:**
1. Make retry configuration per-source, not global
2. AA uses Cloudflare protection -- handle HTTP 403/503 as "temporarily unavailable" not "permanent error"
3. Test with AA unavailable and verify graceful degradation (return Z-Library-only results, not an error)
4. Implement source-level circuit breakers (AA down shouldn't trip Z-Library's circuit breaker)

---

### P-08: Scholarly Line Numbers Confused with Page Numbers
**Severity:** MODERATE
**Phase:** Margin/scholarly numbering detection

**What goes wrong:** The existing `page_numbers.py` detection identifies page numbers by position and numeric pattern. Scholarly line numbers (poetry, legal texts, code listings) appear in similar positions. Adding line number detection without coordinating with `page_numbers.py` creates conflicts where the same number is claimed by both systems.

**Prevention:**
1. Line numbers are sequential within a page and reset per page. Page numbers increment across pages. Use cross-page patterns to disambiguate.
2. Run page number detection first (it already exists and works), then exclude identified page numbers from line number candidates.
3. Expose detection as "scholarly apparatus" to handle verse numbers, section numbers, and line numbers under one umbrella.

---

### P-09: Adaptive DPI Doubles Processing Time Without Escape Hatch
**Severity:** MODERATE
**Phase:** Variable DPI / adaptive resolution

**What goes wrong:** Adaptive DPI requires a pre-analysis pass on each page to determine optimal resolution. For a 500-page PDF, this adds significant overhead. If most pages are text-native (common case), the analysis is wasted.

**Prevention:**
1. Make adaptive DPI opt-in via parameter on `process_document_for_rag`, defaulting to current fixed DPI
2. Use a fast heuristic for the pre-pass: check if page has images > X% of page area (PyMuPDF `page.get_images()` is cheap)
3. Cache DPI decisions so reprocessing the same document skips analysis
4. Set a page budget -- if first N pages are all text-native, skip analysis for remaining pages

---

### P-10: EAPIClient Has Different Auth Lifecycle Than AsyncZlib
**Severity:** MODERATE
**Phase:** AsyncZlib removal

**What goes wrong:** `ZLibraryClient` in `client_manager.py` wraps AsyncZlib's login flow (email/password -> session). EAPIClient in `eapi.py` may authenticate differently. The `__aenter__`/`__aexit__` lifecycle and env vars (`ZLIBRARY_EMAIL`, `ZLIBRARY_PASSWORD`) may not map to EAPIClient's model.

**Prevention:**
1. Study `zlibrary/src/zlibrary/eapi.py` auth flow thoroughly BEFORE starting migration
2. The client_manager abstraction is the right place to handle auth differences -- don't leak EAPIClient internals into the 7 consuming modules
3. Keep both auth flows working during transition (feature flag, not hard cutover)

---

### P-11: Anna's Archive Search API Instability
**Severity:** MODERATE
**Phase:** Anna's Archive integration

**What goes wrong:** AA doesn't have a stable public API. Integrations typically scrape search results or use undocumented endpoints. These break without notice when AA updates their frontend or anti-scraping measures.

**Prevention:**
1. Isolate AA integration behind a clean interface so the scraping/API logic is contained in one module
2. Add health-check/smoke-test that verifies AA integration works (run periodically, not just at release)
3. Design for AA being unavailable -- it's a supplementary source, not a primary one
4. Version-stamp the AA integration so when it breaks, you know which AA change caused it

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Margin detection | False positives on indented text (P-02) | CRITICAL | Page-level margin model, not fixed threshold |
| Margin detection | Interference with footnote pipeline (P-06) | HIGH | Annotate-don't-remove pattern |
| Margin detection | Confusion with page numbers (P-08) | MODERATE | Cross-page pattern analysis, run after page_numbers.py |
| Adaptive DPI | Breaks detection thresholds via mixed coordinate spaces (P-04) | HIGH | Audit and normalize to point-space |
| Adaptive DPI | Performance regression without opt-out (P-09) | MODERATE | Opt-in parameter, fast heuristic pre-pass |
| Anna's Archive | Inconsistent book identity (P-03) | CRITICAL | BookReference abstraction with source provenance |
| Anna's Archive | Legal/TOS exposure (P-03) | CRITICAL | Opt-in source, document in ADR |
| Anna's Archive | Different error patterns (P-07) | MODERATE | Per-source retry config and circuit breakers |
| Anna's Archive | Unstable scraping target (P-11) | MODERATE | Isolated module, health checks, graceful degradation |
| Node.js upgrade | ESM/Jest breakage (P-05) | HIGH | Test Jest setup first, consider Vitest |
| AsyncZlib removal | Silent download breakage (P-01) | CRITICAL | Adapter pattern, integration test |
| AsyncZlib removal | Auth lifecycle mismatch (P-10) | MODERATE | Study EAPIClient auth before starting |

---

## Sources

- Direct codebase analysis: `lib/client_manager.py`, `lib/rag/detection/footnote_core.py`, `lib/rag/detection/page_numbers.py`, `lib/rag/orchestrator_pdf.py`, `zlibrary/src/zlibrary/eapi.py`, `zlibrary/src/zlibrary/libasync.py`
- `package.json` dependency and engine analysis
- PyMuPDF coordinate space behavior: training knowledge (MEDIUM confidence -- verify `get_text("dict")` vs `get_pixmap` coordinate independence against current PyMuPDF docs)
- Anna's Archive legal/availability status: training knowledge (MEDIUM confidence -- verify current TOS before implementation)
- Node.js 18->20 ESM changes: training knowledge (HIGH confidence -- well-documented breaking changes)
