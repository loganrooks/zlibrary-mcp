"""
Unit tests for metadata_generator.py

Tests YAML frontmatter generation, TOC extraction, and metadata sidecar creation.
"""

import pytest
import json
import tempfile
import sys
from pathlib import Path
from datetime import datetime

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'lib'))

from metadata_generator import (
    generate_yaml_frontmatter,
    _yaml_escape,
    extract_toc_from_content,
    extract_page_line_mapping,
    generate_metadata_sidecar,
    save_metadata_sidecar,
    add_yaml_frontmatter_to_content
)


class TestYAMLEscape:
    """Test YAML string escaping."""

    def test_escape_simple_string(self):
        """Test simple strings don't need escaping."""
        assert _yaml_escape("Simple Title") == "Simple Title"

    def test_escape_with_colon(self):
        """Test strings with colons are quoted."""
        result = _yaml_escape("Title: A Study")
        assert result.startswith('"')
        assert result.endswith('"')

    def test_escape_with_quotes(self):
        """Test strings with quotes are escaped."""
        result = _yaml_escape('Book "The Best"')
        assert '\\"' in result or result.startswith('"')


class TestGenerateYAMLFrontmatter:
    """Test YAML frontmatter generation."""

    def test_minimal_frontmatter(self):
        """Test minimal frontmatter with just title."""
        result = generate_yaml_frontmatter(title="Test Book")

        assert result.startswith("---")
        assert result.endswith("---\n")
        assert "title: Test Book" in result

    def test_complete_frontmatter(self):
        """Test complete frontmatter with all fields."""
        result = generate_yaml_frontmatter(
            title="The Burnout Society",
            author="Byung-Chul Han",
            translator="Erik Butler",
            publisher="Stanford University Press",
            year="2015",
            isbn="9780804795098",
            pages=117,
            format_type="pdf",
            ocr_quality=0.95,
            book_id="3505318"
        )

        assert "title: The Burnout Society" in result
        assert "author: Byung-Chul Han" in result
        assert "translator: Erik Butler" in result
        assert "publisher: Stanford University Press" in result
        assert "year: 2015" in result
        assert "isbn: 9780804795098" in result
        assert "pages: 117" in result
        assert "format: pdf" in result
        assert "ocr_quality: 0.95" in result
        assert "source_id: 3505318" in result

    def test_frontmatter_with_processing_date(self):
        """Test that processing date is included."""
        result = generate_yaml_frontmatter(title="Test")
        assert "processing_date:" in result

    def test_frontmatter_structure(self):
        """Test YAML structure is valid."""
        result = generate_yaml_frontmatter(title="Test Book", author="Test Author")

        lines = result.split('\n')
        assert lines[0] == "---"
        assert lines[-2] == "---"  # Second to last (last is empty)


class TestExtractTOCFromContent:
    """Test TOC extraction from content."""

    def test_extract_basic_toc(self):
        """Test extracting basic TOC from markdown."""
        content = """# Chapter 1
Some content here.

## Section 1.1
More content.

# Chapter 2
Final content.
"""
        toc = extract_toc_from_content(content, format_type="markdown")

        assert len(toc) == 3
        assert toc[0]['title'] == 'Chapter 1'
        assert toc[0]['level'] == 1
        assert toc[1]['title'] == 'Section 1.1'
        assert toc[1]['level'] == 2
        assert toc[2]['title'] == 'Chapter 2'
        assert toc[2]['level'] == 1

    def test_extract_toc_with_page_markers(self):
        """Test extracting TOC with page markers."""
        content = """`[p.1]`

# Chapter 1

`[p.5]`

## Section 1.1
"""
        toc = extract_toc_from_content(content, format_type="markdown")

        assert len(toc) == 2
        assert toc[0]['title'] == 'Chapter 1'
        assert toc[0]['page'] == 1
        assert toc[1]['title'] == 'Section 1.1'
        assert toc[1]['page'] == 5

    def test_extract_toc_empty_content(self):
        """Test with content containing no headings."""
        content = "Just some text without headings."
        toc = extract_toc_from_content(content, format_type="markdown")

        assert len(toc) == 0


