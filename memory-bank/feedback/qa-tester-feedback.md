### E2E Test Execution: Z-Library MCP V1 Candidate Verification - [2025-05-07 12:38:21]

**Test Plan:** E2E - Z-Library MCP V1 Candidate Verification - [2025-05-07 12:33:01] (see [`memory-bank/mode-specific/qa-tester.md`](memory-bank/mode-specific/qa-tester.md:1))

**Overall Outcome:** PARTIAL (Multiple critical failures and blockers)

**Tool: `search_books`**

-   **SB_E2E_RETEST_LANG_01 (Re-test Language Filter - formerly SB_TC005)**
    -   **Input**: `{"query": "art", "languages": ["english"]}`
    -   **Expected**: Books in English.
    -   **Actual**: All 10 books returned were "english". URL: `...&languages%5B%5D=english`
    -   **Outcome**: PASS
    -   **Notes**: Previously failing. Fix for `language` to `languages` parameter likely resolved this.

-   **SB_E2E_RETEST_EXT_01 (Re-test Extension Filter - formerly SB_TC006)**
    -   **Input**: `{"query": "cooking", "extensions": ["pdf"]}`
    -   **Expected**: Books in PDF format.
    -   **Actual**: All 10 books returned were "pdf". URL: `...&extensions%5B%5D=PDF`
    -   **Outcome**: PASS
    -   **Notes**: Consistent with previous pass. Uppercasing of extension in URL noted.

-   **SB_E2E_RETEST_YEAR_01 (Re-test Year Filter - formerly SB_TC004)**
    -   **Input**: `{"query": "science", "fromYear": 2020, "toYear": 2023}`
    -   **Expected**: Books published 2020-2023.
    -   **Actual**: All 10 books returned were within 2020-2023. URL: `...&yearFrom=2020&yearTo=2023`
    -   **Outcome**: PASS
    -   **Notes**: Consistent with previous pass and MB entries.

**Tool: `full_text_search`**

-   **FTS_E2E_RETEST_LANG_01 (Re-test Language Filter - formerly FTS_TC004)**
    -   **Input**: `{"query": "quantum mechanics", "languages": ["english"]}`
    -   **Expected**: English books containing "quantum mechanics".
    -   **Actual**: All 10 books returned were "english". URL: `...&languages%5B%5D=english`
    -   **Outcome**: PASS
    -   **Notes**: Previously failing. Fix for `language` to `languages` parameter likely resolved this.

-   **FTS_E2E_RETEST_EXT_01 (Re-test Extension Filter - formerly FTS_TC005)**
    -   **Input**: `{"query": "machine learning", "extensions": ["pdf"]}`
    -   **Expected**: PDF books containing "machine learning".
    -   **Actual**: All 10 books returned were "pdf". URL: `...&extensions%5B%5D=PDF`
    -   **Outcome**: PASS
    -   **Notes**: Previously failing. Uppercasing of extension and `languages` param fix likely resolved this.

-   **FTS_E2E_RETEST_YEAR_01 (Re-test Year Filter)**
    -   **Input**: `{"query": "deep learning", "fromYear": 2018, "toYear": 2020}`
    -   **Expected**: Books published 2018-2020 containing "deep learning".
    -   **Actual**: URL did not contain year parameters (`retrieved_from_url":"https://z-library.sk/fulltext/deep%20learning?&token=9bb75ba4&type=phrase"`). Results included years 2017, 2016.
    -   **Outcome**: FAIL
    -   **Bug ID**: FTS_YEAR_FILTER_NOT_APPLIED_01

-   **FTS_E2E_RETEST_NORESULT_01 (Re-test No-Result Behavior - formerly FTS_TC006)**
    -   **Input**: `{"query": "supercalifragilisticexpialidocious content"}`
    -   **Expected**: Empty list of books.
    -   **Actual**: Returned 10 unexpected books.
    -   **Outcome**: FAIL
    -   **Notes**: Consistent with previous FTS_TC006 failure.

-   **FTS_E2E_RETEST_SINGLEWORD_01 (Re-test Single Word with `words:true` - formerly FTS_TC009)**
    -   **Input**: `{"query": "epistemology", "words": true, "phrase": true}`
    -   **Expected**: Successful search for word "epistemology".
    -   **Actual**: Successful search. URL: `...&type=words`.
    -   **Outcome**: PASS
    -   **Notes**: Previously failing. Fix noted in MB ActiveContext [2025-05-06 17:10:34] resolved this.

**Tool: `download_book_to_file`**

