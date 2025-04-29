# ADR-003: Handle Failure of `get_book_by_id` Tool

**Date**: 2025-04-29

**Status**: Accepted

## Context

The `get_book_by_id` MCP tool, intended to retrieve detailed book information using only a Z-Library book ID, is non-functional.

*   **Initial Implementation:** Relied on the external `zlibrary` Python library's `client.get_by_id(id)` method. This failed due to `ParseError` because the library constructed an incorrect URL (`/book/ID` without a required slug), leading to a 404 response from the Z-Library website ([Ref: MB Pattern 2025-04-15 21:51:00]).
*   **Workaround Attempt 1:** Modify the tool to use `client.search(q=f'id:{id}', exact=True, count=1)` within the Python bridge. This also failed with `ParseError` ([Ref: MB Decision-ParseErrorWorkaround-01 FAILED]).
*   **Workaround Attempt 2 / Debugging:** Further investigation revealed the root cause for the search workaround failure: the Z-Library website itself no longer returns results for `id:` searches. It returns a standard "nothing has been found" page, which the library correctly parses as no results, leading to `BookNotFound` or `ParseError` depending on the exact library path ([Ref: MB ActiveContext 2025-04-16 07:27:22, MB GlobalContext Pattern Update 2025-04-16 07:27:22]).
*   **Workaround Attempt 3 (Internal Search-First):** An internal scraping mechanism was implemented (`_internal_search`, `_internal_get_book_details_by_id` in `lib/python_bridge.py`) to mimic the `search(id:...)` logic ([Ref: MB Pattern 2025-04-16 18:40:05]). However, this relies on the same flawed premise that an ID-based search yields usable results externally, which it does not.

Therefore, retrieving book details *solely* based on an ID is currently impossible due to external website limitations.

## Decision

Acknowledge the external limitation and **deprecate the `get_book_by_id` MCP tool**. Mark it as unreliable and plan for its removal.

## Rationale

1.  **External Root Cause:** The core problem lies with the Z-Library website's behavior, which is outside the control of this project. No amount of internal scraping refinement can succeed if the necessary data (slug or ID search results) is not provided by the external source.
2.  **Consistency:** This decision aligns with the previous deprecation of the `get_download_info` tool ([Ref: MB Decision-DeprecateGetDownloadInfo-01]), which was also rendered unreliable by the same ID lookup failures.
3.  **Workflow Alignment:** ADR-002 ("Download Workflow Redesign") already shifted the primary download mechanism (`download_book_to_file`) to rely on the `bookDetails` object obtained from `search_books`. This object contains the necessary book page URL for scraping the actual download link, bypassing the need for a separate, unreliable ID-only lookup for this core workflow.
4.  **Maintainability & Simplicity:** Removing the tool avoids the need to maintain complex, brittle, and ultimately non-functional scraping code. It simplifies the MCP server's API surface.

## Consequences

*   Consumers of the `zlibrary-mcp` server (e.g., AI agents) must adapt their workflows. To get book details, they **must** use the `search_books` tool, which returns results containing the book ID, title, author, page URL, and other necessary metadata.
*   The `get_book_by_id` function in `lib/python_bridge.py` and `src/lib/zlibrary-api.ts`, along with its associated tests and tool registration in `src/index.ts`, should be removed in a subsequent cleanup task.
*   Documentation (e.g., README, tool references) needs to be updated to reflect the deprecation.

## Alternatives Considered

1.  **Refine Internal Search-First Scraper:** Rejected. This mimics an externally broken mechanism and is highly unlikely to work reliably.
2.  **Implement General Search + Filtering:** Rejected. Only works if metadata beyond the ID is available, making it functionally similar to `search_books` and less useful as a distinct ID lookup tool.
3.  **Further Fork Investigation:** Rejected. Low probability of finding an alternative, reliable ID-only lookup method within the existing `zlibrary` fork, given the external website limitations.
4.  **Keep Tool but Mark Unreliable:** Considered, but full deprecation provides a clearer signal and simplifies the API.