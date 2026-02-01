"""
Enhanced metadata extraction for Z-Library books via EAPI.

Extracts comprehensive metadata from the EAPI /book/{id}/{hash} endpoint
including: description, categories, ISBNs, series, rating, publisher, pages.

Some fields previously available via HTML scraping (terms, booklists, IPFS CIDs)
are not available through the EAPI and are returned as empty/None.

Implementation migrated from HTML scraping to EAPI JSON access.
"""

import logging
from typing import Dict, List, Optional, Any
import sys
import os

# Add zlibrary source directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary', 'src')
sys.path.insert(0, zlibrary_path)

from zlibrary.eapi import EAPIClient, normalize_eapi_book

logger = logging.getLogger(__name__)


def extract_metadata_from_eapi(book_info: dict, mirror_url: str = None) -> Dict[str, Any]:
    """
    Extract enhanced metadata from an EAPI book info response.

    Maps EAPI JSON fields to the existing metadata return format.

    Args:
        book_info: Raw response from EAPIClient.get_book_info()
        mirror_url: Base URL for constructing full URLs (unused with EAPI)

    Returns:
        Dictionary with comprehensive metadata matching the legacy format
    """
    if not book_info:
        return _empty_metadata()

    # The EAPI response contains the book data directly or under a "book" key
    book = book_info.get("book", book_info)

    try:
        metadata = {
            # Tier 1: Essential
            'description': book.get('description') or None,
            'terms': [],  # Not available via EAPI
            'booklists': [],  # Not available via EAPI

            # Tier 2: Important
            'rating': _extract_rating_from_eapi(book),
            'ipfs_cids': [],  # Not available via EAPI
            'series': book.get('series') or None,
            'categories': _extract_categories_from_eapi(book),

            # Tier 3: Optional
            'quality_score': _safe_float(book.get('qualityScore')),
        }

        # ISBNs
        isbn = book.get('isbn', '') or ''
        metadata['isbn_10'] = None
        metadata['isbn_13'] = None
        if isbn:
            cleaned = isbn.replace('-', '').strip()
            if len(cleaned) == 13:
                metadata['isbn_13'] = isbn
            elif len(cleaned) == 10:
                metadata['isbn_10'] = isbn
            else:
                # Store in isbn_13 as default
                metadata['isbn_13'] = isbn

        logger.info("Extracted EAPI metadata for book: %s", book.get('title', 'unknown'))
        return metadata

    except Exception as e:
        logger.error(f"Error extracting EAPI metadata: {e}")
        return _empty_metadata()


async def get_enhanced_metadata(
    book_id: int,
    book_hash: str,
    email: str = "",
    password: str = "",
    mirror_url: str = None,
    eapi_client: Optional[EAPIClient] = None,
) -> Dict[str, Any]:
    """
    Fetch and extract enhanced metadata for a book via EAPI.

    This is the main entry point, replacing the old HTML-based
    extract_complete_metadata() function.

    Args:
        book_id: Z-Library book ID
        book_hash: Z-Library book hash
        email: Z-Library account email (used if no eapi_client provided)
        password: Z-Library account password (used if no eapi_client provided)
        mirror_url: Base URL (unused with EAPI)
        eapi_client: Optional pre-authenticated EAPIClient instance

    Returns:
        Dictionary with comprehensive metadata
    """
    client = eapi_client
    should_close = False
    if client is None:
        from zlibrary.util import discover_eapi_domain
        domain = await discover_eapi_domain()
        client = EAPIClient(domain)
        await client.login(email, password)
        should_close = True

    try:
        book_info = await client.get_book_info(book_id, book_hash)
        return extract_metadata_from_eapi(book_info, mirror_url)
    finally:
        if should_close:
            await client.close()


# Legacy compatibility alias
def extract_complete_metadata(html: str = None, mirror_url: str = None, **kwargs) -> Dict[str, Any]:
    """
    Legacy compatibility wrapper.

    Previously parsed HTML; now returns empty metadata since HTML parsing
    is removed. Use get_enhanced_metadata() with EAPI client instead.
    """
    logger.warning(
        "extract_complete_metadata() is deprecated. Use get_enhanced_metadata() with EAPI client."
    )
    return _empty_metadata()


# Keep extract_description as a no-op for backward compat with python_bridge imports
def extract_description(html: str = None) -> Optional[str]:
    """Deprecated: Use get_enhanced_metadata() via EAPI instead."""
    return None


def _extract_rating_from_eapi(book: dict) -> Optional[Dict[str, Any]]:
    """Extract rating info from EAPI book data."""
    rating_val = book.get('rating')
    if rating_val is None:
        return None
    try:
        return {
            'value': float(rating_val),
            'count': int(book.get('ratingCount', 0)),
        }
    except (ValueError, TypeError):
        return None


def _extract_categories_from_eapi(book: dict) -> List[Dict[str, str]]:
    """Extract categories from EAPI book data."""
    categories = book.get('categories', [])
    if not categories:
        return []
    if isinstance(categories, list):
        return [{'name': str(c), 'url': ''} for c in categories]
    if isinstance(categories, str):
        return [{'name': categories, 'url': ''}]
    return []


def _safe_float(value) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _empty_metadata() -> Dict[str, Any]:
    """Return empty metadata structure with default values."""
    return {
        'description': None,
        'terms': [],
        'booklists': [],
        'rating': None,
        'ipfs_cids': [],
        'series': None,
        'categories': [],
        'isbn_10': None,
        'isbn_13': None,
        'quality_score': None,
    }
