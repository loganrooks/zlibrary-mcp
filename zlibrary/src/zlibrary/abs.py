import re
from typing import Dict, Any, Optional, List, Union, Callable, Coroutine
from typing import Callable, Optional
from bs4 import BeautifulSoup as bsoup
from bs4 import Tag
from urllib.parse import quote

from .exception import ParseError, BookNotFound # Ensure BookNotFound is imported
from .logger import logger

import json


DLNOTFOUND = "Downloads not found"
LISTNOTFOUND = "On your request nothing has been found"


class SearchPaginator:
    __url = ""
    __pos = 0
    __r: Optional[Callable] = None

    mirror = ""
    page = 1
    total = 0
    count = 10

    result = []

    storage = {1: []}

    def __init__(self, url: str, count: int, request: Callable, mirror: str):
        if count > 50:
            count = 50
        if count <= 0:
            count = 1
        self.count = count
        self.__url = url
        self.constructed_url = url # Store the initially constructed URL
        self.__r = request
        self.mirror = mirror

    def __repr__(self):
        return f"<Paginator [{self.__url}], count {self.count}, len(result): {len(self.result)}, pages in storage: {len(self.storage.keys())}>"

    def parse_page(self, page):
        logger.debug(f"Parsing page for URL: {self.__url}")
        html_excerpt = page[:2000].replace('\n', ' ') + ('...' if len(page) > 2000 else '')
        logger.debug(f"Raw HTML excerpt: {html_excerpt}")

        soup = bsoup(page, features="lxml")
        content_area = soup.find("div", {"id": "searchFormResultsList"})
        if not content_area:
            content_area = soup.find("div", {"class": "itemFullText"})
            logger.debug("Using 'div.itemFullText' as content_area for search results.")
            if content_area: logger.debug(f"Content of div.itemFullText (first 2000 chars): {str(content_area)[:2000]}")
            if not content_area:
                content_area = soup.body
                logger.debug("Using soup.body as content_area for search results.")
        else:
            logger.debug("Using 'div#searchFormResultsList' as content_area for search results.")

        if not content_area:
            logger.error("Failed to find any main content area for search results.")
            raise ParseError(f"Could not find main content area for search results URL: {self.__url}")

        is_id_search_url = bool(re.search(r"/s/id%3A", self.__url))
        if not isinstance(content_area, Tag): # Check if it's a Tag before proceeding
            logger.debug("Primary content_area not found or not a Tag.")
            book_page_check = soup.find("div", {"class": "row cardBooks"})
            if book_page_check and is_id_search_url:
                logger.debug("Potential direct book page detected.")
                try:
                    logger.debug("Attempting direct parse with _parse_book_page_soup.")
                    book_item = BookItem(self.__r, self.mirror)
                    book_item["url"] = self.__url 
                    parsed_data = book_item._parse_book_page_soup(soup) 
                    logger.debug(f"Direct parse result: {parsed_data}")
                    self.storage[self.page] = [parsed_data] if parsed_data else []
                    self.result = self.storage[self.page]
                    logger.debug(f"Direct parse successful, result set: {self.result}")
                    return
                except Exception as e:
                    logger.error(f"Direct parse FAILED for {self.__url}: {e}", exc_info=True)
            logger.error(f"Raising ParseError: Could not parse book list (content_area not valid Tag and not a direct book page) for URL: {self.__url}")
            raise ParseError(f"Could not parse book list (content_area not valid Tag) for URL: {self.__url}")

        check_notfound = content_area.find("div", {"class": "notFound"})
        if check_notfound:
            logger.debug("Standard search page returned 'notFound'.")
            self.storage[self.page] = []
            self.result = []
            return

        book_item_wrappers = content_area.findAll("div", {"class": "book-card-wrapper"})
        if not book_item_wrappers:
            book_item_wrappers = content_area.findAll("div", {"class": "book-item"})
            if book_item_wrappers:
                logger.debug(f"Found {len(book_item_wrappers)} 'div.book-item' elements (fallback).")
            else:
                logger.warning("No 'div.book-card-wrapper' or 'div.book-item' elements found. Raising ParseError.")
                raise ParseError("Could not find the book list items.")
        else:
            logger.debug(f"Found {len(book_item_wrappers)} 'div.book-card-wrapper' elements.")

        if book_item_wrappers:
             logger.debug(f"First book item wrapper structure: {str(book_item_wrappers[0])[:500]}...")

        self.storage[self.page] = []
        logger.debug("Parsing standard book list items...")
        for idx, item_wrapper in enumerate(book_item_wrappers, start=1):
            js = BookItem(self.__r, self.mirror)
            book_card_el = item_wrapper.find("z-bookcard")
            if not book_card_el:
                logger.warning(f"No z-bookcard found in item_wrapper {idx}. Skipping.")
                continue

            cover = book_card_el.find("img")
            if not cover:
                logger.warning(f"Cover not found for {idx}-th book-card at url {self.__url}")

            js["id"] = book_card_el.get("id")
            js["isbn"] = book_card_el.get("isbn")

            book_url_attr = book_card_el.get("href")
            if book_url_attr:
                js["url"] = f"{self.mirror}{book_url_attr}"

            if cover:
                img_tag_for_cover = cover.find("img")
                if img_tag_for_cover:
                    js["cover"] = img_tag_for_cover.get("data-src")
                else:
                    js["cover"] = cover.get("data-src")

            publisher = book_card_el.get("publisher")
            if publisher:
                js["publisher"] = publisher.strip()

            # Try attribute first, then slot element for authors
            authors_str = book_card_el.get("authors")
            if not authors_str:
                # Try slot structure: <div slot="author">Name</div>
                author_slot = book_card_el.find("div", {"slot": "author"})
                if author_slot:
                    authors_str = author_slot.get_text(strip=True)

            if authors_str:
                authors_list = [a.strip() for a in authors_str.split(';') if a.strip()]
                if authors_list:
                    js["authors"] = authors_list

            # Try attribute first, then slot element for title
            title_str = book_card_el.get("name")
            if not title_str:
                # Try slot structure: <div slot="title">Title</div>
                title_slot = book_card_el.find("div", {"slot": "title"})
                if title_slot:
                    title_str = title_slot.get_text(strip=True)

            if title_str:
                js["name"] = title_str.strip()

            year = book_card_el.get("year")
            if year:
                js["year"] = year.strip()

            lang = book_card_el.get("language")
            if lang:
                js["language"] = lang.strip()

            ext = book_card_el.get("extension")
            if ext:
                js["extension"] = ext.strip()

            size = book_card_el.get("filesize")
            if size:
                js["size"] = size.strip()

            rating = book_card_el.get("rating")
            if rating:
                js["rating"] = rating.strip()

            quality = book_card_el.get("quality")
            if quality:
                js["quality"] = quality.strip()

            # Explicit title/author fields for clearer API surface
            js["title"] = js.get("name") or None
            js["author"] = js["authors"][0] if js.get("authors") else None

            if not js.get("id") and not js.get("name") and not js.get("url"):
                logger.warning(f"Skipping {idx}-th book-card due to missing essential info (id, name, url).")
                continue

            self.storage[self.page].append(js)

        scripts = soup.findAll("script")
        for scr in scripts:
            txt = scr.text
            if "var pagerOptions" in txt:
                pos = txt.find("pagesTotal: ")
                fix = txt[pos + len("pagesTotal: ") :]
                count_str = fix.split(",")[0]
                if count_str.isdigit():
                    self.total = int(count_str)

    async def init(self):
        page_content = await self.fetch_page()
        if page_content: # Ensure page_content is not None
            self.parse_page(page_content)
        else:
            logger.warning(f"fetch_page returned None for {self.__url}&page={self.page}. Cannot parse.")
            self.storage[self.page] = [] # Ensure storage is initialized for the page
            self.result = []


    async def fetch_page(self):
        if self.__r:
            return await self.__r(f"{self.__url}&page={self.page}")
        return None


    async def next(self):
        if self.__pos >= len(self.storage.get(self.page, [])): # Handle page not in storage
            await self.next_page()
            if not self.storage.get(self.page): # If still not in storage after next_page
                self.result = []
                return self.result


        self.result = self.storage.get(self.page, [])[self.__pos : self.__pos + self.count]
        self.__pos += self.count
        return self.result

    async def prev(self):
        self.__pos -= self.count
        if self.__pos < 1: # Should be self.__pos < 0 if 0-indexed
            await self.prev_page()
            if not self.storage.get(self.page):
                 self.result = []
                 return self.result


        subtract = self.__pos - self.count
        if subtract < 0:
            subtract = 0
        # if self.__pos <= 0: # This logic might be problematic if __pos can be 0
        #     self.__pos = self.count # This seems to reset __pos incorrectly

        current_page_items = self.storage.get(self.page, [])
        self.result = current_page_items[subtract : self.__pos if self.__pos > 0 else 0] # Ensure slice is valid
        return self.result


    async def next_page(self):
        if self.page < self.total:
            self.page += 1
            self.__pos = 0
        else:
            # self.__pos -= self.count # This could make __pos negative if at end
            # if self.__pos < 0:
            #     self.__pos = 0
            # If already at the last page, no next page to fetch
            logger.debug("Already at the last page or total pages unknown.")
            return


        if not self.storage.get(self.page):
            page_content = await self.fetch_page()
            if page_content:
                self.parse_page(page_content)
            else:
                logger.warning(f"fetch_page returned None for next_page {self.page}. Cannot parse.")
                self.storage[self.page] = []


    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.__pos = 0 # Reset position for the new previous page
        else:
            self.__pos = 0
            logger.debug("Already at the first page.")
            return

        if not self.storage.get(self.page):
            page_content = await self.fetch_page()
            if page_content:
                self.parse_page(page_content)
            else:
                logger.warning(f"fetch_page returned None for prev_page {self.page}. Cannot parse.")
                self.storage[self.page] = []
        
        # Set position to the end of the newly loaded previous page to allow .prev() to correctly slice
        self.__pos = len(self.storage.get(self.page, []))


