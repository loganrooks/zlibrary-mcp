# Specification Writer Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
### Feature: Get Book Metadata (Scraping)
- Added: 2025-05-07 08:02:31
- Description: Define the specification for a tool to scrape metadata from a Z-Library book page URL. This includes the output data structure, detailed scraping logic for 16 fields, data cleaning/parsing rules, error handling for missing fields, Python pseudocode for the scraping function, and TDD anchors.
- Acceptance criteria:
    1. Output metadata object structure (Python dictionary) precisely defined, aligning with Zod schema in [`docs/project-plan-zlibrary-mcp.md:204-222`](docs/project-plan-zlibrary-mcp.md:204-222).
    2. Data types and nullability specified for all 16 fields plus `source_url`.
    3. Scraping logic detailed for each field, using (placeholder) CSS selectors.
    4. Data cleaning and parsing rules specified for each field (e.g., authors list, filesize string, description joining, URL attribute extraction).
    5. Error handling for missing/malformed data defined for each field (e.g., return `None` or `[]`).
    6. Python pseudocode for `async def scrape_book_metadata(url: str, session: httpx.AsyncClient) -> Dict[str, Any]:` provided, showing HTML fetching, parsing, data extraction, cleaning, and dictionary construction.
    7. TDD anchors for Python scraping function cover successful extraction, missing fields, parsing of complex fields, and HTML variations.
    8. TDD anchors for Node.js Zod schemas cover input URL validation and output dictionary validation against various valid/invalid structures.
- Dependencies: `httpx`, `BeautifulSoup4` for Python. Zod for Node.js. CSS selectors from `debug` mode.
- Status: Draft (Specification Complete, pending CSS selectors)
- Related: Task 4 in [`docs/project-plan-zlibrary-mcp.md:166-237`](docs/project-plan-zlibrary-mcp.md:166-237)

### Pseudocode: `scrape_book_metadata` (Z-Library Book Page Scraper)
- Created: 2025-05-07 08:02:31
- Updated: 2025-05-07 08:02:31
```pseudocode
# File: zlibrary/src/zlibrary/libasync.py (or new scraping module)
# Dependencies: httpx, beautifulsoup4, typing, re, urllib.parse

from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin

# Placeholder for actual selectors - these need to be defined based on debug mode's findings
SELECTORS = {
    "title": "h1.book-title",
    "authors": "div.col-sm-9 > i > a.color1[title*=\"Find all the author's book\"]",
    "publisher": "div.bookProperty.property_publisher > div.property_value",
    "publication_year": "div.bookProperty.property_year > div.property_value",
    "isbn13": "div.bookProperty.property_isbn.13 > div.property_value",
    "isbn10": "div.bookProperty.property_isbn.10 > div.property_value",
    "doi": "div.bookProperty.property_isbn > div.property_value", # Example, may need specific selector for DOI if different from ISBN field
    "series": "div.bookProperty.property_series > div.property_value",
    "language": "div.bookProperty.property_language > div.property_value",
    "pages": "div.bookProperty.property_pages > div.property_value > span[title*=\"Pages\"]",
    "filesize": "div.bookProperty.property__file > div.property_value",
    "description": "div#bookDescriptionBox",
    "cover_image_url": "div.details-book-cover-container z-cover img[src]", # Or specific img inside
    "tags": "SELECTOR_FOR_TAGS_ANCHOR_OR_ELEMENT a", # Placeholder - e.g., div.tags-container a
    "most_frequent_terms": "div.termsCloud div.termWrap a.color1",
    "related_booklist_urls": "div.related-booklists-block z-booklist[href]", # Placeholder for custom element attribute or child a[href]
    "you_may_be_interested_in_urls": "div.books-mosaic div.masonry-endless div.item a[href*=\"/book/\"]"
}

BookMetadata = Dict[str, Any]

def _safe_get_text(element, default=None):
    if element:
        text = element.get_text(strip=True)
        return text if text else default
    return default

def _safe_get_attr(element, attribute, base_url: Optional[str] = None, default=None):
    if element:
        attr_value = element.get(attribute)
        if attr_value:
            if (attribute == 'href' or attribute == 'src') and base_url:
                attr_value = urljoin(base_url, attr_value)
            return attr_value
    return default

def _safe_get_all_texts(elements_list, default_if_empty=None):
    # ... (implementation as in previous markdown) ...
    if not elements_list:
        return default_if_empty if default_if_empty is not None else []
    texts = [el.get_text(strip=True) for el in elements_list if el.get_text(strip=True)]
    return texts if texts else (default_if_empty if default_if_empty is not None else [])


def _safe_get_all_attrs(elements_list, attribute, base_url: Optional[str] = None, default_if_empty=None):
    # ... (implementation as in previous markdown, ensuring urljoin is used) ...
    if not elements_list:
        return default_if_empty if default_if_empty is not None else []
    attrs = []
    for el in elements_list:
        attr_val = el.get(attribute)
        if attr_val:
            if (attribute == 'href' or attribute == 'src') and base_url:
                attr_val = urljoin(base_url, attr_val)
            attrs.append(attr_val)
    return attrs if attrs else (default_if_empty if default_if_empty is not None else [])

async def scrape_book_metadata(url: str, session: httpx.AsyncClient) -> BookMetadata:
    metadata: BookMetadata = { # Initialize with defaults
        "title": None, "authors": [], "publisher": None, "publication_year": None,
        "isbn": None, "doi": None, "series": None, "language": None, "pages": None,
        "filesize": None, "description": None, "cover_image_url": None, "tags": [],
        "most_frequent_terms": [], "related_booklist_urls": [],
        "you_may_be_interested_in_urls": [], "source_url": url
    }
    parsed_url_obj = urlparse(url)
    base_page_url = f"{parsed_url_obj.scheme}://{parsed_url_obj.netloc}"

    try:
        response = await session.get(url, timeout=20.0, follow_redirects=True)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # --- Title ---
        metadata["title"] = _safe_get_text(soup.select_one(SELECTORS["title"]))

        # --- Authors ---
        metadata["authors"] = _safe_get_all_texts(soup.select(SELECTORS["authors"]), default_if_empty=[])

        # --- Publisher ---
        metadata["publisher"] = _safe_get_text(soup.select_one(SELECTORS["publisher"]))

        # --- Publication Year ---
        year_text = _safe_get_text(soup.select_one(SELECTORS["publication_year"]))
        if year_text and year_text.isdigit(): metadata["publication_year"] = int(year_text)

        # --- ISBN ---
        isbn_text = _safe_get_text(soup.select_one(SELECTORS["isbn13"]))
        if not isbn_text: isbn_text = _safe_get_text(soup.select_one(SELECTORS["isbn10"]))
        if isbn_text: metadata["isbn"] = re.sub(r"[^0-9X]", "", isbn_text)

        # --- DOI ---
        # This selector needs to be specific for DOI, or logic to differentiate from ISBN if field is shared
        doi_element = soup.select_one(SELECTORS["doi"])
        doi_text = _safe_get_text(doi_element)
        if doi_text:
            # Basic check to differentiate from ISBN if selector is shared
            if "10." in doi_text and "/" in doi_text and (not metadata["isbn"] or metadata["isbn"] != re.sub(r"[^0-9X]", "", doi_text)):
                 metadata["doi"] = doi_text.replace("DOI:", "").strip()
            # If DOI selector is different from ISBN, this check might not be needed.

        # --- Series ---
        metadata["series"] = _safe_get_text(soup.select_one(SELECTORS["series"]))

        # --- Language ---
        lang_text = _safe_get_text(soup.select_one(SELECTORS["language"]))
        if lang_text: metadata["language"] = lang_text.lower()

        # --- Pages ---
        pages_text = _safe_get_text(soup.select_one(SELECTORS["pages"]))
        if pages_text:
            cleaned_pages = re.sub(r'\D', '', pages_text)
            if cleaned_pages.isdigit(): metadata["pages"] = int(cleaned_pages)

        # --- Filesize ---
        filesize_text = _safe_get_text(soup.select_one(SELECTORS["filesize"]))
        if filesize_text:
            match = re.search(r'(\d+(\.\d+)?\s*(KB|MB|GB))', filesize_text, re.IGNORECASE)
            if match: metadata["filesize"] = match.group(1)

        # --- Description ---
        desc_el = soup.select_one(SELECTORS["description"])
        if desc_el:
            p_tags = desc_el.find_all('p', recursive=False) # Only direct children
            if p_tags:
                metadata["description"] = "\n".join([p.get_text(strip=True) for p in p_tags if p.get_text(strip=True)]).strip()
            else:
                metadata["description"] = desc_el.get_text(separator="\n", strip=True)


        # --- Cover Image URL ---
        metadata["cover_image_url"] = _safe_get_attr(soup.select_one(SELECTORS["cover_image_url"]), "src", base_url=base_page_url)

        # --- Tags ---
        # Placeholder: Actual selector for tags needed
        metadata["tags"] = _safe_get_all_texts(soup.select(SELECTORS["tags"]), default_if_empty=[])

        # --- Most Frequent Terms ---
        metadata["most_frequent_terms"] = _safe_get_all_texts(soup.select(SELECTORS["most_frequent_terms"]), default_if_empty=[])

        # --- Related Booklist URLs ---
        # Placeholder: Actual selector for related booklist URLs needed
        metadata["related_booklist_urls"] = _safe_get_all_attrs(soup.select(SELECTORS["related_booklist_urls"]), "href", base_url=base_page_url, default_if_empty=[])

        # --- "You may be interested in" URLs ---
        metadata["you_may_be_interested_in_urls"] = _safe_get_all_attrs(soup.select(SELECTORS["you_may_be_interested_in_urls"]), "href", base_url=base_page_url, default_if_empty=[])

    except httpx.HTTPStatusError as e:
        # LOG error: HTTP error fetching {url}: {e.response.status_code}
        pass # Keep defaults
    except httpx.RequestError as e:
        # LOG error: Network error fetching {url}: {e}
        pass # Keep defaults
    except Exception as e:
        # LOG error: Unexpected error scraping {url}: {e}
        pass # Keep defaults
    
    return metadata
```
#### TDD Anchors:
- Test successful extraction of all 16 fields from a complete HTML page.
- Test handling of missing optional fields (e.g., DOI, Series result in `None` or `[]`).
- Test parsing of multiple authors into a list.
- Test correct conversion of publication year and pages to integers.
- Test cleaning of ISBN and DOI strings.
- Test extraction of filesize string (e.g., "12.10 MB").
- Test joining of multi-paragraph descriptions.
- Test correct extraction of `src` for cover image and `href` for URL lists, ensuring they are absolute URLs.
- Test graceful handling of HTTP errors (404, 500) and network errors (timeout).
- Test with HTML variations if `debug` mode identified significant structural differences between pages.
- Test extraction from an article page, focusing on DOI presence.

