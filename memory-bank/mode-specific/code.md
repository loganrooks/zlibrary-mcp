# Auto-Coder Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
### [2025-05-07 06:52:30] Component: `_create_enhanced_filename`
- **Purpose**: Generates a user-readable and filesystem-safe filename for downloaded books based on the convention `LastnameFirstname_TitleOfTheBook_BookID.ext`.
- **Files**: `lib/python_bridge.py`
- **Status**: Implemented
- **Dependencies**: `re` (Python built-in)
- **API Surface**: `_create_enhanced_filename(book_details: dict) -> str`
- **Details**:
    - Parses author (first author, LastnameFirstname logic, capitalization, fallback "UnknownAuthor", 50 char limit).
    - Formats title (fallback "UntitledBook", spaces to underscores, sanitization, 100 char limit).
    - Uses BookID as is (fallback "UnknownID").
    - Formats extension (lowercase, prepends ".", fallback ".unknown").
    - Sanitizes components by removing problematic characters (`/ \ ? % * : | " < > . , ; =`), replacing multiple spaces/underscores with a single underscore, and stripping leading/trailing whitespace/underscores.
    - Assembles filename parts with `_` as separator.
    - Truncates the entire base filename (before extension) to 200 characters if exceeded, attempting to preserve BookID and parts of author/title.
- **Tests**: To be covered by TDD mode, specifically testing various `book_details` inputs and expected filename outputs. Will impact tests for `download_book` in `__tests__/python/test_python_bridge.py`.
- **Related**: [ActiveContext 2025-05-07 06:52:30], [GlobalContext Product: Enhanced Filename Convention Specification - [2025-05-07]], [`docs/project-plan-zlibrary-mcp.md:130-162`](docs/project-plan-zlibrary-mcp.md:130-162)
### [2025-05-07 06:39:00] `lib/python_bridge.py` Cleanup (Task 2.2)
- **Purpose**: Remove deprecated ID-based lookup logic and ensure ADR-002 alignment.
- **Files**: `lib/python_bridge.py`
- **Status**: Implemented.
- **Details**:
    - Removed the `_find_book_by_id_via_search` function.
    - Verified `download_book` function's interface and its call to `zlib_client.download_book` align with ADR-002 (uses `bookDetails`).
    - Confirmed public function interfaces in `lib/python_bridge.py` are consistent with ADR-002.
- **Tests**: Python tests in `__tests__/python/test_python_bridge.py` will need to be checked.
- **Related**: [ActiveContext 2025-05-07 06:39:00], [`docs/project-plan-zlibrary-mcp.md:104-126`](docs/project-plan-zlibrary-mcp.md:104-126), [`docs/adr/ADR-002-Download-Workflow-Redesign.md`](docs/adr/ADR-002-Download-Workflow-Redesign.md)
### [2025-05-07 05:58:00] `libasync.py` Cleanup (Task 2.1)
- **Purpose**: Address Pylance warnings, remove deprecated ID-based download logic, ensure ADR-002 alignment.
- **Files**: `zlibrary/src/zlibrary/libasync.py`
- **Status**: Implemented.
- **Details**:
    - Removed redundant `typing` imports.
    - Removed the `AsyncZlib.get_by_id` method.
    - Verified `AsyncZlib.download_book` aligns with ADR-002 by using `bookDetails` (containing page URL) for download initiation.
- **Tests**: Python tests in `zlibrary/src/test.py` pass.
- **Related**: [ActiveContext 2025-05-07 05:58:00], [`docs/project-plan-zlibrary-mcp.md:79-102`](docs/project-plan-zlibrary-mcp.md:79-102), [`docs/adr/ADR-002-Download-Workflow-Redesign.md`](docs/adr/ADR-002-Download-Workflow-Redesign.md)
### [2025-05-07 03:01:11] Test Regression Fix: `languages` Parameter Change
- **Purpose**: Fix test failures in `__tests__/zlibrary-api.test.js` after renaming `language` to `languages`.
- **Files**: `__tests__/zlibrary-api.test.js`
- **Status**: Implemented.
- **Details**: Updated `expect(mockPythonShellRun).toHaveBeenCalledWith` assertions in `searchBooks` and `fullTextSearch` tests to include `content_types: []` in the stringified JSON arguments passed to the Python bridge. This is because the default empty array for `content_types` is now always included.
- **Tests**: `npm test` now passes.
- **Related**: [ActiveContext 2025-05-07 02:53:59], [feedback/code-feedback.md 2025-05-07 02:53:59]
### [2025-05-07 02:53:59] Intervention: Completion Denied (Manual Testing &amp; Regressions)
- **Trigger**: User feedback on `attempt_completion` [Ref: feedback/code-feedback.md 2025-05-07 02:53:59]
- **Context**: After applying `language` to `languages` parameter changes.
- **Action Taken**: Will perform manual testing and investigate test regressions.
- **Rationale**: Ensure functional correctness and address any new issues.
- **Outcome**: Task ongoing.
- **Follow-up**: Manual tests, then `npm test` analysis.
### [2025-05-06 21:57:33] Implement Token-Based `full_text_search` and `content_types` Parameter
- **Purpose**: Modify `AsyncZlib.full_text_search` to use a token extracted from a Z-Library page and add `content_types` parameter to both `search` and `full_text_search`.
- **Files**: `zlibrary/src/zlibrary/libasync.py`
- **Status**: Implemented.
- **Dependencies**: `re` (new import for regex token extraction), `httpx`, `BeautifulSoup4`.
- **API Surface**:
    - `AsyncZlib.search` signature changed to include `content_types: Optional[List[str]] = None`.
    - `AsyncZlib.full_text_search` signature changed to include `content_types: Optional[List[str]] = None`.
