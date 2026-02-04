#!/usr/bin/env python3
"""Test Anna's Archive search via HTML scraping.

Run: uv run python scripts/experiments/test_annas_search.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv
import httpx

# Load .env from project root (for ANNAS_BASE_URL if set)
load_dotenv(Path(__file__).parent.parent.parent / ".env")
from bs4 import BeautifulSoup

BASE_URL = os.environ.get("ANNAS_BASE_URL", "https://annas-archive.li")


def search_annas(query: str, limit: int = 5):
    """Search Anna's Archive and parse results."""
    url = f"{BASE_URL}/search?q={query}"
    print(f"Searching: {url}")

    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")

        if response.status_code != 200:
            print(f"Error response: {response.text[:500]}")
            return []

        # Check for Cloudflare or verification
        if "challenge" in response.text.lower() or "cf-" in response.text.lower()[:1000]:
            print("\nWARNING: Possible Cloudflare challenge detected")

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for book result links (pattern from annas-mcp)
        results = []
        seen_md5 = set()

        for link in soup.select("a[href^='/md5/']"):
            href = link.get("href", "")
            if not href:
                continue

            md5 = href.split("/")[-1]
            if md5 in seen_md5:
                continue
            seen_md5.add(md5)

            # Try to get title - the link text or nearby text
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                # Try parent or sibling
                parent = link.find_parent("div")
                if parent:
                    title = parent.get_text(strip=True)[:100]

            # Try to get metadata from parent container
            meta = {}
            parent_div = link.find_parent("div", class_=True)
            if parent_div:
                text = parent_div.get_text(" ", strip=True)
                # Look for patterns like "English [en]", "PDF", "2023", "1.2MB"
                if "MB" in text or "KB" in text or "GB" in text:
                    meta["has_size"] = True
                meta["raw_text"] = text[:200]

            results.append(
                {
                    "md5": md5,
                    "title": title[:150] if title else "Unknown",
                    "url": f"{BASE_URL}{href}",
                    "meta": meta,
                }
            )

            if len(results) >= limit:
                break

        return results

    except httpx.TimeoutException:
        print("ERROR: Request timed out")
        return []
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    query = "python programming"
    print(f"\n=== Testing Anna's Archive search for '{query}' ===\n")

    results = search_annas(query)

    print(f"\n{'='*50}")
    print(f"Found {len(results)} results:")
    print(f"{'='*50}")

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['title'][:60]}...")
        print(f"   MD5: {r['md5']}")
        print(f"   URL: {r['url']}")
        if r.get("meta", {}).get("raw_text"):
            print(f"   Meta: {r['meta']['raw_text'][:100]}...")

    if results:
        print(f"\n{'='*50}")
        print(f"SUCCESS: Search scraping works")
        print(f"\nUse this MD5 for fast download test:")
        print(f"  export TEST_MD5='{results[0]['md5']}'")
    else:
        print(f"\n{'='*50}")
        print(f"FAILED: Search scraping failed or returned no results")
        print(f"This may indicate Cloudflare blocking or HTML structure change")
