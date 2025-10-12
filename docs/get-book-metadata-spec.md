# Specification: `get_book_metadata` Tool

**Version:** 1.0
**Date:** 2025-05-07
**Author:** SpecPseudo Mode

## 1. Overview

This document outlines the detailed specification for the `get_book_metadata` MCP tool. This tool is designed to scrape comprehensive metadata from a given Z-Library book page URL. The scraped data will be structured into a Python dictionary, which will then be validated against a Zod schema in the Node.js MCP server.

This specification covers:
- The output metadata object structure.
- Detailed scraping and data cleaning/parsing logic for each metadata field.
- Pseudocode for the Python scraping function.
- TDD anchors for Python and Node.js tests.

## 2. Output Metadata Object Structure (Python Dictionary)

The core Python scraping function, `scrape_book_metadata`, located in `zlibrary/src/zlibrary/libasync.py` (or a new dedicated scraping module), will return a dictionary with the following structure. This structure aligns with the Zod schema defined in [`docs/project-plan-zlibrary-mcp.md:204-222`](docs/project-plan-zlibrary-mcp.md:204-222).

```python
from typing import List, Optional, Dict, Any

BookMetadata = Dict[str, Any] # Simplified for pseudocode, actual implementation might use TypedDict

# Example of the expected dictionary structure:
# {
#     "title": Optional[str],
#     "authors": Optional[List[str]],
#     "publisher": Optional[str],
#     "publication_year": Optional[int],
#     "isbn": Optional[str], # Could be a list if multiple ISBNs are found and schema supports it
#     "doi": Optional[str],
#     "series": Optional[str],
#     "language": Optional[str],
#     "pages": Optional[int],
#     "filesize": Optional[str], # e.g., "12.10 MB"
#     "description": Optional[str],
#     "cover_image_url": Optional[str], # Should be a valid URL
#     "tags": Optional[List[str]],
#     "most_frequent_terms": Optional[List[str]],
#     "related_booklist_urls": Optional[List[str]], # List of valid URLs
#     "you_may_be_interested_in_urls": Optional[List[str]], # List of valid URLs
#     "source_url": str # The input URL
# }
```

**Field Data Types and Nullability:**

*   `title: Optional[str]`
*   `authors: Optional[List[str]]`
*   `publisher: Optional[str]`
*   `publication_year: Optional[int]`
*   `isbn: Optional[str]` (Note: The project plan mentions potentially an array for ISBN 10 & 13. For now, specified as `Optional[str]`. If multiple are found, the first valid one or a concatenated string could be used, or the schema updated.)
*   `doi: Optional[str]`
*   `series: Optional[str]`
*   `language: Optional[str]`
*   `pages: Optional[int]`
*   `filesize: Optional[str]`
*   `description: Optional[str]`
*   `cover_image_url: Optional[str]`
*   `tags: Optional[List[str]]`
*   `most_frequent_terms: Optional[List[str]]`
*   `related_booklist_urls: Optional[List[str]]`
*   `you_may_be_interested_in_urls: Optional[List[str]]`
*   `source_url: str` (This is the input URL and is mandatory)

## 3. Scraping and Data Cleaning/Parsing Logic

The following details the logic for extracting and cleaning data for each of the 16 metadata fields.
**Note:** The CSS selectors listed below are placeholders (e.g., `SELECTOR_FOR_TITLE`) and need to be replaced with the actual selectors identified by `debug` mode.

**Helper Function for Safe Text/Attribute Extraction:**
A helper function should be used to safely extract text or attributes, handling cases where elements are not found.

