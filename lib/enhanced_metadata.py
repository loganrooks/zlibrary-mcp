"""
Enhanced metadata extraction for Z-Library book detail pages.

Extracts comprehensive metadata including:
- Description (816+ chars)
- Terms (60+ conceptual keywords)
- Booklists (11+ curated collections)
- Rating (user ratings and counts)
- IPFS CIDs (2 formats)
- Series, Categories, ISBNs
- Quality scores

Implementation follows TDD approach with tests in __tests__/python/test_enhanced_metadata.py
"""

import re
import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_description(html: str) -> Optional[str]:
    """
    Extract book description from JavaScript embedded in HTML.

    The description is typically found in a schema.org JSON-LD script tag
    or in a JavaScript variable assignment.

    Args:
        html: Raw HTML content of book detail page

    Returns:
        Description text (may be 500-1000 chars) or None if not found
    """
    if not html:
        return None

    try:
        # Method 1: Extract from schema.org JSON-LD
        schema_match = re.search(r'"description"\s*:\s*"([^"]+(?:\\.[^"]*)*)"', html)
        if schema_match:
            description = schema_match.group(1)
            # Decode escaped characters
            description = description.replace('\\"', '"')
            description = description.replace('\\n', '\n')
            description = description.replace('\\r', '')
            return description.strip()

        # Method 2: Extract from JavaScript variable (fallback)
        js_var_match = re.search(r'description\s*[:=]\s*["\']([^"\']+)["\']', html)
        if js_var_match:
            return js_var_match.group(1).strip()

        return None

    except Exception as e:
        logger.error(f"Error extracting description: {e}")
        return None


def extract_terms(html: str) -> List[str]:
    """
    Extract conceptual terms from book detail page.

    Terms are linked throughout the page with URLs like /terms/{term}

    Args:
        html: Raw HTML content of book detail page

    Returns:
        Sorted list of unique terms (may be 50-60+ terms for rich metadata books)
    """
    if not html:
        return []

    try:
        soup = BeautifulSoup(html, 'lxml')

        # Find all links to /terms/
        term_links = soup.find_all('a', href=re.compile(r'^/terms/'))

        # Extract term from URL
        terms = set()
        for link in term_links:
            href = link.get('href', '')
            if href.startswith('/terms/'):
                # Extract term name from URL
                term = href.split('/terms/')[-1]
                # Clean up any trailing slashes or query params
                term = term.split('?')[0].strip('/')
                if term:
                    terms.add(term)

        # Return sorted list
        return sorted(list(terms))

    except Exception as e:
        logger.error(f"Error extracting terms: {e}")
        return []


def extract_booklists(soup: BeautifulSoup, mirror_url: str = None) -> List[Dict[str, Any]]:
    """
    Extract booklist memberships from z-booklist elements.

    Each booklist contains:
    - id: List ID
    - hash: List hash for URL
    - topic: Display name
    - quantity: Number of books in list
    - url: Full URL to booklist page

    Args:
        soup: BeautifulSoup parsed HTML
        mirror_url: Base URL for constructing full URLs (e.g., "https://z-library.sk")

    Returns:
        List of booklist dictionaries (may be 10-15 for popular books)
    """
    if not soup:
        return []

    try:
        booklists = []

        # Find all z-booklist custom elements
        booklist_elements = soup.find_all('z-booklist')

        for element in booklist_elements:
            try:
                booklist = {
                    'id': element.get('id', ''),
                    'hash': '',  # Will extract from href
                    'topic': element.get('topic', ''),
                    'quantity': int(element.get('quantity', 0)),
                    'url': ''
                }

                # Extract href
                href = element.get('href', '')
                if href:
                    # Extract hash from href (format: /booklist/{id}/{hash}/{name}.html)
                    parts = href.split('/')
                    if len(parts) >= 4:
                        booklist['hash'] = parts[3]

                    # Construct full URL
                    if mirror_url:
                        booklist['url'] = f"{mirror_url.rstrip('/')}{href}"
                    else:
                        booklist['url'] = href

                # Only add if we have essential data
                if booklist['id'] and booklist['topic']:
                    booklists.append(booklist)

            except Exception as e:
                logger.warning(f"Error parsing booklist element: {e}")
                continue

        return booklists

    except Exception as e:
        logger.error(f"Error extracting booklists: {e}")
        return []


