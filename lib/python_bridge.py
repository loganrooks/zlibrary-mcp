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
from filename_utils import create_unified_filename
import logging
from urllib.parse import urljoin

# Import the new RAG processing functions
from lib import rag_processing
# Import enhanced metadata extraction
from lib import enhanced_metadata
# Import client manager for dependency injection
from lib import client_manager

# DEPRECATED: Global zlibrary client (for backward compatibility)
# New code should use dependency injection with ZLibraryClient
zlib_client = None
logger = logging.getLogger('zlibrary') # Get the 'zlibrary' logger instance

# Debug mode configuration (ISSUE-009)
# Enable with: ZLIBRARY_DEBUG=1 or DEBUG=1
DEBUG_MODE = os.environ.get('ZLIBRARY_DEBUG', os.environ.get('DEBUG', '')).lower() in ('1', 'true', 'yes')

def _configure_debug_logging():
    """Configure logging based on debug mode setting."""
    if DEBUG_MODE:
        # Set up detailed debug logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled via environment variable")
    else:
        # Default: INFO level with simpler format
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        logger.setLevel(logging.INFO)

# Configure logging on module load
_configure_debug_logging()


def is_debug_mode() -> bool:
    """Check if debug mode is enabled.

    Returns:
        True if ZLIBRARY_DEBUG=1 or DEBUG=1 environment variable is set
    """
    return DEBUG_MODE


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

# HTTP connection pooling (ISSUE-008)
# Module-level client for connection reuse across requests
_http_client: httpx.AsyncClient = None


async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create a shared HTTP client with connection pooling.

    Connection pooling benefits:
    - Reuses TCP connections across requests
    - Reduces TLS handshake overhead
    - Improves latency for sequential requests

    Returns:
        Shared httpx.AsyncClient instance
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_DETAIL_TIMEOUT,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0  # Keep connections alive for 30 seconds
            )
        )
        logger.debug("Created shared HTTP client with connection pooling")
    return _http_client


async def close_http_client():
    """
    Close the shared HTTP client and release connections.

    Call this during cleanup or shutdown to properly close connections.
    Safe to call multiple times.
    """
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.debug("Closed shared HTTP client")


def extract_book_hash_from_href(href: str) -> str:
    """
    Extract book hash from href path.

    Z-Library hrefs follow format: /book/ID/HASH/title

    Args:
        href: Book href like '/book/1252896/882753/encyclopaedia-philosophical-sciences'

    Returns:
        Book hash or None if not extractable

    Example:
        >>> extract_book_hash_from_href('/book/1252896/882753/title')
        '882753'
    """
    if not href:
        return None

    parts = href.strip('/').split('/')

    # Expected format: ['book', 'ID', 'HASH', 'title']
    if len(parts) >= 3 and parts[0] == 'book':
        return parts[2]

    return None


def normalize_book_details(book: dict, mirror: str = None) -> dict:
    """
    Normalize book details to ensure all required fields present.

    Handles field inconsistencies between search results and download requirements:
    - Adds 'url' from 'href' (constructs full URL from relative path)
    - Extracts 'book_hash' from 'href' if missing
    - Ensures all required fields for downstream operations

    Args:
        book: Book dictionary from search results
        mirror: Z-Library mirror URL (optional, will use environment if not provided)

    Returns:
        Normalized book dictionary with guaranteed 'url' and 'book_hash' fields

    Example:
        >>> book = {'id': '123', 'href': '/book/123/abc/title'}
        >>> normalized = normalize_book_details(book)
        >>> assert 'url' in normalized
        >>> assert 'book_hash' in normalized
    """
    normalized = book.copy()

    # Add 'url' from 'href' if missing
    if 'url' not in normalized and 'href' in normalized:
        href = normalized['href']

        if href.startswith('http'):
            # Already full URL
            normalized['url'] = href
        else:
            # Relative path - construct full URL
            mirror_url = mirror or os.getenv('ZLIBRARY_MIRROR', 'https://z-library.sk')
            normalized['url'] = f"{mirror_url.rstrip('/')}/{href.lstrip('/')}"

    # Extract book_hash if missing
    if 'book_hash' not in normalized and 'href' in normalized:
        hash_value = extract_book_hash_from_href(normalized['href'])
        if hash_value:
            normalized['book_hash'] = hash_value

    return normalized


async def _get_client(client: AsyncZlib = None) -> AsyncZlib:
    """
    Get Z-Library client instance.

    Supports dependency injection for testing and resource management.
    Falls back to module-level default for backward compatibility.

    Args:
        client: Optional AsyncZlib instance (for dependency injection)

    Returns:
        AsyncZlib instance (authenticated)
    """
    if client is not None:
        return client

    # Backward compatibility: use deprecated default client
    return await client_manager.get_default_client()


