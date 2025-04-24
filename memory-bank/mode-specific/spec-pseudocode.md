# Specification Writer Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
## Functional Requirements
### Feature: RAG Document Processing Pipeline (v2 - File Output)
- Added: 2025-04-23 23:37:09
- Description: Update the RAG pipeline to save processed text (EPUB, TXT, PDF) to `./processed_rag_output/` and return the `processed_file_path` instead of raw text. Involves updating `download_book_to_file` and `process_document_for_rag` tools (schemas, Node handlers), and Python bridge (`process_document` orchestrates extraction and saving via new `_save_processed_text` helper).
- Acceptance criteria: 1. `download_book_to_file` (process=true) returns `file_path` and `processed_file_path`. 2. `process_document_for_rag` returns `processed_file_path`. 3. Python bridge saves text to `./processed_rag_output/<original>.processed.<format>`. 4. File saving errors (`FileSaveError`) are handled and propagated. 5. Image-based/empty PDFs result in `processed_file_path: None`. 6. Tool schemas reflect new inputs/outputs.
- Dependencies: Node.js (`zod`), Python (`ebooklib`, `beautifulsoup4`, `lxml`, `PyMuPDF`), Existing `zlibrary` Python lib, Managed Python Venv.
- Status: Draft (Specification Complete)
- Related: Decision-RAGOutputFile-01, Pattern-RAGPipeline-FileOutput-01, `docs/rag-pipeline-implementation-spec.md` (v2), `docs/pdf-processing-implementation-spec.md` (v2)


### Feature: Search-First Internal ID Lookup
- Added: 2025-04-16 18:14:41
- Description: Implement internal fetching/parsing logic in `lib/python_bridge.py` to handle ID-based lookups (`get_book_by_id`, `get_download_info`) using a search-first approach. Uses `httpx` to search for the ID, parses the result to find the book page URL, fetches the book page, and parses details using `BeautifulSoup`. Defines `InternalBookNotFoundError`, `InternalParsingError`, `InternalFetchError`, modifies callers, adds `httpx`, `beautifulsoup4`, `lxml` dependencies (already present).
- Acceptance criteria: 1. `_internal_search` finds the correct book URL via search. 2. `_internal_search` handles no results gracefully. 3. `_internal_search` handles search page parsing errors (`InternalParsingError`). 4. `_internal_search` handles network/HTTP errors (`InternalFetchError`). 5. `_internal_get_book_details_by_id` calls search, fetches URL, parses details. 6. Raises `InternalBookNotFoundError` if search finds nothing or book page fetch is 404. 7. Raises `InternalParsingError` on search result or book page parsing failure. 8. Raises `InternalFetchError` on network/HTTP errors during fetch. 9. Callers (`get_book_details`/`get_download_info` handlers) correctly call internal function and translate `InternalBookNotFoundError` to `ValueError`, other errors to `RuntimeError`.
- Dependencies: Python (`httpx`, `beautifulsoup4`, `lxml`, `urllib.parse`), Existing Python bridge structure, Managed Python Venv.
- Status: Draft (Specification Complete)
- Related: Decision-SearchFirstIDLookup-01, `docs/search-first-id-lookup-spec.md`



### Feature: Internal ID-Based Book Lookup
- Added: 2025-04-16 08:12:25
- Description: Implement internal fetching/parsing logic in `lib/python_bridge.py` to handle ID-based lookups (`get_book_by_id`, `get_download_info`) due to external library failures. Uses `httpx` to fetch `/book/ID`, handles expected 404 as `InternalBookNotFoundError`, parses 200 OK if received (unexpected), defines `InternalParsingError`, modifies callers, adds `httpx` dependency.
- Acceptance criteria: 1. `_internal_get_book_details_by_id` raises `InternalBookNotFoundError` on 404. 2. Raises `httpx.HTTPStatusError` on other non-200 errors. 3. Parses details correctly on unexpected 200 OK. 4. Raises `InternalParsingError` on parsing failure. 5. Handles `httpx.RequestError`. 6. Callers (`get_book_details`/`get_download_info` handlers) correctly call internal function and translate `InternalBookNotFoundError` to `ValueError`, other errors to `RuntimeError`. 7. `httpx` is added to `requirements.txt` and installed.
- Dependencies: Python (`httpx`, `beautifulsoup4`, `lxml`), Existing Python bridge structure, Managed Python Venv.
- Status: Draft (Specification Complete)
- Related: Decision-InternalIDLookupURL-01, Pattern-InternalIDScraper-01

<!-- Append new requirements using the format below -->

### Feature: PDF Processing Integration (RAG Pipeline - Task 3)
- Added: 2025-04-14 14:08:30
- Description: Integrate PDF text extraction into the RAG pipeline using PyMuPDF (fitz) within `lib/python-bridge.py`. This involves adding a new `_process_pdf` helper function, updating the `process_document` function to route `.pdf` files to the new helper, and adding `PyMuPDF` to `requirements.txt`.
- Acceptance criteria: 1. `process_document` successfully extracts text from standard PDFs. 2. `process_document` raises appropriate errors for encrypted, corrupted, or image-based PDFs. 3. `PyMuPDF` dependency is installed correctly via `venv-manager.js`. 4. `_process_pdf` handles file not found errors. 5. `_process_pdf` handles `fitz` import errors gracefully.
- Dependencies: Python (`PyMuPDF`), Existing Python bridge structure, Managed Python Venv.
- Status: Draft (Specification Complete)


### Feature: RAG Document Processing Pipeline
- Added: 2025-04-14 12:13:00
- Description: Implement a pipeline to download (EPUB, TXT) and/or process documents for RAG. Includes updating `download_book_to_file` tool (add `process_for_rag` flag, update output schema) and creating `process_document_for_rag` tool (input `file_path`, output `processed_text`). Requires changes in `index.js` (tool registration/schemas), `lib/zlibrary-api.js` (handlers calling Python), and `lib/python-bridge.py` (updated download logic, new processing logic using `ebooklib`, `beautifulsoup4`).
- Acceptance criteria: 1. `download_book_to_file` with `process_for_rag=false` downloads file and returns only `file_path`. 2. `download_book_to_file` with `process_for_rag=true` downloads file, processes it (EPUB/TXT), and returns `file_path` and `processed_text`. 3. `process_document_for_rag` processes an existing EPUB/TXT file and returns `processed_text`. 4. Python bridge correctly handles EPUB extraction via `ebooklib`. 5. Python bridge correctly handles TXT reading (UTF-8, fallback). 6. Python bridge handles file not found, unsupported format, and processing errors gracefully. 7. New Python dependencies (`ebooklib`, `beautifulsoup4`, `lxml`) are managed by `venv-manager.js`.
- Dependencies: Node.js (`zod`), Python (`ebooklib`, `beautifulsoup4`, `lxml`), Existing `zlibrary` Python lib, Managed Python Venv.
- Status: Draft

### Feature: Managed Python Virtual Environment
- Added: 2025-04-14 03:31:01
- Description: Implement automated creation and management of a dedicated Python virtual environment for the `zlibrary` dependency within a user cache directory. This includes Python 3 detection, venv creation, dependency installation (`zlibrary`), storing the venv Python path, and modifying `zlibrary-api.js` to use this path.
- Acceptance criteria: 1. `zlibrary-mcp` successfully executes Python scripts using the managed venv. 2. Setup handles Python 3 detection errors gracefully. 3. Setup handles venv creation errors gracefully. 4. Setup handles dependency installation errors gracefully. 5. Subsequent runs use the existing configured venv.
- Dependencies: Node.js (`env-paths`, `child_process`, `fs`, `path`), User system must have Python 3 installed.
- Status: Draft

### Feature: Node.js SDK Import Fix
- Added: 2025-04-14 03:31:01
- Description: Correct the `require` statement in `index.js` to properly import the `@modelcontextprotocol/sdk`.
- Acceptance criteria: 1. `index.js` successfully imports the SDK without `ERR_PACKAGE_PATH_NOT_EXPORTED` errors. 2. Core SDK functionality is accessible.
- Dependencies: `@modelcontextprotocol/sdk` package.
- Status: Draft


## System Constraints
### Constraint: Processed Output Directory
- Added: 2025-04-23 23:37:09
- Description: Processed RAG text output is saved to `./processed_rag_output/` relative to the workspace root. The Python bridge must have write permissions to this directory.
- Impact: Requires the directory to exist or be creatable by the server process. Potential for clutter if not managed.
- Mitigation strategy: Python bridge's `_save_processed_text` function includes logic to create the directory (`mkdir(parents=True, exist_ok=True)`). Ensure server process has necessary permissions. Consider cleanup strategies if needed later.
- Related: Pattern-RAGPipeline-FileOutput-01


<!-- Append new constraints using the format below -->
### Constraint: Search-First Strategy Reliability
- Added: 2025-04-16 18:14:41
- Description: The 'Search-First' strategy depends entirely on the website's general search returning the correct book when queried with its ID. Previous investigations ([2025-04-16 07:27:22]) suggest this may be unreliable or non-functional.
- Impact: If search-by-ID fails, the entire lookup process fails (`InternalBookNotFoundError`). The strategy is also vulnerable to changes in search result page structure and book detail page structure.
- Mitigation strategy: Implement robust error handling for search failures (`InternalBookNotFoundError`). Use specific but potentially adaptable CSS selectors. Log search failures clearly. Consider this strategy high-risk and potentially temporary.
- Related: Decision-SearchFirstIDLookup-01



### Constraint: Web Scraping Brittleness (Internal ID Lookup)
- Added: 2025-04-16 08:12:25
- Description: The internal ID lookup relies on scraping the `/book/ID` page structure (in the unlikely event of a 200 OK). This is highly susceptible to website HTML changes and anti-scraping measures. The primary path (handling 404) is more robust but provides no book data.
- Impact: The 200 OK parsing logic may break frequently, requiring updates to CSS selectors. The 404 path provides limited functionality (only confirms non-existence).
- Mitigation strategy: Minimize reliance on the 200 OK path. Implement robust error handling and logging for parsing failures. Use specific, but potentially adaptable, CSS selectors. Regularly test against the live site (if feasible).