```
### Feature: Enhanced Filename Convention
- Added: 2025-05-07
- Description: Implement an enhanced filename convention `LastnameFirstname_TitleOfTheBook_BookID.ext` for downloaded books, including author/title formatting, sanitization, and fallbacks.
- Acceptance criteria:
    1. Filenames correctly generated according to the specified format.
    2. Author names are parsed and formatted (LastnameFirstname, handling single/multiple names, initials).
    3. Titles are slugified (spaces to underscores).
    4. BookID is included.
    5. Original extension is used and lowercased.
    6. All components are sanitized for filesystem safety (character removal/replacement, length truncation).
    7. Underscore used as a separator between main components.
    8. Fallback values ("UnknownAuthor", "UntitledBook", "UnknownID", ".unknown") used for missing/empty data.
    9. Python helper function `_create_enhanced_filename(book_details: dict) -> str` implemented in `lib/python_bridge.py`.
   10. Comprehensive TDD test cases cover all specified formatting, sanitization, and edge cases.
- Dependencies: Python `re` module.
- Status: Draft (Specification Complete)
- Related: [`docs/project-plan-zlibrary-mcp.md:130-162`](docs/project-plan-zlibrary-mcp.md:130-162) (Task 3)

### Feature: RAG Robustness - Preprocessing (Front Matter & ToC)
- Added: 2025-04-29 23:15:00
- Description: Implement preprocessing to remove front matter (excluding Title) and extract/format the Table of Contents (ToC) from PDF/EPUB content before RAG processing.
- Acceptance criteria: 1. Front matter identified and removed using heuristics. 2. Title identified and preserved. 3. ToC identified and extracted. 4. ToC formatted as linked Markdown list if output is Markdown. 5. Preprocessing integrated into `process_pdf`/`process_epub`.
- Dependencies: Python (`re`).
- Status: Draft (Specification Complete)
- Related: `docs/rag-robustness-enhancement-spec.md#5-preprocessing---front-matter--toc-handling`

### Feature: RAG Robustness - AI-Assisted Quality Evaluation
- Added: 2025-04-29 23:15:00
- Description: Integrate AI-driven quality assessment into the testing framework to evaluate processed real-world documents for faithfulness, readability, formatting, noise, and preprocessing correctness.
- Acceptance criteria: 1. Testing framework calls AI agent (placeholder/mock initially) with processed content. 2. AI agent provides score and feedback. 3. AI results included in test reports. 4. Pass/fail criteria incorporate AI score.
- Dependencies: Testing framework (`scripts/run_rag_tests.py`), mechanism to call AI agent (e.g., MCP tool, external API).
- Status: Draft (Specification Complete)
- Related: `docs/rag-robustness-enhancement-spec.md#23-testing-methodology--metrics` (FR-TEST-11.5)

*(Updated)* ### Feature: RAG Robustness - Real-World Testing Strategy
- Added: 2025-04-29 19:54:15
- Updated: 2025-04-29 23:15:00
- Description: Define and implement a strategy for testing the RAG pipeline using real-world documents, including selection, storage, methodology (quantitative metrics + AI assessment), pass/fail criteria, and results documentation.
- Acceptance criteria: 1. Test corpus manifest created. 2. Testing framework script implemented. 3. Quantitative metrics defined. 4. AI assessment integrated (FR-TEST-11.5). 5. Pass/Fail criteria updated (FR-TEST-12). 6. Results documentation includes AI feedback (FR-TEST-14).
- Dependencies: `download_book_to_file`, `process_document_for_rag`, Python (`json`, `pathlib`), AI agent mechanism.
- Status: Draft (Specification Complete)
- Related: `docs/rag-robustness-enhancement-spec.md#2-real-world-testing-strategy`
## Functional Requirements
### Feature: RAG Robustness - Real-World Testing Strategy
- Added: 2025-04-29 19:54:15
- Description: Define and implement a strategy for testing the RAG pipeline using a diverse set of real-world documents (PDFs, EPUBs) focusing on philosophy texts, including selection, storage (metadata manifest + on-demand download), methodology, metrics (completeness, accuracy, noise, readability, structure), and results documentation.
- Acceptance criteria: 1. Test corpus manifest (`test_files/rag_corpus/manifest.json`) created. 2. Small local sample set stored (if feasible). 3. Testing framework script (`scripts/run_rag_tests.py`) implemented. 4. Text extraction metrics defined and measurable. 5. Markdown structure metrics defined and measurable. 6. Pass/Fail criteria defined. 7. Results documentation format defined.
- Dependencies: `download_book_to_file` tool, `process_document_for_rag` tool, Python (`json`, `pathlib`, potentially `subprocess` or MCP client lib).
- Status: Draft (Specification Complete)
- Related: `docs/rag-robustness-enhancement-spec.md#2-real-world-testing-strategy`

### Feature: RAG Robustness - PDF Quality Analysis & Improvement
### Pseudocode: PDF Quality Detection (`lib/rag_processing.py`) - `detect_pdf_quality`
- Created: 2025-04-29 19:54:15
```pseudocode
# File: lib/rag_processing.py

FUNCTION detect_pdf_quality(doc: fitz.Document) -> str:
  """Analyzes a PyMuPDF document and returns a quality category."""
  total_pages = len(doc)
  if total_pages == 0: return "EMPTY"

  text_char_count = 0
  image_area_ratio_sum = 0
  font_count = len(doc.get_fonts(full=False)) # Quick check for any fonts

  for page_num in range(total_pages):
    page = doc.load_page(page_num)

    # Text Density Check
    text = page.get_text("text", flags=0) # Basic text extraction
    text_char_count += len(text.strip())

    # Image Area Check
    images = page.get_images(full=True)
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height
    if page_area > 0:
      page_image_area = 0
      for img_info in images:
        xref = img_info[0]
        img_rects = page.get_image_rects(xref) # Find where image is placed
        for rect in img_rects:
             page_image_area += rect.width * rect.height
      image_area_ratio_sum += (page_image_area / page_area)

  avg_chars_per_page = text_char_count / total_pages
  avg_image_ratio = image_area_ratio_sum / total_pages

  # Heuristics (Tunable Thresholds)
  TEXT_DENSITY_THRESHOLD_LOW = 50 # Avg chars per page
  IMAGE_RATIO_THRESHOLD_HIGH = 0.7 # Avg image area ratio

  if avg_chars_per_page < TEXT_DENSITY_THRESHOLD_LOW and avg_image_ratio > IMAGE_RATIO_THRESHOLD_HIGH and font_count == 0:
    return "IMAGE_ONLY"
  elif avg_chars_per_page < TEXT_DENSITY_THRESHOLD_LOW:
    # Low text, might be scanned or poorly extracted
    return "TEXT_LOW"
  elif avg_image_ratio > IMAGE_RATIO_THRESHOLD_HIGH:
    # High image content, but some text present
    return "MIXED"
  else:
    # Assume reasonable text content
    return "TEXT_HIGH"

END FUNCTION
```
#### TDD Anchors:
- `test_detect_quality_text_high`: Verify a normal text PDF returns "TEXT_HIGH".
- `test_detect_quality_image_only`: Verify a scanned PDF (mocked `get_text` empty, `get_images` large, `get_fonts` empty) returns "IMAGE_ONLY".
- `test_detect_quality_text_low`: Verify a PDF with very little text (mocked `get_text` short) returns "TEXT_LOW".
- `test_detect_quality_mixed`: Verify a PDF with significant images but also text returns "MIXED".
- `test_detect_quality_empty_pdf`: Verify an empty PDF (0 pages) returns "EMPTY".
- Related: `docs/rag-robustness-enhancement-spec.md#81-pdf-quality-detection-librag_processingpy`