async def initialize_client():
    """
    Initialize module-level default client.

    DEPRECATED: This function maintains backward compatibility but uses
    global state. New code should use:
        async with ZLibraryClient() as client:
            ...

    Returns:
        Authenticated AsyncZlib instance
    """
    global zlib_client

    logger.warning(
        "initialize_client() is deprecated. "
        "Use ZLibraryClient() with dependency injection instead."
    )

    # Use the new client manager
    zlib_client = await client_manager.get_default_client()
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

async def search(query, exact=False, from_year=None, to_year=None, languages=None, extensions=None, content_types=None, count=10, client: AsyncZlib = None):
    """
    Search for books based on title, author, etc.

    Args:
        query: Search query string
        exact: Use exact matching
        from_year: Filter by start year
        to_year: Filter by end year
        languages: List of language codes
        extensions: List of file extensions
        content_types: List of content types
        count: Number of results
        client: Optional AsyncZlib instance (for dependency injection)

    Returns:
        dict with 'retrieved_from_url' and 'books'
    """
    # Use dependency injection or fallback to default
    zlib = await _get_client(client)

    langs = _parse_enums(languages, Language)
    exts = _parse_enums(extensions, Extension)

    # Execute the search
    logger.info(f"python_bridge.search: Calling zlib.search with query='{query}', exact={exact}, from_year={from_year}, to_year={to_year}, lang={langs}, extensions={exts}, content_types={content_types}, count={count}")

    # Build search kwargs (content_types not supported by base zlibrary)
    search_result = await zlib.search(
        q=query,
        exact=exact,
        from_year=from_year,
        to_year=to_year,
        lang=langs,
        extensions=exts,
        count=count
    )

    # Handle both tuple and non-tuple returns
    if isinstance(search_result, tuple):
        paginator, constructed_url = search_result
    else:
        paginator = search_result
        constructed_url = f"Search for: {query}"

    # Get the first page of results
    book_results = await paginator.next()
    # Diagnostic step:
    constructed_url_to_return = str(constructed_url) # Removed diagnostic prefix
    return {
        "retrieved_from_url": constructed_url_to_return,
        "books": book_results
    }

