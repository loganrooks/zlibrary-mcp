#!/usr/bin/env python3
import sys
import os
import json
import traceback
import re # Added for sanitization

# Add project root to sys.path to allow importing 'lib'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import asyncio
from zlibrary import AsyncZlib, Extension, Language
# DownloadError import removed as it's likely unnecessary here and causing import issues
import aiofiles
from zlibrary.const import OrderOptions # Need this import

import httpx
# Removed re, aiofiles, ebooklib, epub, BeautifulSoup, fitz - moved to rag_processing
from pathlib import Path
import logging
from urllib.parse import urljoin

# Import the new RAG processing functions
from lib import rag_processing
# Global zlibrary client
zlib_client = None
logger = logging.getLogger('zlibrary') # Get the 'zlibrary' logger instance

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


# Removed FileSaveError (now in rag_processing)

# Default HTTP request settings
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
DEFAULT_SEARCH_TIMEOUT = 20
DEFAULT_DETAIL_TIMEOUT = 15

def _sanitize_component(text: str, max_length: int, is_title: bool = False) -> str:
    """Sanitizes a filename component."""
    if not text:
        return ""
    
    # Remove problematic characters
    # / \ ? % * : | " < > . , ; =
    sanitized = re.sub(r'[\\/\?%\*:\ attentes|"<>.,;=]', '', text)
    
    if is_title:
        # Replace spaces with underscores for title
        sanitized = sanitized.replace(' ', '_')
    
    # Replace multiple consecutive underscores/spaces with a single underscore
    sanitized = re.sub(r'[_ ]+', '_', sanitized)
    
    # Strip leading/trailing whitespace and underscores
    sanitized = sanitized.strip('_ ')
    
    # Truncate
    return sanitized[:max_length]

def _create_enhanced_filename(book_details: dict) -> str:
    """
    Creates an enhanced, filesystem-safe filename based on book details.
    Format: LastnameFirstname_TitleOfTheBook_BookID.ext
    """
    author_str = "UnknownAuthor"
    raw_author = book_details.get('author', '')
    if raw_author:
        first_author = raw_author.split(',')[0].strip()
        if first_author:
            name_parts = first_author.split()
            if len(name_parts) == 1:
                # Single word author name (e.g., "Plato")
                author_str = name_parts[0].capitalize()
            elif len(name_parts) > 1:
                lastname = name_parts[-1].capitalize()
                firstnames = "".join([name.capitalize() for name in name_parts[:-1]])
                author_str = f"{lastname}{firstnames}"
    
    formatted_author = _sanitize_component(author_str, 50)

    raw_title = book_details.get('title') or book_details.get('name') # 'name' is often used for title
    title_str = raw_title if raw_title else "UntitledBook"
    formatted_title = _sanitize_component(title_str, 100, is_title=True)

    book_id_str = str(book_details.get('id', "UnknownID"))
    # No real sanitization needed for ID other than ensuring it's a string,
    # but good practice to ensure it doesn't have problematic chars if it's user-influenced.
    # For now, assume 'id' from zlibrary is safe or simple enough.
    # formatted_book_id = _sanitize_component(book_id_str, 20) # Max 20 for ID seems reasonable
    formatted_book_id = book_id_str # Keep as is for now, spec says "Use as is"

    raw_extension = book_details.get('extension', "unknown")
    formatted_extension = f".{raw_extension.lower().lstrip('.')}" if raw_extension else ".unknown"

    base_filename = f"{formatted_author}_{formatted_title}_{formatted_book_id}"
    
    # Truncate entire base filename (before extension) to a max of 200 characters
    if len(base_filename) > 200:
        # Try to preserve BookID and some author/title
        # A simple truncation might cut off critical parts.
        # This strategy attempts to keep BookID intact and as much of title/author as possible.
        id_len = len(formatted_book_id)
        title_len = len(formatted_title)
        author_len = len(formatted_author)
        
        # Max length for author + title, accounting for underscores and ID
        max_auth_title_len = 200 - id_len - 2 # 2 underscores
        
        if author_len + title_len > max_auth_title_len:
            if title_len > max_auth_title_len / 2 and author_len > max_auth_title_len / 2 :
                # Both are long, split remaining length
                allowed_title_len = int(max_auth_title_len / 2)
                allowed_author_len = max_auth_title_len - allowed_title_len
                formatted_title = formatted_title[:allowed_title_len]
                formatted_author = formatted_author[:allowed_author_len]
            elif title_len > author_len:
                # Title is longer, give it more space
                formatted_title = formatted_title[:max_auth_title_len - min(author_len, int(max_auth_title_len*0.3))] # Give author at least 30% or its len
                formatted_author = formatted_author[:max_auth_title_len - len(formatted_title)]
            else:
                # Author is longer or equal
                formatted_author = formatted_author[:max_auth_title_len - min(title_len, int(max_auth_title_len*0.3))] # Give title at least 30% or its len
                formatted_title = formatted_title[:max_auth_title_len - len(formatted_author)]
        
        base_filename = f"{formatted_author}_{formatted_title}_{formatted_book_id}"
        base_filename = base_filename[:200] # Final hard truncate if still over

    return f"{base_filename}{formatted_extension}"

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
    logger.debug(f"_parse_enums: received items={items} for enum_class={enum_class.__name__}")
    parsed_items = []
    if items:
        for item_str in items:
            if not item_str or not isinstance(item_str, str):
                logger.warning(f"_parse_enums: skipping invalid item '{item_str}' in items list {items}")
                continue
            try:
                enum_member = getattr(enum_class, item_str.upper())
                parsed_items.append(enum_member)
                logger.debug(f"_parse_enums: successfully parsed '{item_str}' to {enum_member}")
            except AttributeError:
                # If not found in enum, pass the string directly
                parsed_items.append(item_str)
                logger.debug(f"_parse_enums: attribute error for '{item_str.upper()}' in {enum_class.__name__}, appending original string '{item_str}'")
            except Exception as e:
                logger.error(f"_parse_enums: error processing item '{item_str}' for enum {enum_class.__name__}: {e}")
    logger.debug(f"_parse_enums: returning parsed_items={parsed_items}")
    return parsed_items

