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

def _analyze_pdf_block(block):
  """Analyzes a PyMuPDF text block to infer structure (heading level, list type)."""
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

    if spans:
      first_span = spans[0]
      font_size = first_span.get('size', 10)
      flags = first_span.get('flags', 0)
      is_bold = flags & 2 # Font flag for bold

      # Heading heuristic (example, needs tuning)
      if font_size > 18 or (font_size > 14 and is_bold): heading_level = 1
      elif font_size > 14 or (font_size > 12 and is_bold): heading_level = 2
      elif font_size > 12 or (font_size > 11 and is_bold): heading_level = 3
      # ... more levels ...

      # List heuristic (example, needs tuning)
      trimmed_text = text_content.strip()
      # Basic unordered list check
      if trimmed_text.startswith(('•', '*', '-')):
        is_list_item = True
        list_type = 'ul'
        # Indentation could be inferred from block['bbox'][0] (x-coordinate)
      # Basic ordered list check
      elif re.match(r"^\d+\.\s+", trimmed_text):
        is_list_item = True
        list_type = 'ol'
      # ... more complex list detection (e.g., a), i.) ...

  return {
    'heading_level': heading_level,
    'is_list_item': is_list_item,
    'list_type': list_type,
    'list_indent': list_indent, # Placeholder for future nesting use
    'text': text_content.strip(),
    'spans': spans # Pass spans for footnote detection
  }

def _format_pdf_markdown(page):
  """Generates Markdown string from a PyMuPDF page object."""
  blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
  markdown_lines = []
  footnote_defs = {} # Store footnote definitions [^id]: content
  current_list_type = None
  # list_level = 0 # Basic nesting tracker - deferred

  for block in blocks:
    analysis = _analyze_pdf_block(block)
    text = analysis['text']
    spans = analysis['spans']

    if not text: continue

    # Footnote Reference/Definition Detection (using superscript flag)
    processed_text_parts = []
    potential_def_id = None
    first_span_in_block = True
    for span in spans:
        span_text = span.get('text', '')
        flags = span.get('flags', 0)
        is_superscript = flags & 1 # Superscript flag

        if is_superscript and span_text.isdigit():
            fn_id = span_text
            # Definition heuristic: superscript number at start of block
            if first_span_in_block:
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
        # The text following the superscript number is the definition
        footnote_defs[potential_def_id] = processed_text
        continue # Don't add definition block as regular content

    # Format based on analysis
    if analysis['heading_level'] > 0:
      markdown_lines.append(f"{'#' * analysis['heading_level']} {processed_text}")
      current_list_type = None # Reset list context after heading
    elif analysis['is_list_item']:
      # Basic list handling (needs refinement for nesting based on indent)
      # Remove original list marker from text if present
      if analysis['list_type'] == 'ul':
          clean_text = re.sub(r"^[\*•-]\s*", "", processed_text).strip()
          markdown_lines.append(f"* {clean_text}")
      elif analysis['list_type'] == 'ol':
          clean_text = re.sub(r"^\d+\.\s*", "", processed_text).strip()
          markdown_lines.append(f"1. {clean_text}") # Simple numbering, needs context for correct sequence
      current_list_type = analysis['list_type']
    else: # Regular paragraph
      # Only add if it's not empty after processing
      if processed_text:
          markdown_lines.append(processed_text)
      current_list_type = None # Reset list context

  # Append footnote definitions at the end
  if footnote_defs:
      markdown_lines.append("\n---") # Add separator
      for fn_id, fn_text in sorted(footnote_defs.items()):
          markdown_lines.append(f"[^{fn_id}]: {fn_text}")

  # Join lines with double newlines for paragraph breaks
  return "\n\n".join(markdown_lines).strip()


# --- EPUB Markdown Helpers ---

