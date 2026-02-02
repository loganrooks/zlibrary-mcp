# Technology Stack: v1.1 Quality & Expansion

**Project:** zlibrary-mcp
**Researched:** 2026-02-01
**Scope:** Stack additions for margin detection, adaptive resolution, Anna's Archive, Node 22, AsyncZlib removal
**Overall confidence:** MEDIUM-HIGH

---

## 1. Margin Content Detection in PDFs

### No New Libraries Needed

PyMuPDF (already at >=1.26.0) provides everything required:

| Capability | PyMuPDF API | Purpose |
|------------|-------------|---------|
| Block coordinates | `page.get_text("dict")` | Returns bbox `(x0,y0,x1,y1)` per span with font info |
| Word positions | `page.get_text("words")` | Tuples of `(x0,y0,x1,y1,word,block_no,line_no,word_no)` |
| Region clipping | `page.get_text("blocks", clip=rect)` | Extract only from margin regions |
| Page dimensions | `page.rect` | `Rect(0,0,width,height)` for computing margin zones |
| Font metadata | dict mode spans | `font`, `size`, `flags` per span for classifying margin vs body text |

**Integration point:** New module `lib/rag/detection/margins.py` alongside existing `footnotes.py`, `page_numbers.py`. Uses same `fitz.Page` object already passed to `_format_pdf_markdown()` in `lib/rag/processors/pdf.py`.

**Approach:** Compute body text bounding box (median x0/x1 across blocks), then classify blocks outside that zone as margin content. Use font size differential (margin text is typically smaller) and positional patterns (Stephanus numbers appear at consistent x-offsets near left/right edges).

**Confidence:** HIGH -- PyMuPDF docs confirm all needed APIs exist.

### What NOT to Add

| Library | Why Not |
|---------|---------|
| pdfplumber | Redundant with PyMuPDF; adds dependency for same coordinate extraction |
| pdfminer.six | Slower, more complex API; PyMuPDF already handles layout |
| Tesseract/OCR | Only needed if margins are image-based; defer until proven necessary |

---

## 2. Adaptive Resolution Pipeline

### No New Libraries Needed

PyMuPDF handles variable-DPI rendering natively:

| Capability | PyMuPDF API | Purpose |
|------------|-------------|---------|
| Variable DPI render | `page.get_pixmap(matrix=fitz.Matrix(scale, scale))` | Scale factor maps to DPI (1.0=72dpi, 2.0=144dpi, 4.0=288dpi) |
| Text size analysis | `get_text("dict")` spans | Font size per span to determine if higher DPI needed |
| Image extraction | `page.get_images()` | Detect image-heavy pages needing different treatment |

**Integration point:** Add DPI selection logic to `lib/rag/ocr/` modules. Existing OCR recovery already processes pages; adaptive resolution adds a pre-pass to select appropriate scale factor based on minimum font size detected on each page.

**Algorithm sketch:**
- Default: 150 DPI (scale=2.08) for body text
- Small text (<8pt): 300 DPI (scale=4.17)
- Margin annotations (<6pt): 400 DPI (scale=5.56)
- Image-only pages: 200 DPI (scale=2.78)

**Confidence:** HIGH -- standard PyMuPDF pixmap usage.

---

## 3. Anna's Archive Integration

### API Surface

Anna's Archive has **no official public API documentation**. Access is donation-gated.

| Aspect | Details | Confidence |
|--------|---------|------------|
| Auth | API key via donation at annas-archive.org/donate | MEDIUM |
| Base URL | `annas-archive.li` (configurable, mirrors change) | MEDIUM |
| Search | Query params, returns JSON with book metadata including MD5 | MEDIUM |
| Download | MD5-based download links; "fast download" for donors, fallback to mirrors | MEDIUM |
| Rate limits | Unknown officially; RapidAPI wrapper offers 3K reqs/month on free tier | LOW |
| API key env | `ANNAS_SECRET_KEY` (convention from existing MCP servers) | MEDIUM |

### Recommended Stack Addition

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | (already vendored) | HTTP client for AA API | Already used in zlibrary fork; no new dep |

**No new Python libraries needed.** The Anna's Archive API is a simple REST-like interface. Use httpx (already a dependency) to call it.

### Integration Architecture

Create `lib/sources/annas_archive.py` as a new book source alongside the existing Z-Library EAPI client. Both implement a common interface:

```python
class BookSource(Protocol):
    async def search(self, query: str, **kwargs) -> list[dict]
    async def get_download_link(self, book_id: str) -> str
    async def download(self, book_id: str, output_dir: Path) -> Path
```

**Node.js side:** Add `ANNAS_ARCHIVE_API_KEY` and `ANNAS_ARCHIVE_BASE_URL` env vars. Route through existing Python bridge -- no new Node dependencies.

### Key Reference

