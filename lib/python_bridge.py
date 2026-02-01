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
import aiofiles
from zlibrary.const import OrderOptions # Need this import

from pathlib import Path
from filename_utils import create_unified_filename
import logging

# Import the new RAG processing functions
from lib import rag_processing
# Import enhanced metadata extraction
from lib import enhanced_metadata
# Import client manager for dependency injection
from lib import client_manager

# Add zlibrary source directory to path for EAPI imports
zlibrary_src_path = os.path.join(os.path.dirname(__file__), '..', 'zlibrary', 'src')
if zlibrary_src_path not in sys.path:
    sys.path.insert(0, zlibrary_src_path)
from zlibrary.eapi import EAPIClient, normalize_eapi_book, normalize_eapi_search_response

# DEPRECATED: Global zlibrary client (for backward compatibility)
# New code should use dependency injection with ZLibraryClient
zlib_client = None
logger = logging.getLogger('zlibrary') # Get the 'zlibrary' logger instance

# Module-level EAPI client (created after login)
_eapi_client: EAPIClient = None

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


def normalize_book_details(book: dict, mirror: str = None) -> dict:
    """
    Normalize book details to ensure all required fields present.

    Handles both EAPI response format and legacy format:
    - EAPI provides 'hash' / 'book_hash' directly
    - Legacy format had 'href' with hash embedded in URL path
    - Ensures 'url', 'book_hash' fields for downstream operations

    Args:
        book: Book dictionary from search results
        mirror: Z-Library mirror URL (optional)

    Returns:
        Normalized book dictionary with guaranteed 'url' and 'book_hash' fields
    """
    normalized = book.copy()

    # EAPI provides hash directly — use it
    if 'book_hash' not in normalized:
        if 'hash' in normalized and normalized['hash']:
            normalized['book_hash'] = normalized['hash']
        elif 'href' in normalized:
            hash_value = _extract_book_hash_from_href(normalized['href'])
            if hash_value:
                normalized['book_hash'] = hash_value

    # Add 'url' from 'href' if missing
    if 'url' not in normalized and 'href' in normalized:
        href = normalized['href']
        if href.startswith('http'):
            normalized['url'] = href
        else:
            mirror_url = mirror or os.getenv('ZLIBRARY_MIRROR', 'https://z-library.sk')
            normalized['url'] = f"{mirror_url.rstrip('/')}/{href.lstrip('/')}"

    return normalized


def _extract_book_hash_from_href(href: str) -> str:
    """Extract book hash from href path like '/book/ID/HASH/title'."""
    if not href:
        return None
    parts = href.strip('/').split('/')
    if len(parts) >= 3 and parts[0] == 'book':
        return parts[2]
    return None


async def get_eapi_client() -> EAPIClient:
    """
    Get the shared EAPI client, creating it if needed.

    The EAPI client is created during initialize_eapi_client() which is
    called from main() after AsyncZlib login succeeds.

    Returns:
        Authenticated EAPIClient instance

    Raises:
        RuntimeError: If EAPI client not initialized
    """
    global _eapi_client
    if _eapi_client is None:
        raise RuntimeError("EAPI client not initialized. Call initialize_eapi_client() first.")
    return _eapi_client


async def initialize_eapi_client() -> EAPIClient:
    """
    Initialize the shared EAPI client using environment credentials.

    Creates an EAPIClient, logs in, discovers domains, and stores
    the client for reuse by all tool functions.

    Returns:
        Authenticated EAPIClient instance
    """
    global _eapi_client

    email = os.environ.get('ZLIBRARY_EMAIL')
    password = os.environ.get('ZLIBRARY_PASSWORD')

    if not email or not password:
        raise ValueError("ZLIBRARY_EMAIL and ZLIBRARY_PASSWORD environment variables required")

    # Use a known EAPI domain for initial login
    # Z-Library EAPI domains follow the pattern: z-library.sk, singlelogin.re, etc.
    initial_domain = os.environ.get('ZLIBRARY_EAPI_DOMAIN', 'z-library.sk')

    client = EAPIClient(initial_domain)
    login_result = await client.login(email, password)

    if login_result.get('success') != 1:
        raise RuntimeError(f"EAPI login failed: {login_result}")

    logger.info(f"EAPI client authenticated (userid={client.remix_userid})")

    # Discover optimal domain
    try:
        domains_result = await client.get_domains()
        domains = domains_result.get('domains', [])
        if domains:
            primary = domains[0] if isinstance(domains[0], str) else domains[0].get('domain', '')
            if primary and primary != initial_domain:
                logger.info(f"Switching EAPI domain: {initial_domain} -> {primary}")
                # Create new client on discovered domain with existing credentials
                new_client = EAPIClient(
                    primary,
                    remix_userid=client.remix_userid,
                    remix_userkey=client.remix_userkey,
                )
                await client.close()
                client = new_client
    except Exception as e:
        logger.warning(f"Domain discovery failed, using initial domain: {e}")

    _eapi_client = client
    return _eapi_client


