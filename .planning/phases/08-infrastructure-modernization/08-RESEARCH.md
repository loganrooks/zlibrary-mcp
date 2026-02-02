# Phase 8: Infrastructure Modernization - Research

**Researched:** 2026-02-01
**Domain:** Node.js runtime, Python/Docker packaging, Z-Library EAPI completeness
**Confidence:** MEDIUM (mixed: some areas HIGH, EAPI gaps LOW)

## Summary

Phase 8 covers six requirements across three sub-plans: Node 22 upgrade, AsyncZlib removal, and Docker/EAPI fixes. The Node 22 upgrade is straightforward since the project already uses ESM and targets ES2022. AsyncZlib removal is the most architecturally significant change -- the download path already uses EAPI internally (via `AsyncZlib.download_book` which calls `self._eapi.get_download_link`), so the legacy class is a thin wrapper that can be replaced. The Docker numpy/Alpine issue stems from `opencv-python` as a transitive dependency requiring C compilation on musl. EAPI gap improvements (booklists, full-text search) are limited by what endpoints Z-Library actually exposes.

**Primary recommendation:** Start with Node 22 + env-paths v4 (lowest risk), then AsyncZlib removal (highest value), then Docker fix + EAPI improvements (independent).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Node.js | 22 LTS | Runtime | Active LTS until April 2027, current system runs 18.19.1 |
| env-paths | 4.0.0 | XDG paths | Pure ESM, requires Node 20+. Currently on 3.0.0 |
| typescript | 5.5.x | Compiler | Already in use, no change needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| opencv-python-headless | 4.12.x | Image processing | Replace opencv-python to avoid GUI deps and reduce Alpine issues |
| uv | latest | Python packaging | Already used; handles Alpine wheels via `--python-platform` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alpine Docker base | python:slim (Debian) | Larger image (~150MB vs ~50MB) but no musl compilation issues. Not recommended since builder stage is already Alpine and supergateway runtime is fixed. |
| opencv-python | opencv-python-headless | Same API, no GUI deps, smaller, better Alpine compat. Use this. |

**Installation:**
```bash
npm install env-paths@4
# Node 22: update engines field, CI matrix, Dockerfile builder
```

## Architecture Patterns

### Pattern 1: EAPI-Only Download (AsyncZlib Removal)

**What:** Replace `AsyncZlib.download_book()` with direct EAPI calls in `python_bridge.py`

**Current flow:**
```
python_bridge.download_book()
  -> client_manager.get_default_client()  # returns AsyncZlib
  -> zlib.download_book(book_details, output_dir)
    -> self._eapi.get_download_link(id, hash)  # EAPI call
    -> httpx download with cookies from self._eapi
```

**Target flow:**
```
python_bridge.download_book()
  -> get_eapi_client()  # direct EAPIClient
  -> eapi.get_download_link(id, hash)
  -> httpx download with eapi cookies
```

**Key insight:** `AsyncZlib.download_book()` in `libasync.py:357` already delegates to `self._eapi.get_download_link()`. The only value AsyncZlib adds is cookie management during login, which EAPIClient already handles independently.

**When to use:** This is the only pattern for INFRA-03.

### Pattern 2: Adapter During Transition

**What:** Create a thin adapter that wraps EAPIClient with the same interface as the download functions currently expect from AsyncZlib. Swap in one commit, verify, then remove adapter.

**Steps:**
1. Add `download_file()` method to `EAPIClient` (extract from `AsyncZlib.download_book`)
2. Update `python_bridge.download_book()` to use `get_eapi_client()` instead of `client_manager.get_default_client()`
3. Verify downloads work
4. Remove `client_manager.py` entirely
5. Remove `AsyncZlib` imports from `advanced_search.py`
6. Grep for remaining references, clean up

### Anti-Patterns to Avoid
- **Keeping AsyncZlib "just in case"**: The ADR-005 explicitly notes downloads use EAPI internally. No fallback needed.
- **Changing Docker base image**: The runtime stage uses `ghcr.io/supercorp-ai/supergateway:3.4.3` which is fixed. Only the builder stage is Alpine.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XDG paths | Custom path logic | env-paths v4 | Cross-platform, well-tested |
| Alpine numpy wheels | Build from source | `opencv-python-headless` or `--only-binary :all:` | Avoids GCC/musl compilation entirely |
| EAPI cookie auth | Custom cookie jar | httpx built-in cookie handling | Already used in EAPIClient |

