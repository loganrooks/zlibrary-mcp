"""
PDF quality analysis and block-level structure detection.

Contains functions for analyzing PDF text quality, determining quality
categories, and analyzing individual text blocks for structure inference.
"""
import logging
import os
import re
from typing import Optional

from lib.rag.utils.constants import (
    _PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY,
    _PDF_QUALITY_THRESHOLD_LOW_DENSITY,
    _PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO,
    _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO,
    _PDF_QUALITY_MIN_SPACE_RATIO,
)

logger = logging.getLogger(__name__)

__all__ = [
    'detect_pdf_quality',
    '_analyze_pdf_block',
    '_determine_pdf_quality_category',
]

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None


def _get_fitz():
    """Get fitz module through facade for test mockability."""
    import lib.rag_processing as _rp
    return getattr(_rp, 'fitz', fitz)


def _get_pymupdf_available():
    """Get PYMUPDF_AVAILABLE through facade for test mockability."""
    import lib.rag_processing as _rp
    return getattr(_rp, 'PYMUPDF_AVAILABLE', PYMUPDF_AVAILABLE)

# Phase 2: Enhanced data model imports for structured RAG output
from lib.rag_data_models import (
    TextSpan,
    PageRegion,
    ListInfo,
    create_text_span_from_pymupdf
)


