"""
Marginalia extraction using spatial semantic segmentation.

Detects margins vs. body text spatially, extracts marginal content,
classifies as citations vs. notes, and injects inline markers.
"""

import re
import logging
from typing import Dict, List, Tuple


# Citation system patterns (easily extensible - just add new patterns here)
CITATION_PATTERNS = {
    'kant_a_b': {
        'pattern': r'^[AB]\s*\d+$',
        'description': "Kant's Critique A/B editions (1781/1787)",
        'examples': ['A 50', 'B 75', 'A123', 'B 200']
    },
    'stephanus': {
        'pattern': r'^\d+[a-e]$',
        'description': 'Plato dialogues - Stephanus pagination',
        'examples': ['245c', '246a', '247d']
    },
    'bekker': {
        'pattern': r'^\d+[ab]\d+$',
        'description': 'Aristotle - Bekker numbers',
        'examples': ['184b15', '1094a1', '1098b20']
    },
    'heidegger_sz': {
        'pattern': r'^(SZ\s*)?\d+$',
        'description': 'Heidegger Being and Time - German pages',
        'examples': ['SZ 41', 'SZ42', '41', '42']
    },
    'oxford_classical': {
        'pattern': r'^\d+\.\d+$',
        'description': 'Oxford Classical Texts',
        'examples': ['12.5', '34.10']
    },
    # Easy to add new systems:
    # 'new_system': {
    #     'pattern': r'your_regex_here',
    #     'description': 'Description of system',
    #     'examples': ['example1', 'example2']
    # }
}


