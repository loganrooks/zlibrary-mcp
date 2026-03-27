"""
Tests for lib/rag/detection/footnotes.py — footnote detection wrapper functions.

Covers:
- detect_footnotes_pipeline: pipeline adapter wrapping _detect_footnotes_in_page
- _footnote_with_continuation_to_dict: conversion of FootnoteWithContinuation objects
- _format_footnotes_markdown: markdown formatting of detected footnotes
"""

import pytest
from unittest.mock import MagicMock, patch

from lib.rag.pipeline.models import ContentType, DetectionResult

pytestmark = pytest.mark.unit


class TestDetectFootnotesPipeline:
    """Tests for the detect_footnotes_pipeline detector function."""

    @patch("lib.rag.detection.footnotes._detect_footnotes_in_page")
    def test_basic_footnote_detection(self, mock_detect):
        """Should convert footnote definitions to BlockClassifications."""
        from lib.rag.detection.footnotes import detect_footnotes_pipeline

        mock_detect.return_value = {
            "definitions": [
                {
                    "marker": "1",
                    "text": "See Hegel, p. 42.",
                    "bbox": (50, 700, 550, 720),
                    "classification_confidence": 0.9,
                    "note_type": "author",
                },
            ]
        }

        page = MagicMock()
        context = {}
        result = detect_footnotes_pipeline(page, page_num=5, context=context)

        assert isinstance(result, DetectionResult)
        assert result.detector_name == "footnotes"
        assert len(result.classifications) == 1
        cls = result.classifications[0]
        assert cls.content_type == ContentType.FOOTNOTE
        assert cls.text == "See Hegel, p. 42."
        assert cls.confidence == 0.9
        assert cls.page_num == 5
        assert cls.metadata["marker"] == "1"

    @patch("lib.rag.detection.footnotes._detect_footnotes_in_page")
    def test_definitions_without_bbox_skipped(self, mock_detect):
        """Definitions missing bbox are filtered out."""
        from lib.rag.detection.footnotes import detect_footnotes_pipeline

        mock_detect.return_value = {
            "definitions": [
                {"marker": "1", "text": "Has bbox", "bbox": (0, 0, 100, 20)},
                {"marker": "2", "text": "No bbox", "bbox": None},
                {"marker": "3", "text": "Missing bbox key"},
            ]
        }

        result = detect_footnotes_pipeline(MagicMock(), page_num=1, context={})
        assert len(result.classifications) == 1
        assert result.classifications[0].metadata["marker"] == "1"

    @patch("lib.rag.detection.footnotes._detect_footnotes_in_page")
    def test_context_gets_footnote_bboxes(self, mock_detect):
        """Should store footnote bboxes in context for downstream dedup."""
        from lib.rag.detection.footnotes import detect_footnotes_pipeline

        mock_detect.return_value = {
            "definitions": [
                {"marker": "1", "bbox": (50, 700, 550, 720), "text": "note1"},
                {"marker": "2", "bbox": (50, 730, 550, 750), "text": "note2"},
            ]
        }

        context = {}
        detect_footnotes_pipeline(MagicMock(), page_num=3, context=context)

        assert len(context["footnote_bboxes"]) == 2
        assert context["footnote_bboxes"][0] == (50, 700, 550, 720)

    @patch("lib.rag.detection.footnotes._detect_footnotes_in_page")
    def test_empty_definitions(self, mock_detect):
        """Should handle empty definitions list gracefully."""
        from lib.rag.detection.footnotes import detect_footnotes_pipeline

        mock_detect.return_value = {"definitions": []}

        result = detect_footnotes_pipeline(MagicMock(), page_num=1, context={})
        assert len(result.classifications) == 0

    @patch("lib.rag.detection.footnotes._detect_footnotes_in_page")
    def test_page_num_passed_as_zero_indexed(self, mock_detect):
        """Should pass page_num - 1 to _detect_footnotes_in_page (0-indexed)."""
        from lib.rag.detection.footnotes import detect_footnotes_pipeline

        mock_detect.return_value = {"definitions": []}

        detect_footnotes_pipeline(MagicMock(), page_num=5, context={})

        # _detect_footnotes_in_page uses 0-indexed, so page_num=5 becomes 4
        call_args = mock_detect.call_args
        assert call_args[0][1] == 4

    @patch("lib.rag.detection.footnotes._detect_footnotes_in_page")
    def test_content_field_fallback(self, mock_detect):
        """Should use 'content' key if 'text' key is missing."""
        from lib.rag.detection.footnotes import detect_footnotes_pipeline

        mock_detect.return_value = {
            "definitions": [
                {"marker": "1", "content": "Fallback content", "bbox": (0, 0, 100, 20)},
            ]
        }

        result = detect_footnotes_pipeline(MagicMock(), page_num=1, context={})
        assert result.classifications[0].text == "Fallback content"