def _analyze_pdf_block(
    block: dict,
    preserve_linebreaks: bool = False,
    detect_headings: bool = True,
    return_structured: bool = None
) -> dict:  # Can return dict or PageRegion depending on flag
    """
    Analyzes a PyMuPDF text block dictionary to infer structure.

    Infers heading level, list item status/type based on font size, flags,
    and text patterns. NOTE: These are heuristics and may require tuning.

    Args:
        block: A dictionary representing a text block from page.get_text("dict").
        preserve_linebreaks: If True, preserve original line breaks from PDF (for citation accuracy).
                           If False, join lines intelligently (for readability).
        detect_headings: If True, use font-size heuristics to detect headings.
                        If False, skip heading detection (use when ToC metadata is available).
        return_structured: If True, return PageRegion object with TextSpan list.
                          If False, return legacy dict format.
                          If None, defaults to RAG_USE_STRUCTURED_DATA env var (default 'true').

    Returns:
        PageRegion object if return_structured=True, dict otherwise.
        Legacy dict contains: 'heading_level', 'is_list_item', 'list_type', 'list_indent', 'text', 'spans'.
    """
    # Feature flag: default to structured output per Phase 2 design
    if return_structured is None:
        return_structured = os.getenv('RAG_USE_STRUCTURED_DATA', 'true').lower() == 'true'

    # Heuristic logic based on font size, flags, position, text patterns
    heading_level = 0
    is_list_item = False
    list_type = None # 'ul' or 'ol'
    list_indent = 0 # Placeholder
    list_marker = None # Initialize list_marker
    text_content = ""
    spans = []

    if block.get('type') == 0: # Text block
        # Aggregate text and span info
        # Handle line breaks intelligently to avoid word concatenation
        line_texts = []
        for line in block.get('lines', []):
            line_spans = []
            for span in line.get('spans', []):
                spans.append(span)
                line_spans.append(span.get('text', ''))

            # Join spans within a line - add space between spans to prevent concatenation
            # (PDF spans can represent separate words/phrases on the same line)
            line_text = ' '.join(line_spans)
            # Clean up multiple spaces that might result from empty spans or formatting
            line_text = re.sub(r'\s+', ' ', line_text)
            if line_text:
                line_texts.append(line_text)

        # Join lines based on mode:
        # Citation mode (preserve_linebreaks=True): Keep original line breaks for accurate citations
        # RAG mode (preserve_linebreaks=False): Join intelligently for readability
        if preserve_linebreaks:
            # Keep line breaks as-is for citation accuracy
            text_content = '\n'.join(line_texts)
        else:
            # Join lines intelligently:
            # - If line ends with hyphen, join next line without space (word continuation)
            # - Otherwise, add space between lines
            text_content = ""
            for i, line_text in enumerate(line_texts):
                if i == 0:
                    text_content = line_text
                else:
                    # Check if previous line ended with hyphen (word break)
                    if text_content.endswith('-'):
                        # Remove hyphen and join directly (e.g., "infor-\nmative" -> "informative")
                        text_content = text_content[:-1] + line_text
                    else:
                        # Add space between lines (e.g., "most\naccurate" -> "most accurate")
                        text_content += ' ' + line_text

            # Clean up any multiple spaces that may have resulted
            text_content = re.sub(r'\s+', ' ', text_content)

        # Apply cleaning (null chars, headers/footers) *before* analysis
        text_content = text_content.replace('\x00', '') # Remove null chars first
        header_footer_patterns = [
            # Existing patterns
            re.compile(r"^(JSTOR.*|Downloaded from.*|Copyright ©.*)\n?", re.IGNORECASE | re.MULTILINE),
            re.compile(r"^Page \d+\s*\n?", re.MULTILINE),
            # Added: Pattern to catch lines containing 'Page X' variations, potentially with other text
            re.compile(r"^(.*\bPage \d+\b.*)\n?", re.IGNORECASE | re.MULTILINE)
        ]
        for pattern in header_footer_patterns:
            text_content = pattern.sub('', text_content)
        text_content = re.sub(r'\n\s*\n', '\n\n', text_content).strip() # Consolidate blank lines

        if not text_content: # If cleaning removed everything, return early
             return {
                'heading_level': 0, 'list_marker': None, 'is_list_item': False,
                'list_type': None, 'list_indent': 0, 'text': '', 'spans': spans
             }

        if spans:
            first_span = spans[0]
            font_size = first_span.get('size', 10)
            flags = first_span.get('flags', 0)
            is_bold = flags & 2 # Font flag for bold

            # --- Heading Heuristic (Example based on size/boldness) ---
            # Only apply if detect_headings is True (when ToC is unavailable)
            # Filter out pure page numbers (don't treat "420" as a heading)
            trimmed_text = text_content.strip()
            is_pure_number = re.match(r'^\d+$', trimmed_text)

            if detect_headings and not is_pure_number:
                # Reordered to check more specific conditions first
                if font_size > 12 and font_size <= 14 and is_bold: # H3
                     heading_level = 3
                elif font_size > 11 and font_size <= 12 and is_bold: # H3
                     heading_level = 3
                elif font_size > 14 and font_size <= 18 and is_bold: # H2
                     heading_level = 2
                elif font_size > 12 and font_size <= 14: # H3
                     heading_level = 3
                elif font_size > 14 and font_size <= 18: # H2
                     heading_level = 2
                elif font_size > 18: # H1
                     heading_level = 1

                # --- Validate heading characteristics to filter false positives ---
                if heading_level > 0:
                    # Filter 1: Text too long (headings are typically < 150 chars)
                    if len(trimmed_text) > 150:
                        heading_level = 0
                    # Filter 2: Ends with period (typical paragraph, unless it's a colon for sections)
                    elif trimmed_text.endswith('.') and not trimmed_text.endswith(':.'):
                        heading_level = 0
                    # Filter 3: Colon-ending text that's too long (> 50 chars) is likely a paragraph lead-in
                    elif trimmed_text.endswith(':') and len(trimmed_text) > 50:
                        heading_level = 0
                    # Filter 4: List introduction patterns (e.g., "There are four main reasons:")
                    elif re.match(r'^(There are|Here are|These are|Following are)\s', trimmed_text, re.IGNORECASE):
                        heading_level = 0
                    # Filter 5: Multiple sentences (count sentence-ending punctuation)
                    else:
                        sentence_enders = trimmed_text.count('.') + trimmed_text.count('?') + trimmed_text.count('!')
                        # Exclude periods in abbreviations (e.g., "Ph.D.", "U.S.") by checking spacing
                        # Simple heuristic: if more than 2 sentence enders, likely a paragraph
                        if sentence_enders > 2:
                            heading_level = 0
            # If is_pure_number, heading_level stays 0

            # --- List Heuristic (Example based on starting characters) ---
            # This is basic and doesn't handle indentation/nesting reliably.
            trimmed_text = text_content.strip()
            list_marker = None # Store the detected marker/number

            # Unordered list check (common bullet characters)
            ul_match = re.match(r"^([\*\u2022\u2013-])\s+", trimmed_text) # Added en-dash
            if ul_match:
                is_list_item = True
                list_type = 'ul'
                list_marker = ul_match.group(1)
                # Indentation could be inferred from block['bbox'][0] (x-coordinate)

            # Ordered list check (e.g., "1. ", "a) ", "i. ") - More robust
            ol_match = re.match(r"^(\d+|[a-zA-Z]|[ivxlcdm]+)[\.\)]\s+", trimmed_text, re.IGNORECASE)
            if not is_list_item and ol_match: # Check only if not already identified as UL
                is_list_item = True
                list_type = 'ol'
                list_marker = ol_match.group(1) # Capture number/letter/roman numeral

            # FUTURE: Use block['bbox'][0] (x-coordinate) to infer indentation/nesting.
            # Deferred - low priority enhancement for complex nested lists.

    # Phase 2: Conditional return based on feature flag
    if return_structured:
        # Convert PyMuPDF span dicts to TextSpan objects
        text_spans = [create_text_span_from_pymupdf(span) for span in spans]

        # Create ListInfo if this is a list item
        list_info_obj = None
        if is_list_item:
            list_info_obj = ListInfo(
                is_list_item=True,
                list_type=list_type if list_type else 'ul',  # Default to 'ul' if not set
                marker=list_marker if list_marker else '',
                indent_level=list_indent
            )

        # Get bounding box from block
        bbox = tuple(block.get('bbox', (0.0, 0.0, 0.0, 0.0)))

        # Return structured PageRegion object
        return PageRegion(
            region_type='body',  # Default region type for now
            spans=text_spans,
            bbox=bbox,
            page_num=0,  # Default, caller can override if needed
            heading_level=heading_level if heading_level > 0 else None,
            list_info=list_info_obj
        )
    else:
        # Legacy dict return for backward compatibility
        return {
            'heading_level': heading_level,
            'list_marker': list_marker,
            'is_list_item': is_list_item,
            'list_type': list_type,
            'list_indent': list_indent,
            'text': text_content.strip(),
            'spans': spans  # Pass raw PyMuPDF spans for legacy callers
        }