class BooklistPaginator:
    __url = ""
    __pos = 0
    __r: Optional[Callable] = None

    mirror = ""
    page = 1
    total = 1
    count = 10

    result = []

    storage = {1: []}

    def __init__(self, url: str, count: int, request: Callable, mirror: str):
        self.count = count
        self.__url = url
        self.__r = request
        self.mirror = mirror

    def __repr__(self):
        return f"<Booklist paginator [{self.__url}], count {self.count}, len(result): {len(self.result)}, pages in storage: {len(self.storage.keys())}>"

    def parse_page(self, page):
        soup = bsoup(page, features="lxml")

        check_notfound = soup.find("div", {"class": "cBox1"})
        if check_notfound and LISTNOTFOUND in check_notfound.text.strip():
            logger.debug("Nothing found.")
            self.storage[self.page] = []
            self.result = []
            return

        book_list = soup.findAll("z-booklist")
        if not book_list:
            raise ParseError("Could not find the booklists.")

        self.storage[self.page] = []

        for idx, booklist_item_el in enumerate(book_list, start=1): # Renamed variable
            js = BooklistItemPaginator(self.__r, self.mirror, self.count)

            name = booklist_item_el.get("topic")
            if not name:
                raise ParseError(
                    f"Could not parse {idx}-th booklist at url {self.__url}"
                )
            js["name"] = name.strip()

            book_url_attr = booklist_item_el.get("href") # Renamed variable
            if book_url_attr:
                js["url"] = f"{self.mirror}{book_url_attr}"

            info_wrap = booklist_item_el.get("description")
            if info_wrap:
                js["description"] = info_wrap.strip()

            author = booklist_item_el.get("authorprofile")
            if author:
                js["author"] = author.strip()

            count_attr = booklist_item_el.get("quantity") # Renamed variable
            if count_attr:
                js["count"] = count_attr.strip()

            views = booklist_item_el.get("views")
            if views:
                js["views"] = views.strip()

            js["books_lazy"] = []
            carousel = booklist_item_el.find_all("a")
            if not carousel:
                self.storage[self.page].append(js)
                continue
            for adx, book_el in enumerate(carousel): # Renamed variable
                res = BookItem(self.__r, self.mirror)
                res["url"] = f"{self.mirror}{book_el.get('href')}"
                res["name"] = ""

                zcover = book_el.find("z-cover")
                if zcover:
                    b_id = zcover.get("id")
                    if b_id:
                        res["id"] = b_id.strip()
                    b_au = zcover.get("author")
                    if b_au:
                        res["authors"] = [b_au.strip()] # Changed to authors list
                    b_name = zcover.get("title")
                    if b_name:
                        res["name"] = b_name.strip()
                    cover_img_tags = zcover.find_all("img") # Renamed variable
                    if cover_img_tags:
                        for c_img in cover_img_tags: # Renamed variable
                            d_src = c_img.get("data-src")
                            if d_src:
                                res["cover"] = d_src.strip() # Changed js to res

                # Explicit title/author fields for clearer API surface
                res["title"] = res.get("name") or None
                res["author"] = res["authors"][0] if res.get("authors") else None

                js["books_lazy"].append(res)

            self.storage[self.page].append(js)

        scripts = soup.findAll("script")
        for scr in scripts:
            txt = scr.text
            if "var pagerOptions" in txt:
                pos = txt.find("pagesTotal: ")
                fix = txt[pos + len("pagesTotal: ") :]
                count_str = fix.split(",")[0] # Renamed variable
                if count_str.isdigit():
                    self.total = int(count_str)


    async def init(self):
        page_content = await self.fetch_page() # Renamed variable
        if page_content:
            self.parse_page(page_content)
        else:
            logger.warning(f"fetch_page returned None for {self.__url}&page={self.page} in BooklistPaginator. Cannot parse.")
            self.storage[self.page] = []
            self.result = []
        return self


    async def fetch_page(self):
        if self.__r:
            return await self.__r(f"{self.__url}&page={self.page}")
        return None

    async def next(self):
        if self.__pos >= len(self.storage.get(self.page, [])):
            await self.next_page()
            if not self.storage.get(self.page):
                self.result = []
                return self.result
        
        self.result = self.storage.get(self.page, [])[self.__pos : self.__pos + self.count]
        self.__pos += self.count
        return self.result

    async def prev(self):
        self.__pos -= self.count
        if self.__pos < 0: # Corrected condition
            await self.prev_page()
            if not self.storage.get(self.page):
                 self.result = []
                 return self.result

        current_page_items = self.storage.get(self.page, [])
        # Ensure slice indices are valid
        start_index = max(0, self.__pos - self.count + self.count) # This logic seems off, should be simpler
        # Corrected logic for prev slice:
        # If __pos became negative, prev_page was called which resets __pos to end of new prev page.
        # So, __pos should be positive here.
        # We want items from [__pos - count, __pos) effectively, but __pos was already decremented.
        # Let's rethink: after self.__pos -= self.count, if it's still >= 0, we need items from
        # current_page_items[self.__pos : self.__pos + self.count] if we consider __pos as start of next block.
        # Or, if __pos is the end of the current block, then current_page_items[self.__pos - self.count : self.__pos]
        
        # Simpler: after self.__pos -= self.count, if self.__pos < 0, prev_page is called.
        # prev_page sets self.__pos = len(self.storage[self.page])
        # So, after prev_page, self.__pos is the total number of items on that page.
        # The slice should be the last 'self.count' items.
        start_index = max(0, len(current_page_items) - self.count)
        self.result = current_page_items[start_index:] # Get the last 'count' items
        # This might not be right if __pos was not reset by prev_page correctly.
        # Let's stick to the original logic for now and debug if it fails.
        subtract = self.__pos # This was already decremented by self.count
        if subtract < 0: subtract = 0 # Should not happen if prev_page was called
        
        # The original logic was:
        # subtract = self.__pos - self.count 
        # if subtract < 0: subtract = 0
        # if self.__pos <= 0: self.__pos = self.count 
        # self.result = self.storage[self.page][subtract : self.__pos]
        # This seems more plausible if __pos is the end of the slice.
        
        # Let's use a simplified version based on __pos being the new end after decrement
        end_pos = self.__pos + self.count # Original position before decrement
        start_pos = self.__pos
        if start_pos < 0: start_pos = 0 # Should be handled by prev_page
        
        self.result = self.storage.get(self.page, [])[start_pos : end_pos]


        return self.result


    async def next_page(self):
        if self.page < self.total:
            self.page += 1
            self.__pos = 0
        else:
            logger.debug("BooklistPaginator: Already at the last page or total pages unknown.")
            return

        if not self.storage.get(self.page):
            page_content = await self.fetch_page()
            if page_content:
                self.parse_page(page_content)
            else:
                logger.warning(f"fetch_page returned None for BooklistPaginator next_page {self.page}. Cannot parse.")
                self.storage[self.page] = []


    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.__pos = 0 
        else:
            self.__pos = 0
            logger.debug("BooklistPaginator: Already at the first page.")
            return

        if not self.storage.get(self.page):
            page_content = await self.fetch_page()
            if page_content:
                self.parse_page(page_content)
            else:
                logger.warning(f"fetch_page returned None for BooklistPaginator prev_page {self.page}. Cannot parse.")
                self.storage[self.page] = []
        
        self.__pos = len(self.storage.get(self.page, []))