def _epub_node_to_markdown(node, footnote_defs, list_level=0):
  """Recursively converts BeautifulSoup node to Markdown string."""
  markdown_parts = []
  node_name = getattr(node, 'name', None)
  indent = "  " * list_level # Indentation for nested lists

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
  elif node_name == 'ol':
      # Handle OL items recursively
      for i, child in enumerate(node.find_all('li', recursive=False)):
          item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
          if item_text: markdown_parts.append(f"{indent}{i+1}. {item_text}")
      return "\n".join(markdown_parts) # Return joined list items
  elif node_name == 'li':
      # Process content within LI, prefix handled by parent ul/ol
      prefix = ''
  elif node_name == 'blockquote': prefix = '> '
  elif node_name == 'pre':
      # Handle code blocks
      code_content = node.get_text() # Keep formatting
      return f"```\n{code_content}\n```"
  elif node_name == 'a' and node.get('epub:type') == 'noteref':
      # Handle footnote reference
      ref_id_text = node.get_text(strip=True)
      ref_id_href = node.get('href', '')
      ref_id = None
      if ref_id_text.isdigit():
          ref_id = ref_id_text
      elif '#' in ref_id_href:
          match = re.search(r'(\d+)$', ref_id_href) # Look for digits at the end
          if match: ref_id = match.group(1)

      if ref_id: return f"[^{ref_id}]"
      else: return "" # Ignore if ID not found
  elif node_name == 'aside' and node.get('epub:type') == 'footnote':
      # Store footnote definition and return empty (handled separately)
      fn_id_attr = node.get('id', '')
      fn_id_match = re.search(r'(\d+)$', fn_id_attr) # Look for digits at the end
      fn_id = fn_id_match.group(1) if fn_id_match else None
      # Process the *content* of the aside tag, not the tag itself recursively
      fn_content_parts = []
      for child in node.children:
          if isinstance(child, str):
              cleaned_text = child.strip()
              if cleaned_text: fn_content_parts.append(cleaned_text)
          elif getattr(child, 'name', None):
              child_md = _epub_node_to_markdown(child, footnote_defs, list_level) # Process children
              if child_md: fn_content_parts.append(child_md)
      fn_text = " ".join(fn_content_parts).strip()

      if fn_id and fn_text:
          # Remove potential self-reference like '[^1]' if it's the start
          fn_text = re.sub(r"^\[\^" + re.escape(fn_id) + r"\]\s*", "", fn_text).strip()
          footnote_defs[fn_id] = fn_text
      return "" # Don't include definition inline
  else:
      # Default: process children or get text
      prefix = ''

  # Process children recursively or get text content
  content_parts = []
  for child in getattr(node, 'children', []):
      if isinstance(child, str):
          # Keep significant whitespace, strip leading/trailing only
          cleaned_text = child # Don't strip internal whitespace yet
          if cleaned_text: content_parts.append(cleaned_text)
      elif getattr(child, 'name', None): # It's another tag
          child_md = _epub_node_to_markdown(child, footnote_defs, list_level)
          if child_md: content_parts.append(child_md)

  # Join parts, handling whitespace carefully
  full_content = "".join(content_parts)
  # Collapse multiple whitespace chars but keep single newlines for structure
  full_content = re.sub(r'\s+', ' ', full_content).strip()

  # Apply prefix if content exists
  if full_content:
      # Handle blockquotes needing prefix on each line (if content has newlines)
      if prefix == '> ' and '\n' in full_content:
          return '> ' + full_content.replace('\n', '\n> ')
      else:
          return prefix + full_content
  else:
      return ""


# --- Main Processing Functions (Refactored) ---

def _process_epub(file_path_str: str, output_format: str = 'text') -> str:
    """Extracts text content from an EPUB file, optionally generating Markdown."""
    try:
        book = epub.read_epub(file_path_str)
        all_content_parts = []
        footnote_defs = {} # Collect across all items

        items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        for item in items:
            html_content = item.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'lxml')

            if output_format == 'markdown':
                item_md_parts = []
                # Process body content, collecting footnote defs
                if soup.body:
                    for element in soup.body.children: # Iterate direct children
                         md_part = _epub_node_to_markdown(element, footnote_defs)
                         if md_part: item_md_parts.append(md_part)
                item_markdown = "\n\n".join(item_md_parts).strip() # Join parts with double newline
                if item_markdown: all_content_parts.append(item_markdown)
            else: # Plain text
                # Basic text extraction, could be improved
                text = soup.get_text(separator='\n', strip=True) # Use newline separator
                if text: all_content_parts.append(text)

        # Append collected footnote definitions for Markdown
        if output_format == 'markdown' and footnote_defs:
            fn_section = ["\n\n---"] # Separator
            for fn_id, fn_text in sorted(footnote_defs.items()):
                fn_section.append(f"[^{fn_id}]: {fn_text}")
            all_content_parts.append("\n".join(fn_section))

        full_content = "\n\n".join(all_content_parts).strip()
        if not full_content: raise ValueError("EPUB contains no extractable content")
        return full_content
    except Exception as e:
        logging.exception(f"Error processing EPUB {file_path_str}") # Log full traceback
        raise Exception(f"Error processing EPUB {file_path_str}: {e}") from e


def _process_txt(file_path):
    """Reads content from a TXT file."""
    try:
        # Using errors='ignore' as a simple strategy for RAG where perfect fidelity isn't critical.
        # Consider 'replace' or more robust encoding detection if issues arise.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error processing TXT {file_path}: {e}")


