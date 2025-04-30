# RAG Robustness Enhancement Specification

**Version:** 1.0
**Date:** 2025-04-29
**Author:** Specification Writer (AI Mode)

## 1. Introduction

This document outlines the functional requirements, constraints, edge cases, and implementation details for enhancing the robustness of the Retrieval-Augmented Generation (RAG) document processing pipeline within the `zlibrary-mcp` project. The primary goal is to improve the reliability and quality of text extraction and processing, particularly for real-world PDF and EPUB documents obtained from sources like Z-Library, with an initial focus on philosophy texts.

This specification builds upon existing work documented in:
*   `docs/rag-pipeline-implementation-spec.md` (v2.1)
*   `docs/rag-output-quality-spec.md` (v1.0)
*   `docs/pdf-processing-implementation-spec.md` (v2.0)
*   `docs/rag-output-qa-report-rerun-20250429.md` (QA Feedback)

## 2. Real-World Testing Strategy

### 2.1. Test Document Selection

*   **FR-TEST-01:** A curated test set of at least 20-30 documents shall be selected from Z-Library.
*   **FR-TEST-02:** The test set shall primarily focus on philosophy texts known for complex formatting, footnotes, and potentially older scans.
*   **FR-TEST-03:** The test set shall include a diverse range of formats (PDF, EPUB) and PDF types (text-based, image-based/scanned, mixed).
*   **FR-TEST-04:** The test set shall include documents from other genres (e.g., technical manuals, fiction) to ensure generalizability.
*   **FR-TEST-05:** Metadata for each selected document (Z-Library ID, Title, Author, Format, Source URL, brief description of expected challenges) shall be recorded.

### 2.2. Test Document Storage & Management

*   **FR-TEST-06:** A dedicated directory (e.g., `test_files/rag_corpus/`) shall be created to manage test assets.
*   **Constraint-Storage-01:** Due to potential size and copyright concerns, the primary test corpus may consist of metadata (IDs, URLs) stored in a manifest file (e.g., `test_files/rag_corpus/manifest.json`). Test documents will be downloaded on-the-fly during testing using the `download_book_to_file` tool (with `process_for_rag=false`).
*   **Constraint-Storage-02:** A small, representative subset of documents (max 5-10, anonymized or confirmed public domain if possible) may be stored directly in the repository (`test_files/rag_corpus/samples/`) for basic unit/integration tests, provided they meet size and license constraints.
*   **FR-TEST-07:** The manifest file shall track document ID, format, source URL, expected challenges, and link to any locally stored sample.

### 2.3. Testing Methodology & Metrics

*   **FR-TEST-08:** A testing framework/script shall be developed to automate the process: download (if needed), process (`process_document_for_rag` for both 'text' and 'markdown'), and evaluate outputs.
*   **FR-TEST-09:** **Text Extraction Quality Metrics:**
    *   **Completeness:** Estimated percentage of core text successfully extracted (manual sampling/comparison). Target: >95% for text-based PDFs/EPUBs.
    *   **Accuracy:** Character/Word Error Rate (CER/WER) on selected samples compared to ground truth (if available). Target: <5% CER for text-based.
    *   **Noise Level (Text Output):** Qualitative score (1-5, 1=Low, 5=High) assessing presence of headers/footers, artifacts. Target: <= 2.
    *   **Readability (Text Output):** Qualitative score (1-5, 1=Poor, 5=Excellent) assessing paragraph breaks and text flow. Target: >= 4.
*   **FR-TEST-10:** **Markdown Structure Quality Metrics (Referencing `rag-output-quality-spec.md`):**
    *   **Heading Accuracy:** % correct level mapping. Target: >80%.
    *   **List Accuracy:** % lists correctly identified and formatted (ordered/unordered). Target: >85%.
    *   **Footnote Accuracy:** % footnotes captured and correctly formatted (ref + def). Target: >90%.
    *   **Overall Structure Score:** Qualitative score (1-5). Target: >= 3.5.
*   **FR-TEST-11:** **RAG Output Quality Metrics (Post-Processing):**
    *   *Initial Focus:* Evaluate the *processed* text/markdown quality itself using the metrics above.
    *   *Future:* Define metrics for evaluating the final RAG output (e.g., answer relevance, hallucination rate) using the processed documents, but this is out of scope for the *initial* robustness enhancement.
*   **FR-TEST-12:** **Pass/Fail Criteria:**
    *   **Text-based PDF/EPUB:** Must meet target metrics for Completeness, Accuracy, Noise, Readability, and Markdown structure (if applicable).
    *   **Image-based/Low-Quality PDF:** Must be correctly identified by the Quality Detection mechanism (FR-PDF-03). If OCR is applied, OCR output quality will be assessed (e.g., >70% Completeness, <20% CER target).
    *   **Overall:** >80% of the test corpus documents must pass their respective criteria.

