# Phase 11: Body Text Purity Integration - Research

**Researched:** 2026-02-02
**Domain:** PDF content classification pipeline composition, plugin architecture, multi-file output routing
**Confidence:** HIGH (internal codebase analysis) / MEDIUM (architecture patterns)

## Summary

Phase 11 composes six existing detection modules (footnotes, margins, headings, page numbers, TOC, front matter) into a unified pipeline that separates non-body content from clean body text. The current `process_pdf()` in `orchestrator_pdf.py` already calls these detectors ad-hoc within a ~650-line monolith. The challenge is not building new detectors but **refactoring orchestration** into a plugin-based pipeline with structured multi-file output.

Key findings:
- All six detectors exist and are functional. Their return types are inconsistent (dicts with varying schemas, page-level vs document-level).
- The current pipeline is a single function returning a single string. Phase 11 must split this into multiple output files (body, footnotes, endnotes, citations, metadata).
- The footnote-margin dedup (MARG-FOOTNOTE-DEDUP-DEFERRED) is a concrete integration task requiring footnote bboxes to be passed to `detect_margin_content(excluded_bboxes=...)`.
- A decorator-based registry pattern is the standard Python approach for plugin-style detector registration.

**Primary recommendation:** Refactor `process_pdf()` into a pipeline orchestrator that runs registered detectors, collects typed `DetectionResult` objects, resolves conflicts, and routes content to separate output files via a `DocumentOutput` model.

## Standard Stack

### Core

This phase uses no new external libraries. All work is internal refactoring of existing Python code.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | existing | PDF text/block extraction | Already used by all detectors |
| dataclasses | stdlib | Data models for pipeline results | Zero-dependency, type-safe |
| enum | stdlib | Detection categories, zones | Already used (NoteType, NoteSource) |
| pathlib | stdlib | Multi-file output paths | Already used throughout |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Metadata sidecar output | For `book_meta.json` sidecar |
| logging | stdlib | Pipeline stage tracing | Already pervasive |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Decorator registry | importlib plugin discovery | Over-engineered for 6 detectors; decorator is simpler |
| dataclasses | TypedDict | dataclasses support validation via `__post_init__`, TypedDict is just type hints |
| Sequential pipeline | Independent + merge | Sequential allows early termination; independent allows parallelism; recommend sequential for simplicity since detectors are fast |

## Architecture Patterns

### Recommended Project Structure

```
lib/rag/
├── detection/
│   ├── __init__.py          # Detector registry
│   ├── footnotes.py         # (existing)
│   ├── footnote_core.py     # (existing)
│   ├── footnote_markers.py  # (existing)
│   ├── margins.py           # (existing)
│   ├── margin_patterns.py   # (existing)
│   ├── headings.py          # (existing)
│   ├── page_numbers.py      # (existing)
│   ├── toc.py               # (existing)
│   ├── front_matter.py      # (existing)
│   └── registry.py          # NEW: detector registry + base protocol
├── pipeline/
│   ├── __init__.py
│   ├── models.py            # NEW: DetectionResult, BlockClassification, DocumentOutput
│   ├── compositor.py        # NEW: conflict resolution, block routing
│   └── writer.py            # NEW: multi-file output (body.md, _footnotes.md, _meta.json)
├── orchestrator_pdf.py      # REFACTOR: slim down to pipeline invocation
└── orchestrator.py          # REFACTOR: route to multi-file save
```

### Pattern 1: Detector Registry with Decorator

**What:** Each detector registers itself with a decorator. The pipeline discovers and runs all registered detectors.
**When to use:** When composing multiple independent detection modules.

```python
# lib/rag/detection/registry.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

class ContentType(Enum):
    BODY = "body"
    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"
    MARGIN = "margin"
    HEADING = "heading"
    PAGE_NUMBER = "page_number"
    TOC = "toc"
    FRONT_MATTER = "front_matter"
    HEADER = "header"
    FOOTER = "footer"
    CITATION = "citation"

@dataclass
class BlockClassification:
    """A single block's classification result from a detector."""
    bbox: Tuple[float, float, float, float]
    content_type: ContentType
    text: str
    confidence: float  # 0.0 - 1.0
    detector_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DetectionResult:
    """Result from a single detector for one page."""
    detector_name: str
    classifications: List[BlockClassification]
    page_num: int
    # Detector-specific metadata (e.g., body_column bounds from margin detector)
    metadata: Dict[str, Any] = field(default_factory=dict)

# Registry
_DETECTOR_REGISTRY: Dict[str, Callable] = {}

def register_detector(name: str, priority: int = 50):
    """Decorator to register a page-level detector."""
    def wrapper(func):
        _DETECTOR_REGISTRY[name] = {"func": func, "priority": priority}
        return func
    return wrapper

def get_registered_detectors() -> List[dict]:
    """Return detectors sorted by priority (lower = runs first)."""
    return sorted(_DETECTOR_REGISTRY.values(), key=lambda d: d["priority"])
```

