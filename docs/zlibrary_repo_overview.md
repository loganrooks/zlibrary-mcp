# Overview of `setraline/zlibrary`
## Files
1.  **`__init__.py`**:
    *   **Purpose**: This file marks the `zlibrary` directory as a Python package.
    *   **Contents & Responsibilities**: It imports the main `AsyncZlib` class from `libasync.py` and the `OrderOptions`, `Extension`, and `Language` enums from `const.py`. This makes these key components directly available when someone imports the `zlibrary` package (e.g., `from zlibrary import AsyncZlib`).

2.  **`abs.py`**:
    *   **Purpose**: Defines classes for handling paginated results and representing individual items (books, booklists) returned by the API. It heavily relies on parsing HTML content using `BeautifulSoup`.
    *   **Contents & Responsibilities**:
        *   `SearchPaginator`: Handles pagination for general book search results. It fetches pages, parses the HTML using `BeautifulSoup` to find book items (`z-bookcard` elements), extracts metadata, stores results per page, and provides `next()`/`prev()` methods to navigate results.
        *   `BooklistPaginator`: Handles pagination for *lists* of booklists (both public and private). It parses the HTML (`z-booklist` elements), extracts booklist metadata (name, author, description, etc.), and includes lazy-loaded book previews within each list.
        *   `DownloadsPaginator`: Handles pagination for the user's download history. It parses the HTML table (`dstats-row`) on the download statistics page.
        *   `BookItem`: Represents a single book. It stores basic metadata obtained from search results and includes an asynchronous `fetch()` method to retrieve full book details (like description, ISBN, categories, download URL) by parsing the book's specific page HTML.
        *   `BooklistItemPaginator`: Represents a single booklist and handles fetching *all* books within that specific list. It uses a different API endpoint (`papi/booklist/{id}/get-books`) that returns JSON, parsing that instead of HTML to get the full list of books. It also provides pagination (`next`/`prev`) for the books *within* that list.

3.  **`booklists.py`**:
    *   **Purpose**: Provides an interface specifically for searching Z-Library's booklists feature.
    *   **Contents & Responsibilities**:
        *   `Booklists` class: Contains methods `search_public()` and `search_private()` which construct the appropriate URLs and initialize a `BooklistPaginator` (from `abs.py`) to handle the actual fetching and parsing of booklist search results.

4.  **`const.py`**:
    *   **Purpose**: Defines constant values used throughout the library, primarily for API parameters.
    *   **Contents & Responsibilities**: Contains `Enum` classes:
        *   `Extension`: Defines common ebook file extensions (PDF, EPUB, MOBI, etc.).
        *   `OrderOptions`: Defines sorting options for search results (Popular, Newest, Recent).
        *   `Language`: Defines a very extensive list of language codes that can be used for filtering searches.

5.  **`exception.py`**:
    *   **Purpose**: Defines custom exception classes for specific error conditions encountered by the library.
    *   **Contents & Responsibilities**: Defines several exception types (e.g., `LoopError`, `ParseError`, `LoginFailed`, `NoDomainError`, `EmptyQueryError`, `ProxyNotMatchError`, `NoProfileError`, `NoIdError`) that inherit from Python's base `Exception`. This allows code using the library to catch specific Z-Library related errors.

6.  **`libasync.py`**:
    *   **Purpose**: This is the main entry point and core logic file for the asynchronous Z-Library client.
    *   **Contents & Responsibilities**:
        *   `AsyncZlib` class:
            *   Initialization (`__init__`): Sets up whether to use Tor domains, proxy settings, and an optional `asyncio.Semaphore` to limit concurrent requests.
            *   `_r`: An internal helper method to perform GET requests using the utility functions from `util.py`, applying cookies and the semaphore if enabled.
            *   `login()`: Handles authentication by making a POST request to the login endpoint, storing the returned cookies, and initializing the `ZlibProfile` object. It also handles setting the correct mirror domain, especially when using Tor.
            *   `logout()`: Clears stored cookies and the profile object.
            *   `search()`: Constructs the search URL based on query, filters (years, languages, extensions), and initializes a `SearchPaginator` (from `abs.py`) to handle the results. Requires login first.
            *   `get_by_id()`: Fetches detailed information for a single book using its ID by initializing and calling `fetch()` on a `BookItem` (from `abs.py`).
            *   `full_text_search()`: Similar to `search()`, but uses the full-text search endpoint and specific parameters (phrase vs. words). Also uses `SearchPaginator`. Requires login first.

