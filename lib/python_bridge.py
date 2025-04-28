#!/usr/bin/env python3
import sys
import os
import json
import traceback
import asyncio
from zlibrary import AsyncZlib, Extension, Language
from zlibrary.exception import DownloadError

import httpx
# import os # No longer needed after refactor
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

async def get_download_info(book_id, format=None):
    """
    Get book info including download URL using search workaround.
    """
    if not zlib_client:
        await initialize_client()

    try:
        book = await _find_book_by_id_via_search(book_id)
        
        # Safely extract details using .get()
        title = book.get('name', f"book_{book_id}")
        author = book.get('author', 'Unknown')
        # Use provided format if available, otherwise fallback to book extension, then 'pdf'
        file_format = format or book.get('extension', 'pdf')
        filesize = book.get('size', 'Unknown')
        download_url = book.get('download_url') # Can be None

        return {
            'title': title,
            'author': author,
            'format': file_format,
            'filesize': filesize,
            'download_url': download_url # Return None if not present
        }

    except Exception as e:
        logging.exception(f"Error in get_download_info for ID {book_id}")
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

# --- RAG Document Processing Functions ---

def _process_epub(file_path):
    """Extracts text content from an EPUB file."""
    try:
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


def _save_processed_text(original_file_path_str: str, text_content: str, output_format: str = 'txt') -> Path:
    """Saves the processed text content to a file."""
    # Define output dir inside the function
    processed_output_dir = Path("./processed_rag_output")

    if text_content is None:
        raise ValueError("Cannot save None content.")

    try:
        original_path = Path(original_file_path_str)
        # Ensure the output directory exists
        processed_output_dir.mkdir(parents=True, exist_ok=True) # Use the local variable

        # Generate filename: <original_name>.processed.<format>
        output_filename = f"{original_path.name}.processed.{output_format}"
        output_path = processed_output_dir / output_filename # Use the local variable

        logging.info(f"Saving processed text to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)

        return output_path
    except OSError as e:
        logging.exception(f"OS error saving processed file for {original_file_path_str}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}")
    except Exception as e:
        logging.exception(f"Unexpected error saving processed file for {original_file_path_str}")
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
        # Use pathlib.Path consistently
        file_path = Path(file_path_str)
        if not file_path.exists():
             raise FileNotFoundError(f"File not found: {file_path_str}")

        ext = file_path.suffix.lower() # Use Path object's suffix attribute
        processed_text = None

        # Keep passing str if sub-functions expect it
        if ext == '.epub':
            processed_text = _process_epub(file_path_str)
        elif ext == '.txt':
            processed_text = _process_txt(file_path_str) # Keep passing str if sub-functions expect it
        elif ext == '.pdf':
             # Assuming fitz import check happens in _process_pdf
            processed_text = _process_pdf(file_path_str) # Keep passing str if sub-functions expect it
        else:
            # Use the updated SUPPORTED_FORMATS list
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        # Handle cases where processing might yield no text (e.g., image PDF)
        # _process_pdf now raises ValueError in this case, caught below.
        # If other processors might return None, handle here or ensure they raise.
        if processed_text is None:
             # This case might occur if a processing function returns None instead of raising error
             # Or if an image-only PDF was processed without raising ValueError (adjust _process_pdf if needed)
             logging.warning(f"Processing yielded no text content for {file_path_str}")
             # Decide how to handle - return error or specific indicator? Returning error for now.
             raise ValueError(f"No text content could be extracted from {file_path_str}")

        # Save the processed text
        saved_path = _save_processed_text(file_path_str, processed_text, output_format)

        # Return the path to the saved file
        return {"processed_file_path": str(saved_path)}

    except ImportError as imp_err:
         logging.error(f"Missing dependency for processing {ext} file {file_path_str}: {imp_err}")
         # Return error in the expected format
         return {"error": f"Missing required library to process {ext} files. Please check installation."}
    except (FileNotFoundError, ValueError, FileSaveError) as specific_err: # Catch specific processing/saving errors
        logging.error(f"Error processing document {file_path_str}: {specific_err}")
        return {"error": str(specific_err)}
    except Exception as e:
        # Log full traceback for unexpected errors
        logging.exception(f"Failed to process document {file_path_str}")
        # Wrap unexpected errors and return in expected format
        # Check if it's a re-raised error from _process_pdf etc.
        if isinstance(e, RuntimeError) and ("Error opening or processing PDF" in str(e)):
             return {"error": str(e)} # Propagate specific processing errors directly
        return {"error": f"An unexpected error occurred during document processing: {e}"}

def main():
    # Configure basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            # Explicitly get domain from args, falling back to default in the function if not provided
            domain_arg = args_dict.get('domain')
            if not book_id: raise ValueError("Missing 'book_id'")
            # Call the modified async function, passing domain if provided
            if domain_arg:
                response = asyncio.run(get_by_id(book_id, domain_arg))
            else:
                response = asyncio.run(get_by_id(book_id)) # Use default domain

        elif function_name == 'get_download_info':
            book_id = args_dict.get('book_id')
            format_arg = args_dict.get('format') # Keep format if needed by caller
            # Explicitly get domain from args, falling back to default in the function if not provided
            domain_arg = args_dict.get('domain')
            if not book_id: raise ValueError("Missing 'book_id'")
            # Call the modified async function, passing domain if provided
            if domain_arg:
                 response = asyncio.run(get_download_info(book_id, format_arg, domain_arg))
            else:
                 response = asyncio.run(get_download_info(book_id, format_arg)) # Use default domain

        elif function_name == 'full_text_search':
            response = asyncio.run(full_text_search(**args_dict))
        elif function_name == 'get_download_history':
            response = asyncio.run(get_download_history(**args_dict))
        elif function_name == 'get_download_limits':
            response = asyncio.run(get_download_limits()) # Removed **args_dict as function takes no args
        elif function_name == 'process_document':
            response = asyncio.run(process_document(**args_dict))
        elif function_name == 'download_book': # Handler for download_book
            # Expect 'book_details'
            if 'book_details' not in args_dict:
                 raise ValueError("Missing 'book_details' argument for download_book")
            # Pass the whole dict, but extract other relevant args if needed
            book_details_arg = args_dict['book_details']
            output_dir_arg = args_dict.get('output_dir', './downloads') # Keep output_dir optional
            process_for_rag_arg = args_dict.get('process_for_rag', False)
            processed_output_format_arg = args_dict.get('processed_output_format', 'txt')

            response = asyncio.run(download_book(
                book_details=book_details_arg, # Pass the book_details dict
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

    # --- Exception Handling (Catch errors raised from handlers or asyncio.run) ---
    except ValueError as ve: # Specifically catch ValueError (likely from BookNotFound translation or processing)
        logging.warning(f"ValueError during {function_name}: {ve}")
        print(json.dumps({"error": str(ve)})) # Return the specific error message
        return 1
    except RuntimeError as re: # Specifically catch RuntimeError (likely from Fetch/Parse translation or processing)
        logging.error(f"RuntimeError during {function_name}: {re}")
        print(json.dumps({"error": str(re)})) # Return the specific error message
        return 1
    except FileSaveError as fse: # Catch file saving errors
        logging.error(f"FileSaveError during {function_name}: {fse}")
        print(json.dumps({"error": str(fse)}))
        return 1
    except Exception as e:
        # Print traceback to stderr first
        print(traceback.format_exc(), file=sys.stderr)
        # Then print JSON error to stdout
        print(json.dumps({
            "error": str(e)
            # Optionally remove traceback from stdout JSON if it's now in stderr
            # "traceback": traceback.format_exc()
        }))
        # Catch any other unexpected errors
        logging.exception(f"Unexpected error during {function_name}")
        # Print traceback to stderr first
        print(traceback.format_exc(), file=sys.stderr)
        # Then print generic JSON error to stdout
        print(json.dumps({"error": f"An unexpected error occurred: {e}"}))
        return 1

# --- New download_book function ---
# --- Internal Download/Scraping Helper (Spec v2.1) ---
async def _scrape_and_download(book_page_url: str, output_dir_str: str) -> str:
    """
    Calls the zlibrary fork's download_book method which handles scraping and downloading.
    Note: This function now expects the *book_page_url*, not the full book_details dict,
    as the library's download_book method takes the URL.
    """
    logging.debug(f"_scrape_and_download called with URL: {book_page_url}, Output Dir: {output_dir_str}") # ADDED
    global zlib_client
    if not zlib_client:
        logging.debug("Initializing zlib_client inside _scrape_and_download") # ADDED
        await initialize_client()

    try:
        logging.debug("Inside _scrape_and_download try block") # ADDED
        # Construct a minimal book_details dict required by the library's download_book
        # The library primarily needs the URL for scraping, but might use ID for logging.
        # We extract the ID from the URL if possible as a fallback.
        try:
            book_id_from_url = book_page_url.split('/book/')[1].split('/')[0] if '/book/' in book_page_url else 'unknown_from_url'
        except IndexError:
            book_id_from_url = 'unknown_from_url'

        minimal_book_details = {
            'url': book_page_url,
            'id': book_id_from_url # Provide ID for potential logging within the library
        }

        # Construct filename using details (similar logic as before, but inside helper)
        file_format = 'unknown' # We don't know the format here, library handles it
        # Sanitize filename components
        safe_book_id = str(book_id_from_url).replace('/','_').replace('\\','_')
        safe_format = str(file_format).replace('/','_').replace('\\','_')
        # The library's download_book should ideally determine the correct extension.
        # We construct a temporary name; the library might overwrite it based on headers.
        filename = f"{safe_book_id}.{safe_format}"
        output_path = os.path.join(output_dir_str, filename)
        logging.debug(f"Constructed output path: {output_path}") # ADDED

        # Ensure output directory exists
        logging.debug(f"Ensuring output directory exists: {output_dir_str}") # ADDED
        os.makedirs(output_dir_str, exist_ok=True)
        logging.debug(f"Output directory ensured.") # ADDED

        # Call the library's download_book method
        logging.info(f"Calling zlib_client.download_book for URL: {book_page_url}, Output Path: {output_path}")
        logging.debug(f"Calling await zlib_client.download_book with details: {minimal_book_details}, path: {output_path}") # ADDED
        await zlib_client.download_book(
            book_details=minimal_book_details, # Pass minimal details containing the URL
            output_path=output_path
        )
        logging.debug(f"Await zlib_client.download_book completed.") # ADDED
        # IMPORTANT: The library's download_book returns None on success.
        # We need to return the *intended* output path. The library might save with a different name
        # based on Content-Disposition, but the tests expect the path passed to the helper.
        # For Green phase, assume the library saves to the exact output_path we constructed.
        # Refactor might involve checking the actual saved file name later.
        final_path = output_path # Assume this path for now
        logging.info(f"zlib_client.download_book completed for {book_page_url}. Assumed path: {final_path}")
        return final_path # Return the constructed path

    except DownloadError as e:
        # Catch specific download errors from the library
        logging.error(f"DownloadError during scrape/download for {book_page_url}: {e}")
        raise RuntimeError(f"Download failed: {e}") from e # Re-raise as RuntimeError for Node.js bridge
    except Exception as e:
        # Catch any other unexpected errors
        logging.exception(f"Unexpected error during scrape/download for {book_page_url}")
        raise RuntimeError(f"An unexpected error occurred during download: {e}") from e # Re-raise as RuntimeError

async def download_book(book_details: dict, output_dir='./downloads', process_for_rag=False, processed_output_format='txt') -> dict: # Expect book_details dict
    """
    Downloads a book by calling the scrape helper and optionally processes it for RAG.
    Returns a dictionary containing 'file_path' and optionally 'processed_file_path'
    or 'processing_error'.
    """
    # No need to initialize client here, _scrape_and_download handles it.
    # if not zlib_client:
    #     await initialize_client()

    original_file_path_str = None
    result = {"file_path": None, "processed_file_path": None, "processing_error": None}

    try:
        book_id = book_details.get('id', 'unknown_id') # Get ID for logging
        book_page_url = book_details.get('url')
        if not book_page_url:
             raise ValueError("Missing 'url' (book page URL) in book_details input.")

        logging.info(f"Preparing download for book ID {book_id} via _scrape_and_download...")

        # Step 1: Call the internal scraping and download helper
        original_file_path_str = await _scrape_and_download(book_page_url, output_dir)
        result["file_path"] = original_file_path_str
        logging.info(f"Download helper returned path: {original_file_path_str}")

        # Step 2: Process if requested by calling process_document
        if process_for_rag:
            logging.info(f"Processing downloaded book for RAG: {original_file_path_str}")
            try:
                # Use the existing process_document function
                processing_result = await process_document(original_file_path_str, processed_output_format)

                if "error" in processing_result:
                    # Log processing errors but don't fail the whole download operation
                    logging.error(f"Processing failed for {original_file_path_str}, but download succeeded: {processing_result['error']}")
                    result["processed_file_path"] = None # Indicate processing failed
                    result["processing_error"] = processing_result['error'] # Include error info
                elif "processed_file_path" in processing_result:
                    result["processed_file_path"] = processing_result["processed_file_path"]
                    logging.info(f"Processed text saved to: {result['processed_file_path']}")
                else:
                    # Should not happen if process_document returns correctly
                    logging.error(f"Unexpected result from process_document for {original_file_path_str}: {processing_result}")
                    result["processed_file_path"] = None
                    result["processing_error"] = "Unexpected result from internal processing function."

            except Exception as unexpected_proc_err:
                # Catch errors during the call to process_document itself
                logging.exception(f"Unexpected error calling process_document for {original_file_path_str}")
                result["processed_file_path"] = None
                result["processing_error"] = f"Unexpected error during processing call: {unexpected_proc_err}"

        return result # Return dict with file_path and optional processed_file_path/processing_error

    except Exception as download_err:
        # Catch errors during the download process (including from _scrape_and_download)
        current_book_id = book_details.get('id', 'unknown_id') # Get ID for logging
        logging.exception(f"Failed during download process for book ID {current_book_id}")
        # Re-raise specific errors if needed, or wrap them
        if isinstance(download_err, (ValueError, RuntimeError, DownloadError)): # Propagate known error types
             raise download_err
        raise RuntimeError(f"Failed during download process for book ID {current_book_id}: {download_err}") from download_err


if __name__ == "__main__":
    sys.exit(main())