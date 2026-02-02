# Tests for lib/python_bridge.py (EAPI-based)

import pytest
import os
import sys
from unittest.mock import AsyncMock

from pathlib import Path

# Add lib directory to sys.path explicitly
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "lib"))
)

import python_bridge  # Import the module itself

# Import functions from the module under test
from python_bridge import (
    process_document,
    download_book,
    normalize_book_details,
    eapi_health_check,
    search,
    full_text_search,
    get_download_history,
    get_download_limits,
    get_book_metadata_complete,
    search_by_term_bridge,
    search_by_author_bridge,
    fetch_booklist_bridge,
)


# --- EAPI Mock Fixtures ---

MOCK_EAPI_SEARCH_RESPONSE = {
    "success": 1,
    "books": [
        {
            "id": 12345,
            "title": "The Great Test",
            "author": "Py Test",
            "year": "2025",
            "language": "english",
            "extension": "epub",
            "filesize": "1048576",
            "hash": "abc123hash",
            "rating": "4.5",
            "qualityScore": "4.0",
            "cover": "",
            "href": "",
            "isbn": "",
            "publisher": "",
            "pages": "200",
        }
    ],
}

MOCK_EAPI_BOOK_INFO = {
    "book": {
        "id": 12345,
        "title": "The Great Test",
        "author": "Py Test",
        "description": "A test book description.",
        "isbn": "978-0-123-45678-9",
        "rating": "4.5",
        "ratingCount": 100,
        "series": "Test Series",
        "categories": ["Testing", "Software"],
        "qualityScore": "4.0",
        "hash": "abc123hash",
    }
}


@pytest.fixture
def mock_eapi_client():
    """Create a mock EAPIClient for testing."""
    mock_client = AsyncMock()
    mock_client.search = AsyncMock(return_value=MOCK_EAPI_SEARCH_RESPONSE)
    mock_client.get_book_info = AsyncMock(return_value=MOCK_EAPI_BOOK_INFO)
    mock_client.get_downloaded = AsyncMock(
        return_value={"books": MOCK_EAPI_SEARCH_RESPONSE["books"]}
    )
    mock_client.get_profile = AsyncMock(
        return_value={"user": {"downloads_today_limit": 10, "downloads_today_left": 7}}
    )
    mock_client.get_recently = AsyncMock(return_value=MOCK_EAPI_SEARCH_RESPONSE)
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def patch_eapi_client(mock_eapi_client, mocker):
    """Patch the module-level _eapi_client."""
    mocker.patch.object(python_bridge, "_eapi_client", mock_eapi_client)
    return mock_eapi_client


@pytest.fixture
def mock_eapi_download(mocker, mock_eapi_client):
    """Mocks EAPIClient.download_file for download operations."""
    mock_eapi_client.download_file = AsyncMock(
        return_value="/mock/downloaded/book.epub"
    )
    return mock_eapi_client


@pytest.fixture
def mock_save_text(mocker):
    """Mocks the _save_processed_text function."""
    return mocker.patch(
        "lib.rag_processing.save_processed_text",
        AsyncMock(return_value=Path("/path/to/saved.txt")),
    )


# --- Tests for normalize_book_details (EAPI format) ---


class TestNormalizeBookDetails:
    def test_eapi_hash_field(self):
        """EAPI books have 'hash' directly available."""
        book = {"id": "123", "hash": "abc123", "url": "http://example.com/book/123"}
        normalized = normalize_book_details(book)
        assert normalized["book_hash"] == "abc123"

    def test_eapi_book_hash_already_present(self):
        """If book_hash already exists, don't overwrite."""
        book = {"id": "123", "hash": "abc", "book_hash": "existing"}
        normalized = normalize_book_details(book)
        assert normalized["book_hash"] == "existing"

    def test_legacy_href_extraction(self):
        """Legacy format: extract hash from href path."""
        book = {"id": "123", "href": "/book/123/abc456/title"}
        normalized = normalize_book_details(book)
        assert normalized["book_hash"] == "abc456"

    def test_url_construction_from_href(self):
        """Construct URL from href if url missing."""
        book = {"id": "123", "href": "/book/123/abc/title"}
        normalized = normalize_book_details(book)
        assert "url" in normalized
        assert normalized["url"].endswith("/book/123/abc/title")


# --- Tests for EAPI Health Check ---


class TestEAPIHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self, patch_eapi_client):
        """Should return healthy when EAPI responds correctly."""
        result = await eapi_health_check()
        assert result["status"] == "healthy"
        assert result["transport"] == "eapi"

    @pytest.mark.asyncio
    async def test_unhealthy_bad_response(self, patch_eapi_client):
        """Should return unhealthy when EAPI response is malformed."""
        patch_eapi_client.search = AsyncMock(return_value={"success": 0})
        result = await eapi_health_check()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_unhealthy_exception(self, mocker):
        """Should return unhealthy when EAPI client not initialized."""
        mocker.patch.object(python_bridge, "_eapi_client", None)
        result = await eapi_health_check()
        assert result["status"] == "unhealthy"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_detects_cloudflare(self, patch_eapi_client):
        """Should detect Cloudflare challenge and return cloudflare_blocked error code."""
        patch_eapi_client.search = AsyncMock(
            side_effect=Exception("Checking your browser before accessing")
        )
        result = await eapi_health_check()
        assert result["status"] == "unhealthy"
        assert result["error_code"] == "cloudflare_blocked"

    @pytest.mark.asyncio
    async def test_health_check_detects_network_error(self, patch_eapi_client):
        """Should detect network errors and return network_error code."""
        patch_eapi_client.search = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )
        result = await eapi_health_check()
        assert result["status"] == "unhealthy"
        assert result["error_code"] == "network_error"

    @pytest.mark.asyncio
    async def test_health_check_detects_malformed_response(self, patch_eapi_client):
        """Should return malformed_response for non-standard EAPI responses."""
        patch_eapi_client.search = AsyncMock(return_value={"success": 0})
        result = await eapi_health_check()
        assert result["status"] == "unhealthy"
        assert result["error_code"] == "malformed_response"


# --- Tests for Search (EAPI-based) ---


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_basic(self, patch_eapi_client):
        """Should search via EAPI and normalize results."""
        result = await search(query="python")
        assert "books" in result
        assert "retrieved_from_url" in result
        assert len(result["books"]) == 1
        assert result["books"][0]["id"] == "12345"
        assert result["books"][0]["book_hash"] == "abc123hash"

    @pytest.mark.asyncio
    async def test_search_with_filters(self, patch_eapi_client):
        """Should pass filters to EAPI search."""
        await search(
            query="test",
            exact=True,
            from_year=2020,
            to_year=2025,
            languages=["English"],
            extensions=["pdf"],
            count=5,
        )
        call_kwargs = patch_eapi_client.search.call_args[1]
        assert call_kwargs["exact"] is True
        assert call_kwargs["year_from"] == 2020
        assert call_kwargs["year_to"] == 2025
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_full_text_search_routes_to_search(self, patch_eapi_client):
        """Full text search routes through regular EAPI search."""
        result = await full_text_search(query="test phrase")
        assert "books" in result
        patch_eapi_client.search.assert_called_once()


# --- Tests for Download History / Limits (EAPI-based) ---


class TestProfileEndpoints:
    @pytest.mark.asyncio
    async def test_get_download_history(self, patch_eapi_client):
        result = await get_download_history(count=5)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_download_limits(self, patch_eapi_client):
        result = await get_download_limits()
        assert result["daily_limit"] == 10
        assert result["daily_remaining"] == 7


# --- Tests for get_book_metadata_complete (EAPI-based) ---


class TestGetBookMetadataComplete:
    @pytest.mark.asyncio
    async def test_metadata_via_eapi(self, patch_eapi_client):
        """Should fetch metadata via EAPI get_book_info."""
        result = await get_book_metadata_complete(
            book_id="12345", book_hash="abc123hash"
        )
        assert result["id"] == "12345"
        assert result["book_hash"] == "abc123hash"
        assert result["description"] == "A test book description."
        assert result["series"] == "Test Series"

    @pytest.mark.asyncio
    async def test_metadata_requires_hash(self, patch_eapi_client):
        """Should raise if book_hash not provided."""
        with pytest.raises(ValueError, match="book_hash is required"):
            await get_book_metadata_complete(book_id="12345")


# --- Tests for Bridge Functions (term, author, booklist) ---