### Pseudocode: OCR Integration Workflow (`lib/rag_processing.py`) - `run_ocr_on_pdf` & `process_pdf` Update
- Created: 2025-04-29 19:54:15
```pseudocode
# File: lib/rag_processing.py
# Assumes pytesseract and Pillow/OpenCV are potentially available

FUNCTION run_ocr_on_pdf(pdf_path_str: str, lang: str = 'eng') -> str:
  """Runs OCR on a PDF, potentially page by page, returns aggregated text."""
  # Check if pytesseract and an image library are available
  # Check if tesseract executable is available
  # Handle potential errors if dependencies are missing

  aggregated_text = []
  doc = None
  try:
    doc = fitz.open(pdf_path_str)
    for page_num in range(len(doc)):
      page = doc.load_page(page_num)
      pix = page.get_pixmap(dpi=300) # Render page to image
      img_bytes = pix.tobytes("png") # Get image bytes

      # --- Optional Preprocessing ---
      # image = Image.open(io.BytesIO(img_bytes))
      # image = preprocess_image(image) # Deskew, enhance contrast etc.
      # img_bytes = image_to_bytes(image)
      # --- End Preprocessing ---

      try:
        # Use pytesseract to OCR the image bytes
        page_text = pytesseract.image_to_string(Image.open(io.BytesIO(img_bytes)), lang=lang)
        if page_text:
          aggregated_text.append(page_text.strip())
      except Exception as ocr_error:
        LOG warning f"OCR failed for page {page_num+1} of {pdf_path_str}: {ocr_error}"
        # Optionally: Add placeholder text like "[OCR Failed for Page]"

  except Exception as e:
    LOG error f"Error during OCR preparation for {pdf_path_str}: {e}"
    raise RuntimeError(f"OCR preparation failed: {e}") from e
  finally:
    if doc: doc.close()

  return "\n\n".join(aggregated_text).strip()
END FUNCTION

# --- Update process_pdf ---
FUNCTION process_pdf(file_path: Path, output_format: str = "txt") -> str:
  # ... (initial checks, open doc) ...
  try:
    quality_category = detect_pdf_quality(doc) # Call detection
    logging.info(f"Detected PDF quality for {file_path}: {quality_category}")

    processed_text = None
    ocr_triggered = False

    if quality_category == "TEXT_HIGH":
      # Proceed with PyMuPDF extraction as before (call _format_pdf_markdown or get_text)
      # ... (existing PyMuPDF extraction logic) ...
      processed_text = # result from PyMuPDF extraction
    elif quality_category in ["IMAGE_ONLY", "TEXT_LOW"]:
      try:
        logging.info(f"Triggering OCR for {file_path} due to quality: {quality_category}")
        processed_text = run_ocr_on_pdf(str(file_path)) # Run OCR
        ocr_triggered = True
      except Exception as ocr_err:
        logging.error(f"OCR failed for {file_path}: {ocr_err}. Falling back.")
        # Fallback: Try PyMuPDF anyway for TEXT_LOW, or return empty for IMAGE_ONLY
        if quality_category == "TEXT_LOW":
           # ... (existing PyMuPDF extraction logic) ...
           processed_text = # result from PyMuPDF extraction
        else:
           processed_text = "" # No text from image-only if OCR fails
    elif quality_category == "MIXED":
       # Hybrid approach: Try PyMuPDF first, consider OCR if yield is low?
       # ... (existing PyMuPDF extraction logic) ...
       processed_text = # result from PyMuPDF extraction
       if len(processed_text) < SOME_THRESHOLD * total_pages: # Example threshold
           try:
               logging.info(f"Low text yield from PyMuPDF for MIXED quality {file_path}. Triggering OCR as fallback.")
               ocr_text = run_ocr_on_pdf(str(file_path))
               ocr_triggered = True
               # Combine or replace? For now, let's prefer OCR if triggered.
               processed_text = ocr_text
           except Exception as ocr_err:
               logging.error(f"Fallback OCR failed for {file_path}: {ocr_err}. Using PyMuPDF result.")
               # Keep the potentially low-yield PyMuPDF text
    elif quality_category == "EMPTY":
        processed_text = ""
    else: # Default fallback
        # ... (existing PyMuPDF extraction logic) ...
        processed_text = # result from PyMuPDF extraction

    # Return the final processed text (could be from PyMuPDF or OCR)
    # The calling function `process_document` will handle saving this text.
    return processed_text if processed_text is not None else ""

  # ... (rest of exception handling and finally block) ...
END FUNCTION
```
#### TDD Anchors:
- `test_process_pdf_triggers_ocr_for_image_only`: Mock `detect_pdf_quality` to return "IMAGE_ONLY", mock `run_ocr_on_pdf` to return text. Verify `run_ocr_on_pdf` is called and its text is returned.
- `test_process_pdf_triggers_ocr_for_text_low`: Mock `detect_pdf_quality` to return "TEXT_LOW", mock `run_ocr_on_pdf`. Verify `run_ocr_on_pdf` is called.
- `test_process_pdf_uses_pymupdf_for_text_high`: Mock `detect_pdf_quality` to return "TEXT_HIGH", mock `run_ocr_on_pdf`. Verify `run_ocr_on_pdf` is NOT called and PyMuPDF text is returned.
- `test_process_pdf_handles_ocr_failure`: Mock `detect_pdf_quality` to return "IMAGE_ONLY", mock `run_ocr_on_pdf` to raise `RuntimeError`. Verify error is logged and empty string is returned.
- `test_run_ocr_on_pdf_success`: Mock `fitz.open`, `page.get_pixmap`, `pytesseract.image_to_string`. Verify aggregated text is returned.
- `test_run_ocr_on_pdf_tesseract_not_found`: Mock `pytesseract` call to raise error. Verify `RuntimeError` is raised or handled.
- Related: `docs/rag-robustness-enhancement-spec.md#82-ocr-integration-workflow-librag_processingpy`

### Pseudocode: Testing Framework (`scripts/run_rag_tests.py`)
- Created: 2025-04-29 19:54:15
```pseudocode
# File: scripts/run_rag_tests.py
# Dependencies: argparse, json, pathlib, subprocess (or MCP client if running via tool)
# Assumes zlibrary-mcp server is running or can be called via python_bridge directly

FUNCTION load_manifest(manifest_path):
  # Load JSON manifest file
END FUNCTION

FUNCTION run_single_test(doc_metadata, output_dir, mcp_client):
  # doc_metadata contains ID, format, URL, expected_challenges etc.
  results = {'doc_id': doc_metadata['id'], 'format': doc_metadata['format']}
  downloaded_path = None
  processed_text_path = None
  processed_md_path = None

  TRY
    # 1. Download (if not locally available sample)
    if 'local_sample_path' in doc_metadata:
      downloaded_path = doc_metadata['local_sample_path']
    else:
      # Use download_book_to_file tool via mcp_client or direct call
      # download_result = mcp_client.call('download_book_to_file', {'bookDetails': {...}, 'outputDir': 'temp_downloads'}) # Need bookDetails! Requires search first.
      # OR: Assume download happens externally, test needs path provided.
      # For simplicity, assume path is available or downloaded externally for now.
      downloaded_path = find_or_download_book(doc_metadata['id'], doc_metadata['format']) # Placeholder

    # 2. Process for Text
    # process_text_result = mcp_client.call('process_document_for_rag', {'file_path': downloaded_path, 'output_format': 'txt'})
    process_text_result = call_python_bridge_directly('process_document', {'file_path': downloaded_path, 'output_format': 'txt'}) # Example direct call
    processed_text_path = process_text_result.get('processed_file_path')
    results['text_output_path'] = processed_text_path

    # 3. Process for Markdown
    # process_md_result = mcp_client.call('process_document_for_rag', {'file_path': downloaded_path, 'output_format': 'markdown'})
    process_md_result = call_python_bridge_directly('process_document', {'file_path': downloaded_path, 'output_format': 'markdown'}) # Example direct call
    processed_md_path = process_md_result.get('processed_file_path')
    results['md_output_path'] = processed_md_path

    # 4. Evaluate Outputs
    if processed_text_path:
      results['text_metrics'] = evaluate_output(processed_text_path, 'text', doc_metadata)
    else:
      results['text_metrics'] = {'error': 'Processing failed or no text extracted'}

    if processed_md_path:
      results['md_metrics'] = evaluate_output(processed_md_path, 'markdown', doc_metadata)
    else:
      results['md_metrics'] = {'error': 'Processing failed or no text extracted'}

    # Determine overall pass/fail based on metrics and criteria (FR-TEST-12)
    results['status'] = determine_pass_fail(results, doc_metadata)

  CATCH Exception as e:
    results['status'] = 'FAIL'
    results['error'] = str(e)
  FINALLY:
    # Clean up temp downloads?
    pass

  RETURN results
END FUNCTION

FUNCTION evaluate_output(output_path, format_type, doc_metadata):
  # Load output file content
  # Apply metrics based on format_type (Text: FR-TEST-09, Markdown: FR-TEST-10)
  # Compare against ground truth if available, use heuristics/qualitative scores otherwise
  metrics = {}
  # ... calculate metrics ...
  metrics['completeness_score'] = calculate_completeness(...)
  metrics['accuracy_score'] = calculate_accuracy(...)
  if format_type == 'text':
    metrics['noise_score'] = score_noise(...)
    metrics['readability_score'] = score_readability(...)
  elif format_type == 'markdown':
    metrics['heading_accuracy'] = calculate_heading_accuracy(...)
    metrics['list_accuracy'] = calculate_list_accuracy(...)
    metrics['footnote_accuracy'] = calculate_footnote_accuracy(...)
    metrics['structure_score'] = score_structure(...)
  RETURN metrics
END FUNCTION

FUNCTION determine_pass_fail(results, doc_metadata):
  # Implement logic based on FR-TEST-12
  # Check if required metrics meet target thresholds
  # ...
  RETURN 'PASS' or 'FAIL'
END FUNCTION

FUNCTION main():
  # Parse args: manifest_path, output_dir
  manifest = load_manifest(manifest_path)
  all_results = []
  # Initialize MCP client or setup direct bridge call

  for doc_metadata in manifest['documents']:
    test_result = run_single_test(doc_metadata, output_dir, mcp_client)
    all_results.append(test_result)

  # Generate summary report
  generate_report(all_results, output_dir)
  # Print summary (pass/fail counts)
END FUNCTION

IF __name__ == "__main__":
  main()
```
#### TDD Anchors:
- `test_load_manifest_success`: Verify loading a valid JSON manifest.
- `test_load_manifest_not_found`: Verify error handling for missing manifest.
- `test_run_single_test_calls_process`: Mock `call_python_bridge_directly` (or MCP client), verify `process_document` is called for both 'text' and 'markdown'.
- `test_run_single_test_calls_evaluate`: Mock `evaluate_output`, verify it's called for both formats if processing succeeds.
- `test_run_single_test_handles_processing_error`: Mock `call_python_bridge_directly` to raise error, verify result status is 'FAIL' with error message.
- `test_evaluate_output_text_metrics`: Provide sample text output, verify correct calculation/scoring for text metrics.
- `test_evaluate_output_md_metrics`: Provide sample MD output, verify correct calculation/scoring for MD metrics.
- `test_determine_pass_fail`: Provide sample results dicts, verify correct 'PASS'/'FAIL' determination based on criteria.
- Related: `docs/rag-robustness-enhancement-spec.md#83-testing-framework-scriptsrun_rag_testspy`
- Added: 2025-04-29 19:54:15
- Description: Investigate current PyMuPDF limitations, implement PDF quality detection (`detect_pdf_quality`), integrate OCR (e.g., Tesseract) with conditional triggering based on quality, optionally add preprocessing, and evaluate alternative libraries (`pdfminer.six`).
- Acceptance criteria: 1. PyMuPDF limitations documented. 2. `detect_pdf_quality` function implemented and categorizes PDFs (TEXT_HIGH, TEXT_LOW, IMAGE_ONLY, MIXED). 3. OCR engine integrated into `process_pdf` workflow. 4. OCR triggered correctly based on quality category. 5. OCR errors handled gracefully. 6. (Optional) Preprocessing steps implemented. 7. Alternative library comparison performed and documented.
- Dependencies: Python (`PyMuPDF`, `pytesseract`, potentially `Pillow`/`OpenCV`, `pdfminer.six`), Tesseract system dependency.
- Status: Draft (Specification Complete)
- Related: `docs/rag-robustness-enhancement-spec.md#3-pdf-quality-analysis--improvement`

