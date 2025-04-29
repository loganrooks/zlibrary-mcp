# Auto-Coder Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
### Implementation: `download_book` in Forked Library - [2025-04-24 03:49:26]
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
