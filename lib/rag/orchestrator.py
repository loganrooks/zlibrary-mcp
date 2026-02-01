"""
RAG document processing orchestrator.

Contains the main entry points: process_pdf, process_epub, process_txt,
process_document, and save_processed_text. Orchestrates detection, quality
analysis, formatting, and output generation.
"""
import asyncio
import logging
import os
import subprocess
from pathlib import Path

import aiofiles

from lib.rag.utils.constants import SUPPORTED_FORMATS, PROCESSED_OUTPUT_DIR
from lib.rag.utils.exceptions import TesseractNotFoundError, FileSaveError, OCRDependencyError
from lib.rag.utils.text import _slugify
from lib.rag.utils.cache import _clear_textpage_cache
from lib.rag.utils.header import (
    _generate_document_header, _generate_markdown_toc_from_pdf,
    _find_first_content_page,
)
from lib.rag.detection.toc import (
    _extract_toc_from_pdf, _identify_and_remove_front_matter,
    _extract_and_format_toc,
)
from lib.rag.detection.page_numbers import (
    _detect_written_page_on_page, infer_written_page_numbers,
)
from lib.rag.detection.footnotes import (
    _detect_footnotes_in_page, _format_footnotes_markdown,
    _footnote_with_continuation_to_dict,
)
from lib.rag.ocr.spacing import detect_letter_spacing_issue
from lib.rag.quality.analysis import detect_pdf_quality
from lib.rag.quality.pipeline import QualityPipelineConfig
from lib.rag.ocr.recovery import (
    run_ocr_on_pdf, assess_pdf_ocr_quality, redo_ocr_with_tesseract,
)
from lib.rag.xmark.detection import (
    _detect_xmarks_parallel, _page_needs_xmark_detection_fast,
    _should_enable_xmark_detection_for_document,
)
from lib.rag.processors.pdf import _format_pdf_markdown
from lib.rag.processors.epub import process_epub
from lib.rag.processors.txt import process_txt

from lib.footnote_continuation import CrossPageFootnoteParser
from filename_utils import create_unified_filename, create_metadata_filename
from metadata_generator import generate_metadata_sidecar, save_metadata_sidecar
from metadata_verification import (
    extract_pdf_metadata, extract_epub_metadata, extract_txt_metadata,
    verify_metadata,
)

logger = logging.getLogger(__name__)

# OCR Dependencies (Optional)
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None
    Image = None

try:
    import ebooklib
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

# X-mark detection (opencv) - Phase 2.3
try:
    import cv2
    import numpy as np
    XMARK_AVAILABLE = True
except ImportError:
    XMARK_AVAILABLE = False
    cv2 = None
    np = None


def _get_facade():
    """Get facade module for test mockability of optional dependencies."""
    import lib.rag_processing as _rp
    return _rp

__all__ = [
    'process_pdf',
    'process_document',
    'save_processed_text',
]


