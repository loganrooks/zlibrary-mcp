---
phase: 11-body-text-purity
plan: 01
subsystem: rag-pipeline
tags: [data-models, registry, detection-pipeline]
depends_on: []
provides: [ContentType, DetectorScope, BlockClassification, DetectionResult, DocumentOutput, register_detector, get_registered_detectors]
affects: [11-02, 11-03, 11-04, 11-05, 11-06, 11-07]
tech_stack:
  added: []
  patterns: [decorator-registry, dataclass-models, enum-classification]
key_files:
  created:
    - lib/rag/pipeline/__init__.py
    - lib/rag/pipeline/models.py
    - lib/rag/detection/registry.py
  modified: []
metrics:
  duration: ~2min
  completed: 2026-02-02
---

# Phase 11 Plan 01: Pipeline Data Models and Detector Registry Summary

**One-liner:** Stdlib-only data models (5 types) and decorator-based detector registry with priority ordering for unified detection pipeline.

## What Was Done

### Task 1: Pipeline Data Models
Created `lib/rag/pipeline/` package with:
- `ContentType` enum: 11 content types (body, footnote, endnote, margin, heading, page_number, toc, front_matter, header, footer, citation)
- `DetectorScope` enum: PAGE and DOCUMENT scopes
- `BlockClassification` dataclass: bbox, content_type, text, confidence, detector_name, page_num, metadata
- `DetectionResult` dataclass: detector output container with classifications list
- `DocumentOutput` dataclass: final output with body_text, footnotes, endnotes, citations, metadata, and `write_files()` method

### Task 2: Detector Registry
Created `lib/rag/detection/registry.py` with:
- `register_detector` decorator with name, priority, scope parameters and duplicate guard
- `get_registered_detectors()` returning priority-sorted list with optional scope filtering
- `clear_registry()` for test isolation

## Commits

| Commit | Description |
|--------|-------------|
| 2b4c42c | feat(11-01): create pipeline data models |
| 72273b9 | feat(11-01): create detector registry with priority ordering |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| PIPELINE-MODELS-STDLIB | Stdlib only (dataclasses, enum, typing, pathlib, json) | No external deps for foundation types |
| REGISTRY-SIMPLE-DICT | Simple dict registry with decorator | YAGNI - no config files, dynamic loading, or lifecycle management needed |

## Next Phase Readiness

All foundation types and registry ready for Plans 02-07 to build detectors and compositor on top.