```python
# Pseudocode for helper
def safe_get_text(element, default=None):
    if element:
        text = element.get_text(strip=True)
        return text if text else default
    return default

def safe_get_attr(element, attribute, default=None):
    if element:
        attr_value = element.get(attribute)
        return attr_value if attr_value else default
    return default

def safe_get_all_texts(elements_list, default_if_empty=None):
    if not elements_list:
        return default_if_empty if default_if_empty is not None else []
    texts = [el.get_text(strip=True) for el in elements_list if el.get_text(strip=True)]
    return texts if texts else (default_if_empty if default_if_empty is not None else [])

def safe_get_all_attrs(elements_list, attribute, default_if_empty=None):
    if not elements_list:
        return default_if_empty if default_if_empty is not None else []
    attrs = [el.get(attribute) for el in elements_list if el.get(attribute)]
    # Further validation for URLs can be added here if needed
    return attrs if attrs else (default_if_empty if default_if_empty is not None else [])
```

---

**1. Title:**
    *   **Selector:** `h1.book-title` (Example from provided HTML)
    *   **Extraction:** Get the text content of the element.
    *   **Cleaning:** Strip leading/trailing whitespace.
    *   **Missing/Malformed:** Return `None`.

**2. Author(s):**
    *   **Selector:** `div.col-sm-9 > i > a.color1[title*="Find all the author's book"]` (Example from provided HTML, targets multiple `<a>` tags if present)
    *   **Extraction:** Find all matching `<a>` elements. For each element, extract its text content.
    *   **Cleaning:** Store as a list of strings. Strip whitespace from each author name.
    *   **Missing/Malformed:** Return `[]` (empty list).

**3. Publisher:**
    *   **Selector:** `div.bookProperty.property_publisher > div.property_value` (Example from provided HTML)
    *   **Extraction:** Get the text content of the element.
    *   **Cleaning:** Strip leading/trailing whitespace.
    *   **Missing/Malformed:** Return `None`.

**4. Publication Year:**
    *   **Selector:** `div.bookProperty.property_year > div.property_value` (Example from provided HTML)
    *   **Extraction:** Get the text content.
    *   **Cleaning:** Convert the text to an integer. Strip any non-numeric characters before conversion if necessary.
    *   **Missing/Malformed:** If text cannot be converted to int or element is missing, return `None`.

**5. ISBN:**
    *   **Selector(s):**
        *   ISBN-13: `div.bookProperty.property_isbn.13 > div.property_value` (Example from provided HTML)
        *   ISBN-10: `div.bookProperty.property_isbn.10 > div.property_value` (Example from provided HTML)
    *   **Extraction:** Get text content. Prioritize ISBN-13 if available, otherwise ISBN-10.
    *   **Cleaning:** Strip whitespace and hyphens. Validate format if necessary.
    *   **Missing/Malformed:** Return `None`.

**6. DOI:**
    *   **Selector:** `div.bookProperty.property_isbn > div.property_value` (If DOI is in the same field as ISBN for articles, as seen in the second HTML example. This needs specific selector from debug mode if different.)
        *   Alternatively: `div.bookProperty[itemprop="identifier"][content*="doi"] > div.property_value` (More robust if itemprop is used)
        *   Or: `div.bookProperty:has(div.property_label:contains("DOI")) > div.property_value`
    *   **Extraction:** Get text content.
    *   **Cleaning:** Strip leading/trailing whitespace. Remove "doi:" prefix if present.
    *   **Missing/Malformed:** Return `None`.

**7. Series:**
    *   **Selector:** `div.bookProperty.property_series > div.property_value` (Example from provided HTML)
    *   **Extraction:** Get text content.
    *   **Cleaning:** Strip leading/trailing whitespace.
    *   **Missing/Malformed:** Return `None`.

**8. Language:**
    *   **Selector:** `div.bookProperty.property_language > div.property_value` (Example from provided HTML)
    *   **Extraction:** Get text content.
    *   **Cleaning:** Strip leading/trailing whitespace. Convert to lowercase.
    *   **Missing/Malformed:** Return `None`.

**9. Pages:**
    *   **Selector:** `div.bookProperty.property_pages > div.property_value > span[title*="Pages"]` (Example from provided HTML, assuming the span with title is consistent)
    *   **Extraction:** Get text content of the span.
    *   **Cleaning:** Convert text to an integer. Remove any non-numeric characters (e.g., " pages").
    *   **Missing/Malformed:** If text cannot be converted to int or element is missing, return `None`.

