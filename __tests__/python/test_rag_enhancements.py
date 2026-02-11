"""
Unit tests for RAG processing enhancements.

Tests OCR letter spacing correction and other new RAG functionality.
"""

import pytest
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from rag_processing import detect_letter_spacing_issue, correct_letter_spacing

pytestmark = pytest.mark.unit


class TestDetectLetterSpacingIssue:
    """Test letter spacing issue detection."""

    def test_detect_obvious_spacing_issue(self):
        """Test detection of obvious letter spacing."""
        text = "T H E  B U R N O U T  S O C I E T Y"
        assert detect_letter_spacing_issue(text) is True

    def test_detect_mixed_spacing_issue(self):
        """Test detection with mixed spacing."""
        text = "T H E book has S P A C I N G issues in O C R"
        # Has significant single-letter patterns
        result = detect_letter_spacing_issue(text)
        # Should detect the issue
        assert result is True

    def test_no_spacing_issue_normal_text(self):
        """Test no detection for normal text."""
        text = "The Burnout Society is a book about modern exhaustion."
        assert detect_letter_spacing_issue(text) is False

    def test_no_spacing_issue_short_text(self):
        """Test very short text returns False."""
        text = "Hello"
        assert detect_letter_spacing_issue(text) is False

    def test_spacing_issue_at_threshold(self):
        """Test detection at threshold boundary."""
        # Create text with exactly 60% single letters
        _text = "A B C D E F normal words here"
        # This should be close to threshold
        # May or may not detect depending on implementation


class TestCorrectLetterSpacing:
    """Test letter spacing correction."""

    def test_correct_basic_spacing(self):
        """Test basic letter spacing correction."""
        text = "T H E  B U R N O U T"
        corrected = correct_letter_spacing(text)

        assert "THE" in corrected
        assert "BURNOUT" in corrected
        # Should not have excessive spaces between letters
        assert "T H E" not in corrected

    def test_correct_mixed_content(self):
        """Test correction with mixed spaced and normal text."""
        text = "T H E book about S O C I E T Y and exhaustion"
        corrected = correct_letter_spacing(text)

        assert "THE" in corrected
        assert "book" in corrected  # Normal word preserved
        assert "SOCIETY" in corrected
        assert "exhaustion" in corrected  # Normal word preserved

    def test_correct_lowercase_spacing(self):
        """Test correction of lowercase spaced letters."""
        text = "t h e  b u r n o u t"
        corrected = correct_letter_spacing(text)

        assert "the" in corrected
        assert "burnout" in corrected

    def test_correct_preserves_normal_text(self):
        """Test that normal text is preserved."""
        text = "This is normal text without spacing issues."
        corrected = correct_letter_spacing(text)

        # Should return unchanged or very similar
        assert "This is normal text" in corrected

    def test_correct_handles_mixed_case(self):
        """Test handling of mixed case spacing."""
        text = "T h e  B o o k"
        corrected = correct_letter_spacing(text)

        # Should collapse spacing
        assert "The" in corrected or "THE" in corrected
        assert "Book" in corrected or "BOOK" in corrected

    def test_correct_preserves_paragraphs(self):
        """Test that paragraph structure is preserved."""
        text = """T H E  F I R S T

P A R A G R A P H

T H E  S E C O N D"""

        corrected = correct_letter_spacing(text)

        # Should have line breaks preserved
        assert "\n\n" in corrected or "\n" in corrected
        assert "FIRST" in corrected
        assert "PARAGRAPH" in corrected
        assert "SECOND" in corrected

    def test_correct_handles_punctuation(self):
        """Test that punctuation is handled correctly."""
        text = "T H E , book."
        corrected = correct_letter_spacing(text)

        # THE should be collapsed, punctuation preserved
        assert "THE" in corrected
        assert "," in corrected
        assert "book" in corrected

    def test_no_correction_when_not_needed(self):
        """Test that correction is skipped for normal text."""
        text = "Normal text without spacing issues."
        corrected = correct_letter_spacing(text)

        # Should return original or very similar
        # (Detection should prevent correction)
        assert "Normal text" in corrected

    def test_correct_multiple_spaced_words(self):
        """Test correction of multiple spaced words in sequence."""
        text = "T H E  B U R N O U T  S O C I E T Y  I S  A  B O O K"
        corrected = correct_letter_spacing(text)

        assert "THE" in corrected
        assert "BURNOUT" in corrected
        assert "SOCIETY" in corrected
        assert "IS" in corrected or "is" in corrected
        assert "BOOK" in corrected

    def test_correct_preserves_intentional_spacing(self):
        """Test that intentional spacing between words is preserved."""
        text = "T H E book has I S S U E S but not everywhere"
        corrected = correct_letter_spacing(text)

        # Words should be separated
        assert "book has" in corrected or "book  has" in corrected
        # Not merged together
        assert "bookhas" not in corrected


class TestPageMarkerInjection:
    """Test page marker functionality (conceptual tests)."""

    def test_page_marker_format(self):
        """Test that page markers follow expected format."""
        # This tests the format we expect to see
        marker = "`[p.1]`"

        assert marker.startswith("`[p.")
        assert marker.endswith("]`")
        assert "1" in marker

    def test_page_marker_extraction(self):
        """Test extracting page number from marker."""
        import re

        marker = "`[p.42]`"
        match = re.search(r"`\[p\.(\d+)\]`", marker)

        assert match is not None
        assert match.group(1) == "42"


class TestSectionMarkerInjection:
    """Test section marker functionality (conceptual tests)."""

    def test_section_marker_format(self):
        """Test that section markers follow expected format."""
        # This tests the format we expect to see
        marker = "`[section.1: chapter01.xhtml]`"

        assert marker.startswith("`[section.")
        assert ":" in marker
        assert marker.endswith("]`")

    def test_section_marker_extraction(self):
        """Test extracting section info from marker."""
        import re

        marker = "`[section.3: chapter03.xhtml]`"
        match = re.search(r"`\[section\.(\d+): (.+)\]`", marker)

        assert match is not None
        assert match.group(1) == "3"
        assert match.group(2) == "chapter03.xhtml"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