async def search(query, exact=False, from_year=None, to_year=None, languages=None, extensions=None, content_types=None, count=10):
    """Search for books based on title, author, etc."""
    if not zlib_client:
        await initialize_client()

    langs = _parse_enums(languages, Language)
    exts = _parse_enums(extensions, Extension)

    # Execute the search
    logger.info(f"python_bridge.search: Calling zlib_client.search with query='{query}', exact={exact}, from_year={from_year}, to_year={to_year}, lang={langs}, extensions={exts}, content_types={content_types}, count={count}")
    paginator, constructed_url = await zlib_client.search( # Unpack tuple
        q=query,
        exact=exact,
        from_year=from_year,
        to_year=to_year,
        lang=langs,
        extensions=exts,
        content_types=content_types, # Pass content_types
        count=count
    )

    # Get the first page of results
    book_results = await paginator.next()
    # Diagnostic step:
    constructed_url_to_return = str(constructed_url) # Removed diagnostic prefix
    return {
        "retrieved_from_url": constructed_url_to_return,
        "books": book_results
    }

async def full_text_search(query, exact=False, phrase=True, words=False, languages=None, extensions=None, content_types=None, count=10):
    """Search for text within book contents"""
    if not zlib_client:
        await initialize_client()

    langs = _parse_enums(languages, Language)
    exts = _parse_enums(extensions, Extension)

    # Execute the search
    logger.info(f"python_bridge.full_text_search: Calling zlib_client.full_text_search with query='{query}', exact={exact}, phrase={phrase}, words={words}, lang={langs}, extensions={exts}, content_types={content_types}, count={count}")
    paginator, constructed_url = await zlib_client.full_text_search( # Unpack tuple
        q=query,
        exact=exact,
        phrase=phrase,
        words=words,
        lang=langs,
        extensions=exts,
        content_types=content_types, # Pass content_types
        count=count
    )

    # Get the first page of results
    book_results = await paginator.next()
    # Diagnostic step:
    constructed_url_to_return = str(constructed_url) # Removed diagnostic prefix
    return {
        "retrieved_from_url": constructed_url_to_return,
        "books": book_results
    }

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

