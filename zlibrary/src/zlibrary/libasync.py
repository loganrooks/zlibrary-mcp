import asyncio
import httpx
import aiofiles
import os
from pathlib import Path
from bs4 import BeautifulSoup

from typing import List, Union
from typing import List, Union, Optional, Dict
from urllib.parse import quote
from aiohttp.abc import AbstractCookieJar

from .logger import logger
from .exception import (
    BookNotFound,
    EmptyQueryError,
    ProxyNotMatchError,
    NoProfileError,
    NoDomainError,
    NoIdError,
    LoginFailed,
    ParseError,
    DownloadError
)
from .util import GET_request, POST_request, GET_request_cookies
from .abs import SearchPaginator, BookItem
from .profile import ZlibProfile
from .const import Extension, Language, OrderOptions
from typing import Optional
import json


ZLIB_DOMAIN = "https://z-library.sk/"
LOGIN_DOMAIN = "https://z-library.sk/rpc.php"

ZLIB_TOR_DOMAIN = (
    "http://bookszlibb74ugqojhzhg2a63w5i2atv5bqarulgczawnbmsb6s6qead.onion"
)
LOGIN_TOR_DOMAIN = (
    "http://loginzlib2vrak5zzpcocc3ouizykn6k5qecgj2tzlnab5wcbqhembyd.onion/rpc.php"
)


