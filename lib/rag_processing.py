import re
import logging
from pathlib import Path
import aiofiles
import unicodedata # Added for slugify
import os # Ensure os is imported if needed for path manipulation later

# Check if libraries are available
# OCR Dependencies (Optional)
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None
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

# Constants
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf'] # Keep relevant constants? Or import? Keep for now.
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
        potential_def_id = None # Initialize potential_def_id for each block
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
    markdown_toc_lines = []
    for original_line in toc_lines: # Iterate over original lines
        # Remove trailing dots/spaces and page number from the stripped version
        line_strip = original_line.strip()
        # Regex to remove trailing dots/spaces and page number
        cleaned_line = re.sub(r'\s*[\.\s]+\s*\d+$', '', line_strip).strip()
        if not cleaned_line: continue # Skip empty lines after cleaning

        # Basic indentation check using the original line
        indent_level = 0
        if original_line.startswith('  '): # Check original line for indentation
            indent_level = 1
        # TODO: Add more robust indentation detection if needed (e.g., multiples of 2 spaces)

        # Format as Markdown list item
        indent_str = "  " * indent_level
        markdown_toc_lines.append(f"{indent_str}* {cleaned_line}")

    return "\n".join(markdown_toc_lines)
# NEW _extract_and_format_toc implementation (V2 - Index Based)
def _extract_and_format_toc(content_lines: list[str], output_format: str) -> tuple[list[str], str]:
    """
    (Basic V2) Identifies ToC based on keywords and simple line format,
    formats it (placeholder), returns remaining content lines and formatted ToC.
    Uses index-based approach.
    """
    logging.debug("Running basic ToC extraction (V2)...")
    toc_lines_extracted = []
    formatted_toc = ""
    toc_start_index = -1
    toc_end_index = -1 # Index *after* the last ToC line
    main_content_start_index = -1

    TOC_KEYWORDS = ["contents", "table of contents"]
    TOC_LINE_PATTERN = re.compile(r'.+\s[\.\s]+\s*\d+$')
    MAIN_CONTENT_START_KEYWORDS = ["chapter", "part ", "introduction", "prologue"]

    # Find ToC start
    for i, line in enumerate(content_lines):
        line_lower = line.strip().lower()
        if any(keyword in line_lower for keyword in TOC_KEYWORDS):
            toc_start_index = i
            logging.debug(f"Found ToC keyword at index {i}: {line.strip()}")
            break

    # If no ToC keyword found, return original lines
    if toc_start_index == -1:
        logging.debug("No ToC keyword found.")
        return content_lines, formatted_toc

    # Find start of main content *after* ToC keyword
    for i in range(toc_start_index + 1, len(content_lines)):
        line = content_lines[i]
        line_lower = line.strip().lower()
        # Check if line starts with a keyword AND does NOT look like a ToC entry
        if any(line_lower.startswith(keyword) for keyword in MAIN_CONTENT_START_KEYWORDS) and not TOC_LINE_PATTERN.match(line.strip()):
            main_content_start_index = i
            logging.debug(f"Found main content start at index {i}: {line.strip()}")
            break

    # Determine ToC end index
    if main_content_start_index != -1:
        toc_end_index = main_content_start_index
    else:
        toc_end_index = len(content_lines) # Assume ToC goes to end if no keyword found
        logging.debug("No main content start keyword found after ToC, assuming ToC runs to end.")


    # Extract ToC lines (excluding the header line itself)
    if toc_end_index > toc_start_index + 1:
         # Filter lines within the identified range that match the pattern
         for i in range(toc_start_index + 1, toc_end_index):
             original_line = content_lines[i] # Store original line
             line_strip = original_line.strip()
             # Include blank lines within ToC block based on test case
             # Store the original line to preserve indentation for formatting
             if TOC_LINE_PATTERN.match(line_strip) or not line_strip:
                 toc_lines_extracted.append(original_line) # Append original line


    # Construct remaining lines
    remaining_lines = content_lines[:toc_start_index] + content_lines[toc_end_index:]

    # Format ToC using the helper function if requested and lines were extracted
    if output_format == 'markdown' and toc_lines_extracted:
        formatted_toc = _format_toc_lines_as_markdown(toc_lines_extracted)

    logging.debug(f"Finished ToC extraction (V2). Found {len(toc_lines_extracted)} ToC lines. Formatted TOC length: {len(formatted_toc)}")
    return remaining_lines, formatted_toc

