"""
Test suite for hybrid ToC extraction system.

Tests:
1. _analyze_font_distribution: Font size analysis and body text detection
2. _detect_headings_from_fonts: Font-based heading detection
3. _extract_toc_from_pdf: Hybrid ToC extraction (embedded + font-based)
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Import functions under test
from rag_processing import (
    _analyze_font_distribution,
    _detect_headings_from_fonts,
    _extract_toc_from_pdf
)


@pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="PyMuPDF not available")
class TestAnalyzeFontDistribution:
    """Test font size distribution analysis for body text detection."""

    def test_font_distribution_basic(self):
        """Test font distribution with mock document."""
        # Create mock document with 5 pages
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 5

        # Mock page with text blocks
        mock_page = MagicMock()
        mock_blocks = [
            {
                "type": 0,  # Text block
                "lines": [
                    {
                        "spans": [
                            {"size": 10.0, "text": "Body text paragraph"},
                            {"size": 10.0, "text": "More body text"},
                        ]
                    },
                    {
                        "spans": [
                            {"size": 10.5, "text": "Another paragraph"},
                            {"size": 16.0, "text": "Heading"},  # Outlier
                        ]
                    }
                ]
            }
        ]
        mock_page.get_text.return_value = {"blocks": mock_blocks}
        mock_doc.__getitem__.return_value = mock_page

        # Test
        body_size = _analyze_font_distribution(mock_doc, sample_pages=5)

        # Should return 10.0 (most common size)
        assert body_size == 10.0

    def test_font_distribution_no_text(self):
        """Test behavior with document containing no text."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_page.get_text.return_value = {"blocks": []}
        mock_doc.__getitem__.return_value = mock_page

        # Should return default 10.0
        body_size = _analyze_font_distribution(mock_doc)
        assert body_size == 10.0

    def test_font_distribution_sampling(self):
        """Test page sampling for large documents."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 100  # Large document

        mock_page = MagicMock()
        mock_blocks = [
            {
                "type": 0,
                "lines": [{"spans": [{"size": 12.0, "text": "Sample text"}]}]
            }
        ]
        mock_page.get_text.return_value = {"blocks": mock_blocks}
        mock_doc.__getitem__.return_value = mock_page

        # Should sample only 10 pages (default)
        body_size = _analyze_font_distribution(mock_doc)

        # Verify sampling occurred (not all 100 pages accessed)
        assert mock_doc.__getitem__.call_count == 10
        assert body_size == 12.0


@pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="PyMuPDF not available")
class TestDetectHeadingsFromFonts:
    """Test font-based heading detection."""

    def test_detect_headings_basic(self):
        """Test basic heading detection with size thresholds."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 2

        # Page 1: Body text + H1 heading
        mock_page1 = MagicMock()
        mock_blocks1 = [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {"size": 20.0, "text": "Chapter Title", "flags": 2},  # Large + bold
                        ]
                    },
                    {
                        "spans": [
                            {"size": 10.0, "text": "Body text here", "flags": 0},
                        ]
                    }
                ]
            }
        ]
        mock_page1.get_text.return_value = {"blocks": mock_blocks1}

        # Page 2: Body text + H2 heading
        mock_page2 = MagicMock()
        mock_blocks2 = [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {"size": 15.0, "text": "Section Heading", "flags": 2},  # Medium + bold
                        ]
                    }
                ]
            }
        ]
        mock_page2.get_text.return_value = {"blocks": mock_blocks2}

        mock_doc.__getitem__.side_effect = [mock_page1, mock_page2]

        # Test with body_size=10.0, threshold=1.15
        toc_map = _detect_headings_from_fonts(mock_doc, body_size=10.0, threshold=1.15)

        # Should detect both headings
        assert 1 in toc_map
        assert 2 in toc_map
        assert len(toc_map[1]) == 1
        assert len(toc_map[2]) == 1
        assert toc_map[1][0][1] == "Chapter Title"
        assert toc_map[2][0][1] == "Section Heading"

    def test_detect_headings_false_positive_filters(self):
        """Test false positive filtering (page numbers, short text, etc.)."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        mock_blocks = [
            {
                "type": 0,
                "lines": [
                    {"spans": [{"size": 15.0, "text": "42", "flags": 0}]},  # Pure number
                    {"spans": [{"size": 15.0, "text": "xii", "flags": 0}]},  # Roman numeral
                    {"spans": [{"size": 15.0, "text": "A", "flags": 0}]},  # Single char
                    {"spans": [{"size": 15.0, "text": "1.2.3", "flags": 0}]},  # Mostly punctuation
                    {"spans": [{"size": 15.0, "text": "Valid Heading", "flags": 2}]},  # Should pass
                ]
            }
        ]
        mock_page.get_text.return_value = {"blocks": mock_blocks}
        mock_doc.__getitem__.return_value = mock_page

        toc_map = _detect_headings_from_fonts(mock_doc, body_size=10.0)

        # Should only detect "Valid Heading"
        assert len(toc_map) == 1
        assert len(toc_map[1]) == 1
        assert toc_map[1][0][1] == "Valid Heading"

    def test_detect_headings_level_hierarchy(self):
        """Test heading level assignment based on size ratios."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1

        mock_page = MagicMock()
        body_size = 10.0
        mock_blocks = [
            {
                "type": 0,
                "lines": [
                    {"spans": [{"size": 20.0, "text": "Level 1", "flags": 2}]},  # 2.0x = H1
                    {"spans": [{"size": 16.0, "text": "Level 2", "flags": 2}]},  # 1.6x = H2
                    {"spans": [{"size": 13.0, "text": "Level 3", "flags": 2}]},  # 1.3x = H2 (bold)
                    {"spans": [{"size": 12.0, "text": "Level 4", "flags": 0}]},  # 1.2x = H4 (not bold)
                ]
            }
        ]
        mock_page.get_text.return_value = {"blocks": mock_blocks}
        mock_doc.__getitem__.return_value = mock_page

        toc_map = _detect_headings_from_fonts(mock_doc, body_size=body_size)

        # Check levels
        assert len(toc_map[1]) == 4
        levels = [heading[0] for heading in toc_map[1]]
        assert levels == [1, 2, 2, 4]


@pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="PyMuPDF not available")
class TestExtractTocFromPdf:
    """Test hybrid ToC extraction (embedded + font-based)."""

    def test_extract_toc_embedded_success(self):
        """Test extraction with embedded ToC metadata."""
        mock_doc = MagicMock()

        # Mock embedded ToC
        embedded_toc = [
            [1, "Chapter 1", 1],
            [2, "Section 1.1", 2],
            [1, "Chapter 2", 5],
        ]
        mock_doc.get_toc.return_value = embedded_toc

        toc_map = _extract_toc_from_pdf(mock_doc)

        # Should use embedded ToC
        assert len(toc_map) == 3
        assert toc_map[1] == [(1, "Chapter 1")]
        assert toc_map[2] == [(2, "Section 1.1")]
        assert toc_map[5] == [(1, "Chapter 2")]

    def test_extract_toc_fallback_to_font_based(self):
        """Test fallback to font-based when embedded ToC is empty."""
        mock_doc = MagicMock()
        mock_doc.get_toc.return_value = []  # Empty embedded ToC
        mock_doc.__len__.return_value = 1

        # Mock font analysis - needs both body text and heading for sampling
        mock_page = MagicMock()

        # First call is for font distribution analysis, second is for heading detection
        mock_blocks_analysis = [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {"size": 10.0, "text": "Body text for analysis", "flags": 0}
                        ]
                    }
                ]
            }
        ]

        mock_blocks_headings = [
            {
                "type": 0,
                "lines": [
                    {
                        "spans": [
                            {"size": 10.0, "text": "Body text", "flags": 0},
                            {"size": 16.0, "text": "Font-Based Heading", "flags": 2}
                        ]
                    }
                ]
            }
        ]

        # Return different blocks for analysis vs detection phases
        mock_page.get_text.side_effect = [
            {"blocks": mock_blocks_analysis},  # Font distribution analysis
            {"blocks": mock_blocks_headings}    # Heading detection
        ]
        mock_doc.__getitem__.return_value = mock_page

        toc_map = _extract_toc_from_pdf(mock_doc)

        # Should fall back to font-based detection
        assert len(toc_map) == 1
        assert toc_map[1][0][1] == "Font-Based Heading"

    def test_extract_toc_no_toc_available(self):
        """Test behavior when no ToC is available."""
        mock_doc = MagicMock()
        mock_doc.get_toc.return_value = []
        mock_doc.__len__.return_value = 1

        # Mock page with only body text (no headings)
        mock_page = MagicMock()
        mock_blocks = [
            {
                "type": 0,
                "lines": [{"spans": [{"size": 10.0, "text": "Only body text", "flags": 0}]}]
            }
        ]
        mock_page.get_text.return_value = {"blocks": mock_blocks}
        mock_doc.__getitem__.return_value = mock_page

        toc_map = _extract_toc_from_pdf(mock_doc)

        # Should return empty dict
        assert toc_map == {}

    def test_extract_toc_exception_handling(self):
        """Test exception handling in both phases."""
        mock_doc = MagicMock()
        mock_doc.get_toc.side_effect = Exception("ToC read error")
        mock_doc.__len__.return_value = 1

        # Mock successful font-based fallback
        mock_page = MagicMock()

        # Need blocks for both font analysis and heading detection
        mock_blocks_analysis = [
            {
                "type": 0,
                "lines": [{"spans": [{"size": 10.0, "text": "Body text sample", "flags": 0}]}]
            }
        ]

        mock_blocks_headings = [
            {
                "type": 0,
                "lines": [
                    {"spans": [{"size": 10.0, "text": "Body text", "flags": 0}]},
                    {"spans": [{"size": 15.0, "text": "Fallback Heading", "flags": 2}]}
                ]
            }
        ]

        mock_page.get_text.side_effect = [
            {"blocks": mock_blocks_analysis},  # Font distribution analysis
            {"blocks": mock_blocks_headings}    # Heading detection
        ]
        mock_doc.__getitem__.return_value = mock_page

        toc_map = _extract_toc_from_pdf(mock_doc)

        # Should gracefully fall back to font-based
        assert len(toc_map) == 1
        assert toc_map[1][0][1] == "Fallback Heading"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
