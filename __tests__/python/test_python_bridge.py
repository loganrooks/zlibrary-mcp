# Tests for lib/python-bridge.py

import pytest
import json
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

import httpx
import aiofiles
from pathlib import Path
from zlibrary.exception import DownloadError, ParseError # Added ParseError
from zlibrary import Extension # Import Extension enum
# Add lib directory to sys.path explicitly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

import python_bridge # Import the module itself
from lib import rag_processing # Import the new module

# Import functions from the module under test
# These imports will fail initially if the functions don't exist yet
# We expect NameErrors in the Red phase for unimplemented functions - Removing try/except
# try:
from python_bridge import (
    process_document,
    download_book,
)
# Mock EBOOKLIB_AVAILABLE for tests where the library might be missing
# import python_bridge # Moved to top
python_bridge.EBOOKLIB_AVAILABLE = True # Assume available by default for most tests
# except ImportError as e:
#     # pytest.fail(f"Failed to import from python_bridge: {e}. Ensure lib is in sys.path and functions exist.")
#     # Allow collection to proceed in Red phase; tests marked xfail will handle the failure.
#     pass # Indicate that the import failure is currently expected/handled by xfail


# Dummy Exceptions for Red Phase
class DownloadScrapeError(Exception): pass
class DownloadExecutionError(Exception): pass
class FileSaveError(Exception): pass

# Dummy Functions for Red Phase (Keep only those needed for other tests to run)
# async def _scrape_and_download(book_page_url: str, output_dir_str: str) -> str: # Keep original dummy for now if needed
#     # Basic check for testing import error
#     if 'python_bridge' in sys.modules and not getattr(sys.modules['python_bridge'], 'DOWNLOAD_LIBS_AVAILABLE', True):
#          raise ImportError("Required libraries 'httpx' and 'aiofiles' are not installed.")
#     # Simulate basic success for routing tests
#     filename = book_page_url.split('/')[-1] or 'downloaded_file'
#     return str(Path(output_dir_str) / filename)

# Dummy download_book removed - tests will use the actual implementation

# Add dummy process_document if not fully implemented yet for RAG tests
if 'process_document' not in locals():
    async def process_document(file_path_str: str, output_format: str = "txt") -> dict: # Make dummy async
        # Simulate basic success for download_book RAG tests
        if "fail_process" in file_path_str:
            raise RuntimeError("Simulated processing failure")
        if "no_text" in file_path_str:
             return {"processed_file_path": None}
        return {"processed_file_path": file_path_str + ".processed." + output_format}


# --- Fixtures ---

@pytest.fixture
def mock_zlibrary_client(mocker):
    """Mocks the ZLibrary client instance and its methods."""
    mock_client = MagicMock()
    # Use AsyncMock for the async download_book method
    mock_client.download_book = AsyncMock(return_value='/mock/downloaded/book.epub') # Default success
    mocker.patch('python_bridge.AsyncZlib', return_value=mock_client) # Ensure correct patch target for instantiation
    mocker.patch('python_bridge.zlib_client', mock_client) # Patch the global client instance
    return mock_client

@pytest.fixture
def mock_ebooklib(mocker):
    """Mocks ebooklib functions."""
    mock_epub = MagicMock()
    mock_read_epub = mocker.patch('python_bridge.epub.read_epub', return_value=mock_epub)
    # Mock items
    mock_item1 = MagicMock()
    mock_item1.get_content.return_value = b'<html><body><p>Chapter 1 content.</p></body></html>'
    mock_item1.get_name.return_value = 'chap1.xhtml'
    mock_item2 = MagicMock()
    mock_item2.get_content.return_value = b'<html><head><style>css</style></head><body><p>Chapter 2 content.</p><script>alert("hi")</script></body></html>'
    mock_item2.get_name.return_value = 'chap2.xhtml'
    mock_epub.get_items_of_type.return_value = [mock_item1, mock_item2]
    return mock_read_epub, mock_epub


