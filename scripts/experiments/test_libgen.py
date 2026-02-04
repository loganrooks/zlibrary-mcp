#!/usr/bin/env python3
"""Test libgen-api-enhanced library.

Run: uv run python scripts/experiments/test_libgen.py
"""


def test_libgen_sync():
    """Test synchronous LibGen API."""
    try:
        from libgen_api_enhanced import LibgenSearch
    except ImportError:
        print("ERROR: Run 'uv add libgen-api-enhanced' first")
        return None

    print("=== Testing LibGen Search ===\n")

    # Test search
    s = LibgenSearch()  # Uses default mirror
    print(f"Mirror: {getattr(s, 'mirror', 'default')}")

    query = "python programming"
    print(f"Searching for: {query}")

    try:
        results = s.search_title(query)
        print(f"Found {len(results) if results else 0} results")

        if results:
            book = results[0]
            print(f"\nFirst result:")

            # Handle both object and dict formats
            def get_field(obj, *names):
                for name in names:
                    if hasattr(obj, name):
                        return getattr(obj, name)
                    if isinstance(obj, dict) and name in obj:
                        return obj[name]
                return "N/A"

            print(f"  Title: {get_field(book, 'title', 'Title')}")
            print(f"  Author: {get_field(book, 'author', 'Author')}")
            print(f"  Year: {get_field(book, 'year', 'Year')}")
            print(f"  Extension: {get_field(book, 'extension', 'Extension')}")
            print(f"  Size: {get_field(book, 'size', 'Size')}")
            print(f"  MD5: {get_field(book, 'md5', 'MD5')}")
            print(f"  ID: {get_field(book, 'id', 'ID')}")

            # Check what attributes/keys are available
            if hasattr(book, "__dict__"):
                print(f"\n  Available attributes: {list(book.__dict__.keys())}")
            elif isinstance(book, dict):
                print(f"\n  Available keys: {list(book.keys())}")
            else:
                print(f"\n  Type: {type(book)}")

            # Try to get download link
            print(f"\n=== Testing Download Resolution ===")
            try:
                if hasattr(book, "resolve_direct_download_link"):
                    link = book.resolve_direct_download_link()
                    print(f"  resolve_direct_download_link(): {link[:80] if link else 'None'}...")
                elif hasattr(s, "resolve_download_links"):
                    links = s.resolve_download_links(book)
                    print(f"  resolve_download_links(): {links}")
                else:
                    print("  No download resolution method found on book or search object")

                # Check for pre-existing download URLs
                for attr in [
                    "download_url",
                    "tor_download_link",
                    "Download",
                    "Mirror_1",
                    "Mirror_2",
                ]:
                    val = get_field(book, attr)
                    if val and val != "N/A":
                        print(f"  Found {attr}: {str(val)[:80]}...")

            except Exception as e:
                print(f"  Download resolution error: {type(e).__name__}: {e}")

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
        print(f"\n{'='*50}")
        print(f"SUCCESS: LibGen search works")
        print(f"Results can be used for comparison with Anna's Archive")
    else:
        print(f"\n{'='*50}")
        print(f"FAILED: LibGen search failed or returned no results")