**Key insight:** The numpy problem is not about numpy itself -- it is a transitive dependency of `opencv-python`. Switching to `opencv-python-headless` eliminates GUI dependencies and may resolve Alpine build issues. Alternatively, pinning to `musllinux` wheels or using `--only-binary :all:` avoids source compilation.

## Common Pitfalls

### Pitfall 1: Node 22 Import Assertions Syntax Change
**What goes wrong:** `import assert { type: 'json' }` syntax removed in Node 22; must use `with` keyword
**Why it happens:** V8 engine change, deprecated syntax removed
**How to avoid:** Grep for `import.*assert` in codebase. This project uses `resolveJsonModule` in tsconfig so JSON imports go through TypeScript, not runtime assert syntax. Low risk.
**Warning signs:** Build errors mentioning "import assertions"

### Pitfall 2: AsyncZlib Removal Breaks Download Cookies
**What goes wrong:** Downloads fail because the EAPI client does not have the right cookies/session state
**Why it happens:** AsyncZlib login sets cookies used for file download; EAPIClient has its own cookie flow
**How to avoid:** EAPIClient already manages `remix_userid` and `remix_userkey` cookies after login. The download URL from EAPI should work with the same client's httpx session. Test with a real download.
**Warning signs:** HTTP 403 on download URL

### Pitfall 3: opencv-python-headless Still Needs Build Deps on Alpine
**What goes wrong:** Even headless variant may need compilation on musl
**Why it happens:** PyPI may not have musllinux wheels for all Python versions
**How to avoid:** Check if `opencv-python-headless` has `musllinux` wheels in PyPI. If not, add build deps (`gcc`, `musl-dev`, `g++`) to builder stage only -- they are discarded in runtime stage. Or constrain to `--only-binary :all:` and fail fast if no wheel available.
**Warning signs:** `uv sync` hangs for minutes (compiling C code)

### Pitfall 4: env-paths v4 is Pure ESM (Same as v3)
**What goes wrong:** Import errors if any CommonJS code tries to require it
**Why it happens:** env-paths has been pure ESM since v3
**How to avoid:** Project already uses ESM (`"type": "module"` in package.json) and already has env-paths v3. The v3->v4 upgrade only changes Node version requirement (12 -> 20). Minimal risk.
**Warning signs:** None expected; this is a trivial version bump.

### Pitfall 5: EAPI Has No Booklist or Full-Text Search Endpoints
**What goes wrong:** Attempting to implement "improved" booklist/full-text search hits a wall because the API simply does not have these endpoints
**Why it happens:** EAPI is designed for the mobile app which does not expose booklist browsing
**How to avoid:** Accept that INFRA-05 and INFRA-06 are bounded by EAPI capabilities. Improvements must be creative: better search queries, client-side filtering, similarity-based recommendations, not new endpoints.
**Warning signs:** Spending time reverse-engineering endpoints that do not exist

## Code Examples

### EAPI Download Without AsyncZlib
```python
# Extract from libasync.py:357-397 into standalone function
async def download_book_via_eapi(eapi_client: EAPIClient, book_details: dict, output_dir: str) -> str:
    """Download a book using only EAPIClient."""
    book_id = int(book_details.get('id', 0))
    book_hash = book_details.get('hash') or book_details.get('book_hash', '')

    # Get download link
    dl_resp = await eapi_client.get_download_link(book_id, book_hash)
    download_url = dl_resp.get("file", {}).get("downloadLink") or dl_resp.get("downloadLink", "")

    if not download_url:
        raise ValueError(f"No download link for book {book_id}")

    # Make URL absolute
    if download_url.startswith("/"):
        download_url = f"https://{eapi_client.domain}{download_url}"

    # Download file using the same httpx client (has auth cookies)
    client = await eapi_client._get_client()
    async with client.stream("GET", download_url) as resp:
        resp.raise_for_status()
        # ... save to file (extract from libasync.py:398+)
```

### Node 22 CI Matrix Update
```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: '22'  # was '18'
```

