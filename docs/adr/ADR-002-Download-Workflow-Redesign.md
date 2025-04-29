# ADR-002: Reaffirm Download Workflow with Book Page Scraping

**Date:** 2025-04-24

**Status:** Accepted

## Context

The initial implementation of book downloading within the `zlibrary-mcp` project, particularly concerning the RAG pipeline integration (`feature/rag-file-output` branch), faced issues (Ref: Integration Issue INT-RAG-003). User feedback and integration failures highlighted that simply using Book IDs or assuming direct download URLs constructed from IDs is unreliable due to website changes (e.g., required slugs in URLs, non-functional ID searches).

A strategic shift was mandated: the download workflow must first obtain the specific book page URL, scrape that page to find the *actual* download link `href`, and then initiate the download using the scraped link.

This ADR documents the investigation into how book page URLs are obtained in the current `zlibrary` fork codebase and reaffirms the scraping strategy as implemented in the `download_book` function on the `feature/rag-file-output` branch.

## Investigation Findings

Code analysis (`zlibrary/src/zlibrary/libasync.py`, `zlibrary/src/zlibrary/abs.py`) revealed the following:

1.  **Book Page URL Source:** The `search()` function returns results as `BookItem` objects (dictionary-like). The relative URL of the book's detail page is parsed from search results (`z-bookcard[href]`) and stored under the key `"url"` within the `BookItem`. (Note: `get_by_id` is currently unreliable due to external website changes preventing ID-based lookups).
2.  **`download_book` Implementation:** The `download_book` function (added in commit `8a30920` on `feature/rag-file-output`) correctly expects a `book_details` dictionary (representing a `BookItem`) as input. It retrieves the book page URL using `book_details.get('url')`.
3.  **Scraping Implementation:** `download_book` proceeds to fetch the HTML content of the retrieved book page URL using `httpx`. It then uses `BeautifulSoup4` (with `lxml`) to parse the HTML.
4.  **Download Link Extraction:** It attempts to find the download link using the CSS selector `a.btn.btn-primary.dlButton` and extracts the `href` attribute.
5.  **Final Download:** The download is initiated using the *extracted* `href` (prefixed with the mirror domain if relative), utilizing `httpx` streaming and `aiofiles` for asynchronous writing.

## Decision

Reaffirm the download workflow strategy as implemented in `zlibrary/src/zlibrary/libasync.py::download_book` on the `feature/rag-file-output` branch:

1.  **Obtain Book Details:** Use `search_books` to get the `BookItem` dictionary (passed as `bookDetails`) containing the book page URL (`"url"`).
2.  **Pass Details:** Pass this dictionary (`book_details`) to the `download_book` function.
3.  **Fetch & Scrape:** `download_book` fetches the page specified by `book_details['url']`.
4.  **Parse & Select:** Parse the HTML using `BeautifulSoup4` and `lxml`.
5.  **Extract Link:** Select the download link using the CSS selector `a.btn.btn-primary.dlButton` and extract its `href`. **Note:** This selector is based on observed website structure and is potentially brittle; future maintenance may be required if the website layout changes.
6.  **Download:** Initiate the actual download using the extracted `href`, following redirects and streaming the content.

This strategy directly addresses the requirement to scrape the book page for the actual download link before downloading.

## Consequences

*   **Reliability:** This approach is more reliable than constructing download URLs directly from IDs, as it uses the links provided on the book's page.
*   **Brittleness:** The workflow depends on the stability of the Z-Library website's HTML structure, particularly the CSS selector (`a.btn.btn-primary.dlButton`) used to find the download link. Changes to the website frontend could break this selector, requiring updates to the `download_book` function.
*   **Error Handling:** The implemented `download_book` includes error handling for:
    *   Missing book page URL in input details.
    *   HTTP errors during book page fetch.
    *   Parsing errors or failure to find the download link selector/href.
    *   HTTP errors during the final download.
    *   Network errors during fetch or download.
    *   Filesystem errors when creating directories or writing the file.
*   **No Change to `rag-pipeline.md`:** The existing `docs/architecture/rag-pipeline.md` (v2) already reflects this scraping workflow implicitly within the "Python Bridge" component description, although it doesn't detail the specific selector. No updates are required to that document based on this investigation.

## Alternatives Considered

*   **Direct URL Construction:** Attempting to guess or construct download URLs directly from Book IDs. Rejected as unreliable due to website changes and observed failures (404s, non-functional ID searches).
*   **Using Only `get_download_info` (if available/functional):** Relying on a hypothetical dedicated API endpoint or library function specifically for download links. The current library (`zlibrary` fork) does not have a reliably functioning equivalent separate from the scraping implemented in `download_book`.