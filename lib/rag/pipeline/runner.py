"""Pipeline runner: orchestrates detector execution and output building.

Two-phase pipeline:
1. Document-level pre-pass (TOC, page numbers, front matter, headings)
2. Page-level loop (footnotes, margins) with compositor conflict resolution
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from lib.rag.pipeline.compositor import classify_page_blocks
from lib.rag.pipeline.models import (
    BlockClassification,
    DetectionResult,
    DetectorScope,
    DocumentOutput,
)
from lib.rag.detection.registry import get_registered_detectors

# Trigger detector registration by importing all detection modules
import lib.rag.detection.footnotes  # noqa: F401
import lib.rag.detection.margins  # noqa: F401
import lib.rag.detection.headings  # noqa: F401
import lib.rag.detection.page_numbers  # noqa: F401
import lib.rag.detection.toc  # noqa: F401
import lib.rag.detection.front_matter  # noqa: F401

logger = logging.getLogger(__name__)


def run_document_detectors(doc: Any, context: dict) -> List[DetectionResult]:
    """Run all document-level detectors.

    Args:
        doc: A fitz.Document instance.
        context: Shared context dict that detectors populate.

    Returns:
        List of DetectionResult from document-level detectors.
    """
    detectors = get_registered_detectors(scope=DetectorScope.DOCUMENT)
    results: List[DetectionResult] = []

    for det in detectors:
        try:
            result = det["func"](doc, context)
            if result is not None:
                results.append(result)
        except Exception:
            logger.warning(
                "Document detector '%s' failed, skipping", det["name"], exc_info=True
            )

    return results


def run_page_detectors(
    page: Any, page_num: int, context: dict
) -> List[DetectionResult]:
    """Run all page-level detectors on a single page.

    Args:
        page: A fitz.Page instance.
        page_num: 1-indexed page number.
        context: Shared context dict.

    Returns:
        List of DetectionResult from page-level detectors.
    """
    detectors = get_registered_detectors(scope=DetectorScope.PAGE)
    results: List[DetectionResult] = []

    for det in detectors:
        try:
            result = det["func"](page, page_num, context)
            if result is not None:
                results.append(result)
        except Exception:
            logger.warning(
                "Page detector '%s' failed on page %d, skipping",
                det["name"],
                page_num,
                exc_info=True,
            )

    return results


def _extract_page_blocks(
    page: Any,
) -> Tuple[
    List[Tuple[float, float, float, float]],
    Dict[Tuple[float, float, float, float], str],
]:
    """Extract text block bboxes and their text from a page.

    Returns:
        Tuple of (list of bboxes, dict mapping bbox to text).
    """
    blocks = page.get_text("dict")["blocks"]
    bboxes: List[Tuple[float, float, float, float]] = []
    text_map: Dict[Tuple[float, float, float, float], str] = {}

    for block in blocks:
        if block.get("type", 0) != 0:  # Skip image blocks
            continue
        bbox = tuple(block["bbox"])
        # Extract text from lines/spans
        lines_text = []
        for line in block.get("lines", []):
            spans_text = "".join(span.get("text", "") for span in line.get("spans", []))
            lines_text.append(spans_text)
        text = "\n".join(lines_text)
        if text.strip():
            bboxes.append(bbox)
            text_map[bbox] = text

    return bboxes, text_map


def run_document_pipeline(
    doc: Any,
    output_format: str = "markdown",
    include_metadata: bool = False,
) -> DocumentOutput:
    """Main entry point: orchestrate the two-phase detection pipeline.

    Args:
        doc: A fitz.Document instance.
        output_format: Output format (currently only 'markdown').
        include_metadata: If True, include per-block classification details.

    Returns:
        DocumentOutput with separated content streams.
    """
    from lib.rag.pipeline.writer import build_document_output

    context: dict = {}

    # Phase 1: Document-level pre-pass
    doc_results = run_document_detectors(doc, context)

    # Phase 2: Page-level loop
    classified_pages: Dict[int, List[BlockClassification]] = {}

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1  # 1-indexed

        # Extract raw page blocks
        bboxes, text_map = _extract_page_blocks(page)

        # Run page-level detectors
        page_results = run_page_detectors(page, page_num, context)

        # Combine with document-level results relevant to this page
        all_page_results = page_results + [
            r for r in doc_results if r.page_num == page_num
        ]

        # Resolve conflicts via compositor
        classified = classify_page_blocks(bboxes, all_page_results)

        # Fill in text for compositor-defaulted BODY blocks (they have empty text)
        for block in classified:
            if not block.text and block.bbox in text_map:
                block.text = text_map[block.bbox]
            block.page_num = page_num

        classified_pages[page_num] = classified

    # Phase 3: Build output
    return build_document_output(
        classified_pages, context, include_metadata=include_metadata
    )
