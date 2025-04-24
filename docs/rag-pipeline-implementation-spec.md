# RAG Document Processing Pipeline: Implementation Specification

**Version:** 2.1 (Download Workflow Clarification)
**Date:** 2025-04-24

## 1. Overview

This document details the implementation specifics for the RAG (Retrieval-Augmented Generation) document processing pipeline within the `zlibrary-mcp` server. It covers the necessary changes to MCP tools, Node.js handlers, and the Python bridge to enable downloading and processing of EPUB, TXT, and PDF files for RAG workflows, **saving the processed output to a file and returning the file path.**

**Reason for Update (v2.1):** Clarify the download workflow for `download_book_to_file` to align with ADR-002, emphasizing the two-step process: obtaining `bookDetails` (including the book page URL) via `search_books`, passing these details to the tool, and the internal scraping mechanism used by the Python bridge to find the actual download link.

**Reason for Update (v2.0):** Original design returned raw text, causing agent instability. This version modifies the pipeline to save processed text to `./processed_rag_output/` and return the `processed_file_path`.

Refer to the [RAG Pipeline Architecture (v2)](./architecture/rag-pipeline.md), [PDF Processing Integration Architecture (v2)](./architecture/pdf-processing-integration.md), and [ADR-002: Reaffirm Download Workflow](./adr/ADR-002-Download-Workflow-Redesign.md) documents for the high-level design and data flow.

## 2. MCP Tool Definitions

### 2.1. `download_book_to_file` (Updated)

*   **Description:** Downloads a book file from Z-Library using details obtained from `search_books`. Internally, it fetches the book's page URL (contained within the input `bookDetails`), scrapes the page to find the actual download link, downloads the file, and optionally processes its content for RAG, saving the result to a separate file. See ADR-002 for details.
*   **Input Schema (Zod):**
    ```typescript
    import { z } from 'zod';

    const DownloadBookToFileInputSchema = z.object({
      // Changed from 'id' to 'bookDetails' to align with ADR-002
      bookDetails: z.object({}).passthrough().describe("The full book details object obtained from a search_books result, containing the necessary book page URL under the 'url' key."),
      // 'format' removed as it's determined internally during scraping/download
      outputDir: z.string().optional().default("./downloads").describe("Directory to save the original file (default: './downloads')"),
      process_for_rag: z.boolean().optional().default(false).describe("If true, process content for RAG and save to processed output file"),
      processed_output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')")
    });
    ```
*   **Output Schema (Zod):**
    ```typescript
    // Output depends on the 'process_for_rag' flag
    const DownloadBookToFileOutputSchema = z.object({
        file_path: z.string().describe("The absolute path to the original downloaded file"),
        processed_file_path: z.string().optional().nullable().describe("The absolute path to the file containing processed text (if process_for_rag was true and text was extracted), or null otherwise.") // Updated field, allow null
    });
    ```

### 2.2. `process_document_for_rag` (Updated)

*   **Description:** Processes an existing local document file (EPUB, TXT, PDF) to extract plain text content for RAG, saving the result to a file.
*   **Input Schema (Zod):**
    ```typescript
    import { z } from 'zod';

    const ProcessDocumentForRagInputSchema = z.object({
      file_path: z.string().describe("The absolute path to the document file to process"),
      output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')")
    });
    ```
*   **Output Schema (Zod):**
    ```typescript
    const ProcessDocumentForRagOutputSchema = z.object({
      // Allow null if processing yields no text (e.g., image PDF)
      processed_file_path: z.string().nullable().describe("The absolute path to the file containing extracted and processed plain text content, or null if no text was extracted.")
    });
    ```

## 3. Tool Registration (`index.ts`)

The tools are registered within `index.ts` using the MCP SDK v1.8.0 pattern. Handlers map tool names to implementation functions in `lib/zlibrary-api.ts` and use the Zod schemas for validation.

