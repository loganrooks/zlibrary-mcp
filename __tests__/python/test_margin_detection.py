"""Tests for margin detection and classification modules."""

from lib.rag.detection.margin_patterns import (
    classify_margin_content,
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