### opencv-python-headless in pyproject.toml
```toml
dependencies = [
    # Replace "opencv-python>=4.12.0.88" with:
    "opencv-python-headless>=4.12.0.88",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AsyncZlib for all ops | EAPIClient for search/metadata, AsyncZlib for download | 2026-01 (Phase 7) | Dual client complexity |
| Node 18 | Node 22 LTS | Oct 2024 (22 entered LTS) | Node 18 is EOL |
| env-paths v3 | env-paths v4 | Jan 2025 | Requires Node 20+ |
| opencv-python | opencv-python-headless | N/A | Better for servers/Docker |

**Deprecated/outdated:**
- Node.js 18: EOL since April 2025. No security patches.
- AsyncZlib as download client: Already delegates to EAPI internally. Pure overhead.

## Open Questions

1. **Does EAPIClient's httpx session have the right cookies for file download?**
   - What we know: `download_book` in libasync.py uses `self._eapi.get_download_link()` then downloads with httpx. The download uses a *new* httpx client (not the EAPI one) with cookies from `self.profile`.
   - What's unclear: Whether EAPIClient's cookies (`remix_userid`, `remix_userkey`) are sufficient for the download URL, or if additional cookies from the login flow are needed.
   - Recommendation: Test with a real download using only EAPIClient before removing AsyncZlib. This is the critical validation step for INFRA-03.

2. **Is there an undocumented EAPI endpoint for full-text search?**
   - What we know: [EAPI documentation](https://github.com/baroxyton/zlibrary-eapi-documentation) lists `/eapi/book/search` as the only search endpoint. No `fulltext` or `content` parameter documented.
   - What's unclear: Whether `message` parameter in search does implicit full-text search, or if there are undocumented params.
   - Recommendation: For INFRA-06, try adding parameters like `content=1` or `searchType=fulltext` experimentally. If nothing works, improve the fallback with better query construction and result filtering.

3. **Can UV resolve musllinux wheels for opencv-python-headless?**
   - What we know: UV respects platform markers. Alpine is musl-based.
   - What's unclear: Whether opencv-python-headless publishes musllinux wheels.
   - Recommendation: Check PyPI for available wheels. If no musllinux wheel exists, the Dockerfile builder stage needs build deps (`gcc`, `musl-dev`, `g++`).

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `libasync.py:357-397` (AsyncZlib download uses EAPI internally)
- Codebase analysis: `eapi.py` (EAPIClient with full endpoint coverage)
- Codebase analysis: `docker/Dockerfile` (Alpine builder, supergateway runtime)
- Codebase analysis: `uv.lock` (numpy is transitive dep of opencv-python)
- ADR-005-EAPI-Migration.md (design decisions and consequences)

### Secondary (MEDIUM confidence)
- [Node.js v22 release announcement](https://nodejs.org/en/blog/announcements/v22-release-announce) - Features and breaking changes
- [Node.js 18 EOL](https://www.herodevs.com/blog-posts/node-js-18-end-of-life-breaking-changes-aws-deadlines-and-what-to-do-next) - Migration urgency
- [Node.js v20 to v22 migration](https://nodejs.org/en/blog/migrations/v20-to-v22) - Breaking changes
- [env-paths v4.0.0 release](https://github.com/sindresorhus/env-paths/releases) - Requires Node 20+
- [Z-Library EAPI documentation](https://github.com/baroxyton/zlibrary-eapi-documentation) - All known endpoints

### Tertiary (LOW confidence)
- [NumPy Alpine issues](https://github.com/numpy/numpy/issues/30024) - musl build failures
- [Alpine Docker numpy guide](https://www.pythontutorials.net/blog/installing-numpy-on-docker-alpine/) - Fix approaches
- WebSearch for opencv-python-headless as Alpine fix - community pattern, needs validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Direct codebase analysis + official Node.js docs
- Architecture (AsyncZlib removal): HIGH - Code shows EAPI already handles downloads
- Architecture (EAPI gaps): LOW - Limited by undocumented API surface
- Pitfalls: MEDIUM - Docker/Alpine issues well-documented, EAPI gaps uncertain
- Docker fix: MEDIUM - Multiple approaches, needs validation of wheel availability

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable technologies, EAPI may change without notice)