```typescript
// File: src/index.ts (Conceptual Snippet)
// ... imports (Server, StdioServerTransport, z, zlibraryApi, schemas) ...

// Assume schemas are defined or imported from e.g., './lib/schemas'
import {
  DownloadBookToFileInputSchema, // Use updated schema name if changed
  DownloadBookToFileOutputSchema,
  ProcessDocumentForRagInputSchema,
  ProcessDocumentForRagOutputSchema,
  // ... other schemas
} from './lib/schemas'; // Example path
import * as zlibraryApi from './lib/zlibrary-api'; // Assuming API functions are exported

const server = new Server({
  // ... other server options
  tools: {
    list: async () => {
      return [
        // ... other tools
        {
          name: 'download_book_to_file',
          description: 'Downloads a book file from Z-Library using details obtained from search_books. Internally scrapes the book page for the download link (see ADR-002), downloads, and optionally processes for RAG.', // Updated description
          inputSchema: DownloadBookToFileInputSchema, // Use updated schema
          outputSchema: DownloadBookToFileOutputSchema,
        },
        {
          name: 'process_document_for_rag',
          description: 'Processes an existing local document file (EPUB, TXT, PDF) to extract plain text content for RAG, saving the result to a file.',
          inputSchema: ProcessDocumentForRagInputSchema,
          outputSchema: ProcessDocumentForRagOutputSchema, // Use updated schema
        },
      ];
    },
    call: async (request) => {
      // ... generic validation ...
      if (request.name === 'download_book_to_file') { // Use 'name' based on recent fixes
        const validatedArgs = DownloadBookToFileInputSchema.parse(request.arguments); // Use updated schema
        const result = await zlibraryApi.downloadBookToFile(validatedArgs); // Pass validated args containing bookDetails
        // Optional: DownloadBookToFileOutputSchema.parse(result);
        return result;
      }
      if (request.name === 'process_document_for_rag') { // Use 'name'
        const validatedArgs = ProcessDocumentForRagInputSchema.parse(request.arguments);
        const result = await zlibraryApi.processDocumentForRag(validatedArgs);
        // Optional: ProcessDocumentForRagOutputSchema.parse(result);
        return result;
      }
      // ... handle other tools
      throw new Error(`Tool not found: ${request.name}`);
    },
  },
});

// ... transport setup and server.connect() ...
```

## 4. Node.js Handlers (`lib/zlibrary-api.ts`)

This module contains the TypeScript functions that orchestrate calls to the Python bridge.

```pseudocode
// File: src/lib/zlibrary-api.ts
// Dependencies: ./python-bridge, path

IMPORT callPythonFunction FROM './python-bridge' // Assumes this handles calling Python and parsing JSON response/error
IMPORT path

// --- Updated Function ---

ASYNC FUNCTION downloadBookToFile(args):
  // args = { bookDetails, outputDir?, process_for_rag?, processed_output_format? }
  LOG `Downloading book using details, process_for_rag=${args.process_for_rag}`

  // Prepare arguments for Python script
  pythonArgs = {
    book_details: args.bookDetails, // Pass the whole bookDetails object
    output_dir: args.outputDir,
    process_for_rag: args.process_for_rag,
    processed_output_format: args.processed_output_format
  }

  TRY
    // Call the Python bridge function
    resultJson = AWAIT callPythonFunction('download_book', pythonArgs)

    // Basic validation of Python response
    IF NOT resultJson OR NOT resultJson.file_path THEN
      THROW Error("Invalid response from Python bridge during download: Missing original file_path.")
    ENDIF
    // Check if processed_file_path exists (it could be null if processing yielded no text)
    IF args.process_for_rag AND resultJson.processed_file_path IS UNDEFINED THEN
       THROW Error("Invalid response from Python bridge: Processing requested but processed_file_path key is missing.")
    ENDIF

    // Construct the response object based on the schema
    response = {
      file_path: resultJson.file_path,
      // Include processed_file_path if processing was requested, preserving null if returned
      ...(args.process_for_rag && { processed_file_path: resultJson.processed_file_path })
    }

    RETURN response

  CATCH error
    LOG `Error in downloadBookToFile: ${error.message}`
    // Propagate a user-friendly error
    THROW Error(`Failed to download/process book: ${error.message}`) // Removed ID as it's inside bookDetails
  ENDTRY
END FUNCTION

// --- Updated Function ---

ASYNC FUNCTION processDocumentForRag(args):
  // args = { file_path, output_format? }
  LOG `Processing document for RAG: ${args.file_path}`

  // Resolve to absolute path before sending to Python
  absolutePath = path.resolve(args.file_path)

  pythonArgs = {
    file_path: absolutePath,
    output_format: args.output_format
  }

  TRY
    // Call the Python bridge function
    resultJson = AWAIT callPythonFunction('process_document', pythonArgs)

    // Basic validation of Python response (allow null processed_file_path)
    IF NOT resultJson OR resultJson.processed_file_path IS UNDEFINED THEN
      THROW Error("Invalid response from Python bridge during processing. Missing processed_file_path key.")
    ENDIF

    // Return the result object matching the schema
    RETURN {
      processed_file_path: resultJson.processed_file_path // Can be null
    }

  CATCH error
    LOG `Error in processDocumentForRag: ${error.message}`
    // Propagate a user-friendly error
    THROW Error(`Failed to process document ${args.file_path}: ${error.message}`)
  ENDTRY
END FUNCTION

// --- Export Functions ---
EXPORT { downloadBookToFile, processDocumentForRag /*, ... other functions */ }
```