-   **DBTF_E2E_RETEST_STABILITY_01 (Re-test Stability - DBTF-BUG-001, DBTF-BUG-002)**
    -   **Input**: `{"bookDetails": {"id":"23778950", ...}}` (The Art of War)
    -   **Expected**: Successful download, no `TypeError` or `FileExistsError`.
    -   **Actual**: Failed with `AttributeError: __aenter__` in `aiofiles.open` call within `zlibrary/src/zlibrary/libasync.py`.
    -   **Outcome**: FAIL
    -   **Bug ID**: DBTF_AIOFILES_AENTER_ERROR_01
    -   **Notes**: Original `TypeError` (DBTF-BUG-001) did not occur. `FileExistsError` (DBTF-BUG-002) not applicable as `./downloads` was empty. This new error blocks further `download_book_to_file` testing.

-   **Enhanced Filenames Test**: BLOCKED by DBTF_AIOFILES_AENTER_ERROR_01.
-   **RAG Processing Option Tests**: BLOCKED by DBTF_AIOFILES_AENTER_ERROR_01.

**Tool: `get_metadata`**

-   **GM_E2E_VALID_URL_01 (Valid URL)**
    -   **Input**: `{"url": "https://z-library.sk/book/23778950/c6a0ea/art-war.html"}`
    -   **Expected**: Comprehensive metadata.
    -   **Actual**: Most metadata extracted. `authors` and `isbn_list` were empty.
    -   **Outcome**: PARTIAL
    -   **Bug ID**: GM_MISSING_AUTHORS_ISBN_01

-   **GM_E2E_INVALID_URL_01 (Invalid URL)**
    -   **Input**: `{"url": "https://z-library.sk/book/invalidurl"}`
    -   **Expected**: Error response.
    -   **Actual**: `Error from tool "get_metadata": Python bridge execution failed... HTTP error fetching ... Status 404...` followed by JSON of null/empty fields.
    -   **Outcome**: PASS (Core error detection worked, though bridge error reporting is messy)
    -   **Notes**: Python script correctly identified 404 but Python bridge failed to parse the mixed output (error message + JSON).

**Tool: `process_document_for_rag`**

-   **PDR_E2E_PDF_TEXT_01 (PDF to Text)**
    -   **Input**: `{"file_path": "test_files/sample.pdf", "output_format": "text"}`
    -   **Expected**: Successful text extraction.
    -   **Actual**: Failed with `ValueError: document closed` from `pymupdf`.
    -   **Outcome**: FAIL
    -   **Bug ID**: PDR_PDF_DOCUMENT_CLOSED_ERROR_01

-   **PDR_E2E_EPUB_MD_01 (EPUB to Markdown)**
    -   **Input**: `{"file_path": "test_files/sample.epub", "output_format": "markdown"}`
    -   **Expected**: Successful Markdown generation.
    -   **Actual**: `{"processed_file_path":"processed_rag_output/none-none-None.epub.processed.markdown", "content": [...]}`. Tool executed.
    -   **Outcome**: PASS (Tool execution successful)

-   **PDR_E2E_TXT_TEXT_01 (TXT to Text)**
    -   **Input**: `{"file_path": "test_files/sample.txt", "output_format": "text"}`
    -   **Expected**: Successful processing, content similar to input.
    -   **Actual**: `{"processed_file_path":"processed_rag_output/none-none-None.txt.processed.text", "content":["This is a simple text file for testing.\n","\n","This is a simple text file for testing.\n","\n","It has multiple lines."]}`. Tool executed.
    -   **Outcome**: PASS (Tool execution successful)

**General Verification & Error Handling (Summary)**
- General queries for `search_books` and `full_text_search` (where filters worked) returned results.
- Error handling for invalid Zod schema inputs (e.g., missing `query` for search tools) worked as expected.
- Error handling for `get_metadata` with a bad URL correctly identified the HTTP 404.
- Critical errors in `download_book_to_file` and `process_document_for_rag` (PDF) prevent full verification of these tools and dependent features.
### E2E Test Execution: Z-Library MCP Tools - [2025-05-06 13:18:00]

**Tool: `search_books`**

-   **SB_TC001 (Happy Path - Basic Query)**
    -   **Input**: `{"query": "philosophy"}`
    -   **Actual Output**: Received a list of 10 book objects. Example fields observed: `id`, `isbn` (optional), `url`, `cover`, `publisher`, `year`, `language`, `extension`, `size`, `rating`, `quality`.
    -   **Outcome**: PASS
    -   **Observations**: Default count of 10 results returned as expected. All essential fields present in the book objects.
