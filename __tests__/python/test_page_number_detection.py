"""
Unit tests for lib/rag/detection/page_numbers.py

Targets uncovered lines: 14-15, 43-58, 77-104, 109-122, 127-137, 143,
175, 179, 186-190, 232-234, 251-257.

Uses synthetic mock objects — no real PDFs.
"""

from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers to build mock fitz objects
# ---------------------------------------------------------------------------


def _mock_page(text: str) -> MagicMock:
    """Return a mock fitz.Page whose get_text('text') returns *text*."""
    page = MagicMock()
    page.get_text.return_value = text
    return page


def _mock_doc(page_texts: list[str]) -> MagicMock:
    """Return a mock fitz.Document backed by a list of page text strings."""
    doc = MagicMock()
    pages = [_mock_page(t) for t in page_texts]
    doc.__len__ = lambda self: len(pages)
    doc.__getitem__ = lambda self, idx: pages[idx]
    return doc


# ---------------------------------------------------------------------------
# Import the module under test (fitz may or may not be installed)
# ---------------------------------------------------------------------------

from lib.rag.detection.page_numbers import (
    _extract_written_page_number,
    _roman_to_int,
    _int_to_roman,
    _is_roman_numeral,
    _detect_written_page_on_page,
    infer_written_page_numbers,
    detect_page_numbers_pipeline,
)


# ===================================================================
# _extract_written_page_number  (lines 77-104)
# ===================================================================


class TestExtractWrittenPageNumber:
    """Cover _extract_written_page_number branches."""

    def test_arabic_number_first_line(self):
        page = _mock_page("15\nSome body text here.")
        assert _extract_written_page_number(page) == "15"

    def test_roman_numeral_first_line(self):
        page = _mock_page("xxiii\nSome body text here.")
        assert _extract_written_page_number(page) == "xxiii"

    def test_arabic_number_last_line(self):
        page = _mock_page("Some body text here.\n42")
        assert _extract_written_page_number(page) == "42"

    def test_roman_numeral_last_line_uppercase(self):
        page = _mock_page("Some body text here.\nIV")
        assert _extract_written_page_number(page) == "IV"

    def test_page_pattern_first_line(self):
        page = _mock_page("Page 99\nBody text.")
        assert _extract_written_page_number(page) == "99"

    def test_page_pattern_p_dot_last_line(self):
        page = _mock_page("Body text.\np. 7")
        assert _extract_written_page_number(page) == "7"

    def test_no_page_number(self):
        page = _mock_page("Just some ordinary text.\nNo numbers here.")
        assert _extract_written_page_number(page) is None

    def test_empty_page(self):
        page = _mock_page("   \n   ")
        assert _extract_written_page_number(page) is None

    def test_exception_returns_none(self):
        page = MagicMock()
        page.get_text.side_effect = RuntimeError("boom")
        assert _extract_written_page_number(page) is None


# ===================================================================
# _roman_to_int  (lines 109-122)
# ===================================================================


class TestRomanToInt:
    def test_simple(self):
        assert _roman_to_int("i") == 1

    def test_subtractive(self):
        assert _roman_to_int("iv") == 4
        assert _roman_to_int("ix") == 9
        assert _roman_to_int("xiv") == 14

    def test_large(self):
        assert _roman_to_int("xxiii") == 23
        assert _roman_to_int("xlii") == 42

    def test_uppercase(self):
        assert _roman_to_int("XIV") == 14

    def test_mcm(self):
        assert _roman_to_int("mcm") == 1900


# ===================================================================
# _int_to_roman  (lines 127-137)
# ===================================================================


class TestIntToRoman:
    def test_one(self):
        assert _int_to_roman(1) == "i"

    def test_four(self):
        assert _int_to_roman(4) == "iv"

    def test_twenty_three(self):
        assert _int_to_roman(23) == "xxiii"

    def test_roundtrip(self):
        for n in (1, 4, 9, 14, 23, 42, 100, 500, 1900):
            assert _roman_to_int(_int_to_roman(n)) == n


# ===================================================================
# _is_roman_numeral  (line 143)
# ===================================================================


class TestIsRomanNumeral:
    def test_empty_string(self):
        assert _is_roman_numeral("") is False

    def test_valid(self):
        assert _is_roman_numeral("xiv") is True

    def test_invalid(self):
        assert _is_roman_numeral("abc") is False

    def test_mixed(self):
        assert _is_roman_numeral("x2") is False


