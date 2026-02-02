"""
Page number detection and inference for PDF documents.

Contains written page number extraction, roman numeral conversion,
and page number inference algorithms for mapping PDF pages to written pages.
"""

import logging
import re
from typing import Any, Dict, List

try:
    import fitz  # noqa: F811
except ImportError:
    fitz = None  # type: ignore[assignment]

from lib.rag.detection.registry import register_detector
from lib.rag.pipeline.models import (
    BlockClassification,
    ContentType,
    DetectionResult,
    DetectorScope,
)

logger = logging.getLogger(__name__)

__all__ = [
    "_extract_written_page_number",
    "_roman_to_int",
    "_int_to_roman",
    "_is_roman_numeral",
    "_detect_written_page_on_page",
    "infer_written_page_numbers",
]


@register_detector("page_numbers", priority=5, scope=DetectorScope.DOCUMENT)
def detect_page_numbers_pipeline(doc: Any, context: Dict[str, Any]) -> DetectionResult:
    """Pipeline adapter for page number detection.

    Infers written page numbers and stores mapping in context.
    """
    page_map = infer_written_page_numbers(doc)
    classifications: List[BlockClassification] = []
    for pdf_page, written_num in page_map.items():
        classifications.append(
            BlockClassification(
                bbox=(0, 0, 0, 0),
                content_type=ContentType.PAGE_NUMBER,
                text=str(written_num),
                confidence=0.9,
                detector_name="page_numbers",
                page_num=pdf_page,
                metadata={"written_page": written_num, "bbox_available": False},
            )
        )
    context["page_number_map"] = page_map
    return DetectionResult(
        detector_name="page_numbers",
        classifications=classifications,
        page_num=0,
        metadata={"page_map": page_map},
    )


def _extract_written_page_number(page: "fitz.Page") -> str:
    """
    Try to extract the written page number from a page (e.g., "xxiii", "15", "A-3").

    Checks:
    - First line of page (header position)
    - Last line of page (footer position)

    Returns:
        Written page number as string, or None if not found
    """
    try:
        text = page.get_text("text")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return None

        # Check first line (common header position)
        first_line = lines[0]
        if first_line.isdigit() or re.match(r"^[ivxlc]+$", first_line, re.IGNORECASE):
            return first_line

        # Check last line (common footer position)
        last_line = lines[-1]
        if last_line.isdigit() or re.match(r"^[ivxlc]+$", last_line, re.IGNORECASE):
            return last_line

        # Check for patterns like "Page 15" or "p. 15"
        for line in [first_line, last_line]:
            match = re.search(r"\b(?:page|p\.?)\s*(\d+)\b", line, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    except Exception as e:
        logging.debug(f"Error extracting written page number: {e}")
        return None


def _roman_to_int(roman: str) -> int:
    """Convert roman numeral to integer (e.g., 'xxiii' -> 23)."""
    roman_map = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
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
    symbols = ["m", "cm", "d", "cd", "c", "xc", "l", "xl", "x", "ix", "v", "iv", "i"]

    result = ""
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
    return bool(re.match(r"^[ivxlcdm]+$", text.lower()))


def _detect_written_page_on_page(page: "fitz.Page") -> tuple:
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
        text = page.get_text("text")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return (None, None, None)

        # Check first and last lines (common header/footer positions)
        candidates = [(lines[0], "first"), (lines[-1], "last")]

        for candidate, position in candidates:
            # Check for pure roman numeral
            if _is_roman_numeral(candidate):
                return (candidate.lower(), position, candidate)

            # Check for pure arabic number
            if candidate.isdigit():
                return (candidate, position, candidate)

            # Check for "Page N" or "p. N" patterns
            match = re.search(r"\b(?:page|p\.?)\s*(\d+)\b", candidate, re.IGNORECASE)
            if match:
                return (match.group(1), position, candidate)

        return (None, None, None)

    except Exception as e:
        logging.debug(f"Error detecting written page number: {e}")
        return (None, None, None)


def infer_written_page_numbers(doc: "fitz.Document", scan_pages: int = 20) -> dict:
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

    logging.info(
        f"Scanning first {scan_limit} pages for written page number anchors..."
    )

    for pdf_page_num in range(1, scan_limit + 1):
        page = doc[pdf_page_num - 1]  # 0-indexed
        written_num, position, matched_text = _detect_written_page_on_page(page)

        if written_num:
            # Check for roman numeral
            if _is_roman_numeral(written_num) and roman_start_pdf_page is None:
                roman_start_pdf_page = pdf_page_num
                roman_start_value = _roman_to_int(written_num)
                logging.info(
                    f"Found roman numeral anchor: PDF page {pdf_page_num} = {written_num} ({roman_start_value})"
                )

            # Check for arabic number (only after roman numerals or if no roman found)
            elif written_num.isdigit() and arabic_start_pdf_page is None:
                arabic_start_pdf_page = pdf_page_num
                arabic_start_value = int(written_num)
                logging.info(
                    f"Found arabic number anchor: PDF page {pdf_page_num} = {written_num}"
                )

    # Generate full mapping by inference
    page_map = {}

    # Infer roman numeral pages (preface)
    if roman_start_pdf_page:
        end_roman = arabic_start_pdf_page if arabic_start_pdf_page else total_pages + 1
        for pdf_page in range(roman_start_pdf_page, end_roman):
            offset = pdf_page - roman_start_pdf_page
            roman_value = roman_start_value + offset
            page_map[pdf_page] = _int_to_roman(roman_value)

        logging.info(
            f"Inferred roman numerals: PDF pages {roman_start_pdf_page}-{end_roman - 1}"
        )

    # Infer arabic number pages (main content)
    if arabic_start_pdf_page:
        for pdf_page in range(arabic_start_pdf_page, total_pages + 1):
            offset = pdf_page - arabic_start_pdf_page
            page_map[pdf_page] = str(arabic_start_value + offset)

        logging.info(
            f"Inferred arabic numbers: PDF pages {arabic_start_pdf_page}-{total_pages}"
        )

    logging.info(
        f"Inferred written page numbers for {len(page_map)}/{total_pages} PDF pages"
    )

    return page_map
