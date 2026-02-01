"""
X-mark detection for sous-rature (under erasure) in PDFs.

Contains parallel and single-page X-mark detection, fast pre-filtering,
and document-level detection enablement logic.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    '_detect_xmarks_parallel',
    '_detect_xmarks_single_page',
    '_page_needs_xmark_detection_fast',
    '_should_enable_xmark_detection_for_document',
]


def _detect_xmarks_parallel(pdf_path: Path, page_count: int, max_workers: int = 4, pages_to_check: list = None) -> dict:
    """
    Detect X-marks across pages in parallel.

    Uses ProcessPoolExecutor for true parallel execution (opencv is CPU-bound).
    Detects specified pages or all pages, caches results for sequential processing.

    OPTIMIZATION (2025-10-18): Now accepts pages_to_check for selective detection.
    Use with fast pre-filter for 31x speedup (only check flagged pages).

    Args:
        pdf_path: Path to PDF file
        page_count: Number of pages in PDF
        max_workers: Number of parallel workers (default: 4)
        pages_to_check: List of page numbers to check (default: all pages)

    Returns:
        Dict mapping page_num -> XMarkDetectionResult (only for checked pages)
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import os

    # Determine which pages to check
    if pages_to_check is None:
        pages_to_check = list(range(page_count))

    # Determine optimal worker count
    cpu_count = os.cpu_count() or 4
    workers = min(max_workers, cpu_count, len(pages_to_check))  # Don't spawn more workers than pages

    logging.info(f"Parallel X-mark detection: {len(pages_to_check)} pages with {workers} workers")

    xmark_cache = {}

    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit only specified pages for parallel detection
            future_to_page = {
                executor.submit(_detect_xmarks_single_page, pdf_path, page_num): page_num
                for page_num in pages_to_check
            }

            # Collect results as they complete
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    result = future.result()
                    xmark_cache[page_num] = result

                    if result and result.has_xmarks:
                        logging.debug(f"Page {page_num}: {result.xmark_count} X-marks detected (parallel)")
                except Exception as e:
                    logging.error(f"Page {page_num}: X-mark detection failed in parallel: {e}")
                    # Store None to indicate failure
                    xmark_cache[page_num] = None

    except Exception as e:
        logging.error(f"Parallel X-mark detection failed: {e}, falling back to sequential")
        # Return empty cache, will fallback to sequential detection
        return {}

    detected_count = sum(1 for r in xmark_cache.values() if r and r.has_xmarks)
    logging.info(f"Parallel detection complete: {detected_count} pages with X-marks (out of {len(pages_to_check)} checked)")

    return xmark_cache


def _detect_xmarks_single_page(pdf_path: Path, page_num: int):
    """
    Detect X-marks on a single page (for parallel execution).

    This function is called by ProcessPoolExecutor workers.
    Must be picklable (top-level function, not nested).

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)

    Returns:
        XMarkDetectionResult or None if detection fails
    """
    try:
        from lib.strikethrough_detection import detect_strikethrough_enhanced, XMarkDetectionConfig

        config = XMarkDetectionConfig(
            min_line_length=10,
            diagonal_tolerance=15,
            proximity_threshold=20,
            confidence_threshold=0.5
        )

        result = detect_strikethrough_enhanced(pdf_path, page_num, bbox=None, config=config)
        return result

    except Exception as e:
        # Return None to indicate failure (will be handled by caller)
        logging.error(f"Single page X-mark detection failed for page {page_num}: {e}")
        return None


def _page_needs_xmark_detection_fast(page_text: str, threshold: float = 0.02) -> bool:
    """
    Ultra-fast pre-filter: Determine if page might have X-marks or corruption.

    Uses simplified garbled detection (symbol density only, no entropy).
    Cost: ~0.01ms (after text extraction, nearly free)

    Strategy:
    - Page-level symbol density check
    - Lower threshold (2%) than region-level (25%)
    - Catches localized issues (X-marks add ~1-2% symbols)

    Args:
        page_text: Full page text (already extracted)
        threshold: Symbol density threshold (default: 2% for page-level)

    Returns:
        True if page might have X-marks/corruption (run expensive detection)
        False if page is clean (skip detection, save 5ms)

    Performance:
    - Clean page (97%): 0.01ms -> skip X-mark (save 5ms)
    - Flagged page (3%): 0.01ms -> run X-mark (5ms)
    - Net: 31x speedup on X-mark detection

    Rationale:
    - X-marks corrupt text extraction (")(" instead of "is")
    - This adds ~1-2% symbols to page
    - 2% threshold catches all X-marked pages
    - Normal academic text: 1-1.5% symbols (below threshold)
    - False positives: <5% (acceptable)
    """
    if not page_text or len(page_text) < 100:
        return False

    # Fast character counting (no entropy calculation!)
    total = len(page_text)
    alpha = sum(1 for c in page_text if c.isalpha())
    digits = sum(1 for c in page_text if c.isdigit())
    spaces = sum(1 for c in page_text if c.isspace())
    symbols = total - alpha - digits - spaces

    symbol_density = symbols / total

    # Page-level threshold (2% catches X-marks)
    if symbol_density > threshold:
        return True  # Might have X-marks or corruption

    # Additional check: alphabetic ratio
    alpha_ratio = alpha / total
    if alpha_ratio < 0.70 or alpha_ratio > 0.90:
        return True  # Unusual distribution

    return False  # Clean page, skip expensive X-mark detection

def _should_enable_xmark_detection_for_document(metadata: dict) -> bool:
    """
    Determine if X-mark detection should be enabled for this document.

    Uses ROBUST criteria - NO text pattern matching:
    - User configuration (explicit control)
    - Metadata heuristics (author, subject from Z-Library)
    - Conservative default (enable when uncertain)

    Args:
        metadata: Document metadata (from Z-Library or PDF)

    Returns:
        True if X-mark detection should be enabled for this document
    """
    # User explicit control via environment variable
    mode = os.getenv('RAG_XMARK_DETECTION_MODE', 'auto').lower()

    if mode == 'always':
        return True
    if mode == 'never':
        return False

    # Auto mode: Use metadata heuristics
    if mode in ['auto', 'philosophy_only']:
        author = metadata.get('authors', '').lower() if isinstance(metadata.get('authors'), str) else ''
        subject = metadata.get('subject', '').lower() if metadata.get('subject') else ''
        title = metadata.get('title', '').lower() if metadata.get('title') else ''

        # Known philosophy authors who use sous-rature
        philosophy_authors = ['derrida', 'heidegger', 'levinas', 'nancy', 'agamben', 'deleuze']
        if any(name in author for name in philosophy_authors):
            logging.info(f"X-mark detection enabled: Philosophy author detected ({author})")
            return True

        # Philosophy subject classification
        philosophy_terms = ['philosophy', 'phenomenology', 'ontology', 'metaphysics', 'deconstruction']
        if any(term in subject or term in title for term in philosophy_terms):
            logging.info(f"X-mark detection enabled: Philosophy subject detected")
            return True

        # For 'philosophy_only' mode, disable if not philosophy
        if mode == 'philosophy_only':
            logging.info(f"X-mark detection disabled: Not philosophy corpus")
            return False

    # Auto mode default: ENABLE (conservative)
    # Rationale: Better to run unnecessarily than miss sous-rature
    logging.debug(f"X-mark detection enabled: Default (corpus unknown)")
    return True
