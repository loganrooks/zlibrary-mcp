"""
Stage 3 OCR recovery for the quality pipeline.

Contains _stage_3_ocr_recovery (sous-rature and corruption recovery)
and _find_word_between_contexts (context-based word extraction from OCR text).
"""
import io
import logging
import re
from pathlib import Path
from typing import Optional

from lib.rag.utils.constants import STRATEGY_CONFIGS

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


# Phase 2: Enhanced data model imports
from lib.rag_data_models import PageRegion

__all__ = [
    '_stage_3_ocr_recovery',
    '_find_word_between_contexts',
]


def _stage_3_ocr_recovery(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: 'QualityPipelineConfig',
    ocr_cache: dict = None,
    xmark_result: 'XMarkDetectionResult' = None,
    page_dpi_map: dict = None,
) -> PageRegion:
    """
    Stage 3: OCR recovery - BOTH sous-rature AND corruption.

    Critical: Recovers text under X-marks (sous-rature) AND corrupted text.

    Two recovery paths:
    1. Sous-rature recovery (has X-marks):
       - OCR region under X-mark to recover original word
       - Apply strikethrough formatting
       - Preserve BOTH word and deletion

    2. Corruption recovery (garbled, no X-marks):
       - OCR corrupted region
       - Replace with recovered text

    Args:
        page_region: PageRegion from Stages 1-2
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)
        config: Pipeline configuration
        ocr_cache: Optional cache of OCR results
        xmark_result: X-mark detection result from Stage 2 (if available)

    Returns:
        PageRegion with recovered text and appropriate quality flags
    """
    # Priority 1: Sous-rature text recovery (even if text appears clean!)
    # X-marks indicate intentional deletion - need to recover text UNDER the X-mark
    if page_region.is_strikethrough() and xmark_result and xmark_result.has_xmarks:
        logging.info(f"Stage 3: Recovering sous-rature text on page {page_num}")

        if not getattr(_get_facade(), 'OCR_AVAILABLE', OCR_AVAILABLE):
            logging.warning("OCR unavailable - cannot recover sous-rature text")
            page_region.quality_flags.add('sous_rature_recovery_unavailable')
            return page_region

        try:
            # For each X-mark on this page, OCR the region to recover original text
            import fitz
            from PIL import Image
            import pytesseract
            import io
            import re

            doc = fitz.open(str(pdf_path))
            page = doc[page_num]

            # Get OCR'd text (cache to avoid re-running on same page)
            if ocr_cache is not None and page_num in ocr_cache:
                recovered_text = ocr_cache[page_num]
                logging.debug(f"Stage 3: Using cached OCR for page {page_num}")
            else:
                # OCR entire page at high resolution (adaptive DPI if available)
                dpi = 300  # default fallback
                if page_dpi_map and page_num in page_dpi_map:
                    dpi = page_dpi_map[page_num].dpi
                    logging.debug(f"Stage 3: Using adaptive DPI {dpi} for page {page_num}")
                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))

                # Run Tesseract to recover text
                recovered_text = pytesseract.image_to_string(img, lang='eng')

                if ocr_cache is not None:
                    ocr_cache[page_num] = recovered_text

                logging.debug(f"Stage 3: OCR'd page {page_num} ({len(recovered_text)} chars)")

            doc.close()

            # Common corrupted representations of X-marks
            corrupted_patterns = [')(', '~', ')  (', ') (', '( )', '()', '><']

            # Track if any recovery happened
            recovery_count = 0

            # Build full region text for context extraction
            # CRITICAL: Look at neighboring spans for context!
            all_span_texts = [span.text for span in page_region.spans]

            # Process each span to find and recover corrupted text
            for span_idx, span in enumerate(page_region.spans):
                original_text = span.text

                # Check for corrupted patterns
                for pattern in corrupted_patterns:
                    if pattern not in original_text:
                        continue

                    # Find all occurrences of pattern
                    matches = list(re.finditer(re.escape(pattern), original_text))

                    for match in matches:
                        # Extract context from NEIGHBORING SPANS (not just current span)
                        # Look at previous and next spans for context words

                        before_words = []
                        after_words = []

                        # Get words from previous spans
                        for prev_idx in range(max(0, span_idx - 3), span_idx):
                            prev_text = all_span_texts[prev_idx].strip()
                            if prev_text:
                                before_words.extend(prev_text.split())

                        # Get words from current span before pattern
                        start_pos = match.start()
                        before_text = original_text[:start_pos].strip()
                        if before_text:
                            before_words.extend(before_text.split())

                        # Get words from current span after pattern
                        end_pos = match.end()
                        after_text = original_text[end_pos:].strip()
                        if after_text:
                            after_words.extend(after_text.split())

                        # Get words from next spans
                        for next_idx in range(span_idx + 1, min(len(all_span_texts), span_idx + 4)):
                            next_text = all_span_texts[next_idx].strip()
                            if next_text:
                                after_words.extend(next_text.split())

                        # Limit to last 3 before and first 3 after
                        before_words = before_words[-3:] if before_words else []
                        after_words = after_words[:3] if after_words else []

                        # Try to find matching context in OCR'd text
                        if not before_words and not after_words:
                            logging.warning(f"Stage 3: No context for pattern '{pattern}' - cannot recover")
                            continue

                        recovered_word = _find_word_between_contexts(
                            recovered_text,
                            before_words,
                            after_words
                        )

                        if recovered_word:
                            # Replace corrupted pattern with recovered word
                            new_text = (
                                original_text[:start_pos] +
                                recovered_word +
                                original_text[end_pos:]
                            )
                            span.text = new_text

                            # Add strikethrough formatting
                            span.formatting.add('strikethrough')
                            span.formatting.add('sous-erasure')

                            recovery_count += 1

                            logging.info(
                                f"Stage 3: Recovered '{recovered_word}' from pattern '{pattern}' "
                                f"(context: {' '.join(before_words[-2:])} ___ {' '.join(after_words[:2])})"
                            )
                        else:
                            logging.warning(
                                f"Stage 3: Could not recover word for pattern '{pattern}' "
                                f"(context: {' '.join(before_words)} ___ {' '.join(after_words)})"
                            )

            # Update quality flags
            if recovery_count > 0:
                page_region.quality_flags.add('sous_rature_recovered')
                logging.info(f"Stage 3: Recovered {recovery_count} sous-rature word(s) on page {page_num}")
            else:
                page_region.quality_flags.add('sous_rature_recovery_attempted')
                logging.warning(f"Stage 3: No sous-rature words recovered on page {page_num}")

        except Exception as e:
            logging.error(f"Stage 3: Sous-rature recovery failed: {e}", exc_info=True)
            page_region.quality_flags.add('sous_rature_recovery_failed')

        return page_region

    # Priority 2: Corruption recovery (garbled text, no X-marks)
    elif page_region.is_garbled() and not page_region.is_strikethrough():
        # Check if OCR available
        if not getattr(_get_facade(), 'OCR_AVAILABLE', OCR_AVAILABLE):
            logging.warning("OCR recovery requested but dependencies not available")
            page_region.quality_flags.add('recovery_unavailable')
            return page_region

        # Check confidence threshold (only recover high-confidence garbled text)
        # Note: quality_score = 1.0 - garbled_confidence, so low quality_score = high garbled_confidence
        if page_region.quality_score is None or page_region.quality_score > (1.0 - config.recovery_threshold):
            # Confidence too low for recovery
            page_region.quality_flags.add('low_confidence')
            logging.debug(f"Stage 3: Garbled confidence below threshold, preserving original")
            return page_region

        # Flag as needing OCR recovery (full implementation in Week 2)
        page_region.quality_flags.add('recovery_needed')
        logging.info(f"Stage 3: OCR recovery needed (implementation pending - Week 2)")

    return page_region


