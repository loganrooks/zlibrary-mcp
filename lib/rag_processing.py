import re
import logging
from pathlib import Path
import aiofiles
import unicodedata # Added for slugify
import os # Ensure os is imported if needed for path manipulation later
import io # Added for OCR image handling
import string # Added for garbled text detection
import collections # Added for garbled text detection

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

# Define placeholder initially, overwrite if import succeeds
# class TesseractNotFoundError(Exception): pass # Already defined above

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
            # Reordered to check more specific conditions first
            if font_size > 12 and font_size <= 14 and is_bold: # H3 (Adjusted condition slightly for clarity)
                 heading_level = 3
            elif font_size > 11 and font_size <= 12 and is_bold: # H3 (Adjusted condition slightly for clarity)
                 heading_level = 3
            elif font_size > 14 and font_size <= 18 and is_bold: # H2
                 heading_level = 2
            elif font_size > 12 and font_size <= 14: # H3
                 heading_level = 3
            elif font_size > 14 and font_size <= 18: # H2
                 heading_level = 2
            elif font_size > 18: # H1
                 heading_level = 1
            # TODO: Consider adding more levels or refining based on document analysis.

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
        # potential_def_id = None # Removed duplicate initialization
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
            # Clean the definition text (remove the initial marker if present and any leading punctuation)
            # cleaned_def_text = re.sub(r"^\d+[\.\)]?\s*", "", processed_text).strip() # Original cleaning attempt, now done later
            # Store potentially uncleaned text (cleaning moved to final formatting)
            footnote_defs[potential_def_id] = processed_text # Store raw processed text
            continue # Don't add definition block as regular content

        # Format based on analysis (REMOVED REDUNDANT BLOCK)
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

    # Append footnote definitions at the end
    # Footnote definitions are handled separately below
    # if footnote_defs:
        # markdown_lines.append("---") # REMOVED: Separator added later during footnote_block construction
        # for fn_id, fn_text in sorted(footnote_defs.items()):
            # Apply regex cleaning directly here (Reverted to original regex as lstrip wasn't the issue)
            # cleaned_fn_text = re.sub(r"^[^\w]+", "", fn_text).strip()
            # markdown_lines.append(f"[^{fn_id}]: {cleaned_fn_text}") # Corrected variable name

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
    # Keywords requiring specific handling based on test_remove_front_matter_basic
    FRONT_MATTER_KEYWORDS_SINGLE = ["copyright", "isbn", "published by"]
    FRONT_MATTER_KEYWORDS_MULTI = ["dedication"] # Skips this line and the next
    FRONT_MATTER_KEYWORDS_HEADER_ONLY = ["acknowledgments"] # Skips this line only

    i = 0
    while i < len(content_lines):
        line = content_lines[i]
        line_lower = line.strip().lower()
        skipped = False

        # Check multi-line removal keywords
        if any(keyword in line_lower for keyword in FRONT_MATTER_KEYWORDS_MULTI):
            logging.debug(f"Removing multi-line front matter starting at: {line.strip()}")
            i += 2 # Skip current line and next line
            skipped = True
        # Check header-only removal keywords
        elif any(keyword in line_lower for keyword in FRONT_MATTER_KEYWORDS_HEADER_ONLY):
             logging.debug(f"Removing front matter header line: {line.strip()}")
             i += 1 # Skip current line only
             skipped = True
        # Check single-line removal keywords
        elif any(keyword in line_lower for keyword in FRONT_MATTER_KEYWORDS_SINGLE):
            logging.debug(f"Removing single front matter line: {line.strip()}")
            i += 1 # Skip current line only
            skipped = True

        if not skipped:
            # Preserve blank lines as they appear in the test's expected output
            cleaned_lines.append(line)
            i += 1

    # Return original lines if filtering removed everything (edge case)
    # Note: This edge case handling might need review if the test changes
    if not cleaned_lines and content_lines:
         logging.warning("Front matter removal filtered out all content, returning original.")
         return content_lines, title

    return cleaned_lines, title

