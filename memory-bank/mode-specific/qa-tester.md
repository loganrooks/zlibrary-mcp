# QA Tester Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
### Test Execution: RAG Output Quality Re-evaluation - [2025-04-29 02:33:00]
- **Environment**: Local / **Build**: `60c0764`
- **Outcome**: PARTIAL
- **Summary**: PDF Text: PASS, PDF MD: PARTIAL/FAIL, EPUB MD: FAIL, EPUB Text: PASS. PDF noise significantly reduced. Markdown structure issues persist.
- **Bugs Found**: None explicitly logged, but quality gaps remain (Markdown structure).
- **Notes**: Re-evaluation following TDD refinements (commit `60c0764`). Confirmed PDF noise reduction success. Markdown structure (headings, lists, footnotes) remains a significant issue for both PDF and EPUB, not addressed by refinements. EPUB->Text conversion quality unchanged (acceptable).
- **Report Link**: `docs/rag-output-qa-report-rerun-20250429.md` (To be created)
### Test Execution: RAG Output Quality Evaluation - [2025-04-29 01:38:59]
- **Environment**: Local / **Build**: `d9e237e`
- **Outcome**: PARTIAL (See Report)
- **Summary**: Evaluated `process_document_for_rag` output (Markdown/Text) for PDF/EPUB against `docs/rag-output-quality-spec.md`. PDF outputs failed due to noise/formatting. EPUB Text passed, EPUB Markdown failed on formatting.
- **Bugs Found**: None explicitly logged, but multiple quality issues identified.
- **Notes**: Key issues: Lack of Markdown structure (headings, lists), inclusion of PDF headers/footers, non-standard footnote handling.
- **Report Link**: `docs/rag-output-qa-report.md`
## Test Plans
### Test Plan: E2E - Z-Library MCP Tools - [2025-05-06 13:10:00]
- **Objective**: To perform manual End-to-End (E2E) testing for all existing Z-Library MCP tools to ensure stability and correctness before release.
- **Scope**: All tools provided by the `zlibrary-mcp` server: `search_books`, `full_text_search`, `get_download_history`, `get_download_limits`, `download_book_to_file`, `process_document_for_rag`.
- **Prerequisites**:
    - Z-Library MCP server is running and accessible.
    - User has necessary credentials/access for Z-Library if required by the tools.
    - A sample book file (e.g., PDF, EPUB, TXT) available in the `downloads` directory or a known path for testing `process_document_for_rag`.
    - A known `bookDetails` object from a successful `search_books` call for testing `download_book_to_file`.
- **Associated Bugs**: None initially. Will be updated as testing progresses.
## Test Execution Results
### Test Execution: `full_text_search` No-Result Behavior - [2025-05-07 05:52:00]
- **Environment**: Local / **Build**: Current (as of 2025-05-07)
- **Outcome**: PASS
- **Summary**: Tested `full_text_search` tool with two queries designed to yield no results.
    - Query 1: "zxcvbnmasdfghjklqwertyuiop1234567890zxcvbnmasdfghjklqwertyuiop"
        - Observed Output: `{"retrieved_from_url":"...","books":[]}`
        - Status: PASS (Returned empty list as expected)
    - Query 2: "the epistemological ramifications of invisible pink unicorns in quantum chromodynamics"
        - Observed Output: `{"retrieved_from_url":"...","books":[]}`
        - Status: PASS (Returned empty list as expected)
- **Bugs Found**: None from this specific test. The behavior observed suggests that the previously reported issue FTS_TC006 (no-result queries returning unexpected books) might be resolved or behaves differently now.
- **Notes**: The tool correctly returned an empty list for both highly nonsensical and very specific unlikely queries. This is an improvement over the behavior noted in FTS_TC006 from the E2E test run on 2025-05-06.
- **Report Link**: N/A (Results documented in `attempt_completion`)
<!-- Append summaries of test runs using the format below -->

### Test Execution: E2E Z-Library MCP Tools - [2025-05-06 13:37:30]
- **Environment**: Local / **Build**: Current
- **Outcome**: PARTIAL
- **Summary**:
    - `search_books`: 8/11 PASS (Language filter (SB_TC005, SB_TC007) issues)
    - `full_text_search`: 4/9 PASS (Language (FTS_TC004), Extension (FTS_TC005), No-Result (FTS_TC006), single word with words=true (FTS_TC009) issues)
    - `get_download_history`: 5/5 PASS (Assuming empty history is correct)
    - `get_download_limits`: 1/1 PASS
    - `download_book_to_file`: 2/8 PASS (Core download functionality blocked by DBTF-BUG-001, only Zod validation tests passed)
    - `process_document_for_rag`: 0/7 SKIPPED (Blocked by DBTF-BUG-001)
