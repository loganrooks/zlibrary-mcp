"""
EAPI client for Z-Library JSON API endpoints.

Bypasses Cloudflare by using POST/GET to /eapi/* endpoints
with cookie-based authentication.
"""

import httpx
import aiofiles
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


EAPI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded",
}


class EAPIClient:
    """Z-Library EAPI client using httpx with cookie-based auth."""

    def __init__(
        self,
        domain: str,
        remix_userid: Optional[str] = None,
        remix_userkey: Optional[str] = None,
    ):
        self.domain = domain.rstrip("/")
        self.remix_userid = remix_userid
        self.remix_userkey = remix_userkey
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def _cookies(self) -> Dict[str, str]:
        cookies = {"siteLanguageV2": "en"}
        if self.remix_userid:
            cookies["remix_userid"] = str(self.remix_userid)
        if self.remix_userkey:
            cookies["remix_userkey"] = str(self.remix_userkey)
        return cookies

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=EAPI_HEADERS,
                cookies=self._cookies,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _post(self, path: str, data: Optional[Dict[str, Any]] = None) -> dict:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        resp = await client.post(url, data=data or {})
        resp.raise_for_status()
        return resp.json()

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> dict:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # --- Auth ---

    async def login(self, email: str, password: str) -> dict:
        """POST /eapi/user/login — returns {success, user: {id, remix_userkey}}."""
        result = await self._post(
            "/eapi/user/login",
            {
                "email": email,
                "password": password,
            },
        )
        if result.get("success") == 1 and "user" in result:
            user = result["user"]
            self.remix_userid = str(user.get("id", ""))
            self.remix_userkey = str(user.get("remix_userkey", ""))
            # Recreate client with new cookies
            await self.close()
        return result

    # --- Book endpoints ---

    async def search(
        self,
        message: str,
        *,
        limit: int = 10,
        page: int = 1,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        languages: Optional[List[str]] = None,
        extensions: Optional[List[str]] = None,
        exact: bool = False,
        order: Optional[str] = None,
    ) -> dict:
        """POST /eapi/book/search with form-encoded body."""
        data: Dict[str, Any] = {
            "message": message,
            "limit": str(limit),
            "page": str(page),
        }
        if year_from is not None:
            data["yearFrom"] = str(year_from)
        if year_to is not None:
            data["yearTo"] = str(year_to)
        if languages:
            data["languages[]"] = languages
        if extensions:
            data["extensions[]"] = extensions
        if exact:
            data["e"] = "1"
        if order:
            data["order"] = order
        return await self._post("/eapi/book/search", data)

    async def get_book_info(self, book_id: int, book_hash: str) -> dict:
        """GET /eapi/book/{id}/{hash}."""
        return await self._get(f"/eapi/book/{book_id}/{book_hash}")

    async def get_download_link(self, book_id: int, book_hash: str) -> dict:
        """GET /eapi/book/{id}/{hash}/file."""
        return await self._get(f"/eapi/book/{book_id}/{book_hash}/file")

    async def get_recently(self) -> dict:
        """GET /eapi/book/recently."""
        return await self._get("/eapi/book/recently")

    async def get_most_popular(self) -> dict:
        """GET /eapi/book/most-popular."""
        return await self._get("/eapi/book/most-popular")

    async def get_downloaded(
        self,
        order: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """GET /eapi/user/book/downloaded."""
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if order:
            params["order"] = order
        return await self._get("/eapi/user/book/downloaded", params)

    async def get_profile(self) -> dict:
        """GET /eapi/user/profile."""
        return await self._get("/eapi/user/profile")

    async def get_similar(self, book_id: int, book_hash: str) -> dict:
        """GET /eapi/book/{id}/{hash}/similar."""
        return await self._get(f"/eapi/book/{book_id}/{book_hash}/similar")

    async def get_domains(self) -> dict:
        """GET /eapi/info/domains."""
        return await self._get("/eapi/info/domains")

    async def download_file(
        self,
        book_id: int,
        book_hash: str,
        output_dir: str,
        filename: Optional[str] = None,
    ) -> str:
        """Download a book file using EAPI download link.

        Args:
            book_id: Z-Library book ID
            book_hash: Book hash for URL construction
            output_dir: Directory to save the file
            filename: Optional filename; derived from response headers or URL if omitted

        Returns:
            Absolute path to the downloaded file

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            RuntimeError: If no download link or empty response
        """
        # Get download link from EAPI
        dl_resp = await self.get_download_link(book_id, book_hash)
        download_url = (
            dl_resp.get("file", {}).get("downloadLink")
            or dl_resp.get("downloadLink", "")
            or dl_resp.get("url", "")
            or dl_resp.get("link", "")
        )

        if not download_url:
            raise RuntimeError(
                f"EAPI returned no download link for book {book_id}. Response: {dl_resp}"
            )

        # Make URL absolute if needed
        if download_url.startswith("/"):
            download_url = f"{self.base_url}{download_url}"

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Stream download
        async with httpx.AsyncClient(
            cookies=self._cookies,
            follow_redirects=True,
            timeout=httpx.Timeout(60.0, connect=10.0),
        ) as dl_client:
            async with dl_client.stream("GET", download_url) as response:
                response.raise_for_status()

                # Determine filename
                if not filename:
                    # Try Content-Disposition header
                    cd = response.headers.get("content-disposition", "")
                    if "filename=" in cd:
                        # Extract filename from header
                        parts = cd.split("filename=")
                        if len(parts) > 1:
                            filename = parts[1].strip().strip('"').strip("'")
                    if not filename:
                        # Derive from URL path
                        url_path = str(response.url).split("?")[0]
                        filename = url_path.split("/")[-1] or f"{book_id}.bin"

                output_path = Path(output_dir) / filename

                async with aiofiles.open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)

        # Verify non-empty
        if not output_path.exists() or output_path.stat().st_size == 0:
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(f"Download produced empty file for book {book_id}")

        return str(output_path.resolve())


def normalize_eapi_book(eapi_book: dict) -> dict:
    """Map EAPI book fields to existing MCP tool output format."""
    author = eapi_book.get("author", "")
    return {
        "id": str(eapi_book.get("id", "")),
        "name": eapi_book.get("title", ""),
        "title": eapi_book.get("title", ""),
        "author": author,
        "authors": [author] if author else [],
        "year": eapi_book.get("year", ""),
        "language": eapi_book.get("language", ""),
        "extension": eapi_book.get("extension", ""),
        "size": eapi_book.get("filesize", ""),
        "rating": eapi_book.get("rating", ""),
        "quality": eapi_book.get("qualityScore", ""),
        "cover": eapi_book.get("cover", ""),
        "url": eapi_book.get("href", ""),
        "isbn": eapi_book.get("isbn", ""),
        "publisher": eapi_book.get("publisher", ""),
        "hash": eapi_book.get("hash", ""),
        "book_hash": eapi_book.get("hash", ""),
        "pages": eapi_book.get("pages", ""),
    }


def normalize_eapi_search_response(eapi_response: dict) -> List[dict]:
    """Extract books array from EAPI search response and normalize each."""
    books = eapi_response.get("books", [])
    return [normalize_eapi_book(b) for b in books]
