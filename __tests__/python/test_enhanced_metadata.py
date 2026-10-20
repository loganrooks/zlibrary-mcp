"""
Test suite for enhanced metadata extraction (EAPI-based).

Metadata is extracted from EAPI JSON replies. Only fields the reply carries are
returned; EAPI exposes no terms, booklists or IPFS ids, so none are (#256).
"""

import json
from pathlib import Path

import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit

FIXTURES = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "eapi-book-detail.json").read_text()
)
RETIRED = {"terms", "booklists", "ipfs_cids"}


class TestExtractMetadataFromEAPI:
    """Test EAPI JSON field mapping to metadata format."""

    def test_complete_reply_maps_every_detail_field(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi(FIXTURES["complete"])

        assert metadata == {
            "description": "Part one of the Encyclopaedia of the Philosophical Sciences.",
            "rating": {"value": 4.6, "count": 52},
            "series": "Hackett Classics",
            "categories": [{"name": "Philosophy"}, {"name": "Logic"}],
            "quality_score": 4.0,
            "edition": "Revised",
            "translator": "T. F. Geraets",
            "isbn_13": "978-0-87220-070-5",
        }

    def test_sparse_reply_returns_no_fields(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        assert extract_metadata_from_eapi(FIXTURES["sparse"]) == {}

    def test_empty_book_info(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        assert extract_metadata_from_eapi({}) == {}
        assert extract_metadata_from_eapi(None) == {}

    def test_isbn_10_detection(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi({"book": {"isbn": "0521829747"}})
        assert metadata == {"isbn_10": "0521829747"}

    def test_rating_count_is_not_invented(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        metadata = extract_metadata_from_eapi({"book": {"rating": "3.5"}})
        assert metadata == {"rating": {"value": 3.5}}

    def test_retired_fields_are_never_returned(self):
        from lib.enhanced_metadata import extract_metadata_from_eapi

        for reply in (FIXTURES["complete"], FIXTURES["sparse"], {}):
            assert RETIRED.isdisjoint(extract_metadata_from_eapi(reply))


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

        assert metadata == {"description": "A test book"}
        mock_client.get_book_info.assert_called_once_with(123, "abc")
