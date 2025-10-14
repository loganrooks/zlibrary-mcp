import asyncio
import re
import logging
from pathlib import Path
import aiofiles
import unicodedata # Added for slugify
import os # Ensure os is imported if needed for path manipulation later
import io # Added for OCR image handling
import string # Added for garbled text detection
import collections # Added for garbled text detection
import json # For metadata sidecar generation
import sys # For path manipulation
import subprocess # For ocrmypdf integration
import tempfile # For temporary OCR file handling
sys.path.insert(0, str(Path(__file__).parent))
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
# Define placeholder initially, overwrite if import succeeds
class TesseractNotFoundError(Exception): pass

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image # Added for OCR image handling
    OCR_AVAILABLE = True
    # If import succeeds, use the actual exception
    TesseractNotFoundError = pytesseract.TesseractNotFoundError
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None
    convert_from_path = None
    Image = None
    # Placeholder is already defined outside
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup, NavigableString # Added NavigableString
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False
    BeautifulSoup = None # Define as None if not available
    NavigableString = None # Define as None if not available

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None # Define as None if not available

# Custom Exception (Consider moving if used elsewhere, but keep here for now)
class FileSaveError(Exception):
    """Custom exception for errors during processed file saving."""
    pass

# Custom Exception for Dependency Issues
class OCRDependencyError(Exception): pass

# Constants
SUPPORTED_FORMATS = ['.epub', '.txt', '.pdf'] # Keep relevant constants? Or import? Keep for now.
# PDF Quality Thresholds
_PDF_QUALITY_THRESHOLD_VERY_LOW_DENSITY = 10
_PDF_QUALITY_THRESHOLD_LOW_DENSITY = 50
_PDF_QUALITY_THRESHOLD_HIGH_IMAGE_RATIO = 0.7
_PDF_QUALITY_MIN_CHAR_DIVERSITY_RATIO = 0.15
_PDF_QUALITY_MIN_SPACE_RATIO = 0.05
PROCESSED_OUTPUT_DIR = Path("./processed_rag_output")

# --- Slugify Helper ---

def _slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value).lower() # Ensure string and lowercase
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
        # Replace non-word chars (letters, numbers, underscore) with a space
        value = re.sub(r'[^\w]', ' ', value)
    else:
        # ASCII path: Normalize, encode/decode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        # Replace non a-z0-9 chars (including underscore) with a space
        value = re.sub(r'[^a-z0-9]', ' ', value)

    # Collapse consecutive whitespace to single hyphen
    value = re.sub(r'\s+', '-', value)
    # Strip leading/trailing hyphens
    value = value.strip('-')

    # Ensure slug is not empty, default to 'file' if it becomes empty
    return value if value else 'file'

# --- PDF Markdown Helpers ---

