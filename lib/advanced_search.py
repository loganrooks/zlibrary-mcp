"""
Advanced search functionality with fuzzy match detection and separation.

This module extends the basic search functionality to detect and separate
exact matches from "nearest matches" (fuzzy results) in Z-Library search results.

Z-Library uses a <div class="fuzzyMatchesLine"> element to separate exact matches
from approximate/fuzzy matches in search results.
"""

import asyncio
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup
from bs4.element import Tag
import sys
import os

# Add zlibrary directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary')
sys.path.insert(0, zlibrary_path)

from zlibrary import AsyncZlib


def detect_fuzzy_matches_line(html: str) -> bool:
    """
    Detect if search results contain a fuzzy matches separator line.

    Z-Library uses <div class="fuzzyMatchesLine"> to separate exact matches
    from approximate/fuzzy matches.

    Args:
        html: HTML content from search results page

    Returns:
        True if fuzzy matches line is present, False otherwise
    """
    if not html:
        return False

    soup = BeautifulSoup(html, 'html.parser')
    fuzzy_line = soup.find('div', class_='fuzzyMatchesLine')
    return fuzzy_line is not None


def _parse_bookcard(card) -> Dict:
    """
    Parse a single z-bookcard element into a dictionary.

    Handles both regular books (with attributes) and articles (with slot-based structure).

    Args:
        card: BeautifulSoup element representing a z-bookcard

    Returns:
        Dictionary with book metadata
    """
    result = {}

    # Check if this is an article (uses slot-based structure)
    card_type = card.get('type', '')
    if card_type == 'article':
        # Articles use <div slot="title"> structure
        title_slot = card.find('div', attrs={'slot': 'title'})
        author_slot = card.find('div', attrs={'slot': 'author'})

        result['title'] = title_slot.get_text(strip=True) if title_slot else 'N/A'
        result['authors'] = author_slot.get_text(strip=True) if author_slot else 'N/A'
        result['href'] = card.get('href', '')
        result['type'] = 'article'
    else:
        # Regular books use attributes
        result['id'] = card.get('id', '')
        result['title'] = card.get('title', '')
        result['authors'] = card.get('author', '')
        result['year'] = card.get('year', '')
        result['language'] = card.get('language', '')
        result['extension'] = card.get('extension', '')
        result['size'] = card.get('size', '')
        result['href'] = card.get('href', '')
        result['type'] = 'book'

    return result


def separate_exact_and_fuzzy_results(html: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Separate search results into exact matches and fuzzy matches.

    Results appearing before the fuzzyMatchesLine are exact matches.
    Results appearing after are fuzzy/approximate matches.

    Args:
        html: HTML content from search results page

    Returns:
        Tuple of (exact_matches, fuzzy_matches) where each is a list of book dictionaries
    """
    if not html:
        return [], []

    soup = BeautifulSoup(html, 'html.parser')

    # Find the fuzzy line divider
    fuzzy_line = soup.find('div', class_='fuzzyMatchesLine')

    if not fuzzy_line:
        # No fuzzy line means all results are exact matches
        all_cards = soup.find_all('z-bookcard')
        exact_matches = [_parse_bookcard(card) for card in all_cards]
        return exact_matches, []

    # Get all elements in order to determine position
    # Find the parent container that holds both cards and the fuzzy line
    container = fuzzy_line.find_parent()
    if not container:
        # Fallback: treat all as exact
        all_cards = soup.find_all('z-bookcard')
        exact_matches = [_parse_bookcard(card) for card in all_cards]
        return exact_matches, []

    # Get all child elements in order
    all_elements = list(container.children)

    # Find the index of fuzzy_line
    fuzzy_idx = None
    for idx, elem in enumerate(all_elements):
        if hasattr(elem, 'get') and elem.get('class') and 'fuzzyMatchesLine' in elem.get('class', []):
            fuzzy_idx = idx
            break

    if fuzzy_idx is None:
        # Fuzzy line not found in children, treat all as exact
        all_cards = soup.find_all('z-bookcard')
        exact_matches = [_parse_bookcard(card) for card in all_cards]
        return exact_matches, []

    # Separate results based on position
    exact_matches = []
    fuzzy_matches = []

    for idx, elem in enumerate(all_elements):
        # Skip NavigableString objects (text nodes) - only process Tag elements
        if not isinstance(elem, Tag):
            continue

        # Look for z-bookcard elements
        cards = elem.find_all('z-bookcard')
        for card in cards:
            if idx < fuzzy_idx:
                exact_matches.append(_parse_bookcard(card))
            else:
                fuzzy_matches.append(_parse_bookcard(card))

    return exact_matches, fuzzy_matches


async def search_books_advanced(
    query: str,
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
    Advanced search with exact and fuzzy match separation.

    Performs a Z-Library search and separates results into exact matches
    and fuzzy/approximate matches based on the fuzzyMatchesLine divider.

    Args:
        query: Search query string
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
            'has_fuzzy_matches': bool,
            'exact_matches': List[Dict],
            'fuzzy_matches': List[Dict],
            'total_results': int,
            'query': str
        }
    """
    # Initialize zlibrary client
    if mirror:
        zlib = AsyncZlib(email=email, password=password, remix_userkey='', mirror=mirror)
    else:
        zlib = AsyncZlib(email=email, password=password, remix_userkey='')

    # Perform search
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

    # Execute search
    search_result = await zlib.search(query, **search_kwargs)

    # Handle both tuple and non-tuple returns
    if isinstance(search_result, tuple):
        html, total_count = search_result
    else:
        # If it's a paginator object, we need to extract differently
        html = str(search_result)
        total_count = 0

    # Detect fuzzy matches
    has_fuzzy = detect_fuzzy_matches_line(html)

    # Separate results
    exact_matches, fuzzy_matches = separate_exact_and_fuzzy_results(html)

    return {
        'has_fuzzy_matches': has_fuzzy,
        'exact_matches': exact_matches,
        'fuzzy_matches': fuzzy_matches,
        'total_results': total_count,
        'query': query
    }


# Helper function for synchronous usage from python_bridge
def search_books_advanced_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for search_books_advanced.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(search_books_advanced(*args, **kwargs))
