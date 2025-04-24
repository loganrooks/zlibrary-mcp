# RAG Document Processing Pipeline: Implementation Specification

**Version:** 2.0 (File Output)
**Date:** 2025-04-23

## 1. Overview

This document details the implementation specifics for the RAG (Retrieval-Augmented Generation) document processing pipeline within the `zlibrary-mcp` server. It covers the necessary changes to MCP tools, Node.js handlers, and the Python bridge to enable downloading and processing of EPUB, TXT, and PDF files for RAG workflows, **saving the processed output to a file and returning the file path.**

**Reason for Update (v2):** Original design returned raw text, causing agent instability. This version modifies the pipeline to save processed text to `./processed_rag_output/` and return the `processed_file_path`.

Refer to the [RAG Pipeline Architecture (v2)](./architecture/rag-pipeline.md) and [PDF Processing Integration Architecture (v2)](./architecture/pdf-processing-integration.md) documents for the high-level design and data flow.

## 2. MCP Tool Definitions

### 2.1. `download_book_to_file` (Updated)

*   **Description:** Downloads a book file from Z-Library and optionally processes its content for RAG, saving the result to a separate file.
*   **Input Schema (Zod):**
    ```typescript
    import { z } from 'zod';

    const DownloadBookToFileInputSchema = z.object({
      id: z.string().describe("The Z-Library book ID"),
      format: z.string().optional().describe("File format (e.g., \"pdf\", \"epub\")"), // Added format
      outputDir: z.string().optional().default("./downloads").describe("Directory to save the original file (default: './downloads')"),
      process_for_rag: z.boolean().optional().default(false).describe("If true, process content for RAG and save to processed output file"), // Updated description
      processed_output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')") // New field
    });
    ```
*   **Output Schema (Zod):**
    ```typescript
    // Output depends on the 'process_for_rag' flag
    const DownloadBookToFileOutputSchema = z.object({
        file_path: z.string().describe("The absolute path to the original downloaded file"),
        processed_file_path: z.string().optional().describe("The absolute path to the file containing processed text (only if process_for_rag was true)") // Updated field
    });
    ```

### 2.2. `process_document_for_rag` (Updated)

*   **Description:** Processes an existing local document file (EPUB, TXT, PDF) to extract plain text content for RAG, saving the result to a file.
*   **Input Schema (Zod):**
    ```typescript
    import { z } from 'zod';

    const ProcessDocumentForRagInputSchema = z.object({
      file_path: z.string().describe("The absolute path to the document file to process"),
      output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')") // New field
    });
    ```
*   **Output Schema (Zod):**
    ```typescript
    const ProcessDocumentForRagOutputSchema = z.object({
      processed_file_path: z.string().describe("The absolute path to the file containing extracted and processed plain text content") // Updated field
    });
    ```

## 3. Tool Registration (`index.ts`)

The tools are registered within `index.ts` using the MCP SDK v1.8.0 pattern. Handlers map tool names to implementation functions in `lib/zlibrary-api.ts` and use the Zod schemas for validation.