### 2.4. Results Documentation

*   **FR-TEST-13:** Test results shall be stored in a structured format (e.g., JSON, CSV, Markdown report) within a dedicated output directory (e.g., `test_results/rag_robustness/`).
*   **FR-TEST-14:** Reports shall include per-document metrics, pass/fail status, qualitative scores, and specific examples of failures or significant quality issues.
*   **FR-TEST-15:** Comparison reports shall be generated to track improvements across different versions or library comparisons.

## 3. PDF Quality Analysis & Improvement

### 3.1. PyMuPDF Investigation

*   **FR-PDF-01:** Document the current understanding of `PyMuPDF`'s text extraction mechanism (`page.get_text("text")`, `page.get_text("dict")`) based on its documentation and observed behavior. Confirm it primarily relies on the PDF's text layer.
*   **FR-PDF-02:** Analyze and document `PyMuPDF`'s limitations observed during initial testing with the real-world corpus, focusing on:
    *   Handling of scanned documents (image-based PDFs).
    *   Extraction from complex layouts (multi-column, tables).
    *   Preservation of formatting (paragraph breaks, lists).
    *   Extraction of text near images or graphical elements.
    *   Handling of unusual fonts or encodings.

### 3.2. PDF Quality Detection

*   **FR-PDF-03:** Implement a module/function `detect_pdf_quality(pdf_document: fitz.Document)` within `lib/rag_processing.py` to automatically assess the likely quality and type of a PDF.
*   **FR-PDF-04:** The quality detection shall categorize PDFs into at least: `TEXT_HIGH`, `TEXT_LOW`, `IMAGE_ONLY`, `MIXED`.
*   **FR-PDF-05:** Potential detection metrics/heuristics to implement:
    *   **Text Density:** Analyze the amount and distribution of text returned by `page.get_text()`. Low density might indicate scanned pages.
    *   **Image Presence/Size:** Use `page.get_images()` to detect presence and relative area of images. Large images covering most of the page suggest scanned content.
    *   **Font Information:** Use `page.get_fonts()` to check for embedded fonts. Absence might indicate scanned content.
    *   **(Optional) Character Confidence:** If an initial OCR pass is considered, use its character confidence scores. Low average confidence suggests poor quality.
    *   **(Optional) Keyword Analysis:** Check for common OCR errors or garbled text patterns.
*   **FR-PDF-06:** The detection logic shall be configurable and return a clear quality category.

### 3.3. Preprocessing & OCR Integration

*   **FR-PDF-07:** Integrate an OCR engine (e.g., Tesseract via `pytesseract`) into the PDF processing workflow.
*   **Constraint-OCR-01:** Tesseract (or chosen alternative) must be installable as a system dependency or managed alongside the Python venv. Installation instructions must be documented.
*   **FR-PDF-08:** Define a workflow in `process_pdf` (or a new orchestrating function) to conditionally apply OCR:
    1. Open PDF with `PyMuPDF`.
    2. Call `detect_pdf_quality`.
    3. If quality is `TEXT_HIGH`, proceed with standard `PyMuPDF` text extraction.
    4. If quality is `IMAGE_ONLY` or `TEXT_LOW`, trigger the OCR process.
    5. If quality is `MIXED`, attempt `PyMuPDF` extraction first, then potentially run OCR on image-heavy pages or if text extraction yield is low.
*   **FR-PDF-09:** Implement optional preprocessing steps before OCR for `IMAGE_ONLY`/`TEXT_LOW` PDFs (e.g., using `Pillow` or `OpenCV` if available):
    *   Convert PDF page/images to suitable image format (e.g., PNG, TIFF).
    *   Image deskewing.
    *   Contrast enhancement.
    *   Binarization.
*   **FR-PDF-10:** The OCR function (`run_ocr_on_pdf(pdf_path)`) shall handle calling the external OCR engine, potentially page by page, and aggregate the resulting text.
*   **FR-PDF-11:** Error handling for OCR failures (engine not found, processing errors) shall be implemented, logging warnings and potentially falling back to PyMuPDF output if any exists.

### 3.4. Alternative PDF Libraries

*   **FR-PDF-12:** Define evaluation criteria for comparing `PyMuPDF` against alternatives like `pdfminer.six`. Criteria include:
    *   Extraction Accuracy (Text-based, Scanned via OCR if applicable).
    *   Structure Preservation (for Markdown output).
    *   Speed/Performance.
    *   Ease of Use / API Complexity.
    *   Dependency Management.
    *   License Compatibility.
