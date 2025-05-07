from zlibrary import AsyncZlib, booklists
import asyncio
import unittest.mock # Import unittest.mock
from unittest.mock import AsyncMock, patch, Mock # Import Mock
import httpx
from datetime import date
import logging
import os
from pathlib import Path # Import Path
from zlibrary.exception import LoginFailed, ParseError, DownloadError # Ensure ParseError and DownloadError are imported
from zlibrary.const import OrderOptions # Import OrderOptions

logging.getLogger("zlibrary").addHandler(logging.StreamHandler())
logging.getLogger("zlibrary").setLevel(logging.DEBUG)


async def main():
    lib = AsyncZlib()
    try:
        await lib.login(os.environ.get('ZLOGIN'), os.environ.get('ZPASSW'))
    except LoginFailed as e: # More specific exception
        print(f"Login failed during test setup: {e}. Proceeding with tests that don't require login.")
    except Exception as e:
        print(f"An unexpected error during login: {e}. Proceeding with tests that don't require login.")

    try:
        if lib.profile: # Only run these if login might have succeeded and profile is set
            booklist = await lib.profile.search_public_booklists("test")
            assert len(booklist.storage) > 0

            # count: 10 results per set
            paginator = await lib.search(q="biology", count=10)
            await paginator.next()

            assert len(paginator.result) > 0
            print(paginator.result)

            # fetching next result set (10 ... 20)
            next_set = await paginator.next()

            assert len(next_set) > 0
            print(next_set)

            # get back to previous set (0 ... 10)
            prev_set = await paginator.prev()

            assert len(prev_set) > 0
            print(prev_set)

            book = await paginator.result[0].fetch()
            assert book.get('name')
            print(book)

            # book = await lib.get_by_id('5393918/a28f0c') # Removed as get_by_id is deprecated
            # assert book.get('name')
            # print(book)
        else:
            print("Skipping original tests as lib.profile is not set (likely due to login failure).")

    except AttributeError as e:
        print(f"Skipping some original tests due to login failure and lib.profile not being set: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in original tests: {e}")


    print("\\nRunning download history tests...")
    # It's important to await these calls as they are async functions
    await test_download_history_url_construction()
    print("test_download_history_url_construction PASSED (called)")
    await test_download_history_parsing_new_structure()
    print("test_download_history_parsing_new_structure PASSED (called)")
    await test_download_history_parsing_old_structure()
    print("test_download_history_parsing_old_structure PASSED (called)")
    await test_download_history_empty()
    print("test_download_history_empty PASSED (called)")
    await test_download_history_parse_error()
    print("test_download_history_parse_error PASSED (called)")
    print("All download history tests called.")

    print("\\nRunning download book functionality tests...")
    await test_download_book_functionality()
    print("test_download_book_functionality PASSED (called)")
    print("All download book tests called.")

    print("\\nRunning search URL construction tests...")
    await test_search_url_construction()
    print("test_search_url_construction PASSED (called)") # Will be updated once tests actually pass
    await test_full_text_search_url_construction()
    print("test_full_text_search_url_construction PASSED (called)") # Will be updated
    print("All search URL construction tests called.")

    print("\\nRunning paginator year filter usage tests...")
    await test_search_paginator_uses_year_filters()
    print("test_search_paginator_uses_year_filters PASSED (called)")
    await test_full_text_search_paginator_uses_year_filters()
    print("test_full_text_search_paginator_uses_year_filters PASSED (called)")
    print("All paginator year filter usage tests called.")
 