class TestExtractPageLineMapping:
    """Test page-to-line mapping extraction."""

    def test_basic_page_mapping(self):
        """Test basic page marker extraction."""
        content = """`[p.1]`

Content for page 1.

`[p.2]`

Content for page 2.

`[p.3]`

Content for page 3.
"""
        mapping = extract_page_line_mapping(content)

        assert 1 in mapping
        assert 2 in mapping
        assert 3 in mapping

        assert mapping[1]['start'] < mapping[1]['end']
        assert mapping[2]['start'] > mapping[1]['end']

    def test_page_mapping_no_markers(self):
        """Test with content containing no page markers."""
        content = "Content without page markers."
        mapping = extract_page_line_mapping(content)

        assert len(mapping) == 0

    def test_page_mapping_single_page(self):
        """Test with single page marker."""
        content = """`[p.1]`

All content on one page.
Multiple lines.
Still page 1.
"""
        mapping = extract_page_line_mapping(content)

        assert len(mapping) == 1
        assert 1 in mapping


class TestGenerateMetadataSidecar:
    """Test metadata sidecar generation."""

    def test_basic_metadata_sidecar(self):
        """Test basic metadata generation."""
        book_details = {
            'title': 'Test Book',
            'author': 'Test Author',
            'id': '12345'
        }

        content = """`[p.1]`

# Chapter 1

Some content.
"""

        metadata = generate_metadata_sidecar(
            original_filename="test-book-12345.pdf",
            processed_content=content,
            book_details=book_details,
            format_type="pdf",
            output_format="markdown"
        )

        assert 'source' in metadata
        assert 'toc' in metadata
        assert 'page_line_mapping' in metadata
        assert 'processing_metadata' in metadata

        assert metadata['source']['title'] == 'Test Book'
        assert metadata['source']['author'] == 'Test Author'
        assert metadata['source']['id'] == '12345'

    def test_metadata_with_corrections(self):
        """Test metadata with corrections applied."""
        metadata = generate_metadata_sidecar(
            original_filename="test.pdf",
            processed_content="Content",
            book_details={'title': 'Test'},
            corrections_applied=['letter_spacing_correction', 'ocr_enhancement']
        )

        assert 'letter_spacing_correction' in metadata['processing_metadata']['corrections_applied']
        assert 'ocr_enhancement' in metadata['processing_metadata']['corrections_applied']

    def test_metadata_with_ocr_quality(self):
        """Test metadata with OCR quality score."""
        metadata = generate_metadata_sidecar(
            original_filename="test.pdf",
            processed_content="Content",
            book_details={'title': 'Test'},
            ocr_quality_score=0.92
        )

        assert metadata['processing_metadata']['ocr_quality_score'] == 0.92

    def test_metadata_word_count(self):
        """Test word count calculation."""
        content = "This is a test content with exactly ten words total."

        metadata = generate_metadata_sidecar(
            original_filename="test.pdf",
            processed_content=content,
            book_details={'title': 'Test'}
        )

        assert metadata['processing_metadata']['word_count'] == 10


class TestSaveMetadataSidecar:
    """Test saving metadata to file."""

    def test_save_metadata_to_file(self):
        """Test saving metadata to JSON file."""
        metadata = {
            'source': {'title': 'Test'},
            'toc': [],
            'page_line_mapping': {},
            'processing_metadata': {}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.metadata.json"
            result = save_metadata_sidecar(metadata, output_path)

            assert Path(result).exists()

            # Verify content
            with open(result, 'r') as f:
                saved_data = json.load(f)

            assert saved_data['source']['title'] == 'Test'

    def test_save_metadata_creates_directory(self):
        """Test that save creates parent directories."""
        metadata = {'test': 'data'}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "test.metadata.json"
            result = save_metadata_sidecar(metadata, output_path)

            assert Path(result).exists()
            assert Path(result).parent.exists()


class TestAddYAMLFrontmatterToContent:
    """Test adding YAML frontmatter to content."""

    def test_add_frontmatter_to_content(self):
        """Test prepending frontmatter to content."""
        content = "# Chapter 1\n\nContent here."

        book_details = {
            'title': 'Test Book',
            'author': 'Test Author',
            'id': '12345'
        }

        result = add_yaml_frontmatter_to_content(
            content,
            book_details=book_details,
            format_type="pdf"
        )

        assert result.startswith("---")
        assert "title: Test Book" in result
        assert "# Chapter 1" in result

    def test_frontmatter_separation(self):
        """Test that frontmatter is separated from content."""
        content = "Content"
        book_details = {'title': 'Test'}

        result = add_yaml_frontmatter_to_content(content, book_details=book_details)

        # Should have frontmatter, blank line, then content
        parts = result.split('\n\n')
        assert len(parts) >= 2

    def test_frontmatter_without_book_details(self):
        """Test frontmatter generation without book details."""
        content = "Content"

        result = add_yaml_frontmatter_to_content(content, book_details=None)

        # Should still generate basic frontmatter
        assert "---" in result
        assert "title: Unknown" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
