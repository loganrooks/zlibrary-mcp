---
phase: 12-annas-archive
plan: 04
subsystem: api
tags: [multi-source, router, fallback, annas-archive, libgen]

# Dependency graph
requires:
  - phase: 12-02
    provides: AnnasArchiveAdapter with search and fast download
  - phase: 12-03
    provides: LibgenAdapter with async search and rate limiting
provides:
  - SourceRouter with automatic fallback logic
  - search_multi_source function in python_bridge.py
  - Source attribution in all search results
affects: [mcp-tools, future-sources]

# Tech tracking
tech-stack:
  added: []
  patterns: [router-fallback, lazy-adapter-initialization]

key-files:
  created:
    - lib/sources/router.py
    - __tests__/python/test_source_router.py
  modified:
    - lib/sources/__init__.py
    - lib/python_bridge.py

key-decisions:
  - "ROUTER-AUTO-SOURCE: Auto mode uses Anna's if ANNAS_SECRET_KEY set, else LibGen"
  - "ROUTER-LAZY-INIT: Adapters created only when first needed"
  - "ROUTER-QUOTA-FALLBACK: Zero downloads_left triggers fallback to LibGen"

patterns-established:
  - "Router pattern: Central router dispatches to source adapters with fallback"
  - "Source attribution: All results include source field for transparency"

# Metrics
duration: 6min
completed: 2026-02-03
---

# Phase 12 Plan 04: Source Router Summary

**SourceRouter with auto source selection, Anna's-primary/LibGen-fallback, and search_multi_source bridge function**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-03T12:00:00Z
- **Completed:** 2026-02-03T12:06:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created SourceRouter with intelligent source selection and automatic fallback
- Implemented comprehensive test suite (17 tests) covering all router paths
- Wired search_multi_source into python_bridge.py for MCP tool access
- Results include source attribution for transparency

## Task Commits

Each task was committed atomically:

1. **Task 1: Create source router with fallback logic** - `16d0f45` (feat)
2. **Task 2: Create router integration tests** - `ab67e5d` (test)
3. **Task 3: Wire router into python_bridge.py** - `a453622` (feat)

## Files Created/Modified
- `lib/sources/router.py` - SourceRouter with fallback logic (173 lines)
- `lib/sources/__init__.py` - Added SourceRouter export
- `lib/python_bridge.py` - Added search_multi_source function and router cleanup
- `__tests__/python/test_source_router.py` - 17 tests for router behavior

## Decisions Made

1. **ROUTER-AUTO-SOURCE:** 'auto' source selection uses Anna's Archive if ANNAS_SECRET_KEY is set, otherwise falls back to LibGen. This allows users without Anna's API key to still use the system.

2. **ROUTER-LAZY-INIT:** Adapters are created only when first needed (_get_annas, _get_libgen). This avoids unnecessary resource allocation and allows the router to be instantiated without immediate network calls.

3. **ROUTER-QUOTA-FALLBACK:** When Anna's get_download_url returns quota_info with downloads_left=0, the router raises QuotaExhaustedError internally and falls back to LibGen (if fallback_enabled). This proactive fallback prevents wasted API calls.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required beyond existing ANNAS_SECRET_KEY environment variable (documented in 12-02).

## Next Phase Readiness

Phase 12 complete. Multi-source book search is now available:
- Anna's Archive as primary source (requires API key)
- LibGen as automatic fallback
- Source attribution in all results
- Ready for MCP tool integration

**Phase 12 Success Criteria Verified:**
- Anna's Archive search returns results with MD5 hashes
- Fast download API uses domain_index=1 (avoiding SSL errors)
- LibGen fallback available when Anna's unavailable or quota exhausted
- Source indicator in all results (annas_archive or libgen)
- Configuration via environment variables

---
*Phase: 12-annas-archive*
*Completed: 2026-02-03*
