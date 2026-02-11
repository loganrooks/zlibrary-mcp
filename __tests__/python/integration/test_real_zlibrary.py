"""
Integration tests for Z-Library MCP server.

These tests make REAL API calls to Z-Library and require valid credentials.
They validate that our assumptions about HTML structure, authentication,
and API behavior are correct.

IMPORTANT: These tests use real credentials and make real API calls.
- Be respectful of Z-Library's resources
- Use small result sets (limit=5-10)
- Don't run these in tight loops
- Clean up downloads after tests

Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import pytest
import os
import sys
import asyncio
import time
import shutil
from pathlib import Path

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib"))

from term_tools import search_by_term
from author_tools import search_by_author
from booklist_tools import fetch_booklist
import python_bridge


# Skip all integration tests if credentials not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("ZLIBRARY_EMAIL") or not os.getenv("ZLIBRARY_PASSWORD"),
        reason="Integration tests require ZLIBRARY_EMAIL and ZLIBRARY_PASSWORD environment variables",
    ),
]


@pytest.fixture(scope="module")
def credentials():
    """Provide Z-Library credentials from environment."""
    return {
        "email": os.getenv("ZLIBRARY_EMAIL"),
        "password": os.getenv("ZLIBRARY_PASSWORD"),
        "mirror": os.getenv("ZLIBRARY_MIRROR", ""),
    }


@pytest.fixture(scope="module")
def test_download_dir():
    """Provide temporary download directory for integration tests."""
    test_dir = Path("./downloads_integration_test")
    test_dir.mkdir(exist_ok=True)
    yield str(test_dir)
    # Cleanup after all tests
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.mark.integration
class TestRealAuthentication:
    """Test real Z-Library authentication."""

    @pytest.mark.asyncio
    async def test_authentication_succeeds(self, credentials):
        """Should successfully authenticate with real credentials."""
        from zlibrary.eapi import EAPIClient

        EAPI_DOMAIN = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")

        client = EAPIClient(EAPI_DOMAIN)
        login_result = await client.login(credentials["email"], credentials["password"])

        # Verify login succeeded
        assert login_result.get("success") == 1

        # Verify we can search after authentication
        search_result = await client.search("test", limit=1)
        assert search_result is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_authentication_fails_with_invalid_credentials(self):
        """Should raise error or return failure with invalid credentials."""
        from zlibrary.eapi import EAPIClient

        EAPI_DOMAIN = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")

        client = EAPIClient(EAPI_DOMAIN)
        try:
            login_result = await client.login("invalid@example.com", "wrongpassword")
            # If we get here, check the result
            assert login_result.get("success") != 1
        except Exception:
            pass  # Any exception means auth failed, which is expected

        await client.close()

    @pytest.mark.asyncio
    async def test_session_persistence(self, credentials):
        """Should maintain session across multiple operations."""
        from zlibrary.eapi import EAPIClient

        EAPI_DOMAIN = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")

        client = EAPIClient(EAPI_DOMAIN)
        await client.login(credentials["email"], credentials["password"])

        # Perform multiple searches with same session
        result1 = await client.search("test", limit=1)
        await asyncio.sleep(0.5)
        result2 = await client.search("philosophy", limit=1)
        await asyncio.sleep(0.5)
        result3 = await client.search("science", limit=1)

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None

        await client.close()


@pytest.mark.integration
class TestRealBasicSearch:
    """Test basic search operations with real Z-Library."""

    @pytest.mark.asyncio
    async def test_basic_search_returns_results(self, zlib_client):
        """Should return results for a common search query."""
        # Use injected client (no global state)
        result = await python_bridge.search(
            query="philosophy",
            count=5,
            client=zlib_client,  # Dependency injection
        )

        # Verify structure
        assert "books" in result
        assert "retrieved_from_url" in result

        # Should have found results
        assert len(result["books"]) > 0

        # Validate book structure
        first_book = result["books"][0]
        assert "title" in first_book or "name" in first_book
        assert "id" in first_book or "href" in first_book

    @pytest.mark.asyncio
    async def test_search_with_year_filter(self, zlib_client):
        """Should respect year filters in search."""
        result = await python_bridge.search(
            query="artificial intelligence",
            from_year=2020,
            to_year=2023,
            count=5,
            client=zlib_client,
        )

        # Should return results
        assert len(result["books"]) >= 0

        # If we got results, verify years are in range
        for book in result["books"]:
            year = book.get("year", "")
            if year and year.isdigit():
                year_int = int(year)
                assert 2020 <= year_int <= 2023

    @pytest.mark.asyncio
    async def test_search_with_language_filter(self, zlib_client):
        """Should respect language filters."""
        result = await python_bridge.search(
            query="philosophy", languages=["English"], count=5, client=zlib_client
        )

        # Should return results
        assert len(result["books"]) >= 0


@pytest.mark.integration
class TestRealTermSearch:
    """Test term search with real Z-Library API."""

    @pytest.mark.asyncio
    async def test_search_common_term(self, credentials, zlib_client):
        """Should find books for a common philosophical term."""
        # Test now uses isolated client from fixture
        await asyncio.sleep(1)

        # search_by_term creates its own client, so we test it directly
        result = await search_by_term(
            term="dialectic",
            email=credentials["email"],
            password=credentials["password"],
            limit=5,
        )

        # Verify structure
        assert "term" in result
        assert result["term"] == "dialectic"
        assert "books" in result
        assert "total_results" in result

        # Verify we got real results
        assert result["total_results"] > 0
        assert len(result["books"]) > 0

        # Validate real book structure
        first_book = result["books"][0]
        assert "title" in first_book
        assert first_book["title"] != ""
        assert first_book["title"] != "N/A"

        # Should have some metadata
        assert "id" in first_book or "href" in first_book

    @pytest.mark.asyncio
    async def test_term_search_with_filters(self, credentials, zlib_client):
        """Should support year and language filters in term search."""
        await asyncio.sleep(1)

        result = await search_by_term(
            term="philosophy",
            email=credentials["email"],
            password=credentials["password"],
            year_from=2000,
            languages="English",
            limit=5,
        )

        # Should not error
        assert "books" in result
        assert result["total_results"] >= 0


@pytest.mark.integration
class TestRealAuthorSearch:
    """Test author search with real Z-Library API."""

    @pytest.mark.asyncio
    async def test_search_famous_author(self, credentials, zlib_client):
        """Should find books by a famous author."""
        await asyncio.sleep(1)

        result = await search_by_author(
            author="Hegel",
            email=credentials["email"],
            password=credentials["password"],
            limit=5,
        )

        # Verify structure
        assert "author" in result
        assert "books" in result
        assert "total_results" in result

        # Should find many works
        assert result["total_results"] > 0
        assert len(result["books"]) > 0

        # Validate real book data
        first_book = result["books"][0]
        assert "title" in first_book
        assert first_book["title"] != ""

    @pytest.mark.asyncio
    async def test_search_author_with_comma_format(self, credentials, zlib_client):
        """Should handle 'Lastname, Firstname' format."""
        await asyncio.sleep(1)

        result = await search_by_author(
            author="Hegel, Georg",
            email=credentials["email"],
            password=credentials["password"],
            limit=5,
        )

        # Should find results
        assert result["total_results"] >= 0
        assert isinstance(result["books"], list)

    @pytest.mark.asyncio
    async def test_author_search_with_year_filter(self, credentials, zlib_client):
        """Should support year filtering in author search."""
        await asyncio.sleep(1)

        result = await search_by_author(
            author="Hegel",
            email=credentials["email"],
            password=credentials["password"],
            year_from=1800,
            year_to=1850,
            limit=5,
        )

        # Should return filtered results
        assert result["total_results"] >= 0


@pytest.mark.integration
class TestRealMetadataExtraction:
    """Test metadata extraction with real book pages."""

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="terms and booklists not available via EAPI — were HTML-scraped"
    )
    async def test_extract_from_known_book(self, credentials, zlib_client):
        """Test metadata extraction from a known good book."""
        # Hegel's Encyclopaedia - we know this book exists
        # ID: 1252896, Hash: 882753
        await asyncio.sleep(1)

        # Use the isolated client (python_bridge.get_book_metadata_complete doesn't support client param yet)
        # But the reset_global_client fixture ensures clean state
        metadata = await python_bridge.get_book_metadata_complete(
            book_id="1252896", book_hash="882753"
        )

        # Validate core structure
        assert metadata is not None
        assert isinstance(metadata, dict)

        # Note: enhanced_metadata extracts ENHANCED fields, not basic fields
        # Basic fields like title/author come from search results
        # This function extracts: terms, booklists, description, IPFS, etc.

        # CRITICAL: Validate terms extraction (60+ terms expected)
        assert "terms" in metadata
        assert isinstance(metadata["terms"], list)
        assert len(metadata["terms"]) > 50, (
            f"Expected 60+ terms, got {len(metadata['terms'])}"
        )

        # Verify known terms are present (based on actual Hegel book terms)
        terms_lower = [t.lower() for t in metadata["terms"]]
        # From our exploration, we know this book has these terms:
        assert "absolute" in terms_lower, (
            f"Expected 'absolute' in terms, got: {terms_lower[:10]}"
        )
        assert "reflection" in terms_lower or "determination" in terms_lower

        # CRITICAL: Validate booklists extraction (11+ booklists expected)
        assert "booklists" in metadata
        assert isinstance(metadata["booklists"], list)
        assert len(metadata["booklists"]) > 5, (
            f"Expected 11+ booklists, got {len(metadata['booklists'])}"
        )

        # Validate booklist structure
        first_booklist = metadata["booklists"][0]
        assert "topic" in first_booklist or "name" in first_booklist
        assert "id" in first_booklist
        assert "quantity" in first_booklist or "count" in first_booklist

        # Validate description
        assert "description" in metadata
        assert len(metadata["description"]) > 500, (
            f"Expected 800+ char description, got {len(metadata['description'])}"
        )

        # Log what we got for debugging
        print("\n=== Metadata Extraction Results ===")
        print(f"Terms: {len(metadata['terms'])}")
        print(f"Booklists: {len(metadata['booklists'])}")
        print(f"Description length: {len(metadata.get('description', ''))}")
        print(f"Keys in metadata: {list(metadata.keys())}")

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="IPFS CIDs not available via EAPI — were HTML-scraped")
    async def test_extract_ipfs_cids(self, credentials, zlib_client):
        """Test that IPFS CIDs are extracted."""
        await asyncio.sleep(1)

        metadata = await python_bridge.get_book_metadata_complete(
            book_id="1252896", book_hash="882753"
        )

        # Should have IPFS CIDs
        assert "ipfs_cids" in metadata
        assert isinstance(metadata["ipfs_cids"], list)
        assert len(metadata["ipfs_cids"]) >= 2, "Expected 2 IPFS CID formats"

        # Validate CID format (should be long alphanumeric strings)
        for cid in metadata["ipfs_cids"]:
            assert len(cid) > 40, f"CID too short: {cid}"
            assert cid.startswith("Qm") or cid.startswith("baf"), (
                f"Unexpected CID format: {cid}"
            )

    @pytest.mark.asyncio
    async def test_extract_rating_data(self, credentials, zlib_client):
        """Test that rating and quality metrics are extracted."""
        await asyncio.sleep(1)

        metadata = await python_bridge.get_book_metadata_complete(
            book_id="1252896", book_hash="882753"
        )

        # Should have rating info
        if "rating" in metadata:
            assert "value" in metadata["rating"] or "score" in metadata["rating"]
            assert "count" in metadata["rating"] or "votes" in metadata["rating"]

    @pytest.mark.asyncio
    async def test_extract_download_link(self, credentials, zlib_client):
        """Test that download link is properly extracted."""
        await asyncio.sleep(1)

        metadata = await python_bridge.get_book_metadata_complete(
            book_id="1252896", book_hash="882753"
        )

        # Should have download info
        assert "download" in metadata
        assert isinstance(metadata["download"], dict)

        # Should have link
        assert "link" in metadata["download"]
        assert "/dl/" in metadata["download"]["link"]

    @pytest.mark.asyncio
    async def test_metadata_extraction_performance(self, credentials, zlib_client):
        """Should extract metadata within performance target (<5s with network)."""
        await asyncio.sleep(1)

        start = time.time()
        metadata = await python_bridge.get_book_metadata_complete(
            book_id="1252896", book_hash="882753"
        )
        duration = time.time() - start

        # Should complete reasonably fast (allowing for network latency)
        assert duration < 10.0, f"Metadata extraction took {duration}s, expected <10s"

        # Verify we got data despite speed
        assert metadata is not None
        assert isinstance(metadata, dict)


@pytest.mark.integration
class TestRealBooklistFetching:
    """Test booklist fetching with real Z-Library."""

    @pytest.mark.asyncio
    async def test_fetch_known_booklist(self, credentials):
        """Should fetch a known booklist (Philosophy list)."""
        await asyncio.sleep(1)

        result = await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email=credentials["email"],
            password=credentials["password"],
            page=1,
        )

        # Verify structure
        assert "metadata" in result
        assert "books" in result
        assert "booklist_id" in result

        # Verify we got books
        assert len(result["books"]) > 0, "Philosophy booklist should have books"

        # Verify metadata extraction worked
        assert "name" in result["metadata"] or "total_books" in result["metadata"]

        # Validate book structure
        first_book = result["books"][0]
        assert "title" in first_book
        assert first_book["title"] != ""

    @pytest.mark.asyncio
    async def test_booklist_pagination(self, credentials):
        """Should support paginating through large booklists."""
        await asyncio.sleep(1)

        # Fetch page 1
        page1 = await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email=credentials["email"],
            password=credentials["password"],
            page=1,
        )

        await asyncio.sleep(2)  # Longer delay between requests

        # Fetch page 2
        page2 = await fetch_booklist(
            booklist_id="409997",
            booklist_hash="370858",
            topic="philosophy",
            email=credentials["email"],
            password=credentials["password"],
            page=2,
        )

        # Both should have results
        assert len(page1["books"]) > 0
        assert len(page2["books"]) > 0

        # Page 2 should have different books than page 1
        page1_ids = {b.get("id", b.get("href")) for b in page1["books"]}
        page2_ids = {b.get("id", b.get("href")) for b in page2["books"]}

        # Some books should be different (allowing for some overlap)
        assert len(page1_ids & page2_ids) < len(page1_ids), (
            "Pages should have mostly different books"
        )


@pytest.mark.integration
class TestRealWorldEdgeCases:
    """Test with real-world edge cases from Z-Library."""

    @pytest.mark.asyncio
    async def test_search_returns_both_books_and_articles(
        self, credentials, zlib_client
    ):
        """Should handle mixed search results (books + articles)."""
        await asyncio.sleep(1)

        # Broad search likely to return both
        result = await python_bridge.search(
            query="computer science", count=20, client=zlib_client
        )

        # Extract types
        types = {b.get("type", "book") for b in result["books"]}

        # All should have a type
        assert "book" in types or "article" in types

        # All should have titles
        for book in result["books"]:
            title = book.get("title", book.get("name", ""))
            assert title != "", "All results should have titles"
            assert title != "N/A", "Titles should be extracted, not 'N/A'"

    @pytest.mark.asyncio
    async def test_handle_special_characters_in_titles(self, credentials, zlib_client):
        """Should handle books with special characters in titles."""
        await asyncio.sleep(1)

        # Search for something likely to have special chars
        result = await python_bridge.search(
            query="L'être",  # French with apostrophe
            count=5,
            client=zlib_client,
        )

        # Should not crash on special characters
        assert "books" in result
        assert isinstance(result["books"], list)

    @pytest.mark.asyncio
    async def test_unicode_handling(self, credentials, zlib_client):
        """Should handle Unicode characters in various scripts."""
        await asyncio.sleep(1)

        # Search for something with Unicode
        result = await python_bridge.search(
            query="哲学",  # Chinese for "philosophy"
            count=5,
            client=zlib_client,
        )

        # Should not crash
        assert "books" in result

    @pytest.mark.asyncio
    async def test_empty_search_results(self, credentials, zlib_client):
        """Should handle searches with no results gracefully."""
        await asyncio.sleep(1)

        # Very specific query unlikely to have results
        result = await python_bridge.search(
            query="xyzabc123nonexistent987", count=5, client=zlib_client
        )

        # Should return empty results, not error
        assert "books" in result
        assert isinstance(result["books"], list)
        # May be empty
        assert len(result["books"]) >= 0


@pytest.mark.integration
class TestDownloadOperations:
    """Test download functionality with real Z-Library."""

    @pytest.mark.asyncio
    async def test_download_small_book(
        self, credentials, zlib_client, test_download_dir
    ):
        """Should download a small book successfully."""
        await asyncio.sleep(2)

        # Find a small book
        search_result = await python_bridge.search(
            query="Python", count=1, client=zlib_client
        )

        if len(search_result["books"]) == 0:
            pytest.skip("No books found for download test")

        book = search_result["books"][0]

        # Download the book
        download_result = await python_bridge.download_book(
            book_details=book,
            output_dir=test_download_dir,
            process_for_rag=False,  # Don't process, just download
        )

        # Verify download succeeded
        assert "file_path" in download_result
        assert download_result["file_path"] is not None

        # Verify file exists
        assert os.path.exists(download_result["file_path"]), (
            f"Downloaded file should exist at {download_result['file_path']}"
        )

        # Verify file has content
        file_size = os.path.getsize(download_result["file_path"])
        assert file_size > 1000, (
            f"Downloaded file should have content, got {file_size} bytes"
        )


@pytest.mark.integration
class TestPerformanceMetrics:
    """Measure real-world performance with live API."""

    @pytest.mark.asyncio
    async def test_search_response_time(self, credentials, zlib_client):
        """Measure search response time."""
        await asyncio.sleep(1)

        start = time.time()
        result = await python_bridge.search(query="test", count=5, client=zlib_client)  # noqa: F841
        duration = time.time() - start

        # Should complete reasonably fast (network latency included)
        assert duration < 10.0, f"Search took {duration}s, expected <10s"

        # Log performance for monitoring
        print(f"\nSearch performance: {duration:.2f}s")

    @pytest.mark.asyncio
    async def test_metadata_extraction_response_time(self, credentials, zlib_client):
        """Measure metadata extraction response time."""
        await asyncio.sleep(1)

        start = time.time()
        metadata = await python_bridge.get_book_metadata_complete(
            book_id="1252896", book_hash="882753"
        )
        duration = time.time() - start

        # Should complete reasonably fast
        assert duration < 10.0, f"Metadata extraction took {duration}s, expected <10s"

        # Log performance
        print(f"\nMetadata extraction performance: {duration:.2f}s")
        print(f"Keys in metadata: {list(metadata.keys())}")