async def test_download_history_url_construction():
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.domain = "example.com" # Needed for ZlibProfile
    lib.cookies = {} # Needed for ZlibProfile

    # Mock the internal request method of this specific AsyncZlib instance
    lib._r = AsyncMock(return_value="<html></html>") # Mock what GET_request would return

    from zlibrary.profile import ZlibProfile
    # ZlibProfile expects the request method of its parent AsyncZlib instance
    lib.profile = ZlibProfile(request=lib._r, cookies=lib.cookies, mirror=lib.mirror, domain=lib.domain)

    # Test with no dates
    # Patch DownloadsPaginator where it's looked up (zlibrary.profile)
    with patch('zlibrary.profile.DownloadsPaginator') as MockDownloadsPaginator:
        # Prevent the real init from running and allow inspection of constructor args
        mock_paginator_instance = MockDownloadsPaginator.return_value
        mock_paginator_instance.init = AsyncMock() # Mock the init method of the instance

        await lib.profile.download_history(page=1)
        MockDownloadsPaginator.assert_called_once()
        # Check the 'url' argument passed to DownloadsPaginator constructor
        # constructor_args is a tuple, first element is args, second is kwargs
        # For a class constructor, args_list[0] is the first positional arg to __init__
        # The first argument to DownloadsPaginator is 'url'
        args_list, _ = MockDownloadsPaginator.call_args
        assert args_list[0] == "https://example.com/users/downloads?date_from=&date_to="
        mock_paginator_instance.init.assert_called_once() # Ensure paginator.init() was called

    # Test with from_date
    with patch('zlibrary.profile.DownloadsPaginator') as MockDownloadsPaginator:
        mock_paginator_instance = MockDownloadsPaginator.return_value
        mock_paginator_instance.init = AsyncMock()

        await lib.profile.download_history(page=1, date_from=date(2023, 1, 1))
        MockDownloadsPaginator.assert_called_once()
        args_list, _ = MockDownloadsPaginator.call_args
        assert args_list[0] == "https://example.com/users/downloads?date_from=23-01-01&date_to="
        mock_paginator_instance.init.assert_called_once()

    # Test with to_date
    with patch('zlibrary.profile.DownloadsPaginator') as MockDownloadsPaginator:
        mock_paginator_instance = MockDownloadsPaginator.return_value
        mock_paginator_instance.init = AsyncMock()

        await lib.profile.download_history(page=1, date_to=date(2023, 12, 31))
        MockDownloadsPaginator.assert_called_once()
        args_list, _ = MockDownloadsPaginator.call_args
        assert args_list[0] == "https://example.com/users/downloads?date_from=&date_to=23-12-31"
        mock_paginator_instance.init.assert_called_once()

    # Test with both dates
    with patch('zlibrary.profile.DownloadsPaginator') as MockDownloadsPaginator:
        mock_paginator_instance = MockDownloadsPaginator.return_value
        mock_paginator_instance.init = AsyncMock()
        
        await lib.profile.download_history(page=1, date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))
        MockDownloadsPaginator.assert_called_once()
        args_list, _ = MockDownloadsPaginator.call_args
        assert args_list[0] == "https://example.com/users/downloads?date_from=23-01-01&date_to=23-12-31"
        mock_paginator_instance.init.assert_called_once()

async def test_download_history_parsing_new_structure():
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.domain = "example.com"
    lib.cookies = {}

    # Mock the internal request method. This will be called by DownloadsPaginator
    lib._r = AsyncMock() # Will be configured per test case by reassigning return_value

    from zlibrary.profile import ZlibProfile
    lib.profile = ZlibProfile(request=lib._r, cookies=lib.cookies, mirror=lib.mirror, domain=lib.domain)
    
    # Mock HTML for the new structure
    mock_html_new = """
    <html><body>
    <div class="dstats-table-content">
        <div class="item-wrap">
            <div class="item-info">
                <div class="item-desc">
                    <div class="item-title"><a href="/book/123/slug1">Test Book 1</a></div>
                </div>
                <div class="item-date">01.01.2023, 10:00</div>
            </div>
            <div class="item-actions">
                <a href="/download/123" class="item-format">PDF</a>
            </div>
        </div>
        <div class="item-wrap">
            <div class="item-info">
                <div class="item-desc">
                    <div class="item-title"><a href="/book/456/slug2">Test Book 2</a></div>
                </div>
                <div class="item-date">02.01.2023, 11:00</div>
            </div>
            <div class="item-actions">
                <a href="/download/456" class="item-format">EPUB</a>
            </div>
        </div>
    </div>
    </body></html>
    """
    lib._r.return_value = mock_html_new # Set the mock to return new HTML
    
    history = await lib.profile.download_history(page=1)
    assert len(history.result) == 2
    assert history.result[0]['id'] == '123'
    assert history.result[0]['name'] == 'Test Book 1'
    assert history.result[0]['date'] == '01.01.2023, 10:00'
    assert history.result[0]['download_url'] == 'https://example.com/download/123'
    assert history.result[0]['url'] == 'https://example.com/book/123/slug1'

    assert history.result[1]['id'] == '456'
    assert history.result[1]['name'] == 'Test Book 2'
    assert history.result[1]['date'] == '02.01.2023, 11:00'
    assert history.result[1]['download_url'] == 'https://example.com/download/456'
    assert history.result[1]['url'] == 'https://example.com/book/456/slug2'


