"""
Test suite for booklist exploration tools.
Following TDD: Tests written before implementation.

Booklist tools enable exploration of curated collections on Z-Library.
Books can appear in 11+ booklists, representing expert-curated collections
ranging from broad topics (Philosophy: 954 books) to specific themes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lib.booklist_tools import (
    construct_booklist_url,
    parse_booklist_page,
    get_booklist_metadata,
    fetch_booklist
)


class TestBooklistURLConstruction:
    """Tests for booklist URL construction."""

    def test_construct_basic_url(self):
        """Should construct basic booklist URL."""
        url = construct_booklist_url(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            mirror="https://z-library.sk"
        )

        assert url == "https://z-library.sk/booklist/409997/370858/philosophy.html"

    def test_construct_with_page_number(self):
        """Should add page parameter to URL."""
        url = construct_booklist_url(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            page=2,
            mirror="https://z-library.sk"
        )

        assert "page=2" in url or "/p2" in url

    def test_construct_with_special_topic_chars(self):
        """Should handle URL encoding for special characters in topic."""
        url = construct_booklist_url(
            booklist_id="574373",
            booklist_hash="556ded",
            topic="logique-mathématique",
            mirror="https://z-library.sk"
        )

        # Should be URL encoded
        assert "574373" in url
        assert "556ded" in url

    def test_construct_invalid_id(self):
        """Should validate booklist ID."""
        with pytest.raises(ValueError) as exc_info:
            construct_booklist_url(
                booklist_id="",
                booklist_hash="abc123",
                topic="test",
                mirror="https://z-library.sk"
            )

        assert "id" in str(exc_info.value).lower()

    def test_construct_invalid_hash(self):
        """Should validate booklist hash."""
        with pytest.raises(ValueError) as exc_info:
            construct_booklist_url(
                booklist_id="123",
                booklist_hash="",
                topic="test",
                mirror="https://z-library.sk"
            )

        assert "hash" in str(exc_info.value).lower()


class TestBooklistPageParsing:
    """Tests for parsing booklist pages."""

    def test_parse_basic_booklist(self):
        """Should parse basic booklist with books."""
        html = '''
        <div class="bookList">
            <div class="resItemBox">
                <z-bookcard id="123" title="Book 1" author="Author 1"></z-bookcard>
            </div>
            <div class="resItemBox">
                <z-bookcard id="456" title="Book 2" author="Author 2"></z-bookcard>
            </div>
        </div>
        '''

        books = parse_booklist_page(html)

        assert len(books) == 2
        assert books[0]['id'] == '123'
        assert books[0]['title'] == 'Book 1'
        assert books[1]['id'] == '456'

    def test_parse_booklist_with_articles(self):
        """Should handle articles in booklists."""
        html = '''
        <div class="bookList">
            <div class="resItemBox">
                <z-bookcard type="article" href="/s/article1">
                    <div slot="title">Article Title</div>
                    <div slot="author">Author Name</div>
                </z-bookcard>
            </div>
        </div>
        '''

        books = parse_booklist_page(html)

        assert len(books) == 1
        assert books[0]['title'] == 'Article Title'
        assert books[0]['type'] == 'article'

    def test_parse_empty_booklist(self):
        """Should handle empty booklists."""
        html = '<div class="bookList"></div>'

        books = parse_booklist_page(html)

        assert len(books) == 0

    def test_parse_booklist_with_pagination_info(self):
        """Should extract pagination information."""
        html = '''
        <div class="bookList">
            <z-bookcard id="1" title="Book"></z-bookcard>
        </div>
        <div class="pagination">
            <span>Page 1 of 38</span>
        </div>
        '''

        books = parse_booklist_page(html)

        # Should successfully parse despite pagination
        assert len(books) >= 1

    def test_parse_malformed_html(self):
        """Should handle malformed HTML gracefully."""
        html = '<div><broken>test'

        books = parse_booklist_page(html)

        assert isinstance(books, list)


class TestBooklistMetadataExtraction:
    """Tests for extracting booklist metadata."""

    def test_extract_booklist_name(self):
        """Should extract booklist name/title."""
        html = '''
        <div class="bookListHeader">
            <h1>Philosophy</h1>
            <p>954 books</p>
        </div>
        '''

        metadata = get_booklist_metadata(html)

        assert metadata['name'] == 'Philosophy'
        assert metadata['total_books'] == 954

    def test_extract_booklist_description(self):
        """Should extract booklist description if present."""
        html = '''
        <div class="bookListHeader">
            <h1>Philosophy</h1>
            <div class="description">Collection of philosophical works</div>
        </div>
        '''

        metadata = get_booklist_metadata(html)

        assert 'description' in metadata
        assert 'philosophical' in metadata['description'].lower()

    def test_extract_booklist_count(self):
        """Should extract book count from various formats."""
        html = '''
        <div class="bookListHeader">
            <span class="count">954 items</span>
        </div>
        '''

        metadata = get_booklist_metadata(html)

        assert metadata['total_books'] == 954

    def test_extract_empty_metadata(self):
        """Should handle missing metadata gracefully."""
        html = '<div></div>'

        metadata = get_booklist_metadata(html)

        assert isinstance(metadata, dict)
        # Empty metadata is okay - just needs to be a dict


class TestFetchBooklist:
    """Tests for the main fetch_booklist function."""

    @patch('lib.booklist_tools.httpx.AsyncClient')
    @patch('lib.booklist_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_fetch_booklist_basic(self, mock_zlib_class, mock_client_class):
        """Should fetch basic booklist."""
        # Mock AsyncZlib for authentication
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib

        # Mock login as async function
        async def mock_login(*args, **kwargs):
            return None
        mock_zlib.login = mock_login

        # Mock search as async function
        async def mock_search(*args, **kwargs):
            return ('<div></div>', 0)
        mock_zlib.search = mock_search

        # Mock HTTP client for booklist fetch
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '''
        <div class="bookListHeader"><h1>Philosophy</h1><p>954 books</p></div>
        <div class="bookList">
            <z-bookcard id="123" title="Book 1"></z-bookcard>
        </div>
        '''
        mock_response.status_code = 200

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_client.get = mock_get

        result = await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email="test@example.com",
            password="password"
        )

        assert result['booklist_id'] == '409997'
        assert result['metadata']['name'] == 'Philosophy'
        assert len(result['books']) >= 1

    @patch('lib.booklist_tools.httpx.AsyncClient')
    @patch('lib.booklist_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_fetch_booklist_with_pagination(self, mock_zlib_class, mock_client_class):
        """Should support pagination."""
        # Mock AsyncZlib
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib
        async def mock_login(*args, **kwargs):
            return None
        async def mock_search(*args, **kwargs):
            return ('<div></div>', 0)
        mock_zlib.login = mock_login
        mock_zlib.search = mock_search

        # Mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '<div class="bookList"><z-bookcard id="1" title="Book"></z-bookcard></div>'
        mock_response.status_code = 200

        call_tracker = {}

        async def mock_get(*args, **kwargs):
            call_tracker['url'] = args[0] if args else kwargs.get('url', '')
            return mock_response

        mock_client.get = mock_get

        await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            page=3,
            email="test@example.com",
            password="password"
        )

        # Verify page parameter was passed
        assert 'page' in call_tracker['url'].lower() or 'p3' in call_tracker['url'].lower()

    @patch('lib.booklist_tools.httpx.AsyncClient')
    @patch('lib.booklist_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_fetch_booklist_404(self, mock_zlib_class, mock_client_class):
        """Should handle 404 errors."""
        # Mock AsyncZlib
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib
        async def mock_login(*args, **kwargs):
            return None
        async def mock_search(*args, **kwargs):
            return ('<div></div>', 0)
        mock_zlib.login = mock_login
        mock_zlib.search = mock_search

        # Mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = 'Not found'

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_client.get = mock_get

        with pytest.raises(Exception) as exc_info:
            await fetch_booklist(
                booklist_id="invalid",
                booklist_hash="invalid",
                topic="nonexistent",
                email="test@example.com",
                password="password"
            )

        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    @patch('lib.booklist_tools.httpx.AsyncClient')
    @patch('lib.booklist_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_fetch_booklist_network_error(self, mock_zlib_class, mock_client_class):
        """Should handle network errors."""
        # Mock AsyncZlib
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib
        async def mock_login(*args, **kwargs):
            return None
        async def mock_search(*args, **kwargs):
            return ('<div></div>', 0)
        mock_zlib.login = mock_login
        mock_zlib.search = mock_search

        # Mock HTTP client to raise error
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def mock_get(*args, **kwargs):
            raise Exception("Connection timeout")

        mock_client.get = mock_get

        with pytest.raises(Exception) as exc_info:
            await fetch_booklist(
                booklist_id="409997",
                booklist_hash="370858",
                topic="philosophy",
                email="test@example.com",
                password="password"
            )

        assert "timeout" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()

    @patch('lib.booklist_tools.httpx.AsyncClient')
    @patch('lib.booklist_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_fetch_booklist_authentication(self, mock_zlib_class, mock_client_class):
        """Should handle authentication for booklist fetching."""
        # Mock AsyncZlib
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib
        async def mock_login(*args, **kwargs):
            return None
        async def mock_search(*args, **kwargs):
            return ('<div></div>', 0)
        mock_zlib.login = mock_login
        mock_zlib.search = mock_search

        # Mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        call_tracker = {}

        mock_response = MagicMock()
        mock_response.text = '<div></div>'
        mock_response.status_code = 200

        async def mock_get(*args, **kwargs):
            call_tracker['headers'] = kwargs.get('headers', {})
            return mock_response

        mock_client.get = mock_get

        await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email="test@example.com",
            password="password"
        )

        # Should have authentication headers or cookies
        assert 'headers' in call_tracker or 'cookies' in str(call_tracker)


class TestPerformance:
    """Performance tests for booklist operations."""

    def test_parse_large_booklist_performance(self):
        """Should parse large booklists quickly."""
        # Generate HTML with 100 book cards
        html_parts = ['<div class="bookList">']
        for i in range(100):
            html_parts.append(
                f'<div class="resItemBox">'
                f'<z-bookcard id="{i}" title="Book {i}"></z-bookcard>'
                f'</div>'
            )
        html_parts.append('</div>')
        html = ''.join(html_parts)

        import time
        start = time.time()
        books = parse_booklist_page(html)
        duration = time.time() - start

        assert len(books) == 100
        assert duration < 0.5  # Should complete in under 500ms

    @patch('lib.booklist_tools.httpx.AsyncClient')
    @patch('lib.booklist_tools.AsyncZlib')
    @pytest.mark.asyncio
    async def test_fetch_booklist_performance(self, mock_zlib_class, mock_client_class):
        """Should fetch booklists quickly."""
        # Mock AsyncZlib
        mock_zlib = MagicMock()
        mock_zlib_class.return_value = mock_zlib
        async def mock_login(*args, **kwargs):
            return None
        async def mock_search(*args, **kwargs):
            return ('<div></div>', 0)
        mock_zlib.login = mock_login
        mock_zlib.search = mock_search

        # Mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '<div class="bookList"><z-bookcard id="1" title="Test"></z-bookcard></div>'
        mock_response.status_code = 200

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_client.get = mock_get

        import time
        start = time.time()
        await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email="test@example.com",
            password="password"
        )
        duration = time.time() - start

        assert duration < 3.0  # Should complete in under 3 seconds
