---
phase: 14-test-infrastructure
plan: 02
subsystem: test-infrastructure
tags: [ground-truth, schema-validation, jsonschema, pytest, v3-migration]
requires:
  - phase: 14-01
    provides: pytest marker taxonomy and strict_markers enforcement
provides:
  - Canonical v3 schema as single source of truth for ground truth files
  - Parametrized schema validation test (16 tests)
  - All 7 ground truth files conforming to v3 schema
  - Automated guard preventing schema drift
affects: [phase-17-quality-scoring, ground-truth-authoring]
tech-stack:
  added: [jsonschema 4.26.0]
  patterns: [parametrized-schema-validation, ground-truth-v3-conformance]
key-files:
  created:
    - __tests__/python/test_schema_validation.py
  modified:
    - pyproject.toml
    - uv.lock
    - test_files/ground_truth/heidegger_being_time.json
key-decisions:
  - "Removed null corrupted_extraction from heidegger xmark data rather than relaxing schema (schema stays strict)"
patterns-established:
  - "Parametrized schema validation: every ground truth JSON auto-tested against v3 schema via jsonschema.validate()"
duration: 26min
completed: 2026-02-11
---

# Phase 14 Plan 02: Ground Truth v3 Schema Consolidation Summary

**jsonschema-backed parametrized validation ensuring all 7 ground truth files conform to canonical v3 schema**

## Performance
- **Duration:** 26 minutes
- **Tasks:** 2/2 completed
- **Files modified:** 4

## Accomplishments
- Added jsonschema dev dependency (v4.26.0) for automated schema validation
- Created parametrized test_schema_validation.py with 16 tests (7 schema + 7 PDF-exists + 2 static)
- All 7 ground truth files validated against schema_v3.json
- Old schema files (schema.json, schema_v2.json) confirmed deleted (by 14-01)
- ground_truth_loader.py confirmed updated to reference v3 schema (by 14-01)
- Fixed heidegger_being_time.json null corrupted_extraction field

## Task Commits
1. **Task 1: Migrate ground truth files to v3 and delete old schemas** - `384986e` (already completed by 14-01 executor)
2. **Task 2: Add jsonschema dependency and create validation test** - `338ce73`

## Files Created/Modified
- `__tests__/python/test_schema_validation.py` - Parametrized test validating all ground truth files against v3 schema
- `pyproject.toml` - Added jsonschema dev dependency
- `uv.lock` - Updated lockfile with jsonschema and transitive deps
- `test_files/ground_truth/heidegger_being_time.json` - Removed null corrupted_extraction (invalid per v3 schema)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed null corrupted_extraction from heidegger xmark**
- **Found during:** Task 2 (schema validation test revealed it)
- **Issue:** heidegger_being_time.json had `"corrupted_extraction": null` which is not valid per v3 schema (type: string, no nullable)
- **Fix:** Removed the null field entirely (field is optional in schema)
- **Files modified:** test_files/ground_truth/heidegger_being_time.json
- **Commit:** 338ce73

### Note on Task 1

Task 1 (v1-to-v3 migration of 4 ground truth files, old schema deletion, loader update) was already completed by the 14-01 plan executor in commit 384986e. The 14-01 executor proactively migrated ground truth files as part of applying pytestmark to test files. This plan verified the migration was complete and correct, then focused on Task 2 (the validation test).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- v3 schema is the single canonical schema
- All ground truth files pass automated validation
- New ground truth files will automatically be caught by parametrized test if they don't conform to v3
- Phase 17 (Quality Scoring) can rely on consistent ground truth format

## Self-Check: PASSED