### Feature: RAG Robustness - EPUB Handling Review & Enhancement
- Added: 2025-04-29 19:54:15
- Description: Review current EPUB processing (`process_epub`, `_epub_node_to_markdown`) using the real-world test corpus, identify limitations (nested lists, tables, images, non-standard footnotes), and implement specified enhancements.
- Acceptance criteria: 1. Review completed and limitations documented. 2. Enhancements for tables (basic conversion), images (placeholders), and potentially footnotes implemented in `_epub_node_to_markdown`. 3. Improved handling reflected in test results.
- Dependencies: Python (`ebooklib`, `beautifulsoup4`).
- Status: Draft (Specification Complete)
- Related: `docs/rag-robustness-enhancement-spec.md#4-epub-handling-review`
### Feature: RAG Markdown Structure Generation
- Added: 2025-04-29 02:40:07
- Description: Enhance `_process_pdf` and `_process_epub` in `lib/python_bridge.py` to generate structured Markdown (headings, lists, footnotes) when `output_format='markdown'`, meeting criteria in `docs/rag-output-quality-spec.md`. Strategy uses refined `PyMuPDF` heuristics and enhanced `BeautifulSoup` logic.
- Acceptance criteria: 1. `_process_pdf` generates correct Markdown headings based on font size/style. 2. `_process_pdf` generates correct Markdown lists based on text patterns/indentation. 3. `_process_pdf` generates correct Markdown footnotes based on superscript flags. 4. `_process_epub` generates correct Markdown headings based on `h1-h6` tags. 5. `_process_epub` generates correct Markdown lists (ordered/unordered, nested) based on `ul/ol/li` tags. 6. `_process_epub` generates correct Markdown footnotes based on `epub:type` attributes. 7. Output passes QA against `docs/rag-output-quality-spec.md`.
- Dependencies: Python (`PyMuPDF`, `ebooklib`, `beautifulsoup4`, `lxml`).
- Status: Draft (Specification Complete)
- Related: `docs/rag-markdown-generation-spec.md`, `docs/rag-output-quality-spec.md`, `docs/rag-output-qa-report-rerun-20250429.md`

## Pseudocode Library
### Pseudocode: Enhanced Filename Generation - `_create_enhanced_filename`
- Created: 2025-05-07
- Updated: 2025-05-07
```pseudocode
# File: lib/python_bridge.py
# Dependencies: re

CONSTANT MAX_AUTHOR_LEN = 50
CONSTANT MAX_TITLE_LEN = 100
CONSTANT MAX_TOTAL_FILENAME_BASE_LEN = 200 # Max length before adding extension
CONSTANT INVALID_FILENAME_CHARS_REGEX = r'[/\?%*:|"<>.\\,;=!@#$^&()+{}\[\]~`\']'
CONSTANT NON_ASCII_ALPHANUMERIC_PRESERVE_REGEX = r'[^a-zA-Z0-9_]'

FUNCTION _sanitize_string(input_str: str, component_type: str) -> str:
  sanitized = input_str
  if component_type == "title":
    sanitized = REGEX_REPLACE(sanitized, r'\s+', '_')
  if component_type == "author" OR component_type == "title":
    sanitized = REGEX_REPLACE(sanitized, INVALID_FILENAME_CHARS_REGEX, '')
  elif component_type == "book_id":
    sanitized = REGEX_REPLACE(sanitized, r'[^a-zA-Z0-9]', '')
  if component_type == "author":
    sanitized = REGEX_REPLACE(sanitized, r'\s+', '')
  sanitized = REGEX_REPLACE(sanitized, r'_+', '_')
  sanitized = REGEX_REPLACE(sanitized, r'^_+|_+$', '')
  if component_type == "author":
    if LENGTH(sanitized) > MAX_AUTHOR_LEN:
      sanitized = SUBSTRING(sanitized, 0, MAX_AUTHOR_LEN)
  elif component_type == "title":
    if LENGTH(sanitized) > MAX_TITLE_LEN:
      sanitized = SUBSTRING(sanitized, 0, MAX_TITLE_LEN)
      sanitized = REGEX_REPLACE(sanitized, r'_+$', '')
  RETURN sanitized
END FUNCTION

FUNCTION _format_author(author_str: str) -> str:
  if NOT author_str OR author_str.strip() == "": RETURN "UnknownAuthor"
  first_author = author_str.split(',')[0].split(' and ')[0].split(';')[0].strip()
  words = first_author.split()
  if LENGTH(words) == 0: RETURN "UnknownAuthor"
  if LENGTH(words) == 1:
    lastname = words[0]
    if lastname.isupper() OR (ANY(c.islower() for c in lastname) AND ANY(c.isupper() for c in lastname)):
        lastname = lastname[0].upper() + lastname[1:].lower() if LENGTH(lastname) > 1 else lastname.upper()
    else:
        lastname = lastname.capitalize()
    formatted_name = lastname
  else:
    lastname = words[-1]
    firstnames_parts = words[:-1]
    lastname = lastname[0].upper() + lastname[1:].lower() if LENGTH(lastname) > 1 else lastname.upper()
    formatted_firstnames = ""
    for part in firstnames_parts:
      temp_part = part
      is_initial_with_period = LENGTH(temp_part) == 2 AND temp_part[1] == '.' AND temp_part[0].isalpha()
      is_initial_alone = LENGTH(temp_part) == 1 AND temp_part[0].isalpha()
      if is_initial_with_period OR is_initial_alone:
          formatted_firstnames += temp_part[0].upper()
          if is_initial_with_period: formatted_firstnames += "."
      else:
          formatted_firstnames += part.capitalize()
    formatted_name = lastname + formatted_firstnames
  RETURN _sanitize_string(formatted_name, "author")
END FUNCTION

FUNCTION _format_title(title_str: str) -> str:
  if NOT title_str OR title_str.strip() == "": RETURN "UntitledBook"
  RETURN _sanitize_string(title_str, "title")
END FUNCTION

FUNCTION _format_book_id(book_id_val) -> str:
  if book_id_val IS NULL OR TRIM(str(book_id_val)) == "": RETURN "UnknownID"
  RETURN _sanitize_string(str(book_id_val), "book_id")
END FUNCTION

FUNCTION _format_extension(ext_str: str) -> str:
  if NOT ext_str OR ext_str.strip() == "": ext = "unknown"
  else:
    ext = ext_str.lower()
    if ext.startswith("."): ext = ext[1:]
  ext = REGEX_REPLACE(ext, r'[^a-z0-9]', '')
  if ext == "": return "unknown"
  RETURN ext
END FUNCTION

FUNCTION _create_enhanced_filename(book_details: dict) -> str:
  author_name = _format_author(book_details.get("author"))
  book_title = _format_title(book_details.get("title"))
  book_id = _format_book_id(book_details.get("id"))
  extension = _format_extension(book_details.get("extension"))

  if author_name == "": author_name = "UnknownAuthor"
  if book_title == "" OR book_title == "_": book_title = "UntitledBook"
  if book_id == "": book_id = "UnknownID"
  if extension == "": extension = "unknown"

  base_filename_parts = [author_name, book_title, book_id]
  valid_parts = [part for part in base_filename_parts if part and part != "_"]
  base_filename = "_".join(valid_parts)

  if LENGTH(base_filename) > MAX_TOTAL_FILENAME_BASE_LEN:
    overflow = LENGTH(base_filename) - MAX_TOTAL_FILENAME_BASE_LEN
    if LENGTH(book_title) > overflow AND LENGTH(book_title) > LENGTH(author_name) AND LENGTH(book_title) > LENGTH(book_id):
        new_title_len = LENGTH(book_title) - overflow
        book_title = SUBSTRING(book_title, 0, new_title_len)
        book_title = REGEX_REPLACE(book_title, r'_+$', '')
        if book_title == "": book_title = "ShortTitle"
    base_filename_parts = [author_name, book_title, book_id]
    valid_parts = [part for part in base_filename_parts if part and part != "_"]
    base_filename = "_".join(valid_parts)
    if LENGTH(base_filename) > MAX_TOTAL_FILENAME_BASE_LEN:
        base_filename = SUBSTRING(base_filename, 0, MAX_TOTAL_FILENAME_BASE_LEN)
        base_filename = REGEX_REPLACE(base_filename, r'_+$', '')

  final_filename = base_filename + "." + extension
  RETURN final_filename
