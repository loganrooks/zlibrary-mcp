"""
RAG document processing - backward-compatible facade.

All implementation lives in lib/rag/ subpackages. This module re-exports
all public and semi-private API functions to maintain backward compatibility
with python_bridge.py and all test files.
"""
import asyncio
import re
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple
import aiofiles
import unicodedata
import os
import io
import string
import collections
import json
import sys
import subprocess
import tempfile
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================================
# Phase 4: Extracted modules (lib/rag/)
# ============================================================================
from lib.rag.utils.constants import (
    SUPPORTED_FORMATS, PROCESSED_OUTPUT_DIR,
    _PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY, _PDF_QUALITY_THRESHOLD_LOW_DENSITY,
    _PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO, _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO,
    _PDF_QUALITY_MIN_SPACE_RATIO, STRATEGY_CONFIGS,
)
from lib.rag.utils.exceptions import TesseractNotFoundError, FileSaveError, OCRDependencyError
from lib.rag.utils.text import _slugify, _html_to_text, _apply_formatting_to_text
from lib.rag.utils.cache import _TEXTPAGE_CACHE, _get_cached_text_blocks, _clear_textpage_cache
from lib.rag.utils.header import (
    _generate_document_header, _generate_markdown_toc_from_pdf,
    _find_first_content_page, _extract_publisher_from_front_matter,
)

# Phase 4: Extracted detection and OCR modules
from lib.rag.detection.headings import _analyze_font_distribution, _detect_headings_from_fonts
from lib.rag.detection.toc import (
    _extract_toc_from_pdf, _identify_and_remove_front_matter,
    _format_toc_lines_as_markdown, _extract_and_format_toc,
)
from lib.rag.detection.page_numbers import (
    _extract_written_page_number, _roman_to_int, _int_to_roman,
    _is_roman_numeral, _detect_written_page_on_page, infer_written_page_numbers,
)
from lib.rag.detection.footnotes import (
    _footnote_with_continuation_to_dict, _starts_with_marker,
    _extract_text_from_block, _merge_bboxes, _markers_are_equivalent,
    _find_definition_for_marker, _find_markerless_content,
    _calculate_page_normal_font_size, _is_superscript,
    _detect_footnotes_in_page, _format_footnotes_markdown,
)
from lib.rag.ocr.spacing import detect_letter_spacing_issue, correct_letter_spacing
from lib.rag.ocr.corruption import _is_ocr_corrupted

# Phase 4 Wave 2: Quality, xmark, processors, orchestrator
from lib.rag.quality.analysis import (
    detect_pdf_quality, _analyze_pdf_block, _determine_pdf_quality_category,
)
from lib.rag.quality.pipeline import (
    QualityPipelineConfig,
    _stage_1_statistical_detection,
    _stage_2_visual_analysis,
    _stage_3_ocr_recovery,
    _find_word_between_contexts,
    _apply_quality_pipeline,
)
from lib.rag.ocr.recovery import (
    run_ocr_on_pdf, assess_pdf_ocr_quality, redo_ocr_with_tesseract,
)
from lib.rag.xmark.detection import (
    _detect_xmarks_parallel, _detect_xmarks_single_page,
    _page_needs_xmark_detection_fast, _should_enable_xmark_detection_for_document,
)
from lib.rag.processors.pdf import _format_pdf_markdown
from lib.rag.processors.epub import _epub_node_to_markdown, process_epub
from lib.rag.processors.txt import process_txt
from lib.rag.orchestrator import process_pdf, process_document, save_processed_text


# Phase 2: Enhanced data model imports for structured RAG output
from lib.rag_data_models import (
    TextSpan,
    PageRegion,
    ListInfo,
    create_text_span_from_pymupdf
)

# Phase 2: Formatting group merger for correct markdown generation
from lib.formatting_group_merger import FormattingGroupMerger

# Phase 2.6: Footnote corruption recovery (Bayesian symbol inference)
from lib.footnote_corruption_model import (
    SymbolCorruptionModel,
    FootnoteSchemaValidator,
    apply_corruption_recovery,
    SymbolInference
)

# Phase 3: Note classification (author/translator/editor attribution)
from lib.note_classification import classify_note_comprehensive

# Phase 3: Multi-page footnote continuation tracking
from lib.footnote_continuation import (
    CrossPageFootnoteParser,
    is_footnote_incomplete,
    FootnoteWithContinuation
)

# Phase 2.2: Garbled text detection (extracted to separate module)
from lib.garbled_text_detection import (
    detect_garbled_text,
    detect_garbled_text_enhanced,
    GarbledDetectionConfig,
    GarbledDetectionResult
)

from filename_utils import create_unified_filename, create_metadata_filename
from metadata_generator import (
    generate_metadata_sidecar,
    save_metadata_sidecar,
    add_yaml_frontmatter_to_content
)
from metadata_verification import (
    extract_pdf_metadata,
    extract_epub_metadata,
    extract_txt_metadata,
    verify_metadata
)

# Check if libraries are available
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
    from bs4 import BeautifulSoup, NavigableString
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    BeautifulSoup = None
    NavigableString = None

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

__all__ = [
    # Public API
    'process_pdf', 'process_epub', 'process_txt', 'process_document', 'save_processed_text',
    'detect_pdf_quality', 'run_ocr_on_pdf', 'assess_pdf_ocr_quality', 'redo_ocr_with_tesseract',
    'detect_letter_spacing_issue', 'correct_letter_spacing',
    'QualityPipelineConfig', 'SUPPORTED_FORMATS', 'PROCESSED_OUTPUT_DIR',
    'TesseractNotFoundError', 'FileSaveError', 'OCRDependencyError',
    # Semi-private (used by tests)
    '_analyze_pdf_block', '_format_pdf_markdown', '_epub_node_to_markdown',
    '_detect_footnotes_in_page', '_calculate_page_normal_font_size', '_is_superscript',
    '_format_footnotes_markdown', '_find_definition_for_marker',
    '_footnote_with_continuation_to_dict', '_extract_and_format_toc',
    '_identify_and_remove_front_matter', '_extract_publisher_from_front_matter',
    '_is_ocr_corrupted', '_slugify', '_html_to_text', 'infer_written_page_numbers',
    '_determine_pdf_quality_category',
    '_apply_quality_pipeline', '_stage_1_statistical_detection',
    '_stage_2_visual_analysis', '_stage_3_ocr_recovery',
    '_detect_xmarks_parallel', '_detect_xmarks_single_page',
    '_page_needs_xmark_detection_fast', '_should_enable_xmark_detection_for_document',
    '_find_word_between_contexts',
    'STRATEGY_CONFIGS',
    # Re-exported external dependencies for test mocking
    'detect_garbled_text', 'detect_garbled_text_enhanced',
    'GarbledDetectionConfig', 'GarbledDetectionResult',
]
