import pytest
import httpx
from unittest.mock import AsyncMock

from zlibrary.scrapers import scrape_metadata

# Placeholder for HTML content, to be refined with actual snippets
COMPLETE_HTML_SAMPLE = """
<html>
<body>
    <div class="book-details">
        <h1 itemprop="name">Test Book Title</h1>
        <div class="authors"><a itemprop="author">Author One</a>, <a itemprop="author">Author Two</a></div>
        <div class="series"><a href="/series/123">Test Series</a> (Book 1)</div>
        <div class="publisher">Test Publisher</div>
        <div class="year">2023</div>
        <div class="language">English</div>
        <div class="isbn">978-1234567890, 123456789X</div>
        <div class="category">Fiction</div>
        <div class="description" itemprop="description">This is a test description.</div>
        <img class="cover" itemprop="image" src="http://example.com/cover.jpg" />
        <div class="file-info">
            <span class="property_label">Pages:</span><span class="property_value">300</span>
            <span class="property_label">File size:</span><span class="property_value">2.5 MB</span>
            <span class="property_label">DOI:</span><span class="property_value">10.1234/test.doi</span>
        </div>
        <div id="booklists"><a href="/booklist/1">List 1</a></div>
        <div id="you-may-be-interested-in"><a href="/book/related1">Related 1</a></div>
        <div class="frequentTerms"><a>Term1</a> <a>Term2</a></div>
    </div>
</body>
</html>
"""

DETAILED_HTML_SAMPLE_FOR_PARSING = """
<html>
<body>
    <div class="book-details">
        <h1 itemprop="name">Detailed Book for Parsing</h1>
        <div class="authors">
            <a itemprop="author" href="/author/1">First Author</a>,
            <a itemprop="author" href="/author/2">Second, Name</a>,
            Author Three (No Link)
        </div>
        <div class="series"><a href="/series/456">Another Series</a> (Book #2)</div>
        <div class="publisher">  Another Publisher Inc.  </div>
        <div class="year">  2020  </div>
        <div class="language">  français  </div>
        <div class="isbn">ISBN: 978-0000000001, 0000000002 (pbk), ISBN13: 978-0000000003</div>
        <div class="category">Science, Technology</div>
        <div class="description" itemprop="description">  A detailed description with leading/trailing spaces.  </div>
        <img class="cover" itemprop="image" src="http://example.com/detailed_cover.png?query=param" />
        <div class="file-info">
            <span class="property_label">Pages:</span><span class="property_value">  450 pages </span>
            <span class="property_label">File size:</span><span class="property_value"> 1024 KB </span>
            <span class="property_label">DOI:</span><span class="property_value">  10.5678/another.doi  </span>
        </div>
        <div id="booklists">
            <a href="/booklist/alpha">Alpha List</a>
            <a href="/booklist/beta?sort=new">Beta List</a>
        </div>
        <div id="you-may-be-interested-in">
            <a href="/book/related_alpha">Related Alpha</a>
            <a href="/book/related_beta?ref=detail">Related Beta</a>
        </div>
        <div class="frequentTerms"><a>  Term A  </a> <a>Term B</a></div>
    </div>
</body>
</html>
"""