END FUNCTION
```
#### TDD Anchors:
1.  **Standard Input:** `{"author": "Stephen King", "title": "The Shining", "id": "12345", "extension": "epub"}` -> `"KingStephen_The_Shining_12345.epub"`
2.  **Author Formatting:**
    *   Single name: `{"author": "Plato", ...}` -> `"Plato_..."`
    *   Multiple given names: `{"author": "John Ronald Reuel Tolkien", ...}` -> `"TolkienJohnRonaldReuel_..."`
    *   Missing author: `{"title": "A Book", ...}` -> `"UnknownAuthor_A_Book_..."`
    *   Initials: `{"author": "J. K. Rowling", ...}` -> `"RowlingJK_..."`
3.  **Title Formatting:**
    *   Spaces: `{"title": "A Tale of Two Cities", ...}` -> `"..._A_Tale_of_Two_Cities_..."`
    *   Special Chars: `{"title": "Book: The Sequel? (Part 1/2)", ...}` -> `"..._Book_The_Sequel_Part_12_..."`
    *   Missing: `{"author": "An Author", ...}` -> `"AuthorAn_UntitledBook_..."`
4.  **BookID Formatting:**
    *   Missing: `{"id": null, ...}` -> `"..._UnknownID..."`
    *   Special Chars: `{"id": "ID-123!", ...}` -> `"..._ID123..."`
5.  **Extension Formatting:**
    *   Uppercase: `{"extension": "PDF", ...}` -> `"...pdf"`
    *   Missing: `{...}` -> `"...unknown"`
6.  **Sanitization & Length:**
    *   Long author/title: Test truncation to 50/100 chars.
    *   Overall length > 200: Test title truncation.
    *   All special chars title: `{"title": "!!!", ...}` -> `"..._UntitledBook_..."`
7.  **Edge Cases:**
    *   All fields missing: `{}` -> `"UnknownAuthor_UntitledBook_UnknownID.unknown"`
    *   Author "Æsop" -> "Aesop" (or "sop" depending on final ASCII rule)
### Pseudocode: Python Bridge (`lib/python_bridge.py`) - RAG Markdown Generation Refactor
- Created: 2025-04-29 02:40:07
- Updated: 2025-04-29 02:40:07
```pseudocode
# File: lib/python_bridge.py (Refactored Functions)
# Dependencies: fitz, ebooklib, bs4, logging, re, pathlib

### Pseudocode: Preprocessing Logic (`lib/rag_processing.py`) - `identify_and_remove_front_matter`, `extract_and_format_toc`
- Created: 2025-04-29 23:15:00
```pseudocode
# File: lib/rag_processing.py (Conceptual additions)

# --- Constants for Pattern Matching ---
FRONT_MATTER_KEYWORDS = ["copyright", "dedication", "acknowledgments", "isbn", "published by", ...]
TOC_KEYWORDS = ["contents", "table of contents", ...]

FUNCTION identify_and_remove_front_matter(content_lines: List[str]) -> (List[str], str):
  """Identifies title, removes front matter, returns cleaned content lines and title."""
  cleaned_lines = []
  title = "Unknown Title"
  in_front_matter = True
  potential_title_lines = content_lines[:20] # Heuristic: Title usually near the start

  # --- Title Identification Heuristic ---
  # Look for shortest, non-empty line, possibly all caps, near the beginning.
  # More sophisticated logic needed (e.g., font size if available from PDF dict).
  # title = find_title_heuristic(potential_title_lines)

  # --- Front Matter Removal Heuristic ---
  # Iterate through lines. Look for keywords, page numbers, excessive whitespace.
  # Transition out of front_matter state when likely main content starts (e.g., "Chapter 1", "Introduction", consistent paragraph structure).
  for line in content_lines:
    line_lower = line.strip().lower()
    is_likely_front_matter = False
    if in_front_matter:
       # Check keywords, check for roman numerals often used in front matter page numbers
       if any(keyword in line_lower for keyword in FRONT_MATTER_KEYWORDS):
           is_likely_front_matter = True
       # Add more heuristics (e.g., short lines, centered text patterns)

       # Heuristic to detect start of main content
       if line_lower.startswith("chapter") or line_lower.startswith("part") or line_lower.startswith("introduction"):
            in_front_matter = False

    if not is_likely_front_matter:
      cleaned_lines.append(line)

  # Placeholder implementation - requires significant refinement
  return cleaned_lines, title
END FUNCTION

FUNCTION extract_and_format_toc(content_lines: List[str], output_format: str) -> (List[str], str):
  """Identifies ToC, formats it (if Markdown), returns remaining content lines and formatted ToC."""
  toc_lines = []
  remaining_lines = []
  in_toc = False
  toc_found = False

  # --- ToC Identification Heuristic ---
  # Look for keywords, specific formatting (e.g., lines with text followed by page numbers).
  for line in content_lines:
      line_lower = line.strip().lower()
      if not toc_found and any(keyword in line_lower for keyword in TOC_KEYWORDS):
          in_toc = True
          toc_found = True
          # Potentially skip the "Table of Contents" header itself
          continue

      if in_toc:
          # Heuristic to detect end of ToC (e.g., start of main content, change in formatting)
          if line_lower.startswith("chapter") or line_lower.startswith("part") or line_lower.startswith("introduction"):
              in_toc = False
              remaining_lines.append(line)
          else:
              # Basic check for ToC entry format (text ... number)
              if re.search(r'.+\s+\.?\s*\d+$', line.strip()):
                 toc_lines.append(line.strip())
              else: # Assume end of ToC if format breaks
                  in_toc = False
                  remaining_lines.append(line)
      else:
          remaining_lines.append(line)

  formatted_toc = ""
  if toc_found and output_format == "markdown":
      # --- Markdown Formatting Logic ---
      # Parse toc_lines (extract text and page numbers/links)
      # Create nested list structure based on indentation or numbering
      # Generate Markdown links (#header-slug) - requires header slugs to be generated later
      formatted_toc = format_toc_as_markdown(toc_lines) # Placeholder

  # Placeholder implementation
  return remaining_lines, formatted_toc
END FUNCTION

# --- Integration into process_pdf/process_epub ---
# Before extracting main content or formatting markdown:
# 1. Get initial text lines/structure.
# 2. (cleaned_lines, title) = identify_and_remove_front_matter(initial_lines)
# 3. (final_content_lines, formatted_toc) = extract_and_format_toc(cleaned_lines, output_format)
# 4. Process final_content_lines for main text/markdown generation.
# 5. Prepend title and formatted_toc (if any) to the final output.

```
#### TDD Anchors:
- `test_remove_front_matter_basic`: Verify common copyright/dedication lines are removed.
- `test_remove_front_matter_preserves_title`: Verify the identified title remains (or is returned separately).
- `test_remove_front_matter_handles_no_front_matter`: Verify it works correctly on content without obvious front matter.
- `test_extract_toc_basic`: Verify simple ToC lines are extracted.
- `test_extract_toc_formats_markdown`: Verify extracted ToC is formatted correctly as Markdown list with placeholder links.
- `test_extract_toc_handles_no_toc`: Verify it works correctly when no ToC is found.
- `test_extract_toc_handles_non_standard_toc`: Test robustness against variations.
- `test_integration_pdf_preprocessing`: Verify `process_pdf` calls preprocessing steps and includes Title/ToC in output.
- `test_integration_epub_preprocessing`: Verify `process_epub` calls preprocessing steps and includes Title/ToC in output.
- Related: `docs/rag-robustness-enhancement-spec.md#93-preprocessing-logic-conceptual---to-be-integrated-into-rag_processingpy`

### Pseudocode: Testing Framework (`scripts/run_rag_tests.py`) - AI Evaluation Update
- Updated: 2025-04-29 23:15:00
```pseudocode
# File: scripts/run_rag_tests.py (Updates)

FUNCTION evaluate_output(output_path, format_type, doc_metadata):
  # Load output file content
  content = read_file_content(output_path)

  # Apply quantitative metrics based on format_type (Text: FR-TEST-09, Markdown: FR-TEST-10)
  metrics = {}
  # ... calculate quantitative metrics ...
  metrics['completeness_score'] = calculate_completeness(content, ...)
  metrics['accuracy_score'] = calculate_accuracy(content, ...)
  if format_type == 'text':
    metrics['noise_score'] = score_noise(content, ...)
    metrics['readability_score'] = score_readability(content, ...)
  elif format_type == 'markdown':
    metrics['heading_accuracy'] = calculate_heading_accuracy(content, ...)
    metrics['list_accuracy'] = calculate_list_accuracy(content, ...)
    metrics['footnote_accuracy'] = calculate_footnote_accuracy(content, ...)
    metrics['structure_score'] = score_structure(content, ...)

  # Apply AI Quality Assessment (FR-TEST-11.5)
  ai_assessment = evaluate_quality_with_ai(content, format_type, doc_metadata) # Placeholder call
  metrics['ai_score'] = ai_assessment.get('score')
  metrics['ai_feedback'] = ai_assessment.get('feedback')

  RETURN metrics
END FUNCTION

FUNCTION evaluate_quality_with_ai(content, format_type, doc_metadata):
    """Placeholder: Calls an external AI agent/mode to assess quality."""
    LOG info f"Requesting AI quality assessment for {doc_metadata['id']} ({format_type})"
    # Prepare prompt for AI agent, including content, format, and expected checks
    # prompt = f"Evaluate the following {format_type} content extracted from '{doc_metadata['title']}':\n\n{content}\n\nAssess faithfulness, readability, formatting, noise, front matter removal, and ToC handling. Provide a score (1-5) and detailed feedback."
    # response = call_ai_agent(prompt) # This could be an MCP call or other mechanism
    # Parse response to get score and feedback
    # MOCK IMPLEMENTATION:
    mock_score = random.uniform(3.0, 5.0)
    mock_feedback = "AI assessment placeholder: Looks reasonable." if mock_score > 3.5 else "AI assessment placeholder: Minor formatting issues noted."
    return {'score': mock_score, 'feedback': mock_feedback}
END FUNCTION

FUNCTION determine_pass_fail(results, doc_metadata):
  # Implement logic based on FR-TEST-12, including AI score check
  passed_quantitative = True # Check quantitative metrics against thresholds
  passed_ai = True # Check AI score against threshold (e.g., results['text_metrics'].get('ai_score', 0) >= 3.5)

  # ... detailed checks based on doc type (text, image, etc.) ...

  if passed_quantitative and passed_ai:
      return 'PASS'
  else:
      return 'FAIL'
END FUNCTION
```
#### TDD Anchors:
- `test_evaluate_output_calls_ai`: Mock `evaluate_quality_with_ai`, verify it's called by `evaluate_output`.
- `test_determine_pass_fail_uses_ai_score`: Provide sample results with varying AI scores, verify correct PASS/FAIL based on AI threshold.
- `test_evaluate_quality_with_ai_mock`: Test the placeholder/mock AI call function.
- Related: `docs/rag-robustness-enhancement-spec.md#94-testing-framework-scriptsrun_rag_testspy`
# --- PDF Processing Refactor ---

