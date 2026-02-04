# Phase 12: Anna's Archive Integration - Experiment Plan

**Created:** 2026-02-03
**Status:** Ready for experimentation
**Purpose:** Gather real data through hands-on testing before re-planning

## Why This Experiment

The original CONTEXT.md and RESEARCH.md were written with these assumptions:
- Anna's Archive API requires paid donation (user now HAS a key with 25 fast downloads/day)
- LibGen was the recommended fallback source
- We understood the API from documentation only

**What changed:**
- User donated and has a working secret key
- We discovered the API is minimal: only `/dyn/api/fast_download.json` for downloads
- Search requires HTML scraping (no search API)
- Slow downloads exist but mechanism is unclear
- LibGen also requires scraping (no real API advantage over Anna's Archive)

**What we don't know:**
- Does the fast download API actually work with user's key?
- What does slow download flow look like? Can it be automated?
- What does libgen-api-enhanced actually return?
- Which approach is more stable/maintainable?

---

## Experiments

### Experiment 1: Anna's Archive Fast Download API

**Hypothesis:** The fast download API works with user's secret key and returns a direct download URL.

**Setup:**
```bash
# User provides their secret key
export ANNAS_SECRET_KEY="your-key-here"
```

**Test script:** `scripts/experiments/test_annas_fast_download.py`
```python
#!/usr/bin/env python3
"""Test Anna's Archive fast download API."""
import os
import httpx
import json

SECRET_KEY = os.environ.get("ANNAS_SECRET_KEY")
BASE_URL = "https://annas-archive.li"

# Use a known MD5 hash (from a previous search or known book)
# We'll need user to provide one, or search manually first
TEST_MD5 = "d41d8cd98f00b204e9800998ecf8427e"  # placeholder - user provides real one

def test_fast_download(md5: str):
    """Test the fast download API endpoint."""
    url = f"{BASE_URL}/dyn/api/fast_download.json?md5={md5}&key={SECRET_KEY}"
    print(f"Requesting: {url[:80]}...&key=***")

    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"Error body: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        return None

if __name__ == "__main__":
    if not SECRET_KEY:
        print("ERROR: Set ANNAS_SECRET_KEY environment variable")
        exit(1)

    # User should replace with a real MD5 from a book they want
    result = test_fast_download(TEST_MD5)

    if result and result.get("download_url"):
        print(f"\n✓ SUCCESS: Got download URL")
        print(f"  URL: {result['download_url'][:80]}...")
    elif result and result.get("error"):
        print(f"\n✗ API ERROR: {result['error']}")
    else:
        print(f"\n? UNCLEAR: Unexpected response format")
```

**What to record:**
- [ ] API returns 200?
- [ ] Response contains `download_url`?
- [ ] Response contains `error`? What error?
- [ ] Download URL actually works (can fetch file)?
- [ ] Any rate limit info in response?

**User action:** Run script with real MD5 hash, report results.

---

### Experiment 2: Anna's Archive Search (HTML Scraping)

**Hypothesis:** We can reliably extract book results from Anna's Archive search HTML.

**Test script:** `scripts/experiments/test_annas_search.py`
```python
#!/usr/bin/env python3
"""Test Anna's Archive search via HTML scraping."""
import httpx
from bs4 import BeautifulSoup
import json

BASE_URL = "https://annas-archive.li"

def search_annas(query: str, limit: int = 5):
    """Search Anna's Archive and parse results."""
    url = f"{BASE_URL}/search?q={query}"
    print(f"Searching: {url}")

    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")

        if response.status_code != 200:
            print(f"Error: {response.text[:500]}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for book result links (pattern from annas-mcp)
        results = []
        for link in soup.select("a[href^='/md5/']")[:limit * 2]:  # *2 because duplicates
            # Skip if already seen this href
            href = link.get('href', '')
            if not href or any(r.get('md5') == href.split('/')[-1] for r in results):
                continue

            md5 = href.split('/')[-1]

            # Try to get title from nearby elements
            parent = link.find_parent('div')
            title = link.get_text(strip=True) or "Unknown"

            results.append({
                'md5': md5,
                'title': title[:100],
                'url': f"{BASE_URL}{href}",
            })

            if len(results) >= limit:
                break

        return results

    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        return []

if __name__ == "__main__":
    query = "python programming"
    print(f"\n=== Testing search for '{query}' ===\n")

    results = search_annas(query)

    print(f"\nFound {len(results)} results:")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['title']}")
        print(f"     MD5: {r['md5']}")
        print(f"     URL: {r['url']}")

    if results:
        print(f"\n✓ Search scraping works")
        print(f"  First result MD5 can be used for Experiment 1: {results[0]['md5']}")
    else:
        print(f"\n✗ Search scraping failed or returned no results")
```

**What to record:**
- [ ] Search page loads without CAPTCHA/block?
- [ ] HTML structure matches expected selectors?
- [ ] Can extract MD5, title, author, etc.?
- [ ] Results are consistent across multiple runs?
- [ ] Any Cloudflare challenges?

**User action:** Run script, report results and any issues.

---

### Experiment 3: Anna's Archive Slow Download Flow

**Hypothesis:** Slow downloads can be automated without browser automation.

**Test script:** `scripts/experiments/test_annas_slow_download.py`
```python
#!/usr/bin/env python3
"""Test Anna's Archive slow download flow."""
import httpx
import time
from bs4 import BeautifulSoup

BASE_URL = "https://annas-archive.li"

def test_slow_download(md5: str):
    """Test the slow download path."""
    url = f"{BASE_URL}/slow_download/{md5}"
    print(f"Requesting slow download: {url}")

    client = httpx.Client(timeout=60, follow_redirects=True)

    try:
        # Step 1: Load slow download page
        response = client.get(url)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")

        if "browser_verification" in str(response.url):
            print("\n⚠ BROWSER VERIFICATION REQUIRED")
            print("  This likely requires JavaScript execution or CAPTCHA")
            return {"status": "verification_required", "url": str(response.url)}

        # Step 2: Parse page for download links or waitlist
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for download button
        download_btn = soup.select_one("#download-button")
        if download_btn:
            href = download_btn.get('href')
            print(f"\nDownload button found: href={href}")
            if href:
                print(f"✓ Direct download link available: {href}")
                return {"status": "direct_link", "url": href}
            else:
                print("  Button exists but no href yet (waitlist?)")
                return {"status": "waitlist", "html_snippet": str(download_btn)[:500]}

        # Look for partner server links
        partner_links = soup.select("a[href*='partner']")
        if partner_links:
            print(f"\nFound {len(partner_links)} partner server links:")
            for link in partner_links[:3]:
                print(f"  - {link.get('href', 'no href')[:80]}")
            return {"status": "partner_links", "links": [l.get('href') for l in partner_links[:5]]}

        # Dump page structure for analysis
        print("\nPage structure (first 2000 chars):")
        print(response.text[:2000])
        return {"status": "unknown", "html_preview": response.text[:2000]}

    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        client.close()

if __name__ == "__main__":
    # Use MD5 from Experiment 2, or provide a known one
    TEST_MD5 = "d41d8cd98f00b204e9800998ecf8427e"  # placeholder

    print("=== Testing Slow Download Flow ===\n")
    print("NOTE: Replace TEST_MD5 with a real MD5 from search results\n")

    result = test_slow_download(TEST_MD5)

    print(f"\n=== Result ===")
    print(f"Status: {result.get('status')}")
```

**What to record:**
- [ ] Does slow_download page load without JS?
- [ ] Is browser verification (CAPTCHA) always required?
- [ ] Are there partner server links visible in HTML?
- [ ] Is there a waitlist timer, and can we detect when it completes?
- [ ] Can we get a download URL without JavaScript execution?

**User action:** Run script with real MD5, report what happens.

---

### Experiment 4: LibGen via libgen-api-enhanced

**Hypothesis:** libgen-api-enhanced provides working search and download resolution.

**Test script:** `scripts/experiments/test_libgen.py`
```python
#!/usr/bin/env python3
"""Test libgen-api-enhanced library."""
import asyncio

# First, install: uv add libgen-api-enhanced

def test_libgen_sync():
    """Test synchronous LibGen API."""
    try:
        from libgen_api import LibgenSearch
    except ImportError:
        print("ERROR: Run 'uv add libgen-api-enhanced' first")
        return None

    print("=== Testing LibGen Search ===\n")

    # Test search
    s = LibgenSearch()  # Uses default mirror
    print(f"Mirror: {s.mirror if hasattr(s, 'mirror') else 'default'}")

    query = "python programming"
    print(f"Searching for: {query}")

    try:
        results = s.search_title(query)
        print(f"Found {len(results) if results else 0} results")

        if results:
            book = results[0]
            print(f"\nFirst result:")
            print(f"  Title: {getattr(book, 'title', book.get('Title', 'N/A'))}")
            print(f"  Author: {getattr(book, 'author', book.get('Author', 'N/A'))}")
            print(f"  Year: {getattr(book, 'year', book.get('Year', 'N/A'))}")
            print(f"  Extension: {getattr(book, 'extension', book.get('Extension', 'N/A'))}")
            print(f"  MD5: {getattr(book, 'md5', book.get('MD5', 'N/A'))}")

            # Check what attributes/keys are available
            if hasattr(book, '__dict__'):
                print(f"\n  Available attributes: {list(book.__dict__.keys())}")
            elif isinstance(book, dict):
                print(f"\n  Available keys: {list(book.keys())}")

            # Try to get download link
            print(f"\n=== Testing Download Resolution ===")
            try:
                if hasattr(book, 'resolve_direct_download_link'):
                    link = book.resolve_direct_download_link()
                    print(f"  Download link: {link[:80] if link else 'None'}...")
                elif hasattr(s, 'resolve_download_links'):
                    links = s.resolve_download_links(book)
                    print(f"  Download links: {links}")
                else:
                    print("  No download resolution method found")
                    # Check for pre-existing download URLs
                    for attr in ['download_url', 'tor_download_link', 'Download']:
                        val = getattr(book, attr, None) or (book.get(attr) if isinstance(book, dict) else None)
                        if val:
                            print(f"  Found {attr}: {val[:80] if val else 'None'}...")
            except Exception as e:
                print(f"  Download resolution error: {e}")

            return results
        else:
            print("No results returned")
            return []

    except Exception as e:
        print(f"Search error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_libgen_sync()

    if results:
        print(f"\n✓ LibGen search works")
    else:
        print(f"\n✗ LibGen search failed or returned no results")
```

**What to record:**
- [ ] Library installs cleanly?
- [ ] Search returns results?
- [ ] Result format: objects or dicts? What fields?
- [ ] Download link resolution works?
- [ ] Any rate limiting or errors?

**User action:** Install library, run script, report results.

---

## Experiment Execution Order

1. **Run Experiment 4 (LibGen)** first — no auth needed, establishes baseline
2. **Run Experiment 2 (Anna's Search)** — get real MD5 hashes
3. **Run Experiment 1 (Anna's Fast Download)** with MD5 from step 2 and your API key
4. **Run Experiment 3 (Anna's Slow Download)** — understand the fallback path

---

## Recording Results

### Results: Experiment 1 (Anna's Fast Download API)
```
Date: 2026-02-03
Status: [x] Success
Notes:
- API works with user's secret key
- Returns download_url + account_fast_download_info (quota tracking)
- User has 25 fast downloads/day
- IMPORTANT: domain_index=0 returns HTTPS URLs with SSL errors
- SOLUTION: Use domain_index=1 for HTTP URLs that work perfectly
- Response includes: downloads_left, downloads_per_day, downloads_done_today, recently_downloaded_md5s
- API is self-documenting (includes usage docs in ///download_url field)
```

### Results: Experiment 2 (Anna's Search Scraping)
```
Date: 2026-02-03
Status: [x] Success
Notes:
- HTML scraping works despite Cloudflare warning
- Returns MD5 hashes usable for fast download API
- Results include source prefixes (nexusstc/, lgli/) indicating origin indexes
- Selector: a[href^='/md5/'] works for extracting results
- Can extract: md5, title, url, metadata text
```

### Results: Experiment 3 (Anna's Slow Download)
```
Date: 2026-02-03
Status: [x] Failed (as expected)
Notes:
- Returns 403 with DDoS-Guard "Checking your browser" page
- Requires JavaScript execution for browser verification
- NOT automatable without Playwright or similar browser automation
- RECOMMENDATION: Don't implement slow downloads - use fast API + LibGen fallback instead
```

### Results: Experiment 4 (LibGen)
```
Date: 2026-02-03
Status: [x] Success
Notes:
- libgen-api-enhanced v1.2.4 works
- IMPORTANT: Import is `from libgen_api_enhanced import LibgenSearch` (not libgen_api)
- Search returns 100 results by default
- Result format: objects with attributes (not dicts)
- Available fields: id, title, author, publisher, year, language, pages, size, extension,
  md5, mirrors, tor_download_link, resolved_download_link, date_added, date_last_modified
- resolve_direct_download_link() returned None in test (may need specific setup)
- tor_download_link exists and is populated (Tor .onion URLs)
- Default mirror: https://libgen.li/
```

---

## Decision Matrix

| Capability | Anna's Archive | LibGen | Winner |
|------------|----------------|--------|--------|
| Search | Scraping: ✓ works | Scraping via library: ✓ works | Tie |
| Download (fast) | API: ✓ works (25/day quota) | Tor links: ✓ works | Anna's (simpler) |
| Download (slow) | ✗ blocked (DDoS-Guard) | N/A | N/A |
| Stability | Single API endpoint | Library wraps scraping | Anna's (API contract) |
| Ease of implementation | Medium (scrape search + API download) | Easy (library handles both) | LibGen |
| Rate limits | 25 fast downloads/day | Unknown (scraping limits) | Anna's (known quota) |

**Recommendation after experiments:**

**Primary: Anna's Archive** (user has paid API key)
- Search: HTML scraping at /search?q=...
- Download: Fast download API with domain_index=1
- Quota: 25/day with tracking via API response

**Fallback: LibGen** (when Anna's quota exhausted or unavailable)
- Search: libgen-api-enhanced library
- Download: Tor links or resolved mirrors
- No quota limits (but may have rate limiting)

**Do NOT implement:**
- Anna's Archive slow downloads (requires browser automation)
- Parallel mode initially (add later if needed)

---

## Next Steps After Experiments

1. Update `12-CONTEXT.md` with corrected assumptions
2. Update `12-RESEARCH.md` with validated findings
3. Delete or archive the 3 existing PLAN.md files (based on wrong assumptions)
4. Run `/gsd:plan-phase 12` with fresh context

---

*Phase: 12-annas-archive*
*Experiment plan created: 2026-02-03*
