# Phase 10: Adaptive Resolution Pipeline - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

OCR quality improves automatically by selecting optimal DPI per page and per region based on content analysis. The system targets Tesseract's 30-33px optimal text height range. Adaptive DPI fully replaces the current fixed-DPI approach. OCR engine selection (e.g., Surya fallback) is out of scope.

</domain>

<decisions>
## Implementation Decisions

### DPI thresholds & triggers
- Adaptive DPI is a full replacement for fixed DPI — no opt-in flag, it becomes the default pipeline
- Parallel page processing with auto-detected concurrency (based on available cores/memory)
- General quality improvement motivation — no single document type drives this, optimize broadly

### Output & diagnostics
- Per-page DPI value always included in output metadata (not debug-only)
- Low-confidence pages flagged in both output metadata and developer logs
- Optional debug image generation showing page regions color-coded by DPI choices
- Warnings for low-confidence DPI decisions emitted to logs and metadata

### Claude's Discretion
- DPI floor and ceiling values
- Strict vs relaxed pixel height targeting (30-33px exact vs 25-40px acceptable range)
- Page-level vs dominant-text-size strategy when text sizes are mixed
- Per-page analysis vs sampling-and-applying for long documents
- Whether to auto-retry at higher DPI when OCR confidence is low
- Scanned PDF vs text-layer PDF treatment differences
- Whether to offer a user override for forced fixed DPI
- Which region types get independent re-rendering (footnotes, margins, figures, tables, etc.)
- Region re-rendering method (crop region vs full-page re-render)
- Single-pass vs two-pass architecture
- Region count limits per page
- Whether margin regions always get higher DPI or only when measured pixel height is below threshold
- Full-page special content handling (tables, figures)
- Whether to use Phase 9 bounding boxes only or add new region detection
- Pattern learning across pages for consistent region layouts
- DPI metadata detail level beyond the DPI value itself (reasons, region breakdown)
- Document-level DPI summary statistics
- Performance budget and acceptable slowdown
- Analysis time budget per page
- Large document throttling strategy
- DPI decision caching for reprocessing
- Memory management during parallel processing
- Mid-document cancellation support
- Timing instrumentation granularity
- Debug image output directory organization

</decisions>

<specifics>
## Specific Ideas

- Footnote regions with smaller font could be sampled at higher DPI independently from body text — the user's mental model of how this should work
- Low-confidence page logging doubles as a discovery mechanism for ground truth test scenarios — pages the system struggles with become candidates for test fixtures
- scholardoc-ocr repo (user's remote repo, not on this machine) has an adaptive pipeline philosophy worth studying: it flags pages Tesseract has trouble with and runs Surya on them. The "tiered difficulty" approach is philosophically aligned with adaptive DPI

</specifics>

<deferred>
## Deferred Ideas

- **Tiered OCR engine selection (Surya fallback)** — When Tesseract struggles with a page, fall back to Surya OCR. Inspired by scholardoc-ocr's adaptive pipeline. This is a separate phase from adaptive DPI.
- **GT test fixture pipeline from low-confidence pages** — Automatically collect flagged low-confidence pages into a ground truth candidate pool for improving the system over time.

</deferred>

---

*Phase: 10-adaptive-resolution*
*Context gathered: 2026-02-02*