@pytest.fixture
def mock_fitz(mocker):
    """Mocks the fitz (PyMuPDF) library."""
    # Mock the fitz module itself if it's imported directly
    mock_fitz_module = MagicMock()
    mocker.patch.dict(sys.modules, {'fitz': mock_fitz_module})

    # Mock fitz.open
    mock_doc = MagicMock()
    mock_page = MagicMock()

    # Default behaviors (can be overridden in tests)
    mock_doc.is_encrypted = False
    mock_doc.page_count = 1 # Keep for potential future use
    mock_doc.__len__ = MagicMock(return_value=1) # Add __len__ for the loop
    mock_doc.load_page.return_value = mock_page
    mock_page.get_text.return_value = "Sample PDF text content."

    # Patch fitz.open within the python_bridge module's namespace
    mock_open_func = mocker.patch('python_bridge.fitz.open', return_value=mock_doc)

    # Make mocks accessible (mock_fitz_module might not be needed anymore)
    # mock_fitz_module.open = mock_open_func # Commented out as patch target changed
    mock_fitz_module.Document = MagicMock() # Mock Document class if needed
    # Add FitzError to the mock module if fitz is mocked
    mock_fitz_module.FitzError = RuntimeError # Use RuntimeError as a stand-in

    # Return mocks for potential direct manipulation in tests
    return mock_open_func, mock_doc, mock_page


# --- Tests for ID Lookup Workaround (Using client.search) ---

# Mock data for workaround tests
MOCK_BOOK_RESULT = {
    'id': '12345',
    'name': 'The Great Test',
    'author': 'Py Test', # Already present
    'year': '2025',
    'language': 'en',
    'extension': 'epub',
    'size': '1 MB',
    'url': 'http://example.com/download/12345.epub' # Renamed from download_url
    # Add other relevant fields if the implementation extracts them
}

# --- New Fixtures for Download/Scrape Tests ---

