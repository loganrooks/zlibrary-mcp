import asyncio
import re
import logging
from pathlib import Path
import aiofiles
import unicodedata # Added for slugify
import os # Ensure os is imported if needed for path manipulation later
import io # Added for OCR image handling
import string # Added for garbled text detection
import collections # Added for garbled text detection
import json # For metadata sidecar generation
import sys # For path manipulation
sys.path.insert(0, str(Path(__file__).parent))
from filename_utils import create_unified_filename, create_metadata_filename
from metadata_generator import (
    generate_metadata_sidecar,
    save_metadata_sidecar,
    add_yaml_frontmatter_to_content
)

# Check if libraries are available
# OCR Dependencies (Optional)
# Define placeholder initially, overwrite if import succeeds
class TesseractNotFoundError(Exception): pass

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image # Added for OCR image handling
    OCR_AVAILABLE = True
    # If import succeeds, use the actual exception
    TesseractNotFoundError = pytesseract.TesseractNotFoundError
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None
    Image = None
    # Placeholder is already defined outside
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup, NavigableString # Added NavigableString
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    BeautifulSoup = None # Define as None if not available
    NavigableString = None # Define as None if not available

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None # Define as None if not available

# Custom Exception (Consider moving if used elsewhere, but keep here for now)
class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
    pass

# Custom Exception for Dependency Issues
class OCRDependencyError(Exception): pass

# Constants
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf'] # Keep relevant constants? Or import? Keep for now.
# PDF Quality Thresholds
_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY = 10
_PDF_QUALITY_THRESHOLD_LOW_DENSITY = 50
_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO = 0.7
_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO = 0.15
_PDF_QUALITY_MIN_SPACE_RATIO = 0.05
PROCESSED_OUTPUT_DIR = Path("./processed_rag_output")

# --- Slugify Helper ---

def _slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value).lower() # Ensure string and lowercase
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
        # Replace non-word chars (letters, numbers, underscore) with a space
        value = re.sub(r'[^\w]', ' ', value)
    else:
        # ASCII path: Normalize, encode/decode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        # Replace non a-z0-9 chars (including underscore) with a space
        value = re.sub(r'[^a-z0-9]', ' ', value)

    # Collapse consecutive whitespace to single hyphen
    value = re.sub(r'\s+', '-', value)
    # Strip leading/trailing hyphens
    value = value.strip('-')

    # Ensure slug is not empty, default to 'file' if it becomes empty
    return value if value else 'file'

# --- PDF Markdown Helpers ---

def _analyze_pdf_block(block: dict) -> dict:
    """
    Analyzes a PyMuPDF text block dictionary to infer structure.

    Infers heading level, list item status/type based on font size, flags,
    and text patterns. NOTE: These are heuristics and may require tuning.

    Args:
        block: A dictionary representing a text block from page.get_text("dict").

    Returns:
        A dictionary containing analysis results:
        'heading_level', 'is_list_item', 'list_type', 'list_indent', 'text', 'spans'.
    """
    # Heuristic logic based on font size, flags, position, text patterns
    heading_level = 0
    is_list_item = False
    list_type = None # 'ul' or 'ol'
    list_indent = 0 # Placeholder
    list_marker = None # Initialize list_marker
    text_content = ""
    spans = []

    if block.get('type') == 0: # Text block
        # Aggregate text and span info
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                spans.append(span)
                text_content += span.get('text', '')

        # Apply cleaning (null chars, headers/footers) *before* analysis
        text_content = text_content.replace('\x00', '') # Remove null chars first
        header_footer_patterns = [
            # Existing patterns
            re.compile(r"^(JSTOR.*|Downloaded from.*|Copyright ©.*)\n?", re.IGNORECASE | re.MULTILINE),
            re.compile(r"^Page \d+\s*\n?", re.MULTILINE),
            # Added: Pattern to catch lines containing 'Page X' variations, potentially with other text
            re.compile(r"^(.*\bPage \d+\b.*)\n?", re.IGNORECASE | re.MULTILINE)
        ]
        for pattern in header_footer_patterns:
            text_content = pattern.sub('', text_content)
        text_content = re.sub(r'\n\s*\n', '\n\n', text_content).strip() # Consolidate blank lines

        if not text_content: # If cleaning removed everything, return early
             return {
                'heading_level': 0, 'list_marker': None, 'is_list_item': False,
                'list_type': None, 'list_indent': 0, 'text': '', 'spans': spans
             }

        if spans:
            first_span = spans[0]
            font_size = first_span.get('size', 10)
            flags = first_span.get('flags', 0)
            is_bold = flags & 2 # Font flag for bold

            # --- Heading Heuristic (Example based on size/boldness) ---
            # Filter out pure page numbers (don't treat "420" as a heading)
            trimmed_text = text_content.strip()
            is_pure_number = re.match(r'^\d+$', trimmed_text)

            if not is_pure_number:
                # Reordered to check more specific conditions first
                if font_size > 12 and font_size <= 14 and is_bold: # H3
                     heading_level = 3
                elif font_size > 11 and font_size <= 12 and is_bold: # H3
                     heading_level = 3
                elif font_size > 14 and font_size <= 18 and is_bold: # H2
                     heading_level = 2
                elif font_size > 12 and font_size <= 14: # H3
                     heading_level = 3
                elif font_size > 14 and font_size <= 18: # H2
                     heading_level = 2
                elif font_size > 18: # H1
                     heading_level = 1
            # If is_pure_number, heading_level stays 0

            # --- List Heuristic (Example based on starting characters) ---
            # This is basic and doesn't handle indentation/nesting reliably.
            trimmed_text = text_content.strip()
            list_marker = None # Store the detected marker/number

            # Unordered list check (common bullet characters)
            ul_match = re.match(r"^([\*•–-])\s+", trimmed_text) # Added en-dash
            if ul_match:
                is_list_item = True
                list_type = 'ul'
                list_marker = ul_match.group(1)
                # Indentation could be inferred from block['bbox'][0] (x-coordinate)

            # Ordered list check (e.g., "1. ", "a) ", "i. ") - More robust
            ol_match = re.match(r"^(\d+|[a-zA-Z]|[ivxlcdm]+)[\.\)]\s+", trimmed_text, re.IGNORECASE)
            if not is_list_item and ol_match: # Check only if not already identified as UL
                is_list_item = True
                list_type = 'ol'
                list_marker = ol_match.group(1) # Capture number/letter/roman numeral

            # TODO: Use block['bbox'][0] (x-coordinate) to infer indentation/nesting.

    return {
        'heading_level': heading_level,
        'list_marker': list_marker, # Add marker to return dict
        'is_list_item': is_list_item,
        'list_type': list_type,
        'list_indent': list_indent, # Placeholder for future nesting use
        'text': text_content.strip(),
        'spans': spans # Pass spans for footnote detection
    }