- **Bugs Found**:
    - SB_TC005, SB_TC007: `search_books` language filter not applied correctly.
    - FTS_TC004: `full_text_search` language filter not applied correctly.
    - FTS_TC005: `full_text_search` extension filter not applied correctly.
    - FTS_TC006: `full_text_search` does not return empty for no-result queries.
    - FTS_TC009: `full_text_search` `words:true` does not override single-word phrase restriction.
    - DBTF-BUG-001: `download_book_to_file` - TypeError: AsyncZlib.download_book() got an unexpected keyword argument 'book_id'.
- **Notes**: Detailed test case results are in `memory-bank/feedback/qa-tester-feedback.md`. Several tools show issues with filter application. `download_book_to_file` has a critical regression.
- **Report Link**: `memory-bank/feedback/qa-tester-feedback.md` (entry [2025-05-06 13:18:00])

#### Tool: `search_books`
- **SB_TC001 (Happy Path - Basic Query)**
    - Description: Test basic search with a common query.
    - Input: `{"query": "philosophy"}`
    - Expected: Successful response with a list of books (default 10), each book having expected fields (title, author, etc.).
- **SB_TC002 (Happy Path - Query with Count)**
    - Description: Test search with a specific count.
    - Input: `{"query": "history", "count": 5}`
    - Expected: Successful response with 5 books.
- **SB_TC003 (Happy Path - Exact Match)**
    - Description: Test exact match search.
    - Input: `{"query": "The Republic Plato", "exact": true}`
    - Expected: Successful response, results should be highly relevant to "The Republic" by Plato.
- **SB_TC004 (Happy Path - Year Filter)**
    - Description: Test search with year filters.
    - Input: `{"query": "science", "fromYear": 2020, "toYear": 2023}`
    - Expected: Successful response, books published between 2020 and 2023.
- **SB_TC005 (Happy Path - Language Filter)**
    - Description: Test search with language filter.
    - Input: `{"query": "art", "language": ["english"]}`
    - Expected: Successful response, books primarily in English.
- **SB_TC006 (Happy Path - Extension Filter)**
    - Description: Test search with extension filter.
    - Input: `{"query": "cooking", "extensions": ["pdf"]}`
    - Expected: Successful response, books primarily in PDF format.
- **SB_TC007 (Happy Path - All Filters)**
    - Description: Test search with multiple filters combined.
    - Input: `{"query": "technology", "exact": false, "fromYear": 2021, "toYear": 2022, "language": ["english"], "extensions": ["epub"], "count": 3}`
    - Expected: Successful response with up to 3 English EPUB books on technology published between 2021-2022.
- **SB_TC008 (Edge Case - No Results)**
    - Description: Test search query that yields no results.
    - Input: `{"query": "asdfqwertzxcvasdf"}`
    - Expected: Successful response with an empty list of books or appropriate 'no results' message.
- **SB_TC009 (Error Condition - Missing Query)**
    - Description: Test search with missing required 'query' parameter.
    - Input: `{}`
    - Expected: Error response indicating 'query' is required (Zod validation error).
- **SB_TC010 (Error Condition - Invalid Param Type - Count)**
    - Description: Test search with invalid type for 'count'.
    - Input: `{"query": "math", "count": "five"}`
    - Expected: Error response indicating invalid type for 'count' (Zod validation error).
- **SB_TC011 (Edge Case - Query with Special Characters)**
    - Description: Test search with special characters in query.
    - Input: `{"query": "C++ programming!"}`
    - Expected: Successful response, handles special characters gracefully.

#### Tool: `full_text_search`
- **FTS_TC001 (Happy Path - Basic Query)**
    - Description: Test basic full-text search (phrase default).
    - Input: `{"query": "consciousness philosophy"}`
    - Expected: Successful response with books containing the phrase "consciousness philosophy".
- **FTS_TC002 (Happy Path - Words Match)**
    - Description: Test full-text search with `words=true`.
    - Input: `{"query": "artificial intelligence ethics", "words": true, "phrase": false}`
    - Expected: Successful response with books containing "artificial", "intelligence", "ethics" individually.
- **FTS_TC003 (Happy Path - Exact Match)**
    - Description: Test exact match for full-text search.
    - Input: `{"query": "theory of relativity", "exact": true}`
    - Expected: Successful response, results highly relevant to the exact phrase.
