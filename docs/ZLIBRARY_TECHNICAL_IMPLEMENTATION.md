# Z-Library Technical Implementation Analysis

**Date**: 2025-01-30
**Analysis Method**: Codebase deep-dive and reverse engineering
**Files Analyzed**: `lib/python_bridge.py`, `zlibrary/src/zlibrary/libasync.py`, `zlibrary/src/zlibrary/abs.py`, `zlibrary/src/zlibrary/util.py`

## Executive Summary

The Z-Library MCP server uses a **hybrid Python/Node.js architecture** with a vendored fork of the `sertraline/zlibrary` library. It accesses Z-Library through **HTTP-based web scraping** (not a REST API) using standard HTML parsing techniques. This analysis documents the exact implementation details.

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│     MCP Client (Claude, etc.)           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Node.js MCP Server (src/index.ts)      │
│  - Tool registration                    │
│  - Request routing                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  TypeScript API (src/lib/zlibrary-api.ts)│
│  - Type conversions                     │
│  - PythonShell bridge                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Python Bridge (lib/python_bridge.py)   │
│  - AsyncZlib wrapper                    │
│  - Error handling                       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Vendored Z-Library (zlibrary/)         │
│  - HTTP requests via aiohttp            │
│  - HTML parsing via BeautifulSoup       │
│  - Session/cookie management            │
└──────────────┬──────────────────────────┘
               │
               ▼
       Z-Library Website
```

---

## Authentication Flow

### 1. Login Request

**Endpoint**: `POST {LOGIN_DOMAIN}/rpc.php`
**Default Domain**: `https://z-library.sk/rpc.php`

**Request Payload**:
```json
{
  "isModal": true,
  "email": "user@example.com",
  "password": "userpassword",
  "site_mode": "books",
  "action": "login",
  "isSingleLogin": 1,
  "redirectUrl": "",
  "gg_json_mode": 1
}
```

**Implementation** (from `zlibrary/src/zlibrary/libasync.py:122-172`):
```python
async def login(self, email: str, password: str):
    data = {...}  # Payload above

    # POST request to login endpoint
    resp, jar = await POST_request(
        self.login_domain, data, proxy_list=self.proxy_list
    )

    # Parse JSON response
    resp = json.loads(resp)
    resp = resp['response']

    # Check for validation errors
    if resp.get('validationError'):
        raise LoginFailed(json.dumps(resp, indent=4))

    # Extract cookies from jar
    self.cookies = {}
    for cookie in jar:
        self.cookies[cookie.key] = cookie.value

    # Key cookies received:
    # - remix_userkey
    # - remix_userid
```

### 2. Session Management

**Critical Cookies**:
- `remix_userkey`: User authentication token
- `remix_userid`: User ID for personalization
- Additional session cookies from jar

**Cookie Persistence**: Stored in `self.cookies` dict, sent with all subsequent requests

### 3. Domain Handling

**Default Domains**:
```python
ZLIB_DOMAIN = "https://z-library.sk/"
LOGIN_DOMAIN = "https://z-library.sk/rpc.php"

# Tor support (optional)
ZLIB_TOR_DOMAIN = "http://bookszlibb74ugqojhzhg2a63w5i2atv5bqarulgczawnbmsb6s6qead.onion"
LOGIN_TOR_DOMAIN = "http://loginzlib2vrak5zzpcocc3ouizykn6k5qecgj2tzlnab5wcbqhembyd.onion/rpc.php"
```

**Domain Override**:
```python
# Via environment variable
mirror = os.environ.get('ZLIBRARY_MIRROR')
if mirror:
    zlib_client.mirror = mirror  # Auto-adds https:// if missing
```

**Current Issue**: Default domains (z-library.sk) are parked/inactive. **Must use ZLIBRARY_MIRROR** with an active domain.

---

## Search Implementation

### Search URL Construction

**Base Pattern**: `{mirror}/s/{query}?{parameters}`

**Example URL**:
```
https://active-domain.com/s/python?yearFrom=2020&languages%5B%5D=english&extensions%5B%5D=PDF
```

