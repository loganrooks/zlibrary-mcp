"""
Unified filename generation utilities for Z-Library MCP.

This module provides consistent filename generation across download and RAG processing.
Format: {author-lastname}-{title-slug}-{book-id}.{ext}

Design Decisions:
- Use dashes instead of underscores (web-friendly, filesystem-safe)
- Lowercase slugs (consistent, predictable)
- Author lastname first (easier sorting/grouping)
- Book ID preserved for uniqueness
- Maximum filename length: 255 characters (filesystem limit)
"""

import re
import unicodedata
from pathlib import Path


def slugify(value: str, allow_unicode: bool = False, max_length: int = None) -> str:
    """
    Convert string to filesystem-safe slug.

    Examples:
        "Byung-Chul Han" → "byung-chul-han"
        "The Burnout Society" → "the-burnout-society"
        "L'Être et le Néant" → "l-etre-et-le-neant" (if allow_unicode=False)

    Args:
        value: String to slugify
        allow_unicode: If True, preserve Unicode characters
        max_length: Maximum length for slug (None = no limit)

    Returns:
        Slugified string
    """
    value = str(value).lower().strip()

    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
        # Replace non-word chars with space
        value = re.sub(r'[^\w\s-]', ' ', value)
    else:
        # Convert to ASCII
        value = unicodedata.normalize('NFKD', value)
        value = value.encode('ascii', 'ignore').decode('ascii')
        # Replace non-alphanumeric with space
        value = re.sub(r'[^a-z0-9\s-]', ' ', value)

    # Collapse whitespace to single dash
    value = re.sub(r'[\s_]+', '-', value)
    # Remove consecutive dashes
    value = re.sub(r'-+', '-', value)
    # Strip leading/trailing dashes
    value = value.strip('-')

    # Apply length limit
    if max_length and len(value) > max_length:
        value = value[:max_length].rstrip('-')

    return value if value else 'unknown'


def extract_author_lastname(author_str: str) -> str:
    """
    Extract author's last name from author string.

    Handles formats:
        "Byung-Chul Han" → "han"
        "Han, Byung-Chul" → "han"
        "Agamben, Giorgio" → "agamben"
        "Plato" → "plato"
        "Jean-Luc Nancy" → "nancy"

    Args:
        author_str: Author name in various formats

    Returns:
        Slugified last name
    """
    if not author_str or not author_str.strip():
        return 'unknown-author'

    # Handle comma-separated format (Lastname, Firstname)
    if ',' in author_str:
        parts = author_str.split(',')
        lastname = parts[0].strip()
    else:
        # Space-separated format (Firstname Lastname)
        parts = author_str.strip().split()
        lastname = parts[-1] if parts else author_str

    return slugify(lastname, max_length=50)