- **FTS_TC004 (Happy Path - Language Filter)**
    - Description: Test full-text search with language filter.
    - Input: `{"query": "quantum mechanics", "language": ["english"]}`
    - Expected: Successful response, English books containing "quantum mechanics".
- **FTS_TC005 (Happy Path - Extension Filter)**
    - Description: Test full-text search with extension filter.
    - Input: `{"query": "machine learning", "extensions": ["pdf"]}`
    - Expected: Successful response, PDF books containing "machine learning".
- **FTS_TC006 (Edge Case - No Results)**
    - Description: Test full-text search query that yields no results.
    - Input: `{"query": "supercalifragilisticexpialidocious content"}`
    - Expected: Successful response with an empty list of books or appropriate 'no results' message.
- **FTS_TC007 (Error Condition - Missing Query)**
    - Description: Test full-text search with missing required 'query' parameter.
    - Input: `{}`
    - Expected: Error response indicating 'query' is required (Zod validation error).
- **FTS_TC008 (Error Condition - Phrase Search Single Word)**
    - Description: Test phrase search with a single word (default phrase=true).
    - Input: `{"query": "ontology"}`
    - Expected: Error or specific behavior (e.g., word search). Schema: "requires at least 2 words".
- **FTS_TC009 (Happy Path - Phrase Search Single Word with words=true)**
    - Description: Test single word search when phrase is true but words is also true.
    - Input: `{"query": "epistemology", "words": true, "phrase": true}`
    - Expected: Successful response, searching for the word "epistemology".

#### Tool: `get_download_history`
- **GDH_TC001 (Happy Path - Default Count)**
    - Description: Test fetching download history with default count.
    - Input: `{}`
    - Expected: Successful response with up to 10 history items. (Recently fixed).
- **GDH_TC002 (Happy Path - Specific Count)**
    - Description: Test fetching download history with a specific count.
    - Input: `{"count": 5}`
    - Expected: Successful response with up to 5 history items.
- **GDH_TC003 (Edge Case - Count Zero)**
    - Description: Test fetching download history with count 0.
    - Input: `{"count": 0}`
    - Expected: Successful response, likely an empty list or default items. Behavior to note.
- **GDH_TC004 (Edge Case - Count Larger than History)**
    - Description: Test fetching download history with count larger than actual history.
    - Input: `{"count": 1000}`
    - Expected: Successful response with all available history items.
- **GDH_TC005 (Error Condition - Invalid Count Type)**
    - Description: Test with invalid type for 'count'.
    - Input: `{"count": "three"}`
    - Expected: Error response indicating invalid type for 'count' (Zod validation error).

#### Tool: `get_download_limits`
- **GDL_TC001 (Happy Path)**
    - Description: Test fetching download limits.
    - Input: `{}`
    - Expected: Successful response with download limit information.

#### Tool: `download_book_to_file`
- **DBTF_TC001 (Happy Path - Basic Download)**
    - Description: Test basic book download to default directory.
    - Input: `{"bookDetails": {<valid_bookDetails_object_from_search_books>}}`
    - Expected: Successful response with `file_path` to `./downloads/BOOK_ID.extension`. File valid. (Recently fixed).
- **DBTF_TC002 (Happy Path - Custom Output Directory)**
    - Description: Test book download to a custom output directory.
    - Input: `{"bookDetails": {<valid_bookDetails_object_from_search_books>}, "outputDir": "./custom_downloads"}`
    - Expected: Successful response with `file_path` to `./custom_downloads/BOOK_ID.extension`. Directory created.
- **DBTF_TC003 (Happy Path - Download and RAG Process - Text)**
    - Description: Test download and process for RAG (text output).
    - Input: `{"bookDetails": {<valid_bookDetails_object_epub_or_pdf>}, "process_for_rag": true, "processed_output_format": "text"}`
    - Expected: Successful response with `file_path` and `processed_file_path` (to .txt). Text extracted.
- **DBTF_TC004 (Happy Path - Download and RAG Process - Markdown)**
    - Description: Test download and process for RAG (markdown output).
    - Input: `{"bookDetails": {<valid_bookDetails_object_epub_or_pdf>}, "process_for_rag": true, "processed_output_format": "markdown"}`
    - Expected: Successful response with `file_path` and `processed_file_path` (to .md). Structured markdown.
- **DBTF_TC005 (Error Condition - Missing bookDetails)**
    - Description: Test download with missing required `bookDetails`.
    - Input: `{"outputDir": "./downloads"}`
    - Expected: Error response: `bookDetails` required (Zod validation error).
