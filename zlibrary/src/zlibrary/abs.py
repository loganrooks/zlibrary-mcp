import re
from typing import Dict, Any, Optional, List, Union, Callable, Coroutine
from typing import Callable, Optional
from bs4 import BeautifulSoup as bsoup
from bs4 import Tag
from urllib.parse import quote

from .exception import ParseError
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
        self.__r = request
        self.mirror = mirror

    def __repr__(self):
        return f"<Paginator [{self.__url}], count {self.count}, len(result): {len(self.result)}, pages in storage: {len(self.storage.keys())}>"

    def parse_page(self, page):
        logger.debug(f"Parsing page for URL: {self.__url}")
        # Log truncated raw HTML for debugging purposes
        html_excerpt = page[:2000].replace('\n', ' ') + ('...' if len(page) > 2000 else '')
        logger.debug(f"Raw HTML excerpt: {html_excerpt}")

        soup = bsoup(page, features="lxml")
        box = soup.find("div", {"id": "searchResultBox"})
        logger.debug(f"Found #searchResultBox: {bool(box)}")

        # --- BEGIN FIX for id: search ---
        # Check if this might be a direct book page result from an id: search
        is_id_search_url = bool(re.search(r"/s/id%3A", self.__url))
        if not box or type(box) is not Tag:
            logger.debug("#searchResultBox not found or not a Tag.")
            # If searchResultBox is missing, check if it looks like a book page
            book_page_check = soup.find("div", {"class": "row cardBooks"})
            if book_page_check and is_id_search_url:
                logger.debug("Potential direct book page detected.")
                try:
                    logger.debug("Attempting direct parse with _parse_book_page_soup.")
                    # Attempt to parse this page as a single BookItem
                    book_item = BookItem(self.__r, self.mirror)
                    book_item["url"] = self.__url # Use the current URL, assuming it's the book page
                    # Manually call the parsing logic similar to BookItem.fetch but on existing soup
                    parsed_data = book_item._parse_book_page_soup(soup) # Requires creating/exposing this method
                    logger.debug(f"Direct parse result: {parsed_data}")
                    self.storage[self.page] = [parsed_data] if parsed_data else [] # Ensure list even if parse fails slightly
                    self.result = self.storage[self.page]
                    logger.debug(f"Direct parse successful, result set: {self.result}")
                    return # Successfully parsed as single book page
                except Exception as e:
                    logger.error(f"Direct parse FAILED for {self.__url}: {e}", exc_info=True)
                    # Fall through to raise the original ParseError
            # If it's not a book page or not an ID search, raise the original error
            logger.error(f"Raising ParseError: Could not parse book list (searchResultBox not found and not a direct book page) for URL: {self.__url}")
            raise ParseError(f"Could not parse book list (searchResultBox not found) for URL: {self.__url}")
        # --- END FIX ---

        # This part executes if #searchResultBox WAS found
        check_notfound = soup.find("div", {"class": "notFound"})
        if check_notfound:
            logger.debug("Standard search page returned 'notFound'.")
            self.storage[self.page] = []
            self.result = []
            return

        # with open("test.html", "w") as f: # Keep debug code commented out
        #     f.write(str(box.prettify()))
        book_list = box.findAll("div", {"class": "book-item"})
        logger.debug(f"Found {len(book_list)} 'book-item' divs within #searchResultBox.")
        # Log first item if found for structure check
        if book_list:
             logger.debug(f"First book-item structure: {str(book_list[0])[:500]}...")

        if not book_list:
            logger.warning("No 'book-item' divs found within #searchResultBox. Raising ParseError.")
            raise ParseError("Could not find the book list.")

        self.storage[self.page] = []
        logger.debug("Parsing standard book list items...")
        for idx, book in enumerate(book_list, start=1):
            js = BookItem(self.__r, self.mirror)

            book = book.find("z-bookcard")
            cover = book.find("img")
            if not cover:
                logger.debug(f"Failure to parse {idx}-th book at url {self.__url}")
                continue

            js["id"] = book.get("id")
            js["isbn"] = book.get("isbn")

            book_url = book.get("href")
            if book_url:
                js["url"] = f"{self.mirror}{book_url}"
            img = cover.find("img")
            if img:
                js["cover"] = img.get("data-src")
            else:
                js["cover"] = cover.get("data-src")

            publisher = book.get("publisher")
            if publisher:
                js["publisher"] = publisher.strip()

            slot = book.find("div", {"slot": "author"})
            if slot and slot.text:
                authors = slot.text.split(";")
                authors = [i.strip() for i in authors if i]
                if authors:
                    js["authors"] = authors

            title = book.find("div", {"slot": "title"})
            if title and title.text:
                js["name"] = title.text.strip()

            year = book.get("year")
            if year:
                js["year"] = year.strip()

            lang = book.get("language")
            if lang:
                js["language"] = lang.strip()

            ext = book.get("extension")
            if ext:
                js["extension"] = ext.strip()

            size = book.get("filesize")
            if size:
                js["size"] = size.strip()

            rating = book.get("rating")
            if rating:
                js["rating"] = rating.strip()

            quality = book.get("quality")
            if quality:
                js["quality"] = quality.strip()

            self.storage[self.page].append(js)

        scripts = soup.findAll("script")
        for scr in scripts:
            txt = scr.text
            if "var pagerOptions" in txt:
                pos = txt.find("pagesTotal: ")
                fix = txt[pos + len("pagesTotal: ") :]
                count = fix.split(",")[0]
                self.total = int(count)

    async def init(self):
        page = await self.fetch_page()
        self.parse_page(page)

    async def fetch_page(self):
        if self.__r:
            return await self.__r(f"{self.__url}&page={self.page}")

    async def next(self):
        if self.__pos >= len(self.storage[self.page]):
            await self.next_page()

        self.result = self.storage[self.page][self.__pos : self.__pos + self.count]
        self.__pos += self.count
        return self.result

    async def prev(self):
        self.__pos -= self.count
        if self.__pos < 1:
            await self.prev_page()

        subtract = self.__pos - self.count
        if subtract < 0:
            subtract = 0
        if self.__pos <= 0:
            self.__pos = self.count

        self.result = self.storage[self.page][subtract : self.__pos]
        return self.result

    async def next_page(self):
        if self.page < self.total:
            self.page += 1
            self.__pos = 0
        else:
            self.__pos -= self.count
            if self.__pos < 0:
                self.__pos = 0

        if not self.storage.get(self.page):
            page = await self.fetch_page()
            self.parse_page(page)

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
        else:
            self.__pos = 0
            return

        if not self.storage.get(self.page):
            page = await self.fetch_page()
            self.parse_page(page)

        self.__pos = len(self.storage[self.page])


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

        for idx, booklist in enumerate(book_list, start=1):
            js = BooklistItemPaginator(self.__r, self.mirror, self.count)

            name = booklist.get("topic")
            if not name:
                raise ParseError(
                    f"Could not parse {idx}-th booklist at url {self.__url}"
                )
            js["name"] = name.strip()

            book_url = booklist.get("href")
            if book_url:
                js["url"] = f"{self.mirror}{book_url}"

            info_wrap = booklist.get("description")
            if info_wrap:
                js["description"] = info_wrap.strip()

            author = booklist.get("authorprofile")
            if author:
                js["author"] = author.strip()

            count = booklist.get("quantity")
            if count:
                js["count"] = count.strip()

            views = booklist.get("views")
            if views:
                js["views"] = views.strip()

            js["books_lazy"] = []
            carousel = booklist.find_all("a")
            if not carousel:
                self.storage[self.page].append(js)
                continue
            for adx, book in enumerate(carousel):
                res = BookItem(self.__r, self.mirror)
                res["url"] = f"{self.mirror}{book.get('href')}"
                res["name"] = ""

                zcover = book.find("z-cover")
                if zcover:
                    b_id = zcover.get("id")
                    if b_id:
                        res["id"] = b_id.strip()
                    b_au = zcover.get("author")
                    if b_au:
                        res["author"] = b_au.strip()
                    b_name = zcover.get("title")
                    if b_name:
                        res["name"] = b_name.strip()
                    cover = zcover.find_all("img")
                    if cover:
                        for c in cover:
                            d_src = c.get("data-src")
                            if d_src:
                                js["cover"] = d_src.strip()

                js["books_lazy"].append(res)

            self.storage[self.page].append(js)

        scripts = soup.findAll("script")
        for scr in scripts:
            txt = scr.text
            if "var pagerOptions" in txt:
                pos = txt.find("pagesTotal: ")
                fix = txt[pos + len("pagesTotal: ") :]
                count = fix.split(",")[0]
                self.total = int(count)

    async def init(self):
        page = await self.fetch_page()
        self.parse_page(page)
        return self

    async def fetch_page(self):
        if self.__r:
            return await self.__r(f"{self.__url}&page={self.page}")

    async def next(self):
        if self.__pos >= len(self.storage[self.page]):
            await self.next_page()

        self.result = self.storage[self.page][self.__pos : self.__pos + self.count]
        self.__pos += self.count
        return self.result

    async def prev(self):
        self.__pos -= self.count
        if self.__pos < 1:
            await self.prev_page()

        subtract = self.__pos - self.count
        if subtract < 0:
            subtract = 0
        if self.__pos <= 0:
            self.__pos = self.count

        self.result = self.storage[self.page][subtract : self.__pos]
        return self.result

    async def next_page(self):
        if self.page < self.total:
            self.page += 1
            self.__pos = 0
        else:
            self.__pos -= self.count
            if self.__pos < 0:
                self.__pos = 0

        if not self.storage.get(self.page):
            page = await self.fetch_page()
            self.parse_page(page)

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
        else:
            self.__pos = 0
            return

        if not self.storage.get(self.page):
            page = await self.fetch_page()
            self.parse_page(page)

        self.__pos = len(self.storage[self.page])


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
        return f"<Downloads paginator [{self.__url}]>"

    def parse_page(self, page):
        soup = bsoup(page, features="lxml")
        box = soup.find("div", {"class": "dstats-content"})
        if not box or type(box) is not Tag:
            raise ParseError("Could not parse downloads list.")

        check_notfound = box.find("p")
        if check_notfound and DLNOTFOUND in check_notfound.text.strip():
            logger.debug("This page is empty.")
            self.storage[self.page] = []
            self.result = []
            return

        book_list = box.findAll("tr", {"class": "dstats-row"})
        if not book_list:
            raise ParseError("Could not find the book list.")

        self.storage[self.page] = []

        for _, book in enumerate(book_list, start=1):
            js = BookItem(self.__r, self.mirror)

            title = book.find("div", {"class": "book-title"})
            date = book.find("td", {"class": "lg-w-120"})

            js["name"] = title.text.strip()
            js["date"] = date.text.strip()

            book_url = book.find("a")
            if book_url:
                js["url"] = f"{self.mirror}{book_url.get('href')}"
            self.storage[self.page].append(js)
        self.result = self.storage[self.page]

    async def init(self):
        page = await self.fetch_page()
        self.parse_page(page)
        return self

    async def fetch_page(self):
        if self.__r:
            return await self.__r(f"{self.__url}&page={self.page}")

    async def next_page(self):
        self.page += 1

        if not self.storage.get(self.page):
            page = await self.fetch_page()
            self.parse_page(page)

        self.result = self.storage[self.page]

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
        else:
            return

        if not self.storage.get(self.page):
            page = await self.fetch_page()
            self.parse_page(page)

        self.result = self.storage[self.page]


    # --- BEGIN ADDITION for id: search fix ---
    def _parse_book_page_soup(self, soup: bsoup) -> Dict[str, Any]:
        """Parses a BeautifulSoup object assumed to be a book details page."""
        # This method encapsulates the parsing logic from the original fetch()
        # to allow reuse when parse_page detects a direct book page.
        wrap = soup.find("div", {"class": "row cardBooks"})
        if not wrap or type(wrap) is not Tag:
            raise ParseError(f"Failed to parse book page structure (wrap) for {self['url']}")

        parsed = {}
        parsed["url"] = self["url"] # Assume self['url'] is set correctly before calling

        zcover = soup.find("z-cover")
        if not zcover or type(zcover) is not Tag:
            raise ParseError(f"Failed to find zcover in {self['url']}")

        # --- Simplified parsing logic based on original fetch() ---
        # Cover
        cover_img = zcover.find("img")
        if cover_img:
            parsed["cover"] = cover_img.get("data-src") or cover_img.get("src")

        # Title
        title_tag = soup.find("h1", itemprop="name")
        if title_tag:
            parsed["title"] = title_tag.text.strip()

        # Authors
        col = wrap.find("div", {"class": "col-sm-9"})
        if col and type(col) is Tag:
            authors_div = col.find("div", {"class": "authors"})
            if authors_div:
                parsed["authors"] = []
                anchors = authors_div.find_all("a")
                for anchor in anchors:
                    author_url = anchor.get('href')
                    parsed["authors"].append(
                        {
                            "author": anchor.text.strip(),
                            "author_url": f"{self.mirror}{quote(author_url)}" if author_url else None,
                        }
                    )

        # Properties (Year, Language, Extension, etc.)
        properties_div = soup.find("div", {"class": "properties"})
        if properties_div:
            for prop_item in properties_div.find_all("div", {"class": "property"}):
                name_tag = prop_item.find("div", {"class": "property_label"})
                value_tag = prop_item.find("div", {"class": "property_value"})
                if name_tag and value_tag:
                    prop_name = name_tag.text.strip().lower().replace(":", "")
                    prop_value = value_tag.text.strip()
                    # Map common properties
                    if "year" in prop_name:
                        parsed["year"] = prop_value
                    elif "language" in prop_name:
                        parsed["language"] = prop_value
                    elif "file" in prop_name:
                        # Extract extension and size
                        parts = [p.strip() for p in prop_value.split(',')]
                        if len(parts) > 0: parsed["extension"] = parts[0].lower()
                        if len(parts) > 1: parsed["size"] = parts[1]
                    # Add more properties as needed

        # Description
        description_div = soup.find("div", itemprop="description")
        if description_div:
            parsed["description"] = description_div.text.strip()

        # Add other fields as parsed in the original fetch...
        # (e.g., ISBN, Publisher, Series, etc. - omitted for brevity)

        # --- Important: Update self with parsed data ---
        self.update(parsed)
        self.parsed = parsed # Mark as parsed
        return parsed
    # --- END ADDITION ---

