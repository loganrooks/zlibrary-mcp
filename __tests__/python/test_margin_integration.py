"""Integration tests for the full margin detection pipeline.

Verifies end-to-end: mock PDF page -> detect_margin_content -> _format_pdf_markdown
-> clean markdown with typed annotations.
"""

from unittest.mock import MagicMock


from lib.rag.detection.margins import detect_margin_content
from lib.rag.processors.pdf import _format_pdf_markdown, _associate_margin_to_body


# ---------------------------------------------------------------------------
# Helpers to build mock PyMuPDF page objects
# ---------------------------------------------------------------------------


def _make_rect(width=595, height=842):
    """Create a mock fitz.Rect (A4 page)."""
    rect = MagicMock()
    rect.width = width
    rect.height = height
    # Make equality work for cropbox/mediabox comparison
    rect.__eq__ = lambda self, other: True
    rect.__ne__ = lambda self, other: False
    return rect


def _make_block(x0, y0, x1, y1, text, block_type=0):
    """Create a PyMuPDF-style text block dict."""
    return {
        "type": block_type,
        "bbox": (x0, y0, x1, y1),
        "lines": [
            {
                "spans": [
                    {
                        "text": text,
                        "size": 10,
                        "flags": 0,
                        "font": "Times",
                        "color": 0,
                    }
                ],
                "bbox": (x0, y0, x1, y1),
            }
        ],
    }


def _make_page(blocks, width=595, height=842):
    """Create a mock PyMuPDF page with given blocks."""
    page = MagicMock()
    rect = _make_rect(width, height)
    page.rect = rect
    page.cropbox = rect
    page.mediabox = rect

    dict_data = {"blocks": blocks}
    page.get_text = MagicMock(
        side_effect=lambda fmt, **kw: dict_data if fmt == "dict" else dict_data
    )
    return page


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestStephanusMargins:
    """Scenario 1: Scholarly PDF with Stephanus margin references."""

    def _build_page(self):
        blocks = [
            # Body text blocks (main column)
            _make_block(
                72,
                100,
                540,
                130,
                "Socrates begins the dialogue with a question about virtue.",
            ),
            _make_block(
                72, 140, 540, 170, "He asks whether virtue can be taught or is innate."
            ),
            # Left-margin Stephanus references
            _make_block(10, 105, 55, 120, "231a"),
            _make_block(10, 145, 55, 160, "231b"),
        ]
        return _make_page(blocks)

    def test_margin_blocks_detected(self):
        page = self._build_page()
        result = detect_margin_content(page)
        margin_blocks = result["margin_blocks"]
        types = {mb["type"] for mb in margin_blocks}
        assert "stephanus" in types
        assert len(margin_blocks) == 2

    def test_annotations_in_output(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{stephanus: 231a}}" in md
        assert "{{stephanus: 231b}}" in md

    def test_body_text_clean(self):
        """Body text must not contain leaked Stephanus references."""
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        # Remove annotations to check body text
        body = md.replace("{{stephanus: 231a}}", "").replace("{{stephanus: 231b}}", "")
        assert "231a" not in body
        assert "231b" not in body