- **DBTF_TC006 (Error Condition - Invalid bookDetails type)**
    - Description: Test download with invalid `bookDetails` type.
    - Input: `{"bookDetails": "a_string_id"}`
    - Expected: Error response: invalid type for `bookDetails` (Zod validation error).
- **DBTF_TC007 (Error Condition - Invalid outputDir)**
    - Description: Test download with an invalid/unwritable output directory.
    - Input: `{"bookDetails": {<valid_bookDetails_object_from_search_books>}, "outputDir": "/non_existent_unwritable_path"}`
    - Expected: Error response: failure to save file.
- **DBTF_TC008 (Edge Case - RAG process without format)**
    - Description: Test RAG process with `process_for_rag: true` but no `processed_output_format`.
    - Input: `{"bookDetails": {<valid_bookDetails_object_epub_or_pdf>}, "process_for_rag": true}`
    - Expected: Behavior to note (default format or error). Schema: `processed_output_format` is optional.

#### Tool: `process_document_for_rag`
- **PDR_TC001 (Happy Path - PDF to Text)**
    - Description: Test processing a PDF file to text.
    - Input: `{"file_path": "downloads/sample.pdf", "output_format": "text"}` (Prereq: `downloads/sample.pdf` is valid PDF)
    - Expected: Successful response with `processed_file_path` (to .txt). Text extracted.
- **PDR_TC002 (Happy Path - EPUB to Markdown)**
    - Description: Test processing an EPUB file to markdown.
    - Input: `{"file_path": "downloads/sample.epub", "output_format": "markdown"}` (Prereq: `downloads/sample.epub` is valid EPUB)
    - Expected: Successful response with `processed_file_path` (to .md). Structured markdown.
- **PDR_TC003 (Happy Path - TXT to Text - Default Format)**
    - Description: Test processing a TXT file with default output format.
    - Input: `{"file_path": "downloads/sample.txt"}` (Prereq: `downloads/sample.txt` exists)
    - Expected: Successful response with `processed_file_path` (to .txt). Content similar/identical. Schema: `output_format` optional.
- **PDR_TC004 (Error Condition - Missing file_path)**
    - Description: Test processing with missing required `file_path`.
    - Input: `{"output_format": "text"}`
    - Expected: Error response: `file_path` required (Zod validation error).
- **PDR_TC005 (Error Condition - File Not Found)**
    - Description: Test processing with a non-existent file path.
    - Input: `{"file_path": "downloads/non_existent_file.pdf"}`
    - Expected: Error response: file not found or processing error.
- **PDR_TC006 (Error Condition - Invalid File Type for RAG)**
    - Description: Test processing an unsupported file type (e.g., image).
    - Input: `{"file_path": "downloads/sample_image.jpg"}` (Prereq: `downloads/sample_image.jpg` exists)
    - Expected: Error response: unsupported file type or processing failure.
- **PDR_TC007 (Error Condition - Invalid output_format)**
    - Description: Test processing with an invalid output_format.
    - Input: `{"file_path": "downloads/sample.pdf", "output_format": "xml"}`
    - Expected: Error response: invalid output format or processing failure.
### Test Plan: QA - RAG Markdown Output Quality - [2025-04-29 09:54:30]
- **Objective**: Evaluate the quality and spec adherence of Markdown output generated by the RAG processing pipeline (commit `e943016`).
- **Scope**: Markdown structure generated by `process_document_for_rag` with `output_format='markdown'` for PDF and EPUB inputs, compared against `docs/rag-markdown-generation-spec.md`.
- **Scenarios**:
    - Scenario 1: PDF Processing / Steps: Execute `process_document_for_rag` on `test_files/sample.pdf` with `output_format='markdown'`. Analyze output for headings, lists, footnotes, and general structure against spec. / Expected: Output adheres to Markdown structure defined in spec.
    - Scenario 2: EPUB Processing / Steps: Execute `process_document_for_rag` on `test_files/sample.epub` with `output_format='markdown'`. Analyze output for headings, lists, footnotes, and general structure against spec. / Expected: Output adheres to Markdown structure defined in spec.
- **Prerequisites**: Access to commit `e943016` environment, `test_files/sample.pdf`, `test_files/sample.epub`, and `docs/rag-markdown-generation-spec.md`.
- **Associated Bugs/Findings**: Feature failed QA. Detailed findings documented in `memory-bank/feedback/qa-tester-feedback.md` (entry [2025-04-29 09:52:00]).
<!-- Append new test plans (E2E, UAT, Integration, Exploratory) using the format below -->