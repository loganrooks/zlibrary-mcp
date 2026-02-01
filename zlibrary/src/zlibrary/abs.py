"""Abstract paginator and book item classes.

The HTML-parsing paginators (SearchPaginator, BooklistPaginator, DownloadsPaginator)
are DEPRECATED as of the EAPI migration. They are retained for backward compatibility
but are no longer used in the hot path. All active code uses EAPI endpoints instead.
"""

import re
import warnings
from typing import Dict, Any, Optional, List, Union, Callable, Coroutine
from typing import Callable, Optional
from urllib.parse import quote

from .exception import ParseError, BookNotFound
from .logger import logger

import json


DLNOTFOUND = "Downloads not found"
LISTNOTFOUND = "On your request nothing has been found"


class BookItem(dict):
    """Dictionary-like book item representation.

    Used across the library to hold book metadata.
    Can be created from EAPI data via _from_eapi_dict().
    """
    __r = None
    parsed = None
    mirror = ""

    def __init__(self, request=None, mirror=""):
        super().__init__()
        self.__r = request
        self.mirror = mirror

    @classmethod
    def _from_eapi_dict(cls, data: Dict[str, Any], mirror: str = "") -> "BookItem":
        """Create a BookItem from normalized EAPI data (output of normalize_eapi_book).

        Args:
            data: Normalized EAPI book dictionary.
            mirror: Mirror URL for constructing full URLs.

        Returns:
            BookItem populated with the EAPI data.
        """
        item = cls(request=None, mirror=mirror)
        item.update(data)
        item.parsed = True
        return item

    async def fetch(self):
        """Fetch book details from URL.

        DEPRECATED: Use EAPI get_book_info() instead.
        """
        warnings.warn(
            "BookItem.fetch() is deprecated. Use EAPIClient.get_book_info() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not self.__r:
            raise Exception("Request function not set for BookItem")
        if not self.get("url"):
            raise Exception("BookItem URL not set, cannot fetch details")
        raise NotImplementedError("HTML-based BookItem.fetch() is deprecated. Use EAPI.")

    def _parse_book_page_soup(self, soup) -> Dict[str, Any]:
        """Parse book page HTML soup.

        DEPRECATED: Use normalize_eapi_book() instead.
        """
        warnings.warn(
            "BookItem._parse_book_page_soup() is deprecated. Use normalize_eapi_book() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return {}


class SearchPaginator:
    """HTML-based search paginator.

    DEPRECATED: EAPI search returns paginated JSON directly.
    Use _EAPISearchResult (in libasync.py) instead.
    Retained for backward compatibility only.
    """
    __url = ""
    __pos = 0
    __r: Optional[Callable] = None

    mirror = ""
    page = 1
    total = 0
    count = 10

    result = []
    storage = {1: []}

    def __init__(self, url: str, count: int, request: Callable, mirror: str):
        warnings.warn(
            "SearchPaginator is deprecated. EAPI handles pagination directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        if count > 50:
            count = 50
        if count <= 0:
            count = 1
        self.count = count
        self.__url = url
        self.constructed_url = url
        self.__r = request
        self.mirror = mirror

    def __repr__(self):
        return f"<SearchPaginator [DEPRECATED] [{self.__url}]>"

    def parse_page(self, page):
        raise NotImplementedError("HTML parsing is deprecated. Use EAPI.")

    async def init(self):
        raise NotImplementedError("HTML-based SearchPaginator is deprecated. Use EAPI.")

    async def fetch_page(self):
        raise NotImplementedError("HTML-based SearchPaginator is deprecated. Use EAPI.")

    async def next(self):
        raise NotImplementedError("HTML-based SearchPaginator is deprecated. Use EAPI.")

    async def prev(self):
        raise NotImplementedError("HTML-based SearchPaginator is deprecated. Use EAPI.")

    async def next_page(self):
        raise NotImplementedError("HTML-based SearchPaginator is deprecated. Use EAPI.")

    async def prev_page(self):
        raise NotImplementedError("HTML-based SearchPaginator is deprecated. Use EAPI.")


class BooklistPaginator:
    """HTML-based booklist paginator.

    DEPRECATED: Booklist functionality is degraded under EAPI (no endpoint).
    Retained for backward compatibility only.
    """
    def __init__(self, url: str, count: int, request: Callable, mirror: str):
        warnings.warn(
            "BooklistPaginator is deprecated. EAPI has no booklist endpoint.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.result = []
        self.storage = {1: []}
        self.page = 1
        self.total = 0

    def __repr__(self):
        return "<BooklistPaginator [DEPRECATED]>"

    async def init(self):
        return self


class DownloadsPaginator:
    """HTML-based downloads paginator.

    DEPRECATED: Use EAPI get_downloaded() instead.
    Retained for backward compatibility only.
    """
    def __init__(self, url: str, page: int, request: Callable, mirror: str):
        warnings.warn(
            "DownloadsPaginator is deprecated. Use EAPIClient.get_downloaded() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.result = []
        self.storage = {1: []}
        self.page = page

    def __repr__(self):
        return "<DownloadsPaginator [DEPRECATED]>"

    async def init(self):
        return self


class BooklistItemPaginator(dict):
    """Dictionary representing a single booklist with its books.

    DEPRECATED: Booklist functionality is degraded under EAPI.
    """
    def __init__(self, request=None, mirror="", count: int = 10):
        super().__init__()
        self.books_result = []
        self.books_storage = {1: []}
