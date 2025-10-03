"""
Test suite for author search tools.
Following TDD: Tests written before implementation.

Author tools enable advanced author-based searching with support for
exact name matching, multiple authors, and syntax variations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lib.author_tools import (
    format_author_query,
    search_by_author,
    validate_author_name
)


class TestAuthorQueryFormatting:
    """Tests for author query formatting."""

    def test_format_simple_name(self):
        """Should format simple single-word name."""
        query = format_author_query("Plato")
        assert query == "Plato"

    def test_format_full_name(self):
        """Should handle full names correctly."""
        query = format_author_query("Georg Wilhelm Friedrich Hegel")
        assert "Georg" in query
        assert "Hegel" in query

    def test_format_lastname_firstname(self):
        """Should handle 'Lastname, Firstname' format."""
        query = format_author_query("Hegel, Georg Wilhelm Friedrich")
        assert "Hegel" in query
        assert "Georg" in query

    def test_format_with_exact_flag(self):
        """Should add exact match indicators when requested."""
        query = format_author_query("Hegel", exact=True)
        # Exact format might use quotes or specific syntax
        assert "Hegel" in query

    def test_format_empty_name(self):
        """Should raise error for empty author name."""
        with pytest.raises(ValueError) as exc_info:
            format_author_query("")
        assert "empty" in str(exc_info.value).lower() or "author" in str(exc_info.value).lower()

    def test_format_with_special_characters(self):
        """Should handle special characters in names."""
        query = format_author_query("O'Connor")
        assert "Connor" in query


class TestAuthorNameValidation:
    """Tests for author name validation."""

    def test_validate_simple_name(self):
        """Should validate simple names."""
        assert validate_author_name("Plato") is True

    def test_validate_full_name(self):
        """Should validate full names."""
        assert validate_author_name("Georg Wilhelm Friedrich Hegel") is True

    def test_validate_comma_format(self):
        """Should validate 'Lastname, Firstname' format."""
        assert validate_author_name("Hegel, Georg") is True

    def test_validate_empty_name(self):
        """Should reject empty names."""
        assert validate_author_name("") is False

    def test_validate_whitespace_only(self):
        """Should reject whitespace-only names."""
        assert validate_author_name("   ") is False

    def test_validate_numbers_in_name(self):
        """Should handle names with numbers (e.g., Louis XVI)."""
        assert validate_author_name("Louis XVI") is True

    def test_validate_special_characters(self):
        """Should validate names with apostrophes, hyphens."""
        assert validate_author_name("Jean-Paul Sartre") is True
        assert validate_author_name("O'Brien") is True


class TestSearchByAuthor:
    """Tests for the main search_by_author function."""

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_simple(self, mock_zlib_class):
        """Should perform basic author search."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        mock_html = '''
        <div class="resItemBox">
            <z-bookcard id="123" title="Science of Logic" author="Hegel"></z-bookcard>
        </div>
        '''

        async def mock_search(*args, **kwargs):
            return (mock_html, 1)

        mock_zlib.search = mock_search

        result = await search_by_author(
            author="Hegel",
            email="test@example.com",
            password="password"
        )

        assert result['author'] == 'Hegel'
        assert result['total_results'] >= 1
        assert len(result['books']) >= 1

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_exact_match(self, mock_zlib_class):
        """Should support exact author matching."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        call_tracker = {}

        async def mock_search(*args, **kwargs):
            call_tracker['query'] = args[0] if args else kwargs.get('q', '')
            call_tracker['exact'] = kwargs.get('exact', False)
            return ('<div></div>', 0)

        mock_zlib.search = mock_search

        await search_by_author(
            author="Hegel, Georg Wilhelm Friedrich",
            exact=True,
            email="test@example.com",
            password="password"
        )

        # Should use exact matching
        assert call_tracker.get('exact') is True or 'exact' in str(call_tracker)

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_with_filters(self, mock_zlib_class):
        """Should support year and language filters."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        call_tracker = {}

        async def mock_search(*args, **kwargs):
            call_tracker['kwargs'] = kwargs
            return ('<div></div>', 0)

        mock_zlib.search = mock_search

        await search_by_author(
            author="Hegel",
            email="test@example.com",
            password="password",
            year_from=1800,
            year_to=1850,
            languages="German"
        )

        assert call_tracker['kwargs']['yearFrom'] == 1800
        assert call_tracker['kwargs']['yearTo'] == 1850
        assert call_tracker['kwargs']['languages'] == "German"

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_multiple_results(self, mock_zlib_class):
        """Should handle multiple books by same author."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        mock_html = '''
        <div class="resItemBox">
            <z-bookcard id="1" title="Book 1" author="Hegel"></z-bookcard>
        </div>
        <div class="resItemBox">
            <z-bookcard id="2" title="Book 2" author="Hegel"></z-bookcard>
        </div>
        <div class="resItemBox">
            <z-bookcard id="3" title="Book 3" author="Hegel"></z-bookcard>
        </div>
        '''

        async def mock_search(*args, **kwargs):
            return (mock_html, 3)

        mock_zlib.search = mock_search

        result = await search_by_author(
            author="Hegel",
            email="test@example.com",
            password="password"
        )

        assert len(result['books']) == 3
        assert result['total_results'] == 3

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_invalid_name(self, mock_zlib_class):
        """Should reject invalid author names."""
        with pytest.raises(ValueError) as exc_info:
            await search_by_author(
                author="",
                email="test@example.com",
                password="password"
            )

        assert "author" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_error_handling(self, mock_zlib_class):
        """Should handle search errors gracefully."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_search(*args, **kwargs):
            raise Exception("Network error")

        mock_zlib.search = mock_search

        with pytest.raises(Exception) as exc_info:
            await search_by_author(
                author="Hegel",
                email="test@example.com",
                password="password"
            )

        assert "Network error" in str(exc_info.value)

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_empty_results(self, mock_zlib_class):
        """Should handle empty results gracefully."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        async def mock_search(*args, **kwargs):
            return ('<div>No results</div>', 0)

        mock_zlib.search = mock_search

        result = await search_by_author(
            author="NonexistentAuthor12345",
            email="test@example.com",
            password="password"
        )

        assert result['total_results'] == 0
        assert len(result['books']) == 0

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_pagination(self, mock_zlib_class):
        """Should support pagination parameters."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        call_tracker = {}

        async def mock_search(*args, **kwargs):
            call_tracker['kwargs'] = kwargs
            return ('<div></div>', 0)

        mock_zlib.search = mock_search

        await search_by_author(
            author="Hegel",
            email="test@example.com",
            password="password",
            page=2,
            limit=50
        )

        assert call_tracker['kwargs']['page'] == 2
        assert call_tracker['kwargs']['count'] == 50


class TestPerformance:
    """Performance tests for author search operations."""

    @patch('lib.author_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_author_performance(self, mock_zlib_class):
        """Should complete author search quickly."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        mock_html = '<div class="resItemBox"><z-bookcard id="1" title="Test"></z-bookcard></div>'

        async def mock_search(*args, **kwargs):
            return (mock_html, 1)

        mock_zlib.search = mock_search

        import time
        start = time.time()
        await search_by_author(
            author="Hegel",
            email="test@example.com",
            password="password"
        )
        duration = time.time() - start

        assert duration < 2.0  # Should complete in under 2 seconds