**Implementation** (from `zlibrary/src/zlibrary/libasync.py:178-264`):
```python
async def search(
    self, q: str, exact: bool, from_year, to_year,
    lang: List, extensions: List, content_types: List,
    order, count: int
):
    payload = f"{self.mirror}/s/{quote(q)}?"

    # Add filters
    if exact:
        payload += "&e=1"
    if from_year:
        payload += f"&yearFrom={from_year}"
    if to_year:
        payload += f"&yearTo={to_year}"

    # Languages (URL encoded as languages[])
    for la in lang:
        payload += f"&languages%5B%5D={la.value}"

    # Extensions (URL encoded as extensions[])
    for ext in extensions:
        payload += f"&extensions%5B%5D={ext.value.upper()}"

    # Content types
    for ct in content_types:
        payload += f"&selected_content_types%5B%5D={quote(ct)}"

    # Order
    if order:
        payload += f"&order={order.value}"

    # Create paginator for results
    paginator = SearchPaginator(
        url=payload, count=count,
        request=self._r, mirror=self.mirror
    )
    await paginator.init()
    return paginator, payload
```

### Search Response Parsing

**HTTP Method**: GET request to search URL
**Response Format**: HTML page (not JSON!)

**HTML Structure** (from `zlibrary/src/zlibrary/abs.py:46-150`):
```html
<div id="searchFormResultsList">
  <div class="book-card-wrapper">
    <z-bookcard
      id="12345"
      isbn="978-0-123456-78-9"
      href="/book/12345/abc123"
      publisher="Publisher Name"
      authors="Author One; Author Two"
      name="Book Title"
      year="2024"
      language="english"
      extension="PDF"
      filesizeString="10.5 MB">

      <img data-src="https://covers.zlibcdn2.com/covers/abc123.jpg" />
    </z-bookcard>
  </div>
  <!-- More book-card-wrapper divs -->
</div>
```

**Parsing Logic**:
1. Find main container: `<div id="searchFormResultsList">`
2. Find all: `<div class="book-card-wrapper">`
3. Extract `<z-bookcard>` custom element
4. Read attributes directly from `<z-bookcard>`
5. Extract cover from `<img data-src="...">`

**Fallback Parsing**:
- If `searchFormResultsList` not found → try `<div class="itemFullText">`
- If `book-card-wrapper` not found → try `<div class="book-item">`
- Direct book page detection for ID searches

### Book Data Structure

```python
BookItem = {
    "id": "12345",
    "isbn": "978-0-123456-78-9",
    "url": "https://domain.com/book/12345/abc123",
    "cover": "https://covers.zlibcdn2.com/covers/abc123.jpg",
    "publisher": "Publisher Name",
    "authors": ["Author One", "Author Two"],
    "name": "Book Title",
    "year": 2024,
    "language": "english",
    "extension": "PDF",
    "filesizeString": "10.5 MB"
}
```

---

## HTTP Request Details

### Request Library

**Python HTTP Client**: `aiohttp` (async HTTP library)
**Fallback for some operations**: `httpx`

**Configuration** (from `zlibrary/src/zlibrary/util.py:12-20`):
```python
HEAD = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

TIMEOUT = aiohttp.ClientTimeout(
    total=180,      # 3 minutes total
    connect=0,      # No specific connect timeout
    sock_connect=120,  # 2 minutes for socket connection
    sock_read=180   # 3 minutes for reading
)
```

### Request Functions

```python
# GET request
async def GET_request(url, cookies=None, proxy_list=None) -> str:
    async with aiohttp.ClientSession(
        headers=HEAD,
        cookie_jar=aiohttp.CookieJar(unsafe=True),
        cookies=cookies,
        timeout=TIMEOUT,
        connector=ChainProxyConnector.from_urls(proxy_list) if proxy_list else None
    ) as sess:
        async with sess.get(url) as resp:
            return await resp.text()

# POST request
async def POST_request(url, data, proxy_list=None):
    async with aiohttp.ClientSession(...) as sess:
        async with sess.post(url, data=data) as resp:
            return (await resp.text(), sess.cookie_jar)
```

---

## Download Implementation

### Download URL Discovery

**Per ADR-002**: Downloads require `bookDetails` from search results, not direct ID lookup.

