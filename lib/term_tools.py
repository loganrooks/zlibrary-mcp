"""
Term exploration tools for Z-Library conceptual navigation.

This module enables discovery based on conceptual terms, allowing
researchers to navigate by philosophical/technical concepts rather
than just keywords. Uses EAPI for all Z-Library data access.
"""

import asyncio
from typing import Dict, List, Optional
import sys
import os

# Add zlibrary source directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary', 'src')
sys.path.insert(0, zlibrary_path)

from zlibrary.eapi import EAPIClient, normalize_eapi_search_response


async def search_by_term(
    term: str,
    email: str,
    password: str,
    mirror: str = "",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    languages: Optional[str] = None,
    extensions: Optional[str] = None,
    page: int = 1,
    limit: int = 25,
    eapi_client: Optional[EAPIClient] = None,
) -> Dict:
    """
    Search for books by conceptual term using EAPI.

    Args:
        term: Conceptual term to search for (e.g., "dialectic", "reflection")
        email: Z-Library account email
        password: Z-Library account password
        mirror: Optional custom mirror URL
        year_from: Optional filter for publication year (start)
        year_to: Optional filter for publication year (end)
        languages: Optional comma-separated language codes
        extensions: Optional comma-separated file extensions
        page: Page number for pagination (default: 1)
        limit: Results per page (default: 25)
        eapi_client: Optional pre-authenticated EAPIClient instance

    Returns:
        Dictionary with structure:
        {
            'term': str,
            'books': List[Dict],
            'total_results': int
        }
    """
    if not term or not term.strip():
        raise ValueError("Term cannot be empty")

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
        # Build search kwargs
        lang_list = None
        if languages:
            lang_list = languages.split(',') if isinstance(languages, str) else languages
        ext_list = None
        if extensions:
            ext_list = extensions.split(',') if isinstance(extensions, str) else extensions

        response = await client.search(
            message=term,
            limit=limit,
            page=page,
            year_from=year_from,
            year_to=year_to,
            languages=lang_list,
            extensions=ext_list,
            exact=True,
        )

        books = normalize_eapi_search_response(response)

        return {
            'term': term,
            'books': books,
            'total_results': len(books),
        }
    finally:
        if should_close:
            await client.close()


# Synchronous wrapper for use from python_bridge
def search_by_term_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for search_by_term.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(search_by_term(*args, **kwargs))
