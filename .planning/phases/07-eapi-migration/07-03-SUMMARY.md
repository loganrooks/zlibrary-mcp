---
phase: 07-eapi-migration
plan: 03
subsystem: lib-tools
tags: [eapi, migration, beautifulsoup-removal, search, metadata]
depends_on: [07-01]
provides: [eapi-backed-lib-tools]
affects: [07-04]
tech-stack:
  removed: [beautifulsoup4, lxml, httpx-direct]
  patterns: [eapi-client-injection, graceful-degradation]
key-files:
  modified:
    - lib/term_tools.py
    - lib/author_tools.py
    - lib/enhanced_metadata.py
    - lib/booklist_tools.py
    - __tests__/python/test_term_tools.py
    - __tests__/python/test_author_tools.py
    - __tests__/python/test_enhanced_metadata.py
    - __tests__/python/test_booklist_tools.py
decisions:
  - id: D-0703-01
    title: Booklist graceful degradation
    choice: Search fallback with degraded flag
    reason: EAPI has no booklist browsing endpoint
  - id: D-0703-02
    title: EAPI fields not available
    choice: Return empty defaults for terms, booklists, IPFS CIDs
    reason: These HTML-only fields have no EAPI equivalent
  - id: D-0703-03
    title: EAPIClient dependency injection
    choice: Optional eapi_client parameter on all functions
    reason: Enables testing and allows python_bridge to share a single client
metrics:
  duration: ~6min
  completed: 2026-02-01
---

# Phase 7 Plan 3: Lib Tools EAPI Migration Summary

**One-liner:** Replaced BeautifulSoup HTML scraping in all 4 lib/ tool modules with EAPIClient calls, removing ~960 lines of parsing code

## What Was Done

### Task 1: term_tools.py and author_tools.py
- Replaced `AsyncZlib` + Paginator pattern with `EAPIClient.search()` + `normalize_eapi_search_response()`
- Removed `construct_term_search_url()`, `parse_term_search_results()`, `_parse_author_search_results()` (HTML parsing functions)
- Added `eapi_client` optional parameter for dependency injection
- Preserved `validate_author_name()` and `format_author_query()` utilities
- Preserved return format: `{term/author, books, total_results}`

### Task 2: enhanced_metadata.py and booklist_tools.py
- **enhanced_metadata.py**: Complete rewrite from 20+ BeautifulSoup extraction functions to EAPI JSON field mapping. New `get_enhanced_metadata()` async function calls `EAPIClient.get_book_info()`. Legacy `extract_complete_metadata()` and `extract_description()` kept as deprecated stubs.
- **booklist_tools.py**: Graceful degradation since EAPI has no booklist endpoint. `fetch_booklist()` falls back to topic-based search, returns `degraded: True` flag.
- Fields unavailable via EAPI (terms, booklists, IPFS CIDs) return empty defaults.

### Test Updates (Deviation - Rule 3)
All 4 test files required rewriting since they imported removed functions and mocked `AsyncZlib`/`BeautifulSoup` patterns. Rewrote to use `AsyncMock` with `eapi_client` injection pattern. 406 tests pass (1 pre-existing failure unrelated to changes).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] sys.path needed zlibrary/src not zlibrary/**
- **Found during:** Task 1 verification
- **Issue:** `from zlibrary.eapi import EAPIClient` failed because sys.path pointed to `zlibrary/` (namespace package) instead of `zlibrary/src/`
- **Fix:** Changed path insert to `zlibrary/src` directory

**2. [Rule 3 - Blocking] Test files imported removed functions**
- **Found during:** Verification
- **Issue:** All 4 test files imported functions that were removed (construct_booklist_url, parse_term_search_results, etc.) and mocked AsyncZlib which was no longer used
- **Fix:** Rewrote all 4 test files to use EAPI mocking patterns
- **Files:** test_term_tools.py, test_author_tools.py, test_enhanced_metadata.py, test_booklist_tools.py

## Commits

| Hash | Message |
|------|---------|
| 122d4b2 | feat(07-03): migrate term_tools and author_tools to EAPI |
| ddf712a | feat(07-03): migrate enhanced_metadata and booklist_tools to EAPI |
| b667f98 | test(07-03): update tests for EAPI-migrated lib/ tools |

## Next Phase Readiness

Plan 07-04 (python_bridge integration) can proceed. All lib/ tools now accept `eapi_client` parameter. The bridge needs to:
1. Create a shared EAPIClient instance
2. Pass it to term_tools, author_tools, enhanced_metadata, booklist_tools calls
3. Update `get_book_metadata_complete()` to use `get_enhanced_metadata()` instead of `extract_complete_metadata()`