MINIMAL_HTML_SAMPLE = """
<html>
<body>
    <div class="book-details">
        <h1 itemprop="name">Minimal Book</h1>
        <!-- No authors, series, publisher, year, language, isbn, category, doi -->
        <div class="description" itemprop="description">Minimal description.</div>
        <img class="cover" itemprop="image" src="http://example.com/minimal_cover.jpg" />
        <div class="file-info">
            <!-- No pages, filesize, doi -->
        </div>
        <!-- No booklists, related books, frequent terms -->
    </div>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_scrape_metadata_complete_extraction():
    url = "http://example.com/book/1"
    mock_request = httpx.Request("GET", url)
    mock_response = httpx.Response(200, html=COMPLETE_HTML_SAMPLE, request=mock_request)
    
    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_session.get.return_value = mock_response

    expected_metadata = {
        "title": "Test Book Title",
        "authors": ["Author One", "Author Two"],
        "series_name": "Test Series",
        "series_url": "http://example.com/series/123", # Expect absolute URL
        "publisher": "Test Publisher",
        "publication_year": 2023,
        "language": "English",
        "isbn_list": ["9781234567890", "123456789X"], # Expect no hyphens
        "categories": ["Fiction"], # Assuming spec implies list even for one
        "description": "This is a test description.",
        "cover_image_url": "http://example.com/cover.jpg",
        "pages_count": 300,
        "filesize_str": "2.5 MB",
        "doi": "10.1234/test.doi",
        "booklists_urls": ["http://example.com/booklist/1"], # Expect absolute URL
        "you_may_be_interested_in_urls": ["http://example.com/book/related1"], # Expect absolute URL
        "most_frequent_terms": ["Term1", "Term2"],
        "source_url": url,
    }

    # This test will fail until scrape_metadata is implemented
    # and selectors are correctly defined in scrapers.py
    # based on docs/get-book-metadata-spec.md
    metadata = await scrape_metadata(url, mock_session)
    assert metadata == expected_metadata

@pytest.mark.asyncio
async def test_scrape_metadata_missing_optional_fields():
    url = "http://example.com/book/minimal"
    mock_request = httpx.Request("GET", url)
    mock_response = httpx.Response(200, html=MINIMAL_HTML_SAMPLE, request=mock_request)

    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_session.get.return_value = mock_response

    expected_metadata = {
        "title": "Minimal Book",
        "authors": [],
        "series_name": None,
        "series_url": None,
        "publisher": None,
        "publication_year": None,
        "language": None,
        "isbn_list": [],
        "categories": [],
        "description": "Minimal description.",
        "cover_image_url": "http://example.com/minimal_cover.jpg",
        "pages_count": None,
        "filesize_str": None,
        "doi": None,
        "booklists_urls": [],
        "you_may_be_interested_in_urls": [],
        "most_frequent_terms": [],
        "source_url": url,
    }
    metadata = await scrape_metadata(url, mock_session)
    assert metadata == expected_metadata

@pytest.mark.asyncio
async def test_scrape_metadata_specific_format_parsing_and_urls():
    url = "http://example.com/book/detailed"
    mock_request = httpx.Request("GET", url)
    mock_response = httpx.Response(200, html=DETAILED_HTML_SAMPLE_FOR_PARSING, request=mock_request)

    mock_session = AsyncMock(spec=httpx.AsyncClient)
    mock_session.get.return_value = mock_response

    expected_metadata = {
        "title": "Detailed Book for Parsing",
        "authors": ["First Author", "Second, Name", "Author Three (No Link)"],
        "series_name": "Another Series",
        "series_url": "http://example.com/series/456", # Expect absolute URL
        "publisher": "Another Publisher Inc.",
        "publication_year": 2020,
        "language": "français",
        "isbn_list": ["9780000000001", "0000000002", "9780000000003"], # Expect no hyphens
        "categories": ["Science", "Technology"],
        "description": "A detailed description with leading/trailing spaces.",
        "cover_image_url": "http://example.com/detailed_cover.png?query=param",
        "pages_count": 450,
        "filesize_str": "1024 KB",
        "doi": "10.5678/another.doi",
        "booklists_urls": ["http://example.com/booklist/alpha", "http://example.com/booklist/beta?sort=new"], # Expect absolute URLs
        "you_may_be_interested_in_urls": ["http://example.com/book/related_alpha", "http://example.com/book/related_beta?ref=detail"], # Expect absolute URLs
        "most_frequent_terms": ["Term A", "Term B"],
        "source_url": url,
    }
    metadata = await scrape_metadata(url, mock_session)
    assert metadata == expected_metadata

# TODO: Add more tests based on objectives:
# - Description and frequent terms handling (covered partially by above)
# - source_url pass-through (covered by all tests)
# - Edge cases for data cleaning/sanitization (e.g. empty strings for optional text fields if not None)