def _find_word_between_contexts(
    text: str,
    before_words: list,
    after_words: list,
    max_word_length: int = 20
) -> Optional[str]:
    """
    Find a word in text that appears between given context words.

    Strategy: Search for context pattern in text, extract word between.

    Args:
        text: Full text to search in (OCR'd text)
        before_words: List of words expected before target word
        after_words: List of words expected after target word
        max_word_length: Maximum length of word to extract (sanity check)

    Returns:
        Recovered word if found, None otherwise

    Example:
        >>> text = "the sign is that ill-named thing"
        >>> before = ["the", "sign"]
        >>> after = ["that", "ill-named"]
        >>> _find_word_between_contexts(text, before, after)
        'is'
    """
    if not text:
        return None

    # Normalize text and context words
    text_normalized = ' '.join(text.split())  # Normalize whitespace

    # Build regex pattern for context matching
    # Pattern: (before_words) WORD (after_words)
    # Allow for some flexibility in whitespace and case

    # Build before pattern
    if before_words:
        before_pattern = r'\s+'.join(re.escape(w) for w in before_words[-2:])  # Last 2 words
    else:
        before_pattern = ''

    # Build after pattern
    if after_words:
        after_pattern = r'\s+'.join(re.escape(w) for w in after_words[:2])  # First 2 words
    else:
        after_pattern = ''

    # Build full pattern: before + (capture word) + after
    if before_pattern and after_pattern:
        # Both context available
        pattern = (
            before_pattern +
            r'\s+(\w{1,' + str(max_word_length) + r'})\s+' +
            after_pattern
        )
    elif before_pattern:
        # Only before context
        pattern = before_pattern + r'\s+(\w{1,' + str(max_word_length) + r'})'
    elif after_pattern:
        # Only after context
        pattern = r'(\w{1,' + str(max_word_length) + r'})\s+' + after_pattern
    else:
        # No context - cannot reliably extract
        return None

    # Try case-insensitive match first
    match = re.search(pattern, text_normalized, re.IGNORECASE)

    if match:
        recovered_word = match.group(1)

        # Sanity checks
        if len(recovered_word) > max_word_length:
            return None
        if not recovered_word.strip():
            return None

        return recovered_word

    return None