def _process_pdf(file_path: str, output_format: str = 'text') -> str:
    """
    Extracts text content from a PDF file using PyMuPDF (fitz), optionally
    generating basic Markdown structure.
    """
    logging.info(f"Processing PDF: {file_path} (Format: {output_format})")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = None
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted: {file_path}")
            raise ValueError("PDF is encrypted")

        all_content = []
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                if output_format == 'markdown':
                    page_content = _format_pdf_markdown(page) # Use the helper
                else: # Default to text processing
                    page_content = page.get_text("text")
                    if page_content:
                        # Apply text cleaning (null chars, headers/footers)
                        page_content = page_content.replace('\x00', '')
                        header_footer_patterns = [
                            re.compile(r"^(JSTOR.*|Downloaded from.*|Copyright ©.*)\n?", re.IGNORECASE | re.MULTILINE),
                            re.compile(r"^Page \d+\s*\n?", re.MULTILINE)
                        ]
                        for pattern in header_footer_patterns:
                            page_content = pattern.sub('', page_content)
                        page_content = re.sub(r'\n\s*\n', '\n\n', page_content).strip()

                if page_content:
                    all_content.append(page_content)

            except Exception as page_error:
                logging.warning(f"Could not process page {page_num + 1} in {file_path}: {page_error}")

        full_content = "\n\n".join(all_content).strip()
        if not full_content:
            logging.warning(f"No extractable content found in PDF: {file_path}")
            raise ValueError("PDF contains no extractable content layer (possibly image-based)")

        logging.info(f"Finished PDF: {file_path}. Extracted length: {len(full_content)}")
        return full_content

    except RuntimeError as fitz_error:
        logging.error(f"PyMuPDF error processing {file_path}: {fitz_error}")
        raise RuntimeError(f"Error opening or processing PDF: {file_path} - {fitz_error}") from fitz_error
    except Exception as e:
        logging.exception(f"Unexpected error processing PDF {file_path}") # Log traceback
        # Re-raise specific errors if needed, otherwise wrap
        if isinstance(e, (ValueError, FileNotFoundError)):
             raise e
        raise RuntimeError(f"Unexpected error processing PDF {file_path}: {e}") from e
    finally:
        if doc:
            doc.close()

