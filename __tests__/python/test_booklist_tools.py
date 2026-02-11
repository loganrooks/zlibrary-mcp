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


class TestFetchBooklistSync:
    """Test the synchronous wrapper."""

    def test_sync_wrapper_exists(self):
        from lib.booklist_tools import fetch_booklist_sync

        assert callable(fetch_booklist_sync)
