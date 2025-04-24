# PDF Processing Integration: Implementation Specification

**Version:** 2.0 (File Output)
**Date:** 2025-04-23

## 1. Overview

This document details the implementation specifics for integrating PDF document processing into the `zlibrary-mcp` server's RAG pipeline. It focuses on the Python bridge (`lib/python-bridge.py`) changes required to extract text from PDFs using `PyMuPDF (fitz)` and aligns with the v2 RAG architecture where processed text is saved to a file.

Refer to the [PDF Processing Integration Architecture (v2)](./architecture/pdf-processing-integration.md) document for the high-level design.

## 2. Python Bridge (`lib/python_bridge.py`) Modifications

### 2.1. Helper Function: `_process_pdf`

This function extracts text from a PDF file using `PyMuPDF`. **It returns the extracted text string.**

```python
# File: lib/python_bridge.py (Helper Function)
# Dependencies: fitz (PyMuPDF), os, logging, pathlib
import fitz # PyMuPDF
import os
import logging
from pathlib import Path

# Assume logging is configured

# Attempt to import fitz and set flag
try:
    import fitz # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def _process_pdf(file_path: Path) -> str:
    """
    Processes a PDF file using PyMuPDF to extract plain text.

    Args:
        file_path: Path object for the PDF file.

    Returns:
        The extracted plain text content as a string. Returns an empty string
        if the PDF contains no extractable text (e.g., image-based).

    Raises:
        ImportError: If PyMuPDF (fitz) is not installed.
        FileNotFoundError: If the file_path does not exist.
        ValueError: If the PDF is encrypted.
        RuntimeError: If there's an error opening or processing the PDF.
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("Required library 'PyMuPDF' is not installed.")
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

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
                text = page.get_text("text") # Extract plain text
                if text:
                    all_text.append(text.strip())
            except Exception as page_error:
                logging.warning(f"Could not process page {page_num + 1} in {file_path}: {page_error}")

        full_text = "\n\n".join(all_text).strip()

        if not full_text:
            logging.warning(f"No extractable text found in PDF (possibly image-based): {file_path}")
            # Return empty string for image-based or empty PDFs
            return ""
            # Previous version raised ValueError here, changed to return ""

        logging.info(f"Finished PDF: {file_path}. Extracted length: {len(full_text)}")
        return full_text

    except fitz.fitz.FitzError as fitz_error:
        logging.error(f"PyMuPDF error processing {file_path}: {fitz_error}")
        raise RuntimeError(f"Error opening or processing PDF: {file_path} - {fitz_error}") from fitz_error
    except Exception as e:
        # Re-raise specific errors if needed
        if isinstance(e, (ValueError, FileNotFoundError, ImportError)):
             raise e
        logging.error(f"Unexpected error processing PDF {file_path}: {e}")
        raise RuntimeError(f"Error opening or processing PDF: {file_path} - {e}") from e
    finally:
        if doc:
            try:
                doc.close()
            except Exception as close_error:
                logging.error(f"Error closing PDF document {file_path}: {close_error}")

```

### 2.2. Helper Function: `_save_processed_text` (New)

This function handles saving the extracted text content to the designated output directory.

```python
# File: lib/python_bridge.py (New Helper Function)
# Dependencies: logging, pathlib

import logging
from pathlib import Path

PROCESSED_OUTPUT_DIR = Path("./processed_rag_output") # Define output dir

class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
    pass

def _save_processed_text(original_file_path: Path, text_content: str, output_format: str = "txt") -> Path:
    """
    Saves the processed text content to a file in the PROCESSED_OUTPUT_DIR.

    Args:
        original_file_path: Path object of the original input file.
        text_content: The string content to save.
        output_format: The desired file extension for the output file (default 'txt').

    Returns:
        The Path object of the successfully saved file.

    Raises:
        ValueError: If text_content is None.
        FileSaveError: If any OS or unexpected error occurs during saving.
    """
    if text_content is None:
         raise ValueError("Cannot save None content.")

    try:
        # Ensure output directory exists
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Construct output filename: <original_name>.processed.<format>
        base_name = original_file_path.name
        output_filename = f"{base_name}.processed.{output_format}"
        output_file_path = PROCESSED_OUTPUT_DIR / output_filename

        logging.info(f"Saving processed text to: {output_file_path}")

        # Write content to file (UTF-8)
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
```

