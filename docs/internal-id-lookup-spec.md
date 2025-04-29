**Note:** This specification describes an internal scraping strategy that was ultimately deemed unworkable due to external website limitations. The `get_book_by_id` tool has been deprecated. See **[ADR-003: Handle Failure of `get_book_by_id` Tool](./adr/ADR-003-Handle-ID-Lookup-Failure.md)** for the final decision.

---
# Specification: Internal ID-Based Book Lookup

## 1. Background

The external `zlibrary` Python library and subsequent workarounds (like `id:` search) have proven unreliable for fetching book details based solely on their Z-Library ID. This is primarily due to external website changes (e.g., `/book/ID` URLs returning 404 Not Found because they lack a required slug, `id:` search functionality removed/broken on the site).

As per architectural decision **Decision-InternalIDLookupURL-01**, the strategy is to implement internal fetching and parsing logic within `lib/python_bridge.py`. This involves directly attempting to fetch the `/book/ID` URL, explicitly handling the expected 404 error as the primary "book not found" case, and attempting to parse the page only if an unexpected 200 OK response is received.

## 2. Requirements

### 2.1. Python Bridge (`lib/python_bridge.py`)

#### 2.1.1. Imports
Ensure the following imports are present:
```python
import httpx
from bs4 import BeautifulSoup
import logging
import os
import json
import sys
import argparse
import asyncio # Added for asyncio.run
# Existing zlibrary imports might be needed for ZLibrary() client if still used elsewhere
```

#### 2.1.2. Custom Exceptions
Define new internal exceptions:
```python
class InternalBookNotFoundError(Exception):
    """Custom exception for when a book ID lookup results in a 404."""
    pass

class InternalParsingError(Exception):
    """Custom exception for errors during HTML parsing of book details."""
    pass
```

#### 2.1.3. New Function: `_internal_get_book_details_by_id`
Implement the following asynchronous function:

```python
### Pseudocode: Python Bridge (`lib/python-bridge.py`) - `_internal_get_book_details_by_id`
# - Created: 2025-04-16 08:13:38
# - Updated: 2025-04-16 08:13:38

async def _internal_get_book_details_by_id(book_id: str, domain: str) -> dict:
    """
    Attempts to fetch book details by directly accessing https://<domain>/book/<book_id>.
    Primarily expects a 404, raising InternalBookNotFoundError.
    If a 200 is received, attempts to parse the page.
    """
    target_url = f"https://{domain}/book/{book_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' # Example User-Agent
    }
    timeout_seconds = 15 # Configurable timeout

    logging.info(f"Attempting internal lookup for book ID {book_id} at {target_url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(target_url, headers=headers)

            # --- Status Code Handling ---
            if response.status_code == 404:
                logging.warning(f"Internal lookup for book ID {book_id} resulted in 404 (Not Found).")
                raise InternalBookNotFoundError(f"Book ID {book_id} not found via internal lookup (404).")

            # Raise error for other non-200 statuses
            response.raise_for_status() # Raises httpx.HTTPStatusError for 4xx/5xx other than 404

            # --- 200 OK Parsing (Unexpected Case) ---
            logging.warning(f"Received unexpected 200 OK for internal lookup of book ID {book_id}. Attempting to parse.")
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                details = {}

                # Example Selectors (These MUST be verified and adjusted based on actual page structure)
                title_element = soup.select_one('h1[itemprop="name"]')
                details['title'] = title_element.text.strip() if title_element else None

                author_element = soup.select_one('a[itemprop="author"]') # Adjust selector
                details['author'] = author_element.text.strip() if author_element else None

                # Add selectors for other fields: year, publisher, description, etc.
                # Example:
                # year_element = soup.select_one('.book-details .property-year .property_value')
                # details['year'] = year_element.text.strip() if year_element else None

                # Example Download URL Selector (Verify this)
                download_link_element = soup.select_one('a.btn-primary[href*="/download"]') # Adjust selector
                details['download_url'] = download_link_element['href'] if download_link_element and download_link_element.has_attr('href') else None
                # Potentially need to make URL absolute: urljoin(response.url, details['download_url'])

                if not details.get('title'): # Check if essential data is missing
                     logging.error(f"Parsing failed for book ID {book_id}: Essential data (e.g., title) missing.")
                     raise InternalParsingError(f"Failed to parse essential details for book ID {book_id} from 200 OK page.")

                logging.info(f"Successfully parsed details for book ID {book_id} from unexpected 200 OK.")
                return details

            except Exception as parse_exc:
                logging.exception(f"Error parsing 200 OK page for book ID {book_id}: {parse_exc}")
                raise InternalParsingError(f"Failed to parse page content for book ID {book_id}: {parse_exc}") from parse_exc

    except httpx.RequestError as req_err:
        # Handles connection errors, timeouts, etc.
        logging.error(f"HTTP request error during internal lookup for book ID {book_id}: {req_err}")
        raise RuntimeError(f"Network error during internal lookup for book ID {book_id}: {req_err}") from req_err
    except httpx.HTTPStatusError as status_err:
        # Handles non-200/404 errors raised by response.raise_for_status()
        logging.error(f"Unexpected HTTP status {status_err.response.status_code} during internal lookup for book ID {book_id}: {status_err}")
        raise RuntimeError(f"Unexpected HTTP status {status_err.response.status_code} for book ID {book_id}.") from status_err
    # InternalBookNotFoundError and InternalParsingError are raised directly
    except Exception as e:
         # Catch any other unexpected errors
         logging.exception(f"Unexpected error during internal lookup for book ID {book_id}: {e}")
         raise RuntimeError(f"An unexpected error occurred during internal lookup for book ID {book_id}: {e}") from e

```