### Constraint: PyMuPDF Dependency and License
- Added: 2025-04-14 14:08:30
- Description: The project will depend on `PyMuPDF`. This library must be successfully installed into the managed Python environment. Its license is AGPL-3.0, which is deemed acceptable for this server-side use case but should be noted.
- Impact: PDF processing will fail if `PyMuPDF` cannot be installed or imported. License compliance must be maintained.
- Mitigation strategy: Ensure `requirements.txt` includes `PyMuPDF`. `venv-manager.js` must handle installation. Implement checks for `fitz` import within `python-bridge.py`.


### Constraint: Python RAG Libraries
- Added: 2025-04-14 12:13:00
- Description: The managed Python environment must successfully install `ebooklib`, `beautifulsoup4`, and `lxml` for EPUB processing.
- Impact: EPUB processing will fail if these libraries cannot be installed or imported.
- Mitigation strategy: Ensure `requirements.txt` is correct and `venv-manager.js` installs dependencies properly. Provide clear errors if import fails in `python-bridge.py`.

### Constraint: Python 3 Prerequisite
- Added: 2025-04-14 03:31:01
- Description: The user's system must have a functional Python 3 installation (version 3.6+ recommended for `venv`) accessible via the system's PATH or detectable by the chosen Node.js detection library.
- Impact: The managed venv setup will fail if Python 3 is not found.
- Mitigation strategy: Provide clear error messages guiding the user to install Python 3.


## Edge Cases
### Edge Case: File Saving - OS Error
- Identified: 2025-04-23 23:37:09
- Scenario: `_save_processed_text` attempts to write the processed file but encounters an OS error (e.g., insufficient permissions, disk full).
- Expected behavior: `_save_processed_text` raises `FileSaveError`. `process_document` catches it and propagates the error (or a `RuntimeError`) to Node.js. Node.js returns a structured error to the agent.
- Testing approach: Mock `open()` or `file.write()` within `_save_processed_text` to raise `OSError`. Verify `FileSaveError` is raised and handled correctly up the chain.

### Edge Case: File Saving - Unexpected Error
- Identified: 2025-04-23 23:37:09
- Scenario: An unexpected error occurs within `_save_processed_text` (e.g., during path manipulation, directory creation).
- Expected behavior: The function catches the generic `Exception`, logs it, and raises `FileSaveError` wrapping the original error.
- Testing approach: Inject errors into path manipulation or directory creation logic. Verify `FileSaveError` is raised.


<!-- Append new edge cases using the format below -->
### Edge Case: Search-First - Search Returns No Results
- Identified: 2025-04-16 18:14:41
- Scenario: `_internal_search` is called with a valid or invalid book ID, but the website's search yields no results (or parsing finds no items).
- Expected behavior: `_internal_search` returns an empty list. `_internal_get_book_details_by_id` catches this and raises `InternalBookNotFoundError`.
- Testing approach: Mock `httpx.get` to return HTML with no search results. Call `_internal_get_book_details_by_id`. Verify `InternalBookNotFoundError`.

### Edge Case: Search-First - Search Page Parsing Error
- Identified: 2025-04-16 18:14:41
- Scenario: `_internal_search` receives HTML, but the structure has changed, causing `BeautifulSoup` selectors (`#searchResultBox .book-item`, `a[href]`) to fail.
- Expected behavior: `_internal_search` raises `InternalParsingError`.
- Testing approach: Mock `httpx.get` to return malformed/changed HTML. Call `_internal_search`. Verify `InternalParsingError`.

### Edge Case: Search-First - Book Page Fetch 404
- Identified: 2025-04-16 18:14:41
- Scenario: `_internal_search` successfully returns a `book_page_url`, but fetching that URL results in a 404.
- Expected behavior: `_internal_get_book_details_by_id` catches the 404 and raises `InternalBookNotFoundError`.
- Testing approach: Mock `_internal_search` to return a URL. Mock `httpx.get` for that URL to return a 404 status. Call `_internal_get_book_details_by_id`. Verify `InternalBookNotFoundError`.

### Edge Case: Search-First - Book Page Parsing Error
- Identified: 2025-04-16 18:14:41
- Scenario: Book page is fetched successfully, but its structure has changed, causing detail selectors (title, author, download link) to fail.
- Expected behavior: `_internal_get_book_details_by_id` raises `InternalParsingError` (either during parsing or when checking for essential missing data).
- Testing approach: Mock `_internal_search` to return a URL. Mock `httpx.get` to return malformed/changed book page HTML. Call `_internal_get_book_details_by_id`. Verify `InternalParsingError`.



### Edge Case: PDF Processing - Encrypted PDF
- Identified: 2025-04-14 14:08:30
- Scenario: `_process_pdf` is called with a password-protected/encrypted PDF.
- Expected behavior: `fitz.open()` succeeds, but `doc.is_encrypted` returns true. `_process_pdf` raises `ValueError("PDF is encrypted")`.
- Testing approach: Obtain/create an encrypted PDF. Call `_process_pdf`. Verify the correct `ValueError`.

### Edge Case: PDF Processing - Corrupted PDF
- Identified: 2025-04-14 14:08:30
- Scenario: `_process_pdf` is called with a corrupted or malformed PDF file that `fitz` cannot open or process correctly.
- Expected behavior: `fitz.open()` or page processing methods raise an exception (e.g., `fitz.fitz.FitzError`, `RuntimeError`). `_process_pdf` catches this and raises `RuntimeError("Error opening or processing PDF: ...")`.
- Testing approach: Obtain/create a corrupted PDF. Call `_process_pdf`. Verify the correct `RuntimeError`.

### Edge Case: PDF Processing - Image-Based PDF
- Identified: 2025-04-14 14:08:30
- Scenario: `_process_pdf` is called with a PDF containing only scanned images without an OCR text layer.
- Expected behavior: `page.get_text("text")` returns empty strings for all pages. `_process_pdf` detects the empty `full_text` result and raises `ValueError("PDF contains no extractable text layer (possibly image-based)")`.
- Testing approach: Obtain/create an image-only PDF. Call `_process_pdf`. Verify the correct `ValueError`.

### Edge Case: PDF Processing - Empty PDF
- Identified: 2025-04-14 14:08:30
- Scenario: `_process_pdf` is called with a valid PDF file that contains no pages or no text content.
- Expected behavior: Similar to image-based PDF, no text is extracted. `_process_pdf` raises `ValueError("PDF contains no extractable text layer (possibly image-based)")`.
- Testing approach: Create an empty PDF. Call `_process_pdf`. Verify the correct `ValueError`.

### Edge Case: PDF Processing - `fitz` Import Error
- Identified: 2025-04-14 14:08:30
- Scenario: `python-bridge.py` attempts to `import fitz` but `PyMuPDF` is not installed in the venv.
- Expected behavior: An `ImportError` occurs. The calling function (`process_document`) should catch this and raise a user-friendly `RuntimeError` indicating a missing dependency.
- Testing approach: Mock the environment so `import fitz` fails. Call `process_document` with a PDF path. Verify the appropriate `RuntimeError`.


### Edge Case: RAG Processing - File Not Found
- Identified: 2025-04-14 12:13:00
- Scenario: `process_document_for_rag` is called with a `file_path` that does not exist.
- Expected behavior: Python bridge raises `FileNotFoundError`, Node.js handler catches it and returns an appropriate error to the agent.
- Testing approach: Call `process_document_for_rag` with a non-existent path. Verify the correct error is returned.

### Edge Case: RAG Processing - Unsupported Format
- Identified: 2025-04-14 12:13:00
- Scenario: `process_document_for_rag` (or internal processing via download) is called with a file format other than EPUB or TXT (e.g., PDF, DOCX).
- Expected behavior: Python bridge raises `ValueError` indicating unsupported format, Node.js handler catches it and returns an error.
- Testing approach: Create dummy files with unsupported extensions. Call processing functions. Verify `ValueError`.

### Edge Case: RAG Processing - EPUB Parsing Error
- Identified: 2025-04-14 12:13:00
- Scenario: `_process_epub` encounters a corrupted or malformed EPUB file that `ebooklib` cannot parse.
- Expected behavior: `ebooklib` raises an error, `_process_epub` catches it (or lets it propagate), logs the error, and the calling function (`process_document` or `download_book`) handles it (e.g., returns `None` for text, includes error info).
- Testing approach: Obtain or create a corrupted EPUB file. Call `_process_epub`. Verify error handling.

### Edge Case: RAG Processing - TXT Encoding Error
- Identified: 2025-04-14 12:13:00
- Scenario: `_process_txt` encounters a TXT file that is not UTF-8 or Latin-1, or has other read errors.
- Expected behavior: `_process_txt` attempts UTF-8, then Latin-1. If both fail, it raises the underlying `Exception`, which is caught, logged, and handled by the caller.
- Testing approach: Create TXT files with unusual encodings or trigger read errors (e.g., permissions). Verify fallback and error handling.

### Edge Case: Venv Management - Python Not Found
- Identified: 2025-04-14 03:31:01
- Scenario: The `findPythonExecutable` function fails to locate a compatible Python 3 installation on the user's system.
- Expected behavior: The setup process halts, and a clear error message is displayed instructing the user to install Python 3.
- Testing approach: Mock the Python detection library/logic to return 'not found'. Verify the correct error is thrown.

### Edge Case: Venv Management - Venv Creation Failure
- Identified: 2025-04-14 03:31:01
- Scenario: The `python3 -m venv <path>` command fails (e.g., due to permissions, disk space, corrupted Python installation).
- Expected behavior: The setup process halts, and an error message indicating venv creation failure is displayed.
- Testing approach: Mock `child_process.execSync`/`exec` to throw an error during the venv creation command. Verify the correct error is propagated.