```typescript
// File: src/index.ts (Conceptual Snippet)
// ... imports (Server, StdioServerTransport, z, zlibraryApi, schemas) ...

// Assume schemas are defined or imported from e.g., './lib/schemas'
import {
  DownloadBookToFileInputSchema,
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
          description: 'Downloads a book file from Z-Library and optionally processes its content for RAG, saving the result to a separate file.', // Updated description
          inputSchema: DownloadBookToFileInputSchema, // Updated schema
          outputSchema: DownloadBookToFileOutputSchema, // Updated schema
        },
        {
          name: 'process_document_for_rag', // Updated description
          description: 'Processes an existing local document file (EPUB, TXT, PDF) to extract plain text content for RAG, saving the result to a file.',
          inputSchema: ProcessDocumentForRagInputSchema, // Updated schema
          outputSchema: ProcessDocumentForRagOutputSchema, // Updated schema
        },
      ];
    },
    call: async (request) => {
      // ... generic validation ...
      if (request.name === 'download_book_to_file') { // Use 'name' based on recent fixes
        const validatedArgs = DownloadBookToFileInputSchema.parse(request.arguments);
        const result = await zlibraryApi.downloadBookToFile(validatedArgs);
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
  // args = { id, format?, outputDir?, process_for_rag?, processed_output_format? }
  LOG `Downloading book ${args.id}, process_for_rag=${args.process_for_rag}`

  // Prepare arguments for Python script
  pythonArgs = {
    book_id: args.id,
    format: args.format, // Pass format if provided
    output_dir: args.outputDir,
    // output_filename: args.outputFilename, // Removed, Python handles naming
    process_for_rag: args.process_for_rag,
    processed_output_format: args.processed_output_format // Pass format
  }

  TRY
    // Call the Python bridge function
    resultJson = AWAIT callPythonFunction('download_book', pythonArgs)

    // Basic validation of Python response
    IF NOT resultJson OR NOT resultJson.file_path THEN
      THROW Error("Invalid response from Python bridge during download: Missing original file_path.")
    ENDIF
    IF args.process_for_rag AND resultJson.processed_file_path IS NULL THEN
       // If processing was requested but failed or yielded no path, it's an issue
       THROW Error("Invalid response from Python bridge: Processing requested but processed_file_path missing.")
    ENDIF

    // Construct the response object based on the schema
    response = {
      file_path: resultJson.file_path
    }
    // Include processed_file_path only if requested and successfully returned
    IF args.process_for_rag AND resultJson.processed_file_path IS NOT NULL THEN
      response.processed_file_path = resultJson.processed_file_path
    ENDIF

    RETURN response

  CATCH error
    LOG `Error in downloadBookToFile: ${error.message}`
    // Propagate a user-friendly error
    THROW Error(`Failed to download/process book ${args.id}: ${error.message}`)
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
    output_format: args.output_format // Pass format
  }

  TRY
    // Call the Python bridge function
    resultJson = AWAIT callPythonFunction('process_document', pythonArgs)

    // Basic validation of Python response
    IF NOT resultJson OR resultJson.processed_file_path IS NULL THEN
      THROW Error("Invalid response from Python bridge during processing. Missing processed_file_path.")
    ENDIF

    // Return the result object matching the schema
    RETURN {
      processed_file_path: resultJson.processed_file_path
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
# Dependencies: zlibrary, ebooklib, beautifulsoup4, lxml, PyMuPDF
# Standard Libs: json, sys, os, argparse, logging, pathlib
import json
import sys
import os
import argparse
import logging
from pathlib import Path
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

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf'] # Added PDF
PROCESSED_OUTPUT_DIR = Path("./processed_rag_output") # Relative to workspace root

# --- Custom Exceptions ---
class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
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
            # Return empty string instead of raising error for image PDFs
            return ""
            # raise ValueError("PDF contains no extractable text layer (possibly image-based)")
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
    if text_content is None:
         raise ValueError("Cannot save None content.")

    try:
        # Ensure output directory exists
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Construct output filename
        base_name = original_file_path.name
        output_filename = f"{base_name}.processed.{output_format}"
        output_file_path = PROCESSED_OUTPUT_DIR / output_filename

        logging.info(f"Saving processed text to: {output_file_path}")

        # Write content to file
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

# --- Core Bridge Functions (Updated) ---

def process_document(file_path_str: str, output_format: str = "txt") -> dict:
    """
    Detects file type, calls the appropriate processing function, saves the result,
    and returns a dictionary containing the processed file path.
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path_str}")

    _, ext = file_path.suffix.lower()
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

        # Save the result if text was extracted
        if processed_text is not None and processed_text.strip(): # Check if non-empty
            output_path = _save_processed_text(file_path, processed_text, output_format)
            return {"processed_file_path": str(output_path)}
        else:
            # Handle cases where no text was extracted (e.g., image PDF)
            logging.warning(f"No processable text extracted from {file_path}. No output file saved.")
            # Return None or an empty path to indicate no file was saved
            return {"processed_file_path": None}

    except ImportError as imp_err:
         logging.error(f"Missing dependency for processing {ext} file {file_path}: {imp_err}")
         raise RuntimeError(f"Missing required library to process {ext} files.") from imp_err
    except FileSaveError as save_err:
        # Propagate file saving errors directly
        logging.error(f"Failed to save processed output for {file_path}: {save_err}")
        raise save_err # Re-raise FileSaveError
    except Exception as e:
        logging.exception(f"Failed to process document {file_path}")
        if isinstance(e, (FileNotFoundError, ValueError)): raise e
        raise RuntimeError(f"An unexpected error occurred processing {file_path}: {e}") from e


def download_book(book_id, format=None, output_dir=None, process_for_rag=False, processed_output_format="txt"):
    """
    Downloads a book and optionally processes it, saving the processed text.
    Returns a dictionary containing file_path and optionally processed_file_path.
    """
    zl = ZLibrary() # Adjust initialization as needed
    logging.info(f"Attempting download for book_id: {book_id}, format: {format}")

    # Use the library's download method
    # Note: The original library might not support format selection directly in download.
    # This might require getting download info first, then downloading a specific link.
    # Assuming for now the library handles it or we adapt this call later.
    download_result_path_str = zl.download_book(
        book_id=book_id,
        # format=format, # Pass format if library supports it
        output_dir=output_dir,
        # output_filename=output_filename # Let library handle naming based on metadata
    )

    if not download_result_path_str or not os.path.exists(download_result_path_str):
        raise RuntimeError(f"Download failed or file not found for book_id: {book_id}")

    download_result_path = Path(download_result_path_str)
    logging.info(f"Book downloaded successfully to: {download_result_path}")

    result = {"file_path": str(download_result_path)}
    processed_path = None

    if process_for_rag:
        logging.info(f"Processing downloaded file for RAG: {download_result_path}")
        try:
            # Call the updated process_document which now saves the file
            process_result = process_document(str(download_result_path), processed_output_format)
            processed_path = process_result.get("processed_file_path")
            if processed_path:
                 result["processed_file_path"] = processed_path
            else:
                 # Log if processing happened but didn't yield a savable file
                 logging.warning(f"Processing requested for {download_result_path}, but no output file was saved (e.g., image PDF).")
                 result["processed_file_path"] = None # Explicitly set to None

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
            book_id = args_dict.get('book_id')
            if not book_id: raise ValueError("Missing 'book_id'")
            response = download_book(
                book_id,
                args_dict.get('format'),
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
            raise ValueError(f"Unknown function name: {cli_args.function_name}")

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

2.  **Update `requirements.txt`:**
    ```text
    # requirements.txt
    zlibrary # Or the specific version/fork used
    ebooklib
    beautifulsoup4
    lxml
    PyMuPDF
    ```

3.  **Update `lib/venv-manager.ts`:** Ensure `installDependencies` uses `pip install -r requirements.txt`.

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
    *   Verify `DownloadBookToFileInputSchema` accepts `process_for_rag`, `processed_output_format`.
    *   Verify `DownloadBookToFileOutputSchema` includes optional `processed_file_path`.
    *   Verify `ProcessDocumentForRagInputSchema` requires `file_path`, accepts optional `output_format`.
    *   Verify `ProcessDocumentForRagOutputSchema` requires `processed_file_path`.

2.  **Tool Registration (`src/index.ts`):**
    *   Test `tools/list` includes updated descriptions/schemas.
    *   Test `tools/call` routes correctly.
    *   Test input validation using updated Zod schemas.

3.  **Node.js Handlers (`src/lib/zlibrary-api.ts`):**
    *   `downloadBookToFile`: Mock `callPythonFunction`. Test `process_for_rag` flag passed. Test handling of responses with/without `processed_file_path`. Test error handling (missing paths).
    *   `processDocumentForRag`: Mock `callPythonFunction`. Test `file_path` and `output_format` passed. Test handling of successful response (`processed_file_path`) and error response.

4.  **Python Bridge - `download_book` (`lib/python_bridge.py`):**
    *   Mock `zlibrary.download_book`.
    *   Test `process_for_rag=False` -> Returns only `file_path`.
    *   Test `process_for_rag=True` -> Calls `process_document` internally.
    *   Test `process_for_rag=True` (Successful Processing) -> Returns `file_path` and `processed_file_path`.
    *   Test `process_for_rag=True` (Processing Fails/No Text) -> Returns `file_path` and `processed_file_path: None`.
    *   Test download failure handling.

5.  **Python Bridge - `process_document` (`lib/python_bridge.py`):**
    *   Test file type detection (EPUB, TXT, PDF, unsupported).
    *   Test routing to `_process_epub`, `_process_txt`, `_process_pdf`.
    *   Test calls `_save_processed_text` on success.
    *   Test returns `{"processed_file_path": path}` on success.
    *   Test returns `{"processed_file_path": None}` if no text extracted (e.g., image PDF).
    *   Test handling of `FileNotFoundError`.
    *   Test handling of `ValueError` (unsupported format).
    *   Test propagation of `FileSaveError`.
    *   Test propagation of processing errors (ImportError, RuntimeError).

6.  **Python Bridge - `_process_epub`, `_process_txt`, `_process_pdf` (`lib/python_bridge.py`):**
    *   (Existing tests remain relevant)
    *   Verify they return extracted text string or raise appropriate errors.
    *   Verify `_process_pdf` returns empty string for image PDFs.

7.  **Python Bridge - `_save_processed_text` (`lib/python_bridge.py`):**
    *   Test successful save returns correct `Path` object.
    *   Test directory creation (`./processed_rag_output/`).
    *   Test correct filename generation (`<original>.processed.<format>`).
    *   Test raises `FileSaveError` on OS errors (mock `open`/`write` to fail).
    *   Test raises `ValueError` if `text_content` is None.

8.  **Python Bridge - Main Execution (`lib/python_bridge.py`):**
    *   Test routing to updated `download_book` and `process_document`.
    *   Test passing of new format arguments.
    *   Test successful JSON output format (including `processed_file_path`).
    *   Test error JSON output format on exceptions (including `FileSaveError`).

9.  **Dependency Management (`src/lib/venv-manager.ts`):**
    *   Test `installDependencies` uses correct `requirements.txt` path.
    *   Test `pip install` command includes `--no-cache-dir`, `--force-reinstall`, `--upgrade`, `-r`.
    *   Test error handling.