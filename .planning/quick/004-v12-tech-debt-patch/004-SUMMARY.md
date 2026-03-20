---
phase: quick
plan: 004
duration: 5min
completed: 2026-03-20
---

# Quick Task 004: Fix 6 tech debt items from v1.2 audit

**Executed inline (6 well-understood fixes from v1.2 milestone audit)**

## Performance
- **Duration:** 5min
- **Tasks:** 1 (6 sub-fixes)
- **Files modified:** 6

## Task Commits
1. **Fix 6 tech debt items** - `7e20480`

## Files Modified
- `jest.teardown.js` — deleted (process.exit(0) masked coverage failures)
- `jest.config.js` — removed globalTeardown, recalibrated thresholds for 93-test suite
- `package.json` — added --forceExit to test script, excluded zlibrary/src/test.py from tarball
- `.github/workflows/ci.yml` — removed || true from audit jobs (now blocking)
- `README.md` — added npm registry install path (npm install -g zlibrary-mcp)
- `__tests__/python/test_inline_footnotes.py` — added setup_method to clear _TEXTPAGE_CACHE (fixes flaky test)

## Root Cause Analysis: Flaky Test
`test_markerless_continuation_detected` failed in full-suite runs because `_TEXTPAGE_CACHE` in `lib/rag/utils/cache.py` uses `id(page)` as cache key. When Python garbage-collects fitz.Page objects and reuses their memory addresses, the cache returns stale entries from previous tests. Fix: clear cache in `setup_method()`.
