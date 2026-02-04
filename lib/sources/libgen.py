"""LibGen source adapter using libgen-api-enhanced library.

LibGen is used as a fallback when Anna's Archive quota is exhausted
or unavailable. LibGen has no quota limits but requires rate limiting
to avoid being blocked.
"""

import asyncio
import time
from typing import List

from .base import SourceAdapter
from .config import SourceConfig
from .models import DownloadResult, SourceType, UnifiedBookResult

# CRITICAL: Import is libgen_api_enhanced, NOT libgen_api
from libgen_api_enhanced import LibgenSearch


class LibgenAdapter(SourceAdapter):
    """LibGen source adapter.

    Wraps the synchronous libgen-api-enhanced library with async interface.
    Implements rate limiting to avoid being blocked by LibGen servers.

    Attributes:
        MIN_REQUEST_INTERVAL: Minimum seconds between requests (2.0)
    """

    MIN_REQUEST_INTERVAL = 2.0  # seconds between requests

    def __init__(self, config: SourceConfig):
        """Initialize adapter with configuration.

        Args:
            config: SourceConfig with libgen_mirror setting
        """
        self.config = config
        self.mirror = config.libgen_mirror
        self._last_request = 0.0

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        Sleeps if the last request was less than MIN_REQUEST_INTERVAL ago.
        """
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request = time.time()

    async def search(self, query: str, **kwargs) -> List[UnifiedBookResult]:
        """Search for books matching query.

        Uses libgen-api-enhanced LibgenSearch.search_title() wrapped in
        asyncio.to_thread() to avoid blocking the event loop.

        Args:
            query: Search string (title, author, ISBN, etc.)
            **kwargs: Ignored (for interface compatibility)

        Returns:
            List of UnifiedBookResult with source=LIBGEN
        """
        await self._rate_limit()

        def _search_sync():
            s = LibgenSearch(mirror=self.mirror)
            return s.search_title(query)

        results = await asyncio.to_thread(_search_sync)

        if not results:
            return []

        return [
            UnifiedBookResult(
                md5=getattr(book, "md5", "") or "",
                title=getattr(book, "title", "") or "",
                author=getattr(book, "author", "") or "",
                year=str(getattr(book, "year", "") or ""),
                extension=getattr(book, "extension", "") or "",
                size=getattr(book, "size", "") or "",
                source=SourceType.LIBGEN,
                download_url=getattr(book, "tor_download_link", "") or "",
                extra={
                    "id": getattr(book, "id", ""),
                    "language": getattr(book, "language", ""),
                    "pages": getattr(book, "pages", ""),
                },
            )
            for book in results
        ]

    async def get_download_url(self, md5: str) -> DownloadResult:
        """Get download URL for a book by MD5 hash.

        LibGen doesn't have direct MD5 lookup, so this searches by MD5
        as a query and finds the matching book.

        Args:
            md5: MD5 hash identifying the book

        Returns:
            DownloadResult with URL and no quota_info (LibGen has no quota)

        Raises:
            ValueError: If book with given MD5 not found
        """
        await self._rate_limit()

        def _search_by_md5():
            s = LibgenSearch(mirror=self.mirror)
            # LibGen doesn't have direct MD5 lookup, search by MD5 as query
            results = s.search_title(md5)
            for book in results:
                if getattr(book, "md5", "").lower() == md5.lower():
                    return book
            return None

        book = await asyncio.to_thread(_search_by_md5)

        if not book:
            raise ValueError(f"Book with MD5 {md5} not found in LibGen")

        download_url = getattr(book, "tor_download_link", "") or ""
        if not download_url:
            # Try mirrors if tor link not available
            mirrors = getattr(book, "mirrors", {})
            if mirrors:
                download_url = (
                    list(mirrors.values())[0]
                    if isinstance(mirrors, dict)
                    else str(mirrors)
                )

        if not download_url:
            raise ValueError(f"No download URL found for book {md5}")

        return DownloadResult(
            url=download_url,
            source=SourceType.LIBGEN,
            quota_info=None,  # LibGen has no quota
        )

    async def close(self) -> None:
        """Clean up resources.

        LibgenSearch doesn't maintain persistent connections,
        so this is a no-op.
        """
        pass
