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
from typing import Dict, List, Optional
import sys
import os

logger = logging.getLogger(__name__)

# Add zlibrary source directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary', 'src')
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
        from zlibrary.util import discover_eapi_domain
        domain = await discover_eapi_domain()
        client = EAPIClient(domain)
        await client.login(email, password)
        should_close = True

    try:
        # EAPI has no booklist endpoint — fall back to topic-based search
        logger.info(
            "Booklist browsing not available via EAPI. "
            "Falling back to search for topic: %s", topic
        )
        response = await client.search(
            message=topic,
            limit=25,
            page=page,
        )
        books = normalize_eapi_search_response(response)

        return {
            'booklist_id': booklist_id,
            'booklist_hash': booklist_hash,
            'topic': topic,
            'metadata': {
                'name': topic,
                'total_books': len(books),
                'description': (
                    f'Booklist browsing is not available via EAPI. '
                    f'Showing search results for "{topic}" instead. '
                    f'Use search_books for more targeted results.'
                ),
            },
            'books': books,
            'page': page,
            'degraded': True,
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