def _format_pdf_markdown(page: fitz.Page) -> str:
    """
    Generates a Markdown string from a PyMuPDF page object.

    Extracts text blocks, analyzes structure using _analyze_pdf_block,
    and formats the output as Markdown, including basic headings, lists,
    and footnote definitions.

    Args:
        page: A fitz.Page object.

    Returns:
        A string containing the generated Markdown.
    """
    fn_id = None # Initialize to prevent UnboundLocalError
    cleaned_fn_text = "" # Initialize to prevent UnboundLocalError
    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
    markdown_lines = []
    footnote_defs = {} # Store footnote definitions [^id]: content
    current_list_type = None
    list_marker = None # Initialize list_marker
    # list_level = 0 # Basic nesting tracker - deferred

    for block in blocks:
        analysis = _analyze_pdf_block(block)
        text = analysis['text']
        spans = analysis['spans']

        # Cleaning is now done in _analyze_pdf_block
        if not text: continue

        # Footnote Reference/Definition Detection (using superscript flag)
        processed_text_parts = []
        potential_def_id = None
        first_span_in_block = True
        fn_id = None # Initialize fn_id before the span loop
        for span in spans:
            span_text = span.get('text', '')
            flags = span.get('flags', 0)
            is_superscript = flags & 1 # Superscript flag

            if is_superscript and span_text.isdigit():
                fn_id = span_text
                # Definition heuristic: superscript number at start of block, possibly followed by '.' or ')'
                if first_span_in_block and re.match(r"^\d+[\.\)]?\s*", text): # Use 'text' instead of 'text_content'
                    potential_def_id = fn_id
                    # Don't add the number itself to the text for definitions
                else: # Reference
                    processed_text_parts.append(f"[^{fn_id}]")
            else:
                processed_text_parts.append(span_text)
            first_span_in_block = False

        processed_text = "".join(processed_text_parts).strip()

        # Store definition if found, otherwise format content
        if potential_def_id:
            # Store potentially uncleaned text (cleaning moved to final formatting)
            footnote_defs[potential_def_id] = processed_text # Store raw processed text
            continue # Don't add definition block as regular content

        # Format based on analysis
        if analysis['heading_level'] > 0:
            markdown_lines.append(f"{'#' * analysis['heading_level']} {processed_text}")
            current_list_type = None # Reset list context after heading
        elif analysis['is_list_item']:
            # Basic list handling (needs refinement for nesting based on indent)
            # Remove original list marker from text if present
            list_marker = analysis.get('list_marker')
            clean_text = processed_text # Start with original processed text

            if analysis['list_type'] == 'ul' and list_marker:
                # Use regex to remove the specific marker found
                clean_text = re.sub(r"^" + re.escape(list_marker) + r"\s*", "", processed_text).strip()
                markdown_lines.append(f"* {clean_text}")
            elif analysis['list_type'] == 'ol' and list_marker:
                 # Use regex to remove the specific marker found (number/letter/roman + ./))
                clean_text = re.sub(r"^" + re.escape(list_marker) + r"[\.\)]\s*", "", processed_text, flags=re.IGNORECASE).strip()
                # Use the detected marker for the Markdown list item
                markdown_lines.append(f"{list_marker}. {clean_text}")
            current_list_type = analysis['list_type']
        else: # Regular paragraph
            # Only add if it's not empty after processing (e.g., after footnote extraction)
            if processed_text:
                markdown_lines.append(processed_text)
            current_list_type = None # Reset list context

    # Join main content lines with double newlines
    main_content = "\n\n".join(md_line for md_line in markdown_lines if not md_line.startswith("[^")) # Exclude footnote defs for now
    main_content_stripped = main_content.strip() # Store stripped version for checks

    # Format footnote section separately, joining with single newlines
    footnote_block = ""
    if footnote_defs:
        footnote_lines = []
        for fn_id, fn_text in sorted(footnote_defs.items()):
            # Apply regex cleaning directly here
            cleaned_fn_text = re.sub(r"^[^\w]+", "", fn_text).strip()
            footnote_lines.append(f"[^{fn_id}]: {cleaned_fn_text}")
        # Construct the footnote block with correct spacing
        footnote_block = "---\n" + "\n".join(footnote_lines) # Definitions joined by single newline

    # Combine main content and footnote section
    if footnote_block:
        # Add double newline separator only if main content exists and is not empty
        separator = "\n\n" if main_content_stripped else ""
        # Ensure no leading/trailing whitespace on the final combined string
        return (main_content_stripped + separator + footnote_block).strip()
    else:
        # Return only the stripped main content if no footnotes
        return main_content_stripped


# --- EPUB Markdown Helpers ---

def _epub_node_to_markdown(node: BeautifulSoup, footnote_defs: dict, list_level: int = 0) -> str:
    """
    Recursively converts a BeautifulSoup node (from EPUB HTML) to Markdown.
    Handles common HTML tags (headings, p, lists, blockquote, pre) and
    EPUB-specific footnote references/definitions (epub:type="noteref/footnote").
    """
    # Handle plain text nodes directly
    if isinstance(node, NavigableString):
        return str(node) # Return the string content
    markdown_parts = []
    node_name = getattr(node, 'name', None)
    indent = "  " * list_level # Indentation for nested lists
    prefix = '' # Default prefix

    if node_name == 'h1': prefix = '# '
    elif node_name == 'h2': prefix = '## '
    elif node_name == 'h3': prefix = '### '
    elif node_name == 'h4': prefix = '#### '
    elif node_name == 'h5': prefix = '##### '
    elif node_name == 'h6': prefix = '###### '
    elif node_name == 'p': prefix = ''
    elif node_name == 'ul':
        # Handle UL items recursively
        for child in node.find_all('li', recursive=False):
            item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
            if item_text: markdown_parts.append(f"{indent}* {item_text}")
        return "\n".join(markdown_parts) # Return joined list items
    elif node_name == 'nav' and node.get('epub:type') == 'toc':
        # Handle Table of Contents (often uses nested <p><a>...</a></p> or similar)
        for child in node.descendants:
            if getattr(child, 'name', None) == 'a' and child.get_text(strip=True):
                 link_text = child.get_text(strip=True)
                 markdown_parts.append(f"* {link_text}")
        return "\n".join(markdown_parts)
    elif node_name == 'ol':
        # Handle OL items recursively
        for i, child in enumerate(node.find_all('li', recursive=False)):
            item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
            if item_text: markdown_parts.append(f"{indent}{i+1}. {item_text}")
        return "\n".join(markdown_parts)
    elif node_name == 'li':
        # Process content within LI, prefix handled by parent ul/ol
        prefix = ''
    elif node_name == 'blockquote':
        prefix = '> '
    elif node_name == 'pre':
        # Handle code blocks
        code_content = node.get_text()
        return f"```\n{code_content}\n```"
    elif node_name == 'img':
        # Handle images - create placeholder
        src = node.get('src', '')
        alt = node.get('alt', '')
        return f"[Image: {src}/{alt}]" # Placeholder format as per spec/test
    elif node_name == 'table':
        # Basic table handling - extract text content
        # TODO: Implement proper Markdown table conversion later if needed
        return node.get_text(separator=' ', strip=True)
    elif node_name == 'a' and node.get('epub:type') == 'noteref':
        # Footnote reference
        href = node.get('href', '')
        fn_id_match = re.search(r'#ft(\d+)', href) # Example pattern, adjust if needed
        if fn_id_match:
            fn_id = fn_id_match.group(1)
            # Return the reference marker, process siblings/children if any (unlikely for simple ref)
            child_content = "".join(_epub_node_to_markdown(child, footnote_defs, list_level) for child in node.children).strip()
            return f"{child_content}[^{fn_id}]" # Append ref marker
        else:
             # Fallback if pattern doesn't match, process children
             pass # Continue to process children below
    elif node.get('epub:type') == 'footnote':
        # Footnote definition
        fn_id = node.get('id', '')
        fn_id_match = re.search(r'ft(\d+)', fn_id) # Example pattern
        if fn_id_match:
            num_id = fn_id_match.group(1)
            # Extract definition text, excluding the backlink if present
            content_node = node.find('p') or node # Assume content is in <p> or directly in the element
            if content_node:
                # Remove backlink if it exists (common pattern)
                backlink = content_node.find('a', {'epub:type': 'backlink'})
                if backlink: backlink.decompose()
                # Get cleaned text content
                fn_text = content_node.get_text(strip=True)
                footnote_defs[num_id] = fn_text
            return "" # Don't include definition inline
        else:
            # Fallback if ID pattern doesn't match
            pass # Continue to process children below

    # Process children recursively if not handled by specific tag logic above
    child_content = "".join(_epub_node_to_markdown(child, footnote_defs, list_level) for child in node.children).strip()

    # Apply prefix and return, handle block vs inline elements appropriately
    if node_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote']:
        # Block elements get prefix and potential double newline separation handled by caller
        return f"{prefix}{child_content}"
    else:
        # Inline elements just return their content
        return child_content


