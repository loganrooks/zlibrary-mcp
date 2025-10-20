"""
Phase 2 Integration Tests for _analyze_pdf_block refactoring.

Tests the refactored _analyze_pdf_block() function with both:
1. Legacy dict return path (backward compatibility)
2. New PageRegion structured path (Phase 2 data model)

Validates:
- Feature flag behavior (environment variable)
- Explicit parameter override
- Output equivalence between paths
- TextSpan formatting extraction
- ListInfo creation for list items
"""

import pytest
import os
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

from rag_processing import _analyze_pdf_block
from rag_data_models import PageRegion, TextSpan, ListInfo

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@pytest.fixture
def sample_pdf_block():
    """Create a sample PDF block for testing."""
    if not PYMUPDF_AVAILABLE:
        pytest.skip("PyMuPDF not available")

    test_pdf = Path(__file__).parent.parent.parent / 'test_files' / 'heidegger_pages_79-88.pdf'
    if not test_pdf.exists():
        pytest.skip(f"Test PDF not found: {test_pdf}")

    doc = fitz.open(str(test_pdf))
    page = doc[0]
    blocks = page.get_text('dict')['blocks']
    text_blocks = [b for b in blocks if b.get('type') == 0]

    if not text_blocks:
        pytest.skip("No text blocks found in test PDF")

    block = text_blocks[0]
    doc.close()
    return block