def extract_rating(html: str) -> Optional[Dict[str, Any]]:
    """
    Extract user rating and rating count from book metadata.

    Rating is typically found in schema.org JSON-LD aggregateRating.

    Args:
        html: Raw HTML content of book detail page

    Returns:
        Dictionary with 'value' (float 0.0-5.0) and 'count' (int) or None
    """
    if not html:
        return None

    try:
        rating = {}

        # Extract from schema.org JSON-LD
        rating_value_match = re.search(r'"ratingValue"\s*:\s*"([^"]+)"', html)
        rating_count_match = re.search(r'"ratingCount"\s*:\s*(\d+)', html)

        if rating_value_match:
            rating['value'] = float(rating_value_match.group(1))

        if rating_count_match:
            rating['count'] = int(rating_count_match.group(1))

        # Return None if no rating data found
        if not rating:
            return None

        return rating

    except Exception as e:
        logger.error(f"Error extracting rating: {e}")
        return None


def extract_ipfs_cids(soup: BeautifulSoup) -> List[str]:
    """
    Extract IPFS CIDs from book detail page.

    Z-Library provides IPFS access with two CID formats:
    - CIDv0 (starts with Qm...)
    - CIDv1 (starts with bafy...)

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        List of IPFS CID strings (typically 2 CIDs)
    """
    if not soup:
        return []

    try:
        cids = []

        # Find all elements with data-copy attribute (copy-to-clipboard functionality)
        copy_elements = soup.find_all(attrs={'data-copy': True})

        for element in copy_elements:
            cid = element.get('data-copy', '')
            # Validate it looks like an IPFS CID
            if cid and (cid.startswith('Qm') or cid.startswith('bafy')):
                if len(cid) > 30:  # CIDs are long strings
                    cids.append(cid)

        # Also check for IPFS links
        ipfs_links = soup.find_all('a', href=re.compile(r'ipfs://|/ipfs/'))
        for link in ipfs_links:
            href = link.get('href', '')
            # Extract CID from URL
            if 'ipfs://' in href:
                cid = href.split('ipfs://')[-1].split('/')[0]
            elif '/ipfs/' in href:
                cid = href.split('/ipfs/')[-1].split('/')[0]
            else:
                continue

            if cid and (cid.startswith('Qm') or cid.startswith('bafy')):
                cids.append(cid)

        # Remove duplicates and return
        return list(dict.fromkeys(cids))  # Preserves order

    except Exception as e:
        logger.error(f"Error extracting IPFS CIDs: {e}")
        return []


def extract_quality_score(html: str) -> Optional[float]:
    """
    Extract file quality score from book metadata.

    Quality score is typically found in JavaScript variables or JSON data.

    Args:
        html: Raw HTML content of book detail page

    Returns:
        Quality score as float (0.0-5.0) or None
    """
    if not html:
        return None

    try:
        # Look for quality in JavaScript
        quality_match = re.search(r'"quality"\s*:\s*"([^"]+)"', html)
        if quality_match:
            return float(quality_match.group(1))

        # Alternative: look for quality property
        quality_prop_match = re.search(r'quality\s*[:=]\s*([0-9.]+)', html)
        if quality_prop_match:
            return float(quality_prop_match.group(1))

        return None

    except Exception as e:
        logger.error(f"Error extracting quality score: {e}")
        return None


