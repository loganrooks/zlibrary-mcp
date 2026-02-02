"""
Footnote detection, extraction, and formatting for PDF documents.

This module re-exports all footnote detection symbols from submodules:
- footnote_markers: Marker matching and definition finding helpers
- footnote_core: Main detection loop and font analysis

Also contains small helper functions for dict conversion and markdown formatting.
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

# Import continuation tracking for _footnote_with_continuation_to_dict
from lib.footnote_continuation import FootnoteWithContinuation

# Re-export from submodules
from lib.rag.detection.footnote_markers import (
    _starts_with_marker,
    _extract_text_from_block,
    _merge_bboxes,
    _markers_are_equivalent,
    _find_definition_for_marker,
    _find_markerless_content,
)

from lib.rag.detection.footnote_core import (
    _calculate_page_normal_font_size,
    _is_superscript,
    _detect_footnotes_in_page,
)

# Re-export _is_ocr_corrupted for backward compatibility
from lib.rag.ocr.corruption import _is_ocr_corrupted

__all__ = [
    "_footnote_with_continuation_to_dict",
    "_starts_with_marker",
    "_extract_text_from_block",
    "_merge_bboxes",
    "_markers_are_equivalent",
    "_find_definition_for_marker",
    "_find_markerless_content",
    "_calculate_page_normal_font_size",
    "_is_superscript",
    "_is_ocr_corrupted",
    "_detect_footnotes_in_page",
    "_format_footnotes_markdown",
]


@register_detector("footnotes", priority=10, scope=DetectorScope.PAGE)
def detect_footnotes_pipeline(
    page: Any, page_num: int, context: Dict[str, Any]
) -> DetectionResult:
    """Pipeline adapter for footnote detection.

    Wraps _detect_footnotes_in_page and converts results to DetectionResult.
    Stores detected footnote bboxes in context for downstream dedup (margins).
    """
    result = _detect_footnotes_in_page(page, page_num - 1)  # existing uses 0-indexed
    classifications: List[BlockClassification] = []
    for defn in result.get("definitions", []):
        bbox = defn.get("bbox")
        if not bbox:
            continue
        classifications.append(
            BlockClassification(
                bbox=tuple(bbox),
                content_type=ContentType.FOOTNOTE,
                text=defn.get("text", defn.get("content", "")),
                confidence=defn.get("classification_confidence", 0.8),
                detector_name="footnotes",
                page_num=page_num,
                metadata={
                    "marker": defn.get("marker"),
                    "note_type": defn.get("note_type"),
                },
            )
        )
    # Store bboxes in context for downstream detectors (margin dedup)
    context["footnote_bboxes"] = [
        tuple(d["bbox"]) for d in result.get("definitions", []) if d.get("bbox")
    ]
    return DetectionResult(
        detector_name="footnotes",
        classifications=classifications,
        page_num=page_num,
        metadata=result,
    )


def _footnote_with_continuation_to_dict(
    footnote: FootnoteWithContinuation,
) -> Dict[str, Any]:
    """
    Convert FootnoteWithContinuation object to dict format for compatibility.

    Args:
        footnote: FootnoteWithContinuation object from continuation parser

    Returns:
        Dictionary with all footnote metadata including continuation info
    """
    from lib.rag_data_models import NoteSource

    # Convert NoteSource enum to string if needed
    note_source_str = (
        footnote.note_source.name
        if isinstance(footnote.note_source, NoteSource)
        else str(footnote.note_source)
    )

    return {
        "marker": footnote.marker,
        "actual_marker": footnote.marker,  # For compatibility with corruption recovery
        "content": footnote.content,
        "pages": footnote.pages,
        "bboxes": footnote.bboxes,
        "is_complete": footnote.is_complete,
        "continuation_confidence": footnote.continuation_confidence,
        "note_source": note_source_str,
        "classification_confidence": footnote.classification_confidence,
        "classification_method": footnote.classification_method,
        "font_name": footnote.font_name,
        "font_size": footnote.font_size,
        # Add incomplete detection fields for consistency
        "incomplete_confidence": 1.0 - footnote.continuation_confidence
        if not footnote.is_complete
        else 1.0,
        "incomplete_reason": "multi_page" if len(footnote.pages) > 1 else "complete",
    }


def _format_footnotes_markdown(footnotes: Dict[str, Any]) -> str:
    """
    Format detected footnotes as markdown footnote syntax.

    Uses corrected symbols from corruption recovery if available.

    Args:
        footnotes: Dictionary from _detect_footnotes_in_page() with corruption recovery

    Returns:
        Markdown footnote definitions: [^*]: Content or [^dagger]: Content
    """
    lines = []

    for definition in footnotes.get("definitions", []):
        # Use actual_marker if corruption recovery was applied
        marker = definition.get("actual_marker", definition.get("marker", "?"))
        content = definition.get("content", "")

        # Add confidence information as HTML comment if low confidence
        confidence = definition.get("confidence", 1.0)
        if confidence < 0.75:
            confidence_note = f"<!-- Confidence: {confidence:.2f}, Method: {definition.get('inference_method', 'unknown')} -->"
            lines.append(f"[^{marker}]: {content}\n{confidence_note}")
        else:
            # Markdown footnote syntax
            lines.append(f"[^{marker}]: {content}")

    return "\n\n".join(lines)