## 5. Python Bridge (`lib/python_bridge.py`)

This script handles the core logic for downloading, processing, and saving files.

```python
# File: lib/python_bridge.py
# Dependencies: zlibrary, ebooklib, beautifulsoup4, lxml, PyMuPDF, httpx, aiofiles
# Standard Libs: json, sys, os, argparse, logging, pathlib, asyncio, urllib.parse
import json
import sys
import os
import argparse
import logging
import asyncio
from pathlib import Path
from urllib.parse import urljoin
from zlibrary import ZLibrary # Assumed installed via venv

# --- Attempt to import processing libraries ---
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

# --- Attempt to import download/scraping libraries ---
try:
    import httpx
    import aiofiles
    DOWNLOAD_LIBS_AVAILABLE = True
except ImportError:
    DOWNLOAD_LIBS_AVAILABLE = False


# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf']
PROCESSED_OUTPUT_DIR = Path("./processed_rag_output")
DOWNLOAD_SELECTOR = "a.btn.btn-primary.dlButton" # As per ADR-002

# --- Custom Exceptions ---
class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
    pass

class DownloadScrapeError(Exception):
    """Custom exception for errors during download link scraping."""
    pass

class DownloadExecutionError(Exception):
    """Custom exception for errors during the final file download."""
    pass


# --- Helper Functions for Processing ---

def _html_to_text(html_content):
    """Extracts plain text from HTML using BeautifulSoup."""
    if not html_content: return ""
    soup = BeautifulSoup(html_content, 'lxml')
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def _process_epub(file_path: Path) -> str:
    """Processes an EPUB file to extract plain text. Returns text string."""
    if not EBOOKLIB_AVAILABLE:
        raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB file: {file_path}")
    book = epub.read_epub(str(file_path))
    all_text = []
    items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    for item in items:
        content = item.get_content()
        if content:
            try:
                html_content = content.decode('utf-8', errors='ignore')
                text = _html_to_text(html_content)
                if text: all_text.append(text)
            except Exception as e:
                logging.warning(f"Could not decode/process item {item.get_name()} in {file_path}: {e}")
    full_text = "\n\n".join(all_text).strip()
    logging.info(f"Finished EPUB: {file_path}. Length: {len(full_text)}")
    return full_text

def _process_txt(file_path: Path) -> str:
    """Processes a TXT file. Returns text string."""
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

def _process_pdf(file_path: Path) -> str:
    """Processes a PDF file using PyMuPDF. Returns text string."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("Required library 'PyMuPDF' is not installed.")
    logging.info(f"Processing PDF: {file_path}")
    doc = None
    try:
        doc = fitz.open(str(file_path))
        if doc.is_encrypted:
            logging.warning(f"PDF is encrypted: {file_path}")
            raise ValueError("PDF is encrypted")
        all_text = []
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                text = page.get_text("text")
                if text: all_text.append(text.strip())
            except Exception as page_error:
                logging.warning(f"Could not process page {page_num + 1} in {file_path}: {page_error}")
        full_text = "\n\n".join(all_text).strip()
        if not full_text:
            logging.warning(f"No extractable text in PDF (image-based?): {file_path}")
            return "" # Return empty string for image PDFs
        logging.info(f"Finished PDF: {file_path}. Length: {len(full_text)}")
        return full_text
    except fitz.fitz.FitzError as fitz_error:
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

# --- New Helper Function for Saving ---

def _save_processed_text(original_file_path: Path, text_content: str, output_format: str = "txt") -> Path:
    """Saves the processed text content to a file."""
    if text_content is None: # Allow empty string, but not None
         raise ValueError("Cannot save None content.")

    try:
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        base_name = original_file_path.name
        output_filename = f"{base_name}.processed.{output_format}"
        output_file_path = PROCESSED_OUTPUT_DIR / output_filename
        logging.info(f"Saving processed text to: {output_file_path}")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        logging.info(f"Successfully saved processed text for {original_file_path.name}")
        return output_file_path
    except OSError as e:
        logging.error(f"OS error saving processed file {output_file_path}: {e}")
        raise FileSaveError(f"Failed to save processed file due to OS error: {e}") from e
    except Exception as e:
        logging.error(f"Unexpected error saving processed file {output_file_path}: {e}")
        raise FileSaveError(f"An unexpected error occurred while saving processed file: {e}") from e

# --- Helper for Scraping and Downloading (async) ---

async def _scrape_and_download(book_page_url: str, output_dir_str: str) -> str:
    """Fetches book page, scrapes download link, and downloads the file."""
    if not DOWNLOAD_LIBS_AVAILABLE:
        raise ImportError("Required libraries 'httpx' and 'aiofiles' are not installed.")

    headers = {'User-Agent': 'Mozilla/5.0 ...'} # Add appropriate User-Agent
    timeout = 30.0

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
        # 1. Fetch book page
        try:
            logging.info(f"Fetching book page: {book_page_url}")
            response = await client.get(book_page_url)
            response.raise_for_status() # Check for HTTP errors
        except httpx.RequestError as exc:
            logging.error(f"Network error fetching book page {book_page_url}: {exc}")
            raise DownloadScrapeError(f"Network error fetching book page: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            logging.error(f"HTTP error {exc.response.status_code} fetching book page {book_page_url}")
            raise DownloadScrapeError(f"HTTP error {exc.response.status_code} fetching book page.") from exc

        # 2. Parse and Scrape download link
        try:
            soup = BeautifulSoup(response.text, 'lxml')
            link_element = soup.select_one(DOWNLOAD_SELECTOR)
            if not link_element or not link_element.has_attr('href'):
                logging.error(f"Could not find download link using selector '{DOWNLOAD_SELECTOR}' on {book_page_url}")
                raise DownloadScrapeError("Download link selector not found on book page.")
            relative_url = link_element['href']
            download_url = urljoin(str(response.url), relative_url)
            logging.info(f"Found download URL: {download_url}")
        except Exception as exc:
            logging.exception(f"Error parsing book page {book_page_url}")
            raise DownloadScrapeError(f"Error parsing book page: {exc}") from exc

        # 3. Determine output path and filename
        output_dir = Path(output_dir_str)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Try to get filename from Content-Disposition or URL
        filename = download_url.split('/')[-1].split('?')[0] or "downloaded_book" # Basic fallback

        # 4. Download the file
        try:
            logging.info(f"Starting download from {download_url}")
            async with client.stream('GET', download_url) as download_response:
                # Try to get filename from header first
                content_disposition = download_response.headers.get('content-disposition')
                if content_disposition:
                    import re
                    fname_match = re.search(r'filename\*?=(?:UTF-8\'\')?([^;\n]*)', content_disposition, re.IGNORECASE)
                    if fname_match:
                        potential_fname = fname_match.group(1).strip('"')
                        # Basic sanitization
                        potential_fname = re.sub(r'[\\/*?:"<>|]', "_", potential_fname)
                        if potential_fname:
                            filename = potential_fname

                output_path = output_dir / filename
                logging.info(f"Saving download to: {output_path}")

                download_response.raise_for_status() # Check download request status

                async with aiofiles.open(output_path, 'wb') as f:
                    async for chunk in download_response.aiter_bytes():
                        await f.write(chunk)

            logging.info(f"Download complete: {output_path}")
            return str(output_path)

        except httpx.RequestError as exc:
            logging.error(f"Network error during download from {download_url}: {exc}")
            raise DownloadExecutionError(f"Network error during download: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            logging.error(f"HTTP error {exc.response.status_code} during download from {download_url}")
            raise DownloadExecutionError(f"HTTP error {exc.response.status_code} during download.") from exc
        except OSError as exc:
            logging.error(f"File system error saving download to {output_path}: {exc}")
            raise DownloadExecutionError(f"File system error saving download: {exc}") from exc
        except Exception as exc:
            logging.exception(f"Unexpected error during download/saving from {download_url}")
            raise DownloadExecutionError(f"Unexpected error during download: {exc}") from exc


# --- Core Bridge Functions (Updated) ---

def process_document(file_path_str: str, output_format: str = "txt") -> dict:
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

    try:
        logging.info(f"Starting processing for: {file_path}")
        if ext == '.epub':
            processed_text = _process_epub(file_path)
        elif ext == '.txt':
            processed_text = _process_txt(file_path)
        elif ext == '.pdf':
            processed_text = _process_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        # Save the result if text was extracted (allow empty string)
        if processed_text is not None:
            output_path = _save_processed_text(file_path, processed_text, output_format)
            return {"processed_file_path": str(output_path)}
        else:
            # Handle cases where no text was extracted (e.g., image PDF returned "")
            logging.warning(f"No processable text extracted from {file_path}. No output file saved.")
            return {"processed_file_path": None} # Indicate no file saved

    except ImportError as imp_err:
         logging.error(f"Missing dependency for processing {ext} file {file_path}: {imp_err}")
         raise RuntimeError(f"Missing required library to process {ext} files.") from imp_err
    except FileSaveError as save_err:
        logging.error(f"Failed to save processed output for {file_path}: {save_err}")
        raise save_err # Re-raise FileSaveError
    except Exception as e:
        logging.exception(f"Failed to process document {file_path}")
        if isinstance(e, (FileNotFoundError, ValueError)): raise e
        raise RuntimeError(f"An unexpected error occurred processing {file_path}: {e}") from e


def download_book(book_details: dict, output_dir=None, process_for_rag=False, processed_output_format="txt"):
    """
    Downloads a book using details containing the book page URL. Extracts the URL,
    fetches the page, scrapes the download link (selector: a.btn.btn-primary.dlButton),
    downloads the file, and optionally processes it. See ADR-002.
    Returns a dictionary containing file_path and optionally processed_file_path.
    """
    # Use default output dir if not provided
    output_dir_str = output_dir if output_dir else "./downloads"

    logging.info(f"Attempting download using book details, process_for_rag={process_for_rag}")

    book_page_url = book_details.get('url')
    if not book_page_url:
        raise ValueError("Missing 'url' (book page URL) in book_details input.")

    try:
        # Perform scraping and download using the async helper
        # Run the async function synchronously for the bridge
        download_result_path_str = asyncio.run(_scrape_and_download(book_page_url, output_dir_str))

    except (DownloadScrapeError, DownloadExecutionError) as download_err:
        logging.error(f"Download failed for book page {book_page_url}: {download_err}")
        raise RuntimeError(f"Download failed: {download_err}") from download_err
    except Exception as e:
        logging.exception(f"Unexpected error during download process for {book_page_url}")
        raise RuntimeError(f"Unexpected download error: {e}") from e

    # --- Post-Download Processing ---
    download_result_path = Path(download_result_path_str)
    logging.info(f"Book downloaded successfully to: {download_result_path}")

    result = {"file_path": str(download_result_path)}
    processed_path_str = None # Use string path

    if process_for_rag:
        logging.info(f"Processing downloaded file for RAG: {download_result_path}")
        try:
            # Call the updated process_document which now saves the file
            process_result = process_document(str(download_result_path), processed_output_format)
            processed_path_str = process_result.get("processed_file_path") # Can be None
            result["processed_file_path"] = processed_path_str # Assign None if processing yielded no text

        except Exception as e:
            # Log processing errors but don't fail the download result
            logging.error(f"Failed to process document after download for {download_result_path}: {e}")
            result["processed_file_path"] = None # Indicate processing failure

    return result

# --- Main Execution Block (Handles calls from Node.js) ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Z-Library MCP Python Bridge')
    parser.add_argument('function_name', type=str, help='Name of the function to call')
    parser.add_argument('json_args', type=str, help='JSON string containing function arguments')
    cli_args = parser.parse_args()

    try:
        args_dict = json.loads(cli_args.json_args)
        response = None # Initialize response

        if cli_args.function_name == 'download_book':
            book_details = args_dict.get('book_details')
            if not book_details or not isinstance(book_details, dict):
                 raise ValueError("Missing or invalid 'book_details' object")
            response = download_book(
                book_details,
                args_dict.get('output_dir'),
                args_dict.get('process_for_rag', False),
                args_dict.get('processed_output_format', "txt")
            )
        elif cli_args.function_name == 'process_document':
            file_path = args_dict.get('file_path')
            if not file_path: raise ValueError("Missing 'file_path'")
            response = process_document(
                file_path,
                args_dict.get('output_format', "txt")
            )
        # Add handlers for other Python functions if needed
        # elif cli_args.function_name == 'search_books': ...
        else:
            # --- Placeholder for other ZLibrary functions ---
            # Example: Forwarding to ZLibrary instance if function exists
            zl = ZLibrary()
            func = getattr(zl, cli_args.function_name, None)
            if func and callable(func):
                 logging.info(f"Calling ZLibrary function: {cli_args.function_name}")
                 # Note: ZLibrary functions might be async, requiring asyncio.run
                 # This needs careful checking based on the actual library methods
                 if asyncio.iscoroutinefunction(func):
                     response = asyncio.run(func(**args_dict))
                 else:
                     response = func(**args_dict)
            else:
                 raise ValueError(f"Unknown or non-callable function name: {cli_args.function_name}")

        # Print the successful JSON response to stdout
        print(json.dumps(response))
        sys.stdout.flush()

    except Exception as e:
        # Log the full error traceback to stderr
        logging.exception("Python bridge encountered an error")
        # Print a JSON error structure to stdout for Node.js
        error_response = {
            "error": type(e).__name__,
            "message": str(e)
        }
        print(json.dumps(error_response))
        sys.stdout.flush()
        sys.exit(1) # Exit with a non-zero code
```