[iosifache/annas-mcp](https://github.com/iosifache/annas-mcp) is an existing Anna's Archive MCP server using `ANNAS_SECRET_KEY` for auth. Study its API patterns before implementation. Also available: [RapidAPI wrapper](https://rapidapi.com/tribestick-tribestick-default/api/annas-archive-api) as fallback reference.

**Confidence:** MEDIUM -- no official API docs exist. Implementation will require studying third-party wrappers or the [Anna's Archive source code](https://github.com/LilyLoops/annas-archive).

### What NOT to Add

| Option | Why Not |
|--------|---------|
| RapidAPI wrapper | Adds third-party dependency, rate limits, and cost |
| `archive_of_anna` npm package | Unmaintained JS wrapper; we need Python-side integration |
| Scraping approach | Fragile; the donation API key path is more reliable |

---

## 4. Node 22 LTS Upgrade

### Current State

- `package.json` engines: `"node": ">=18"`
- Node 18 is **EOL** -- no security patches
- Recommendation: Skip Node 20, go directly to Node 22 LTS (supported until April 2027)

### Migration Checklist

| Area | Action | Risk |
|------|--------|------|
| Engine field | Update to `"node": ">=22"` | None |
| `--experimental-vm-modules` | Still needed for Jest ESM in Node 22 | None |
| Import assertions | Replace any `assert` keyword with `with` if used | Likely none in codebase |
| `dirent.path` | Replace with `dirent.parentPath` if used | Grep codebase |
| Native modules | `npm rebuild` -- PythonShell uses N-API, should be fine | LOW |
| OpenSSL/TLS | Stricter defaults in Node 22 | May affect Z-Library HTTPS if certs are weak |
| `fetch` API | Now stable -- can remove polyfills if any | Benefit |
| CI/CD | Update GitHub Actions `node-version` | Standard |
| OS requirements | glibc 2.28+ required | Verify deployment targets |

### Benefits

- 10-15% V8 performance improvement
- Stable fetch API
- Active security patches until April 2027
- Native WebSocket client available

**Confidence:** HIGH -- well-documented migration path.

---

## 5. AsyncZlib Removal (Pure EAPI)

### Current State (Verified via Code Inspection)

`download_book()` in `libasync.py` line 357 **already uses EAPI exclusively**:
1. Calls `self._eapi.get_download_link(book_id, book_hash)` for URL
2. Streams download via httpx with EAPI cookies

The `AsyncZlib` class still exists but its download path routes through EAPI. The EAPI client (`eapi.py`) is self-contained with full endpoint coverage:

| EAPI Endpoint | Method | Purpose |
|---------------|--------|---------|
| `/eapi/user/login` | POST | Authentication |
| `/eapi/book/search` | POST | Search with filters |
| `/eapi/book/{id}/{hash}` | GET | Book info |
| `/eapi/book/{id}/{hash}/file` | GET | Download link |
| `/eapi/book/recently` | GET | Recent books |
| `/eapi/book/most-popular` | GET | Popular books |
| `/eapi/user/book/downloaded` | GET | Download history |
| `/eapi/user/profile` | GET | User profile |
| `/eapi/book/{id}/{hash}/similar` | GET | Similar books |
| `/eapi/info/domains` | GET | Domain list |

### Removal Scope

| What to Remove | Why | Risk |
|----------------|-----|------|
| `AsyncZlib` class body (web scraping paths) | Dead code; EAPI handles everything | LOW |
| HTML parsing in libasync (`bs4` usage) | Only for web scraping fallback | Verify no other callers |
| `GET_request`, `POST_request` utils | Only used by web scraping | Check for other callers |
| Web login flow in libasync | EAPI has `/eapi/user/login` | LOW |

### No New Dependencies -- This is Pure Removal

Replace `AsyncZlib` with a thin wrapper around `EAPIClient`. The `python_bridge.py` call sites need updating to use the simplified class.

**Confidence:** HIGH -- code inspection confirms EAPI is the active path for all operations.

---

## Summary: Stack Delta for v1.1

| Capability | New Python Deps | New Node Deps | New Env Vars | New Modules |
|------------|----------------|---------------|--------------|-------------|
| Margin detection | None | None | None | `lib/rag/detection/margins.py` |
| Adaptive resolution | None | None | None | Logic in `lib/rag/ocr/` |
| Anna's Archive | None (httpx exists) | None | `ANNAS_ARCHIVE_API_KEY`, `ANNAS_ARCHIVE_BASE_URL` | `lib/sources/annas_archive.py` |
| Node 22 upgrade | None | None | None | package.json + CI config |
| AsyncZlib removal | None (removes code) | None | None | Simplified wrapper class |

**Key insight: This milestone requires zero new library dependencies.** All capabilities are achievable with the existing stack (PyMuPDF, httpx) plus new code modules. The main work is architectural -- new detection modules, source abstraction layer, and class simplification.

---

## Sources

- [PyMuPDF text extraction docs](https://pymupdf.readthedocs.io/en/latest/app1.html) -- block coordinates, dict mode
- [PyMuPDF page API](https://pymupdf.readthedocs.io/en/latest/page.html) -- clip parameter, get_pixmap
- [PyMuPDF text recipes](https://pymupdf.readthedocs.io/en/latest/recipes-text.html) -- practical extraction patterns
- [PyMuPDF get_text coordinates discussion](https://github.com/pymupdf/PyMuPDF/discussions/2128)
- [iosifache/annas-mcp](https://github.com/iosifache/annas-mcp) -- existing Anna's Archive MCP server
- [RapidAPI Anna's Archive](https://rapidapi.com/tribestick-tribestick-default/api/annas-archive-api) -- third-party API wrapper
- [Anna's Archive SearXNG engine docs](https://docs.searxng.org/dev/engines/online/annas_archive.html)
- [Node.js 22 release announcement](https://nodejs.org/en/blog/announcements/v22-release-announce)
- [Auth0 Node 18 to 22 migration guide](https://auth0.com/docs/troubleshoot/product-lifecycle/deprecations-and-migrations/migrate-nodejs-22)
- [HeroDevs Node 18 EOL analysis](https://www.herodevs.com/blog-posts/node-js-18-end-of-life-breaking-changes-aws-deadlines-and-what-to-do-next)
