# Phase 7: EAPI Migration - Research

**Researched:** 2026-02-01
**Domain:** Z-Library EAPI JSON endpoints (replacing HTML scraping)
**Confidence:** HIGH

## Summary

Z-Library exposes a full JSON API at `/eapi/` endpoints, originally built for the Android app. These endpoints bypass Cloudflare browser challenges because they use POST with form-encoded bodies (not HTML GET requests). The EAPI is well-documented by the community and has multiple working reference implementations. The migration replaces all BeautifulSoup HTML parsing in the vendored `zlibrary/` fork and the `lib/*_tools.py` modules with direct EAPI JSON calls.

The EAPI covers every operation the MCP server needs: search, book metadata, download, download history, download limits, most popular, recently added, and user profile. Authentication uses `remix_userid` and `remix_userkey` cookies/headers obtained from the existing login endpoint.

**Primary recommendation:** Build a new `EAPIClient` class in the vendored zlibrary fork that replaces all HTML-scraping methods with EAPI JSON calls, keeping the same public interface so `python_bridge.py` changes are minimal.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | existing | HTTP client for EAPI calls | Already in project, async support, connection pooling |
| aiohttp | existing | Used by vendored fork's `util.py` | Already handles login POST; can be used for EAPI too |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| requests | N/A | Sync HTTP (bipinkrish impl uses it) | NOT recommended; project is async |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Modifying vendored fork in-place | New standalone EAPI module | Standalone is cleaner but requires more python_bridge rewiring |
| aiohttp for EAPI calls | httpx for EAPI calls | httpx already has connection pooling in python_bridge; but aiohttp is used for auth. Either works. Use httpx for consistency with python_bridge.py |

**Installation:** No new dependencies needed. `httpx` and `aiohttp` already installed.

## Architecture Patterns

### Recommended Project Structure
```
zlibrary/src/zlibrary/
├── libasync.py          # Modified: EAPI methods replace HTML-scraping methods
├── eapi.py              # NEW: Low-level EAPI client (HTTP calls + JSON parsing)
├── abs.py               # Modified: SearchPaginator simplified or replaced
├── util.py              # Existing: Keep POST_request for login, add EAPI helpers
├── profile.py           # Modified: get_limits/download_history via EAPI
├── booklists.py         # Modified: booklist search via EAPI
└── ...

lib/
├── term_tools.py        # Modified: Use EAPI search with term queries
├── author_tools.py      # Modified: Use EAPI search with author queries
├── booklist_tools.py    # Modified: Use EAPI for booklist fetching
├── enhanced_metadata.py # Modified: Use EAPI /eapi/book/{id}/{hash} for metadata
└── python_bridge.py     # Minimal changes: normalize EAPI response format
```