def _format_toc_lines_as_markdown(toc_lines: list[str]) -> str:
    """Formats extracted ToC lines into a Markdown list."""
    markdown_list = []
    # Basic formatting, assuming simple list structure for now
    # TODO: Add nesting based on indentation/numbering patterns if needed
    for line in toc_lines:
        # Basic cleaning: remove leading/trailing whitespace and potential page numbers at the end
        cleaned_line = re.sub(r'\s+\.?\s*\d+$', '', line).strip()
        if cleaned_line:
            # Simple bullet point for now
            markdown_list.append(f"* {cleaned_line}")
    return "\n".join(markdown_list)

def _extract_and_format_toc(content_lines: list[str], output_format: str) -> tuple[list[str], str]:
    """
    Identifies ToC lines using keywords and basic structure heuristics,
    formats it (if Markdown), returns remaining content lines and formatted ToC.
    """
    logging.debug("Running basic ToC extraction...")
    toc_lines = []
    remaining_lines = []
    in_toc = False
    toc_found = False
    # Keywords to identify potential start of ToC
    TOC_KEYWORDS = ["contents", "table of contents"]
    # Keywords/patterns to identify potential end of ToC or start of main content
    END_TOC_PATTERNS = [
        re.compile(r"^(chapter|part|section|introduction)\s+\d+", re.IGNORECASE),
        re.compile(r"^(prologue|epilogue|appendix)", re.IGNORECASE),
        # Add more patterns if needed based on common book structures
    ]

    # --- ToC Identification Heuristic ---
    i = 0
    while i < len(content_lines):
        line = content_lines[i]
        line_strip = line.strip()
        line_lower = line_strip.lower()

        if not toc_found and any(keyword in line_lower for keyword in TOC_KEYWORDS):
            in_toc = True
            toc_found = True
            logging.debug(f"Potential ToC start found: {line_strip}")
            # Skip the header line itself
            i += 1
            continue

        if in_toc:
            # Check for end patterns
            if any(pattern.match(line_strip) for pattern in END_TOC_PATTERNS):
                logging.debug(f"Potential ToC end found at: {line_strip}")
                in_toc = False
                remaining_lines.append(line) # Add the line that ended the ToC
            # Basic check for ToC entry format (text ... number) or just text
            elif re.search(r'.+\s+\.?\s*\d+$', line_strip) or (line_strip and not line_strip.isdigit()):
                 # Check if it looks like a ToC line (has text, maybe ends in number)
                 # Avoid adding lines that are just page numbers
                 if not line_strip.isdigit():
                     toc_lines.append(line_strip)
                 else:
                     # If it's just a number, it might be the end or noise
                     logging.debug(f"Skipping potential ToC line (just digits): {line_strip}")
                     # Heuristic: If we see multiple digit-only lines, maybe end ToC? Needs refinement.
            else: # Assume end of ToC if format breaks significantly or line is empty
                logging.debug(f"Potential ToC end found (format break/empty): {line_strip}")
                in_toc = False
                remaining_lines.append(line) # Add the line that ended the ToC
        else:
            remaining_lines.append(line)
        i += 1

    formatted_toc = ""
    if toc_found and output_format == "markdown":
        logging.debug(f"Formatting {len(toc_lines)} extracted ToC lines as Markdown.")
        formatted_toc = _format_toc_lines_as_markdown(toc_lines)

    return remaining_lines, formatted_toc


