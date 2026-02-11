"""
Test suite for author search tools (EAPI-based).

Author tools enable advanced author-based searching with support for
exact name matching, multiple authors, and syntax variations.
"""

import pytest
from unittest.mock import AsyncMock
from lib.author_tools import format_author_query, search_by_author, validate_author_name

pytestmark = pytest.mark.unit


class TestAuthorQueryFormatting:
    """Tests for author query formatting."""

    def test_format_simple_name(self):
        query = format_author_query("Plato")
        assert query == "Plato"

    def test_format_full_name(self):
        query = format_author_query("Georg Wilhelm Friedrich Hegel")
        assert "Georg" in query and "Hegel" in query

    def test_format_lastname_firstname(self):
        query = format_author_query("Hegel, Georg Wilhelm Friedrich")
        assert "Hegel" in query and "Georg" in query

    def test_format_with_exact_flag(self):
        query = format_author_query("Hegel", exact=True)
        assert '"Hegel"' == query

    def test_format_empty_name(self):
        with pytest.raises(ValueError):
            format_author_query("")

    def test_format_with_special_characters(self):
        query = format_author_query("O'Connor")
        assert "Connor" in query


class TestAuthorNameValidation:
    """Tests for author name validation."""

    def test_validate_simple_name(self):
        assert validate_author_name("Plato") is True

    def test_validate_full_name(self):
        assert validate_author_name("Georg Wilhelm Friedrich Hegel") is True

    def test_validate_comma_format(self):
        assert validate_author_name("Hegel, Georg") is True

    def test_validate_empty_name(self):
        assert validate_author_name("") is False

    def test_validate_whitespace_only(self):
        assert validate_author_name("   ") is False

    def test_validate_numbers_in_name(self):
        assert validate_author_name("Louis XVI") is True

    def test_validate_special_characters(self):
        assert validate_author_name("Jean-Paul Sartre") is True
        assert validate_author_name("O'Brien") is True


class TestSearchByAuthor:
    """Tests for the EAPI-based search_by_author function."""

    @pytest.mark.asyncio
    async def test_search_author_simple(self):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value={
                "books": [
                    {
                        "id": 123,
                        "title": "Science of Logic",
                        "author": "Hegel",
                        "hash": "abc",
                    }
                ]
            }
        )

        result = await search_by_author(
            author="Hegel",
            email="",
            password="",
            eapi_client=mock_client,
        )

        assert result["author"] == "Hegel"
        assert result["total_results"] == 1
        assert len(result["books"]) == 1

    @pytest.mark.asyncio
    async def test_search_author_exact_match(self):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await search_by_author(
            author="Hegel, Georg Wilhelm Friedrich",
            exact=True,
            email="",
            password="",
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs.get("exact") is True

    @pytest.mark.asyncio
    async def test_search_author_with_filters(self):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await search_by_author(
            author="Hegel",
            email="",
            password="",
            year_from=1800,
            year_to=1850,
            languages="German",
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["year_from"] == 1800
        assert call_kwargs["year_to"] == 1850
        assert call_kwargs["languages"] == ["German"]

    @pytest.mark.asyncio
    async def test_search_author_invalid_name(self):
        with pytest.raises(ValueError):
            await search_by_author(author="", email="", password="")

    @pytest.mark.asyncio
    async def test_search_author_error_handling(self):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("Network error"))

        with pytest.raises(Exception, match="Network error"):
            await search_by_author(
                author="Hegel",
                email="",
                password="",
                eapi_client=mock_client,
            )

    @pytest.mark.asyncio
    async def test_search_author_empty_results(self):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        result = await search_by_author(
            author="NonexistentAuthor12345",
            email="",
            password="",
            eapi_client=mock_client,
        )

        assert result["total_results"] == 0
        assert len(result["books"]) == 0

    @pytest.mark.asyncio
    async def test_search_author_pagination(self):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={"books": []})

        await search_by_author(
            author="Hegel",
            email="",
            password="",
            page=2,
            limit=50,
            eapi_client=mock_client,
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["limit"] == 50
        assert call_kwargs["page"] == 2


class TestSyncWrapper:
    def test_sync_wrapper_exists(self):
        from lib.author_tools import search_by_author_sync

        assert callable(search_by_author_sync)
