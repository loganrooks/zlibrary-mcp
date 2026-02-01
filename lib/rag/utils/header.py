"""
Document header and TOC generation utilities for RAG processing.

Contains functions for generating document headers from PDF metadata,
markdown table of contents, and finding first content pages.
Also contains _extract_publisher_from_front_matter (will move to
detection/front_matter.py in subsequent decomposition).
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = [
    '_generate_document_header',
    '_generate_markdown_toc_from_pdf',
    '_find_first_content_page',
    '_extract_publisher_from_front_matter',
]


def _extract_publisher_from_front_matter(doc: 'fitz.Document', max_pages: int = 5) -> tuple:
    """
    Extract publisher and year from front matter text (title page, copyright page).

    Scans first N pages for publisher patterns like:
    - "Cambridge University Press"
    - "Oxford University Press"
    - "Published by [Publisher]"
    - Copyright lines with publisher info
    - "[Publisher Name], [Year]" patterns

    Args:
        doc: PyMuPDF document object
        max_pages: Maximum pages to scan for publisher info

    Returns:
        tuple: (publisher: str|None, year: str|None)
    """
    # Common publisher patterns (ordered by specificity)
    publisher_patterns = [
        # Specific well-known publishers
        r'(?i)(Cambridge University Press)',
        r'(?i)(Oxford University Press)',
        r'(?i)(MIT Press)',
        r'(?i)(Princeton University Press)',
        r'(?i)(Harvard University Press)',
        r'(?i)(Yale University Press)',
        r'(?i)(University of Chicago Press)',
        r'(?i)(Routledge)',
        r'(?i)(Springer)',
        r'(?i)(Wiley)',
        r'(?i)(Pearson)',
        r'(?i)(McGraw[- ]Hill)',
        r'(?i)(Elsevier)',
        r'(?i)(Palgrave Macmillan)',

        # Generic patterns
        r'(?i)Published by ([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books))',
        r'(?i)©\s*\d{4}\s+(?:by\s+)?([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books))',
        r'(?i)Copyright\s+©?\s*\d{4}\s+(?:by\s+)?([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books))',
        r'(?i)([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books)),?\s+\d{4}',
    ]

    # Year patterns
    year_patterns = [
        r'(?i)©\s*(\d{4})',
        r'(?i)Copyright\s+©?\s*(\d{4})',
        r'(?i)Published.*?(\d{4})',
        r'(?i)\b(19\d{2}|20[0-2]\d)\b',  # Years 1900-2029
    ]

    # Filter out conversion tools that appear in metadata
    conversion_tools = [
        'calibre', 'adobe', 'acrobat', 'distiller', 'pdftex',
        'latex', 'pdflatex', 'xelatex', 'luatex', 'context',
        'prince', 'antenna house', 'ghostscript', 'ps2pdf'
    ]

    publisher = None
    year = None

    # Scan first few pages
    for page_num in range(min(max_pages, len(doc))):
        try:
            page = doc[page_num]
            text = page.get_text()

            # Defensive: ensure text is a string
            if not isinstance(text, str):
                continue

            # Try to find publisher
            if not publisher:
                for pattern in publisher_patterns:
                    match = re.search(pattern, text)
                    if match:
                        # Extract publisher name (first capture group or full match)
                        potential_publisher = match.group(1) if match.lastindex else match.group(0)
                        potential_publisher = potential_publisher.strip()

                        # Filter out conversion tools
                        if not any(tool in potential_publisher.lower() for tool in conversion_tools):
                            # Clean up common artifacts
                            potential_publisher = re.sub(r'\s+', ' ', potential_publisher)  # Normalize whitespace

                            # Validate it's not too long or too short
                            if 5 < len(potential_publisher) < 60:
                                publisher = potential_publisher
                                break

            # Try to find publication year
            if not year:
                for pattern in year_patterns:
                    match = re.search(pattern, text)
                    if match:
                        potential_year = match.group(1)
                        # Validate year range (1900-2029)
                        if potential_year.isdigit() and 1900 <= int(potential_year) <= 2029:
                            year = potential_year
                            break

            # Stop if we found both
            if publisher and year:
                break

        except Exception as e:
            logging.warning(f"Error extracting publisher from page {page_num}: {e}")
            continue

    return publisher, year


def _generate_document_header(doc: 'fitz.Document') -> str:
    """
    Generate a clean document header from PDF metadata and front matter.

    Extracts publisher from actual front matter text (not PDF metadata)
    to avoid picking up conversion tools like "calibre 3.32.0".

    Returns markdown formatted:
    # Title
    **Author:** Name
    **Translator:** Name (if available)
    **Publisher:** Name | **Year:** YYYY
    """
    metadata = doc.metadata

    title = metadata.get('title', 'Untitled')
    author = metadata.get('author', 'Unknown Author')

    # Build header
    lines = [f"# {title}", ""]

    if author and author != 'Unknown Author':
        lines.append(f"**Author:** {author}")

    # Check for translator in subject or keywords (common places)
    translator = None
    subject = metadata.get('subject', '')
    if 'translat' in subject.lower():
        translator = subject

    if translator:
        lines.append(f"**Translator:** {translator}")

    # Extract publisher and year from front matter text (NOT metadata)
    publisher, year = _extract_publisher_from_front_matter(doc, max_pages=5)

    # Fallback to metadata year if not found in text
    if not year:
        creation_date = metadata.get('creationDate', '')
        if creation_date and isinstance(creation_date, str):
            year_match = re.search(r'(\d{4})', creation_date)
            if year_match:
                year = year_match.group(1)

    pub_info = []
    if publisher:
        pub_info.append(f"**Publisher:** {publisher}")
    if year:
        pub_info.append(f"**Year:** {year}")

    if pub_info:
        lines.append(" | ".join(pub_info))

    lines.append("")  # Blank line after header
    return "\n".join(lines)


def _generate_markdown_toc_from_pdf(toc_map: dict, skip_front_matter: bool = True) -> str:
    """
    Generate markdown-formatted table of contents with links.

    Args:
        toc_map: dict mapping page_num to list of (level, title) tuples
        skip_front_matter: If True, skip entries like "Title Page", "Copyright Page", "Contents"

    Returns:
        Markdown formatted ToC with links
    """
    front_matter_titles = {
        'title page', 'copyright page', 'copyright',
        'contents', 'table of contents'
    }

    toc_lines = ["## Table of Contents", ""]

    # Sort entries by page number
    sorted_pages = sorted(toc_map.keys())

    for page_num in sorted_pages:
        for level, title in toc_map[page_num]:
            # Skip front matter if requested
            if skip_front_matter and title.lower() in front_matter_titles:
                continue

            # Create markdown link (GitHub-style anchor)
            # Convert title to anchor: lowercase, spaces to hyphens, remove special chars
            anchor = title.lower()
            anchor = anchor.replace(' ', '-')
            anchor = ''.join(c for c in anchor if c.isalnum() or c == '-')
            anchor = anchor.strip('-')

            # Indent based on level
            indent = "  " * (level - 1)

            # Format as markdown list with link
            toc_lines.append(f"{indent}* [{title}](#{anchor}) - [[PDF_page_{page_num}]]")

    toc_lines.append("")  # Blank line after ToC
    return "\n".join(toc_lines)


def _find_first_content_page(toc_map: dict) -> int:
    """
    Find the first real content page (skip front matter entries).

    Returns page number of first non-front-matter ToC entry.
    """
    front_matter_titles = {
        'title page', 'copyright page', 'copyright',
        'contents', 'table of contents'
    }

    sorted_pages = sorted(toc_map.keys())

    for page_num in sorted_pages:
        for level, title in toc_map[page_num]:
            if title.lower() not in front_matter_titles:
                return page_num

    # Fallback: return first ToC page
    return sorted_pages[0] if sorted_pages else 1