**Process**:
1. Search for book → get `BookItem` with `url` attribute
2. Fetch book detail page → scrape for download link
3. Download from extracted link

**Book Detail Page** (from code analysis):
- URL pattern: `{mirror}/book/{id}/{hash}`
- Contains download button/link
- Must be scraped with BeautifulSoup

### Download Link Extraction

Implementation in `python_bridge.py` uses direct HTTP fetch + BeautifulSoup parsing:
```python
async def fetch_book_detail_page(book_url):
    async with httpx.AsyncClient(cookies=self.cookies) as client:
        response = await client.get(book_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        download_link = soup.find("a", {"class": "download-button"})
        return download_link.get("href")
```

---

## Page Structure Analysis

### Search Results Page

**URL**: `{mirror}/s/{query}?filters`
**Method**: GET
**Response**: HTML

**Key Elements**:
```html
<div id="searchFormResultsList">
  <!-- Container for all results -->

  <div class="book-card-wrapper">
    <!-- Individual book wrapper -->

    <z-bookcard
      id="..."
      isbn="..."
      href="..."
      publisher="..."
      authors="..."
      name="..."
      year="..."
      language="..."
      extension="..."
      filesizeString="...">
      <!-- Custom element with all book data as attributes -->

      <img data-src="cover-url" />
      <!-- Lazy-loaded cover image -->
    </z-bookcard>
  </div>
</div>

<div class="notFound">
  <!-- Shown when no results -->
</div>
```

### Book Detail Page

**URL**: `{mirror}/book/{id}/{hash}`
**Method**: GET
**Response**: HTML

**Expected Elements** (inferred from download logic):
- Download button/link with actual file URL
- Book metadata (description, ISBN, etc.)
- Cover image
- Related books

---

## JavaScript Requirements

### Analysis from Code

**Current Implementation**: Pure HTTP + HTML parsing
- No JavaScript execution
- No browser automation
- No dynamic content handling

**Implications**:
✅ **Works if Z-Library serves**:
- Static HTML pages
- Server-side rendered content
- Traditional web forms

❌ **Fails if Z-Library requires**:
- JavaScript rendering
- Dynamic AJAX loading
- Client-side routing
- CAPTCHA challenges

### Evidence from Codebase

```python
# util.py uses aiohttp - standard HTTP client
# abs.py uses BeautifulSoup - static HTML parser
# No Selenium, Playwright, or browser automation
```

**Conclusion**: Current implementation assumes Z-Library uses **server-side rendering** with **static HTML**.

---

## API Endpoints Map

### Discovered Endpoints

| Endpoint | Method | Purpose | Response Format |
|----------|--------|---------|-----------------|
| `/rpc.php` | POST | Authentication | JSON |
| `/s/{query}` | GET | Search books | HTML |
| `/book/{id}/{hash}` | GET | Book details | HTML |
| `/eapi/book/search` | GET | API search (internal) | JSON |
| `/profile` | GET | User profile | HTML |
| `/booklists` | GET | User book lists | HTML |

### RPC Endpoint Details

**Full URL**: `https://{domain}/rpc.php`

**Known Actions**:
```json
{
  "action": "login",           // User authentication
  "action": "logout",          // Session termination
  "action": "profile",         // User data (?)
  "site_mode": "books",        // vs "articles"
  "isSingleLogin": 1,          // Hydra mode flag
  "gg_json_mode": 1            // Return JSON format
}
```

---

## Data Flow Example

### Search Flow

```
1. User request: "Search for Python books"
   ↓
2. MCP Server receives request
   ↓
3. TypeScript → PythonShell → python_bridge.py
   ↓
4. python_bridge.py:
   - Checks if zlib_client exists
   - Calls initialize_client() if needed
   ↓
5. initialize_client():
   - Reads ZLIBRARY_EMAIL, ZLIBRARY_PASSWORD
   - Creates AsyncZlib()
   - Calls zlib_client.login(email, password)
   ↓
6. zlib_client.login():
   - POST to https://z-library.sk/rpc.php
   - Receives JSON with validation status
   - Extracts cookies: remix_userkey, remix_userid
   - Sets self.mirror to active domain
   ↓
7. python_bridge.search():
   - Calls zlib_client.search(q="python", count=10)
   ↓
8. zlib_client.search():
   - Constructs URL: "{mirror}/s/python?"
   - Creates SearchPaginator
   - Calls paginator.init()
   ↓
9. SearchPaginator.init():
   - GET request to search URL with cookies
   - Receives HTML response
   - Calls parse_page(html)
   ↓
10. parse_page():
    - BeautifulSoup parses HTML
    - Finds <div id="searchFormResultsList">
    - Extracts all <z-bookcard> elements
    - Reads attributes: id, name, authors, etc.
    - Returns list of BookItems
    ↓
11. Results flow back through layers to MCP client
```

