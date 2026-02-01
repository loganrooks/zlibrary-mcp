"""
Quality pipeline for RAG processing.

Contains the multi-stage quality pipeline (statistical detection, visual analysis,
OCR recovery) and the QualityPipelineConfig configuration class.
"""
import io
import logging
import os
import re
from dataclasses import dataclass
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

# Phase 2.2: Garbled text detection
from lib.garbled_text_detection import (
    detect_garbled_text_enhanced,
    GarbledDetectionConfig,
)

__all__ = [
    'QualityPipelineConfig',
    '_stage_1_statistical_detection',
    '_stage_2_visual_analysis',
    '_stage_3_ocr_recovery',
    '_find_word_between_contexts',
    '_apply_quality_pipeline',
]


@dataclass
class QualityPipelineConfig:
    """Configuration for the quality pipeline stages."""

    # Feature toggles
    enable_pipeline: bool = True
    detect_garbled: bool = True
    detect_strikethrough: bool = True
    enable_ocr_recovery: bool = True

    # Strategy
    strategy: str = 'hybrid'  # 'philosophy' | 'technical' | 'hybrid'

    # Thresholds (from strategy)
    garbled_threshold: float = 0.75
    recovery_threshold: float = 0.8

    # Performance
    batch_size: int = 10

    @classmethod
    def from_env(cls) -> 'QualityPipelineConfig':
        """Load configuration from environment variables."""
        strategy_name = os.getenv('RAG_QUALITY_STRATEGY', 'hybrid')
        strategy = STRATEGY_CONFIGS.get(strategy_name, STRATEGY_CONFIGS['hybrid'])

        return cls(
            enable_pipeline=os.getenv('RAG_ENABLE_QUALITY_PIPELINE', 'true').lower() == 'true',
            detect_garbled=os.getenv('RAG_DETECT_GARBLED', 'true').lower() == 'true',
            detect_strikethrough=os.getenv('RAG_DETECT_STRIKETHROUGH', 'true').lower() == 'true',
            enable_ocr_recovery=os.getenv('RAG_ENABLE_OCR_RECOVERY', 'true').lower() == 'true',
            strategy=strategy_name,
            garbled_threshold=strategy['garbled_threshold'],
            recovery_threshold=strategy['recovery_threshold'],
            batch_size=int(os.getenv('RAG_QUALITY_BATCH_SIZE', '10'))
        )


def _stage_1_statistical_detection(page_region: PageRegion, config: QualityPipelineConfig) -> PageRegion:
    """
    Stage 1: Detect garbled text via statistical analysis.

    Uses detect_garbled_text_enhanced() from lib.garbled_text_detection to analyze
    text quality based on entropy, symbol density, and character repetition.

    Args:
        page_region: PageRegion object from _analyze_pdf_block()
        config: Pipeline configuration

    Returns:
        PageRegion with populated quality_flags and quality_score (if garbled)
    """
    # Get full text from all spans
    full_text = page_region.get_text()

    if not full_text or len(full_text) < 10:
        # Too short to analyze reliably
        page_region.quality_flags = set()
        page_region.quality_score = 1.0
        return page_region

    # Create garbled detection config from pipeline config
    garbled_config = GarbledDetectionConfig(
        symbol_density_threshold=0.25,
        repetition_threshold=0.7,
        entropy_threshold=config.garbled_threshold,
        min_text_length=10
    )

    # Detect garbled text
    garbled_result = detect_garbled_text_enhanced(full_text, garbled_config)

    # Populate quality metadata
    if garbled_result.is_garbled:
        page_region.quality_flags = garbled_result.flags.copy()
        page_region.quality_score = 1.0 - garbled_result.confidence  # Convert to quality score (1.0 = perfect)

        logging.debug(f"Stage 1: Garbled text detected (confidence: {garbled_result.confidence:.2f}), "
                     f"flags: {garbled_result.flags}")
    else:
        page_region.quality_flags = set()
        page_region.quality_score = 1.0  # Perfect quality

    return page_region