# --- PDF Processing ---
def _analyze_pdf_quality(pdf_path: str) -> dict:
    # ... (implementation as before) ...
    if not PYMUPDF_AVAILABLE:
        logging.warning("PyMuPDF not available, skipping PDF quality analysis.")
        return {'quality': 'unknown', 'details': 'PyMuPDF not installed'}
    total_text_length = 0
    text_length_threshold = 50 # Reverting threshold
    doc = None
    full_text_content = ""
    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted, cannot analyze quality: {pdf_path}")
            return {'quality': 'unknown', 'details': 'PDF is encrypted'}
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Extract text and clean null chars immediately
            text = page.get_text("text", flags=0).replace('\x00', '').strip()
            total_text_length += len(text)
            full_text_content += text # Add cleaned text
            if total_text_length >= text_length_threshold: break
    except FileNotFoundError:
        logging.error(f"PDF file not found for quality analysis: {pdf_path}")
        return {'quality': 'error', 'details': 'File not found'}
    except Exception as e:
        logging.error(f"Error analyzing PDF quality for {pdf_path}: {e}")
        return {'quality': 'error', 'details': f'PyMuPDF error: {e}'}
    finally:
        if doc: doc.close()
    if total_text_length < text_length_threshold:
        logging.info(f"PDF detected as potentially image-only (text length {total_text_length}): {pdf_path}")
        return {'quality': 'image_only', 'details': 'No significant text found', 'ocr_recommended': True}
    # Using Spec thresholds with OR condition
    MIN_CHAR_DIVERSITY_RATIO = 0.15
    MIN_SPACE_RATIO = 0.05
    # MIN_AVG_WORD_LEN = 2.5 # Not using avg word length

    if full_text_content:
        # Apply header/footer cleaning before analysis
        cleaned_analysis_text = full_text_content
        header_footer_patterns = [
             re.compile(r"^(JSTOR.*|Downloaded from.*|Copyright ©.*)\n?", re.IGNORECASE | re.MULTILINE),
             re.compile(r"^Page \d+\s*\n?", re.MULTILINE),
             re.compile(r"^(.*\bPage \d+\b.*)\n?", re.IGNORECASE | re.MULTILINE), # Copied from process_pdf
             # Commenting out more specific JSTOR/boilerplate patterns
             # re.compile(r"^Source:.*\n?", re.IGNORECASE | re.MULTILINE),
             # re.compile(r"^Published by:.*\n?", re.IGNORECASE | re.MULTILINE),
             # re.compile(r"^Stable URL:.*\n?", re.IGNORECASE | re.MULTILINE),
             # re.compile(r"^Your use of the JSTOR archive.*\n?", re.IGNORECASE | re.MULTILINE),
             # re.compile(r"^is collaborating with JSTOR.*\n?", re.IGNORECASE | re.MULTILINE),
             # re.compile(r"^The Massachusetts Review\n?", re.IGNORECASE | re.MULTILINE), # Already commented out
        ]
        for pattern in header_footer_patterns:
            cleaned_analysis_text = pattern.sub('', cleaned_analysis_text)
        # Commenting out specific cleaning for JSTOR download/terms lines
        # download_pattern = re.compile(r"This content downloaded from.*?\n", re.IGNORECASE)
        # cleaned_analysis_text = download_pattern.sub('', cleaned_analysis_text)
        # terms_pattern = re.compile(r"All use subject to https://about.jstor.org/terms\n?", re.IGNORECASE)
        # cleaned_analysis_text = terms_pattern.sub('', cleaned_analysis_text)
        cleaned_analysis_text = re.sub(r'\n\s*\n', '\n\n', cleaned_analysis_text).strip() # Consolidate blank lines

        # Perform analysis on cleaned text
        non_whitespace_chars = ''.join(cleaned_analysis_text.split())
        total_chars = len(cleaned_analysis_text) # Need total_chars for space_ratio
        total_non_whitespace = len(non_whitespace_chars)
        unique_non_whitespace = len(set(non_whitespace_chars))
        space_count = cleaned_analysis_text.count(' ') # Use cleaned text for space count
        char_diversity_ratio = (unique_non_whitespace / total_non_whitespace) if total_non_whitespace > 0 else 0
        space_ratio = (space_count / total_chars) if total_chars > 0 else 0

        # Check based on low diversity OR low space ratio (using spec thresholds)
        if total_non_whitespace > 10: # Keep minimum text check
            if char_diversity_ratio < MIN_CHAR_DIVERSITY_RATIO or space_ratio < MIN_SPACE_RATIO:
                details = f"Low char diversity ({char_diversity_ratio:.2f} < {MIN_CHAR_DIVERSITY_RATIO}) or low space ratio ({space_ratio:.2f} < {MIN_SPACE_RATIO})" # Using spec thresholds
                logging.info(f"PDF detected as potentially poor extraction ({details}): {pdf_path}")
                # Using updated details string consistent with the OR condition
                return {'quality': 'poor_extraction', 'details': 'Low character diversity or low space ratio detected', 'ocr_recommended': True}
    logging.debug(f"PDF quality analysis: Passed checks. Path: {pdf_path}")
    return {'quality': 'good'}

