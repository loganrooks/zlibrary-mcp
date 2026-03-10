---
phase: 11
plan: 05
subsystem: rag-pipeline
tags: [pipeline, runner, writer, output-routing]
depends_on: ["11-03", "11-04"]
provides: ["run_document_pipeline", "build_document_output", "format_body_text", "format_footnotes"]
affects: ["11-06", "11-07"]
tech_stack:
  added: []
  patterns: ["two-phase-pipeline", "lazy-import", "content-routing"]
key_files:
  created:
    - lib/rag/pipeline/runner.py
    - lib/rag/pipeline/writer.py
  modified:
    - lib/rag/pipeline/__init__.py
metrics:
  duration: ~2min
  completed: 2026-02-02
---

# Phase 11 Plan 05: Pipeline Runner & Writer Summary

**One-liner:** Two-phase pipeline runner orchestrating 6 detectors with content-routing writer that separates body/footnotes/margins/metadata

## What Was Built

### Pipeline Runner (`lib/rag/pipeline/runner.py`)
- `run_document_pipeline(doc, output_format, include_metadata)` - main entry point
- `run_document_detectors(doc, context)` - runs TOC, page numbers, front matter, headings
- `run_page_detectors(page, page_num, context)` - runs footnotes, margins per page
- `_extract_page_blocks(page)` - extracts bboxes and text from PyMuPDF pages
- Graceful degradation: failed detectors logged and skipped, pipeline continues
- Imports all 6 detection modules at top to trigger decorator registration

### Output Writer (`lib/rag/pipeline/writer.py`)
- `build_document_output(classified_pages, context, include_metadata)` - routes blocks to output streams
- `format_body_text(body_blocks, margin_blocks)` - continuous text with inline `[margin: ...]`
- `format_footnotes(footnote_blocks)` - grouped by page as numbered lists
- `format_metadata_sidecar(document_metadata, processing_metadata)` - JSON sidecar structure
- Content routing: BODY/HEADING to body, FOOTNOTE separate, MARGIN inline, PAGE_NUMBER stripped
- Context consumption: page_number_map, toc_map, front_matter used to exclude/route content

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| PIPELINE-LAZY-IMPORT | Used `__getattr__` lazy import in `__init__.py` to avoid circular import between pipeline and detection registry |
| WRITER-PAGE-BREAK | Pages separated by double newline in body text (no explicit `---` separator) |
| WRITER-MARGIN-APPEND | Margin annotations appended at end of their page's body text block |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between pipeline.__init__ and detection.registry**
- **Found during:** Task 2 verification
- **Issue:** Importing `run_document_pipeline` in `__init__.py` triggered circular import chain through registry
- **Fix:** Used `__getattr__` lazy import pattern in `__init__.py`
- **Files modified:** `lib/rag/pipeline/__init__.py`

## Commits

| Hash | Description |
|------|-------------|
| de63f5f | feat(11-05): create pipeline runner with two-phase execution |
| 21135c7 | feat(11-05): create output writer with content routing and metadata |