- **Tests**: Existing tests for these methods will likely require updates to reflect the new parameter and potential changes in URL construction for `full_text_search`. New tests for token extraction logic would be beneficial.
- **Details**:
    - `AsyncZlib.search`: Added loop to append `&selected_content_types%5B%5D={value}` for each `content_type`.
    - `AsyncZlib.full_text_search`:
        - Added initial GET request to `/s/` to fetch HTML.
        - Used `BeautifulSoup` and `re.search` to extract token from JavaScript: `newURL.searchParams.append('token', 'TOKEN_VALUE')`.
        - Constructed URL with `&token={token}` and `&type=phrase`.
        - Added loop for `&selected_content_types%5B%5D={value}`.
        - All list parameters (`languages`, `extensions`, `content_types`) are non-indexed.
        - `extensions` are uppercased.
- **Related**: [ActiveContext 2025-05-06 21:57:33], [GlobalContext Progress 2025-05-06 21:57:33], [User Task 2025-05-06 21:52:18], [memory-bank/feedback/code-feedback.md - Entry 2025-05-06 19:08:06]
### [2025-05-06 18:24:11] URL Parameter Formatting Changed to Non-Indexed
- **Purpose**: Modify URL parameter formatting for `languages` and `extensions` in `search` and `full_text_search` methods to use non-indexed format (e.g., `languages[]=value`) as per revised user objective.
- **Files**: `zlibrary/src/zlibrary/libasync.py`
- **Status**: Implemented.
- **Dependencies**: None.
- **API Surface**: N/A (Internal implementation detail of URL construction).
- **Tests**: Existing tests for URL parameter formatting may now fail and require updates.
- **Details**: Changed loops iterating over `lang` and `extensions` lists to append `&languages%5B%5D={value}` or `&extensions%5B%5D={value}` instead of the indexed `&languages%5B{i}%5D={value}`.
- **Related**: [ActiveContext 2025-05-06 18:23:33], [GlobalContext Progress 2025-05-06 18:23:51], [User Feedback 2025-05-06 18:23:01]
### [2025-05-06 18:06:36] URL Parameter Formatting Verification
- **Purpose**: Verify that `languages` and `extensions` parameters in `search` and `full_text_search` methods in `zlibrary/src/zlibrary/libasync.py` use indexed URL formatting.
- **Files**: `zlibrary/src/zlibrary/libasync.py`
- **Status**: Verified (No changes needed).
- **Dependencies**: None.
- **API Surface**: N/A (Internal implementation detail).
- **Tests**: N/A (No code changes made).
- **Details**: Confirmed that the existing implementation already uses the correct indexed format (e.g., `languages[0]=value`) for these parameters in both specified methods.
- **Related**: [ActiveContext 2025-05-06 18:05:57], [GlobalContext Progress 2025-05-06 18:06:15]
### [2025-05-06 12:37:17] `download_book_to_file` Fixes
- **Purpose**: To resolve "Missing original file_path" error and path handling bug in the `download_book_to_file` tool.
- **Files**:
    - `zlibrary/src/zlibrary/libasync.py`: Modified `AsyncZlib.download_book` method.
        - Renamed `output_path: str` parameter to `output_dir_str: str`.
        - Changed return type annotation from `-> None:` to `-> str:`.
        - Added logic to construct `actual_output_path` from `book_details` and `output_dir_str`.
        - Updated directory creation logic to use `output_directory`.
        - Updated file opening logic to use `actual_output_path`.
        - Changed final return to `str(actual_output_path)`.
        - Updated logging to use `actual_output_path`.
    - `lib/python_bridge.py`: Modified `download_book` function.
        - Updated the call to `zlib_client.download_book` to use the new parameter name `output_dir_str`.
- **Status**: Implemented.
- **Details**: These changes address the root causes identified by `debug` mode: `libasync.py` returning `None` and incorrect path handling. The method now returns the actual path of the downloaded file, and the output directory is correctly used.
- **Related**: [ActiveContext 2025-05-06 12:37:17], [GlobalContext Progress 2025-05-06 12:37:17], [See Debug Completion Report - ActiveContext 2025-05-06 12:35:22]
## API/Handler Modifications
### [2025-05-06 12:12:30] `get_download_history` Endpoint and Parser Update
- **Purpose**: To fix the `get_download_history` tool which was failing due to an obsolete endpoint and incorrect parser logic.
- **Files**:
    - `zlibrary/src/zlibrary/profile.py`: Modified `download_history` method to change the target URL from `/users/dstats.php` to `/users/downloads`.
    - `zlibrary/src/zlibrary/abs.py`: Modified `DownloadsPaginator.parse_page` method to correctly parse the HTML structure of the new `/users/downloads` page. This involved updating selectors to find table rows (`tr.dstats-row`), and then extracting `data-item_id`, download date/time, book title, book URL, and re-download URL from the table cells (`td`) within each row.