### Edge Case: Venv Management - Dependency Installation Failure
- Identified: 2025-04-14 03:31:01
- Scenario: The `<venv_pip> install zlibrary` command fails (e.g., network issues, PyPI unavailable, incompatible `zlibrary` version).
- Expected behavior: The setup process halts, and an error message indicating dependency installation failure is displayed.
- Testing approach: Mock `child_process.execSync`/`exec` to throw an error during the pip install command. Verify the correct error is propagated.

### Edge Case: Venv Management - Corrupted Config File
- Identified: 2025-04-14 03:31:01
- Scenario: The `venv_config.json` file exists but is malformed or contains an invalid/non-executable Python path.
- Expected behavior: The `ensureVenvReady` function detects the invalid config, attempts to repair the venv (re-install dependencies, re-verify Python path), and saves a new valid config. If repair fails, an error is thrown.
- Testing approach: Create mock corrupted config files. Mock `fs` reads/writes and `child_process` calls. Verify the repair logic is triggered and succeeds/fails correctly.


## Pseudocode Library
### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `_save_processed_text` (New)
- Created: 2025-04-23 23:37:09
- Updated: 2025-04-23 23:37:09
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
#### TDD Anchors:
- Test successful save returns correct `Path` object.
- Test directory creation (`./processed_rag_output/`).
- Test correct filename generation (`<original>.processed.<format>`).
- Test raises `FileSaveError` on OS errors (mock `open`/`write` to fail).
- Test raises `ValueError` if `text_content` is None.

### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `process_document` (Updated for File Output)
- Created: 2025-04-14 14:08:30
- Updated: 2025-04-23 23:37:09
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
#### TDD Anchors:
- Test routes `.pdf` extension to `_process_pdf`.
- Test calls `_save_processed_text` when helper returns non-empty text.
- Test returns `{"processed_file_path": path}` on successful processing and saving.
- Test does *not* call `_save_processed_text` if helper returns empty string.
- Test returns `{"processed_file_path": None}` if helper returns empty string.
- Test propagates errors from helpers (e.g., `ValueError`, `RuntimeError`, `ImportError`).
- Test propagates `FileSaveError` from `_save_processed_text`.
- Test raises `FileNotFoundError` if input path doesn't exist.

### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `download_book` (Updated for File Output)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-23 23:37:09
```python
# File: lib/python_bridge.py (Updated Core Function)
# Dependencies: zlibrary, os, logging, pathlib
# Assumes process_document is defined and handles saving

import os
import logging
from pathlib import Path
from zlibrary import ZLibrary

def download_book(book_id, format=None, output_dir=None, process_for_rag=False, processed_output_format="txt"):
    """
    Downloads a book and optionally processes it, saving the processed text.
    Returns a dictionary containing file_path and optionally processed_file_path.
    """
    zl = ZLibrary() # Adjust initialization as needed
    logging.info(f"Attempting download for book_id: {book_id}, format: {format}")

    # Perform download (assuming library handles naming)
    download_result_path_str = zl.download_book(
        book_id=book_id,
        # format=format, # Pass if library supports
        output_dir=output_dir,
    )

    if not download_result_path_str or not os.path.exists(download_result_path_str):
        raise RuntimeError(f"Download failed or file not found for book_id: {book_id}")

    download_result_path = Path(download_result_path_str)
    logging.info(f"Book downloaded successfully to: {download_result_path}")

    result = {"file_path": str(download_result_path)}
    processed_path_str = None

    if process_for_rag:
        logging.info(f"Processing downloaded file for RAG: {download_result_path}")
        try:
            # Call the updated process_document which saves the file
            process_result = process_document(str(download_result_path), processed_output_format)
            processed_path_str = process_result.get("processed_file_path") # Get the path string
            if processed_path_str:
                 result["processed_file_path"] = processed_path_str
            else:
                 logging.warning(f"Processing requested for {download_result_path}, but no output file was saved.")
                 result["processed_file_path"] = None # Explicitly set to None

        except Exception as e:
            logging.error(f"Failed to process document after download for {download_result_path}: {e}")
            result["processed_file_path"] = None # Indicate processing failure

    return result
```
#### TDD Anchors:
- Mock `zlibrary.download_book`.
- Test `process_for_rag=False` -> Returns only `file_path`.
- Test `process_for_rag=True` -> Calls `process_document` internally.
- Test `process_for_rag=True` (Successful Processing) -> Returns `file_path` and `processed_file_path` (string path).
- Test `process_for_rag=True` (Processing Fails/No Text) -> Returns `file_path` and `processed_file_path: None`.
- Test download failure handling.

### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `_process_pdf` (Updated Return)
- Created: 2025-04-14 14:08:30
- Updated: 2025-04-23 23:37:09
```python
# File: lib/python_bridge.py (Helper Function - Updated Return Logic)
# ... (imports and function signature as before) ...
def _process_pdf(file_path: Path) -> str:
    # ... (error checking, opening doc, encryption check as before) ...
    try:
        # ... (page iteration and text extraction as before) ...
        full_text = "\n\n".join(all_text).strip()

        if not full_text:
            logging.warning(f"No extractable text found in PDF (possibly image-based): {file_path}")
            return "" # RETURN EMPTY STRING

        logging.info(f"Finished PDF: {file_path}. Extracted length: {len(full_text)}")
        return full_text
    # ... (exception handling as before) ...
    finally:
        # ... (doc.close() as before) ...
```
#### TDD Anchors:
- Test returns empty string (`""`) for image-based PDF.
- Test returns empty string (`""`) for empty PDF.
- (Other anchors remain the same)

### Pseudocode: Tool Schemas (Zod) - Updated for File Output
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-23 23:37:09
```typescript
// File: src/lib/schemas.ts (or inline in index.ts)
import { z } from 'zod';

// Updated Input for download_book_to_file
export const DownloadBookToFileInputSchema = z.object({
  id: z.string().describe("The Z-Library book ID"),
  format: z.string().optional().describe("File format (e.g., \"pdf\", \"epub\")"),
  outputDir: z.string().optional().default("./downloads").describe("Directory to save the original file (default: './downloads')"),
  process_for_rag: z.boolean().optional().default(false).describe("If true, process content for RAG and save to processed output file"),
  processed_output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')")
});

// Updated Output for download_book_to_file
export const DownloadBookToFileOutputSchema = z.object({
    file_path: z.string().describe("The absolute path to the original downloaded file"),
    processed_file_path: z.string().optional().describe("The absolute path to the file containing processed text (only if process_for_rag was true)")
});

// Updated Input for process_document_for_rag
export const ProcessDocumentForRagInputSchema = z.object({
  file_path: z.string().describe("The absolute path to the document file to process"),
  output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')")
});

// Updated Output for process_document_for_rag
export const ProcessDocumentForRagOutputSchema = z.object({
  processed_file_path: z.string().describe("The absolute path to the file containing extracted and processed plain text content")
});
```
#### TDD Anchors:
- Verify `DownloadBookToFileInputSchema` accepts `process_for_rag`, `processed_output_format`.
- Verify `DownloadBookToFileOutputSchema` includes optional `processed_file_path`.
- Verify `ProcessDocumentForRagInputSchema` requires `file_path`, accepts optional `output_format`.
- Verify `ProcessDocumentForRagOutputSchema` requires `processed_file_path`.

### Pseudocode: Tool Registration (`index.ts` Snippet) - Updated for File Output
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-23 23:37:09
```typescript
// File: src/index.ts (Conceptual Snippet)
// ... imports (Server, StdioServerTransport, z, zlibraryApi, schemas) ...

import {
  DownloadBookToFileInputSchema,
  DownloadBookToFileOutputSchema,
  ProcessDocumentForRagInputSchema,
  ProcessDocumentForRagOutputSchema,
  // ... other schemas
} from './lib/schemas';
import * as zlibraryApi from './lib/zlibrary-api';

const server = new Server({
  // ... other server options
  tools: {
    list: async () => {
      return [
        // ... other tools
        {
          name: 'download_book_to_file',
          description: 'Downloads a book file from Z-Library and optionally processes its content for RAG, saving the result to a separate file.',
          inputSchema: DownloadBookToFileInputSchema,
          outputSchema: DownloadBookToFileOutputSchema,
        },
        {
          name: 'process_document_for_rag',
          description: 'Processes an existing local document file (EPUB, TXT, PDF) to extract plain text content for RAG, saving the result to a file.',
          inputSchema: ProcessDocumentForRagInputSchema,
          outputSchema: ProcessDocumentForRagOutputSchema,
        },
      ];
    },
    call: async (request) => {
      // ... generic validation ...
      if (request.name === 'download_book_to_file') {
        const validatedArgs = DownloadBookToFileInputSchema.parse(request.arguments);
        const result = await zlibraryApi.downloadBookToFile(validatedArgs);
        return result;
      }
      if (request.name === 'process_document_for_rag') {
        const validatedArgs = ProcessDocumentForRagInputSchema.parse(request.arguments);
        const result = await zlibraryApi.processDocumentForRag(validatedArgs);
        return result;
      }
      // ... handle other tools
      throw new Error(`Tool not found: ${request.name}`);
    },
  },
});
// ... transport setup and server.connect() ...
```
#### TDD Anchors:
- Test `tools/list` includes updated descriptions/schemas.
- Test `tools/call` routes correctly.
- Test input validation using updated Zod schemas.

