from datetime import date
from typing import Optional
from .eapi import EAPIClient, normalize_eapi_book
from .booklists import Booklists, OrderOptions
from .exception import ParseError
from .logger import logger

class ZlibProfile:
    __r = None
    cookies = {}
    domain = None
    mirror = None
    _eapi: Optional[EAPIClient] = None

    def __init__(self, request, cookies, mirror, domain, eapi_client=None):
        self.__r = request
        self.cookies = cookies
        self.mirror = mirror
        self.domain = domain
        self._eapi = eapi_client

    async def get_limits(self):
        """Get download limits via EAPI profile endpoint."""
        if not self._eapi:
            raise ParseError("EAPI client not available for get_limits()")

        try:
            profile_resp = await self._eapi.get_profile()
            user = profile_resp.get("user", {})

            # Extract download limits from profile response
            downloads_today = user.get("downloads_today", 0)
            downloads_limit = user.get("downloads_limit", 0)

            # Handle alternative response structures
            if not downloads_limit:
                downloads_limit = user.get("dailyDownloadLimit", 0)
            if not downloads_today:
                downloads_today = user.get("dailyDownloadsCount", 0)

            daily = int(downloads_today) if downloads_today else 0
            allowed = int(downloads_limit) if downloads_limit else 0

            return {
                "daily_amount": daily,
                "daily_allowed": allowed,
                "daily_remaining": max(0, allowed - daily),
                "daily_reset": "",  # EAPI profile doesn't provide reset time
            }
        except Exception as e:
            logger.error(f"EAPI get_limits failed: {e}", exc_info=True)
            raise ParseError(f"Failed to get download limits via EAPI: {e}") from e

    async def download_history(self, page: int = 1, date_from: date = None, date_to: date = None):
        """Get download history via EAPI."""
        if date_from:
            assert type(date_from) is date
        if date_to:
            assert type(date_to) is date
        if page:
            assert type(page) is int

        if not self._eapi:
            raise ParseError("EAPI client not available for download_history()")

        try:
            resp = await self._eapi.get_downloaded(page=page, limit=10)
            books_raw = resp.get("books", [])
            books = [normalize_eapi_book(b) for b in books_raw]

            # Return a simple result object with .result for backward compat
            result = _DownloadHistoryResult(books)
            return result
        except Exception as e:
            logger.error(f"EAPI download_history failed: {e}", exc_info=True)
            raise ParseError(f"Failed to get download history via EAPI: {e}") from e

    async def search_public_booklists(self, q: str, count: int = 10, order: OrderOptions = ""):
        """Search public booklists.

        NOTE: EAPI may not have a booklist endpoint. This functionality
        is degraded — returns empty results with a warning.
        """
        logger.warning("Booklist search is degraded: EAPI has no booklist endpoint. Returning empty results.")
        result = _BooklistResult([])
        return result

    async def search_private_booklists(self, q: str, count: int = 10, order: OrderOptions = ""):
        """Search private booklists.

        NOTE: EAPI may not have a booklist endpoint. This functionality
        is degraded — returns empty results with a warning.
        """
        logger.warning("Private booklist search is degraded: EAPI has no booklist endpoint. Returning empty results.")
        result = _BooklistResult([])
        return result


class _DownloadHistoryResult:
    """Lightweight wrapper for download history results (backward compat with DownloadsPaginator)."""

    def __init__(self, books):
        self.result = books
        self.storage = {1: books}
        self.page = 1

    def __repr__(self):
        return f"<DownloadHistoryResult count={len(self.result)}>"


class _BooklistResult:
    """Lightweight wrapper for booklist results (backward compat with BooklistPaginator)."""

    def __init__(self, items):
        self.result = items
        self.storage = {1: items}
        self.page = 1

    def __repr__(self):
        return f"<BooklistResult count={len(self.result)}>"