class AsyncZlib:
    semaphore = True
    onion = False

    __semaphore = asyncio.Semaphore(64)
    _jar: Optional[AbstractCookieJar] = None

    cookies = None
    proxy_list = None

    _mirror = ""
    login_domain = None
    domain = None
    profile = None

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, value):
        if not value.startswith("http"):
            value = "https://" + value
        self._mirror = value

    def __init__(
        self,
        onion: bool = False,
        proxy_list: Optional[list] = None,
        disable_semaphore: bool = False,
    ):
        if proxy_list:
            if type(proxy_list) is list:
                self.proxy_list = proxy_list
                logger.debug("Set proxy_list: %s", str(proxy_list))
            else:
                raise ProxyNotMatchError

        if onion:
            self.onion = True
            self.login_domain = LOGIN_TOR_DOMAIN
            self.domain = ZLIB_TOR_DOMAIN
            self.mirror = self.domain

            if not proxy_list:
                print(
                    "Tor proxy must be set to route through onion domains.\n"
                    "Set up a tor service and use: onion=True, proxy_list=['socks5://127.0.0.1:9050']"
                )
                exit(1)
        else:
            self.login_domain = LOGIN_DOMAIN
            self.domain = ZLIB_DOMAIN

        if disable_semaphore:
            self.semaphore = False

    async def _r(self, url: str):
        if self.semaphore:
            async with self.__semaphore:
                return await GET_request(
                    url, proxy_list=self.proxy_list, cookies=self.cookies
                )
        else:
            return await GET_request(
                url, proxy_list=self.proxy_list, cookies=self.cookies
            )

    async def login(self, email: str, password: str):
        data = {
            "isModal": True,
            "email": email,
            "password": password,
            "site_mode": "books",
            "action": "login",
            "isSingleLogin": 1,
            "redirectUrl": "",
            "gg_json_mode": 1,
        }

        resp, jar = await POST_request(
            self.login_domain, data, proxy_list=self.proxy_list
        )
        resp = json.loads(resp)
        resp = resp['response']
        logger.debug(f"Login response: {resp}")
        if resp.get('validationError'):
            raise LoginFailed(json.dumps(resp, indent=4))
        self._jar = jar

        self.cookies = {}
        for cookie in self._jar:
            self.cookies[cookie.key] = cookie.value
        logger.debug("Set cookies: %s", self.cookies)

        if self.onion and self.domain:
            url = self.domain + "/?remix_userkey=%s&remix_userid=%s" % (
                self.cookies["remix_userkey"],
                self.cookies["remix_userid"],
            )
            resp, jar = await GET_request_cookies(
                url, proxy_list=self.proxy_list, cookies=self.cookies
            )

            self._jar = jar
            for cookie in self._jar:
                self.cookies[cookie.key] = cookie.value
            logger.debug("Set cookies: %s", self.cookies)

            self.mirror = self.domain
            logger.info("Set working mirror: %s" % self.mirror)
        else:
            self.mirror = ZLIB_DOMAIN.strip("/")

            if not self.mirror:
                raise NoDomainError

        self.profile = ZlibProfile(self._r, self.cookies, self.mirror, ZLIB_DOMAIN)
        return self.profile

    async def logout(self):
        self._jar = None
        self.cookies = None

    async def search(
        self,
        q: str = "",
        exact: bool = False,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        lang: List[Union[Language, str]] = [],
        extensions: List[Union[Extension, str]] = [],
        order: Optional[Union[OrderOptions, str]] = None, # Added order parameter
        count: int = 10,
    ) -> SearchPaginator:
        if not self.profile:
            raise NoProfileError
        # Allow empty query if sorting by newest (to get all recent books)
        # if not q:
        #     raise EmptyQueryError
        if not q and not (order and (order == OrderOptions.NEWEST or order == "date_created")):
             raise EmptyQueryError("Search query cannot be empty unless ordering by newest.")


        payload = f"{self.mirror}/s/{quote(q)}?"
        if exact:
            payload += "&e=1"
        if from_year:
            assert str(from_year).isdigit()
            payload += f"&yearFrom={from_year}"
        if to_year:
            assert str(to_year).isdigit()
            payload += f"&yearTo={to_year}"
        if lang:
            assert type(lang) is list
            for la in lang:
                if type(la) is str:
                    payload += f"&languages%5B%5D={la}"
                elif type(la) is Language:
                    payload += f"&languages%5B%5D={la.value}"
        if extensions:
            assert type(extensions) is list
            for ext in extensions:
                if type(ext) is str:
                    payload += f"&extensions%5B%5D={ext}"
                elif type(ext) is Extension:
                    payload += f"&extensions%5B%5D={ext.value}"
        # Add order logic
        if order:
            if isinstance(order, OrderOptions):
                payload += f"&order={order.value}"
            elif isinstance(order, str):
                 # Basic validation for string input
                 allowed_orders = [opt.value for opt in OrderOptions]
                 if order in allowed_orders:
                      payload += f"&order={order}"
                 else:
                      logger.warning(f"Invalid string value '{order}' provided for order parameter. Ignoring.")
            else:
                 logger.warning(f"Invalid type '{type(order)}' provided for order parameter. Ignoring.")


        paginator = SearchPaginator(
            url=payload, count=count, request=self._r, mirror=self.mirror
        )
        await paginator.init()
        return paginator

    async def get_by_id(self, id: str = ""):
        """Gets book details by searching for its ID."""
        if not id:
            raise NoIdError
        if not self.profile:
            raise NoProfileError

        try:
            # Search for the specific ID
            search_query = f"id:{id}"
            search_url_for_log = f"{self.mirror}/s/{quote(search_query)}?exact=1" # Construct approx URL for logging
            logger.debug(f"get_by_id: Attempting search with query: '{search_query}' (URL approx: {search_url_for_log})")
            paginator = await self.search(q=search_query, exact=True, count=1)
            # Assuming paginator.init() was called within self.search and parsed the first page
            # We need the results from the paginator's storage or result attribute
            results = paginator.result # Access the parsed results directly

            if not results:
                # Explicitly log that the search returned no results
                logger.warning(f"get_by_id: Search for '{search_query}' (URL approx: {search_url_for_log}) returned 0 results.")
                raise BookNotFound(f"Book with ID {id} not found via search.")

            if len(results) > 1:
                # This shouldn't happen with exact=True and count=1, but handle defensively
                logger.warning(f"get_by_id: Ambiguous result: Found {len(results)} books for ID {id} via search. Returning first.")
                # raise ParseError(f"Ambiguous result: Found multiple books for ID {id}.") # Decide if this should be an error

            book_item = results[0]
            logger.debug(f"get_by_id: Found book via search: {book_item.get('name')}")
            # Ensure the full book details are fetched if needed (search results might be partial)
            # Note: The previous fix assumed BookItem.fetch was needed, but the current code
            # implies the paginator might already contain full details if parsing succeeded.
            # Let's keep the check for now, but it might be redundant if abs.py parsing is complete.
            if not book_item.parsed:
                 logger.debug(f"get_by_id: Search result for id:{id} is partial or not marked parsed, fetching full details...")
                 await book_item.fetch() # fetch() should ideally mark item as parsed
                 logger.debug(f"get_by_id: Full details fetched for id:{id}")

            return book_item
        except BookNotFound as bnf:
             # Re-raise BookNotFound specifically if caught from search/fetch
             logger.warning(f"get_by_id({id}) resulted in BookNotFound: {bnf}")
             raise bnf
        except ParseError as pe:
             logger.error(f"get_by_id({id}) resulted in ParseError during search/fetch: {pe}", exc_info=True)
             raise pe
        except Exception as e:
            # Catch other potential errors during search/parsing
            logger.error(f"get_by_id({id}) failed due to an unexpected error: {e}", exc_info=True)
            raise ParseError(f"Failed to get book by ID {id} due to an unexpected error: {e}") from e

    async def full_text_search(
        self,
        q: str = "",
        exact: bool = False,
        phrase: bool = False,
        words: bool = False,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        lang: List[Union[Language, str]] = [],
        extensions: List[Union[Extension, str]] = [],
        count: int = 10,
    ) -> SearchPaginator:
        if not self.profile:
            raise NoProfileError
        if not q:
            raise EmptyQueryError
        if not phrase and not words:
            raise Exception(
                "You should either specify 'words=True' to match words, or 'phrase=True' to match phrase."
            )

        payload = "%s/fulltext/%s?" % (self.mirror, quote(q))
        if phrase:
            check = q.split(" ")
            if len(check) < 2:
                raise Exception(
                    (
                        "At least 2 words must be provided for phrase search. "
                        "Use 'words=True' to match a single word."
                    )
                )
            payload += "&type=phrase"
        else:
            payload += "&type=words"

        if exact:
            payload += "&e=1"
        if from_year:
            assert str(from_year).isdigit()
            payload += f"&yearFrom={from_year}"
        if to_year:
            assert str(to_year).isdigit()
            payload += f"&yearTo={to_year}"
        if lang:
            assert type(lang) is list
            for la in lang:
                if type(la) is str:
                    payload += f"&languages%5B%5D={la}"
                elif type(la) is Language:
                    payload += f"&languages%5B%5D={la.value}"
        if extensions:
            assert type(extensions) is list
            for ext in extensions:
                if type(ext) is str:
                    payload += f"&extensions%5B%5D={ext}"
                elif type(ext) is Extension:
                    payload += f"&extensions%5B%5D={ext.value}"

        paginator = SearchPaginator(
            url=payload, count=count, request=self._r, mirror=self.mirror
        )
        await paginator.init()
        return paginator

    async def download_book(self, book_details: Dict, output_path: str) -> None:
        """Downloads a book to the specified output path by scraping the book page."""
        if not self.profile:
            raise NoProfileError("Login required before downloading.")

        book_id = book_details.get('id', 'Unknown')
        book_page_url = book_details.get('url')

        if not book_page_url:
            logger.error(f"No book page URL ('url') found in book_details for book ID: {book_id}. Details: {book_details}")
            raise DownloadError(f"Could not find a book page URL for book ID: {book_id}")

        # Ensure the book page URL includes the mirror if it's relative
        if not book_page_url.startswith('http'):
            if not self.mirror:
                 raise DownloadError("Cannot construct book page URL: Z-Library mirror/domain is not set.")
            book_page_url = f"{self.mirror.rstrip('/')}/{book_page_url.lstrip('/')}"

        logger.info(f"Fetching book page to find download link: {book_page_url}")

        try:
            # Use httpx directly to fetch the book page HTML, ensuring we get the full response object
            async with httpx.AsyncClient(proxy=self.proxy_list[0] if self.proxy_list else None, cookies=self.cookies, follow_redirects=True) as client:
                 response = await client.get(book_page_url)
                 response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                 html_content = response.text
                 soup = BeautifulSoup(html_content, 'lxml') # Use lxml parser

            # --- Find the actual download link ---
            # Attempt to find the download button/link using a common selector pattern.
            # *** This selector might need adjustment based on actual website structure ***
            download_link_element = soup.select_one('a.addDownloadedBook[href*="/dl/"]') # Updated selector based on user feedback

            if not download_link_element or not download_link_element.get('href'):
                logger.error(f"Could not find download link element or href on book page: {book_page_url}. Selector 'a.addDownloadedBook[href*=\"/dl/\"]' failed.")
                # Optionally log soup excerpt for debugging
                # logger.debug(f"HTML excerpt: {soup.prettify()[:1000]}")
                raise DownloadError(f"Could not extract download link from book page for ID: {book_id}")

            download_url = download_link_element['href']
            logger.info(f"Found download link: {download_url}")

            # Ensure the extracted download URL includes the mirror if it's relative
            if not download_url.startswith('http'):
                if not self.mirror:
                     raise DownloadError("Cannot construct download URL: Z-Library mirror/domain is not set.")
                download_url = f"{self.mirror.rstrip('/')}/{download_url.lstrip('/')}"

        except httpx.HTTPStatusError as e:
             logger.error(f"HTTP error fetching book page {book_page_url}: {e.response.status_code} - {e.response.text[:200]}", exc_info=True)
             raise DownloadError(f"Failed to fetch book page for ID {book_id} (HTTP {e.response.status_code})") from e
        except httpx.RequestError as e:
             logger.error(f"Network error fetching book page {book_page_url}: {e}", exc_info=True)
             raise DownloadError(f"Failed to fetch book page for ID {book_id} (Network Error)") from e
        except Exception as e:
            logger.error(f"Error parsing book page or finding download link for {book_page_url}: {e}", exc_info=True)
            raise DownloadError(f"Failed to process book page for ID {book_id}") from e


        logger.info(f"Attempting download from extracted URL: {download_url} to {output_path}")

        # --- Ensure Output Directory Exists ---
        try:
            output_dir = Path(output_path).parent
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {output_dir}")
        except OSError as e:
            logger.error(f"Failed to create output directory {output_dir}: {e}", exc_info=True)
            raise DownloadError(f"Failed to create output directory {output_dir}: {e}") from e

        # --- Perform Download using httpx stream ---
        try:
            # Use httpx directly for streaming download
            async with httpx.AsyncClient(proxy=self.proxy_list[0] if self.proxy_list else None, cookies=self.cookies, follow_redirects=True) as client:
                 async with client.stream("GET", download_url) as response:
                      response.raise_for_status() # Check for HTTP errors

                      # Get total size for progress (optional)
                      total_size = int(response.headers.get('content-length', 0))
                      downloaded_size = 0
                      logger.info(f"Starting download ({total_size} bytes)...")

                      async with aiofiles.open(output_path, 'wb') as f:
                          async for chunk in response.aiter_bytes():
                              await f.write(chunk)
                              downloaded_size += len(chunk)
                              # Optional: Add progress logging here if needed
                              # logger.debug(f"Downloaded {downloaded_size}/{total_size} bytes")

            logger.info(f"Successfully downloaded book ID {book_id} to {output_path}")
            # Method returns None on success
            return None # Explicitly return None

        except httpx.HTTPStatusError as e:
             logger.error(f"HTTP error during download from {download_url}: {e.response.status_code} - {e.response.text[:200]}", exc_info=True)
             # Clean up partial file
             if os.path.exists(output_path): os.remove(output_path)
             raise DownloadError(f"Download failed for book ID {book_id} (HTTP {e.response.status_code})") from e
        except httpx.RequestError as e:
             logger.error(f"Network error during download from {download_url}: {e}", exc_info=True)
             if os.path.exists(output_path): os.remove(output_path)
             raise DownloadError(f"Download failed for book ID {book_id} (Network Error)") from e
        except Exception as e:
            logger.error(f"Unexpected error during download for book ID {book_id}: {e}", exc_info=True)
            # Clean up partial file
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
                    logger.debug(f"Removed incomplete file after unexpected error: {output_path}")
            except OSError:
                 logger.warning(f"Could not remove incomplete file after unexpected error: {output_path}")
            # Raise the final error
            raise DownloadError(f"An unexpected error occurred during download for book ID {book_id}") from e