# --- Core Bridge Functions ---

async def process_document(
    file_path_str: str,
    output_format: str = "txt",
    book_id: str = None, # Add metadata params
    author: str = None,
    title: str = None
) -> dict:
    """
    Detects file type, calls the appropriate processing function, saves the result
    with appropriate filename (slug or original), and returns a dictionary
    containing the processed file path (or null).
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path_str}")

    _, ext = os.path.splitext(file_path.name) # Use os.path.splitext for reliability
    ext = ext.lower()
    processed_text = None
    processed_file_path = None # Initialize
    content_lines = [] # Initialize content list

    try:
        logger.info(f"Starting processing for: {file_path} with format {output_format}")
        if ext == '.epub':
            processed_text = rag_processing.process_epub(file_path, output_format)
        elif ext == '.txt':
            # TXT processing doesn't have a separate markdown path in spec
            processed_text = await rag_processing.process_txt(file_path)
        elif ext == '.pdf':
            processed_text = rag_processing.process_pdf(file_path, output_format)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Save the processed text if any was extracted
        if processed_text is not None and processed_text != "":
            # Pass metadata to save_processed_text
            # Construct book_details dictionary
            book_details_dict = {
                "id": book_id,
                "author": author,
                "title": title
            }
            processed_file_path = await rag_processing.save_processed_text(
                original_file_path=file_path,
                processed_content=processed_text, # Corrected argument name
                output_format=output_format,
                book_details=book_details_dict # Pass as dictionary
            )
        else:
             logging.warning(f"No text extracted from {file_path}, processed file not saved.")
             logger.warning(f"No text extracted from {file_path}, processed file not saved.")
             processed_file_path = None # Explicitly set to None

    # Read content if file was created
        if processed_file_path and Path(processed_file_path).exists():
            async with aiofiles.open(processed_file_path, mode='r', encoding='utf-8') as f:
                content_lines = await f.readlines() # Read all lines into a list

        return {"processed_file_path": str(processed_file_path) if processed_file_path else None, "content": content_lines}

    except Exception as e:
        logger.exception(f"Error processing document {file_path_str}") # Log full traceback
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
    if not book_page_url: # Should not happen if ADR-002 is followed (book_details always has URL)
        logger.error("Critical: 'url' key missing in book_details for download_book. This indicates a deviation from ADR-002.")
        raise ValueError("Missing 'url' key in bookDetails object.")

    downloaded_file_path_str = None
    final_file_path_str = None # Path with enhanced filename
    processed_file_path_str = None # Path for RAG processed file

    try:
        # Step 1: Download the book using the library's method.
        # This will save it with a name determined by the zlibrary library (likely just ID.ext or similar).
        original_download_path_str = await zlib_client.download_book(book_details=book_details, output_dir_str=output_dir)
        
        if not original_download_path_str or not Path(original_download_path_str).exists():
            raise FileNotFoundError(f"Book download failed or file not found at: {original_download_path_str}")

        # Step 2: Create the enhanced filename.
        # Ensure 'extension' is in book_details for _create_enhanced_filename
        if 'extension' not in book_details and original_download_path_str:
             _, ext_from_path = os.path.splitext(original_download_path_str)
             book_details['extension'] = ext_from_path.lstrip('.')

        enhanced_filename = _create_enhanced_filename(book_details)
        final_file_path = Path(output_dir) / enhanced_filename
        final_file_path_str = str(final_file_path)

        # Step 3: Rename the downloaded file to the enhanced filename.
        # Ensure output_dir exists for the rename operation
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        os.rename(original_download_path_str, final_file_path_str)
        logger.info(f"Renamed downloaded file from {original_download_path_str} to {final_file_path_str}")
        downloaded_file_path_str = final_file_path_str # This is now the primary path

        # Step 4: Optionally process for RAG.
        if process_for_rag and downloaded_file_path_str:
            logger.info(f"Processing downloaded file for RAG: {downloaded_file_path_str}")
            process_result = await process_document(
                file_path_str=downloaded_file_path_str,
                output_format=processed_output_format,
                book_id=book_details.get('id'),
                author=book_details.get('author'),
                title=book_details.get('name') or book_details.get('title') # Use 'name' or 'title'
            )
            processed_file_path_str = process_result.get("processed_file_path")

        return {
            "file_path": downloaded_file_path_str, # This is the path with the enhanced filename
            "processed_file_path": processed_file_path_str
        }

    except Exception as e:
        logger.exception(f"Error in download_book for book ID {book_details.get('id')}, URL {book_page_url}")
        raise e

# --- Main Execution Block ---
import argparse # Moved import here

async def main():
    parser = argparse.ArgumentParser(description='Z-Library Python Bridge')
    parser.add_argument('function_name', help='Name of the function to call')
    parser.add_argument('args_json', help='JSON string of arguments for the function')
    cli_args = parser.parse_args()

    function_name = cli_args.function_name
    try:
        logger.info(f"python_bridge.main: Received raw args_json: {cli_args.args_json}")
        args_dict_immediately_after_parse = json.loads(cli_args.args_json)
        logger.info(f"python_bridge.main: args_dict_immediately_after_parse: {args_dict_immediately_after_parse}")
        
        # Use a new variable for subsequent operations to preserve the initially parsed one for logging comparison if needed.
        args_dict = args_dict_immediately_after_parse.copy()
        # The original log line that was causing confusion:
        logger.info(f"python_bridge.main: Initial args_dict (now a copy) for processing: {args_dict}")

    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments provided."}), file=sys.stderr)
        sys.exit(1)

    try:
        # Ensure client is initialized if needed by the function
        if function_name not in ['process_document']: # Add functions that DON'T need client
             if not zlib_client:
                await initialize_client()

        # Call the requested function
        # Standardize 'language' key to 'languages' if present for search functions
        # Also handle if 'languages' (plural) is already provided with data
        if function_name in ['search', 'full_text_search']:
            if 'language' in args_dict and args_dict['language']:
                args_dict['languages'] = args_dict.pop('language')
            elif 'languages' in args_dict and args_dict['languages']:
                # It's already plural and has data, do nothing to args_dict['languages']
                pass
            else: # Neither 'language' nor 'languages' found with data, ensure 'languages' key exists for the call
                args_dict['languages'] = []

            # Ensure content_types is present, even if empty, for consistent handling
            if 'content_types' not in args_dict or not args_dict['content_types']:
                args_dict['content_types'] = []


        if function_name == 'search':
            logger.info(f"python_bridge.main: About to call search with args_dict: {args_dict}")
            result = await search(**args_dict)
        elif function_name == 'full_text_search':
            logger.info(f"python_bridge.main: About to call full_text_search with args_dict: {args_dict}")
            result = await full_text_search(**args_dict)
        elif function_name == 'get_download_history':
            result = await get_download_history(**args_dict)
        elif function_name == 'get_download_limits':
            result = await get_download_limits(**args_dict)
        elif function_name == 'download_book': # Changed from download_book_to_file
             result = await download_book(**args_dict)
        elif function_name == 'process_document': # Changed from process_document_for_rag
             # Correct the keyword argument name from file_path to file_path_str if present
             if 'file_path' in args_dict:
                 args_dict['file_path_str'] = args_dict.pop('file_path')
             result = await process_document(**args_dict)
        else:
            raise ValueError(f"Unknown function: {function_name}")

        # Print only confirmation and path to stdout to avoid large content
        # ALL results from Python script must be wrapped in the MCP structure
        # that callPythonFunction expects for its first parse.
        mcp_style_response = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result) # The actual result is stringified here
                }
            ]
        }
        print(json.dumps(mcp_style_response))

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