7.  **`logger.py`**:
    *   **Purpose**: Sets up basic logging for the library.
    *   **Contents & Responsibilities**: It gets a logger instance named `zlibrary` and adds a `logging.NullHandler()`. This prevents log messages from being outputted by default unless the application *using* this library explicitly configures handlers for the `zlibrary` logger.

8.  **`profile.py`**:
    *   **Purpose**: Handles functionality related to an authenticated user's profile and actions.
    *   **Contents & Responsibilities**:
        *   `ZlibProfile` class:
            *   Initialized by `AsyncZlib.login()` with the necessary request function and cookies.
            *   `get_limits()`: Fetches and parses the user's download limits page to return daily download counts and reset times.
            *   `download_history()`: Fetches the user's download history, allowing filtering by date, and uses the `DownloadsPaginator` (from `abs.py`) for pagination.
            *   `search_public_booklists()` / `search_private_booklists()`: Provides access to searching booklists via the `Booklists` class (from `booklists.py`).

9.  **`util.py`**:
    *   **Purpose**: Contains utility functions for making asynchronous HTTP requests.
    *   **Contents & Responsibilities**: Provides asynchronous functions (`GET_request`, `GET_request_cookies`, `POST_request`, `HEAD_request`) built on top of the `aiohttp` library. They handle setting user-agent headers, timeouts, cookie management (`aiohttp.CookieJar`), and optional proxy support via `aiohttp_socks`. These functions are used by other modules (`libasync.py`, `abs.py`) to interact with the Z-Library website/API.


## Example Workflow

Here is typical workflow of searching for a book by name and downloading it using the `sertraline/zlibrary` library, based on its structure.

**Assumptions:**

*   You have installed the necessary libraries (`aiohttp`, `aiohttp_socks`, `beautifulsoup4`).
*   You are running this within an `async` Python environment (e.g., inside an `async def` function, using `asyncio.run()`).
*   You have valid Z-Library login credentials (`your_email`, `your_password`).
*   The book you're searching for is "The Hitchhiker's Guide to the Galaxy".

**Workflow Steps & Underlying Logic:**

1.  **Initialization:**
    *   **User Code:**
        ```python
        import asyncio
        from zlibrary import AsyncZlib, Language, Extension

        async def main():
            # Initialize the client
            client = AsyncZlib()
            # Optional: If using Tor/proxy:
            # client = AsyncZlib(onion=True, proxy_list=['socks5://127.0.0.1:9050'])
        ```
    *   **Library Logic (`libasync.py:__init__`)**:
        *   Sets default API domains (e.g., `ZLIB_DOMAIN`, `LOGIN_DOMAIN`) or Tor equivalents if `onion=True`.
        *   Stores proxy information if provided.
        *   Sets up an `asyncio.Semaphore` (unless disabled) to limit concurrent requests later.

2.  **Login:**
    *   **User Code:**
        ```python
        # Inside main()
        try:
            print("Logging in...")
            profile = await client.login('your_email', 'your_password')
            print(f"Login successful! Using mirror: {client.mirror}")
        except Exception as e:
            print(f"Login failed: {e}")
            return # Can't proceed without login
        ```
    *   **Library Logic (`libasync.py:login` -> `util.py:POST_request`)**:
        *   Constructs a data payload containing email, password, and other required form fields (`isModal`, `action`, etc.).
        *   Calls the internal `POST_request` utility function.
        *   `util.POST_request` uses `aiohttp` to send a POST request to the `client.login_domain`. It handles headers, creates a cookie jar, and uses proxies if configured.
        *   The response (expected to be JSON) and the resulting cookie jar are returned.
        *   `login` parses the JSON response. It checks for `validationError` and raises `LoginFailed` (from `exception.py`) if authentication fails.
        *   If successful, it extracts the cookies (like `remix_userkey`, `remix_userid`) from the returned `aiohttp` cookie jar and stores them in `client.cookies`.
        *   It determines and sets the `client.mirror` (the main Z-Library domain to use for subsequent requests). This might involve an extra GET request if using Tor to confirm the correct domain with session cookies.
        *   It initializes and returns a `ZlibProfile` object (`profile.py`), passing it the internal request function (`_r`), the obtained cookies, and the mirror URL. This profile object is also stored in `client.profile`.

