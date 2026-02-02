"""Tests for margin detection and classification modules."""

from unittest.mock import MagicMock

import pytest

from lib.rag.detection.margin_patterns import (
    classify_margin_content,
)
from lib.rag.detection.margins import (
    _infer_body_column,
    _classify_block_zone,
    detect_margin_content,
)


# ============================================================
# classify_margin_content tests
# ============================================================


class TestClassifyMarginContent:
    """Tests for typed margin content classification."""

    # --- Stephanus references ---

    def test_stephanus_basic(self):
        assert classify_margin_content("231a") == ("stephanus", "231a")

    def test_stephanus_range(self):
        assert classify_margin_content("514b-c") == ("stephanus", "514b-c")

    def test_stephanus_two_digit(self):
        assert classify_margin_content("45e") == ("stephanus", "45e")

    def test_stephanus_en_dash_range(self):
        assert classify_margin_content("99a\u2013c") == ("stephanus", "99a\u2013c")

    # --- Bekker references ---

    def test_bekker_basic(self):
        assert classify_margin_content("1094a1") == ("bekker", "1094a1")

    def test_bekker_four_digit(self):
        assert classify_margin_content("1140b5") == ("bekker", "1140b5")

    def test_bekker_three_digit(self):
        assert classify_margin_content("980a12") == ("bekker", "980a12")

    # --- Line numbers ---

    def test_line_number_simple(self):
        assert classify_margin_content("25") == ("line_number", "25")

    def test_line_number_one(self):
        assert classify_margin_content("1") == ("line_number", "1")

    def test_line_number_max(self):
        assert classify_margin_content("9999") == ("line_number", "9999")

    def test_line_number_zero_not_matched(self):
        assert classify_margin_content("0") == ("margin", "0")

    def test_line_number_out_of_range(self):
        assert classify_margin_content("10000") == ("margin", "10000")

    # --- Generic margin ---

    def test_generic_margin_cf(self):
        assert classify_margin_content("cf. Book III") == ("margin", "cf. Book III")

    def test_generic_margin_see_also(self):
        assert classify_margin_content("See also p. 45") == ("margin", "See also p. 45")

    def test_generic_margin_empty(self):
        assert classify_margin_content("") == ("margin", "")

    # --- Edge cases ---

    def test_whitespace_stripped(self):
        assert classify_margin_content(" 231a ") == ("stephanus", "231a")

    def test_pure_number_is_line_number_not_stephanus(self):
        assert classify_margin_content("123") == ("line_number", "123")

    def test_three_digit_plus_letter_is_stephanus(self):
        assert classify_margin_content("123a") == ("stephanus", "123a")

    def test_four_digit_plus_ab_plus_digit_is_bekker(self):
        assert classify_margin_content("1234a1") == ("bekker", "1234a1")

    def test_no_overlap_stephanus_bekker(self):
        # "123a" is Stephanus (no trailing digit), "123a1" would need 3+ digits + a/b + digit
        assert classify_margin_content("123a")[0] == "stephanus"
        assert classify_margin_content("123a1")[0] == "bekker"


# ============================================================
# _infer_body_column tests
# ============================================================


def _make_block(x0, y0, x1, y1, text="body text"):
    """Helper to create a PyMuPDF-style text block dict."""
    return {
        "bbox": (x0, y0, x1, y1),
        "lines": [{"spans": [{"text": text}]}],
    }


def _make_page_rect(width=612, height=792):
    rect = MagicMock()
    rect.x0 = 0
    rect.y0 = 0
    rect.x1 = width
    rect.y1 = height
    rect.width = width
    rect.height = height
    return rect


class TestInferBodyColumn:
    """Tests for statistical body column inference."""

    def test_clustered_blocks_infer_body(self):
        blocks = [_make_block(72, i * 50, 540, i * 50 + 40) for i in range(6)]
        page_rect = _make_page_rect()
        result = _infer_body_column(blocks, page_rect)
        assert result["body_left"] == pytest.approx(72, abs=6)
        assert result["body_right"] == pytest.approx(540, abs=6)
        assert result["is_two_column"] is False

    def test_few_blocks_use_fallback(self):
        blocks = [_make_block(100, 50, 500, 90)]
        page_rect = _make_page_rect(612, 792)
        result = _infer_body_column(blocks, page_rect, fallback_margin_pct=0.12)
        # fallback: 612 * 0.12 = 73.44
        assert result["body_left"] == pytest.approx(73.44, abs=1)
        assert result["body_right"] == pytest.approx(612 - 73.44, abs=1)

    def test_two_column_detection(self):
        # Two groups of blocks at different x0 positions
        blocks = []
        for i in range(5):
            blocks.append(_make_block(72, i * 50, 290, i * 50 + 40))
        for i in range(5):
            blocks.append(_make_block(310, i * 50, 540, i * 50 + 40))
        page_rect = _make_page_rect()
        result = _infer_body_column(blocks, page_rect)
        assert result["is_two_column"] is True