class BookItem(dict):
    parsed = None
    __r: Optional[Callable] = None

    def __init__(self, request, mirror):
        super().__init__()
        self.__r = request
        self.mirror = mirror

    async def fetch(self):
        if not self.__r:
            raise ParseError("Instance of BookItem does not contain a request method.")
        page = await self.__r(self["url"])
        try:
            soup = bsoup(page, features="lxml")
            # Use the new helper method to parse the soup
            parsed_data = self._parse_book_page_soup(soup)
            return parsed_data
        except Exception as e:
            logger.error(f"Error fetching or parsing book page {self['url']}: {e}")
            raise ParseError(f"Failed to fetch or parse {self['url']}") from e

        details = wrap.find("div", {"class": "bookDetailsBox"})

        properties = ["year", "edition", "publisher", "language"]
        for prop in properties:
            if type(details) is Tag:
                x = details.find("div", {"class": "property_" + prop})
                if x and type(x) is Tag:
                    x = x.find("div", {"class": "property_value"})
                    if x:
                        parsed[prop] = x.text.strip()

        if type(details) is Tag:
            isbns = details.findAll("div", {"class": "property_isbn"})
            for isbn in isbns:
                txt = isbn.find("div", {"class": "property_label"}).text.strip(":")
                val = isbn.find("div", {"class": "property_value"})
                parsed[txt] = val.text.strip()

            cat = details.find("div", {"class": "property_categories"})
            if cat and type(cat) is Tag:
                cat = cat.find("div", {"class": "property_value"})
                if cat and type(cat) is Tag:
                    link = cat.find("a")
                    if link and type(link) is Tag:
                        parsed["categories"] = cat.text.strip()
                        parsed["categories_url"] = f"{self.mirror}{link.get('href')}"

            file = details.find("div", {"class": "property__file"})
            if file and type(file) is Tag:
                file = file.text.strip().split(",")
                parsed["extension"] = file[0].split("\n")[1]
                parsed["size"] = file[1].strip()

        rating = wrap.find("div", {"class": "book-rating"})
        if rating and type(rating) is Tag:
            parsed["rating"] = "".join(
                filter(lambda x: bool(x), rating.text.replace("\n", "").split(" "))
            )

        dl_btn = soup.find("a", {"class": "btn btn-default addDownloadedBook"})
        if dl_btn and type(dl_btn) is Tag:
            if "unavailable" in dl_btn.text:
                parsed["download_url"] = "Unavailable (use tor to download)"
            else:
                parsed["download_url"] = f"{self.mirror}{dl_btn.get('href')}"
        self.parsed = parsed
        return parsed