def detect_pdf_quality(pdf_path: str) -> dict: # Renamed from _analyze_pdf_quality
    """
    Analyzes a PDF file using PyMuPDF to determine its quality category.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A dictionary containing:
        - 'quality': Category ('TEXT_HIGH', 'TEXT_LOW', 'IMAGE_ONLY', 'MIXED', 'EMPTY', 'ENCRYPTED', 'ERROR')
        - 'details': A string explaining the reason.
        - 'ocr_recommended': Boolean indicating if OCR is suggested.
    """
    if not PYMUPDF_AVAILABLE:
        logging.error("PyMuPDF (fitz) is not installed. Cannot analyze PDF quality.")
        return {'quality': 'ERROR', 'details': 'PyMuPDF library not available.'}

    doc = None
    try:
        doc = fitz.open(pdf_path)

        # Check for empty PDF first
        total_pages = len(doc)
        if total_pages == 0:
            logging.warning(f"PDF has 0 pages: {pdf_path}")
            return {'quality': 'EMPTY', 'details': 'PDF has 0 pages.'}

        # Then check for encryption
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted: {pdf_path}")
            return {'quality': 'ENCRYPTED', 'details': 'PDF is encrypted.'}

        total_text_chars = 0
        total_image_area = 0
        total_page_area = 0
        unique_chars = set()

        for page_num in range(total_pages):
            page = doc.load_page(page_num)

            # Text Analysis
            text = page.get_text("text", flags=0) # Basic text extraction
            page_text_len = len(text.strip())
            total_text_chars += page_text_len
            unique_chars.update(text.strip())

            # Image Analysis
            images = page.get_images(full=True)
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            if page_area > 0:
                total_page_area += page_area
                page_image_area = 0
                for img_info in images:
                    xref = img_info[0]
                    try:
                        img_rects = page.get_image_rects(xref) # Find where image is placed
                        for rect in img_rects:
                            page_image_area += rect.width * rect.height
                    except ValueError as e:
                        logging.warning(f"Could not get rect for image xref {xref} on page {page_num} of {pdf_path}: {e}")
                total_image_area += page_image_area

        # Calculate overall metrics
        avg_chars_per_page = total_text_chars / total_pages if total_pages > 0 else 0
        avg_image_ratio = total_image_area / total_page_area if total_page_area > 0 else 0
        char_diversity = len(unique_chars) / total_text_chars if total_text_chars > 0 else 0
        space_count = sum(1 for char in unique_chars if char.isspace()) # Count spaces in unique chars
        space_ratio = space_count / len(unique_chars) if unique_chars else 0

        # Determine category using helper function
        return _determine_pdf_quality_category(
            avg_chars_per_page, avg_image_ratio, char_diversity, space_ratio, total_text_chars, pdf_path
        )

    except Exception as e:
        logging.error(f"Error analyzing PDF quality for {pdf_path}: {e}")
        return {'quality': 'ERROR', 'details': f'Error during analysis: {e}'}
    finally:
        if doc: doc.close()

def _determine_pdf_quality_category(
    avg_chars_per_page: float,
    avg_image_ratio: float,
    char_diversity: float,
    space_ratio: float,
    total_chars: int,
    pdf_path: str # For logging
) -> dict:
    """Determines the PDF quality category based on calculated metrics."""

    # Determine category based on heuristics (Order: IMAGE_ONLY -> MIXED -> TEXT_LOW -> TEXT_HIGH)
    is_very_low_density = avg_chars_per_page < _PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY
    is_low_density = avg_chars_per_page < _PDF_QUALITY_THRESHOLD_LOW_DENSITY
    is_high_image_ratio = avg_image_ratio > _PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO
    is_poor_extraction = char_diversity < _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO or space_ratio < _PDF_QUALITY_MIN_SPACE_RATIO

    if is_very_low_density: # IMAGE_ONLY: Primarily based on very low text density
        logging.info(f"PDF detected as IMAGE_ONLY (Very Low Density): {pdf_path}")
        return {'quality': 'IMAGE_ONLY', 'details': f'Very low average characters per page ({avg_chars_per_page:.1f} < {_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY})', 'ocr_recommended': True}
    elif is_high_image_ratio: # MIXED: High image ratio but wasn't IMAGE_ONLY
        details = f'High average image ratio ({avg_image_ratio:.2f} > {_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO})'
        logging.info(f"PDF detected as MIXED ({details}): {pdf_path}")
        return {'quality': 'MIXED', 'details': details}
    elif is_poor_extraction and total_chars > 10: # TEXT_LOW (Poor Extraction): Low quality text, wasn't IMAGE_ONLY or MIXED
         details = f"Low char diversity ({char_diversity:.2f} < {_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO}) or low space ratio ({space_ratio:.2f} < {_PDF_QUALITY_MIN_SPACE_RATIO})"
         logging.info(f"PDF detected as TEXT_LOW ({details}): {pdf_path}")
         return {'quality': 'TEXT_LOW', 'details': details + ' detected', 'ocr_recommended': True}
    elif is_low_density: # TEXT_LOW (Low Density): Low density, wasn't IMAGE_ONLY, MIXED, or Poor Extraction
        details = f'Low average characters per page ({avg_chars_per_page:.1f} < {_PDF_QUALITY_THRESHOLD_LOW_DENSITY})'
        logging.info(f"PDF detected as TEXT_LOW ({details}): {pdf_path}")
        return {'quality': 'TEXT_LOW', 'details': details, 'ocr_recommended': True} # Recommend OCR for low density too
    else: # Default to TEXT_HIGH
        logging.info(f"PDF detected as TEXT_HIGH: {pdf_path}")
        return {'quality': 'TEXT_HIGH', 'details': 'Sufficient text density and low image ratio detected'}