def process_pdf(file_path: Path, output_format: str = "txt") -> str:
    """Processes a PDF file, extracts text, applies preprocessing, and returns content."""
    if not PYMUPDF_AVAILABLE: raise ImportError("Required library 'PyMuPDF' is not installed.")
    logging.info(f"Processing PDF: {file_path} for format: {output_format}")

    # --- Start: Quality Analysis and Conditional OCR ---
    quality_analysis = _analyze_pdf_quality(str(file_path))
    if quality_analysis.get('ocr_recommended'):
        logging.info(f"Quality analysis ({quality_analysis.get('quality')}) recommends OCR for {file_path}. Running OCR...")
        # Ensure run_ocr_on_pdf is called with the correct path object or string
        return run_ocr_on_pdf(str(file_path))
    # --- End: Quality Analysis ---

    # If quality is good or unknown (and OCR not forced), proceed with normal extraction
    logging.info(f"PDF quality ({quality_analysis.get('quality')}) deemed sufficient or OCR not recommended. Proceeding with standard extraction for {file_path}")

    doc = None
    all_lines = []
    try:
        doc = fitz.open(str(file_path))
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted: {file_path}")
            raise ValueError("PDF is encrypted")

        # 1. Extract all text lines first
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                text = page.get_text("text")
                if text:
                    # Basic cleaning and split into lines
                    cleaned_page_text = text.replace('\x00', '')
                    all_lines.extend(cleaned_page_text.splitlines())
            except Exception as page_e:
                logging.error(f"Error processing page {page_num} of PDF {file_path}: {page_e}")
                # Continue processing other pages

        if not all_lines:
            logging.warning(f"No text could be extracted from PDF: {file_path}")
            return "" # Return empty if no text extracted

        # 2. Apply front matter removal
        lines_after_fm, title = _identify_and_remove_front_matter(all_lines)
        logging.debug(f"PDF Title identified: {title}")

        # 3. Apply ToC extraction
        remaining_lines, formatted_toc = _extract_and_format_toc(lines_after_fm, output_format)

        # 4. Combine results
        # NOTE: Current approach joins preprocessed lines. For 'markdown' output,
        # this bypasses the detailed _format_pdf_markdown function which operates page-by-page.
        # TODO: Refactor PDF processing to apply preprocessing *before* page-level Markdown formatting.
        main_content = "\n".join(remaining_lines)

        # Prepend ToC if it exists and format is markdown
        if formatted_toc and output_format == 'markdown':
            # Add separator between ToC and main content
            final_output = f"## Table of Contents\n\n{formatted_toc}\n\n---\n\n{main_content}"
        else:
            final_output = main_content

        return final_output.strip()

    except fitz.fitz.FitzError as fitz_e: # Catch specific PyMuPDF errors
        logging.error(f"PyMuPDF error processing PDF {file_path}: {fitz_e}")
        raise RuntimeError(f"Failed to process PDF: {fitz_e}") from fitz_e
    except ValueError as val_e: # Catch encryption error
         logging.error(f"Value error processing PDF {file_path}: {val_e}")
         raise val_e
    except Exception as e:
        logging.error(f"Unexpected error processing PDF {file_path}: {e}")
        raise RuntimeError(f"Unexpected error processing PDF: {e}") from e
    finally:
        if doc:
            doc.close()

# --- EPUB Processing ---

