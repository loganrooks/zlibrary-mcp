# Phase 12: Anna's Archive Integration - Research

**Researched:** 2026-02-02
**Updated:** 2026-02-03 (experimental validation + LibGen ecosystem deep dive)
**Domain:** Multi-source book search/download, API integration, fallback orchestration
**Confidence:** HIGH (validated through hands-on experiments)

## Summary

**UPDATED AFTER EXPERIMENTS:** User has a working Anna's Archive API key (25 fast downloads/day). The fast download API works. Search requires HTML scraping. Slow downloads are blocked by DDoS-Guard and should not be implemented.

The recommended approach is:
1. **Primary: Anna's Archive** — scrape search, use fast download API with `domain_index=1`
2. **Fallback: LibGen** — use `libgen-api-enhanced` library when Anna's quota exhausted

**Key experimental findings (see 12-EXPERIMENT.md for details):**
- Fast download API works with `domain_index=1` (returns working HTTP URLs)
- Default `domain_index=0` returns HTTPS URLs with SSL errors — avoid
- API tracks quota: `downloads_left`, `downloads_done_today`
- Search scraping works despite Cloudflare warnings
- Slow downloads require browser JS — not automatable without Playwright
- LibGen library works but import is `libgen_api_enhanced` not `libgen_api`

**LibGen ecosystem findings (see LibGen Library Landscape section):**
- `libgen-api-enhanced` v1.2.4 is the best choice (actively maintained, 53 stars, zero open issues)
- No official LibGen search API — all libraries use HTML scraping
- Build vs Buy verdict: **USE LIBRARY** — maintenance burden of custom scraper outweighs benefits
- Mirror stability is the main risk, not HTML structure changes

**Primary recommendation:** Implement Anna's Archive as primary source with LibGen fallback. Skip slow downloads entirely. Use `libgen-api-enhanced` — do not build custom scraper.

## Go/No-Go Analysis (Updated)

### Anna's Archive Fast Download API
| Criterion | Assessment | Status |
|-----------|-----------|--------|
| Free access | User donated and has API key | PASS |
| Search capability | HTML scraping works | PASS |
| Download capability | API works with domain_index=1 | PASS |
| API stability | Single documented endpoint | PASS |
| Rate limits | 25/day, tracked in response | KNOWN |

**Verdict: GO** — primary source

### Anna's Archive Slow Downloads
| Criterion | Assessment | Status |
|-----------|-----------|--------|
| Automatable | Blocked by DDoS-Guard | FAIL |
| Requires | Browser JS execution | FAIL |

**Verdict: NO-GO** — do not implement

### Library Genesis (via libgen-api-enhanced)
| Criterion | Assessment | Status |
|-----------|-----------|--------|
| Free access | Yes — fully free, no API key | PASS |
| Search capability | Library handles scraping | PASS |
| Download capability | Tor links + mirror resolution | PASS |
| Stability | Library maintained, configurable mirrors | PASS |
| Maintenance | Active (Oct 2025 release, 5-10 day issue resolution) | PASS |

**Verdict: GO** — fallback source

---

## LibGen Library Landscape

### Evaluated Libraries

