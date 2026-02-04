#!/usr/bin/env python3
"""Test Anna's Archive slow download flow.

Prerequisites:
  Set TEST_MD5 from search results (env var or .env file)

Run: uv run python scripts/experiments/test_annas_slow_download.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv
import httpx

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")
from bs4 import BeautifulSoup

TEST_MD5 = os.environ.get("TEST_MD5")
BASE_URL = os.environ.get("ANNAS_BASE_URL", "https://annas-archive.li")


def test_slow_download(md5: str):
    """Test the slow download path."""
    url = f"{BASE_URL}/slow_download/{md5}"
    print(f"Requesting: {url}")

    client = httpx.Client(timeout=60, follow_redirects=True)

    try:
        response = client.get(url)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")

        # Check for browser verification redirect
        if "browser_verification" in str(response.url):
            print("\n" + "=" * 50)
            print("BROWSER VERIFICATION REQUIRED")
            print("=" * 50)
            print("The slow download path requires browser verification.")
            print("This likely needs JavaScript execution or CAPTCHA solving.")
            print(f"Verification URL: {response.url}")
            return {
                "status": "verification_required",
                "verification_url": str(response.url),
                "automatable": False,
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for download button
        download_btn = soup.select_one("#download-button")
        if download_btn:
            href = download_btn.get("href")
            disabled = download_btn.get("disabled")
            classes = download_btn.get("class", [])

            print(f"\nDownload button found:")
            print(f"  href: {href}")
            print(f"  disabled: {disabled}")
            print(f"  classes: {classes}")

            if href and not disabled:
                print("\nDirect download link available!")
                return {"status": "direct_link", "url": href, "automatable": True}
            else:
                print("\nButton exists but not yet active (waitlist)")
                return {
                    "status": "waitlist",
                    "button_html": str(download_btn)[:500],
                    "automatable": "unknown",
                }

        # Look for partner server links
        partner_links = []
        for link in soup.select("a"):
            href = link.get("href", "")
            text = link.get_text(strip=True).lower()
            if "partner" in text or "server" in text or "download" in text:
                partner_links.append({"href": href, "text": link.get_text(strip=True)[:50]})

        if partner_links:
            print(f"\nFound {len(partner_links)} potential download links:")
            for pl in partner_links[:5]:
                print(f"  - {pl['text']}: {pl['href'][:60]}...")
            return {
                "status": "partner_links",
                "links": partner_links[:10],
                "automatable": "maybe",
            }

        # Look for any useful info
        print("\nNo obvious download mechanism found.")
        print("Page title:", soup.title.string if soup.title else "None")

        # Check for common elements
        forms = soup.select("form")
        print(f"Forms on page: {len(forms)}")

        scripts = soup.select("script")
        print(f"Scripts on page: {len(scripts)}")

        # Dump relevant sections
        main_content = soup.select_one("main") or soup.select_one("#content") or soup.select_one("body")
        if main_content:
            text = main_content.get_text(" ", strip=True)[:1000]
            print(f"\nMain content preview:\n{text}")

        return {
            "status": "unknown",
            "page_title": soup.title.string if soup.title else None,
            "forms_count": len(forms),
            "scripts_count": len(scripts),
            "automatable": "unknown",
        }

    except httpx.TimeoutException:
        print("ERROR: Request timed out")
        return {"status": "timeout", "automatable": False}
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return {"status": "error", "error": str(e), "automatable": False}
    finally:
        client.close()


if __name__ == "__main__":
    print("=== Testing Anna's Archive Slow Download Flow ===\n")

    if not TEST_MD5:
        print("ERROR: Set TEST_MD5 environment variable")
        print("  Run test_annas_search.py first to get an MD5")
        print("  export TEST_MD5='md5-from-search'")
        exit(1)

    print(f"Using MD5: {TEST_MD5}")
    print(f"Using base URL: {BASE_URL}")
    print()

    result = test_slow_download(TEST_MD5)

    print(f"\n{'='*50}")
    print(f"RESULT SUMMARY")
    print(f"{'='*50}")
    print(f"Status: {result.get('status')}")
    print(f"Automatable: {result.get('automatable')}")

    if result.get("status") == "verification_required":
        print("\nCONCLUSION: Slow downloads require browser automation (Playwright)")
        print("This is a significant implementation effort.")

    elif result.get("status") == "direct_link":
        print("\nCONCLUSION: Slow downloads may be automatable via simple HTTP!")
        print(f"Direct URL: {result.get('url')}")

    elif result.get("status") == "partner_links":
        print("\nCONCLUSION: Partner server links found - may be automatable")
        print("Need to test if these links work without JavaScript")

    else:
        print("\nCONCLUSION: Need more investigation")
        print("The page structure may have changed or requires JS rendering")