class TestBekkerMargins:
    """Scenario 2: Scholarly PDF with Bekker margin references."""

    def _build_page(self):
        blocks = [
            _make_block(
                72, 100, 540, 130, "Aristotle discusses the nature of the good."
            ),
            _make_block(72, 140, 540, 170, "Every art and inquiry aims at some good."),
            _make_block(10, 105, 60, 120, "1094a1"),
            _make_block(10, 145, 60, 160, "1094a15"),
        ]
        return _make_page(blocks)

    def test_bekker_detected(self):
        page = self._build_page()
        result = detect_margin_content(page)
        types = [mb["type"] for mb in result["margin_blocks"]]
        assert "bekker" in types

    def test_bekker_annotations_in_output(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{bekker: 1094a1}}" in md
        assert "{{bekker: 1094a15}}" in md

    def test_body_clean_of_bekker(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        body = md.replace("{{bekker: 1094a1}}", "").replace("{{bekker: 1094a15}}", "")
        assert "1094a1" not in body


class TestLineNumberMargins:
    """Scenario 3: Poetry with line numbers in left margin."""

    def _build_page(self):
        blocks = [
            _make_block(
                72,
                100,
                540,
                115,
                "Sing, O goddess, the anger of Achilles son of Peleus,",
            ),
            _make_block(
                72, 120, 540, 135, "that brought countless ills upon the Achaeans."
            ),
            _make_block(
                72,
                140,
                540,
                155,
                "Many a brave soul did it send hurrying down to Hades,",
            ),
            _make_block(
                72, 160, 540, 175, "and many a hero did it yield a prey to dogs."
            ),
            # Line numbers in left margin (multi-digit; single digits filtered as scan artifacts)
            _make_block(10, 102, 35, 115, "10"),
            _make_block(10, 122, 35, 135, "15"),
            _make_block(10, 142, 35, 155, "20"),
            _make_block(10, 162, 35, 175, "25"),
        ]
        return _make_page(blocks)

    def test_line_numbers_detected(self):
        page = self._build_page()
        result = detect_margin_content(page)
        types = [mb["type"] for mb in result["margin_blocks"]]
        assert types.count("line_number") == 4

    def test_line_number_annotations(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{line_number: 10}}" in md
        assert "{{line_number: 15}}" in md
        assert "{{line_number: 20}}" in md
        assert "{{line_number: 25}}" in md

    def test_body_is_clean_poetry(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        # Body should contain poetry text
        assert "Sing, O goddess" in md
        assert "countless ills" in md


class TestGenericMarginNotes:
    """Scenario 4: Right-margin cross-reference note."""

    def _build_page(self):
        blocks = [
            _make_block(
                72,
                100,
                500,
                130,
                "The prisoners in the cave see only shadows on the wall.",
            ),
            _make_block(
                72, 140, 500, 170, "They mistake these shadows for reality itself."
            ),
            _make_block(
                72,
                180,
                500,
                210,
                "Education is the process of turning the soul around.",
            ),
            _make_block(
                72,
                220,
                500,
                250,
                "The philosopher must return to the cave to lead others.",
            ),
            # Right margin note (well beyond the body right edge ~500)
            _make_block(510, 105, 585, 125, "cf. Republic 514a"),
        ]
        return _make_page(blocks)

    def test_generic_margin_detected(self):
        page = self._build_page()
        result = detect_margin_content(page)
        assert len(result["margin_blocks"]) == 1
        assert result["margin_blocks"][0]["type"] == "margin"

    def test_margin_annotation_in_output(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{margin: cf. Republic 514a}}" in md


class TestTwoColumnLayout:
    """Scenario 5: Two-column layout must NOT produce false margin detections."""

    def _build_page(self):
        # Two columns: left at x=72-290, right at x=310-540
        # Need enough blocks per column for statistical inference
        blocks = [
            _make_block(72, 100, 290, 130, "Left column paragraph one text here."),
            _make_block(72, 140, 290, 170, "Left column paragraph two text here."),
            _make_block(72, 180, 290, 210, "Left column paragraph three text."),
            _make_block(72, 220, 290, 250, "Left column paragraph four text."),
            _make_block(310, 100, 540, 130, "Right column paragraph one text here."),
            _make_block(310, 140, 540, 170, "Right column paragraph two text here."),
            _make_block(310, 180, 540, 210, "Right column paragraph three text."),
            _make_block(310, 220, 540, 250, "Right column paragraph four text."),
        ]
        return _make_page(blocks)

    def test_two_column_detected(self):
        page = self._build_page()
        result = detect_margin_content(page)
        assert result["is_two_column"] is True

    def test_no_false_margin_blocks(self):
        page = self._build_page()
        result = detect_margin_content(page)
        assert len(result["margin_blocks"]) == 0

    def test_no_annotations_in_output(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{" not in md


class TestNoMarginPDF:
    """Scenario 6: Standard PDF without margins -- backward compatibility."""

    def _build_page(self):
        blocks = [
            _make_block(
                72, 100, 540, 130, "This is a standard paragraph in a normal PDF."
            ),
            _make_block(
                72, 140, 540, 170, "There are no margin annotations or references."
            ),
            _make_block(
                72, 180, 540, 210, "The text flows normally without side content."
            ),
            _make_block(72, 220, 540, 250, "All blocks are in the body zone."),
        ]
        return _make_page(blocks)

    def test_no_margins_detected(self):
        page = self._build_page()
        result = detect_margin_content(page)
        assert len(result["margin_blocks"]) == 0

    def test_output_has_no_annotations(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{" not in md

    def test_body_text_preserved(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "standard paragraph" in md
        assert "flows normally" in md


class TestScanArtifactFiltering:
    """Scenario 7: Narrow/single-char margin blocks should be filtered out."""

    def _build_page(self):
        blocks = [
            _make_block(72, 100, 540, 130, "Body text for the main content area."),
            _make_block(72, 140, 540, 170, "More body text follows here."),
            _make_block(72, 180, 540, 210, "And a third paragraph of body text."),
            _make_block(72, 220, 540, 250, "Fourth paragraph for stats."),
            # Scan artifacts in margin zone: single char (too short)
            _make_block(10, 105, 25, 115, "x"),
            # Very narrow block (width < 10pt)
            _make_block(10, 145, 18, 155, "ab"),
        ]
        return _make_page(blocks)

    def test_artifacts_filtered(self):
        page = self._build_page()
        result = detect_margin_content(page)
        # Single char "x" filtered by _MIN_TEXT_LEN < 2
        # Narrow block "ab" (width=8) filtered by _MIN_BLOCK_WIDTH < 10
        assert len(result["margin_blocks"]) == 0

    def test_no_artifact_annotations(self):
        page = self._build_page()
        result = detect_margin_content(page)
        md = _format_pdf_markdown(page, margin_blocks=result["margin_blocks"])
        assert "{{" not in md


class TestAssociateMarginToBody:
    """Unit tests for margin-to-body block association."""

    def test_y_overlap_match(self):
        body_blocks = [
            {"bbox": (72, 100, 540, 130)},
            {"bbox": (72, 140, 540, 170)},
        ]
        # Margin at y=110 (center) overlaps body block 0
        idx = _associate_margin_to_body((10, 105, 50, 115), body_blocks)
        assert idx == 0

    def test_nearest_match(self):
        body_blocks = [
            {"bbox": (72, 100, 540, 110)},
            {"bbox": (72, 200, 540, 210)},
        ]
        # Margin at y=195-205, closer to block 1
        idx = _associate_margin_to_body((10, 195, 50, 205), body_blocks)
        assert idx == 1

    def test_empty_body_blocks(self):
        idx = _associate_margin_to_body((10, 100, 50, 120), [])
        assert idx == 0