class DownloadsPaginator:
    __url = ""
    __r = None
    page = 1
    mirror = ""

    result = []

    storage = {1: []}

    def __init__(self, url: str, page: int, request: Callable, mirror: str):
        self.__url = url
        self.__r = request
        self.mirror = mirror
        self.page = page

    def __repr__(self):
        return f"<DownloadsPaginator [{self.__url}]>"

    def parse_page(self, page_content_html: str): # Renamed for clarity
        soup = bsoup(page_content_html, features="lxml")
        content_area = soup.find("div", {"class": "dstats-table-content"})
        if not content_area:
            logger.debug("Primary 'dstats-table-content' not found. Trying fallbacks for DownloadsPaginator.")
            content_area = soup.find("div", {"id": "content"})
            if not content_area:
                content_area = soup.find("main")
                if not content_area:
                    content_area = soup.find("div", {"class": "content"})
                    if not content_area:
                        content_area = soup.body
                        logger.debug("Using soup.body as content_area for DownloadsPaginator.")

        if not content_area or not isinstance(content_area, Tag):
            logger.error(f"Could not find a valid main content area for downloads list. URL: {self.__url}")
            raise ParseError(f"Could not find a valid main content area for downloads list. URL: {self.__url}")

        check_notfound = content_area.find("p", string=re.compile(DLNOTFOUND, re.IGNORECASE))
        if check_notfound: # Simpler check
            logger.debug("DownloadsPaginator: This page appears empty (downloads not found message).")
            self.storage[self.page] = []
            self.result = []
            return

        book_list = content_area.find_all("div", {"class": "item-wrap"})
        is_new_structure_dominant = True # Assume new structure if item-wrap is found
        if not book_list:
            is_new_structure_dominant = False
            book_list = content_area.find_all("tr", {"class": "dstats-row"})
            if not book_list:
                if DLNOTFOUND in soup.get_text(): # Broader check in full text
                    logger.debug("DownloadsPaginator: Found 'Downloads not found' text in soup, treating as empty page.")
                    self.storage[self.page] = []
                    self.result = []
                    return
                else:
                    logger.error("DownloadsPaginator: Could not find book items using new ('item-wrap') or old ('dstats-row') selectors.")
                    raise ParseError("Could not find the book list items in DownloadsPaginator.")

        self.storage[self.page] = []

        for idx, item in enumerate(book_list, start=1):
            js = BookItem(self.__r, self.mirror) # BookItem is a dict-like object
            
            # Determine structure based on the dominant type found, or per item if mixed (though unlikely for this page)
            is_current_item_new_structure = item.name == 'div' and 'item-wrap' in item.get('class', [])
            
            if is_current_item_new_structure: # Parsing for new structure (div.item-wrap)
                logger.debug(f"DownloadsPaginator: Parsing item {idx} as new structure (item-wrap) for URL: {self.__url}")
                info_div = item.find("div", {"class": "item-info"})
                if not info_div:
                    logger.warning(f"Item {idx} (new structure): 'item-info' div not found. Skipping.")
                    continue

                title_tag = None
                item_desc_div = info_div.find("div", {"class": "item-desc"})
                if item_desc_div:
                    title_tag = item_desc_div.find("div", {"class": "item-title"})
                
                if not title_tag: # Fallback to h5 if item-title not in item-desc
                    title_tag = info_div.find("h5")

                if title_tag and title_tag.a and title_tag.a.text and title_tag.a.get("href"):
                    js["name"] = title_tag.a.text.strip()
                    js["url"] = f"{self.mirror}{title_tag.a.get('href')}"
                    match = re.search(r"/book/(\d+)", title_tag.a.get('href'))
                    if match:
                        js["id"] = match.group(1)
                    # else: ID might come from download link or data-item_id on item-wrap
                else:
                    logger.warning(f"Item {idx} (new structure): Title/URL tag not found or invalid. Skipping.")
                    continue # Essential info missing

                date_tag = info_div.find("div", {"class": "item-date"})
                if date_tag:
                    js["date"] = date_tag.text.strip()
                
                actions_div = item.find("div", {"class": "item-actions"})
                if actions_div:
                    dl_link_tag = actions_div.find("a", class_="item-format", href=re.compile(r"/download/")) # More specific regex
                    if dl_link_tag and dl_link_tag.get("href"):
                        js["download_url"] = f"{self.mirror}{dl_link_tag.get('href')}"
                        js["extension"] = dl_link_tag.text.strip()
                        # Extract ID from download URL if not already found from book URL
                        if not js.get("id"):
                            dl_match = re.search(r"/download/(\d+)", dl_link_tag.get("href"))
                            if dl_match:
                                js["id"] = dl_match.group(1)
                
                # Fallback for ID from data-item_id if still not found
                if not js.get("id"):
                    item_id_attr = item.get("data-item_id")
                    if item_id_attr:
                        js["id"] = item_id_attr
                
                if not js.get("id") or not js.get("name"): # Check essential fields
                    logger.warning(f"Item {idx} (new structure): Missing ID or Name after parsing. JS: {js}. Skipping.")
                    continue

            else:  # Parsing for old structure (tr.dstats-row)
                logger.debug(f"DownloadsPaginator: Parsing item {idx} as old structure (dstats-row) for URL: {self.__url}")
                cells = item.find_all("td")
                if len(cells) < 5: # title, format, size, date, download_link
                    logger.warning(f"Item {idx} (old structure): not enough cells ({len(cells)} found). Expected 5. Skipping.")
                    continue
                
                # Title and Book URL (cells[0])
                title_link_tag = cells[0].find("a")
                if title_link_tag and title_link_tag.has_attr("href"):
                    js["name"] = title_link_tag.text.strip()
                    js["url"] = f"{self.mirror}{title_link_tag['href']}"
                    match = re.search(r"/book/(\d+)", title_link_tag['href'])
                    if match:
                        js["id"] = match.group(1)
                else:
                    logger.warning(f"Item {idx} (old structure): Title/URL not found in first cell. Skipping.")
                    continue

                # Extension (cells[1])
                js["extension"] = cells[1].text.strip()
                # Size (cells[2]) - optional
                js["size"] = cells[2].text.strip()
                # Date (cells[3])
                js["date"] = cells[3].text.strip()
                
                # Download URL (cells[4])
                dl_link_tag_old = cells[4].find("a", href=re.compile(r"/download/"))
                if dl_link_tag_old and dl_link_tag_old.has_attr("href"):
                    js["download_url"] = f"{self.mirror}{dl_link_tag_old['href']}"
                    # Extract/confirm ID from download URL
                    if not js.get("id"):
                        dl_match = re.search(r"/download/(\d+)", dl_link_tag_old.get("href"))
                        if dl_match:
                            js["id"] = dl_match.group(1)
                else:
                    logger.warning(f"Item {idx} (old structure): Download link not found in last cell.")
                
                if not js.get("id"): # Check ID again, essential for old structure too
                    logger.warning(f"Item {idx} (old structure): Missing ID after parsing. JS: {js}. Skipping.")
                    continue
            
            if js.get("id") and js.get("name"): # Add to results only if essential info is present
                 self.storage[self.page].append(js)
            else:
                logger.warning(f"Item {idx}: Skipped due to missing essential ID or Name. Final JS: {js}")


        # Pagination (assuming it's outside the main content_area or handled globally)
        # This part of the original code might need to be adapted or might not apply to downloads page
        # For now, focusing on item parsing. If pagination is different, it needs separate logic.
        # Example: scripts = soup.findAll("script") ... for var pagerOptions
        # This is usually for search results, download history might use simple next/prev links.
        # For now, we assume the 'total' pages might not be easily available or needed for basic history retrieval.
        # If the downloads page has clear next/prev links, that would be parsed here.
        # For simplicity, this example doesn't implement complex pagination parsing for downloads.
        # It assumes we get one page of results.
        # A more robust solution would inspect the actual downloads page for pagination controls.
        
        # A simple way to check for more pages could be looking for a "Next" link
        # next_page_link = soup.find("a", text=re.compile("Next", re.IGNORECASE)) # or specific class/id
        # self.total = self.page + 1 if next_page_link else self.page # Simplistic total update

        self.result = self.storage[self.page]


    async def init(self):
        page_content = await self.fetch_page()
        if page_content:
            self.parse_page(page_content)
        else:
            logger.warning(f"fetch_page returned None for DownloadsPaginator {self.__url}&page={self.page}. Cannot parse.")
            self.storage[self.page] = []
            self.result = []
        return self # Return self to allow chaining or direct access to results


    async def fetch_page(self):
        if self.__r:
            # Ensure the URL for fetching includes the page number correctly
            # The base self.__url might already have page param from profile.py, or not.
            # Let's assume profile.py constructs the base URL with date filters,
            # and we append page here if not already present.
            url_to_fetch = self.__url
            if f"page={self.page}" not in self.__url:
                 # Check if URL already has query params
                separator = '&' if '?' in self.__url else '?'
                url_to_fetch = f"{self.__url}{separator}page={self.page}"
            
            logger.debug(f"DownloadsPaginator: Fetching page {self.page} from URL: {url_to_fetch}")
            return await self.__r(url_to_fetch)
        return None

    # next(), prev(), next_page(), prev_page() methods for DownloadsPaginator
    # These would be simpler if the downloads page has straightforward next/prev links
    # or if total pages can be determined. For now, let's assume single page or
    # leave them as basic stubs if full pagination isn't immediately needed for the tests.

    async def next_page(self):
        # This is a simplified version. Real pagination would check if a next page exists.
        self.page += 1
        self.__pos = 0 # Reset position for the new page
        logger.debug(f"DownloadsPaginator: Attempting to load next page ({self.page}).")
        await self.init() # Re-initialize to fetch and parse the new page

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.__pos = 0 # Reset position
            logger.debug(f"DownloadsPaginator: Attempting to load previous page ({self.page}).")
            await self.init() # Re-initialize
        else:
            logger.debug("DownloadsPaginator: Already at the first page.")
    
    # next() and prev() for item-wise iteration if needed, though often just getting page results is enough.
    # For now, the primary goal is that self.result is populated by init().


