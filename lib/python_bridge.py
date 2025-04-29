#!/usr/bin/env python3
import sys
import os
import json
import traceback
import asyncio
from zlibrary import AsyncZlib, Extension, Language
from zlibrary.exception import DownloadError
from zlibrary.const import OrderOptions # Need this import

import httpx
import re # Add re module for regex
# os import removed, using pathlib
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

import fitz  # PyMuPDF
import logging
from urllib.parse import urljoin
# Global zlibrary client
zlib_client = None

# Custom Internal Exceptions
class InternalBookNotFoundError(Exception):
    """Custom exception for when a book ID lookup results in a 404."""
    pass

class InternalParsingError(Exception):
    """Custom exception for errors during HTML parsing of book details."""
    pass


class InternalFetchError(Exception):
    """Error during HTTP request (network, non-200 status, timeout)."""
    pass


class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
    pass


# Default HTTP request settings
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
DEFAULT_SEARCH_TIMEOUT = 20
DEFAULT_DETAIL_TIMEOUT = 15

async def initialize_client():
    global zlib_client

    # Load credentials from environment variables or config file
    email = os.environ.get('ZLIBRARY_EMAIL')
    password = os.environ.get('ZLIBRARY_PASSWORD')

    if not email or not password:
        raise Exception("ZLIBRARY_EMAIL and ZLIBRARY_PASSWORD environment variables must be set")

    # Initialize the AsyncZlib client
    zlib_client = AsyncZlib()
    await zlib_client.login(email, password)
    return zlib_client

# Helper function to parse string lists into ZLibrary enums
def _parse_enums(items, enum_class):
    parsed_items = []
    if items:
        for item in items:
            try:
                parsed_items.append(getattr(enum_class, item.upper()))
            except AttributeError:
                # If not found in enum, pass the string directly (library might handle it)
                parsed_items.append(item)
    return parsed_items

async def search(query, exact=False, from_year=None, to_year=None, languages=None, extensions=None, count=10):
    """Search for books based on title, author, etc."""
    if not zlib_client:
        await initialize_client()

    langs = _parse_enums(languages, Language)
    exts = _parse_enums(extensions, Extension)

    # Execute the search
    paginator = await zlib_client.search(
        q=query,
        exact=exact,
        from_year=from_year,
        to_year=to_year,
        lang=langs,
        extensions=exts,
        count=count
    )

    # Get the first page of results
    results = await paginator.next()
    return results

async def _find_book_by_id_via_search(book_id):
    """Helper to find a single book by ID using the search workaround."""
    # Client initialization is handled by the calling function's check or implicitly by zlib_client calls
    # if not zlib_client:
    #     await initialize_client()

    # No separate try/except here; let the caller handle logging context
    paginator = await zlib_client.search(q=f'id:{book_id}', exact=True, count=1)
    results = await paginator.next()

    if len(results) == 1:
        return results[0]
    elif len(results) == 0:
        raise ValueError(f"Book ID {book_id} not found via search.")
    else:
        # This case should ideally not happen with exact ID search and count=1
        logging.warning(f"Ambiguous search result for Book ID {book_id}. Results: {results}")
        raise ValueError(f"Ambiguous search result for Book ID {book_id}.")


async def get_by_id(book_id):
    """Get book details by ID using search workaround"""
    if not zlib_client:
        await initialize_client()

    try:
        book = await _find_book_by_id_via_search(book_id)
        return book
    except Exception as e:
        logging.exception(f"Error in get_by_id for ID {book_id}")
        raise e # Re-raise the exception after logging

async def full_text_search(query, exact=False, phrase=True, words=False, languages=None, extensions=None, count=10):
    """Search for text within book contents"""
    if not zlib_client:
        await initialize_client()

    langs = _parse_enums(languages, Language)
    exts = _parse_enums(extensions, Extension)

    # Execute the search
    paginator = await zlib_client.full_text_search(
        q=query,
        exact=exact,
        phrase=phrase,
        words=words,
        lang=langs,
        extensions=exts,
        count=count
    )

    # Get the first page of results
    results = await paginator.next()
    return results

async def get_download_history(count=10):
    """Get user's download history"""
    if not zlib_client:
        await initialize_client()

    # Get download history paginator
    history_paginator = await zlib_client.profile.download_history()

    # Get first page of history
    history = history_paginator.result
    return history

async def get_download_limits():
    """Get user's download limits"""
    if not zlib_client:
        await initialize_client()

    limits = await zlib_client.profile.get_limits()
    return limits

async def get_recent_books(count=10, format=None):
    """Get recently added books, optionally filtered by format."""
    if not zlib_client:
        await initialize_client()

    # Convert single format string to list of extensions if provided
    extensions_list = []
    if format:
        # Attempt to parse as enum, fallback to string
        try:
            extensions_list.append(getattr(Extension, format.upper()))
        except AttributeError:
            extensions_list.append(format) # Pass raw string if not an enum

    try:
        # Use search with empty query and order by newest
        paginator = await zlib_client.search(
            q="",
            order=OrderOptions.NEWEST,
            count=count,
            extensions=extensions_list,
            # Include defaults for other search params
            exact=False,
            from_year=None,
            to_year=None,
            lang=[]
        )
        # Get results from the first page (assuming .next() is needed based on test mock)
        results = await paginator.next()
        # If the library changes and results are directly on paginator after search:
        # results = paginator.results
        return results
    except Exception as e:
        logging.exception(f"Error fetching recent books (count={count}, format={format})")
        raise e # Re-raise the original error for main handler

# --- RAG Document Processing Functions ---

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