**10. Filesize:**
    *   **Selector:** `div.bookProperty.property__file > div.property_value` (Example from provided HTML)
    *   **Extraction:** Get text content.
    *   **Cleaning:** Strip leading/trailing whitespace. The format is "PDF, 12.10 MB". Extract the size part (e.g., "12.10 MB").
    *   **Missing/Malformed:** Return `None`.

**11. Description:**
    *   **Selector:** `div#bookDescriptionBox` (Example from provided HTML)
    *   **Extraction:** Get the text content. If description is split into multiple `<p>` tags within this div, concatenate their text with a newline or space.
    *   **Cleaning:** Strip leading/trailing whitespace. Normalize multiple spaces.
    *   **Missing/Malformed:** Return `None`.

**12. Cover Image URL:**
    *   **Selector:** `div.details-book-cover-container z-cover img[src]` or `div.col-sm-3.details-book-cover-container img[src]` (Example from provided HTML)
    *   **Extraction:** Get the `src` attribute of the `<img>` tag.
    *   **Cleaning:** Ensure it's a full URL (prepend domain if relative, though example shows full URL).
    *   **Missing/Malformed:** Return `None`.

**13. Tags:**
    *   **Selector:** `div.books-tags-wrap z-tags` (This is a custom element, need to inspect its shadow DOM or how it renders tags, or if there's an alternative plain HTML representation of tags if `z-tags` is not easily parsable).
        *   Alternative if `z-tags` is hard to parse: Look for a script tag containing tag data, or individual tag `<a>` elements if they exist.
        *   **Placeholder Selector:** `SELECTOR_FOR_TAGS a` (assuming tags are links)
    *   **Extraction:** Find all tag elements. Extract text from each.
    *   **Cleaning:** Store as a list of strings. Strip whitespace.
    *   **Missing/Malformed:** Return `[]`.

**14. Most Frequent Terms:**
    *   **Selector:** `div.termsCloud div.termWrap a.color1` (Example from provided HTML)
    *   **Extraction:** Find all `<a>` elements within `div.termsCloud`. Extract text from each.
    *   **Cleaning:** Store as a list of strings. Strip whitespace.
    *   **Missing/Malformed:** Return `[]`.

**15. Related Booklist URLs:**
    *   **Selector:** `div.related-booklists-block z-booklist[href]` (Custom element, inspect `href` attribute)
        *   Alternative: `div.related-booklists-block a[href*="/booklist/"]` (If `z-booklist` renders as a standard `<a>` or contains one)
    *   **Extraction:** Find all relevant elements. Extract the `href` attribute.
    *   **Cleaning:** Store as a list of strings. Ensure they are full URLs (prepend domain if relative).
    *   **Missing/Malformed:** Return `[]`.

**16. "You may be interested in" URLs:**
    *   **Selector:** `div.books-mosaic div.masonry-endless div.item a[href*="/book/"]` (Example from provided HTML)
    *   **Extraction:** Find all `<a>` elements. Extract the `href` attribute.
    *   **Cleaning:** Store as a list of strings. Ensure they are full URLs (prepend domain if relative).
    *   **Missing/Malformed:** Return `[]`.

---
**Source URL:**
    *   This field is the input `url` string itself and should be directly included in the output dictionary.

## 4. Pseudocode for Python Scraping Function

This pseudocode outlines the `scrape_book_metadata` function.

```python
# File: zlibrary/src/zlibrary/libasync.py (or new scraping module)
# Dependencies: httpx, beautifulsoup4, typing, re, urllib.parse

from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
import re 
from urllib.parse import urlparse, urljoin

# Placeholder for actual selectors - these need to be defined based on debug mode's findings
SELECTORS = {
    "title": "h1.book-title",
    "authors": "div.col-sm-9 > i > a.color1[title*=\"Find all the author's book\"]",
    "publisher": "div.bookProperty.property_publisher > div.property_value",
    "publication_year": "div.bookProperty.property_year > div.property_value",
    "isbn13": "div.bookProperty.property_isbn.13 > div.property_value",
    "isbn10": "div.bookProperty.property_isbn.10 > div.property_value",
    "doi": "div.bookProperty.property_isbn > div.property_value", # Example, may need specific selector
    "series": "div.bookProperty.property_series > div.property_value",
    "language": "div.bookProperty.property_language > div.property_value",
    "pages": "div.bookProperty.property_pages > div.property_value > span[title*=\"Pages\"]",
    "filesize": "div.bookProperty.property__file > div.property_value",
    "description": "div#bookDescriptionBox",
    "cover_image_url": "div.details-book-cover-container z-cover img[src]",
    "tags": "SELECTOR_FOR_TAGS a", # Placeholder
    "most_frequent_terms": "div.termsCloud div.termWrap a.color1",
    "related_booklist_urls": "div.related-booklists-block z-booklist[href]", # Placeholder for custom element attribute
    "you_may_be_interested_in_urls": "div.books-mosaic div.masonry-endless div.item a[href*=\"/book/\"]"
}

BookMetadata = Dict[str, Any]

# Helper function (as defined in Section 3)
def _safe_get_text(element, default=None):
    if element:
        text = element.get_text(strip=True)
        return text if text else default
    return default

def _safe_get_attr(element, attribute, base_url: Optional[str] = None, default=None):
    if element:
        attr_value = element.get(attribute)
        if attr_value:
            if (attribute == 'href' or attribute == 'src') and base_url:
                attr_value = urljoin(base_url, attr_value)
            return attr_value
    return default

def _safe_get_all_texts(elements_list, default_if_empty=None):
    if not elements_list:
        return default_if_empty if default_if_empty is not None else []
    texts = [el.get_text(strip=True) for el in elements_list if el.get_text(strip=True)]
    return texts if texts else (default_if_empty if default_if_empty is not None else [])

def _safe_get_all_attrs(elements_list, attribute, base_url: Optional[str] = None, default_if_empty=None):
    if not elements_list:
        return default_if_empty if default_if_empty is not None else []
    attrs = []
    for el in elements_list:
        attr_val = el.get(attribute)
        if attr_val:
            if (attribute == 'href' or attribute == 'src') and base_url:
                attr_val = urljoin(base_url, attr_val)
            attrs.append(attr_val)
    return attrs if attrs else (default_if_empty if default_if_empty is not None else [])


async def scrape_book_metadata(url: str, session: httpx.AsyncClient) -> BookMetadata:
    metadata: BookMetadata = {
        "title": None,
        "authors": [],
        "publisher": None,
        "publication_year": None,
        "isbn": None,
        "doi": None,
        "series": None,
        "language": None,
        "pages": None,
        "filesize": None,
        "description": None,
        "cover_image_url": None,
        "tags": [],
        "most_frequent_terms": [],
        "related_booklist_urls": [],
        "you_may_be_interested_in_urls": [],
        "source_url": url
    }
    
    parsed_url_obj = urlparse(url)
    base_page_url = f"{parsed_url_obj.scheme}://{parsed_url_obj.netloc}"

    try:
        response = await session.get(url, timeout=20.0, follow_redirects=True) 
        response.raise_for_status() 
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Title
        metadata["title"] = _safe_get_text(soup.select_one(SELECTORS["title"]))

        # 2. Authors
        metadata["authors"] = _safe_get_all_texts(soup.select(SELECTORS["authors"]), default_if_empty=[])

        # 3. Publisher
        metadata["publisher"] = _safe_get_text(soup.select_one(SELECTORS["publisher"]))

        # 4. Publication Year
        year_text = _safe_get_text(soup.select_one(SELECTORS["publication_year"]))
        if year_text and year_text.isdigit():
            metadata["publication_year"] = int(year_text)

        # 5. ISBN (Prioritize ISBN-13)
        isbn_text = _safe_get_text(soup.select_one(SELECTORS["isbn13"]))
        if not isbn_text: 
            isbn_text = _safe_get_text(soup.select_one(SELECTORS["isbn10"]))
        if isbn_text:
             metadata["isbn"] = re.sub(r"[^0-9X]", "", isbn_text) 

        # 6. DOI
        doi_element = soup.select_one(SELECTORS["doi"]) 
        doi_text = _safe_get_text(doi_element)
        if doi_text:
            if "10." in doi_text and "/" in doi_text: 
                 metadata["doi"] = doi_text.replace("DOI:", "").strip()
            elif metadata["isbn"] is None and SELECTORS["doi"] == SELECTORS["isbn13"]: 
                 pass


        # 7. Series
        metadata["series"] = _safe_get_text(soup.select_one(SELECTORS["series"]))

        # 8. Language
        lang_text = _safe_get_text(soup.select_one(SELECTORS["language"]))
        if lang_text:
            metadata["language"] = lang_text.lower()

        # 9. Pages
        pages_text = _safe_get_text(soup.select_one(SELECTORS["pages"]))
        if pages_text:
            cleaned_pages_text = re.sub(r'\D', '', pages_text) 
            if cleaned_pages_text.isdigit():
                metadata["pages"] = int(cleaned_pages_text)

        # 10. Filesize
        filesize_text = _safe_get_text(soup.select_one(SELECTORS["filesize"])) 
        if filesize_text:
            match = re.search(r'(\d+(\.\d+)?\s*(KB|MB|GB))', filesize_text, re.IGNORECASE)
            if match:
                metadata["filesize"] = match.group(1)

        # 11. Description
        description_element = soup.select_one(SELECTORS["description"])
        if description_element:
            p_tags = description_element.find_all('p', recursive=False)
            if p_tags:
                metadata["description"] = "\n".join([_safe_get_text(p) for p in p_tags if _safe_get_text(p)]).strip()
            else:
                metadata["description"] = _safe_get_text(description_element)

        # 12. Cover Image URL
        metadata["cover_image_url"] = _safe_get_attr(soup.select_one(SELECTORS["cover_image_url"]), "src", base_url=base_page_url)


        # 13. Tags
        metadata["tags"] = _safe_get_all_texts(soup.select(SELECTORS["tags"]), default_if_empty=[])


        # 14. Most Frequent Terms
        metadata["most_frequent_terms"] = _safe_get_all_texts(soup.select(SELECTORS["most_frequent_terms"]), default_if_empty=[])

        # 15. Related Booklist URLs
        metadata["related_booklist_urls"] = _safe_get_all_attrs(soup.select(SELECTORS["related_booklist_urls"]), "href", base_url=base_page_url, default_if_empty=[])


        # 16. "You may be interested in" URLs
        metadata["you_may_be_interested_in_urls"] = _safe_get_all_attrs(soup.select(SELECTORS["you_may_be_interested_in_urls"]), "href", base_url=base_page_url, default_if_empty=[])

    except httpx.HTTPStatusError as e:
        # Log error: Failed to fetch URL {url}, status: {e.response.status_code}
        print(f"HTTP error fetching {url}: {e}") # Replace with proper logging
    except httpx.RequestError as e:
        # Log error: Network error fetching URL {url}: {e}
        print(f"Network error fetching {url}: {e}") # Replace with proper logging
    except Exception as e:
        # Log error: Unexpected error scraping {url}: {e}
        print(f"Unexpected error scraping {url}: {e}") # Replace with proper logging

    return metadata

```

## 5. TDD Anchors

### 5.1. Python Scraping Function (`scrape_book_metadata` in `zlibrary/libasync.py`)

*   **Mocking:**
    *   Mock `httpx.AsyncClient.get` to return `httpx.Response` objects with predefined HTML content (snippets or full example pages).
    *   Mock `httpx.AsyncClient.get` to raise `httpx.HTTPStatusError` (e.g., 404, 500).
    *   Mock `httpx.AsyncClient.get` to raise `httpx.RequestError` (e.g., network timeout).

*   **Test Cases:**
    1.  **Test Full Data Extraction:**
        *   Input: Mocked HTML for a page with all 16 metadata fields present (e.g., using the first HTML example provided by the user).
        *   Expected: Dictionary containing all 16 fields correctly parsed and cleaned.
    2.  **Test Missing Optional Fields:**
        *   Input: Mocked HTML where optional fields like DOI, Series, ISBN (if only one type is present), some URL lists are missing.
        *   Expected: Corresponding dictionary keys should have `None` (for singular optional fields) or `[]` (for list optional fields). `source_url` should always be present.
    3.  **Test Specific Field Parsing - Authors:**
        *   Input: HTML with single author. Expected: `authors: ["Author Name"]`.
        *   Input: HTML with multiple authors (e.g., "Pierre Bourdieu, Jean-Claude Passeron"). Expected: `authors: ["Pierre Bourdieu", "Jean-Claude Passeron"]`.
        *   Input: HTML with no author elements. Expected: `authors: []`.
    4.  **Test Specific Field Parsing - Publication Year:**
        *   Input: HTML with valid year "1990". Expected: `publication_year: 1990`.
        *   Input: HTML with non-numeric year "Nineteen Ninety". Expected: `publication_year: None`.
        *   Input: HTML with year element missing. Expected: `publication_year: None`.
    5.  **Test Specific Field Parsing - ISBN:**
        *   Input: HTML with ISBN-13 "978-0-8039-8320-5". Expected: `isbn: "9780803983205"`.
        *   Input: HTML with only ISBN-10 "0803983204". Expected: `isbn: "0803983204"`.
        *   Input: HTML with no ISBN. Expected: `isbn: None`.
    6.  **Test Specific Field Parsing - DOI:**
        *   Input: HTML with DOI "10.2307/1343969" (from article example). Expected: `doi: "10.2307/1343969"`.
        *   Input: HTML with DOI prefix "DOI: 10.1234/foo". Expected: `doi: "10.1234/foo"`.
        *   Input: HTML with no DOI. Expected: `doi: None`.
    7.  **Test Specific Field Parsing - Pages:**
        *   Input: HTML with "288" pages. Expected: `pages: 288`.
        *   Input: HTML with "Approx. 300 pages". Expected: `pages: 300` (or `None` if parsing is strict to digits only).
        *   Input: HTML with no pages. Expected: `pages: None`.
    8.  **Test Specific Field Parsing - Filesize:**
        *   Input: HTML with "PDF, 12.10 MB". Expected: `filesize: "12.10 MB"`.
        *   Input: HTML with "EPUB, 850 KB". Expected: `filesize: "850 KB"`.
        *   Input: HTML with malformed filesize string. Expected: `filesize: None`.
    9.  **Test Specific Field Parsing - Description:**
        *   Input: HTML with description in a single block. Expected: Cleaned text.
        *   Input: HTML with description split into multiple `<p>` tags. Expected: Concatenated text of all `<p>` tags.
        *   Input: HTML with no description. Expected: `description: None`.
    10. **Test Specific Field Parsing - Cover Image URL:**
        *   Input: HTML with `<img src="https://example.com/cover.jpg">`. Expected: `cover_image_url: "https://example.com/cover.jpg"`.
        *   Input: HTML with `<img src="/relative/cover.jpg">`. Expected: `cover_image_url: "https://[base_domain]/relative/cover.jpg"` (after proper URL joining).
        *   Input: HTML with no cover image. Expected: `cover_image_url: None`.
    11. **Test Specific Field Parsing - URL Lists (Tags, Related Booklists, Interested In):**
        *   Input: HTML with multiple `<a>` tags for one of these lists. Expected: List of correctly extracted and cleaned `href` (for URLs) or text (for tags).
        *   Input: HTML with no elements for one of these lists. Expected: `[]` for that list.
        *   Input: HTML with relative URLs. Expected: List of absolute URLs.
    12. **Test HTTP Error Handling:**
        *   Input: Mock `session.get` to raise `httpx.HTTPStatusError(response=httpx.Response(404))`.
        *   Expected: Dictionary with all metadata fields as `None` or `[]`, but `source_url` should still be the input URL. Error logged.
    13. **Test Network Error Handling:**
        *   Input: Mock `session.get` to raise `httpx.RequestError("Timeout")`.
        *   Expected: Dictionary with all metadata fields as `None` or `[]`, `source_url` present. Error logged.
    14. **Test HTML Variations (if significant ones noted by `debug` mode):**
        *   Input: Mocked HTML representing a known structural variation.
        *   Expected: Correct extraction despite the variation, or graceful fallback to `None`/`[]` for affected fields.
    15. **Test Article Page (for DOI):**
        *   Input: Mocked HTML similar to the second example provided by the user (article page with DOI).
        *   Expected: `doi` field correctly populated, other fields might be `None` or `[]` if not applicable to articles.

### 5.2. Node.js Zod Schemas (for `get_book_metadata` tool in `src/index.ts`)

*   **Input Schema (`BookPageUrlSchema` - example name):**
    *   `z.object({ url: z.string().url() })`
    *   Test valid URL input.
    *   Test invalid URL input (e.g., not a string, not a URL, empty string). Expected: Zod validation error.

*   **Output Schema (`BookMetadataSchema` - from project plan):**
    *   Test with a valid Python dictionary output that matches the schema perfectly. Expected: Validation passes.
    *   Test with Python dictionary output where an optional string field (e.g., `doi`) is `null`. Expected: Validation passes.
    *   Test with Python dictionary output where an optional list field (e.g., `tags`) is `null` or an empty array `[]`. Expected: Validation passes.
    *   Test with Python dictionary output where a required field (`source_url`) is missing. Expected: Zod validation error.
    *   Test with Python dictionary output where a field has the wrong data type (e.g., `publication_year` is a string "1990" instead of number `1990`). Expected: Zod validation error.
    *   Test with Python dictionary output where `cover_image_url` is not a valid URL string. Expected: Zod validation error.
    *   Test with Python dictionary output where `related_booklist_urls` contains non-URL strings. Expected: Zod validation error.
    *   Test with an empty dictionary. Expected: Zod validation error (missing `source_url`).

## 6. Edge Cases & Constraints

*   **HTML Structure Changes:** The primary constraint is the reliance on Z-Library's HTML structure. Changes to the website can break selectors. Robust selectors and graceful error handling per field are crucial.
*   **Missing Metadata:** Not all books will have all fields. The system must handle this by returning `None` or `[]` as appropriate.
*   **Data Formatting Variations:** Dates, ISBNs, filesizes might have slight variations. Cleaning logic should be flexible.
*   **Rate Limiting/Anti-Scraping:** The `httpx.AsyncClient` should be configured with reasonable timeouts and potentially a shared session if multiple calls are made in sequence by other parts of the application (though this tool makes one call per book URL). User-Agent spoofing might be considered if issues arise.
*   **Character Encoding:** Assume UTF-8, which is standard. `httpx` handles this well.
*   **JavaScript-Rendered Content:** If critical metadata is rendered by JavaScript after initial page load, `httpx` + `BeautifulSoup` alone won't suffice. This would require a browser automation tool (e.g., Playwright, Puppeteer) which is outside the current scope defined by using `httpx`. The provided HTML suggests server-side rendering for most data.
*   **Custom Web Components (`z-cover`, `z-tags`, `z-booklist`):** Scraping data from these might require inspecting their rendered HTML output or understanding if they expose data attributes. If they use Shadow DOM and data is not reflected in the light DOM, scraping becomes more complex. The pseudocode assumes these render into parseable HTML or have accessible attributes.

## 7. Future Considerations

*   **Selector Configuration:** If Z-Library's HTML changes frequently, making selectors configurable (e.g., via a JSON file) could be beneficial, but adds complexity.
*   **More Granular ISBN Handling:** Store ISBN-10 and ISBN-13 separately if the schema is updated.
*   **Structured Series Info:** If series includes a number (e.g., "Book 1 of The Series"), parse this into a structured object.
*   **Advanced Text Cleaning:** For fields like description, more advanced NLP cleaning could be applied if needed.