# --- Helper Functions for Processing ---

def _html_to_text(html_content):
    """Extracts plain text from HTML using BeautifulSoup."""
    if not BeautifulSoup:
        logging.warning("BeautifulSoup not available, cannot extract text from HTML.")
        return ""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        logging.error(f"Error parsing HTML with BeautifulSoup: {e}")
        return "" # Return empty string on parsing error

# --- Preprocessing Helpers ---

def _identify_and_remove_front_matter(content_lines: list[str]) -> tuple[list[str], str]:
    """
    Identifies title (basic heuristic), removes basic front matter lines based on keywords,
    returns cleaned content lines and title. Matches current test expectations.
    """
    logging.debug("Running basic front matter removal and title identification...")
    title = "Unknown Title" # Default title
    cleaned_lines = []

    # --- Basic Title Identification Heuristic ---
    # Look for the first non-empty line within the first ~5 lines
    for line in content_lines[:5]:
        stripped_line = line.strip()
        if stripped_line:
            title = stripped_line
            logging.debug(f"Identified potential title: {title}")
            break # Found the first non-empty line, assume it's the title

    # --- Front Matter Removal Logic ---
    # Define keywords for publisher info, copyright, etc.
    FRONT_MATTER_SKIP_TWO = ["dedication", "copyright notice"] # Skip line + next
    FRONT_MATTER_SKIP_ONE = [
        "copyright", "isbn", "published by", "acknowledgments",
        "cambridge university press", "stanford university press",
        "library of congress", "cataloging in publication",
        "all rights reserved", "printed in", "reprinted",
        "first published", "permissions", "without permission"
    ]

    i = 0
    while i < len(content_lines):
        line = content_lines[i]
        line_lower = line.strip().lower()
        skipped = False

        # Check skip-two keywords first
        if any(keyword in line_lower for keyword in FRONT_MATTER_SKIP_TWO):
            logging.debug(f"Skipping front matter block (2 lines) starting with: {line.strip()}")
            i += 2 # Skip current line and the next line
            skipped = True
        # Check skip-one keywords if not already skipped
        elif any(keyword in line_lower for keyword in FRONT_MATTER_SKIP_ONE):
            logging.debug(f"Skipping single front matter line: {line.strip()}")
            i += 1 # Skip current line only
            skipped = True

        if not skipped:
            # Preserve lines
            cleaned_lines.append(line)
            i += 1

    # Return original lines if filtering removed everything (edge case)
    # Note: This edge case handling might need review if the test changes
    # Ensure a tuple is always returned, even if cleaned_lines is empty
    if not cleaned_lines:
         logging.warning("Front matter removal resulted in empty content.")
         # Return empty list and the identified title
         return [], title

    return cleaned_lines, title

