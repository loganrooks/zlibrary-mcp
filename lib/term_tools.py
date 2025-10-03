"""
Term exploration tools for Z-Library conceptual navigation.

This module enables discovery based on the 60+ conceptual terms
extracted from each book, allowing researchers to navigate by
philosophical/technical concepts rather than just keywords.
"""

import asyncio
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from bs4.element import Tag
import sys
import os

# Add zlibrary directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary')
sys.path.insert(0, zlibrary_path)

from zlibrary import AsyncZlib


def construct_term_search_url(term: str, mirror: str = "https://z-library.sk") -> str:
    """
    Construct a URL for searching by term on Z-Library.

    Z-Library uses /s/{term}?e=1 format for term searches where e=1
    indicates exact term matching.

    Args:
        term: The conceptual term to search for
        mirror: Z-Library mirror URL

    Returns:
        Constructed search URL

    Raises:
        ValueError: If term is empty or invalid
    """
    if not term or not term.strip():
        raise ValueError("Term cannot be empty")

    # Clean and encode the term
    cleaned_term = term.strip()
    encoded_term = quote_plus(cleaned_term)

    # Construct URL with exact match parameter
    url = f"{mirror}/s/{encoded_term}?e=1"

    return url


def parse_term_search_results(html: str) -> List[Dict]:
    """
    Parse book results from term search HTML.

    Handles both regular books and articles, similar to advanced_search
    parsing logic.

    Args:
        html: HTML content from term search results page

    Returns:
        List of book dictionaries with metadata
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')

    # Find all book cards (similar to advanced_search pattern)
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
    limit: int = 25
) -> Dict:
    """
    Search for books by conceptual term.

    Enables navigation through Z-Library's conceptual index, allowing
    discovery based on philosophical/technical terms extracted from books.

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

    Returns:
        Dictionary with structure:
        {
            'term': str,
            'books': List[Dict],
            'total_results': int
        }

    Example:
        >>> result = await search_by_term(
        ...     term="dialectic",
        ...     email="user@example.com",
        ...     password="password",
        ...     languages="English",
        ...     year_from=2000
        ... )
        >>> print(f"Found {len(result['books'])} books on {result['term']}")
    """
    # Initialize zlibrary client
    if mirror:
        zlib = AsyncZlib(email=email, password=password, remix_userkey='', mirror=mirror)
    else:
        zlib = AsyncZlib(email=email, password=password, remix_userkey='')

    # Build search parameters
    search_kwargs = {
        'page': page,
        'count': limit
    }

    if year_from is not None:
        search_kwargs['yearFrom'] = year_from
    if year_to is not None:
        search_kwargs['yearTo'] = year_to
    if languages:
        search_kwargs['languages'] = languages
    if extensions:
        search_kwargs['extensions'] = extensions

    # Execute search using the term as query
    # Z-Library's term search is essentially a specialized text search
    search_result = await zlib.search(term, **search_kwargs)

    # Handle both tuple and non-tuple returns
    if isinstance(search_result, tuple):
        html, total_count = search_result
    else:
        html = str(search_result)
        total_count = 0

    # Parse results
    books = parse_term_search_results(html)

    return {
        'term': term,
        'books': books,
        'total_results': total_count
    }


# Synchronous wrapper for use from python_bridge
def search_by_term_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for search_by_term.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(search_by_term(*args, **kwargs))