### Pseudocode: Node.js Handlers (`lib/zlibrary-api.ts`) - Updated for File Output
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-23 23:37:09
```pseudocode
// File: src/lib/zlibrary-api.ts
// Dependencies: ./python-bridge, path

IMPORT callPythonFunction FROM './python-bridge'
IMPORT path

ASYNC FUNCTION downloadBookToFile(args):
  // args = { id, format?, outputDir?, process_for_rag?, processed_output_format? }
  LOG `Downloading book ${args.id}, process_for_rag=${args.process_for_rag}`
  pythonArgs = {
    book_id: args.id,
    format: args.format,
    output_dir: args.outputDir,
    process_for_rag: args.process_for_rag,
    processed_output_format: args.processed_output_format
  }
  TRY
    resultJson = AWAIT callPythonFunction('download_book', pythonArgs)
    IF NOT resultJson OR NOT resultJson.file_path THEN
      THROW Error("Invalid response from Python: Missing original file_path.")
    ENDIF
    IF args.process_for_rag AND resultJson.processed_file_path IS UNDEFINED THEN // Check if key exists
       THROW Error("Invalid response from Python: Processing requested but processed_file_path missing or null.")
    ENDIF
    response = { file_path: resultJson.file_path }
    IF args.process_for_rag THEN // Always include the key if processing was requested
      response.processed_file_path = resultJson.processed_file_path // Could be null if processing yielded no text
    ENDIF
    RETURN response
  CATCH error
    LOG `Error in downloadBookToFile: ${error.message}`
    THROW Error(`Failed to download/process book ${args.id}: ${error.message}`)
  ENDTRY
END FUNCTION

ASYNC FUNCTION processDocumentForRag(args):
  // args = { file_path, output_format? }
  LOG `Processing document for RAG: ${args.file_path}`
  absolutePath = path.resolve(args.file_path)
  pythonArgs = {
    file_path: absolutePath,
    output_format: args.output_format
  }
  TRY
    resultJson = AWAIT callPythonFunction('process_document', pythonArgs)
    IF NOT resultJson OR resultJson.processed_file_path IS UNDEFINED THEN // Check if key exists
      THROW Error("Invalid response from Python: Missing processed_file_path.")
    ENDIF
    RETURN { processed_file_path: resultJson.processed_file_path } // Could be null
  CATCH error
    LOG `Error in processDocumentForRag: ${error.message}`
    THROW Error(`Failed to process document ${args.file_path}: ${error.message}`)
  ENDTRY
END FUNCTION

EXPORT { downloadBookToFile, processDocumentForRag /*, ... */ }
```
#### TDD Anchors:
- `downloadBookToFile`: Mock `callPythonFunction`. Test `process_for_rag` flag passed. Test handling of responses with/without `processed_file_path` (including null). Test error handling (missing paths).
- `processDocumentForRag`: Mock `callPythonFunction`. Test `file_path` and `output_format` passed. Test handling of successful response (`processed_file_path`, including null) and error response.


<!-- Append new pseudocode blocks using the format below -->
### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `_internal_search`
- Created: 2025-04-16 18:14:41
- Updated: 2025-04-16 18:14:41
```python
# File: lib/python_bridge.py (Addition)
# Dependencies: httpx, bs4, logging, asyncio, urllib.parse

IMPORT httpx
IMPORT logging
IMPORT asyncio
FROM bs4 IMPORT BeautifulSoup
FROM urllib.parse IMPORT urljoin

# Assume logging is configured
# Assume InternalFetchError, InternalParsingError are defined

ASYNC FUNCTION _internal_search(query: str, domain: str, count: int = 1) -> list[dict]:
    """Performs an internal search and extracts book page URLs."""
    search_url = f"https://{domain}/s/{query}" # Example search URL pattern
    headers = { 'User-Agent': 'Mozilla/5.0 ...' } # Standard User-Agent
    timeout_seconds = 20

    LOG info f"Performing internal search for '{query}' at {search_url}"

    TRY
        ASYNC WITH httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = AWAIT client.get(search_url, headers=headers)

            IF response.status_code != 200 THEN
                LOG error f"Internal search failed for '{query}'. Status: {response.status_code}"
                RAISE InternalFetchError(f"Search request failed with status {response.status_code}")
            ENDIF

            # Parse HTML
            TRY
                soup = BeautifulSoup(response.text, 'lxml')
                results = []
                # Selector based on prompt - needs verification
                book_items = soup.select('#searchResultBox .book-item')

                IF NOT book_items THEN
                    LOG warning f"No book items found in search results for '{query}' using selector '#searchResultBox .book-item'."
                    RETURN [] # No results found is not necessarily an error here
                ENDIF

                FOR item IN book_items[:count]:
                    link_element = item.select_one('a[href]') # Find the main link
                    IF link_element AND link_element.has_attr('href'):
                        relative_url = link_element['href']
                        # Ensure URL is absolute
                        absolute_url = urljoin(str(response.url), relative_url)
                        results.append({'book_page_url': absolute_url})
                        LOG info f"Found potential book URL: {absolute_url}"
                    ELSE
                        LOG warning f"Could not find valid link element in search result item for '{query}'."
                    ENDIF
                ENDFOR

                RETURN results

            EXCEPT Exception as parse_exc:
                LOG exception f"Error parsing search results page for '{query}': {parse_exc}"
                RAISE InternalParsingError(f"Failed to parse search results page: {parse_exc}")

    EXCEPT httpx.RequestError as req_err:
        LOG error f"Network error during internal search for '{query}': {req_err}"
        RAISE InternalFetchError(f"Network error during search: {req_err}")
    EXCEPT Exception as e:
         LOG exception f"Unexpected error during internal search for '{query}': {e}"
         RAISE InternalFetchError(f"An unexpected error occurred during search: {e}") # Or re-raise

END FUNCTION
```
#### TDD Anchors:
- Test successful search returns list with `{'book_page_url': '...'}`.
- Test search with no results returns empty list `[]`.
- Test search page parsing error raises `InternalParsingError`.
- Test network error (timeout, connection refused) raises `InternalFetchError`.
- Test non-200 HTTP status code raises `InternalFetchError`.
- Test `urljoin` correctly makes relative URLs absolute.

### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `_internal_get_book_details_by_id` (Search-First)
- Created: 2025-04-16 18:14:41
- Updated: 2025-04-16 18:14:41
```python
# File: lib/python_bridge.py (Addition/Modification)
# Dependencies: httpx, bs4, logging, asyncio, urllib.parse
# Assumes _internal_search and custom exceptions are defined

ASYNC FUNCTION _internal_get_book_details_by_id(book_id: str, domain: str) -> dict:
    """Fetches book details using the Search-First strategy."""
    LOG info f"Attempting Search-First internal lookup for book ID {book_id}"

    # 1. Search for the book ID to find the correct URL
    TRY
        search_results = AWAIT _internal_search(query=str(book_id), domain=domain, count=1)
    EXCEPT (InternalFetchError, InternalParsingError) as search_err:
        LOG error f"Internal search step failed for book ID {book_id}: {search_err}"
        # Propagate or wrap the error; using InternalFetchError as a general category
        RAISE InternalFetchError(f"Search step failed for ID {book_id}: {search_err}")
    EXCEPT Exception as e:
        LOG exception f"Unexpected error during search step for ID {book_id}: {e}"
        RAISE InternalFetchError(f"Unexpected error during search step for ID {book_id}: {e}")


    IF NOT search_results:
        LOG warning f"Internal search for book ID {book_id} returned no results."
        RAISE InternalBookNotFoundError(f"Book ID {book_id} not found via internal search.")
    ENDIF

    book_page_url = search_results[0].get('book_page_url')
    IF NOT book_page_url:
        LOG error f"Internal search result for book ID {book_id} missing 'book_page_url'."
        RAISE InternalParsingError("Search result parsing failed: book_page_url missing.")
    ENDIF

    LOG info f"Found book page URL via search: {book_page_url}"

    # 2. Fetch the book detail page
    headers = { 'User-Agent': 'Mozilla/5.0 ...' }
    timeout_seconds = 15

    TRY
        ASYNC WITH httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = AWAIT client.get(book_page_url, headers=headers)

            IF response.status_code == 404 THEN
                 LOG warning f"Book page fetch for ID {book_id} resulted in 404 at {book_page_url}."
                 # This might indicate the search result was stale or incorrect
                 RAISE InternalBookNotFoundError(f"Book page not found (404) at {book_page_url} for ID {book_id}.")
            ENDIF

            response.raise_for_status() # Raise for other non-200 errors

            # 3. Parse the book detail page
            TRY
                soup = BeautifulSoup(response.text, 'lxml')
                details = {}

                # --- Placeholder Selectors (MUST BE VERIFIED/REFINED) ---
                title_element = soup.select_one('h1[itemprop="name"]') # Example
                details['title'] = title_element.text.strip() IF title_element ELSE None

                author_element = soup.select_one('a[itemprop="author"]') # Example
                details['author'] = author_element.text.strip() IF author_element ELSE None

                year_element = soup.select_one('.property-year .property_value') # Example
                details['year'] = year_element.text.strip() IF year_element ELSE None

                publisher_element = soup.select_one('.property-publisher .property_value') # Example
                details['publisher'] = publisher_element.text.strip() IF publisher_element ELSE None

                description_element = soup.select_one('.book-description') # Example
                details['description'] = description_element.text.strip() IF description_element ELSE None

                # Download URL(s) - This often requires specific logic
                download_link_element = soup.select_one('a.btn-primary[href*="/download"]') # Example
                download_url = None
                IF download_link_element AND download_link_element.has_attr('href'):
                    download_url = urljoin(str(response.url), download_link_element['href'])
                details['download_url'] = download_url
                # --- End Placeholder Selectors ---

                # Check for essential missing data
                IF details['title'] IS None OR details['download_url'] IS None THEN
                    LOG error f"Parsing failed for book ID {book_id}: Essential details missing (title or download_url)."
                    RAISE InternalParsingError(f"Failed to parse essential details (title/download_url) for book ID {book_id}.")
                ENDIF

                LOG info f"Successfully parsed details for book ID {book_id} from {book_page_url}"
                RETURN details

            EXCEPT Exception as parse_exc:
                LOG exception f"Error parsing book detail page for ID {book_id} at {book_page_url}: {parse_exc}"
                RAISE InternalParsingError(f"Failed to parse book detail page: {parse_exc}")

    EXCEPT httpx.RequestError as req_err:
        LOG error f"Network error fetching book page for ID {book_id} at {book_page_url}: {req_err}"
        RAISE InternalFetchError(f"Network error fetching book page: {req_err}")
    EXCEPT httpx.HTTPStatusError as status_err:
        LOG error f"HTTP status error {status_err.response.status_code} fetching book page for ID {book_id} at {book_page_url}: {status_err}"
        RAISE InternalFetchError(f"HTTP error {status_err.response.status_code} fetching book page.")
    # InternalBookNotFoundError, InternalParsingError raised directly from parsing block
    EXCEPT Exception as e:
         LOG exception f"Unexpected error fetching/parsing book page for ID {book_id}: {e}"
         RAISE InternalFetchError(f"An unexpected error occurred fetching/parsing book page: {e}") # Or re-raise

END FUNCTION
```
#### TDD Anchors:
- Test successful flow: search -> fetch -> parse -> returns details dict.
- Test `_internal_search` fails (raises `InternalFetchError`) -> raises `InternalFetchError`.
- Test `_internal_search` returns empty list -> raises `InternalBookNotFoundError`.
- Test `_internal_search` result missing `book_page_url` -> raises `InternalParsingError`.
- Test book page fetch fails (network error) -> raises `InternalFetchError`.
- Test book page fetch returns 404 -> raises `InternalBookNotFoundError`.
- Test book page fetch returns other non-200 status -> raises `InternalFetchError`.
- Test book page parsing fails (bad HTML) -> raises `InternalParsingError`.
- Test book page parsing succeeds but essential data (title, download_url) is missing -> raises `InternalParsingError`.