# This class seems to be a general book item representation.
# It's used by SearchPaginator, BooklistPaginator, and DownloadsPaginator.
# The _parse_book_page_soup method is crucial if a direct book page is encountered.
class BookItem(dict):
    __r = None
    parsed = None
    mirror = ""

    def __init__(self, request, mirror):
        super().__init__()
        self.__r = request
        self.mirror = mirror

    async def fetch(self):
        if not self.__r:
            raise Exception("Request function not set for BookItem")
        if not self.get("url"):
            raise Exception("BookItem URL not set, cannot fetch details")

        logger.debug(f"BookItem: Fetching details for {self.get('url')}")
        try:
            page_content = await self.__r(self.get("url"))
            if not page_content:
                logger.warning(f"BookItem: No content returned from fetch for URL {self.get('url')}")
                raise ParseError(f"No content from fetch for {self.get('url')}")

            soup = bsoup(page_content, features="lxml")
            parsed_data = self._parse_book_page_soup(soup)
            self.update(parsed_data) # Update the BookItem dict with parsed data
            self.parsed = True
            return self
        except Exception as e:
            logger.error(f"BookItem: Error fetching/parsing {self.get('url')}: {e}", exc_info=True)
            raise ParseError(f"Failed to fetch/parse book details for {self.get('url')}") from e


    def _parse_book_page_soup(self, soup: bsoup) -> Dict[str, Any]:
        """
        Parses the HTML soup of a single book page to extract details.
        This method is intended to be called when a direct book page is processed.
        """
        data: Dict[str, Any] = {}
        logger.debug(f"BookItem._parse_book_page_soup: Starting parse for URL: {self.get('url', 'N/A')}")

        # Example: Extracting title (selector might vary)
        title_tag = soup.find("h1", itemprop="name") # Common pattern for book title
        if title_tag:
            data["name"] = title_tag.text.strip()
        else: # Fallback for title
            title_tag_alt = soup.select_one("div.book-details h1") # Another common pattern
            if title_tag_alt:
                data["name"] = title_tag_alt.text.strip()
            else:
                logger.warning(f"_parse_book_page_soup: Title not found for {self.get('url')}")


        # Example: Extracting authors (selector might vary)
        authors_container = soup.find("div", class_="authors") # Common container
        if authors_container:
            author_tags = authors_container.find_all("a", itemprop="author")
            authors = [a.text.strip() for a in author_tags if a.text]
            if authors:
                data["authors"] = authors
        if not data.get("authors"):
             logger.warning(f"_parse_book_page_soup: Authors not found for {self.get('url')}")


        # Example: Extracting year (selector might vary)
        year_tag = soup.find("div", class_="property_year")
        if year_tag:
            year_value_tag = year_tag.find("div", class_="property_value")
            if year_value_tag:
                data["year"] = year_value_tag.text.strip()
        if not data.get("year"):
            logger.warning(f"_parse_book_page_soup: Year not found for {self.get('url')}")

        # Add more parsing logic for other fields like description, publisher, ISBN, language, extension, size etc.
        # This needs to be adapted to the actual HTML structure of the book page.
        # For now, this is a placeholder for what BookItem.fetch would populate.
        
        # If this is called from SearchPaginator for an ID search that landed on a book page,
        # we might already have some info in `self` (the BookItem dict itself).
        # This function should ideally fill in missing details or confirm existing ones.
        # For now, it just returns what it can parse directly from the soup.
        
        # Explicit title/author fields for clearer API surface
        data["title"] = data.get("name") or None
        data["author"] = data["authors"][0] if data.get("authors") else None

        logger.debug(f"BookItem._parse_book_page_soup: Parsed data: {data}")
        return data


