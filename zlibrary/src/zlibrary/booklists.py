"""Booklists module.

NOTE: EAPI does not have a dedicated booklist endpoint.
Booklist functionality is gracefully degraded - methods return empty results.
The Booklists class is retained for backward compatibility.
"""

from .const import OrderOptions
from typing import Callable, Optional
from .logger import logger


class Booklists:
    __r: Optional[Callable] = None
    cookies = {}
    mirror: Optional[str] = None

    def __init__(self, request, cookies, mirror):
        self.__r = request
        self.cookies = cookies
        self.mirror = mirror

    async def search_public(
        self, q: str = "", count: int = 10, order: OrderOptions | str = ""
    ):
        """Search public booklists.

        DEGRADED: EAPI has no booklist endpoint. Returns empty result set.
        """
        logger.warning("Booklists.search_public: EAPI has no booklist endpoint. Returning empty results.")
        return _EmptyBooklistResult()

    async def search_private(
        self, q: str = "", count: int = 10, order: OrderOptions | str = ""
    ):
        """Search private booklists.

        DEGRADED: EAPI has no booklist endpoint. Returns empty result set.
        """
        logger.warning("Booklists.search_private: EAPI has no booklist endpoint. Returning empty results.")
        return _EmptyBooklistResult()


class _EmptyBooklistResult:
    """Empty result placeholder for degraded booklist functionality."""

    def __init__(self):
        self.result = []
        self.storage = {1: []}
        self.page = 1
        self.total = 0

    def __repr__(self):
        return "<EmptyBooklistResult>"