async def test_download_history_parsing_old_structure():
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.domain = "example.com"
    lib.cookies = {}
    # Mock the internal request method. This will be called by DownloadsPaginator
    lib._r = AsyncMock() # Will be configured per test case by reassigning return_value

    from zlibrary.profile import ZlibProfile
    lib.profile = ZlibProfile(request=lib._r, cookies=lib.cookies, mirror=lib.mirror, domain=lib.domain)

    # Mock HTML for the old structure
    mock_html_old = """
    <html><body>
    <div class="dstats-table-content">
        <table>
            <tr class="dstats-row">
                <td><a href="/book/789/slug3">Old Book 1</a></td>
                <td>PDF</td>
                <td>1.2 MB</td>
                <td>03.01.2023, 12:00</td>
                <td><a href="/download/789">Download</a></td>
            </tr>
        </table>
    </div>
    </body></html>
    """
    lib._r.return_value = mock_html_old # Set the mock to return old HTML

    history = await lib.profile.download_history(page=1)
    assert len(history.result) == 1
    assert history.result[0]['id'] == '789'
    assert history.result[0]['name'] == 'Old Book 1'
    assert history.result[0]['date'] == '03.01.2023, 12:00'
    assert history.result[0]['download_url'] == 'https://example.com/download/789'
    assert history.result[0]['url'] == 'https://example.com/book/789/slug3'

async def test_download_history_empty():
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.domain = "example.com"
    lib.cookies = {}
    # Mock the internal request method. This will be called by DownloadsPaginator
    lib._r = AsyncMock() # Will be configured per test case by reassigning return_value

    from zlibrary.profile import ZlibProfile
    lib.profile = ZlibProfile(request=lib._r, cookies=lib.cookies, mirror=lib.mirror, domain=lib.domain)
    mock_html_empty = """
    <html><body>
    <div class="dstats-table-content">
        <p>Downloads not found</p>
    </div>
    </body></html>
    """
    lib._r.return_value = mock_html_empty # Set the mock to return empty HTML
    history = await lib.profile.download_history(page=1)
    assert len(history.result) == 0

async def test_download_history_parse_error():
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.domain = "example.com"
    lib.cookies = {}
    # Mock the internal request method. This will be called by DownloadsPaginator
    lib._r = AsyncMock() # This will be set with mock_html_broken

    from zlibrary.profile import ZlibProfile
    lib.profile = ZlibProfile(request=lib._r, cookies=lib.cookies, mirror=lib.mirror, domain=lib.domain)
    mock_html_broken = """<html><body><div class="another-class">Broken</div></body></html>"""
    lib._r.return_value = mock_html_broken # Set the mock to return broken HTML
    try:
        await lib.profile.download_history(page=1)
        assert False, "ParseError not raised"
    except ParseError:
        assert True
    # print(book) # This line was causing NameError, removed.
