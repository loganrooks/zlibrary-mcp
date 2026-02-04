# Phase 12: LibGen Ecosystem Deep Dive - Research Addendum

**Researched:** 2026-02-03
**Domain:** LibGen Python libraries, webscraping stability, mirror ecosystem
**Confidence:** MEDIUM (multiple sources, some verification gaps)

## Summary

This addendum supplements the main 12-RESEARCH.md with in-depth analysis of the LibGen ecosystem. The existing research correctly identified `libgen-api-enhanced` as the recommended library, but lacked alternatives analysis and build-vs-buy justification.

**Key findings:**
1. `libgen-api-enhanced` is the best choice among available libraries (actively maintained, good features)
2. `libgen-api-modern` is a viable alternative with async support but less proven
3. Building a custom scraper is NOT recommended — maintenance burden outweighs benefits
4. LibGen has no official search API — all libraries use HTML scraping
5. Mirror stability is an ongoing concern — libraries must support mirror switching

**Primary recommendation:** Use `libgen-api-enhanced` v1.2.4 with configurable mirror support. Do not build custom scraper.

---

## LibGen Library Landscape

### Evaluated Libraries

| Library | Version | Last Update | Stars | Maintenance | Async | Recommendation |
|---------|---------|-------------|-------|-------------|-------|----------------|
| [libgen-api-enhanced](https://github.com/onurhanak/libgen-api-enhanced) | 1.2.4 | Oct 2025 | 53 | Active | No | **USE THIS** |
| [libgen-api-modern](https://pypi.org/project/libgen-api-modern/) | 1.0.0 | Jul 2025 | ? | New | Yes | Alternative |
| [grab-fork-from-libgen](https://github.com/Lamarcke/grab-fork-from-libgen) | 3.5.0 | Mar 2025 | 3 | Maintained | Yes | Too complex |
| [libgen-api](https://github.com/harrison-broadbent/libgen-api) | 1.0.0 | Jan 2022 | 216 | Abandoned | No | Do not use |
| [libgenparser](https://github.com/BeastImran/libgenparser) | - | Dec 2022 | 8 | Archived | Yes | Do not use |
| [libgen](https://pypi.org/project/libgen/) | - | 12+ mo | - | Inactive | No | Do not use |

### libgen-api-enhanced (RECOMMENDED)

**Why it's the best choice:**
1. **Actively maintained** — latest release Oct 29, 2025
2. **Zero open issues** — 6 issues total, all resolved
3. **Issue response time** — most resolved within 5-10 days
4. **Mirror support** — configurable mirror extension (.li, .bz, .gs, etc.)
5. **Experimentally validated** — works in our test environment (see 12-EXPERIMENT.md)
6. **Simple dependencies** — only requires `bs4` and `requests`
7. **Good feature set** — search by title/author, filters, direct download links

**Limitations:**
- Synchronous only (must wrap in `asyncio.to_thread()`)
- No built-in rate limiting
- Download link resolution sometimes returns None (Tor links work)

**Dependencies:**
```
bs4
requests
Python >=3.10
```

**Import (CRITICAL):**
```python
# Package name differs from import name!
from libgen_api_enhanced import LibgenSearch  # NOT libgen_api
```

### libgen-api-modern (Alternative)

**Potential advantages:**
- Native async support via `aiohttp`
- Modern CLI interface
- Sync + async functions (`search_sync`, `search_async`)

**Concerns:**
- Very new (v1.0.0, Jul 2025)
- GitHub repo not found (404)
- Less battle-tested
- Unknown issue response time

**Verdict:** Monitor but don't adopt yet. If async becomes critical and libgen-api-enhanced doesn't meet needs, reconsider.

### grab-fork-from-libgen (Not Recommended)

**Why not:**
- Requires Calibre installation for downloads
- More complex API surface
- Only 3 stars (less community validation)
- The Calibre dependency adds significant setup friction

**When to consider:** Only if format conversion (PDF <-> EPUB <-> MOBI) becomes a requirement.

---

## LibGen API Reality

### No Official Search API

LibGen provides a JSON API at `json.php` but it does NOT support search:

```
# This works (by ID):
curl 'http://libgen.io/json.php?ids=1,2&fields=Title,Author,MD5'

# This does NOT exist:
curl 'http://libgen.io/search.php?query=python'  # No JSON search API
```

The API is designed for mirror maintainers to sync databases, not for end-user search. All Python libraries implement search by:
1. HTTP GET to `search.php` with query parameter
2. Parse HTML response to extract book entries
3. Optionally fetch full metadata via `json.php` using extracted IDs

**Implication:** Search always involves HTML scraping. This is a fundamental constraint, not a library limitation.

### Rate Limiting

From [libgen API documentation](https://garbage.world/the-library-genesis-api.html):

> "The Library Genesis maintainers very kindly made a public API that doesn't require an API key to use, so don't abuse it or they might change that. In any case, if you make too many requests in a short period of time they'll temporarily block your IP address."

**Recommendations:**
- Implement application-level rate limiting
- Add delays between requests (1-2 seconds minimum)
- Cache search results when possible

---

## Mirror Ecosystem

### Current Working Mirrors (as of Jan 2026)

| Mirror | Status | Notes |
|--------|--------|-------|
| libgen.li | Working | Default in libgen-api-enhanced |
| libgen.rs | Working | Alternative recommended |
| libgen.la | Working | Commonly cited |
| libgen.bz | Working | Supported by libraries |
| libgen.gs | Working | Supported by libraries |
| libgen.vg | Working | Less common |
| libgen.is | Unstable | Historical issues |
| libgen.io | Unstable | Often down |

**Mirror Monitoring Resources:**
- [libgen.help](https://libgen.help/) — Live status monitoring
- [libgen.so](https://libgen.so) — Mirror verification pipeline

### Mirror Switching in libgen-api-enhanced

```python
from libgen_api_enhanced import LibgenSearch

# Default mirror (.li)
s = LibgenSearch()

# Custom mirror
s = LibgenSearch(mirror="rs")  # Uses libgen.rs
s = LibgenSearch(mirror="bz")  # Uses libgen.bz
```

**Implementation strategy:**
1. Default to `.li` (most stable per library maintainer)
2. Allow user override via `LIBGEN_MIRROR` env var
3. Consider mirror fallback on connection failure

---

## Webscraping Stability Analysis

### Historical Breakage in libgen-api-enhanced

From GitHub issues:
- **Issue #9 (Oct 2025):** "Frequently unable to search for any books?" — resolved
- **Issue #2 (Jul-Aug 2025):** "the domain is Down" — domain change required
- **Issue #1 (Feb-Mar 2025):** "libgen.is not work" — mirror update needed

**Pattern:** Issues are primarily about mirror availability, not HTML structure changes.

### General Webscraping Risk

From [Crawlbase 2025](https://crawlbase.com/blog/web-scraping-challenges-and-solutions/):

> "Websites often change their HTML structure and API endpoints... These frequent changes hinder scrapers from carrying out their tasks."

**LibGen-specific assessment:**
- LibGen's HTML structure is relatively stable (simple table layout)
- The main breakage source is domain/mirror changes, not HTML redesigns
- Libraries handle this through configurable mirror support
- Release v1.1.3 specifically included "fix default mirror"

**Confidence:** MEDIUM — LibGen HTML has been stable historically, but no guarantees.

---

## Build vs Buy Decision

### Option A: Use libgen-api-enhanced (RECOMMENDED)

**Pros:**
- Battle-tested (53 stars, used by others)
- Maintained by someone else (issue response 5-10 days)
- Mirror issues already handled
- ~200 lines of code we don't maintain

**Cons:**
- Dependency on external maintainer
- Synchronous (requires thread wrapping)
- No control over release timing

### Option B: Build Custom Scraper (NOT RECOMMENDED)

**Pros:**
- Full control over implementation
- Can optimize for our specific needs
- No external dependency

**Cons:**
- **Significant maintenance burden** — estimated 2-4 hours per mirror/HTML change
- Need to monitor LibGen changes ourselves
- Duplicating work already done by the community
- Time better spent on core features

### Option C: Vendor/Fork libgen-api-enhanced (FALLBACK)

**When to consider:**
- If maintainer abandons project (no updates for 6+ months)
- If critical bug not addressed
- If we need modifications they won't merge

**How:**
1. Fork repository
2. Copy to `vendors/libgen_api_enhanced/`
3. Import from vendored copy
4. Apply patches as needed

**Current verdict:** Not needed. Library is actively maintained.

---

## Recommendation Summary

### Use: libgen-api-enhanced v1.2.4

```bash
# Installation
pip install libgen-api-enhanced==1.2.4
# or
uv add libgen-api-enhanced
```

### Configuration

```python
import os
from libgen_api_enhanced import LibgenSearch

# Get mirror from env, default to 'li'
mirror = os.environ.get('LIBGEN_MIRROR', 'li')
s = LibgenSearch(mirror=mirror)
```

### Async Wrapper Pattern

```python
import asyncio
from libgen_api_enhanced import LibgenSearch

async def search_libgen(query: str, mirror: str = 'li') -> list:
    """Async wrapper for synchronous LibGen library."""
    def _search():
        s = LibgenSearch(mirror=mirror)
        return s.search_title(query)

    return await asyncio.to_thread(_search)
```

### Rate Limiting

```python
import time

class LibgenAdapter:
    MIN_REQUEST_INTERVAL = 2.0  # seconds

    def __init__(self):
        self._last_request = 0

    async def search(self, query: str) -> list:
        # Respect rate limit
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

        self._last_request = time.time()
        return await search_libgen(query)
```

---

## Common Pitfalls (LibGen-Specific)

### Pitfall 1: Wrong Import Name
**What goes wrong:** `ModuleNotFoundError: No module named 'libgen_api'`
**Cause:** Package name `libgen-api-enhanced` differs from import `libgen_api_enhanced`
**Fix:** `from libgen_api_enhanced import LibgenSearch`
**Verified:** 2026-02-03 in 12-EXPERIMENT.md

### Pitfall 2: Mirror Down
**What goes wrong:** Connection timeout, empty results
**Cause:** Default mirror may be down
**Fix:** Make mirror configurable, implement fallback logic
```python
FALLBACK_MIRRORS = ['li', 'rs', 'bz']

async def search_with_fallback(query: str) -> list:
    for mirror in FALLBACK_MIRRORS:
        try:
            return await search_libgen(query, mirror=mirror)
        except Exception as e:
            logger.warning(f"Mirror {mirror} failed: {e}")
    raise LibgenUnavailable("All mirrors failed")
```

### Pitfall 3: Blocking Event Loop
**What goes wrong:** Application freezes during LibGen search
**Cause:** Library uses synchronous `requests`, blocks async event loop
**Fix:** Always wrap in `asyncio.to_thread()`

### Pitfall 4: No Rate Limiting
**What goes wrong:** IP temporarily blocked, requests fail
**Cause:** Too many requests too fast
**Fix:** Implement minimum delay between requests (2+ seconds)

### Pitfall 5: Download Link Resolution Fails
**What goes wrong:** `resolve_direct_download_link()` returns None
**Cause:** Library.lol (download resolver) may be down or slow
**Fix:** Use `tor_download_link` field directly if available
```python
book = results[0]
# Prefer tor link (always populated)
url = book.tor_download_link
# Or try resolution
if not url:
    url = book.resolve_direct_download_link()
```

---

## Open Questions

### 1. libgen-api-modern Viability
**What we know:** New library (Jul 2025) with async support
**What's unclear:** GitHub repo 404, actual reliability
**Recommendation:** Monitor but don't adopt. If libgen-api-enhanced stalls, investigate.

### 2. Long-term Library Maintenance
**What we know:** libgen-api-enhanced has 6 releases in 2024-2025, active maintainer
**What's unclear:** Will maintenance continue?
**Recommendation:** Prepare vendoring fallback plan (Option C above)

### 3. Tor Download Links
**What we know:** `tor_download_link` is populated, requires Tor access
**What's unclear:** Can we resolve these without Tor? Alternative resolution?
**Recommendation:** Test with Tor proxy in production, document setup

---

## Sources

### Primary (MEDIUM-HIGH confidence)
- [GitHub: onurhanak/libgen-api-enhanced](https://github.com/onurhanak/libgen-api-enhanced) — Releases, issues, code
- [PyPI: libgen-api-enhanced](https://pypi.org/project/libgen-api-enhanced/) — Version info
- [12-EXPERIMENT.md](./12-EXPERIMENT.md) — Local validation

### Secondary (MEDIUM confidence)
- [Snyk: libgen-api-enhanced](https://snyk.io/advisor/python/libgen-api-enhanced) — Maintenance status (via WebSearch)
- [The Library Genesis API](https://garbage.world/the-library-genesis-api.html) — API documentation
- [LibGen Help](https://libgen.help/) — Mirror status

### Tertiary (LOW confidence - need validation)
- [libgen-api-modern PyPI](https://pypi.org/project/libgen-api-modern/) — Alternative library info
- WebSearch results about mirror stability — Community reports

---

## Metadata

**Confidence breakdown:**
- Library recommendation: MEDIUM-HIGH — experimentally validated, issues reviewed
- Mirror ecosystem: MEDIUM — multiple sources agree
- Build vs buy: HIGH — clear cost/benefit analysis
- Pitfalls: HIGH — from experiment + GitHub issues

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days — monitor for library updates)

---

*Addendum to: 12-RESEARCH.md*
*Purpose: Deep dive into LibGen library ecosystem for Phase 12 planning*