class TestFootnoteWithContinuationToDict:
    """Tests for _footnote_with_continuation_to_dict conversion."""

    def _make_footnote(self, **kwargs):
        """Create a FootnoteWithContinuation with defaults."""
        from lib.footnote_continuation import FootnoteWithContinuation
        from lib.rag_data_models import NoteSource

        defaults = {
            "marker": "1",
            "content": "Test content",
            "pages": [5],
            "bboxes": [{"x0": 50, "y0": 700, "x1": 550, "y1": 720}],
            "is_complete": True,
            "continuation_confidence": 1.0,
            "note_source": NoteSource.AUTHOR,
            "classification_confidence": 0.95,
            "classification_method": "schema_based",
            "font_name": "TimesNewRoman",
            "font_size": 9.0,
        }
        defaults.update(kwargs)
        return FootnoteWithContinuation(**defaults)

    def test_basic_conversion(self):
        """Should convert all fields to dict format."""
        from lib.rag.detection.footnotes import _footnote_with_continuation_to_dict

        fn = self._make_footnote()
        result = _footnote_with_continuation_to_dict(fn)

        assert result["marker"] == "1"
        assert result["actual_marker"] == "1"
        assert result["content"] == "Test content"
        assert result["pages"] == [5]
        assert result["is_complete"] is True
        assert result["continuation_confidence"] == 1.0
        assert result["font_name"] == "TimesNewRoman"
        assert result["font_size"] == 9.0
        assert result["classification_method"] == "schema_based"

    def test_note_source_enum_converted_to_name(self):
        """NoteSource enum should be converted to its name string."""
        from lib.rag.detection.footnotes import _footnote_with_continuation_to_dict
        from lib.rag_data_models import NoteSource

        fn = self._make_footnote(note_source=NoteSource.TRANSLATOR)
        result = _footnote_with_continuation_to_dict(fn)

        assert result["note_source"] == "TRANSLATOR"

    def test_note_source_string_passthrough(self):
        """String note_source should pass through as str()."""
        from lib.rag.detection.footnotes import _footnote_with_continuation_to_dict

        fn = self._make_footnote(note_source="custom_source")
        result = _footnote_with_continuation_to_dict(fn)

        assert result["note_source"] == "custom_source"

    def test_incomplete_footnote_fields(self):
        """Incomplete footnotes get proper incomplete_confidence and reason."""
        from lib.rag.detection.footnotes import _footnote_with_continuation_to_dict

        fn = self._make_footnote(
            is_complete=False,
            continuation_confidence=0.8,
            pages=[5, 6],
        )
        result = _footnote_with_continuation_to_dict(fn)

        assert result["is_complete"] is False
        assert result["incomplete_confidence"] == pytest.approx(0.2)
        assert result["incomplete_reason"] == "multi_page"

    def test_complete_single_page(self):
        """Complete single-page footnotes get reason 'complete'."""
        from lib.rag.detection.footnotes import _footnote_with_continuation_to_dict

        fn = self._make_footnote(is_complete=True, pages=[5])
        result = _footnote_with_continuation_to_dict(fn)

        assert result["incomplete_confidence"] == 1.0
        assert result["incomplete_reason"] == "complete"


class TestFormatFootnotesMarkdown:
    """Tests for _format_footnotes_markdown formatting."""

    def test_basic_formatting(self):
        """Should produce markdown footnote syntax."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        footnotes = {
            "definitions": [
                {"marker": "1", "content": "See Hegel, p. 42."},
                {"marker": "2", "content": "Cf. Kant, CPR A234/B287."},
            ]
        }

        result = _format_footnotes_markdown(footnotes)

        assert "[^1]: See Hegel, p. 42." in result
        assert "[^2]: Cf. Kant, CPR A234/B287." in result

    def test_low_confidence_adds_html_comment(self):
        """Low-confidence footnotes get an HTML comment with metadata."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        footnotes = {
            "definitions": [
                {
                    "marker": "*",
                    "content": "Uncertain note",
                    "confidence": 0.5,
                    "inference_method": "pattern_match",
                },
            ]
        }

        result = _format_footnotes_markdown(footnotes)

        assert "[^*]: Uncertain note" in result
        assert "<!-- Confidence: 0.50" in result
        assert "pattern_match" in result

    def test_high_confidence_no_comment(self):
        """High-confidence footnotes have no HTML comment."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        footnotes = {
            "definitions": [
                {"marker": "1", "content": "Normal note", "confidence": 0.9},
            ]
        }

        result = _format_footnotes_markdown(footnotes)

        assert "<!--" not in result
        assert "[^1]: Normal note" in result

    def test_empty_definitions(self):
        """Empty definitions list returns empty string."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        assert _format_footnotes_markdown({"definitions": []}) == ""

    def test_uses_actual_marker_over_marker(self):
        """Should prefer actual_marker (from corruption recovery) over marker."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        footnotes = {
            "definitions": [
                {
                    "marker": "?",
                    "actual_marker": "dagger",
                    "content": "Recovered footnote",
                },
            ]
        }

        result = _format_footnotes_markdown(footnotes)

        assert "[^dagger]:" in result

    def test_missing_marker_uses_question_mark(self):
        """Missing marker defaults to '?'."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        footnotes = {
            "definitions": [
                {"content": "No marker note"},
            ]
        }

        result = _format_footnotes_markdown(footnotes)

        assert "[^?]:" in result

    def test_multiple_footnotes_separated_by_double_newline(self):
        """Footnotes should be separated by double newlines."""
        from lib.rag.detection.footnotes import _format_footnotes_markdown

        footnotes = {
            "definitions": [
                {"marker": "1", "content": "First"},
                {"marker": "2", "content": "Second"},
            ]
        }

        result = _format_footnotes_markdown(footnotes)

        assert "\n\n" in result