### Pattern 2: Conflict Resolution (Compositor)

**What:** When multiple detectors claim the same block, resolve by priority and confidence.
**When to use:** When footnote and margin detectors both flag the same block.

```python
# lib/rag/pipeline/compositor.py
def resolve_conflicts(
    results: List[DetectionResult],
    bias: str = "body"  # "body" = ambiguous content stays in body
) -> Dict[Tuple[float,...], BlockClassification]:
    """Merge all detector results, resolving overlapping bbox claims.

    Priority rules:
    1. Higher-confidence classification wins
    2. On tie: footnote > margin > page_number > header/footer
    3. Body is the default — if no detector claims a block, it's body
    4. Recall bias: if max confidence < threshold, classify as body
    """
    ...
```

### Pattern 3: Multi-File Output

**What:** Route classified content to separate output files.
**When to use:** For the flat-file suffix layout (book.md, book_footnotes.md, book_meta.json).

```python
# lib/rag/pipeline/writer.py
@dataclass
class DocumentOutput:
    """Complete output for a processed document."""
    body_text: str
    footnotes: Optional[str] = None
    endnotes: Optional[str] = None
    citations: Optional[str] = None
    metadata: Optional[dict] = None  # TOC, front matter, processing stats

    def write_files(self, base_path: Path, output_format: str = "markdown"):
        """Write all output files with suffix convention."""
        stem = base_path.stem
        parent = base_path.parent

        # Body: book.md
        (parent / f"{stem}.md").write_text(self.body_text)

        # Footnotes: book_footnotes.md (only if non-empty)
        if self.footnotes:
            (parent / f"{stem}_footnotes.md").write_text(self.footnotes)

        # Metadata: book_meta.json (always)
        if self.metadata:
            (parent / f"{stem}_meta.json").write_text(
                json.dumps(self.metadata, indent=2)
            )
```

### Anti-Patterns to Avoid

- **Monolith orchestrator:** Don't keep adding detector calls inside `process_pdf()`. Extract to pipeline.
- **String-based content type:** Use `ContentType` enum, not raw strings like `"footnote"`.
- **Implicit detector ordering:** Make execution order explicit via priority numbers.
- **Modifying body text in-place:** Detectors should classify blocks, not mutate text. The compositor decides what goes where.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plugin discovery | importlib scanning | Decorator registry | Only 6 detectors; decorator is explicit and debuggable |
| Confidence calibration | Custom calibration framework | Simple float 0-1 with threshold | Experimental threshold tuning per CONTEXT.md; start simple |
| JSON schema validation | jsonschema library | dataclass `__post_init__` | Metadata sidecar is internal; no external consumers yet |
| Multi-file atomicity | Transaction/rollback | Write-then-rename | Output files are best-effort; partial output is acceptable |

**Key insight:** This phase is primarily a refactoring and composition challenge, not a new-capability challenge. All detection logic exists. The risk is in over-engineering the pipeline framework rather than focusing on the composition.

## Common Pitfalls

### Pitfall 1: Recall Loss During Composition

**What goes wrong:** Body text accidentally classified as non-body by a detector, silently removed from output.
**Why it happens:** Margin detector claims a block that's actually body text near a page edge; no recall regression test catches it.
**How to avoid:**
1. Default-to-body bias: any block not claimed by a detector at sufficient confidence stays in body.
2. Recall regression test: snapshot the body text output from existing test PDFs BEFORE refactoring. After refactoring, assert body text is identical or superset.
3. Confidence floor: blocks below threshold (e.g., 0.6) always stay in body regardless of detector claim.
**Warning signs:** Output body text is shorter than before the refactoring.

### Pitfall 2: Footnote-Margin Double Classification

**What goes wrong:** A footnote block is also classified as margin content, appearing in both `_footnotes.md` and inline as `{{margin: ...}}`.
**Why it happens:** `MARG-FOOTNOTE-DEDUP-DEFERRED` — footnote bboxes are not currently passed to `detect_margin_content(excluded_bboxes=...)`.
**How to avoid:** Pass footnote bboxes from `_detect_footnotes_in_page` result to `detect_margin_content` as excluded_bboxes. The compositor should also deduplicate by bbox overlap.
**Warning signs:** Same text appears in both footnote output and margin annotations.

### Pitfall 3: Breaking Backward Compatibility

**What goes wrong:** Existing users of `process_pdf()` get different output format, breaking downstream RAG pipelines.
**Why it happens:** Refactoring changes the return type from single string to multi-file.
**How to avoid:**
1. Keep `process_pdf()` returning a single string (body text) for backward compat.
2. Add new `process_pdf_structured()` or pipeline entry point that returns `DocumentOutput`.
3. Update `process_document()` in orchestrator.py to use the new entry point and save multiple files.
**Warning signs:** Existing tests fail after refactoring.