def process_pdf(
    file_path: Path,
    output_format: str = "txt",
    preserve_linebreaks: bool = False,
    detect_footnotes: bool = False,
    enable_quality_pipeline: bool = True
) -> str:
    """
    Processes a PDF file, extracts text, applies preprocessing, and returns content.

    Args:
        file_path: Path to PDF file
        output_format: Output format ("txt" or "markdown")
        preserve_linebreaks: If True, preserve original line breaks from PDF for citation accuracy.
                           If False, join lines intelligently for readability (default).
        detect_footnotes: If True, detect and format footnotes/endnotes (default: False)
        enable_quality_pipeline: If True, run OCR quality pipeline for sous-rature detection (default: True).
                               Set to False for footnote-only processing to achieve 95% speedup.
                               Footnote detection doesn't require OCR text recovery.

    Returns:
        Processed text content
    """
    # Get optional deps from facade for test mockability
    _rp = _get_facade()
    _fitz = getattr(_rp, 'fitz', fitz)
    _OCR_AVAILABLE = getattr(_rp, 'OCR_AVAILABLE', OCR_AVAILABLE)
    _PYMUPDF_AVAILABLE = getattr(_rp, 'PYMUPDF_AVAILABLE', PYMUPDF_AVAILABLE)
    _XMARK_AVAILABLE = getattr(_rp, 'XMARK_AVAILABLE', XMARK_AVAILABLE)

    # Get commonly-mocked functions from facade for test mockability
    _detect_pdf_quality = getattr(_rp, 'detect_pdf_quality', detect_pdf_quality)
    _run_ocr_on_pdf = getattr(_rp, 'run_ocr_on_pdf', run_ocr_on_pdf)
    _assess_pdf_ocr_quality = getattr(_rp, 'assess_pdf_ocr_quality', assess_pdf_ocr_quality)
    _redo_ocr_with_tesseract = getattr(_rp, 'redo_ocr_with_tesseract', redo_ocr_with_tesseract)
    _identify_fm = getattr(_rp, '_identify_and_remove_front_matter', _identify_and_remove_front_matter)
    _extract_toc_fn = getattr(_rp, '_extract_and_format_toc', _extract_and_format_toc)
    _format_md = getattr(_rp, '_format_pdf_markdown', _format_pdf_markdown)

    if not _PYMUPDF_AVAILABLE: raise ImportError("Required library 'PyMuPDF' (fitz) is not installed.")
    logging.info(f"Processing PDF: {file_path} for format: {output_format}")
    doc = None

    # Phase 2: Load quality pipeline configuration
    if not enable_quality_pipeline:
        # Disable OCR pipeline for 95% speedup (footnote detection doesn't need OCR text recovery)
        quality_config = QualityPipelineConfig(
            enable_pipeline=False,
            detect_strikethrough=False,
            strategy='disabled'
        )
        logging.info("Quality pipeline DISABLED for footnote-only processing (BUG-5 optimization)")
    else:
        quality_config = QualityPipelineConfig.from_env()
        logging.debug(f"Quality pipeline config: enabled={quality_config.enable_pipeline}, "
                     f"strategy={quality_config.strategy}")

    # Phase 2 Optimization: X-mark detection filtering and caching
    # Create page-level cache (detect once per page, not per block)
    xmark_cache = {}

    # Determine if X-mark detection should be enabled for this document
    # Uses metadata (author, subject) - NO text pattern matching
    doc_metadata = {}  # Will be populated from PDF metadata or book_details
    enable_xmark_for_doc = _should_enable_xmark_detection_for_document(doc_metadata)

    # Check if parallel detection is enabled
    parallel_xmark = os.getenv('RAG_PARALLEL_XMARK_DETECTION', 'false').lower() == 'true'
    xmark_workers = int(os.getenv('RAG_XMARK_WORKERS', '4'))

    if not enable_xmark_for_doc:
        logging.info("X-mark detection DISABLED for this document (not philosophy corpus)")
        # Disable strikethrough detection in config for this document
        quality_config.detect_strikethrough = False
    elif parallel_xmark and quality_config.detect_strikethrough and _XMARK_AVAILABLE:
        logging.info(f"X-mark detection ENABLED with PARALLEL mode ({xmark_workers} workers)")
    else:
        logging.info("X-mark detection ENABLED for this document (sequential mode)")

    # Track if we created a temp OCR file (for cleanup)
    temp_ocr_file = None

    try:
        # --- OCR Quality Assessment and Remediation ---
        # Check if PDF needs re-OCRing BEFORE processing
        quality_assessment = _assess_pdf_ocr_quality(file_path)
        logging.info(f"PDF quality assessment: {quality_assessment}")

        if quality_assessment["recommendation"] in ["redo_ocr", "force_ocr"]:
            logging.info(f"Quality score {quality_assessment['score']:.2f} - Re-OCRing PDF for better extraction")
            try:
                # Re-OCR with Tesseract, save to temp directory
                ocr_pdf = _redo_ocr_with_tesseract(file_path)
                temp_ocr_file = ocr_pdf

                # Process the OCR'd version instead of original
                file_path = ocr_pdf
                logging.info(f"Using OCR'd PDF: {ocr_pdf}")

            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as ocr_err:
                logging.warning(f"OCR remediation failed, using original PDF: {ocr_err}")
                # Fall back to original file_path

        # --- Quality Analysis (legacy system - keeping for compatibility) ---
        quality_info = _detect_pdf_quality(str(file_path))
        quality_category = quality_info.get("quality_category", "UNKNOWN")
        ocr_needed = quality_info.get("ocr_recommended", False) # Use correct key 'ocr_recommended'

        # --- OCR (if needed and available) ---
        if ocr_needed:
            if _OCR_AVAILABLE:
                logging.info(f"Quality analysis ({quality_category}) recommends OCR for {file_path}. Running OCR...")
                try:
                    # Cycle 21 Refactor: Use run_ocr_on_pdf which now uses fitz
                    ocr_text = _run_ocr_on_pdf(str(file_path))
                    if ocr_text:
                         logging.info(f"OCR successful for {file_path}.")

                         # DISABLED: Letter spacing correction (now using ocrmypdf re-OCR instead)
                         # ocr_text = correct_letter_spacing(ocr_text)

                         # Preprocess OCR text (basic for now, can be expanded)
                         try: # Add try block for preprocessing OCR text
                             ocr_lines = ocr_text.splitlines()
                             (cleaned_lines, title) = _identify_fm(ocr_lines)
                             (final_content_lines, formatted_toc) = _extract_toc_fn(cleaned_lines, output_format)
                         except Exception as preprocess_err:
                             logging.error(f"Error preprocessing OCR text for {file_path}: {preprocess_err}", exc_info=True)
                             # If preprocessing fails, maybe return raw OCR text or skip?
                             # For now, let's log and proceed to standard extraction by raising the error
                             # to be caught by the outer OCR exception handler.
                             # Re-raise to ensure it's caught by the main handler below
                             raise RuntimeError(f"Error preprocessing OCR text: {preprocess_err}") from preprocess_err

                         # Construct output similar to standard processing
                         final_output_parts = []
                         if title != "Unknown Title":
                             final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
                         if formatted_toc: # Only add ToC if Markdown requested
                             final_output_parts.append(formatted_toc)
                         main_content = "\n".join(final_content_lines)
                         final_output_parts.append(main_content.strip())
                         # Return *inside* the if ocr_text block to prevent fall-through
                         return "\n\n".join(part for part in final_output_parts if part)
                    else:
                         logging.warning(f"OCR run for {file_path} but returned no text. Proceeding with standard extraction.")
                except OCRDependencyError as ocr_dep_err:
                     logging.warning(f"OCR skipped for {file_path}: {ocr_dep_err}")
                     raise ocr_dep_err # Re-raise to prevent fall-through
                except TesseractNotFoundError as tess_err: # Catch specific error instance
                     logging.warning(f"OCR skipped for {file_path}: Tesseract not found or not in PATH.")
                     raise tess_err # Re-raise specific error
                except Exception as ocr_err:
                     logging.error(f"Error during OCR or OCR preprocessing for {file_path}: {ocr_err}", exc_info=True)
                     # Re-raise the original error if it came from preprocessing, otherwise wrap
                     if isinstance(ocr_err, RuntimeError) and "Error preprocessing OCR text" in str(ocr_err):
                         raise ocr_err # Re-raise the specific preprocessing error
                     else:
                         raise RuntimeError(f"OCR or preprocessing failed: {ocr_err}") from ocr_err
            else:
                logging.warning(f"OCR needed for {file_path} ({quality_category}), but dependencies (pytesseract/pdf2image/PIL) are not installed. Skipping OCR.")

        # --- Standard Extraction (if OCR not needed OR if OCR failed during preprocessing) ---
        logging.debug(f"Performing standard PDF extraction for {file_path}...")
        doc = _fitz.open(str(file_path))
        if doc.is_encrypted:
            logging.warning(f"PDF {file_path} is encrypted.")
            if not doc.authenticate(""):
                raise ValueError(f"PDF {file_path} is encrypted and cannot be opened.")
            logging.info(f"Successfully decrypted {file_path} with empty password.")

        # Phase 2: Optimized X-mark detection (if enabled)
        # OPTIMIZATION: Use fast pre-filter to identify pages needing expensive detection
        if enable_xmark_for_doc and quality_config.detect_strikethrough and _XMARK_AVAILABLE:
            # Fast pre-filter: Check all pages for anomalies (~0.01ms per page)
            logging.info(f"Running fast pre-filter on {len(doc)} pages...")
            pages_needing_xmark_check = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()  # Need anyway for processing

                # Fast garbled check (symbol density only, no entropy)
                if _page_needs_xmark_detection_fast(page_text, threshold=0.02):
                    pages_needing_xmark_check.append(page_num)

            logging.info(f"Pre-filter: {len(pages_needing_xmark_check)}/{len(doc)} pages flagged for X-mark detection "
                        f"({len(pages_needing_xmark_check)/len(doc)*100:.1f}%)")

            # Parallel X-mark detection ONLY on flagged pages
            if pages_needing_xmark_check:
                if parallel_xmark:
                    logging.info(f"Starting parallel X-mark detection on {len(pages_needing_xmark_check)} flagged pages "
                                f"with {xmark_workers} workers...")
                    xmark_cache = _detect_xmarks_parallel(file_path, len(doc), max_workers=xmark_workers,
                                                         pages_to_check=pages_needing_xmark_check)
                else:
                    logging.info(f"Sequential X-mark detection on {len(pages_needing_xmark_check)} flagged pages...")
                    xmark_cache = {}  # Will populate on-demand during processing

                logging.info(f"X-mark detection complete: {sum(1 for r in xmark_cache.values() if r and r.has_xmarks)} pages with X-marks")
            else:
                logging.info("Pre-filter: No pages flagged, skipping X-mark detection entirely (100% clean corpus)")
                xmark_cache = {}
                quality_config.detect_strikethrough = False  # Disable for this document

        # 1. Extract ToC and infer written page numbers BEFORE processing pages
        logging.debug("Extracting ToC and inferring written page numbers...")
        toc_map = _extract_toc_from_pdf(doc)
        written_page_map = infer_written_page_numbers(doc)

        # 1.5. Generate document header and markdown ToC
        document_header = ""
        markdown_toc = ""
        if output_format == "markdown":
            document_header = _generate_document_header(doc)
            markdown_toc = _generate_markdown_toc_from_pdf(toc_map, skip_front_matter=True)

        # 2. Determine first content page (skip front matter like "Title Page", "Copyright", "Contents")
        # Default to page 1 (process all pages) unless we have confident ToC
        # Small PDFs (< 10 pages) likely don't have front matter worth skipping
        first_content_page = 1
        if toc_map and len(doc) >= 10:  # Only skip front matter for larger documents (>= 10 pages)
            first_content_page = _find_first_content_page(toc_map)
            logging.info(f"Starting content at page {first_content_page} (first real content after front matter)")
        else:
            logging.info(f"Processing all pages from page 1 (small document or no confident ToC)")

        # 2. Extract structured content using block-level analysis
        logging.debug("Performing structured PDF extraction with block analysis...")
        page_count = len(doc)
        page_contents = []  # Store content with page numbers
        all_footnotes = []  # Collect footnotes from all pages

        # Phase 3: Initialize continuation parser for multi-page footnote tracking
        continuation_parser = CrossPageFootnoteParser() if detect_footnotes else None

        for i, page in enumerate(doc):
            page_num = i + 1

            # Skip front matter pages (before first ToC entry)
            if page_num < first_content_page:
                logging.debug(f"Skipping front matter page {page_num}")
                continue

            logging.debug(f"Processing page {page_num}/{page_count} with block analysis...")

            # Detect footnotes on this page if requested
            if detect_footnotes:
                page_footnotes = _detect_footnotes_in_page(page, i)
                if page_footnotes.get('definitions'):
                    # Phase 3: Process through continuation state machine
                    try:
                        completed_footnotes = continuation_parser.process_page(
                            page_footnotes['definitions'],
                            page_num
                        )

                        # Convert FootnoteWithContinuation objects to dict format
                        completed_dicts = [
                            _footnote_with_continuation_to_dict(fn) for fn in completed_footnotes
                        ]

                        # Add completed footnotes to results
                        all_footnotes.extend(completed_dicts)

                        logging.debug(
                            f"Found {len(page_footnotes['definitions'])} footnotes on page {page_num}, "
                            f"{len(completed_footnotes)} completed"
                        )
                    except Exception as e:
                        # Fallback: If continuation processing fails, use original behavior
                        logging.warning(f"Continuation processing failed on page {page_num}: {e}")
                        all_footnotes.extend(page_footnotes['definitions'])
                        logging.debug(f"Found {len(page_footnotes['definitions'])} footnotes on page {page_num}")

            if output_format == "markdown":
                # Get ToC entries and written page number for this page
                toc_entries = toc_map.get(page_num, [])
                written_page = written_page_map.get(page_num)

                # Detect written page number with position for duplication removal
                written_page_position = None
                written_page_text = None
                if written_page:
                    # Re-detect to get position and matched text
                    detected_num, detected_pos, detected_text = _detect_written_page_on_page(page)
                    if detected_num == written_page:
                        written_page_position = detected_pos
                        written_page_text = detected_text

                # Use sophisticated _format_pdf_markdown for structure preservation
                # Pass ToC and page numbering info
                # Phase 2: Pass pdf_path, quality_config, and xmark_cache for quality pipeline
                page_markdown = _format_md(
                    page,
                    preserve_linebreaks=preserve_linebreaks,
                    toc_entries=toc_entries,
                    pdf_page_num=page_num,
                    written_page_num=written_page,
                    written_page_position=written_page_position,
                    written_page_text=written_page_text,
                    use_toc_headings=bool(toc_map),  # Use ToC if available
                    pdf_path=file_path,
                    quality_config=quality_config,
                    xmark_cache=xmark_cache
                )

                # Skip empty/minimal pages (< 100 chars of actual content)
                # Strip page markers to check actual content
                content_only = page_markdown
                for marker in [f'[[PDF_page_{page_num}]]', f'((p.{written_page}))'] if written_page else [f'[[PDF_page_{page_num}]]']:
                    content_only = content_only.replace(marker, '')

                # Also remove ToC heading if present (it will be in ToC anyway)
                if toc_entries:
                    for level, title in toc_entries:
                        content_only = content_only.replace('#' * level + ' ' + title, '')

                content_only = content_only.strip()

                # Keep page if:
                # 1. It has ToC entries (always keep pages with ToC headings)
                # 2. OR it has substantial content (> 100 chars)
                has_toc = bool(toc_entries)
                has_content = len(content_only) > 100

                if page_markdown and (has_toc or has_content):
                    # Page markers now handled inside _format_pdf_markdown
                    page_contents.append(page_markdown)
                else:
                    logging.debug(f"Skipping empty/minimal page {page_num} ({len(content_only)} chars, has_toc={has_toc})")
            else:
                # For plain text, use basic extraction
                page_text = page.get_text("text")
                if page_text:
                    # Add page marker
                    page_with_marker = f"[Page {page_num}]\n\n{page_text}"
                    page_contents.append(page_with_marker)

        # Phase 3: Finalize any remaining incomplete footnotes at document end
        if detect_footnotes and continuation_parser:
            try:
                final_footnotes = continuation_parser.finalize()
                if final_footnotes:
                    # Convert FootnoteWithContinuation objects to dict format
                    final_dicts = [
                        _footnote_with_continuation_to_dict(fn) for fn in final_footnotes
                    ]
                    all_footnotes.extend(final_dicts)
                    logging.info(f"Finalized {len(final_footnotes)} incomplete footnotes at document end")

                # Log continuation summary
                summary = continuation_parser.get_summary()
                logging.info(
                    f"Continuation summary: {summary['total_completed']} completed, "
                    f"{summary['multi_page_count']} multi-page, "
                    f"avg confidence: {summary['average_confidence']:.2f}"
                )
            except Exception as e:
                logging.warning(f"Failed to finalize continuation parser: {e}")

        # 2. Combine all pages
        full_content = "\n\n".join(page_contents)

        # 2.5. Apply letter spacing correction if needed (for digital-native PDFs too)
        # DISABLED: Letter spacing correction (now using ocrmypdf re-OCR for poor quality PDFs)
        # if detect_letter_spacing_issue(full_content[:1000]):
        #     logging.info("Applying letter spacing correction to PDF content...")
        #     full_content = correct_letter_spacing(full_content)

        # 3. Preprocess the content (front matter, ToC extraction)
        # For structured markdown, we already have good structure, just extract front matter
        content_lines = full_content.splitlines()
        (lines_after_fm, title) = _identify_fm(content_lines)
        (final_content_lines, formatted_toc) = _extract_toc_fn(lines_after_fm, output_format)

        # 4. Construct final output
        final_output_parts = []

        # Add custom header and markdown ToC (if we have PDF ToC)
        if toc_map and output_format == "markdown":
            if document_header:
                final_output_parts.append(document_header)
            if markdown_toc:
                final_output_parts.append(markdown_toc)
        # Fallback: add extracted title if no ToC
        elif title != "Unknown Title" and not toc_map:
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)

        # Old heuristic ToC (only if no PDF ToC available)
        if formatted_toc and not toc_map:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines)
        final_output_parts.append(main_content.strip())

        # Add footnotes at the end if detected
        if detect_footnotes and all_footnotes:
            # Deduplicate footnotes by (page, marker) instead of just marker
            # This allows same marker (e.g., "1") to appear on different pages
            # Example: Heidegger has marker "1" on both page 22 and page 23
            seen_markers_per_page = {}  # {page_num: set(markers)}
            unique_footnotes = []

            for fn in all_footnotes:
                marker = fn.get('actual_marker', fn.get('marker'))
                # Extract page number from 'pages' list (primary) or fallback fields
                pages = fn.get('pages', [])
                page_num = pages[0] if pages else fn.get('page_number', fn.get('page', -1))

                logging.debug("Footnote dedup: marker=%s pages=%s page_num=%s", marker, pages, page_num)

                # Special handling for markerless continuations - each is unique
                # Markerless blocks (marker=None) are continuation candidates that should
                # never be deduplicated, as each represents distinct orphaned content
                if marker is None:
                    unique_footnotes.append(fn)  # Don't deduplicate
                    continue

                # Per-page deduplication instead of global
                if page_num not in seen_markers_per_page:
                    seen_markers_per_page[page_num] = set()

                # Check if marker already seen on THIS page
                if marker not in seen_markers_per_page[page_num]:
                    seen_markers_per_page[page_num].add(marker)
                    unique_footnotes.append(fn)
                    logging.debug(f"Adding footnote: page {page_num}, marker '{marker}'")
                else:
                    # True duplicate: same marker on same page (likely bbox-based duplicate)
                    logging.debug(f"Skipping duplicate footnote on page {page_num}: marker '{marker}'")

            footnote_section = _format_footnotes_markdown({'definitions': unique_footnotes})
            if footnote_section:
                final_output_parts.append("\n\n---\n\n## Footnotes\n\n" + footnote_section)
                logging.info(f"Added {len(unique_footnotes)} footnotes to output (deduplicated from {len(all_footnotes)})")

        final_output = "\n\n".join(part for part in final_output_parts if part).strip()

        # Close doc before returning
        if doc is not None and not doc.is_closed:
            doc.close()
            logging.debug(f"Closed PDF document before return: {file_path}")

        # Clear textpage cache to free memory
        _clear_textpage_cache()

        return final_output

    except Exception as fitz_err: # Broaden exception type for PyMuPDF errors
        # Check if the error originated from the OCR/preprocessing block
        if isinstance(fitz_err, (OCRDependencyError, TesseractNotFoundError, RuntimeError)) and \
           ("OCR" in str(fitz_err) or "Tesseract" in str(fitz_err)):
             logging.error(f"Re-raising OCR-related error for {file_path}: {fitz_err}", exc_info=True)
             raise fitz_err # Re-raise the original OCR-related error to stop execution

        # Check if it's likely an encryption error first
        # Use isinstance to check for ValueError which might indicate encryption
        elif "encrypted" in str(fitz_err).lower() or isinstance(fitz_err, ValueError):
             logging.error(f"PyMuPDF/Value error processing encrypted PDF {file_path}: {fitz_err}", exc_info=True)
             raise ValueError(f"PDF {file_path} is encrypted and cannot be opened.") from fitz_err
        else: # Handle other PyMuPDF or general errors
             logging.error(f"PyMuPDF/Other error processing {file_path}: {fitz_err}", exc_info=True)
             # Use RuntimeError for broader fitz errors or other exceptions
             raise RuntimeError(f"Error opening or processing PDF {file_path}: {fitz_err}") from fitz_err
    # Removed the separate ValueError and Exception catches as they are covered above.
    finally:
        # Close document if it exists and is not already closed
        # Note: PyMuPDF's __len__() raises ValueError when closed, so we can't use 'if doc:'
        if doc is not None and not doc.is_closed:
            doc.close()
            logging.debug(f"Closed PDF document: {file_path}")

        # Clean up temporary OCR file if created
        if temp_ocr_file and temp_ocr_file.exists():
            try:
                temp_ocr_file.unlink()
                logging.debug(f"Cleaned up temporary OCR file: {temp_ocr_file}")
            except Exception as cleanup_err:
                logging.warning(f"Failed to clean up temp OCR file {temp_ocr_file}: {cleanup_err}")