def process_epub(file_path: Path, output_format: str = "txt") -> str:
    """Processes an EPUB file, extracts text, applies preprocessing, and returns content."""
    if not EBOOKLIB_AVAILABLE:
        raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB: {file_path} for format: {output_format}")

    try:
        book = epub.read_epub(str(file_path))
        all_lines = []
        footnote_defs = {} # For Markdown footnote collection

        # Basic text extraction (simplistic for integration step)
        # TODO: Refine this to use _epub_node_to_markdown for proper formatting later
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        for item in items:
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            # Extract text, split into lines
            text = soup.get_text(separator='\n', strip=True)
            if text:
                all_lines.extend(text.splitlines())

        # --- End of for item in items loop ---

        if not all_lines:
            logging.warning(f"No text could be extracted from EPUB: {file_path}")
            return ""

        # Apply front matter removal
        lines_after_fm, title = _identify_and_remove_front_matter(all_lines)
        logging.debug(f"EPUB Title identified: {title}")

        # Apply ToC extraction
        remaining_lines, formatted_toc = _extract_and_format_toc(lines_after_fm, output_format)

        # Combine results (simple join for now)
        # NOTE: Current approach joins preprocessed lines. For 'markdown' output,
        # this bypasses the detailed _epub_node_to_markdown function which operates node-by-node.
        # TODO: Refactor EPUB processing to apply preprocessing *before* node-level Markdown formatting.
        main_content = "\n".join(remaining_lines)

        # Prepend ToC if it exists and format is markdown
        if formatted_toc and output_format == 'markdown':
            final_output = f"## Table of Contents\n\n{formatted_toc}\n\n---\n\n{main_content}"
        else:
            final_output = main_content

        return final_output.strip()

    except FileNotFoundError: # Corrected indentation
        logging.error(f"EPUB file not found: {file_path}")
        raise
    except Exception as e: # Corrected indentation
        logging.error(f"Error processing EPUB {file_path}: {e}")
        # Consider more specific exceptions from ebooklib if needed
        raise RuntimeError(f"Failed to process EPUB: {e}") from e

# --- OCR Processing ---

def run_ocr_on_pdf(pdf_path: str) -> str:
    """
    Runs OCR on a given PDF file and returns the extracted text.
    Requires pytesseract and pdf2image.
    """
    if not OCR_AVAILABLE:
        logging.error("OCR dependencies (pytesseract, pdf2image) not installed. Cannot run OCR.")
        return "" # Return empty string if dependencies are missing

    logging.info(f"Running OCR on: {pdf_path}")
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path)
        
        full_text = ""
        # Process each image with pytesseract
        for i, image in enumerate(images):
            logging.debug(f"Running OCR on page {i+1} of {pdf_path}")
            try:
                page_text = pytesseract.image_to_string(image)
                full_text += page_text + "\n\n" # Add page separator
            except pytesseract.TesseractNotFoundError:
                 logging.warning("Tesseract is not installed or not in your PATH. OCR failed.") # Changed to warning to match test mock
                 # Return empty string as per test_run_ocr_on_pdf_handles_tesseract_not_found expectation
                 return ""
            except Exception as ocr_err:
                 logging.error(f"Error during OCR processing on page {i+1} of {pdf_path}: {ocr_err}")
                 # Optionally continue to next page or return partial result/error indicator
                 # For now, continue to next page
                 continue

        logging.info(f"OCR completed for {pdf_path}. Extracted length: {len(full_text)}")
        return full_text.strip()

    except Exception as e:
        logging.error(f"Error converting PDF to images for OCR ({pdf_path}): {e}")
        # Handle pdf2image errors (e.g., file not found, poppler issues)
        return "" # Return empty string on conversion error

# Removed duplicated block
# Removing duplicated except clauses
async def save_processed_text(
    original_file_path: Path,
    text_content: str,
    output_format: str = "txt",
    book_id: str = None,
    author: str = None,
    title: str = None
) -> Path:
    # ... (implementation as before) ...
    output_filename = "unknown_processed_file"
    try:
        if text_content is None: raise ValueError("Cannot save None content.")
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        original_stem = original_file_path.stem
        _, original_ext = os.path.splitext(original_file_path.name)
        output_extension = f".{output_format.lower()}"
        if book_id and author and title:
            author_slug = _slugify(author)
            title_slug = _slugify(title)
            slug = f"{author_slug}-{title_slug}"
            max_slug_len = 100
            if len(slug) > max_slug_len:
                slug = slug[:max_slug_len]
                if '-' in slug: slug = slug.rsplit('-', 1)[0]
            output_filename = f"{slug}-{book_id}{output_extension}"
        else:
            output_filename = f"{original_stem}.processed{output_extension}"
            logging.warning(f"Metadata (author, title, book_id) missing for {original_file_path}. Using fallback filename: {output_filename}")
        output_path = PROCESSED_OUTPUT_DIR / output_filename
        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            await f.write(text_content)
        logging.info(f"Processed text saved to: {output_path}")
        return output_path
    except OSError as e:
        logging.error(f"OS error saving processed file {output_path}: {e}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}") from e
    except Exception as e:
        logging.exception(f"Failed to save processed text for {original_file_path}")
        raise FileSaveError(f"Failed to save processed text to {output_filename}: {e}") from e