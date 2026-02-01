"""
Footnote detection, extraction, and formatting for PDF documents.

Contains the marker-driven footnote detection architecture, multi-block
collection, corruption recovery integration, note classification,
and markdown formatting. (~700 lines allowed per plan)
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from lib.rag.utils.cache import _get_cached_text_blocks
from lib.rag.ocr.corruption import _is_ocr_corrupted

# Import continuation tracking and corruption recovery
from lib.footnote_continuation import (
    FootnoteWithContinuation,
    is_footnote_incomplete,
)
from lib.footnote_corruption_model import (
    apply_corruption_recovery,
)
from lib.note_classification import classify_note_comprehensive

__all__ = [
    '_footnote_with_continuation_to_dict',
    '_starts_with_marker',
    '_extract_text_from_block',
    '_merge_bboxes',
    '_markers_are_equivalent',
    '_find_definition_for_marker',
    '_find_markerless_content',
    '_calculate_page_normal_font_size',
    '_is_superscript',
    '_is_ocr_corrupted',
    '_detect_footnotes_in_page',
    '_format_footnotes_markdown',
]

def _footnote_with_continuation_to_dict(footnote: FootnoteWithContinuation) -> Dict[str, Any]:
    """
    Convert FootnoteWithContinuation object to dict format for compatibility.

    Args:
        footnote: FootnoteWithContinuation object from continuation parser

    Returns:
        Dictionary with all footnote metadata including continuation info
    """
    from lib.rag_data_models import NoteSource

    # Convert NoteSource enum to string if needed
    note_source_str = footnote.note_source.name if isinstance(footnote.note_source, NoteSource) else str(footnote.note_source)

    return {
        'marker': footnote.marker,
        'actual_marker': footnote.marker,  # For compatibility with corruption recovery
        'content': footnote.content,
        'pages': footnote.pages,
        'bboxes': footnote.bboxes,
        'is_complete': footnote.is_complete,
        'continuation_confidence': footnote.continuation_confidence,
        'note_source': note_source_str,
        'classification_confidence': footnote.classification_confidence,
        'classification_method': footnote.classification_method,
        'font_name': footnote.font_name,
        'font_size': footnote.font_size,
        # Add incomplete detection fields for consistency
        'incomplete_confidence': 1.0 - footnote.continuation_confidence if not footnote.is_complete else 1.0,
        'incomplete_reason': 'multi_page' if len(footnote.pages) > 1 else 'complete'
    }



def _starts_with_marker(text: str, marker_patterns: dict, marker_priority: list) -> bool:
    """
    Check if text starts with a footnote marker.

    Args:
        text: Text to check
        marker_patterns: Dict of regex patterns for marker matching
        marker_priority: List of pattern types to check

    Returns:
        True if text starts with any marker pattern
    """
    import re

    text = text.strip()
    for pattern_type in marker_priority:
        # BUG-3 FIX: Skip if pattern not in dict
        if pattern_type not in marker_patterns:
            continue

        pattern = marker_patterns[pattern_type]
        if re.match(rf'^({pattern})[\.\s\t]', text):
            return True
    return False



def _extract_text_from_block(block: dict) -> str:
    """
    Extract all text from a PyMuPDF block.

    Args:
        block: PyMuPDF block dict with 'lines' key

    Returns:
        Concatenated text from all lines and spans
    """
    if "lines" not in block:
        return ""

    block_text = ""
    for line in block["lines"]:
        for span in line.get("spans", []):
            block_text += span.get("text", "")

    return block_text.strip()



def _merge_bboxes(blocks: List[dict]) -> dict:
    """
    Merge bounding boxes from multiple blocks into single bbox.

    Args:
        blocks: List of PyMuPDF block dicts with 'bbox' key

    Returns:
        Merged bbox dict with x0, y0, x1, y1 keys
    """
    if not blocks:
        return {'x0': 0, 'y0': 0, 'x1': 0, 'y1': 0}

    x0 = min(b['bbox'][0] for b in blocks)
    y0 = min(b['bbox'][1] for b in blocks)
    x1 = max(b['bbox'][2] for b in blocks)
    y1 = max(b['bbox'][3] for b in blocks)

    return [x0, y0, x1, y1]



def _markers_are_equivalent(marker: str, detected_marker: str) -> bool:
    """
    Check if detected_marker is equivalent to marker (exact match or known corruption).

    ISSUE-FN-004 FIX: This function validates marker equivalence to prevent pairing
    incorrect markers with definitions. For example, marker "4" should NOT match
    a definition starting with "*".

    Args:
        marker: The marker we're searching for (from body text)
        detected_marker: The marker found at definition start (from footer)

    Returns:
        True if markers are equivalent (exact match or known corruption pattern)

    Examples:
        _markers_are_equivalent("*", "*")    -> True (exact match)
        _markers_are_equivalent("*", "iii")  -> True (known corruption: * → iii)
        _markers_are_equivalent("†", "t")    -> True (known corruption: † → t)
        _markers_are_equivalent("4", "*")    -> False (not equivalent)
        _markers_are_equivalent("a", "b")    -> False (different markers)
    """
    # 1. Exact match (most common case)
    if marker == detected_marker:
        return True

    # 2. Known corruption patterns (from SymbolCorruptionModel.CORRUPTION_TABLE)
    # These are observed corruptions where detected_marker could be corrupted from marker
    CORRUPTION_EQUIVALENCES = {
        # marker: set of possible corrupted forms
        '*': {'*', 'iii', 'asterisk'},
        '†': {'†', 't', 'dagger', 'cross'},
        '‡': {'‡', 'iii', 'tt', 'double-dagger'},
        '§': {'§', 's', 'sec', 'section'},
        '¶': {'¶', 'p', 'para', 'paragraph'},
        '°': {'°', 'o', '0', 'degree'},
    }

    # Check if detected_marker is a known corruption of marker
    if marker in CORRUPTION_EQUIVALENCES:
        if detected_marker in CORRUPTION_EQUIVALENCES[marker]:
            return True

    # 3. Reverse check: if detected_marker is the "actual" symbol and marker is corrupted
    # This handles cases where body text has corruption but footer has actual symbol
    for actual_symbol, corruptions in CORRUPTION_EQUIVALENCES.items():
        if detected_marker == actual_symbol and marker in corruptions:
            return True

    # 4. Not equivalent
    return False



def _find_definition_for_marker(page: Any, marker: str, marker_y_position: float, marker_patterns: dict, page_num: int) -> Optional[Dict[str, Any]]:
    """
    Search ENTIRE page below marker position for definition.
    Collects ALL blocks belonging to footnote (multi-block support).

    NOT restricted to bottom 20% - search wherever text appears.
    Handles inline footnotes (Kant at 50-60% down page) and traditional bottom footnotes.

    Args:
        page: PyMuPDF page object
        marker: The marker to search for ('*', '1', 'a', etc.)
        marker_y_position: Y coordinate of marker in body
        marker_patterns: Dict of regex patterns for marker matching
        page_num: Page number (for multi-page tracking)

    Returns:
        Definition dict or None
        {
            'marker': '*',
            'content': 'Footnote text...',
            'bbox': [...],
            'type': 'symbol',
            'source': 'inline' or 'footer',
            'y_position': float,
            'blocks_collected': int,
            'pages': [page_num]
        }
    """
    import re

    # Get all text blocks on page (CACHED)
    blocks = _get_cached_text_blocks(page, "dict")

    # Find the first occurrence of marker at START of a text block BELOW marker position
    # This handles both inline (immediately below) and traditional (page bottom)
    marker_priority = ['numeric', 'roman', 'symbol', 'letter']

    # Sort blocks by y position for sequential processing
    sorted_blocks = sorted([b for b in blocks if "lines" in b], key=lambda b: b["bbox"][1])

    for block_idx, block in enumerate(sorted_blocks):
        # Only consider blocks BELOW the marker
        block_y = block["bbox"][1]  # Top y-coordinate
        if block_y <= marker_y_position:
            continue

        # Check each line in this block
        for line in block.get("lines", []):
            # Extract line text
            line_text = ""
            for span in line["spans"]:
                line_text += span["text"]
            line_text = line_text.strip()

            if not line_text:
                continue

            # Try to match ANY marker pattern at line start
            # Accept: period, space, or tab after marker (Kant uses tabs!)
            # CRITICAL FIX (ISSUE-FN-001): Match ANY marker pattern, not just exact marker
            # This allows corruption recovery to fix mismatches later (e.g., "iii" → "*")
            for pattern_type in marker_priority:
                # BUG-3 FIX: Skip pattern if not in marker_patterns dict
                if pattern_type not in marker_patterns:
                    continue

                pattern = marker_patterns[pattern_type]
                match = re.match(rf'^({pattern})[\.\s\t]', line_text)

                if match:
                    # Found a marker-like pattern at definition start
                    detected_marker = match.group(1)
                    content_start = line_text[match.end():].strip()

                    # ISSUE-FN-004 FIX: Validate that detected marker matches requested marker
                    # Only accept this definition if:
                    # 1. Exact match (detected_marker == marker), OR
                    # 2. Corruption equivalence (detected could be corrupted version of marker)
                    #
                    # This prevents pairing marker "4" with a "*" footnote definition
                    if not _markers_are_equivalent(marker, detected_marker):
                        continue  # Skip this block, keep searching for actual match

                    # Enhanced validation for letter patterns to prevent false positives
                    # Single letters like "a" or "b" should only match if they're likely footnote markers
                    if pattern_type == 'letter':
                        # Reject if:
                        # 1. Content too short (not a real footnote)
                        # 2. Letter is not lowercase (footnotes typically use lowercase)
                        # 3. Not in traditional footnote area (bottom 40% of page)
                        if not content_start or len(content_start) < 3:
                            continue

                        page_height = page.rect.height
                        footnote_area_threshold = page_height * 0.60  # Bottom 40%

                        if not detected_marker.islower():
                            continue

                        if block_y < footnote_area_threshold:
                            continue  # Skip letters in upper part of page (likely body text)

                    # MULTI-BLOCK COLLECTION STRATEGY:
                    # 1. Collect remaining lines in current block
                    # 2. Continue to subsequent blocks until stop condition
                    # Stop conditions:
                    #   - Hit another footnote marker
                    #   - Vertical gap > 10 pixels (new section)
                    #   - Reach end of page

                    collected_blocks = [block]
                    full_content = content_start

                    # Collect remaining lines in first block
                    line_index = block.get("lines", []).index(line)
                    for continuation_line in block.get("lines", [])[line_index + 1:]:
                        continuation_text = ""
                        for span in continuation_line["spans"]:
                            continuation_text += span["text"]
                        continuation_text = continuation_text.strip()

                        if continuation_text:
                            # Check if this is a new footnote (starts with different marker)
                            if _starts_with_marker(continuation_text, marker_patterns, marker_priority):
                                break  # Stop collecting content
                            full_content += ' ' + continuation_text

                    # Collect from subsequent blocks
                    last_block_bottom = block["bbox"][3]  # Bottom y-coordinate

                    for next_block in sorted_blocks[block_idx + 1:]:
                        next_block_top = next_block["bbox"][1]

                        # Check vertical gap (stop if > 10 pixels)
                        vertical_gap = next_block_top - last_block_bottom
                        if vertical_gap > 10:
                            break

                        # Extract text from next block
                        block_text = _extract_text_from_block(next_block)

                        if not block_text.strip():
                            continue

                        # Check if starts with new marker (stop condition)
                        if _starts_with_marker(block_text, marker_patterns, marker_priority):
                            break

                        # Collect this block's content
                        collected_blocks.append(next_block)
                        full_content += ' ' + block_text.strip()
                        last_block_bottom = next_block["bbox"][3]

                    # Merge bounding boxes from all collected blocks
                    merged_bbox = _merge_bboxes(collected_blocks)

                    # Determine if inline or footer based on y position
                    # Inline: within 200 pixels of marker (roughly same column/region)
                    # Footer: > 200 pixels below marker (traditional bottom footnote)
                    distance_from_marker = block_y - marker_y_position
                    source = 'inline' if distance_from_marker < 200 else 'footer'

                    # CRITICAL FIX (ISSUE-FN-001 continued):
                    # Use requested_marker as the primary marker (what body text has)
                    # Store detected_marker as observed_text for corruption recovery
                    return {
                        'marker': marker,  # Use requested marker from body text
                        'observed_marker': detected_marker,  # Store what we actually found in footer
                        'content': full_content,
                        'bbox': merged_bbox,
                        'type': pattern_type,
                        'source': source,
                        'y_position': block_y,
                        'blocks_collected': len(collected_blocks),
                        'pages': [page_num]  # CRITICAL: Enable multi-page tracking
                    }

    return None  # No definition found



def _find_markerless_content(page: Any, existing_definitions: List[Dict[str, Any]], marker_y_positions: Dict[str, float], page_num: int) -> List[Dict[str, Any]]:
    """
    Find text blocks WITHOUT markers that could be continuations.

    Signals for markerless continuations:
    - Near other footnote definitions (spatial proximity)
    - In traditional footnote area (bottom 20%)
    - Similar font to other footnotes
    - Starts lowercase or with conjunction
    - No marker at beginning of text

    Args:
        page: PyMuPDF page object
        existing_definitions: List of already-found definitions
        marker_y_positions: Dict mapping markers to their y positions
        page_num: Page number (for multi-page tracking)

    Returns:
        List of potential continuation dicts with confidence scores
        [{
            'marker': None,
            'content': 'which everything must submit...',
            'bbox': {...},
            'potential_continuation': True,
            'continuation_confidence': 0.85,
            'pages': [page_num],
            'nearest_definition': '*'  # Closest existing definition
        }]
    """
    import re

    if not existing_definitions:
        return []  # No definitions to continue

    page_height = page.rect.height

    # EXPANDED SEARCH AREA: Bottom 50% instead of 20%
    # Rationale: Inline footnote continuations (like Kant) can appear mid-page (50-70%)
    # Traditional bottom-only footnotes still work with this threshold
    # False positive risk is mitigated by strong continuation signals (starts lowercase, continuation words)
    traditional_footnote_threshold = page_height * 0.50  # Bottom 50%

    # Get all text blocks (CACHED)
    blocks = _get_cached_text_blocks(page, "dict")

    # Build spatial index of existing definitions
    definition_positions = {}
    for defn in existing_definitions:
        if defn.get('bbox'):
            definition_positions[defn['marker']] = defn['bbox'][1]  # y position

    # Common footnote marker patterns (to exclude blocks that ARE footnotes)
    marker_patterns = {
        'numeric': r'\d+',
        'roman': r'(?:i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3})',
        'letter': r'[a-z]',
        'symbol': r'[*†‡§¶#]'
    }

    markerless_candidates = []

    for block in blocks:
        if "lines" not in block:
            continue

        # Extract block text
        block_text = ""
        for line in block.get("lines", []):
            for span in line["spans"]:
                block_text += span["text"] + " "
        block_text = block_text.strip()

        if not block_text or len(block_text) < 10:
            continue  # Too short

        # Check if block starts with a marker (if so, it's a new footnote, not continuation)
        has_marker_at_start = False
        for pattern in marker_patterns.values():
            if re.match(rf'^({pattern})[\.\s\t]', block_text):
                has_marker_at_start = True
                break

        if has_marker_at_start:
            continue  # This is a new footnote, not a continuation

        # Calculate confidence signals
        block_y = block["bbox"][1]
        confidence_signals = {}

        # Signal 1: Proximity to existing definition
        min_distance = float('inf')
        nearest_definition = None
        for marker, defn_y in definition_positions.items():
            distance = abs(block_y - defn_y)
            if distance < min_distance:
                min_distance = distance
                nearest_definition = marker

        confidence_signals['proximity'] = max(0, 1.0 - (min_distance / 100))  # Within 100px = high confidence

        # Signal 2: In traditional footnote area
        if block_y >= traditional_footnote_threshold:
            confidence_signals['in_footnote_area'] = 0.7
        else:
            confidence_signals['in_footnote_area'] = 0.3

        # Signal 3: Starts with lowercase or continuation words
        starts_lowercase = block_text[0].islower()
        continuation_words = ['which', 'who', 'whom', 'whose', 'that', 'and', 'but', 'or']
        starts_with_continuation = any(block_text.lower().startswith(word + ' ') for word in continuation_words)

        if starts_lowercase or starts_with_continuation:
            confidence_signals['continuation_text'] = 0.8
        else:
            confidence_signals['continuation_text'] = 0.2

        # Signal 4: Font similarity (extract from block if available)
        # Check if block has font info and compare with existing definitions
        font_match_score = 0.5  # Default
        if block.get('lines'):
            # Get first span's font info
            first_line = block['lines'][0]
            if first_line.get('spans'):
                first_span = first_line['spans'][0]
                block_font_name = first_span.get('font', '')
                block_font_size = first_span.get('size', 0)

                # Compare with existing definitions' fonts
                for defn in existing_definitions:
                    defn_font_name = defn.get('font_name', '')
                    defn_font_size = defn.get('font_size', 0)

                    if defn_font_name and block_font_name:
                        # Check if fonts match or are similar
                        if defn_font_name == block_font_name:
                            # Exact match
                            size_diff = abs(block_font_size - defn_font_size) if defn_font_size else 0
                            if size_diff < 1.0:  # Within 1pt
                                font_match_score = 0.9
                                break
                            elif size_diff < 2.0:  # Within 2pt
                                font_match_score = 0.7
                                break

        confidence_signals['font_match'] = font_match_score

        # Calculate overall confidence (weighted average)
        # ADJUSTED WEIGHTS: Prioritize continuation text signals over spatial signals
        # This handles inline footnotes better (Kant case)
        weights = {
            'proximity': 0.3,  # Reduced from 0.4
            'in_footnote_area': 0.15,  # Reduced from 0.2
            'continuation_text': 0.45,  # Increased from 0.3 (PRIMARY signal)
            'font_match': 0.1  # Unchanged
        }

        overall_confidence = sum(confidence_signals[k] * weights[k] for k in weights)

        # Lowered threshold from 0.6 to 0.55 to catch inline continuations
        # Strong continuation signals (starts with 'which', lowercase) should push above threshold
        if overall_confidence > 0.55:
            # Format to match CrossPageFootnoteParser expectations
            markerless_candidates.append({
                'marker': None,  # Explicitly no marker (continuation)
                'content': block_text,
                'bbox': block["bbox"],
                'is_continuation': True,  # Flag for CrossPageFootnoteParser
                'continuation_confidence': overall_confidence,
                'nearest_definition': nearest_definition,
                'y_position': block_y,
                'confidence_signals': confidence_signals,
                'pages': [page_num],  # CRITICAL: Enable multi-page tracking
                # Optional metadata for debugging
                'source': 'markerless',
                'type': 'continuation'
            })

    return markerless_candidates




def _calculate_page_normal_font_size(blocks: List[Dict[str, Any]]) -> float:
    """
    Calculate the normal/average font size for body text on a page.

    Strategy:
    1. Collect all font sizes from text spans
    2. Use median (more robust to outliers than mean)
    3. Filter out extreme sizes (headers, footnotes)

    Args:
        blocks: PyMuPDF text blocks from page.get_text("dict")["blocks"]

    Returns:
        Normal font size in points (typically 9-12pt for body text)
    """
    font_sizes = []

    for block in blocks:
        if block.get('type') != 0:  # Skip non-text blocks
            continue

        for line in block.get('lines', []):
            for span in line.get('spans', []):
                size = span.get('size', 0)
                if size > 0:  # Valid size
                    font_sizes.append(size)

    if not font_sizes:
        return 10.0  # Default fallback

    # Use median for robustness
    font_sizes.sort()
    n = len(font_sizes)
    if n % 2 == 0:
        median = (font_sizes[n//2 - 1] + font_sizes[n//2]) / 2
    else:
        median = font_sizes[n//2]

    return median



def _is_superscript(span: Dict[str, Any], normal_font_size: float) -> bool:
    """
    Detect if a span is superscript formatted using multiple signals.

    Superscript Detection Strategy (Multi-Signal):
    1. PRIMARY: PyMuPDF superscript flag (bit 0 in flags)
    2. VALIDATION: Font size ratio (superscripts are 60-85% of normal)
    3. FALLBACK: If flag missing but size ratio matches, still accept

    Real-world data from Kant PDF:
    - Normal text: 9.24pt, flags=4
    - Superscript markers: 5.83pt, flags=5 (bit 0 set)
    - Size ratio: 5.83/9.24 = 0.631 (63%)

    Args:
        span: PyMuPDF span dict with 'size', 'flags', 'origin', 'bbox'
        normal_font_size: Average font size for body text on page

    Returns:
        True if superscript, False otherwise

    Performance:
        <0.1ms per span check (bit operations + float comparison)
    """
    # Signal 1: Check superscript flag (bit 0)
    flags = span.get('flags', 0)
    has_super_flag = (flags & 1) != 0  # Bit 0 = superscript

    # Signal 2: Check font size ratio
    span_size = span.get('size', normal_font_size)
    size_ratio = span_size / normal_font_size if normal_font_size > 0 else 1.0

    # Superscripts are typically 60-85% of normal size
    # Too small (<50%) might be subscript or corruption
    # Too large (>90%) is likely normal text with flag error
    is_smaller = 0.50 < size_ratio < 0.85

    # Decision logic:
    # - Flag + size ratio: DEFINITE superscript (both signals agree)
    # - Flag only: LIKELY superscript (trust PyMuPDF)
    # - Size only: POSSIBLE superscript (could be small text)
    #
    # We accept if flag is set OR both size and flag conditions suggest superscript
    # This handles both:
    # - Correct PDFs with proper flags
    # - PDFs with missing flags but correct sizing

    if has_super_flag:
        # Flag is set - validate with size if available
        if span_size > 0:
            # If flag is set but size is normal, flag might be error
            # Accept anyway (trust PyMuPDF flag)
            return True
        return True

    # No flag - use size as fallback
    # Only accept if significantly smaller (avoid false positives)
    if is_smaller and size_ratio < 0.75:
        # Very small text without flag - likely superscript with missing flag
        return True

    return False





def _detect_footnotes_in_page(page: Any, page_num: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect footnotes/endnotes in a PDF page using marker-driven architecture.

    MARKER-DRIVEN STRATEGY (NEW):
    1. Scan body text for footnote markers (superscript, special symbols)
    2. For each marker, search ENTIRE page below marker for definition (NOT restricted to bottom 20%)
    3. Find markerless content that could be continuations
    4. Apply corruption recovery and classification

    This handles:
    - Traditional bottom footnotes (Derrida)
    - Inline footnotes mid-page (Kant at 50-60%)
    - Markerless continuations across pages

    Args:
        page: PyMuPDF page object
        page_num: Page number (0-indexed)

    Returns:
        Dictionary with 'markers' and 'definitions' lists:
        {
            'markers': [{'marker': '1', 'bbox': [...], 'context': '...'}],
            'definitions': [{'marker': '1', 'content': '...', 'bbox': [...]}]
        }
    """
    import re

    result = {
        'markers': [],
        'definitions': []
    }

    # Get page dimensions
    page_height = page.rect.height

    # Get all text blocks with position (CACHED)
    blocks = _get_cached_text_blocks(page, "dict")

    # Calculate normal font size for superscript detection
    normal_font_size = _calculate_page_normal_font_size(blocks)

    # Common footnote marker patterns
    # - Numeric: 1, 2, 3, ... (as superscript or regular)
    # - Symbols: *, †, ‡, §, ¶, #
    # - Letters: a, b, c, ... (as superscript)
    # - Roman numerals: i, ii, iii, iv, ...

    marker_patterns = {
        'numeric': r'\d+',
        'roman': r'(?:i{1,3}|iv|v|vi{0,3}|ix|x|xi{0,3})',  # i-xiii
        'letter': r'[a-z]',
        'symbol': r'[*†‡§¶#]'
    }

    # PHASE 1: Scan body text for footnote markers
    # No spatial restriction - scan entire page for markers
    marker_y_positions = {}  # Track marker positions for definition search

    for block in blocks:
        if "lines" not in block:
            continue

        # Get first line text to check if block starts with a footnote marker
        block_first_line = ""
        if block.get("lines"):
            for span in block.get("lines", [])[0].get("spans", []):
                block_first_line += span.get("text", "")
        # Check if block starts with pattern like "* text" or "1. text"
        block_starts_with_marker = bool(re.match(r'^[*†‡§¶#\d]+[\.\s\t]', block_first_line.strip()))

        for line_idx, line in enumerate(block.get("lines", [])):
            line_text = ""
            span_positions = []  # Track where each span starts

            for span in line["spans"]:
                span_positions.append(len(line_text))
                line_text += span["text"]

            # Process spans with position knowledge
            for span_idx, span in enumerate(line["spans"]):
                text = span["text"]
                span_start_pos = span_positions[span_idx]

                # Check for superscript markers using enhanced multi-signal detection
                is_superscript = _is_superscript(span, normal_font_size)

                # Check for footnote symbols (even if not superscript)
                is_footnote_symbol = text.strip() in ['*', '†', '‡', '§', '¶', '°', '∥', '#']

                # Detect markers in multiple contexts:
                # 1. Superscript text (numbers or symbols) - HIGH CONFIDENCE
                # 2. Footnote symbols after headings/text - MEDIUM CONFIDENCE
                # 3. Symbols within brackets [p. 23†] - HIGH CONFIDENCE
                is_in_bracket = '[' in line_text and ']' in line_text and is_footnote_symbol

                # CRITICAL FILTER: Exclude markers at START of blocks that look like footnote definitions
                # Example: "* Now and again..." → NOT a marker (it's the footnote definition start)
                # Example: "text * text" → IS a marker (in body text)
                #
                # CRITICAL FIX (ISSUE-FN-001): Check if marker is first CHARACTER in span TEXT,
                # not if span is first in block. The bug was checking span_start_pos (span position
                # in line) instead of checking if the marker is at the start of the span's text.
                #
                # Correct scenarios:
                # - Definition: "* The title..." → marker IS first char in span → skip ✓
                # - Body text: "text *" → marker IS NOT first char in span → detect ✓
                #
                # Buggy version checked: (line_idx == 0 and span_start_pos == 0)
                # This gave false positives: "text *" had span_start_pos==0 (span is first)
                # but marker "*" was NOT at start of span text!

                # Check: Does this LINE's TEXT start with a marker pattern?
                # We check the LINE text, not the span text, because a marker at the end
                # of a line ("text *") would have a span starting with *, but the LINE doesn't.
                # This correctly identifies footnote definitions like "* The title..."
                line_text_clean = line_text.strip()
                marker_pattern_at_start = bool(re.match(r'^[*†‡§¶#\d]+', line_text_clean))
                is_at_definition_start = (line_idx == 0 and marker_pattern_at_start)

                if is_at_definition_start and block_starts_with_marker and not is_superscript:
                    # This is a footnote DEFINITION start (e.g., "* The title...")
                    # Skip it - we already detected the marker in body text
                    continue

                # IMPORTANT: Only accept as marker if:
                # - Superscript (any character) OR
                # - Known footnote symbol (*, †, ‡, etc.) AND NOT at definition start OR
                # - In bracket context OR
                # - CORRUPTION-AWARE: Known corruption pattern (NEW FIX for BUG-1)
                # Reject: random letters that aren't superscript

                marker_text = text.strip()

                # BUG-1 FIX: Check for known corruption patterns
                # If we already detected markers, check if this text matches corruption table
                # Example: After detecting '*', a standalone 't' is likely corrupted '†'
                # This allows corruption recovery to run even on non-superscript corrupted markers
                is_known_corruption = False
                if result['markers'] and len(marker_text) <= 3 and not is_at_definition_start:
                    # Known corruption patterns from footnote_corruption_model.py CORRUPTION_TABLE
                    # These are OBSERVED corruptions that should map to ACTUAL symbols
                    corruption_chars = {
                        't',    # † → 't' (85% probability)
                        'iii',  # * → 'iii' OR ‡ → 'iii'
                        'tt',   # ‡ → 'tt'
                        's',    # § → 's'
                        'p',    # ¶ → 'p'
                        'o',    # ° → 'o'
                        '0',    # ° → '0'
                        'sec',  # § → 'sec'
                        'para'  # ¶ → 'para'
                    }
                    if marker_text in corruption_chars:
                        # Additional context check: only accept if font size is reasonable for body text
                        # This prevents catching random body text words
                        font_size = span.get('size', 10.0)
                        if 8.0 <= font_size <= 12.0:  # Typical body text range
                            is_known_corruption = True
                            logging.debug(f"Detected potential corrupted marker: '{marker_text}' (after {len(result['markers'])} markers, size: {font_size:.1f})")

                # BUG-2 FIX: Stricter validation for superscript markers
                # Not ALL superscripts are footnote markers (e.g., page refs, math notation, cross-refs)
                # Require superscript + (symbol OR sequential digit/letter)
                is_valid_superscript = False
                if is_superscript:
                    # Check if it's a known footnote symbol
                    if marker_text in ['*', '†', '‡', '§', '¶', '#', '°', '∥']:
                        is_valid_superscript = True
                    # BUG-3 FIX: OR numeric marker (single or multi-digit) with validation
                    elif marker_text.isdigit():
                        # Numeric markers can be 1-2 digits (e.g., 1-20 are common in academic texts)
                        # Reject if >20 (likely page/section reference)
                        digit_val = int(marker_text)

                        if digit_val > 20:
                            # Too large, likely page number or section reference
                            pass  # is_valid_superscript remains False
                        elif len(marker_text) == 1:
                            # Single digit (1-9): Be permissive for superscripts
                            # BUG-3 FIX: Accept any single-digit superscript 1-9
                            # Being superscript is strong enough signal
                            # Don't require strict sequencing (pages can have independent sequences)
                            if digit_val <= 9:
                                is_valid_superscript = True
                            # Could still validate sequence as confidence signal, but don't reject
                        else:
                            # Multi-digit (10-20): Accept if superscript (rules out body text)
                            # Being superscript is strong signal it's a footnote marker, not page number
                            is_valid_superscript = True
                    # BUG-3 FIX: OR single letter a-j with relaxed isolation (handles hyphenated words)
                    elif marker_text.isalpha() and len(marker_text) == 1:
                        # Check isolation - must have space/punctuation before OR after
                        # RELAXED: Allow letter-before (handles "prin-ciplee" where e is marker)
                        span_pos = span_positions[span_idx]
                        before_char = line_text[span_pos - 1] if span_pos > 0 else ' '
                        after_pos = span_pos + len(marker_text)
                        after_char = line_text[after_pos] if after_pos < len(line_text) else ' '

                        # BUG-3 FIX: Relaxed isolation for superscript letters
                        # Original: Required space/punct BOTH before AND after
                        # New: Require space/punct AFTER (before can be letter for hyphenation)
                        # Example: "ciplee" where 'e' is superscript marker after word
                        has_isolation_after = after_char in ' \t)]}.,;:\n'

                        if marker_text in 'abcdefghij' and has_isolation_after:
                            is_valid_superscript = True

                is_likely_marker = (
                    is_valid_superscript or  # BUG-2 FIX: Stricter superscript validation
                    (is_footnote_symbol and not is_at_definition_start) or  # Symbol in body (not definition start)
                    is_in_bracket or  # Bracketed symbols
                    is_known_corruption  # BUG-1 FIX: Known corruption patterns
                )

                # Extra filter for single letters ONLY if not already identified as marker
                # This prevents false positives from OCR corruption like "h", "t"
                # Single letters can be:
                # 1. Superscript markers (a, b, c) - ALREADY accepted above
                # 2. Valid footnote markers (a-j) with formatting AND isolation - Check here
                # 3. Random body text ("The", "And") - REJECT
                # 4. OCR corruption fragments ("h", "t") - REJECT
                if not is_likely_marker and marker_text.isalpha() and len(marker_text) == 1:
                    # Whitelist of valid single-letter markers in academic texts
                    # Common alphabetic markers: a-j (covers most footnote sequences)
                    VALID_SINGLE_LETTERS = set('abcdefghij')

                    # Check if letter has special formatting (bold, italic, superscript)
                    # PyMuPDF flags: 1=superscript, 2=italic, 4=serifed, 8=monospaced, 16=bold
                    # Special formatting = bold OR italic OR superscript (not just serifed)
                    span_flags = span.get("flags", 0)
                    has_special_formatting = bool(span_flags & (1 | 2 | 16))  # superscript | italic | bold

                    # Check if letter is isolated (surrounded by spaces/punctuation)
                    # Extract context around this span
                    span_pos = span_positions[span_idx]
                    before_char = line_text[span_pos - 1] if span_pos > 0 else ' '
                    after_pos = span_pos + len(marker_text)
                    after_char = line_text[after_pos] if after_pos < len(line_text) else ' '
                    is_isolated = before_char in ' \t([{' and after_char in ' \t)]}.,;:'

                    # STRICTER LOGIC: Require ALL of:
                    # 1. Lowercase letter
                    # 2. In whitelist of valid markers
                    # 3. Has special formatting (bold/italic)
                    # 4. Is isolated (not part of word)
                    # This prevents false positives from OCR fragments like "h", "t"
                    if (marker_text.islower() and
                        marker_text in VALID_SINGLE_LETTERS and
                        has_special_formatting and
                        is_isolated):
                        # Likely a valid footnote marker
                        is_likely_marker = True
                    else:
                        # Likely body text or OCR corruption
                        is_likely_marker = False

                if is_likely_marker:
                    # Potential footnote marker
                    marker_text = text.strip()

                    # OCR QUALITY FILTER: Reject corrupted text before pattern matching
                    # This prevents false positives from OCR artifacts like "the~", "cnt.i,ic~"
                    is_corrupted, corruption_conf, corruption_reason = _is_ocr_corrupted(marker_text)
                    if is_corrupted:
                        logging.debug(
                            f"Rejecting OCR corrupted marker candidate: '{marker_text}' "
                            f"({corruption_reason}, confidence: {corruption_conf:.2f})"
                        )
                        continue  # Skip this span, don't add to markers

                    # For symbols, match against patterns
                    for pattern_type, pattern in marker_patterns.items():
                        if re.match(pattern, marker_text):
                            marker_bbox = span.get("bbox", block["bbox"])
                            marker_y = marker_bbox[1]  # Top y-coordinate

                            result['markers'].append({
                                'marker': marker_text,
                                'text': marker_text,  # Add explicit text field
                                'bbox': marker_bbox,
                                'context': line_text[:100],
                                'type': pattern_type,
                                'is_superscript': is_superscript,
                                'source': 'body'  # Mark as from body (more reliable)
                            })

                            # Track marker position for definition search
                            # Use earliest occurrence if marker appears multiple times
                            if marker_text not in marker_y_positions:
                                marker_y_positions[marker_text] = marker_y
                            break  # Don't match multiple patterns

    # EARLY EXIT: Traditional footnotes fast path
    # If all markers are numeric AND all definitions are in bottom 30% of page,
    # we can skip inline and markerless detection (saves ~3.6ms)
    if result['markers']:
        all_numeric = all(m.get('type') == 'numeric' for m in result['markers'])
        traditional_threshold = page_height * 0.70  # Bottom 30%

        # Quick check: Are markers in traditional footnote area?
        markers_in_traditional_area = all(
            marker_y_positions.get(m['marker'], 0) > traditional_threshold
            for m in result['markers']
        )

        use_fast_path = all_numeric and markers_in_traditional_area

        if use_fast_path:
            # Traditional footnotes: Just find definitions, skip markerless
            for marker_dict in result['markers']:
                marker = marker_dict['marker']
                marker_y = marker_y_positions.get(marker, 0)

                definition = _find_definition_for_marker(page, marker, marker_y, marker_patterns, page_num)

                if definition:
                    definition['marker_position'] = marker_dict['bbox']
                    definition['is_superscript'] = marker_dict.get('is_superscript', False)
                    result['definitions'].append(definition)

            # Skip markerless detection for traditional footnotes
            markerless = []
        else:
            # Full detection path: Inline or mixed footnotes
            # PHASE 2: For each marker, find definition ANYWHERE on page below marker
            for marker_dict in result['markers']:
                marker = marker_dict['marker']
                marker_y = marker_y_positions.get(marker, 0)

                definition = _find_definition_for_marker(page, marker, marker_y, marker_patterns, page_num)

                if definition:
                    # Add marker info to definition
                    definition['marker_position'] = marker_dict['bbox']
                    definition['is_superscript'] = marker_dict.get('is_superscript', False)
                    result['definitions'].append(definition)

            # PHASE 3: Find markerless content (potential continuations)
            markerless = _find_markerless_content(page, result['definitions'], marker_y_positions, page_num)
            result['definitions'].extend(markerless)
    else:
        # No markers found, still check for markerless
        markerless = _find_markerless_content(page, result['definitions'], marker_y_positions, page_num)
        result['definitions'].extend(markerless)

    # BUG-2 FIX: Deduplication for TRUE duplicates only (same marker + same bbox)
    # Don't deduplicate different markers in same bbox (multi-footnote blocks like Derrida)
    # Example: Derrida has both * and † in single block "iii ...text... t ...text..."
    seen_marker_bbox_pairs = set()
    unique_definitions = []
    for definition in result.get('definitions', []):
        marker = definition.get('marker', '?')
        bbox = definition.get('bbox', {})
        bbox_key = tuple(bbox) if isinstance(bbox, (list, tuple)) else str(bbox)

        # Deduplication key: (marker, bbox) not just bbox
        dedup_key = (marker, bbox_key)

        if dedup_key not in seen_marker_bbox_pairs:
            seen_marker_bbox_pairs.add(dedup_key)
            unique_definitions.append(definition)
        else:
            logging.debug(f"Skipping TRUE duplicate: marker '{marker}' at same bbox")

    result['definitions'] = unique_definitions
    if len(result.get('definitions', [])) != len(unique_definitions):
        logging.debug(f"Deduplication: {len(result.get('definitions', []))} → {len(unique_definitions)} definitions")

    # Apply corruption recovery using Bayesian inference
    # Use schema from body markers to correct footer corruptions
    corrected_markers, corrected_definitions = apply_corruption_recovery(
        result.get('markers', []),
        unique_definitions  # BUG-2 FIX: Use deduplicated definitions
    )

    # Detect schema type for classification
    # Import locally to avoid circular dependency issues
    from lib.footnote_corruption_model import _detect_schema_type
    detected_schema = _detect_schema_type(corrected_markers)

    # Apply note classification to corrected definitions
    # This determines if notes are from author, translator, or editor
    classified_definitions = []
    for definition in corrected_definitions:
        marker = definition.get('actual_marker', definition.get('marker', ''))
        content = definition.get('content', '')

        # SKIP CLASSIFICATION for markerless continuations
        # These don't have markers and will be merged by CrossPageFootnoteParser
        if marker is None:
            # Pass through without classification
            classified_definitions.append({
                **definition,
                'note_source': 'CONTINUATION',  # Special marker for continuations
                'classification_confidence': definition.get('confidence', 0.5),
                'classification_method': 'markerless',
                'classification_evidence': {'reason': 'markerless continuation, no classification needed'}
            })
            continue

        # Build marker_info dict for classification
        marker_info = {
            'is_superscript': definition.get('is_superscript', False),
            'is_lowercase': marker.islower() if marker else False,
            'is_uppercase': marker.isupper() if marker else False,
            'content_length': len(content)
        }

        try:
            # Perform comprehensive classification
            classification_result = classify_note_comprehensive(
                marker=marker,
                content=content,
                schema_type=detected_schema,
                marker_info=marker_info
            )

            # Add classification fields to definition
            classified_def = {
                **definition,
                'note_source': classification_result['note_source'].name,  # Convert enum to string name (AUTHOR, TRANSLATOR, etc.)
                'classification_confidence': classification_result['confidence'],
                'classification_method': classification_result['method'],
                'classification_evidence': classification_result['evidence']
            }
            classified_definitions.append(classified_def)

            # Log classification for debugging
            logging.debug(
                f"Note classification: marker='{marker}' → {classification_result['note_source'].name} "
                f"(confidence: {classification_result['confidence']:.2f}, method: {classification_result['method']})"
            )

        except Exception as e:
            # If classification fails, default to UNKNOWN and log error
            logging.warning(f"Classification failed for marker '{marker}': {e}")
            from lib.rag_data_models import NoteSource
            classified_def = {
                **definition,
                'note_source': NoteSource.UNKNOWN.name,  # Use .name for string representation
                'classification_confidence': 0.0,
                'classification_method': 'error',
                'classification_evidence': {'error': str(e)}
            }
            classified_definitions.append(classified_def)

    # Phase 3: Add incomplete detection to each footnote
    # This enables multi-page continuation tracking
    for definition in classified_definitions:
        content = definition.get('content', '')
        is_incomplete, confidence, reason = is_footnote_incomplete(content)

        definition['is_complete'] = not is_incomplete
        definition['incomplete_confidence'] = confidence
        definition['incomplete_reason'] = reason

        # Log incomplete detections for debugging
        if is_incomplete:
            marker = definition.get('actual_marker', definition.get('marker', ''))
            logging.debug(
                f"Footnote '{marker}' incomplete (confidence: {confidence:.2f}, reason: {reason})"
            )

    # Return corrected results with classification
    return {
        'markers': corrected_markers,
        'definitions': classified_definitions,
        'corruption_applied': True,
        'schema_type': detected_schema
    }



def _format_footnotes_markdown(footnotes: Dict[str, Any]) -> str:
    """
    Format detected footnotes as markdown footnote syntax.

    Uses corrected symbols from corruption recovery if available.

    Args:
        footnotes: Dictionary from _detect_footnotes_in_page() with corruption recovery

    Returns:
        Markdown footnote definitions: [^*]: Content or [^†]: Content
    """
    lines = []

    for definition in footnotes.get('definitions', []):
        # Use actual_marker if corruption recovery was applied
        marker = definition.get('actual_marker', definition.get('marker', '?'))
        content = definition.get('content', '')

        # Add confidence information as HTML comment if low confidence
        confidence = definition.get('confidence', 1.0)
        if confidence < 0.75:
            confidence_note = f"<!-- Confidence: {confidence:.2f}, Method: {definition.get('inference_method', 'unknown')} -->"
            lines.append(f"[^{marker}]: {content}\n{confidence_note}")
        else:
            # Markdown footnote syntax
            lines.append(f"[^{marker}]: {content}")

    return "\n\n".join(lines)

