"""
Author search tools for advanced author-based discovery.

This module enables sophisticated author searches with support for
exact name matching, syntax variations, and filtering by publication
year, language, and file type. Uses EAPI for all Z-Library data access.
"""

import asyncio
from typing import Dict, List, Optional
import sys
import os
import re

# Add zlibrary source directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary', 'src')
sys.path.insert(0, zlibrary_path)

from zlibrary.eapi import EAPIClient, normalize_eapi_search_response


def validate_author_name(author: str) -> bool:
    """
    Validate author name format.

    Accepts:
    - Simple names: "Plato"
    - Full names: "Georg Wilhelm Friedrich Hegel"
    - Comma format: "Hegel, Georg"
    - Names with numbers: "Louis XVI"
    - Names with special chars: "Jean-Paul Sartre", "O'Brien"

    Args:
        author: Author name to validate

    Returns:
        True if valid, False otherwise
    """
    if not author or not author.strip():
        return False

    # Allow letters, spaces, hyphens, apostrophes, commas, and numbers
    pattern = r'^[a-zA-Z\u00C0-\u00FF0-9\s\-\',\.]+$'
    return bool(re.match(pattern, author))


def format_author_query(author: str, exact: bool = False) -> str:
    """
    Format author name for Z-Library search query.

    Handles various name formats:
    - "Hegel" -> "Hegel"
    - "Georg Wilhelm Friedrich Hegel" -> "Georg Wilhelm Friedrich Hegel"
    - "Hegel, Georg Wilhelm Friedrich" -> "Hegel Georg Wilhelm Friedrich"

    Args:
        author: Author name to format
        exact: If True, may add exact match indicators (quotes)

    Returns:
        Formatted query string

    Raises:
        ValueError: If author name is empty or invalid
    """
    if not author or not author.strip():
        raise ValueError("Author name cannot be empty")

    cleaned = author.strip()

    # If it's in "Lastname, Firstname" format, reorder
    if ',' in cleaned:
        parts = [p.strip() for p in cleaned.split(',', 1)]
        cleaned = ' '.join(parts)

    if exact:
        cleaned = f'"{cleaned}"'

    return cleaned


async def search_by_author(
    author: str,
    email: str,
    password: str,
    exact: bool = False,
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
    Search for books by author using EAPI.

    Args:
        author: Author name (supports various formats)
        email: Z-Library account email
        password: Z-Library account password
        exact: If True, search for exact author name match
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
            'author': str,
            'books': List[Dict],
            'total_results': int
        }

    Raises:
        ValueError: If author name is invalid
    """
    if not validate_author_name(author):
        raise ValueError(f"Invalid author name: {author}")

    query = format_author_query(author, exact=exact)

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
        lang_list = None
        if languages:
            lang_list = languages.split(',') if isinstance(languages, str) else languages
        ext_list = None
        if extensions:
            ext_list = extensions.split(',') if isinstance(extensions, str) else extensions

        response = await client.search(
            message=query,
            limit=limit,
            page=page,
            year_from=year_from,
            year_to=year_to,
            languages=lang_list,
            extensions=ext_list,
            exact=exact,
        )

        books = normalize_eapi_search_response(response)

        return {
            'author': author,
            'books': books,
            'total_results': len(books),
        }
    finally:
        if should_close:
            await client.close()


# Synchronous wrapper for use from python_bridge
def search_by_author_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for search_by_author.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(search_by_author(*args, **kwargs))