FUNCTION _analyze_pdf_block(block):
  """Analyzes a PyMuPDF text block to infer structure (heading level, list type)."""
  # Heuristic logic based on font size, flags, position, text patterns
  # Example:
  heading_level = 0
  is_list_item = False
  list_type = None # 'ul' or 'ol'
  list_indent = 0
  text_content = ""
  spans = []

  IF block['type'] == 0: # Text block
    # Aggregate text and span info
    for line in block.get('lines', []):
      for span in line.get('spans', []):
        spans.append(span)
        text_content += span.get('text', '')

    IF spans:
      first_span = spans[0]
      font_size = first_span.get('size', 10)
      flags = first_span.get('flags', 0)
      is_bold = flags & 2

      # Heading heuristic (example)
      IF font_size > 18 OR (font_size > 14 AND is_bold): heading_level = 1
      ELIF font_size > 14 OR (font_size > 12 AND is_bold): heading_level = 2
      ELIF font_size > 12 OR (font_size > 11 AND is_bold): heading_level = 3
      # ... more levels

      # List heuristic (example)
      trimmed_text = text_content.strip()
      IF trimmed_text.startswith(('•', '*', '-')):
        is_list_item = True
        list_type = 'ul'
        # Indentation could be inferred from block['bbox'][0] (x-coordinate)
      ELIF re.match(r"^\d+\.\s+", trimmed_text):
        is_list_item = True
        list_type = 'ol'
      # ... more complex list detection (e.g., a), i.)

  RETURN {
    'heading_level': heading_level,
    'is_list_item': is_list_item,
    'list_type': list_type,
    'list_indent': list_indent, # Placeholder for future use
    'text': text_content.strip(),
    'spans': spans # Pass spans for potential footnote detection
  }
END FUNCTION

FUNCTION _format_pdf_markdown(page):
  """Generates Markdown string from a PyMuPDF page object."""
  blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
  markdown_lines = []
  footnote_defs = {} # Store footnote definitions [^id]: content
  current_list_type = None
  list_level = 0 # Basic nesting tracker

  FOR block in blocks:
    analysis = _analyze_pdf_block(block)
    text = analysis['text']
    spans = analysis['spans']

    IF NOT text: CONTINUE

    # Footnote Reference/Definition Detection (using superscript flag)
    processed_text_parts = []
    potential_def_id = None
    first_span_in_block = True
    for span in spans:
        span_text = span.get('text', '')
        flags = span.get('flags', 0)
        is_superscript = flags & 1

        IF is_superscript AND span_text.isdigit():
            fn_id = span_text
            # Definition heuristic: superscript at start of block
            IF first_span_in_block:
                potential_def_id = fn_id
            ELSE: # Reference
                processed_text_parts.append(f"[^{fn_id}]")
        ELSE:
            processed_text_parts.append(span_text)
        first_span_in_block = False

    processed_text = "".join(processed_text_parts).strip()

    # Store definition if found
    IF potential_def_id:
        footnote_defs[potential_def_id] = processed_text # Text after the superscript number
        CONTINUE # Don't add definition block as regular content

    # Format based on analysis
    IF analysis['heading_level'] > 0:
      markdown_lines.append(f"{'#' * analysis['heading_level']} {processed_text}")
      current_list_type = None # Reset list context after heading
    ELIF analysis['is_list_item']:
      # Basic list handling (needs refinement for nesting based on indent)
      IF analysis['list_type'] == 'ul':
        markdown_lines.append(f"* {processed_text}")
      ELIF analysis['list_type'] == 'ol':
        markdown_lines.append(f"1. {processed_text}") # Simple numbering, needs context for correct sequence
      current_list_type = analysis['list_type']
    ELSE: # Regular paragraph
      markdown_lines.append(processed_text)
      current_list_type = None # Reset list context

  # Append footnote definitions
  FOR fn_id, fn_text in sorted(footnote_defs.items()):
      markdown_lines.append(f"\n[^{fn_id}]: {fn_text}")

  RETURN "\n\n".join(markdown_lines)
END FUNCTION

FUNCTION _process_pdf(file_path_str: str, output_format: str = 'text') -> str:
    # ... (initial checks: file exists, import fitz) ...
    doc = None
    TRY
        doc = fitz.open(file_path_str)
        IF doc.is_encrypted: RAISE ValueError("PDF is encrypted")

        all_content = []
        FOR page_num in range(len(doc)):
            page = doc.load_page(page_num)
            IF output_format == 'markdown':
                page_content = _format_pdf_markdown(page)
            ELSE: # Default to text
                page_content = page.get_text("text")
                # Apply text cleaning (null chars, headers/footers - reuse existing logic)
                page_content = page_content.replace('\x00', '')
                # ... other cleaning regex ...
                page_content = page_content.strip()

            IF page_content:
                all_content.append(page_content)

        full_content = "\n\n".join(all_content).strip()
        IF NOT full_content: RAISE ValueError("PDF contains no extractable content")
        RETURN full_content
    # ... (exception handling: FitzError, generic) ...
    FINALLY
        IF doc: doc.close()
    ENDTRY
END FUNCTION


# --- EPUB Processing Refactor ---

FUNCTION _epub_node_to_markdown(node, footnote_defs):
  """Recursively converts BeautifulSoup node to Markdown string."""
  markdown_parts = []
  IF node.name == 'h1': prefix = '# '
  ELIF node.name == 'h2': prefix = '## '
  # ... h3-h6 ...
  ELIF node.name == 'p': prefix = ''
  ELIF node.name == 'ul':
      # Handle UL items recursively
      for child in node.find_all('li', recursive=False):
          item_text = _epub_node_to_markdown(child, footnote_defs).strip()
          if item_text: markdown_parts.append(f"* {item_text}")
      return "\n".join(markdown_parts) # Return joined list items
  ELIF node.name == 'ol':
      # Handle OL items recursively
      for i, child in enumerate(node.find_all('li', recursive=False)):
          item_text = _epub_node_to_markdown(child, footnote_defs).strip()
          if item_text: markdown_parts.append(f"{i+1}. {item_text}")
      return "\n".join(markdown_parts) # Return joined list items
  ELIF node.name == 'li':
      # Process content within LI, ignore prefix
      prefix = ''
  ELIF node.name == 'blockquote': prefix = '> '
  ELIF node.name == 'pre':
      # Handle code blocks
      code_content = node.get_text()
      return f"```\n{code_content}\n```"
  ELIF node.name == 'a' AND node.get('epub:type') == 'noteref':
      # Handle footnote reference
      ref_id = node.get_text(strip=True) or re.search(r'\d+', node.get('href', '')).group(0)
      if ref_id: return f"[^{ref_id}]"
      else: return "" # Ignore if ID not found
  ELIF node.name == 'aside' AND node.get('epub:type') == 'footnote':
      # Store footnote definition and return empty (handled separately)
      fn_id = re.search(r'\d+', node.get('id', '')).group(0)
      fn_text = node.get_text(strip=True)
      if fn_id and fn_text: footnote_defs[fn_id] = fn_text
      return "" # Don't include definition inline
  ELSE:
      # Default: process children or get text
      prefix = ''

  # Process children recursively or get text content
  content_parts = []
  for child in node.children:
      if isinstance(child, str):
          cleaned_text = child.strip()
          if cleaned_text: content_parts.append(cleaned_text)
      else: # It's another tag
          child_md = _epub_node_to_markdown(child, footnote_defs)
          if child_md: content_parts.append(child_md)

  full_content = " ".join(content_parts).strip() # Join parts with space

  # Apply prefix if content exists
  if full_content:
      # Handle blockquotes needing prefix on each line
      if prefix == '> ':
          return '> ' + full_content.replace('\n', '\n> ')
      else:
          return prefix + full_content
  else:
      return ""

END FUNCTION

FUNCTION _process_epub(file_path_str: str, output_format: str = 'text') -> str:
    # ... (initial checks: file exists, import ebooklib/bs4) ...
    book = epub.read_epub(file_path_str)
    all_content = []
    footnote_defs = {} # Collect across all items

    items = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    FOR item in items:
        html_content = item.get_content().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html_content, 'lxml')

        IF output_format == 'markdown':
            item_md_parts = []
            # Process body content, collecting footnote defs
            if soup.body:
                for element in soup.body.children: # Iterate direct children
                     md_part = _epub_node_to_markdown(element, footnote_defs)
                     if md_part: item_md_parts.append(md_part)
            item_markdown = "\n\n".join(item_md_parts)
            if item_markdown: all_content.append(item_markdown)
        ELSE: # Plain text
            text = soup.get_text(strip=True)
            if text: all_content.append(text)

    # Append collected footnote definitions for Markdown
    if output_format == 'markdown' and footnote_defs:
        fn_section = ["\n\n---"] # Separator
        for fn_id, fn_text in sorted(footnote_defs.items()):
            fn_section.append(f"[^{fn_id}]: {fn_text}")
        all_content.append("\n".join(fn_section))

    full_content = "\n\n".join(all_content).strip()
    IF NOT full_content: RAISE ValueError("EPUB contains no extractable content")
    RETURN full_content
    # ... (exception handling) ...
END FUNCTION

# --- Main Function Update ---
# Ensure the `main` function passes `output_format` (defaulting to 'text' if not provided by Node.js)
# to `process_document`. The `process_document` function already passes it to `_process_pdf`.
# The `_process_epub` function also needs the `output_format` parameter added.

