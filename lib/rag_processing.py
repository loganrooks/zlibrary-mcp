import re
import logging
from pathlib import Path
import aiofiles
import unicodedata # Added for slugify
import os # Ensure os is imported if needed for path manipulation later

# Check if libraries are available
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    BeautifulSoup = None # Define as None if not available

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
    if not html_content: return ""
    # Use lxml if available, fallback to html.parser
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser')
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def process_epub(file_path: Path, output_format: str = "txt") -> str:
    """Processes an EPUB file to extract text or generate Markdown."""
    if not EBOOKLIB_AVAILABLE:
        raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB file: {file_path} for format: {output_format}")
    book = epub.read_epub(str(file_path))
    all_content = []
    footnote_defs = {} # For Markdown

    items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    for item in items:
        content = item.get_content()
        if content:
            try:
                html_content = content.decode('utf-8', errors='ignore')
                if output_format == 'markdown':
                    # Use lxml if available, fallback to html.parser
                    try:
                        soup = BeautifulSoup(html_content, 'lxml')
                    except:
                        soup = BeautifulSoup(html_content, 'html.parser')
                    # Process body content, skipping script/style
                    body = soup.find('body')
                    if body:
                         # Pass footnote_defs dict to collect definitions
                        markdown_text = _epub_node_to_markdown(body, footnote_defs) # Assumes _epub_node_to_markdown exists
                        if markdown_text: all_content.append(markdown_text)
                else: # Default to text
                    text = _html_to_text(html_content)
                    if text: all_content.append(text)
            except Exception as e:
                logging.warning(f"Could not decode/process item {item.get_name()} in {file_path}: {e}")

    # Join content with double newlines for paragraphs
    full_content = "\n\n".join(all_content).strip()

    # Append footnotes if generating Markdown
    if output_format == 'markdown' and footnote_defs:
        footnote_block_lines = ["---"]
        for fn_id, fn_text in sorted(footnote_defs.items()):
             # Basic cleaning for footnote definition text
            cleaned_fn_text = re.sub(r"^[^\w]+", "", fn_text).strip()
            footnote_block_lines.append(f"[^{fn_id}]: {cleaned_fn_text}")
        # Add separator only if there's main content
        if full_content:
            full_content += "\n\n" + "\n".join(footnote_block_lines)
        else:
            full_content = "\n".join(footnote_block_lines)


    logging.info(f"Finished EPUB: {file_path}. Format: {output_format}. Length: {len(full_content)}")
    return full_content