def extract_series(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract series information from book properties.

    Series is typically in a bookProperty div with label "Series:".

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        Series name as string or None
    """
    if not soup:
        return None

    try:
        # Look for series in bookProperty divs
        property_divs = soup.find_all('div', class_=re.compile(r'bookProperty'))

        for prop_div in property_divs:
            label_div = prop_div.find('div', class_='property_label')
            if label_div and 'Series' in label_div.get_text():
                value_div = prop_div.find(['div', 'span'], class_='property_value')
                if value_div:
                    return value_div.get_text().strip()

        return None

    except Exception as e:
        logger.error(f"Error extracting series: {e}")
        return None


def extract_categories(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract category classification from book detail page.

    Categories are hierarchical and link to category browse pages.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        List of category dictionaries with 'name' and 'url'
    """
    if not soup:
        return []

    try:
        categories = []

        # Find all links to /category/
        category_links = soup.find_all('a', href=re.compile(r'^/category/'))

        for link in category_links:
            category = {
                'name': link.get_text().strip(),
                'url': link.get('href', '')
            }
            if category['name'] and category['url']:
                categories.append(category)

        return categories

    except Exception as e:
        logger.error(f"Error extracting categories: {e}")
        return []


def extract_isbns(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract ISBN-10 and ISBN-13 from book properties.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        Dictionary with 'isbn_10' and 'isbn_13' keys
    """
    if not soup:
        return {'isbn_10': None, 'isbn_13': None}

    try:
        isbns = {'isbn_10': None, 'isbn_13': None}

        # Look for ISBN in bookProperty divs
        property_divs = soup.find_all('div', class_=re.compile(r'bookProperty'))

        for prop_div in property_divs:
            label_div = prop_div.find('div', class_='property_label')
            if not label_div:
                continue

            label_text = label_div.get_text().strip()

            if 'ISBN 10' in label_text or 'ISBN-10' in label_text:
                value_div = prop_div.find(['div', 'span'], class_='property_value')
                if value_div:
                    isbns['isbn_10'] = value_div.get_text().strip()

            elif 'ISBN 13' in label_text or 'ISBN-13' in label_text:
                value_div = prop_div.find(['div', 'span'], class_='property_value')
                if value_div:
                    isbns['isbn_13'] = value_div.get_text().strip()

        return isbns

    except Exception as e:
        logger.error(f"Error extracting ISBNs: {e}")
        return {'isbn_10': None, 'isbn_13': None}


def extract_complete_metadata(html: str, mirror_url: str = None) -> Dict[str, Any]:
    """
    Extract all enhanced metadata from book detail page.

    This is the main function that orchestrates extraction of all metadata fields.

    Args:
        html: Raw HTML content of book detail page
        mirror_url: Base URL for constructing full URLs (e.g., "https://z-library.sk")

    Returns:
        Dictionary with comprehensive metadata including:
        - description (str)
        - terms (list[str])
        - booklists (list[dict])
        - rating (dict)
        - ipfs_cids (list[str])
        - series (str)
        - categories (list[dict])
        - isbn_10, isbn_13 (str)
        - quality_score (float)
    """
    if not html:
        logger.warning("Empty HTML provided for metadata extraction")
        return _empty_metadata()

    try:
        # Parse HTML once
        soup = BeautifulSoup(html, 'lxml')

        # Extract all metadata fields
        metadata = {
            # Tier 1: Essential (always extract)
            'description': extract_description(html),
            'terms': extract_terms(html),
            'booklists': extract_booklists(soup, mirror_url),

            # Tier 2: Important (extract when available)
            'rating': extract_rating(html),
            'ipfs_cids': extract_ipfs_cids(soup),
            'series': extract_series(soup),
            'categories': extract_categories(soup),

            # Tier 3: Optional (nice to have)
            'quality_score': extract_quality_score(html),
        }

        # Extract ISBNs and merge into metadata
        isbns = extract_isbns(soup)
        metadata['isbn_10'] = isbns['isbn_10']
        metadata['isbn_13'] = isbns['isbn_13']

        logger.info(f"Extracted metadata with {len(metadata['terms'])} terms, "
                   f"{len(metadata['booklists'])} booklists")

        return metadata

    except Exception as e:
        logger.error(f"Error extracting complete metadata: {e}")
        return _empty_metadata()


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