def _stage_2_visual_analysis(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig,
    xmark_cache: dict = None
) -> tuple:
    """
    Stage 2: Detect X-marks/strikethrough via opencv.

    CRITICAL: Runs INDEPENDENTLY of Stage 1 (not conditionally).

    Rationale: Sous-rature PDFs often have CLEAN TEXT with VISUAL X-marks.
    If we only check garbled text, we miss clean sous-rature!

    Design Change (2025-10-18): Originally designed to run only on garbled text,
    but real PDF validation showed this misses sous-rature on clean text.
    Now runs on ALL regions (performance cost: ~5ms/region acceptable).

    Args:
        page_region: PageRegion from Stage 1 (with quality_flags)
        pdf_path: Path to PDF file for visual analysis
        page_num: Page number (0-indexed)
        config: Pipeline configuration
        xmark_cache: Optional cache of X-mark detection results

    Returns:
        Tuple of (PageRegion, XMarkDetectionResult)
        PageRegion with 'sous_rature' flag if X-marks detected
        XMarkDetectionResult for use in Stage 3 recovery
    """
    # REMOVED: "Only run if garbled" check (2025-10-18 fix)
    # Sous-rature can appear on clean text, so always check for X-marks

    # Initialize quality_flags if not set (may be None from Stage 1 if text clean)
    if page_region.quality_flags is None:
        page_region.quality_flags = set()

    xmark_result = None

    # Check if opencv available (use facade for test mockability)
    _XMARK_AVAILABLE = getattr(_get_facade(), 'XMARK_AVAILABLE', XMARK_AVAILABLE)
    if not _XMARK_AVAILABLE:
        logging.warning("X-mark detection requested but opencv not available")
        page_region.quality_flags.add('xmark_detection_unavailable')
        return page_region, None

    try:
        from lib.strikethrough_detection import detect_strikethrough_enhanced, XMarkDetectionConfig

        # Page-level caching: Detect once per page, reuse for all blocks
        if xmark_cache is not None and page_num in xmark_cache:
            # Use cached result
            xmark_result = xmark_cache[page_num]
            logging.debug(f"Stage 2: Using cached X-mark detection for page {page_num}")
        else:
            # Configure X-mark detection
            xmark_config = XMarkDetectionConfig(
                min_line_length=10,
                diagonal_tolerance=15,  # degrees from 45
                proximity_threshold=20,  # pixels
                confidence_threshold=0.5
            )

            # Detect X-marks in entire page (not just region bbox)
            xmark_result = detect_strikethrough_enhanced(pdf_path, page_num, bbox=None, config=xmark_config)

            # Cache result for this page
            if xmark_cache is not None:
                xmark_cache[page_num] = xmark_result
                logging.debug(f"Stage 2: Cached X-mark detection for page {page_num} (found {xmark_result.xmark_count})")

        # Check if ANY X-marks on page (cached result is page-level)
        # For block-level precision, could check bbox overlap, but for now use page-level

        # If X-marks found, this is sous-rature (needs recovery in Stage 3!)
        if xmark_result.has_xmarks:
            page_region.quality_flags.add('sous_rature')
            page_region.quality_flags.add('strikethrough')  # For is_strikethrough() check
            page_region.quality_flags.add('intentional_deletion')
            page_region.quality_score = 1.0  # Perfect quality (philosophical content)

            logging.info(f"Stage 2: Sous-rature detected on page {page_num} "
                        f"({xmark_result.xmark_count} X-marks, confidence: {xmark_result.confidence:.2f})")
            # Continue to Stage 3 for text recovery!

        logging.debug(f"Stage 2: X-mark detection complete, has_xmarks={xmark_result.has_xmarks}")

    except Exception as e:
        logging.error(f"Stage 2: X-mark detection error: {e}", exc_info=True)
        page_region.quality_flags.add('xmark_detection_error')

    return page_region, xmark_result


def _stage_3_ocr_recovery(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig,
    ocr_cache: dict = None,
    xmark_result: 'XMarkDetectionResult' = None
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
                # OCR entire page at high resolution
                pix = page.get_pixmap(dpi=300)
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
    import re

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


def _apply_quality_pipeline(
    page_region: PageRegion,
    pdf_path: Path,
    page_num: int,
    config: QualityPipelineConfig,
    xmark_cache: dict = None,
    ocr_cache: dict = None
) -> PageRegion:
    """
    Apply sequential waterfall quality pipeline to a PageRegion.

    Stages:
    1. Statistical Detection - Analyze text for garbled patterns
    2. Visual Analysis - Check for X-marks/strikethrough
    3. OCR Recovery - Recover text under X-marks OR garbled text

    CRITICAL: Stage 3 now runs for BOTH sous-rature AND corruption:
    - If X-marks: Recover text UNDER X-marks (sous-rature)
    - If garbled (no X-marks): Replace with OCR'd text (corruption)

    See: docs/specifications/PHASE_2_INTEGRATION_SPECIFICATION.md

    Args:
        page_region: PageRegion object from _analyze_pdf_block()
        pdf_path: Path to PDF file for visual/OCR analysis
        page_num: Page number (0-indexed)
        config: Pipeline configuration (feature flags, thresholds)
        xmark_cache: Optional cache of X-mark detection results
        ocr_cache: Optional cache of OCR results

    Returns:
        PageRegion with populated quality_flags and quality_score
    """
    if not config.enable_pipeline:
        return page_region

    # Stage 1: Statistical Detection
    if config.detect_garbled:
        page_region = _stage_1_statistical_detection(page_region, config)

    # Stage 2: Visual X-mark Detection (INDEPENDENT - not conditional on Stage 1)
    # CRITICAL FIX (2025-10-18): Sous-rature has clean text with visual X-marks.
    # Running only on garbled text misses clean sous-rature! Run unconditionally.
    # OPTIMIZATION (2025-10-18): Uses page-level caching to avoid redundant detection
    xmark_result = None
    if config.detect_strikethrough:
        page_region, xmark_result = _stage_2_visual_analysis(
            page_region, pdf_path, page_num, config, xmark_cache
        )

    # Stage 3: OCR Recovery
    # CRITICAL (2025-10-18): TWO recovery paths:
    # 1. Sous-rature: Recover text UNDER X-marks (even if text looks clean)
    # 2. Corruption: Replace garbled text with OCR
    if config.enable_ocr_recovery:
        # Path 1: Sous-rature recovery (has X-marks)
        if page_region.is_strikethrough():
            page_region = _stage_3_ocr_recovery(
                page_region, pdf_path, page_num, config, ocr_cache, xmark_result
            )
        # Path 2: Corruption recovery (garbled, no X-marks)
        elif page_region.is_garbled():
            page_region = _stage_3_ocr_recovery(
                page_region, pdf_path, page_num, config, ocr_cache, xmark_result
            )

    return page_region
