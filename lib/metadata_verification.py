"""
Metadata verification system for comparing Z-Library API data against extracted document metadata.

Provides extraction, comparison, and confidence scoring to identify metadata discrepancies
and recommend trusted sources.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from difflib import SequenceMatcher

# Check for optional dependencies
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    ebooklib = None
    epub = None
    BeautifulSoup = None


# ============================================================================
# Metadata Extraction Functions
# ============================================================================

def extract_pdf_metadata(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract metadata from PDF document.

    Extraction sources (in priority order):
    1. PDF metadata dictionary (doc.metadata)
    2. Front matter text patterns (title page, copyright page)

    Args:
        file_path: Path to PDF file

    Returns:
        Dictionary with extracted metadata fields:
        {
            'title': str,
            'author': str,
            'publisher': str,
            'year': str,
            'isbn': str
        }
    """
    if not PYMUPDF_AVAILABLE:
        logging.warning("PyMuPDF not available, cannot extract PDF metadata")
        return {}

    metadata = {
        'title': None,
        'author': None,
        'publisher': None,
        'year': None,
        'isbn': None
    }

    try:
        doc = fitz.open(str(file_path))

        # --- Source 1: Front Matter Text (PRIORITY) ---
        # Scan first 10 pages for title page, copyright page (copyright often on page 8)
        front_matter_text = ""
        for page_num in range(min(10, len(doc))):
            page = doc[page_num]
            front_matter_text += page.get_text('text') + "\n\n"

        # Extract publisher from front matter TEXT (more accurate than metadata)
        publisher = _extract_publisher_from_text(front_matter_text)
        if publisher:
            metadata['publisher'] = publisher

        # Extract title from first page
        title = _extract_title_from_text(front_matter_text)
        if title:
            metadata['title'] = title

        # --- Source 2: PDF Metadata Dictionary (FALLBACK) ---
        pdf_metadata = doc.metadata
        if pdf_metadata:
            # Use metadata for fields not found in front matter
            if not metadata['title']:
                metadata['title'] = _clean_metadata_field(pdf_metadata.get('title'))

            if not metadata['author']:
                metadata['author'] = _clean_metadata_field(pdf_metadata.get('author'))

            # Year from metadata as fallback
            if not metadata['year']:
                creation_date = pdf_metadata.get('creationDate', '')
                if creation_date:
                    year_match = re.search(r'(\d{4})', creation_date)
                    if year_match:
                        metadata['year'] = year_match.group(1)

        # Extract year from copyright page
        if not metadata['year']:
            year = _extract_year_from_text(front_matter_text)
            if year:
                metadata['year'] = year

        # Extract ISBN from front matter
        isbn = _extract_isbn_from_text(front_matter_text)
        if isbn:
            metadata['isbn'] = isbn

        doc.close()

        # Log extraction results
        extracted_fields = [k for k, v in metadata.items() if v]
        logging.info(f"Extracted PDF metadata fields: {extracted_fields}")

        return metadata

    except Exception as e:
        logging.error(f"Error extracting PDF metadata from {file_path}: {e}")
        return metadata