async def search_advanced(query, exact=False, from_year=None, to_year=None, languages=None, extensions=None, content_types=None, count=10):
    """
    Advanced search with exact and fuzzy match separation.

    Returns search results separated into exact matches and fuzzy matches
    based on Z-Library's fuzzyMatchesLine divider.

    Returns:
        dict with keys:
            - has_fuzzy_matches: bool
            - exact_matches: list of book dicts
            - fuzzy_matches: list of book dicts
            - total_results: int
            - query: str
            - retrieved_from_url: str
    """
    if not zlib_client:
        await initialize_client()

    # Import advanced search module
    from lib import advanced_search

    # Get credentials from environment
    email = os.environ.get('ZLIBRARY_EMAIL')
    password = os.environ.get('ZLIBRARY_PASSWORD')
    mirror = os.environ.get('ZLIBRARY_MIRROR', '')

    # Convert languages and extensions to comma-separated strings if needed
    langs_str = ','.join(languages) if languages else None
    exts_str = ','.join(extensions) if extensions else None

    # Call advanced search
    logger.info(f"python_bridge.search_advanced: Calling advanced_search with query='{query}', exact={exact}, from_year={from_year}, to_year={to_year}")

    result = await advanced_search.search_books_advanced(
        query=query,
        email=email,
        password=password,
        mirror=mirror,
        year_from=from_year,
        year_to=to_year,
        languages=langs_str,
        extensions=exts_str,
        page=1,
        limit=count
    )

    # Add retrieved_from_url for consistency with other search functions
    result['retrieved_from_url'] = f"Advanced search for: {query}"

    return result

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

    Args:
        book_details: Book dictionary from search (must have 'url' or 'href')
        output_dir: Directory to save downloaded file
        process_for_rag: If True, also extract text for RAG
        processed_output_format: Format for RAG output ('txt' or 'markdown')

    Returns:
        dict with 'file_path' and optional 'processed_file_path'
    """
    if not zlib_client:
        await initialize_client()

    # Normalize book details to ensure 'url' and 'book_hash' fields
    book_details = normalize_book_details(book_details)

    # Now get the URL (normalized function ensures it exists)
    book_page_url = book_details.get('url')

    if not book_page_url:
        logger.error(f"Critical: Neither 'url' nor 'href' found in book_details: {list(book_details.keys())}")
        raise ValueError("Missing 'url' or 'href' key in bookDetails object. Cannot download without book page URL.")

    downloaded_file_path_str = None
    final_file_path_str = None # Path with enhanced filename
    processed_file_path_str = None # Path for RAG processed file

    try:
        # Step 1: Download the book using the library's method.
        # This will save it with a name determined by the zlibrary library (likely just ID.ext or similar).
        original_download_path_str = await zlib_client.download_book(book_details=book_details, output_dir_str=output_dir)
        
        if not original_download_path_str or not Path(original_download_path_str).exists():
            raise FileNotFoundError(f"Book download failed or file not found at: {original_download_path_str}")

        # Step 2: Create the unified filename.
        # Ensure 'extension' is in book_details for create_unified_filename
        if 'extension' not in book_details and original_download_path_str:
             _, ext_from_path = os.path.splitext(original_download_path_str)
             book_details['extension'] = ext_from_path.lstrip('.')

        # Use unified filename generation with disambiguation fields
        unified_filename = create_unified_filename(
            book_details,
            year=book_details.get('year', ''),
            language=book_details.get('language', '')
        )
        final_file_path = Path(output_dir) / unified_filename
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


async def get_book_metadata_complete(book_id: str, book_hash: str = None) -> dict:
    """
    Fetch complete metadata for a book by ID, including enhanced fields.

    This function fetches the book detail page HTML and extracts comprehensive metadata:
    - Description (500-1000 chars)
    - Terms (50-60+ conceptual keywords)
    - Booklists (10+ curated collections)
    - Rating (user ratings with count)
    - IPFS CIDs (2 formats for decentralized access)
    - Series information
    - Categories (hierarchical classification)
    - ISBNs (10 and 13)
    - Quality score
    - All standard book properties

    Args:
        book_id: Z-Library book ID (e.g., "1252896")
        book_hash: Optional book hash (will be fetched if not provided)

    Returns:
        Dictionary with complete metadata including enhanced fields
    """
    if not zlib_client:
        await initialize_client()

    try:
        # Construct book detail page URL
        # Z-Library book detail URLs: https://z-library.sk/book/{id}/{hash}/title
        # We need the hash to construct the URL, but we can also try without it

        # Get current mirror URL from authenticated client
        # The zlibrary client maintains the correct domain after login
        mirror_url = zlib_client.domain if zlib_client and hasattr(zlib_client, 'domain') else None
        if not mirror_url:
            # Fallback to environment or try common domains
            mirror_url = os.environ.get('ZLIBRARY_MIRROR')
            if not mirror_url:
                # This shouldn't happen after successful login, but provide fallback
                logger.warning("No mirror URL available from client, using fallback")
                mirror_url = 'https://z-library.sk'

        # If we don't have the hash, we need to search for the book first to get its URL
        if not book_hash:
            logger.info(f"No book_hash provided, searching for book ID {book_id} to get detail URL")
            # Search by ID (this is a fallback, ideally book_hash is provided)
            # Note: Z-Library doesn't support search by ID directly, so we'd need the title
            # For now, we'll require the book_hash or construct a minimal URL
            raise ValueError("book_hash is required for get_book_metadata_complete")

        # Construct book detail URL
        book_url = f"{mirror_url.rstrip('/')}/book/{book_id}/{book_hash}/"

        logger.info(f"Fetching book metadata from: {book_url}")

        # Fetch the book detail page HTML using shared client (connection pooling)
        client = await get_http_client()
        response = await client.get(book_url)
        response.raise_for_status()
        html = response.text

        logger.info(f"Fetched {len(html)} bytes of HTML for book {book_id}")

        # Extract enhanced metadata
        metadata = enhanced_metadata.extract_complete_metadata(html, mirror_url=mirror_url)

        # Add book ID and URL to metadata
        metadata['id'] = book_id
        metadata['book_hash'] = book_hash
        metadata['book_url'] = book_url

        # Log extraction results
        logger.info(f"Extracted metadata for book {book_id}: "
                   f"{len(metadata.get('terms', []))} terms, "
                   f"{len(metadata.get('booklists', []))} booklists, "
                   f"description length: {len(metadata.get('description', '') or '')}")

        return metadata

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise InternalBookNotFoundError(f"Book ID {book_id} not found (404)")
        else:
            raise InternalFetchError(f"HTTP error fetching book metadata: {e}")

    except Exception as e:
        logger.exception(f"Error fetching complete metadata for book {book_id}")
        raise RuntimeError(f"Failed to fetch complete metadata for book {book_id}: {e}") from e


# --- Main Execution Block ---
import argparse # Moved import here

# ===== PHASE 3: TERM, AUTHOR, AND BOOKLIST TOOLS =====

async def search_by_term_bridge(
    term: str,
    year_from: int = None,
    year_to: int = None,
    languages: list = None,
    extensions: list = None,
    limit: int = 25
) -> dict:
    """
    Search for books by conceptual term.

    Args:
        term: Conceptual term (e.g., "dialectic", "reflection")
        year_from: Optional start year filter
        year_to: Optional end year filter
        languages: Optional list of language codes
        extensions: Optional list of file extensions
        limit: Results per page (default: 25)

    Returns:
        dict with 'term', 'books', 'total_results'
    """
    if not zlib_client:
        await initialize_client()

    # Import term tools
    from lib import term_tools

    # Get credentials
    email = os.environ.get('ZLIBRARY_EMAIL')
    password = os.environ.get('ZLIBRARY_PASSWORD')
    mirror = os.environ.get('ZLIBRARY_MIRROR', '')

    # Convert lists to comma-separated strings if needed
    langs_str = ','.join(languages) if languages else None
    exts_str = ','.join(extensions) if extensions else None

    logger.info(f"python_bridge.search_by_term: term='{term}', year_from={year_from}, year_to={year_to}")

    result = await term_tools.search_by_term(
        term=term,
        email=email,
        password=password,
        mirror=mirror,
        year_from=year_from,
        year_to=year_to,
        languages=langs_str,
        extensions=exts_str,
        limit=limit
    )

    return result


async def search_by_author_bridge(
    author: str,
    exact: bool = False,
    year_from: int = None,
    year_to: int = None,
    languages: list = None,
    extensions: list = None,
    limit: int = 25
) -> dict:
    """
    Search for books by author with advanced options.

    Args:
        author: Author name (supports various formats)
        exact: If True, exact author name matching
        year_from: Optional start year filter
        year_to: Optional end year filter
        languages: Optional list of language codes
        extensions: Optional list of file extensions
        limit: Results per page (default: 25)

    Returns:
        dict with 'author', 'books', 'total_results'
    """
    if not zlib_client:
        await initialize_client()

    # Import author tools
    from lib import author_tools

    # Get credentials
    email = os.environ.get('ZLIBRARY_EMAIL')
    password = os.environ.get('ZLIBRARY_PASSWORD')
    mirror = os.environ.get('ZLIBRARY_MIRROR', '')

    # Convert lists to comma-separated strings if needed
    langs_str = ','.join(languages) if languages else None
    exts_str = ','.join(extensions) if extensions else None

    logger.info(f"python_bridge.search_by_author: author='{author}', exact={exact}")

    result = await author_tools.search_by_author(
        author=author,
        email=email,
        password=password,
        exact=exact,
        mirror=mirror,
        year_from=year_from,
        year_to=year_to,
        languages=langs_str,
        extensions=exts_str,
        limit=limit
    )

    return result


async def fetch_booklist_bridge(
    booklist_id: str,
    booklist_hash: str,
    topic: str,
    page: int = 1
) -> dict:
    """
    Fetch a Z-Library booklist.

    Args:
        booklist_id: Numeric ID of the booklist
        booklist_hash: Hash code for the booklist
        topic: Topic name (URL-safe)
        page: Page number (default: 1)

    Returns:
        dict with 'booklist_id', 'metadata', 'books', 'page'
    """
    if not zlib_client:
        await initialize_client()

    # Import booklist tools
    from lib import booklist_tools

    # Get credentials
    email = os.environ.get('ZLIBRARY_EMAIL')
    password = os.environ.get('ZLIBRARY_PASSWORD')
    mirror = os.environ.get('ZLIBRARY_MIRROR', '')

    logger.info(f"python_bridge.fetch_booklist: id={booklist_id}, hash={booklist_hash}, topic='{topic}'")

    result = await booklist_tools.fetch_booklist(
        booklist_id=booklist_id,
        booklist_hash=booklist_hash,
        topic=topic,
        email=email,
        password=password,
        page=page,
        mirror=mirror
    )

    return result


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
        elif function_name == 'get_book_metadata_complete':
             result = await get_book_metadata_complete(**args_dict)
        elif function_name == 'search_by_term_bridge':
             result = await search_by_term_bridge(**args_dict)
        elif function_name == 'search_by_author_bridge':
             result = await search_by_author_bridge(**args_dict)
        elif function_name == 'fetch_booklist_bridge':
             result = await fetch_booklist_bridge(**args_dict)
        elif function_name == 'search_advanced':
             result = await search_advanced(**args_dict)
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