### Pattern 1: EAPI Client Layer
**What:** A single class that encapsulates all EAPI HTTP calls, handling auth headers, request formatting, and JSON response parsing.
**When to use:** All Z-Library data access operations.
**Example:**
```python
# Source: baroxyton/zlibrary-eapi-documentation + bipinkrish/Zlibrary-API
class EAPIClient:
    BASE_HEADERS = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
        'Accept': 'text/html,application/xhtml+xml,...',
    }

    def __init__(self, domain: str, remix_userid: str, remix_userkey: str):
        self.domain = domain
        self.cookies = {
            'siteLanguageV2': 'en',
            'remix_userid': remix_userid,
            'remix_userkey': remix_userkey,
        }

    async def search(self, message: str, **filters) -> dict:
        """POST /eapi/book/search"""
        data = {'message': message}
        if filters.get('yearFrom'): data['yearFrom'] = filters['yearFrom']
        if filters.get('yearTo'): data['yearTo'] = filters['yearTo']
        if filters.get('languages'):
            for lang in filters['languages']:
                data.setdefault('languages[]', []).append(lang)
        if filters.get('extensions'):
            for ext in filters['extensions']:
                data.setdefault('extensions[]', []).append(ext)
        if filters.get('exact'): data['e'] = 1
        if filters.get('page'): data['page'] = filters['page']
        if filters.get('limit'): data['limit'] = filters['limit']
        if filters.get('order'): data['order'] = filters['order']

        return await self._post('/eapi/book/search', data)

    async def get_book_info(self, book_id: str, book_hash: str) -> dict:
        """GET /eapi/book/{id}/{hash}"""
        return await self._get(f'/eapi/book/{book_id}/{book_hash}')

    async def get_download_link(self, book_id: str, book_hash: str) -> dict:
        """GET /eapi/book/{id}/{hash}/file"""
        return await self._get(f'/eapi/book/{book_id}/{book_hash}/file')

    async def get_most_popular(self) -> dict:
        """GET /eapi/book/most-popular"""
        return await self._get('/eapi/book/most-popular')

    async def get_recently(self) -> dict:
        """GET /eapi/book/recently"""
        return await self._get('/eapi/book/recently')

    async def get_downloaded(self, order=None, page=None, limit=None) -> dict:
        """GET /eapi/user/book/downloaded"""
        params = {}
        if order: params['order'] = order
        if page: params['page'] = page
        if limit: params['limit'] = limit
        return await self._get('/eapi/user/book/downloaded', params=params)

    async def get_profile(self) -> dict:
        """GET /eapi/user/profile"""
        return await self._get('/eapi/user/profile')

    async def get_similar(self, book_id: str, book_hash: str) -> dict:
        """GET /eapi/book/{id}/{hash}/similar"""
        return await self._get(f'/eapi/book/{book_id}/{book_hash}/similar')

    async def get_domains(self) -> dict:
        """GET /eapi/info/domains"""
        return await self._get('/eapi/info/domains')

    async def _post(self, path: str, data: dict) -> dict:
        url = f'{self.domain}{path}'
        async with httpx.AsyncClient(cookies=self.cookies, headers=self.BASE_HEADERS) as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            return resp.json()

    async def _get(self, path: str, params: dict = None) -> dict:
        url = f'{self.domain}{path}'
        async with httpx.AsyncClient(cookies=self.cookies, headers=self.BASE_HEADERS) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
```

### Pattern 2: Response Normalization
**What:** EAPI returns different field names than the current HTML-parsed BookItem dicts. A normalization layer maps EAPI fields to the existing MCP tool response format.
**When to use:** Between EAPI response and python_bridge return values.
**Example:**
```python
def normalize_eapi_book(eapi_book: dict) -> dict:
    """Convert EAPI book object to existing MCP tool format."""
    return {
        'id': str(eapi_book.get('id', '')),
        'name': eapi_book.get('title', ''),
        'title': eapi_book.get('title', ''),
        'author': eapi_book.get('author', ''),
        'authors': [eapi_book.get('author', '')] if eapi_book.get('author') else [],
        'year': eapi_book.get('year', ''),
        'language': eapi_book.get('language', ''),
        'extension': eapi_book.get('extension', ''),
        'size': eapi_book.get('filesize', ''),
        'rating': eapi_book.get('rating', ''),
        'quality': eapi_book.get('qualityScore', ''),
        'cover': eapi_book.get('cover', ''),
        'url': eapi_book.get('href', ''),  # May need mirror prefix
        'isbn': eapi_book.get('isbn', ''),
        'publisher': eapi_book.get('publisher', ''),
        'hash': eapi_book.get('hash', ''),  # EAPI provides hash directly
        'book_hash': eapi_book.get('hash', ''),
        'pages': eapi_book.get('pages', ''),
    }
```

### Pattern 3: Login Flow Preserving remix_userid/remix_userkey
**What:** The existing login via `POST /rpc.php` works and returns cookies. Extract `remix_userid` and `remix_userkey` from those cookies, then use them for all EAPI calls.
**When to use:** Authentication initialization.
**Example:**
```python
# After existing login:
# self.cookies already contains remix_userid and remix_userkey
# These are the ONLY cookies needed for EAPI calls

# Alternative: use EAPI login directly
async def eapi_login(self, email: str, password: str) -> dict:
    """POST /eapi/user/login returns remix_userid and remix_userkey"""
    resp = await self._post('/eapi/user/login', {
        'email': email,
        'password': password
    })
    # resp contains: {'success': 1, 'user': {'id': ..., 'remix_userkey': ...}}
    return resp
```