def extract_epub_metadata(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract metadata from EPUB document.

    Extraction source: EPUB OPF manifest metadata elements

    Args:
        file_path: Path to EPUB file

    Returns:
        Dictionary with extracted metadata fields
    """
    if not EBOOKLIB_AVAILABLE:
        logging.warning("ebooklib not available, cannot extract EPUB metadata")
        return {}

    metadata = {
        'title': None,
        'author': None,
        'publisher': None,
        'year': None,
        'isbn': None
    }

    try:
        book = epub.read_epub(str(file_path))

        # Extract from EPUB metadata
        metadata['title'] = _clean_metadata_field(book.get_metadata('DC', 'title'))
        metadata['author'] = _clean_metadata_field(book.get_metadata('DC', 'creator'))
        metadata['publisher'] = _clean_metadata_field(book.get_metadata('DC', 'publisher'))

        # Extract year from date field
        date = book.get_metadata('DC', 'date')
        if date:
            date_str = _clean_metadata_field(date)
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                metadata['year'] = year_match.group(1)

        # Extract ISBN from identifier
        identifiers = book.get_metadata('DC', 'identifier')
        if identifiers:
            for identifier in identifiers:
                if isinstance(identifier, tuple):
                    identifier = identifier[0]
                isbn = _extract_isbn_from_text(str(identifier))
                if isbn:
                    metadata['isbn'] = isbn
                    break

        extracted_fields = [k for k, v in metadata.items() if v]
        logging.info(f"Extracted EPUB metadata fields: {extracted_fields}")

        return metadata

    except Exception as e:
        logging.error(f"Error extracting EPUB metadata from {file_path}: {e}")
        return metadata


def extract_txt_metadata(file_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract metadata from TXT document.

    Very limited extraction capability - mainly filename heuristics.

    Args:
        file_path: Path to TXT file

    Returns:
        Dictionary with extracted metadata fields (mostly empty)
    """
    metadata = {
        'title': None,
        'author': None,
        'publisher': None,
        'year': None,
        'isbn': None
    }

    try:
        # Try to extract title from filename
        filename = file_path.stem
        # Remove common patterns like "author - title" or "[year] title"
        cleaned_filename = re.sub(r'^\[?\d{4}\]?\s*[-–]\s*', '', filename)
        cleaned_filename = re.sub(r'^[^-–]+\s*[-–]\s*', '', cleaned_filename)

        if cleaned_filename and len(cleaned_filename) > 3:
            metadata['title'] = cleaned_filename.replace('_', ' ').strip()

        logging.info(f"Extracted TXT metadata (limited): title={metadata['title']}")

        return metadata

    except Exception as e:
        logging.error(f"Error extracting TXT metadata from {file_path}: {e}")
        return metadata


# ============================================================================
# Verification and Comparison
# ============================================================================

def verify_metadata(
    api_metadata: Dict[str, Optional[str]],
    extracted_metadata: Dict[str, Optional[str]]
) -> Dict:
    """
    Compare API metadata against extracted document metadata.

    Performs field-by-field comparison with confidence scoring and generates
    trust recommendations for each field.

    Args:
        api_metadata: Metadata from Z-Library API (book_details)
        extracted_metadata: Metadata extracted from document

    Returns:
        Verification report with structure:
        {
            'fields': {
                'title': {
                    'api_value': str,
                    'extracted_value': str,
                    'confidence': float (0-100),
                    'match_type': str ('exact'|'fuzzy'|'substring'|'none'),
                    'trusted_source': str ('api'|'extracted'|'review'),
                    'recommendation': str
                },
                ... (author, publisher, year, isbn)
            },
            'overall_confidence': float (0-100),
            'discrepancies': list[str],
            'summary': str
        }
    """
    fields_to_verify = ['title', 'author', 'publisher', 'year', 'isbn']

    verification_report = {
        'fields': {},
        'overall_confidence': 0.0,
        'discrepancies': [],
        'summary': ''
    }

    total_confidence = 0.0
    fields_compared = 0

    for field in fields_to_verify:
        api_value = api_metadata.get(field)
        extracted_value = extracted_metadata.get(field)

        # Skip if both are empty
        if not api_value and not extracted_value:
            continue

        # Compare values
        comparison = _compare_metadata_field(
            field_name=field,
            api_value=api_value,
            extracted_value=extracted_value
        )

        verification_report['fields'][field] = comparison

        # Track discrepancies
        if comparison['match_type'] == 'none' and api_value and extracted_value:
            verification_report['discrepancies'].append(
                f"{field}: API='{api_value}' vs Extracted='{extracted_value}'"
            )

        # Accumulate confidence for overall score
        if api_value or extracted_value:
            total_confidence += comparison['confidence']
            fields_compared += 1

    # Calculate overall confidence
    if fields_compared > 0:
        verification_report['overall_confidence'] = round(total_confidence / fields_compared, 1)

    # Generate summary
    verification_report['summary'] = _generate_verification_summary(verification_report)

    logging.info(f"Metadata verification complete: {verification_report['overall_confidence']}% confidence, "
                 f"{len(verification_report['discrepancies'])} discrepancies")

    return verification_report


def _compare_metadata_field(
    field_name: str,
    api_value: Optional[str],
    extracted_value: Optional[str]
) -> Dict:
    """
    Compare a single metadata field with confidence scoring.

    Scoring logic:
    - Exact match (after normalization): 100%
    - High fuzzy match (>0.9 similarity): 90%
    - Good fuzzy match (>0.8 similarity): 80%
    - Moderate fuzzy match (>0.7 similarity): 70%
    - Substring match: 60%
    - No match: 0%
    - One source only: 50% (use available source)

    Args:
        field_name: Name of metadata field
        api_value: Value from API
        extracted_value: Value from document

    Returns:
        Comparison result dictionary
    """
    result = {
        'api_value': api_value,
        'extracted_value': extracted_value,
        'confidence': 0.0,
        'match_type': 'none',
        'trusted_source': 'review',
        'recommendation': ''
    }

    # Case 1: Both empty
    if not api_value and not extracted_value:
        result['confidence'] = 0.0
        result['match_type'] = 'none'
        result['trusted_source'] = 'none'
        result['recommendation'] = f"No {field_name} data available from either source"
        return result

    # Case 2: Only API has data
    if api_value and not extracted_value:
        result['confidence'] = 50.0
        result['match_type'] = 'api_only'
        result['trusted_source'] = 'api'
        result['recommendation'] = f"Use API {field_name} (no extracted data available)"
        return result

    # Case 3: Only extracted has data
    if extracted_value and not api_value:
        result['confidence'] = 50.0
        result['match_type'] = 'extracted_only'
        result['trusted_source'] = 'extracted'
        result['recommendation'] = f"Use extracted {field_name} (no API data available)"
        return result

    # Case 4: Both have data - perform comparison
    api_normalized = _normalize_text(api_value)
    extracted_normalized = _normalize_text(extracted_value)

    # Exact match (after normalization)
    if api_normalized == extracted_normalized:
        result['confidence'] = 100.0
        result['match_type'] = 'exact'
        result['trusted_source'] = 'both'
        result['recommendation'] = f"Perfect match - use either source for {field_name}"
        return result

    # Fuzzy match using SequenceMatcher
    similarity = SequenceMatcher(None, api_normalized, extracted_normalized).ratio()

    if similarity > 0.9:
        result['confidence'] = 90.0
        result['match_type'] = 'fuzzy_high'
        result['trusted_source'] = 'extracted'
        result['recommendation'] = f"High similarity - prefer extracted {field_name}"
    elif similarity > 0.8:
        result['confidence'] = 80.0
        result['match_type'] = 'fuzzy_good'
        result['trusted_source'] = 'extracted'
        result['recommendation'] = f"Good similarity - prefer extracted {field_name}"
    elif similarity > 0.7:
        result['confidence'] = 70.0
        result['match_type'] = 'fuzzy_moderate'
        result['trusted_source'] = 'extracted'
        result['recommendation'] = f"Moderate similarity - prefer extracted {field_name}"
    # Substring match
    elif api_normalized in extracted_normalized or extracted_normalized in api_normalized:
        result['confidence'] = 60.0
        result['match_type'] = 'substring'
        result['trusted_source'] = 'extracted'
        result['recommendation'] = f"Substring match - prefer extracted {field_name}"
    else:
        # Low confidence - flag for review
        result['confidence'] = 0.0
        result['match_type'] = 'none'
        result['trusted_source'] = 'review'
        result['recommendation'] = f"Significant discrepancy - manual review needed for {field_name}"

    return result


# ============================================================================
# Utility Functions
# ============================================================================

def _normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    - Convert to lowercase
    - Remove extra whitespace
    - Remove common punctuation
    - Trim leading/trailing whitespace
    """
    if not text:
        return ""

    # Convert to lowercase
    normalized = text.lower()

    # Remove common punctuation (keep hyphens for names)
    normalized = re.sub(r'[.,;:!?"\'\[\]\(\)]', '', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    # Trim
    normalized = normalized.strip()

    return normalized


def _clean_metadata_field(value) -> Optional[str]:
    """Clean and normalize metadata field value."""
    if not value:
        return None

    # Handle tuple format from EPUB metadata
    if isinstance(value, (list, tuple)):
        if len(value) > 0:
            value = value[0]
        else:
            return None

    # Convert to string and strip
    cleaned = str(value).strip()

    # Return None if empty
    return cleaned if cleaned else None


def _extract_title_from_text(text: str) -> Optional[str]:
    """
    Extract title from front matter text.

    Heuristic: Look for capitalized text in first few lines.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    for line in lines[:10]:  # Check first 10 non-empty lines
        # Skip very short lines
        if len(line) < 5:
            continue

        # Skip lines that look like headers/footers
        if re.match(r'^(page|chapter|\d+)', line, re.IGNORECASE):
            continue

        # Title is often in title case or all caps
        if line.istitle() or line.isupper():
            # Clean up the title
            title = re.sub(r'\s+', ' ', line)
            if len(title) > 10:  # Reasonable title length
                return title

    return None


def _extract_publisher_from_text(text: str) -> Optional[str]:
    """
    Extract publisher from copyright page text.

    Looks for patterns like:
    - "Published by [Publisher Name]"
    - "[Publisher Name] Publishing"
    - "© [Year] [Publisher Name]"
    - "CAMBRIDGE UNIVERSITY PRESS" (all caps)
    """
    # Pattern 0: Well-known publishers (case-insensitive, whole line)
    well_known = [
        'cambridge university press', 'oxford university press',
        'mit press', 'princeton university press', 'harvard university press',
        'yale university press', 'stanford university press',
        'university of chicago press', 'routledge', 'springer',
        'wiley', 'pearson', 'mcgraw-hill', 'elsevier'
    ]

    for publisher in well_known:
        # Match whole publisher name (case-insensitive)
        pattern = re.escape(publisher)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Return in title case
            return match.group(0).title()

    # Pattern 1: "Published by X"
    match = re.search(r'published by\s+([A-Z][A-Za-z\s&]+?)(?:\n|,|\.|\s{2,})', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 2: "X Press" or "X Publishing" (case-insensitive)
    match = re.search(r'([A-Z][A-Za-z\s&]+?)\s+(Press|Publishing|Publishers)', text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} {match.group(2)}".strip()

    # Pattern 3: After copyright symbol
    match = re.search(r'©\s*\d{4}\s+(?:by\s+)?([A-Z][A-Za-z\s&]+?)(?:\n|,|\.)', text)
    if match:
        publisher = match.group(1).strip()
        # Filter out author names (heuristic: publishers have certain keywords)
        if any(word in publisher.lower() for word in ['press', 'publishing', 'publishers', 'university', 'books']):
            return publisher

    return None


def _extract_year_from_text(text: str) -> Optional[str]:
    """
    Extract publication year from copyright page text.

    Looks for patterns like:
    - "© 2023"
    - "Copyright 2023"
    - "Published 2023"
    """
    # Pattern 1: Copyright symbol with year
    match = re.search(r'©\s*(\d{4})', text)
    if match:
        return match.group(1)

    # Pattern 2: "Copyright YYYY"
    match = re.search(r'copyright\s+(\d{4})', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: "Published YYYY"
    match = re.search(r'published\s+(\d{4})', text, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _extract_isbn_from_text(text: str) -> Optional[str]:
    """
    Extract ISBN from text.

    Matches both ISBN-10 and ISBN-13 formats.
    """
    # Pattern: ISBN followed by digits with optional hyphens
    match = re.search(r'ISBN[:\s]*([0-9-]{10,17})', text, re.IGNORECASE)
    if match:
        isbn = match.group(1).replace('-', '').strip()
        # Validate length (10 or 13 digits)
        if len(isbn) in [10, 13]:
            return isbn

    return None


def _generate_verification_summary(report: Dict) -> str:
    """Generate human-readable summary of verification report."""
    field_count = len(report['fields'])
    discrepancy_count = len(report['discrepancies'])
    confidence = report['overall_confidence']

    if confidence >= 90:
        quality = "Excellent"
    elif confidence >= 70:
        quality = "Good"
    elif confidence >= 50:
        quality = "Fair"
    else:
        quality = "Poor"

    summary = f"{quality} metadata quality ({confidence}% confidence). "
    summary += f"Verified {field_count} fields. "

    if discrepancy_count == 0:
        summary += "No significant discrepancies found."
    elif discrepancy_count == 1:
        summary += "1 discrepancy requires review."
    else:
        summary += f"{discrepancy_count} discrepancies require review."

    return summary
