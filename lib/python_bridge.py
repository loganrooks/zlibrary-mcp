#!/usr/bin/env python3
import sys
import os
import json
import traceback
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
        logging.info(f"Starting processing for: {file_path} with format {output_format}")
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
             processed_file_path = None # Explicitly set to None

        # Read content if file was created
        if processed_file_path and Path(processed_file_path).exists():
            async with aiofiles.open(processed_file_path, mode='r', encoding='utf-8') as f:
                content_lines = await f.readlines() # Read all lines into a list

        return {"processed_file_path": str(processed_file_path) if processed_file_path else None, "content": content_lines}

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
        # Use the client's download method
        # downloaded_file_path_str = await _scrape_and_download(book_page_url, output_dir) # Assumes _scrape_and_download exists
        downloaded_file_path_str = await zlib_client.download_book(book_details, output_dir) # Use client download

        if process_for_rag and downloaded_file_path_str:
            logging.info(f"Processing downloaded file for RAG: {downloaded_file_path_str}")
            # Call the main process_document function, passing metadata
            process_result = await process_document(
                file_path_str=downloaded_file_path_str,
                output_format=processed_output_format,
                book_id=book_details.get('id'), # Extract from book_details
                author=book_details.get('author'),
                title=book_details.get('name') # Use 'name' key for title
            )
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
import argparse # Moved import here

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