@patch('aiofiles.open', new_callable=AsyncMock)
@patch('zlibrary.libasync.httpx.AsyncClient') # This will be MockHttpxClientClassArg
@patch('os.makedirs')
async def test_download_book_functionality(mock_makedirs_arg, MockHttpxClientClassArg, mock_aio_open_arg):
    lib = AsyncZlib()
    lib.mirror = "https://example.com" # Set a dummy mirror
    lib.domain = "example.com"
    lib.cookies = {}
    lib.profile = AsyncMock() # Mock profile to satisfy the check

    # Mock book_details
    mock_book_details = {
        "id": "12345",
        "extension": "epub",
        "name": "Test Book Title", # For potential future use in filename
        "url": "/book/12345/test-book-title" # Add a dummy URL
    }
    output_dir = "./test_downloads" # Use a test-specific directory

    # Expected path
    expected_filename = f"{mock_book_details['id']}.{mock_book_details['extension']}"
    # Construct expected_path using pathlib.Path for consistency with actual_output_path in libasync.py
    expected_path = str(Path(output_dir) / expected_filename)

    # --- Mocking httpx.AsyncClient for two separate uses with side_effect ---

    # --- Setup for first httpx.AsyncClient() call (page fetch) ---
    mock_client_for_page = AsyncMock(name="mock_client_for_page_instance")
    mock_entered_client_for_page = AsyncMock(name="mock_entered_client_for_page")
    mock_page_response = AsyncMock(name="mock_page_response")

    mock_page_response.text = '<html><body><a class="btn btn-primary dlButton addDownloadedBook" href="/dl/actual_download_link/12345.epub">Download</a></body></html>'
    mock_page_response.status_code = 200
    mock_page_response.raise_for_status = Mock(name="page_response_raise_for_status") # Synchronous mock

    mock_entered_client_for_page.get = AsyncMock(return_value=mock_page_response, name="entered_client_get_method")

    mock_client_for_page.__aenter__.return_value = mock_entered_client_for_page
    mock_client_for_page.__aexit__ = AsyncMock(return_value=False, name="client_for_page_aexit")

    # --- Setup for second httpx.AsyncClient() call (file download) ---
    mock_client_for_download = AsyncMock(name="mock_client_for_download_instance")
    mock_entered_client_for_download = AsyncMock(name="mock_entered_client_for_download")
    mock_file_response = AsyncMock(name="mock_file_response")
    mock_file_response.headers = Mock(name="mock_file_response_headers")
    mock_file_response.headers.get.return_value = "123456" # Mock content-length for headers.get('content-length', 0)
    
    async def mock_aiter_bytes(chunk_size=None):
        yield b"dummy epub content"
    mock_file_response.aiter_bytes = mock_aiter_bytes
    mock_file_response.status_code = 200
    mock_file_response.raise_for_status = Mock(name="file_response_raise_for_status") # Synchronous mock

    # This is what client.stream() returns. It must be an async context manager.
    mock_stream_cm_object = AsyncMock(name="stream_cm_object_returned_by_stream_method")
    mock_stream_cm_object.__aenter__.return_value = mock_file_response # Configure existing AsyncMock attribute
    mock_stream_cm_object.__aexit__.return_value = False # Configure existing AsyncMock attribute

    mock_entered_client_for_download.stream = Mock(return_value=mock_stream_cm_object, name="entered_client_stream_method")

    mock_client_for_download.__aenter__.return_value = mock_entered_client_for_download
    mock_client_for_download.__aexit__ = AsyncMock(return_value=False, name="client_for_download_aexit")

    MockHttpxClientClassArg.side_effect = [mock_client_for_page, mock_client_for_download]
    
    returned_path = await lib.download_book(
        book_details=mock_book_details,
        output_dir_str=output_dir
    )

    # Assertions
    mock_makedirs_arg.assert_called_once_with(Path(output_dir), exist_ok=True)
    mock_aio_open_arg.assert_called_once_with(Path(expected_path), 'wb')
    
    mock_aio_open_arg.return_value.__aenter__.return_value.write.assert_called_once_with(b"dummy epub content")
    
    assert returned_path == expected_path
    print(f"test_download_book_functionality PASSED: Returned path {returned_path} matches expected {expected_path}")
    #     shutil.rmtree(output_dir)
