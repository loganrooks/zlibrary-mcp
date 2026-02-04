"""TDD tests for LibGen adapter.

Tests verify LibgenAdapter implements SourceAdapter interface correctly,
returning UnifiedBookResult with source=LIBGEN and wrapping sync
LibgenSearch calls in asyncio.to_thread().
"""

from unittest.mock import MagicMock, patch
import pytest

from lib.sources.config import SourceConfig
from lib.sources.models import SourceType


class TestLibgenAdapterSearch:
    """Tests for LibgenAdapter.search() method."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SourceConfig(
            libgen_mirror="li",
            default_source="libgen",
            fallback_enabled=False,
        )

    @pytest.fixture
    def mock_book(self):
        """Create a mock book result from LibgenSearch."""
        book = MagicMock()
        book.md5 = "abc123def456"
        book.title = "Python Programming"
        book.author = "John Doe"
        book.year = "2023"
        book.extension = "pdf"
        book.size = "5 MB"
        book.tor_download_link = "https://example.com/download/abc123def456"
        book.id = "12345"
        book.language = "English"
        book.pages = "500"
        return book

    @pytest.mark.asyncio
    async def test_search_returns_results(self, config, mock_book):
        """Search should return list of UnifiedBookResult with source=LIBGEN."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = [mock_book]
            mock_search_class.return_value = mock_instance

            results = await adapter.search("python")

            assert len(results) == 1
            assert results[0].md5 == "abc123def456"
            assert results[0].title == "Python Programming"
            assert results[0].author == "John Doe"
            assert results[0].source == SourceType.LIBGEN
            assert (
                results[0].download_url == "https://example.com/download/abc123def456"
            )

    @pytest.mark.asyncio
    async def test_search_empty_returns_empty_list(self, config):
        """Search with no results should return empty list."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = []
            mock_search_class.return_value = mock_instance

            results = await adapter.search("nonexistent_book_xyz123")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_uses_asyncio_to_thread(self, config, mock_book):
        """Search should wrap sync call in asyncio.to_thread()."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = [mock_book]
            mock_search_class.return_value = mock_instance

            with patch("lib.sources.libgen.asyncio.to_thread") as mock_to_thread:
                # Make to_thread actually call the function
                async def call_func(func, *args, **kwargs):
                    return func(*args, **kwargs)

                mock_to_thread.side_effect = call_func

                await adapter.search("python")

                # Verify to_thread was called
                mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_handles_missing_attributes(self, config):
        """Search should handle books with missing attributes gracefully."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        # Book with minimal attributes
        minimal_book = MagicMock(spec=[])  # Empty spec means no attributes
        minimal_book.configure_mock(**{})

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = [minimal_book]
            mock_search_class.return_value = mock_instance

            results = await adapter.search("python")

            # Should not raise, should use empty defaults
            assert len(results) == 1
            assert results[0].md5 == ""
            assert results[0].title == ""
            assert results[0].source == SourceType.LIBGEN


class TestLibgenAdapterDownload:
    """Tests for LibgenAdapter.get_download_url() method."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SourceConfig(
            libgen_mirror="li",
            default_source="libgen",
            fallback_enabled=False,
        )

    @pytest.fixture
    def mock_book(self):
        """Create a mock book result from LibgenSearch."""
        book = MagicMock()
        book.md5 = "abc123def456"
        book.title = "Python Programming"
        book.tor_download_link = "https://example.com/download/abc123def456"
        return book

    @pytest.mark.asyncio
    async def test_get_download_url_returns_result(self, config, mock_book):
        """get_download_url should return DownloadResult with URL."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = [mock_book]
            mock_search_class.return_value = mock_instance

            result = await adapter.get_download_url("abc123def456")

            assert result.url == "https://example.com/download/abc123def456"
            assert result.source == SourceType.LIBGEN
            assert result.quota_info is None  # LibGen has no quota

    @pytest.mark.asyncio
    async def test_get_download_url_not_found_raises(self, config):
        """get_download_url should raise when book not found."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = []
            mock_search_class.return_value = mock_instance

            with pytest.raises(ValueError, match="not found"):
                await adapter.get_download_url("nonexistent123")

    @pytest.mark.asyncio
    async def test_get_download_url_uses_mirrors_fallback(self, config):
        """get_download_url should fall back to mirrors if tor_download_link empty."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        book = MagicMock()
        book.md5 = "abc123def456"
        book.tor_download_link = ""
        book.mirrors = {"mirror1": "https://mirror1.com/download"}

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = [book]
            mock_search_class.return_value = mock_instance

            result = await adapter.get_download_url("abc123def456")

            assert result.url == "https://mirror1.com/download"


class TestLibgenAdapterRateLimiting:
    """Tests for LibgenAdapter rate limiting."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SourceConfig(
            libgen_mirror="li",
            default_source="libgen",
            fallback_enabled=False,
        )

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self, config):
        """Second request should wait for MIN_REQUEST_INTERVAL."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)

        with patch("lib.sources.libgen.LibgenSearch") as mock_search_class:
            mock_instance = MagicMock()
            mock_instance.search_title.return_value = []
            mock_search_class.return_value = mock_instance

            with patch("lib.sources.libgen.asyncio.sleep") as mock_sleep:
                # First request
                await adapter.search("python")

                # Force _last_request to be recent
                import time

                adapter._last_request = time.time()

                # Second request should trigger sleep
                await adapter.search("java")

                # Sleep should have been called
                mock_sleep.assert_called()


class TestLibgenAdapterInterface:
    """Tests verifying LibgenAdapter implements SourceAdapter interface."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SourceConfig(
            libgen_mirror="li",
            default_source="libgen",
            fallback_enabled=False,
        )

    def test_implements_source_adapter(self, config):
        """LibgenAdapter should implement SourceAdapter ABC."""
        from lib.sources.base import SourceAdapter
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)
        assert isinstance(adapter, SourceAdapter)

    @pytest.mark.asyncio
    async def test_close_is_callable(self, config):
        """LibgenAdapter.close() should be callable without error."""
        from lib.sources.libgen import LibgenAdapter

        adapter = LibgenAdapter(config)
        await adapter.close()  # Should not raise