@pytest.fixture
def mock_httpx_client(mocker):
    """Mocks httpx.AsyncClient and its methods."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "<html><body><a class='btn btn-primary dlButton' href='/download/book/123'>Download</a></body></html>"
    mock_response.url = httpx.URL("http://example.com/book/123/slug") # Mock URL for urljoin
    mock_response.headers = {'content-disposition': 'attachment; filename="test_book.epub"'}
    mock_response.raise_for_status = MagicMock()

    async def mock_get(*args, **kwargs):
        # Allow side effect for error testing
        if hasattr(mock_response, '_side_effect_get') and mock_response._side_effect_get:
            raise mock_response._side_effect_get
        return mock_response

    async def mock_stream(*args, **kwargs):
        # Allow side effect for error testing
        if hasattr(mock_response, '_side_effect_stream') and mock_response._side_effect_stream:
            raise mock_response._side_effect_stream

        # Simulate streaming response
        class MockAsyncIterator:
            def __init__(self):
                self._chunks = [b'chunk1', b'chunk2']
                self._iter = iter(self._chunks)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

        mock_stream_response = AsyncMock(spec=httpx.Response)
        mock_stream_response.status_code = 200
        mock_stream_response.headers = mock_response.headers # Use same headers
        mock_stream_response.aiter_bytes.return_value = MockAsyncIterator()
        mock_stream_response.raise_for_status = MagicMock() # Ensure it doesn't raise by default
        # Allow overriding raise_for_status for HTTP error tests
        if hasattr(mock_response, '_side_effect_stream_raise') and mock_response._side_effect_stream_raise:
             mock_stream_response.raise_for_status.side_effect = mock_response._side_effect_stream_raise

        return mock_stream_response

    mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
    mock_client_instance.get = AsyncMock(side_effect=mock_get)
    mock_client_instance.stream = AsyncMock(side_effect=mock_stream)

    # Patch the class instantiation
    mock_async_client_class = mocker.patch('httpx.AsyncClient', return_value=mock_client_instance)

    # Return mocks for potential modification in tests
    return mock_async_client_class, mock_client_instance, mock_response

@pytest.fixture
def mock_aiofiles(mocker):
    """Mocks aiofiles.open."""
    mock_file = AsyncMock()
    # Assign an AsyncMock to mock_file.write
    mock_file.write = AsyncMock() # No need for mock_write function now
    mock_file.__aenter__.return_value = mock_file # For async with context
    mock_file.__aexit__.return_value = None

    mock_open = mocker.patch('aiofiles.open', return_value=mock_file)
    return mock_open, mock_file

@pytest.fixture
def mock_beautifulsoup(mocker):
    """Mocks BeautifulSoup."""
    mock_soup_instance = MagicMock()
    mock_link = MagicMock()
    mock_link.has_attr.return_value = True
    mock_link.__getitem__.return_value = '/download/book/123' # href value
    mock_soup_instance.select_one.return_value = mock_link

    mock_bs_class = mocker.patch('python_bridge.BeautifulSoup', return_value=mock_soup_instance)
    return mock_bs_class, mock_soup_instance

@pytest.fixture
def mock_pathlib(mocker):
    """Mocks pathlib.Path methods."""
    # Create a real Path object for the directory part to allow mkdir
    mock_dir_path_instance = MagicMock(spec=Path)
    mock_dir_path_instance.mkdir = MagicMock()

    # Create a separate mock for the final file path
    mock_file_path_instance = MagicMock(spec=Path)
    mock_file_path_instance.name = "test_book.epub"
    mock_file_path_instance.exists.return_value = True # Assume exists by default
    mock_file_path_instance.__str__.return_value = "/mock/path/test_book.epub"

    # When the directory path is divided by a filename, return the file path mock
    mock_dir_path_instance.__truediv__.return_value = mock_file_path_instance

    # Patch Path class to return the directory mock initially
    mock_path_class = mocker.patch('python_bridge.Path', return_value=mock_dir_path_instance)

    return mock_path_class, mock_dir_path_instance, mock_file_path_instance

@pytest.fixture
def mock_process_document(mocker):
    """Mocks the process_document function."""
    # Use the dummy implementation if available, otherwise mock
    if 'process_document' in locals():
        mock_func = mocker.patch('python_bridge.process_document', wraps=process_document)
    else:
        mock_func = mocker.patch('python_bridge.process_document', return_value={"processed_file_path": "/path/to/processed.txt"})
    return mock_func

# Add fixture for _save_processed_text
@pytest.fixture
def mock_save_text(mocker):
    """Mocks the _save_processed_text function."""
    # Mock the function directly within the python_bridge module
    return mocker.patch('lib.rag_processing.save_processed_text', AsyncMock(return_value=Path("/path/to/saved.txt"))) # Updated path


    book_details = asyncio.run(get_by_id('12345')) # Use actual function name and asyncio.run

    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)
    assert book_details == MOCK_BOOK_RESULT

@pytest.mark.asyncio
async def test_download_book_bridge_success(mock_zlibrary_client, tmp_path, mocker):
    """Tests the python_bridge.download_book function for successful execution."""
    book_details_mock = {"id": "987", "extension": "pdf", "name": "Bridge Test Book", "url": "https://example.com/book/987/bridge-test-book"}
    output_dir_mock = str(tmp_path / "downloads_bridge")
    expected_downloaded_path = str(Path(output_dir_mock) / f"{book_details_mock['id']}.{book_details_mock['extension']}")

    # Configure the mock client's download_book to return the expected path
    mock_zlibrary_client.download_book.return_value = expected_downloaded_path
    
    # Mock rag_processing.save_processed_text as it might be called if process_for_rag is True (though default is False)
    # We are primarily testing the bridge's interaction with zlibrary.download_book here.
    mocker.patch('lib.rag_processing.save_processed_text', AsyncMock(return_value=Path(expected_downloaded_path + ".processed.txt")))
    mocker.patch('lib.rag_processing.process_document', AsyncMock(return_value={"processed_file_path": expected_downloaded_path + ".processed.txt"}))


    # Call the bridge function
    # The bridge function itself is not async, but it calls an async method.
    # We need to await the call if the bridge function itself was async.
    # Based on its current structure, it seems to run the async code internally.
    # Let's assume the bridge function `download_book` is synchronous and handles asyncio.run internally
    # If it were async, the test would be: result = await python_bridge.download_book(...)
    
    # The python_bridge.download_book function is async.
    result_dict = await python_bridge.download_book(
        book_details=book_details_mock,
        output_dir=output_dir_mock,
        process_for_rag=False # Explicitly False for this test
    )

    # Assert that the underlying zlibrary client's download_book was called correctly
    mock_zlibrary_client.download_book.assert_called_once_with(
        book_id=book_details_mock['id'], # Ensure book_id is passed
        book_details=book_details_mock,
        output_dir_str=output_dir_mock, # Check for the renamed parameter
        # process_for_rag=False, # This param is for the MCP tool, not the zlibrary lib
        # processed_output_format=None # This param is for the MCP tool
    )

    # Assert the structure and content of the result from the bridge
    assert "file_path" in result_dict
    assert result_dict["file_path"] == expected_downloaded_path
    assert result_dict.get("processed_file_path") is None

@pytest.mark.asyncio
async def test_download_book_bridge_returns_processed_path_if_rag_true(mock_zlibrary_client, tmp_path, mocker):
    book_details_mock = {"id": "988", "extension": "txt", "name": "Bridge RAG Test Book", "url": "https://example.com/book/988/bridge-rag-test-book"}
    output_dir_mock = str(tmp_path / "downloads_bridge_rag")
    original_downloaded_path = str(Path(output_dir_mock) / f"{book_details_mock['id']}.{book_details_mock['extension']}")
    processed_path_mock = original_downloaded_path + ".processed.md"

    mock_zlibrary_client.download_book.return_value = original_downloaded_path
    
    # Mock the process_document function within python_bridge itself
    mock_process_doc = mocker.patch('python_bridge.process_document', AsyncMock(return_value={"processed_file_path": processed_path_mock, "content": ["Processed content"]}))
    # No longer need to mock pathlib.Path.exists here as python_bridge.process_document is fully mocked

    result_dict = await python_bridge.download_book(
        book_details=book_details_mock,
        output_dir=output_dir_mock,
        process_for_rag=True,
        processed_output_format="markdown"
    )

    mock_zlibrary_client.download_book.assert_called_once_with(
        book_id=book_details_mock['id'],
        book_details=book_details_mock,
        output_dir_str=output_dir_mock
    )
    mock_process_doc.assert_called_once_with(
        file_path_str=original_downloaded_path,
        output_format="markdown",
        book_id=book_details_mock['id'],
        author=book_details_mock.get('author'), # Use .get() in case author is not in mock
        title=book_details_mock['name']
    )
    assert result_dict.get("file_path") == original_downloaded_path
    assert result_dict.get("processed_file_path") == processed_path_mock

@pytest.mark.asyncio
async def test_download_book_bridge_handles_zlib_download_error(mock_zlibrary_client, tmp_path, mocker):
    book_details_mock = {"id": "989", "extension": "epub", "name": "Bridge Error Test", "url": "https://example.com/book/989/bridge-error-test"}
    output_dir_mock = str(tmp_path / "downloads_bridge_err")

    mock_zlibrary_client.download_book.side_effect = DownloadError("Zlib download failed")
    
    mocker.patch('lib.rag_processing.process_document', AsyncMock()) # Mock to prevent unintended calls

    with pytest.raises(DownloadError, match="Zlib download failed"):
        await python_bridge.download_book(
            book_details=book_details_mock,
            output_dir=output_dir_mock,
            process_for_rag=False
        )
    
    mock_zlibrary_client.download_book.assert_called_once()
    python_bridge.rag_processing.process_document.assert_not_called()

@pytest.mark.asyncio
async def test_download_book_bridge_handles_processing_error_if_rag_true(mock_zlibrary_client, tmp_path, mocker):
    book_details_mock = {"id": "990", "extension": "pdf", "name": "Bridge RAG Error Test", "url": "https://example.com/book/990/bridge-rag-error-test"}
    output_dir_mock = str(tmp_path / "downloads_bridge_rag_err")
    original_downloaded_path = str(Path(output_dir_mock) / f"{book_details_mock['id']}.{book_details_mock['extension']}")

    mock_zlibrary_client.download_book.return_value = original_downloaded_path
    # No longer need to mock pathlib.Path.exists here
    
    mock_process_doc = mocker.patch('python_bridge.process_document', AsyncMock(side_effect=RuntimeError("RAG failed")))

    with pytest.raises(RuntimeError, match="RAG failed"):
        await python_bridge.download_book(
            book_details=book_details_mock,
            output_dir=output_dir_mock,
            process_for_rag=True,
            processed_output_format="text"
        )
    
    mock_zlibrary_client.download_book.assert_called_once()
    mock_process_doc.assert_called_once()
# --- Test Cases ---

# 6. Python Bridge - _process_epub
# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_epub_success(tmp_path, mocker, mock_save_text):
    epub_path = tmp_path / "test.epub"
    epub_path.touch()
    expected_content = "Chapter 1 content.\nChapter 2 content."
    # Mock the internal helper called by process_document
    mock_internal_epub = mocker.patch('lib.rag_processing.process_epub', return_value=expected_content) # Updated path

    # Add default None for new metadata args
    result = await process_document(str(epub_path), book_id=None, author=None, title=None)

    mock_internal_epub.assert_called_once_with(Path(epub_path), 'txt') # Expect Path and 'txt'
    # Update mock_save_text assertion to include metadata=None
    mock_save_text.assert_called_once_with(
        original_file_path=Path(epub_path),
        processed_content=expected_content, # Changed text_content -> processed_content
        output_format='txt',
        book_details={'id': None, 'author': None, 'title': None} # Changed book_id/author/title -> book_details
    )
    # Assert the final dictionary returned by process_document
    assert result == {"processed_file_path": str(mock_save_text.return_value), "content": []} # Added content key

# Test removed as EBOOKLIB_AVAILABLE flag logic was removed.
# ImportError is handled by the import statement itself.
# def test_process_epub_ebooklib_not_available(tmp_path, mocker):
#     epub_path = tmp_path / "test.epub"
#     # epub_path.touch() # Don't create file
#     # Mock the flag used in the function
#     mocker.patch('python_bridge.EBOOKLIB_AVAILABLE', False)
#     with pytest.raises(ImportError, match="Required library 'ebooklib' is not installed or available."):
#          # Use dummy path
#         _process_epub(str(epub_path))

# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_epub_read_error(tmp_path, mocker, mock_save_text):
    epub_path = tmp_path / "test.epub"
    epub_path.touch()
    # Mock the internal helper to raise an error
    mock_internal_epub = mocker.patch('lib.rag_processing.process_epub', side_effect=Exception("EPUB read failed")) # Updated path

    # Assert that process_document wraps and raises the error
    with pytest.raises(RuntimeError, match=r"Error processing document .*test\.epub: EPUB read failed"): # Expect RuntimeError
        # Add default None for new metadata args
        await process_document(str(epub_path), book_id=None, author=None, title=None)

    mock_internal_epub.assert_called_once_with(Path(epub_path), 'txt') # Expect Path and 'txt'
    mock_save_text.assert_not_called() # Save should not be called on error

# 7. Python Bridge - _process_txt
# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_txt_utf8(tmp_path, mocker, mock_save_text):
    txt_path = tmp_path / "test_utf8.txt"
    content = "This is a UTF-8 file.\nWith multiple lines.\nAnd special chars: éàçü."
    txt_path.write_text(content, encoding='utf-8')
    # Mock the internal helper
    mock_internal_txt = mocker.patch('lib.rag_processing.process_txt', return_value=content) # Updated path

    # Add default None for new metadata args
    result = await process_document(str(txt_path), book_id=None, author=None, title=None)

    mock_internal_txt.assert_called_once_with(Path(txt_path)) # Expect Path
    # Update mock_save_text assertion to include metadata=None
    mock_save_text.assert_called_once_with(
        original_file_path=Path(txt_path),
        processed_content=content, # Changed text_content -> processed_content
        output_format='txt',
        book_details={'id': None, 'author': None, 'title': None} # Changed book_id/author/title -> book_details
    )
    assert result == {"processed_file_path": str(mock_save_text.return_value), "content": []} # Added content key

# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_txt_latin1_fallback(tmp_path, mocker, mock_save_text):
    txt_path = tmp_path / "test_latin1.txt"
    content_latin1 = "This is a Latin-1 file with chars like: äöüß."
    txt_path.write_text(content_latin1, encoding='latin-1')
    # Simulate the behavior of _process_txt with fallback
    expected_processed_content = "This is a Latin-1 file with chars like: ."
    mock_internal_txt = mocker.patch('lib.rag_processing.process_txt', return_value=expected_processed_content) # Updated path

    # Add default None for new metadata args
    result = await process_document(str(txt_path), book_id=None, author=None, title=None)

    mock_internal_txt.assert_called_once_with(Path(txt_path)) # Expect Path
    # Update mock_save_text assertion to include metadata=None
    mock_save_text.assert_called_once_with(
        original_file_path=Path(txt_path),
        processed_content=expected_processed_content, # Changed text_content -> processed_content
        output_format='txt',
        book_details={'id': None, 'author': None, 'title': None} # Changed book_id/author/title -> book_details
    )
    assert result == {"processed_file_path": str(mock_save_text.return_value), "content": []} # Added content key

# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_txt_read_error(tmp_path, mocker, mock_save_text):
    txt_path = tmp_path / "no_permission.txt"
    txt_path.touch() # <<< ADDED: Create the file so exists() check passes
    # Mock the internal helper to raise the error
    mock_internal_txt = mocker.patch('lib.rag_processing.process_txt', side_effect=IOError("Permission denied")) # Updated path

    # Assert that process_document wraps and raises the error
    with pytest.raises(RuntimeError, match=r"Error processing document .*no_permission\.txt: Permission denied"): # Expect RuntimeError
        # Add default None for new metadata args
        await process_document(str(txt_path), book_id=None, author=None, title=None)

    mock_internal_txt.assert_called_once_with(Path(txt_path)) # Expect Path
    mock_save_text.assert_not_called()


# X. Python Bridge - _process_pdf (New Tests)
# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_pdf_success(tmp_path, mocker, mock_save_text):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()
    expected_content = "Sample PDF text content."
    # Mock the internal helper
    mock_internal_pdf = mocker.patch('lib.rag_processing.process_pdf', return_value=expected_content) # Updated path

    # Add default None for new metadata args
    result = await process_document(str(pdf_path), book_id=None, author=None, title=None)

    mock_internal_pdf.assert_called_once_with(Path(pdf_path), 'txt') # Expect Path and 'txt'
    # Update mock_save_text assertion to include metadata=None
    mock_save_text.assert_called_once_with(
        original_file_path=Path(pdf_path),
        processed_content=expected_content, # Changed text_content -> processed_content
        output_format='txt',
        book_details={'id': None, 'author': None, 'title': None} # Changed book_id/author/title -> book_details
    )
    assert result == {"processed_file_path": str(mock_save_text.return_value), "content": []} # Added content key

# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_pdf_encrypted(tmp_path, mocker, mock_save_text):
    pdf_path = tmp_path / "encrypted.pdf"
    pdf_path.touch()
    # Mock the internal helper to raise error
    mock_internal_pdf = mocker.patch('lib.rag_processing.process_pdf', side_effect=ValueError("PDF is encrypted")) # Updated path

    with pytest.raises(RuntimeError, match=r"Error processing document .*encrypted\.pdf: PDF is encrypted"): # Expect RuntimeError wrapper
        # Add default None for new metadata args
        await process_document(str(pdf_path), book_id=None, author=None, title=None)

    mock_internal_pdf.assert_called_once_with(Path(pdf_path), 'txt') # Expect Path and 'txt'
    mock_save_text.assert_not_called()

# Refactored to test via process_document
@pytest.mark.asyncio
async def test_process_document_pdf_corrupted(tmp_path, mocker, mock_save_text): # Refactored test
    """Tests if process_document handles corrupted PDF files gracefully."""
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.touch()
    # Mock the internal helper to raise the error
    # Use fitz exception if available, otherwise generic RuntimeError
    fitz_error = getattr(sys.modules.get('fitz', None), 'FitzError', RuntimeError)
    mock_internal_pdf = mocker.patch('lib.rag_processing.process_pdf', side_effect=fitz_error("Corrupted PDF")) # Updated path

    with pytest.raises(RuntimeError, match=r"Error processing document .*corrupted\.pdf.*Corrupted PDF"): # Expect RuntimeError wrapper
        # Add default None for new metadata args
        await process_document(str(pdf_path), book_id=None, author=None, title=None)

    mock_internal_pdf.assert_called_once_with(Path(pdf_path), 'txt')
    mock_save_text.assert_not_called()