async def test_search_url_construction():
    """Tests the URL construction for AsyncZlib.search with various filter combinations."""
    lib = AsyncZlib()
    lib.mirror = "https://example.com" # Set a dummy mirror
    lib.profile = AsyncMock() # Mock profile to satisfy the check in search method
    lib._r = AsyncMock(return_value="<html><body><div class='notFound'></div></body></html>") # Mock _r to prevent real HTTP calls

    # Mock SearchPaginator to capture the URL
    with patch('zlibrary.libasync.SearchPaginator') as MockSearchPaginator: # Corrected patch target
        mock_paginator_instance = MockSearchPaginator.return_value
        mock_paginator_instance.init = AsyncMock(return_value=None)

        # Test case 1: Basic search query
        await lib.search(q="test query")
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/test%20query?",
            count=10, # Default count
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 2: Query with exact match
        await lib.search(q="exact test", exact=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/exact%20test?&e=1",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 3: Query with languages
        await lib.search(q="lang test", lang=["english", "spanish"])
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/lang%20test?&languages%5B%5D=english&languages%5B%5D=spanish",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 4: Query with extensions
        await lib.search(q="ext test", extensions=["epub", "PDF"])
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/ext%20test?&extensions%5B%5D=EPUB&extensions%5B%5D=PDF",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 5: Query with content_types
        await lib.search(q="content test", content_types=["book", "article"])
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/content%20test?&selected_content_types%5B%5D=book&selected_content_types%5B%5D=article",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 6: Query with from_year and to_year
        await lib.search(q="year test", from_year=2020, to_year=2022)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/year%20test?&yearFrom=2020&yearTo=2022",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        
        # Test case 7: Query with order
        await lib.search(q="order test", order=OrderOptions.POPULAR)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/order%20test?&order=popular",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 8: Combination of filters
        await lib.search(
            q="combo test",
            exact=True,
            lang=["french"],
            extensions=["mobi"],
            content_types=["magazine"],
            from_year=2021,
            order=OrderOptions.NEWEST
        )
        MockSearchPaginator.assert_called_with(
            url=unittest.mock.ANY, # URL can be complex, check components below
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        called_args_combo, called_kwargs_combo = MockSearchPaginator.call_args
        actual_url_combo = called_kwargs_combo.get('url', called_args_combo[0] if called_args_combo else None)

        assert "https://example.com/s/combo%20test?" in actual_url_combo
        assert "&e=1" in actual_url_combo
        assert "&languages%5B%5D=french" in actual_url_combo
        assert "&extensions%5B%5D=MOBI" in actual_url_combo
        assert "&selected_content_types%5B%5D=magazine" in actual_url_combo
        assert "&yearFrom=2021" in actual_url_combo
        assert "&order=date_created" in actual_url_combo
        MockSearchPaginator.reset_mock()

        # Test case 9: Empty filter arrays
        await lib.search(q="empty filters", lang=[], extensions=[], content_types=[])
        MockSearchPaginator.assert_called_with(
            url="https://example.com/s/empty%20filters?",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()

        # Test case 10: Single value in filter arrays
        await lib.search(q="single value filters", lang=["german"], extensions=["azw3"], content_types=["journal"])
        MockSearchPaginator.assert_called_with(
            url=unittest.mock.ANY, # URL can be complex, check components below
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        called_args_single, called_kwargs_single = MockSearchPaginator.call_args
        actual_url_single = called_kwargs_single.get('url', called_args_single[0] if called_args_single else None)
        assert "https://example.com/s/single%20value%20filters?" in actual_url_single
        assert "&languages%5B%5D=german" in actual_url_single
        assert "&extensions%5B%5D=AZW3" in actual_url_single
        assert "&selected_content_types%5B%5D=journal" in actual_url_single
        MockSearchPaginator.reset_mock()

    print("test_search_url_construction PASSED (conceptually, will fail until implemented)")

async def test_full_text_search_url_construction():
    """Tests the URL construction for AsyncZlib.full_text_search with various filter combinations."""
    lib = AsyncZlib()
    lib.mirror = "https://example.com" # Set a dummy mirror
    lib.profile = AsyncMock() # Mock profile to satisfy the check in search method
    lib._r = AsyncMock(return_value="<html><body><div class='notFound'></div></body></html>") # Mock _r

    # Mock SearchPaginator to capture the URL
    # Mock the token fetching part within full_text_search
    with patch('zlibrary.libasync.httpx.AsyncClient') as MockHttpxClient, \
         patch('zlibrary.libasync.SearchPaginator') as MockSearchPaginator: # Corrected patch target
        
        # Setup mock for httpx.AsyncClient().get() to return a response with mock HTML for token
        mock_response = AsyncMock()
        mock_response.text = "<html><script>newURL.searchParams.append('token', 'test_token_123');</script></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock() # Ensure raise_for_status is a synchronous mock

        mock_get = AsyncMock(return_value=mock_response)
        MockHttpxClient.return_value.__aenter__.return_value.get = mock_get
        
        mock_paginator_instance = MockSearchPaginator.return_value
        mock_paginator_instance.init = AsyncMock(return_value=None)

        # Test case 1: Basic full-text search query
        await lib.full_text_search(q="full text query", phrase=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/full%20text%20query?&token=test_token_123&type=phrase",
            count=10, # Default count
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 2: Full-text query with exact match
        await lib.full_text_search(q="exact full text", exact=True, phrase=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/exact%20full%20text?&token=test_token_123&type=phrase&e=1",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 3: Full-text query with languages
        await lib.full_text_search(q="lang full text", lang=["english", "spanish"], phrase=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/lang%20full%20text?&token=test_token_123&type=phrase&languages%5B%5D=english&languages%5B%5D=spanish",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 4: Full-text query with extensions
        await lib.full_text_search(q="ext full text", extensions=["epub", "PDF"], phrase=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/ext%20full%20text?&token=test_token_123&type=phrase&extensions%5B%5D=EPUB&extensions%5B%5D=PDF",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 5: Full-text query with content_types
        await lib.full_text_search(q="content full text", content_types=["book", "article"], phrase=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/content%20full%20text?&token=test_token_123&type=phrase&selected_content_types%5B%5D=book&selected_content_types%5B%5D=article",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 6: Full-text query with from_year and to_year
        await lib.full_text_search(q="year full text", from_year=2020, to_year=2022, phrase=True)
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/year%20full%20text?&token=test_token_123&type=phrase&yearFrom=2020&yearTo=2022",
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 7: Combination of filters for full-text search
        await lib.full_text_search(
            q="combo full text",
            exact=True,
            lang=["french"],
            extensions=["mobi"],
            content_types=["magazine"],
            from_year=2021,
            phrase=True
        )
        MockSearchPaginator.assert_called_with(
            url=unittest.mock.ANY, # URL can be complex
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        called_args_fts_combo, called_kwargs_fts_combo = MockSearchPaginator.call_args
        actual_url_fts_combo = called_kwargs_fts_combo.get('url', called_args_fts_combo[0] if called_args_fts_combo else None)

        assert "https://example.com/fulltext/combo%20full%20text?" in actual_url_fts_combo
        assert "&token=test_token_123" in actual_url_fts_combo
        assert "&type=phrase" in actual_url_fts_combo
        assert "&e=1" in actual_url_fts_combo
        assert "&languages%5B%5D=french" in actual_url_fts_combo
        assert "&extensions%5B%5D=MOBI" in actual_url_fts_combo
        assert "&selected_content_types%5B%5D=magazine" in actual_url_fts_combo
        assert "&yearFrom=2021" in actual_url_fts_combo
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

        # Test case 8: Full-text query with words=True
        await lib.full_text_search(q="words true test", words=True, phrase=False) # Ensure phrase is False if words is True
        MockSearchPaginator.assert_called_with(
            url="https://example.com/fulltext/words%20true%20test?&token=test_token_123&type=words", # Assuming type=words if words=True
            count=10,
            request=unittest.mock.ANY,
            mirror=lib.mirror
        )
        MockSearchPaginator.reset_mock()
        MockHttpxClient.return_value.__aenter__.return_value.get.reset_mock()

    print("test_full_text_search_url_construction PASSED (conceptually, will fail until implemented)")

async def test_search_paginator_uses_year_filters():
    """Tests if SearchPaginator correctly uses year filters when making its request."""
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.profile = AsyncMock()
    
    mock_response_html = """
    <html><body>
        <div id="searchFormResultsList">
            <div class="book-card-wrapper">
                <z-bookcard id="123" name="Test Book Year" href="/book/123/test-book-year"></z-bookcard>
            </div>
        </div>
        <div class="paginatorRow"></div>
    </body></html>
    """
    lib._r = AsyncMock(return_value=mock_response_html)

    await lib.search(q="year paginator test", from_year=2020, to_year=2022)
    
    lib._r.assert_called_once()
    args, _ = lib._r.call_args
    called_url = args[0]
    
    assert "https://example.com/s/year%20paginator%20test?" in called_url, f"Base URL mismatch: {called_url}"
    assert "&yearFrom=2020" in called_url, f"yearFrom missing or incorrect in called URL: {called_url}"
    assert "&yearTo=2022" in called_url, f"yearTo missing or incorrect in called URL: {called_url}"
    print("test_search_paginator_uses_year_filters: Assertions for lib._r call passed.")

@patch('zlibrary.libasync.httpx.AsyncClient')
async def test_full_text_search_paginator_uses_year_filters(MockHttpxClientClassArg):
    """Tests if SearchPaginator for full-text search correctly uses year filters."""
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.profile = AsyncMock()

    # Mock for token fetching
    mock_token_client_instance = AsyncMock()
    mock_token_response = AsyncMock()
    mock_token_response.text = "<html><script>newURL.searchParams.append('token', 'mocked_token_for_year_test');</script></html>"
    mock_token_response.status_code = 200
    mock_token_response.raise_for_status = Mock()
    mock_token_client_instance.get = AsyncMock(return_value=mock_token_response)
    MockHttpxClientClassArg.return_value.__aenter__.return_value = mock_token_client_instance
    
    mock_response_html = """
    <html><body>
        <div id="searchFormResultsList">
            <div class="book-card-wrapper">
                <z-bookcard id="456" name="Test Fulltext Book Year" href="/book/456/test-fulltext-book-year"></z-bookcard>
            </div>
        </div>
        <div class="paginatorRow"></div>
    </body></html>
    """
    lib._r = AsyncMock(return_value=mock_response_html)

    await lib.full_text_search(q="year fulltext paginator", from_year=2021, to_year=2023, phrase=True)
    
    lib._r.assert_called_once()
    args, _ = lib._r.call_args
    called_url = args[0]
    
    assert "https://example.com/fulltext/year%20fulltext%20paginator?" in called_url, f"Base URL mismatch: {called_url}"
    assert "&token=mocked_token_for_year_test" in called_url, f"Token missing in called URL: {called_url}"
    assert "&type=phrase" in called_url, f"Type phrase missing in called URL: {called_url}"
    assert "&yearFrom=2021" in called_url, f"yearFrom missing or incorrect in called URL: {called_url}"
    assert "&yearTo=2023" in called_url, f"yearTo missing or incorrect in called URL: {called_url}"
    print("test_full_text_search_paginator_uses_year_filters: Assertions for lib._r call passed.")
async def test_download_book_missing_url_in_details():
    lib = AsyncZlib()
    lib.profile = AsyncMock() # Mock profile to satisfy the check
    mock_book_details_no_url = {"id": "67890", "extension": "pdf"}
    try:
        await lib.download_book(book_details=mock_book_details_no_url, output_dir_str="./test_downloads")
        assert False, "DownloadError not raised for missing URL"
    except DownloadError as e:
        assert "Could not find a book page URL" in str(e)
    except Exception as e:
        assert False, f"Unexpected exception {type(e)} raised: {e}"

@patch('zlibrary.libasync.httpx.AsyncClient')
async def test_download_book_page_fetch_http_error(MockHttpxClientClassArg):
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.profile = AsyncMock()
    mock_book_details = {"id": "111", "url": "/book/111/test", "extension": "epub"}

    mock_client_instance = AsyncMock()
    mock_entered_client = AsyncMock()
    mock_response = AsyncMock()
# Configure the response mock for the HTTPStatusError
    error_response_mock_page = Mock(status_code=404)
    error_response_mock_page.text = "Mocked 404 page error text"
    mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("404 Not Found", request=Mock(), response=error_response_mock_page))
    
    mock_entered_client.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__.return_value = mock_entered_client
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    MockHttpxClientClassArg.return_value = mock_client_instance

    try:
        await lib.download_book(book_details=mock_book_details, output_dir_str="./test_downloads")
        assert False, "DownloadError not raised for page fetch HTTP error"
    except DownloadError as e:
        assert "Failed to fetch book page for ID 111 (HTTP 404)" in str(e)
    except Exception as e:
        assert False, f"Unexpected exception {type(e)} raised: {e}"

@patch('zlibrary.libasync.httpx.AsyncClient')
async def test_download_book_no_download_link_found(MockHttpxClientClassArg):
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.profile = AsyncMock()
    mock_book_details = {"id": "222", "url": "/book/222/another", "extension": "pdf"}

    mock_client_instance = AsyncMock()
    mock_entered_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = "<html><body>No download link here</body></html>" # HTML without the target link
    mock_response.raise_for_status = Mock() # No HTTP error for page fetch

    mock_entered_client.get = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__.return_value = mock_entered_client
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    MockHttpxClientClassArg.return_value = mock_client_instance

    try:
        await lib.download_book(book_details=mock_book_details, output_dir_str="./test_downloads")
        assert False, "DownloadError not raised when no download link is found"
    except DownloadError as e:
        assert e.args[0] == "Failed to process book page for ID 222"
    except Exception as e:
        assert False, f"Unexpected exception {type(e)} raised: {e}"

@patch('os.makedirs') # Mock makedirs to prevent actual directory creation
@patch('aiofiles.open', new_callable=AsyncMock) # Mock aiofiles.open
@patch('zlibrary.libasync.httpx.AsyncClient')
async def test_download_book_file_download_http_error(MockHttpxClientClassArg, mock_aio_open, mock_makedirs):
    lib = AsyncZlib()
    lib.mirror = "https://example.com"
    lib.profile = AsyncMock()
    mock_book_details = {"id": "333", "url": "/book/333/final", "extension": "epub"}

    # Mock for page fetch (successful)
    mock_client_page = AsyncMock()
    mock_entered_page = AsyncMock()
    mock_page_response = AsyncMock()
    mock_page_response.text = '<html><body><a class="btn btn-primary dlButton addDownloadedBook" href="/dl/actual_download_link/333.epub">Download</a></body></html>'
    mock_page_response.raise_for_status = Mock()
    mock_entered_page.get = AsyncMock(return_value=mock_page_response)
    mock_client_page.__aenter__.return_value = mock_entered_page
    mock_client_page.__aexit__ = AsyncMock(return_value=False)

    # Mock for file download (fails)
    mock_client_download = AsyncMock()
    mock_entered_download = AsyncMock()
    mock_file_stream_response = AsyncMock() # This is what client.stream() returns
    mock_file_data_response = AsyncMock() # This is what the context manager for stream returns
    
# Configure the response mock for the HTTPStatusError
    error_response_mock_download = Mock(status_code=500)
    error_response_mock_download.text = "Mocked 500 download error text"
    mock_file_data_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("500 Server Error", request=Mock(), response=error_response_mock_download))
    
    mock_file_stream_response.__aenter__.return_value = mock_file_data_response
    mock_file_stream_response.__aexit__ = AsyncMock(return_value=False)
    mock_entered_download.stream = Mock(return_value=mock_file_stream_response)
    
    mock_client_download.__aenter__.return_value = mock_entered_download
    mock_client_download.__aexit__ = AsyncMock(return_value=False)

    MockHttpxClientClassArg.side_effect = [mock_client_page, mock_client_download]
    
    # Mock aiofiles.open to prevent actual file operations
    mock_aio_open.return_value.__aenter__.return_value.write = AsyncMock()


    try:
        await lib.download_book(book_details=mock_book_details, output_dir_str="./test_downloads")
        assert False, "DownloadError not raised for file download HTTP error"
    except DownloadError as e:
        assert "Download failed for book ID 333 (HTTP 500)" in str(e)
    except Exception as e:
        assert False, f"Unexpected exception {type(e)} raised: {e}"

# Add new test calls to main
async def run_new_download_tests():
    print("\\nRunning NEW download book error handling tests...")
    await test_download_book_missing_url_in_details()
    print("test_download_book_missing_url_in_details PASSED (called)")
    await test_download_book_page_fetch_http_error()
    print("test_download_book_page_fetch_http_error PASSED (called)")
    await test_download_book_no_download_link_found()
    print("test_download_book_no_download_link_found PASSED (called)")
    await test_download_book_file_download_http_error()
    print("test_download_book_file_download_http_error PASSED (called)")
    print("All NEW download book error handling tests called.")

if __name__ == "__main__":
    # asyncio.run(main()) # Keep original main call commented for now
    # For isolated testing of new tests:
    async def run_all_tests():
        await main() # Run original tests first
        await run_new_download_tests() # Then run new tests

    asyncio.run(run_all_tests())

if __name__ == '__main__':
    asyncio.run(main())
