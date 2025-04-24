# Tests for lib/python-bridge.py

import pytest
import json
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, mock_open, AsyncMock

# sys.path modification removed, relying on pytest.ini

# Import functions from the module under test
# These imports will fail initially if the functions don't exist yet
try:
    from python_bridge import (
        _process_epub,
        _process_txt,
        _process_pdf,
        get_by_id,             # Renamed from get_book_by_id
        get_download_info,     # Added for workaround tests
        process_document,
        # Add main execution part if needed for testing CLI interface
    )
    # Mock EBOOKLIB_AVAILABLE for tests where the library might be missing
    import python_bridge
    python_bridge.EBOOKLIB_AVAILABLE = True # Assume available by default for most tests
except ImportError as e:
    # pytest.fail(f"Failed to import from python_bridge: {e}. Ensure lib is in sys.path and functions exist.")
    # Allow collection to proceed in Red phase; tests marked xfail will handle the failure.
    pass # Indicate that the import failure is currently expected/handled by xfail


# --- Fixtures ---

@pytest.fixture
def mock_zlibrary_client(mocker):
    """Mocks the ZLibrary client instance and its methods."""
    mock_client = MagicMock()
    mock_client.download_book.return_value = '/mock/downloaded/book.epub' # Default success
    mocker.patch('python_bridge.ZLibrary', return_value=mock_client)
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
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    mock_page.get_text.return_value = "Sample PDF text content."

    mock_open_func = mocker.patch('fitz.open', return_value=mock_doc)

    # Make mocks accessible
    mock_fitz_module.open = mock_open_func
    mock_fitz_module.Document = MagicMock() # Mock Document class if needed

    # Return mocks for potential direct manipulation in tests
    return mock_open_func, mock_doc, mock_page


# --- Tests for ID Lookup Workaround (Using client.search) ---

# Mock data for workaround tests
MOCK_BOOK_RESULT = {
    'id': '12345',
    'name': 'The Great Test',
    'author': 'Py Test',
    'year': '2025',
    'language': 'en',
    'extension': 'epub',
    'size': '1 MB',
    'download_url': 'http://example.com/download/12345.epub'
    # Add other relevant fields if the implementation extracts them
}

# get_book_by_id tests
# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_by_id_workaround_success(mocker): # Renamed test function
    """Tests get_by_id successfully finding one book via search."""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    # Mock the async paginator's next method
    async def mock_next():
        return [MOCK_BOOK_RESULT]
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)

    # Patch the global client variable
    mocker.patch('python_bridge.zlib_client', mock_client)
    # Ensure initialize_client doesn't run if client is patched
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None)) # Use regular MagicMock for sync func

    book_details = asyncio.run(get_by_id('12345')) # Use actual function name and asyncio.run

    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)
    assert book_details == MOCK_BOOK_RESULT

# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_by_id_workaround_not_found(mocker): # Renamed test function
    """Tests get_by_id raising error when search finds no book."""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    async def mock_next():
        return []
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)
    mocker.patch('python_bridge.zlib_client', mock_client)
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None))

    with pytest.raises(ValueError, match=r"Book ID 12345 not found via search."): # Updated match string
        asyncio.run(get_by_id('12345')) # Use actual function name and asyncio.run
    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)

# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_by_id_workaround_ambiguous(mocker): # Renamed test function
    """Tests get_by_id raising error when search finds multiple books."""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    async def mock_next():
        return [MOCK_BOOK_RESULT, {'id': '67890'}]
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)
    mocker.patch('python_bridge.zlib_client', mock_client)
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None))

    with pytest.raises(ValueError, match=r"Ambiguous search result for Book ID 12345."): # Updated match string
        asyncio.run(get_by_id('12345')) # Use actual function name and asyncio.run
    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)


# get_download_info tests
# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_download_info_workaround_success(mocker):
    """Tests get_download_info successfully finding download URL via search."""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    async def mock_next():
        return [MOCK_BOOK_RESULT]
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)
    mocker.patch('python_bridge.zlib_client', mock_client)
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None))

    download_info = asyncio.run(get_download_info('12345')) # Use asyncio.run

    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)
    # Assert the full dictionary returned by the implementation
    expected_info = {
        'title': 'The Great Test',
        'author': 'Py Test',
        'format': 'epub', # Default from MOCK_BOOK_RESULT extension
        'filesize': '1 MB',
        'download_url': 'http://example.com/download/12345.epub'
    }
    assert download_info == expected_info

# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_download_info_workaround_no_url(mocker):
    """Tests get_download_info returns None for download_url when not found."""
    mock_book_no_url = MOCK_BOOK_RESULT.copy()
    del mock_book_no_url['download_url'] # Remove download_url from mock data
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    async def mock_next():
        return [mock_book_no_url]
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)
    mocker.patch('python_bridge.zlib_client', mock_client)
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None))

    # Expect the function to return successfully with download_url as None
    download_info = asyncio.run(get_download_info('12345')) # Use asyncio.run
    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)
    assert download_info['download_url'] is None
    # Optionally check other fields
    assert download_info['title'] == 'The Great Test'


# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_download_info_workaround_not_found(mocker):
    """Tests get_download_info raising error when search finds no book."""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    async def mock_next():
        return []
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)
    mocker.patch('python_bridge.zlib_client', mock_client)
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None))

    with pytest.raises(ValueError, match=r"Book ID 12345 not found via search."): # Match helper error
        asyncio.run(get_download_info('12345')) # Use asyncio.run
    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)

# @pytest.mark.xfail(reason="Workaround using client.search not implemented yet") # Removed xfail
def test_get_download_info_workaround_ambiguous(mocker):
    """Tests get_download_info raising error when search finds multiple books."""
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    async def mock_next():
        return [MOCK_BOOK_RESULT, {'id': '67890'}]
    mock_paginator.next = mock_next
    # Mock the async search method using AsyncMock
    mock_client.search = AsyncMock(return_value=mock_paginator)
    mocker.patch('python_bridge.zlib_client', mock_client)
    mocker.patch('python_bridge.initialize_client', MagicMock(return_value=None))

    with pytest.raises(ValueError, match=r"Ambiguous search result for Book ID 12345."): # Match helper error
        asyncio.run(get_download_info('12345')) # Use asyncio.run
    mock_client.search.assert_called_once_with(q='id:12345', exact=True, count=1)



# --- Test Cases ---

# 6. Python Bridge - _process_epub
@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_epub_success(tmp_path, mock_ebooklib):
    epub_path = tmp_path / "test.epub"
    epub_path.touch() # Create dummy file
    mock_read_epub, _ = mock_ebooklib

    result = _process_epub(str(epub_path))

    mock_read_epub.assert_called_once_with(str(epub_path))
    assert "Chapter 1 content." in result
    assert "Chapter 2 content." in result
    assert "<script>" not in result # Check script tags removed
    assert "css" not in result # Check style content removed (implicitly via get_text)

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_epub_ebooklib_not_available(tmp_path, mocker):
    epub_path = tmp_path / "test.epub"
    epub_path.touch()
    mocker.patch('python_bridge.EBOOKLIB_AVAILABLE', False)
    with pytest.raises(ImportError, match="Required library 'ebooklib' is not installed"):
        _process_epub(str(epub_path))

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_epub_read_error(tmp_path, mock_ebooklib):
    epub_path = tmp_path / "test.epub"
    epub_path.touch()
    mock_read_epub, _ = mock_ebooklib
    mock_read_epub.side_effect = Exception("EPUB read failed")

    with pytest.raises(Exception, match="EPUB read failed"):
        _process_epub(str(epub_path))

# 7. Python Bridge - _process_txt
@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_txt_utf8(tmp_path):
    txt_path = tmp_path / "test_utf8.txt"
    content = "This is a UTF-8 file.\nWith multiple lines.\nAnd special chars: éàçü."
    txt_path.write_text(content, encoding='utf-8')

    result = _process_txt(str(txt_path))
    assert result == content

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_txt_latin1_fallback(tmp_path):
    txt_path = tmp_path / "test_latin1.txt"
    content_latin1 = "This is a Latin-1 file with chars like: äöüß."
    # Write as latin-1, this will cause UTF-8 read to fail
    txt_path.write_text(content_latin1, encoding='latin-1')

    result = _process_txt(str(txt_path))
    assert result == content_latin1 # Expect successful fallback read

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_txt_read_error(tmp_path, mocker):
    txt_path = tmp_path / "no_permission.txt"
    # Don't create the file, or mock open to raise an error
    mocker.patch('builtins.open', side_effect=IOError("Permission denied"))

    with pytest.raises(IOError, match="Permission denied"):
        _process_txt(str(txt_path))


# X. Python Bridge - _process_pdf (New Tests)
@pytest.mark.xfail(reason="_process_pdf implementation does not exist yet")
def test_process_pdf_success(tmp_path, mock_fitz):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.touch()
    mock_open_func, mock_doc, mock_page = mock_fitz

    result = _process_pdf(str(pdf_path))

    mock_open_func.assert_called_once_with(str(pdf_path))
    mock_doc.load_page.assert_called_once_with(0)
    mock_page.get_text.assert_called_once_with('text')
    assert result == "Sample PDF text content."