### 2.3. Core Function: `process_document` (Updated)

This function orchestrates the processing: it detects the file type, calls the appropriate helper (`_process_pdf`, `_process_epub`, `_process_txt`), receives the extracted text, calls `_save_processed_text`, and returns the path to the saved file.

```python
# File: lib/python_bridge.py (Updated Core Function)
# Dependencies: os, logging, pathlib
# Assumes _process_pdf, _process_epub, _process_txt, _save_processed_text are defined
# Assumes SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf']

import os
import logging
from pathlib import Path

# Assume other imports and helpers are present

def process_document(file_path_str: str, output_format: str = "txt") -> dict:
    """
    Detects file type, calls the appropriate processing function, saves the result,
    and returns a dictionary containing the processed file path.

    Args:
        file_path_str: Absolute path string to the document file.
        output_format: Desired output file format extension (default 'txt').

    Returns:
        A dictionary: {"processed_file_path": "path/to/output.processed.txt"}
        or {"processed_file_path": None} if no text was extracted/saved.

    Raises:
        FileNotFoundError: If input file not found.
        ValueError: If format is unsupported or PDF is encrypted.
        ImportError: If required processing library is missing.
        FileSaveError: If saving the processed text fails.
        RuntimeError: For other processing or unexpected errors.
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
            processed_text = _process_pdf(file_path) # Gets text string
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        # Save the result if non-empty text was extracted
        if processed_text: # Check if string is not None and not empty
            output_path = _save_processed_text(file_path, processed_text, output_format)
            return {"processed_file_path": str(output_path)}
        else:
            # Handle cases where no text was extracted (e.g., image PDF, empty file)
            logging.warning(f"No processable text extracted from {file_path}. No output file saved.")
            return {"processed_file_path": None} # Indicate no file saved

    except ImportError as imp_err:
         logging.error(f"Missing dependency for processing {ext} file {file_path}: {imp_err}")
         raise RuntimeError(f"Missing required library to process {ext} files.") from imp_err
    except FileSaveError as save_err:
        # Propagate file saving errors directly
        logging.error(f"Failed to save processed output for {file_path}: {save_err}")
        raise save_err # Re-raise FileSaveError
    except Exception as e:
        logging.exception(f"Failed to process document {file_path}")
        # Re-raise specific errors if they weren't caught earlier
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise e
        # Wrap unexpected errors
        raise RuntimeError(f"An unexpected error occurred processing {file_path}: {e}") from e

```

## 3. Python Dependency Management

*   **Required Library:** `PyMuPDF`
*   **`requirements.txt`:** Ensure `PyMuPDF` is listed.
*   **`lib/venv-manager.ts`:** Ensure it installs from `requirements.txt`. (See main RAG spec for details).

## 4. TDD Anchors (Updated)

1.  **`_process_pdf` (`lib/python_bridge.py`):**
    *   Test successful extraction returns text string.
    *   Test raises `ValueError` for encrypted PDF.
    *   Test raises `RuntimeError` for corrupted PDF.
    *   Test returns empty string (`""`) for image-based PDF.
    *   Test returns empty string (`""`) for empty PDF.
    *   Test raises `FileNotFoundError` for non-existent path.
    *   Test raises `ImportError` if `fitz` not available.

2.  **`_save_processed_text` (`lib/python_bridge.py`):**
    *   Test successful save returns correct `Path` object.
    *   Test directory creation (`./processed_rag_output/`).
    *   Test correct filename generation (`<original>.processed.<format>`).
    *   Test raises `FileSaveError` on OS errors (mock `open`/`write` to fail).
    *   Test raises `ValueError` if `text_content` is None.

3.  **`process_document` (`lib/python_bridge.py`):**
    *   Test routes `.pdf` extension to `_process_pdf`.
    *   Test calls `_save_processed_text` when `_process_pdf` returns non-empty text.
    *   Test returns `{"processed_file_path": path}` on successful processing and saving.
    *   Test does *not* call `_save_processed_text` if `_process_pdf` returns empty string.
    *   Test returns `{"processed_file_path": None}` if `_process_pdf` returns empty string.
    *   Test propagates errors from `_process_pdf` (e.g., `ValueError`, `RuntimeError`, `ImportError`).
    *   Test propagates `FileSaveError` from `_save_processed_text`.
    *   Test raises `FileNotFoundError` if input path doesn't exist.