## 6. Python Dependency Management

The RAG processing requires additional Python libraries.

1.  **Required Libraries:**
    *   `ebooklib`: For parsing EPUB files.
    *   `beautifulsoup4`: For cleaning HTML content.
    *   `lxml`: Recommended HTML parser for `beautifulsoup4`.
    *   `PyMuPDF`: For parsing PDF files.
    *   `httpx`: For async HTTP requests (downloading/scraping).
    *   `aiofiles`: For async file writing (downloading).

2.  **Update `requirements.txt`:**
    ```text
    # requirements.txt
    zlibrary # Or the specific version/fork used
    ebooklib
    beautifulsoup4
    lxml
    PyMuPDF
    httpx
    aiofiles
    ```

3.  **Update `lib/venv-manager.ts`:** Ensure `installDependencies` uses `pip install -r requirements.txt`. (Pseudocode remains the same as v2.0, assuming it correctly uses `-r`).

    ```pseudocode
    // File: src/lib/venv-manager.ts (Conceptual Snippet for installDependencies)

    FUNCTION installDependencies(venvDirPath):
      pipPath = getPlatformPipPath(venvDirPath)
      requirementsPath = path.resolve(__dirname, '..', '..', 'requirements.txt') // Adjust path relative to dist/lib

      IF NOT fs.existsSync(requirementsPath):
          LOG `requirements.txt not found at ${requirementsPath}, skipping.`
          RETURN
      ENDIF

      LOG `Installing/updating dependencies from ${requirementsPath} using: ${pipPath}`
      // Use '-r' and '--upgrade'
      // Add --no-cache-dir and --force-reinstall based on previous fixes
      command = `"${pipPath}" install --no-cache-dir --force-reinstall --upgrade -r "${requirementsPath}"`
      TRY
        EXECUTE command synchronously
        LOG "Dependencies installed/updated successfully."
      CATCH error
        THROW Error(`Failed to install Python dependencies: ${error.message}`)
      ENDTRY
    END FUNCTION
    ```

