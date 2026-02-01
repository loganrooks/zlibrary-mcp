"""
Footnote marker matching and definition finding helpers.

Contains functions for matching footnote markers in text, extracting text from
blocks, merging bounding boxes, checking marker equivalence, finding definitions
for markers, and finding markerless continuation content.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from lib.rag.utils.cache import _get_cached_text_blocks
from lib.rag.ocr.corruption import _is_ocr_corrupted

logger = logging.getLogger(__name__)

__all__ = [
    '_starts_with_marker',
    '_extract_text_from_block',
    '_merge_bboxes',
    '_markers_are_equivalent',
    '_find_definition_for_marker',
    '_find_markerless_content',
]


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
    text = text.strip()
    for pattern_type in marker_priority:
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
        _markers_are_equivalent("*", "iii")  -> True (known corruption: * -> iii)
        _markers_are_equivalent("dagger", "t")    -> True (known corruption: dagger -> t)
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
        '\u2020': {'\u2020', 't', 'dagger', 'cross'},
        '\u2021': {'\u2021', 'iii', 'tt', 'double-dagger'},
        '\u00a7': {'\u00a7', 's', 'sec', 'section'},
        '\u00b6': {'\u00b6', 'p', 'para', 'paragraph'},
        '\u00b0': {'\u00b0', 'o', '0', 'degree'},
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
            # This allows corruption recovery to fix mismatches later (e.g., "iii" -> "*")
            for pattern_type in marker_priority:
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
        'symbol': r'[*\u2020\u2021\u00a7\u00b6#]'
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