### Anti-Patterns to Avoid
- **Keeping dual paths (HTML + EAPI):** Do not maintain both parsing approaches. Fully commit to EAPI. HTML parsing is the root cause of the Cloudflare issue.
- **Creating new httpx clients per request:** Use connection pooling. The existing `get_http_client()` pattern in python_bridge.py is correct.
- **Ignoring the hash field:** EAPI requires book hash for metadata and download. The current HTML scraper extracts hash from URLs. EAPI search results include hash directly --- use it.
- **Hardcoding domain:** The EAPI domain should come from the authenticated session, not a constant. Use `/eapi/info/domains` to discover current domains.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EAPI endpoint mapping | Custom URL builder | Follow baroxyton documentation exactly | Endpoints are well-documented, no guessing needed |
| Response format discovery | Trial-and-error | Reference bipinkrish/Zlibrary-API | Working implementation shows exact field names |
| Download link resolution | HTML scraping of book page | `/eapi/book/{id}/{hash}/file` | Returns direct download link in JSON |
| Book metadata extraction | HTML parsing with BeautifulSoup | `/eapi/book/{id}/{hash}` | Returns all metadata as JSON |
| Domain discovery | Manual mirror configuration | `/eapi/info/domains` | Returns current working domains |
| Pagination | Custom page counter | EAPI `page` and `limit` params | Built into search endpoint |

**Key insight:** The EAPI is a complete replacement for all HTML scraping operations. Every piece of data currently extracted via BeautifulSoup has an EAPI equivalent that returns structured JSON.

## Common Pitfalls

### Pitfall 1: Domain Mismatch
**What goes wrong:** EAPI calls fail because the domain used for HTML scraping doesn't work for EAPI endpoints (or vice versa).
**Why it happens:** Z-Library uses personalized domains and "Hydra mode". Not all domains expose EAPI endpoints.
**How to avoid:** After login, call `/eapi/info/domains` to get the correct domain for EAPI calls. Store and use this domain for all subsequent EAPI requests.
**Warning signs:** HTTP 403, redirect loops, or HTML challenge pages in EAPI responses.

### Pitfall 2: Missing book hash
**What goes wrong:** Cannot call EAPI metadata or download endpoints because hash is not available.
**Why it happens:** The current system stores book info without the hash field (it was embedded in HTML URLs). EAPI search results include `hash` directly.
**How to avoid:** Always store and propagate the `hash` field from EAPI search results. Map it to `book_hash` in normalized output.
**Warning signs:** "book_hash is required" errors in get_book_metadata_complete.

### Pitfall 3: Form-encoded arrays
**What goes wrong:** EAPI ignores filter parameters (languages, extensions).
**Why it happens:** Arrays must use bracket notation: `languages[]=english&languages[]=german`, not JSON arrays.
**How to avoid:** Use `httpx` data parameter with list values, or manually construct form-encoded body with `[]` suffix.
**Warning signs:** Search returns unfiltered results despite passing language/extension filters.

### Pitfall 4: Confusing search_books and full_text_search
**What goes wrong:** Full-text search stops working because there's no separate EAPI endpoint for it.
**Why it happens:** The HTML version uses `/fulltext/` URL path with a JS-extracted token. EAPI uses the same `/eapi/book/search` endpoint.
**How to avoid:** For full_text_search, the EAPI search endpoint may not have a direct equivalent. Test whether the `message` parameter in `/eapi/book/search` supports full-text queries. If not, this tool may need to be marked as degraded or use a workaround.
**Warning signs:** full_text_search returns same results as regular search.

