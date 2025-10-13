"""
Metadata generation utilities for RAG processing.

Provides YAML frontmatter and JSON sidecar file generation for academic citations.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


def generate_yaml_frontmatter(
    title: str,
    author: str = None,
    book_id: str = None,
    format_type: str = None,
    pages: int = None,
    publisher: str = None,
    year: str = None,
    isbn: str = None,
    translator: str = None,
    ocr_quality: float = None,
    processing_date: str = None,
    **kwargs
) -> str:
    """
    Generate YAML frontmatter for markdown files.

    Example:
        ---
        title: The Burnout Society
        author: Byung-Chul Han
        translator: Erik Butler
        publisher: Stanford University Press
        year: 2015
        isbn: 9780804795098
        pages: 117
        format: pdf
        ocr_quality: 0.95
        processing_date: 2025-10-13
        source_id: 3505318
        ---

    Args:
        title: Book title
        author: Author name
        book_id: Z-Library book ID
        format_type: File format (pdf, epub, etc.)
        pages: Number of pages
        publisher: Publisher name
        year: Publication year
        isbn: ISBN number
        translator: Translator name
        ocr_quality: OCR quality score (0-1)
        processing_date: Date of processing
        **kwargs: Additional metadata fields

    Returns:
        YAML frontmatter string
    """
    yaml_lines = ["---"]

    # Required fields
    if title:
        yaml_lines.append(f"title: {_yaml_escape(title)}")

    # Optional fields (in order of importance)
    if author:
        yaml_lines.append(f"author: {_yaml_escape(author)}")

    if translator:
        yaml_lines.append(f"translator: {_yaml_escape(translator)}")

    if publisher:
        yaml_lines.append(f"publisher: {_yaml_escape(publisher)}")

    if year:
        yaml_lines.append(f"year: {year}")

    if isbn:
        yaml_lines.append(f"isbn: {isbn}")

    if pages:
        yaml_lines.append(f"pages: {pages}")

    if format_type:
        yaml_lines.append(f"format: {format_type}")

    if ocr_quality is not None:
        yaml_lines.append(f"ocr_quality: {ocr_quality:.2f}")

    if processing_date:
        yaml_lines.append(f"processing_date: {processing_date}")
    else:
        yaml_lines.append(f"processing_date: {datetime.now().strftime('%Y-%m-%d')}")

    if book_id:
        yaml_lines.append(f"source_id: {book_id}")

    # Add any additional metadata
    for key, value in kwargs.items():
        if value is not None:
            yaml_lines.append(f"{key}: {_yaml_escape(str(value))}")

    yaml_lines.append("---")
    yaml_lines.append("")  # Empty line after frontmatter

    return "\n".join(yaml_lines)


def _yaml_escape(value: str) -> str:
    """
    Escape string for YAML if it contains special characters.

    Args:
        value: String to escape

    Returns:
        YAML-safe string
    """
    # Check if quoting is needed
    if any(char in value for char in [':', '#', '{', '}', '[', ']', ',', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`']):
        # Escape internal quotes and wrap in quotes
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def extract_toc_from_content(content: str, format_type: str = "markdown") -> List[Dict]:
    """
    Extract table of contents from processed content.

    Looks for heading markers and constructs TOC with line numbers.

    Args:
        content: Processed markdown/text content
        format_type: Content format

    Returns:
        List of TOC entries with line numbers
    """
    toc_entries = []
    lines = content.split('\n')
    last_page_num = None  # Track most recent page marker

    for line_num, line in enumerate(lines, start=1):
        # Check for page markers (standalone or in text)
        page_marker_match = re.search(r'`\[p\.(\d+)\]`', line)
        if page_marker_match:
            last_page_num = int(page_marker_match.group(1))

        # Markdown headings
        if format_type == "markdown":
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Extract page number from title if present, otherwise use last seen
                page_match = re.search(r'`\[p\.(\d+)\]`', title)
                if page_match:
                    page_num = int(page_match.group(1))
                else:
                    page_num = last_page_num

                # Remove page marker from title if present
                clean_title = re.sub(r'`\[p\.\d+\]`\s*', '', title)

                toc_entries.append({
                    "title": clean_title,
                    "level": level,
                    "line_start": line_num,
                    "page": page_num
                })

    return toc_entries


def extract_page_line_mapping(content: str) -> Dict[int, Dict[str, int]]:
    """
    Extract page-to-line number mappings from content.

    Looks for page markers like `[p.1]` and creates mappings.

    Args:
        content: Processed content with page markers

    Returns:
        Dictionary mapping page numbers to line ranges
    """
    page_mappings = {}
    lines = content.split('\n')

    current_page = None
    page_start_line = None

    for line_num, line in enumerate(lines, start=1):
        # Look for page markers
        page_match = re.search(r'`\[p\.(\d+)\]`', line)

        if page_match:
            # End previous page if exists
            if current_page is not None and page_start_line is not None:
                page_mappings[current_page] = {
                    "start": page_start_line,
                    "end": line_num - 1
                }

            # Start new page
            current_page = int(page_match.group(1))
            page_start_line = line_num

    # Close last page
    if current_page is not None and page_start_line is not None:
        page_mappings[current_page] = {
            "start": page_start_line,
            "end": len(lines)
        }

    return page_mappings


def generate_metadata_sidecar(
    original_filename: str,
    processed_content: str,
    book_details: Dict = None,
    ocr_quality_score: float = None,
    corrections_applied: List[str] = None,
    format_type: str = "pdf",
    output_format: str = "markdown"
) -> Dict:
    """
    Generate comprehensive metadata sidecar for processed document.

    Creates JSON metadata file with:
    - Source metadata (title, author, publisher, etc.)
    - Front matter information
    - Table of contents with page/line numbers
    - Page-to-line mappings
    - Processing metadata

    Args:
        original_filename: Original file path
        processed_content: Processed markdown/text content
        book_details: Dictionary with book metadata
        ocr_quality_score: OCR quality score if applicable
        corrections_applied: List of correction algorithms applied
        format_type: Original format (pdf, epub, etc.)
        output_format: Output format (markdown, txt)

    Returns:
        Dictionary with complete metadata
    """
    if book_details is None:
        book_details = {}

    if corrections_applied is None:
        corrections_applied = []

    # Extract TOC and page mappings
    toc = extract_toc_from_content(processed_content, output_format)
    page_mappings = extract_page_line_mapping(processed_content)

    # Count words and pages
    word_count = len(processed_content.split())
    page_count = len(page_mappings)

    # Build metadata structure
    metadata = {
        "source": {
            "title": book_details.get('title', 'Unknown'),
            "author": book_details.get('author', 'Unknown'),
            "id": book_details.get('id'),
            "format": format_type,
            "original_filename": Path(original_filename).name
        },
        "toc": toc,
        "page_line_mapping": page_mappings,
        "processing_metadata": {
            "processing_date": datetime.now().isoformat(),
            "output_format": output_format,
            "word_count": word_count,
            "page_count": page_count if page_count > 0 else None,
            "corrections_applied": corrections_applied
        }
    }

    # Add OCR quality if available
    if ocr_quality_score is not None:
        metadata["processing_metadata"]["ocr_quality_score"] = round(ocr_quality_score, 2)

    # Add optional source metadata
    optional_fields = ['publisher', 'year', 'isbn', 'translator', 'pages', 'extension']
    for field in optional_fields:
        if field in book_details and book_details[field]:
            metadata["source"][field] = book_details[field]

    return metadata


def save_metadata_sidecar(
    metadata: Dict,
    output_path: Path
) -> str:
    """
    Save metadata to JSON sidecar file.

    Args:
        metadata: Metadata dictionary
        output_path: Path for metadata file

    Returns:
        Path to saved metadata file
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON with pretty formatting
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return str(output_path)


def add_yaml_frontmatter_to_content(
    content: str,
    book_details: Dict = None,
    ocr_quality: float = None,
    format_type: str = None
) -> str:
    """
    Prepend YAML frontmatter to markdown content.

    Args:
        content: Markdown content
        book_details: Book metadata
        ocr_quality: OCR quality score
        format_type: Original format

    Returns:
        Content with YAML frontmatter
    """
    if book_details is None:
        book_details = {}

    frontmatter = generate_yaml_frontmatter(
        title=book_details.get('title', 'Unknown'),
        author=book_details.get('author'),
        book_id=book_details.get('id'),
        format_type=format_type,
        pages=book_details.get('pages'),
        publisher=book_details.get('publisher'),
        year=book_details.get('year'),
        isbn=book_details.get('isbn'),
        translator=book_details.get('translator'),
        ocr_quality=ocr_quality
    )

    return f"{frontmatter}\n{content}"