def _analyze_pdf_block(block: dict, preserve_linebreaks: bool = False, detect_headings: bool = True) -> dict:
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

    Returns:
        A dictionary containing analysis results:
        'heading_level', 'is_list_item', 'list_type', 'list_indent', 'text', 'spans'.
    """
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
                        # Remove hyphen and join directly (e.g., "infor-\nmative" → "informative")
                        text_content = text_content[:-1] + line_text
                    else:
                        # Add space between lines (e.g., "most\naccurate" → "most accurate")
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
            ul_match = re.match(r"^([\*•–-])\s+", trimmed_text) # Added en-dash
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

            # TODO: Use block['bbox'][0] (x-coordinate) to infer indentation/nesting.

    return {
        'heading_level': heading_level,
        'list_marker': list_marker, # Add marker to return dict
        'is_list_item': is_list_item,
        'list_type': list_type,
        'list_indent': list_indent, # Placeholder for future nesting use
        'text': text_content.strip(),
        'spans': spans # Pass spans for footnote detection
    }

def _analyze_font_distribution(doc: 'fitz.Document', sample_pages: int = 10) -> float:
    """
    Analyze font size distribution across document to identify body text size.

    Uses statistical mode of font sizes from a sample of pages to determine
    the most common text size (body text). This serves as a baseline for
    detecting headings via relative size comparison.

    Args:
        doc: PyMuPDF document object
        sample_pages: Number of pages to sample (default: 10, max: total pages)

    Returns:
        float: Mode (most common) font size in points, or 10.0 if analysis fails
    """
    from collections import Counter

    font_sizes = []
    total_pages = len(doc)
    pages_to_sample = min(sample_pages, total_pages)

    # Sample pages evenly throughout document
    if total_pages <= sample_pages:
        page_indices = range(total_pages)
    else:
        # Spread samples evenly: beginning, middle, end
        step = total_pages // sample_pages
        page_indices = range(0, total_pages, step)[:sample_pages]

    logging.debug(f"Analyzing font distribution across {pages_to_sample} pages")

    try:
        for page_num in page_indices:
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = span.get("size")
                            text = span.get("text", "").strip()

                            # Only count substantial text (ignore page numbers, isolated chars)
                            if size and text and len(text) >= 3:
                                # Round to nearest 0.5 to group similar sizes
                                font_sizes.append(round(size * 2) / 2)

        if not font_sizes:
            logging.warning("No font sizes extracted, using default body size of 10.0")
            return 10.0

        # Find mode (most common font size)
        size_counts = Counter(font_sizes)
        body_size = size_counts.most_common(1)[0][0]

        logging.info(f"Detected body text size: {body_size}pt "
                    f"(from {len(font_sizes)} text spans, "
                    f"top 3 sizes: {size_counts.most_common(3)})")

        return body_size

    except Exception as e:
        logging.warning(f"Error analyzing font distribution: {e}, using default 10.0")
        return 10.0


def _detect_headings_from_fonts(
    doc: 'fitz.Document',
    body_size: float,
    threshold: float = 1.15,
    min_heading_length: int = 3,
    max_heading_length: int = 150
) -> dict:
    """
    Detect headings across all pages using font-based heuristics.

    Identifies potential headings by comparing font sizes against the body text
    baseline. Larger font sizes indicate higher-level headings. Includes filters
    to reduce false positives (page numbers, short text, overly long text).

    Algorithm:
    1. Scan all text spans in document
    2. Compare each span's font size to body_size
    3. If size >= body_size * threshold, consider as heading
    4. Assign heading level based on relative size (larger = higher level)
    5. Filter false positives based on length, content patterns

    Args:
        doc: PyMuPDF document object
        body_size: Mode font size from _analyze_font_distribution (body text baseline)
        threshold: Multiplier for minimum heading size (default: 1.15 = 15% larger)
        min_heading_length: Minimum characters for valid heading (default: 3)
        max_heading_length: Maximum characters for valid heading (default: 150)

    Returns:
        dict: Maps page_number (1-indexed) to list of (level, title) tuples
              Empty dict if no headings detected
    """
    toc_map = {}
    min_heading_size = body_size * threshold

    logging.info(f"Detecting headings: body_size={body_size}pt, "
                f"min_heading_size={min_heading_size:.1f}pt "
                f"(threshold={threshold})")

    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
            page_headings = []

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            size = span.get("size", 0)
                            text = span.get("text", "").strip()
                            flags = span.get("flags", 0)
                            is_bold = bool(flags & 2)  # Font flag for bold

                            # Check if this span qualifies as a heading
                            if size >= min_heading_size and text:
                                # --- False Positive Filters ---

                                # Filter 1: Length constraints
                                if len(text) < min_heading_length or len(text) > max_heading_length:
                                    continue

                                # Filter 2: Pure numbers (likely page numbers)
                                if re.match(r'^\d+$', text):
                                    continue

                                # Filter 3: Roman numerals alone (likely page numbers)
                                if re.match(r'^[ivxlcdm]+$', text, re.IGNORECASE) and len(text) <= 5:
                                    continue

                                # Filter 4: Single letters or punctuation
                                if len(text) == 1:
                                    continue

                                # Filter 5: Mostly numbers/punctuation (e.g., "1.2.3", "---")
                                alpha_ratio = sum(c.isalpha() for c in text) / len(text)
                                if alpha_ratio < 0.5:
                                    continue

                                # --- Determine Heading Level ---
                                # Level based on relative font size (larger = higher level)
                                # Also consider bold formatting for disambiguation

                                size_ratio = size / body_size

                                if size_ratio >= 1.8:
                                    # 80%+ larger than body = H1
                                    level = 1
                                elif size_ratio >= 1.5:
                                    # 50-80% larger = H2
                                    level = 2
                                elif size_ratio >= 1.3:
                                    # 30-50% larger = H3 (or H2 if bold)
                                    level = 2 if is_bold else 3
                                elif size_ratio >= 1.15:
                                    # 15-30% larger = H3 (or H4 if not bold)
                                    level = 3 if is_bold else 4
                                else:
                                    # Below threshold (shouldn't happen due to initial check)
                                    continue

                                page_headings.append((level, text))

            # Add headings to map (use 1-indexed page numbers for consistency)
            if page_headings:
                toc_map[page_num + 1] = page_headings

        total_headings = sum(len(headings) for headings in toc_map.values())
        logging.info(f"Font-based detection found {total_headings} headings "
                    f"across {len(toc_map)} pages")

        # Log sample headings for validation
        if toc_map:
            sample_page = next(iter(toc_map))
            sample_headings = toc_map[sample_page][:3]
            logging.debug(f"Sample headings from page {sample_page}: {sample_headings}")

        return toc_map

    except Exception as e:
        logging.warning(f"Error detecting headings from fonts: {e}")
        return {}


def _extract_toc_from_pdf(doc: 'fitz.Document') -> dict:
    """
    Extract table of contents using hybrid approach: embedded metadata first,
    font-based heuristics as fallback.

    Strategy:
    1. Try embedded ToC from PDF metadata (doc.get_toc())
    2. If empty, analyze font distribution to find body text size
    3. Use font size heuristics to detect headings (15%+ larger than body)
    4. Build heading hierarchy based on relative font sizes

    Font-based detection achieves 70-85% accuracy based on research findings.
    Works best for PDFs with consistent heading formatting (size, boldness).

    Args:
        doc: PyMuPDF document object

    Returns:
        dict: Maps page_number (1-indexed) to list of (level, title) tuples
              Empty dict if no ToC available via either method
    """
    toc_map = {}

    # --- Phase 1: Try Embedded ToC (Primary Method) ---
    try:
        toc = doc.get_toc()  # Returns list of [level, title, page_num]
        if toc:
            for level, title, page_num in toc:
                if page_num not in toc_map:
                    toc_map[page_num] = []
                toc_map[page_num].append((level, title))

            logging.info(f"✓ Embedded ToC: {len(toc)} entries covering {len(toc_map)} pages")
            return toc_map
        else:
            logging.info("✗ No embedded ToC metadata found, trying font-based detection")

    except Exception as toc_err:
        logging.warning(f"✗ Error reading embedded ToC: {toc_err}, trying font-based detection")

    # --- Phase 2: Font-Based Heuristics (Fallback Method) ---
    try:
        # Step 1: Analyze font distribution to find body text size
        body_size = _analyze_font_distribution(doc, sample_pages=10)

        # Step 2: Detect headings using font size threshold (15% larger than body)
        toc_map = _detect_headings_from_fonts(
            doc,
            body_size=body_size,
            threshold=1.15,  # 15% larger than body text
            min_heading_length=3,
            max_heading_length=150
        )

        if toc_map:
            total_headings = sum(len(headings) for headings in toc_map.values())
            logging.info(f"✓ Font-based ToC: {total_headings} headings across {len(toc_map)} pages "
                        f"(body_size={body_size:.1f}pt)")
        else:
            logging.info("✗ Font-based detection found no headings")

        return toc_map

    except Exception as font_err:
        logging.warning(f"✗ Font-based ToC detection failed: {font_err}")
        return {}


def _extract_written_page_number(page: 'fitz.Page') -> str:
    """
    Try to extract the written page number from a page (e.g., "xxiii", "15", "A-3").
    
    Checks:
    - First line of page (header position)
    - Last line of page (footer position)
    
    Returns:
        Written page number as string, or None if not found
    """
    try:
        text = page.get_text('text')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return None
        
        # Check first line (common header position)
        first_line = lines[0]
        if first_line.isdigit() or re.match(r'^[ivxlc]+$', first_line, re.IGNORECASE):
            return first_line
        
        # Check last line (common footer position)
        last_line = lines[-1]
        if last_line.isdigit() or re.match(r'^[ivxlc]+$', last_line, re.IGNORECASE):
            return last_line
        
        # Check for patterns like "Page 15" or "p. 15"
        for line in [first_line, last_line]:
            match = re.search(r'\b(?:page|p\.?)\s*(\d+)\b', line, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    except Exception as e:
        logging.debug(f"Error extracting written page number: {e}")
        return None


def _roman_to_int(roman: str) -> int:
    """Convert roman numeral to integer (e.g., 'xxiii' -> 23)."""
    roman_map = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
    roman = roman.lower()
    total = 0
    prev_value = 0
    
    for char in reversed(roman):
        value = roman_map.get(char, 0)
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value
    
    return total


def _int_to_roman(num: int) -> str:
    """Convert integer to roman numeral (e.g., 23 -> 'xxiii')."""
    values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    symbols = ['m', 'cm', 'd', 'cd', 'c', 'xc', 'l', 'xl', 'x', 'ix', 'v', 'iv', 'i']
    
    result = ''
    for i, value in enumerate(values):
        count = num // value
        if count:
            result += symbols[i] * count
            num -= value * count
    
    return result


def _is_roman_numeral(text: str) -> bool:
    """Check if text is a valid roman numeral."""
    if not text:
        return False
    return bool(re.match(r'^[ivxlcdm]+$', text.lower()))


def _detect_written_page_on_page(page: 'fitz.Page') -> tuple:
    """
    Try to detect written page number on a SINGLE page.

    Checks common positions (header/footer) for:
    - Roman numerals (i, ii, iii, iv, v, etc.)
    - Arabic numbers (1, 2, 3, etc.)

    Returns:
        Tuple of (page_number, position, matched_text) where:
        - page_number: The detected page number as string
        - position: 'first' or 'last' indicating which line contained it
        - matched_text: The exact text that matched (for removal)
        Returns (None, None, None) if not found
    """
    try:
        text = page.get_text('text')
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return (None, None, None)

        # Check first and last lines (common header/footer positions)
        candidates = [
            (lines[0], 'first'),
            (lines[-1], 'last')
        ]

        for candidate, position in candidates:
            # Check for pure roman numeral
            if _is_roman_numeral(candidate):
                return (candidate.lower(), position, candidate)

            # Check for pure arabic number
            if candidate.isdigit():
                return (candidate, position, candidate)

            # Check for "Page N" or "p. N" patterns
            match = re.search(r'\b(?:page|p\.?)\s*(\d+)\b', candidate, re.IGNORECASE)
            if match:
                return (match.group(1), position, candidate)

        return (None, None, None)

    except Exception as e:
        logging.debug(f"Error detecting written page number: {e}")
        return (None, None, None)


def infer_written_page_numbers(doc: 'fitz.Document', scan_pages: int = 20) -> dict:
    """
    Infer written page numbers for entire PDF by finding anchor points.
    
    Algorithm:
    1. Scan first N pages to find:
       - First roman numeral (marks preface start)
       - First arabic number (marks main content start)
    2. Infer all subsequent pages by incrementing from anchor points
    
    This is much more reliable than OCRing every page.
    
    Args:
        doc: PyMuPDF document
        scan_pages: Number of pages to scan for anchor points (default 20)
    
    Returns:
        dict mapping pdf_page_num (1-indexed) -> written_page_str
    """
    total_pages = len(doc)
    scan_limit = min(scan_pages, total_pages)
    
    # Find anchor points
    roman_start_pdf_page = None
    roman_start_value = None
    arabic_start_pdf_page = None
    arabic_start_value = None
    
    logging.info(f"Scanning first {scan_limit} pages for written page number anchors...")
    
    for pdf_page_num in range(1, scan_limit + 1):
        page = doc[pdf_page_num - 1]  # 0-indexed
        written_num, position, matched_text = _detect_written_page_on_page(page)

        if written_num:
            # Check for roman numeral
            if _is_roman_numeral(written_num) and roman_start_pdf_page is None:
                roman_start_pdf_page = pdf_page_num
                roman_start_value = _roman_to_int(written_num)
                logging.info(f"Found roman numeral anchor: PDF page {pdf_page_num} = {written_num} ({roman_start_value})")

            # Check for arabic number (only after roman numerals or if no roman found)
            elif written_num.isdigit() and arabic_start_pdf_page is None:
                arabic_start_pdf_page = pdf_page_num
                arabic_start_value = int(written_num)
                logging.info(f"Found arabic number anchor: PDF page {pdf_page_num} = {written_num}")
    
    # Generate full mapping by inference
    page_map = {}
    
    # Infer roman numeral pages (preface)
    if roman_start_pdf_page:
        end_roman = arabic_start_pdf_page if arabic_start_pdf_page else total_pages + 1
        for pdf_page in range(roman_start_pdf_page, end_roman):
            offset = pdf_page - roman_start_pdf_page
            roman_value = roman_start_value + offset
            page_map[pdf_page] = _int_to_roman(roman_value)
        
        logging.info(f"Inferred roman numerals: PDF pages {roman_start_pdf_page}-{end_roman-1}")
    
    # Infer arabic number pages (main content)
    if arabic_start_pdf_page:
        for pdf_page in range(arabic_start_pdf_page, total_pages + 1):
            offset = pdf_page - arabic_start_pdf_page
            page_map[pdf_page] = str(arabic_start_value + offset)
        
        logging.info(f"Inferred arabic numbers: PDF pages {arabic_start_pdf_page}-{total_pages}")
    
    logging.info(f"Inferred written page numbers for {len(page_map)}/{total_pages} PDF pages")
    
    return page_map


def _extract_publisher_from_front_matter(doc: 'fitz.Document', max_pages: int = 5) -> tuple:
    """
    Extract publisher and year from front matter text (title page, copyright page).

    Scans first N pages for publisher patterns like:
    - "Cambridge University Press"
    - "Oxford University Press"
    - "Published by [Publisher]"
    - Copyright lines with publisher info
    - "[Publisher Name], [Year]" patterns

    Args:
        doc: PyMuPDF document object
        max_pages: Maximum pages to scan for publisher info

    Returns:
        tuple: (publisher: str|None, year: str|None)
    """
    # Common publisher patterns (ordered by specificity)
    publisher_patterns = [
        # Specific well-known publishers
        r'(?i)(Cambridge University Press)',
        r'(?i)(Oxford University Press)',
        r'(?i)(MIT Press)',
        r'(?i)(Princeton University Press)',
        r'(?i)(Harvard University Press)',
        r'(?i)(Yale University Press)',
        r'(?i)(University of Chicago Press)',
        r'(?i)(Routledge)',
        r'(?i)(Springer)',
        r'(?i)(Wiley)',
        r'(?i)(Pearson)',
        r'(?i)(McGraw[- ]Hill)',
        r'(?i)(Elsevier)',
        r'(?i)(Palgrave Macmillan)',

        # Generic patterns
        r'(?i)Published by ([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books))',
        r'(?i)©\s*\d{4}\s+(?:by\s+)?([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books))',
        r'(?i)Copyright\s+©?\s*\d{4}\s+(?:by\s+)?([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books))',
        r'(?i)([A-Z][A-Za-z\s&]+(?:Press|Publishing|Publishers|Books)),?\s+\d{4}',
    ]

    # Year patterns
    year_patterns = [
        r'(?i)©\s*(\d{4})',
        r'(?i)Copyright\s+©?\s*(\d{4})',
        r'(?i)Published.*?(\d{4})',
        r'(?i)\b(19\d{2}|20[0-2]\d)\b',  # Years 1900-2029
    ]

    # Filter out conversion tools that appear in metadata
    conversion_tools = [
        'calibre', 'adobe', 'acrobat', 'distiller', 'pdftex',
        'latex', 'pdflatex', 'xelatex', 'luatex', 'context',
        'prince', 'antenna house', 'ghostscript', 'ps2pdf'
    ]

    publisher = None
    year = None

    # Scan first few pages
    for page_num in range(min(max_pages, len(doc))):
        try:
            page = doc[page_num]
            text = page.get_text()

            # Defensive: ensure text is a string
            if not isinstance(text, str):
                continue

            # Try to find publisher
            if not publisher:
                for pattern in publisher_patterns:
                    match = re.search(pattern, text)
                    if match:
                        # Extract publisher name (first capture group or full match)
                        potential_publisher = match.group(1) if match.lastindex else match.group(0)
                        potential_publisher = potential_publisher.strip()

                        # Filter out conversion tools
                        if not any(tool in potential_publisher.lower() for tool in conversion_tools):
                            # Clean up common artifacts
                            potential_publisher = re.sub(r'\s+', ' ', potential_publisher)  # Normalize whitespace

                            # Validate it's not too long or too short
                            if 5 < len(potential_publisher) < 60:
                                publisher = potential_publisher
                                break

            # Try to find publication year
            if not year:
                for pattern in year_patterns:
                    match = re.search(pattern, text)
                    if match:
                        potential_year = match.group(1)
                        # Validate year range (1900-2029)
                        if potential_year.isdigit() and 1900 <= int(potential_year) <= 2029:
                            year = potential_year
                            break

            # Stop if we found both
            if publisher and year:
                break

        except Exception as e:
            logging.warning(f"Error extracting publisher from page {page_num}: {e}")
            continue

    return publisher, year


def _generate_document_header(doc: 'fitz.Document') -> str:
    """
    Generate a clean document header from PDF metadata and front matter.

    Extracts publisher from actual front matter text (not PDF metadata)
    to avoid picking up conversion tools like "calibre 3.32.0".

    Returns markdown formatted:
    # Title
    **Author:** Name
    **Translator:** Name (if available)
    **Publisher:** Name | **Year:** YYYY
    """
    metadata = doc.metadata

    title = metadata.get('title', 'Untitled')
    author = metadata.get('author', 'Unknown Author')

    # Build header
    lines = [f"# {title}", ""]

    if author and author != 'Unknown Author':
        lines.append(f"**Author:** {author}")

    # Check for translator in subject or keywords (common places)
    translator = None
    subject = metadata.get('subject', '')
    if 'translat' in subject.lower():
        translator = subject

    if translator:
        lines.append(f"**Translator:** {translator}")

    # Extract publisher and year from front matter text (NOT metadata)
    publisher, year = _extract_publisher_from_front_matter(doc, max_pages=5)

    # Fallback to metadata year if not found in text
    if not year:
        creation_date = metadata.get('creationDate', '')
        if creation_date and isinstance(creation_date, str):
            year_match = re.search(r'(\d{4})', creation_date)
            if year_match:
                year = year_match.group(1)

    pub_info = []
    if publisher:
        pub_info.append(f"**Publisher:** {publisher}")
    if year:
        pub_info.append(f"**Year:** {year}")

    if pub_info:
        lines.append(" | ".join(pub_info))

    lines.append("")  # Blank line after header
    return "\n".join(lines)


def _generate_markdown_toc_from_pdf(toc_map: dict, skip_front_matter: bool = True) -> str:
    """
    Generate markdown-formatted table of contents with links.
    
    Args:
        toc_map: dict mapping page_num to list of (level, title) tuples
        skip_front_matter: If True, skip entries like "Title Page", "Copyright Page", "Contents"
    
    Returns:
        Markdown formatted ToC with links
    """
    front_matter_titles = {
        'title page', 'copyright page', 'copyright', 
        'contents', 'table of contents'
    }
    
    toc_lines = ["## Table of Contents", ""]
    
    # Sort entries by page number
    sorted_pages = sorted(toc_map.keys())
    
    for page_num in sorted_pages:
        for level, title in toc_map[page_num]:
            # Skip front matter if requested
            if skip_front_matter and title.lower() in front_matter_titles:
                continue
            
            # Create markdown link (GitHub-style anchor)
            # Convert title to anchor: lowercase, spaces to hyphens, remove special chars
            anchor = title.lower()
            anchor = anchor.replace(' ', '-')
            anchor = ''.join(c for c in anchor if c.isalnum() or c == '-')
            anchor = anchor.strip('-')
            
            # Indent based on level
            indent = "  " * (level - 1)
            
            # Format as markdown list with link
            toc_lines.append(f"{indent}* [{title}](#{anchor}) - [[PDF_page_{page_num}]]")
    
    toc_lines.append("")  # Blank line after ToC
    return "\n".join(toc_lines)


def _find_first_content_page(toc_map: dict) -> int:
    """
    Find the first real content page (skip front matter entries).
    
    Returns page number of first non-front-matter ToC entry.
    """
    front_matter_titles = {
        'title page', 'copyright page', 'copyright',
        'contents', 'table of contents'
    }
    
    sorted_pages = sorted(toc_map.keys())
    
    for page_num in sorted_pages:
        for level, title in toc_map[page_num]:
            if title.lower() not in front_matter_titles:
                return page_num
    
    # Fallback: return first ToC page
    return sorted_pages[0] if sorted_pages else 1


def _format_pdf_markdown(
    page: fitz.Page,
    preserve_linebreaks: bool = False,
    toc_entries: list = None,
    pdf_page_num: int = None,
    written_page_num: str = None,
    written_page_position: str = None,
    written_page_text: str = None,
    use_toc_headings: bool = True
) -> str:
    """
    Generates a Markdown string from a PyMuPDF page object.

    Extracts text blocks, analyzes structure using _analyze_pdf_block,
    and formats the output as Markdown, including basic headings, lists,
    and footnote definitions.

    Args:
        page: A fitz.Page object.
        preserve_linebreaks: If True, preserve original line breaks from PDF (for citation accuracy).
        toc_entries: List of (level, title) tuples for ToC entries on this page (from PDF metadata)
        pdf_page_num: PDF page number (1-indexed) for page markers
        written_page_num: Written page number (e.g., "xxiii", "15") if detected
        written_page_position: Position of written page number ('first' or 'last')
        written_page_text: Exact text of written page number to remove from content
        use_toc_headings: If True, use ToC for headings instead of font-size heuristics

    Returns:
        A string containing the generated Markdown.
    """
    fn_id = None # Initialize to prevent UnboundLocalError
    cleaned_fn_text = "" # Initialize to prevent UnboundLocalError
    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT).get("blocks", [])
    markdown_lines = []
    footnote_defs = {} # Store footnote definitions [^id]: content
    current_list_type = None
    list_marker = None # Initialize list_marker

    # --- Page Markers (at the very start) ---
    page_markers = []

    # Always add PDF page number
    if pdf_page_num:
        page_markers.append(f"[[PDF_page_{pdf_page_num}]]")

    # Add written page number if available
    if written_page_num:
        page_markers.append(f"((p.{written_page_num}))")

    # Add page markers to output
    if page_markers:
        markdown_lines.append(" ".join(page_markers))
        markdown_lines.append("")  # Blank line after markers

    # --- ToC Headings (if this page has ToC entries) ---
    if use_toc_headings and toc_entries:
        for level, title in toc_entries:
            # Shift ToC levels down by 1 (document title is H1, so ToC entries start at H2)
            adjusted_level = level + 1
            heading_marker = '#' * adjusted_level
            markdown_lines.append(f"{heading_marker} {title}")
        markdown_lines.append("")  # Blank line after ToC headings

    # --- Extract and format blocks ---
    # Count only text blocks for position tracking
    text_blocks = [b for b in blocks if b.get("type") == 0]
    text_block_idx = 0

    for block_idx, block in enumerate(blocks):
        # Skip non-text blocks
        if block.get("type") != 0:
            continue

        # Pass use_toc_headings flag to disable font-size heading detection
        analysis = _analyze_pdf_block(block, preserve_linebreaks=preserve_linebreaks, detect_headings=not use_toc_headings)
        text = analysis['text']
        spans = analysis['spans']

        # Cleaning is now done in _analyze_pdf_block
        if not text:
            text_block_idx += 1
            continue

        # --- Remove written page number duplication ---
        # If this is the first or last text block and contains the written page number, remove it
        is_first_block = (text_block_idx == 0)
        is_last_block = (text_block_idx == len(text_blocks) - 1)

        if written_page_text and written_page_position:
            should_filter = (
                (written_page_position == 'first' and is_first_block) or
                (written_page_position == 'last' and is_last_block)
            )

            if should_filter:
                # Check if this block's text matches or contains the written page number
                text_stripped = text.strip()

                # If the entire block is just the page number, skip it entirely
                if text_stripped == written_page_text.strip():
                    logging.debug(f"Skipping block containing only written page number: '{text_stripped}'")
                    text_block_idx += 1
                    continue

                # If the page number appears at start or end of the block, remove it
                if text_stripped.startswith(written_page_text.strip()):
                    # Remove from start and clean up any trailing whitespace
                    text = text_stripped[len(written_page_text.strip()):].strip()
                    logging.debug(f"Removed written page number from start of block: '{written_page_text}'")
                elif text_stripped.endswith(written_page_text.strip()):
                    # Remove from end and clean up any leading whitespace
                    text = text_stripped[:-len(written_page_text.strip())].strip()
                    logging.debug(f"Removed written page number from end of block: '{written_page_text}'")

        # Re-check if text is empty after page number removal
        if not text:
            text_block_idx += 1
            continue

        # Footnote Reference/Definition Detection (using superscript flag)
        # Rebuild text WITH footnote markers at correct positions
        processed_text_parts = []
        potential_def_id = None
        first_span_in_block = True
        fn_id = None

        # Process spans to rebuild text with footnote markers
        for span in spans:
            span_text = span.get('text', '')
            flags = span.get('flags', 0)
            is_superscript = flags & 1

            # Detect both numeric (1, 2, 3) and letter (a, b, c) footnotes
            is_footnote_marker = (
                (span_text.isdigit()) or
                (len(span_text) == 1 and span_text.isalpha() and span_text.islower())
            )

            if is_superscript and is_footnote_marker:
                fn_id = span_text
                # Definition heuristic: at start of block
                if first_span_in_block and re.match(r"^[a-z0-9]+[\.\)]?\s*", text, re.IGNORECASE):
                    potential_def_id = fn_id
                    # For definitions, add the marker as-is (will be detected later)
                    processed_text_parts.append(span_text)
                else:
                    # Reference: insert markdown footnote marker
                    processed_text_parts.append(f"[^{fn_id}]")
            else:
                # Regular text: add as-is
                processed_text_parts.append(span_text)

            first_span_in_block = False

        # Join parts and clean up spacing
        processed_text = ''.join(processed_text_parts)
        # Clean up multiple spaces
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()

        # Store definition if found, otherwise format content
        if potential_def_id:
            # Store potentially uncleaned text (cleaning moved to final formatting)
            footnote_defs[potential_def_id] = processed_text # Store raw processed text
            text_block_idx += 1
            continue # Don't add definition block as regular content

        # Format based on analysis (only if not using ToC headings)
        if analysis['heading_level'] > 0 and not use_toc_headings:
            markdown_lines.append(f"{'#' * analysis['heading_level']} {processed_text}")
            current_list_type = None # Reset list context after heading
        elif analysis['is_list_item']:
            # Basic list handling (needs refinement for nesting based on indent)
            # Remove original list marker from text if present
            list_marker = analysis.get('list_marker')
            clean_text = processed_text # Start with original processed text

            if analysis['list_type'] == 'ul' and list_marker:
                # Use regex to remove the specific marker found
                clean_text = re.sub(r"^" + re.escape(list_marker) + r"\s*", "", processed_text).strip()
                markdown_lines.append(f"* {clean_text}")
            elif analysis['list_type'] == 'ol' and list_marker:
                 # Use regex to remove the specific marker found (number/letter/roman + ./))
                clean_text = re.sub(r"^" + re.escape(list_marker) + r"[\.\)]\s*", "", processed_text, flags=re.IGNORECASE).strip()
                # Use the detected marker for the Markdown list item
                markdown_lines.append(f"{list_marker}. {clean_text}")
            current_list_type = analysis['list_type']
        else: # Regular paragraph
            # Only add if it's not empty after processing (e.g., after footnote extraction)
            if processed_text:
                markdown_lines.append(processed_text)
            current_list_type = None # Reset list context

        # Increment text block counter at the end of each iteration
        text_block_idx += 1

    # Join main content lines with double newlines
    main_content = "\n\n".join(md_line for md_line in markdown_lines if not md_line.startswith("[^")) # Exclude footnote defs for now
    main_content_stripped = main_content.strip() # Store stripped version for checks

    # Format footnote section separately, joining with single newlines
    footnote_block = ""
    if footnote_defs:
        footnote_lines = []
        for fn_id, fn_text in sorted(footnote_defs.items()):
            # Apply regex cleaning directly here
            cleaned_fn_text = re.sub(r"^[^\w]+", "", fn_text).strip()
            footnote_lines.append(f"[^{fn_id}]: {cleaned_fn_text}")
        # Construct the footnote block with correct spacing
        footnote_block = "---\n" + "\n".join(footnote_lines) # Definitions joined by single newline

    # Combine main content and footnote section
    if footnote_block:
        # Add double newline separator only if main content exists and is not empty
        separator = "\n\n" if main_content_stripped else ""
        # Ensure no leading/trailing whitespace on the final combined string
        return (main_content_stripped + separator + footnote_block).strip()
    else:
        # Return only the stripped main content if no footnotes
        return main_content_stripped


# --- EPUB Markdown Helpers ---

def _epub_node_to_markdown(node: BeautifulSoup, footnote_defs: dict, list_level: int = 0) -> str:
    """
    Recursively converts a BeautifulSoup node (from EPUB HTML) to Markdown.
    Handles common HTML tags (headings, p, lists, blockquote, pre) and
    EPUB-specific footnote references/definitions (epub:type="noteref/footnote").
    """
    # Handle plain text nodes directly
    if isinstance(node, NavigableString):
        return str(node) # Return the string content
    markdown_parts = []
    node_name = getattr(node, 'name', None)
    indent = "  " * list_level # Indentation for nested lists
    prefix = '' # Default prefix

    if node_name == 'h1': prefix = '# '
    elif node_name == 'h2': prefix = '## '
    elif node_name == 'h3': prefix = '### '
    elif node_name == 'h4': prefix = '#### '
    elif node_name == 'h5': prefix = '##### '
    elif node_name == 'h6': prefix = '###### '
    elif node_name == 'p': prefix = ''
    elif node_name == 'ul':
        # Handle UL items recursively
        for child in node.find_all('li', recursive=False):
            item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
            if item_text: markdown_parts.append(f"{indent}* {item_text}")
        return "\n".join(markdown_parts) # Return joined list items
    elif node_name == 'nav' and node.get('epub:type') == 'toc':
        # Handle Table of Contents (often uses nested <p><a>...</a></p> or similar)
        for child in node.descendants:
            if getattr(child, 'name', None) == 'a' and child.get_text(strip=True):
                 link_text = child.get_text(strip=True)
                 markdown_parts.append(f"* {link_text}")
        return "\n".join(markdown_parts)
    elif node_name == 'ol':
        # Handle OL items recursively
        for i, child in enumerate(node.find_all('li', recursive=False)):
            item_text = _epub_node_to_markdown(child, footnote_defs, list_level + 1).strip()
            if item_text: markdown_parts.append(f"{indent}{i+1}. {item_text}")
        return "\n".join(markdown_parts)
    elif node_name == 'li':
        # Process content within LI, prefix handled by parent ul/ol
        prefix = ''
    elif node_name == 'blockquote':
        prefix = '> '
    elif node_name == 'pre':
        # Handle code blocks
        code_content = node.get_text()
        return f"```\n{code_content}\n```"
    elif node_name == 'img':
        # Handle images - create placeholder
        src = node.get('src', '')
        alt = node.get('alt', '')
        return f"[Image: {src}/{alt}]" # Placeholder format as per spec/test
    elif node_name == 'table':
        # Basic table handling - extract text content
        # TODO: Implement proper Markdown table conversion later if needed
        return node.get_text(separator=' ', strip=True)
    elif node_name == 'a' and node.get('epub:type') == 'noteref':
        # Footnote reference
        href = node.get('href', '')
        fn_id_match = re.search(r'#ft(\d+)', href) # Example pattern, adjust if needed
        if fn_id_match:
            fn_id = fn_id_match.group(1)
            # Return the reference marker, process siblings/children if any (unlikely for simple ref)
            child_content = "".join(_epub_node_to_markdown(child, footnote_defs, list_level) for child in node.children).strip()
            return f"{child_content}[^{fn_id}]" # Append ref marker
        else:
             # Fallback if pattern doesn't match, process children
             pass # Continue to process children below
    elif node.get('epub:type') == 'footnote':
        # Footnote definition
        fn_id = node.get('id', '')
        fn_id_match = re.search(r'ft(\d+)', fn_id) # Example pattern
        if fn_id_match:
            num_id = fn_id_match.group(1)
            # Extract definition text, excluding the backlink if present
            content_node = node.find('p') or node # Assume content is in <p> or directly in the element
            if content_node:
                # Remove backlink if it exists (common pattern)
                backlink = content_node.find('a', {'epub:type': 'backlink'})
                if backlink: backlink.decompose()
                # Get cleaned text content
                fn_text = content_node.get_text(strip=True)
                footnote_defs[num_id] = fn_text
            return "" # Don't include definition inline
        else:
            # Fallback if ID pattern doesn't match
            pass # Continue to process children below

    # Process children recursively if not handled by specific tag logic above
    child_content = "".join(_epub_node_to_markdown(child, footnote_defs, list_level) for child in node.children).strip()

    # Apply prefix and return, handle block vs inline elements appropriately
    if node_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote']:
        # Block elements get prefix and potential double newline separation handled by caller
        return f"{prefix}{child_content}"
    else:
        # Inline elements just return their content
        return child_content


# --- Helper Functions for Processing ---

def _html_to_text(html_content):
    """Extracts plain text from HTML using BeautifulSoup."""
    if not BeautifulSoup:
        logging.warning("BeautifulSoup not available, cannot extract text from HTML.")
        return ""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        logging.error(f"Error parsing HTML with BeautifulSoup: {e}")
        return "" # Return empty string on parsing error

# --- Preprocessing Helpers ---

def _identify_and_remove_front_matter(content_lines: list[str]) -> tuple[list[str], str]:
    """
    Identifies title (basic heuristic), removes basic front matter lines based on keywords,
    returns cleaned content lines and title. Matches current test expectations.
    """
    logging.debug("Running basic front matter removal and title identification...")
    title = "Unknown Title" # Default title
    cleaned_lines = []

    # --- Basic Title Identification Heuristic ---
    # Look for the first non-empty line within the first ~5 lines
    # SKIP page markers (they're not titles)
    for line in content_lines[:5]:
        stripped_line = line.strip()
        # Skip page markers like [[PDF_page_1]] or ((p.1))
        if stripped_line and not (stripped_line.startswith('[[') or stripped_line.startswith('((')):
            title = stripped_line
            logging.debug(f"Identified potential title: {title}")
            break # Found the first non-empty line, assume it's the title

    # --- Front Matter Removal Logic ---
    # Define keywords for publisher info, copyright, etc.
    FRONT_MATTER_SKIP_TWO = ["dedication", "copyright notice"] # Skip line + next
    FRONT_MATTER_SKIP_ONE = [
        "copyright", "isbn", "published by", "acknowledgments",
        "cambridge university press", "stanford university press",
        "library of congress", "cataloging in publication",
        "all rights reserved", "printed in", "reprinted",
        "first published", "permissions", "without permission"
    ]

    i = 0
    while i < len(content_lines):
        line = content_lines[i]
        line_lower = line.strip().lower()
        skipped = False

        # Check skip-two keywords first
        if any(keyword in line_lower for keyword in FRONT_MATTER_SKIP_TWO):
            logging.debug(f"Skipping front matter block (2 lines) starting with: {line.strip()}")
            i += 2 # Skip current line and the next line
            skipped = True
        # Check skip-one keywords if not already skipped
        elif any(keyword in line_lower for keyword in FRONT_MATTER_SKIP_ONE):
            logging.debug(f"Skipping single front matter line: {line.strip()}")
            i += 1 # Skip current line only
            skipped = True

        if not skipped:
            # Preserve lines
            cleaned_lines.append(line)
            i += 1

    # Return original lines if filtering removed everything (edge case)
    # Note: This edge case handling might need review if the test changes
    # Ensure a tuple is always returned, even if cleaned_lines is empty
    if not cleaned_lines:
         logging.warning("Front matter removal resulted in empty content.")
         # Return empty list and the identified title
         return [], title

    return cleaned_lines, title

def _format_toc_lines_as_markdown(toc_lines: list[str]) -> str:
    """Formats extracted ToC lines into a Markdown list, handling basic indentation."""
    markdown_list = []
    base_indent = -1 # Track base indentation level

    for line in toc_lines:
        stripped_line = line.strip()
        if not stripped_line: continue # Skip empty lines

        # Basic indentation detection (count leading spaces)
        indent_level = len(line) - len(line.lstrip(' '))
        if base_indent == -1:
            base_indent = indent_level # Set base indent on first non-empty line

        # Calculate relative indent level (simple approach)
        relative_indent = max(0, (indent_level - base_indent) // 2) # Assume 2 spaces per level
        indent_str = "  " * relative_indent
        # Remove page numbers/dots for cleaner Markdown
        text_part = re.sub(r'[\s.]{2,}\d+$', '', stripped_line).strip()
        markdown_list.append(f"{indent_str}* {text_part}")

    return "\n".join(markdown_list)

def _extract_and_format_toc(content_lines: list[str], output_format: str) -> tuple[list[str], str]:
    """
    Extracts Table of Contents (ToC) lines based on heuristics, formats it
    (currently only for Markdown), and returns remaining content lines and formatted ToC.
    """
    logging.debug("Attempting to extract and format Table of Contents...")
    toc_lines = []
    remaining_lines = []
    in_toc = False
    toc_start_index = -1 # Added: Track start of ToC
    toc_end_index = -1
    # main_content_start_index = -1 # Removed: Simplify logic based on toc_end_index

    # Heuristic: Look for common ToC start keywords
    TOC_START_KEYWORDS = ["contents", "table of contents"]
    # Heuristic: Look for lines ending with page numbers (dots or spaces before number)
    # Updated regex to be more specific and avoid matching chapter titles
    TOC_LINE_PATTERN = re.compile(r'^(.*?)[\s.]{2,}(\d+)$') # Non-greedy match for text, require >=2 dots/spaces before number
    # Heuristic: Look for common main content start keywords
    MAIN_CONTENT_START_KEYWORDS = ["introduction", "preface", "chapter 1", "part i"]

    # First pass: Identify potential ToC block
    for i, line in enumerate(content_lines):
        line_lower = line.strip().lower()

        if not in_toc and any(keyword in line_lower for keyword in TOC_START_KEYWORDS):
            in_toc = True
            toc_start_index = i # Record start index
            logging.debug(f"Potential ToC start found at line {i}: {line.strip()}")
            # Don't add the keyword line itself to toc_lines
            continue # Skip the "Contents" line itself

        if in_toc:
            # Check if line matches ToC pattern OR is empty (allow empty lines within ToC)
            is_toc_like = bool(TOC_LINE_PATTERN.match(line.strip())) or not line.strip()
            # Check if line signals start of main content AND doesn't look like a ToC line itself
            is_main_content_start = any(line_lower.startswith(keyword) for keyword in MAIN_CONTENT_START_KEYWORDS) and not is_toc_like

            if is_toc_like and not is_main_content_start:
                # toc_lines.append(line) # Keep original line with indentation - NO, collect indices first
                toc_end_index = i # Track the last potential ToC line index
            # Simplified end condition: if it's not a ToC line, assume ToC ended on the previous line.
            else:
                logging.debug(f"Potential ToC end detected before line {i} (non-matching line): {line.strip()}")
                break # Stop processing ToC lines

    # Determine final content lines based on findings
    if toc_start_index != -1 and toc_end_index != -1 and toc_end_index >= toc_start_index: # Ensure end is after start
        # ToC found: combine lines before start and after end
        remaining_lines = content_lines[:toc_start_index] + content_lines[toc_end_index + 1:]
        # Ensure toc_lines only contains lines within the identified block
        # (Adjust indices relative to the original content_lines)
        actual_toc_start_line_index = toc_start_index + 1 # Line after the keyword
        actual_toc_end_line_index = toc_end_index
        toc_lines = content_lines[actual_toc_start_line_index : actual_toc_end_line_index + 1]

    else:
        # No ToC found or block incomplete, keep all original lines
        remaining_lines = content_lines
        toc_lines = [] # Ensure toc_lines is empty

    logging.debug(f"Identified {len(toc_lines)} ToC lines. {len(remaining_lines)} remaining content lines.")

    # Format ToC only if requested and lines were found
    formatted_toc = "" # Initialize as empty string instead of None
    if output_format == "markdown" and toc_lines:
        formatted_toc = _format_toc_lines_as_markdown(toc_lines)
        logging.debug("Formatted ToC for Markdown output.")

    return remaining_lines, formatted_toc

# --- PDF Quality Analysis ---

def detect_pdf_quality(pdf_path: str) -> dict: # Renamed from _analyze_pdf_quality
    """
    Analyzes a PDF to determine text quality and recommend OCR if needed.

    Returns a dictionary with 'quality_category' ('TEXT_HIGH', 'TEXT_LOW', 'IMAGE_ONLY', 'MIXED', 'EMPTY', 'ENCRYPTED'),
    'ocr_needed' (boolean), and 'reason' (string).
    """
    if not PYMUPDF_AVAILABLE:
        return {'quality_category': 'UNKNOWN', 'ocr_needed': False, 'reason': 'PyMuPDF not available'}

    doc = None
    try:
        doc = fitz.open(pdf_path)
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


# --- OCR Quality Assessment and Remediation ---

def assess_pdf_ocr_quality(pdf_path: Path, sample_pages: int = 10) -> dict:
    """
    Assess OCR quality of a PDF by sampling pages and detecting common issues.

    Samples pages strategically (beginning, middle, end) and checks for:
    - Letter spacing issues (e.g., "T H E")
    - Low text extraction rate
    - High image-to-text ratio

    Args:
        pdf_path: Path to PDF file
        sample_pages: Number of pages to sample (default 10)

    Returns:
        dict with:
            - score: Quality score 0-1 (1 = perfect, 0 = terrible)
            - has_text_layer: Whether PDF has embedded text
            - issues: List of detected issues
            - recommendation: "use_existing" | "redo_ocr" | "force_ocr"
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count

        if total_pages == 0:
            return {
                "score": 0.0,
                "has_text_layer": False,
                "issues": ["no_pages"],
                "recommendation": "error"
            }

        # Sample strategy: first 3 + middle 4 + last 3
        # For small PDFs, sample all pages
        if total_pages <= sample_pages:
            sample_indices = list(range(total_pages))
        else:
            first = list(range(min(3, total_pages)))
            last = list(range(max(total_pages - 3, 3), total_pages))
            middle_start = total_pages // 2 - 2
            middle = list(range(middle_start, min(middle_start + 4, total_pages)))
            sample_indices = sorted(set(first + middle + last))[:sample_pages]

        # Quality metrics
        pages_with_issues = 0
        pages_with_text = 0
        total_chars = 0
        issue_types = set()

        for page_num in sample_indices:
            page = doc[page_num]
            text = page.get_text()

            # Check if page has text
            if len(text.strip()) > 50:  # Minimum threshold for "has text"
                pages_with_text += 1
                total_chars += len(text)

                # Check for letter spacing issues
                if detect_letter_spacing_issue(text):
                    pages_with_issues += 1
                    issue_types.add("letter_spacing")
            else:
                issue_types.add("missing_text")

        doc.close()

        # Calculate quality score
        has_text_layer = pages_with_text > 0

        if not has_text_layer:
            return {
                "score": 0.0,
                "has_text_layer": False,
                "issues": list(issue_types),
                "recommendation": "force_ocr"
            }

        # Score based on percentage of clean pages
        clean_pages_ratio = 1.0 - (pages_with_issues / len(sample_indices))

        # Penalize if very few pages have text
        text_coverage_ratio = pages_with_text / len(sample_indices)

        # Average characters per sampled page
        avg_chars = total_chars / max(pages_with_text, 1)

        # Combined score (weighted)
        score = (
            clean_pages_ratio * 0.6 +  # Primary: how many pages are clean
            text_coverage_ratio * 0.3 +  # Secondary: text coverage
            min(avg_chars / 1000, 1.0) * 0.1  # Tertiary: text density
        )

        # Determine recommendation
        if score >= 0.75:
            recommendation = "use_existing"
        elif score >= 0.3:
            recommendation = "redo_ocr"
        else:
            recommendation = "force_ocr"

        logging.info(
            f"OCR quality assessment: score={score:.2f}, "
            f"pages_sampled={len(sample_indices)}, "
            f"pages_with_issues={pages_with_issues}, "
            f"recommendation={recommendation}"
        )

        return {
            "score": round(score, 2),
            "has_text_layer": has_text_layer,
            "issues": list(issue_types),
            "recommendation": recommendation
        }

    except Exception as e:
        logging.error(f"Error assessing PDF quality: {e}")
        return {
            "score": 0.5,  # Neutral score on error
            "has_text_layer": True,  # Assume it exists
            "issues": ["assessment_error"],
            "recommendation": "use_existing"  # Safe fallback
        }


