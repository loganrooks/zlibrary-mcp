"""Anna's Archive source adapter.

Provides search and fast download functionality for Anna's Archive.
Search uses HTML scraping, downloads use the fast download API.

Key decisions:
- ANNAS-DOMAIN-INDEX-1: Use domain_index=1 for fast download API
  (domain_index=0 has SSL errors)
- ANNAS-SCRAPE-SEARCH: Search via HTML scraping (no search API exists)
"""

from typing import List, Optional
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from .base import SourceAdapter
from .config import SourceConfig
from .models import DownloadResult, QuotaInfo, SourceType, UnifiedBookResult


class QuotaExhaustedError(Exception):
    """Raised when Anna's Archive download quota is exhausted."""

    pass


class AnnasArchiveAdapter(SourceAdapter):
    """Anna's Archive adapter implementing SourceAdapter interface.

    Provides:
    - search(query) -> List[UnifiedBookResult] via HTML scraping
    - get_download_url(md5) -> DownloadResult via fast download API

    Configuration:
    - annas_base_url: Base URL for Anna's Archive (default: https://annas-archive.li)
    - annas_secret_key: API key for fast downloads (required for get_download_url)
    """

    def __init__(self, config: SourceConfig):
        """Initialize adapter with configuration.

        Args:
            config: SourceConfig with Anna's Archive settings
        """
        self.config = config
        self.base_url = config.annas_base_url.rstrip("/")
        self.secret_key = config.annas_secret_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.

        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30, follow_redirects=True)
        return self._client

    async def search(self, query: str, **kwargs) -> List[UnifiedBookResult]:
        """Search Anna's Archive for books.

        Scrapes HTML from /search?q={query} and extracts MD5 hashes
        using selector: a[href^='/md5/']

        Args:
            query: Search query string
            **kwargs: Additional search options (unused)

        Returns:
            List of UnifiedBookResult with source=ANNAS_ARCHIVE
        """
        client = await self._get_client()
        url = f"{self.base_url}/search?q={quote(query)}"
        response = await client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        seen = set()

        for link in soup.select("a[href^='/md5/']"):
            href = link.get("href", "")
            md5 = href.split("/")[-1]

            # Skip empty or duplicate MD5s
            if not md5 or md5 in seen:
                continue

            seen.add(md5)
            title = link.get_text(strip=True) or "Unknown"

            results.append(
                UnifiedBookResult(
                    md5=md5,
                    title=title,
                    source=SourceType.ANNAS_ARCHIVE,
                    extra={"url": f"{self.base_url}/md5/{md5}"},
                )
            )

        return results

    async def get_download_url(self, md5: str) -> DownloadResult:
        """Get fast download URL for a book.

        Calls /dyn/api/fast_download.json with MD5 and API key.
        CRITICAL: Uses domain_index=1 (domain_index=0 has SSL errors).

        Args:
            md5: MD5 hash identifying the book

        Returns:
            DownloadResult with URL and quota info

        Raises:
            ValueError: If ANNAS_SECRET_KEY not configured
            Exception: If API returns error or no download_url
        """
        if not self.secret_key:
            raise ValueError("ANNAS_SECRET_KEY not configured")

        client = await self._get_client()
        url = f"{self.base_url}/dyn/api/fast_download.json"
        params = {
            "md5": md5,
            "key": self.secret_key,
            "domain_index": 1,  # CRITICAL: Use 1, not 0 (SSL errors on 0)
        }

        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Check for API error
        if data.get("error"):
            raise Exception(f"Anna's Archive API error: {data['error']}")

        # Extract download URL
        download_url = data.get("download_url")
        if not download_url:
            raise Exception("No download_url in response")

        # Extract quota info if available
        quota_info = None
        account_info = data.get("account_fast_download_info")
        if account_info:
            quota_info = QuotaInfo(
                downloads_left=account_info.get("downloads_left", 0),
                downloads_per_day=account_info.get("downloads_per_day", 0),
                downloads_done_today=account_info.get("downloads_done_today", 0),
            )

        return DownloadResult(
            url=download_url,
            source=SourceType.ANNAS_ARCHIVE,
            quota_info=quota_info,
        )

    async def close(self) -> None:
        """Clean up HTTP client resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