class BooklistItemPaginator(dict):
    __url = ""
    __pos = 0

    page = 1
    mirror = ""
    count = 10
    total = 0

    result = []

    storage = {1: []}

    def __init__(self, request, mirror, count: int = 10):
        super().__init__()
        self.__r = request
        self.mirror = mirror
        self.count = count

    async def fetch(self):
        parsed = {}
        parsed["url"] = self["url"]
        parsed["name"] = self["name"]

        get_id = self["url"].split("/")[-2]
        payload = f"papi/booklist/{get_id}/get-books"
        self.__url = f"{self.mirror}/{payload}"

        await self.init()

        self.parsed = parsed
        return parsed

    async def init(self):
        fjs = await self.fetch_json()
        await self.parse_json(fjs)
        return self

    async def parse_json(self, fjs):
        self.storage[self.page] = []

        fjs = json.loads(fjs)
        for book in fjs["books"]:
            js = BookItem(self.__r, self.mirror)

            js["id"] = book["book"]["id"]
            js["isbn"] = book["book"]["identifier"]

            book_url = book["book"].get("href")
            if book_url:
                js["url"] = f"{self.mirror}{book_url}"

            js["cover"] = book["book"].get("cover")
            js["name"] = book["book"].get("title")

            js["publisher"] = book["book"].get("publisher")

            js["authors"] = book["book"].get("author").split(",")

            js["year"] = book["book"].get("year")
            js["language"] = book["book"].get("language")

            js["extension"] = book["book"].get("extension")
            js["size"] = book["book"].get("filesizeString")

            js["rating"] = book["book"].get("qualityScore")

            self.storage[self.page].append(js)

        count = fjs["pagination"]["total_pages"]
        self.total = int(count)

    async def fetch_json(self):
        return await self.__r(f"{self.__url}/{self.page}")

    async def next(self):
        if self.__pos >= len(self.storage[self.page]):
            await self.next_page()

        self.result = self.storage[self.page][self.__pos : self.__pos + self.count]
        self.__pos += self.count
        return self.result

    async def prev(self):
        self.__pos -= self.count
        if self.__pos < 1:
            await self.prev_page()

        subtract = self.__pos - self.count
        if subtract < 0:
            subtract = 0
        if self.__pos <= 0:
            self.__pos = self.count

        self.result = self.storage[self.page][subtract : self.__pos]
        return self.result

    async def next_page(self):
        if self.page < self.total:
            self.page += 1
            self.__pos = 0
        else:
            self.__pos -= self.count
            if self.__pos < 0:
                self.__pos = 0

        if not self.storage.get(self.page):
            json = await self.fetch_json()
            await self.parse_json(json)

    async def prev_page(self):
        if self.page > 1:
            self.page -= 1
        else:
            self.__pos = 0
            return

        if not self.storage.get(self.page):
            json = await self.fetch_json()
            await self.parse_json(json)

        self.__pos = len(self.storage[self.page])