def redo_ocr_with_tesseract(input_pdf: Path, output_dir: Path = None) -> Path:
    """
    Re-OCR a PDF using Tesseract via ocrmypdf.

    Strips existing (poor quality) text layer and performs fresh OCR.

    Args:
        input_pdf: Path to input PDF with poor OCR quality
        output_dir: Directory for output PDF (default: temp directory)

    Returns:
        Path to OCR'd PDF file

    Raises:
        subprocess.CalledProcessError: If ocrmypdf fails
        FileNotFoundError: If tesseract is not installed
    """
    if output_dir is None:
        output_dir = Path(tempfile.gettempdir())

    output_dir.mkdir(parents=True, exist_ok=True)

    # Output filename: original_name.ocr.pdf
    output_pdf = output_dir / f"{input_pdf.stem}.ocr.pdf"

    logging.info(f"Re-OCRing PDF with Tesseract: {input_pdf.name}")

    try:
        # ocrmypdf command: strip bad OCR, re-OCR with Tesseract
        result = subprocess.run(
            [
                'ocrmypdf',
                '--redo-ocr',  # Strip existing text layer, re-OCR
                '--optimize', '1',  # Light optimization
                '--output-type', 'pdf',  # Output as PDF
                '--jobs', '4',  # Parallel processing (4 threads)
                '--skip-big', '50',  # Skip pages > 50MB (likely images)
                str(input_pdf),
                str(output_pdf)
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        logging.info(f"OCR complete: {output_pdf}")
        return output_pdf

    except subprocess.TimeoutExpired:
        logging.error(f"OCR timeout after 10 minutes: {input_pdf.name}")
        raise
    except subprocess.CalledProcessError as e:
        logging.error(f"OCR failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logging.error("Tesseract not found. Install with: apt-get install tesseract-ocr")
        raise


# --- Garbled Text Detection ---

def detect_letter_spacing_issue(text: str, sample_size: int = 500) -> bool:
    """
    Detects if text has excessive letter spacing (e.g., "T H E" instead of "THE").

    This is a common OCR issue in scanned PDFs where spaces appear between every letter.

    Args:
        text: Text to analyze
        sample_size: Number of characters to sample for analysis

    Returns:
        True if letter spacing issue detected
    """
    if len(text) < 10:  # Lower threshold for short samples
        return False

    # Sample text for analysis (first N characters)
    sample = text[:sample_size] if len(text) > sample_size else text

    # Count words that are single letters (the symptom of letter spacing)
    words = sample.split()
    if len(words) == 0:
        return False

    single_letter_words = sum(1 for word in words if len(word.strip()) == 1 and word.isalpha())

    # Calculate ratio of single-letter words to total words
    ratio = single_letter_words / len(words)

    # If more than 50% of words are single letters, it's likely a spacing issue
    # Lowered threshold to catch "T h e  B o o k" style cases
    if ratio > 0.5:
        logging.debug(f"Letter spacing issue detected: {single_letter_words}/{len(words)} words are single letters ({ratio:.1%})")
        return True

    return False


def correct_letter_spacing(text: str) -> str:
    """
    Corrects excessive letter spacing in OCR text.

    Transforms: "T H E  B U R N O U T" → "THE BURNOUT"

    Algorithm:
    1. Identify sequences of single letters separated by spaces
    2. Collapse them into words
    3. Preserve intentional spacing and punctuation

    Args:
        text: Text with potential letter spacing issues

    Returns:
        Corrected text
    """
    if not text or not detect_letter_spacing_issue(text):
        return text

    logging.info("Applying letter spacing correction...")

    # Split into lines to preserve paragraph structure
    lines = text.split('\n')
    corrected_lines = []

    for line in lines:
        # Pattern explanation:
        # - Matches sequences of single letters with spaces between them
        # - Handles: "T H E", "T h e", "T H E ,", etc.
        # - Captures letters and spaces, excluding punctuation at boundaries
        #
        # Strategy: Find patterns like "X Y Z" where X, Y, Z are single letters
        # This works by looking for: letter + (space + letter) repeated 1+ times

        # First, handle case where letters are separated by single spaces
        # This pattern captures "T H E" or "T h e" style sequences
        corrected_line = line

        # Multiple passes to handle all patterns
        max_iterations = 5
        for _ in range(max_iterations):
            original = corrected_line

            # Pattern: Single letter, space, another single letter (repeated)
            # Matches: "T H E", "T h e", "B O O K", etc.
            # Uses lookbehind and lookahead to avoid word boundaries issues
            corrected_line = re.sub(
                r'(?<!\S)([A-Za-z])(\s+[A-Za-z])+(?!\S)',
                lambda m: m.group(0).replace(' ', ''),
                corrected_line
            )

            # If no changes, we're done
            if corrected_line == original:
                break

        corrected_lines.append(corrected_line)

    corrected_text = '\n'.join(corrected_lines)

    # Clean up any excessive spaces that may have been introduced
    corrected_text = re.sub(r'\s{3,}', '  ', corrected_text)

    logging.info(f"Letter spacing correction complete. Length: {len(text)} → {len(corrected_text)}")
    return corrected_text


def detect_garbled_text(text: str, non_alpha_threshold: float = 0.25, repetition_threshold: float = 0.7, min_length: int = 10) -> bool:
    """
    Detects potentially garbled text based on heuristics like non-alphanumeric ratio
    and character repetition.
    """
    text_length = len(text)
    if text_length < min_length:
        return False # Too short to reliably analyze

    # 1. Non-Alphanumeric Ratio
    non_alpha_count = sum(1 for char in text if not char.isalnum() and not char.isspace())
    non_alpha_ratio = non_alpha_count / text_length
    if non_alpha_ratio > non_alpha_threshold:
        logging.debug(f"Garbled text detected: High non-alpha ratio ({non_alpha_ratio:.2f} > {non_alpha_threshold})")
        return True

    # 2. Character Repetition Ratio
    # Count occurrences of each character (excluding spaces)
    char_counts = collections.Counter(c for c in text if not c.isspace())
    if not char_counts: # Handle case of only spaces
        return False
    most_common_char, most_common_count = char_counts.most_common(1)[0]
    repetition_ratio = most_common_count / (text_length - text.count(' ')) # Ratio based on non-space chars
    if repetition_ratio > repetition_threshold:
        logging.debug(f"Garbled text detected: High repetition ratio ({repetition_ratio:.2f} > {repetition_threshold}) for char '{most_common_char}'")
        return True

    # TODO: Add more heuristics? (e.g., dictionary word check, common pattern matching)

    return False


# --- Main Processing Functions ---

def process_pdf(file_path: Path, output_format: str = "txt", preserve_linebreaks: bool = False) -> str:
    """
    Processes a PDF file, extracts text, applies preprocessing, and returns content.

    Args:
        file_path: Path to PDF file
        output_format: Output format ("txt" or "markdown")
        preserve_linebreaks: If True, preserve original line breaks from PDF for citation accuracy.
                           If False, join lines intelligently for readability (default).

    Returns:
        Processed text content
    """
    if not PYMUPDF_AVAILABLE: raise ImportError("Required library 'PyMuPDF' (fitz) is not installed.")
    logging.info(f"Processing PDF: {file_path} for format: {output_format}")
    doc = None

    # Track if we created a temp OCR file (for cleanup)
    temp_ocr_file = None

    try:
        # --- OCR Quality Assessment and Remediation ---
        # Check if PDF needs re-OCRing BEFORE processing
        quality_assessment = assess_pdf_ocr_quality(file_path)
        logging.info(f"PDF quality assessment: {quality_assessment}")

        if quality_assessment["recommendation"] in ["redo_ocr", "force_ocr"]:
            logging.info(f"Quality score {quality_assessment['score']:.2f} - Re-OCRing PDF for better extraction")
            try:
                # Re-OCR with Tesseract, save to temp directory
                ocr_pdf = redo_ocr_with_tesseract(file_path)
                temp_ocr_file = ocr_pdf

                # Process the OCR'd version instead of original
                file_path = ocr_pdf
                logging.info(f"Using OCR'd PDF: {ocr_pdf}")

            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as ocr_err:
                logging.warning(f"OCR remediation failed, using original PDF: {ocr_err}")
                # Fall back to original file_path

        # --- Quality Analysis (legacy system - keeping for compatibility) ---
        quality_info = detect_pdf_quality(str(file_path))
        quality_category = quality_info.get("quality_category", "UNKNOWN")
        ocr_needed = quality_info.get("ocr_recommended", False) # Use correct key 'ocr_recommended'

        # --- OCR (if needed and available) ---
        if ocr_needed:
            if OCR_AVAILABLE:
                logging.info(f"Quality analysis ({quality_category}) recommends OCR for {file_path}. Running OCR...")
                try:
                    # Cycle 21 Refactor: Use run_ocr_on_pdf which now uses fitz
                    ocr_text = run_ocr_on_pdf(str(file_path))
                    if ocr_text:
                         logging.info(f"OCR successful for {file_path}.")

                         # DISABLED: Letter spacing correction (now using ocrmypdf re-OCR instead)
                         # ocr_text = correct_letter_spacing(ocr_text)

                         # Preprocess OCR text (basic for now, can be expanded)
                         try: # Add try block for preprocessing OCR text
                             ocr_lines = ocr_text.splitlines()
                             (cleaned_lines, title) = _identify_and_remove_front_matter(ocr_lines)
                             (final_content_lines, formatted_toc) = _extract_and_format_toc(cleaned_lines, output_format)
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
        doc = fitz.open(str(file_path))
        if doc.is_encrypted:
            logging.warning(f"PDF {file_path} is encrypted.")
            if not doc.authenticate(""):
                raise ValueError(f"PDF {file_path} is encrypted and cannot be opened.")
            logging.info(f"Successfully decrypted {file_path} with empty password.")

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
        first_content_page = 1
        if toc_map:
            first_content_page = _find_first_content_page(toc_map)
            logging.info(f"Starting content at page {first_content_page} (first real content after front matter)")

        # 2. Extract structured content using block-level analysis
        logging.debug("Performing structured PDF extraction with block analysis...")
        page_count = len(doc)
        page_contents = []  # Store content with page numbers

        for i, page in enumerate(doc):
            page_num = i + 1

            # Skip front matter pages (before first ToC entry)
            if page_num < first_content_page:
                logging.debug(f"Skipping front matter page {page_num}")
                continue

            logging.debug(f"Processing page {page_num}/{page_count} with block analysis...")

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
                page_markdown = _format_pdf_markdown(
                    page,
                    preserve_linebreaks=preserve_linebreaks,
                    toc_entries=toc_entries,
                    pdf_page_num=page_num,
                    written_page_num=written_page,
                    written_page_position=written_page_position,
                    written_page_text=written_page_text,
                    use_toc_headings=bool(toc_map)  # Use ToC if available
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
        (lines_after_fm, title) = _identify_and_remove_front_matter(content_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

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
        final_output = "\n\n".join(part for part in final_output_parts if part).strip()

        # Close doc before returning
        if doc is not None and not doc.is_closed:
            doc.close()
            logging.debug(f"Closed PDF document before return: {file_path}")
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


def process_epub(file_path: Path, output_format: str = "txt") -> str:
    """Processes an EPUB file, extracts text, applies preprocessing, and returns content."""
    if not EBOOKLIB_AVAILABLE: raise ImportError("Required library 'ebooklib' is not installed.")
    logging.info(f"Processing EPUB: {file_path} for format: {output_format}")

    logging.debug(f"Attempting to read EPUB: {file_path}")
    try:
        logging.debug("Successfully opened EPUB file.")
        book = epub.read_epub(str(file_path))
        all_lines = []
        footnote_defs = {} # Collect footnote definitions across items

        # --- Extract Content (HTML) ---
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        logging.debug(f"Found {len(items)} items of type ITEM_DOCUMENT.")

        section_counter = 0
        for item in items:
            section_counter += 1
            logging.debug(f"Processing item: {item.get_name()}")
            try:
                content = item.get_content()
                if isinstance(content, bytes):
                    # Attempt decoding with common encodings
                    try:
                        html_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            html_content = content.decode('latin-1')
                        except UnicodeDecodeError:
                            logging.warning(f"Could not decode content from item {item.get_name()} in {file_path}. Skipping.")
                            continue
                # If not skipped, proceed with processing
                else: # Assume it's already a string
                    html_content = content

                if not html_content: continue

                # Add section marker for academic citations
                item_name = item.get_name()
                if output_format == "markdown":
                    section_marker = f"`[section.{section_counter}: {item_name}]`\n"
                    all_lines.append(section_marker)
                else:
                    section_marker = f"[Section {section_counter}: {item_name}]\n"
                    all_lines.append(section_marker)

                logging.debug(f"Converting item {item.get_name()} content to {output_format}...")
                # --- Convert HTML to Text or Markdown ---
                try: # Add try block around conversion
                    if output_format == "markdown":
                        logging.debug(f"Item {item.get_name()}: Converting HTML to Markdown...")
                        soup = BeautifulSoup(html_content, 'html.parser')
                        body = soup.find('body')
                        if body:
                            # Process body content, collecting footnote definitions
                            item_markdown = _epub_node_to_markdown(body, footnote_defs)
                            # Append footnote definitions collected from this item
                            # (Footnote formatting happens at the end)
                            all_lines.extend(item_markdown.splitlines())
                        else:
                             logging.warning(f"No <body> tag found in item {item.get_name()}. Skipping.")
                    else: # Default to text
                        logging.debug(f"Item {item.get_name()}: Extracting plain text from HTML...")
                        item_text = _html_to_text(html_content)
                        if item_text:
                            all_lines.extend(item_text.splitlines())
                except Exception as conversion_err:
                     logging.error(f"Error converting content from item {item.get_name()} in {file_path}: {conversion_err}", exc_info=True)
                     # Optionally add a placeholder or skip the item
                     all_lines.append(f"[Error processing item {item.get_name()}]")

            except Exception as item_err:
                logging.error(f"Error reading content from item {item.get_name()} in {file_path}: {item_err}", exc_info=True)
                all_lines.append(f"[Error reading item {item.get_name()}]")

        # --- Preprocessing ---
        logging.debug("Starting EPUB preprocessing (front matter, ToC)...")
        (lines_after_fm, title) = _identify_and_remove_front_matter(all_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines) # Join preprocessed lines
        final_output_parts.append(main_content.strip())

        # Append formatted footnote definitions if output is markdown
        if output_format == "markdown" and footnote_defs:
            footnote_block_lines = ["---"]
            for fn_id, fn_text in sorted(footnote_defs.items()):
                footnote_block_lines.append(f"[^{fn_id}]: {fn_text}")
            final_output_parts.append("\n".join(footnote_block_lines))

        return "\n\n".join(part for part in final_output_parts if part).strip()

    except Exception as e:
        logging.error(f"Error processing EPUB {file_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error processing EPUB {file_path}: {e}") from e


async def process_txt(file_path: Path, output_format: str = "txt") -> str:
    """Processes a TXT file, applies preprocessing, and returns content."""
    logging.info(f"Processing TXT: {file_path}")
    try:
        try:
            # Try reading as UTF-8 first
            async def read_utf8():
                 async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                     return await f.readlines()
            content_lines = await read_utf8() # Await async read
        except UnicodeDecodeError:
            logging.warning(f"UTF-8 decoding failed for {file_path}. Trying latin-1.")
            try:
                async def read_latin1():
                     async with aiofiles.open(file_path, mode='r', encoding='latin-1') as f:
                         return await f.readlines()
                content_lines = await read_latin1() # Await async read
            except Exception as read_err:
                 logging.error(f"Failed to read {file_path} with fallback encoding: {read_err}")
                 raise IOError(f"Could not read file {file_path}") from read_err
        except Exception as read_err:
             logging.error(f"Failed to read {file_path}: {read_err}")
             raise IOError(f"Could not read file {file_path}") from read_err

        # --- Preprocessing ---
        logging.debug("Starting TXT preprocessing (front matter, ToC)...")
        (lines_after_fm, title) = _identify_and_remove_front_matter(content_lines)
        (final_content_lines, formatted_toc) = _extract_and_format_toc(lines_after_fm, output_format)

        # --- Final Output Construction ---
        final_output_parts = []
        if title != "Unknown Title":
            final_output_parts.append(f"# {title}" if output_format == "markdown" else title)
        if formatted_toc:
            final_output_parts.append(formatted_toc)

        main_content = "\n".join(final_content_lines)
        final_output_parts.append(main_content.strip())

        return "\n\n".join(part for part in final_output_parts if part).strip()

    except Exception as e:
        logging.error(f"Error processing TXT {file_path}: {e}", exc_info=True)
        raise RuntimeError(f"Error processing TXT {file_path}: {e}") from e


# --- OCR Function ---

def run_ocr_on_pdf(pdf_path: str, lang: str = 'eng') -> str: # Cycle 21 Refactor: Add lang parameter
    """
    Performs OCR on a PDF file using Tesseract via PyMuPDF rendering.

    Args:
        pdf_path: Path to the PDF file.
        lang: Language code for Tesseract (e.g., 'eng').

    Returns:
        Extracted text content as a single string.

    Raises:
        OCRDependencyError: If required OCR dependencies are not installed.
        TesseractNotFoundError: If Tesseract executable is not found.
        RuntimeError: For other processing errors.
    """
    if not OCR_AVAILABLE:
        raise OCRDependencyError("OCR dependencies (pytesseract, pdf2image, Pillow) not installed.")
    if not PYMUPDF_AVAILABLE:
        raise OCRDependencyError("PyMuPDF (fitz) is required for OCR rendering but not installed.")

    logging.info(f"Running OCR on {pdf_path} with language '{lang}'...")
    extracted_text = ""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        logging.debug(f"PDF has {page_count} pages.")

        for i, page in enumerate(doc):
            page_num = i + 1
            logging.debug(f"Processing page {page_num}/{page_count} for OCR...")
            try:
                # Render page to pixmap, then to PNG bytes
                pix = page.get_pixmap(dpi=300) # Higher DPI for better OCR
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))

                # Perform OCR on the image
                page_text = pytesseract.image_to_string(img, lang=lang)
                extracted_text += page_text + "\n\n" # Add page separator
                logging.debug(f"OCR successful for page {page_num}.")
            # Specific exception must come BEFORE generic Exception
            except TesseractNotFoundError as tess_err:
                 logging.error(f"Tesseract not found during OCR on page {page_num}: {tess_err}")
                 raise # Re-raise to be caught by outer handler
            except Exception as page_err:
                 logging.error(f"Error during OCR on page {page_num}: {page_err}", exc_info=True)
                 # Continue to next page if one fails? Or raise? Let's continue for now.
                 extracted_text += f"[OCR Error on Page {page_num}]\n\n"

        logging.info(f"OCR completed for {pdf_path}. Total extracted length: {len(extracted_text)}")
        return extracted_text.strip()

    # Removed redundant outer TesseractNotFoundError catch, inner loop handler re-raises.
    # Catch specific PyMuPDF file opening errors or other RuntimeErrors
    except RuntimeError as fitz_err:
         logging.error(f"PyMuPDF/Runtime error during OCR preparation for {pdf_path}: {fitz_err}", exc_info=True)
         raise RuntimeError(f"PyMuPDF/Runtime error during OCR: {fitz_err}") from fitz_err
    except Exception as e: # General catch for other unexpected errors
        logging.error(f"Unexpected error during OCR for {pdf_path}: {e}", exc_info=True)
        raise RuntimeError(f"Unexpected OCR error: {e}") from e
    finally:
        # Close document if it exists and is not already closed
        if doc is not None and not doc.is_closed:
            doc.close()


# --- File Saving ---

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
            if not EBOOKLIB_AVAILABLE:
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
            ocr_quality_score=None,  # TODO: Calculate if OCR was used
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

                if format_type == 'pdf' and PYMUPDF_AVAILABLE:
                    try:
                        doc = fitz.open(str(original_path))
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