*   **FR-PDF-13:** Outline experiments to run the real-world test corpus through `PyMuPDF` and at least one alternative (`pdfminer.six`), comparing results against the defined metrics (FR-TEST-09, FR-TEST-10).
*   **FR-PDF-14:** Document the comparison results and provide a recommendation on whether to switch libraries or use a hybrid approach.

## 4. EPUB Handling Review

*   **FR-EPUB-01:** Review the current `process_epub` and `_epub_node_to_markdown` functions in `lib/rag_processing.py` using the real-world test corpus.
*   **FR-EPUB-02:** Identify and document limitations in handling complex EPUB structures, such as:
    *   Deeply nested lists.
    *   Complex tables (current implementation likely just extracts text).
    *   Embedded images/SVGs (currently ignored).
    *   Non-standard footnote/reference markup.
    *   Unusual HTML tags or attributes affecting structure.
*   **FR-EPUB-03:** Specify enhancements for `_epub_node_to_markdown` to improve handling of identified limitations (e.g., basic table-to-Markdown conversion, image placeholder generation `[Image: src/alt]`, support for more `epub:type` attributes).

## 5. Non-Functional Requirements

*   **NFR-PERF-01:** PDF/EPUB processing time for average-sized books (e.g., 300-500 pages) should remain within acceptable limits (e.g., < 60 seconds without OCR, < 5 minutes with OCR, TBD based on testing).
*   **NFR-ERR-01:** Clear error messages shall be provided for processing failures (e.g., encrypted PDF, corrupted file, OCR failure, unsupported format).
*   **NFR-ERR-02:** Processing failures on one document in a batch should not prevent processing of others (if batch processing is implemented later).
*   **NFR-LOG-01:** Key stages (detection, OCR trigger, library used, success/failure) shall be logged appropriately.
*   **NFR-CONF-01:** OCR usage, preprocessing steps, and potentially quality detection thresholds should be configurable (e.g., via environment variables or a config file).

## 6. Constraints & Assumptions

*   **Constraint-SysDep-01:** OCR engines (like Tesseract) may require system-level installation by the user.
*   **Constraint-LibLic-01:** Adherence to licenses of all used libraries (PyMuPDF: AGPL, Tesseract: Apache 2.0, etc.) is required.
*   **Constraint-Perf-01:** OCR processing can be computationally expensive and significantly increase processing time.
*   **Assumption-Corpus-01:** A diverse and representative corpus of test documents can be acquired from Z-Library or similar sources.
*   **Assumption-OCRQual-01:** OCR will provide usable text for documents where direct text extraction fails, but perfect accuracy is not expected.
*   **Assumption-Structure-01:** Heuristics for PDF structure detection (headings, lists) will be imperfect but provide a reasonable approximation for Markdown generation.

## 7. Edge Cases

*   **EC-PDF-01:** Encrypted/Password-protected PDFs. (Expected: `ValueError`)
*   **EC-PDF-02:** Corrupted/Malformed PDF files. (Expected: `RuntimeError` from `fitz`)
*   **EC-PDF-03:** PDFs containing only images (no text layer). (Expected: Quality detection -> `IMAGE_ONLY`, OCR triggered or empty text returned)
*   **EC-PDF-04:** PDFs with mixed text and images. (Expected: Quality detection -> `MIXED`, hybrid processing)
*   **EC-PDF-05:** PDFs with non-standard fonts or encodings leading to garbled `PyMuPDF` output. (Expected: Quality detection -> `TEXT_LOW`, OCR triggered)
*   **EC-PDF-06:** Extremely large PDF files causing memory issues. (Expected: Potential `MemoryError`, needs graceful handling/logging)
*   **EC-EPUB-01:** Corrupted/Malformed EPUB files. (Expected: `ebooklib` error, caught as `RuntimeError`)
*   **EC-EPUB-02:** EPUBs with non-standard or complex HTML/CSS affecting parsing. (Expected: Potentially incorrect Markdown structure, logged warnings)
*   **EC-EPUB-03:** EPUBs with DRM. (Expected: `ebooklib` error, caught as `RuntimeError`)
*   **EC-OCR-01:** OCR engine not installed or found in PATH. (Expected: `RuntimeError` or specific error during OCR trigger)
*   **EC-OCR-02:** OCR process fails or times out. (Expected: Logged error, potentially fallback to `PyMuPDF` output if available)
*   **EC-OCR-03:** OCR produces nonsensical output for certain pages/documents. (Expected: Poor quality metrics, may require manual review)
*   **EC-FS-01:** Insufficient disk space or permissions to save processed files or temporary OCR images. (Expected: `FileSaveError` or `OSError`)
*   **EC-Lang-01:** Documents in languages not well-supported by OCR engine. (Expected: Poor OCR quality)