def analyze_document_layout_adaptive(doc, sample_pages: List[int] = None, num_samples: int = 20) -> Dict:
    """
    Adaptively analyze document layout across multiple pages using statistical clustering.

    NO fixed thresholds - learns margin positions from actual text distribution.

    Algorithm:
    1. Sample multiple pages throughout document
    2. Collect all x-coordinates (left edges of all text blocks)
    3. Build histogram and identify clusters
    4. Largest cluster = body text zone
    5. Edge clusters = potential margins
    6. Validate margins by checking content patterns

    Args:
        doc: PyMuPDF document object
        sample_pages: Specific pages to analyze (None = auto-sample)
        num_samples: Number of pages to sample

    Returns:
        {
            'page_width': float,
            'page_height': float,
            'body_zone': {'x_start': float, 'x_end': float, 'confidence': float},
            'left_margin': {'x_start': float, 'x_end': float, 'has_content': bool},
            'right_margin': {'x_start': float, 'x_end': float, 'has_content': bool},
            'layout_type': str  # 'single_column', 'double_column', 'with_margins', etc.
        }
    """
    import collections

    total_pages = len(doc)

    # Sample pages evenly throughout document
    if sample_pages is None:
        step = max(1, total_pages // num_samples)
        sample_pages = list(range(0, total_pages, step))[:num_samples]

    # Collect x-coordinates from all sampled pages
    all_x_left = []
    all_x_right = []
    page_dimensions = []

    for page_idx in sample_pages:
        if page_idx >= total_pages:
            continue

        page = doc[page_idx]
        page_dimensions.append((page.rect.width, page.rect.height))

        blocks = page.get_text("dict")['blocks']

        for block in blocks:
            if block.get('type') != 0:  # Skip non-text blocks
                continue

            bbox = block['bbox']
            x_left = bbox[0]
            x_right = bbox[2]

            all_x_left.append(x_left)
            all_x_right.append(x_right)

    # Use most common page dimensions
    page_width = collections.Counter([w for w, h in page_dimensions]).most_common(1)[0][0]
    page_height = collections.Counter([h for w, h in page_dimensions]).most_common(1)[0][0]

    if not all_x_left:
        # No text found - return default
        logging.warning("No text found in sampled pages, using defaults")
        return _default_zones(page_width, page_height)

    # Cluster x-coordinates using simple histogram binning
    # Bin width: 5 pixels
    bin_width = 5
    bins = int(page_width / bin_width)

    # Count x_left positions in each bin
    left_histogram = [0] * bins
    for x in all_x_left:
        bin_idx = min(int(x / bin_width), bins - 1)
        left_histogram[bin_idx] += 1

    # Find main body text cluster (largest peak in histogram)
    # Look for sustained high-frequency region (not just single peak)
    max_count = max(left_histogram)
    threshold = max_count * 0.3  # 30% of peak

    # Find continuous region above threshold
    body_start_bin = None
    body_end_bin = None

    for i, count in enumerate(left_histogram):
        if count >= threshold:
            if body_start_bin is None:
                body_start_bin = i
            body_end_bin = i

    if body_start_bin is None:
        # Fallback
        return _default_zones(page_width, page_height)

    # Convert bins back to x-coordinates
    body_x_start = body_start_bin * bin_width
    body_x_end = (body_end_bin + 1) * bin_width

    # Refine using actual positions
    body_texts = [x for x in all_x_left if body_x_start <= x <= body_x_end]
    if body_texts:
        body_x_start = min(body_texts)
        body_x_end_candidates = [x for x in all_x_right if x >= body_x_start]
        if body_x_end_candidates:
            body_x_end = max(body_x_end_candidates)

    # Check for marginal content
    left_margin_content = [x for x in all_x_left if x < body_x_start - 10]
    right_margin_content = [x for x in all_x_left if x > body_x_end + 10]

    zones = {
        'page_width': page_width,
        'page_height': page_height,
        'body_zone': {
            'x_start': body_x_start,
            'x_end': body_x_end,
            'confidence': len(body_texts) / len(all_x_left) if all_x_left else 0
        },
        'left_margin': {
            'x_start': 0,
            'x_end': body_x_start - 10,
            'has_content': len(left_margin_content) > 0
        },
        'right_margin': {
            'x_start': body_x_end + 10,
            'x_end': page_width,
            'has_content': len(right_margin_content) > 0
        },
        'layout_type': _infer_layout_type(body_x_start, body_x_end, page_width,
                                          len(left_margin_content), len(right_margin_content))
    }

    logging.info(f"Adaptive layout detection: body=[{body_x_start:.1f}, {body_x_end:.1f}], "
                 f"left_margin={len(left_margin_content)} blocks, "
                 f"right_margin={len(right_margin_content)} blocks, "
                 f"type={zones['layout_type']}")

    return zones


def _default_zones(page_width: float, page_height: float) -> Dict:
    """Fallback to standard zones if detection fails."""
    body_start = page_width * 0.15
    body_end = page_width * 0.85

    return {
        'page_width': page_width,
        'page_height': page_height,
        'body_zone': {'x_start': body_start, 'x_end': body_end, 'confidence': 0.0},
        'left_margin': {'x_start': 0, 'x_end': body_start - 10, 'has_content': False},
        'right_margin': {'x_start': body_end + 10, 'x_end': page_width, 'has_content': False},
        'layout_type': 'unknown'
    }


def _infer_layout_type(body_start: float, body_end: float, page_width: float,
                       left_margin_count: int, right_margin_count: int) -> str:
    """
    Infer layout type from detected zones.

    Returns:
        'single_column', 'with_left_marginalia', 'with_right_marginalia',
        'with_both_marginalia', 'double_column', 'centered', etc.
    """
    body_width = body_end - body_start
    body_center = (body_start + body_end) / 2
    page_center = page_width / 2

    # Check if centered
    is_centered = abs(body_center - page_center) < page_width * 0.1

    # Check margin usage
    has_left = left_margin_count > 5  # More than 5 blocks = substantial content
    has_right = right_margin_count > 5

    if has_left and has_right:
        return 'with_both_marginalia'
    elif has_left:
        return 'with_left_marginalia'
    elif has_right:
        return 'with_right_marginalia'
    elif is_centered:
        return 'centered_single_column'
    elif body_width < page_width * 0.5:
        return 'narrow_column'  # Possible double-column
    else:
        return 'standard_single_column'


def classify_text_blocks_by_zone(page, zones: Dict) -> Dict:
    """
    Classify text blocks as body, left-margin, or right-margin.

    Uses spatial position (x-coordinate) to classify.

    Args:
        page: PyMuPDF page object
        zones: Output from analyze_page_layout()

    Returns:
        {
            'body': [{'text': str, 'y': float, 'bbox': tuple}, ...],
            'margin_left': [{'text': str, 'y': float, 'bbox': tuple}, ...],
            'margin_right': [{'text': str, 'y': float, 'bbox': tuple}, ...]
        }
    """
    classified = {
        'body': [],
        'margin_left': [],
        'margin_right': []
    }

    blocks = page.get_text("dict")['blocks']

    for block in blocks:
        if block.get('type') != 0:  # Skip non-text blocks
            continue

        bbox = block['bbox']
        x_left = bbox[0]
        y_top = bbox[1]
        y_bottom = bbox[3]
        y_mid = (y_top + y_bottom) / 2

        # Extract text from block
        text_parts = []
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                text_parts.append(span.get('text', ''))
        text = ''.join(text_parts).strip()

        if not text:
            continue

        # Classify by x-position
        if x_left < zones['left_margin']['x_end']:
            classified['margin_left'].append({
                'text': text,
                'y': y_mid,
                'bbox': bbox
            })
        elif x_left > zones['right_margin']['x_start']:
            classified['margin_right'].append({
                'text': text,
                'y': y_mid,
                'bbox': bbox
            })
        else:
            classified['body'].append({
                'text': text,
                'y': y_mid,
                'bbox': bbox
            })

    logging.debug(f"Classified: {len(classified['body'])} body, "
                  f"{len(classified['margin_left'])} left margin, "
                  f"{len(classified['margin_right'])} right margin")

    return classified


def classify_marginalia_type(text: str) -> Tuple[str, str]:
    """
    Classify marginalia as citation system vs. generic note.

    Uses light pattern matching AFTER spatial extraction.

    Args:
        text: Extracted marginal text (e.g., "A 50", "See p. 30")

    Returns:
        Tuple of (type, system):
            ('citation', 'kant_a_b') or ('note', None)
    """
    text_clean = text.strip()

    # Check against known citation patterns (easily extensible)
    for system_name, system_info in CITATION_PATTERNS.items():
        pattern = system_info['pattern']
        if re.match(pattern, text_clean, re.IGNORECASE):
            logging.debug(f"Identified citation: '{text_clean}' matches {system_name}")
            return ('citation', system_name)

    # Default to generic note
    return ('note', None)


def detect_citation_systems(all_marginalia: List) -> Dict:
    """
    Detect which citation system(s) are present in document.

    Args:
        all_marginalia: All extracted marginalia from document

    Returns:
        {
            'systems_detected': ['kant_a_b', 'stephanus'],
            'system_counts': {'kant_a_b': 247, 'stephanus': 0},
            'primary_system': 'kant_a_b',
            'confidence': 0.95
        }
    """
    system_counts = {name: 0 for name in CITATION_PATTERNS.keys()}

    for margin in all_marginalia:
        margin_type, system_name = classify_marginalia_type(margin['text'])
        if margin_type == 'citation' and system_name:
            system_counts[system_name] += 1

    # Filter to detected systems
    detected = [name for name, count in system_counts.items() if count > 0]

    # Primary system = most frequent
    primary = max(system_counts.items(), key=lambda x: x[1])[0] if detected else None

    # Confidence based on consistency
    total_citations = sum(system_counts.values())
    max_count = system_counts.get(primary, 0) if primary else 0
    confidence = max_count / total_citations if total_citations > 0 else 0

    return {
        'systems_detected': detected,
        'system_counts': system_counts,
        'primary_system': primary,
        'confidence': round(confidence, 2)
    }


def align_marginalia_with_body(classified: Dict, y_tolerance: int = 15) -> List:
    """
    Align marginalia with body text using y-coordinate matching.

    Args:
        classified: Output from classify_text_blocks_by_zone()
        y_tolerance: Vertical tolerance in pixels

    Returns:
        List of body blocks with aligned marginalia:
        [
            {
                'text': 'Body text...',
                'y': 450,
                'marginalia': [
                    {'type': 'citation', 'text': 'A 50', 'side': 'left'},
                    {'type': 'note', 'text': 'nb', 'side': 'right'}
                ]
            },
            ...
        ]
    """
    aligned = []

    for body_block in classified['body']:
        body_y = body_block['y']
        matched_marginalia = []

        # Find left margin items near this y-position
        for margin in classified['margin_left']:
            if abs(margin['y'] - body_y) <= y_tolerance:
                margin_type = classify_marginalia_type(margin['text'])
                matched_marginalia.append({
                    'type': margin_type,  # 'citation' or 'note'
                    'text': margin['text'],
                    'side': 'left',
                    'y': margin['y']
                })

        # Find right margin items near this y-position
        for margin in classified['margin_right']:
            if abs(margin['y'] - body_y) <= y_tolerance:
                margin_type = classify_marginalia_type(margin['text'])
                matched_marginalia.append({
                    'type': margin_type,
                    'text': margin['text'],
                    'side': 'right',
                    'y': margin['y']
                })

        # Sort by y-position then side (left first)
        matched_marginalia.sort(key=lambda m: (m['y'], m['side'] != 'left'))

        aligned.append({
            'text': body_block['text'],
            'y': body_y,
            'bbox': body_block['bbox'],
            'marginalia': matched_marginalia
        })

    return aligned


def inject_marginalia_markers(text: str, marginalia: List) -> str:
    """
    Inject marginalia markers inline at start of text.

    Args:
        text: Body text
        marginalia: List of marginalia dicts with 'type' and 'text'

    Returns:
        Text with inline marginalia markers

    Example:
        Input: "The transcendental unity...", [{'type': 'citation', 'text': 'A 50'}]
        Output: "{{cite: "A 50"}} The transcendental unity..."
    """
    markers = []

    for margin in marginalia:
        if margin['type'] == 'citation':
            markers.append(f'{{{{cite: "{margin["text"]}"}}}}')
        else:
            markers.append(f'{{{{note: "{margin["text"]}"}}}}')

    if markers:
        marker_str = ' '.join(markers)
        return f"{marker_str} {text}"
    else:
        return text


def extract_canonical_mappings(aligned_blocks: List, page_num: int, line_offset: int = 0) -> Dict:
    """
    Build canonical citation → page/line mappings.

    Only processes citation-type marginalia (ignores notes).

    Args:
        aligned_blocks: Output from align_marginalia_with_body()
        page_num: Current PDF page number
        line_offset: Line number offset for this page

    Returns:
        {
            "A 50": {"pdf_page": 102, "line_start": 1450},
            "B 75": {"pdf_page": 102, "line_start": 1450},
            ...
        }
    """
    mappings = {}
    current_line = line_offset

    for block in aligned_blocks:
        # Calculate approximate line numbers (crude estimate)
        text_lines = block['text'].count('\n') + 1
        line_end = current_line + text_lines

        # Extract citations only
        for margin in block['marginalia']:
            if margin['type'] == 'citation':
                citation_ref = margin['text'].strip()

                mappings[citation_ref] = {
                    'pdf_page': page_num,
                    'line_start': current_line,
                    'line_end': line_end,
                    'text_sample': block['text'][:100]  # First 100 chars
                }

        current_line = line_end

    return mappings
