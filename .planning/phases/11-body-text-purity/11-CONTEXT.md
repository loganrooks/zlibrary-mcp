# Phase 11: Body Text Purity Integration - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

All detection modules (footnotes, margins, headings, page numbers, TOC, front matter) compose into a unified pipeline that delivers clean body text with non-body content clearly separated. This phase orchestrates existing detectors into a cohesive system with structured output, confidence scoring, and recall regression testing.

</domain>

<decisions>
## Implementation Decisions

### Output Structure
- **Margins:** Inline near original position, visible format (not HTML comments) — margins are citation-relevant and should be readable
- **Footnotes/endnotes:** Separate output files with `_footnotes` / `_endnotes` suffixes — each file embeds independently in RAG
- **Citations:** Separate `_citations` suffix file if citations are detected
- **File layout:** Flat with suffixes (e.g., `book.md`, `book_footnotes.md`, `book_meta.json`), not directory-per-document
- **Document metadata:** Always output by default — TOC structure, front matter info as structured sidecar (distinct from processing metadata)
- **Processing metadata:** Optional flag (`include_metadata=true`) — per-block classifications, confidence scores, detector source
- **Front matter/TOC:** Strip from body text but capture in document metadata output
- **Headings:** Keep in body as markdown headings; page numbers stripped

### Confidence Scoring
- **Multi-granular approach:** Per-detector confidence always; per-block only when ambiguity or conflict exists (adaptive)
- **Score semantics:** Research whether multi-class scoring (separate body-confidence vs type-confidence) provides measurable benefit over single-score — experiment to determine
- **Document-level trends:** Experiment to determine if tracking confidence trends across document regions improves classification
- **Threshold configuration:** Justify any threshold decisions with experimental spikes, not just theory
- **Low-confidence behavior and score exposure:** Claude's discretion based on recall/precision trade-off

### Composition Priority
- **Pipeline architecture:** Best-practice approach — don't constrain to existing code, refactor as needed (no sunk cost)
- **Plugin-style detector registration:** Detectors register themselves; pipeline discovers and runs them
- **Broad plugin scope:** Design should not foreclose extensibility to other pipeline stages (OCR, preprocessing) in future, though current focus is detection plugins only
- **Conflict resolution, execution ordering, inapplicable document handling:** Claude's discretion
- **Typed declarations vs uniform non-body:** Claude's discretion, informed by output file routing needs

### Recall vs Precision
- **Asymmetric tolerance:** Zero tolerance for recall loss (body text must never be misclassified as non-body); small margin acceptable for precision (occasional non-body leakage in body text tolerated)
- **Bias direction:** Favor keeping ambiguous content in body text — but validate experimentally what actually harms RAG embedding/search quality
- **Strictness mode:** Claude's discretion on whether a user-facing toggle adds value

### Test Corpus
- **Organize existing test_files:** Audit current fixtures, identify gaps
- **Ground truth creation:** Real PDFs with Sonnet-extracted + human-verified ground truth
- **Edge case fixtures:** Create synthetic test files for edge cases
- **Regression suite:** Fixed snapshot corpus (must never regress) PLUS growing corpus for expanded coverage
- **Ground truth timing:** Claude's discretion on whether this is a phase task or prerequisite

### Claude's Discretion
- Document metadata format (JSON sidecar vs YAML front matter)
- Page boundary handling in body text (markers vs continuous flow)
- Backward compatibility with single-file output
- Confidence score exposure in MCP tool responses
- Passthrough/raw mode for baseline comparison
- Plugin safety mechanisms (auto-disable vs fail-the-build)
- Degradation strategy for unusual document formats
- Pipeline model (sequential cascade vs independent + merge)

</decisions>

<specifics>
## Specific Ideas

- "Don't get trapped by sunk cost fallacy" — willing to refactor existing detectors if a better composition architecture requires it
- Plugin architecture should be broad enough for future pipeline stages (OCR, preprocessing), not just detection
- Document metadata (TOC, front matter) is distinct from processing metadata and should always be output — it provides RAG context
- Footnotes are per-page so can't just dump at end of document — separate file approach addresses this naturally
- Many confidence/threshold decisions should be justified by experimental spikes, not just theoretical reasoning

</specifics>

<deferred>
## Deferred Ideas

- Pluggable OCR engines (different OCR pipelines per document type) — future extensibility, not Phase 11 scope
- Pluggable preprocessing pipelines — architecture should not foreclose this but not implementing now

</deferred>

---

*Phase: 11-body-text-purity*
*Context gathered: 2026-02-02*