## 7. TDD Anchors (Updated)

1.  **Tool Schemas (`src/lib/schemas.ts`):**
    *   Verify `DownloadBookToFileInputSchema` requires `bookDetails` object, accepts optional `outputDir`, `process_for_rag`, `processed_output_format`.
    *   Verify `DownloadBookToFileOutputSchema` includes `file_path` and optional `processed_file_path` (nullable).
    *   Verify `ProcessDocumentForRagInputSchema` requires `file_path`, accepts optional `output_format`.
    *   Verify `ProcessDocumentForRagOutputSchema` requires `processed_file_path` (nullable).

2.  **Tool Registration (`src/index.ts`):**
    *   Test `tools/list` includes updated descriptions/schemas for `download_book_to_file`.
    *   Test `tools/call` routes `download_book_to_file` correctly.
    *   Test input validation using updated `DownloadBookToFileInputSchema`.

3.  **Node.js Handlers (`src/lib/zlibrary-api.ts`):**
    *   `downloadBookToFile`: Mock `callPythonFunction`. Test `bookDetails` object passed correctly. Test handling of responses with/without `processed_file_path` (including null). Test error handling (missing paths, Python errors).
    *   `processDocumentForRag`: Mock `callPythonFunction`. Test `file_path` and `output_format` passed. Test handling of successful response (`processed_file_path`, including null) and error response.