3.  **Search for the Book:**
    *   **User Code:**
        ```python
        # Inside main()
        book_title = "The Hitchhiker's Guide to the Galaxy"
        print(f"Searching for '{book_title}'...")
        try:
            # Perform the search, request first 5 results
            search_paginator = await client.search(
                q=book_title,
                count=5,
                # Optional filters:
                # lang=[Language.ENGLISH],
                # extensions=[Extension.EPUB]
            )
            print(f"Found {search_paginator.total} potential results across all pages.")
        except Exception as e:
            print(f"Search failed: {e}")
            return
        ```
    *   **Library Logic (`libasync.py:search` -> `abs.py:SearchPaginator` -> `util.py:GET_request`)**:
        *   `client.search` first checks if `client.profile` exists (i.e., if logged in), raising `NoProfileError` otherwise. It also checks for an empty query (`EmptyQueryError`).
        *   It constructs the search URL by appending the URL-encoded query (`/s/{quoted_query}`) and any specified filters (like `&languages%5B%5D=english`) to the `client.mirror`.
        *   It creates an instance of `SearchPaginator` (`abs.py`), passing the constructed URL, the desired result count per page (`count`), the client's internal request function (`client._r`), and the mirror URL.
        *   It calls `await search_paginator.init()`.
        *   Inside `search_paginator.init()`:
            *   It calls `await self.fetch_page()`.
            *   `fetch_page` uses the passed request function (`client._r`) which ultimately calls `util.GET_request`.
            *   `util.GET_request` uses `aiohttp` to perform a GET request to the search URL (first page), sending the stored `client.cookies`.
            *   The HTML content of the search results page is returned.
            *   `init` then calls `self.parse_page(html_content)`.
            *   `parse_page` uses `BeautifulSoup` to parse the HTML. It finds the main results container (`#searchResultBox`) and then iterates through individual book entries (finding `z-bookcard` tags).
            *   For each `z-bookcard`, it creates a `BookItem` instance (`abs.py`) and populates it by extracting basic metadata (ID, title, authors, cover URL, year, language, extension, size, rating, book page URL) directly from the tag's attributes and nested elements.
            *   These populated `BookItem` objects are stored in `self.storage[1]` (mapping page number to list of results).
            *   It also parses the HTML (often looking in `<script>` tags) to find the total number of result pages (`self.total`).
        *   The initialized `search_paginator` object is returned.

4.  **Process Search Results & Select Book:**
    *   **User Code:**
        ```python
        # Inside main()
        selected_book = None
        try:
            # Get the first batch of results (up to 'count' specified earlier)
            results = await search_paginator.next()
            if not results:
                print("No results found on the first page.")
                return

            print("\\n--- Search Results (Page 1) ---")
            for i, book in enumerate(results):
                # Display basic info from the BookItem dictionary
                print(f"{i+1}. ID: {book.get('id')}, Title: {book.get('name')}")
                print(f"   Authors: {book.get('authors')}, Year: {book.get('year')}, Ext: {book.get('extension')}")
                # --- User Logic to select the correct book ---
                # Example: Select the first result for simplicity
                if i == 0: # Or add more sophisticated matching logic here
                    selected_book = book
                    print(f"   --> Selecting this book.")

            # If more results needed:
            # results_page_2 = await search_paginator.next() # Might fetch page 2 automatically
            # Or:
            # await search_paginator.next_page()
            # results_page_2 = await search_paginator.next()

        except Exception as e:
            print(f"Error processing results: {e}")
            return

        if not selected_book:
            print("Could not find a suitable book in the first batch.")
            return
        ```
    *   **Library Logic (`abs.py:SearchPaginator.next`)**:
        *   The `next()` method returns a slice of the results stored for the current page (`self.storage[self.page]`).
        *   It manages an internal position (`self.__pos`). If `next()` is called and the position is at the end of the current page's results, it automatically calls `await self.next_page()`.
        *   `next_page()` increments the page counter. If the new page's results aren't already in `self.storage`, it calls `fetch_page()` and `parse_page()` again (as described in step 3) to get and process the HTML for the *next* page.

