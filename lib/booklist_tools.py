"""
Booklist exploration tools for curated collection discovery.

This module enables exploration of Z-Library's curated booklists,
where each book can appear in 11+ collections representing expert-curated
themes ranging from broad topics (Philosophy: 954 books) to specific subjects.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from urllib.parse import quote
from bs4 import BeautifulSoup
from bs4.element import Tag
import httpx
import sys
import os

logger = logging.getLogger(__name__)

# Add zlibrary directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary')
sys.path.insert(0, zlibrary_path)

from zlibrary import AsyncZlib


def construct_booklist_url(
    booklist_id: str,
    booklist_hash: str,
    topic: str,
    page: int = 1,
    mirror: str = "https://z-library.sk"
) -> str:
    """
    Construct a URL for accessing a Z-Library booklist.

    Z-Library booklists use the format:
    /booklist/{id}/{hash}/{topic}.html

    Args:
        booklist_id: Numeric ID of the booklist
        booklist_hash: Hash code for the booklist
        topic: URL-safe topic name
        page: Page number (default: 1)
        mirror: Z-Library mirror URL

    Returns:
        Constructed booklist URL

    Raises:
        ValueError: If ID or hash is empty/invalid
    """
    if not booklist_id or not booklist_id.strip():
        raise ValueError("Booklist ID cannot be empty")

    if not booklist_hash or not booklist_hash.strip():
        raise ValueError("Booklist hash cannot be empty")

    # Clean inputs
    booklist_id = booklist_id.strip()
    booklist_hash = booklist_hash.strip()

    # URL encode topic to handle special characters
    encoded_topic = quote(topic)

    # Construct base URL
    url = f"{mirror}/booklist/{booklist_id}/{booklist_hash}/{encoded_topic}.html"

    # Add pagination if not first page
    if page > 1:
        # Z-Library might use ?page=N or similar
        url += f"?page={page}"

    return url


def parse_booklist_page(html: str) -> List[Dict]:
    """
    Parse book entries from a booklist page.

    Extracts all books/articles from the booklist HTML, similar to
    search result parsing.

    Args:
        html: HTML content from booklist page

    Returns:
        List of book dictionaries with metadata
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'lxml')

    # Find all book cards in the booklist
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
            # Regular books - try both attributes and slot structure
            book_data['id'] = card.get('id', '')
            book_data['href'] = card.get('href', '')
            book_data['year'] = card.get('year', '')
            book_data['language'] = card.get('language', '')
            book_data['extension'] = card.get('extension', '')
            book_data['size'] = card.get('size', '')
            book_data['type'] = 'book'

            # Title - try attribute first, then slot
            title = card.get('title', '') or card.get('name', '')
            if not title:
                title_slot = card.find('div', attrs={'slot': 'title'})
                title = title_slot.get_text(strip=True) if title_slot else ''
            book_data['title'] = title

            # Authors - try attribute first, then slot
            authors = card.get('author', '') or card.get('authors', '')
            if not authors:
                author_slot = card.find('div', attrs={'slot': 'author'})
                authors = author_slot.get_text(strip=True) if author_slot else ''
            book_data['authors'] = authors

        results.append(book_data)

    return results


def get_booklist_metadata(html: str) -> Dict:
    """
    Extract metadata about the booklist from the page.

    Extracts:
    - Booklist name/title
    - Total book count
    - Description (if available)

    Args:
        html: HTML content from booklist page

    Returns:
        Dictionary with booklist metadata
    """
    if not html:
        return {}

    soup = BeautifulSoup(html, 'lxml')

    metadata = {}

    # Try to find booklist header/title
    # Common patterns:
    # <h1>Philosophy</h1>
    # <div class="bookListHeader"><h1>...</h1></div>

    # Look for h1 title
    title_elem = soup.find('h1')
    if title_elem:
        metadata['name'] = title_elem.get_text(strip=True)

    # Look for book count
    # Patterns: "954 books", "954 items", "954"
    # Could be in various places
    count_patterns = [
        soup.find(string=lambda string: string and 'book' in string.lower()),
        soup.find(string=lambda string: string and 'item' in string.lower()),
        soup.find(class_='count'),
        soup.find('span', class_='quantity')
    ]

    for pattern in count_patterns:
        if pattern:
            text = pattern.get_text() if hasattr(pattern, 'get_text') else str(pattern)
            # Extract numbers from text
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                metadata['total_books'] = int(numbers[0])
                break

    # Look for description
    desc_elem = soup.find('div', class_='description') or soup.find(class_='bookListDescription')
    if desc_elem:
        metadata['description'] = desc_elem.get_text(strip=True)

    return metadata


async def fetch_booklist(
    booklist_id: str,
    booklist_hash: str,
    topic: str,
    email: str,
    password: str,
    page: int = 1,
    mirror: str = ""
) -> Dict:
    """
    Fetch a complete booklist from Z-Library.

    Retrieves the specified booklist page, extracts all books,
    and returns both the books and metadata about the list.

    Args:
        booklist_id: Numeric ID of the booklist
        booklist_hash: Hash code for the booklist
        topic: Topic name (URL-safe)
        email: Z-Library account email (for authentication)
        password: Z-Library account password
        page: Page number (default: 1)
        mirror: Optional custom mirror URL

    Returns:
        Dictionary with structure:
        {
            'booklist_id': str,
            'booklist_hash': str,
            'topic': str,
            'metadata': Dict (name, total_books, description),
            'books': List[Dict],
            'page': int
        }

    Raises:
        Exception: If booklist not found (404) or network error

    Example:
        >>> result = await fetch_booklist(
        ...     booklist_id="409997",
        ...     booklist_hash="370858",
        ...     topic="philosophy",
        ...     email="user@example.com",
        ...     password="password"
        ... )
        >>> print(f"Fetched {len(result['books'])} books from {result['metadata']['name']}")
    """
    if not mirror:
        mirror = "https://z-library.sk"

    # Construct URL
    url = construct_booklist_url(booklist_id, booklist_hash, topic, page, mirror)

    # Need to authenticate with Z-Library first to get session cookies
    # Initialize zlibrary client to get auth cookies
    zlib = AsyncZlib()
    await zlib.login(email, password)

    # Perform a dummy search to ensure authentication
    # This establishes the session
    try:
        await zlib.search("init", count=1)
    except Exception as e:
        logger.warning("Initial search during authentication failed: %s", e)

    # Now fetch the booklist page with authenticated session
    # We need to use the same session/cookies from zlib client
    # For now, we'll use a simple HTTP client with authentication headers

    async with httpx.AsyncClient() as client:
        # Add user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Fetch the page
        response = await client.get(url, headers=headers, follow_redirects=True)

        if response.status_code == 404:
            raise Exception(f"Booklist not found: {booklist_id}/{booklist_hash}/{topic}")

        if response.status_code != 200:
            raise Exception(f"Failed to fetch booklist: HTTP {response.status_code}")

        html = response.text

    # Parse the results
    books = parse_booklist_page(html)
    metadata = get_booklist_metadata(html)

    return {
        'booklist_id': booklist_id,
        'booklist_hash': booklist_hash,
        'topic': topic,
        'metadata': metadata,
        'books': books,
        'page': page
    }


# Synchronous wrapper for use from python_bridge
def fetch_booklist_sync(*args, **kwargs) -> Dict:
    """
    Synchronous wrapper for fetch_booklist.

    Uses asyncio.run() to execute the async function.
    """
    return asyncio.run(fetch_booklist(*args, **kwargs))