### Pitfall 4: Over-Engineering the Plugin System

**What goes wrong:** Building a generic, extensible plugin framework that's complex to debug for only 6 detectors.
**Why it happens:** CONTEXT.md says "broad plugin scope for future extensibility."
**How to avoid:** Build the registry pattern but keep it simple (decorator + dict). Don't add configuration files, dynamic loading, or complex lifecycle management. The "broad scope" means the pattern should be extensible, not that it needs to handle everything now.
**Warning signs:** Registry code is longer than 100 lines; detector registration requires more than a decorator.

### Pitfall 5: Confidence Score Complexity Creep

**What goes wrong:** Implementing multi-class confidence, document-level trends, and adaptive thresholds all at once.
**Why it happens:** CONTEXT.md says "experiment to determine" for several confidence aspects.
**How to avoid:** Start with per-detector single confidence float. Add multi-class or document-level only if experiments show measurable benefit. Use thresholds that default to recall-biased values.
**Warning signs:** Confidence model has more than 3 parameters per block.

## Code Examples

### Current Detector Call Pattern (What Exists)

```python
# In orchestrator_pdf.py process_pdf(), lines ~448-488
# Each detector called separately with ad-hoc result handling

# Footnotes
page_footnotes = _detect_footnotes_in_page(page, i)
if page_footnotes.get("definitions"):
    completed_footnotes = continuation_parser.process_page(...)

# Margins
margin_result = detect_margin_content(page, excluded_bboxes=None)
margin_blocks = margin_result.get("margin_blocks", [])

# ToC
toc_map = _extract_toc_from_pdf(doc)  # Document-level, before page loop

# Page numbers
written_page_map = infer_written_page_numbers(doc)  # Document-level

# Front matter
(lines_after_fm, title) = _identify_and_remove_front_matter(content_lines)

# Headings
# Called indirectly through toc.py → headings.py
```

### Target Pipeline Pattern (What to Build)

```python
# lib/rag/pipeline/compositor.py

from lib.rag.detection.registry import get_registered_detectors, DetectionResult

def run_detection_pipeline(
    doc: "fitz.Document",
    page_num: int,
    page: "fitz.Page",
    context: dict,  # Shared state: body_column, toc_map, etc.
) -> List[DetectionResult]:
    """Run all registered detectors on a page."""
    results = []
    for detector in get_registered_detectors():
        try:
            result = detector["func"](page, page_num, context)
            results.append(result)
        except Exception as e:
            logger.warning(f"Detector {detector['func'].__name__} failed on page {page_num}: {e}")
            # Graceful degradation: skip failed detector, don't halt pipeline
    return results
```

### Footnote-Margin Dedup Integration

```python
# In the page loop, footnotes run first (priority 10), margins second (priority 20)
# Margins receive footnote bboxes via context

# detector: footnotes (priority=10)
@register_detector("footnotes", priority=10)
def detect_footnotes(page, page_num, context):
    result = _detect_footnotes_in_page(page, page_num - 1)  # 0-indexed
    # Store bboxes in context for downstream detectors
    context["footnote_bboxes"] = [d["bbox"] for d in result.get("definitions", [])]
    ...

# detector: margins (priority=20)
@register_detector("margins", priority=20)
def detect_margins(page, page_num, context):
    excluded = context.get("footnote_bboxes", [])
    result = detect_margin_content(page, excluded_bboxes=excluded)
    ...
```

### Multi-File Output Integration

