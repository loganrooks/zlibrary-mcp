"""
Unit tests for lib/rag/detection/headings.py

Targets uncovered lines: 24-25, 39-56, 90-91, 113-114, 128-130,
194-242, 246, 256-258, 262-264.

Uses synthetic mock objects — no real PDFs.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Fake TEXTFLAGS_DICT constant
_FAKE_TEXTFLAGS = 0


def _make_span(text: str, size: float, flags: int = 0) -> dict:
    """Build a dict span as returned by PyMuPDF get_text('dict')."""
    return {"text": text, "size": size, "flags": flags}


def _make_text_block(spans: list[dict]) -> dict:
    """Wrap spans in a single-line text block."""
    return {
        "type": 0,
        "lines": [{"spans": spans}],
    }


def _make_image_block() -> dict:
    return {"type": 1}


def _mock_page_with_blocks(blocks: list[dict]) -> MagicMock:
    """Return a mock page whose get_text('dict', ...) returns the given blocks."""
    page = MagicMock()
    page.get_text.return_value = {"blocks": blocks}
    return page


def _mock_doc_from_pages(pages: list[MagicMock]) -> MagicMock:
    doc = MagicMock()
    doc.__len__ = lambda self: len(pages)
    doc.__getitem__ = lambda self, idx: pages[idx]
    return doc


# ---------------------------------------------------------------------------
# Patch fitz.TEXTFLAGS_DICT at module level so the import succeeds even when
# fitz is not installed or the constant is missing.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_fitz_flags():
    """Ensure fitz.TEXTFLAGS_DICT exists for the headings module."""
    import lib.rag.detection.headings as mod

    if mod.fitz is None:
        # fitz not installed — create a minimal stub
        fake_fitz = MagicMock()
        fake_fitz.TEXTFLAGS_DICT = _FAKE_TEXTFLAGS
        mod.fitz = fake_fitz
    elif not hasattr(mod.fitz, "TEXTFLAGS_DICT"):
        mod.fitz.TEXTFLAGS_DICT = _FAKE_TEXTFLAGS
    yield


from lib.rag.detection.headings import (
    _analyze_font_distribution,
    _detect_headings_from_fonts,
    detect_headings_pipeline,
)


# ===================================================================
# _analyze_font_distribution  (lines 90-91, 113-114, 128-130)
# ===================================================================


class TestAnalyzeFontDistribution:
    def test_returns_mode_font_size(self):
        """Body text at 12pt should be detected as mode."""
        spans_12 = [_make_span("Body text here", 12.0)] * 5
        spans_16 = [_make_span("Heading", 16.0)]
        blocks = [_make_text_block(spans_12 + spans_16)]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        result = _analyze_font_distribution(doc, sample_pages=10)
        assert result == 12.0

    def test_empty_doc_returns_default(self):
        """No text spans -> fallback 10.0."""
        page = _mock_page_with_blocks([])
        doc = _mock_doc_from_pages([page])
        result = _analyze_font_distribution(doc)
        assert result == 10.0

    def test_short_text_ignored(self):
        """Spans shorter than 3 chars should be ignored."""
        blocks = [_make_text_block([_make_span("ab", 14.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        result = _analyze_font_distribution(doc)
        assert result == 10.0  # falls back because nothing qualifies

    def test_image_blocks_skipped(self):
        """Image blocks (type=1) should be skipped."""
        blocks = [
            _make_image_block(),
            _make_text_block([_make_span("Body text here", 10.0)]),
        ]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        result = _analyze_font_distribution(doc)
        assert result == 10.0

    def test_many_pages_sampling(self):
        """When total_pages > sample_pages, should sample evenly."""
        blocks = [_make_text_block([_make_span("Body text here", 11.0)])]
        pages = [_mock_page_with_blocks(blocks) for _ in range(25)]
        doc = _mock_doc_from_pages(pages)
        result = _analyze_font_distribution(doc, sample_pages=5)
        assert result == 11.0

    def test_exception_returns_default(self):
        """If page raises, should return 10.0."""
        page = MagicMock()
        page.get_text.side_effect = RuntimeError("corrupt page")
        doc = _mock_doc_from_pages([page])
        result = _analyze_font_distribution(doc)
        assert result == 10.0


# ===================================================================
# _detect_headings_from_fonts  (lines 194-242, 246, 256-258, 262-264)
# ===================================================================


class TestDetectHeadingsFromFonts:
    def test_h1_detected(self):
        """Font 1.8x body => H1."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Chapter One Title", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert 1 in toc
        assert toc[1][0][0] == 1  # level
        assert toc[1][0][1] == "Chapter One Title"

    def test_h2_detected(self):
        """Font 1.5x body => H2."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Section Heading", 15.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert 1 in toc
        assert toc[1][0][0] == 2

    def test_h3_bold(self):
        """Font 1.3x body + bold => H2; without bold => H3."""
        body_size = 10.0
        bold_span = _make_span("Bold SubSection", 13.0, flags=2)
        plain_span = _make_span("Plain SubSection", 13.0, flags=0)
        blocks = [_make_text_block([bold_span, plain_span])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        levels = [h[0] for h in toc[1]]
        assert 2 in levels  # bold -> H2
        assert 3 in levels  # non-bold -> H3

    def test_h4_non_bold(self):
        """Font 1.15x body, not bold => H4."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Minor heading text", 11.5, flags=0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert 1 in toc
        assert toc[1][0][0] == 4

    def test_h3_bold_at_115(self):
        """Font 1.15x body, bold => H3."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Bold minor heading", 11.5, flags=2)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert 1 in toc
        assert toc[1][0][0] == 3

    def test_filter_pure_number(self):
        """Pure digits should be filtered as page numbers."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("123", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert toc == {}

    def test_filter_short_roman(self):
        """Short roman numerals (<=5 chars) filtered."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("viii", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert toc == {}

    def test_filter_too_short(self):
        """Text shorter than min_heading_length filtered."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Hi", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert toc == {}

    def test_filter_too_long(self):
        """Text longer than max_heading_length filtered."""
        body_size = 10.0
        long_text = "A" * 151
        blocks = [_make_text_block([_make_span(long_text, 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert toc == {}

    def test_filter_low_alpha_ratio(self):
        """Text with <50% alphabetic chars filtered."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("1.2.3.4.5", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert toc == {}

    def test_filter_single_char(self):
        """Single character text (len==1) should be filtered even at heading size.
        Must use min_heading_length=1 so the length-constraint check passes
        and the single-char filter on line 213 is reached."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("A", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size, min_heading_length=1)
        assert toc == {}

    def test_else_branch_below_threshold_in_level_cascade(self):
        """Size ratio technically >= threshold (due to floating point) but
        falls into the else/continue branch at the bottom of the level cascade.
        A size_ratio of exactly 1.0 passes the initial `size >= min_heading_size`
        check when threshold is exactly 1.0, but hits the else branch in the
        level determination cascade (all comparisons < 1.15 fail)."""
        body_size = 10.0
        # With threshold=1.0, min_heading_size = 10.0, so size 10.0 passes
        # the initial check. But size_ratio = 1.0 < 1.15, so it hits else: continue
        blocks = [_make_text_block([_make_span("Some Valid Text", 10.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size, threshold=1.0)
        assert toc == {}

    def test_below_threshold_skipped(self):
        """Font size below threshold is not heading."""
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Normal text here", 10.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert toc == {}

    def test_exception_returns_empty(self):
        """Exception during detection returns empty dict."""
        page = MagicMock()
        page.get_text.side_effect = RuntimeError("corrupt")
        doc = _mock_doc_from_pages([page])
        toc = _detect_headings_from_fonts(doc, 10.0)
        assert toc == {}

    def test_multiple_pages(self):
        """Headings across multiple pages."""
        body_size = 10.0
        p1 = _mock_page_with_blocks(
            [_make_text_block([_make_span("Chapter One", 18.0)])]
        )
        p2 = _mock_page_with_blocks(
            [_make_text_block([_make_span("Chapter Two", 18.0)])]
        )
        doc = _mock_doc_from_pages([p1, p2])
        toc = _detect_headings_from_fonts(doc, body_size)
        assert 1 in toc and 2 in toc


# ===================================================================
# detect_headings_pipeline  (lines 39-56)
# ===================================================================


class TestDetectHeadingsPipeline:
    def test_pipeline_adapter(self):
        body_size = 10.0
        blocks = [_make_text_block([_make_span("Big Heading", 18.0)])]
        page = _mock_page_with_blocks(blocks)
        doc = _mock_doc_from_pages([page])
        context = {}

        with patch(
            "lib.rag.detection.headings._analyze_font_distribution",
            return_value=body_size,
        ):
            result = detect_headings_pipeline(doc, context)

        assert result.detector_name == "headings"
        assert "headings_map" in context
        assert len(result.classifications) >= 1
        cl = result.classifications[0]
        assert cl.content_type.value == "heading"
        assert cl.metadata["level"] == 1

    def test_pipeline_no_headings(self):
        page = _mock_page_with_blocks(
            [_make_text_block([_make_span("body text", 10.0)])]
        )
        doc = _mock_doc_from_pages([page])
        context = {}
        with patch(
            "lib.rag.detection.headings._analyze_font_distribution",
            return_value=10.0,
        ):
            result = detect_headings_pipeline(doc, context)
        assert result.classifications == []
        assert context["headings_map"] == {}