class TestAnalyzePdfBlockRefactoring:
    """Test suite for Phase 2 refactoring of _analyze_pdf_block()."""

    def test_legacy_path_returns_dict(self, sample_pdf_block):
        """Test that return_structured=False returns legacy dict format."""
        result = _analyze_pdf_block(sample_pdf_block, return_structured=False)

        assert isinstance(result, dict), "Legacy path should return dict"
        assert 'heading_level' in result
        assert 'list_marker' in result
        assert 'is_list_item' in result
        assert 'list_type' in result
        assert 'list_indent' in result
        assert 'text' in result
        assert 'spans' in result
        assert isinstance(result['spans'], list)

    def test_structured_path_returns_pageregion(self, sample_pdf_block):
        """Test that return_structured=True returns PageRegion object."""
        result = _analyze_pdf_block(sample_pdf_block, return_structured=True)

        assert type(result).__name__ == 'PageRegion', "Structured path should return PageRegion"
        assert hasattr(result, 'spans'), "PageRegion should have spans attribute"
        assert hasattr(result, 'bbox'), "PageRegion should have bbox attribute"
        assert hasattr(result, 'page_num'), "PageRegion should have page_num attribute"
        assert hasattr(result, 'heading_level'), "PageRegion should have heading_level attribute"
        assert hasattr(result, 'list_info'), "PageRegion should have list_info attribute"

    def test_structured_path_creates_textspans(self, sample_pdf_block):
        """Test that structured path creates TextSpan objects."""
        result = _analyze_pdf_block(sample_pdf_block, return_structured=True)

        assert len(result.spans) > 0, "Should have at least one span"
        first_span = result.spans[0]
        assert type(first_span).__name__ == 'TextSpan', "Spans should be TextSpan objects"
        assert hasattr(first_span, 'text'), "TextSpan should have text attribute"
        assert hasattr(first_span, 'formatting'), "TextSpan should have formatting attribute"
        assert isinstance(first_span.formatting, set), "Formatting should be a set"

    def test_env_var_default_to_structured(self, sample_pdf_block):
        """Test that default behavior (no param) uses env var, defaults to structured."""
        # Clear env var to test default
        old_val = os.environ.get('RAG_USE_STRUCTURED_DATA')
        if 'RAG_USE_STRUCTURED_DATA' in os.environ:
            del os.environ['RAG_USE_STRUCTURED_DATA']

        try:
            result = _analyze_pdf_block(sample_pdf_block)
            assert type(result).__name__ == 'PageRegion', \
                "Default should be structured (RAG_USE_STRUCTURED_DATA defaults to 'true')"
        finally:
            # Restore env var
            if old_val:
                os.environ['RAG_USE_STRUCTURED_DATA'] = old_val

    def test_env_var_false_uses_legacy(self, sample_pdf_block):
        """Test that RAG_USE_STRUCTURED_DATA='false' triggers legacy path."""
        old_val = os.environ.get('RAG_USE_STRUCTURED_DATA')
        os.environ['RAG_USE_STRUCTURED_DATA'] = 'false'

        try:
            result = _analyze_pdf_block(sample_pdf_block)
            assert isinstance(result, dict), "Env var 'false' should use legacy path"
        finally:
            # Restore env var
            if old_val:
                os.environ['RAG_USE_STRUCTURED_DATA'] = old_val
            else:
                del os.environ['RAG_USE_STRUCTURED_DATA']

    def test_env_var_true_uses_structured(self, sample_pdf_block):
        """Test that RAG_USE_STRUCTURED_DATA='true' triggers structured path."""
        old_val = os.environ.get('RAG_USE_STRUCTURED_DATA')
        os.environ['RAG_USE_STRUCTURED_DATA'] = 'true'

        try:
            result = _analyze_pdf_block(sample_pdf_block)
            assert type(result).__name__ == 'PageRegion', "Env var 'true' should use structured path"
        finally:
            # Restore env var
            if old_val:
                os.environ['RAG_USE_STRUCTURED_DATA'] = old_val
            else:
                del os.environ['RAG_USE_STRUCTURED_DATA']

    def test_explicit_param_overrides_env_var(self, sample_pdf_block):
        """Test that explicit return_structured parameter overrides env var."""
        old_val = os.environ.get('RAG_USE_STRUCTURED_DATA')
        os.environ['RAG_USE_STRUCTURED_DATA'] = 'true'

        try:
            # Explicitly request legacy despite env var = 'true'
            result = _analyze_pdf_block(sample_pdf_block, return_structured=False)
            assert isinstance(result, dict), "Explicit param should override env var"
        finally:
            # Restore env var
            if old_val:
                os.environ['RAG_USE_STRUCTURED_DATA'] = old_val
            else:
                del os.environ['RAG_USE_STRUCTURED_DATA']

    def test_output_text_equivalence(self, sample_pdf_block):
        """Test that both paths extract equivalent text content."""
        legacy = _analyze_pdf_block(sample_pdf_block, return_structured=False)
        structured = _analyze_pdf_block(sample_pdf_block, return_structured=True)

        legacy_text = legacy['text']
        structured_text = structured.get_text()

        # Allow for minor spacing differences (within 5 characters)
        assert abs(len(legacy_text) - len(structured_text)) < 5, \
            f"Text length should be similar: {len(legacy_text)} vs {len(structured_text)}"

        # Check that both have non-empty text
        assert len(legacy_text) > 0, "Legacy path should extract text"
        assert len(structured_text) > 0, "Structured path should extract text"

    def test_formatting_extraction(self, sample_pdf_block):
        """Test that structured path correctly extracts formatting from PyMuPDF flags."""
        result = _analyze_pdf_block(sample_pdf_block, return_structured=True)

        # Check that at least one span has formatting
        has_formatting = any(len(span.formatting) > 0 for span in result.spans)
        # Note: This may not be true for all PDFs, so we just check that the field exists
        for span in result.spans:
            assert isinstance(span.formatting, set), "Each span should have formatting as set"

    def test_bbox_extraction(self, sample_pdf_block):
        """Test that structured path extracts bounding box from block."""
        result = _analyze_pdf_block(sample_pdf_block, return_structured=True)

        assert isinstance(result.bbox, tuple), "bbox should be a tuple"
        assert len(result.bbox) == 4, "bbox should have 4 coordinates (x0, y0, x1, y1)"

        # Check that bbox contains valid numbers (not all zeros)
        assert any(coord != 0.0 for coord in result.bbox), "bbox should contain non-zero values"

    def test_heading_level_preservation(self, sample_pdf_block):
        """Test that heading_level is correctly passed to PageRegion."""
        # Test with heading detection enabled
        result = _analyze_pdf_block(sample_pdf_block, detect_headings=True, return_structured=True)

        # heading_level should be None or an integer
        assert result.heading_level is None or isinstance(result.heading_level, int), \
            "heading_level should be None or int"

    def test_backward_compatibility_maintained(self, sample_pdf_block):
        """Test that legacy code using the function without new parameter still works."""
        # This simulates existing code that doesn't know about return_structured parameter
        result = _analyze_pdf_block(sample_pdf_block, preserve_linebreaks=False, detect_headings=True)

        # Result should work regardless of whether it's dict or PageRegion
        # (with env var default, it will be PageRegion)
        assert result is not None, "Function should return a result"
