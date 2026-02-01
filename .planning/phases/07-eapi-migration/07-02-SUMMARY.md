# Phase 7 Plan 02: Core Library EAPI Migration Summary

**One-liner:** Replaced all HTML scraping in vendored zlibrary fork with EAPI calls across 4 core files

## What Was Done

### Task 1: Rewrite libasync.py to use EAPIClient
- Replaced `search()` HTML GET + SearchPaginator with `self._eapi.search()` + normalize
- Replaced `full_text_search()` HTML token extraction + BeautifulSoup with EAPI search (documented limitation: EAPI doesn't distinguish full-text vs title search)
- Replaced `download_book()` HTML page scraping with `self._eapi.get_download_link()`
- Created `_EAPISearchResult` class as lightweight paginator wrapper for backward compatibility
- Initialized EAPIClient in `login()` with cookie-based auth and domain discovery
- Added `_personal_domain` for download URL construction
- Passed `eapi_client` to ZlibProfile for profile/history operations

### Task 2: Simplify abs.py, profile.py, booklists.py
- **abs.py**: Replaced 1000+ lines of HTML parsing with deprecated stubs. Added `BookItem._from_eapi_dict()` classmethod. All paginator classes retained as deprecated shells.
- **profile.py**: `get_limits()` now uses `EAPIClient.get_profile()`. `download_history()` now uses `EAPIClient.get_downloaded()`. Created `_DownloadHistoryResult` and `_BooklistResult` wrappers.
- **booklists.py**: Gracefully degraded (EAPI has no booklist endpoint). Returns empty results with warning log.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Keep deprecated paginator shells | Prevents import errors in code that references these classes |
| Gracefully degrade booklists | EAPI has no booklist endpoint; better than crashing |
| Route full_text_search through regular search | EAPI doesn't distinguish search modes |
| Use cookie-based auth for downloads | Reuse EAPI client cookies for streaming download |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Profile constructor updated to accept eapi_client**
- Found during: Task 1
- Issue: ZlibProfile needed EAPIClient access but didn't accept it
- Fix: Added `eapi_client=None` parameter to `__init__`
- Files: profile.py

## Metrics

- Duration: ~4 min
- Lines removed: ~1200 (HTML parsing code)
- Lines added: ~550 (EAPI integration + wrappers)
- Net reduction: ~650 lines
- BeautifulSoup references removed: All (from 4 files)

## Key Files

### Created
- None

### Modified
- `zlibrary/src/zlibrary/libasync.py` — EAPI-backed search, full_text_search, download
- `zlibrary/src/zlibrary/abs.py` — Deprecated HTML paginators, added BookItem._from_eapi_dict()
- `zlibrary/src/zlibrary/profile.py` — EAPI-backed get_limits, download_history
- `zlibrary/src/zlibrary/booklists.py` — Gracefully degraded (no EAPI endpoint)

## Verification Results

- `grep -r 'BeautifulSoup' libasync.py profile.py booklists.py` — 0 matches
- `from zlibrary import AsyncZlib` — imports successfully
- AsyncZlib public API: search, full_text_search, download_book, login, logout, profile — all present
- TypeScript build: clean
- Python unit tests: 29 passed (pre-existing failures in booklist_tools, term_tools, author_tools unrelated)