```python
# In orchestrator.py process_document(), after process_pdf_structured()
output = process_pdf_structured(file_path, output_format)  # Returns DocumentOutput

# Save files with suffix convention
base_path = PROCESSED_OUTPUT_DIR / slugified_name
output.write_files(base_path, output_format)

return {
    "processed_file_path": str(base_path.with_suffix(".md")),
    "footnotes_file_path": str(base_path.parent / f"{base_path.stem}_footnotes.md") if output.footnotes else None,
    "metadata_file_path": str(base_path.parent / f"{base_path.stem}_meta.json"),
    "stats": { ... }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ad-hoc detector calls in monolith | Plugin registry with typed results | Phase 11 (this phase) | Enables composition, testability, extensibility |
| Single-string output | Multi-file with suffixes | Phase 11 (this phase) | RAG-friendly; footnotes embeddable independently |
| No confidence scores | Per-detector confidence | Phase 11 (this phase) | Enables threshold tuning, ambiguity handling |
| Footnotes appended to body | Separate footnotes file | Phase 11 (this phase) | Clean body text for RAG embedding |

## Existing Detector Inventory

| Detector | Module | Level | Returns | Confidence? |
|----------|--------|-------|---------|-------------|
| Footnotes | `detection/footnote_core.py` | Page | `{"definitions": [...], "markers": [...]}` | Yes (`classification_confidence`) |
| Margins | `detection/margins.py` | Page | `{"margin_blocks": [...], "body_column": (...)}` | No (implicit: is/isn't margin) |
| Headings | `detection/headings.py` | Document | `[(level, title, page)]` | No |
| Page numbers | `detection/page_numbers.py` | Document | `{page_num: written_num}` | No |
| TOC | `detection/toc.py` | Document | `{page_num: [(level, title)]}` | No |
| Front matter | `detection/toc.py` / `utils/header.py` | Document | `(cleaned_lines, title)` | No |

**Key observation:** Footnotes and margins operate at page level with bbox data. Headings, page numbers, TOC, and front matter operate at document level. The pipeline needs both a document-level pre-pass (TOC, page numbers, front matter, headings) and a page-level detection loop (footnotes, margins).

## Existing Test Infrastructure

| Test File | Content | Coverage |
|-----------|---------|----------|
| `margins_test_pages.pdf` | Scholarly PDF with margin content | Margin detection |
| `derrida_*.pdf` | Multiple Derrida excerpts | Footnotes, body text |
| `heidegger_*.pdf` | Multiple Heidegger excerpts | Footnotes, continuation |
| `kant_*.pdf` | Kant critique pages | Footnotes, asterisks |
| `ground_truth/*.json` | 11 ground truth files | Footnote accuracy |
| `test_xmarks_and_strikethrough.pdf` | Sous-rature detection | Quality pipeline |

**Gaps for Phase 11:**
1. No ground truth for margin detection accuracy
2. No ground truth for "clean body text" (body minus all non-body content)
3. No multi-file output tests
4. No end-to-end composition test (all detectors together)
5. No recall regression baseline snapshot

## Open Questions

1. **Document-level vs page-level pipeline model**
   - What we know: TOC/headings/page-numbers are document-level; footnotes/margins are page-level.
   - What's unclear: Should document-level detectors run as "pre-pass" plugins or as separate pipeline stages?
   - Recommendation: Two-phase pipeline — document pre-pass (registers context), then page-level loop. Both phases use the same registry pattern but different interfaces.

2. **Backward compatibility strategy**
   - What we know: `process_pdf()` returns a single string; many tests depend on this.
   - What's unclear: Whether to modify `process_pdf()` or add a parallel entry point.
   - Recommendation: Add `process_pdf_structured()` returning `DocumentOutput`; keep `process_pdf()` as thin wrapper calling structured and returning `body_text`.

3. **Confidence score granularity**
   - What we know: CONTEXT.md says experiment to determine multi-class vs single-score.
   - What's unclear: Whether multi-class scoring provides measurable benefit.
   - Recommendation: Start with single float per-detector. Add multi-class only if experimental results justify it.

4. **Metadata sidecar format**
   - What we know: CONTEXT.md leaves this to Claude's discretion (JSON vs YAML).
   - Recommendation: JSON (`_meta.json`). Already used in codebase for ground truth, metadata. No YAML dependency needed.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `lib/rag/orchestrator_pdf.py` — current pipeline (~750 lines)
- Codebase analysis: `lib/rag/detection/margins.py` — margin detector interface
- Codebase analysis: `lib/rag/detection/footnote_core.py` — footnote detector interface
- Codebase analysis: `lib/rag/detection/toc.py`, `headings.py`, `page_numbers.py` — document-level detectors
- Codebase analysis: `lib/rag_data_models.py` — existing data models (PageRegion, Entity, NoteType)
- Project state: `.planning/STATE.md` — MARG-FOOTNOTE-DEDUP-DEFERRED decision

### Secondary (MEDIUM confidence)
- [Registry Pattern with Decorators in Python (Dec 2025)](https://medium.com/@tihomir.manushev/implementing-the-registry-pattern-with-decorators-in-python-de8daf4a452a) — decorator registry pattern
- [Building a Plugin Architecture with Python](https://mwax911.medium.com/building-a-plugin-architecture-with-python-7b4ab39ad4fc) — plugin discovery and hook points
- [Python Registry Pattern (Nov 2025)](https://dev.to/dentedlogic/stop-writing-giant-if-else-chains-master-the-python-registry-pattern-ldm) — clean alternative to factory classes
- Phase 11 CONTEXT.md — user decisions and constraints

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, pure internal refactoring
- Architecture: HIGH — based on direct codebase analysis of all 6 detectors and current pipeline
- Pitfalls: HIGH — derived from actual code patterns (MARG-FOOTNOTE-DEDUP-DEFERRED, single-string return)
- Plugin pattern: MEDIUM — decorator registry is well-established but web sources only

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (stable — internal refactoring, no external dependencies)