| Library | Version | Last Update | Stars | Maintenance | Async | Recommendation |
|---------|---------|-------------|-------|-------------|-------|----------------|
| [libgen-api-enhanced](https://github.com/onurhanak/libgen-api-enhanced) | 1.2.4 | Oct 2025 | 53 | Active | No | **USE THIS** |
| [libgen-api-modern](https://pypi.org/project/libgen-api-modern/) | 1.0.0 | Jul 2025 | ? | New | Yes | Monitor only |
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

### libgen-api-modern (Alternative — Monitor Only)

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

### LibGen API Reality

LibGen provides a JSON API at `json.php` but it does **NOT** support search:

```bash
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

### Build vs Buy Decision

#### Option A: Use libgen-api-enhanced (RECOMMENDED)

**Pros:**
- Battle-tested (53 stars, used by others)
- Maintained by someone else (issue response 5-10 days)
- Mirror issues already handled
- ~200 lines of code we don't maintain

**Cons:**
- Dependency on external maintainer
- Synchronous (requires thread wrapping)
- No control over release timing

#### Option B: Build Custom Scraper (NOT RECOMMENDED)

**Pros:**
- Full control over implementation
- Can optimize for our specific needs
- No external dependency

**Cons:**
- **Significant maintenance burden** — estimated 2-4 hours per mirror/HTML change
- Need to monitor LibGen changes ourselves
- Duplicating work already done by the community
- Time better spent on core features

#### Option C: Vendor/Fork libgen-api-enhanced (FALLBACK PLAN)

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
3. Implement mirror fallback on connection failure

### Webscraping Stability Analysis

**Historical breakage in libgen-api-enhanced (from GitHub issues):**
- **Issue #9 (Oct 2025):** "Frequently unable to search for any books?" — resolved
- **Issue #2 (Jul-Aug 2025):** "the domain is Down" — domain change required
- **Issue #1 (Feb-Mar 2025):** "libgen.is not work" — mirror update needed

**Pattern:** Issues are primarily about mirror availability, not HTML structure changes.

**LibGen-specific assessment:**
- LibGen's HTML structure is relatively stable (simple table layout)
- The main breakage source is domain/mirror changes, not HTML redesigns
- Libraries handle this through configurable mirror support
- Release v1.1.3 specifically included "fix default mirror"

**Confidence:** MEDIUM — LibGen HTML has been stable historically, but no guarantees.

---

## Standard Stack

### Core
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| httpx | (existing) | HTTP requests for Anna's Archive | Use for search scraping and API calls |
| beautifulsoup4 | (existing) | HTML parsing | For Anna's Archive search results |
| libgen-api-enhanced | 1.2.4 | LibGen search + download | Import as `libgen_api_enhanced`, NOT `libgen_api` |

### Installation
```bash
# Add to pyproject.toml or requirements.txt
pip install libgen-api-enhanced==1.2.4
# or
uv add libgen-api-enhanced
```

### Environment Variables
```bash
# Required for Anna's Archive fast downloads
ANNAS_SECRET_KEY=your_secret_key_here

# Optional: Anna's Archive mirror (if main domain down)
ANNAS_BASE_URL=https://annas-archive.li

# Optional: LibGen mirror (default: li)
LIBGEN_MIRROR=li

# Source routing
BOOK_SOURCE_DEFAULT=auto          # 'auto' | 'annas' | 'libgen'
BOOK_SOURCE_FALLBACK_ENABLED=true
```

---

## Architecture Patterns

### Pattern 1: Anna's Archive Adapter
```python
class AnnasArchiveAdapter(SourceAdapter):
    """Anna's Archive with fast download API."""

    def __init__(self, secret_key: str, base_url: str = "https://annas-archive.li"):
        self.secret_key = secret_key
        self.base_url = base_url

    async def search(self, query: str, **kwargs) -> List[UnifiedBookResult]:
        """Scrape search results from HTML."""
        url = f"{self.base_url}/search?q={quote(query)}"
        response = await self.client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        results = []
        for link in soup.select("a[href^='/md5/']"):
            md5 = link.get('href', '').split('/')[-1]
            if md5 and md5 not in seen:
                results.append(UnifiedBookResult(
                    md5=md5,
                    title=link.get_text(strip=True),
                    source='annas_archive',
                    # ... extract other fields
                ))
        return results

    async def get_download_url(self, md5: str) -> DownloadResult:
        """Get fast download URL via API."""
        url = f"{self.base_url}/dyn/api/fast_download.json"
        params = {
            "md5": md5,
            "key": self.secret_key,
            "domain_index": 1,  # IMPORTANT: Use 1 for working HTTP URLs
        }
        response = await self.client.get(url, params=params)
        data = response.json()

        if data.get("download_url"):
            return DownloadResult(
                url=data["download_url"],
                quota_info=data.get("account_fast_download_info"),
            )
        raise DownloadError(data.get("error", "Unknown error"))
```

### Pattern 2: LibGen Adapter with Rate Limiting
```python
import time
import asyncio
from libgen_api_enhanced import LibgenSearch

class LibgenAdapter(SourceAdapter):
    """LibGen via libgen-api-enhanced library with rate limiting."""

    MIN_REQUEST_INTERVAL = 2.0  # seconds between requests

    def __init__(self, mirror: str = 'li'):
        self.mirror = mirror
        self._last_request = 0

    async def search(self, query: str, **kwargs) -> List[UnifiedBookResult]:
        """Search via library (runs sync code in thread)."""
        # Respect rate limit
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

        self._last_request = time.time()

        def _search():
            s = LibgenSearch(mirror=self.mirror)
            return s.search_title(query)

        results = await asyncio.to_thread(_search)

        return [
            UnifiedBookResult(
                md5=book.md5,
                title=book.title,
                author=book.author,
                year=book.year,
                extension=book.extension,
                size=book.size,
                source='libgen',
                download_url=book.tor_download_link,
            )
            for book in results
        ]
```

### Pattern 3: Source Router with Fallback
```python
async def search_with_fallback(query: str, source: str = 'auto') -> SearchResult:
    """Search with automatic fallback."""
    config = get_source_config()

    if source == 'auto':
        source = 'annas' if config.annas_key else 'libgen'

    try:
        if source == 'annas':
            return await annas_adapter.search(query)
    except (QuotaExceeded, SourceUnavailable) as e:
        if config.fallback_enabled:
            logger.warning(f"Anna's Archive failed: {e}, falling back to LibGen")
            return await libgen_adapter.search(query)
        raise

    return await libgen_adapter.search(query)
```

### Pattern 4: LibGen Mirror Fallback
```python
FALLBACK_MIRRORS = ['li', 'rs', 'bz']

async def search_libgen_with_mirror_fallback(query: str) -> list:
    """Try multiple mirrors on failure."""
    for mirror in FALLBACK_MIRRORS:
        try:
            adapter = LibgenAdapter(mirror=mirror)
            return await adapter.search(query)
        except Exception as e:
            logger.warning(f"LibGen mirror {mirror} failed: {e}")
    raise LibgenUnavailable("All LibGen mirrors failed")
```

---

## Common Pitfalls

### Anna's Archive Pitfalls

#### Pitfall 1: Wrong domain_index for Anna's Archive
**What goes wrong:** Download URLs fail with SSL errors
**Why it happens:** `domain_index=0` returns HTTPS URLs to servers with misconfigured SSL
**How to avoid:** Always use `domain_index=1` which returns working HTTP URLs
**Verified:** 2026-02-03 experiment confirmed

#### Pitfall 2: Attempting slow downloads
**What goes wrong:** 403 errors, DDoS-Guard blocking
**Why it happens:** Slow download path requires browser JavaScript
**How to avoid:** Don't implement slow downloads. Use fast API + LibGen fallback.
**Verified:** 2026-02-03 experiment confirmed

#### Pitfall 3: Not tracking API quota
**What goes wrong:** Unexpected quota exhaustion, failed downloads
**Why it happens:** Not monitoring `downloads_left` in API response
**How to avoid:** Parse `account_fast_download_info` from every API response, trigger fallback when quota low
**API returns:** `downloads_left`, `downloads_per_day`, `downloads_done_today`, `recently_downloaded_md5s`

### LibGen Pitfalls

#### Pitfall 4: Wrong import for libgen-api-enhanced
**What goes wrong:** `ModuleNotFoundError: No module named 'libgen_api'`
**Why it happens:** Package name `libgen-api-enhanced` differs from import name `libgen_api_enhanced`
**How to avoid:** Use `from libgen_api_enhanced import LibgenSearch`
**Verified:** 2026-02-03 experiment confirmed

#### Pitfall 5: LibGen sync blocking event loop
**What goes wrong:** Application freezes during LibGen search
**Why it happens:** `libgen-api-enhanced` uses synchronous `requests` library
**How to avoid:** Always wrap LibGen calls in `asyncio.to_thread()`

#### Pitfall 6: LibGen mirror down
**What goes wrong:** Connection timeout, empty results
**Why it happens:** Default mirror may be unavailable
**How to avoid:** Make mirror configurable via `LIBGEN_MIRROR` env var, implement fallback logic
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

#### Pitfall 7: No rate limiting for LibGen
**What goes wrong:** IP temporarily blocked, requests fail
**Why it happens:** Too many requests too fast
**How to avoid:** Implement minimum delay between requests (2+ seconds)

#### Pitfall 8: Download link resolution fails
**What goes wrong:** `resolve_direct_download_link()` returns None
**Why it happens:** Library.lol (download resolver) may be down or slow
**How to avoid:** Use `tor_download_link` field directly if available
```python
book = results[0]
# Prefer tor link (always populated)
url = book.tor_download_link
# Or try resolution as backup
if not url:
    url = book.resolve_direct_download_link()
```

---

## Code Examples (Validated)

### Anna's Archive Search Scraping
```python
# Validated 2026-02-03
import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://annas-archive.li"

async def search_annas(query: str) -> list[dict]:
    url = f"{BASE_URL}/search?q={query}"
    response = await httpx.AsyncClient().get(url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []
    seen = set()
    for link in soup.select("a[href^='/md5/']"):
        md5 = link.get('href', '').split('/')[-1]
        if md5 and md5 not in seen:
            seen.add(md5)
            results.append({
                'md5': md5,
                'title': link.get_text(strip=True),
                'url': f"{BASE_URL}/md5/{md5}",
            })
    return results
```

### Anna's Archive Fast Download API
```python
# Validated 2026-02-03
import httpx
import os

async def get_fast_download(md5: str) -> dict:
    key = os.environ["ANNAS_SECRET_KEY"]
    url = "https://annas-archive.li/dyn/api/fast_download.json"
    params = {
        "md5": md5,
        "key": key,
        "domain_index": 1,  # CRITICAL: Use 1 for working HTTP URLs
    }

    response = await httpx.AsyncClient().get(url, params=params, timeout=30)
    data = response.json()

    if data.get("download_url"):
        return {
            "url": data["download_url"],
            "downloads_left": data["account_fast_download_info"]["downloads_left"],
        }
    raise Exception(data.get("error", "Download failed"))
```

### LibGen Search with Mirror Support
```python
# Validated 2026-02-03
import os
import asyncio
from libgen_api_enhanced import LibgenSearch

async def search_libgen(query: str, mirror: str = None) -> list[dict]:
    """Search LibGen with configurable mirror."""
    mirror = mirror or os.environ.get('LIBGEN_MIRROR', 'li')

    def _search():
        s = LibgenSearch(mirror=mirror)
        return s.search_title(query)

    results = await asyncio.to_thread(_search)

    return [
        {
            'md5': book.md5,
            'title': book.title,
            'author': book.author,
            'year': book.year,
            'extension': book.extension,
            'size': book.size,
            'download_url': book.tor_download_link,
            'source': 'libgen',
        }
        for book in results
    ]
```

### LibGen with Rate Limiting
```python
# Validated pattern
import time
import asyncio

class RateLimitedLibgenAdapter:
    MIN_REQUEST_INTERVAL = 2.0  # seconds

    def __init__(self):
        self._last_request = 0

    async def search(self, query: str, mirror: str = 'li') -> list:
        # Respect rate limit
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

        self._last_request = time.time()
        return await search_libgen(query, mirror=mirror)
```

---

## Open Questions

### Resolved
1. ~~Anna's Archive API requires donation~~ — User has key, API works
2. ~~Slow downloads feasibility~~ — Blocked by DDoS-Guard, not implementing
3. ~~libgen-api-enhanced import path~~ — Use `libgen_api_enhanced`
4. ~~Download URL SSL issues~~ — Use `domain_index=1` for HTTP URLs
5. ~~Which LibGen library to use~~ — `libgen-api-enhanced` v1.2.4
6. ~~Build vs buy for LibGen~~ — Use library, don't build custom

### Remaining
1. **libgen-api-modern viability** — New library with async support, but GitHub 404. Monitor.
2. **Long-term library maintenance** — Prepare vendoring fallback if `libgen-api-enhanced` abandoned
3. **Tor download links** — May need Tor proxy setup for production; test resolution alternatives

---

## Sources

### Primary (HIGH confidence - experimentally validated)
- Anna's Archive fast download API — tested 2026-02-03, works with domain_index=1
- Anna's Archive search scraping — tested 2026-02-03, works
- libgen-api-enhanced v1.2.4 — tested 2026-02-03, works
- [GitHub: onurhanak/libgen-api-enhanced](https://github.com/onurhanak/libgen-api-enhanced) — Releases, issues, code
- [PyPI: libgen-api-enhanced](https://pypi.org/project/libgen-api-enhanced/) — Version info

### Secondary (MEDIUM confidence)
- [Snyk: libgen-api-enhanced](https://snyk.io/advisor/python/libgen-api-enhanced) — Maintenance status
- [The Library Genesis API](https://garbage.world/the-library-genesis-api.html) — API documentation
- [LibGen Help](https://libgen.help/) — Mirror status

### Tertiary (LOW confidence - need validation)
- [libgen-api-modern PyPI](https://pypi.org/project/libgen-api-modern/) — Alternative library info
- WebSearch results about mirror stability — Community reports

### Experimental Validation
- See `12-EXPERIMENT.md` for full experiment logs and scripts
- Test scripts in `scripts/experiments/`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — experimentally validated
- Architecture: HIGH — based on working code patterns from experiments
- LibGen library choice: MEDIUM-HIGH — experimentally validated + GitHub issues reviewed
- Mirror ecosystem: MEDIUM — multiple sources agree, no authoritative single source
- Build vs buy: HIGH — clear cost/benefit analysis, community precedent
- Pitfalls: HIGH — discovered through actual testing + issue history
- Code examples: HIGH — all validated to work

**Research date:** 2026-02-02
**Experimental validation:** 2026-02-03
**LibGen ecosystem research:** 2026-02-03
**Valid until:** 2026-03-03 (30 days)

---

*Phase: 12-annas-archive*
*Research completed: 2026-02-02*
*Experimentally validated: 2026-02-03*
*LibGen ecosystem deep dive: 2026-02-03*
*Ready for planning: YES*