# Check if libraries are available (already present in file)
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

try:
    import fitz # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Constants (already present in file)
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf']
PROCESSED_OUTPUT_DIR = Path("./processed_rag_output")

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

def _process_epub(file_path: Path, output_format: str = "txt") -> str:
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

def _process_txt(file_path: Path) -> str:
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

def _process_pdf(file_path: Path, output_format: str = "txt") -> str:
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


async def _save_processed_text(original_file_path: Path, text_content: str, output_format: str = "txt") -> Path:
    """Saves the processed text content to a file asynchronously."""
    if text_content is None: # Allow empty string, but not None
         raise ValueError("Cannot save None content.")

    try:
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        base_name = original_file_path.name
        # Ensure output format is part of the extension
        output_filename = f"{base_name}.processed.{output_format}"
        output_file_path = PROCESSED_OUTPUT_DIR / output_filename
        logging.info(f"Saving processed text to: {output_file_path}")
        async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
            await f.write(text_content)
        logging.info(f"Successfully saved processed text for {original_file_path.name}")
        return output_file_path
    except OSError as e:
        logging.error(f"OS error saving processed file {output_file_path}: {e}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}") from e
    except Exception as e:
        logging.error(f"Unexpected error saving processed file {output_file_path}: {e}")
        raise FileSaveError(f"An unexpected error occurred while saving processed file: {e}") from e

# --- Core Bridge Functions (Updated) ---

async def process_document(file_path_str: str, output_format: str = "txt") -> dict:
    """
    Detects file type, calls the appropriate processing function, saves the result,
    and returns a dictionary containing the processed file path (or null).
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path_str}")

    _, ext = os.path.splitext(file_path.name) # Use os.path.splitext for reliability
    ext = ext.lower()
    processed_text = None
    processed_file_path = None # Initialize

    try:
        logging.info(f"Starting processing for: {file_path} with format {output_format}")
        if ext == '.epub':
            processed_text = _process_epub(file_path, output_format)
        elif ext == '.txt':
            # TXT processing doesn't have a separate markdown path in spec
            processed_text = _process_txt(file_path)
        elif ext == '.pdf':
            processed_text = _process_pdf(file_path, output_format)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Save the processed text if any was extracted
        if processed_text is not None and processed_text != "":
            processed_file_path = await _save_processed_text(file_path, processed_text, output_format)
        else:
             logging.warning(f"No text extracted from {file_path}, processed file not saved.")
             processed_file_path = None # Explicitly set to None

        return {"processed_file_path": str(processed_file_path) if processed_file_path else None}

    except Exception as e:
        logging.exception(f"Error processing document {file_path_str}") # Log full traceback
        # Re-raise to be caught by the main handler
        raise RuntimeError(f"Error processing document {file_path_str}: {e}") from e

# --- download_book function needs to be async ---
async def download_book(book_details: dict, output_dir: str, process_for_rag: bool = False, processed_output_format: str = "txt"):
    """
    Downloads a book using scraping, optionally processes it, and returns file paths.
    """
    if not zlib_client:
        await initialize_client()

    book_page_url = book_details.get('url')
    if not book_page_url:
        raise ValueError("Missing 'url' key in bookDetails object.")

    downloaded_file_path_str = None
    processed_file_path_str = None # Initialize

    try:
        # Use the scraping helper
        downloaded_file_path_str = await _scrape_and_download(book_page_url, output_dir) # Assumes _scrape_and_download exists

        if process_for_rag and downloaded_file_path_str:
            logging.info(f"Processing downloaded file for RAG: {downloaded_file_path_str}")
            # Call the main process_document function
            process_result = await process_document(downloaded_file_path_str, processed_output_format)
            processed_file_path_str = process_result.get("processed_file_path") # Can be None

        return {
            "file_path": downloaded_file_path_str,
            "processed_file_path": processed_file_path_str # Will be None if not processed or no text
        }

    except Exception as e:
        logging.exception(f"Error in download_book for URL {book_page_url}")
        # Re-raise the specific error type if possible, otherwise generic
        raise e # Let main handler format the final error message

# --- Main Execution Block ---
async def main():
    parser = argparse.ArgumentParser(description='Z-Library Python Bridge')
    parser.add_argument('function_name', help='Name of the function to call')
    parser.add_argument('args_json', help='JSON string of arguments for the function')
    cli_args = parser.parse_args()

    function_name = cli_args.function_name
    try:
        args_dict = json.loads(cli_args.args_json)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments provided."}), file=sys.stderr)
        sys.exit(1)

    try:
        # Ensure client is initialized if needed by the function
        if function_name not in ['process_document']: # Add functions that DON'T need client
             if not zlib_client:
                await initialize_client()

        # Call the requested function
        if function_name == 'search':
            result = await search(**args_dict)
        elif function_name == 'get_by_id':
            result = await get_by_id(**args_dict)
        elif function_name == 'full_text_search':
            result = await full_text_search(**args_dict)
        elif function_name == 'get_download_history':
            result = await get_download_history(**args_dict)
        elif function_name == 'get_download_limits':
            result = await get_download_limits(**args_dict)
        elif function_name == 'get_recent_books':
             result = await get_recent_books(**args_dict)
        elif function_name == 'download_book': # Changed from download_book_to_file
             result = await download_book(**args_dict)
        elif function_name == 'process_document': # Changed from process_document_for_rag
             result = await process_document(**args_dict)
        else:
            raise ValueError(f"Unknown function: {function_name}")

        # Print result as JSON to stdout
        print(json.dumps(result))

    except Exception as e:
        # Print error as JSON to stderr
        error_info = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_info), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())