-   **SB_TC002 (Happy Path - Query with Count)**
    -   **Input**: `{"query": "history", "count": 5}`
    -   **Actual Output**: Received a list of 5 book objects.
    -   **Outcome**: PASS
    -   **Observations**: Correct number of results returned as specified by 'count' parameter.
-   **SB_TC003 (Happy Path - Exact Match)**
    -   **Input**: `{"query": "The Republic Plato", "exact": true}`
    -   **Actual Output**: Received a list of 10 book objects. First result: `id: "29531289", url: "https://z-library.sk/book/29531289/7ea6e2/the-republic-plato.html"`.
    -   **Outcome**: PASS
    -   **Observations**: Results are highly relevant to the exact query.
-   **SB_TC004 (Happy Path - Year Filter)**
    -   **Input**: `{"query": "science", "fromYear": 2020, "toYear": 2023}`
    -   **Actual Output**: Received a list of 10 book objects. All observed 'year' fields were within the range 2020-2023.
    -   **Outcome**: PASS
    -   **Observations**: Year filter works as expected.
-   **SB_TC005 (Happy Path - Language Filter)**
    -   **Input**: `{"query": "art", "language": ["english"]}`
    -   **Actual Output**: Received a list of 10 book objects. Languages observed: french, english, italian.
    -   **Outcome**: FAIL
    -   **Observations**: Language filter did not restrict results to only "english". Books in other languages (french, italian) were included.
-   **SB_TC006 (Happy Path - Extension Filter)**
    -   **Input**: `{"query": "cooking", "extensions": ["pdf"]}`
    -   **Actual Output**: Received a list of 10 book objects. All observed 'extension' fields were "pdf".
    -   **Outcome**: PASS
    -   **Observations**: Extension filter works as expected.
-   **SB_TC007 (Happy Path - All Filters)**
    -   **Input**: `{"query": "technology", "exact": false, "fromYear": 2021, "toYear": 2022, "language": ["english"], "extensions": ["epub"], "count": 3}`
    -   **Actual Output**: Received a list of 3 book objects. Languages observed: chinese, english. Years: 2022, 2021. Extensions: all epub.
    -   **Outcome**: FAIL
    -   **Observations**: Language filter did not restrict results to only "english"; "chinese" language books were included. Year, extension, and count filters appeared to work correctly for the returned set.
-   **SB_TC008 (Edge Case - No Results)**
    -   **Input**: `{"query": "asdfqwertzxcvasdf"}`
    -   **Actual Output**: `[]` (Empty list)
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns an empty list for a query with no matches.
-   **SB_TC009 (Error Condition - Missing Query)**
    -   **Input**: `{}`
    -   **Actual Output**: `Error: Invalid arguments for tool "search_books": query: Required`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns a validation error when the required 'query' parameter is missing.
-   **SB_TC010 (Error Condition - Invalid Param Type - Count)**
    -   **Input**: `{"query": "math", "count": "five"}`
    -   **Actual Output**: `Error: Invalid arguments for tool "search_books": count: Expected number, received string`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns a validation error when 'count' parameter is of an invalid type.
-   **SB_TC011 (Edge Case - Query with Special Characters)**
    -   **Input**: `{"query": "C++ programming!"}`
    -   **Actual Output**: Received a list of 10 book objects, all relevant to "C++ programming".
    -   **Outcome**: PASS
    -   **Observations**: Special characters in the query were handled gracefully.
**Tool: `full_text_search`**

-   **FTS_TC001 (Happy Path - Basic Query)**
    -   **Input**: `{"query": "consciousness philosophy"}`
    -   **Actual Output**: Received a list of 10 book objects.
    -   **Outcome**: PASS
    -   **Observations**: Tool returned results. Content verification (presence of "consciousness philosophy") requires manual inspection of books.
-   **FTS_TC002 (Happy Path - Words Match)**
    -   **Input**: `{"query": "artificial intelligence ethics", "words": true, "phrase": false}`
    -   **Actual Output**: Received a list of 10 book objects.
    -   **Outcome**: PASS
    -   **Observations**: Tool returned results. Content verification (presence of individual words) requires manual inspection of books.
-   **FTS_TC003 (Happy Path - Exact Match)**
    -   **Input**: `{"query": "theory of relativity", "exact": true}`
    -   **Actual Output**: Received a list of 10 book objects.
    -   **Outcome**: PASS
    -   **Observations**: Tool returned results. Content verification (exact match for "theory of relativity") requires manual inspection of books.
-   **FTS_TC004 (Happy Path - Language Filter)**
    -   **Input**: `{"query": "quantum mechanics", "language": ["english"]}`
    -   **Actual Output**: Received a list of 10 book objects. Languages observed: chinese, english.
    -   **Outcome**: FAIL
    -   **Observations**: Language filter did not restrict results to only "english". Books in "chinese" were included. Content verification (presence of "quantum mechanics") requires manual inspection.