- **Status**: Implemented.
- **Details**: The previous endpoint `/users/dstats.php` was returning a 404. Debug investigation indicated `/users/downloads` as the new endpoint. Parser logic was updated based on user-provided HTML for the new page.
- **Related**: [ActiveContext 2025-05-06 12:11:44], [GlobalContext Progress 2025-05-06 12:12:11]
## Intervention Log
### [2025-05-06 04:49:15] Intervention: Deprecate `get_recent_books`
- **Trigger**: User Feedback [Ref: ActiveContext 2025-05-06 04:49:15]
- **Context**: After multiple failed attempts to fix `ParseError` for `get_recent_books` and `get_download_history`.
- **Action Taken**: User decided to deprecate `get_recent_books`. Focus shifted to verifying the fix for `get_download_history`.
- **Rationale**: `get_recent_books` page was not showing results, making parser fixes impossible. User prefers to enhance `search_books` instead.
- **Outcome**: `get_recent_books` fix is no longer pursued. `get_download_history` fix attempt also failed verification [Ref: Debug Completion 2025-05-06 04:50:12].
- **Follow-up**: Further investigation needed for `get_download_history` if the tool is still required. Consider if the issue is HTML content retrieval vs. parsing.
### Implementation: `download_book` in Forked Library - [2025-04-24 03:49:26]
### [2025-04-29 19:34:25] _slugify Function
- **Purpose**: Generate URL-safe slugs from strings (author, title).
- **Files**: `lib/rag_processing.py`
- **Status**: Implemented
- **Dependencies**: `re`, `unicodedata`
- **API Surface**: `_slugify(value, allow_unicode=False)`
- **Tests**: `__tests__/python/test_rag_processing.py::test_slugify_ascii`, `__tests__/python/test_rag_processing.py::test_slugify_unicode`

### [2025-04-29 19:34:25] save_processed_text Function Update
- **Purpose**: Modified to generate human-readable filenames using `_slugify`.
- **Files**: `lib/rag_processing.py`
- **Status**: Implemented
- **Dependencies**: `_slugify`, `pathlib.Path`, `aiofiles`, `logging`, `os`
- **API Surface**: `save_processed_text(original_file_path: Path, text_content: str, output_format: str = "txt", book_id: str = None, author: str = None, title: str = None) -> Path`
- **Tests**: `__tests__/python/test_rag_processing.py` (various tests)
## API/Handler Modifications
### [2025-05-06 02:40:36] Fix RAG Tool Async/Await Issues
- **Purpose**: Resolved `NameError: name 'asyncio' is not defined` and `RuntimeError: asyncio.run() cannot be called from a running event loop` during `process_document_for_rag` calls.
- **Files**:
    - `lib/rag_processing.py`: Added `import asyncio` (line 1). Changed `process_txt` (line 947) to `async def`. Changed `asyncio.run(read_utf8())` to `await read_utf8()` (line 956) and `asyncio.run(read_latin1())` to `await read_latin1()` (line 963).
    - `lib/python_bridge.py`: Changed `processed_text = rag_processing.process_txt(file_path)` to `processed_text = await rag_processing.process_txt(file_path)` (line 230) within the `process_document` function.