### Cookie Flow

```
Login → Server sets cookies → Stored in cookie jar
                              ↓
All requests → Include cookies → Server authenticates
```

---

## Scraping Techniques Used

### 1. Custom Element Parsing

Z-Library uses **custom HTML elements** (`<z-bookcard>`) with data as attributes:

```python
# Extract from custom element
book_card_el = item_wrapper.find("z-bookcard")
book_id = book_card_el.get("id")
title = book_card_el.get("name")
authors = book_card_el.get("authors")  # Semicolon-separated
```

**Advantage**: All data in attributes, no deep DOM traversal needed
**Risk**: If Z-Library changes element structure, scraping breaks

### 2. Lazy-Loaded Images

```python
# Cover images use data-src for lazy loading
img_tag = cover.find("img")
cover_url = img_tag.get("data-src")  # Not src!
```

**Implication**: Images load via JavaScript but URLs are in HTML

### 3. Pagination

```python
class SearchPaginator:
    page = 1
    storage = {1: []}  # Cache pages

    async def next(self):
        # Fetch next page
        # Parse results
        # Store in cache
```

**URL Pattern**: `{base_url}&page={page_number}`

---

## Domain Management

### Current Implementation

```python
class AsyncZlib:
    _mirror = ""  # Active domain
    domain = None  # Default domain
    login_domain = None  # Login endpoint

    @mirror.setter
    def mirror(self, value):
        if not value.startswith("http"):
            value = "https://" + value
        self._mirror = value
```

### Domain Resolution Priority

1. **Environment Variable**: `ZLIBRARY_MIRROR` (highest priority)
2. **Default Constants**: `ZLIB_DOMAIN` (likely inactive)
3. **Post-Login Discovery**: Sets `self.mirror` from successful login

### Critical Issue

**Default domain is INACTIVE**:
```python
ZLIB_DOMAIN = "https://z-library.sk/"  # Parked/blocked
```

**Solution Required**: Always set `ZLIBRARY_MIRROR` environment variable

---

## Error Handling

### Exception Types

From `zlibrary/src/zlibrary/exception.py`:
```python
BookNotFound          # 404 on book lookup
EmptyQueryError       # Search with empty query
ProxyNotMatchError    # Invalid proxy config
NoProfileError        # Not logged in
NoDomainError         # No mirror domain set
NoIdError            # Missing book ID
LoginFailed          # Authentication failed
ParseError           # HTML parsing failed
DownloadError        # Download failed
```

### Error Classification

**Network Errors** (retryable):
- Connection refused
- Timeouts
- DNS failures

**Authentication Errors** (not retryable):
- Invalid credentials
- Account blocked
- Session expired

**Parsing Errors** (not retryable):
- HTML structure changed
- Missing elements
- Invalid data format

---

## Performance Characteristics

### Concurrency Control

```python
__semaphore = asyncio.Semaphore(64)  # Max 64 concurrent requests

async def _r(self, url: str):
    if self.semaphore:
        async with self.__semaphore:
            response = await GET_request(...)
```

**Limits**: 64 concurrent requests to prevent overwhelming server

### Timeouts

```python
TIMEOUT = aiohttp.ClientTimeout(
    total=180,       # 3 minutes max
    sock_connect=120,  # 2 minutes to connect
    sock_read=180    # 3 minutes to read
)
```

**Implication**: Very generous timeouts, assumes slow/unreliable servers

---

## Scraping Vulnerabilities

### 1. DOM Structure Dependency

**Risk**: Code assumes specific HTML structure
```python
content_area = soup.find("div", {"id": "searchFormResultsList"})
```

