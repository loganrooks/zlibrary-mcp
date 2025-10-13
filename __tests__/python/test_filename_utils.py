"""
Unit tests for filename_utils.py

Tests unified filename generation, slugification, and author extraction.
"""

import pytest
import sys
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

from filename_utils import (
    slugify,
    extract_author_lastname,
    create_unified_filename,
    create_metadata_filename,
    parse_filename
)


class TestSlugify:
    """Test slugification function."""

    def test_basic_slugify(self):
        """Test basic string slugification."""
        assert slugify("The Burnout Society") == "the-burnout-society"
        assert slugify("L'Être et le Néant") == "l-etre-et-le-neant"

    def test_slugify_with_special_chars(self):
        """Test slugification with special characters."""
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("Test: A Study") == "test-a-study"
        assert slugify("Book #1") == "book-1"

    def test_slugify_multiple_spaces(self):
        """Test handling of multiple spaces."""
        assert slugify("Multiple   Spaces") == "multiple-spaces"
        assert slugify("  Leading and trailing  ") == "leading-and-trailing"

    def test_slugify_unicode(self):
        """Test Unicode handling."""
        assert slugify("Byung-Chul Han") == "byung-chul-han"
        assert slugify("José Saramago") == "jose-saramago"

    def test_slugify_empty_string(self):
        """Test empty string handling."""
        assert slugify("") == "unknown"
        assert slugify("   ") == "unknown"

    def test_slugify_max_length(self):
        """Test length limiting."""
        long_string = "a" * 100
        result = slugify(long_string, max_length=50)
        assert len(result) == 50
        assert result == "a" * 50


class TestExtractAuthorLastname:
    """Test author lastname extraction."""

    def test_extract_simple_name(self):
        """Test simple single-word names."""
        assert extract_author_lastname("Plato") == "plato"
        assert extract_author_lastname("Aristotle") == "aristotle"

    def test_extract_two_word_name(self):
        """Test two-word names."""
        assert extract_author_lastname("Byung-Chul Han") == "han"
        assert extract_author_lastname("Giorgio Agamben") == "agamben"

    def test_extract_comma_separated(self):
        """Test comma-separated format (Lastname, Firstname)."""
        assert extract_author_lastname("Han, Byung-Chul") == "han"
        assert extract_author_lastname("Agamben, Giorgio") == "agamben"

    def test_extract_hyphenated_lastname(self):
        """Test hyphenated last names."""
        assert extract_author_lastname("Jean-Luc Nancy") == "nancy"
        assert extract_author_lastname("Jean-François Lyotard") == "lyotard"

    def test_extract_empty_or_none(self):
        """Test empty/None author."""
        assert extract_author_lastname("") == "unknown-author"
        assert extract_author_lastname("   ") == "unknown-author"

    def test_extract_with_titles(self):
        """Test names with titles."""
        assert extract_author_lastname("Dr. Byung-Chul Han") == "han"


class TestCreateUnifiedFilename:
    """Test unified filename generation."""

    def test_basic_filename_generation(self):
        """Test basic filename generation."""
        book_details = {
            'author': 'Byung-Chul Han',
            'title': 'The Burnout Society',
            'id': '3505318',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details)
        assert result == "han-the-burnout-society-3505318.pdf"

    def test_filename_with_comma_author(self):
        """Test with comma-separated author."""
        book_details = {
            'author': 'Agamben, Giorgio',
            'title': 'The Coming Community',
            'id': '6035827',
            'extension': 'epub'
        }
        result = create_unified_filename(book_details)
        assert result == "agamben-the-coming-community-6035827.epub"

    def test_filename_missing_author(self):
        """Test with missing author."""
        book_details = {
            'title': 'Unknown Work',
            'id': '12345',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details)
        assert result == "unknown-author-unknown-work-12345.pdf"

    def test_filename_missing_title(self):
        """Test with missing title."""
        book_details = {
            'author': 'Test Author',
            'id': '12345',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details)
        assert result == "author-untitled-12345.pdf"

    def test_filename_with_special_chars(self):
        """Test with special characters in title."""
        book_details = {
            'author': 'Test Author',
            'title': 'Book: A Study (Part 1)',
            'id': '99999',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details)
        assert "book-a-study-part-1" in result
        assert result.endswith(".pdf")

    def test_filename_with_suffix(self):
        """Test with suffix parameter."""
        book_details = {
            'author': 'Test Author',
            'title': 'Test Book',
            'id': '123',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details, suffix='.processed.markdown')
        assert result.endswith('.processed.markdown')

    def test_filename_extension_override(self):
        """Test extension override."""
        book_details = {
            'author': 'Test Author',
            'title': 'Test Book',
            'id': '123',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details, extension='epub')
        assert result.endswith('.epub')

    def test_filename_length_truncation(self):
        """Test automatic length truncation."""
        book_details = {
            'author': 'A' * 100,
            'title': 'B' * 100,
            'id': '12345',
            'extension': 'pdf'
        }
        result = create_unified_filename(book_details, max_total_length=100)
        # Should truncate to fit within max_total_length + extension
        assert len(result) <= 110  # 100 + ".pdf" + some buffer


class TestCreateMetadataFilename:
    """Test metadata filename generation."""

    def test_metadata_from_original(self):
        """Test metadata filename from original."""
        original = "han-burnout-society-3505318.pdf"
        result = create_metadata_filename(original)
        assert result == "han-burnout-society-3505318.pdf.metadata.json"

    def test_metadata_from_processed(self):
        """Test metadata filename from processed file."""
        processed = "han-burnout-society-3505318.pdf.processed.markdown"
        result = create_metadata_filename(processed)
        # Should remove .processed.markdown
        assert result == "han-burnout-society-3505318.pdf.metadata.json"

    def test_metadata_with_path(self):
        """Test with full path."""
        full_path = "/downloads/han-burnout-society-3505318.pdf"
        result = create_metadata_filename(full_path)
        assert result == "han-burnout-society-3505318.pdf.metadata.json"


class TestParseFilename:
    """Test filename parsing."""

    def test_parse_basic_filename(self):
        """Test parsing basic filename."""
        filename = "han-burnout-society-3505318.pdf"
        result = parse_filename(filename)

        assert result['author_slug'] == 'han'
        assert result['title_slug'] == 'burnout-society'
        assert result['book_id'] == '3505318'
        assert result['extension'] == 'pdf'

    def test_parse_processed_filename(self):
        """Test parsing processed filename."""
        filename = "han-burnout-society-3505318.pdf.processed.markdown"
        result = parse_filename(filename)

        assert result['author_slug'] == 'han'
        assert result['title_slug'] == 'burnout-society'
        assert result['book_id'] == '3505318'
        assert result['extension'] == 'processed.markdown'

    def test_parse_with_path(self):
        """Test parsing with full path."""
        filename = "/downloads/agamben-community-6035827.epub"
        result = parse_filename(filename)

        assert result['author_slug'] == 'agamben'
        assert result['title_slug'] == 'community'
        assert result['book_id'] == '6035827'
        assert result['extension'] == 'epub'

    def test_parse_multi_word_title(self):
        """Test parsing multi-word title."""
        filename = "nancy-inoperative-community-1234567.pdf"
        result = parse_filename(filename)

        assert result['author_slug'] == 'nancy'
        assert result['title_slug'] == 'inoperative-community'
        assert result['book_id'] == '1234567'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
