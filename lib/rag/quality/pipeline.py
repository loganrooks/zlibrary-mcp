"""
Quality pipeline for RAG processing.

Contains the multi-stage quality pipeline (statistical detection, visual analysis,
OCR recovery) and the QualityPipelineConfig configuration class.

OCR recovery (Stage 3) and word-finding helper are in ocr_stage.py.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

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

# Re-export from ocr_stage submodule
from lib.rag.quality.ocr_stage import (
    _stage_3_ocr_recovery,
    _find_word_between_contexts,
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