async def eapi_health_check() -> dict:
    """
    Check EAPI connectivity and functionality.

    Performs a minimal search to verify the EAPI client can
    communicate with Z-Library successfully.

    Returns:
        dict with 'status' ('healthy' or 'unhealthy'), 'transport', and optionally 'error'
    """
    try:
        client = await get_eapi_client()
        response = await client.search("test", limit=1)

        if response.get('success') == 1 and isinstance(response.get('books'), list):
            return {
                'status': 'healthy',
                'transport': 'eapi',
                'books_returned': len(response.get('books', [])),
            }
        else:
            return {
                'status': 'unhealthy',
                'transport': 'eapi',
                'error': f"Unexpected response: success={response.get('success')}",
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'transport': 'eapi',
            'error': str(e),
        }


async def search(query, exact=False, from_year=None, to_year=None, languages=None, extensions=None, content_types=None, count=10, client=None):
    """
    Search for books using EAPI.

    Args:
        query: Search query string
        exact: Use exact matching
        from_year: Filter by start year
        to_year: Filter by end year
        languages: List of language codes
        extensions: List of file extensions
        content_types: List of content types (ignored by EAPI)
        count: Number of results
        client: Unused (kept for backward compatibility)

    Returns:
        dict with 'retrieved_from_url' and 'books'
    """
    eapi = await get_eapi_client()

    # Convert language/extension enums to strings for EAPI
    lang_list = None
    if languages:
        lang_list = [str(l) if not isinstance(l, str) else l for l in languages]
    ext_list = None
    if extensions:
        ext_list = [str(e) if not isinstance(e, str) else e for e in extensions]

    logger.info(f"python_bridge.search: EAPI search query='{query}', exact={exact}, count={count}")

    response = await eapi.search(
        message=query,
        limit=count,
        exact=exact,
        year_from=from_year,
        year_to=to_year,
        languages=lang_list,
        extensions=ext_list,
    )

    books = normalize_eapi_search_response(response)

    return {
        "retrieved_from_url": f"EAPI search: {query}",
        "books": books
    }


async def full_text_search(query, exact=False, phrase=True, words=False, languages=None, extensions=None, content_types=None, count=10):
    """
    Search for text within book contents via EAPI.

    Note: EAPI does not have a separate full-text search endpoint.
    Routes through regular EAPI search.
    """
    # Route through regular EAPI search (full-text specific params not supported)
    return await search(
        query=query,
        exact=exact,
        from_year=None,
        to_year=None,
        languages=languages,
        extensions=extensions,
        content_types=content_types,
        count=count,
    )


async def get_download_history(count=10):
    """Get user's download history via EAPI."""
    eapi = await get_eapi_client()
    response = await eapi.get_downloaded(limit=count)
    books = response.get('books', [])
    return [normalize_eapi_book(b) for b in books]