**If Z-Library changes**:
- Changes div ID → scraping breaks
- Changes class names → scraping breaks
- Switches to JavaScript rendering → scraping breaks

### 2. No JavaScript Support

**Current**: Pure HTTP + BeautifulSoup
**Cannot handle**:
- React/Vue/Angular SPAs
- AJAX-loaded content
- Client-side routing
- Dynamic forms

### 3. CAPTCHA Vulnerability

**Current**: No CAPTCHA handling
**If implemented**: Complete scraping failure

### 4. Rate Limiting

**Current**: 64 concurrent request semaphore
**No implementation for**:
- Exponential backoff (now added)
- Request queuing
- Rate limit detection
- Automatic slowdown

---

## Technical Debt

### Identified Issues

1. **Hardcoded Domains**: `z-library.sk` is parked
2. **No Domain Discovery**: Manual ZLIBRARY_MIRROR required
3. **Fragile Parsing**: Depends on exact HTML structure
4. **No JS Fallback**: Cannot handle modern web apps
5. **Limited Error Recovery**: Basic retry only (now improved)

---

## Recommendations for Testing

### Test Checklist with Real Credentials

1. **Authentication Test**:
   ```bash
   export ZLIBRARY_EMAIL="logansrooks@gmail.com"
   export ZLIBRARY_PASSWORD="190297@Lsr"
   export ZLIBRARY_MIRROR="https://active-domain.com"  # Need to find

   # Test login
   python3 -c "
   import asyncio
   from zlibrary import AsyncZlib

   async def test():
       lib = AsyncZlib()
       await lib.login('$ZLIBRARY_EMAIL', '$ZLIBRARY_PASSWORD')
       print('Login successful!')
       print(f'Mirror: {lib.mirror}')
       print(f'Cookies: {lib.cookies.keys()}')

   asyncio.run(test())
   "
   ```

2. **Search Test**:
   ```python
   paginator = await lib.search(q="python programming", count=10)
   results = await paginator.next()
   print(f"Found {len(results)} books")
   for book in results:
       print(f"- {book['name']} by {book.get('authors', 'Unknown')}")
   ```

3. **HTML Structure Analysis**:
   ```python
   # Capture raw HTML from search
   response = await GET_request(f"{lib.mirror}/s/test")
   with open('search_page.html', 'w') as f:
       f.write(response)
   # Analyze structure manually
   ```

4. **Download Flow Test**:
   ```python
   # Get first book from search
   book = results[0]
   # Fetch detail page
   detail_html = await GET_request(book['url'])
   # Parse for download link
   soup = BeautifulSoup(detail_html, 'html.parser')
   # Document actual structure
   ```

---

## Next Steps for Exploration

### Priority Actions

1. **Find Active Domain**:
   - Email blackbox@zbox.ph with subject "get domains"
   - Check community forums
   - Try known mirrors: singlelogin.app, 1lib.sk

2. **Test Authentication**:
   - Use credentials to login
   - Document cookies received
   - Verify mirror domain in response

3. **Capture Real Responses**:
   - Save login JSON response
   - Save search HTML page
   - Save book detail HTML page
   - Document actual structure vs assumptions

4. **Identify Weak Points**:
   - Check for JavaScript requirements
   - Look for CAPTCHA implementation
   - Test rate limiting thresholds
   - Document anti-scraping measures

5. **Update Implementation**:
   - Fix hardcoded domains
   - Add domain discovery
   - Enhance error messages
   - Improve resilience

---

## Conclusion

The existing implementation is a **sophisticated HTTP scraper** that:
- ✅ Uses proper session management with cookies
- ✅ Supports proxy routing and Tor
- ✅ Has concurrent request limiting
- ✅ Parses custom HTML elements efficiently
- ❌ Lacks JavaScript execution capability
- ❌ Cannot handle CAPTCHAs
- ❌ Depends on hardcoded inactive domains
- ❌ No automatic domain discovery

**To properly explore Z-Library, we need**:
1. An active mirror domain
2. Test the login with real credentials
3. Capture and analyze real responses
4. Document actual vs assumed behavior

This will inform whether browser automation (Playwright) is truly needed or if the current HTTP scraping is sufficient.