def detect_pdf_quality(pdf_path: str) -> dict: # Renamed from _analyze_pdf_quality
    """
    Analyzes a PDF to determine text quality and recommend OCR if needed.

    Returns a dictionary with 'quality_category' ('TEXT_HIGH', 'TEXT_LOW', 'IMAGE_ONLY', 'MIXED', 'EMPTY', 'ENCRYPTED'),
    'ocr_needed' (boolean), and 'reason' (string).
    """
    _fitz = _get_fitz()
    if not _get_pymupdf_available() or _fitz is None:
        return {'quality_category': 'UNKNOWN', 'ocr_needed': False, 'reason': 'PyMuPDF not available'}

    doc = None
    try:
        doc = _fitz.open(pdf_path)
        if doc.is_encrypted:
            # Try decrypting with empty password
            if not doc.authenticate(""):
                logging.warning(f"PDF {pdf_path} is encrypted and password protected.")
                return {'quality_category': 'ENCRYPTED', 'ocr_needed': False, 'reason': 'PDF is encrypted'}
            logging.info(f"Successfully decrypted {pdf_path} with empty password.")

        page_count = len(doc)
        if page_count == 0:
            logging.warning(f"PDF {pdf_path} has 0 pages.")
            return {'quality_category': 'EMPTY', 'ocr_needed': False, 'reason': 'PDF has no pages'}

        total_chars = 0
        total_image_area = 0
        total_page_area = 0
        unique_chars = set()

        for page in doc:
            page_area = page.rect.width * page.rect.height
            if page_area <= 0: continue # Skip pages with no area

            total_page_area += page_area

            # Text analysis
            text = page.get_text("text")
            page_chars = len(text)
            total_chars += page_chars
            unique_chars.update(text)

            # Image analysis
            # Use page.get_images(full=True) instead of get_image_rects
            img_list = page.get_images(full=True)
            # Img tuple format: (xref, smask, width, height, ...)
            # Calculate area using width (index 2) and height (index 3)
            page_image_area = sum(img[2] * img[3] for img in img_list if len(img) >= 4) # Ensure tuple has enough elements
            total_image_area += page_image_area

        avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
        image_ratio = total_image_area / total_page_area if total_page_area > 0 else 0
        char_diversity_ratio = len(unique_chars) / total_chars if total_chars > 0 else 0
        space_ratio = sum(1 for char in "".join(unique_chars) if char.isspace()) / len(unique_chars) if unique_chars else 0


        # Determine category based on heuristics
        category, reason, ocr_needed = _determine_pdf_quality_category(
            avg_chars_per_page, image_ratio, char_diversity_ratio, space_ratio
        )

        return {'quality_category': category, 'ocr_needed': ocr_needed, 'reason': reason}

    except Exception as e:
        logging.error(f"Error analyzing PDF quality for {pdf_path}: {e}", exc_info=True)
        # Check if error suggests encryption
        if "encrypted" in str(e).lower():
             return {'quality_category': 'ENCRYPTED', 'ocr_needed': False, 'reason': f'Error opening PDF (likely encrypted): {e}'}
        return {'quality_category': 'ERROR', 'ocr_needed': False, 'reason': f'Error analyzing PDF: {e}'}
    finally:
        # Close document if it exists and is not already closed
        if doc is not None and not doc.is_closed:
            doc.close()