### Pseudocode: Python Bridge (`lib/python-bridge.py`) - Caller Modifications (Search-First)
- Created: 2025-04-16 18:14:41
- Updated: 2025-04-16 18:14:41
```python
# File: lib/python-bridge.py (Modification in __main__ block)

# Example for 'get_book_details' action handler
elif cli_args.function_name == 'get_book_details':
    book_id = args_dict.get('book_id')
    domain = args_dict.get('domain', 'z-library.sk') # Or get from config/args
    IF NOT book_id: RAISE ValueError("Missing 'book_id'")

    TRY
        # Call the new async function using asyncio.run()
        details = asyncio.run(_internal_get_book_details_by_id(book_id, domain))
        response = details # Format if needed

    EXCEPT InternalBookNotFoundError as e:
        # Translate to ValueError for Node.js
        LOG warning f"BookNotFound for ID {book_id}: {e}"
        RAISE ValueError(f"Book ID {book_id} not found.")
    EXCEPT (InternalFetchError, InternalParsingError) as e:
        # Translate fetch/parse errors to RuntimeError
        LOG error f"Fetch/Parse error for ID {book_id}: {e}"
        RAISE RuntimeError(f"Failed to fetch or parse details for book ID {book_id}.")
    EXCEPT Exception as e:
         # Catch any other unexpected errors from the async function or asyncio.run
         LOG exception f"Unexpected error processing book ID {book_id}"
         RAISE RuntimeError(f"An unexpected error occurred processing book ID {book_id}.")

# Similar logic for 'get_download_info', potentially extracting just 'download_url' from details dict
elif cli_args.function_name == 'get_download_info':
     # ... get book_id, domain ...
     TRY
         details = asyncio.run(_internal_get_book_details_by_id(book_id, domain))
         IF details.get('download_url') IS None:
             RAISE InternalParsingError("Download URL missing from parsed details.") # Caught below
         response = {"download_url": details['download_url']}
     EXCEPT InternalBookNotFoundError as e:
         RAISE ValueError(f"Book ID {book_id} not found.")
     EXCEPT (InternalFetchError, InternalParsingError) as e:
         RAISE RuntimeError(f"Failed to get download info for book ID {book_id}.")
     EXCEPT Exception as e:
         RAISE RuntimeError(f"An unexpected error occurred getting download info for book ID {book_id}.")

# ... rest of main block ...
# print(json.dumps(response))
```
#### TDD Anchors:
- Test `get_book_details` handler calls `asyncio.run(_internal_get_book_details_by_id)`.
- Test `get_book_details` handler translates `InternalBookNotFoundError` to `ValueError`.
- Test `get_book_details` handler translates `InternalFetchError` to `RuntimeError`.
- Test `get_book_details` handler translates `InternalParsingError` to `RuntimeError`.
- Test `get_download_info` handler calls `asyncio.run(_internal_get_book_details_by_id)`.
- Test `get_download_info` handler translates `InternalBookNotFoundError` to `ValueError`.
- Test `get_download_info` handler translates `InternalFetchError`/`InternalParsingError` to `RuntimeError`.
- Test `get_download_info` handler raises `RuntimeError` if `download_url` is missing after successful parse.



### Pseudocode: Python Bridge (`lib/python-bridge.py`) - `_internal_get_book_details_by_id`
- Created: 2025-04-16 08:12:25
- Updated: 2025-04-16 08:12:25
```python
# File: lib/python_bridge.py (Addition)
# Dependencies: httpx, bs4, logging, asyncio

import httpx
from bs4 import BeautifulSoup
import logging
import asyncio

# Assume logging is configured elsewhere

class InternalBookNotFoundError(Exception):
    """Custom exception for when a book ID lookup results in a 404."""
    pass

class InternalParsingError(Exception):
    """Custom exception for errors during HTML parsing of book details."""
    pass

async def _internal_get_book_details_by_id(book_id: str, domain: str) -> dict:
    """
    Attempts to fetch book details by directly accessing https://<domain>/book/<book_id>.
    Primarily expects a 404, raising InternalBookNotFoundError.
    If a 200 is received, attempts to parse the page.
    """
    target_url = f"https://{domain}/book/{book_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' # Example User-Agent
    }
    timeout_seconds = 15 # Configurable timeout

    logging.info(f"Attempting internal lookup for book ID {book_id} at {target_url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(target_url, headers=headers)

            # --- Status Code Handling ---
            if response.status_code == 404:
                logging.warning(f"Internal lookup for book ID {book_id} resulted in 404 (Not Found).")
                raise InternalBookNotFoundError(f"Book ID {book_id} not found via internal lookup (404).")

            # Raise error for other non-200 statuses
            response.raise_for_status() # Raises httpx.HTTPStatusError for 4xx/5xx other than 404

            # --- 200 OK Parsing (Unexpected Case) ---
            logging.warning(f"Received unexpected 200 OK for internal lookup of book ID {book_id}. Attempting to parse.")
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                details = {}

                # Example Selectors (These MUST be verified and adjusted based on actual page structure)
                title_element = soup.select_one('h1[itemprop="name"]')
                details['title'] = title_element.text.strip() if title_element else None

                author_element = soup.select_one('a[itemprop="author"]') # Adjust selector
                details['author'] = author_element.text.strip() if author_element else None

                # Add selectors for other fields: year, publisher, description, etc.
                # Example:
                # year_element = soup.select_one('.book-details .property-year .property_value')
                # details['year'] = year_element.text.strip() if year_element else None

                # Example Download URL Selector (Verify this)
                download_link_element = soup.select_one('a.btn-primary[href*="/download"]') # Adjust selector
                details['download_url'] = download_link_element['href'] if download_link_element and download_link_element.has_attr('href') else None
                # Potentially need to make URL absolute: urljoin(response.url, details['download_url'])

                if not details.get('title'): # Check if essential data is missing
                     logging.error(f"Parsing failed for book ID {book_id}: Essential data (e.g., title) missing.")
                     raise InternalParsingError(f"Failed to parse essential details for book ID {book_id} from 200 OK page.")

                logging.info(f"Successfully parsed details for book ID {book_id} from unexpected 200 OK.")
                return details

            except Exception as parse_exc:
                logging.exception(f"Error parsing 200 OK page for book ID {book_id}: {parse_exc}")
                raise InternalParsingError(f"Failed to parse page content for book ID {book_id}: {parse_exc}") from parse_exc

    except httpx.RequestError as req_err:
        # Handles connection errors, timeouts, etc.
        logging.error(f"HTTP request error during internal lookup for book ID {book_id}: {req_err}")
        raise RuntimeError(f"Network error during internal lookup for book ID {book_id}: {req_err}") from req_err
    except httpx.HTTPStatusError as status_err:
        # Handles non-200/404 errors raised by response.raise_for_status()
        logging.error(f"Unexpected HTTP status {status_err.response.status_code} during internal lookup for book ID {book_id}: {status_err}")
        raise RuntimeError(f"Unexpected HTTP status {status_err.response.status_code} for book ID {book_id}.") from status_err
    # InternalBookNotFoundError and InternalParsingError are raised directly
    except Exception as e:
         # Catch any other unexpected errors
         logging.exception(f"Unexpected error during internal lookup for book ID {book_id}: {e}")
         raise RuntimeError(f"An unexpected error occurred during internal lookup for book ID {book_id}: {e}") from e
```
#### TDD Anchors:
- Test case 1: 404 Not Found raises InternalBookNotFoundError.
- Test case 2: Other HTTP Error raises httpx.HTTPStatusError.
- Test case 3: Network Error raises httpx.RequestError.
- Test case 4: Successful 200 OK (Mock HTML) returns details dict.
- Test case 5: Parsing Error (200 OK) raises InternalParsingError.
- Test case 6: Missing Elements (200 OK) handled gracefully / raises InternalParsingError.