### Pitfall 5: Download requires personal domain
**What goes wrong:** Download links from EAPI don't work or redirect.
**Why it happens:** The EAPI documentation notes "personal zlibrary domains are now required for downloading."
**How to avoid:** Use the personal domain from `/eapi/info/domains` for download operations. The `downloadLink` from `/eapi/book/{id}/{hash}/file` may already include the correct domain.
**Warning signs:** 403 errors or Cloudflare challenges on download attempts.

### Pitfall 6: Breaking existing test expectations
**What goes wrong:** Tests fail because response field names or structure changed.
**Why it happens:** Tests mock the old HTML-parsed response format.
**How to avoid:** The normalization layer (Pattern 2) must produce output identical to the current format. Update test mocks to reflect EAPI responses, but keep tool output format unchanged.
**Warning signs:** Failing assertions on field names like `name` vs `title`.

## Code Examples

### EAPI Search (verified from bipinkrish/Zlibrary-API)
```python
# Source: https://github.com/bipinkrish/Zlibrary-API
# POST /eapi/book/search
async def eapi_search(client, domain, cookies, message, limit=10, page=1):
    url = f"{domain}/eapi/book/search"
    data = {
        'message': message,
        'limit': limit,
        'page': page,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 ...',
    }
    resp = await client.post(url, data=data, cookies=cookies, headers=headers)
    result = resp.json()
    # result = {
    #   'success': 1,
    #   'books': [
    #     {
    #       'id': '12345',
    #       'title': 'Book Title',
    #       'author': 'Author Name',
    #       'year': '2020',
    #       'language': 'english',
    #       'extension': 'pdf',
    #       'filesize': '5242880',
    #       'pages': '300',
    #       'publisher': 'Publisher',
    #       'isbn': '978-...',
    #       'cover': 'https://...',
    #       'hash': 'abc123',
    #       'href': '/book/12345/abc123/title',
    #       ...
    #     }
    #   ],
    #   'pagination': {'totalPages': 5, 'currentPage': 1}
    # }
    return result
```

### EAPI Download (verified from bipinkrish/Zlibrary-API)
```python
# Source: https://github.com/bipinkrish/Zlibrary-API
# GET /eapi/book/{id}/{hash}/file
async def eapi_download(client, domain, cookies, book_id, book_hash, output_dir):
    url = f"{domain}/eapi/book/{book_id}/{book_hash}/file"
    resp = await client.get(url, cookies=cookies)
    result = resp.json()
    # result = {
    #   'success': 1,
    #   'file': {
    #     'description': 'Book Title',
    #     'author': 'Author Name',
    #     'extension': 'pdf',
    #     'downloadLink': '/dl/12345/abc123',
    #   }
    # }
    download_url = f"{domain}{result['file']['downloadLink']}"
    # Download the actual file from download_url
    # NOTE: bipinkrish uses special headers for the download request
    async with client.stream('GET', download_url, cookies=cookies) as resp:
        filename = f"{result['file']['description']} ({result['file']['author']}).{result['file']['extension']}"
        async with aiofiles.open(os.path.join(output_dir, filename), 'wb') as f:
            async for chunk in resp.aiter_bytes():
                await f.write(chunk)
    return filename
```

### EAPI Book Metadata
```python
# GET /eapi/book/{id}/{hash}
async def eapi_book_info(client, domain, cookies, book_id, book_hash):
    url = f"{domain}/eapi/book/{book_id}/{book_hash}"
    resp = await client.get(url, cookies=cookies)
    result = resp.json()
    # Returns full book metadata as JSON
    # Fields include: id, title, author, year, publisher, language,
    # pages, isbn, cover, filesize, extension, description, etc.
    return result
```