def _format_toc_lines_as_markdown(toc_lines: list[str]) -> str:
    """Formats extracted ToC lines into a Markdown list, handling basic indentation."""
    markdown_list = []
    base_indent = -1 # Track base indentation level

    for line in toc_lines:
        stripped_line = line.strip()
        if not stripped_line: continue # Skip empty lines

        # Basic indentation detection (count leading spaces)
        indent_level = len(line) - len(line.lstrip(' '))
        if base_indent == -1:
            base_indent = indent_level # Set base indent on first non-empty line

        # Calculate relative indent level (simple approach)
        relative_indent = max(0, (indent_level - base_indent) // 2) # Assume 2 spaces per level
        indent_str = "  " * relative_indent
        # Remove page numbers/dots for cleaner Markdown
        text_part = re.sub(r'[\s.]{2,}\d+$', '', stripped_line).strip()
        markdown_list.append(f"{indent_str}* {text_part}")

    return "\n".join(markdown_list)

def _extract_and_format_toc(content_lines: list[str], output_format: str) -> tuple[list[str], str]:
    """
    Extracts Table of Contents (ToC) lines based on heuristics, formats it
    (currently only for Markdown), and returns remaining content lines and formatted ToC.
    """
    logging.debug("Attempting to extract and format Table of Contents...")
    toc_lines = []
    remaining_lines = []
    in_toc = False
    toc_start_index = -1 # Added: Track start of ToC
    toc_end_index = -1
    # main_content_start_index = -1 # Removed: Simplify logic based on toc_end_index

    # Heuristic: Look for common ToC start keywords
    TOC_START_KEYWORDS = ["contents", "table of contents"]
    # Heuristic: Look for lines ending with page numbers (dots or spaces before number)
    # Updated regex to be more specific and avoid matching chapter titles
    TOC_LINE_PATTERN = re.compile(r'^(.*?)[\s.]{2,}(\d+)$') # Non-greedy match for text, require >=2 dots/spaces before number
    # Heuristic: Look for common main content start keywords
    MAIN_CONTENT_START_KEYWORDS = ["introduction", "preface", "chapter 1", "part i"]

    # First pass: Identify potential ToC block
    for i, line in enumerate(content_lines):
        line_lower = line.strip().lower()

        if not in_toc and any(keyword in line_lower for keyword in TOC_START_KEYWORDS):
            in_toc = True
            toc_start_index = i # Record start index
            logging.debug(f"Potential ToC start found at line {i}: {line.strip()}")
            # Don't add the keyword line itself to toc_lines
            continue # Skip the "Contents" line itself

        if in_toc:
            # Check if line matches ToC pattern OR is empty (allow empty lines within ToC)
            is_toc_like = bool(TOC_LINE_PATTERN.match(line.strip())) or not line.strip()
            # Check if line signals start of main content AND doesn't look like a ToC line itself
            is_main_content_start = any(line_lower.startswith(keyword) for keyword in MAIN_CONTENT_START_KEYWORDS) and not is_toc_like

            if is_toc_like and not is_main_content_start:
                # toc_lines.append(line) # Keep original line with indentation - NO, collect indices first
                toc_end_index = i # Track the last potential ToC line index
            # Simplified end condition: if it's not a ToC line, assume ToC ended on the previous line.
            else:
                logging.debug(f"Potential ToC end detected before line {i} (non-matching line): {line.strip()}")
                break # Stop processing ToC lines

    # Determine final content lines based on findings
    if toc_start_index != -1 and toc_end_index != -1 and toc_end_index >= toc_start_index: # Ensure end is after start
        # ToC found: combine lines before start and after end
        remaining_lines = content_lines[:toc_start_index] + content_lines[toc_end_index + 1:]
        # Ensure toc_lines only contains lines within the identified block
        # (Adjust indices relative to the original content_lines)
        actual_toc_start_line_index = toc_start_index + 1 # Line after the keyword
        actual_toc_end_line_index = toc_end_index
        toc_lines = content_lines[actual_toc_start_line_index : actual_toc_end_line_index + 1]

    else:
        # No ToC found or block incomplete, keep all original lines
        remaining_lines = content_lines
        toc_lines = [] # Ensure toc_lines is empty

    logging.debug(f"Identified {len(toc_lines)} ToC lines. {len(remaining_lines)} remaining content lines.")

    # Format ToC only if requested and lines were found
    formatted_toc = "" # Initialize as empty string instead of None
    if output_format == "markdown" and toc_lines:
        formatted_toc = _format_toc_lines_as_markdown(toc_lines)
        logging.debug("Formatted ToC for Markdown output.")

    return remaining_lines, formatted_toc

# --- PDF Quality Analysis ---

def detect_pdf_quality(pdf_path: str) -> dict: # Renamed from _analyze_pdf_quality
    """
    Analyzes a PDF to determine text quality and recommend OCR if needed.

    Returns a dictionary with 'quality_category' ('TEXT_HIGH', 'TEXT_LOW', 'IMAGE_ONLY', 'MIXED', 'EMPTY', 'ENCRYPTED'),
    'ocr_needed' (boolean), and 'reason' (string).
    """
    if not PYMUPDF_AVAILABLE:
        return {'quality_category': 'UNKNOWN', 'ocr_needed': False, 'reason': 'PyMuPDF not available'}

    doc = None
    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            # Try decrypting with empty password
            if not doc.authenticate(""):
                logging.warning(f"PDF {pdf_path} is encrypted and password protected.")
                return {'quality_category': 'ENCRYPTED', 'ocr_needed': False, 'reason': 'PDF is encrypted'}
            logging.info(f"Successfully decrypted {pdf_path} with empty password.")

        page_count = len(doc)
        if page_count == 0:
            logging.warning(f"PDF {pdf_path} has 0 pages.")
            return {'quality_category': 'EMPTY', 'ocr_needed': False, 'reason': 'PDF has no pages'}

        total_chars = 0
        total_image_area = 0
        total_page_area = 0
        unique_chars = set()

        for page in doc:
            page_area = page.rect.width * page.rect.height
            if page_area <= 0: continue # Skip pages with no area

            total_page_area += page_area

            # Text analysis
            text = page.get_text("text")
            page_chars = len(text)
            total_chars += page_chars
            unique_chars.update(text)

            # Image analysis
            # Use page.get_images(full=True) instead of get_image_rects
            img_list = page.get_images(full=True)
            # Img tuple format: (xref, smask, width, height, ...)
            # Calculate area using width (index 2) and height (index 3)
            page_image_area = sum(img[2] * img[3] for img in img_list if len(img) >= 4) # Ensure tuple has enough elements
            total_image_area += page_image_area

        avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
        image_ratio = total_image_area / total_page_area if total_page_area > 0 else 0
        char_diversity_ratio = len(unique_chars) / total_chars if total_chars > 0 else 0
        space_ratio = sum(1 for char in "".join(unique_chars) if char.isspace()) / len(unique_chars) if unique_chars else 0


        # Determine category based on heuristics
        category, reason, ocr_needed = _determine_pdf_quality_category(
            avg_chars_per_page, image_ratio, char_diversity_ratio, space_ratio
        )

        return {'quality_category': category, 'ocr_needed': ocr_needed, 'reason': reason}

    except Exception as e:
        logging.error(f"Error analyzing PDF quality for {pdf_path}: {e}", exc_info=True)
        # Check if error suggests encryption
        if "encrypted" in str(e).lower():
             return {'quality_category': 'ENCRYPTED', 'ocr_needed': False, 'reason': f'Error opening PDF (likely encrypted): {e}'}
        return {'quality_category': 'ERROR', 'ocr_needed': False, 'reason': f'Error analyzing PDF: {e}'}
    finally:
        # Close document if it exists and is not already closed
        if doc is not None and not doc.is_closed:
            doc.close()

def _determine_pdf_quality_category(
    avg_chars: float, img_ratio: float, char_diversity: float, space_ratio: float
) -> tuple[str, str, bool]:
    """Helper function to determine PDF quality category based on metrics."""
    # Check for high image ratio first
    if img_ratio > _PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO:
         # If significant image area, but also some text, classify as MIXED
         # If text quality is also low, still recommend OCR
         ocr_rec = avg_chars < _PDF_QUALITY_THRESHOLD_LOW_DENSITY or \
                   char_diversity < _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO or \
                   space_ratio < _PDF_QUALITY_MIN_SPACE_RATIO
         reason = f'High image ratio ({img_ratio:.2f} > {_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO})'
         if ocr_rec:
             reason += f' and low text quality indicators (avg_chars={avg_chars:.1f}, diversity={char_diversity:.2f}, space={space_ratio:.2f})'
         return 'MIXED', reason, ocr_rec
    # Only check for IMAGE_ONLY if image ratio is not high
    elif avg_chars < _PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY:
        return 'IMAGE_ONLY', f'Very low average characters per page ({avg_chars:.1f} < {_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY})', True
    elif avg_chars < _PDF_QUALITY_THRESHOLD_LOW_DENSITY or \
         char_diversity < _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO or \
         space_ratio < _PDF_QUALITY_MIN_SPACE_RATIO:
        return 'TEXT_LOW', f'Low average characters per page ({avg_chars:.1f} < {_PDF_QUALITY_THRESHOLD_LOW_DENSITY}) or low char diversity ({char_diversity:.2f} < {_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO}) or low space ratio ({space_ratio:.2f} < {_PDF_QUALITY_MIN_SPACE_RATIO})', True
    else:
        return 'TEXT_HIGH', f'Sufficient average characters per page ({avg_chars:.1f}) and low image ratio ({img_ratio:.2f})', False


# --- Garbled Text Detection ---

def detect_letter_spacing_issue(text: str, sample_size: int = 500) -> bool:
    """
    Detects if text has excessive letter spacing (e.g., "T H E" instead of "THE").

    This is a common OCR issue in scanned PDFs where spaces appear between every letter.

    Args:
        text: Text to analyze
        sample_size: Number of characters to sample for analysis

    Returns:
        True if letter spacing issue detected
    """
    if len(text) < 10:  # Lower threshold for short samples
        return False

    # Sample text for analysis (first N characters)
    sample = text[:sample_size] if len(text) > sample_size else text

    # Count words that are single letters (the symptom of letter spacing)
    words = sample.split()
    if len(words) == 0:
        return False

    single_letter_words = sum(1 for word in words if len(word.strip()) == 1 and word.isalpha())

    # Calculate ratio of single-letter words to total words
    ratio = single_letter_words / len(words)

    # If more than 50% of words are single letters, it's likely a spacing issue
    # Lowered threshold to catch "T h e  B o o k" style cases
    if ratio > 0.5:
        logging.debug(f"Letter spacing issue detected: {single_letter_words}/{len(words)} words are single letters ({ratio:.1%})")
        return True

    return False


def correct_letter_spacing(text: str) -> str:
    """
    Corrects excessive letter spacing in OCR text.

    Transforms: "T H E  B U R N O U T" → "THE BURNOUT"

    Algorithm:
    1. Identify sequences of single letters separated by spaces
    2. Collapse them into words
    3. Preserve intentional spacing and punctuation

    Args:
        text: Text with potential letter spacing issues

    Returns:
        Corrected text
    """
    if not text or not detect_letter_spacing_issue(text):
        return text

    logging.info("Applying letter spacing correction...")

    # Split into lines to preserve paragraph structure
    lines = text.split('\n')
    corrected_lines = []

    for line in lines:
        # Pattern explanation:
        # - Matches sequences of single letters with spaces between them
        # - Handles: "T H E", "T h e", "T H E ,", etc.
        # - Captures letters and spaces, excluding punctuation at boundaries
        #
        # Strategy: Find patterns like "X Y Z" where X, Y, Z are single letters
        # This works by looking for: letter + (space + letter) repeated 1+ times

        # First, handle case where letters are separated by single spaces
        # This pattern captures "T H E" or "T h e" style sequences
        corrected_line = line

        # Multiple passes to handle all patterns
        max_iterations = 5
        for _ in range(max_iterations):
            original = corrected_line

            # Pattern: Single letter, space, another single letter (repeated)
            # Matches: "T H E", "T h e", "B O O K", etc.
            # Uses lookbehind and lookahead to avoid word boundaries issues
            corrected_line = re.sub(
                r'(?<!\S)([A-Za-z])(\s+[A-Za-z])+(?!\S)',
                lambda m: m.group(0).replace(' ', ''),
                corrected_line
            )

            # If no changes, we're done
            if corrected_line == original:
                break

        corrected_lines.append(corrected_line)

    corrected_text = '\n'.join(corrected_lines)

    # Clean up any excessive spaces that may have been introduced
    corrected_text = re.sub(r'\s{3,}', '  ', corrected_text)

    logging.info(f"Letter spacing correction complete. Length: {len(text)} → {len(corrected_text)}")
    return corrected_text


def detect_garbled_text(text: str, non_alpha_threshold: float = 0.25, repetition_threshold: float = 0.7, min_length: int = 10) -> bool:
    """
    Detects potentially garbled text based on heuristics like non-alphanumeric ratio
    and character repetition.
    """
    text_length = len(text)
    if text_length < min_length:
        return False # Too short to reliably analyze

    # 1. Non-Alphanumeric Ratio
    non_alpha_count = sum(1 for char in text if not char.isalnum() and not char.isspace())
    non_alpha_ratio = non_alpha_count / text_length
    if non_alpha_ratio > non_alpha_threshold:
        logging.debug(f"Garbled text detected: High non-alpha ratio ({non_alpha_ratio:.2f} > {non_alpha_threshold})")
        return True

    # 2. Character Repetition Ratio
    # Count occurrences of each character (excluding spaces)
    char_counts = collections.Counter(c for c in text if not c.isspace())
    if not char_counts: # Handle case of only spaces
        return False
    most_common_char, most_common_count = char_counts.most_common(1)[0]
    repetition_ratio = most_common_count / (text_length - text.count(' ')) # Ratio based on non-space chars
    if repetition_ratio > repetition_threshold:
        logging.debug(f"Garbled text detected: High repetition ratio ({repetition_ratio:.2f} > {repetition_threshold}) for char '{most_common_char}'")
        return True

    # TODO: Add more heuristics? (e.g., dictionary word check, common pattern matching)

    return False


# --- Main Processing Functions ---

def process_pdf(file_path: Path, output_format: str = "txt") -> str:
    """Processes a PDF file, extracts text, applies preprocessing, and returns content."""
    if not PYMUPDF_AVAILABLE: raise ImportError("Required library 'PyMuPDF' (fitz) is not installed.")
    logging.info(f"Processing PDF: {file_path} for format: {output_format}")
    doc = None
    try:
        # --- Quality Analysis ---
        quality_info = detect_pdf_quality(str(file_path))
        quality_category = quality_info.get("quality_category", "UNKNOWN")
        ocr_needed = quality_info.get("ocr_recommended", False) # Use correct key 'ocr_recommended'

        # --- OCR (if needed and available) ---
        if ocr_needed:
            if OCR_AVAILABLE:
                logging.info(f"Quality analysis ({quality_category}) recommends OCR for {file_path}. Running OCR...")
                try:
                    # Cycle 21 Refactor: Use run_ocr_on_pdf which now uses fitz
                    ocr_text = run_ocr_on_pdf(str(file_path))
                    if ocr_text:
                         logging.info(f"OCR successful for {file_path}.")

                         # Apply letter spacing correction if needed
                         ocr_text = correct_letter_spacing(ocr_text)

                         # Preprocess OCR text (basic for now, can be expanded)
                         try: # Add try block for preprocessing OCR text
                             ocr_lines = ocr_text.splitlines()
                             (cleaned_lines, title) = _identify_and_remove_front_matter(ocr_lines)
                             (final_content_lines, formatted_toc) = _extract_and_format_toc(cleaned_lines, output_format)
                         except Exception as preprocess_err:
                             logging.error(f"Error preprocessing OCR text for {file_path}: {preprocess_err}", exc_info=True)
                             # If preprocessing fails, maybe return raw OCR text or skip?
                             # For now, let's log and proceed to standard extraction by raising the error
                             # to be caught by the outer OCR exception handler.
                             # Re-raise to ensure it's caught by the main handler below
                             raise RuntimeError(f"Error preprocessing OCR text: {preprocess_err}") from preprocess_err

                         # Construct output similar to standard processing
                         final_output_parts = []
                         if title != "Unknown Title":
                             final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
                         if formatted_toc: # Only add ToC if Markdown requested
                             final_output_parts.append(formatted_toc)
                         main_content = "\n".join(final_content_lines)
                         final_output_parts.append(main_content.strip())
                         # Return *inside* the if ocr_text block to prevent fall-through
                         return "\n\n".join(part for part in final_output_parts if part)
                    else:
                         logging.warning(f"OCR run for {file_path} but returned no text. Proceeding with standard extraction.")
                except OCRDependencyError as ocr_dep_err:
                     logging.warning(f"OCR skipped for {file_path}: {ocr_dep_err}")
                     raise ocr_dep_err # Re-raise to prevent fall-through
                except TesseractNotFoundError as tess_err: # Catch specific error instance
                     logging.warning(f"OCR skipped for {file_path}: Tesseract not found or not in PATH.")
                     raise tess_err # Re-raise specific error
                except Exception as ocr_err:
                     logging.error(f"Error during OCR or OCR preprocessing for {file_path}: {ocr_err}", exc_info=True)
                     # Re-raise the original error if it came from preprocessing, otherwise wrap
                     if isinstance(ocr_err, RuntimeError) and "Error preprocessing OCR text" in str(ocr_err):
                         raise ocr_err # Re-raise the specific preprocessing error
                     else:
                         raise RuntimeError(f"OCR or preprocessing failed: {ocr_err}") from ocr_err
            else:
                logging.warning(f"OCR needed for {file_path} ({quality_category}), but dependencies (pytesseract/pdf2image/PIL) are not installed. Skipping OCR.")

        # --- Standard Extraction (if OCR not needed OR if OCR failed during preprocessing) ---
        logging.debug(f"Performing standard PDF extraction for {file_path}...")
        doc = fitz.open(str(file_path))
        if doc.is_encrypted:
            logging.warning(f"PDF {file_path} is encrypted.")
            if not doc.authenticate(""):
                raise ValueError(f"PDF {file_path} is encrypted and cannot be opened.")
            logging.info(f"Successfully decrypted {file_path} with empty password.")

        # 1. Extract structured content using block-level analysis
        logging.debug("Performing structured PDF extraction with block analysis...")
        page_count = len(doc)
        page_contents = []  # Store content with page numbers

        for i, page in enumerate(doc):
            page_num = i + 1
            logging.debug(f"Processing page {page_num}/{page_count} with block analysis...")

            if output_format == "markdown":
                # Use sophisticated _format_pdf_markdown for structure preservation
                page_markdown = _format_pdf_markdown(page)
                if page_markdown:
                    # Add page marker for academic citations (no backticks - they render as code)
                    page_with_marker = f"[p.{page_num}]\n\n{page_markdown}"
                    page_contents.append(page_with_marker)
            else:
                # For plain text, use basic extraction
                page_text = page.get_text("text")
                if page_text:
                    # Add page marker
                    page_with_marker = f"[Page {page_num}]\n\n{page_text}"
                    page_contents.append(page_with_marker)

        # 2. Combine all pages
        full_content = "\n\n".join(page_contents)

        # 2.5. Apply letter spacing correction if needed (for digital-native PDFs too)
        if detect_letter_spacing_issue(full_content[:1000]):
            logging.info("Applying letter spacing correction to PDF content...")
            full_content = correct_letter_spacing(full_content)

        # 3. Preprocess the content (front matter, ToC extraction)
        # For structured markdown, we already have good structure, just extract front matter
        content_lines = full_content.splitlines()
        (lines_after_fm, title) = _identify_and_remove_front_matter(content_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

        # 4. Construct final output
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines)
        final_output_parts.append(main_content.strip())
        final_output = "\n\n".join(part for part in final_output_parts if part).strip()

        # Close doc before returning
        if doc is not None and not doc.is_closed:
            doc.close()
            logging.debug(f"Closed PDF document before return: {file_path}")
        return final_output

    except Exception as fitz_err: # Broaden exception type for PyMuPDF errors
        # Check if the error originated from the OCR/preprocessing block
        if isinstance(fitz_err, (OCRDependencyError, TesseractNotFoundError, RuntimeError)) and \
           ("OCR" in str(fitz_err) or "Tesseract" in str(fitz_err)):
             logging.error(f"Re-raising OCR-related error for {file_path}: {fitz_err}", exc_info=True)
             raise fitz_err # Re-raise the original OCR-related error to stop execution

        # Check if it's likely an encryption error first
        # Use isinstance to check for ValueError which might indicate encryption
        elif "encrypted" in str(fitz_err).lower() or isinstance(fitz_err, ValueError):
             logging.error(f"PyMuPDF/Value error processing encrypted PDF {file_path}: {fitz_err}", exc_info=True)
             raise ValueError(f"PDF {file_path} is encrypted and cannot be opened.") from fitz_err
        else: # Handle other PyMuPDF or general errors
             logging.error(f"PyMuPDF/Other error processing {file_path}: {fitz_err}", exc_info=True)
             # Use RuntimeError for broader fitz errors or other exceptions
             raise RuntimeError(f"Error opening or processing PDF {file_path}: {fitz_err}") from fitz_err
    # Removed the separate ValueError and Exception catches as they are covered above.
    finally:
        # Close document if it exists and is not already closed
        # Note: PyMuPDF's __len__() raises ValueError when closed, so we can't use 'if doc:'
        if doc is not None and not doc.is_closed:
            doc.close()
            logging.debug(f"Closed PDF document: {file_path}")


def process_epub(file_path: Path, output_format: str = "txt") -> str:
    """Processes an EPUB file, extracts text, applies preprocessing, and returns content."""
    if not EBOOKLIB_AVAILABLE: raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB: {file_path} for format: {output_format}")

    logging.debug(f"Attempting to read EPUB: {file_path}")
    try:
        logging.debug("Successfully opened EPUB file.")
        book = epub.read_epub(str(file_path))
        all_lines = []
        footnote_defs = {} # Collect footnote definitions across items

        # --- Extract Content (HTML) ---
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        logging.debug(f"Found {len(items)} items of type ITEM_DOCUMENT.")

        section_counter = 0
        for item in items:
            section_counter += 1
            logging.debug(f"Processing item: {item.get_name()}")
            try:
                content = item.get_content()
                if isinstance(content, bytes):
                    # Attempt decoding with common encodings
                    try:
                        html_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            html_content = content.decode('latin-1')
                        except UnicodeDecodeError:
                            logging.warning(f"Could not decode content from item {item.get_name()} in {file_path}. Skipping.")
                            continue
                # If not skipped, proceed with processing
                else: # Assume it's already a string
                    html_content = content

                if not html_content: continue

                # Add section marker for academic citations
                item_name = item.get_name()
                if output_format == "markdown":
                    section_marker = f"`[section.{section_counter}: {item_name}]`\n"
                    all_lines.append(section_marker)
                else:
                    section_marker = f"[Section {section_counter}: {item_name}]\n"
                    all_lines.append(section_marker)

                logging.debug(f"Converting item {item.get_name()} content to {output_format}...")
                # --- Convert HTML to Text or Markdown ---
                try: # Add try block around conversion
                    if output_format == "markdown":
                        logging.debug(f"Item {item.get_name()}: Converting HTML to Markdown...")
                        soup = BeautifulSoup(html_content, 'html.parser')
                        body = soup.find('body')
                        if body:
                            # Process body content, collecting footnote definitions
                            item_markdown = _epub_node_to_markdown(body, footnote_defs)
                            # Append footnote definitions collected from this item
                            # (Footnote formatting happens at the end)
                            all_lines.extend(item_markdown.splitlines())
                        else:
                             logging.warning(f"No <body> tag found in item {item.get_name()}. Skipping.")
                    else: # Default to text
                        logging.debug(f"Item {item.get_name()}: Extracting plain text from HTML...")
                        item_text = _html_to_text(html_content)
                        if item_text:
                            all_lines.extend(item_text.splitlines())
                except Exception as conversion_err:
                     logging.error(f"Error converting content from item {item.get_name()} in {file_path}: {conversion_err}", exc_info=True)
                     # Optionally add a placeholder or skip the item
                     all_lines.append(f"[Error processing item {item.get_name()}]")

            except Exception as item_err:
                logging.error(f"Error reading content from item {item.get_name()} in {file_path}: {item_err}", exc_info=True)
                all_lines.append(f"[Error reading item {item.get_name()}]")

        # --- Preprocessing ---
        logging.debug("Starting EPUB preprocessing (front matter, ToC)...")
        (lines_after_fm, title) = _identify_and_remove_front_matter(all_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines) # Join preprocessed lines
        final_output_parts.append(main_content.strip())

        # Append formatted footnote definitions if output is markdown
        if output_format == "markdown" and footnote_defs:
            footnote_block_lines = ["---"]
            for fn_id, fn_text in sorted(footnote_defs.items()):
                footnote_block_lines.append(f"[^{fn_id}]: {fn_text}")
            final_output_parts.append("\n".join(footnote_block_lines))

        return "\n\n".join(part for part in final_output_parts if part).strip()

    except Exception as e:
        logging.error(f"Error processing EPUB {file_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error processing EPUB {file_path}: {e}") from e


async def process_txt(file_path: Path, output_format: str = "txt") -> str:
    """Processes a TXT file, applies preprocessing, and returns content."""
    logging.info(f"Processing TXT: {file_path}")
    try:
        try:
            # Try reading as UTF-8 first
            async def read_utf8():
                 async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                     return await f.readlines()
            content_lines = await read_utf8() # Await async read
        except UnicodeDecodeError:
            logging.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
            try:
                async def read_latin1():
                     async with aiofiles.open(file_path, mode='r', encoding='latin-1') as f:
                         return await f.readlines()
                content_lines = await read_latin1() # Await async read
            except Exception as read_err:
                 logging.error(f"Failed to read {file_path} with fallback encoding: {read_err}")
                 raise IOError(f"Could not read file {file_path}") from read_err
        except Exception as read_err:
             logging.error(f"Failed to read {file_path}: {read_err}")
             raise IOError(f"Could not read file {file_path}") from read_err

        # --- Preprocessing ---
        logging.debug("Starting TXT preprocessing (front matter, ToC)...")
        (lines_after_fm, title) = _identify_and_remove_front_matter(content_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines)
        final_output_parts.append(main_content.strip())

        return "\n\n".join(part for part in final_output_parts if part).strip()

    except Exception as e:
        logging.error(f"Error processing TXT {file_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error processing TXT {file_path}: {e}") from e


# --- OCR Function ---

def run_ocr_on_pdf(pdf_path: str, lang: str = 'eng') -> str: # Cycle 21 Refactor: Add lang parameter
    """
    Performs OCR on a PDF file using Tesseract via PyMuPDF rendering.

    Args:
        pdf_path: Path to the PDF file.
        lang: Language code for Tesseract (e.g., 'eng').

    Returns:
        Extracted text content as a single string.

    Raises:
        OCRDependencyError: If required OCR dependencies are not installed.
        TesseractNotFoundError: If Tesseract executable is not found.
        RuntimeError: For other processing errors.
    """
    if not OCR_AVAILABLE:
        raise OCRDependencyError("OCR dependencies (pytesseract, pdf2image, Pillow) not installed.")
    if not PYMUPDF_AVAILABLE:
        raise OCRDependencyError("PyMuPDF (fitz) is required for OCR rendering but not installed.")

    logging.info(f"Running OCR on {pdf_path} with language '{lang}'...")
    extracted_text = ""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        logging.debug(f"PDF has {page_count} pages.")

        for i, page in enumerate(doc):
            page_num = i + 1
            logging.debug(f"Processing page {page_num}/{page_count} for OCR...")
            try:
                # Render page to pixmap, then to PNG bytes
                pix = page.get_pixmap(dpi=300) # Higher DPI for better OCR
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))

                # Perform OCR on the image
                page_text = pytesseract.image_to_string(img, lang=lang)
                extracted_text += page_text + "\n\n" # Add page separator
                logging.debug(f"OCR successful for page {page_num}.")
            # Specific exception must come BEFORE generic Exception
            except TesseractNotFoundError as tess_err:
                 logging.error(f"Tesseract not found during OCR on page {page_num}: {tess_err}")
                 raise # Re-raise to be caught by outer handler
            except Exception as page_err:
                 logging.error(f"Error during OCR on page {page_num}: {page_err}", exc_info=True)
                 # Continue to next page if one fails? Or raise? Let's continue for now.
                 extracted_text += f"[OCR Error on Page {page_num}]\n\n"

        logging.info(f"OCR completed for {pdf_path}. Total extracted length: {len(extracted_text)}")
        return extracted_text.strip()

    # Removed redundant outer TesseractNotFoundError catch, inner loop handler re-raises.
    # Catch specific PyMuPDF file opening errors or other RuntimeErrors
    except RuntimeError as fitz_err:
         logging.error(f"PyMuPDF/Runtime error during OCR preparation for {pdf_path}: {fitz_err}", exc_info=True)
         raise RuntimeError(f"PyMuPDF/Runtime error during OCR: {fitz_err}") from fitz_err
    except Exception as e: # General catch for other unexpected errors
        logging.error(f"Unexpected error during OCR for {pdf_path}: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected OCR error: {e}") from e
    finally:
        # Close document if it exists and is not already closed
        if doc is not None and not doc.is_closed:
            doc.close()


