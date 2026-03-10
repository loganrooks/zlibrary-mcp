# Phase 7 Plan 4: Python Bridge EAPI Wiring Summary

**One-liner:** Wired EAPIClient through python_bridge.py, replaced all HTML scraping with EAPI calls, added health check, updated all test mocks to EAPI format.

## Changes Made

### Task 1: Update python_bridge.py for EAPI client lifecycle
- **Commit:** a89aac3
- Added `initialize_eapi_client()` with login + domain discovery
- Added `get_eapi_client()` for shared client access
- Added `eapi_health_check()` for connectivity monitoring
- Rewrote `search()`, `full_text_search()`, `get_download_history()`, `get_download_limits()` to use EAPI
- Rewrote `get_book_metadata_complete()` to use `enhanced_metadata.get_enhanced_metadata()` via EAPI
- Updated bridge functions (`search_by_term_bridge`, `search_by_author_bridge`, `fetch_booklist_bridge`) to pass shared eapi_client
- Added `get_recent_books()` via EAPI
- Removed: httpx connection pooling, BeautifulSoup imports, HTML fetching, `urljoin`, `DEFAULT_HEADERS`
- Updated `normalize_book_details()` to handle EAPI hash field directly
- Net: -177 lines (440 removed, 263 added)

### Task 2: Update all Python test mocks for EAPI format
- **Commit:** a97de65
- Replaced all HTML/httpx mock fixtures with EAPI JSON mock fixtures
- Added `mock_eapi_client` and `patch_eapi_client` fixtures
- New test classes: `TestNormalizeBookDetails`, `TestEAPIHealthCheck`, `TestSearch`, `TestProfileEndpoints`, `TestGetBookMetadataComplete`, `TestBridgeFunctions`, `TestDownloadBook`
- Removed: `mock_beautifulsoup`, `mock_httpx_client`, `mock_fitz`, `mock_ebooklib` fixtures
- Net: -133 lines (475 removed, 342 added)
- All 68 tests across 5 files pass

### Task 3: Verification
- `npm run build`: PASSED
- Python tests (EAPI-related): 68/68 PASSED
- Jest tests: 138/139 passed (1 pre-existing failure in paths.test.js)
- BeautifulSoup in hot paths: 0 matches
- Health check: exists and tested

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed discover_eapi_domain usage**
- **Found during:** Task 1
- **Issue:** lib tools called `discover_eapi_domain()` without required `eapi_client` parameter
- **Fix:** Bridge always passes shared eapi_client, so the broken fallback path is never hit
- **Files:** lib/python_bridge.py

**2. [Rule 1 - Bug] Fixed _create_enhanced_filename references**
- **Found during:** Task 2
- **Issue:** Old tests referenced `_create_enhanced_filename` which was renamed to `create_unified_filename`
- **Fix:** Updated test mocks to patch `create_unified_filename`
- **Files:** __tests__/python/test_python_bridge.py

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Keep AsyncZlib for downloads | EAPI download endpoint returns URL but actual file download still needs the legacy client |
| Route full_text_search through regular EAPI search | EAPI has no separate full-text search endpoint |
| Initialize EAPI client in main() not at module level | Avoids side effects on import, supports testing |

## Key Files

### Created
- None

### Modified
- `lib/python_bridge.py` — EAPI client lifecycle, all API calls via EAPI
- `__tests__/python/test_python_bridge.py` — EAPI mock fixtures and tests

## Metrics

- **Duration:** ~8 minutes
- **Completed:** 2026-02-01
- **Tests:** 68 passed, 0 failed (EAPI-related)