### Pseudocode: Python Bridge (`lib/python-bridge.py`) - Caller Modifications
- Created: 2025-04-16 08:12:25
- Updated: 2025-04-16 08:12:25
```python
# File: lib/python-bridge.py (Modification)
# Dependencies: asyncio, logging
import asyncio
import logging
# Assume _internal_get_book_details_by_id, InternalBookNotFoundError, InternalParsingError are defined above
# Assume httpx is imported

# Inside if __name__ == "__main__": block

# Example modification for a function handling 'get_book_details' action
elif cli_args.function_name == 'get_book_details': # Assuming a unified function now
    book_id = args_dict.get('book_id')
    domain = args_dict.get('domain', 'z-library.sk') # Get domain from args or use default
    if not book_id: raise ValueError("Missing 'book_id'")

    try:
        # Use asyncio.run() to call the async function from sync context
        details = asyncio.run(_internal_get_book_details_by_id(book_id, domain))
        # Format 'details' dictionary as needed for the Node.js response
        response = details # Or transform structure if necessary

    except InternalBookNotFoundError:
        # Translate internal error to ValueError for Node.js
        raise ValueError(f"Book ID {book_id} not found.")
    except (InternalParsingError, httpx.RequestError, RuntimeError) as e:
        # Translate other internal/HTTP errors to RuntimeError
        logging.error(f"Failed to get details for book ID {book_id}: {e}")
        raise RuntimeError(f"Failed to fetch or parse book details for ID {book_id}.")
    except Exception as e:
         logging.exception(f"Unexpected error in get_book_details handler for ID {book_id}")
         raise RuntimeError(f"An unexpected error occurred processing book ID {book_id}.")

# Similar logic needs to be applied if get_download_info is a separate entry point.
# It might call the same _internal_get_book_details_by_id and extract the download_url.
elif cli_args.function_name == 'get_download_info':
     book_id = args_dict.get('book_id')
     domain = args_dict.get('domain', 'z-library.sk')
     if not book_id: raise ValueError("Missing 'book_id'")
     try:
         details = asyncio.run(_internal_get_book_details_by_id(book_id, domain))
         if not details.get('download_url'):
              raise InternalParsingError("Download URL not found in parsed details.")
         response = {"download_url": details['download_url']} # Format as needed

     except InternalBookNotFoundError:
         raise ValueError(f"Book ID {book_id} not found.")
     except (InternalParsingError, httpx.RequestError, RuntimeError) as e:
         logging.error(f"Failed to get download info for book ID {book_id}: {e}")
         raise RuntimeError(f"Failed to fetch or parse download info for ID {book_id}.")
     except Exception as e:
         logging.exception(f"Unexpected error in get_download_info handler for ID {book_id}")
         raise RuntimeError(f"An unexpected error occurred processing book ID {book_id}.")

# Ensure the main block correctly handles the response variable
# print(json.dumps(response))
```
#### TDD Anchors:
- Test case 1: Correctly calls asyncio.run(_internal_get_book_details_by_id).
- Test case 2: Translates InternalBookNotFoundError to ValueError.
- Test case 3: Translates InternalParsingError/httpx.RequestError to RuntimeError.
- Test case 4: Formats return data correctly for Node.js.


### Pseudocode: Python Bridge (`lib/python-bridge.py`) - `_process_pdf`
- Created: 2025-04-14 14:08:30
- Updated: 2025-04-14 14:08:30
```python
# File: lib/python-bridge.py (Addition)
# Dependencies: fitz, os, logging

import fitz  # PyMuPDF
import os
import logging

# Assume logging is configured elsewhere

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
        ImportError: If fitz (PyMuPDF) is not installed (implicitly raised on import).
    """
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
                # Decide whether to continue or raise based on severity

        # Combine extracted text
        full_text = "\n\n".join(all_text).strip()

        # Check if any text was extracted
        if not full_text:
            logging.warning(f"No extractable text found in PDF (possibly image-based): {file_path}")
            raise ValueError("PDF contains no extractable text layer (possibly image-based)")

        logging.info(f"Finished PDF: {file_path}. Extracted length: {len(full_text)}")
        return full_text

    except fitz.fitz.FitzError as fitz_error: # Catch specific fitz errors if needed
        logging.error(f"PyMuPDF error processing {file_path}: {fitz_error}")
        raise RuntimeError(f"Error opening or processing PDF: {file_path} - {fitz_error}")
    except Exception as e:
        # Catch other potential errors during opening or processing
        logging.error(f"Unexpected error processing PDF {file_path}: {e}")
        # Re-raise specific errors if needed (like ValueError from checks)
        if isinstance(e, (ValueError, FileNotFoundError)):
             raise e
        raise RuntimeError(f"Error opening or processing PDF: {file_path} - {e}")
    finally:
        # Ensure the document is closed
        if doc:
            try:
                doc.close()
            except Exception as close_error:
                logging.error(f"Error closing PDF document {file_path}: {close_error}")

```
#### TDD Anchors:
- Test case 1: Successful extraction from standard PDF.
- Test case 2: Raises `ValueError` for encrypted PDF.
- Test case 3: Raises `RuntimeError` for corrupted PDF.
- Test case 4: Raises `ValueError` for image-based PDF.
- Test case 5: Raises `ValueError` for empty PDF.
- Test case 6: Raises `FileNotFoundError` for non-existent path.
- Test case 7: Handles page processing errors gracefully (logs warning).
- Test case 8: Ensures `doc.close()` is called in `finally` block.

### Pseudocode: Python Bridge (`lib/python-bridge.py`) - `process_document` Modification
- Created: 2025-04-14 14:08:30
- Updated: 2025-04-14 14:08:30
```python
# File: lib/python-bridge.py (Modification)

# Update SUPPORTED_FORMATS if it exists
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf'] # Added .pdf

# Inside the process_document function:
def process_document(file_path_str: str) -> str:
    """Processes a document file (EPUB, TXT, PDF) to extract text."""
    if not os.path.exists(file_path_str):
        raise FileNotFoundError(f"File not found: {file_path_str}")

    _, ext = os.path.splitext(file_path_str)
    ext = ext.lower()
    processed_text = None

    try:
        if ext == '.epub':
            # Ensure EBOOKLIB_AVAILABLE check happens here or in _process_epub
            processed_text = _process_epub(file_path_str)
        elif ext == '.txt':
            processed_text = _process_txt(file_path_str)
        elif ext == '.pdf': # <-- New condition
            # Ensure fitz import check happens here or in _process_pdf
            # Implicitly handles ImportError if fitz not installed
            processed_text = _process_pdf(file_path_str) # <-- Call new function
        else:
            # Use the updated SUPPORTED_FORMATS list in the error message
            raise ValueError(f"Unsupported file format: {ext}. Supported: {SUPPORTED_FORMATS}")

        if processed_text is None:
             # This case might occur if a processing function returns None instead of raising error
             raise RuntimeError(f"Processing function returned None for {file_path_str}")

        return processed_text

    except ImportError as imp_err:
         # Catch import errors for any format-specific library
         logging.error(f"Missing dependency for processing {ext} file {file_path_str}: {imp_err}")
         raise RuntimeError(f"Missing required library to process {ext} files. Please check installation.") from imp_err
    # Keep existing specific error handling (FileNotFoundError, ValueError)
    # Add or modify general exception handling if needed
    except Exception as e:
        logging.exception(f"Failed to process document {file_path_str}")
        # Re-raise specific errors if they weren't caught earlier
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise e
        # Wrap unexpected errors
        raise RuntimeError(f"An unexpected error occurred during document processing: {e}") from e

```
#### TDD Anchors:
- Test case 1: Routes `.pdf` extension to `_process_pdf`.
- Test case 2: Routes `.epub`, `.txt` correctly.
- Test case 3: Raises `ValueError` for unsupported extensions.
- Test case 4: Propagates errors raised by `_process_pdf` (e.g., `ValueError`, `RuntimeError`).
- Test case 5: Catches `ImportError` (e.g., if `fitz` is missing) and raises `RuntimeError`.
- Test case 6: Raises `FileNotFoundError` if input path doesn't exist.


### Pseudocode: Tool Schemas (Zod)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-14 12:13:00
```typescript
// File: lib/schemas.js (or inline in index.js)
import { z } from 'zod';

// Updated Input for download_book_to_file
export const DownloadBookToFileInputSchema = z.object({
  bookId: z.string().describe("The Z-Library book ID"),
  outputDir: z.string().optional().describe("Directory to save the file (relative to project root or absolute)"),
  outputFilename: z.string().optional().describe("Desired filename (extension will be added automatically)"),
  process_for_rag: z.boolean().optional().default(false).describe("If true, process content for RAG and return text") // New field
});

// Updated Output for download_book_to_file
export const DownloadBookToFileOutputSchema = z.object({
    file_path: z.string().describe("The absolute path to the downloaded file"),
    processed_text: z.string().optional().describe("The extracted plain text content (only if process_for_rag was true)") // New optional field
});

// New Input for process_document_for_rag
export const ProcessDocumentForRagInputSchema = z.object({
  file_path: z.string().describe("The absolute path to the document file to process")
});

// New Output for process_document_for_rag
export const ProcessDocumentForRagOutputSchema = z.object({
  processed_text: z.string().describe("The extracted plain text content")
});
```
#### TDD Anchors:
- Test case 1: `DownloadBookToFileInputSchema` validation (accepts/rejects process_for_rag).
- Test case 2: `DownloadBookToFileOutputSchema` validation (accepts/rejects optional processed_text).
- Test case 3: `ProcessDocumentForRagInputSchema` validation (requires file_path).
- Test case 4: `ProcessDocumentForRagOutputSchema` validation (requires processed_text).

