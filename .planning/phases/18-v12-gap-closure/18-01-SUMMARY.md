---
phase: 18-v12-gap-closure
plan: 01
subsystem: testing
tags: [pytest, ground-truth, performance, footnotes]
requires:
  - phase: 17-quality-gates
    provides: CI pipeline that surfaces test-full failures on push-to-master
provides:
  - 4 footnote tests fixed to use v3 ground truth schema accessors
  - 3 performance tests with CI-appropriate thresholds (3x original values)
affects: [test-full CI, test_real_footnotes.py, test_inline_footnotes.py, test_garbled_performance.py, test_superscript_detection.py]
tech-stack:
  added: []
  patterns: [v3 ground truth schema key access pattern: footnote["marker"]["symbol"] and footnote["definition"]["content"]]
key-files:
  created: []
  modified:
    - __tests__/python/test_real_footnotes.py
    - __tests__/python/test_inline_footnotes.py
    - __tests__/python/test_garbled_performance.py
    - __tests__/python/test_superscript_detection.py
key-decisions:
  - "Fix test code to match v3 schema, not the ground truth data (16/16 schema validation tests already passing confirmed v3 JSON is correct)"
  - "Static 3x multiplier for performance thresholds (0.005→0.015, 0.001→0.003, 0.010→0.030) covers both local and CI variance"
  - "No conditional CI environment detection — static loosening is simpler and the thresholds were too tight even locally"
patterns-established:
  - "v3 footnote accessor: footnote[\"marker\"][\"symbol\"] for symbol, footnote[\"definition\"][\"content\"] for content body"
duration: 18min
completed: 2026-03-20
---

# Phase 18 Plan 01: Fix 7 Broken test-full CI Tests Summary

**Fixed 4 v3 schema accessor failures in footnote tests and loosened 3 performance thresholds with 3x multiplier, making test-full CI green on push-to-master.**

## Performance
- **Duration:** 18min
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments
- Fixed `test_footnote_detection_with_real_pdf`: replaced `footnote["marker"]` / `footnote["expected_output"]` / `footnote["content"]` with v3 equivalents
- Fixed `test_footnote_marker_in_body_text`: removed non-existent `marker_context` key, updated to `marker_symbol`
- Fixed `test_footnote_content_extraction`: updated both `marker` and `content` accessors to v3 nested keys
- Fixed `test_derrida_traditional_footnotes_regression`: removed `expected_output` key reference, updated to v3 schema
- Loosened `test_detection_long_text_scales_linearly`: 5ms → 15ms absolute threshold
- Loosened `test_typical_region_fast`: 1ms → 3ms average threshold
- Loosened `test_superscript_check_performance`: 10ms → 30ms total threshold
- Verified 79 passed across all 4 files with no regressions introduced
- Verified 719 non-integration tests pass with 0 failures

## Task Commits
1. **Task 1: Fix footnote tests to use v3 ground truth schema accessors** - `c250e0e`
2. **Task 2: Loosen performance test thresholds with 3x multiplier** - `0b8b455`

## Files Created/Modified
- `__tests__/python/test_real_footnotes.py` - Updated 3 test methods to use `footnote["marker"]["symbol"]` and `footnote["definition"]["content"]`
- `__tests__/python/test_inline_footnotes.py` - Updated regression test to use v3 schema accessors, removed `expected_output` key reference
- `__tests__/python/test_garbled_performance.py` - Loosened `large_time < 0.005` to `< 0.015` and `avg_time < 0.001` to `< 0.003`
- `__tests__/python/test_superscript_detection.py` - Loosened `elapsed < 0.010` to `< 0.030`, updated comment and error message

## Decisions & Deviations

**Decisions:**
- Fixed test code to match v3 schema (not the ground truth data). The 16/16 schema validation tests confirmed v3 JSON was correct — the test accessors were stale.
- Used static 3x multiplier for performance thresholds. No CI environment variable detection needed — thresholds were too tight even locally, per RESEARCH.md analysis showing 2–2.8x observed variance.

**Deviations:**
- Plan specified class `TestGarbledDetectionPerformance` for `test_detection_long_text_scales_linearly`, but actual class is `TestPerformance`. Corrected without impact on outcomes. (Rule 1 - auto-fixed)
- Plan specified class `TestDerridaTraditionalRegression` for the inline footnote test, but actual class is `TestRealWorldInlineFootnotes`. Corrected without impact on outcomes. (Rule 1 - auto-fixed)
- Pre-existing flaky test `TestMarkerlessContinuation::test_markerless_continuation_detected` fails in full-suite runs due to test isolation (shared PDF state), passes in isolation. Was already failing before these changes (confirmed via git stash). Not introduced by this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
ISSUES.md ISSUE-GT-001 and ISSUE-PERF-001 can now be marked resolved (handled in Plan 02). test-full CI should pass on push-to-master for these 7 tests. Pre-existing integration test failure (TestRealBasicSearch) requires real Z-Library credentials and is unrelated.

## Self-Check: PASSED

- FOUND: .planning/phases/18-v12-gap-closure/18-01-SUMMARY.md
- FOUND: c250e0e (fix footnote tests to use v3 ground truth schema accessors)
- FOUND: 0b8b455 (loosen performance test thresholds with 3x multiplier)
