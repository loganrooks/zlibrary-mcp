"""
Author search tools for advanced author-based discovery.

This module enables sophisticated author searches with support for
exact name matching, syntax variations, and filtering by publication
year, language, and file type.
"""

import asyncio
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from bs4.element import Tag
import sys
import os
import re

# Add zlibrary directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary')
sys.path.insert(0, zlibrary_path)

from zlibrary import AsyncZlib


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

    # Check if it's just whitespace
    if not author.strip():
        return False

    # Allow letters, spaces, hyphens, apostrophes, commas, and numbers
    # This covers most international names
    pattern = r'^[a-zA-ZÀ-ÿ0-9\s\-\',\.]+$'
    return bool(re.match(pattern, author))


def format_author_query(author: str, exact: bool = False) -> str:
    """
    Format author name for Z-Library search query.

    Handles various name formats:
    - "Hegel" → "Hegel"
    - "Georg Wilhelm Friedrich Hegel" → "Georg Wilhelm Friedrich Hegel"
    - "Hegel, Georg Wilhelm Friedrich" → "Hegel Georg Wilhelm Friedrich"

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

    # Clean the author name
    cleaned = author.strip()

    # If it's in "Lastname, Firstname" format, reorder
    if ',' in cleaned:
        parts = [p.strip() for p in cleaned.split(',', 1)]
        cleaned = ' '.join(parts)

    # For exact matching, we might want to add quotes
    # but this depends on Z-Library's search behavior
    if exact:
        # Z-Library may support quoted searches for exact matching
        # Testing would confirm the exact syntax
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
    limit: int = 25
) -> Dict:
    """
    Search for books by author with advanced options.

    Supports various author name formats and provides filtering by
    year, language, and file type.

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

    Returns:
        Dictionary with structure:
        {
            'author': str,
            'books': List[Dict],
            'total_results': int
        }

    Raises:
        ValueError: If author name is invalid

    Example:
        >>> result = await search_by_author(
        ...     author="Hegel, Georg Wilhelm Friedrich",
        ...     exact=True,
        ...     email="user@example.com",
        ...     password="password",
        ...     year_from=1800,
        ...     year_to=1850
        ... )
        >>> print(f"Found {len(result['books'])} books by {result['author']}")
    """
    # Validate author name
    if not validate_author_name(author):
        raise ValueError(f"Invalid author name: {author}")

    # Format the query
    query = format_author_query(author, exact=exact)

    # Initialize zlibrary client
    zlib = AsyncZlib()
    await zlib.login(email, password)

    # Build search parameters matching AsyncZlib.search() signature
    search_kwargs = {
        'q': query,
        'count': limit,
        'exact': exact
    }

    if year_from is not None:
        search_kwargs['from_year'] = year_from
    if year_to is not None:
        search_kwargs['to_year'] = year_to
    if languages:
        search_kwargs['lang'] = languages.split(',') if isinstance(languages, str) else languages
    if extensions:
        search_kwargs['extensions'] = extensions.split(',') if isinstance(extensions, str) else extensions

    # Execute search
    search_result = await zlib.search(**search_kwargs)

    # Handle both tuple and non-tuple returns (AsyncZlib.search returns Paginator or tuple)
    if isinstance(search_result, tuple):
        paginator, constructed_url = search_result
    else:
        paginator = search_result
        constructed_url = f"Search for author: {author}"

    # Get the first page of results (paginator.next() returns list of book dicts)
    books = await paginator.next()

    return {
        'author': author,
        'books': books,
        'total_results': len(books)  # For now, return books in this page
    }


def _parse_author_search_results(html: str) -> List[Dict]:
    """
    Parse book results from author search HTML.

    Similar to term_tools parsing but specific to author searches.

    Args:
        html: HTML content from search results page

    Returns:
        List of book dictionaries with metadata
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'lxml')

    # Find all book cards
    all_cards = soup.find_all('z-bookcard')

    if not all_cards:
        return []

    results = []

    for card in all_cards:
        book_data = {}

        # Check if this is an article (uses slot-based structure)
        card_type = card.get('type', '')
        if card_type == 'article':
            # Articles use <div slot="title"> structure
            title_slot = card.find('div', attrs={'slot': 'title'})
            author_slot = card.find('div', attrs={'slot': 'author'})

            book_data['title'] = title_slot.get_text(strip=True) if title_slot else 'N/A'
            book_data['authors'] = author_slot.get_text(strip=True) if author_slot else 'N/A'
            book_data['href'] = card.get('href', '')
            book_data['type'] = 'article'
        else:
            # Regular books use attributes
            book_data['id'] = card.get('id', '')
            book_data['title'] = card.get('title', '')
            book_data['authors'] = card.get('author', '')
            book_data['year'] = card.get('year', '')
            book_data['language'] = card.get('language', '')
            book_data['extension'] = card.get('extension', '')
            book_data['size'] = card.get('size', '')
            book_data['href'] = card.get('href', '')
            book_data['type'] = 'book'

        results.append(book_data)

    return results


# Synchronous wrapper for use from python_bridge
def search_by_author_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for search_by_author.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(search_by_author(*args, **kwargs))
