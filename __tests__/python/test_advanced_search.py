"""
Test suite for advanced search functionality with fuzzy match detection.
Following TDD: Tests written before implementation.
"""

import pytest
from unittest.mock import MagicMock
from lib.advanced_search import (
    detect_fuzzy_matches_line,
    separate_exact_and_fuzzy_results,
    search_books_advanced,
)


class MockAsyncClient:
    """Mock httpx.AsyncClient for testing."""

    def __init__(self, html_response):
        self.html = html_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url):
        mock_response = MagicMock()
        mock_response.text = self.html
        return mock_response


class MockPaginator:
    """Mock Paginator for AsyncZlib.search()"""

    def __init__(self, url="https://test.com"):
        self._SearchPaginator__url = url

    async def next(self):
        return []


class TestFuzzyMatchesLineDetection:
    """Tests for detecting the fuzzy matches divider in search results."""

    def test_detect_fuzzy_matches_line_present(self):
        """Should detect fuzzyMatchesLine when present in HTML."""
        html = """
        <div class="resItemBox">Book 1</div>
        <div class="resItemBox">Book 2</div>
        <div class="fuzzyMatchesLine">Maybe you are looking for these:</div>
        <div class="resItemBox">Book 3</div>
        """

        result = detect_fuzzy_matches_line(html)
        assert result is True

    def test_detect_fuzzy_matches_line_absent(self):
        """Should return False when no fuzzyMatchesLine present."""
        html = """
        <div class="resItemBox">Book 1</div>
        <div class="resItemBox">Book 2</div>
        <div class="resItemBox">Book 3</div>
        """

        result = detect_fuzzy_matches_line(html)
        assert result is False

    def test_detect_fuzzy_matches_empty_html(self):
        """Should handle empty HTML gracefully."""
        result = detect_fuzzy_matches_line("")
        assert result is False

    def test_detect_fuzzy_matches_none_html(self):
        """Should handle None HTML gracefully."""
        result = detect_fuzzy_matches_line(None)
        assert result is False


class TestSeparateExactAndFuzzyResults:
    """Tests for separating search results into exact and fuzzy matches."""

    def test_separate_with_fuzzy_line(self):
        """Should separate results when fuzzy line present."""
        html = """
        <div class="resItemBox exactResults">
            <z-bookcard id="1" title="Exact Match 1"></z-bookcard>
        </div>
        <div class="resItemBox exactResults">
            <z-bookcard id="2" title="Exact Match 2"></z-bookcard>
        </div>
        <div class="fuzzyMatchesLine">Maybe you are looking for these:</div>
        <div class="resItemBox">
            <z-bookcard id="3" title="Fuzzy Match 1"></z-bookcard>
        </div>
        <div class="resItemBox">
            <z-bookcard id="4" title="Fuzzy Match 2"></z-bookcard>
        </div>
        """

        exact, fuzzy = separate_exact_and_fuzzy_results(html)

        assert len(exact) == 2
        assert len(fuzzy) == 2
        assert exact[0]["id"] == "1"
        assert exact[1]["id"] == "2"
        assert fuzzy[0]["id"] == "3"
        assert fuzzy[1]["id"] == "4"

    def test_separate_without_fuzzy_line(self):
        """Should return all results as exact when no fuzzy line."""
        html = """
        <div class="resItemBox">
            <z-bookcard id="1" title="Book 1"></z-bookcard>
        </div>
        <div class="resItemBox">
            <z-bookcard id="2" title="Book 2"></z-bookcard>
        </div>
        """

        exact, fuzzy = separate_exact_and_fuzzy_results(html)

        assert len(exact) == 2
        assert len(fuzzy) == 0
        assert exact[0]["id"] == "1"
        assert exact[1]["id"] == "2"

    def test_separate_only_fuzzy_results(self):
        """Should handle case with only fuzzy results (no exact matches)."""
        html = """
        <div class="fuzzyMatchesLine">Maybe you are looking for these:</div>
        <div class="resItemBox">
            <z-bookcard id="1" title="Fuzzy Match 1"></z-bookcard>
        </div>
        """

        exact, fuzzy = separate_exact_and_fuzzy_results(html)

        assert len(exact) == 0
        assert len(fuzzy) == 1
        assert fuzzy[0]["id"] == "1"

    def test_separate_empty_html(self):
        """Should handle empty HTML gracefully."""
        exact, fuzzy = separate_exact_and_fuzzy_results("")

        assert len(exact) == 0
        assert len(fuzzy) == 0

    def test_separate_with_article_cards(self):
        """Should handle articles with slot-based structure."""
        html = """
        <div class="resItemBox">
            <z-bookcard type="article" href="/s/article1">
                <div slot="title">Article Title</div>
                <div slot="author">Author Name</div>
            </z-bookcard>
        </div>
        <div class="fuzzyMatchesLine">Maybe you are looking for these:</div>
        <div class="resItemBox">
            <z-bookcard id="2" title="Book"></z-bookcard>
        </div>
        """

        exact, fuzzy = separate_exact_and_fuzzy_results(html)

        assert len(exact) == 1
        assert len(fuzzy) == 1
        assert exact[0]["title"] == "Article Title"


class TestSearchBooksAdvanced:
    """Tests for the deprecated advanced search wrapper function."""

    @pytest.mark.asyncio
    async def test_search_advanced_raises_not_implemented(self):
        """search_books_advanced raises NotImplementedError after AsyncZlib removal."""
        with pytest.raises(NotImplementedError, match="AsyncZlib.*removed"):
            await search_books_advanced(
                query="test query", email="test@example.com", password="password"
            )


class TestPerformance:
    """Performance tests for advanced search operations."""

    def test_fuzzy_detection_performance(self):
        """Should detect fuzzy line quickly on large HTML."""
        # Generate HTML with 100 book cards
        html_parts = ['<div class="container">']
        for i in range(50):
            html_parts.append(
                f'<div class="resItemBox"><z-bookcard id="{i}"></z-bookcard></div>'
            )
        html_parts.append(
            '<div class="fuzzyMatchesLine">Maybe you are looking for these:</div>'
        )
        for i in range(50, 100):
            html_parts.append(
                f'<div class="resItemBox"><z-bookcard id="{i}"></z-bookcard></div>'
            )
        html_parts.append("</div>")
        html = "".join(html_parts)

        import time

        start = time.time()
        result = detect_fuzzy_matches_line(html)
        duration = time.time() - start

        assert result is True
        assert duration < 0.1  # Should complete in under 100ms

    def test_separation_performance(self):
        """Should separate results quickly on large result set."""
        html_parts = ['<div class="container">']
        for i in range(50):
            html_parts.append(
                f'<div class="resItemBox"><z-bookcard id="{i}" title="Book {i}"></z-bookcard></div>'
            )
        html_parts.append(
            '<div class="fuzzyMatchesLine">Maybe you are looking for these:</div>'
        )
        for i in range(50, 100):
            html_parts.append(
                f'<div class="resItemBox"><z-bookcard id="{i}" title="Book {i}"></z-bookcard></div>'
            )
        html_parts.append("</div>")
        html = "".join(html_parts)

        import time

        start = time.time()
        exact, fuzzy = separate_exact_and_fuzzy_results(html)
        duration = time.time() - start

        assert len(exact) == 50
        assert len(fuzzy) == 50
        assert duration < 0.2  # Should complete in under 200ms
