# Architecture: PDF Processing Integration for RAG Pipeline (v2 - File Output)

**Date:** 2025-04-23 (Updated from 2025-04-14)

## 1. Overview

This document outlines the architectural changes required to add PDF document processing capabilities to the `zlibrary-mcp` server's Retrieval-Augmented Generation (RAG) pipeline. The integration focuses on leveraging the established Python bridge (`lib/python-bridge.py`) and aligns with the updated RAG pipeline design (v2) which saves processed output to files instead of returning raw text.

## 2. Architectural Changes

PDF processing will be integrated into the `process_document` function within `lib/python-bridge.py`, which now orchestrates text extraction, saving the result to a file, and returning the file path.

### 2.1. Integration Point (`lib/python-bridge.py`)

The existing file type detection logic within `process_document` remains, but the handling of the returned text from helper functions changes:

```python
# Inside process_document function...
ext = file_path.suffix.lower()
processed_text = None
output_file_path = None # New variable

try:
    if ext == '.epub':
        processed_text = _process_epub(file_path_str)
    elif ext == '.txt':
        processed_text = _process_txt(file_path_str)
    elif ext == '.pdf': # <-- Existing condition
        processed_text = _process_pdf(file_path_str) # Helper returns text
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    if processed_text is not None:
        # NEW: Save the processed text to a file
        output_file_path = _save_processed_text(file_path_str, processed_text, output_format) # New helper
        return {"processed_file_path": str(output_file_path)}
    else:
        # Handle cases where processing yielded no text (e.g., image PDF)
        # Error might have been raised within helper, or return None/empty
        # Specific error handling depends on helper implementation
        # For now, assume error raised or handled before this point if critical
        # If helper returns None/empty for non-critical reasons (e.g. image PDF),
        # it might be logged, but we don't save an empty file here.
        # The main RAG pipeline doc covers general error reporting.
        # Let's assume helpers raise exceptions for critical processing failures.
        # If helper returns None/empty string for valid reasons (image PDF),
        # we might return an indicator or log it, but not save a file.
        # Refined error handling TBD during implementation.
        # For now, focus on the successful save path.
        # If processed_text is None due to non-critical reason:
        logger.warning(f"No text extracted from {file_path_str}")
        # Return structure TBD - maybe None, maybe specific status
        # Let's assume for now it returns None or empty path if no text saved
        return {"processed_file_path": None} # Or appropriate indicator

except Exception as e:
    logger.error(f"Error processing {file_path_str}: {e}")
    # Re-raise or return structured error for Node.js
    # This aligns with general error handling in RAG pipeline doc
    raise # Or return {"error": ...}

```
*(Note: Exact implementation of saving and detailed error handling within `process_document` needs refinement)*

### 2.2. Helper Function Responsibility (`_process_pdf`)

The helper function `_process_pdf(file_path)` remains responsible for PDF-specific extraction logic using PyMuPDF/fitz. **Crucially, it returns the extracted text string to `process_document`, which then handles saving.**

### 2.3. New Helper Function (`_save_processed_text`)

A new helper function, `_save_processed_text(original_file_path, text_content, format)`, will be added to `lib/python-bridge.py`. It will:
*   Determine the output path in `./processed_rag_output/`.
*   Generate the filename using the convention (`<original_name>.processed.<format>`).
*   Create the output directory if it doesn't exist.
*   Write the `text_content` to the file.
*   Handle potential file I/O errors (permissions, disk space), raising a specific `FileSaveError`.
*   Return the `pathlib.Path` object of the saved file.

### 2.4. Error Handling

*   Errors during text extraction within `_process_pdf` (e.g., encrypted, corrupted, image-based) should be handled as before, potentially raising exceptions or returning specific error indicators/empty text.
*   Errors during file saving within `_save_processed_text` should raise a `FileSaveError`.
*   The main `process_document` function catches these errors and propagates them appropriately to the Node.js layer, which returns a structured error to the agent (as defined in the main RAG pipeline architecture document).

### 2.5. Extensibility

This design remains extensible. Adding support for new formats involves adding another `elif` condition, a corresponding `_process_format()` helper returning text, and ensuring `_save_processed_text` handles the output correctly.

## 3. Python Library Recommendation

*   **Recommended Library:** **PyMuPDF (fitz)** (Remains unchanged)
*   **Justification:** (Remains unchanged)
*   **Alternatives:** (Remains unchanged)

## 4. Implementation Outline (Updated)

*   **`lib/python-bridge.py`:**
    *   Add `import fitz`.
    *   Implement `_process_pdf(file_path)` using `fitz` to **return extracted text**.
    *   Implement `_save_processed_text(original_file_path, text_content, format)` to handle saving to `./processed_rag_output/`.
    *   Modify `process_document` to call the appropriate processor, then call `_save_processed_text`, and return `{"processed_file_path": path_str}` or handle errors.
*   **`requirements.txt`:**
    *   Ensure `PyMuPDF` is present.
*   **`lib/venv-manager.js`:**
    *   No changes anticipated.

## 5. Related Documents & Memory Bank Entries

*   `docs/architecture/rag-pipeline.md` (v2 - File Output)
*   Decision-PDFLibraryChoice-01
*   Decision-RAGOutputFile-01 (New decision regarding file output)
*   Pattern-RAGPipeline-FileOutput-01 (New pattern describing file output)