# Example modification in main():
# elif function_name == 'process_document':
#     file_path = args_dict.get('file_path')
#     output_format = args_dict.get('output_format', 'text') # Get format or default
#     if not file_path: raise ValueError("Missing 'file_path'")
#     response = await process_document(file_path, output_format) # Pass format
```
#### TDD Anchors:
**PDF (`_process_pdf` / `_format_pdf_markdown`):**
- `test_pdf_heading_level_1`: Verify large font size maps to `# Heading`.
- `test_pdf_heading_level_2`: Verify medium-large font size maps to `## Heading`.
- `test_pdf_heading_level_3`: Verify medium font size maps to `### Heading`.
- `test_pdf_paragraph`: Verify normal font size maps to plain paragraph text.
- `test_pdf_unordered_list`: Verify blocks starting with `*`/`•`/`-` map to `* List item`.
- `test_pdf_ordered_list`: Verify blocks starting with `1.` map to `1. List item`.
- `test_pdf_footnote_reference`: Verify inline superscript number maps to `[^1]`.
- `test_pdf_footnote_definition`: Verify block starting with superscript number stores definition `[^1]: Footnote text`.
- `test_pdf_multiple_footnotes`: Verify multiple references and definitions are handled correctly and appended.
- `test_pdf_no_text`: Verify `ValueError` raised if no text extracted.
- `test_pdf_encrypted`: Verify `ValueError` raised for encrypted PDF.
- `test_pdf_output_format_text`: Verify plain text output when `output_format='text'`.
- `test_pdf_output_format_markdown`: Verify Markdown output when `output_format='markdown'`.

**EPUB (`_process_epub` / `_epub_node_to_markdown`):**
- `test_epub_heading_tags`: Verify `<h1>` to `<h6>` map to `#` to `######`.
- `test_epub_paragraph_tag`: Verify `<p>` maps to plain paragraph text.
- `test_epub_unordered_list`: Verify `<ul><li>Item</li></ul>` maps to `* Item`.
- `test_epub_ordered_list`: Verify `<ol><li>Item</li></ol>` maps to `1. Item`.
- `test_epub_nested_lists`: Verify nested `ul`/`ol` are formatted correctly with indentation (Note: pseudocode needs refinement for indent).
- `test_epub_blockquote`: Verify `<blockquote>` maps to `> Quote`.
- `test_epub_code_block`: Verify `<pre><code>` maps to fenced code block.
- `test_epub_footnote_reference`: Verify `<a epub:type="noteref">` maps to `[^1]`.
- `test_epub_footnote_definition`: Verify `<aside epub:type="footnote">` stores definition and is appended correctly.
- `test_epub_multiple_footnotes`: Verify multiple references and definitions are handled.
- `test_epub_no_content`: Verify `ValueError` raised if no content extracted.
- `test_epub_output_format_text`: Verify plain text output when `output_format='text'`.
- `test_epub_output_format_markdown`: Verify Markdown output when `output_format='markdown'`.

# Specification Writer Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
## Functional Requirements
### Feature: RAG Output Quality Evaluation Criteria
- Added: 2025-04-29 01:34:12
- Description: Defined measurable quality criteria for evaluating Markdown and Text output from the `process_document_for_rag` tool (EPUB/PDF sources) to ensure suitability for RAG ingestion. Covers structure preservation, content fidelity, reference handling, and RAG-specific suitability (chunking, metadata, images). Includes TDD anchors for future automated testing.
- Acceptance criteria: 1. Specification document `docs/rag-output-quality-spec.md` exists. 2. Document covers criteria for both Markdown and Text outputs. 3. Document includes TDD anchors. 4. Criteria are clear and measurable for QA testing.
- Dependencies: `process_document_for_rag` tool implementation (`lib/python_bridge.py` using `ebooklib`, `PyMuPDF`).
- Status: Draft (Specification Complete)
- Related: `docs/rag-output-quality-spec.md`
### Feature: RAG Document Processing Pipeline (v2 - File Output)
- Added: 2025-04-23 23:37:09
- Description: Update the RAG pipeline to save processed text (EPUB, TXT, PDF) to `./processed_rag_output/` and return the `processed_file_path` instead of raw text. **Clarifies the `download_book_to_file` workflow per ADR-002 (input `bookDetails` from search, internal scraping).** Involves updating `download_book_to_file` and `process_document_for_rag` tools (schemas, Node handlers), and Python bridge (`download_book` handles scraping, `process_document` orchestrates extraction and saving via `_save_processed_text` helper).
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


### Edge Case: Preprocessing - Non-standard Front Matter
- Identified: 2025-04-29 23:15:00
- Scenario: Document lacks common front matter keywords or structure.
- Expected behavior: Preprocessing step identifies nothing to remove, proceeds gracefully without error.
- Testing approach: Include documents with minimal/no front matter in test corpus.
- Related: `docs/rag-robustness-enhancement-spec.md#8-edge-cases` (EC-PREPROC-01)

### Edge Case: Preprocessing - Unusual ToC Format
- Identified: 2025-04-29 23:15:00
- Scenario: Table of Contents is embedded within main text, uses non-standard formatting, or is missing page numbers/links.
- Expected behavior: ToC extraction may fail or be incomplete. Should log a warning but not halt processing. Markdown formatting might be absent or incorrect.
- Testing approach: Include documents with diverse ToC formats in test corpus. Verify graceful failure and logging.
- Related: `docs/rag-robustness-enhancement-spec.md#8-edge-cases` (EC-PREPROC-02)

### Edge Case: Preprocessing - Valuable Front Matter
- Identified: 2025-04-29 23:15:00
- Scenario: Front matter sections like Preface or Introduction contain content relevant for RAG.
- Expected behavior: Current heuristics might incorrectly remove valuable content. Requires careful tuning of removal logic or potential configuration options to preserve specific sections.
- Testing approach: Manually review processed output for key documents where valuable front matter is expected. Compare against original.
- Related: `docs/rag-robustness-enhancement-spec.md#8-edge-cases` (EC-PREPROC-03)

### Edge Case: Preprocessing - Ambiguous/Missing Title
- Identified: 2025-04-29 23:15:00
- Scenario: Document lacks a clear title page or has multiple potential titles.
- Expected behavior: Title identification heuristic may fail or select an incorrect title. Should use a placeholder (e.g., "Unknown Title") or the filename as fallback.
- Testing approach: Include documents with missing or ambiguous titles in test corpus. Verify fallback behavior.
- Related: `docs/rag-robustness-enhancement-spec.md#8-edge-cases` (EC-PREPROC-04)
<!-- Append new constraints using the format below -->
### Constraint: Search-First Strategy Reliability
### Constraint: Test Document Storage
- Added: 2025-04-29 19:54:15
- Description: Due to size/copyright, the main test corpus will be a metadata manifest; documents downloaded on-demand. Only a small subset of public domain/anonymized samples stored locally.
- Impact: Testing requires network access and depends on `download_book_to_file` functioning. Local tests limited.
- Mitigation strategy: Use manifest file. Ensure download tool is stable. Select diverse local samples carefully.
- Related: `docs/rag-robustness-enhancement-spec.md#22-test-document-storage--management`

### Constraint: OCR System Dependency
- Added: 2025-04-29 19:54:15
- Description: OCR engines (e.g., Tesseract) require system-level installation by the user, which cannot be fully automated by the MCP server.
- Impact: OCR functionality will fail if the dependency is not met. Adds setup complexity for users.
- Mitigation strategy: Provide clear documentation and installation instructions. Implement checks and informative error messages if the OCR engine is not found.
- Related: `docs/rag-robustness-enhancement-spec.md#33-preprocessing--ocr-integration`

### Constraint: OCR Performance
- Added: 2025-04-29 19:54:15
- Description: OCR is computationally expensive and can significantly increase document processing time compared to direct text extraction.
- Impact: May affect user experience for large documents or batch processing. Requires resource consideration.
- Mitigation strategy: Trigger OCR conditionally based on quality detection. Log processing times. Inform user about potential delays. Optimize preprocessing if possible.
- Related: `docs/rag-robustness-enhancement-spec.md#5-non-functional-requirements`

### Constraint: Library Licenses
- Added: 2025-04-29 19:54:15
- Description: Must adhere to licenses of all libraries (e.g., PyMuPDF: AGPL, Tesseract: Apache 2.0).
- Impact: Requires license compliance checks and awareness. AGPL for PyMuPDF is acceptable for server-side use but notable.
- Mitigation strategy: Document licenses. Ensure usage complies with terms.
- Related: `docs/rag-robustness-enhancement-spec.md#6-constraints--assumptions`
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
### Edge Case: PDF - Encrypted/Password
- Identified: 2025-04-29 19:54:15
- Scenario: Processing an encrypted PDF.
- Expected behavior: `process_pdf` raises `ValueError`. Error propagated to user.
- Testing approach: Test with an encrypted PDF. Verify `ValueError`.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-PDF-01)

### Edge Case: PDF - Corrupted/Malformed
- Identified: 2025-04-29 19:54:15
- Scenario: Processing a corrupted PDF file.
- Expected behavior: `fitz` raises error, `process_pdf` catches and raises `RuntimeError`. Error propagated.
- Testing approach: Test with a known corrupted PDF. Verify `RuntimeError`.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-PDF-02)

### Edge Case: PDF - Image Only
- Identified: 2025-04-29 19:54:15
- Scenario: Processing a PDF containing only images.
- Expected behavior: `detect_pdf_quality` returns "IMAGE_ONLY". OCR is triggered. If OCR fails, empty text is returned/saved (resulting in `processed_file_path: None`).
- Testing approach: Test with an image-only PDF. Verify quality detection, OCR trigger, and final output (OCR text or None).
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-PDF-03)

### Edge Case: PDF - Mixed Text/Image
- Identified: 2025-04-29 19:54:15
- Scenario: Processing a PDF with both text layers and large images.
- Expected behavior: `detect_pdf_quality` returns "MIXED". Hybrid processing attempts PyMuPDF first, potentially triggers OCR as fallback based on yield.
- Testing approach: Test with a mixed PDF. Verify quality detection and processing path.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-PDF-04)

