import asyncio
import httpx
import aiofiles
import os
from pathlib import Path
from bs4 import BeautifulSoup
import re # Added for token extraction

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
# Optional removed as it's covered by line 10 (now line 9)
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
                response = await GET_request(
                    url, proxy_list=self.proxy_list, cookies=self.cookies
                )
                if hasattr(response, 'text'):
                    logger.debug(f"Response text for {url}: {response.text[:1000]}") # Log first 1000 chars
                else:
                    logger.debug(f"Response for {url} is not an HTTPX object, it is a string: {str(response)[:1000]}") # Log first 1000 chars
                return response
        else:
            response = await GET_request(
                url, proxy_list=self.proxy_list, cookies=self.cookies
            )
            if hasattr(response, 'text'):
                logger.debug(f"Response text for {url}: {response.text[:1000]}") # Log first 1000 chars
            else:
                logger.debug(f"Response for {url} is not an HTTPX object, it is a string: {str(response)[:1000]}") # Log first 1000 chars
            return response

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
        content_types: Optional[List[str]] = None, # Added content_types
        order: Optional[Union[OrderOptions, str]] = None, # Added order parameter
        count: int = 10,
    ): # -> Tuple[SearchPaginator, str]: # Return type changed
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
            logger.info(f"AsyncZlib.search: 'lang' parameter is present: {lang}")
            assert type(lang) is list
            for la in lang:
                logger.info(f"AsyncZlib.search: Processing lang item: {la}")
                if type(la) is str:
                    payload += f"&languages%5B%5D={la}"
                    logger.info(f"AsyncZlib.search: Appended lang string. Payload now: {payload}")
                elif type(la) is Language:
                    payload += f"&languages%5B%5D={la.value}"
                    logger.info(f"AsyncZlib.search: Appended lang enum. Payload now: {payload}")
        else:
            logger.info("AsyncZlib.search: 'lang' parameter is NOT present or is empty.")
        if extensions:
            logger.info(f"AsyncZlib.search: 'extensions' parameter is present: {extensions}")
            assert type(extensions) is list
            for ext in extensions:
                logger.info(f"AsyncZlib.search: Processing ext item: {ext}")
                if type(ext) is str:
                    payload += f"&extensions%5B%5D={ext.upper()}"
                    logger.info(f"AsyncZlib.search: Appended ext string. Payload now: {payload}")
                elif type(ext) is Extension:
                    payload += f"&extensions%5B%5D={ext.value.upper()}"
                    logger.info(f"AsyncZlib.search: Appended ext enum. Payload now: {payload}")
        else:
            logger.info("AsyncZlib.search: 'extensions' parameter is NOT present or is empty.")
        if content_types:
            logger.info(f"AsyncZlib.search: 'content_types' parameter is present: {content_types}")
            assert type(content_types) is list
            for ct_value in content_types:
                logger.info(f"AsyncZlib.search: Processing content_type item: {ct_value}")
                payload += f"&selected_content_types%5B%5D={quote(ct_value)}"
                logger.info(f"AsyncZlib.search: Appended content_type. Payload now: {payload}")
        else:
            logger.info("AsyncZlib.search: 'content_types' parameter is NOT present or is empty.")
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


        logger.info(f"Constructed search_books URL (before Paginator init): {payload}")
        paginator = SearchPaginator(
            url=payload, count=count, request=self._r, mirror=self.mirror
        )
        await paginator.init()
        logger.info(f"Returning from AsyncZlib.search with payload: {payload}") # Log payload just before return
        return paginator, payload # Return paginator and the full payload URL

    # Removed deprecated get_by_id method.
    # Download workflow relies on bookDetails from search_books as per ADR-002.

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
        content_types: Optional[List[str]] = None, # Added content_types
        count: int = 10,
    ): # -> Tuple[SearchPaginator, str]: # Return type changed
        if not self.profile:
            raise NoProfileError
        if not q:
            raise EmptyQueryError
        if not phrase and not words:
            raise Exception(
                "You should either specify 'words=True' to match words, or 'phrase=True' to match phrase."
            )

        # Fetch token for full-text search
        token = None
        try:
            search_page_url = f"{self.mirror}/s/" # A page likely to contain the token
            logger.debug(f"full_text_search: Fetching search page for token: {search_page_url}")
            # Use httpx directly to fetch the search page HTML
            async with httpx.AsyncClient(proxy=self.proxy_list[0] if self.proxy_list else None, cookies=self.cookies, follow_redirects=True) as client:
                search_page_response = await client.get(search_page_url)
                search_page_response.raise_for_status()
                search_html_content = search_page_response.text
            
            soup = BeautifulSoup(search_html_content, 'lxml')
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Regex to find: newURL.searchParams.append('token', 'TOKEN_VALUE')
                    match = re.search(r"newURL\.searchParams\.append\('token',\s*'([^']+)'\)", script.string)
                    if match:
                        token = match.group(1)
                        logger.info(f"full_text_search: Extracted token: {token}")
                        break
            if not token:
                logger.warning("full_text_search: Could not extract token from search page. Proceeding without token, which may lead to incorrect results.")

        except httpx.HTTPStatusError as e:
            logger.error(f"full_text_search: HTTP error fetching search page for token: {e.response.status_code} - {e.response.text[:200]}", exc_info=True)
            logger.warning("full_text_search: Proceeding without token due to HTTP error during token fetch.")
        except Exception as e:
            logger.error(f"full_text_search: Error fetching or parsing search page for token: {e}", exc_info=True)
            logger.warning("full_text_search: Proceeding without token due to an unexpected error during token fetch.")

        payload = "%s/fulltext/%s?" % (self.mirror, quote(q))
        
        if token:
            payload += f"&token={quote(token)}"
        
        # Add type parameter based on words or phrase flags.
        # The initial check at line 335 ensures at least one is True.
        if words:
            payload += "&type=words"
        elif phrase: # This implies words is False
            payload += "&type=phrase"

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
                    payload += f"&extensions%5B%5D={ext.upper()}"
                elif type(ext) is Extension:
                    payload += f"&extensions%5B%5D={ext.value.upper()}"
        if content_types:
            assert type(content_types) is list
            for ct_value in content_types:
                payload += f"&selected_content_types%5B%5D={quote(ct_value)}"

        logger.info(f"Constructed full_text_search URL (before Paginator init): {payload}")
        paginator = SearchPaginator(
            url=payload, count=count, request=self._r, mirror=self.mirror
        )
        await paginator.init()
        logger.info(f"Returning from AsyncZlib.full_text_search with payload: {payload}") # Log payload just before return
        return paginator, payload # Return paginator and the full payload URL
    async def download_book(self, book_details: Dict, output_dir_str: str) -> str:
        """Downloads a book to the specified output path by scraping the book page."""
        if not self.profile:
            raise NoProfileError()

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

        # Construct Full File Path
        book_id_for_filename = book_details.get('id', 'unknown_book')
        extension = book_details.get('extension', 'epub') # Or derive more reliably if possible
        filename = f"{book_id_for_filename}.{extension}"
        
        output_directory = Path(output_dir_str) # Treat the input param as a directory
        actual_output_path = output_directory / filename

        logger.info(f"Attempting download from extracted URL: {download_url} to {actual_output_path}")

        # --- Ensure Output Directory Exists ---
        try:
            os.makedirs(output_directory, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {output_directory}")
        except OSError as e:
            logger.error(f"Failed to create output directory {output_directory}: {e}", exc_info=True)
            raise DownloadError(f"Failed to create output directory {output_directory}: {e}") from e

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

                      async with aiofiles.open(actual_output_path, 'wb') as f:
                          async for chunk in response.aiter_bytes():
                              await f.write(chunk)
                              downloaded_size += len(chunk)
                              # Optional: Add progress logging here if needed
                              # logger.debug(f"Downloaded {downloaded_size}/{total_size} bytes")

            logger.info(f"Successfully downloaded book ID {book_id} to {actual_output_path}")
            return str(actual_output_path)

        except httpx.HTTPStatusError as e:
             logger.error(f"HTTP error during download from {download_url}: {e.response.status_code} - {e.response.text[:200]}", exc_info=True)
             # Clean up partial file
             if os.path.exists(actual_output_path): os.remove(actual_output_path)
             raise DownloadError(f"Download failed for book ID {book_id} (HTTP {e.response.status_code})") from e
        except httpx.RequestError as e:
             logger.error(f"Network error during download from {download_url}: {e}", exc_info=True)
             if os.path.exists(actual_output_path): os.remove(actual_output_path)
             raise DownloadError(f"Download failed for book ID {book_id} (Network Error)") from e
        except Exception as e:
            logger.error(f"Unexpected error during download for book ID {book_id}: {e}", exc_info=True)
            # Clean up partial file
            try:
                if os.path.exists(actual_output_path):
                    os.remove(actual_output_path)
                    logger.debug(f"Removed incomplete file after unexpected error: {actual_output_path}")
            except OSError:
                 logger.warning(f"Could not remove incomplete file after unexpected error: {actual_output_path}")
            # Raise the final error
            raise DownloadError(f"An unexpected error occurred during download for book ID {book_id}") from e