class TestBridgeFunctions:
    @pytest.mark.asyncio
    async def test_search_by_term_bridge(self, patch_eapi_client, mocker):
        """Should pass eapi_client to term_tools."""
        mock_term_search = AsyncMock(
            return_value={"term": "dialectic", "books": [], "total_results": 0}
        )
        mocker.patch("lib.term_tools.search_by_term", mock_term_search)
        result = await search_by_term_bridge(term="dialectic")
        assert result["term"] == "dialectic"
        # Verify eapi_client was passed
        call_kwargs = mock_term_search.call_args[1]
        assert call_kwargs["eapi_client"] is patch_eapi_client

    @pytest.mark.asyncio
    async def test_search_by_author_bridge(self, patch_eapi_client, mocker):
        """Should pass eapi_client to author_tools."""
        mock_author_search = AsyncMock(
            return_value={"author": "Hegel", "books": [], "total_results": 0}
        )
        mocker.patch("lib.author_tools.search_by_author", mock_author_search)
        result = await search_by_author_bridge(author="Hegel")
        assert result["author"] == "Hegel"
        call_kwargs = mock_author_search.call_args[1]
        assert call_kwargs["eapi_client"] is patch_eapi_client

    @pytest.mark.asyncio
    async def test_fetch_booklist_bridge(self, patch_eapi_client, mocker):
        """Should pass eapi_client to booklist_tools."""
        mock_booklist = AsyncMock(
            return_value={
                "booklist_id": "123",
                "books": [],
                "degraded": True,
                "topic": "test",
                "metadata": {},
                "page": 1,
                "booklist_hash": "abc",
            }
        )
        mocker.patch("lib.booklist_tools.fetch_booklist", mock_booklist)
        result = await fetch_booklist_bridge(
            booklist_id="123", booklist_hash="abc", topic="test"
        )
        assert result["degraded"] is True
        call_kwargs = mock_booklist.call_args[1]
        assert call_kwargs["eapi_client"] is patch_eapi_client


# --- Tests for Download Book (now uses EAPIClient.download_file) ---


class TestDownloadBook:
    @pytest.mark.asyncio
    async def test_download_book_success(
        self, mock_eapi_download, tmp_path, mocker, patch_eapi_client
    ):
        """Tests download_book for successful execution."""
        book_details_mock = {
            "id": "987",
            "extension": "pdf",
            "name": "Bridge Test Book",
            "author": "Test Author",
            "url": "https://example.com/book/987/test",
            "hash": "testhash123",
        }
        output_dir_mock = str(tmp_path / "downloads")

        original_path = str(Path(output_dir_mock) / "987.pdf")
        expected_filename = "AuthorTest_Bridge_Test_Book_987.pdf"
        expected_final_path = str(Path(output_dir_mock) / expected_filename)

        mock_eapi_download.download_file.return_value = original_path
        mocker.patch(
            "python_bridge.create_unified_filename", return_value=expected_filename
        )
        mocker.patch("os.rename")
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("python_bridge.process_document", AsyncMock())

        result = await download_book(
            book_details=book_details_mock,
            output_dir=output_dir_mock,
            process_for_rag=False,
        )

        assert result["file_path"] == expected_final_path
        assert result.get("processed_file_path") is None

    @pytest.mark.asyncio
    async def test_download_book_with_rag(
        self, mock_eapi_download, tmp_path, mocker, patch_eapi_client
    ):
        """Tests download_book with RAG processing."""
        book_details_mock = {
            "id": "988",
            "extension": "txt",
            "name": "RAG Test Book",
            "author": "RAG Author",
            "url": "https://example.com/book/988/test",
            "hash": "raghash123",
        }
        output_dir_mock = str(tmp_path / "downloads_rag")
        original_path = str(Path(output_dir_mock) / "988.txt")
        expected_filename = "AuthorRAG_RAG_Test_Book_988.txt"
        expected_final_path = str(Path(output_dir_mock) / expected_filename)
        processed_path = expected_final_path + ".processed.md"

        mock_eapi_download.download_file.return_value = original_path
        mocker.patch(
            "python_bridge.create_unified_filename", return_value=expected_filename
        )
        mocker.patch("os.rename")
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch(
            "python_bridge.process_document",
            AsyncMock(
                return_value={"processed_file_path": processed_path, "content": []}
            ),
        )

        result = await download_book(
            book_details=book_details_mock,
            output_dir=output_dir_mock,
            process_for_rag=True,
            processed_output_format="markdown",
        )

        assert result["file_path"] == expected_final_path
        assert result["processed_file_path"] == processed_path

    @pytest.mark.asyncio
    async def test_download_book_error(
        self, mock_eapi_download, tmp_path, mocker, patch_eapi_client
    ):
        """Tests download_book handles download errors."""
        book_details_mock = {
            "id": "989",
            "extension": "epub",
            "name": "Error Test",
            "url": "https://example.com/book/989/test",
            "hash": "errhash",
        }
        mock_eapi_download.download_file.side_effect = RuntimeError("Download failed")

        with pytest.raises(RuntimeError, match="Download failed"):
            await download_book(
                book_details=book_details_mock,
                output_dir=str(tmp_path / "downloads_err"),
                process_for_rag=False,
            )