# --- File Saving ---

async def process_document(file_path_str: str, output_format: str = "txt", book_details: dict = None) -> dict:
    """
    Processes a document (PDF, EPUB, TXT) based on its extension,
    extracts text, applies preprocessing, saves it, and returns the path.
    """
    if book_details is None: # Ensure book_details is a dict for _slugify
        book_details = {}

    file_path = Path(file_path_str)
    file_extension = file_path.suffix.lower()
    processed_text = ""

    logging.info(f"Processing document: {file_path} with format {output_format}")

    try:
        if file_extension == '.pdf':
            processed_text = await asyncio.to_thread(process_pdf, file_path, output_format)
        elif file_extension == '.epub':
            if not EBOOKLIB_AVAILABLE:
                raise ImportError("Required library 'ebooklib' is not installed or available for EPUB processing.")
            processed_text = await asyncio.to_thread(process_epub, file_path, output_format)
        elif file_extension == '.txt':
            processed_text = await process_txt(file_path, output_format) # process_txt is already async
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

        if processed_text is None or not processed_text.strip():
            logging.warning(f"No text extracted from {file_path}")
            # Return None for path if no content, but keep content list for consistency
            return {"processed_file_path": None, "content": []}

        # Save the processed text with metadata
        # Determine corrections applied (for metadata)
        corrections = []
        if file_extension == '.pdf':
            # Check if letter spacing correction was applied
            if detect_letter_spacing_issue(processed_text[:500]):
                corrections.append("letter_spacing_correction")

        # Pass book_details to save_processed_text for filename generation
        # This also generates and saves the metadata sidecar
        saved_path = await save_processed_text(
            original_file_path=file_path,
            processed_content=processed_text,
            output_format=output_format, # This should be the format of the processed_text (e.g. 'md' or 'txt')
            book_details=book_details,
            ocr_quality_score=None,  # TODO: Calculate if OCR was used
            corrections_applied=corrections
        )

        # Determine metadata file path
        from filename_utils import create_metadata_filename
        processed_filename = Path(saved_path).name
        metadata_filename = create_metadata_filename(processed_filename)
        metadata_path = PROCESSED_OUTPUT_DIR / metadata_filename

        # Return ONLY paths, not content (prevents MCP token overflow)
        # User can selectively read portions of the processed file
        return {
            "processed_file_path": str(saved_path),
            "metadata_file_path": str(metadata_path) if metadata_path.exists() else None,
            "stats": {
                "word_count": len(processed_text.split()),
                "char_count": len(processed_text),
                "format": output_format
            }
        }

    except Exception as e:
        logging.error(f"Error processing document {file_path}: {e}")
        # Re-raise as a RuntimeError to be caught by the bridge's main error handler
        raise RuntimeError(f"Error processing document {file_path}: {e}") from e
