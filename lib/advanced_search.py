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

# DEPRECATED: AsyncZlib removed in 08-02. search_books_advanced() no longer functional.
# HTML-based fuzzy match detection requires web scraping which EAPI does not support.
# The helper functions (detect_fuzzy_matches_line, separate_exact_and_fuzzy_results)
# remain available for any future HTML parsing needs.


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

    soup = BeautifulSoup(html, "lxml")
    fuzzy_line = soup.find("div", class_="fuzzyMatchesLine")
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
    card_type = card.get("type", "")
    if card_type == "article":
        # Articles use <div slot="title"> structure
        title_slot = card.find("div", attrs={"slot": "title"})
        author_slot = card.find("div", attrs={"slot": "author"})

        result["title"] = title_slot.get_text(strip=True) if title_slot else "N/A"
        result["authors"] = author_slot.get_text(strip=True) if author_slot else "N/A"
        result["href"] = card.get("href", "")
        result["type"] = "article"
    else:
        # Regular books - try both attributes and slot structure
        result["id"] = card.get("id", "")
        result["href"] = card.get("href", "")
        result["year"] = card.get("year", "")
        result["language"] = card.get("language", "")
        result["extension"] = card.get("extension", "")
        result["size"] = card.get("size", "")
        result["type"] = "book"

        # Title - try attribute first, then slot
        title = card.get("title", "") or card.get("name", "")
        if not title:
            title_slot = card.find("div", attrs={"slot": "title"})
            title = title_slot.get_text(strip=True) if title_slot else ""
        result["title"] = title

        # Authors - try attribute first, then slot
        authors = card.get("author", "") or card.get("authors", "")
        if not authors:
            author_slot = card.find("div", attrs={"slot": "author"})
            authors = author_slot.get_text(strip=True) if author_slot else ""
        result["authors"] = authors

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

    soup = BeautifulSoup(html, "lxml")

    # Find the fuzzy line divider
    fuzzy_line = soup.find("div", class_="fuzzyMatchesLine")

    if not fuzzy_line:
        # No fuzzy line means all results are exact matches
        all_cards = soup.find_all("z-bookcard")
        exact_matches = [_parse_bookcard(card) for card in all_cards]
        return exact_matches, []

    # Get all elements in order to determine position
    # Find the parent container that holds both cards and the fuzzy line
    container = fuzzy_line.find_parent()
    if not container:
        # Fallback: treat all as exact
        all_cards = soup.find_all("z-bookcard")
        exact_matches = [_parse_bookcard(card) for card in all_cards]
        return exact_matches, []

    # Get all child elements in order
    all_elements = list(container.children)

    # Find the index of fuzzy_line
    fuzzy_idx = None
    for idx, elem in enumerate(all_elements):
        if (
            hasattr(elem, "get")
            and elem.get("class")
            and "fuzzyMatchesLine" in elem.get("class", [])
        ):
            fuzzy_idx = idx
            break

    if fuzzy_idx is None:
        # Fuzzy line not found in children, treat all as exact
        all_cards = soup.find_all("z-bookcard")
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
        cards = elem.find_all("z-bookcard")
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
    limit: int = 25,
) -> Dict:
    """
    DEPRECATED: Advanced search with exact and fuzzy match separation.

    This function previously used AsyncZlib for HTML scraping to detect
    fuzzy match separators. AsyncZlib was removed in plan 08-02.
    EAPI does not provide fuzzy match separation.

    Raises:
        NotImplementedError: Always. Use regular EAPI search instead.
    """
    raise NotImplementedError(
        "search_books_advanced requires HTML scraping (AsyncZlib), which was removed. "
        "Use EAPI search via python_bridge.search() instead."
    )


# DEPRECATED: Helper function for synchronous usage from python_bridge
def search_books_advanced_sync(*args, **kwargs) -> Dict:
    """DEPRECATED: Synchronous wrapper for search_books_advanced."""
    return asyncio.run(search_books_advanced(*args, **kwargs))