# --- Garbled Text Detection ---

import re
import logging # Added import
from collections import Counter
def detect_garbled_text(text: str, non_alpha_threshold: float = 0.3, repetition_threshold: float = 0.7, min_length: int = 10) -> bool: # Lowered thresholds further
    """
    Detects potentially garbled text based on simple heuristics.


    Args:
        text: The input text string.
        non_alpha_threshold: Ratio of non-alphanumeric (excluding space) chars to trigger garbled.
        repetition_threshold: Ratio of the most frequent character to trigger garbled.
        min_length: Minimum length to apply heuristics (shorter strings are assumed not garbled).

    Returns:
        True if the text is likely garbled, False otherwise.
    """
    if not text or len(text) < min_length:
        return False # Too short to analyze reliably

    text_length = len(text)
    alphanumeric_chars = 0
    non_alphanum_chars = 0 # Count non-alphanumeric, excluding spaces

    # Calculate alphanumeric ratio (excluding spaces)
    for char in text:
        if char.isalnum():
            alphanumeric_chars += 1
        elif not char.isspace():
            non_alphanum_chars += 1

    total_non_space_chars = alphanumeric_chars + non_alphanum_chars
    non_alpha_ratio = 0.0
    if total_non_space_chars > 0:
        non_alpha_ratio = non_alphanum_chars / total_non_space_chars
        # logging.debug(f"Non-alpha ratio: {non_alpha_ratio:.2f} (Threshold: {non_alpha_threshold})") # Removed Debug log
        if non_alpha_ratio > non_alpha_threshold:
            # logging.debug(f"Garbled text detected (non-alpha ratio)") # Removed Debug log
            return True

    # Check for high repetition
    repetition_ratio = 0.0
    if text_length > 0:
        char_counts = Counter(text)
        # Removed the 'if char_counts:' check as Counter handles empty strings
        most_common_char_count = char_counts.most_common(1)[0][1] if char_counts else 0
        repetition_ratio = most_common_char_count / text_length
        # logging.debug(f"Repetition ratio: {repetition_ratio:.2f} (Threshold: {repetition_threshold})") # Removed Debug log
        if repetition_ratio > repetition_threshold:
            # logging.debug(f"Garbled text detected (repetition ratio)") # Removed Debug log
            return True

    # Removed the simple common letter frequency check for now
    # logging.debug(f"Text not detected as garbled. NonAlphaRatio={non_alpha_ratio:.2f}, RepetitionRatio={repetition_ratio:.2f}") # Removed Debug log
    return False # Default to not garbled if no heuristics triggered
    whitespace_chars = 0
    char_counts = collections.Counter(text)

    for char in text:
        if char.isalnum():
            alphanumeric_chars += 1
        elif char.isspace():
            whitespace_chars += 1
        else:
            non_alphanum_chars += 1

    # Heuristic 1: High ratio of non-alphanumeric characters (excluding whitespace)
    relevant_length = text_length - whitespace_chars
    if relevant_length > 0:
        non_alpha_ratio = non_alphanum_chars / relevant_length
        if non_alpha_ratio > non_alpha_threshold:
            logging.debug(f"Garbled text detected: High non-alpha ratio ({non_alpha_ratio:.2f} > {non_alpha_threshold})")
            return True

    # Heuristic 2: High repetition of a single character
    if char_counts:
        most_common_char_count = char_counts.most_common(1)[0][1]
        repetition_ratio = most_common_char_count / text_length
        if repetition_ratio > repetition_threshold:
            logging.debug(f"Garbled text detected: High repetition ratio ({repetition_ratio:.2f} > {repetition_threshold})")
            return True

    # Add more heuristics if needed (e.g., vowel ratio, common word frequency)

    return False # Default to not garbled