def process_txt(file_path: Path) -> str:
    """Processes a TXT file. Returns text string."""
    # Note: TXT processing doesn't have a separate Markdown path in the spec
    logging.info(f"Processing TXT file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f: text = f.read()
        logging.info(f"Finished TXT (UTF-8): {file_path}. Length: {len(text)}")
        return text
    except UnicodeDecodeError:
        logging.warning(f"UTF-8 failed for {file_path}. Trying 'latin-1'.")
        try:
            with open(file_path, 'r', encoding='latin-1') as f: text = f.read()
            logging.info(f"Finished TXT (latin-1): {file_path}. Length: {len(text)}")
            return text
        except Exception as e:
            logging.error(f"Failed to read TXT {file_path} even with latin-1: {e}")
            raise RuntimeError(f"Failed to read TXT file {file_path}: {e}") from e
    except Exception as e:
        logging.error(f"Failed to read TXT file {file_path}: {e}")
        raise RuntimeError(f"Failed to read TXT file {file_path}: {e}") from e

def _analyze_pdf_quality(pdf_path: str) -> dict:
    """
    Analyzes PDF quality.
    Checks for image-only content, poor text extraction, etc.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A dictionary describing the PDF quality.
        Example: {'quality': 'good'}
                 {'quality': 'image_only', 'details': 'No significant text found'}
                 {'quality': 'poor_extraction', 'details': 'Low character diversity or gibberish detected'}
    """
    if not PYMUPDF_AVAILABLE:
        logging.warning("PyMuPDF not available, skipping PDF quality analysis.")
        return {'quality': 'unknown', 'details': 'PyMuPDF not installed'}

    total_text_length = 0
    text_length_threshold = 50 # Characters threshold to consider it image-only

    doc = None
    try:
        doc = fitz.open(pdf_path)
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted, cannot analyze quality: {pdf_path}")
            return {'quality': 'unknown', 'details': 'PDF is encrypted'}

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Extract plain text, ignoring formatting flags for simple length check
            text = page.get_text("text", flags=0).strip()
            total_text_length += len(text)
            # Optimization: If we exceed threshold early, no need to check further pages
            if total_text_length >= text_length_threshold:
                 break # Exit loop early if enough text is found

    except FileNotFoundError:
        logging.error(f"PDF file not found for quality analysis: {pdf_path}")
        # Return an error status if file not found
        return {'quality': 'error', 'details': 'File not found'}
    except Exception as e:
        # Catch potential PyMuPDF errors during opening or processing
        logging.error(f"Error analyzing PDF quality for {pdf_path}: {e}")
        return {'quality': 'error', 'details': f'PyMuPDF error: {e}'}
    finally:
        if doc:
            doc.close() # Ensure the document is closed

    # Check if text length is below threshold
    if total_text_length < text_length_threshold:
        logging.info(f"PDF detected as potentially image-only (text length {total_text_length}): {pdf_path}")
        return {'quality': 'image_only', 'details': 'No significant text found'}
    else:
        # Placeholder for future checks (poor extraction, etc.)
        logging.debug(f"PDF quality analysis (initial): Text found (length {total_text_length}). Path: {pdf_path}")
        # For now, if not image-only, return 'unknown' as other checks aren't done
        # This will be updated when poor extraction checks are added.
        return {'quality': 'unknown', 'details': 'Text found, further analysis pending'}
def process_pdf(file_path: Path, output_format: str = "txt") -> str:
    """Processes a PDF file using PyMuPDF. Returns text or Markdown string."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("Required library 'PyMuPDF' is not installed.")
    logging.info(f"Processing PDF: {file_path} for format: {output_format}")
    doc = None
    try:
        doc = fitz.open(str(file_path))
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted: {file_path}")
            raise ValueError("PDF is encrypted")

        all_content = []
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                if output_format == 'markdown':
                    markdown_text = _format_pdf_markdown(page) # Assumes _format_pdf_markdown exists
                    if markdown_text: all_content.append(markdown_text)
                else: # Default to text
                    text = page.get_text("text")
                    if text:
                         # Apply basic cleaning even for text output
                        cleaned_text = text.replace('\x00', '').strip()
                        # Basic header/footer removal for text output too
                        header_footer_patterns = [
                            re.compile(r"^(JSTOR.*|Downloaded from.*|Copyright ©.*)\n?", re.IGNORECASE | re.MULTILINE),
                            re.compile(r"^Page \d+\s*\n?", re.MULTILINE),
                            re.compile(r"^(.*\bPage \d+\b.*)\n?", re.IGNORECASE | re.MULTILINE)
                        ]
                        for pattern in header_footer_patterns:
                            cleaned_text = pattern.sub('', cleaned_text)
                        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text).strip()
                        if cleaned_text: all_content.append(cleaned_text)
            except Exception as page_error:
                logging.warning(f"Could not process page {page_num + 1} in {file_path}: {page_error}")

        # Join pages with double newlines
        full_content = "\n\n".join(all_content).strip()

        if not full_content:
            logging.warning(f"No extractable text in PDF (image-based?): {file_path}")
            return "" # Return empty string for image PDFs or empty content

        logging.info(f"Finished PDF: {file_path}. Format: {output_format}. Length: {len(full_content)}")
        return full_content
    except fitz.fitz.FitzError as fitz_error: # Correct exception type
        logging.error(f"PyMuPDF error processing {file_path}: {fitz_error}")
        raise RuntimeError(f"Error opening/processing PDF: {file_path} - {fitz_error}") from fitz_error
    except Exception as e:
        if isinstance(e, (ValueError, FileNotFoundError)): raise e
        logging.error(f"Unexpected error processing PDF {file_path}: {e}")
        raise RuntimeError(f"Error opening/processing PDF: {file_path} - {e}") from e
    finally:
        if doc:
            try: doc.close()
            except Exception as close_error: logging.error(f"Error closing PDF {file_path}: {close_error}")


async def save_processed_text(
    original_file_path: Path,
    text_content: str,
    output_format: str = "txt",
    book_id: str = None, # Add book_id
    author: str = None,  # Add author
    title: str = None    # Add title
) -> Path:
    """Saves the processed text content to a file with a human-readable slug if metadata is provided."""
    output_filename = "unknown_processed_file" # Default filename in case of early error
    try:
        if text_content is None: # Allow empty string, but not None
             raise ValueError("Cannot save None content.")

        # Ensure output directory exists
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Determine filename
        original_stem = original_file_path.stem
        # Use os.path.splitext to reliably get the original extension for fallback
        _, original_ext = os.path.splitext(original_file_path.name)
        output_extension = f".{output_format.lower()}" # e.g., .txt, .md

        if book_id and author and title:
            # Generate slug: author-title
            author_slug = _slugify(author)
            title_slug = _slugify(title)
            slug = f"{author_slug}-{title_slug}"
            # Limit slug length if necessary (e.g., 100 chars) to avoid overly long filenames
            max_slug_len = 100
            if len(slug) > max_slug_len:
                 # Cut at max_slug_len, then find last hyphen to avoid cutting mid-word
                slug = slug[:max_slug_len]
                if '-' in slug:
                    slug = slug.rsplit('-', 1)[0]

            # Construct new filename: author-title-id.extension
            output_filename = f"{slug}-{book_id}{output_extension}"
        else:
            # Fallback: append ".processed" to the original stem and add the new extension
            output_filename = f"{original_stem}.processed{output_extension}"
            logging.warning(f"Metadata (author, title, book_id) missing for {original_file_path}. Using fallback filename: {output_filename}")


        output_path = PROCESSED_OUTPUT_DIR / output_filename

        # Write content asynchronously
        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            await f.write(text_content)

        logging.info(f"Processed text saved to: {output_path}")
        return output_path

    except OSError as e:
        logging.error(f"OS error saving processed file {output_path}: {e}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}") from e
    except Exception as e:
        logging.exception(f"Failed to save processed text for {original_file_path}")
        # Wrap the original exception for better context
        raise FileSaveError(f"Failed to save processed text to {output_filename}: {e}") from e