### Pseudocode: Tool Registration (`index.js` Snippet)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-14 12:13:00
```javascript
// File: index.js (Conceptual Snippet)
// ... imports (Server, StdioServerTransport, z, zlibraryApi, schemas) ...

// Assume schemas are defined or imported
const {
  DownloadBookToFileInputSchema,
  DownloadBookToFileOutputSchema,
  ProcessDocumentForRagInputSchema,
  ProcessDocumentForRagOutputSchema
} = require('./lib/schemas'); // Example path

const server = new Server({
  // ... other server options
  tools: {
    list: async () => {
      return [
        // ... other tools
        {
          name: 'download_book_to_file',
          description: 'Downloads a book file from Z-Library and optionally processes its content for RAG.',
          inputSchema: DownloadBookToFileInputSchema,
          outputSchema: DownloadBookToFileOutputSchema, // Updated
        },
        {
          name: 'process_document_for_rag', // New
          description: 'Processes an existing local document file (EPUB, TXT) to extract plain text content for RAG.',
          inputSchema: ProcessDocumentForRagInputSchema,
          outputSchema: ProcessDocumentForRagOutputSchema,
        },
      ];
    },
    call: async (request) => {
      // ... generic validation ...
      if (request.tool_name === 'download_book_to_file') {
        const validatedArgs = DownloadBookToFileInputSchema.parse(request.arguments);
        const result = await zlibraryApi.downloadBookToFile(validatedArgs);
        // DownloadBookToFileOutputSchema.parse(result); // Optional output validation
        return result;
      }
      if (request.tool_name === 'process_document_for_rag') { // New
        const validatedArgs = ProcessDocumentForRagInputSchema.parse(request.arguments);
        const result = await zlibraryApi.processDocumentForRag(validatedArgs);
        // ProcessDocumentForRagOutputSchema.parse(result); // Optional output validation
        return result;
      }
      throw new Error(`Tool not found: ${request.tool_name}`);
    },
  },
});
// ... transport setup and server.connect() ...
```
#### TDD Anchors:
- Test case 1: `tools/list` includes updated `download_book_to_file`.
- Test case 2: `tools/list` includes new `process_document_for_rag`.
- Test case 3: `tools/call` routes `download_book_to_file` correctly.
- Test case 4: `tools/call` routes `process_document_for_rag` correctly.
- Test case 5: `tools/call` performs input validation for both tools.

### Pseudocode: Node.js Handlers (`lib/zlibrary-api.js`)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-14 12:13:00
```pseudocode
// File: lib/zlibrary-api.js
// Dependencies: ./python-bridge, path

IMPORT callPythonFunction FROM './python-bridge'
IMPORT path

ASYNC FUNCTION downloadBookToFile(args):
  // args = { bookId, outputDir, outputFilename, process_for_rag }
  LOG `Downloading book ${args.bookId}, process_for_rag=${args.process_for_rag}`
  pythonArgs = {
    book_id: args.bookId,
    output_dir: args.outputDir,
    output_filename: args.outputFilename,
    process_for_rag: args.process_for_rag
  }
  TRY
    resultJson = AWAIT callPythonFunction('download_book', pythonArgs)
    IF NOT resultJson OR NOT resultJson.file_path THEN
      THROW Error("Invalid response from Python bridge during download.")
    ENDIF
    response = { file_path: resultJson.file_path }
    IF args.process_for_rag AND resultJson.processed_text IS NOT NULL THEN
      response.processed_text = resultJson.processed_text
    ELSE IF args.process_for_rag AND resultJson.processed_text IS NULL THEN
      LOG `Warning: process_for_rag was true but Python bridge did not return processed_text for ${resultJson.file_path}`
    ENDIF
    RETURN response
  CATCH error
    LOG `Error in downloadBookToFile: ${error.message}`
    THROW Error(`Failed to download/process book ${args.bookId}: ${error.message}`)
  ENDTRY
END FUNCTION

ASYNC FUNCTION processDocumentForRag(args):
  // args = { file_path }
  LOG `Processing document for RAG: ${args.file_path}`
  absolutePath = path.resolve(args.file_path)
  pythonArgs = { file_path: absolutePath }
  TRY
    resultJson = AWAIT callPythonFunction('process_document', pythonArgs)
    IF NOT resultJson OR resultJson.processed_text IS NULL THEN
      THROW Error("Invalid response from Python bridge during processing. Missing processed_text.")
    ENDIF
    RETURN { processed_text: resultJson.processed_text }
  CATCH error
    LOG `Error in processDocumentForRag: ${error.message}`
    THROW Error(`Failed to process document ${args.file_path}: ${error.message}`)
  ENDTRY
END FUNCTION

EXPORT { downloadBookToFile, processDocumentForRag /*, ... */ }
```
#### TDD Anchors:
- Test case 1: `downloadBookToFile` passes `process_for_rag` flag correctly.
- Test case 2: `downloadBookToFile` handles response with/without `processed_text`.
- Test case 3: `downloadBookToFile` handles Python errors.
- Test case 4: `processDocumentForRag` passes `file_path` correctly.
- Test case 5: `processDocumentForRag` handles successful response.
- Test case 6: `processDocumentForRag` handles Python errors.

### Pseudocode: Python Bridge (`lib/python-bridge.py`)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-14 12:13:00
```python
# File: lib/python-bridge.py
# Dependencies: zlibrary, ebooklib, beautifulsoup4, lxml
# Standard Libs: json, sys, os, argparse, logging
import json, sys, os, argparse, logging
from zlibrary import ZLibrary
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SUPPORTED_FORMATS = ['.epub', '.txt']

# --- Helper Functions ---
def _html_to_text(html_content):
    soup = BeautifulSoup(html_content, 'lxml') # Use lxml
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    lines = (line.strip() for line in soup.get_text().splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def _process_epub(file_path):
    if not EBOOKLIB_AVAILABLE:
        raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB: {file_path}")
    book = epub.read_epub(file_path)
    all_text = []
    items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    for item in items:
        content = item.get_content()
        if content:
            try:
                html_content = content.decode('utf-8', errors='ignore')
                text = _html_to_text(html_content)
                if text:
                    all_text.append(text)
            except Exception as e:
                logging.warning(f"Could not process item {item.get_name()} in {file_path}: {e}")
    full_text = "\n\n".join(all_text)
    logging.info(f"Finished EPUB: {file_path}. Length: {len(full_text)}")
    return full_text

def _process_txt(file_path):
    logging.info(f"Processing TXT: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logging.info(f"Finished TXT: {file_path}. Length: {len(text)}")
        return text
    except UnicodeDecodeError:
        logging.warning(f"UTF-8 failed for {file_path}. Trying 'latin-1'.")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                text = f.read()
            logging.info(f"Finished TXT (latin-1): {file_path}. Length: {len(text)}")
            return text
        except Exception as e:
            logging.error(f"Failed reading {file_path} with latin-1: {e}")
            raise
    except Exception as e:
        logging.error(f"Failed reading {file_path}: {e}")
        raise

# --- Core Functions ---
def process_document(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == '.epub':
        return _process_epub(file_path)
    elif ext == '.txt':
        return _process_txt(file_path)
    else:
        raise ValueError(f"Unsupported format: {ext}. Supported: {SUPPORTED_FORMATS}")

def download_book(book_id, output_dir=None, output_filename=None, process_for_rag=False):
    zl = ZLibrary()
    logging.info(f"Downloading book_id: {book_id}")
    download_result_path = zl.download_book(
        book_id=book_id,
        output_dir=output_dir,
        output_filename=output_filename
    )
    if not download_result_path or not os.path.exists(download_result_path):
        raise RuntimeError(f"Download failed for book_id: {book_id}")
    logging.info(f"Downloaded to: {download_result_path}")
    result = {"file_path": download_result_path}
    if process_for_rag:
        logging.info(f"Processing for RAG: {download_result_path}")
        try:
            processed_text = process_document(download_result_path)
            result["processed_text"] = processed_text
        except Exception as e:
            logging.error(f"Processing failed after download for {download_result_path}: {e}")
            result["processed_text"] = None
    return result

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('function_name', type=str)
    parser.add_argument('json_args', type=str)
    cli_args = parser.parse_args()
    try:
        args_dict = json.loads(cli_args.json_args)
        if cli_args.function_name == 'download_book':
            book_id = args_dict.get('book_id')
            if not book_id: raise ValueError("Missing 'book_id'")
            response = download_book(
                book_id,
                args_dict.get('output_dir'),
                args_dict.get('output_filename'),
                args_dict.get('process_for_rag', False)
            )
        elif cli_args.function_name == 'process_document':
            file_path = args_dict.get('file_path')
            if not file_path: raise ValueError("Missing 'file_path'")
            processed_text = process_document(file_path)
            response = {"processed_text": processed_text}
        else:
            raise ValueError(f"Unknown function: {cli_args.function_name}")
        print(json.dumps(response))
        sys.stdout.flush()
    except Exception as e:
        logging.exception("Python bridge error")
        error_response = {"error": type(e).__name__, "message": str(e)}
        print(json.dumps(error_response))
        sys.stdout.flush()
        sys.exit(1)
```
#### TDD Anchors:
- Test case 1: `download_book` with `process=False` returns only path.
- Test case 2: `download_book` with `process=True` calls `process_document`.
- Test case 3: `download_book` with `process=True` returns path and text (success).
- Test case 4: `download_book` with `process=True` returns path and None text (processing failure).
- Test case 5: `process_document` routes EPUB/TXT correctly.
- Test case 6: `process_document` handles FileNotFoundError.
- Test case 7: `process_document` handles unsupported format ValueError.
- Test case 8: `_process_epub` extracts text from sample EPUB.
- Test case 9: `_process_epub` handles ImportError if libs missing.
- Test case 10: `_process_epub` handles parsing errors.
- Test case 11: `_process_txt` reads UTF-8 file.
- Test case 12: `_process_txt` reads Latin-1 file (fallback).
- Test case 13: `_process_txt` handles read errors.
- Test case 14: Main execution block parses args, calls functions, returns JSON (success/error).

