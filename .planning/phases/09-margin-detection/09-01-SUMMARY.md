---
phase: 09-margin-detection
plan: 01
subsystem: rag-detection
tags: [margin-detection, pdf-processing, scholarly-references, tdd]
dependency_graph:
  requires: []
  provides: [margin-zone-detection, typed-margin-classification, body-column-inference]
  affects: [09-02, 09-03]
tech_stack:
  added: []
  patterns: [statistical-clustering, zone-classification, typed-content-regex]
key_files:
  created:
    - lib/rag/detection/margins.py
    - lib/rag/detection/margin_patterns.py
  modified:
    - lib/rag/detection/__init__.py
    - __tests__/python/test_margin_detection.py
decisions:
  - id: MARG-BEKKER-FIRST
    decision: Check Bekker regex before Stephanus (more specific pattern prevents ambiguity)
  - id: MARG-MIDPOINT-ZONE
    decision: Use block midpoint (not edges) for margin-left vs margin-right classification
metrics:
  duration: ~5min
  completed: 2026-02-02
---

# Phase 09 Plan 01: Margin Detection Engine Summary

**One-liner:** Statistical body-column inference with typed margin classification (Stephanus, Bekker, line numbers) using edge clustering and configurable zone boundaries.

## What Was Built

Two new detection modules for the RAG pipeline:

1. **margin_patterns.py** - Regex-based typed classification of margin text into Stephanus (Plato), Bekker (Aristotle), line numbers, or generic margin annotations. Priority ordering: Bekker > Stephanus > line_number > margin.

2. **margins.py** - Page-level margin detection engine:
   - `_infer_body_column()` - Clusters text block x-positions into 5pt bins to find dominant body column edges
   - Two-column detection via second-peak analysis (>30% of primary, >100pt gap)
   - `_classify_block_zone()` - Assigns blocks to header/footer/margin-left/margin-right/body
   - `detect_margin_content()` - Full pipeline: infer columns, classify zones, type margin content
   - Scan artifact filtering (single-char, narrow blocks <10pt)
   - `excluded_bboxes` parameter for footnote detector coordination
   - Configurable via env vars: RAG_HEADER_ZONE_PCT, RAG_FOOTER_ZONE_PCT, RAG_MARGIN_FALLBACK_PCT

## Test Coverage

34 tests covering:
- 20 classify_margin_content tests (all types, edge cases, ambiguity)
- 3 body column inference tests (clustered, fallback, two-column)
- 6 zone classification tests (all zones + configurable pcts)
- 5 detect_margin_content integration tests (detection, exclusion, artifacts, header/footer, structure)

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message |
|------|---------|
| 10bd9b6 | feat(09-01): add margin_patterns.py with typed content classification |
| c911a51 | feat(09-01): add margins.py with body-column inference and zone classification |

## Next Phase Readiness

Plan 02 (pipeline integration) can proceed. The `detect_margin_content` function is ready to be wired into the RAG processing pipeline. The `excluded_bboxes` parameter enables coordination with the existing footnote detector.
