---
phase: 14-test-infrastructure
plan: 03
subsystem: ci/devops
tags: [ci, github-actions, repo-cleanup, pytest-markers]
requires:
  - phase: 14-01
    provides: "pytest marker registration (slow, integration, benchmark)"
provides:
  - "Clean repo root (zero .py files)"
  - "Fast CI job (test-fast) with marker-based test filtering"
  - "Full CI job (test-full) on push-to-master + manual dispatch"
  - "workflow_dispatch input for manual full suite trigger"
affects: [ci, repo-structure, developer-experience]
tech-stack:
  added: []
  patterns: ["CI fast/full split via pytest markers", "workflow_dispatch for manual full suite"]
key-files:
  created: []
  modified:
    - ".github/workflows/ci.yml"
    - "scripts/debugging/debug_asterisk_full_search.py (relocated)"
    - "scripts/debugging/debug_find_asterisk_anywhere.py (relocated + fixed)"
    - "scripts/debugging/debug_kant_page2_asterisk.py (relocated)"
    - "scripts/debugging/debug_kant_page3_content.py (relocated)"
    - "scripts/debugging/debug_page2_block10_11.py (relocated)"
    - "scripts/debugging/debug_page3_block8_full.py (relocated)"
    - "scripts/debugging/debug_page3_continuation.py (relocated)"
    - "scripts/validation/multi_corpus_validation.py (relocated)"
    - "scripts/archive/test_footnote_validation.py (relocated)"
    - "scripts/archive/test_kant_page2_debug.py (relocated)"
key-decisions:
  - "Used git mv for all relocations to preserve file history"
  - "test-fast runs on both push and PR for fast feedback; test-full only on push-to-master and manual dispatch"
  - "Added --benchmark-disable to fast job to skip pytest-benchmark overhead"
patterns-established:
  - "CI fast/full split: marker-based test filtering for PR speed, full suite on merge"
duration: 22min
completed: 2026-02-11
---

# Phase 14 Plan 03: Repo Cleanup and CI Split Summary

**Relocated 10 root Python scripts to scripts/ and split CI into fast (6s) and full (19min) test paths using pytest markers**

## Performance
- **Duration:** 22min
- **Tasks:** 2/2 completed
- **Files modified:** 11 (10 relocated + 1 CI config)

## Accomplishments
- Moved all 10 stray Python files from repo root to organized subdirectories (scripts/debugging/, scripts/validation/, scripts/archive/)
- Split single CI test job into test-fast (every PR, ~6s) and test-full (push-to-master + manual, ~19min)
- Added workflow_dispatch input allowing manual full suite trigger
- Fast test path filters with `-m "not slow and not integration" --benchmark-disable` running 719 tests in 5.8s
- Full suite runs 871 tests (846 pass, 5 skip, 7 xfail, 23 pre-existing failures from integration/real-world tests)

## Task Commits
1. **Task 1: Relocate Python files from repo root to scripts/** - `1b1601a`
2. **Task 2: Split CI into fast and full test jobs** - `eb8bbac`

## Files Created/Modified
- `.github/workflows/ci.yml` - Split into test-fast, test-full, and audit jobs with workflow_dispatch
- `scripts/debugging/debug_*.py` (7 files) - Relocated from repo root
- `scripts/validation/multi_corpus_validation.py` - Relocated from repo root
- `scripts/archive/test_footnote_validation.py` - Relocated from repo root
- `scripts/archive/test_kant_page2_debug.py` - Relocated from repo root

## Decisions & Deviations

### Decisions
- **git mv for relocations**: Preserves file history in git log
- **test-fast on all triggers**: Both push and PR get fast feedback (test-full only on push-to-master)
- **--benchmark-disable in fast job**: Skips pytest-benchmark collection overhead without excluding benchmark-decorated tests

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Python 3.10-incompatible f-string syntax in debug_find_asterisk_anywhere.py**
- **Found during:** Task 1 (pre-commit hook ruff check)
- **Issue:** f-strings used `f"{"=" * 80}"` syntax which requires Python 3.12+ but project targets >=3.10
- **Fix:** Changed to `f"{'=' * 80}"` (single quotes inside f-string)
- **Files modified:** scripts/debugging/debug_find_asterisk_anywhere.py
- **Commit:** 1b1601a

**2. [Rule 3 - Blocking] Ruff auto-fixed 39 lint issues across relocated scripts**
- **Found during:** Task 1 (pre-commit hook ruff check + ruff format)
- **Issue:** Pre-existing lint/format issues in debug scripts triggered pre-commit failures
- **Fix:** Allowed ruff auto-fix (39 issues) and manually fixed 2 remaining syntax errors
- **Files modified:** All 10 relocated scripts (formatting changes)
- **Commit:** 1b1601a

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Repo root is clean of stray Python files (prerequisite for Phase 15 cleanup)
- CI provides fast PR feedback (~6s) while maintaining full suite as safety net on merge
- All pytest markers from 14-01 are now leveraged in CI pipeline

## Self-Check: PASSED
- 14-03-SUMMARY.md: FOUND
- Commit 1b1601a (Task 1): FOUND
- Commit eb8bbac (Task 2): FOUND
- .github/workflows/ci.yml: FOUND
- scripts/debugging/debug_asterisk_full_search.py: FOUND
- scripts/archive/test_footnote_validation.py: FOUND
- Root .py files count: 0
