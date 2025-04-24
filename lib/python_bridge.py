#!/usr/bin/env python3
import sys
import json
import traceback
import asyncio
from zlibrary import AsyncZlib, Extension, Language

import os
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

import fitz  # PyMuPDF
import logging
# Global zlibrary client
zlib_client = None

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

# Define supported formats (as per spec example)
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf']

async def process_document(file_path_str: str, output_format='text') -> dict:
    """Processes a document file (EPUB, TXT, PDF) to extract text content."""
    try:
        # Use os.path as per spec pseudocode for consistency
        if not os.path.exists(file_path_str):
            raise FileNotFoundError(f"File not found: {file_path_str}")

        _, ext = os.path.splitext(file_path_str)
        ext = ext.lower()
        processed_text = None

        if ext == '.epub':
            processed_text = _process_epub(file_path_str)
        elif ext == '.txt':
            processed_text = _process_txt(file_path_str)
        elif ext == '.pdf':
             # Assuming fitz import check happens in _process_pdf
            processed_text = _process_pdf(file_path_str)
        else:
            # Use the updated SUPPORTED_FORMATS list
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        # Currently only supports 'text' output
        if output_format != 'text':
            # Log a warning or handle differently if needed in the future
            # Currently, only text output is supported.
            pass # No operation needed if format is 'text' or ignored

        if processed_text is None:
             # This case might occur if a processing function returns None instead of raising error
             logging.error(f"Processing function returned None for {file_path_str}")
             raise RuntimeError(f"Processing function returned None for {file_path_str}")

        return {"processed_text": processed_text}

    except ImportError as imp_err:
         logging.error(f"Missing dependency for processing {ext} file {file_path_str}: {imp_err}")
         # Return error in the expected format
         return {"error": f"Missing required library to process {ext} files. Please check installation."}
    except (FileNotFoundError, ValueError) as specific_err: # Catch specific errors first
        logging.error(f"Error processing document {file_path_str}: {specific_err}")
        return {"error": str(specific_err)}
    except Exception as e:
        # Log full traceback for unexpected errors
        logging.exception(f"Failed to process document {file_path_str}")
        # Wrap unexpected errors and return in expected format
        # Check if it's a re-raised error from _process_pdf etc.
        if isinstance(e, RuntimeError) and ("Error opening or processing PDF" in str(e) or "Processing function returned None" in str(e)):
             return {"error": str(e)} # Propagate specific processing errors directly
        return {"error": f"An unexpected error occurred during document processing: {e}"}

# --- Main Execution Logic ---


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing arguments"}))
        return 1
    
    function_name = sys.argv[1]
    args_json = sys.argv[2]
    
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON arguments"}))
        return 1
    
    try:
        # Map function name to async function - using accurately named functions
        function_map = {
            'search': search,
            'get_by_id': get_by_id,
            'get_download_info': get_download_info,  # Renamed to accurately reflect behavior
            'full_text_search': full_text_search,
            'get_download_history': get_download_history,
            'get_download_limits': get_download_limits,
            'process_document': process_document # Added RAG processing function
        }
        
        if function_name not in function_map:
            print(json.dumps({"error": f"Unknown function: {function_name}"}))
            return 1
        
        # Execute the async function and get result
        result = asyncio.run(function_map[function_name](*args))
        
        # Output the result as JSON
        print(json.dumps(result))
        return 0
    
    except Exception as e:
        # Print traceback to stderr first
        print(traceback.format_exc(), file=sys.stderr)
        # Then print JSON error to stdout
        print(json.dumps({
            "error": str(e)
            # Optionally remove traceback from stdout JSON if it's now in stderr
            # "traceback": traceback.format_exc()
        }))
        return 1

if __name__ == "__main__":
    sys.exit(main())