def _determine_pdf_quality_category(
    avg_chars: float, img_ratio: float, char_diversity: float, space_ratio: float
) -> tuple[str, str, bool]:
    """Helper function to determine PDF quality category based on metrics."""
    # Check for high image ratio first
    if img_ratio > _PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO:
         # If significant image area, but also some text, classify as MIXED
         # If text quality is also low, still recommend OCR
         ocr_rec = avg_chars < _PDF_QUALITY_THRESHOLD_LOW_DENSITY or \
                   char_diversity < _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO or \
                   space_ratio < _PDF_QUALITY_MIN_SPACE_RATIO
         reason = f'High image ratio ({img_ratio:.2f} > {_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO})'
         if ocr_rec:
             reason += f' and low text quality indicators (avg_chars={avg_chars:.1f}, diversity={char_diversity:.2f}, space={space_ratio:.2f})'
         return 'MIXED', reason, ocr_rec
    # Only check for IMAGE_ONLY if image ratio is not high
    elif avg_chars < _PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY:
        return 'IMAGE_ONLY', f'Very low average characters per page ({avg_chars:.1f} < {_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY})', True
    elif avg_chars < _PDF_QUALITY_THRESHOLD_LOW_DENSITY or \
         char_diversity < _PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO or \
         space_ratio < _PDF_QUALITY_MIN_SPACE_RATIO:
        return 'TEXT_LOW', f'Low average characters per page ({avg_chars:.1f} < {_PDF_QUALITY_THRESHOLD_LOW_DENSITY}) or low char diversity ({char_diversity:.2f} < {_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO}) or low space ratio ({space_ratio:.2f} < {_PDF_QUALITY_MIN_SPACE_RATIO})', True
    else:
        return 'TEXT_HIGH', f'Sufficient average characters per page ({avg_chars:.1f}) and low image ratio ({img_ratio:.2f})', False
