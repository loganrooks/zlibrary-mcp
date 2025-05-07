# File: zlibrary/src/zlibrary/scrapers.py
# Dependencies: httpx, beautifulsoup4, typing, re, urllib.parse

from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin

# Selectors based on docs/get-book-metadata-spec.md and test HTML structure
SELECTORS = {
    "title": "h1[itemprop='name']",
    "authors": "div.authors a[itemprop='author']", # For multiple authors
    "authors_fallback_text": "div.authors", # Fallback if no <a> tags
    "series_text": "div.series", # For series text like "Test Series (Book 1)"
    "series_url": "div.series a[href]",
    "publisher": "div.publisher", # Simplified for test HTML, spec: "div.bookProperty.property_publisher .property_value"
    "publication_year": "div.year", # Simplified for test HTML, spec: "div.bookProperty.property_year .property_value"
    "language": "div.language", # Simplified for test HTML, spec: "div.bookProperty.property_language .property_value"
    "isbn_container": "div.isbn", # Container for ISBNs, spec: "div.bookProperty.property_isbn.13 .property_value", "div.bookProperty.property_isbn.10 .property_value"
    "categories_text": "div.category", # Simplified for test HTML, spec: "div.bookProperty.property_categories .property_value" or "div.tag-box a.tag"
    "description": "div[itemprop='description']", # More specific
    "cover_image_url": "img.cover[itemprop='image']", # More specific
    "pages_text_container": "div.file-info", # Container for pages, filesize, doi from test HTML
    "doi_text_container": "div.file-info", # Container for pages, filesize, doi from test HTML
    "filesize_text_container": "div.file-info", # Container for pages, filesize, doi from test HTML
    "booklists_urls": "div#booklists a[href]",
    "you_may_be_interested_in_urls": "div#you-may-be-interested-in a[href]",
    "most_frequent_terms": "div.frequentTerms a",
    # Selectors from original scrapers.py that might be more robust for real pages
    "publisher_spec": "div.bookProperty.property_publisher > div.property_value",
    "publication_year_spec": "div.bookProperty.property_year > div.property_value",
    "language_spec": "div.bookProperty.property_language > div.property_value",
    "isbn13_spec": "div.bookProperty.property_isbn.\\31 3 > div.property_value",
    "isbn10_spec": "div.bookProperty.property_isbn.\\31 0 > div.property_value",
    "series_spec": "div.bookProperty.property_series > div.property_value",
    "series_url_spec": "div.bookProperty.property_series > div.property_value a[href]",
    "pages_spec": "div.bookProperty.property_pages > div.property_value > span[title*='Pages']", # More specific from original
    "filesize_spec": "div.bookProperty.property__file > div.property_value", # More specific from original
    "doi_spec_value": "div.bookProperty.property_doi > div.property_value", # Spec direct DOI
    "doi_label_check_spec": "div.bookProperty > div.property_label",
    "doi_value_check_spec": "div.bookProperty > div.property_value",
    "description_spec": "div#bookDescriptionBox",
    "cover_image_url_spec": "div.details-book-cover-container z-cover img[src]",
    "cover_image_url_alt_spec": "div.col-sm-3.details-book-cover-container img[src]",
    "categories_spec_tags": "div.tag-box a.tag", # From spec for tags/categories
    "most_frequent_terms_spec": "div.termsCloud div.termWrap a.color1",
    "booklists_urls_spec": "div.related-booklists-block a[href*='/booklist/']",
    "you_may_be_interested_in_urls_spec": "div.books-mosaic div.masonry-endless div.item a[href*='/book/']"
}

BookMetadata = Dict[str, Any]

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
                # Ensure the URL is absolute
                parsed_attr_url = urlparse(attr_value)
                if not parsed_attr_url.scheme or not parsed_attr_url.netloc:
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
                parsed_attr_url = urlparse(attr_val)
                if not parsed_attr_url.scheme or not parsed_attr_url.netloc:
                    attr_val = urljoin(base_url, attr_val)
            attrs.append(attr_val)
    return attrs if attrs else (default_if_empty if default_if_empty is not None else [])


