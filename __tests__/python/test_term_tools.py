"""
Test suite for term exploration tools.
Following TDD: Tests written before implementation.

Term exploration enables conceptual navigation through Z-Library's
60+ terms per book, allowing discovery based on philosophical/technical concepts.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from lib.term_tools import (
    construct_term_search_url,
    search_by_term,
    parse_term_search_results
)


class MockPaginator:
    """Mock Paginator object for testing."""

    def __init__(self, books):
        self.books = books

    async def next(self):
        return self.books


class TestTermURLConstruction:
    """Tests for term search URL construction."""

    def test_construct_single_word_term(self):
        """Should construct URL for single-word term."""
        url = construct_term_search_url("dialectic", mirror="https://z-library.sk")
        assert url == "https://z-library.sk/s/dialectic?e=1"

    def test_construct_multi_word_term(self):
        """Should handle multi-word terms with proper encoding."""
        url = construct_term_search_url("absolute knowledge", mirror="https://z-library.sk")
        # Space should be encoded
        assert "absolute" in url
        assert "knowledge" in url
        assert "?e=1" in url

    def test_construct_term_with_special_chars(self):
        """Should properly encode special characters in terms."""
        url = construct_term_search_url("being-in-itself", mirror="https://z-library.sk")
        assert "being" in url.lower()
        assert "itself" in url.lower()

    def test_construct_with_custom_mirror(self):
        """Should respect custom mirror parameter."""
        url = construct_term_search_url("dialectic", mirror="https://custom-mirror.org")
        assert url.startswith("https://custom-mirror.org")

    def test_construct_empty_term(self):
        """Should handle empty term gracefully."""
        with pytest.raises(ValueError) as exc_info:
            construct_term_search_url("", mirror="https://z-library.sk")
        assert "empty" in str(exc_info.value).lower() or "term" in str(exc_info.value).lower()


class TestTermSearchResultParsing:
    """Tests for parsing term search results."""

    def test_parse_basic_results(self):
        """Should parse basic book results from term search."""
        html = '''
        <div class="resItemBox">
            <z-bookcard id="123" title="Book on Dialectic" author="Hegel"></z-bookcard>
        </div>
        <div class="resItemBox">
            <z-bookcard id="456" title="More Dialectic" author="Marx"></z-bookcard>
        </div>
        '''

        results = parse_term_search_results(html)

        assert len(results) == 2
        assert results[0]['id'] == '123'
        assert results[0]['title'] == 'Book on Dialectic'
        assert results[1]['id'] == '456'

    def test_parse_with_fuzzy_matches(self):
        """Should handle fuzzy matches in term search."""
        html = '''
        <div class="resItemBox">
            <z-bookcard id="123" title="Exact"></z-bookcard>
        </div>
        <div class="fuzzyMatchesLine">Maybe you are looking for these:</div>
        <div class="resItemBox">
            <z-bookcard id="456" title="Fuzzy"></z-bookcard>
        </div>
        '''

        results = parse_term_search_results(html)

        # Should include both exact and fuzzy
        assert len(results) == 2

    def test_parse_empty_results(self):
        """Should handle empty results gracefully."""
        html = '<div class="searchContent">No results found</div>'

        results = parse_term_search_results(html)

        assert len(results) == 0

    def test_parse_malformed_html(self):
        """Should handle malformed HTML without crashing."""
        html = '<div><broken<tag>test</div>'

        results = parse_term_search_results(html)

        # Should return empty list, not crash
        assert isinstance(results, list)

    def test_parse_with_articles(self):
        """Should parse articles alongside books in term results."""
        html = '''
        <div class="resItemBox">
            <z-bookcard type="article" href="/s/article1">
                <div slot="title">Article on Dialectic</div>
                <div slot="author">Author Name</div>
            </z-bookcard>
        </div>
        <div class="resItemBox">
            <z-bookcard id="123" title="Book Title"></z-bookcard>
        </div>
        '''

        results = parse_term_search_results(html)

        assert len(results) == 2
        assert results[0]['title'] == 'Article on Dialectic'
        assert results[0]['type'] == 'article'
        assert results[1]['type'] == 'book'


class TestSearchByTerm:
    """Tests for the main search_by_term function."""

    @patch('lib.term_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_by_term_basic(self, mock_zlib_class):
        """Should perform basic term search."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib


        # Mock login

        mock_zlib.login = AsyncMock()


        mock_html = '''
        <div class="resItemBox">
            <z-bookcard id="123" title="Dialectic Book"></z-bookcard>
        </div>
        '''

        async def mock_search(*args, **kwargs):
            return MockPaginator([{'id': '1', 'name': 'Dialectic Book', 'authors': ['Test']}])

        mock_zlib.search = mock_search

        result = await search_by_term(
            term="dialectic",
            email="test@example.com",
            password="password"
        )

        assert result['term'] == 'dialectic'
        assert result['total_results'] >= 1
        assert len(result['books']) >= 1
        # Books from Paginator have 'name' field
        assert result['books'][0]['name'] == 'Dialectic Book'

    @patch('lib.term_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_by_term_with_limit(self, mock_zlib_class):
        """Should respect limit parameter."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Mock login
        mock_zlib.login = AsyncMock()

        call_tracker = {}

        async def mock_search(*args, **kwargs):
            call_tracker['kwargs'] = kwargs
            return MockPaginator([])

        mock_zlib.search = mock_search

        await search_by_term(
            term="dialectic",
            email="test@example.com",
            password="password",
            limit=50
        )

        assert call_tracker['kwargs']['count'] == 50

    @patch('lib.term_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_by_term_with_filters(self, mock_zlib_class):
        """Should support language and year filters."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Mock login
        mock_zlib.login = AsyncMock()

        call_tracker = {}

        async def mock_search(*args, **kwargs):
            call_tracker['kwargs'] = kwargs
            return MockPaginator([])

        mock_zlib.search = mock_search

        await search_by_term(
            term="dialectic",
            email="test@example.com",
            password="password",
            year_from=2000,
            year_to=2023,
            languages="English"
        )

        # Check actual parameter names used by AsyncZlib.search
        assert call_tracker['kwargs']['from_year'] == 2000
        assert call_tracker['kwargs']['to_year'] == 2023
        assert 'English' in str(call_tracker['kwargs'].get('lang', []))

    @patch('lib.term_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_by_term_error_handling(self, mock_zlib_class):
        """Should handle search errors gracefully."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib


        # Mock login

        mock_zlib.login = AsyncMock()


        async def mock_search(*args, **kwargs):
            raise Exception("Network error")

        mock_zlib.search = mock_search

        with pytest.raises(Exception) as exc_info:
            await search_by_term(
                term="dialectic",
                email="test@example.com",
                password="password"
            )

        assert "Network error" in str(exc_info.value)

    @patch('lib.term_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_by_term_empty_results(self, mock_zlib_class):
        """Should handle empty results gracefully."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib


        # Mock login

        mock_zlib.login = AsyncMock()


        async def mock_search(*args, **kwargs):
            return MockPaginator([])

        mock_zlib.search = mock_search

        result = await search_by_term(
            term="nonexistentterm12345",
            email="test@example.com",
            password="password"
        )

        assert result['total_results'] == 0
        assert len(result['books']) == 0


class TestPerformance:
    """Performance tests for term search operations."""

    def test_parse_performance_large_results(self):
        """Should parse large result sets quickly."""
        # Generate HTML with 100 book cards
        html_parts = ['<div class="container">']
        for i in range(100):
            html_parts.append(
                f'<div class="resItemBox">'
                f'<z-bookcard id="{i}" title="Book {i}" author="Author {i}"></z-bookcard>'
                f'</div>'
            )
        html_parts.append('</div>')
        html = ''.join(html_parts)

        import time
        start = time.time()
        results = parse_term_search_results(html)
        duration = time.time() - start

        assert len(results) == 100
        assert duration < 0.5  # Should complete in under 500ms

    @patch('lib.term_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_search_performance(self, mock_zlib_class):
        """Should complete term search quickly."""
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib


        # Mock login

        mock_zlib.login = AsyncMock()


        mock_html = '<div class="resItemBox"><z-bookcard id="1" title="Test"></z-bookcard></div>'

        async def mock_search(*args, **kwargs):
            return MockPaginator([{'id': '1', 'name': 'Test', 'authors': ['Test']}])

        mock_zlib.search = mock_search

        import time
        start = time.time()
        await search_by_term(
            term="dialectic",
            email="test@example.com",
            password="password"
        )
        duration = time.time() - start

        assert duration < 2.0  # Should complete in under 2 seconds