async def process_document(file_path_str: str, output_format: str = "txt", book_details: dict = None) -> dict:
    """
    Processes a document (PDF, EPUB, TXT) based on its extension,
    extracts text, applies preprocessing, saves it, and returns the path.
    """
    if book_details is None: # Ensure book_details is a dict for _slugify
        book_details = {}

    file_path = Path(file_path_str)
    file_extension = file_path.suffix.lower()
    processed_text = ""

    logging.info(f"Processing document: {file_path} with format {output_format}")

    try:
        if file_extension == '.pdf':
            processed_text = await asyncio.to_thread(process_pdf, file_path, output_format)
        elif file_extension == '.epub':
            if not _get_facade().EBOOKLIB_AVAILABLE:
                raise ImportError("Required library 'ebooklib' is not installed or available for EPUB processing.")
            processed_text = await asyncio.to_thread(process_epub, file_path, output_format)
        elif file_extension == '.txt':
            processed_text = await process_txt(file_path, output_format) # process_txt is already async
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

        if processed_text is None or not processed_text.strip():
            logging.warning(f"No text extracted from {file_path}")
            # Return None for path if no content, but keep content list for consistency
            return {"processed_file_path": None, "content": []}

        # Save the processed text with metadata
        # Determine corrections applied (for metadata)
        corrections = []
        if file_extension == '.pdf':
            # Check if letter spacing correction was applied
            if detect_letter_spacing_issue(processed_text[:500]):
                corrections.append("letter_spacing_correction")

        # Pass book_details to save_processed_text for filename generation
        # This also generates and saves the metadata sidecar
        saved_path = await save_processed_text(
            original_file_path=file_path,
            processed_content=processed_text,
            output_format=output_format, # This should be the format of the processed_text (e.g. 'md' or 'txt')
            book_details=book_details,
            ocr_quality_score=None,  # FUTURE: Calculate OCR quality score if OCR was used
            corrections_applied=corrections
        )

        # Determine metadata file path
        from filename_utils import create_metadata_filename
        processed_filename = Path(saved_path).name
        metadata_filename = create_metadata_filename(processed_filename)
        metadata_path = PROCESSED_OUTPUT_DIR / metadata_filename

        # Return ONLY paths, not content (prevents MCP token overflow)
        # User can selectively read portions of the processed file
        return {
            "processed_file_path": str(saved_path),
            "metadata_file_path": str(metadata_path) if metadata_path.exists() else None,
            "stats": {
                "word_count": len(processed_text.split()),
                "char_count": len(processed_text),
                "format": output_format
            }
        }

    except Exception as e:
        logging.error(f"Error processing document {file_path}: {e}")
        # Re-raise as a RuntimeError to be caught by the bridge's main error handler
        raise RuntimeError(f"Error processing document {file_path}: {e}") from e