async def scrape_metadata(url: str, session: httpx.AsyncClient) -> BookMetadata:
    # Initialize metadata dictionary to match BookMetadataOutputSchema and test expectations
    metadata: BookMetadata = {
        "title": None,
        "authors": [],
        "series_name": None,
        "series_url": None,
        "publisher": None,
        "publication_year": None,
        "language": None,
        "isbn_list": [],
        "categories": [],
        "description": None,
        "cover_image_url": None,
        "pages_count": None,
        "filesize_str": None,
        "doi": None,
        "booklists_urls": [],
        "you_may_be_interested_in_urls": [],
        "most_frequent_terms": [],
        "source_url": url,
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
        authors_list = []
        # Try the more specific selector first
        author_elements = soup.select("div.col-sm-9 > i > a.color1[title*=\"Find all the author's book\"]")
        if not author_elements: # Fallback to a simpler version
            author_elements = soup.select("div.col-sm-9 i a.color1")

        for el in author_elements:
            author_name = _safe_get_text(el)
            if author_name and author_name not in authors_list:
                authors_list.append(author_name)

        # If specific selectors didn't work, try the original broader approach as a last resort,
        # but this is less reliable for the problematic pages.
        if not authors_list:
            authors_container_fallback = soup.select_one(SELECTORS["authors_fallback_text"])
            if authors_container_fallback:
                author_elements_fallback = authors_container_fallback.select(SELECTORS["authors"])
                for el_fb in author_elements_fallback:
                    authors_list.append(_safe_get_text(el_fb))
                
                full_authors_text_fb = _safe_get_text(authors_container_fallback)
                if full_authors_text_fb:
                    potential_authors_fb = [a.strip() for a in re.split(r',|;', full_authors_text_fb) if a.strip()]
                    for pa_fb in potential_authors_fb:
                        is_already_added_substring_fb = False
                        for added_author_fb in authors_list:
                            if pa_fb in added_author_fb:
                                is_already_added_substring_fb = True
                                break
                        if not is_already_added_substring_fb and pa_fb not in authors_list:
                            is_just_a_tag_text_fb = any(pa_fb == _safe_get_text(ae_fb) for ae_fb in author_elements_fallback)
                            if not is_just_a_tag_text_fb:
                               authors_list.append(pa_fb)
                authors_list = [author for author in authors_list if author]

        metadata["authors"] = authors_list if authors_list else []


        # 3. Series Name & URL
        series_text_element = soup.select_one(SELECTORS["series_text"])
        if series_text_element:
            series_full_text = _safe_get_text(series_text_element)
            if series_full_text:
                # Try to extract series name before parenthesis
                series_match = re.match(r"^(.*?)(?:\s*\(.*\))?$", series_full_text)
                if series_match and series_match.group(1):
                    metadata["series_name"] = series_match.group(1).strip()
                else:
                    metadata["series_name"] = series_full_text.strip() # Fallback to full text
        
        series_url_element = soup.select_one(SELECTORS["series_url"])
        if not series_url_element and series_text_element: # Try within the series_text element
            series_url_element = series_text_element.select_one("a[href]")

        metadata["series_url"] = _safe_get_attr(series_url_element, "href", base_url=base_page_url)
        if not metadata["series_name"]: # If only URL was found, try to get name from <a> text
            metadata["series_name"] = _safe_get_text(series_url_element)


        # 4. Publisher
        metadata["publisher"] = _safe_get_text(soup.select_one(SELECTORS["publisher"]))
        if not metadata["publisher"]:
            metadata["publisher"] = _safe_get_text(soup.select_one(SELECTORS["publisher_spec"]))


        # 5. Publication Year
        year_text = _safe_get_text(soup.select_one(SELECTORS["publication_year"]))
        if not year_text:
            year_text = _safe_get_text(soup.select_one(SELECTORS["publication_year_spec"]))
        if year_text:
            year_match = re.search(r'\d{4}', year_text.strip())
            if year_match:
                metadata["publication_year"] = int(year_match.group(0))

        # 6. Language
        lang_text = _safe_get_text(soup.select_one(SELECTORS["language"]))
        if not lang_text:
            lang_text = _safe_get_text(soup.select_one(SELECTORS["language_spec"]))
        if lang_text:
            metadata["language"] = lang_text.strip() # Keep case as is for now, tests expect "English", "français"

        # 7. ISBN List
        cleaned_isbns = []
        isbn13_text = _safe_get_text(soup.select_one(SELECTORS["isbn13_spec"]))
        if isbn13_text:
            cleaned_isbn13 = re.sub(r'[^0-9X]', '', isbn13_text.upper())
            if len(cleaned_isbn13) == 13:
                cleaned_isbns.append(cleaned_isbn13)

        isbn10_text = _safe_get_text(soup.select_one(SELECTORS["isbn10_spec"]))
        if isbn10_text:
            cleaned_isbn10 = re.sub(r'[^0-9X]', '', isbn10_text.upper())
            if len(cleaned_isbn10) == 10 and cleaned_isbn10 not in cleaned_isbns:
                cleaned_isbns.append(cleaned_isbn10)
        
        # Fallback to regex search if specific selectors fail, as a last resort
        if not cleaned_isbns:
            all_text_for_isbn_search = soup.get_text(separator=" ")
            found_isbns_fallback = re.findall(r'\b(?:ISBN(?:-1[03])?:?\s*)?((?:97[89]-?)?\d{9}[\dX])\b', all_text_for_isbn_search, re.IGNORECASE)
            for isbn_val_fb in found_isbns_fallback:
                cleaned_fb = re.sub(r'[^0-9X]', '', isbn_val_fb.upper())
                if (len(cleaned_fb) == 10 or len(cleaned_fb) == 13) and cleaned_fb not in cleaned_isbns:
                    cleaned_isbns.append(cleaned_fb)
            
        metadata["isbn_list"] = list(dict.fromkeys(cleaned_isbns)) # Remove duplicates

        # 8. Categories
        categories_text = _safe_get_text(soup.select_one(SELECTORS["categories_text"]))
        if categories_text:
            metadata["categories"] = [cat.strip() for cat in categories_text.split(',') if cat.strip()]
        else: # Fallback to spec tags selector
            tag_elements = soup.select(SELECTORS["categories_spec_tags"])
            if tag_elements:
                metadata["categories"] = _safe_get_all_texts(tag_elements, default_if_empty=[])


        # 9. Description
        desc_el = soup.select_one(SELECTORS["description"])
        if not desc_el:
            desc_el = soup.select_one(SELECTORS["description_spec"])
        metadata["description"] = _safe_get_text(desc_el)
        if metadata["description"]:
             metadata["description"] = metadata["description"].strip()


        # 10. Cover Image URL
        cover_el = soup.select_one(SELECTORS["cover_image_url"])
        if not cover_el: # Fallback to spec selectors
            cover_el = soup.select_one(SELECTORS["cover_image_url_spec"])
        if not cover_el:
            cover_el = soup.select_one(SELECTORS["cover_image_url_alt_spec"])
        metadata["cover_image_url"] = _safe_get_attr(cover_el, "src", base_url=base_page_url)


        # 11. Pages Count, 12. Filesize Str, 13. DOI (from file-info or spec)
        # Try test HTML structure first
        file_info_container = soup.select_one(SELECTORS["pages_text_container"]) # Assuming pages_text_container is same for all three
        if file_info_container:
            prop_labels = file_info_container.select("span.property_label")
            prop_values = file_info_container.select("span.property_value")

            for label, value_el in zip(prop_labels, prop_values):
                label_text = _safe_get_text(label, "").lower()
                value_text = _safe_get_text(value_el)
                if not value_text: continue

                if "pages" in label_text:
                    pages_match = re.search(r'\d+', value_text)
                    if pages_match: metadata["pages_count"] = int(pages_match.group(0))
                elif "file size" in label_text:
                    metadata["filesize_str"] = value_text.strip()
                elif "doi" in label_text and "10." in value_text:
                    metadata["doi"] = value_text.strip()
        
        # Fallbacks using spec selectors if not found in test structure
        if metadata["pages_count"] is None:
            pages_text_spec = _safe_get_text(soup.select_one(SELECTORS["pages_spec"]))
            if pages_text_spec:
                pages_match_spec = re.search(r'\d+', pages_text_spec)
                if pages_match_spec: metadata["pages_count"] = int(pages_match_spec.group(0))

        if metadata["filesize_str"] is None:
            filesize_text_spec = _safe_get_text(soup.select_one(SELECTORS["filesize_spec"]))
            if filesize_text_spec: metadata["filesize_str"] = filesize_text_spec.strip()
        
        if metadata["doi"] is None:
            doi_text_spec = _safe_get_text(soup.select_one(SELECTORS["doi_spec_value"]))
            if doi_text_spec and "10." in doi_text_spec:
                metadata["doi"] = doi_text_spec.strip()
            else: # Try generic label check from spec
                doi_prop_elements_spec = soup.select('div.bookProperty') # Re-select based on spec structure
                for prop_el_spec in doi_prop_elements_spec:
                    label_el_spec = prop_el_spec.select_one(SELECTORS["doi_label_check_spec"])
                    value_el_spec = prop_el_spec.select_one(SELECTORS["doi_value_check_spec"])
                    if label_el_spec and value_el_spec and "DOI" in _safe_get_text(label_el_spec, "").upper():
                        doi_text_candidate_spec = _safe_get_text(value_el_spec)
                        if doi_text_candidate_spec and "10." in doi_text_candidate_spec and "/" in doi_text_candidate_spec:
                            metadata["doi"] = doi_text_candidate_spec.replace("DOI:", "").strip()
                            break


        # 14. Booklist URLs
        booklist_elements = soup.select(SELECTORS["booklists_urls"])
        if not booklist_elements:
            booklist_elements = soup.select(SELECTORS["booklists_urls_spec"])
        metadata["booklists_urls"] = _safe_get_all_attrs(booklist_elements, "href", base_url=base_page_url, default_if_empty=[])


        # 15. You May Be Interested In URLs
        related_elements = soup.select(SELECTORS["you_may_be_interested_in_urls"])
        if not related_elements:
            related_elements = soup.select(SELECTORS["you_may_be_interested_in_urls_spec"])
        metadata["you_may_be_interested_in_urls"] = _safe_get_all_attrs(related_elements, "href", base_url=base_page_url, default_if_empty=[])


        # 16. Most Frequent Terms
        terms_elements = soup.select(SELECTORS["most_frequent_terms"])
        if not terms_elements:
            terms_elements = soup.select(SELECTORS["most_frequent_terms_spec"])
        metadata["most_frequent_terms"] = _safe_get_all_texts(terms_elements, default_if_empty=[])


    except httpx.HTTPStatusError as e:
        print(f"HTTP error fetching {url}: Status {e.response.status_code} on {e.request.url if e.request else 'unknown URL'}")
    except httpx.RequestError as e:
        print(f"Network error fetching {url}: {e} on {e.request.url if e.request else 'unknown URL'}")
    except Exception as e:
        import traceback
        print(f"Unexpected error scraping {url}: {e}\n{traceback.format_exc()}")

    return metadata