# --- Tests for process_document (unchanged — local file processing) ---


@pytest.mark.asyncio
async def test_process_document_epub_success(tmp_path, mocker, mock_save_text):
    epub_path = tmp_path / "test.epub"
    epub_path.touch()
    expected_content = "Chapter 1 content.\nChapter 2 content."
    mock_internal_epub = mocker.patch(
        "lib.rag_processing.process_epub", return_value=expected_content
    )

    result = await process_document(
        str(epub_path), book_id=None, author=None, title=None
    )

    mock_internal_epub.assert_called_once_with(Path(epub_path), "txt")
    mock_save_text.assert_called_once_with(
        original_file_path=Path(epub_path),
        processed_content=expected_content,
        output_format="txt",
        book_details={"id": None, "author": None, "title": None},
    )
    assert result == {
        "processed_file_path": str(mock_save_text.return_value),
        "content": [],
    }


@pytest.mark.asyncio
async def test_process_document_epub_read_error(tmp_path, mocker, mock_save_text):
    epub_path = tmp_path / "test.epub"
    epub_path.touch()
    mocker.patch(
        "lib.rag_processing.process_epub", side_effect=Exception("EPUB read failed")
    )

    with pytest.raises(
        RuntimeError, match=r"Error processing document .*test\.epub: EPUB read failed"
    ):
        await process_document(str(epub_path), book_id=None, author=None, title=None)
    mock_save_text.assert_not_called()


@pytest.mark.asyncio
async def test_process_document_txt_utf8(tmp_path, mocker, mock_save_text):
    txt_path = tmp_path / "test_utf8.txt"
    content = "This is a UTF-8 file.\nWith multiple lines.\nAnd special chars."
    txt_path.write_text(content, encoding="utf-8")
    mock_internal_txt = mocker.patch(
        "lib.rag_processing.process_txt", return_value=content
    )

    result = await process_document(
        str(txt_path), book_id=None, author=None, title=None
    )

    mock_internal_txt.assert_called_once_with(Path(txt_path))
    mock_save_text.assert_called_once_with(
        original_file_path=Path(txt_path),
        processed_content=content,
        output_format="txt",
        book_details={"id": None, "author": None, "title": None},
    )
    assert result == {
        "processed_file_path": str(mock_save_text.return_value),
        "content": [],
    }


@pytest.mark.asyncio
async def test_process_document_pdf_success(tmp_path, mocker, mock_save_text):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()
    expected_content = "Sample PDF text content."
    mock_internal_pdf = mocker.patch(
        "lib.rag_processing.process_pdf", return_value=expected_content
    )

    result = await process_document(
        str(pdf_path), book_id=None, author=None, title=None
    )

    mock_internal_pdf.assert_called_once_with(Path(pdf_path), "txt")
    mock_save_text.assert_called_once_with(
        original_file_path=Path(pdf_path),
        processed_content=expected_content,
        output_format="txt",
        book_details={"id": None, "author": None, "title": None},
    )
    assert result == {
        "processed_file_path": str(mock_save_text.return_value),
        "content": [],
    }


@pytest.mark.asyncio
async def test_process_document_pdf_encrypted(tmp_path, mocker, mock_save_text):
    pdf_path = tmp_path / "encrypted.pdf"
    pdf_path.touch()
    mocker.patch(
        "lib.rag_processing.process_pdf", side_effect=ValueError("PDF is encrypted")
    )

    with pytest.raises(
        RuntimeError,
        match=r"Error processing document .*encrypted\.pdf: PDF is encrypted",
    ):
        await process_document(str(pdf_path), book_id=None, author=None, title=None)
    mock_save_text.assert_not_called()
