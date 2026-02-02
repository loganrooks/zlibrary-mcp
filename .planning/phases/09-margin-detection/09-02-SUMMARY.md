---
phase: 09-margin-detection
plan: 02
subsystem: rag-pipeline
tags: [margin-detection, pdf-processing, pipeline-integration]
depends_on: [09-01]
provides: [margin-pipeline-integration, typed-annotations]
affects: [09-03]
tech-stack:
  patterns: [y-center-proximity-matching, bbox-exclusion-set, inline-annotation-format]
key-files:
  modified:
    - lib/rag/orchestrator_pdf.py
    - lib/rag/processors/pdf.py
decisions:
  - id: MARG-CACHE-COMPAT
    decision: "Block bboxes identical between get_text('dict') and get_text('dict', flags=TEXTFLAGS_DICT); margin_bbox_set matching works across both call styles"
  - id: MARG-FOOTNOTE-DEDUP-DEFERRED
    decision: "Footnote bboxes not passed to detect_margin_content yet; deferred to Phase 11 deduplication"
metrics:
  duration: ~3min
  completed: 2026-02-02
---

# Phase 9 Plan 2: Pipeline Integration Summary

Integrated margin detection into the PDF processing pipeline so margin content is detected per-page, excluded from body text, and emitted as typed inline annotations.

## One-liner

Margin detection wired into orchestrator page loop with bbox exclusion and y-center annotation placement in formatter.

## Tasks Completed

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Integrate margin detection into orchestrator page loop | 90a0212 | Import detect_margin_content, call in page loop, pass margin_blocks to formatter |
| 2 | Add margin_blocks handling to _format_pdf_markdown | 87e04f3 | margin_blocks param, _associate_margin_to_body helper, bbox exclusion, annotation insertion |

## Key Implementation Details

### Orchestrator Integration (orchestrator_pdf.py)
- `detect_margin_content(page)` called after footnote detection, before `_format_md`
- `excluded_bboxes=None` with TODO for Phase 11 footnote bbox deduplication
- Cache discrepancy documented: `get_text("dict")` vs `get_text("dict", flags=TEXTFLAGS_DICT)` produce identical block bboxes

### Formatter Integration (pdf.py)
- `_associate_margin_to_body()` helper uses y-center overlap with nearest-distance fallback
- `margin_bbox_set` built from margin block bboxes for O(1) exclusion lookups
- `margin_map` associates each margin annotation to nearest body block index
- `body_block_idx` counter tracks non-margin blocks separately from `text_block_idx`
- Annotations emitted as `{{type: content}}` strings (e.g., `{{bekker: 1025a}}`, `{{line_number: 15}}`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pre-existing ruff E701 in orchestrator_pdf.py**
- **Found during:** Task 1 commit
- **Issue:** `if not _PYMUPDF_AVAILABLE: raise ImportError(...)` on single line
- **Fix:** Split to two lines
- **Commit:** 90a0212

**2. [Rule 3 - Blocking] Fixed pre-existing ruff F841 in pdf.py**
- **Found during:** Task 2 commit
- **Issue:** `current_list_type` assigned but never used
- **Fix:** Added `# noqa: F841` (pre-existing code, not introduced by this plan)
- **Commit:** 87e04f3

## Verification Results

- 572 unit tests pass (0 regressions)
- Pipeline imports verified end-to-end
- TypeScript build passes with validation

## Next Phase Readiness

Plan 09-03 (tests) can proceed. The integration is complete and all existing tests pass. Key testing targets:
- Margin blocks excluded from body text
- Annotations placed adjacent to correct body blocks
- No regressions in footnote/heading/page number detection