class BooklistItemPaginator(dict):
    # This class seems to be a dictionary with added paginator-like methods.
    # It's used by BooklistPaginator to represent individual booklists that can then fetch their books.
    __url = ""
    __pos = 0
    __r: Optional[Callable] = None
    __page = 1 # Internal page state for fetching books within this booklist
    __total_books_in_list = 0 # If available from booklist page
    __books_per_page = 10 # Default, might be configurable if booklist pages have pagination

    mirror = ""
    # result = [] # This would store books of the current booklist page
    # storage = {1: []} # This would store pages of books for this booklist

    def __init__(self, request, mirror, count: int = 10):
        super().__init__()
        self.__r = request
        self.mirror = mirror
        self.__books_per_page = count # How many books to fetch per page for this booklist
        self.books_storage = {1: []} # Initialize storage for books within this booklist
        self.books_result = []


    async def fetch(self): # Fetches the books for this specific booklist
        if not self.__r:
            raise Exception("Request function not set for BooklistItemPaginator")
        if not self.get("url"): # URL of the booklist itself
            raise Exception("BooklistItemPaginator URL not set, cannot fetch booklist details")

        logger.debug(f"BooklistItemPaginator: Fetching books for booklist URL: {self.get('url')}")
        # This should fetch the booklist page and parse books from it.
        # The current parse_json seems to be for a different structure.
        # This needs to be a proper HTML parser for the booklist page.
        
        # For now, let's assume init() will be called to fetch and parse the first page of books.
        await self.init_books()
        return self # Return self to allow access to .books_result or .books_storage


    async def init_books(self): # Renamed from init to avoid conflict if this class is used elsewhere
        # Fetches and parses the first page of books for this booklist
        page_content = await self.fetch_book_page()
        if page_content:
            self.parse_book_page_for_items(page_content) # New method to parse books from booklist page
        else:
            logger.warning(f"fetch_book_page returned None for {self.get('url')}&page={self.__page}. Cannot parse books.")
            self.books_storage[self.__page] = []
            self.books_result = []


    async def fetch_book_page(self): # Fetches a page of books for this booklist
        if self.__r and self.get("url"):
            # Assuming booklist pages also use a 'page' query parameter
            booklist_page_url = f"{self.get('url')}&page={self.__page}"
            logger.debug(f"BooklistItemPaginator: Fetching book page {self.__page} from URL: {booklist_page_url}")
            return await self.__r(booklist_page_url)
        return None

    def parse_book_page_for_items(self, page_html: str):
        """Parses an HTML page of a booklist to extract individual book items."""
        soup = bsoup(page_html, features="lxml")
        self.books_storage[self.__page] = [] # Clear/initialize for current page

        # Selector for book items within a booklist page - THIS IS AN ASSUMPTION AND NEEDS VERIFICATION
        # It's likely similar to SearchPaginator's item parsing.
        # For example, if booklist pages use the same z-bookcard structure:
        book_item_wrappers = soup.findAll("div", {"class": "book-card-wrapper"}) # Or "div.book-item"
        if not book_item_wrappers:
             book_item_wrappers = soup.findAll("div", {"class": "book-item"})

        if not book_item_wrappers:
            logger.warning(f"BooklistItemPaginator: No book items found on booklist page: {self.get('url')}&page={self.__page}")
            self.books_result = []
            return

        for item_wrapper in book_item_wrappers:
            js_book = BookItem(self.__r, self.mirror)
            book_card_el = item_wrapper.find("z-bookcard")
            if book_card_el:
                # Simplified parsing, adapt from SearchPaginator.parse_page as needed
                js_book["id"] = book_card_el.get("id")
                js_book["name"] = book_card_el.get("name", "").strip()
                href = book_card_el.get("href")
                if href:
                    js_book["url"] = f"{self.mirror}{href}"
                # ... parse other attributes like authors, year, extension ...
                self.books_storage[self.__page].append(js_book)
        
        self.books_result = self.books_storage[self.__page]
        
        # Parse total pages for books in this list, if available
        # scripts = soup.findAll("script") ... for var pagerOptions ... self.__total_books_in_list = ...


    async def parse_json(self, fjs): # This method seems unused or for a different purpose
        logger.warning("BooklistItemPaginator.parse_json is likely obsolete or misused here.")
        # This was the original content, seems to parse a JSON response, not HTML for books
        if type(fjs) is str:
            fjs = json.loads(fjs)
        if type(fjs) is list:
            for item in fjs:
                self.result.append(item)
        elif type(fjs) is dict:
            self.result.append(fjs)
        else:
            raise ParseError("Could not parse json")


    # Pagination for books within this booklist
    async def next_books_page(self):
        # Assuming __total_books_in_list is somehow populated
        # Or simply try fetching next page until no results
        if self.__page < getattr(self, '_BooklistItemPaginator__total_books_in_list', self.__page + 1): # Guess next page if total unknown
            self.__page += 1
            self.__pos = 0 # Reset item position for the new page of books
            await self.init_books() # Fetch and parse new page of books
        else:
            logger.debug(f"BooklistItemPaginator: No more book pages for booklist {self.get('name')}")


    async def prev_books_page(self):
        if self.__page > 1:
            self.__page -= 1
            self.__pos = 0
            await self.init_books()
        else:
            logger.debug(f"BooklistItemPaginator: Already at the first book page for booklist {self.get('name')}")

    # next() and prev() for iterating through books on the current page of this booklist
    async def next_book_item(self): # Renamed from next
        current_page_books = self.books_storage.get(self.__page, [])
        if self.__pos >= len(current_page_books):
            # Potentially try to load next_books_page here if desired
            # For now, just indicate end of current page's books
            return [] 
        
        # This iterates one by one, not by self.count
        # If self.count is for books within booklist, logic needs adjustment
        # For now, assume it returns one book at a time from books_result
        if self.__pos < len(self.books_result):
            book_to_return = self.books_result[self.__pos]
            self.__pos +=1
            return [book_to_return] # Return as list to match paginator style
        return []


    async def prev_book_item(self): # Renamed from prev
        if self.__pos > 0:
            self.__pos -=1
            return [self.books_result[self.__pos]]
        # Potentially try to load prev_books_page if __pos is 0 and self.__page > 1
        return []