5.  **Fetch Detailed Book Info (including Download Link):**
    *   **User Code:**
        ```python
        # Inside main()
        print(f"\\nFetching details for Book ID: {selected_book.get('id')}...")
        try:
            # selected_book is a BookItem instance from the search results
            detailed_info = await selected_book.fetch()
            download_link = detailed_info.get("download_url")

            if download_link:
                print(f"Successfully fetched details.")
                print(f"   Description: {detailed_info.get('description', 'N/A')[:100]}...") # Show snippet
                print(f"   Download URL found: {download_link}")
            else:
                print("Could not find a download link in the details.")
                return

        except Exception as e:
            print(f"Failed to fetch book details: {e}")
            return
        ```
    *   **Library Logic (`abs.py:BookItem.fetch` -> `util.py:GET_request`)**:
        *   The `selected_book` (which is a `BookItem`) already contains the URL to the book's specific page (e.g., `https://z-library.sk/book/123456`).
        *   The `fetch()` method calls the internal request function (`self.__r`, which points to `client._r`) to perform a `util.GET_request` to that specific book URL, again sending the necessary `client.cookies`.
        *   It receives the HTML content of the book's page.
        *   It parses this new HTML using `BeautifulSoup`.
        *   It looks for more detailed information: the full description (`#bookDescriptionBox`), specific properties like ISBN, Publisher, Categories (`.bookDetailsBox`), and critically, the download button (`.btn.addDownloadedBook`).
        *   It extracts the `href` attribute from the download button anchor tag – this is the `download_url`. It also checks if the button text indicates unavailability (e.g., for Tor-only downloads).
        *   All extracted details are stored in the `selected_book.parsed` dictionary, which is then returned.

6.  **Download the File (External to Library Core Logic):**
    *   **User Code (Example using `aiohttp`):**
        ```python
        # Inside main()
        # NOTE: This part uses aiohttp directly, leveraging the cookies and link
        # obtained from the zlibrary library. The library itself doesn't download.

        if download_link and "Unavailable" not in download_link:
            # Reuse the client's proxy settings if they exist
            connector = None
            if client.proxy_list:
                 from aiohttp_socks import ChainProxyConnector
                 connector = ChainProxyConnector.from_urls(client.proxy_list)

            # Create a new session or reuse one, ensuring cookies are passed
            async with aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(unsafe=True), # Use a jar
                cookies=client.cookies, # Pass the login cookies!
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=600) # Longer timeout for download
             ) as session:
                print(f"Attempting to download from: {download_link}")
                try:
                    async with session.get(download_link) as response:
                        response.raise_for_status() # Raise error for bad status (4xx, 5xx)

                        # Try to get filename from headers, fallback to ID + extension
                        filename = f"{selected_book.get('id', 'unknown_book')}.{detailed_info.get('extension', 'file')}"
                        content_disposition = response.headers.get('Content-Disposition')
                        if content_disposition:
                            import re
                            fname_match = re.search('filename="?(.+)"?', content_disposition)
                            if fname_match:
                                filename = fname_match.group(1)

                        print(f"Downloading to file: {filename}")
                        with open(filename, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192) # Read in chunks
                                if not chunk:
                                    break
                                f.write(chunk)
                        print(f"Download complete: {filename}")

                except aiohttp.ClientError as e:
                    print(f"Download failed: {e}")
                except Exception as e:
                    print(f"An error occurred during download: {e}")
        else:
            print("Download link is unavailable or requires specific setup (like Tor).")

        # --- End of main ---
        # asyncio.run(main())
        ```
    *   **Logic**:
        *   This step is *outside* the `sertraline/zlibrary` library's direct functions but relies heavily on its output (`download_link` and `client.cookies`).
        *   You need a separate HTTP client (like `aiohttp` shown here, or `requests` in a synchronous context) to make a GET request to the `download_link`.
        *   **Crucially**, you *must* include the authentication cookies (`client.cookies`) in this request. Z-Library uses these cookies to verify you are logged in and authorized to download the file.
        *   The code handles potential redirects, checks the response status, reads the file content in chunks, and writes it to a local file. It also attempts to extract a sensible filename from the `Content-Disposition` header, falling back to using the book ID and extension.

This detailed flow shows how the library orchestrates the process by handling authentication, constructing API/web page requests, parsing HTML/JSON responses to extract relevant data (search results, book details, download links), and managing pagination, while the final file download requires using the library's outputs with a standard HTTP client.