### Edge Case: PDF - Garbled Text/Encoding
- Identified: 2025-04-29 19:54:15
- Scenario: PDF text layer exists but is garbled due to font/encoding issues.
- Expected behavior: `detect_pdf_quality` potentially returns "TEXT_LOW". OCR is triggered.
- Testing approach: Test with a PDF known to have encoding issues. Verify quality detection and OCR trigger.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-PDF-05)

### Edge Case: PDF - Large File Memory
- Identified: 2025-04-29 19:54:15
- Scenario: Processing an extremely large PDF causing memory exhaustion.
- Expected behavior: Process may fail with `MemoryError`. Needs graceful handling and logging.
- Testing approach: Test with a very large PDF. Monitor memory usage. Verify error handling if failure occurs.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-PDF-06)

### Edge Case: EPUB - Corrupted/Malformed
- Identified: 2025-04-29 19:54:15
- Scenario: Processing a corrupted EPUB file.
- Expected behavior: `ebooklib` raises error, caught as `RuntimeError`. Error propagated.
- Testing approach: Test with a known corrupted EPUB. Verify `RuntimeError`.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-EPUB-01)

### Edge Case: EPUB - Complex/Non-standard HTML
- Identified: 2025-04-29 19:54:15
- Scenario: EPUB uses unusual HTML structures not handled by `_epub_node_to_markdown`.
- Expected behavior: Markdown output may be incomplete or incorrectly formatted. Warnings logged.
- Testing approach: Test with EPUBs containing complex tables, nested elements, non-standard tags. Review output quality.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-EPUB-02)

### Edge Case: EPUB - DRM
- Identified: 2025-04-29 19:54:15
- Scenario: Processing an EPUB with Digital Rights Management.
- Expected behavior: `ebooklib` likely raises error, caught as `RuntimeError`. Error propagated.
- Testing approach: Test with a DRM-protected EPUB (if legally possible). Verify `RuntimeError`.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-EPUB-03)

### Edge Case: OCR - Engine Not Found
- Identified: 2025-04-29 19:54:15
- Scenario: OCR is triggered, but the engine (e.g., Tesseract) is not installed or not in PATH.
- Expected behavior: `run_ocr_on_pdf` raises `RuntimeError` or specific error. Error logged, fallback to PyMuPDF attempted if applicable.
- Testing approach: Uninstall/rename Tesseract executable. Trigger OCR. Verify error handling and fallback.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-OCR-01)

### Edge Case: OCR - Processing Failure/Timeout
- Identified: 2025-04-29 19:54:15
- Scenario: OCR engine starts but fails internally or times out on a specific page/document.
- Expected behavior: Error logged by `run_ocr_on_pdf`. Fallback to PyMuPDF attempted if applicable. Partial results may be returned.
- Testing approach: Induce OCR failure (e.g., corrupted image input, low timeout). Verify logging and fallback.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-OCR-02)

### Edge Case: OCR - Nonsensical Output
- Identified: 2025-04-29 19:54:15
- Scenario: OCR runs but produces garbage text due to poor input quality or language mismatch.
- Expected behavior: Output saved, but quality metrics will be very low. May require manual review flag.
- Testing approach: Test with very low-quality scans or documents in unsupported languages. Review output and metrics.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-OCR-03)

### Edge Case: File System - Disk Full / Permissions
- Identified: 2025-04-29 19:54:15
- Scenario: Attempting to save processed file or temporary OCR images fails due to disk space or permissions.
- Expected behavior: `_save_processed_text` raises `FileSaveError`. OCR may fail with `OSError`. Errors propagated.
- Testing approach: Simulate disk full or permission denied errors (e.g., using filesystem mocks or restricted test environment). Verify error propagation.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-FS-01)

### Edge Case: Language Mismatch (OCR)
- Identified: 2025-04-29 19:54:15
- Scenario: Document language differs significantly from the language specified for OCR.
- Expected behavior: OCR output quality will be very poor.
- Testing approach: Test with documents in different languages, specifying incorrect language to OCR. Evaluate output quality.
- Related: `docs/rag-robustness-enhancement-spec.md#7-edge-cases` (EC-Lang-01)
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

### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `download_book` (Updated for Download Workflow)
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-24 17:33:32
```python
# File: lib/python_bridge.py (Updated Core Function)
# Dependencies: zlibrary, os, logging, pathlib, asyncio
# Assumes process_document is defined and handles saving
# Assumes _scrape_and_download helper is defined

import os
import logging
import asyncio
from pathlib import Path
# from zlibrary import ZLibrary # ZLibrary instance not needed directly if scraping

# Custom Exceptions assumed defined: DownloadScrapeError, DownloadExecutionError, FileSaveError

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
### Pseudocode: Python Bridge (`lib/python_bridge.py`) - `_scrape_and_download` (New Helper)
- Created: 2025-04-24 17:33:32
- Updated: 2025-04-24 17:33:32
```python
# File: lib/python_bridge.py (New Helper Function)
# Dependencies: httpx, aiofiles, bs4, logging, asyncio, urllib.parse, re

import httpx
import aiofiles
import logging
import asyncio
import re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Assumed defined: DOWNLOAD_SELECTOR, DownloadScrapeError, DownloadExecutionError

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
```
#### TDD Anchors:
- Test raises `ImportError` if `httpx`/`aiofiles` missing.
- Mock `httpx.AsyncClient.get` for book page fetch. Test successful fetch.
- Test book page fetch failure (network error) raises `DownloadScrapeError`.
- Test book page fetch failure (HTTP status error) raises `DownloadScrapeError`.
- Mock `BeautifulSoup` parsing. Test successful selection of download link (`a.btn.btn-primary.dlButton`) and extraction of `href`.
- Test parsing failure (selector not found) raises `DownloadScrapeError`.
- Test unexpected parsing error raises `DownloadScrapeError`.
- Mock `httpx.AsyncClient.stream` for final download. Test successful download writes file and returns correct path.
- Test filename extraction logic (Content-Disposition, URL fallback).
- Test final download failure (network error) raises `DownloadExecutionError`.
- Test final download failure (HTTP status error) raises `DownloadExecutionError`.
- Test file saving failure (OS error) raises `DownloadExecutionError`.


            result["processed_file_path"] = None # Indicate processing failure

    return result
```
#### TDD Anchors:
- Test raises `ValueError` if `book_details['url']` is missing.
- Test successful extraction of URL from `book_details`.
- Mock `_scrape_and_download`. Test it's called with correct URL and output dir.
- Test successful return from `_scrape_and_download` results in correct `file_path`.
- Test `DownloadScrapeError` or `DownloadExecutionError` from `_scrape_and_download` raises `RuntimeError`.
- Test `process_for_rag=True` calls `process_document` with the downloaded path.
- Test `process_for_rag=True` (Successful Processing) -> Returns `file_path` and `processed_file_path` (string path).
- Test `process_for_rag=True` (Processing Fails/No Text) -> Returns `file_path` and `processed_file_path: None`.

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

### Pseudocode: Tool Schemas (Zod) - Updated for File Output & Download Workflow
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-24 17:33:32
```typescript
// File: src/lib/schemas.ts (or inline in index.ts)
import { z } from 'zod';

// Updated Input for download_book_to_file
export const DownloadBookToFileInputSchema = z.object({
  // Changed from 'id' to 'bookDetails' to align with ADR-002
  bookDetails: z.object({}).passthrough().describe("The full book details object obtained from a search_books result, containing the necessary book page URL under the 'url' key."),
  // 'format' removed as it's determined internally during scraping/download
  outputDir: z.string().optional().default("./downloads").describe("Directory to save the original file (default: './downloads')"),
  process_for_rag: z.boolean().optional().default(false).describe("If true, process content for RAG and save to processed output file"),
  processed_output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')")
});

// Updated Output for download_book_to_file
export const DownloadBookToFileOutputSchema = z.object({
    file_path: z.string().describe("The absolute path to the original downloaded file"),
    processed_file_path: z.string().optional().nullable().describe("The absolute path to the file containing processed text (if process_for_rag was true and text was extracted), or null otherwise.") // Updated field, allow null
});

// Updated Input for process_document_for_rag
export const ProcessDocumentForRagInputSchema = z.object({
  file_path: z.string().describe("The absolute path to the document file to process"),
  output_format: z.string().optional().default("txt").describe("Desired format for the processed output file (default: 'txt')")
});

// Updated Output for process_document_for_rag
export const ProcessDocumentForRagOutputSchema = z.object({
  // Allow null if processing yields no text (e.g., image PDF)
  processed_file_path: z.string().nullable().describe("The absolute path to the file containing extracted and processed plain text content, or null if no text was extracted.")
});
```
#### TDD Anchors:
- Verify `DownloadBookToFileInputSchema` requires `bookDetails` object, accepts optional `outputDir`, `process_for_rag`, `processed_output_format`.
- Verify `DownloadBookToFileOutputSchema` includes `file_path` and optional `processed_file_path` (nullable).
- Verify `ProcessDocumentForRagInputSchema` requires `file_path`, accepts optional `output_format`.
- Verify `ProcessDocumentForRagOutputSchema` requires `processed_file_path` (nullable).

### Pseudocode: Tool Registration (`index.ts` Snippet) - Updated for File Output & Download Workflow
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-24 17:33:32
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
#### TDD Anchors:
- Test `tools/list` includes updated descriptions/schemas for `download_book_to_file`.
- Test `tools/call` routes `download_book_to_file` correctly.
- Test input validation using updated `DownloadBookToFileInputSchema`.

### Pseudocode: Node.js Handlers (`lib/zlibrary-api.ts`) - Updated for File Output & Download Workflow
- Created: 2025-04-14 12:13:00
- Updated: 2025-04-24 17:33:32
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
#### TDD Anchors:
- `downloadBookToFile`: Mock `callPythonFunction`. Test `bookDetails` object passed correctly. Test handling of responses with/without `processed_file_path` (including null). Test error handling (missing paths, Python errors).
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

