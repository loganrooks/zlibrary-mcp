"""Compositor: resolves conflicts between detector claims and classifies blocks.

Core principle: recall-biased body text preservation. When in doubt, a block
is BODY text rather than a non-body classification. This prevents body text
loss which is the worst failure mode for RAG output quality.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DetectionResult,
)

# Lower number = higher priority (wins ties)
TYPE_PRIORITY: Dict[ContentType, int] = {
    ContentType.FOOTNOTE: 1,
    ContentType.ENDNOTE: 2,
    ContentType.MARGIN: 3,
    ContentType.PAGE_NUMBER: 4,
    ContentType.HEADER: 5,
    ContentType.FOOTER: 6,
    ContentType.TOC: 7,
    ContentType.FRONT_MATTER: 8,
    ContentType.CITATION: 9,
    ContentType.HEADING: 10,
    ContentType.BODY: 99,
}

OVERLAP_THRESHOLD = 0.5


def compute_bbox_overlap(
    bbox_a: Tuple[float, float, float, float],
    bbox_b: Tuple[float, float, float, float],
) -> float:
    """Compute overlap ratio between two bboxes.

    Returns intersection area / min(area_a, area_b), so a small box
    fully inside a large box returns 1.0.
    """
    x0 = max(bbox_a[0], bbox_b[0])
    y0 = max(bbox_a[1], bbox_b[1])
    x1 = min(bbox_a[2], bbox_b[2])
    y1 = min(bbox_a[3], bbox_b[3])

    if x1 <= x0 or y1 <= y0:
        return 0.0

    intersection = (x1 - x0) * (y1 - y0)
    area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
    area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
    min_area = min(area_a, area_b)

    if min_area <= 0:
        return 0.0

    return intersection / min_area


def classify_page_blocks(
    page_blocks: List[Tuple[float, float, float, float]],
    detection_results: List[DetectionResult],
    confidence_floor: float = 0.6,
) -> List[BlockClassification]:
    """Classify blocks on a single page using detection results.

    For each page block bbox:
    - Find all detector classifications that overlap >50%
    - If none: BODY with confidence 1.0
    - If best confidence < confidence_floor: BODY (recall bias)
    - Otherwise: highest confidence wins; type priority breaks ties
    """
    # Collect all classifications from all results
    all_claims: List[BlockClassification] = []
    for result in detection_results:
        all_claims.extend(result.classifications)

    classified: List[BlockClassification] = []

    for block_bbox in page_blocks:
        # Find overlapping claims
        overlapping: List[BlockClassification] = []
        for claim in all_claims:
            if compute_bbox_overlap(block_bbox, claim.bbox) > OVERLAP_THRESHOLD:
                overlapping.append(claim)

        if not overlapping:
            # No claims → default to BODY
            classified.append(
                BlockClassification(
                    bbox=block_bbox,
                    content_type=ContentType.BODY,
                    text="",
                    confidence=1.0,
                    detector_name="compositor:default",
                )
            )
            continue

        # Sort: highest confidence first, then by type priority (lower = wins)
        overlapping.sort(
            key=lambda c: (-c.confidence, TYPE_PRIORITY.get(c.content_type, 99))
        )
        best = overlapping[0]

        if best.confidence < confidence_floor:
            # Below floor → recall bias, keep as BODY
            classified.append(
                BlockClassification(
                    bbox=block_bbox,
                    content_type=ContentType.BODY,
                    text=best.text,
                    confidence=1.0,
                    detector_name="compositor:recall_bias",
                    metadata={"original_claim": best.content_type.value},
                )
            )
        else:
            classified.append(
                BlockClassification(
                    bbox=block_bbox,
                    content_type=best.content_type,
                    text=best.text,
                    confidence=best.confidence,
                    detector_name=best.detector_name,
                )
            )

    return classified


def resolve_conflicts(
    all_results: List[DetectionResult],
    page_blocks_by_page: Dict[int, List[Tuple[float, float, float, float]]],
) -> Dict[int, List[BlockClassification]]:
    """Resolve conflicts across all pages.

    Args:
        all_results: Detection results from all detectors.
        page_blocks_by_page: Dict mapping page_num to list of block bboxes.

    Returns:
        Dict mapping page_num to list of final BlockClassification.
    """
    output: Dict[int, List[BlockClassification]] = {}

    for page_num, blocks in page_blocks_by_page.items():
        # Filter results relevant to this page
        page_results = [r for r in all_results if r.page_num == page_num]
        output[page_num] = classify_page_blocks(blocks, page_results)

    return output
