"""
Unit tests for superscript marker detection in footnote processing.

Tests the _is_superscript() and _calculate_page_normal_font_size() functions
that enable detection of superscript footnote markers in PDFs.

Test Coverage:
1. Font size calculation (median, outliers, empty pages)
2. Superscript detection (flag-based, size-based, combined)
3. False positive prevention (normal text, small text)
4. Real-world PDF validation (Kant numeric markers)
"""

import pytest
import sys
from pathlib import Path

# Add lib to path for importing rag_processing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from rag_processing import _is_superscript, _calculate_page_normal_font_size


class TestFontSizeCalculation:
    """Test normal font size calculation for pages."""

    def test_median_calculation_odd_count(self):
        """Calculate median with odd number of spans."""
        blocks = [
            {
                'type': 0,
                'lines': [
                    {
                        'spans': [
                            {'size': 9.0},
                            {'size': 10.0},
                            {'size': 11.0},
                        ]
                    }
                ]
            }
        ]

        result = _calculate_page_normal_font_size(blocks)
        assert result == 10.0, "Median of [9, 10, 11] should be 10.0"

    def test_median_calculation_even_count(self):
        """Calculate median with even number of spans."""
        blocks = [
            {
                'type': 0,
                'lines': [
                    {
                        'spans': [
                            {'size': 9.0},
                            {'size': 10.0},
                            {'size': 11.0},
                            {'size': 12.0},
                        ]
                    }
                ]
            }
        ]

        result = _calculate_page_normal_font_size(blocks)
        assert result == 10.5, "Median of [9, 10, 11, 12] should be 10.5"

    def test_mixed_text_types(self):
        """Calculate font size with headers, body, and footnotes."""
        blocks = [
            {
                'type': 0,
                'lines': [
                    {'spans': [{'size': 18.0}]},  # Header
                    {'spans': [{'size': 9.0}]},   # Body
                    {'spans': [{'size': 9.0}]},   # Body
                    {'spans': [{'size': 9.0}]},   # Body
                    {'spans': [{'size': 6.0}]},   # Footnote
                ]
            }
        ]

        result = _calculate_page_normal_font_size(blocks)
        # Median of [6, 9, 9, 9, 18] = 9.0
        assert result == 9.0, "Median should ignore outliers (header 18pt, footnote 6pt)"

    def test_empty_page(self):
        """Handle empty page gracefully."""
        blocks = []
        result = _calculate_page_normal_font_size(blocks)
        assert result == 10.0, "Empty page should return default 10.0pt"

    def test_non_text_blocks(self):
        """Skip non-text blocks (images, etc.)."""
        blocks = [
            {'type': 1},  # Image block
            {
                'type': 0,
                'lines': [
                    {'spans': [{'size': 9.0}]}
                ]
            }
        ]

        result = _calculate_page_normal_font_size(blocks)
        assert result == 9.0, "Should skip non-text blocks"


class TestSuperscriptDetection:
    """Test superscript span detection."""

    def test_flag_based_detection(self):
        """Detect superscript via PyMuPDF flag (bit 0)."""
        span = {
            'size': 6.0,
            'flags': 1,  # Bit 0 set = superscript
        }
        normal_size = 10.0

        assert _is_superscript(span, normal_size) is True, \
            "Flag=1 (bit 0 set) should be detected as superscript"

    def test_flag_with_validation(self):
        """Detect superscript with flag + size validation."""
        span = {
            'size': 6.0,  # 60% of normal (matches superscript)
            'flags': 5,   # Bits 0 and 2 set (real Kant PDF data)
        }
        normal_size = 10.0

        assert _is_superscript(span, normal_size) is True, \
            "Superscript flag with correct size should be detected"

    def test_size_based_fallback(self):
        """Detect superscript via size when flag is missing."""
        span = {
            'size': 6.5,  # 65% of normal (clearly superscript size)
            'flags': 0,   # No flag set
        }
        normal_size = 10.0

        assert _is_superscript(span, normal_size) is True, \
            "Very small text (<75% of normal) should be detected as superscript"

    def test_normal_text_not_superscript(self):
        """Normal text should not be detected as superscript."""
        span = {
            'size': 10.0,  # Same as normal
            'flags': 0,
        }
        normal_size = 10.0

        assert _is_superscript(span, normal_size) is False, \
            "Normal sized text without flag should not be superscript"

    def test_slightly_smaller_text_rejected(self):
        """Slightly smaller text (80-90%) should not be superscript."""
        span = {
            'size': 8.5,  # 85% of normal (too large for superscript)
            'flags': 0,
        }
        normal_size = 10.0

        assert _is_superscript(span, normal_size) is False, \
            "Text >75% of normal without flag is not superscript"

    def test_too_small_text_rejected(self):
        """Very small text (<50%) might be subscript or corruption."""
        span = {
            'size': 4.0,  # 40% of normal (too small)
            'flags': 0,
        }
        normal_size = 10.0

        assert _is_superscript(span, normal_size) is False, \
            "Text <50% of normal without flag might be subscript/corruption"

    def test_kant_pdf_realistic_data(self):
        """Test with actual Kant PDF superscript data."""
        # Real data from test_files/kant_critique_pages_80_85.pdf
        # Normal text: 9.24pt, flags=4
        # Superscript: 5.83pt, flags=5
        span = {
            'size': 5.83,
            'flags': 5,  # Bits 0 and 2 set
        }
        normal_size = 9.24

        assert _is_superscript(span, normal_size) is True, \
            "Real Kant PDF superscript should be detected"

        # Verify size ratio
        size_ratio = 5.83 / 9.24
        assert 0.60 < size_ratio < 0.65, \
            f"Kant superscript size ratio should be ~63%, got {size_ratio:.2%}"

    def test_page_number_not_superscript(self):
        """Page numbers (normal sized digits) should not be superscript."""
        # Real data from Kant PDF page number "63"
        span = {
            'size': 9.0,
            'flags': 4,  # No superscript flag
        }
        normal_size = 9.24

        assert _is_superscript(span, normal_size) is False, \
            "Page numbers should not be detected as superscript"

    def test_flag_error_with_normal_size(self):
        """Flag set but normal size - trust flag anyway."""
        span = {
            'size': 10.0,  # Same as normal
            'flags': 1,    # Superscript flag set
        }
        normal_size = 10.0

        # Decision: Trust PyMuPDF flag even if size doesn't match
        assert _is_superscript(span, normal_size) is True, \
            "Trust superscript flag even with normal size (PDF encoding issue)"


