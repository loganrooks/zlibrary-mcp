# Phase 9: Margin Detection & Scholarly References - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect margin content in scholarly PDFs, classify it by type, and output it as structured inline annotations separate from body text. The system processes PDF pages and produces clean body text with margin content marked using a bracket annotation system. Typed reference classification (Stephanus, Bekker, etc.) is deferred — this phase implements generic margin detection and marking only.

</domain>

<decisions>
## Implementation Decisions

### Reference type coverage
- All margin content captured generically — no type-specific classification in this phase
- Single generic marker format: `{{margin: content}}` for all detected margin text
- Typed variants (e.g., `{{stephanus: 231a}}`, `{{bekker: 1094a1}}`) deferred to future milestone — the bracket format is designed to support this extension
- Marginal glosses (explanatory notes, not just reference numbers) are captured the same way
- No attempt to differentiate printed marginalia from handwritten annotations in this phase

### Annotation output format
- Inline placement: margin markers appear next to the body text line they're adjacent to in the PDF
- Bracket delimiter choice, escaping strategy, and conflict handling at Claude's discretion
- Multi-line margin content handling (join vs preserve newlines) at Claude's discretion
- Standalone margin markers (no adjacent body text) placement at Claude's discretion
- Document-end summary of margin annotations at Claude's discretion
- Left/right margin position encoding at Claude's discretion
- Footnote detection interop at Claude's discretion (Phase 11 composes all detectors)
- Graceful degradation (readability without margin awareness) at Claude's discretion
- Must be compatible with existing RAG pipeline markdown output

### Detection confidence & ambiguity
- Threshold strategy for margin vs body text classification at Claude's discretion
- Confidence score exposure (binary vs scored, inline vs metadata) at Claude's discretion
- Precision/recall priority balance at Claude's discretion
- Whether to auto-detect margin relevance per document at Claude's discretion
- Validation approach at Claude's discretion

### Document type adaptability
- Wide variety of scholarly PDFs must be supported (not optimized for one publisher/series)
- Per-document configuration approach at Claude's discretion (note: MCP tool context means no interactive user, but optional parameters are possible)
- Facing page awareness at Claude's discretion
- Special layout handling (two-column, sidebar boxes, etc.) at Claude's discretion

### Claude's Discretion
Claude has significant flexibility in this phase. The user's firm decisions are:
1. Generic `{{margin: content}}` bracket format (not typed classification)
2. Inline placement near adjacent body text
3. Capture all margin text (glosses included)
4. Wide document variety support

Everything else — delimiter details, confidence thresholds, multi-line handling, position encoding, summary output, validation approach, layout adaptability — is at Claude's discretion during research and planning.

</decisions>

<specifics>
## Specific Ideas

- Bracket format designed for future extension: `{{type: content}}` pattern so typed variants can be added in later milestones without format changes
- System will be consumed as an MCP tool — no interactive configuration possible
- User works with wide variety of scholarly PDFs across many publishers and formats

</specifics>

<deferred>
## Deferred Ideas

- Typed reference classification (Stephanus, Bekker, line numbers) — future milestone, extend `{{margin: ...}}` to `{{stephanus: ...}}`, etc.
- Handwritten annotation vs printed marginalia differentiation — future milestone, too complex for now

</deferred>

---

*Phase: 09-margin-detection*
*Context gathered: 2026-02-02*
