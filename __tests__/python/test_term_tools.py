"""
Test suite for term exploration tools (EAPI-based).

Term exploration enables conceptual navigation through Z-Library's
terms, using EAPI search endpoint instead of HTML scraping.
"""

import pytest
from unittest.mock import AsyncMock
from lib.term_tools import search_by_term

pytestmark = pytest.mark.unit


class TestSearchByTerm:
    """Tests for the EAPI-based search_by_term function."""

    @pytest.mark.asyncio
    async def test_search_by_term_basic(self):
        """Should perform basic term search via EAPI."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value={
                "books": [
                    {
                        "id": 123,
                        "title": "Dialectic Book",
                        "author": "Hegel",
                        "hash": "abc",
                    }
                ]
            }
        )

        result = await search_by_term(
            term="dialectic",
            email="test@example.com",
            password="password",
            eapi_client=mock_client,
        )

        assert result["term"] == "dialectic"
        assert result["total_results"] == 1
        assert len(result["books"]) == 1
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_term_exact_flag(self):
        """Should pass exact=True to EAPI search."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await search_by_term(
            term="dialectic",
            email="",
            password="",
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args
        assert (
            call_kwargs.kwargs.get("exact") is True
            or call_kwargs[1].get("exact") is True
        )

    @pytest.mark.asyncio
    async def test_search_by_term_with_filters(self):
        """Should pass year and language filters to EAPI."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await search_by_term(
            term="dialectic",
            email="",
            password="",
            year_from=2000,
            year_to=2023,
            languages="English",
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["year_from"] == 2000
        assert call_kwargs["year_to"] == 2023
        assert call_kwargs["languages"] == ["English"]

    @pytest.mark.asyncio
    async def test_search_by_term_with_limit(self):
        """Should respect limit parameter."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await search_by_term(
            term="dialectic",
            email="",
            password="",
            limit=50,
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_search_by_term_empty_results(self):
        """Should handle empty results gracefully."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        result = await search_by_term(
            term="nonexistentterm12345",
            email="",
            password="",
            eapi_client=mock_client,
        )

        assert result["total_results"] == 0
        assert len(result["books"]) == 0

    @pytest.mark.asyncio
    async def test_search_by_term_error_handling(self):
        """Should propagate search errors."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("Network error"))

        with pytest.raises(Exception, match="Network error"):
            await search_by_term(
                term="dialectic",
                email="",
                password="",
                eapi_client=mock_client,
            )

    def test_search_by_term_empty_term(self):
        """Should reject empty term."""
        with pytest.raises(ValueError):
            import asyncio

            asyncio.run(
                search_by_term(
                    term="",
                    email="",
                    password="",
                    eapi_client=AsyncMock(),
                )
            )

    @pytest.mark.asyncio
    async def test_search_by_term_normalizes_results(self):
        """Should normalize EAPI response to standard book format."""
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value={
                "books": [
                    {
                        "id": 1,
                        "title": "Test",
                        "author": "Author",
                        "hash": "h1",
                        "year": "2020",
                        "language": "english",
                        "extension": "pdf",
                    }
                ]
            }
        )

        result = await search_by_term(
            term="test",
            email="",
            password="",
            eapi_client=mock_client,
        )

        book = result["books"][0]
        assert "id" in book
        assert "title" in book
        assert "author" in book


class TestSyncWrapper:
    def test_sync_wrapper_exists(self):
        from lib.term_tools import search_by_term_sync

        assert callable(search_by_term_sync)
