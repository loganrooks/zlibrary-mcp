---
phase: 14-test-infrastructure
plan: 01
subsystem: testing
tags: [pytest, markers, test-selection, ci]
requires: []
provides:
  - "7-marker pytest taxonomy (unit, integration, slow, ground_truth, real_world, performance, e2e)"
  - "Module-level pytestmark on all 39 Python test files"
  - "Strict marker enforcement via --strict-markers in addopts"
  - "Fast test subset: 698 tests in ~4s via -m 'not slow and not integration'"
affects: [test-infrastructure, ci-pipeline, developer-workflow]
tech-stack:
  added: []
  patterns: [pytest-marker-taxonomy, strict-marker-enforcement]
key-files:
  created: []
  modified:
    - pytest.ini
    - "__tests__/python/test_*.py (38 files)"
    - "__tests__/python/integration/test_real_zlibrary.py"
key-decisions:
  - "Used addopts = --strict-markers instead of strict_markers = true (pytest 8.x compatibility)"
  - "Added import pytest to 3 files missing it (compositor, margin_integration, resolution_analyzer)"
  - "Kept existing class-level @pytest.mark decorators alongside module-level pytestmark (redundant but safe)"
  - "Converted test_real_zlibrary.py pytestmark from skipif-only to list with integration marker + skipif"
patterns-established:
  - "Module-level pytestmark: Every test file declares pytestmark after imports, before first class/function"
  - "Marker taxonomy: unit (fast/mocked), slow (real PDFs), ground_truth (JSON validation), integration (credentials), performance (benchmarks), real_world (full validation), e2e (pipeline tests)"
duration: 21min
completed: 2026-02-11
---

# Phase 14 Plan 01: Pytest Marker Taxonomy Summary

**7-marker pytest taxonomy with strict enforcement and module-level pytestmark on all 39 test files, enabling marker-based test selection for CI and developer workflows**

## Performance
- **Duration:** 21 minutes
- **Tasks:** 2/2 completed
- **Files modified:** 40

## Accomplishments
- Registered complete 7-marker taxonomy in pytest.ini: unit, integration, slow, ground_truth, real_world, performance, e2e
- Enabled strict marker enforcement via addopts = --strict-markers (pytest 8.x compatible)
- Applied pytestmark to all 39 Python test files with correct classification
- Fast subset (not slow, not integration) selects 713/865 tests, runs 698 in ~4 seconds
- Fixed 24 pre-existing ruff lint issues in test files (F841 unused vars, E712 equality checks, F401 unused imports, F601 duplicate dict keys)

## Task Commits
1. **Task 1: Register complete marker taxonomy in pytest.ini** - `9b1b2af`
2. **Task 2: Apply pytestmark to all Python test files** - `db45908`

## Marker Distribution
| Marker | Files | Description |
|--------|-------|-------------|
| unit | 29 | Mocked dependencies, no real file I/O |
| slow | 3 | Real PDF processing via PyMuPDF |
| slow + ground_truth | 2 | Real PDFs + ground truth JSON validation |
| real_world + slow + ground_truth | 1 | Full real-world validation |
| performance | 2 | Timing/benchmark tests |
| integration | 2 | Requires Z-Library credentials |

## Files Created/Modified
- `pytest.ini` - Added unit + ground_truth markers, enabled --strict-markers via addopts
- `__tests__/python/test_*.py` (38 files) - Added pytestmark declarations
- `__tests__/python/integration/test_real_zlibrary.py` - Updated pytestmark to list with integration marker + skipif

## Decisions & Deviations

### Decisions
1. **addopts vs strict_markers config key:** pytest 8.x does not support `strict_markers = true` as a config key (throws PytestConfigWarning). Used `addopts = --strict-markers` instead, which is the correct approach for pytest 8.x.

2. **Existing decorators preserved:** For test_pipeline_integration.py and integration/test_real_zlibrary.py, kept existing `@pytest.mark.integration` class decorators alongside new module-level pytestmark (redundant but safe per plan guidance).

### Deviations

**1. [Rule 1 - Bug] Fixed addopts config for pytest 8.x**
- **Found during:** Task 1
- **Issue:** Plan specified `strict_markers = true` config key, but pytest 8.4.2 doesn't recognize it (PytestConfigWarning: Unknown config option)
- **Fix:** Used `addopts = --strict-markers` which is the correct pytest 8.x mechanism
- **Files modified:** pytest.ini
- **Commit:** 9b1b2af

**2. [Rule 3 - Blocking] Fixed 24 pre-existing ruff lint issues**
- **Found during:** Task 2 (pre-commit hook failure)
- **Issue:** Pre-commit hook runs ruff on entire staged files, blocking commit due to pre-existing F841, E712, F401, F601 violations
- **Fix:** Prefixed unused variables with underscore, used `is True`/`is False` instead of `== True`/`== False`, added `# noqa: F401` for availability-check imports, removed duplicate dict key
- **Files modified:** 10 test files
- **Commit:** db45908

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All test files have markers, enabling CI to run fast subset via `-m "not slow and not integration"`
- Strict enforcement prevents future test files from using unregistered markers
- Ready for Plan 02 (if any) or next phase

## Self-Check: PASSED
- pytest.ini: FOUND
- 14-01-SUMMARY.md: FOUND
- Commit 9b1b2af: FOUND
- Commit db45908: FOUND
- Test files missing pytestmark: 0
- strict-markers in pytest.ini: FOUND
- Markers registered: 7
