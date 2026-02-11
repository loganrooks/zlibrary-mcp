"""
Test suite for enhanced metadata extraction (EAPI-based).

After EAPI migration, metadata is extracted from JSON responses
rather than HTML parsing. Tests validate the EAPI field mapping
and the legacy compatibility stubs.
"""

import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


class TestExtractMetadataFromEAPI:
    """Test EAPI JSON field mapping to metadata format."""

    def test_extract_full_metadata(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        book_info = {
            "book": {
                "title": "The Encyclopaedia Logic",
                "author": "Hegel",
                "description": "A comprehensive study of dialectical method.",
                "isbn": "978-0-521-82974-3",
                "rating": "5.0",
                "ratingCount": 1344,
                "series": "Cambridge Hegel Translations",
                "categories": ["Philosophy", "Logic"],
                "qualityScore": "4.5",
            }
        }

        metadata = extract_metadata_from_eapi(book_info)

        assert metadata["description"] == "A comprehensive study of dialectical method."
        assert metadata["isbn_13"] == "978-0-521-82974-3"
        assert metadata["rating"]["value"] == 5.0
        assert metadata["rating"]["count"] == 1344
        assert metadata["series"] == "Cambridge Hegel Translations"
        assert len(metadata["categories"]) == 2
        assert metadata["quality_score"] == 4.5

    def test_extract_empty_book_info(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi({})
        assert metadata == extract_metadata_from_eapi(None)

    def test_extract_missing_fields(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi({"book": {"title": "Test"}})

        assert metadata["description"] is None
        assert metadata["terms"] == []
        assert metadata["booklists"] == []
        assert metadata["ipfs_cids"] == []
        assert metadata["rating"] is None
        assert metadata["series"] is None
        assert metadata["isbn_10"] is None
        assert metadata["isbn_13"] is None

    def test_isbn_10_detection(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi({"book": {"isbn": "0521829747"}})
        assert metadata["isbn_10"] == "0521829747"
        assert metadata["isbn_13"] is None

    def test_unavailable_eapi_fields_documented(self):
        """Fields not in EAPI should return empty defaults."""
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi({"book": {"title": "Test"}})

        # These are explicitly not available via EAPI
        assert metadata["terms"] == []
        assert metadata["booklists"] == []
        assert metadata["ipfs_cids"] == []


class TestGetEnhancedMetadata:
    """Test the async main entry point."""

    @pytest.mark.asyncio
    async def test_get_enhanced_metadata_with_client(self):
        from lib.enhanced_metadata import get_enhanced_metadata

        mock_client = AsyncMock()
        mock_client.get_book_info = AsyncMock(
            return_value={"book": {"title": "Test", "description": "A test book"}}
        )

        metadata = await get_enhanced_metadata(
            book_id=123,
            book_hash="abc",
            eapi_client=mock_client,
        )

        assert metadata["description"] == "A test book"
        mock_client.get_book_info.assert_called_once_with(123, "abc")


class TestLegacyCompatibility:
    """Test backward compatibility stubs."""

    def test_extract_complete_metadata_returns_empty(self):
        from lib.enhanced_metadata import extract_complete_metadata

        metadata = extract_complete_metadata("<html></html>")
        assert metadata["terms"] == []
        assert metadata["description"] is None

    def test_extract_description_returns_none(self):
        from lib.enhanced_metadata import extract_description

        assert extract_description("<html></html>") is None

    def test_empty_metadata_structure(self):
        from lib.enhanced_metadata import _empty_metadata

        metadata = _empty_metadata()
        expected_keys = [
            "description",
            "terms",
            "booklists",
            "rating",
            "ipfs_cids",
            "series",
            "categories",
            "isbn_10",
            "isbn_13",
            "quality_score",
        ]
        for key in expected_keys:
            assert key in metadata
