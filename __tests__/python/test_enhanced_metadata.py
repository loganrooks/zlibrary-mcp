"""
Test suite for enhanced metadata extraction from Z-Library book detail pages.

Tests follow TDD approach: Tests written first, implementation follows.
Uses real HTML fixtures from claudedocs/exploration/ for validation.

Phase 1 Priority: Description, Terms, Booklists, Rating, IPFS
"""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup
import json
import re


# Test fixtures path
FIXTURES_DIR = Path(__file__).parent.parent.parent / "claudedocs" / "exploration"
BOOK_ENHANCED_HTML = FIXTURES_DIR / "book_enhanced.html"
COMPLETE_METADATA_JSON = FIXTURES_DIR / "complete_book_metadata.json"


@pytest.fixture
def book_enhanced_html():
    """Load the enhanced book HTML fixture (Hegel's book)."""
    with open(BOOK_ENHANCED_HTML, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def book_enhanced_soup(book_enhanced_html):
    """Parse the enhanced book HTML into BeautifulSoup."""
    return BeautifulSoup(book_enhanced_html, 'html.parser')


@pytest.fixture
def expected_complete_metadata():
    """Load expected complete metadata from JSON fixture."""
    with open(COMPLETE_METADATA_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================================
# PHASE 1: Description Extraction
# ============================================================================

class TestDescriptionExtraction:
    """Test description extraction from JavaScript embedded in HTML."""

    def test_extract_description_exists(self, book_enhanced_html):
        """Test that description is extracted when present."""
        from lib.enhanced_metadata import extract_description

        description = extract_description(book_enhanced_html)

        assert description is not None
        assert isinstance(description, str)
        assert len(description) > 0

    def test_extract_description_content(self, book_enhanced_html):
        """Test that extracted description matches expected content."""
        from lib.enhanced_metadata import extract_description

        description = extract_description(book_enhanced_html)

        # Verify it contains key phrases from Hegel's book
        assert "Encyclopaedia Logic" in description
        assert "dialectical method" in description
        assert "Hegel" in description

    def test_extract_description_length(self, book_enhanced_html):
        """Test that description has expected length (around 816 chars)."""
        from lib.enhanced_metadata import extract_description

        description = extract_description(book_enhanced_html)

        # Description should be substantial (between 500-1000 chars)
        assert 500 <= len(description) <= 1000

    def test_extract_description_no_html_entities(self, book_enhanced_html):
        """Test that HTML entities are properly decoded."""
        from lib.enhanced_metadata import extract_description

        description = extract_description(book_enhanced_html)

        # Should not contain escaped quotes or HTML entities
        assert '\\"' not in description
        assert '&quot;' not in description
        assert '&#' not in description

    def test_extract_description_missing(self):
        """Test handling when description is not present."""
        from lib.enhanced_metadata import extract_description

        html_no_desc = '<html><body>No description here</body></html>'
        description = extract_description(html_no_desc)

        assert description is None or description == ""


# ============================================================================
# PHASE 1: Terms Extraction
# ============================================================================

class TestTermsExtraction:
    """Test conceptual terms extraction from book detail page."""

    def test_extract_terms_exists(self, book_enhanced_html):
        """Test that terms are extracted when present."""
        from lib.enhanced_metadata import extract_terms

        terms = extract_terms(book_enhanced_html)

        assert terms is not None
        assert isinstance(terms, list)
        assert len(terms) > 0

    def test_extract_terms_count(self, book_enhanced_html):
        """Test that correct number of terms is extracted (60+ for Hegel)."""
        from lib.enhanced_metadata import extract_terms

        terms = extract_terms(book_enhanced_html)

        # Should have around 60 terms for this rich metadata book
        assert len(terms) >= 50, f"Expected >= 50 terms, got {len(terms)}"

    def test_extract_terms_content(self, book_enhanced_html):
        """Test that expected Hegelian terms are present."""
        from lib.enhanced_metadata import extract_terms

        terms = extract_terms(book_enhanced_html)

        # Key Hegelian concepts should be present (from actual HTML term links)
        # Note: "dialectic" appears in text but not as a term link
        expected_terms = ["absolute", "reflection", "necessity",
                         "judgment", "universal", "concrete", "determination"]

        for expected_term in expected_terms:
            assert expected_term in terms, f"Expected term '{expected_term}' not found"

    def test_extract_terms_sorted(self, book_enhanced_html):
        """Test that terms are returned in sorted order."""
        from lib.enhanced_metadata import extract_terms

        terms = extract_terms(book_enhanced_html)

        # Should be alphabetically sorted
        assert terms == sorted(terms)

    def test_extract_terms_no_duplicates(self, book_enhanced_html):
        """Test that duplicate terms are removed."""
        from lib.enhanced_metadata import extract_terms

        terms = extract_terms(book_enhanced_html)

        # No duplicates
        assert len(terms) == len(set(terms))

    def test_extract_terms_missing(self):
        """Test handling when no terms are present."""
        from lib.enhanced_metadata import extract_terms

        html_no_terms = '<html><body>No term links here</body></html>'
        terms = extract_terms(html_no_terms)

        assert terms == []


# ============================================================================
# PHASE 1: Booklists Extraction
# ============================================================================

class TestBooklistsExtraction:
    """Test booklist extraction from z-booklist elements."""

    def test_extract_booklists_exists(self, book_enhanced_soup):
        """Test that booklists are extracted when present."""
        from lib.enhanced_metadata import extract_booklists

        booklists = extract_booklists(book_enhanced_soup, mirror_url="https://z-library.sk")

        assert booklists is not None
        assert isinstance(booklists, list)
        assert len(booklists) > 0

    def test_extract_booklists_count(self, book_enhanced_soup):
        """Test that correct number of booklists is extracted (11+ for Hegel)."""
        from lib.enhanced_metadata import extract_booklists

        booklists = extract_booklists(book_enhanced_soup, mirror_url="https://z-library.sk")

        # Should have around 11 booklists for this book
        assert len(booklists) >= 10, f"Expected >= 10 booklists, got {len(booklists)}"

    def test_extract_booklist_structure(self, book_enhanced_soup):
        """Test that booklist objects have correct structure."""
        from lib.enhanced_metadata import extract_booklists

        booklists = extract_booklists(book_enhanced_soup, mirror_url="https://z-library.sk")

        for booklist in booklists:
            # Each booklist should have these fields
            assert 'id' in booklist
            assert 'hash' in booklist
            assert 'topic' in booklist
            assert 'quantity' in booklist
            assert 'url' in booklist

            # Types
            assert isinstance(booklist['id'], str)
            assert isinstance(booklist['topic'], str)
            assert isinstance(booklist['quantity'], int)
            assert isinstance(booklist['url'], str)

    def test_extract_booklist_philosophy_present(self, book_enhanced_soup):
        """Test that 'Philosophy' booklist is found."""
        from lib.enhanced_metadata import extract_booklists

        booklists = extract_booklists(book_enhanced_soup, mirror_url="https://z-library.sk")

        topics = [bl['topic'] for bl in booklists]
        assert 'Philosophy' in topics

        # Find the philosophy booklist and verify it's large
        phil_list = next(bl for bl in booklists if bl['topic'] == 'Philosophy')
        assert phil_list['quantity'] > 500  # Should have 954 books

    def test_extract_booklist_url_construction(self, book_enhanced_soup):
        """Test that booklist URLs are properly constructed."""
        from lib.enhanced_metadata import extract_booklists

        mirror_url = "https://z-library.sk"
        booklists = extract_booklists(book_enhanced_soup, mirror_url=mirror_url)

        for booklist in booklists:
            # URL should start with mirror
            assert booklist['url'].startswith(mirror_url)
            # URL should contain /booklist/
            assert '/booklist/' in booklist['url']

    def test_extract_booklists_missing(self):
        """Test handling when no booklists are present."""
        from lib.enhanced_metadata import extract_booklists

        html_no_booklists = BeautifulSoup('<html><body>No booklists</body></html>', 'html.parser')
        booklists = extract_booklists(html_no_booklists, mirror_url="https://z-library.sk")

        assert booklists == []


# ============================================================================
# PHASE 1: Rating Extraction
# ============================================================================

class TestRatingExtraction:
    """Test rating and quality score extraction."""

    def test_extract_rating_exists(self, book_enhanced_html):
        """Test that rating is extracted when present."""
        from lib.enhanced_metadata import extract_rating

        rating = extract_rating(book_enhanced_html)

        assert rating is not None
        assert isinstance(rating, dict)

    def test_extract_rating_structure(self, book_enhanced_html):
        """Test that rating has correct structure."""
        from lib.enhanced_metadata import extract_rating

        rating = extract_rating(book_enhanced_html)

        assert 'value' in rating
        assert 'count' in rating
        assert isinstance(rating['value'], float)
        assert isinstance(rating['count'], int)

    def test_extract_rating_values(self, book_enhanced_html):
        """Test that rating values are in valid ranges."""
        from lib.enhanced_metadata import extract_rating

        rating = extract_rating(book_enhanced_html)

        # Rating should be 5.0 for Hegel's book
        assert 0.0 <= rating['value'] <= 5.0
        assert rating['value'] == 5.0

        # Should have 1344 user ratings
        assert rating['count'] > 1000
        assert rating['count'] == 1344

    def test_extract_rating_missing(self):
        """Test handling when rating is not present."""
        from lib.enhanced_metadata import extract_rating

        html_no_rating = '<html><body>No rating</body></html>'
        rating = extract_rating(html_no_rating)

        assert rating is None or rating == {}


# ============================================================================
# PHASE 1: IPFS CID Extraction
# ============================================================================

class TestIPFSExtraction:
    """Test IPFS CID extraction from book detail page."""

    def test_extract_ipfs_cids_exists(self, book_enhanced_soup):
        """Test that IPFS CIDs are extracted when present."""
        from lib.enhanced_metadata import extract_ipfs_cids

        cids = extract_ipfs_cids(book_enhanced_soup)

        assert cids is not None
        assert isinstance(cids, list)

    def test_extract_ipfs_cids_count(self, book_enhanced_soup):
        """Test that two IPFS CID formats are extracted."""
        from lib.enhanced_metadata import extract_ipfs_cids

        cids = extract_ipfs_cids(book_enhanced_soup)

        # Should have 2 CIDs (Qm... and bafy...)
        assert len(cids) >= 2, f"Expected >= 2 CIDs, got {len(cids)}"

    def test_extract_ipfs_cid_formats(self, book_enhanced_soup):
        """Test that both IPFS CID formats are present."""
        from lib.enhanced_metadata import extract_ipfs_cids

        cids = extract_ipfs_cids(book_enhanced_soup)

        # Should have one CID starting with Qm (CIDv0)
        qm_cids = [cid for cid in cids if cid.startswith('Qm')]
        assert len(qm_cids) >= 1

        # Should have one CID starting with bafy (CIDv1)
        bafy_cids = [cid for cid in cids if cid.startswith('bafy')]
        assert len(bafy_cids) >= 1

    def test_extract_ipfs_cid_validity(self, book_enhanced_soup):
        """Test that extracted CIDs look valid."""
        from lib.enhanced_metadata import extract_ipfs_cids

        cids = extract_ipfs_cids(book_enhanced_soup)

        for cid in cids:
            # CIDs should be alphanumeric strings
            assert cid.isalnum()
            # CIDs should be reasonably long (> 30 chars)
            assert len(cid) > 30

    def test_extract_ipfs_cids_missing(self):
        """Test handling when no IPFS CIDs are present."""
        from lib.enhanced_metadata import extract_ipfs_cids

        html_no_ipfs = BeautifulSoup('<html><body>No IPFS</body></html>', 'html.parser')
        cids = extract_ipfs_cids(html_no_ipfs)

        assert cids == []


# ============================================================================
# PHASE 1: Quality Score Extraction
# ============================================================================

class TestQualityScoreExtraction:
    """Test quality score extraction from book metadata."""

    def test_extract_quality_score_exists_or_none(self, book_enhanced_html):
        """Test that quality score extraction doesn't crash (may be None)."""
        from lib.enhanced_metadata import extract_quality_score

        quality = extract_quality_score(book_enhanced_html)

        # Quality may not be present in all books
        assert quality is None or isinstance(quality, float)

    def test_extract_quality_score_value_if_present(self, book_enhanced_html):
        """Test that quality score is in valid range if present."""
        from lib.enhanced_metadata import extract_quality_score

        quality = extract_quality_score(book_enhanced_html)

        # If quality is present, it should be in valid range
        if quality is not None:
            assert 0.0 <= quality <= 5.0

    def test_extract_quality_score_missing(self):
        """Test handling when quality score is not present."""
        from lib.enhanced_metadata import extract_quality_score

        html_no_quality = '<html><body>No quality</body></html>'
        quality = extract_quality_score(html_no_quality)

        assert quality is None


# ============================================================================
# PHASE 1: Series Extraction
# ============================================================================

class TestSeriesExtraction:
    """Test series information extraction."""

    def test_extract_series_exists(self, book_enhanced_soup):
        """Test that series is extracted when present."""
        from lib.enhanced_metadata import extract_series

        series = extract_series(book_enhanced_soup)

        assert series is not None
        assert isinstance(series, str)

    def test_extract_series_content(self, book_enhanced_soup):
        """Test that correct series is extracted."""
        from lib.enhanced_metadata import extract_series

        series = extract_series(book_enhanced_soup)

        # Hegel's book should be in Cambridge Hegel Translations series
        assert "Cambridge" in series
        assert "Hegel" in series

    def test_extract_series_missing(self):
        """Test handling when series is not present."""
        from lib.enhanced_metadata import extract_series

        html_no_series = BeautifulSoup('<html><body>No series</body></html>', 'html.parser')
        series = extract_series(html_no_series)

        assert series is None or series == ""


# ============================================================================
# PHASE 1: Categories Extraction
# ============================================================================

class TestCategoriesExtraction:
    """Test category extraction from book detail page."""

    def test_extract_categories_exists(self, book_enhanced_soup):
        """Test that categories are extracted when present."""
        from lib.enhanced_metadata import extract_categories

        categories = extract_categories(book_enhanced_soup)

        assert categories is not None
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_extract_categories_structure(self, book_enhanced_soup):
        """Test that category objects have correct structure."""
        from lib.enhanced_metadata import extract_categories

        categories = extract_categories(book_enhanced_soup)

        for category in categories:
            assert 'name' in category
            assert 'url' in category
            assert isinstance(category['name'], str)
            assert isinstance(category['url'], str)

    def test_extract_categories_content(self, book_enhanced_soup):
        """Test that expected categories are present."""
        from lib.enhanced_metadata import extract_categories

        categories = extract_categories(book_enhanced_soup)

        names = [cat['name'] for cat in categories]
        # Should contain Philosophy or Anthropology
        assert any('Philosophy' in name or 'Anthropology' in name for name in names)

    def test_extract_categories_missing(self):
        """Test handling when no categories are present."""
        from lib.enhanced_metadata import extract_categories

        html_no_cats = BeautifulSoup('<html><body>No categories</body></html>', 'html.parser')
        categories = extract_categories(html_no_cats)

        assert categories == []


# ============================================================================
# PHASE 1: ISBN Extraction
# ============================================================================

class TestISBNExtraction:
    """Test ISBN extraction from book properties."""

    def test_extract_isbn_13_exists(self, book_enhanced_soup):
        """Test that ISBN-13 is extracted when present."""
        from lib.enhanced_metadata import extract_isbns

        isbns = extract_isbns(book_enhanced_soup)

        assert 'isbn_13' in isbns
        assert isbns['isbn_13'] is not None

    def test_extract_isbn_10_exists(self, book_enhanced_soup):
        """Test that ISBN-10 is extracted when present."""
        from lib.enhanced_metadata import extract_isbns

        isbns = extract_isbns(book_enhanced_soup)

        assert 'isbn_10' in isbns
        assert isbns['isbn_10'] is not None

    def test_extract_isbn_validity(self, book_enhanced_soup):
        """Test that extracted ISBNs have correct format."""
        from lib.enhanced_metadata import extract_isbns

        isbns = extract_isbns(book_enhanced_soup)

        # ISBN-13 should be 13 digits
        if isbns.get('isbn_13'):
            isbn_13_clean = re.sub(r'[^0-9]', '', isbns['isbn_13'])
            assert len(isbn_13_clean) == 13

        # ISBN-10 should be 10 characters (9 digits + check digit)
        if isbns.get('isbn_10'):
            isbn_10_clean = re.sub(r'[^0-9X]', '', isbns['isbn_10'])
            assert len(isbn_10_clean) == 10


# ============================================================================
# PHASE 1: Complete Metadata Extraction (Integration Test)
# ============================================================================

class TestCompleteMetadataExtraction:
    """Test complete metadata extraction from book detail page."""

    def test_extract_complete_metadata_all_fields(self, book_enhanced_html):
        """Test that all priority fields are extracted."""
        from lib.enhanced_metadata import extract_complete_metadata

        metadata = extract_complete_metadata(book_enhanced_html, mirror_url="https://z-library.sk")

        # Tier 1: Essential fields
        assert 'description' in metadata
        assert 'terms' in metadata
        assert 'booklists' in metadata

        # Tier 2: Important fields
        assert 'rating' in metadata
        assert 'ipfs_cids' in metadata
        assert 'series' in metadata
        assert 'categories' in metadata
        assert 'isbn_13' in metadata
        assert 'isbn_10' in metadata

        # Tier 3: Optional fields
        assert 'quality_score' in metadata

    def test_extract_complete_metadata_types(self, book_enhanced_html):
        """Test that extracted fields have correct types."""
        from lib.enhanced_metadata import extract_complete_metadata

        metadata = extract_complete_metadata(book_enhanced_html, mirror_url="https://z-library.sk")

        assert isinstance(metadata['description'], str)
        assert isinstance(metadata['terms'], list)
        assert isinstance(metadata['booklists'], list)
        assert isinstance(metadata['rating'], dict)
        assert isinstance(metadata['ipfs_cids'], list)
        assert isinstance(metadata['categories'], list)

    def test_extract_complete_metadata_richness(self, book_enhanced_html):
        """Test that extracted metadata is rich (25+ fields total)."""
        from lib.enhanced_metadata import extract_complete_metadata

        metadata = extract_complete_metadata(book_enhanced_html, mirror_url="https://z-library.sk")

        # Count non-None fields
        non_none_fields = sum(1 for v in metadata.values() if v is not None and v != [] and v != {})

        # Should have at least 9 fields with data (quality_score may be None)
        assert non_none_fields >= 9, f"Expected >= 9 fields with data, got {non_none_fields}"

    def test_extract_complete_metadata_validation(self, book_enhanced_html, expected_complete_metadata):
        """Test that extracted metadata matches expected values from fixture."""
        from lib.enhanced_metadata import extract_complete_metadata

        metadata = extract_complete_metadata(book_enhanced_html, mirror_url="https://z-library.sk")

        # Validate key fields match expected
        if expected_complete_metadata.get('rating'):
            assert metadata['rating']['value'] == expected_complete_metadata['rating']['value']

        if expected_complete_metadata.get('terms'):
            # At least 80% of expected terms should be present
            expected_terms_set = set(expected_complete_metadata['terms'])
            extracted_terms_set = set(metadata['terms'])
            overlap = len(expected_terms_set & extracted_terms_set) / len(expected_terms_set)
            assert overlap >= 0.8, f"Only {overlap*100}% of expected terms found"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_html(self):
        """Test handling of malformed HTML."""
        from lib.enhanced_metadata import extract_complete_metadata

        malformed = '<html><body><div class="unclosed">'

        # Should not crash, may return partial data
        try:
            metadata = extract_complete_metadata(malformed, mirror_url="https://z-library.sk")
            assert isinstance(metadata, dict)
        except Exception as e:
            pytest.fail(f"Should handle malformed HTML gracefully: {e}")

    def test_empty_html(self):
        """Test handling of empty HTML."""
        from lib.enhanced_metadata import extract_complete_metadata

        empty = ''

        metadata = extract_complete_metadata(empty, mirror_url="https://z-library.sk")

        # Should return empty/default values
        assert metadata['terms'] == []
        assert metadata['booklists'] == []
        assert metadata['ipfs_cids'] == []

    def test_missing_mirror_url(self, book_enhanced_html):
        """Test handling when mirror_url is not provided."""
        from lib.enhanced_metadata import extract_complete_metadata

        # Should work with None or empty mirror (booklist URLs will be relative)
        metadata = extract_complete_metadata(book_enhanced_html, mirror_url=None)

        assert isinstance(metadata, dict)
        # Booklists should still have data but URLs might be relative
        assert isinstance(metadata['booklists'], list)


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance of metadata extraction."""

    def test_extraction_speed(self, book_enhanced_html, benchmark):
        """Test that extraction completes in reasonable time."""
        from lib.enhanced_metadata import extract_complete_metadata

        # Should complete in under 1 second
        result = benchmark(extract_complete_metadata, book_enhanced_html, "https://z-library.sk")

        assert isinstance(result, dict)

    def test_multiple_extractions(self, book_enhanced_html):
        """Test that multiple extractions are consistent."""
        from lib.enhanced_metadata import extract_complete_metadata

        # Extract twice
        metadata1 = extract_complete_metadata(book_enhanced_html, "https://z-library.sk")
        metadata2 = extract_complete_metadata(book_enhanced_html, "https://z-library.sk")

        # Should be identical
        assert metadata1['terms'] == metadata2['terms']
        assert metadata1['rating'] == metadata2['rating']
        assert len(metadata1['booklists']) == len(metadata2['booklists'])