# Helper function to save processed text
def _save_processed_text(file_path_str: str, text_content: str, output_format: str = 'txt') -> Path:
    """Saves the processed text content to a file."""
    processed_output_dir = Path("./processed_rag_output")

    if text_content is None:
        raise ValueError("Cannot save None content.")

    try:
        original_path = Path(file_path_str)
        # Ensure the output directory exists
        processed_output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename: <original_name>.processed.<format>
        # Use original stem + suffix if possible, otherwise just name
        if original_path.suffix:
            base_name = original_path.stem
        else:
            base_name = original_path.name # Use full name if no suffix

        # Ensure output format is reasonable (default to txt)
        safe_output_format = output_format if output_format in ['txt', 'md', 'markdown'] else 'txt'
        if safe_output_format == 'markdown': safe_output_format = 'md' # Use shorter extension

        output_filename = f"{base_name}.processed.{safe_output_format}"
        output_path = processed_output_dir / output_filename

        logging.info(f"Saving processed text to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        return output_path
    except OSError as e:
        logging.exception(f"OS error saving processed file for {file_path_str}: {e}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}")
    except Exception as e:
        logging.exception(f"Unexpected error saving processed file for {file_path_str}")
        # Wrap unexpected errors
        raise FileSaveError(f"An unexpected error occurred during file saving: {e}")

# Define supported formats (as per spec example)
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf']

async def process_document(file_path_str: str, output_format='txt') -> dict:
    """
    Processes a document file (EPUB, TXT, PDF) to extract text content,
    saves it to a file, and returns the path.
    Accepts 'text' or 'markdown' for output_format.
    """
    try:
        file_path = Path(file_path_str)
        if not file_path.exists():
             raise FileNotFoundError(f"File not found: {file_path_str}")

        ext = file_path.suffix.lower()
        # Normalize output format alias
        normalized_output_format = 'markdown' if output_format == 'md' else output_format
        if normalized_output_format not in ['text', 'markdown']:
            normalized_output_format = 'text' # Default to text if invalid

        processed_text = None

        if ext == '.epub':
            processed_text = _process_epub(file_path_str, normalized_output_format) # Pass format
        elif ext == '.txt':
            # TXT processing doesn't change based on output_format, but save format does
            processed_text = _process_txt(file_path_str)
        elif ext == '.pdf':
            processed_text = _process_pdf(file_path_str, normalized_output_format) # Pass format
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        # _process_pdf raises ValueError if no text is extracted.
        # Ensure other processors do too or handle None here if necessary.
        if processed_text is None:
             # This case should ideally not be reached if processors raise errors appropriately.
             logging.warning(f"Processing yielded None content for {file_path_str}, expected an exception.")
             raise ValueError(f"No text content could be extracted from {file_path_str}")

        # Save the processed text
        saved_path = _save_processed_text(file_path_str, processed_text, normalized_output_format)

        # Return the path to the saved file
        return {"processed_file_path": str(saved_path)}

    except ImportError as imp_err:
         logging.error(f"Missing dependency for processing {ext} file {file_path_str}: {imp_err}")
         return {"error": f"Missing required library to process {ext} files. Please check installation."}
    except (FileNotFoundError, ValueError, FileSaveError) as specific_err:
        logging.error(f"Error processing document {file_path_str}: {specific_err}")
        return {"error": str(specific_err)}
    except Exception as e:
        logging.exception(f"Failed to process document {file_path_str}")
        # Propagate specific processing errors directly if they are RuntimeErrors
        if isinstance(e, RuntimeError) and ("Error opening or processing PDF" in str(e)):
             return {"error": str(e)}
        return {"error": f"An unexpected error occurred during document processing: {e}"}

def main():
    # Configure basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Argument parsing MUST happen *before* the main try block uses function_name
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing arguments"}))
        return 1

    function_name = sys.argv[1]
    args_json = sys.argv[2]

    try:
        args_dict = json.loads(args_json)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments"}))
        return 1

    response = None # Initialize response

    try:
        # --- Action Handling ---
        if function_name == 'search':
            response = asyncio.run(search(**args_dict))
        elif function_name == 'get_by_id': # Renamed from get_book_details in spec example
            book_id = args_dict.get('book_id')
            if not book_id: raise ValueError("Missing 'book_id'")
            response = asyncio.run(get_by_id(book_id))
        elif function_name == 'get_download_info':
            # This tool is deprecated and likely relies on faulty ID lookup.
            # Consider removing or raising a specific error.
            logging.warning("Deprecated tool 'get_download_info' called.")
            raise NotImplementedError("Tool 'get_download_info' is deprecated.")
            # book_id = args_dict.get('book_id')
            # format_arg = args_dict.get('format') # Keep format if needed by caller
            # if not book_id: raise ValueError("Missing 'book_id'")
            # response = asyncio.run(get_download_info(book_id, format_arg))
        elif function_name == 'full_text_search':
            response = asyncio.run(full_text_search(**args_dict))
        elif function_name == 'get_download_history':
            response = asyncio.run(get_download_history(**args_dict))
        elif function_name == 'get_download_limits':
            response = asyncio.run(get_download_limits())
        elif function_name == 'get_recent_books': # <<< CORRECTLY PLACED HANDLER
            response = asyncio.run(get_recent_books(**args_dict)) # <<< CORRECTLY PLACED HANDLER
        elif function_name == 'process_document':
            # Get format from args, default to 'text'
            output_format = args_dict.get('output_format', 'text')
            args_dict['output_format'] = output_format # Ensure it's in the dict for **args_dict
            response = asyncio.run(process_document(**args_dict))
        elif function_name == 'download_book': # Handler for download_book
            if 'book_details' not in args_dict:
                 raise ValueError("Missing 'book_details' argument for download_book")
            # Get format from args, default to 'text'
            processed_output_format = args_dict.get('processed_output_format', 'text')
            args_dict['processed_output_format'] = processed_output_format # Ensure it's in the dict
            response = asyncio.run(download_book(**args_dict))
        else:
            print(json.dumps({"error": f"Unknown function: {function_name}"}))
            return 1

        # Output the result as JSON if no error occurred during action handling
        print(json.dumps(response))
        return 0

    # --- Exception Handling ---
    except ValueError as ve:
        logging.warning(f"ValueError during {function_name}: {ve}")
        print(json.dumps({"error": str(ve)}))
        return 1
    except RuntimeError as re:
        logging.error(f"RuntimeError during {function_name}: {re}")
        print(json.dumps({"error": str(re)}))
        return 1
    except FileSaveError as fse:
        logging.error(f"FileSaveError during {function_name}: {fse}")
        print(json.dumps({"error": str(fse)}))
        return 1
    except NotImplementedError as nie:
        logging.warning(f"NotImplementedError during {function_name}: {nie}")
        print(json.dumps({"error": str(nie)}))
        return 1
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        logging.exception(f"Unexpected error during {function_name}")
        # Re-added generic error message for unexpected errors
        print(json.dumps({"error": f"An unexpected error occurred: {e}"}))
        return 1

# --- Internal Download/Scraping Helper (Spec v2.1) ---
async def _scrape_and_download(book_page_url: str, output_path: str) -> str:
    """
    Calls the zlibrary fork's download_book method which handles scraping and downloading.
    Note: This function now expects the *book_page_url* and the full *output_path*.
    """
    global zlib_client
    if not zlib_client:
        await initialize_client()

    try:
        # Construct a minimal book_details dict required by the library's download_book
        try:
            book_id_from_url = book_page_url.split('/book/')[1].split('/')[0] if '/book/' in book_page_url else 'unknown_from_url'
        except IndexError:
            book_id_from_url = 'unknown_from_url'

        minimal_book_details = {
            'url': book_page_url,
            'id': book_id_from_url # Provide ID for potential logging within the library
        }

        # REMOVED Filename generation and directory creation - now handled by caller

        # Call the library's download_book method
        logging.info(f"Calling zlib_client.download_book for URL: {book_page_url}, Output Path: {output_path}")
        await zlib_client.download_book(
            book_details=minimal_book_details, # Pass minimal details containing the URL
            output_path=output_path # Pass the full string path received from caller
        )

        # Library download_book returns None on success, so we return the expected output path
        return output_path

    except DownloadError as de:
        logging.error(f"DownloadError during scrape/download for {book_page_url}: {de}")
        raise RuntimeError(f"Download failed: {de}") from de # Wrap DownloadError
    except Exception as e:
        logging.exception(f"Unexpected error during scrape/download for {book_page_url}")
        raise RuntimeError(f"An unexpected error occurred during download: {e}") from e # Wrap other errors


async def download_book(book_details: dict, output_dir='./downloads', process_for_rag=False, processed_output_format='txt') -> dict:
    """
    Downloads a book using the provided details.
    Optionally processes the downloaded file for RAG.
    Accepts 'text' or 'markdown' for processed_output_format.
    """
    global zlib_client
    if not zlib_client:
        await initialize_client()

    # Validate input
    if not isinstance(book_details, dict):
        raise TypeError("book_details must be a dictionary.")
    if 'id' not in book_details or 'extension' not in book_details:
         raise ValueError("book_details must contain 'id' and 'extension'.")
    # Removed URL check here, as _scrape_and_download now uses zlib_client.download_book which takes book_details directly

    downloaded_file_path_str = None
    processed_file_path_str = None
    processing_error_str = None

    try:
        # Ensure output directory exists
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # Construct the full output path
        file_name = f"{book_details['id']}.{book_details['extension']}"
        full_output_path = str(output_dir_path / file_name)
        downloaded_file_path_str = full_output_path # Store the intended path

        # Call the library's download method directly
        logging.info(f"Initiating download for book ID {book_details['id']} to {full_output_path}")
        await zlib_client.download_book(
            book_details=book_details, # Pass the full details
            output_path=full_output_path
        )
        logging.info(f"Download successful for book ID {book_details['id']}")

        # --- RAG Processing (Optional) ---
        if process_for_rag:
            logging.info(f"Processing downloaded file for RAG: {downloaded_file_path_str}")
            try:
                # Pass the desired format to process_document
                processing_result = await process_document(downloaded_file_path_str, processed_output_format)
                if "error" in processing_result:
                    processing_error_str = processing_result["error"]
                    logging.error(f"RAG processing failed for {downloaded_file_path_str}: {processing_error_str}")
                else:
                    processed_file_path_str = processing_result.get("processed_file_path")
                    logging.info(f"RAG processing successful. Output: {processed_file_path_str}")

            except Exception as proc_err:
                # Catch unexpected errors during the process_document call itself
                logging.exception(f"Unexpected error calling process_document for {downloaded_file_path_str}")
                processing_error_str = f"Unexpected error during processing call: {proc_err}"

    except DownloadError as de:
        logging.error(f"DownloadError for book ID {book_details['id']}: {de}")
        # Re-raise as RuntimeError for the main handler
        raise RuntimeError(f"Download failed: {de}") from de
    except Exception as e:
        logging.exception(f"Failed during download process for book ID {book_details['id']}")
        # Re-raise other critical errors (like ValueError from input validation)
        if isinstance(e, (ValueError, TypeError)):
             raise e
        # Wrap other unexpected errors
        raise RuntimeError(f"An unexpected error occurred during download: {e}") from e

    # Return structured result
    return {
        "file_path": downloaded_file_path_str,
        "processed_file_path": processed_file_path_str,
        "processing_error": processing_error_str
    }


if __name__ == "__main__":
    sys.exit(main())