class TestClassifyBlockZone:
    """Tests for block zone classification."""

    def test_body_block(self):
        zone = _classify_block_zone(
            (100, 100, 500, 120), 72, 540, _make_page_rect(), 0.08, 0.08
        )
        assert zone == "body"

    def test_left_margin(self):
        zone = _classify_block_zone(
            (10, 100, 60, 120), 72, 540, _make_page_rect(), 0.08, 0.08
        )
        assert zone == "margin-left"

    def test_right_margin(self):
        zone = _classify_block_zone(
            (550, 100, 600, 120), 72, 540, _make_page_rect(), 0.08, 0.08
        )
        assert zone == "margin-right"

    def test_header_zone(self):
        # top 8% of 792 = 63.36
        zone = _classify_block_zone(
            (100, 10, 500, 50), 72, 540, _make_page_rect(), 0.08, 0.08
        )
        assert zone == "header"

    def test_footer_zone(self):
        # bottom 8% of 792 = 728.64+
        zone = _classify_block_zone(
            (100, 750, 500, 780), 72, 540, _make_page_rect(), 0.08, 0.08
        )
        assert zone == "footer"

    def test_configurable_zones(self):
        # 15% header zone = 118.8
        zone = _classify_block_zone(
            (100, 100, 500, 110), 72, 540, _make_page_rect(), 0.15, 0.08
        )
        assert zone == "header"


class TestDetectMarginContent:
    """Tests for the main detect_margin_content function."""

    def _make_mock_page(self, blocks, width=612, height=792):
        page = MagicMock()
        rect = _make_page_rect(width, height)
        page.rect = rect
        page.cropbox = rect
        page.mediabox = rect
        page.get_text.return_value = {"blocks": blocks}
        return page

    def test_detects_margin_blocks(self):
        blocks = [
            # Body blocks
            *[
                _make_block(72, i * 50 + 100, 540, i * 50 + 140, "body text here")
                for i in range(5)
            ],
            # Left margin block with Stephanus ref
            _make_block(10, 100, 60, 115, "231a"),
        ]
        page = self._make_mock_page(blocks)
        result = detect_margin_content(page)
        assert len(result["margin_blocks"]) == 1
        assert result["margin_blocks"][0]["type"] == "stephanus"
        assert result["margin_blocks"][0]["content"] == "231a"
        assert result["is_two_column"] is False

    def test_excluded_bboxes_skipped(self):
        blocks = [
            *[_make_block(72, i * 50 + 100, 540, i * 50 + 140) for i in range(5)],
            _make_block(10, 100, 60, 115, "231a"),
        ]
        page = self._make_mock_page(blocks)
        # Exclude the margin block
        result = detect_margin_content(page, excluded_bboxes=[(10, 100, 60, 115)])
        assert len(result["margin_blocks"]) == 0

    def test_scan_artifact_filtered(self):
        blocks = [
            *[_make_block(72, i * 50 + 100, 540, i * 50 + 140) for i in range(5)],
            # Single char - scan artifact
            _make_block(10, 100, 18, 115, "x"),
            # Narrow block
            _make_block(10, 200, 18, 215, "abc"),
        ]
        page = self._make_mock_page(blocks)
        result = detect_margin_content(page)
        assert len(result["margin_blocks"]) == 0

    def test_header_footer_excluded(self):
        blocks = [
            *[_make_block(72, i * 50 + 100, 540, i * 50 + 140) for i in range(5)],
            # Block in header zone (margin-left position but top of page)
            _make_block(10, 10, 60, 30, "231a"),
            # Block in footer zone
            _make_block(10, 760, 60, 780, "45e"),
        ]
        page = self._make_mock_page(blocks)
        result = detect_margin_content(page)
        assert len(result["margin_blocks"]) == 0

    def test_return_structure(self):
        blocks = [_make_block(72, i * 50 + 100, 540, i * 50 + 140) for i in range(5)]
        page = self._make_mock_page(blocks)
        result = detect_margin_content(page)
        assert "margin_blocks" in result
        assert "body_column" in result
        assert "is_two_column" in result
        assert isinstance(result["body_column"], tuple)
        assert len(result["body_column"]) == 2