async def save_processed_text(
    original_file_path: str,
    processed_content: str,
    output_format: str = "txt",
    book_details: dict | None = None, # Added book_details for slug
    ocr_quality_score: float | None = None, # For metadata
    corrections_applied: list | None = None # For metadata
) -> str:
    """Saves the processed text content to a file in the output directory."""
    try:
        original_path = Path(original_file_path)
        original_filename = original_path.stem
        original_extension = original_path.suffix.lower()

        # --- Generate Filename using unified format ---
        if book_details:
            # Use unified filename generation
            base_name = create_unified_filename(book_details, extension=None)
            processed_filename = f"{base_name}{original_extension}.processed.{output_format}"
        else:
            # Fallback if no book_details
            base_name = _slugify(original_filename)
            processed_filename = f"{base_name}{original_extension}.processed.{output_format}"

        # --- Ensure Output Directory Exists ---
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = PROCESSED_OUTPUT_DIR / processed_filename

        # --- Write Content Asynchronously (NO YAML frontmatter) ---
        # Main markdown should be CLEAN for RAG (only content + page markers)
        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            await f.write(processed_content)

        logging.info(f"Successfully saved processed content to: {output_path}")

        # --- Generate and Save Metadata Sidecar ---
        if book_details:
            try:
                format_type = original_path.suffix.lower().lstrip('.')

                # Generate metadata
                metadata = generate_metadata_sidecar(
                    original_filename=str(original_path),
                    processed_content=processed_content,  # Use processed_content, not final_content
                    book_details=book_details,
                    ocr_quality_score=ocr_quality_score,
                    corrections_applied=corrections_applied or [],
                    format_type=format_type,
                    output_format=output_format
                )

                # Save metadata sidecar
                metadata_filename = create_metadata_filename(processed_filename)
                metadata_path = PROCESSED_OUTPUT_DIR / metadata_filename
                save_metadata_sidecar(metadata, metadata_path)

                logging.info(f"Successfully saved metadata sidecar to: {metadata_path}")
            except Exception as meta_err:
                logging.warning(f"Failed to generate metadata sidecar: {meta_err}")
                # Don't fail the whole operation if metadata generation fails

        return str(output_path) # Return the string representation of the path

    except ValueError as ve: # Catch the specific error for None content
         logging.error(f"ValueError during save: {ve}")
         # Construct a meaningful path for the error message if possible
         unknown_path = PROCESSED_OUTPUT_DIR / f"{_slugify(original_path.stem)}.processed.{output_format}"
         raise FileSaveError(f"Failed to save processed text to {unknown_path}: {ve}") from ve
    except OSError as ose:
        logging.error(f"OS error saving processed file: {ose}")
        # Construct a meaningful path for the error message if possible
        failed_path = PROCESSED_OUTPUT_DIR / processed_filename if 'processed_filename' in locals() else "unknown_processed_file"
        raise FileSaveError(f"Failed to save processed file due to OS error: {ose}") from ose
    except Exception as e:
        logging.error(f"Unexpected error saving processed file: {e}", exc_info=True)
        failed_path = PROCESSED_OUTPUT_DIR / processed_filename if 'processed_filename' in locals() else "unknown_processed_file"
        raise FileSaveError(f"Unexpected error saving processed file {failed_path}: {e}") from e