### EAPI Login (alternative to current /rpc.php)
```python
# POST /eapi/user/login
async def eapi_login(client, domain, email, password):
    url = f"{domain}/eapi/user/login"
    data = {'email': email, 'password': password}
    resp = await client.post(url, data=data)
    result = resp.json()
    # result = {
    #   'success': 1,
    #   'user': {
    #     'id': '12345',
    #     'remix_userkey': 'abcdef...',
    #     ...
    #   }
    # }
    remix_userid = str(result['user']['id'])
    remix_userkey = result['user']['remix_userkey']
    return remix_userid, remix_userkey
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTML scraping with BeautifulSoup | EAPI JSON endpoints | Always existed (Android app API) | Full JSON, no parsing fragility |
| GET requests for search results | POST to /eapi/book/search | Same endpoint, different usage | Bypasses Cloudflare JS challenge |
| Token extraction from JS for full-text search | May not have EAPI equivalent | Unknown | Potential degradation of full_text_search |
| HTML download page scraping for links | /eapi/book/{id}/{hash}/file | Same endpoint | Direct download link in JSON |

**Deprecated/outdated:**
- HTML scraping via `SearchPaginator.parse_page()`: Blocked by Cloudflare. Must be replaced.
- `z-bookcard` custom element parsing: Cloudflare prevents HTML delivery. Must be replaced.
- Token extraction for full-text search: JS challenge blocks the page needed for token extraction.

## MCP Tool to EAPI Endpoint Mapping

| MCP Tool | Current Implementation | EAPI Replacement | Notes |
|----------|----------------------|------------------|-------|
| `search_books` | `AsyncZlib.search()` → HTML GET → BeautifulSoup | `POST /eapi/book/search` | Direct replacement |
| `full_text_search` | `AsyncZlib.full_text_search()` → HTML GET + JS token | `POST /eapi/book/search` (?) | May not have exact equivalent; test with same endpoint |
| `search_by_author` | `lib/author_tools.py` → HTML GET → `z-bookcard` parse | `POST /eapi/book/search` with author in message | Author search is likely just a search query variant |
| `search_by_term` | `lib/term_tools.py` → HTML GET → `z-bookcard` parse | `POST /eapi/book/search` with term in message | Term search is likely just a search query variant |
| `search_advanced` | `python_bridge.search_advanced()` → dual search | `POST /eapi/book/search` with exact flag | Exact vs fuzzy separation done client-side |
| `get_recent_books` | `AsyncZlib.search()` with order=newest | `GET /eapi/book/recently` | Direct endpoint exists |
| `fetch_booklist` | `lib/booklist_tools.py` → HTML parse | No direct EAPI equivalent visible | May need HTML fallback or different approach |
| `get_book_metadata` | `python_bridge.get_book_metadata_complete()` → HTML | `GET /eapi/book/{id}/{hash}` | Direct replacement, returns JSON |
| `download_book_to_file` | `AsyncZlib.download_book()` → HTML page scrape → link | `GET /eapi/book/{id}/{hash}/file` → download link | Two-step: get link, then download |
| `get_download_history` | `profile.download_history()` → HTML parse | `GET /eapi/user/book/downloaded` | Direct replacement |
| `get_download_limits` | `profile.get_limits()` → HTML parse | `GET /eapi/user/profile` (extract limits) | Profile includes download limits |
| `process_document_for_rag` | Local file processing | No change needed | Not an API operation |

## Files Requiring Modification

### Must Change (HTML scraping in hot path)
1. **`zlibrary/src/zlibrary/libasync.py`** - `AsyncZlib.search()`, `full_text_search()`, `download_book()` - all use HTML GET + BeautifulSoup
2. **`zlibrary/src/zlibrary/abs.py`** - `SearchPaginator.parse_page()`, `BooklistPaginator.parse_page()`, `DownloadsPaginator.parse_page()`, `BookItem._parse_book_page_soup()` - all BeautifulSoup HTML parsers
3. **`zlibrary/src/zlibrary/profile.py`** - `get_limits()`, `download_history()` - HTML GET + BeautifulSoup
4. **`zlibrary/src/zlibrary/booklists.py`** - `search_public()`, `search_private()` - HTML GET + BooklistPaginator
5. **`zlibrary/src/zlibrary/util.py`** - `GET_request()` returns HTML string; needs JSON variant or replacement
6. **`lib/term_tools.py`** - HTML GET + `z-bookcard` parsing
7. **`lib/author_tools.py`** - HTML GET + `z-bookcard` parsing
8. **`lib/booklist_tools.py`** - HTML GET + `z-bookcard` parsing
9. **`lib/enhanced_metadata.py`** - HTML parsing with BeautifulSoup (20+ usages)
10. **`lib/python_bridge.py`** - `get_book_metadata_complete()` uses HTML fetch; `normalize_book_details()` needs update for EAPI hash field

### No Change Needed
1. **`lib/rag_processing.py`** (and `lib/rag_processing/` package) - Local file processing, no HTTP
2. **`lib/python_bridge.py`** `process_document()` - Local file processing
3. **`src/index.ts`** - MCP tool definitions unchanged (input/output format preserved)
4. **`src/lib/zlibrary-api.ts`** - PythonShell bridge unchanged (calls same python_bridge functions)

## Open Questions

1. **Full-text search EAPI equivalent?**
   - What we know: HTML full-text search uses `/fulltext/` path with a JS-extracted token. EAPI `/eapi/book/search` exists.
   - What's unclear: Whether `/eapi/book/search` supports full-text search mode (searching within book content vs titles/authors).
   - Recommendation: Test `/eapi/book/search` with various parameters. If it doesn't support full-text, either (a) mark the tool as degraded, or (b) explore if there's an undocumented EAPI endpoint. LOW confidence.

2. **Booklist EAPI endpoint?**
   - What we know: EAPI has `/eapi/user/book/saved` and recommendation endpoints, but no documented public booklist browsing endpoint.
   - What's unclear: Whether `/booklists` browsing has an EAPI equivalent.
   - Recommendation: Test if booklist pages are also Cloudflare-blocked. If yes, the `fetch_booklist` tool may need to be degraded or an alternative approach found. MEDIUM confidence.

3. **EAPI response field names exact mapping?**
   - What we know: bipinkrish implementation shows `title`, `author`, `hash`, `href` fields.
   - What's unclear: Complete field list and exact names for all fields across all endpoints (cover URL format, filesize units, etc.).
   - Recommendation: Empirical testing with live API after implementing login. Compare EAPI response to current normalized book dict. HIGH confidence this can be resolved during implementation.

4. **Rate limiting on EAPI?**
   - What we know: EAPI is the Android app API, probably has rate limiting.
   - What's unclear: Exact rate limits, how they differ from web scraping limits.
   - Recommendation: Use the existing retry + circuit breaker infrastructure. Observe rate limit responses during testing.

5. **EAPI health check / Cloudflare detection?**
   - What we know: Success criterion #4 requires automated health check.
   - What's unclear: Best approach to detect future EAPI breakage.
   - Recommendation: Implement a lightweight smoke test that calls `/eapi/book/search` with a known query and validates `success: 1` in response.

## Sources

### Primary (HIGH confidence)
- [baroxyton/zlibrary-eapi-documentation](https://github.com/baroxyton/zlibrary-eapi-documentation) - Complete EAPI endpoint documentation
- [bipinkrish/Zlibrary-API](https://github.com/bipinkrish/Zlibrary-API) - Working Python EAPI implementation (reference)
- Codebase analysis of `zlibrary/src/zlibrary/` - Current HTML scraping implementation

### Secondary (MEDIUM confidence)
- [SearXNG zlibrary engine](https://docs.searxng.org/dev/engines/online/zlibrary.html) - Confirms Z-Library search structure (HTML-based, not EAPI)
- [sertraline/zlibrary](https://github.com/sertraline/zlibrary) - Upstream vendored fork (HTML scraping only)

### Tertiary (LOW confidence)
- EAPI field names from bipinkrish code analysis - Need live testing to confirm exact response format

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries needed, EAPI is well-documented
- Architecture: HIGH - Clean replacement pattern, reference implementation exists
- Pitfalls: MEDIUM - Booklist and full-text search EAPI coverage uncertain
- EAPI endpoint mapping: HIGH for search/download/metadata, MEDIUM for booklists/full-text

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (EAPI is stable Android app API, unlikely to change rapidly)