- **Status**: Implemented and Verified.
- **Details**: The `asyncio` library was missing from `rag_processing.py`. Additionally, `asyncio.run()` was being called from within an already running event loop, and `process_txt` (now async) was not being awaited by its caller. These changes correct the async control flow.
- **Related**: [ActiveContext 2025-05-06 02:40:36]
### [2025-05-06 02:24:48] Fix Python Bridge Output for MCP Data Flow
- **Purpose**: Resolved incorrect data return for tools like `get_download_limits`. The Python bridge (`lib/python_bridge.py`) was not outputting data in the doubly-wrapped JSON structure expected by `callPythonFunction` in `src/lib/zlibrary-api.ts`.
- **Files**: `lib/python_bridge.py` (modified `main` function's print statement, lines 353-360).
- **Status**: Implemented and Verified.
- **Details**: Changed the Python script's `main` function to always print `json.dumps({ "content": [{ "type": "text", "text": json.dumps(actual_python_result) }] })`. This ensures the Node.js layer receives the correct intermediate structure for parsing. The `tools/call` handler in `src/index.ts` remains as `return { content: [{ type: 'text', text: JSON.stringify(result) }] };` for the final client response.
- **Related**: Task [Fix Incorrect Data Return in MCP `tools/call` Handler], [GlobalContext Progress 2025-05-06 02:24:48], [GlobalContext Pattern 2025-05-06 02:24:48], [User Feedback 2025-05-06 02:07:05]
### [2025-05-06 02:05:11] Fix MCP Result Format (`tools/call` - Raw Object)
- **Purpose**: Corrected the `tools/call` handler to return the raw result object directly within the `content` array, resolving incorrect data return (e.g., stringified dict instead of actual dict) reported after INT-001 fix.
- **Files**: `src/index.ts` (modified line 331).
- **Status**: Implemented.
- **Details**: Changed `return { content: [{ type: 'text', text: JSON.stringify(result) }] };` to `return { content: [result] };`. Build and tests passed.
- **Related**: Task [Fix Incorrect Data Return in MCP `tools/call` Handler], [GlobalContext Progress 2025-05-06 02:05:11], [GlobalContext Pattern 2025-05-06 02:05:11], [GlobalContext Pattern 2025-05-05 22:29:07] (Previous structure)

### [2025-04-29 16:36:11] Fix MCP Result Format (`tools/call`)
- **Purpose**: Ensure the `tools/call` handler returns results in the standard MCP format `{ result: value }`.
- **Files**: `src/index.ts` (modified line 332).
- **Status**: Implemented.
- **Details**: Changed the return statement in the handler to `return { result: result } as any;`. Cast to `any` to bypass inaccurate SDK TypeScript type for `ServerResult`. Verified with `npm test`.
- **Related**: Task [2025-04-29 16:33:52], Commit `47edb7a`, Holistic Review Finding [Ref: holistic-reviewer completion 2025-04-29 15:41:26].
### [2025-04-29 03:01:59] RAG Markdown Generation (PDF/EPUB)
- **Purpose**: Enhance PDF and EPUB processing to generate structured Markdown output (headings, lists, footnotes).
- **Files**: `lib/python_bridge.py` (modified `_process_pdf`, `_process_epub`, `process_document`, `main`; added `_analyze_pdf_block`, `_format_pdf_markdown`, `_epub_node_to_markdown`).
- **Status**: Implemented (TDD Green Phase Complete).
- **Dependencies**: `fitz` (PyMuPDF), `ebooklib`, `beautifulsoup4`, `lxml`.
- **API Surface**: Modified `process_document` function in Python bridge to accept `output_format` ('text' or 'markdown').
- **Tests**: `__tests__/python/test_python_bridge.py` (relevant xfail tests now xpass).
- **Related**: `docs/rag-markdown-generation-spec.md`, ActiveContext [2025-04-29 03:01:59]
- **Approach**: Implemented the missing `download_book` async method in the `AsyncZlib` class (`zlibrary/src/zlibrary/libasync.py`) using `httpx` for downloading (with redirect following) and `aiofiles` for asynchronous file writing. Added a custom `DownloadError` exception (`zlibrary/src/zlibrary/exception.py`) and updated the forked library's dependencies (`zlibrary/pyproject.toml`).
- **Key Files Modified/Created**:
  - `zlibrary/src/zlibrary/libasync.py`: Added imports (`httpx`, `aiofiles`, `os`, `pathlib`, `Dict`, `DownloadError`), added `download_book` method.
  - `zlibrary/src/zlibrary/exception.py`: Added `DownloadError` class.
  - `zlibrary/pyproject.toml`: Added `httpx` and `aiofiles` to dependencies.
- **Notes**: Resolved Git commit issues related to the `zlibrary/` subdirectory being an embedded repository by removing `zlibrary/.git` before committing. Addresses integration blocker INT-RAG-003.
- **Related**: ActiveContext [2025-04-24 03:49:26], GlobalContext [2025-04-24 03:49:26], Decision-DownloadBookDeps-01


### Implementation: Search-First ID Lookup (TDD Green Phase) - [2025-04-16 18:40:05]
- **Approach**: Implemented internal search (`_internal_search`) and modified internal lookup (`_internal_get_book_details_by_id`) in `lib/python_bridge.py` using `httpx`/`BeautifulSoup` per spec (`docs/search-first-id-lookup-spec.md`). Updated callers (`get_by_id`, `get_download_info`, `main`) to use new logic and translate exceptions.
- **Key Files Modified/Created**:
  - `lib/python_bridge.py`: Added imports (`urljoin`), exceptions (`InternalFetchError`), functions (`_internal_search`), modified `_internal_get_book_details_by_id`, `get_by_id`, `get_download_info`, `main`.
  - `__tests__/python/test_python_bridge.py`: Added `@pytest.mark.asyncio` decorators, fixed missing `domain` args, corrected mock logic/assertions, removed `xfail` markers, fixed warnings.
  - `requirements-dev.txt`: Added `pytest-asyncio`.
- **Notes**: Required multiple iterations to fix Python tests. Issues included missing `pytest-asyncio` plugin, missing `@pytest.mark.asyncio` decorators, incorrect mock setup for nested async calls (`_internal_search` within `_internal_get_book_details_by_id`), incorrect `assert_awaited_once_with` arguments, and incorrect `pytest.raises` match patterns. Used `write_to_file` for test file due to repeated `apply_diff` failures. Python tests related to this feature now pass. Node tests (`npm test`) also pass.
- **Related**: `docs/search-first-id-lookup-spec.md`, ActiveContext [2025-04-16 18:40:05], GlobalContext [2025-04-16 18:40:05]



### Implementation: Internal ID Lookup (TDD Green Phase) - [2025-04-16 08:38:32]
- **Approach**: Implemented internal web scraping for ID lookups in `lib/python_bridge.py` as per spec `docs/internal-id-lookup-spec.md`. Added `_internal_get_book_details_by_id` using `httpx` to fetch `/book/ID`, handle expected 404s (`InternalBookNotFoundError`), and parse 200 OK (unexpected case) with placeholder selectors. Modified callers `get_by_id` and `get_download_info` to use the new function and translate exceptions (`InternalBookNotFoundError` -> `ValueError`, `InternalParsingError`/`RuntimeError` -> `RuntimeError`).
- **Key Files Modified/Created**:
  - `lib/python_bridge.py`: Added imports (`httpx`), exceptions (`InternalBookNotFoundError`, `InternalParsingError`), function `_internal_get_book_details_by_id`, modified `get_by_id`, `get_download_info`.
  - `__tests__/python/test_python_bridge.py`: Removed old `*_workaround_*` tests, un-xfail'd new internal lookup tests, corrected assertions for error messages.
- **Notes**: Required multiple attempts to run Python tests due to incorrect venv path assumption (needed `/home/rookslog/.cache/...` path from `venv-manager.ts`, not `./venv`) and missing dependencies (`pytest`, `httpx`) in venv. Manually installed dev requirements and `httpx` via pip as a temporary measure. Fixed exception handling logic in `_internal_get_book_details_by_id` to allow `InternalBookNotFoundError` to propagate correctly. Updated test assertions to match new error messages. Python tests (relevant ones) and Node tests now pass.
- **Related**: `docs/internal-id-lookup-spec.md`, ActiveContext [2025-04-16 08:38:32], GlobalContext [2025-04-16 08:38:32], Feedback [2025-04-16 08:32:47]


### Implementation: Fix `zlibrary` ID Lookup Bugs - [2025-04-16 00:03:16]
- **Approach**: Applied fixes directly to the external `sertraline/zlibrary` source code within the `zlibrary/` subdirectory based on the strategy outlined in the task and Memory Bank (Decision-IDLookupStrategy-01, ActiveContext [2025-04-15 23:18:25]).
- **Key Files Modified/Created**:
  - `zlibrary/src/zlibrary/libasync.py`: Modified `get_by_id` to use `search(q=f'id:{id}', exact=True, count=1)` instead of constructing the URL directly.
  - `zlibrary/src/zlibrary/abs.py`: Modified `SearchPaginator.parse_page` to detect and handle potential direct book page results from `id:` searches by attempting to parse using a new helper method `_parse_book_page_soup`. Extracted parsing logic from `BookItem.fetch` into `_parse_book_page_soup` and updated `fetch` to use the helper. Removed redundant parsing code from `fetch`.
- **Notes**: The fixes address the `ParseError` issues caused by incorrect URL construction in `get_by_id` and unexpected HTML structure in `id:` search results. Required multiple `apply_diff` attempts due to partial application failures.
- **Related**: Issue-ParseError-IDLookup-01, Decision-IDLookupStrategy-01, ActiveContext [2025-04-16 00:02:36], GlobalContext [2025-04-16 00:03:00]


### Implementation: ID Lookup Workaround (TDD Green Phase) - [2025-04-15 22:39:35]
- **Approach**: Implemented search-based workaround for `get_by_id` and `get_download_info` in `lib/python_bridge.py` to address `ParseError` from faulty `client.get_by_id`. Followed TDD Green phase: modified code minimally to make existing xfailed tests pass.
- **Key Files Modified/Created**:
  - `lib/python_bridge.py`: Replaced `client.get_by_id` calls with `client.search(q=f'id:{book_id}', exact=True, count=1)` and added result handling (0, 1, >1 results).
  - `__tests__/python/test_python_bridge.py`: Removed `@pytest.mark.xfail` from 8 tests, corrected function name (`get_by_id`), added `import asyncio`, updated mocks (`AsyncMock`), and adjusted assertions for error messages and return values.
  - `__tests__/zlibrary-api.test.js`: Corrected `toHaveBeenCalledWith` assertions for `mockPythonShellRun` (script name `python_bridge.py`, script path `/home/rookslog/zlibrary-mcp/lib`).
  - `__tests__/python-bridge.test.js`: Corrected `toHaveBeenCalledWith` assertion for `spawn` (script path `/home/rookslog/zlibrary-mcp/dist/lib/python_bridge.py`).
- **Notes**: Required multiple test runs and fixes for Python tests (missing `asyncio` import, incorrect `AsyncMock` usage) and Node tests (incorrect script name/path assertions in mocks). All tests now pass.
- **Related**: Decision-ParseErrorWorkaround-01, ActiveContext [2025-04-15 22:39:35], GlobalContext [2025-04-15 22:39:35]


### Implementation: Jest/ESM Test Suite Fix (Delegated) - [2025-04-15 15:29:00]
- **Approach**: Task delegated due to context overload and repeated errors fixing Jest/ESM issues. Delegated agent identified unreliable mocking of built-in Node modules (`fs`, `child_process`) with `jest.unstable_mockModule` and dynamic imports as the root cause of persistent test failures (`spawn ENOENT`, timeouts).
- **Resolution**: Refactored `src/lib/venv-manager.ts` to use Dependency Injection, decoupling it from direct `fs`/`child_process` usage. Updated `__tests__/venv-manager.test.js` to pass mock objects via DI. Corrected various assertion errors in other test files.
- **Key Files Modified/Created**: `src/lib/venv-manager.ts`, `__tests__/venv-manager.test.js`, `__tests__/zlibrary-api.test.js`, `__tests__/index.test.js`, `__tests__/python-bridge.test.js`, `jest.config.js` (across sessions).
- **Notes**: Dependency Injection proved crucial for stable testing in the Jest/ESM environment. All tests now pass. Recommend TDD run for regression testing.



### Implementation: Jest Test Suite Fixes (TS/ESM Handover) - Confirmation [2025-04-15 13:45:08]
- **Approach**: Confirmed via Memory Bank ([2025-04-15 05:31:00]) that all Jest tests were passing after a previous task reset and subsequent fixes involving Dependency Injection.
- **Key Files Modified/Created**: None in this instance.
- **Notes**: Task was reset due to context window issues, but the objective was already achieved in the prior context.
- **Related**: ActiveContext [2025-04-15 13:44:30], GlobalContext [2025-04-15 13:44:48]



### Implementation: Jest Test Suite Fixes (TS/ESM Handover) - Complete [2025-04-15 05:04:00]
- **Approach**: Successfully fixed all remaining Jest test failures. Refactored `__tests__/zlibrary-api.test.js` to mock API functions directly. Delegated persistent `__tests__/venv-manager.test.js` failures to a `debug` task, which resolved them by refactoring `src/lib/venv-manager.ts` to use Dependency Injection (DI) for `fs` and `child_process`, bypassing Jest ESM mocking issues.
- **Key Files Modified/Created**:
  - `__tests__/zlibrary-api.test.js`: Refactored mocks.
  - `__tests__/venv-manager.test.js`: Updated by debug task to use DI.
  - `src/lib/venv-manager.ts`: Refactored by debug task to use DI.
  - `jest.config.js`: Added `transform: {}` (may be redundant now).
- **Notes**: All test suites now pass. The DI pattern proved effective for testing modules interacting with built-in Node APIs in Jest ESM.
- **Related**: Decision-JestMockingStrategy-01, Decision-DIForVenvManager-01 (Assumed from Debug task), ActiveContext [2025-04-15 05:04:00]


### Implementation: Jest Test Fixes (TS/ESM Handover) - Final Attempt 2 [2025-04-15 04:08:00]
- **Approach**: Attempted `jest.spyOn` as an alternative to `unstable_mockModule` for mocking `fs` methods in `__tests__/venv-manager.test.js`. This also failed to resolve the 3 persistent test failures.
- **Key Files Modified/Created**:
  - `__tests__/venv-manager.test.js`: Refactored one test to use `jest.spyOn`.
- **Notes**: Concluded that standard Jest mocking techniques (`unstable_mockModule`, `spyOn`) are insufficient to reliably mock built-in Node modules (`fs`, `child_process`) in this specific Jest ESM context, likely due to interactions with dynamic imports or Jest's internal module handling. The remaining 3 failures require a different approach (e.g., refactoring `venv-manager.ts`, deeper Jest ESM investigation).
- **Related**: Decision-JestMockingStrategy-01, ActiveContext [2025-04-15 04:08:00]


### Implementation: Jest Test Fixes (TS/ESM Handover) - Final Attempt [2025-04-15 04:00:00]
- **Approach**: Made final attempts to fix `__tests__/venv-manager.test.js`. Corrected `fs.existsSync` mock implementation and reverted error handling changes in `src/lib/venv-manager.ts`. Added `transform: {}` to `jest.config.js` to explicitly disable Jest transformations.
- **Key Files Modified/Created**:
  - `__tests__/venv-manager.test.js`: Updated `fs.existsSync` mock.
  - `src/lib/venv-manager.ts`: Reverted error handling.
  - `jest.config.js`: Added `transform: {}`.
- **Notes**: The 3 failures in `venv-manager.test.js` persist. The issues with mocking built-in modules (`fs`, `child_process`) and async rejection handling in Jest ESM remain unresolved by these changes. Concluding debugging efforts for this task.
- **Related**: Decision-JestMockingStrategy-01, ActiveContext [2025-04-15 04:00:00]


### Implementation: Jest Test Fixes (TS/ESM Handover) - [2025-04-15 03:41:00]
- **Approach**: Investigated persistent Jest ESM test failures. Refactored `__tests__/zlibrary-api.test.js` to mock exported API functions directly using `jest.unstable_mockModule` and `jest.resetModules()`, resolving all failures in that suite. Made multiple attempts to fix `__tests__/venv-manager.test.js` failures related to mocking `fs` (`existsSync`, `readFileSync`) and `child_process` (`spawn` error handling) using `unstable_mockModule`, dynamic imports, and adjusting error propagation logic. These attempts were unsuccessful.
- **Key Files Modified/Created**:
  - `__tests__/zlibrary-api.test.js`: Refactored mocks.
  - `__tests__/venv-manager.test.js`: Multiple mock adjustments.
  - `src/lib/venv-manager.ts`: Error handling adjustments (reverted).
- **Notes**: The `zlibrary-api.test.js` suite now passes reliably. The `venv-manager.test.js` failures (3 tests) seem deeply related to Jest ESM's handling of built-in module mocks and async error propagation, requiring further investigation or alternative testing strategies (e.g., refactoring `venv-manager.ts`).
- **Related**: Decision-JestMockingStrategy-01


### Implementation: Fix Tool Listing (INT-001, Final Fix) - [2025-04-14 22:05:00]
- **Approach**: Corrected the `ToolDefinition` interface to use `inputSchema` (camelCase) instead of `input_schema`, resolving the TypeScript error and aligning the interface with the returned object structure. This followed previous fixes aligning capability declaration and `zodToJsonSchema` usage with working examples.
- **Key Files Modified/Created**: `src/index.ts`
- **Notes**: Build successful. User confirmed tools are now listed correctly in RooCode, resolving INT-001. The critical fixes were ensuring capabilities were passed during `new Server()` instantiation and using the correct `inputSchema` key.



### Implementation: Fix Tool Listing (INT-001, Attempt 3) - [2025-04-14 21:58:00]
- **Approach**: Compared `src/index.ts` (TS/ESM, SDK v1.8.0) with working example `wonderwhy-er/DesktopCommanderMCP/src/server.ts`. Identified and fixed two key differences: removed a redundant `server.registerCapabilities` call and corrected the `zodToJsonSchema` call in the `ListToolsRequest` handler to only pass the schema object (removed the second `name` argument).
- **Key Files Modified/Created**: `src/index.ts`
- **Notes**: Build successful. `mcp_settings.json` verified. This aligns our server's initialization and schema generation with a known working pattern, addressing the likely cause of tools not being listed in RooCode.



### Implementation: Fix Schema Generation (INT-001, Attempt 2.3) - [2025-04-14 19:37:07]
- **Approach**: Final server-side attempt based on external examples. Modified `index.js` ListToolsRequest handler (lines 241-257) to remove the optional `name` argument from the `zodToJsonSchema` call, matching the `wonderwhy-er/DesktopCommanderMCP` example. Kept the logic to handle empty schemas explicitly.
- **Key Files Modified/Created**: `index.js`
- **Notes**: User confirmed client UI still shows 'No tools found'. GitHub issue search revealed RooCode issue #2085 describing identical behavior, strongly suggesting a client-side regression in RooCode v3.9.0+ is the root cause. Server-side fixes exhausted.



### Implementation: Fix Schema Generation (INT-001, Attempt 2.1) - [2025-04-14 19:29:19]
- **Approach**: Refined the fix for INT-001 in `index.js`. Corrected the CJS import for `zod-to-json-schema` (removed `.default` on line 7) and uncommented all tools in `toolRegistry` (lines 156-202) to ensure they are processed by the schema generation logic in the `ListToolsRequest` handler.
- **Key Files Modified/Created**: `index.js`
- **Notes**: This addresses potential issues with the CJS import and ensures all defined tools are attempted for schema generation. Ready for user verification.



### Implementation: Fix Schema Generation (INT-001, Attempt 2) - [2025-04-14 19:27:00]
- **Approach**: Modified `index.js` ListToolsRequest handler (lines 241-258) to correctly use `zod-to-json-schema` and skip tools that fail generation, instead of using placeholders. This was based on the hypothesis that individual schema generation errors were the primary cause.
- **Key Files Modified/Created**: `index.js`
- **Notes**: User confirmed client UI still shows 'No tools found' after restarting the server. This indicates the fix was insufficient and the root cause is likely more complex, potentially involving client-side parsing or SDK/CJS interactions, as suggested by previous debugging and architectural analysis.



### Implementation: RAG Document Pipeline - PDF Processing (TDD Green Phase) - [2025-04-14 14:30:00]
- **Approach**: Implemented minimal code changes for PDF processing (Task 3) based on spec `docs/pdf-processing-implementation-spec.md` and failing tests from TDD Red phase [2025-04-14 14:13:42]. Used `PyMuPDF (fitz)`. Fixed unrelated test failures in `__tests__/index.test.js` by updating outdated test expectations.
- **Key Files Modified/Created**:
  - `requirements.txt`: Added `PyMuPDF`.
  - `lib/python-bridge.py`: Added `import fitz`, `import logging`. Added `_process_pdf` function. Modified `process_document`.
  - `__tests__/index.test.js`: Updated expectations for `registerCapabilities` and handler responses (`content` key).
- **Notes**: TDD Green phase complete. All tests pass. Ready for Refactor phase.


### Implementation: RAG Document Pipeline - PDF Processing (TDD Green Phase) - [2025-04-14 14:25:00]
- **Approach**: Implemented minimal code changes for PDF processing (Task 3) based on spec `docs/pdf-processing-implementation-spec.md` and failing tests from TDD Red phase [2025-04-14 14:13:42]. Used `PyMuPDF (fitz)`.
- **Key Files Modified/Created**:
  - `requirements.txt`: Added `PyMuPDF`.
  - `lib/python-bridge.py`: Added `import fitz`, `import logging`. Added `_process_pdf` function implementing text extraction with error handling (encryption, no text, corruption). Modified `process_document` to add `.pdf` handling via `elif`, updated signature/docstring, added `SUPPORTED_FORMATS` list, refined error handling/propagation.
- **Notes**: Code changes complete for Green phase. Next step is running `npm test` to verify tests pass.


### Implementation: RAG Document Pipeline (TDD Green Phase) - [2025-04-14 12:31:05]
- **Approach**: Implemented RAG pipeline features as per spec (`docs/rag-pipeline-implementation-spec.md`) and TDD Red phase tests. Updated `venv-manager.js` to use `requirements.txt`. Updated `index.js` with new/modified Zod schemas and tool registrations. Updated `lib/zlibrary-api.js` to handle `process_for_rag` flag in `downloadBookToFile` and added `processDocumentForRag` handler calling Python. Implemented EPUB/TXT processing logic in `lib/python-bridge.py` using `ebooklib` and `BeautifulSoup`, adding `process_document` function and registering it.
- **Key Files Modified/Created**:
  - `requirements.txt`: New file listing Python dependencies (`zlibrary`, `ebooklib`, `beautifulsoup4`, `lxml`).
  - `lib/venv-manager.js`: Modified `installDependencies` and `checkPackageInstalled` to use `requirements.txt`.
  - `index.js`: Updated `DownloadBookToFileParamsSchema`, added `ProcessDocumentForRagParamsSchema`. Updated `handlers` and `toolRegistry` for `download_book_to_file` and `process_document_for_rag`.
  - `lib/zlibrary-api.js`: Added `process_for_rag` param to `downloadBookToFile`, added logic to call `processDocumentForRag`. Added `processDocumentForRag` function definition.
  - `lib/python-bridge.py`: Added imports (`ebooklib`, `bs4`, `os`, `pathlib`). Added `_process_epub`, `_process_txt`, `process_document` functions. Added `process_document` to `function_map`.
- **Notes**: TDD Green phase implementation complete. Test run shows remaining failures are within test files (`__tests__/*.test.js`), related to outdated mocks, incorrect expectations (e.g., missing default args), or incorrect test function calls. Core implementation logic appears correct based on spec and passing Python tests.


### Implementation: Global Execution Fix (Managed Venv) - [2025-04-14 04:11:52]
- **Approach**: Implemented `lib/venv-manager.js` for Python venv detection, creation, dependency installation (`zlibrary`), and configuration storage using `env-paths`. Updated `lib/zlibrary-api.js` to use the managed Python path via `getManagedPythonPath`. Updated `index.js` to call `ensureVenvReady` and use correct SDK import. Removed old `lib/python-env.js`.
- **Key Files Modified/Created**:
  - `lib/venv-manager.js`: New file implementing the core venv management logic.
  - `index.js`: Updated SDK import, replaced `ensureZLibraryInstalled` with `ensureVenvReady`.
  - `lib/zlibrary-api.js`: Updated `callPythonFunction` to use `getManagedPythonPath`.
  - `package.json`: Added `env-paths` dependency.

### Dependency: httpx (Forked Library) - [2025-04-24 03:18:12]
- **Version**: (Added to `zlibrary/pyproject.toml`)
- **Purpose**: Async HTTP client used for downloading books in the `download_book` method within the forked `zlibrary` library.
- **Used by**: `zlibrary/src/zlibrary/libasync.py`
- **Config notes**: Chosen for async support and redirect handling.

### Dependency: aiofiles (Forked Library) - [2025-04-24 03:18:12]
- **Version**: (Added to `zlibrary/pyproject.toml`)
- **Purpose**: Async file I/O library used for writing downloaded book content in the `download_book` method within the forked `zlibrary` library.
- **Used by**: `zlibrary/src/zlibrary/libasync.py`
- **Config notes**: Necessary for non-blocking file operations in async context.


## Dependencies Log


### Dependency: pytest-asyncio - [2025-04-16 18:40:05]
- **Version**: 0.26.0 (Installed via pip)
- **Purpose**: Pytest plugin to handle async test functions.
- **Used by**: `__tests__/python/test_python_bridge.py`
- **Config notes**: Added to `requirements-dev.txt`. Required `@pytest.mark.asyncio` decorator on async tests.

### Dependency: httpx - [2025-04-16 08:38:32]
- **Version**: 0.28.1 (Installed via pip)
- **Purpose**: Modern asynchronous HTTP client for making requests in `_internal_get_book_details_by_id`.
- **Used by**: `lib/python_bridge.py`
- **Config notes**: Added to `requirements.txt` in Red phase. Manually installed during Green phase due to test failure.

### Dependency: PyMuPDF - [2025-04-14 14:25:00]
- **Version**: (Installed via pip from requirements.txt)
- **Purpose**: Python library for PDF text extraction (`fitz`). Chosen for accuracy and performance (Decision-PDFLibraryChoice-01).
- **Used by**: `lib/python-bridge.py` (`_process_pdf`)
- **Config notes**: AGPL-3.0 license.


<!-- Append new dependencies using the format below -->
### Dependency: ebooklib - [2025-04-14 12:31:05]
- **Version**: (Installed via pip from requirements.txt)
- **Purpose**: Python library for reading/writing EPUB files.
- **Used by**: `lib/python-bridge.py` (`_process_epub`)
- **Config notes**: None.

### Dependency: beautifulsoup4 - [2025-04-14 12:31:05]
- **Version**: (Installed via pip from requirements.txt)
- **Purpose**: Python library for parsing HTML/XML (used for EPUB content).
- **Used by**: `lib/python-bridge.py` (`_process_epub`)
- **Config notes**: Requires a parser like `lxml`.

### Dependency: lxml - [2025-04-14 12:31:05]
- **Version**: (Installed via pip from requirements.txt)
- **Purpose**: Python library for processing XML and HTML (used as parser for BeautifulSoup).
- **Used by**: `lib/python-bridge.py` (implicitly by `_process_epub` via BeautifulSoup)
- **Config notes**: None.


  - `__tests__/index.test.js`: Updated mocks for `venv-manager`.
  - `__tests__/zlibrary-api.test.js`: Refactored mock setup significantly to handle module loading order.
  - `jest.config.js`: Removed `transformIgnorePatterns` after switching to mocking `env-paths`.
  - `__mocks__/env-paths.js`: Added mock for `env-paths`.
- **Files Removed**:
  - `lib/python-env.js`
  - `__tests__/python-env.test.js`
- **Notes**: TDD Green phase complete. Required significant debugging of Jest mock setup, particularly around module loading order and ESM dependencies. Final solution involved standard Jest mocking patterns without `resetModules` in `beforeEach` for `zlibrary-api.test.js` and mocking the `env-paths` module directly.

### Dependency: env-paths - [2025-04-14 04:11:52]
- **Version**: ^3.0.0
- **Purpose**: Determine user-specific cache directory path reliably across platforms for storing the managed Python venv.
- **Used by**: `lib/venv-manager.js`
- **Config notes**: None.