# --- Main Processing Functions ---

def process_pdf(file_path: Path, output_format: str = "txt") -> str:
    """Processes a PDF file, extracts text, applies preprocessing, and returns content."""
    if not PYMUPDF_AVAILABLE: raise ImportError("Required library 'PyMuPDF' is not installed.")
    logging.info(f"Processing PDF: {file_path} for format: {output_format}")

    # --- Start: Quality Analysis and Conditional OCR ---
    quality_analysis = detect_pdf_quality(str(file_path)) # Already updated, ensuring context match
    quality_category = quality_analysis.get('quality', 'UNKNOWN') # Get category

    # Handle ERROR/UNKNOWN/ENCRYPTED from quality check before deciding on OCR
    if quality_category in ['ERROR', 'UNKNOWN', 'ENCRYPTED', 'EMPTY']:
         logging.warning(f"PDF quality analysis returned {quality_category} for {file_path}. Cannot process further.")
         # Return empty string or raise error? Returning empty for now.
         return ""

    if quality_analysis.get('ocr_recommended'):
        logging.info(f"Quality analysis ({quality_category}) recommends OCR for {file_path}. Running OCR...")
        try:
            # Ensure run_ocr_on_pdf is called with the correct path object or string
            return run_ocr_on_pdf(str(file_path))
        except OCRDependencyError as dep_err:
             logging.error(f"OCR dependency error for {file_path}: {dep_err}. Cannot perform OCR.")
             # Fallback: Attempt standard extraction even if OCR was recommended but failed due to deps
             logging.warning(f"Falling back to standard extraction for {file_path} after OCR dependency error.")
        except Exception as ocr_run_err:
             logging.error(f"Error running OCR for {file_path}: {ocr_run_err}. Cannot perform OCR.")
             # Fallback: Attempt standard extraction
             logging.warning(f"Falling back to standard extraction for {file_path} after OCR runtime error.")

    # --- End: Quality Analysis ---

    # If quality is good or unknown (and OCR not forced/failed), proceed with normal extraction
    logging.info(f"Proceeding with standard extraction for {file_path} (Quality: {quality_category})")

    doc = None
    all_lines = []
    try:
        doc = fitz.open(str(file_path))
        # Re-check encryption just in case, though detect_pdf_quality should handle it
        if doc.is_encrypted:
            raise ValueError("PDF is encrypted.") # Raise error if encrypted here

        # --- Preprocessing ---
        extracted_lines = []
        if output_format == "markdown":
            for page in doc:
                extracted_lines.extend(_format_pdf_markdown(page).splitlines())
        else: # Default to text
            for page in doc:
                extracted_lines.extend(page.get_text("text", flags=0).splitlines())

        (cleaned_lines, title) = _identify_and_remove_front_matter(extracted_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(cleaned_lines, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        # Join main content lines appropriately
        if output_format == "markdown":
             # Markdown formatting already handled joining paragraphs etc.
             # Need to reconstruct from lines, respecting potential double newlines
             main_content = "\n".join(final_content_lines) # Basic join for now
             # Refine joining later if needed to preserve paragraph breaks better
        else:
             main_content = "\n".join(final_content_lines)

        final_output_parts.append(main_content.strip())

        return "\n\n".join(part for part in final_output_parts if part) # Join sections with double newline

    except fitz.fitz.FitzError as fitz_err: # Catch specific PyMuPDF errors
        logging.error(f"PyMuPDF error processing {file_path}: {fitz_err}")
        raise RuntimeError(f"PyMuPDF error: {fitz_err}") from fitz_err
    except ValueError as val_err: # Catch encryption error
        logging.error(f"ValueError processing {file_path}: {val_err}")
        raise # Re-raise encryption error
    except Exception as e:
        logging.error(f"Unexpected error processing PDF {file_path}: {e}")
        raise RuntimeError(f"Unexpected PDF processing error: {e}") from e
    finally:
        if doc: doc.close()


def process_epub(file_path: Path, output_format: str = "txt") -> str:
    """Processes an EPUB file, extracts text, applies preprocessing, and returns content."""
    if not EBOOKLIB_AVAILABLE: raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB: {file_path} for format: {output_format}")

    try:
        book = epub.read_epub(str(file_path))
        all_lines = []
        footnote_defs = {} # Collect footnote definitions across items

        # --- Extract Content (HTML) ---
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        for item in items:
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
                else: # Assume it's already a string
                    html_content = content

                if not html_content: continue

                # --- Convert HTML to Text or Markdown ---
                if output_format == "markdown":
                    soup = BeautifulSoup(html_content, 'html.parser')
                    body = soup.find('body')
                    if body:
                         # Process body content node by node
                         md_content = "\n".join(
                             _epub_node_to_markdown(child, footnote_defs).strip()
                             for child in body.children if child.name # Process only tags
                         ).strip()
                         # Consolidate multiple newlines created by block elements
                         md_content = re.sub(r'\n{3,}', '\n\n', md_content)
                         all_lines.extend(md_content.splitlines())
                else: # Default to text
                    text_content = _html_to_text(html_content)
                    all_lines.extend(text_content.splitlines())

            except Exception as item_err:
                 logging.warning(f"Error processing item {item.get_name()} in {file_path}: {item_err}. Skipping item.")

        # --- Preprocessing ---
        (cleaned_lines, title) = _identify_and_remove_front_matter(all_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(cleaned_lines, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        # Join main content lines appropriately
        main_content = "\n".join(final_content_lines) # Basic join for now
        final_output_parts.append(main_content.strip())

        # Append footnote definitions if output is Markdown
        if output_format == "markdown" and footnote_defs:
            footnote_block = "---\n" + "\n".join(
                f"[^{fn_id}]: {fn_text}" for fn_id, fn_text in sorted(footnote_defs.items())
            )
            final_output_parts.append(footnote_block)

        return "\n\n".join(part for part in final_output_parts if part) # Join sections

    except ebooklib.epub.EpubException as epub_err:
        logging.error(f"Ebooklib error processing {file_path}: {epub_err}")
        raise RuntimeError(f"Ebooklib error: {epub_err}") from epub_err
    except Exception as e:
        logging.error(f"Unexpected error processing EPUB {file_path}: {e}")
        raise RuntimeError(f"Unexpected EPUB processing error: {e}") from e


def process_txt(file_path: Path, output_format: str = "txt") -> str:
    """Processes a TXT file, applies preprocessing, and returns content."""
    logging.info(f"Processing TXT: {file_path} for format: {output_format}")
    try:
        # Attempt decoding with UTF-8 first, then fallback
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
        except UnicodeDecodeError:
            logging.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    all_lines = f.readlines()
            except Exception as enc_err:
                 logging.error(f"Failed to decode {file_path} with fallback encoding: {enc_err}")
                 raise RuntimeError(f"File decoding error: {enc_err}") from enc_err

        # --- Preprocessing ---
        # Strip newline characters from each line before preprocessing
        all_lines_stripped = [line.rstrip('\n\r') for line in all_lines]
        (cleaned_lines, title) = _identify_and_remove_front_matter(all_lines_stripped)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(cleaned_lines, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            # TXT output doesn't get Markdown heading
            final_output_parts.append(title)
        if formatted_toc and output_format == "markdown": # Only add ToC if Markdown requested
            final_output_parts.append(formatted_toc)

        # Join main content lines
        main_content = "\n".join(final_content_lines)
        final_output_parts.append(main_content.strip())

        # No footnote processing for TXT
        return "\n\n".join(part for part in final_output_parts if part) # Join sections

    except FileNotFoundError:
        logging.error(f"TXT file not found: {file_path}")
        raise
    except Exception as e:
        logging.error(f"Error processing TXT {file_path}: {e}")
        raise RuntimeError(f"TXT processing error: {e}") from e


def run_ocr_on_pdf(pdf_path: str, lang: str = 'eng') -> str: # Cycle 21 Refactor: Add lang parameter
    """
    Runs OCR on a PDF using Tesseract via pytesseract and pdf2image.
    Handles potential dependency errors and Tesseract execution errors.

    Args:
        pdf_path: Path to the PDF file.
        lang: Language code for Tesseract (default 'eng').

    Returns:
        Aggregated text extracted via OCR.

    Raises:
        OCRDependencyError: If required libraries (pytesseract, pdf2image, PIL) are not installed.
        RuntimeError: If Tesseract executable is not found or other runtime errors occur.
    """
    if not OCR_AVAILABLE:
        raise OCRDependencyError("OCR dependencies (pytesseract, pdf2image, Pillow) not installed.")

    try:
        # Check for Tesseract executable before processing
        pytesseract.get_tesseract_version()
    except TesseractNotFoundError as e:
         logging.error(f"Tesseract executable not found: {e}. Please install Tesseract.")
         # Raise a more informative error or handle as needed
         raise RuntimeError(f"Tesseract not found: {e}") from e

    aggregated_text = []
    doc = None
    try:
        # Use pdf2image to convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=300) # Use pdf2image

        for i, image in enumerate(images):
            page_num = i + 1
            try:
                # Use pytesseract to OCR the image
                page_text = pytesseract.image_to_string(image, lang=lang)
                if page_text:
                    aggregated_text.append(page_text.strip())
            except TesseractNotFoundError as e: # Catch specific error here too
                 logging.warning(f"Tesseract not found during processing page {page_num} of {pdf_path}: {e}. Check installation.")
                 # Re-raise or handle - re-raising for now
                 raise RuntimeError(f"Tesseract not found during processing: {e}") from e
            except Exception as ocr_error:
                logging.warning(f"OCR failed for page {page_num} of {pdf_path}: {ocr_error}")
                # Optionally: Add placeholder text like "[OCR Failed for Page]"

    except Exception as e:
        # Catch errors from convert_from_path or other issues
        logging.error(f"Error during OCR preparation/conversion for {pdf_path}: {e}")
        raise RuntimeError(f"OCR processing failed: {e}") from e
    finally:
        # pdf2image doesn't require explicit closing like fitz
        pass

    return "\n\n".join(aggregated_text).strip()


# --- File Saving Helper ---

async def save_processed_text(
    original_file_path: Path,
    text_content: str | None,
    output_format: str = "txt",
    book_id: str | None = None,
    author: str | None = None,
    title: str | None = None,
    max_slug_len: int = 100 # Added max length for slug
) -> Path:
    """Saves the processed text content to a file in the output directory."""
    if text_content is None:
        # Raise a specific error if content is None
        raise FileSaveError(f"Failed to save processed text to unknown_processed_file: Cannot save None content.")

    try:
        # Create filename
        if author and title and book_id:
            # Generate slug from author and title
            author_slug = _slugify(author)
            title_slug = _slugify(title)
            full_slug = f"{author_slug}-{title_slug}"

            # Truncate slug if too long, ensuring it doesn't cut mid-word if possible
            if len(full_slug) > max_slug_len:
                truncated = full_slug[:max_slug_len]
                # Try to cut at the last hyphen before the limit
                last_hyphen = truncated.rfind('-')
                if last_hyphen > max_slug_len // 2: # Avoid cutting too short
                    full_slug = truncated[:last_hyphen]
                else:
                    full_slug = truncated # Cut hard if no good hyphen found

            filename = f"{full_slug}-{book_id}.{output_format}"
        else:
            # Fallback filename if metadata is missing
            base_name = original_file_path.stem
            filename = f"{base_name}.processed.{output_format}"

        # Ensure output directory exists
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Construct final path
        final_path = PROCESSED_OUTPUT_DIR / filename

        # Write content asynchronously
        async with aiofiles.open(final_path, mode='w', encoding='utf-8') as f:
            await f.write(text_content)

        logging.info(f"Processed text saved to: {final_path}")
        return final_path

    except ValueError as ve: # Catch the specific ValueError from None content check
         logging.error(f"Error saving processed text: {ve}")
         raise FileSaveError(f"Failed to save processed text to {filename if 'filename' in locals() else 'unknown_processed_file'}: {ve}") from ve
    except OSError as e:
        logging.error(f"OS error saving processed file {filename if 'filename' in locals() else 'unknown'}: {e}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}") from e
    except Exception as e:
        logging.error(f"Unexpected error saving processed file {filename if 'filename' in locals() else 'unknown'}: {e}")
        raise FileSaveError(f"Unexpected error saving processed file: {e}") from e