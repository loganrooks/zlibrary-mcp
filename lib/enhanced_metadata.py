"""
Enhanced metadata extraction for Z-Library books via EAPI.

Extracts the detail fields get_book can report from the EAPI
/book/{id}/{hash} endpoint: description, categories, ISBN, series, edition,
translator, rating and quality score.

Only fields the reply actually carries are returned; an absent or empty upstream
value leaves its key out. EAPI exposes no terms, booklists or IPFS ids, so this
module returns none (#256).
"""

import logging
from typing import Dict, List, Optional, Any
import sys
import os

# Add zlibrary source directory to path
zlibrary_path = os.path.join(os.path.dirname(__file__), "..", "zlibrary", "src")
sys.path.insert(0, zlibrary_path)

from zlibrary.eapi import EAPIClient, resolve_eapi_domain

logger = logging.getLogger(__name__)


def extract_metadata_from_eapi(
    book_info: dict, mirror_url: str = None
) -> Dict[str, Any]:
    """
    Extract enhanced metadata from an EAPI book info response.

    Args:
        book_info: Raw response from EAPIClient.get_book_info()
        mirror_url: Base URL for constructing full URLs (unused with EAPI)

    Returns:
        Dictionary holding only the detail fields present in the reply
    """
    if not book_info:
        return {}

    # The EAPI response contains the book data directly or under a "book" key
    book = book_info.get("book", book_info)

    try:
        metadata = {
            "description": book.get("description") or None,
            "rating": _extract_rating_from_eapi(book),
            "series": book.get("series") or None,
            "categories": _extract_categories_from_eapi(book) or None,
            "quality_score": _safe_float(book.get("qualityScore")),
            "edition": book.get("edition") or None,
            "translator": book.get("translator") or None,
        }

        # ISBNs
        isbn = book.get("isbn", "") or ""
        if isbn:
            cleaned = isbn.replace("-", "").strip()
            if len(cleaned) == 10:
                metadata["isbn_10"] = isbn
            else:
                # Thirteen digits, or an unrecognised length stored as ISBN-13
                metadata["isbn_13"] = isbn

        logger.info(
            "Extracted EAPI metadata for book: %s", book.get("title", "unknown")
        )
        return {key: value for key, value in metadata.items() if value is not None}

    except Exception as e:
        logger.error(f"Error extracting EAPI metadata: {e}")
        return {}


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

    Args:
        book_id: Z-Library book ID
        book_hash: Z-Library book hash
        email: Z-Library account email (used if no eapi_client provided)
        password: Z-Library account password (used if no eapi_client provided)
        mirror_url: Base URL (unused with EAPI)
        eapi_client: Optional pre-authenticated EAPIClient instance

    Returns:
        Dictionary holding only the detail fields present in the reply
    """
    client = eapi_client
    should_close = False
    if client is None:
        # Resolve a healthy EAPI domain before login: honours an explicit
        # ZLIBRARY_EAPI_DOMAIN override, otherwise probes the fallback list
        # via one-row POST /eapi/book/search (ISSUE-API-002: the old z-library.sk
        # default is DiamWall-walled).
        domain = await resolve_eapi_domain()
        client = EAPIClient(domain)
        await client.login(email, password)
        should_close = True

    try:
        book_info = await client.get_book_info(book_id, book_hash)
        return extract_metadata_from_eapi(book_info, mirror_url)
    finally:
        if should_close:
            await client.close()


def _extract_rating_from_eapi(book: dict) -> Optional[Dict[str, Any]]:
    """Extract rating info from EAPI book data."""
    rating_val = book.get("rating")
    if rating_val is None:
        return None
    try:
        rating = {"value": float(rating_val)}
        if book.get("ratingCount") is not None:
            rating["count"] = int(book["ratingCount"])
        return rating
    except (ValueError, TypeError):
        return None


def _extract_categories_from_eapi(book: dict) -> List[Dict[str, str]]:
    """Extract categories from EAPI book data."""
    categories = book.get("categories", [])
    if not categories:
        return []
    if isinstance(categories, list):
        return [{"name": str(c)} for c in categories if c]
    if isinstance(categories, str):
        return [{"name": categories}]
    return []


def _safe_float(value) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
