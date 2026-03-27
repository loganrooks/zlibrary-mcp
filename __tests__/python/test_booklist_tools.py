"""
Test suite for booklist exploration tools (EAPI-based).

After EAPI migration, booklist tools use search-based fallback since
the EAPI does not expose a direct booklist browsing endpoint.
"""

import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


class TestFetchBooklist:
    """Tests for the EAPI-based fetch_booklist function."""

    @pytest.mark.asyncio
    async def test_fetch_booklist_returns_degraded_response(self):
        """Should return a degraded response with search fallback."""
        from lib.booklist_tools import fetch_booklist

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value={
                "books": [
                    {"id": 123, "title": "Book 1", "author": "Author 1", "hash": "abc"},
                ]
            }
        )

        result = await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email="test@example.com",
            password="password",
            eapi_client=mock_client,
        )

        assert result["booklist_id"] == "409997"
        assert result["degraded"] is True
        assert result["topic"] == "philosophy"
        assert len(result["books"]) == 1
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_fetch_booklist_with_eapi_client(self):
        """Should use provided eapi_client without creating a new one."""
        from lib.booklist_tools import fetch_booklist

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        result = await fetch_booklist(
            booklist_id="123",
            booklist_hash="abc",
            topic="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        assert result["degraded"] is True
        assert result["books"] == []
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_booklist_preserves_return_format(self):
        """Return dict has expected keys for python_bridge compat."""
        from lib.booklist_tools import fetch_booklist

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        result = await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="t",
            email="",
            password="",
            eapi_client=mock_client,
        )

        for key in [
            "booklist_id",
            "booklist_hash",
            "topic",
            "metadata",
            "books",
            "page",
        ]:
            assert key in result


class TestFetchBooklistEnrichment:
    """Tests for the metadata enrichment logic in fetch_booklist."""

    @pytest.mark.asyncio
    async def test_enriches_top_5_books_with_metadata(self):
        """Should enrich up to 5 books with description, categories, rating."""
        from lib.booklist_tools import fetch_booklist

        books = [
            {"id": i, "title": f"Book {i}", "author": f"Author {i}", "hash": f"h{i}"}
            for i in range(7)
        ]
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": books})
        mock_client.get_book_info = AsyncMock(
            return_value={
                "book": {
                    "description": "A great book",
                    "categories": ["Philosophy"],
                    "rating": 4.5,
                }
            }
        )

        result = await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        # First 5 should be enriched
        for book in result["books"][:5]:
            assert book.get("description") == "A great book"
            assert book.get("categories") == ["Philosophy"]
            assert book.get("rating") == 4.5

        # Book 6 and 7 should NOT be enriched
        for book in result["books"][5:]:
            assert "description" not in book

        # get_book_info called exactly 5 times
        assert mock_client.get_book_info.call_count == 5

    @pytest.mark.asyncio
    async def test_enrichment_failure_handled_gracefully(self):
        """Should not fail if get_book_info raises for some books."""
        from lib.booklist_tools import fetch_booklist

        books = [
            {"id": 1, "title": "Book 1", "hash": "h1"},
            {"id": 2, "title": "Book 2", "hash": "h2"},
        ]
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": books})
        mock_client.get_book_info = AsyncMock(
            side_effect=[
                Exception("Network error"),
                {"book": {"description": "OK book"}},
            ]
        )

        result = await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        # Should still return both books
        assert len(result["books"]) == 2
        # Second book got enriched despite first failing
        assert result["books"][1].get("description") == "OK book"

    @pytest.mark.asyncio
    async def test_books_without_id_or_hash_not_enriched(self):
        """Books missing id or hash should be skipped for enrichment."""
        from lib.booklist_tools import fetch_booklist

        books = [
            {"title": "No ID", "hash": "h1"},  # missing id
            {"id": 2, "title": "No Hash"},  # missing hash
            {"id": 3, "title": "Good", "hash": "h3"},
        ]
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": books})
        mock_client.get_book_info = AsyncMock(
            return_value={"book": {"description": "enriched"}}
        )

        await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        # Only book 3 has both id and hash
        assert mock_client.get_book_info.call_count == 1

    @pytest.mark.asyncio
    async def test_source_field_added_to_all_books(self):
        """All books should get source='topic_search_enriched'."""
        from lib.booklist_tools import fetch_booklist

        books = [
            {"id": 1, "title": "Book 1", "hash": "h1"},
            {"id": 2, "title": "Book 2", "hash": "h2"},
        ]
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": books})
        mock_client.get_book_info = AsyncMock(return_value={"book": {}})

        result = await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        for book in result["books"]:
            assert book["source"] == "topic_search_enriched"

    @pytest.mark.asyncio
    async def test_enrichment_skipped_when_no_hash(self):
        """Books with no hash at all should not trigger enrichment."""
        from lib.booklist_tools import fetch_booklist

        # After normalize_eapi_book, a book without hash in raw input
        # will have hash="" and book_hash="", so enrichment is skipped.
        books = [
            {"id": 1, "title": "Book 1"},  # no hash field
        ]
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": books})
        mock_client.get_book_info = AsyncMock(
            return_value={"book": {"description": "should not happen"}}
        )

        result = await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        # No hash means no enrichment
        assert mock_client.get_book_info.call_count == 0
        assert "description" not in result["books"][0]

    @pytest.mark.asyncio
    async def test_pagination_parameter(self):
        """Should pass page parameter to search."""
        from lib.booklist_tools import fetch_booklist

        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await fetch_booklist(
            booklist_id="1",
            booklist_hash="h",
            topic="test",
            email="",
            password="",
            page=3,
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["page"] == 3


class TestFetchBooklistSync:
    """Test the synchronous wrapper."""

    def test_sync_wrapper_exists(self):
        from lib.booklist_tools import fetch_booklist_sync

        assert callable(fetch_booklist_sync)
