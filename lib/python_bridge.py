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

def _process_epub(file_path):
    """Extracts text content from an EPUB file."""
    # The import itself will raise ImportError if ebooklib is not available.
    # No need for the EBOOKLIB_AVAILABLE flag check here.
    # if not EBOOKLIB_AVAILABLE:
    #      raise ImportError("Required library 'ebooklib' is not installed or available.")
    try:
        # Assuming ebooklib is available if we pass the check above
        book = epub.read_epub(file_path)
        content = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            # Extract text, trying to preserve paragraphs
            text = '\n\n'.join(p.get_text(strip=True) for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            if not text: # Fallback if no paragraph tags found
                text = soup.get_text(strip=True)
            content.append(text)
        return "\n\n".join(content)
    except Exception as e:
        raise Exception(f"Error processing EPUB {file_path}: {e}")

def _process_txt(file_path):
    """Reads content from a TXT file."""
    try:
        # Using errors='ignore' as a simple strategy for RAG where perfect fidelity isn't critical.
        # Consider 'replace' or more robust encoding detection if issues arise.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error processing TXT {file_path}: {e}")


def _process_pdf(file_path: str) -> str:
    """
    Extracts text content from a PDF file using PyMuPDF (fitz).

    Args:
        file_path: The absolute path to the PDF file.

    Returns:
        The extracted plain text content.

    Raises:
        FileNotFoundError: If the file_path does not exist.
        ValueError: If the PDF is encrypted or contains no extractable text.
        RuntimeError: If there's an error opening or processing the PDF.
        ImportError: If fitz (PyMuPDF) is not installed.
    """
    # Assuming logging is configured elsewhere or basicConfig is used
    # logging.basicConfig(level=logging.INFO) # Uncomment if basic logging needed
    logging.info(f"Processing PDF: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = None  # Initialize doc to None for finally block
    try:
        # Attempt to open the PDF
        doc = fitz.open(file_path)

        # Check for encryption
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted: {file_path}")
            raise ValueError("PDF is encrypted")

        all_text = []
        # Iterate through pages
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                text = page.get_text("text") # Extract plain text
                if text:
                    all_text.append(text.strip())
            except Exception as page_error:
                logging.warning(f"Could not process page {page_num + 1} in {file_path}: {page_error}")
                # Continue processing other pages

        # Combine extracted text
        full_text = "\n\n".join(all_text).strip()

        # Check if any text was extracted
        if not full_text:
            logging.warning(f"No extractable text found in PDF (possibly image-based): {file_path}")
            raise ValueError(
                "PDF contains no extractable text layer (possibly image-based)"
            )

        logging.info(f"Finished PDF: {file_path}. Extracted length: {len(full_text)}")
        return full_text

    except RuntimeError as fitz_error: # Catch generic runtime errors, potentially from fitz
        logging.error(f"PyMuPDF error processing {file_path}: {fitz_error}")
        raise RuntimeError(
            f"Error opening or processing PDF: {file_path} - {fitz_error}"
        )
    except Exception as e:
        # Catch other potential errors during opening or processing
        logging.error(f"Unexpected error processing PDF {file_path}: {e}")
        # Re-raise specific errors if needed
        if isinstance(e, (ValueError, FileNotFoundError)):
            raise e
        raise RuntimeError(
            f"Error opening or processing PDF: {file_path} - {e}"
        )
    finally:
        # Ensure the document is closed
        if doc:
            try:
                doc.close()
            except Exception as close_error:
                logging.error(f"Error closing PDF document {file_path}: {close_error}")


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
        output_filename = f"{original_path.name}.processed.{output_format}"
        output_path = processed_output_dir / output_filename

        logging.info(f"Saving processed text to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)

        return output_path
    except OSError as e:
        logging.exception(f"OS error saving processed file for {file_path_str}")
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
    """
    try:
        file_path = Path(file_path_str)
        if not file_path.exists():
             raise FileNotFoundError(f"File not found: {file_path_str}")

        ext = file_path.suffix.lower()
        processed_text = None

        if ext == '.epub':
            processed_text = _process_epub(file_path_str)
        elif ext == '.txt':
            processed_text = _process_txt(file_path_str)
        elif ext == '.pdf':
            processed_text = _process_pdf(file_path_str)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        # _process_pdf raises ValueError if no text is extracted.
        # Ensure other processors do too or handle None here if necessary.
        if processed_text is None:
             # This case should ideally not be reached if processors raise errors appropriately.
             logging.warning(f"Processing yielded None content for {file_path_str}, expected an exception.")
             raise ValueError(f"No text content could be extracted from {file_path_str}")

        # Save the processed text
        saved_path = _save_processed_text(file_path_str, processed_text, output_format)

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
            book_id = args_dict.get('book_id')
            format_arg = args_dict.get('format') # Keep format if needed by caller
            if not book_id: raise ValueError("Missing 'book_id'")
            response = asyncio.run(get_download_info(book_id, format_arg))
        elif function_name == 'full_text_search':
            response = asyncio.run(full_text_search(**args_dict))
        elif function_name == 'get_download_history':
            response = asyncio.run(get_download_history(**args_dict))
        elif function_name == 'get_download_limits':
            response = asyncio.run(get_download_limits())
        elif function_name == 'get_recent_books': # <<< CORRECTLY PLACED HANDLER
            response = asyncio.run(get_recent_books(**args_dict)) # <<< CORRECTLY PLACED HANDLER
        elif function_name == 'process_document':
            response = asyncio.run(process_document(**args_dict))
        elif function_name == 'download_book': # Handler for download_book
            if 'book_details' not in args_dict:
                 raise ValueError("Missing 'book_details' argument for download_book")
            book_details_arg = args_dict['book_details']
            output_dir_arg = args_dict.get('output_dir', './downloads')
            process_for_rag_arg = args_dict.get('process_for_rag', False)
            processed_output_format_arg = args_dict.get('processed_output_format', 'txt')
            response = asyncio.run(download_book(
                book_details=book_details_arg,
                output_dir=output_dir_arg,
                process_for_rag=process_for_rag_arg,
                processed_output_format=processed_output_format_arg
            ))
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
    except Exception as e:
        print(traceback.format_exc(), file=sys.stderr)
        print(json.dumps({"error": str(e)}))
        logging.exception(f"Unexpected error during {function_name}")
        # Re-added generic error message for unexpected errors
        print(json.dumps({"error": f"An unexpected error occurred: {e}"}))
        return 1

# --- New download_book function ---
# --- Internal Download/Scraping Helper (Spec v2.1) ---
async def _scrape_and_download(book_page_url: str, output_path: str) -> str: # Accept full output path
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


async def download_book(book_details: dict, output_dir='./downloads', process_for_rag=False, processed_output_format='txt') -> dict: # Expect book_details dict
    """
    Downloads a book using the provided details.
    Optionally processes the downloaded file for RAG.
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
                # Call process_document which handles extraction and saving
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