4.  **Python Bridge - `download_book` (`lib/python_bridge.py`):**
    *   Test raises `ValueError` if `book_details['url']` is missing.
    *   Test successful extraction of URL from `book_details`.
    *   Mock `_scrape_and_download`. Test it's called with correct URL and output dir.
    *   Test successful return from `_scrape_and_download` results in correct `file_path`.
    *   Test `DownloadScrapeError` or `DownloadExecutionError` from `_scrape_and_download` raises `RuntimeError`.
    *   Test `process_for_rag=True` calls `process_document` with the downloaded path.
    *   Test `process_for_rag=True` (Successful Processing) -> Returns `file_path` and `processed_file_path` (string path).
    *   Test `process_for_rag=True` (Processing Fails/No Text) -> Returns `file_path` and `processed_file_path: None`.

5.  **Python Bridge - `_scrape_and_download` (`lib/python_bridge.py`):**
    *   Test raises `ImportError` if `httpx`/`aiofiles` missing.
    *   Mock `httpx.AsyncClient.get` for book page fetch. Test successful fetch.
    *   Test book page fetch failure (network error) raises `DownloadScrapeError`.
    *   Test book page fetch failure (HTTP status error) raises `DownloadScrapeError`.
    *   Mock `BeautifulSoup` parsing. Test successful selection of download link (`a.btn.btn-primary.dlButton`) and extraction of `href`.
    *   Test parsing failure (selector not found) raises `DownloadScrapeError`.
    *   Test unexpected parsing error raises `DownloadScrapeError`.
    *   Mock `httpx.AsyncClient.stream` for final download. Test successful download writes file and returns correct path.
    *   Test filename extraction logic (Content-Disposition, URL fallback).
    *   Test final download failure (network error) raises `DownloadExecutionError`.
    *   Test final download failure (HTTP status error) raises `DownloadExecutionError`.
    *   Test file saving failure (OS error) raises `DownloadExecutionError`.

6.  **Python Bridge - `process_document` (`lib/python_bridge.py`):**
    *   (Anchors remain largely the same as v2.0)
    *   Test returns `{"processed_file_path": None}` if processing helper returns empty string.

7.  **Python Bridge - `_process_epub`, `_process_txt`, `_process_pdf` (`lib/python_bridge.py`):**
    *   (Anchors remain largely the same as v2.0)
    *   Verify they return extracted text string (or empty string for image PDF) or raise appropriate errors.

8.  **Python Bridge - `_save_processed_text` (`lib/python_bridge.py`):**
    *   (Anchors remain the same as v2.0)
    *   Test raises `ValueError` if `text_content` is None (but allows empty string).

9.  **Python Bridge - Main Execution (`lib/python_bridge.py`):**
    *   Test routing to updated `download_book`.
    *   Test passing of `book_details` object.
    *   Test successful JSON output format (including `processed_file_path`, potentially null).
    *   Test error JSON output format on exceptions (including `DownloadScrapeError`, `DownloadExecutionError`).

10. **Dependency Management (`src/lib/venv-manager.ts`):**
    *   (Anchors remain the same as v2.0)
    *   Ensure `httpx` and `aiofiles` are included in `requirements.txt` tests.