def create_unified_filename(
    book_details: dict,
    extension: str = None,
    suffix: str = None,
    max_total_length: int = 200
) -> str:
    """
    Create unified filename for download or RAG processing.

    Format: {author-lastname}-{title-slug}-{book-id}[.suffix].{ext}

    Examples:
        Download: "han-burnout-society-3505318.pdf"
        RAG: "han-burnout-society-3505318.pdf.processed.markdown"
        Metadata: "han-burnout-society-3505318.pdf.metadata.json"

    Args:
        book_details: Dictionary with 'author', 'title', 'id', optionally 'extension'
        extension: File extension (overrides book_details['extension'])
        suffix: Additional suffix before extension (e.g., '.processed.markdown')
        max_total_length: Maximum filename length before extension

    Returns:
        Filesystem-safe filename
    """
    # Extract and process author
    author_str = book_details.get('author', '')
    if not author_str:
        # Try 'authors' list as fallback
        authors_list = book_details.get('authors', [])
        if isinstance(authors_list, list) and authors_list:
            author_str = authors_list[0]
    author_slug = extract_author_lastname(author_str)

    # Extract and process title
    title_str = book_details.get('title') or book_details.get('name', '')
    if not title_str:
        title_slug = 'untitled'
    else:
        title_slug = slugify(title_str, max_length=100)

    # Extract book ID
    book_id = str(book_details.get('id', 'no-id'))

    # Construct base filename
    base_name = f"{author_slug}-{title_slug}-{book_id}"

    # Truncate if necessary (preserve book ID)
    if len(base_name) > max_total_length:
        id_len = len(book_id)
        available_len = max_total_length - id_len - 1  # -1 for dash before ID

        # Split available length between author and title (60/40 ratio)
        author_max = int(available_len * 0.3)
        title_max = available_len - author_max

        author_slug = author_slug[:author_max].rstrip('-')
        title_slug = title_slug[:title_max].rstrip('-')

        base_name = f"{author_slug}-{title_slug}-{book_id}"

    # Add extension first (if no suffix provided)
    if not suffix:
        if extension:
            ext = extension.lower().lstrip('.')
            filename = f"{base_name}.{ext}"
        elif 'extension' in book_details:
            ext = book_details['extension'].lower().lstrip('.')
            filename = f"{base_name}.{ext}"
        else:
            filename = base_name
    else:
        # If suffix provided, assume it includes extension handling
        filename = f"{base_name}{suffix}"

    return filename


def create_metadata_filename(original_filename: str) -> str:
    """
    Create metadata sidecar filename from original filename.

    Examples:
        "han-burnout-society-3505318.pdf" → "han-burnout-society-3505318.pdf.metadata.json"
        "agamben-community-6035827.epub" → "agamben-community-6035827.epub.metadata.json"

    Args:
        original_filename: Original file or processed filename

    Returns:
        Metadata filename
    """
    # Remove any existing .processed.* suffix for metadata
    base = re.sub(r'\.processed\.\w+$', '', original_filename)

    # Get just the filename without directory
    base = Path(base).name

    return f"{base}.metadata.json"


def parse_filename(filename: str) -> dict:
    """
    Parse unified filename back into components.

    Examples:
        "han-burnout-society-3505318.pdf" → {
            'author_slug': 'han',
            'title_slug': 'burnout-society',
            'book_id': '3505318',
            'extension': 'pdf'
        }

    Args:
        filename: Unified format filename

    Returns:
        Dictionary with parsed components
    """
    # Remove directory if present
    filename = Path(filename).name

    # Handle multi-part extensions (e.g., .pdf.processed.markdown)
    # Look for .processed. pattern first
    if '.processed.' in filename:
        # Split at .processed. to separate base from processed extension
        parts = filename.split('.processed.')
        base_with_first_ext = parts[0]  # e.g., "han-burnout-society-3505318.pdf"
        processed_ext = parts[1]  # e.g., "markdown"

        # Remove the original extension to get the true base
        base_parts = base_with_first_ext.rsplit('.', 1)
        base_name = base_parts[0]  # e.g., "han-burnout-society-3505318"
        # The extension is just the processed part
        extension = f"processed.{processed_ext}"
    else:
        # Simple case - single extension
        parts = filename.rsplit('.', 1)
        base_name = parts[0]
        extension = parts[1] if len(parts) > 1 else None

    # Split into components (author-title-id)
    # Find last dash followed by digits (book ID)
    match = re.match(r'^(.+)-(\d+)$', base_name)

    if match:
        author_title = match.group(1)
        book_id = match.group(2)

        # Split author from title (first component is author)
        components = author_title.split('-', 1)
        author_slug = components[0] if components else 'unknown'
        title_slug = components[1] if len(components) > 1 else 'untitled'
    else:
        # Fallback if pattern doesn't match
        author_slug = 'unknown'
        title_slug = base_name
        book_id = 'no-id'

    return {
        'author_slug': author_slug,
        'title_slug': title_slug,
        'book_id': book_id,
        'extension': extension
    }