### Pseudocode: Venv Manager Update (`lib/venv-manager.js` Snippet)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-14 12:13:00
```pseudocode
// File: lib/venv-manager.js (Conceptual Snippet)
// ... other imports ...
IMPORT path from 'path'
IMPORT fs from 'fs'

FUNCTION installDependencies(venvDirPath):
  pipPath = getPlatformPipPath(venvDirPath)
  // Assumes requirements.txt is in the project root
  requirementsPath = path.resolve(__dirname, '..', 'requirements.txt')

  IF NOT fs.existsSync(requirementsPath):
      LOG "requirements.txt not found at ${requirementsPath}, skipping dependency installation."
      RETURN
  ENDIF

  LOG "Installing/updating dependencies from requirements.txt using: " + pipPath
  // Use '-r' flag to install from requirements file
  // Add '--upgrade' to ensure existing packages are updated if needed
  command = `"${pipPath}" install --upgrade -r "${requirementsPath}"`
  TRY
    EXECUTE command synchronously // Consider adding output logging
    LOG "Dependencies installed/updated successfully."
  CATCH error
    THROW Error("Failed to install Python dependencies from requirements.txt: " + error.message)
  ENDTRY
END FUNCTION
```
#### TDD Anchors:
- Test case 1: `installDependencies` correctly finds `requirements.txt`.
- Test case 2: `installDependencies` skips if `requirements.txt` is missing.
- Test case 3: `installDependencies` executes pip install command with `-r` and `--upgrade` flags.
- Test case 4: `installDependencies` handles errors during pip execution.

### Pseudocode: VenvManager - Core Logic
- Created: 2025-04-14 03:31:01
- Updated: 2025-04-14 03:31:01
```pseudocode
// File: lib/venv-manager.js
// Dependencies: env-paths, fs, path, child_process

CONSTANT VENV_DIR_NAME = "venv"
CONSTANT CONFIG_FILE_NAME = "venv_config.json"
CONSTANT PYTHON_DEPENDENCY = "zlibrary" // Add version if needed: "zlibrary==1.0.0"

FUNCTION getPythonPath():
  // Main function called by external modules (e.g., zlibrary-api.js)
  // Ensures venv is ready and returns the path to the venv's Python executable.
  TRY
    CALL ensureVenvReady()
    config = READ parseJsonFile(getConfigPath())
    IF config.pythonPath EXISTS AND isExecutable(config.pythonPath) THEN
      RETURN config.pythonPath
    ELSE
      THROW Error("Managed Python environment is configured but invalid.")
    ENDIF
  CATCH error
    LOG error
    THROW Error("Failed to get managed Python environment path: " + error.message)
  ENDTRY
END FUNCTION

FUNCTION ensureVenvReady():
  // Checks if venv is set up; creates/repairs if necessary.
  configPath = getConfigPath()
  venvDir = getVenvDir()

  IF fileExists(configPath) THEN
    config = READ parseJsonFile(configPath)
    IF config.pythonPath EXISTS AND isExecutable(config.pythonPath) THEN
      LOG "Managed Python environment found and valid."
      RETURN // Already ready
    ELSE
      LOG "Managed Python config found but invalid. Attempting repair..."
      // Proceed to setup/repair steps below
    ENDIF
  ELSE
      LOG "Managed Python config not found. Starting setup..."
      // Proceed to setup steps below
  ENDIF

  // Setup/Repair Steps
  IF NOT directoryExists(venvDir) THEN
      LOG "Creating venv directory..."
      pythonExe = CALL findPythonExecutable() // Throws if not found
      CALL createVenv(pythonExe, venvDir) // Throws on failure
  ELSE
      LOG "Venv directory exists."
  ENDIF

  // Always try to install/update dependencies in case venv exists but is incomplete
  LOG "Ensuring dependencies are installed..."
  CALL installDependencies(venvDir) // Throws on failure

  LOG "Saving venv configuration..."
  pythonVenvPath = getPlatformPythonPath(venvDir)
  IF NOT isExecutable(pythonVenvPath) THEN
      THROW Error("Venv Python executable not found or not executable after setup: " + pythonVenvPath)
  ENDIF
  CALL saveVenvConfig(configPath, pythonVenvPath) // Throws on failure

  LOG "Managed Python environment setup complete."
END FUNCTION

FUNCTION findPythonExecutable():
  // Finds a suitable Python 3 executable.
  // Uses a library or custom logic (e.g., check PATH for python3, python).
  // Return path to executable or throw error if not found.
  LOG "Searching for Python 3 executable..."
  // ... implementation using find-python-script or similar ...
  IF foundPath THEN
    LOG "Found Python 3 at: " + foundPath
    RETURN foundPath
  ELSE
    THROW Error("Python 3 installation not found. Please install Python 3 and ensure it's in your PATH.")
  ENDIF
END FUNCTION

FUNCTION createVenv(pythonExePath, venvDirPath):
  // Creates the virtual environment.
  LOG "Creating Python virtual environment at: " + venvDirPath
  command = `"${pythonExePath}" -m venv "${venvDirPath}"`
  TRY
    EXECUTE command synchronously // Use child_process.execSync or async equivalent
    LOG "Venv created successfully."
  CATCH error
    THROW Error("Failed to create Python virtual environment: " + error.message)
  ENDTRY
END FUNCTION

FUNCTION installDependencies(venvDirPath):
  // Installs Python dependencies using the venv's pip.
  pipPath = getPlatformPipPath(venvDirPath)
  IF NOT isExecutable(pipPath) THEN
      THROW Error("Venv pip executable not found or not executable: " + pipPath)
  ENDIF

  LOG "Installing dependencies using: " + pipPath
  command = `"${pipPath}" install ${PYTHON_DEPENDENCY}`
  TRY
    EXECUTE command synchronously // Use child_process.execSync or async equivalent
    LOG "Dependencies installed successfully."
  CATCH error
    THROW Error("Failed to install Python dependencies: " + error.message)
  ENDTRY
END FUNCTION

FUNCTION saveVenvConfig(configFilePath, pythonVenvPath):
  // Saves the venv Python path to the config file.
  configData = { pythonPath: pythonVenvPath }
  TRY
    WRITE JSON.stringify(configData) TO configFilePath
    LOG "Venv configuration saved to: " + configFilePath
  CATCH error
    THROW Error("Failed to write venv config file: " + error.message)
  ENDTRY
END FUNCTION

// --- Helper Functions ---

FUNCTION getConfigPath():
  paths = CALL envPaths('zlibrary-mcp', { suffix: '' })
  RETURN path.join(paths.cache, CONFIG_FILE_NAME)
END FUNCTION

FUNCTION getVenvDir():
  paths = CALL envPaths('zlibrary-mcp', { suffix: '' })
  RETURN path.join(paths.cache, VENV_DIR_NAME)
END FUNCTION

FUNCTION getPlatformPipPath(venvDirPath):
  IF OS is Windows THEN
    RETURN path.join(venvDirPath, 'Scripts', 'pip.exe')
  ELSE // Assume Unix-like
    RETURN path.join(venvDirPath, 'bin', 'pip')
  ENDIF
END FUNCTION

FUNCTION getPlatformPythonPath(venvDirPath):
  IF OS is Windows THEN
    RETURN path.join(venvDirPath, 'Scripts', 'python.exe')
  ELSE // Assume Unix-like
    RETURN path.join(venvDirPath, 'bin', 'python')
  ENDIF
END FUNCTION

FUNCTION isExecutable(filePath):
  // Checks if a file exists and is executable (using fs.accessSync or similar).
  TRY
    CALL fs.accessSync(filePath, fs.constants.X_OK)
    RETURN TRUE
  CATCH error
    RETURN FALSE
  ENDTRY
END FUNCTION

FUNCTION parseJsonFile(filePath):
  // Reads and parses a JSON file. Handles errors.
  TRY
    content = READ fs.readFileSync(filePath, 'utf8')
    RETURN JSON.parse(content)
  CATCH error
    LOG "Error reading/parsing JSON file: " + filePath + " - " + error.message
    RETURN {} // Return empty object on error
  ENDTRY
END FUNCTION

// ... other helpers like fileExists, directoryExists as needed ...
```
#### TDD Anchors:
- Test case 1: Python 3 detection (found/not found/error)
- Test case 2: Venv creation (success/failure)
- Test case 3: Dependency installation (success/failure)
- Test case 4: Config path generation and file I/O (read/write/error)
- Test case 5: Full `ensureVenvReady` lifecycle (initial setup, valid existing, repair invalid)
- Test case 6: `getPythonPath` returns correct path or throws error

### Pseudocode: ZLibraryAPI - Integration
- Created: 2025-04-14 03:31:01
- Updated: 2025-04-14 03:31:01
```pseudocode
// File: lib/zlibrary-api.js (Relevant Snippet)
// Dependencies: python-shell, ./venv-manager

IMPORT { PythonShell } from 'python-shell'
IMPORT venvManager from './venv-manager' // Or adjust path
IMPORT path from 'path'

ASYNC FUNCTION searchZlibrary(query):
  TRY
    // 1. Get the Python path from the venv manager
    pythonPath = AWAIT venvManager.getPythonPath() // Ensures venv is ready

    // 2. Define PythonShell options using the retrieved path
    options = {
      mode: 'text',
      pythonPath: pythonPath, // CRITICAL: Use the managed venv path
      pythonOptions: ['-u'],
      scriptPath: path.dirname(require.resolve('zlibrary/search')), // Adjust if needed
      args: [query]
    }

    // 3. Create and run PythonShell
    pyshell = new PythonShell('search', options) // Assuming 'search.py' is the script

    // ... (rest of the existing promise-based handling for pyshell.on('message'), .end(), .on('error')) ...

  CATCH error
    LOG "Error during Zlibrary search: " + error.message
    THROW error // Re-throw or handle appropriately
  ENDTRY
END FUNCTION
```
#### TDD Anchors:
- Test case 1: `venvManager.getPythonPath` is called before `PythonShell`
- Test case 2: `PythonShell` options include the correct `pythonPath`
- Test case 3: Errors from `getPythonPath` are handled