async def save_processed_text(
    original_file_path: str,
    processed_content: str,
    output_format: str = "txt",
    book_details: dict | None = None, # Added book_details for slug
    ocr_quality_score: float | None = None, # For metadata
    corrections_applied: list | None = None # For metadata
) -> str:
    """Saves the processed text content to a file in the output directory."""
    try:
        original_path = Path(original_file_path)
        original_filename = original_path.stem
        original_extension = original_path.suffix.lower()

        # --- Generate Filename using unified format ---
        if book_details:
            # Use unified filename generation
            # Remove 'extension' key to avoid double extension bug
            clean_book_details = {k: v for k, v in book_details.items() if k != 'extension'}
            base_name = create_unified_filename(clean_book_details, extension=None)
            processed_filename = f"{base_name}{original_extension}.processed.{output_format}"
        else:
            # Fallback if no book_details
            base_name = _slugify(original_filename)
            processed_filename = f"{base_name}{original_extension}.processed.{output_format}"

        # --- Ensure Output Directory Exists ---
        PROCESSED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = PROCESSED_OUTPUT_DIR / processed_filename

        # --- Write Content Asynchronously (NO YAML frontmatter) ---
        # Main markdown should be CLEAN for RAG (only content + page markers)
        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            await f.write(processed_content)

        logging.info(f"Successfully saved processed content to: {output_path}")

        # --- Generate and Save Metadata Sidecar ---
        if book_details:
            try:
                format_type = original_path.suffix.lower().lstrip('.')

                # --- Metadata Verification Step (NEW) ---
                # Extract metadata from document for verification
                extracted_metadata = {}
                try:
                    if format_type == 'pdf':
                        extracted_metadata = extract_pdf_metadata(original_path)
                    elif format_type == 'epub':
                        extracted_metadata = extract_epub_metadata(original_path)
                    elif format_type == 'txt':
                        extracted_metadata = extract_txt_metadata(original_path)

                    logging.info(f"Extracted document metadata for verification: {list(extracted_metadata.keys())}")
                except Exception as extract_err:
                    logging.warning(f"Could not extract document metadata for verification: {extract_err}")
                    extracted_metadata = {}

                # Verify API metadata against extracted metadata
                verification_report = None
                if extracted_metadata:
                    try:
                        # Prepare API metadata in consistent format
                        api_metadata = {
                            'title': book_details.get('title'),
                            'author': book_details.get('author'),
                            'publisher': book_details.get('publisher'),
                            'year': book_details.get('year'),
                            'isbn': book_details.get('isbn')
                        }

                        verification_report = verify_metadata(api_metadata, extracted_metadata)
                        logging.info(f"Metadata verification: {verification_report['summary']}")

                        # Log any discrepancies for review
                        if verification_report['discrepancies']:
                            logging.warning(f"Metadata discrepancies found: {verification_report['discrepancies']}")
                    except Exception as verify_err:
                        logging.warning(f"Could not verify metadata: {verify_err}")
                        verification_report = None

                # Extract PDF ToC and metadata for verification
                pdf_toc = None
                extracted_metadata = None

                if format_type == 'pdf' and _get_facade().PYMUPDF_AVAILABLE:
                    try:
                        doc = _get_facade().fitz.open(str(original_path))
                        pdf_toc = doc.get_toc()  # Returns list of [level, title, page]
                        doc.close()
                        logging.info(f"Extracted {len(pdf_toc)} ToC entries from PDF for metadata")
                    except Exception as toc_err:
                        logging.warning(f"Could not extract PDF ToC for metadata: {toc_err}")

                    # Extract and verify metadata
                    try:
                        from metadata_verification import extract_pdf_metadata, verify_metadata
                        extracted_metadata = extract_pdf_metadata(str(original_path))
                        verification_report = verify_metadata(book_details, extracted_metadata)
                        logging.info(f"Metadata verification: {verification_report.get('summary', 'N/A')}")
                    except ImportError:
                        logging.warning("metadata_verification module not available")
                    except Exception as verify_err:
                        logging.warning(f"Metadata verification failed: {verify_err}")

                # Generate metadata with verification report
                metadata = generate_metadata_sidecar(
                    original_filename=str(original_path),
                    processed_content=processed_content,  # Use processed_content, not final_content
                    book_details=book_details,
                    ocr_quality_score=ocr_quality_score,
                    corrections_applied=corrections_applied or [],
                    format_type=format_type,
                    output_format=output_format,
                    pdf_toc=pdf_toc
                )

                # Add verification report to metadata if available
                if 'verification_report' in locals() and verification_report:
                    metadata['verification'] = verification_report

                # Add verification report to metadata if available
                if verification_report:
                    metadata['verification'] = verification_report

                # Save metadata sidecar
                metadata_filename = create_metadata_filename(processed_filename)
                metadata_path = PROCESSED_OUTPUT_DIR / metadata_filename
                save_metadata_sidecar(metadata, metadata_path)

                logging.info(f"Successfully saved metadata sidecar to: {metadata_path}")
            except Exception as meta_err:
                logging.warning(f"Failed to generate metadata sidecar: {meta_err}")
                # Don't fail the whole operation if metadata generation fails

        return str(output_path) # Return the string representation of the path

    except ValueError as ve: # Catch the specific error for None content
         logging.error(f"ValueError during save: {ve}")
         # Construct a meaningful path for the error message if possible
         unknown_path = PROCESSED_OUTPUT_DIR / f"{_slugify(original_path.stem)}.processed.{output_format}"
         raise FileSaveError(f"Failed to save processed text to {unknown_path}: {ve}") from ve
    except OSError as ose:
        logging.error(f"OS error saving processed file: {ose}")
        # Construct a meaningful path for the error message if possible
        failed_path = PROCESSED_OUTPUT_DIR / processed_filename if 'processed_filename' in locals() else "unknown_processed_file"
        raise FileSaveError(f"Failed to save processed file due to OS error: {ose}") from ose
    except Exception as e:
        logging.error(f"Unexpected error saving processed file: {e}", exc_info=True)
        failed_path = PROCESSED_OUTPUT_DIR / processed_filename if 'processed_filename' in locals() else "unknown_processed_file"
        raise FileSaveError(f"Unexpected error saving processed file {failed_path}: {e}") from e
