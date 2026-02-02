"""
Margin zone detection and block classification for PDF pages.

Detects margin content by statistically inferring body column boundaries
from text block positions, classifying blocks by zone (left margin, right
margin, body, header, footer), and applying typed content classification.
"""

import logging
import os
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from lib.rag.detection.margin_patterns import classify_margin_content

logger = logging.getLogger(__name__)

# Bin size for edge clustering (points)
_BIN_SIZE = 5

# Minimum block width to avoid scan artifacts (points)
_MIN_BLOCK_WIDTH = 10

# Minimum text length to avoid single-char noise
_MIN_TEXT_LEN = 2

# Minimum blocks needed for statistical inference
_MIN_BLOCKS_FOR_STATS = 3

# Two-column detection: second peak must be at least this fraction of first
_TWO_COL_RATIO = 0.3

# Two-column detection: minimum gap between column starts (points)
_TWO_COL_GAP = 100


def _extract_block_text(block: Dict[str, Any]) -> str:
    """Extract all text from a block by joining span texts."""
    parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "")
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _infer_body_column(
    text_blocks: List[Dict[str, Any]],
    page_rect: Any,
    fallback_margin_pct: float = 0.12,
) -> Dict[str, Any]:
    """Infer body column boundaries from text block positions.

    Uses statistical clustering of left-edge (x0) positions to find
    the dominant body column. Falls back to percentage-based margins
    when too few blocks are available.

    Returns:
        Dict with 'body_left', 'body_right', 'is_two_column'.
    """
    page_width = page_rect.width

    if len(text_blocks) < _MIN_BLOCKS_FOR_STATS:
        margin = page_width * fallback_margin_pct
        return {
            "body_left": margin,
            "body_right": page_width - margin,
            "is_two_column": False,
        }

    # Bin left edges
    left_bins: Counter = Counter()
    right_bins: Counter = Counter()
    for block in text_blocks:
        bbox = block["bbox"]
        x0, x1 = bbox[0], bbox[2]
        left_bins[round(x0 / _BIN_SIZE) * _BIN_SIZE] += 1
        right_bins[round(x1 / _BIN_SIZE) * _BIN_SIZE] += 1

    # Most common left edge = body left
    top_lefts = left_bins.most_common(2)
    body_left = top_lefts[0][0]

    # Check for two-column layout
    is_two_column = False
    if len(top_lefts) > 1:
        first_count = top_lefts[0][1]
        second_count = top_lefts[1][1]
        gap = abs(top_lefts[1][0] - top_lefts[0][0])
        if second_count >= first_count * _TWO_COL_RATIO and gap >= _TWO_COL_GAP:
            is_two_column = True
            # Expand body to cover both columns
            body_left = min(top_lefts[0][0], top_lefts[1][0])

    # Most common right edge = body right
    top_right = right_bins.most_common(1)[0][0]
    if is_two_column:
        # Use the rightmost right edge
        top_rights = right_bins.most_common(2)
        top_right = max(r[0] for r in top_rights)

    return {
        "body_left": body_left,
        "body_right": top_right,
        "is_two_column": is_two_column,
    }


def _classify_block_zone(
    block_bbox: Tuple[float, float, float, float],
    body_left: float,
    body_right: float,
    page_rect: Any,
    header_zone_pct: float,
    footer_zone_pct: float,
) -> str:
    """Classify a block's zone based on its position.

    Returns one of: 'header', 'footer', 'margin-left', 'margin-right', 'body'.
    """
    x0, y0, x1, y1 = block_bbox
    page_height = page_rect.height

    header_limit = page_height * header_zone_pct
    footer_limit = page_height * (1 - footer_zone_pct)

    # Header/footer take priority
    if y1 <= header_limit:
        return "header"
    if y0 >= footer_limit:
        return "footer"

    # Margin zones: block must be predominantly outside body
    mid_x = (x0 + x1) / 2
    if mid_x < body_left:
        return "margin-left"
    if mid_x > body_right:
        return "margin-right"

    return "body"


def detect_margin_content(
    page: Any,
    excluded_bboxes: Optional[List[Tuple[float, float, float, float]]] = None,
    header_zone_pct: Optional[float] = None,
    footer_zone_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """Detect and classify margin content on a PDF page.

    Args:
        page: PyMuPDF page object.
        excluded_bboxes: Bboxes to skip (e.g. already-detected footnotes).
        header_zone_pct: Header zone as fraction of page height. Env: RAG_HEADER_ZONE_PCT.
        footer_zone_pct: Footer zone as fraction of page height. Env: RAG_FOOTER_ZONE_PCT.

    Returns:
        Dict with 'margin_blocks' (list), 'body_column' (tuple), 'is_two_column' (bool).
    """
    if header_zone_pct is None:
        header_zone_pct = float(os.getenv("RAG_HEADER_ZONE_PCT", "0.08"))
    if footer_zone_pct is None:
        footer_zone_pct = float(os.getenv("RAG_FOOTER_ZONE_PCT", "0.08"))
    fallback_margin_pct = float(os.getenv("RAG_MARGIN_FALLBACK_PCT", "0.12"))

    # Use mediabox if cropbox differs (scanned documents)
    page_rect = page.rect
    if hasattr(page, "cropbox") and hasattr(page, "mediabox"):
        if page.cropbox != page.mediabox:
            page_rect = page.mediabox

    excluded = set()
    if excluded_bboxes:
        excluded = {tuple(round(v, 1) for v in bb) for bb in excluded_bboxes}

    # Extract text blocks
    data = page.get_text("dict")
    blocks = [b for b in data.get("blocks", []) if "lines" in b]

    # Infer body column
    col_info = _infer_body_column(blocks, page_rect, fallback_margin_pct)
    body_left = col_info["body_left"]
    body_right = col_info["body_right"]
    is_two_column = col_info["is_two_column"]

    margin_blocks: List[Dict[str, Any]] = []

    for block in blocks:
        bbox = tuple(block["bbox"])
        x0, y0, x1, y1 = bbox

        # Skip excluded bboxes
        rounded_bbox = tuple(round(v, 1) for v in bbox)
        if rounded_bbox in excluded:
            continue

        # Filter scan artifacts
        block_width = x1 - x0
        if block_width < _MIN_BLOCK_WIDTH:
            continue

        text = _extract_block_text(block)
        if len(text) < _MIN_TEXT_LEN:
            continue

        zone = _classify_block_zone(
            bbox, body_left, body_right, page_rect, header_zone_pct, footer_zone_pct
        )

        if zone in ("margin-left", "margin-right"):
            content_type, content = classify_margin_content(text)
            margin_blocks.append(
                {
                    "bbox": bbox,
                    "text": text,
                    "zone": zone,
                    "type": content_type,
                    "content": content,
                }
            )

    return {
        "margin_blocks": margin_blocks,
        "body_column": (body_left, body_right),
        "is_two_column": is_two_column,
    }
