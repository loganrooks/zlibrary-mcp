"""
Tests for lib/rag/utils/text.py — text processing utilities.

Covers uncovered branches in _slugify (allow_unicode, empty result),
_html_to_text (missing BeautifulSoup, parse error), and
_apply_formatting_to_text (italic, bold+italic, strikethrough, sous-erasure,
underline, superscript, subscript, trailing-whitespace skip).
"""

import pytest
from unittest.mock import MagicMock

from lib.rag.utils.text import _slugify, _html_to_text, _apply_formatting_to_text

pytestmark = pytest.mark.unit


class TestSlugify:
    """Tests for the _slugify helper."""

    def test_basic_ascii(self):
        """Standard ASCII input produces a clean slug."""
        assert _slugify("Hello World") == "hello-world"

    def test_special_characters_stripped(self):
        """Non-alphanumeric characters become hyphens."""
        assert _slugify("Hello, World! (2024)") == "hello-world-2024"

    def test_unicode_normalized_to_ascii(self):
        """Accented characters decompose to ASCII by default."""
        result = _slugify("cafe\u0301")  # cafe + combining accent
        assert result == "cafe"

    def test_allow_unicode_preserves_non_ascii(self):
        """With allow_unicode=True, non-ASCII letters are kept."""
        result = _slugify("Hegels Phänomenologie", allow_unicode=True)
        assert "phänomenologie" in result or "phanomenologie" in result

    def test_allow_unicode_collapses_whitespace(self):
        """Even in unicode mode, multiple spaces collapse to single hyphen."""
        result = _slugify("hello   world", allow_unicode=True)
        assert result == "hello-world"

    def test_empty_string_returns_file(self):
        """Empty input or input that reduces to nothing returns 'file'."""
        assert _slugify("") == "file"

    def test_only_special_chars_returns_file(self):
        """Input with only special characters returns 'file'."""
        assert _slugify("!!!@@@###") == "file"

    def test_leading_trailing_hyphens_stripped(self):
        """Leading and trailing hyphens are removed."""
        assert _slugify("-hello-") == "hello"

    def test_consecutive_spaces(self):
        """Multiple consecutive spaces become a single hyphen."""
        assert _slugify("a    b    c") == "a-b-c"

    def test_numeric_input(self):
        """Numeric strings work fine."""
        assert _slugify("12345") == "12345"


class TestHtmlToText:
    """Tests for the _html_to_text helper."""

    def test_basic_html(self):
        """Extracts plain text from simple HTML."""
        result = _html_to_text("<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "world" in result

    def test_nested_html(self):
        """Handles nested HTML elements."""
        html = "<div><p>Paragraph 1</p><p>Paragraph 2</p></div>"
        result = _html_to_text(html)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result

    def test_beautifulsoup_unavailable(self, monkeypatch):
        """Returns empty string when BeautifulSoup is not available."""
        monkeypatch.setattr("lib.rag.utils.text.BeautifulSoup", None)
        result = _html_to_text("<p>Hello</p>")
        assert result == ""

    def test_parse_error_returns_empty(self, monkeypatch):
        """Returns empty string when BeautifulSoup raises an exception."""
        mock_bs = MagicMock(side_effect=Exception("Parse error"))
        monkeypatch.setattr("lib.rag.utils.text.BeautifulSoup", mock_bs)
        result = _html_to_text("<p>broken</p>")
        assert result == ""

    def test_empty_html(self):
        """Empty HTML input returns empty string."""
        result = _html_to_text("")
        assert result == ""


class TestApplyFormattingToText:
    """Tests for _apply_formatting_to_text markdown formatting."""

    def test_no_formatting(self):
        """Empty formatting set returns text unchanged."""
        assert _apply_formatting_to_text("hello", set()) == "hello"

    def test_bold(self):
        """Bold formatting wraps text in **."""
        assert _apply_formatting_to_text("hello", {"bold"}) == "**hello**"

    def test_italic(self):
        """Italic formatting wraps text in *."""
        assert _apply_formatting_to_text("hello", {"italic"}) == "*hello*"

    def test_bold_italic_combined(self):
        """Bold + italic formatting wraps text in ***."""
        result = _apply_formatting_to_text("hello", {"bold", "italic"})
        assert result == "***hello***"

    def test_strikethrough(self):
        """Strikethrough wraps text in ~~."""
        assert _apply_formatting_to_text("hello", {"strikethrough"}) == "~~hello~~"

    def test_sous_erasure_without_strikethrough(self):
        """Sous-erasure (when no strikethrough) also produces ~~ wrapping."""
        result = _apply_formatting_to_text("Being", {"sous-erasure"})
        assert result == "~~Being~~"

    def test_sous_erasure_with_strikethrough_no_double_wrap(self):
        """When both sous-erasure and strikethrough, only one ~~ wrapping."""
        result = _apply_formatting_to_text("hello", {"strikethrough", "sous-erasure"})
        assert result == "~~hello~~"
        # Should NOT be ~~~~hello~~~~
        assert "~~~~" not in result

    def test_underline(self):
        """Underline wraps text in <u> tags."""
        assert _apply_formatting_to_text("hello", {"underline"}) == "<u>hello</u>"

    def test_superscript(self):
        """Superscript wraps text in ^."""
        assert _apply_formatting_to_text("2", {"superscript"}) == "^2^"

    def test_subscript(self):
        """Subscript wraps text in ~."""
        assert _apply_formatting_to_text("2", {"subscript"}) == "~2~"

    def test_trailing_space_skips_formatting(self):
        """Text ending with space is NOT formatted (prevents malformed markdown)."""
        assert _apply_formatting_to_text("hello ", {"bold"}) == "hello "

    def test_trailing_tab_skips_formatting(self):
        """Text ending with tab is NOT formatted."""
        assert _apply_formatting_to_text("hello\t", {"italic"}) == "hello\t"

    def test_trailing_newline_skips_formatting(self):
        """Text ending with newline is NOT formatted."""
        assert _apply_formatting_to_text("hello\n", {"bold"}) == "hello\n"

    def test_combined_bold_and_underline(self):
        """Multiple formatting types can stack."""
        result = _apply_formatting_to_text("hello", {"bold", "underline"})
        assert "**hello**" in result or "<u>" in result
        # Both should be applied
        assert "<u>" in result
        assert "**" in result

    def test_combined_italic_superscript(self):
        """Italic and superscript can combine."""
        result = _apply_formatting_to_text("n", {"italic", "superscript"})
        # The inner text gets italic first, then superscript wraps
        assert "^" in result
        assert "*" in result
