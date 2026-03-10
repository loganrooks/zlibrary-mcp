# Phase 12: Anna's Archive Integration - Context

**Gathered:** 2026-02-02
**Updated:** 2026-02-03 (after experimental validation)
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can search and download books from Anna's Archive as the primary source (user has API key with 25 fast downloads/day), with LibGen as fallback when quota is exhausted or Anna's is unavailable. Clear source attribution in results.

**Experimental findings (see 12-EXPERIMENT.md and 12-RESEARCH.md):**
- Anna's Archive fast download API works with `domain_index=1`
- Search requires HTML scraping (no search API)
- Slow downloads blocked by DDoS-Guard — not implementing
- LibGen works via `libgen-api-enhanced` library

</domain>

<decisions>
## Implementation Decisions

### Source priority (UPDATED)
- **Primary: Anna's Archive** — user has paid API key (25 fast downloads/day)
- **Fallback: LibGen** — free, no quota, for when Anna's quota exhausted
- Default source is `auto` (Anna's Archive if key present, else LibGen)
- Manual override via `source` parameter on search tools

### Anna's Archive implementation
- **Search:** HTML scraping at `/search?q=...` (selector: `a[href^='/md5/']`)
- **Download:** Fast download API at `/dyn/api/fast_download.json`
- **CRITICAL:** Use `domain_index=1` parameter — domain_index=0 returns HTTPS URLs with SSL errors
- Track quota via `account_fast_download_info` in API response
- Trigger fallback when `downloads_left` reaches 0

### LibGen implementation
- Use `libgen-api-enhanced` library (import as `libgen_api_enhanced`, NOT `libgen_api`)
- Wrap sync calls in `asyncio.to_thread()` to avoid blocking
- Download via `tor_download_link` field or resolved mirrors

### What NOT to implement
- Anna's Archive slow downloads (blocked by DDoS-Guard, requires browser automation)
- Parallel mode (defer to future enhancement)

### Fallback trigger logic
- Fallback activates on: Anna's quota exhausted, Anna's errors/timeouts, manual override
- Manual override via `source` parameter (`source: 'annas' | 'libgen' | 'auto'`)
- On fallback: clean switch — return only fallback source results

### Source attribution & result schema
- All results include `source` field ('annas_archive' or 'libgen')
- Unified result schema with common fields: md5, title, author, year, extension, size, download_url
- Source-specific extras in `extra` dict if needed

### Configuration
- `ANNAS_SECRET_KEY` — required for Anna's Archive downloads
- `ANNAS_BASE_URL` — optional, for mirror switching (default: https://annas-archive.li)
- `LIBGEN_MIRROR` — optional, LibGen mirror (default: li)
- `BOOK_SOURCE_DEFAULT` — 'auto' | 'annas' | 'libgen' (default: auto)
- `BOOK_SOURCE_FALLBACK_ENABLED` — true/false (default: true)

</decisions>

<specifics>
## Specific Implementation Notes

### Validated code patterns (from experiments)
All patterns in 12-RESEARCH.md are experimentally validated and can be used directly.

### Critical details
1. **domain_index=1 is mandatory** — domain_index=0 SSL errors confirmed
2. **Import path:** `from libgen_api_enhanced import LibgenSearch`
3. **Quota tracking:** API returns `downloads_left`, `downloads_done_today`, `downloads_per_day`
4. **Async wrapping:** LibGen library is sync, must use `asyncio.to_thread()`

### Environment setup
User has `.env` file with `ANNAS_SECRET_KEY` set. The experiment scripts in `scripts/experiments/` demonstrate working patterns.

</specifics>

<deferred>
## Deferred Ideas

- Parallel mode (query both sources, merge results) — add in future if needed
- Anna's Archive slow downloads — would require Playwright, not worth complexity
- Advanced search filters — implement basic search first

</deferred>

---

*Phase: 12-annas-archive*
*Context gathered: 2026-02-02*
*Updated after experiments: 2026-02-03*
