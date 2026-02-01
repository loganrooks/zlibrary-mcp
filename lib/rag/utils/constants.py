"""
Constants for RAG processing.

Contains format definitions, quality thresholds, output directories,
and strategy configuration profiles.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    'SUPPORTED_FORMATS',
    'PROCESSED_OUTPUT_DIR',
    '_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY',
    '_PDF_QUALITY_THRESHOLD_LOW_DENSITY',
    '_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO',
    '_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO',
    '_PDF_QUALITY_MIN_SPACE_RATIO',
    'STRATEGY_CONFIGS',
]

# Constants
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf'] # Keep relevant constants? Or import? Keep for now.
# PDF Quality Thresholds
_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY = 10
_PDF_QUALITY_THRESHOLD_LOW_DENSITY = 50
_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO = 0.7
_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO = 0.15
_PDF_QUALITY_MIN_SPACE_RATIO = 0.05
PROCESSED_OUTPUT_DIR = Path("./processed_rag_output")

# ============================================================================
# Phase 2: Quality Pipeline Configuration (Integration 2025-10-18)
# ============================================================================

# Strategy profiles for quality pipeline
# See: docs/specifications/PHASE_2_INTEGRATION_SPECIFICATION.md
STRATEGY_CONFIGS = {
    'philosophy': {
        'garbled_threshold': 0.9,        # Very conservative (preserve ambiguous text)
        'recovery_threshold': 0.95,      # Almost never auto-recover
        'enable_strikethrough': True,    # Always check for sous-rature
        'priority': 'preservation'       # Err on side of keeping original
    },
    'technical': {
        'garbled_threshold': 0.6,        # Aggressive detection
        'recovery_threshold': 0.7,       # More likely to recover
        'enable_strikethrough': False,   # Technical docs rarely have strikethrough
        'priority': 'quality'            # Err on side of recovery
    },
    'hybrid': {  # DEFAULT
        'garbled_threshold': 0.75,       # Balanced
        'recovery_threshold': 0.8,       # Moderate confidence required
        'enable_strikethrough': True,    # Check for visual markers
        'priority': 'balanced'           # Case-by-case decisions
    }
}
