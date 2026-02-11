"""
Booklist exploration tools for curated collection discovery.

This module previously enabled exploration of Z-Library's curated booklists
via HTML scraping. The EAPI does not expose a booklist browsing endpoint,
so booklist fetching is gracefully degraded with a clear message directing
users to use search_books instead.

Preserved function signatures for backward compatibility with python_bridge.
"""

import asyncio
import logging
from typing import Dict, Optional
import sys
import os

logger = logging.getLogger(__name__)

# Add zlibrary source directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), "..", "zlibrary", "src")
sys.path.insert(0, zlibrary_path)

from zlibrary.eapi import EAPIClient, normalize_eapi_search_response


async def fetch_booklist(
    booklist_id: str,
    booklist_hash: str,
    topic: str,
    email: str,
    password: str,
    page: int = 1,
    mirror: str = "",
    eapi_client: Optional[EAPIClient] = None,
) -> Dict:
    """
    Fetch a booklist from Z-Library.

    NOTE: The EAPI does not support direct booklist browsing. This function
    returns a degraded response with a search-based fallback when an
    eapi_client is provided, or a degraded notice otherwise.

    Args:
        booklist_id: Numeric ID of the booklist
        booklist_hash: Hash code for the booklist
        topic: Topic name
        email: Z-Library account email
        password: Z-Library account password
        page: Page number (default: 1)
        mirror: Optional custom mirror URL
        eapi_client: Optional pre-authenticated EAPIClient instance

    Returns:
        Dictionary with booklist structure (degraded: books from topic search)
    """
    # Use provided client or create a new one
    client = eapi_client
    should_close = False
    if client is None:
        domain = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")
        client = EAPIClient(domain)
        await client.login(email, password)
        should_close = True

    try:
        # EAPI has no booklist endpoint — fall back to enriched topic search
        logger.info(
            "Booklist browsing not available via EAPI. "
            "Falling back to enriched topic search for: %s",
            topic,
        )
        response = await client.search(
            message=topic,
            limit=25,
            page=page,
        )
        books = normalize_eapi_search_response(response)

        # Enrich top results with metadata (description, categories, rating)
        enriched_count = 0
        for book in books[:5]:
            book_id = book.get("id")
            book_hash = book.get("hash") or book.get("book_hash")
            if book_id and book_hash:
                try:
                    info = await client.get_book_info(int(book_id), book_hash)
                    book_data = info.get("book", info) if info else {}
                    if book_data.get("description"):
                        book["description"] = book_data["description"]
                    if book_data.get("categories"):
                        book["categories"] = book_data["categories"]
                    if book_data.get("rating"):
                        book["rating"] = book_data["rating"]
                    enriched_count += 1
                except Exception as e:
                    logger.debug("Could not enrich book %s: %s", book_id, e)

        logger.info(
            "Enriched %d/%d top results with metadata",
            enriched_count,
            min(5, len(books)),
        )

        # Mark each book with source
        for book in books:
            book["source"] = "topic_search_enriched"

        return {
            "booklist_id": booklist_id,
            "booklist_hash": booklist_hash,
            "topic": topic,
            "metadata": {
                "name": topic,
                "total_books": len(books),
                "description": (
                    f"True booklist browsing is not available via EAPI. "
                    f'These are curated topic search results for "{topic}" '
                    f"with metadata enrichment for the top {enriched_count} results. "
                    f"Use search_books with specific queries for more targeted results."
                ),
            },
            "books": books,
            "page": page,
            "degraded": True,
            "source": "topic_search_enriched",
        }
    finally:
        if should_close:
            await client.close()


# Synchronous wrapper for use from python_bridge
def fetch_booklist_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for fetch_booklist.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(fetch_booklist(*args, **kwargs))