async def get_download_limits():
    """Get user's download limits via EAPI profile."""
    eapi = await get_eapi_client()
    profile = await eapi.get_profile()
    user = profile.get('user', profile)
    return {
        'daily_limit': user.get('downloads_today_limit', 'unknown'),
        'daily_remaining': user.get('downloads_today_left', 'unknown'),
    }


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
    Downloads a book, optionally processes it, and returns file paths.

    Uses the AsyncZlib client for the actual download (which handles
    the download page scraping internally).

    Args:
        book_details: Book dictionary from search (must have 'url' or 'href')
        output_dir: Directory to save downloaded file
        process_for_rag: If True, also extract text for RAG
        processed_output_format: Format for RAG output ('txt' or 'markdown')

    Returns:
        dict with 'file_path' and optional 'processed_file_path'
    """
    # Get the legacy client for download (download still uses AsyncZlib)
    zlib = await client_manager.get_default_client()

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
        original_download_path_str = await zlib.download_book(book_details=book_details, output_dir_str=output_dir)

        if not original_download_path_str or not Path(original_download_path_str).exists():
            raise FileNotFoundError(f"Book download failed or file not found at: {original_download_path_str}")

        # Step 2: Create the unified filename.
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
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        os.rename(original_download_path_str, final_file_path_str)
        logger.info(f"Renamed downloaded file from {original_download_path_str} to {final_file_path_str}")
        downloaded_file_path_str = final_file_path_str

        # Step 4: Optionally process for RAG.
        if process_for_rag and downloaded_file_path_str:
            logger.info(f"Processing downloaded file for RAG: {downloaded_file_path_str}")
            process_result = await process_document(
                file_path_str=downloaded_file_path_str,
                output_format=processed_output_format,
                book_id=book_details.get('id'),
                author=book_details.get('author'),
                title=book_details.get('name') or book_details.get('title')
            )
            processed_file_path_str = process_result.get("processed_file_path")

        return {
            "file_path": downloaded_file_path_str,
            "processed_file_path": processed_file_path_str
        }

    except Exception as e:
        logger.exception(f"Error in download_book for book ID {book_details.get('id')}, URL {book_page_url}")
        raise e


async def get_book_metadata_complete(book_id: str, book_hash: str = None) -> dict:
    """
    Fetch complete metadata for a book by ID via EAPI.

    Uses the EAPI get_book_info endpoint instead of HTML scraping.

    Args:
        book_id: Z-Library book ID (e.g., "1252896")
        book_hash: Book hash (required)

    Returns:
        Dictionary with complete metadata including enhanced fields
    """
    if not book_hash:
        raise ValueError("book_hash is required for get_book_metadata_complete")

    eapi = await get_eapi_client()

    try:
        metadata = await enhanced_metadata.get_enhanced_metadata(
            book_id=int(book_id),
            book_hash=book_hash,
            eapi_client=eapi,
        )

        # Add book ID and hash to metadata
        metadata['id'] = book_id
        metadata['book_hash'] = book_hash

        logger.info(f"Extracted EAPI metadata for book {book_id}: "
                   f"description length: {len(metadata.get('description', '') or '')}")

        return metadata

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
    Search for books by conceptual term via EAPI.
    """
    from lib import term_tools

    eapi = await get_eapi_client()

    # Convert lists to comma-separated strings if needed
    langs_str = ','.join(languages) if languages else None
    exts_str = ','.join(extensions) if extensions else None

    logger.info(f"python_bridge.search_by_term: term='{term}', year_from={year_from}, year_to={year_to}")

    result = await term_tools.search_by_term(
        term=term,
        email="",  # Not needed when eapi_client provided
        password="",
        year_from=year_from,
        year_to=year_to,
        languages=langs_str,
        extensions=exts_str,
        limit=limit,
        eapi_client=eapi,
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
    Search for books by author via EAPI.
    """
    from lib import author_tools

    eapi = await get_eapi_client()

    langs_str = ','.join(languages) if languages else None
    exts_str = ','.join(extensions) if extensions else None

    logger.info(f"python_bridge.search_by_author: author='{author}', exact={exact}")

    result = await author_tools.search_by_author(
        author=author,
        email="",
        password="",
        exact=exact,
        year_from=year_from,
        year_to=year_to,
        languages=langs_str,
        extensions=exts_str,
        limit=limit,
        eapi_client=eapi,
    )

    return result


async def fetch_booklist_bridge(
    booklist_id: str,
    booklist_hash: str,
    topic: str,
    page: int = 1
) -> dict:
    """
    Fetch a Z-Library booklist via EAPI (degraded: topic search fallback).
    """
    from lib import booklist_tools

    eapi = await get_eapi_client()

    logger.info(f"python_bridge.fetch_booklist: id={booklist_id}, hash={booklist_hash}, topic='{topic}'")

    result = await booklist_tools.fetch_booklist(
        booklist_id=booklist_id,
        booklist_hash=booklist_hash,
        topic=topic,
        email="",
        password="",
        page=page,
        eapi_client=eapi,
    )

    return result


async def get_recent_books(count: int = 10) -> dict:
    """Get recently added books via EAPI."""
    eapi = await get_eapi_client()
    response = await eapi.get_recently()
    books = response.get('books', [])
    return {
        'books': [normalize_eapi_book(b) for b in books[:count]],
    }


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

        # Use a new variable for subsequent operations
        args_dict = args_dict_immediately_after_parse.copy()
        logger.info(f"python_bridge.main: Initial args_dict (now a copy) for processing: {args_dict}")

    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments provided."}), file=sys.stderr)
        sys.exit(1)

    try:
        # Initialize EAPI client for all functions except local file processing
        if function_name not in ['process_document']:
            await initialize_eapi_client()

        # Standardize 'language' key to 'languages' if present for search functions
        if function_name in ['search', 'full_text_search']:
            if 'language' in args_dict and args_dict['language']:
                args_dict['languages'] = args_dict.pop('language')
            elif 'languages' in args_dict and args_dict['languages']:
                pass
            else:
                args_dict['languages'] = []

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
        elif function_name == 'download_book':
             result = await download_book(**args_dict)
        elif function_name == 'process_document':
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
        elif function_name == 'get_recent_books':
             result = await get_recent_books(**args_dict)
        elif function_name == 'eapi_health_check':
             result = await eapi_health_check()
        else:
            raise ValueError(f"Unknown function: {function_name}")

        # Print only confirmation and path to stdout to avoid large content
        mcp_style_response = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result)
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
    finally:
        # Clean up EAPI client
        if _eapi_client:
            await _eapi_client.close()

if __name__ == "__main__":
    asyncio.run(main())
