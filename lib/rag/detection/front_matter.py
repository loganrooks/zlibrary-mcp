"""
Front matter extraction from PDF documents.

Contains publisher and year extraction from title/copyright pages.
"""

import logging
from typing import Any, Dict, List

from lib.rag.detection.registry import register_detector
from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DetectionResult,
    DetectorScope,
)

logger = logging.getLogger(__name__)

# Re-export from header module (where it lives alongside _generate_document_header)
from lib.rag.utils.header import _extract_publisher_from_front_matter

__all__ = [
    "_extract_publisher_from_front_matter",
]


@register_detector("front_matter", priority=25, scope=DetectorScope.DOCUMENT)
def detect_front_matter_pipeline(doc: Any, context: Dict[str, Any]) -> DetectionResult:
    """Pipeline adapter for front matter detection.

    Extracts publisher/year info and marks front matter pages for stripping.
    """
    publisher, year = _extract_publisher_from_front_matter(doc)
    classifications: List[BlockClassification] = []
    # Mark first few pages as front matter candidates
    max_front_pages = min(5, len(doc))
    for page_idx in range(max_front_pages):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        if text:
            classifications.append(
                BlockClassification(
                    bbox=(0, 0, 0, 0),
                    content_type=ContentType.FRONT_MATTER,
                    text=text[:200],  # Truncate for metadata
                    confidence=0.6,
                    detector_name="front_matter",
                    page_num=page_idx + 1,
                    metadata={"bbox_available": False},
                )
            )
    front_matter_info = {"publisher": publisher, "year": year}
    context["front_matter"] = front_matter_info
    return DetectionResult(
        detector_name="front_matter",
        classifications=classifications,
        page_num=0,
        metadata=front_matter_info,
    )