#### 2.1.4. Caller Modifications (`get_download_info`)
Modify the existing Python functions called by the Node.js bridge (`get_download_info` or similar within the `if __name__ == "__main__":` block) to use the new internal lookup function.

```python
# Inside if __name__ == "__main__": block

# Example modification for a function handling 'get_book_details' action
elif cli_args.function_name == 'get_book_details': # Assuming a unified function now
    book_id = args_dict.get('book_id')
    domain = args_dict.get('domain', 'z-library.sk') # Get domain from args or use default
    if not book_id: raise ValueError("Missing 'book_id'")

    try:
        # Use asyncio.run() to call the async function from sync context
        # Ensure asyncio is imported at the top
        details = asyncio.run(_internal_get_book_details_by_id(book_id, domain))
        # Format 'details' dictionary as needed for the Node.js response
        response = details # Or transform structure if necessary

    except InternalBookNotFoundError:
        # Translate internal error to ValueError for Node.js
        raise ValueError(f"Book ID {book_id} not found.")
    except (InternalParsingError, httpx.RequestError, RuntimeError) as e:
        # Translate other internal/HTTP errors to RuntimeError
        logging.error(f"Failed to get details for book ID {book_id}: {e}")
        raise RuntimeError(f"Failed to fetch or parse book details for ID {book_id}.")
    except Exception as e:
         logging.exception(f"Unexpected error in get_book_details handler for ID {book_id}")
         raise RuntimeError(f"An unexpected error occurred processing book ID {book_id}.")

# Similar logic needs to be applied if get_download_info is a separate entry point.
# It might call the same _internal_get_book_details_by_id and extract the download_url.
elif cli_args.function_name == 'get_download_info':
     book_id = args_dict.get('book_id')
     domain = args_dict.get('domain', 'z-library.sk')
     if not book_id: raise ValueError("Missing 'book_id'")
     try:
         # Ensure asyncio is imported at the top
         details = asyncio.run(_internal_get_book_details_by_id(book_id, domain))
         if not details.get('download_url'):
              raise InternalParsingError("Download URL not found in parsed details.")
         response = {"download_url": details['download_url']} # Format as needed

     except InternalBookNotFoundError:
         raise ValueError(f"Book ID {book_id} not found.")
     except (InternalParsingError, httpx.RequestError, RuntimeError) as e:
         logging.error(f"Failed to get download info for book ID {book_id}: {e}")
         raise RuntimeError(f"Failed to fetch or parse download info for ID {book_id}.")
     except Exception as e:
         logging.exception(f"Unexpected error in get_download_info handler for ID {book_id}")
         raise RuntimeError(f"An unexpected error occurred processing book ID {book_id}.")

# Ensure the main block correctly handles the response variable and prints it
# print(json.dumps(response))
```

### 2.2. Dependency Management

Add `httpx` to the Python dependencies.

**File:** `requirements.txt`
```text
# ... other dependencies
httpx>=0.20 # Or latest compatible version
beautifulsoup4>=4.9
lxml>=4.6 # Required by BeautifulSoup for better parsing
# Ensure zlibrary is still listed if needed elsewhere, or remove if fully replaced
# Ensure PyMuPDF, ebooklib are listed if RAG features are active
```
*Note: `lxml` is added as it's generally preferred for `BeautifulSoup` parsing.*

### 2.3. TDD Anchors

Key test cases to cover during implementation:

**`_internal_get_book_details_by_id`:**
1.  **404 Not Found:** Mock `httpx.AsyncClient.get` to return a 404 response. Verify `InternalBookNotFoundError` is raised.
2.  **Other HTTP Error:** Mock `httpx.AsyncClient.get` to return a 500 or 403 response. Verify `httpx.HTTPStatusError` is raised (and subsequently caught/translated by caller).
3.  **Network Error:** Mock `httpx.AsyncClient.get` to raise `httpx.RequestError`. Verify it's caught and translated to `RuntimeError` by the caller.
4.  **Successful 200 OK (Mock HTML):** Mock `httpx.AsyncClient.get` to return a 200 OK response with sample valid HTML. Verify correct details dictionary is returned.
5.  **Parsing Error (200 OK):** Mock `httpx.AsyncClient.get` to return 200 OK but with malformed/unexpected HTML. Verify `InternalParsingError` is raised.
6.  **Missing Elements (200 OK):** Mock `httpx.AsyncClient.get` to return 200 OK with HTML missing key elements (e.g., title, author, download link). Verify graceful handling (e.g., `None` values in dict, potentially `InternalParsingError` if essential data missing).

**Caller Functions (`get_book_details`/`get_download_info` handlers):**
7.  **Correct Internal Call:** Verify the handler correctly calls `asyncio.run(_internal_get_book_details_by_id)` with the right arguments.
8.  **Error Translation (NotFound):** Mock `_internal_get_book_details_by_id` to raise `InternalBookNotFoundError`. Verify the handler catches it and raises `ValueError("Book ID ... not found.")`.
9.  **Error Translation (Parsing/HTTP):** Mock `_internal_get_book_details_by_id` to raise `InternalParsingError` or `httpx.RequestError`. Verify the handler catches it and raises `RuntimeError("Failed to fetch or parse...")`.
10. **Data Formatting:** Verify the handler correctly formats the dictionary returned by `_internal_get_book_details_by_id` into the JSON structure expected by the Node.js layer.

**Dependency:**
11. **`httpx` Installation:** Verify that the `venv-manager` successfully installs `httpx` from the updated `requirements.txt`.