## 8. Pseudocode & TDD Anchors

### 8.1. PDF Quality Detection (`lib/rag_processing.py`)

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

**TDD Anchors (Quality Detection):**
*   `test_detect_quality_text_high`: Verify a normal text PDF returns "TEXT_HIGH".
*   `test_detect_quality_image_only`: Verify a scanned PDF (mocked `get_text` empty, `get_images` large, `get_fonts` empty) returns "IMAGE_ONLY".
*   `test_detect_quality_text_low`: Verify a PDF with very little text (mocked `get_text` short) returns "TEXT_LOW".
*   `test_detect_quality_mixed`: Verify a PDF with significant images but also text returns "MIXED".
*   `test_detect_quality_empty_pdf`: Verify an empty PDF (0 pages) returns "EMPTY".

### 8.2. OCR Integration Workflow (`lib/rag_processing.py`)

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

**TDD Anchors (OCR Integration):**
*   `test_process_pdf_triggers_ocr_for_image_only`: Mock `detect_pdf_quality` to return "IMAGE_ONLY", mock `run_ocr_on_pdf` to return text. Verify `run_ocr_on_pdf` is called and its text is returned.
*   `test_process_pdf_triggers_ocr_for_text_low`: Mock `detect_pdf_quality` to return "TEXT_LOW", mock `run_ocr_on_pdf`. Verify `run_ocr_on_pdf` is called.
*   `test_process_pdf_uses_pymupdf_for_text_high`: Mock `detect_pdf_quality` to return "TEXT_HIGH", mock `run_ocr_on_pdf`. Verify `run_ocr_on_pdf` is NOT called and PyMuPDF text is returned.
*   `test_process_pdf_handles_ocr_failure`: Mock `detect_pdf_quality` to return "IMAGE_ONLY", mock `run_ocr_on_pdf` to raise `RuntimeError`. Verify error is logged and empty string is returned.
*   `test_run_ocr_on_pdf_success`: Mock `fitz.open`, `page.get_pixmap`, `pytesseract.image_to_string`. Verify aggregated text is returned.
*   `test_run_ocr_on_pdf_tesseract_not_found`: Mock `pytesseract` call to raise error. Verify `RuntimeError` is raised or handled.

### 8.3. Testing Framework (`scripts/run_rag_tests.py`)

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

**TDD Anchors (Testing Framework):**
*   `test_load_manifest_success`: Verify loading a valid JSON manifest.
*   `test_load_manifest_not_found`: Verify error handling for missing manifest.
*   `test_run_single_test_calls_process`: Mock `call_python_bridge_directly` (or MCP client), verify `process_document` is called for both 'text' and 'markdown'.
*   `test_run_single_test_calls_evaluate`: Mock `evaluate_output`, verify it's called for both formats if processing succeeds.
*   `test_run_single_test_handles_processing_error`: Mock `call_python_bridge_directly` to raise error, verify result status is 'FAIL' with error message.
*   `test_evaluate_output_text_metrics`: Provide sample text output, verify correct calculation/scoring for text metrics.
*   `test_evaluate_output_md_metrics`: Provide sample MD output, verify correct calculation/scoring for MD metrics.
*   `test_determine_pass_fail`: Provide sample results dicts, verify correct 'PASS'/'FAIL' determination based on criteria.

## 9. Definition of Done

The RAG Robustness Enhancement implementation is considered complete when:

1.  The real-world testing strategy (selection, storage, methodology) is documented and approved.
2.  The testing framework script (`scripts/run_rag_tests.py` or similar) is implemented and functional.
3.  PDF Quality Detection (`detect_pdf_quality`) is implemented and integrated into the PDF processing workflow.
4.  OCR integration (`run_ocr_on_pdf`) is implemented, including conditional triggering based on quality detection and basic error handling.
5.  Configurable options for OCR/preprocessing are implemented (NFR-CONF-01).
6.  Enhancements identified for EPUB handling (FR-EPUB-03) are implemented.
7.  All new code includes corresponding unit tests (following TDD principles where applicable).
8.  The automated test suite (`npm test`, `pytest`) passes, including new tests for robustness features.
9.  The RAG robustness testing framework passes with >80% of the defined test corpus meeting the pass criteria (FR-TEST-12).
10. Performance meets defined NFRs (NFR-PERF-01).
11. Documentation (this spec, README, installation notes for OCR) is updated.
12. Code is reviewed, approved, and merged to the main branch.