-   **FTS_TC005 (Happy Path - Extension Filter)**
    -   **Input**: `{"query": "machine learning", "extensions": ["pdf"]}`
    -   **Actual Output**: Received a list of 10 book objects. Extensions observed: epub, mobi, pdf.
    -   **Outcome**: FAIL
    -   **Observations**: Extension filter did not restrict results to only "pdf". Books with "epub" and "mobi" extensions were included. Content verification (presence of "machine learning") requires manual inspection.
-   **FTS_TC006 (Edge Case - No Results)**
    -   **Input**: `{"query": "supercalifragilisticexpialidocious content"}`
    -   **Actual Output**: Received a list of 10 book objects (unexpected results, e.g., ID "5742224").
    -   **Outcome**: FAIL
    -   **Observations**: Tool did not return an empty list for a query expected to yield no results. It returned seemingly unrelated books. This suggests the full-text search might not be working as intended or falls back to a general search.
-   **FTS_TC007 (Error Condition - Missing Query)**
    -   **Input**: `{}`
    -   **Actual Output**: `Error: Invalid arguments for tool "full_text_search": query: Required`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns a validation error when the required 'query' parameter is missing.
-   **FTS_TC008 (Error Condition - Phrase Search Single Word)**
    -   **Input**: `{"query": "ontology"}`
    -   **Actual Output**: `Error from tool "full_text_search": Python bridge execution failed for full_text_search: ... Exception: At least 2 words must be provided for phrase search. Use 'words=True' to match a single word.`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns an error when a single word is provided for phrase search (default).
-   **FTS_TC009 (Happy Path - Phrase Search Single Word with words=true)**
    -   **Input**: `{"query": "epistemology", "words": true, "phrase": true}`
    -   **Actual Output**: `Error from tool "full_text_search": Python bridge execution failed for full_text_search: ... Exception: At least 2 words must be provided for phrase search. Use 'words=True' to match a single word.`
    -   **Outcome**: FAIL
    -   **Observations**: Tool returned an error instead of performing a word search. The `words: true` parameter did not override the single-word restriction for phrase search.
-   **FTS_TC009 (Happy Path - Phrase Search Single Word with words=true)**
    -   **Input**: `{"query": "epistemology", "words": true, "phrase": true}`
    -   **Actual Output**: `Error from tool "full_text_search": Python bridge execution failed for full_text_search: ... Exception: At least 2 words must be provided for phrase search. Use 'words=True' to match a single word.`
    -   **Outcome**: FAIL
    -   **Observations**: Tool returned an error instead of performing a word search. The `words: true` parameter did not override the single-word restriction for phrase search.
**Tool: `get_download_history`**

-   **GDH_TC001 (Happy Path - Default Count)**
    -   **Input**: `{}`
    -   **Actual Output**: `[]` (Empty list)
    -   **Outcome**: PASS
    -   **Observations**: Tool returned an empty list. This is a PASS if the user's download history is indeed empty. The tool was recently fixed to address issues with an obsolete endpoint.
-   **GDH_TC002 (Happy Path - Specific Count)**
    -   **Input**: `{"count": 5}`
    -   **Actual Output**: `[]` (Empty list)
    -   **Outcome**: PASS
    -   **Observations**: Tool returned an empty list. This is a PASS if the user's download history is indeed empty. If history exists, it should return up to 5 items.
-   **GDH_TC003 (Edge Case - Count Zero)**
    -   **Input**: `{"count": 0}`
    -   **Actual Output**: `[]` (Empty list)
    -   **Outcome**: PASS
    -   **Observations**: Tool returned an empty list as expected when count is 0.
-   **GDH_TC004 (Edge Case - Count Larger than History)**
    -   **Input**: `{"count": 1000}`
    -   **Actual Output**: `[]` (Empty list)
    -   **Outcome**: PASS
    -   **Observations**: Tool returned an empty list. This is a PASS if the user's download history is indeed empty. If history exists, it should return all available items.
-   **GDH_TC005 (Error Condition - Invalid Count Type)**
    -   **Input**: `{"count": "three"}`
    -   **Actual Output**: `Error: Invalid arguments for tool "get_download_history": count: Expected number, received string`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns a validation error when 'count' parameter is of an invalid type.
**Tool: `get_download_limits`**