@pytest.mark.xfail(reason="_process_pdf implementation does not exist yet")
def test_process_pdf_encrypted(tmp_path, mock_fitz):
    pdf_path = tmp_path / "encrypted.pdf"
    pdf_path.touch()
    mock_open_func, mock_doc, _ = mock_fitz
    mock_doc.is_encrypted = True

    with pytest.raises(ValueError, match="Encrypted PDF files are not supported"):
        _process_pdf(str(pdf_path))
    mock_open_func.assert_called_once_with(str(pdf_path))

@pytest.mark.xfail(reason="_process_pdf implementation does not exist yet")
def test_process_pdf_corrupted(tmp_path, mock_fitz):
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.touch()
    mock_open_func, _, _ = mock_fitz
    mock_open_func.side_effect = RuntimeError("Failed to open PDF")

    with pytest.raises(RuntimeError, match="Failed to open PDF"):
        _process_pdf(str(pdf_path))
    mock_open_func.assert_called_once_with(str(pdf_path))

@pytest.mark.xfail(reason="_process_pdf implementation does not exist yet")
def test_process_pdf_image_based(tmp_path, mock_fitz):
    pdf_path = tmp_path / "image.pdf"
    pdf_path.touch()
    mock_open_func, mock_doc, mock_page = mock_fitz
    mock_page.get_text.return_value = "" # Simulate no text extracted

    result = _process_pdf(str(pdf_path))

    mock_open_func.assert_called_once_with(str(pdf_path))
    assert result == "" # Or potentially a warning message, TBD by implementation

@pytest.mark.xfail(reason="_process_pdf implementation does not exist yet")
def test_process_pdf_file_not_found(tmp_path, mock_fitz):
    # NOTE: We don't mock fitz.open raising FileNotFoundError, 
    # because the check should happen *before* calling fitz.open
    # This test relies on process_document or _process_pdf checking os.path.exists
    pdf_path = tmp_path / "not_a_real_file.pdf"
    # pdf_path.touch() # File does NOT exist
    mock_open_func, _, _ = mock_fitz

    # Assuming the check happens within _process_pdf itself
    with pytest.raises(FileNotFoundError):
         _process_pdf(str(pdf_path))
    # Or if the check is in process_document, this test might need adjustment
    # mock_open_func.assert_not_called() # If check is before fitz.open

# 5. Python Bridge - process_document
@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_document_epub_routing(tmp_path, mocker):
    epub_path = tmp_path / "book.epub"
    epub_path.touch()
    mock_proc_epub = mocker.patch('python_bridge._process_epub', return_value="EPUB Content")

    result = process_document(str(epub_path))

    mock_proc_epub.assert_called_once_with(str(epub_path))
    assert result == "EPUB Content"

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_document_txt_routing(tmp_path, mocker):
    txt_path = tmp_path / "doc.txt"
    txt_path.write_text("TXT Content", encoding='utf-8')
    mock_proc_txt = mocker.patch('python_bridge._process_txt', return_value="TXT Content")

    result = process_document(str(txt_path))

    mock_proc_txt.assert_called_once_with(str(txt_path))
    assert result == "TXT Content"


@pytest.mark.xfail(reason="PDF routing in process_document does not exist yet")
def test_process_document_pdf_routing(tmp_path, mocker):
    pdf_path = tmp_path / "book.pdf"
    pdf_path.touch()
    mock_proc_pdf = mocker.patch('python_bridge._process_pdf', return_value="PDF Content")

    result = process_document(str(pdf_path))

    mock_proc_pdf.assert_called_once_with(str(pdf_path))
    assert result == "PDF Content"

@pytest.mark.xfail(reason="Error propagation for PDF in process_document not tested")
def test_process_document_pdf_error_propagation(tmp_path, mocker):
    pdf_path = tmp_path / "error.pdf"
    pdf_path.touch()
    mock_proc_pdf = mocker.patch('python_bridge._process_pdf', side_effect=ValueError("PDF processing failed"))

    with pytest.raises(ValueError, match="PDF processing failed"):
        process_document(str(pdf_path))
    mock_proc_pdf.assert_called_once_with(str(pdf_path))

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_document_file_not_found(tmp_path):
    non_existent_path = tmp_path / "not_real.txt"
    with pytest.raises(FileNotFoundError):
        process_document(str(non_existent_path))

@pytest.mark.xfail(reason="Implementation does not exist yet")
def test_process_document_unsupported_format(tmp_path):
    unsupported_path = tmp_path / "image.jpg"
    unsupported_path.touch()
    with pytest.raises(ValueError, match="Unsupported file format: .jpg"):
        process_document(str(unsupported_path))

# 8. Python Bridge - Main Execution (Basic tests)
# TODO: Add tests for __main__ block if testing CLI interface is desired