# ===================================================================
# _detect_written_page_on_page  (lines 175, 179, 186-190)
# ===================================================================


class TestDetectWrittenPageOnPage:
    def test_roman_first_line(self):
        page = _mock_page("xiv\nBody text here.")
        num, pos, matched = _detect_written_page_on_page(page)
        assert num == "xiv"
        assert pos == "first"
        assert matched == "xiv"

    def test_arabic_last_line(self):
        page = _mock_page("Body text here.\n42")
        num, pos, matched = _detect_written_page_on_page(page)
        assert num == "42"
        assert pos == "last"
        assert matched == "42"

    def test_page_pattern(self):
        page = _mock_page("Body text.\nPage 5")
        num, pos, matched = _detect_written_page_on_page(page)
        assert num == "5"
        assert pos == "last"

    def test_no_match(self):
        page = _mock_page("Hello world.\nGoodbye world.")
        assert _detect_written_page_on_page(page) == (None, None, None)

    def test_empty_page(self):
        page = _mock_page("   ")
        assert _detect_written_page_on_page(page) == (None, None, None)

    def test_exception_returns_triple_none(self):
        page = MagicMock()
        page.get_text.side_effect = RuntimeError("fail")
        assert _detect_written_page_on_page(page) == (None, None, None)


# ===================================================================
# infer_written_page_numbers  (lines 232-234, 251-257)
# ===================================================================


class TestInferWrittenPageNumbers:
    def test_roman_anchor_only(self):
        """Pages: title, iii, iv, v — no arabic anchor."""
        texts = ["Title Page", "iii\nText", "Body text\niv", "Body text\nv"]
        doc = _mock_doc(texts)
        result = infer_written_page_numbers(doc, scan_pages=10)
        # Should map pages starting from the first roman anchor
        assert 2 in result  # pdf page 2 => iii
        assert result[2] == "iii"
        assert result[3] == "iv"
        assert result[4] == "v"

    def test_arabic_anchor_only(self):
        """Pages: title, 1, body, body — arabic starts on page 2."""
        texts = ["Title Page", "1\nChapter One", "Body text", "More body"]
        doc = _mock_doc(texts)
        result = infer_written_page_numbers(doc, scan_pages=10)
        assert 2 in result
        assert result[2] == "1"
        assert result[3] == "2"
        assert result[4] == "3"

    def test_roman_then_arabic(self):
        """Preface in roman then main content in arabic."""
        texts = [
            "Title",  # page 1 — no match
            "i\nPreface",  # page 2 — roman anchor
            "ii\nMore",  # page 3
            "1\nChapter 1",  # page 4 — arabic anchor
            "Body text",  # page 5
        ]
        doc = _mock_doc(texts)
        result = infer_written_page_numbers(doc, scan_pages=10)
        # Roman section: pages 2-3
        assert result[2] == "i"
        assert result[3] == "ii"
        # Arabic section: pages 4-5
        assert result[4] == "1"
        assert result[5] == "2"

    def test_no_anchors(self):
        texts = ["Title Page", "Some text", "More text"]
        doc = _mock_doc(texts)
        result = infer_written_page_numbers(doc, scan_pages=10)
        assert result == {}


# ===================================================================
# detect_page_numbers_pipeline  (lines 43-58)
# ===================================================================


class TestDetectPageNumbersPipeline:
    def test_pipeline_adapter(self):
        """Ensure the pipeline adapter populates context and returns DetectionResult."""
        texts = ["Title", "1\nBody"]
        doc = _mock_doc(texts)
        context = {}
        result = detect_page_numbers_pipeline(doc, context)

        assert result.detector_name == "page_numbers"
        assert "page_number_map" in context
        # Should have at least one classification
        assert len(result.classifications) >= 1
        cl = result.classifications[0]
        assert cl.content_type.value == "page_number"
        assert cl.detector_name == "page_numbers"

    def test_pipeline_no_pages(self):
        doc = _mock_doc(["No numbers here", "Still nothing"])
        context = {}
        result = detect_page_numbers_pipeline(doc, context)
        assert result.classifications == []
        assert context["page_number_map"] == {}