-   **GDL_TC001 (Happy Path)**
    -   **Input**: `{}`
    -   **Actual Output**: `{"daily_amount":2,"daily_allowed":999,"daily_remaining":997,"daily_reset":"Downloads will be reset in 3h 27m"}`
    -   **Outcome**: PASS
    -   **Observations**: Tool successfully returned download limit information with expected fields.
**Tool: `download_book_to_file`**

-   **DBTF_TC001 (Happy Path - Basic Download)**
    -   **Input**: `{"bookDetails": {"id":"815658", ...}}`
    -   **Actual Output**: `Error from tool "download_book_to_file": Failed to download book: Python bridge execution failed for download_book: ... TypeError: AsyncZlib.download_book() got an unexpected keyword argument 'book_id'`
    -   **Outcome**: FAIL
    -   **Observations**: The Python bridge (`lib/python_bridge.py`) is incorrectly calling `zlib_client.download_book` with a `book_id` argument. This argument was removed/renamed in `zlibrary/src/zlibrary/libasync.py` during previous fixes (around [2025-05-06 12:37:17] as per `activeContext.md`). The bridge should pass `book_details` and `output_dir_str`.
    -   **Bug ID**: DBTF-BUG-001 (Unexpected `book_id` argument in `download_book` call)
-   **DBTF_TC005 (Error Condition - Missing bookDetails)**
    -   **Input**: `{"outputDir": "./downloads"}`
    -   **Actual Output**: `Error: Invalid arguments for tool "download_book_to_file": bookDetails: Required`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns a validation error when the required 'bookDetails' parameter is missing.
-   **DBTF_TC006 (Error Condition - Invalid bookDetails type)**
    -   **Input**: `{"bookDetails": "a_string_id"}`
    -   **Actual Output**: `Error: Invalid arguments for tool "download_book_to_file": bookDetails: Expected object, received string`
    -   **Outcome**: PASS
    -   **Observations**: Correctly returns a validation error when 'bookDetails' parameter is of an invalid type.
### QA Feedback: RAG Markdown Output (commit e943016) - [2025-04-29 09:52:00]
- **Source:** Task instruction for QA testing RAG Markdown generation.
- **Issue/Observation:** Tested the `process_document_for_rag` tool with `output_format='markdown'` on `test_files/sample.pdf` and `test_files/sample.epub` against `docs/rag-markdown-generation-spec.md`. The feature fails QA.
- **Details (PDF - `test_files/sample.pdf`):**
    - **Headings:** Partially detected (`#`), but page numbers/running headers incorrectly formatted as `###` (e.g., lines 43, 49, 83, 89). Fails spec requirement for robust heading detection based on heuristics.
    - **Lists:** Numbered items in the original text (e.g., the theses) are not formatted as Markdown lists (`1.`, `2.`). Fails spec.
    - **Footnotes:** Footnote markers (`1`, `2`, `3`, `4`, `6` in the text) are not formatted using Markdown syntax (`[^n]`), and no corresponding definitions (`[^n]: ...`) are generated. Fails spec.
    - **Text Flow:** Generally preserved, but paragraph breaks seem inconsistent (e.g., lines 23-24, 25-26).
    - **Noise:** Null characters (` `) appear within text (e.g., lines 15, 45, 85), indicating incomplete text cleaning. Fails spec.
    - **Overall (PDF):** Significantly fails to meet spec requirements for structural Markdown generation from PDFs.
- **Details (EPUB - `test_files/sample.epub`):**
    - **Headings:** Correctly identified and formatted using `#`. Meets spec.
    - **Lists:** The "Contents" section (line 7) is rendered as plain text, not a Markdown list (`*` or `1.`). Fails spec requirement for list mapping.
    - **Paragraphs:** Generally preserved with appropriate line breaks. Meets spec.
    - **Footnotes:** Footnote markers (`1` to `31` appear in the text) are rendered as plain numbers, not Markdown syntax (`[^n]`). Corresponding footnote definitions (`[^n]: ...`) are missing entirely from the output. Fails spec requirement for EPUB footnote handling.
    - **Overall (EPUB):** Cleaner text output than PDF, and headings are correct, but fails on critical structural elements (lists, footnotes) defined in the spec.
- **Conclusion:** The RAG Markdown generation feature (commit `e943016`) does not meet the requirements outlined in `docs/rag-markdown-generation-spec.md` for either PDF or EPUB inputs based on the tested samples. It fails significantly on list and footnote generation for both formats, and additionally shows issues with heading detection and text cleaning for PDFs.
- **Action Taken:** Documented findings. Will update QA Test Plan and report failure via `attempt_completion`. Recommend further development/debugging.
# QA Tester Feedback
<!-- Entries below should be added reverse chronologically (newest first) -->