class TestSuperscriptIntegration:
    """Integration tests with real PDFs."""

    def test_kant_pdf_marker_detection(self):
        """Verify superscript markers detected in Kant PDF."""
        import fitz
        from rag_processing import _detect_footnotes_in_page

        # Open test PDF with known superscript markers
        pdf_path = Path(__file__).parent.parent.parent / "test_files" / "kant_critique_pages_80_85.pdf"

        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        page = doc[0]

        # Detect footnotes
        result = _detect_footnotes_in_page(page, 0)

        # Should find numeric markers (2, 3, etc.)
        markers = result.get('markers', [])
        numeric_markers = [m for m in markers if m.get('type') == 'numeric']

        assert len(numeric_markers) > 0, \
            "Should detect numeric markers in Kant PDF"

        # Check that superscript markers are flagged
        superscript_markers = [m for m in markers if m.get('is_superscript')]

        assert len(superscript_markers) > 0, \
            "Should detect at least some markers as superscript"

        # Verify specific expected markers (from visual inspection)
        marker_texts = [m['marker'] for m in numeric_markers]
        assert '2' in marker_texts or '3' in marker_texts, \
            "Should detect markers 2 or 3 from Kant PDF"

        doc.close()

    def test_no_false_positives_body_text(self):
        """Ensure normal body text digits aren't marked as superscript."""
        import fitz
        from rag_processing import _calculate_page_normal_font_size, _is_superscript

        # Open test PDF
        pdf_path = Path(__file__).parent.parent.parent / "test_files" / "kant_critique_pages_80_85.pdf"

        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        page = doc[0]

        blocks = page.get_text("dict")["blocks"]
        normal_size = _calculate_page_normal_font_size(blocks)

        # Count superscript vs normal text spans
        superscript_count = 0
        normal_count = 0

        for block in blocks:
            if block.get('type') != 0:
                continue

            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    if _is_superscript(span, normal_size):
                        superscript_count += 1
                    else:
                        normal_count += 1

        # Most text should be normal (>90%)
        total = superscript_count + normal_count
        normal_ratio = normal_count / total if total > 0 else 0

        assert normal_ratio > 0.90, \
            f"Most text should be normal, got {normal_ratio:.1%} normal vs {superscript_count} superscript"

        doc.close()


class TestPerformance:
    """Test performance characteristics."""

    def test_superscript_check_performance(self):
        """Verify superscript check is fast (<0.1ms per span)."""
        import time

        span = {
            'size': 6.0,
            'flags': 1,
        }
        normal_size = 10.0

        # Warmup
        for _ in range(100):
            _is_superscript(span, normal_size)

        # Time 10000 checks
        start = time.perf_counter()
        for _ in range(10000):
            _is_superscript(span, normal_size)
        elapsed = time.perf_counter() - start

        # Should be <1ms total for 10k checks (<0.1μs per check)
        assert elapsed < 0.010, \
            f"10k superscript checks should be <10ms, got {elapsed*1000:.2f}ms"

    def test_font_size_calculation_performance(self):
        """Verify font size calculation is fast (<1ms per page)."""
        import time

        # Create realistic page with 100 spans
        blocks = [
            {
                'type': 0,
                'lines': [
                    {
                        'spans': [
                            {'size': 9.0 + (i % 3)}
                            for i in range(100)
                        ]
                    }
                ]
            }
        ]

        # Warmup
        for _ in range(10):
            _calculate_page_normal_font_size(blocks)

        # Time 1000 calculations
        start = time.perf_counter()
        for _ in range(1000):
            _calculate_page_normal_font_size(blocks)
        elapsed = time.perf_counter() - start

        # Should be <1ms per call
        per_call = elapsed / 1000
        assert per_call < 0.001, \
            f"Font size calculation should be <1ms, got {per_call*1000:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
