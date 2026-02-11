"""
Tests for OCR quality validation to prevent false positive marker detection.

This test suite validates the OCR corruption detection system that prevents
false positives from corrupted text containing tilde characters and other
OCR artifacts.
"""

import pytest
import sys
import os

# Add lib directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from rag_processing import _is_ocr_corrupted

pytestmark = pytest.mark.unit


class TestOCRCorruptionDetection:
    """Test OCR corruption detection to prevent false positives."""

    def test_tilde_corruption_simple(self):
        """Test that simple tilde corruption is detected."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("the~")
        assert is_corrupted is True
        assert confidence >= 0.90
        assert reason == "tilde_corruption"

    def test_tilde_corruption_with_special_chars(self):
        """Test tilde with additional special characters."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("of~·")
        assert is_corrupted is True
        assert confidence >= 0.90
        assert reason == "tilde_corruption"

    def test_tilde_corruption_in_word(self):
        """Test tilde embedded in word."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("r:~sentially")
        assert is_corrupted is True
        assert confidence >= 0.90
        assert reason == "tilde_corruption"

    def test_severe_corruption_multiple_special(self):
        """Test severe corruption with multiple special characters."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("cnt.i,ic~")
        assert is_corrupted is True
        # Should be detected by tilde OR excessive special chars
        assert confidence >= 0.85
        assert reason in ["tilde_corruption", "excessive_special_chars"]

    def test_excessive_special_chars_short_text(self):
        """Test excessive special characters in short text."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("a.b,c:")
        assert is_corrupted is True
        assert confidence >= 0.85
        assert reason == "excessive_special_chars"

    def test_mixed_corruption_pattern(self):
        """Test letter-punctuation-letter corruption pattern."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("a.b")
        assert is_corrupted is True
        assert confidence >= 0.80
        assert reason in ["mixed_corruption", "excessive_special_chars"]

    def test_clean_marker_numeric(self):
        """Test clean numeric marker is not flagged."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("1")
        assert is_corrupted is False
        assert confidence >= 0.85
        assert reason == "clean_text"

    def test_clean_marker_symbol(self):
        """Test clean symbol markers are not flagged."""
        for symbol in ["*", "†", "‡", "§", "¶"]:
            is_corrupted, confidence, reason = _is_ocr_corrupted(symbol)
            assert is_corrupted is False, (
                f"Symbol {symbol} should not be flagged as corrupted"
            )
            assert confidence >= 0.85
            assert reason == "clean_text"

    def test_clean_marker_letter(self):
        """Test clean single letter marker is not flagged."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("a")
        assert is_corrupted is False
        assert confidence >= 0.85
        assert reason == "clean_text"

    def test_clean_marker_word(self):
        """Test clean word is not flagged."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("text")
        assert is_corrupted is False
        assert confidence >= 0.85
        assert reason == "clean_text"

    def test_clean_marker_multi_digit(self):
        """Test clean multi-digit marker is not flagged."""
        is_corrupted, confidence, reason = _is_ocr_corrupted("123")
        assert is_corrupted is False
        assert confidence >= 0.85
        assert reason == "clean_text"

    def test_heidegger_false_positives(self):
        """Test actual false positives from Heidegger PDF."""
        false_positives = [
            "the~",
            "h",  # Single letter in corrupted context
            "of~·",
            "r:~sentially",
            "cnt.i,ic~",
            "advan~;e.",
        ]

        corrupted_count = 0
        for text in false_positives:
            is_corrupted, confidence, reason = _is_ocr_corrupted(text)
            if is_corrupted:
                corrupted_count += 1
                print(
                    f"✓ Correctly flagged '{text}' as corrupted ({reason}, conf: {confidence:.2f})"
                )
            else:
                print(f"✗ Failed to flag '{text}' as corrupted")

        # Should detect at least 5 out of 6 (83%+)
        detection_rate = corrupted_count / len(false_positives)
        assert detection_rate >= 0.80, (
            f"Should detect at least 80% of corruptions, got {detection_rate:.0%}"
        )

    def test_valid_markers_not_flagged(self):
        """Test that valid markers are not incorrectly flagged as corrupted."""
        valid_markers = ["1", "2", "*", "†", "a", "b", "i", "ii"]

        for marker in valid_markers:
            is_corrupted, confidence, reason = _is_ocr_corrupted(marker)
            assert is_corrupted is False, (
                f"Valid marker '{marker}' should not be flagged as corrupted"
            )

    def test_single_invalid_char_rejection(self):
        """Test that single invalid characters are rejected."""
        # These are single characters that are not valid markers
        invalid_chars = ["~", ":", ";", ",", "."]

        for char in invalid_chars:
            is_corrupted, confidence, reason = _is_ocr_corrupted(char)
            assert is_corrupted is True, (
                f"Invalid char '{char}' should be flagged as corrupted"
            )
            assert reason in ["tilde_corruption", "invalid_single_char"]

    def test_boundary_conditions(self):
        """Test boundary conditions for special character counting."""
        # Text with letter-punct-letter pattern will trigger mixed_corruption
        is_corrupted, _, reason = _is_ocr_corrupted("abc.def,g")
        assert is_corrupted is True  # Detected by mixed_corruption pattern
        assert reason == "mixed_corruption"

        # Just over threshold (3 special chars in 9 chars)
        is_corrupted, _, _ = _is_ocr_corrupted("a.b,c:def")
        assert is_corrupted is True  # 3 special chars in 9 chars is too much

        # Clean case: no letter-punct-letter pattern
        is_corrupted, _, _ = _is_ocr_corrupted("abc123def")
        assert is_corrupted is False  # No corruption patterns

    def test_longer_text_tolerance(self):
        """Test that longer text with some special chars is not flagged."""
        # Longer text can have more special characters
        is_corrupted, _, _ = _is_ocr_corrupted("This is a sentence, with punctuation.")
        assert is_corrupted is False  # Normal sentence should be clean


class TestOCRQualityIntegration:
    """Test OCR quality integration with marker detection."""

    @pytest.fixture
    def heidegger_pdf_path(self):
        """Path to Heidegger test PDF."""
        return "test_files/heidegger_pages_22-23_primary_footnote_test.pdf"

    def test_heidegger_false_positive_reduction(self, heidegger_pdf_path):
        """
        Test that OCR quality filter reduces false positives in Heidegger PDF.

        Expected behavior:
        - Before fix: ~25 markers detected (21 false positives = 87.5% FP rate)
        - After fix: 3-5 markers detected (<2 false positives = <5% FP rate)
        """
        import fitz
        from rag_processing import _detect_footnotes_in_page

        doc = fitz.open(heidegger_pdf_path)
        page = doc[0]
        result = _detect_footnotes_in_page(page, 0)

        total_markers = len(result["markers"])

        print("\n=== Marker Detection Results ===")
        print(f"Total markers detected: {total_markers}")

        # Count markers with corruption indicators
        corrupted_markers = []
        clean_markers = []

        for marker in result["markers"]:
            marker_text = marker["marker"]
            is_corrupted, conf, reason = _is_ocr_corrupted(marker_text)

            if is_corrupted:
                corrupted_markers.append(
                    {"text": marker_text, "reason": reason, "confidence": conf}
                )
            else:
                clean_markers.append(marker_text)

        print(f"Clean markers: {len(clean_markers)} - {clean_markers}")
        print(f"Corrupted markers detected: {len(corrupted_markers)}")
        for cm in corrupted_markers[:5]:
            print(f"  - '{cm['text']}' ({cm['reason']}, conf: {cm['confidence']:.2f})")

        # After fix, should have:
        # - Total markers < 10 (was ~25)
        # - Clean markers should be majority (>50%)
        # - False positive rate < 20% (was 87.5%)

        assert total_markers < 15, (
            f"Should detect <15 markers after OCR filter, got {total_markers}"
        )

        # Note: This test will initially fail until integration is complete
        # Once integrated, clean_markers should dominate


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
