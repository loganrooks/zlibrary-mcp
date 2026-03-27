"""
Tests for lib/rag/detection/front_matter.py — front matter detection pipeline.

Tests the detect_front_matter_pipeline function which wraps
_extract_publisher_from_front_matter and classifies front matter pages.
"""

import pytest
from unittest.mock import MagicMock, patch

from lib.rag.pipeline.models import ContentType, DetectionResult

pytestmark = pytest.mark.unit


def _make_mock_page(text="Some front matter text"):
    """Create a mock fitz page with get_text() support."""
    page = MagicMock()
    page.get_text.return_value = text
    return page


def _make_mock_doc(page_texts):
    """Create a mock fitz doc with indexable pages."""
    pages = [_make_mock_page(t) for t in page_texts]
    doc = MagicMock()
    doc.__len__ = MagicMock(return_value=len(pages))
    doc.__getitem__ = MagicMock(side_effect=lambda idx: pages[idx])
    return doc


class TestDetectFrontMatterPipeline:
    """Tests for detect_front_matter_pipeline detector function."""

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_basic_front_matter_detection(self, mock_extract):
        """Should classify non-empty front matter pages."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = ("Oxford University Press", "2020")
        doc = _make_mock_doc(["Title Page", "Copyright 2020", "Dedication"])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        assert isinstance(result, DetectionResult)
        assert result.detector_name == "front_matter"
        assert len(result.classifications) == 3
        for cls in result.classifications:
            assert cls.content_type == ContentType.FRONT_MATTER
            assert cls.confidence == 0.6
            assert cls.detector_name == "front_matter"

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_empty_pages_skipped(self, mock_extract):
        """Pages with no text should not generate classifications."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = (None, None)
        doc = _make_mock_doc(["Title Page", "", "   ", "Content"])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        # Only page 0 has text after strip(); pages 1 and 2 are empty/whitespace
        assert len(result.classifications) == 2  # pages 0 and 3

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_max_five_pages_scanned(self, mock_extract):
        """Should scan at most 5 pages even if document is longer."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = (None, None)
        # 10-page document with text on all pages
        doc = _make_mock_doc([f"Page {i}" for i in range(10)])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        # Only first 5 pages scanned
        assert len(result.classifications) == 5
        page_nums = [c.page_num for c in result.classifications]
        assert page_nums == [1, 2, 3, 4, 5]

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_short_document(self, mock_extract):
        """Documents with fewer than 5 pages scan all pages."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = (None, None)
        doc = _make_mock_doc(["Page 1", "Page 2"])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        assert len(result.classifications) == 2

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_context_updated_with_front_matter_info(self, mock_extract):
        """Should store publisher/year in the shared context dict."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = ("Cambridge University Press", "2019")
        doc = _make_mock_doc(["Title"])
        context = {}

        detect_front_matter_pipeline(doc, context)

        assert context["front_matter"]["publisher"] == "Cambridge University Press"
        assert context["front_matter"]["year"] == "2019"

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_metadata_in_result(self, mock_extract):
        """Result metadata contains publisher and year."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = ("MIT Press", "2021")
        doc = _make_mock_doc(["Title"])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        assert result.metadata["publisher"] == "MIT Press"
        assert result.metadata["year"] == "2021"

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_text_truncated_to_200_chars(self, mock_extract):
        """Classification text is truncated to 200 characters."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = (None, None)
        long_text = "A" * 500
        doc = _make_mock_doc([long_text])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        assert len(result.classifications[0].text) == 200

    @patch("lib.rag.detection.front_matter._extract_publisher_from_front_matter")
    def test_page_num_is_one_indexed(self, mock_extract):
        """Page numbers in classifications should be 1-indexed."""
        from lib.rag.detection.front_matter import detect_front_matter_pipeline

        mock_extract.return_value = (None, None)
        doc = _make_mock_doc(["Page 1", "Page 2", "Page 3"])
        context = {}

        result = detect_front_matter_pipeline(doc, context)

        page_nums = [c.page_num for c in result.classifications]
        assert page_nums == [1, 2, 3]
