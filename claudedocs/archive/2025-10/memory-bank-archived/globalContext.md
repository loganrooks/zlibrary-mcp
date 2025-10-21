---
### Progress - [2025-05-07 08:02:31]
- **`get_book_metadata` Tool Specification (Task 4)**:
    - Defined the detailed specification for the `get_book_metadata` tool, which scrapes metadata from Z-Library book pages.
    - Specification includes the Python dictionary output structure, data types, nullability for 16 metadata fields plus `source_url`.
    - Outlined scraping logic for each field, including data cleaning/parsing considerations and handling for missing/malformed data (with placeholders for CSS selectors pending `debug` mode input).
    - Provided Python pseudocode for the `scrape_book_metadata(url: str, session: httpx.AsyncClient)` function, demonstrating HTML fetching with `httpx`, parsing with `BeautifulSoup4`, data extraction, cleaning, and dictionary construction.
    - Listed comprehensive TDD anchors for both the Python scraping function (mocked HTML, field extraction, missing fields, parsing complex fields, HTML variations) and Node.js Zod schemas (input/output validation).
    - This addresses Task 4 of the project plan: [`docs/project-plan-zlibrary-mcp.md:166-237`](docs/project-plan-zlibrary-mcp.md:166-237).
- **Related Entries**: [ActiveContext 2025-05-07 08:02:31], [memory-bank/mode-specific/spec-pseudocode.md - Feature: Get Book Metadata - [2025-05-07 08:02:31]]

---
### Progress - [2025-05-07 06:52:30]
- **Enhanced Filename Convention Implemented (Task 3)**:
    - Implemented the `LastnameFirstname_TitleOfTheBook_BookID.ext` filename convention in `lib/python_bridge.py`.
    - Created a helper function `_create_enhanced_filename` to handle parsing, sanitization, and formatting of author, title, BookID, and extension.
    - Integrated this helper into the `download_book` function, which now renames the downloaded file to the new convention and returns the updated path.
    - This addresses Task 3 of the project plan: [`docs/project-plan-zlibrary-mcp.md:130-162`](docs/project-plan-zlibrary-mcp.md:130-162).
- **Related Entries**: [ActiveContext 2025-05-07 06:52:30], [GlobalContext Product: Enhanced Filename Convention Specification - [2025-05-07]], [memory-bank/mode-specific/code.md Component: _create_enhanced_filename - [2025-05-07 06:52:30]]

---
### Pattern: Enhanced Filename Convention - [2025-05-07 06:52:30]
- **Context**: Standardizing downloaded book filenames for better readability and filesystem safety.
- **Problem**: Default filenames (e.g., `BOOK_ID.extension`) are not user-friendly and may lack important metadata at a glance.
- **Solution**: Implemented a new filename convention: `LastnameFirstname_TitleOfTheBook_BookID.ext`.
    - A helper function `_create_enhanced_filename(book_details: dict) -> str` in `lib/python_bridge.py` generates this filename.
    - It parses author (first author, LastnameFirstname), title (slugified), BookID, and extension from `book_details`.
    - Includes robust string sanitization (removes invalid characters, handles spaces, truncates components and overall length) and fallbacks for missing data.
    - The `download_book` function in `lib/python_bridge.py` now uses this helper to rename the downloaded file and returns the path with the new convention.
- **Impact**: Improves user experience by providing more informative filenames. Enhances filesystem compatibility.
- **Related Files**: `lib/python_bridge.py`
- **Related Specification**: [GlobalContext Product: Enhanced Filename Convention Specification - [2025-05-07]]
---
### Progress - [2025-05-07 06:42:40]
- **Python Bridge Unit Test Update (Task 2.2)**:
    - Updated unit tests in `__tests__/python/test_python_bridge.py` to align with changes in `lib/python_bridge.py` (removal of `_find_book_by_id_via_search` and ADR-002 compliance for `download_book`).
    - Specifically, assertions for `download_book` mock calls were corrected to no longer expect `book_id` as a direct parameter.
    - All Python unit tests in `__tests__/python/test_python_bridge.py` pass.
    - Full MCP regression test suite (`npm test`) also passed, confirming no integration issues from Python bridge changes.
- **Related Entries**: [ActiveContext 2025-05-07 06:42:40], [`docs/project-plan-zlibrary-mcp.md#task-22-update-and-verify-python-bridge-unit-tests`](docs/project-plan-zlibrary-mcp.md), [`docs/adr/ADR-002-Download-Workflow-Redesign.md`](docs/adr/ADR-002-Download-Workflow-Redesign.md)
---
### Progress - [2025-05-07 06:39:00]
- **`lib/python_bridge.py` Cleanup (Task 2.2)**:
    - Removed the deprecated `_find_book_by_id_via_search` function from [`lib/python_bridge.py`](lib/python_bridge.py).
    - Confirmed that the `download_book` function in [`lib/python_bridge.py`](lib/python_bridge.py) correctly uses `bookDetails` as input and aligns with the `AsyncZlib.download_book` method in [`zlibrary/src/zlibrary/libasync.py`](zlibrary/src/zlibrary/libasync.py), adhering to ADR-002.
    - Reviewed public functions in [`lib/python_bridge.py`](lib/python_bridge.py) and confirmed their interfaces are consistent with ADR-002.
- **Related Entries**: [ActiveContext 2025-05-07 06:39:00], [`docs/project-plan-zlibrary-mcp.md:104-126`](docs/project-plan-zlibrary-mcp.md:104-126), [`docs/adr/ADR-002-Download-Workflow-Redesign.md`](docs/adr/ADR-002-Download-Workflow-Redesign.md)
---
### Progress - [2025-05-07 05:58:00]
- **`zlibrary/libasync.py` Cleanup (Task 2.1)**:
    - Addressed Pylance warnings in `zlibrary/src/zlibrary/libasync.py` by removing redundant `typing` imports.
    - Removed the deprecated `AsyncZlib.get_by_id` method, which was used for direct ID-based book fetching.
    - Confirmed that the `AsyncZlib.download_book` method aligns with ADR-002, strictly using `bookDetails` (which includes the book page URL) as input for initiating downloads.
    - Python tests in `zlibrary/src/test.py` passed after these changes.
- Verified `AsyncZlib.download_book` test coverage post-cleanup (Task 2.1). Commented out 1 obsolete test for `get_by_id`, added 4 new error handling unit tests to `zlibrary/src/test.py`. All 14 Python tests in `zlibrary/src/test.py` now pass, confirming ADR-002 alignment and improved robustness.
- **Related Entries**: [ActiveContext 2025-05-07 05:58:00], [`docs/project-plan-zlibrary-mcp.md:79-102`](docs/project-plan-zlibrary-mcp.md:79-102), [`docs/adr/ADR-002-Download-Workflow-Redesign.md`](docs/adr/ADR-002-Download-Workflow-Redesign.md)
### Pattern: MCP Server Testing Protocol - [2025-05-07 01:10:33]
- **Context**: Debugging and verifying changes to MCP servers, particularly those involving interaction with external systems or complex data flows (e.g., Node.js to Python bridge).
- **Problem**: Incorrect or incomplete testing procedures can lead to flawed diagnostics, repeated errors, wasted effort, and inability to confirm if changes have the intended effect. Basing diagnostic work on stale or unverified server states is unreliable.
- **Solution (Mandatory Protocol)**: When testing changes to an MCP server (especially after code modifications):
    1.  **Request Server Restart**: Explicitly ask the user to restart the relevant MCP server to ensure all code changes are active. Wait for user confirmation.
    2.  **Execute Test**: Perform the specific test action (e.g., `use_mcp_tool` with defined parameters) intended to verify the change.
    3.  **Check LATEST Log Entries**: After the test execution, use `read_file` to fetch the *latest* entries from relevant log files (e.g., `zlibrary_debug.log`, Node.js console output if available). Focus on entries generated *after* the server restart and test execution. Pay close attention to timestamps.
    4.  **Diagnose Based on Fresh Data**: Perform diagnostic work and formulate next steps *only* after analyzing the fresh log data from the latest test run.
- **Rationale**: This protocol ensures that diagnostics are based on the current state of the server and the actual outcome of recent changes, preventing cycles of incorrect assumptions and fixes.
- **Impact**: Improved reliability of debugging, faster issue resolution, reduced user frustration.
- **Related Interventions**: [See code-feedback.md - Intervention 2025-05-07 01:09:26]

---
### Progress - [2025-05-07 05:52:00]
- **`full_text_search` No-Result Behavior Test**:
    - Manual testing of the `full_text_search` tool with queries designed to yield no results ("zxcvbnmasdfghjklqwertyuiop1234567890zxcvbnmasdfghjklqwertyuiop" and "the epistemological ramifications of invisible pink unicorns in quantum chromodynamics") confirmed that the tool now correctly returns an empty list of books (`"books":[]`).
    - This behavior is an improvement over previously reported issues (e.g., FTS_TC006) where such queries returned unexpected results. The "no-result behavior" mentioned in [`docs/project-plan-zlibrary-mcp.md:24`](docs/project-plan-zlibrary-mcp.md:24) appears to be handled gracefully for these test cases.
- **Related Entries**: [ActiveContext 2025-05-07 05:52:00], [memory-bank/mode-specific/qa-tester.md - Test Execution Results 2025-05-07 05:52:00]

---
### Progress - [2025-05-06 21:57:33]
- **Token-Based `full_text_search` and `content_types` Parameter**:
    - Modified `zlibrary/src/zlibrary/libasync.py` to implement token extraction for `AsyncZlib.full_text_search`. The token is fetched from the `/s/` page and included in the `/fulltext/` API call.
    - Added a new optional `content_types: Optional[List[str]] = None` parameter to both `AsyncZlib.search` and `AsyncZlib.full_text_search` methods.
    - Ensured `languages`, `extensions`, and `content_types` are formatted as non-indexed array parameters in the URL. Extensions are uppercased.
    - The `full_text_search` now defaults to `type=phrase` and includes the extracted token.
- **Related Entries**: [ActiveContext 2025-05-06 21:57:33], [User Task 2025-05-06 21:52:18], [memory-bank/feedback/code-feedback.md - Entry 2025-05-06 19:08:06]
---
### Progress - [2025-05-06 18:23:51]
- **E2E Search Filter Failures (Phase 1, Task 1 - URL Format Changed to Non-Indexed)**:
    - Modified the `search` and `full_text_search` methods in `zlibrary/src/zlibrary/libasync.py` to use non-indexed URL parameter formatting for `languages` and `extensions` (e.g., `languages[]=value`).
    - This change was made based on direct user feedback clarifying that the Z-Library API expects non-indexed parameters, overriding the original task's objective which was to ensure indexed formatting.
- **Related Entries**: [ActiveContext 2025-05-06 18:23:33], [User Feedback 2025-05-06 18:23:01]
---
### Progress - [2025-05-06 18:06:15]
- **E2E Search Filter Failures (Phase 1, Task 1 - URL Format Verification)**:
    - Verified the URL parameter formatting for `languages` and `extensions` in the `search` and `full_text_search` methods within `zlibrary/src/zlibrary/libasync.py`.
    - Confirmed that both methods already correctly implement indexed formatting (e.g., `languages[0]=value`, `extensions[0]=value`).
    - No code changes were necessary for this specific task.
- **Related Entries**: [ActiveContext 2025-05-06 18:05:57]
---
### Progress - [2025-05-06 17:10:34]
- **E2E Search Filter Investigation (Phase 1, Task 1 - Partial Fix)**:
    - Fixed internal logic error in `zlibrary/src/zlibrary/libasync.py` for `full_text_search` tool (Issue FTS_TC009) related to single-word queries with `words:true` and `phrase:true`. The `words:true` flag is now correctly prioritized. Verification via `npm test` passed.
    - Investigation into other filter issues (`search_books` language filter; `full_text_search` language, extension, and no-result filters) indicates these are likely due to Z-Library website behavior (e.g., unsupported filter combinations, different parameter expectations for full-text search, or unexpected responses for no-result queries) rather than internal code errors in parameter passing or parsing.
- **Related Entries**: [ActiveContext 2025-05-06 17:10:34], [QA Tester Feedback 2025-05-06 13:18:00]
---
### Progress - [2025-05-06 16:31:22]
- **Project Plan Update (TDD & Regression Testing Emphasis)**:
    - Updated `docs/project-plan-zlibrary-mcp.md` based on user feedback.
    - Enhanced the "VI. General Procedures for All Phases" section to include:
        - Detailed "Test-Driven Development (TDD) Workflow" subsection: Outlines Red-Green-Refactor cycle, scope for TDD, and mode integration for TDD stages.
        - Explicit "TDD Integration" within the "Version Control" subsection: Details how TDD cycles integrate with Git (commits per cycle/feature, commit message conventions for TDD stages).
        - Strengthened "Verification and Regression Testing" subsection: Emphasizes post-task verification, specific regression checks after refactoring, and E2E re-testing milestones.
    - Mode delegation descriptions updated to reflect `tdd` mode's role in full TDD cycles and regression checks.
- **Related Entries**: [ActiveContext 2025-05-06 16:31:22], [GlobalContext Progress 2025-05-06 16:25:27] (Initial plan creation)
---
### Progress - [2025-05-06 16:25:27]
- **Project Plan Creation**:
    - Successfully created the comprehensive project plan document: `docs/project-plan-zlibrary-mcp.md`.
    - The plan details Phase 1 (V1 Release: cleanup, bug fixes, critical features like `get_book_metadata` and enhanced filenames), Phase 2 (Advanced Features: direct advanced search, architectural review), and Phase 3 (Ongoing Refinement).
    - Each task within the phases includes detailed architectural considerations: dependencies, potential challenges, technical approach, mode delegation, verification, and impact assessment.
    - User priorities and clarifications (e.g., `get_book_metadata` scope, deferred advanced search fields in `search_books`) have been incorporated.
- **Related Entries**: [ActiveContext 2025-05-06 16:25:27]
---
### Progress - [2025-05-06 14:02:42]
- **DBTF-BUG-001 Fix Test Verification**:
    - Ran full test suite (`npm test`) after applying the fix for DBTF-BUG-001.
    - All 4 test suites and 53 tests passed.
    - Console errors observed during the test run appear to be related to expected error handling paths in tests and did not cause failures.
    - The fix for DBTF-BUG-001 is confirmed to not introduce regressions caught by the automated test suite.
- **Related Entries**: [ActiveContext 2025-05-06 14:02:42], [GlobalContext Progress 2025-05-06 13:54:11]
---
### Progress - [2025-05-06 13:54:11]
- **`download_book_to_file` Bug Fix Verification (DBTF-BUG-001 & DBTF-BUG-002)**:
    - Successfully called `download_book_to_file` tool after applying the fix to `lib/python_bridge.py` (removing `book_id` kwarg) and after the user removed a conflicting file named `downloads`.
    - This verifies that the `TypeError` (DBTF-BUG-001) is resolved.
    - This also verifies that the `FileExistsError` (DBTF-BUG-002) is resolved by removing the conflicting file.
    - Book downloaded successfully to `downloads/4552708.epub`.
- **Related Entries**: [ActiveContext 2025-05-06 13:54:11], [GlobalContext Progress 2025-05-06 13:49:38], [memory-bank/mode-specific/debug.md - Issue DBTF-BUG-001], [memory-bank/mode-specific/debug.md - Issue DBTF-BUG-002]
---
### Progress - [2025-05-06 13:49:38]
- **`download_book_to_file` Bug Fix (DBTF-BUG-001)**:
    - Identified that `lib/python_bridge.py` was incorrectly passing `book_id` as a keyword argument to `AsyncZlib.download_book` in `zlibrary/src/zlibrary/libasync.py`.
    - The `AsyncZlib.download_book` function expects `book_details` (object) and `output_dir_str`, and can derive `book_id` from `book_details`.
    - Applied fix to `lib/python_bridge.py` to remove the redundant `book_id` keyword argument from the call.
- **Related Entries**: [ActiveContext 2025-05-06 13:49:38], [memory-bank/feedback/qa-tester-feedback.md - Bug ID: DBTF-BUG-001], [ActiveContext 2025-05-06 12:37:17], [GlobalContext Progress 2025-05-06 12:37:17]
---
### Progress - [2025-05-06 12:52:00]
- **`download_book_to_file` Fix Verification (TDD)**:
    - Added new unit tests to `zlibrary/src/test.py` for `AsyncZlib.download_book` covering:
        - Correct file path construction (e.g., `./downloads/BOOK_ID.extension`).
        - Mocked directory creation (`os.makedirs`).
        - Mocked file saving (`aiofiles.open` and write).
        - Correct return value (`str(actual_output_path)`).
    - Updated unit tests in `__tests__/python/test_python_bridge.py` for `python_bridge.download_book`:
        - Ensured correct parameters (including `book_id` and `output_dir_str`) are passed to the mocked `zlibrary.AsyncZlib.download_book`.
        - Verified handling of `process_for_rag` flag and `processed_output_format`.
        - Confirmed correct JSON response structure (`file_path`, `processed_file_path`).
        - Tested error propagation from the underlying library.
    - All new/updated Python tests for `download_book_to_file` pass at the library and bridge levels (`pytest`).
    - Full MCP application test suite (`npm test`) passed, indicating no regressions in other parts of the system from these changes.
    - The "Missing original file_path" error and the path handling bug for `download_book_to_file` are confirmed resolved by these tests.
- **Related Entries**: [ActiveContext 2025-05-06 12:52:00], [Task: Test Fixes for `download_book_to_file` Errors and Check Regressions], [GlobalContext Progress 2025-05-06 12:37:17] (Code mode changes)
---
### Progress - [2025-05-06 12:37:17]
- **`download_book_to_file` Fixes Implemented**:
    - Modified `zlibrary/src/zlibrary/libasync.py` (`AsyncZlib.download_book`):
        - Renamed `output_path: str` parameter to `output_dir_str: str`.
        - Changed return type annotation from `-> None:` to `-> str:`.
        - Added logic to construct `actual_output_path` using `book_details` (ID, extension) and `output_dir_str`.
        - Updated directory creation to use `output_directory` (derived from `output_dir_str`).
        - Updated file opening to use `actual_output_path`.
        - Changed final return to `str(actual_output_path)`.
        - Updated logging to refer to `actual_output_path`.
    - Modified `lib/python_bridge.py` (`download_book` function):
        - Updated the call to `zlib_client.download_book` to pass `output_dir_str=output_dir` due to parameter rename in `libasync.py`.
- **Objective**: Resolve "Missing original file_path" error and path handling bug.
- **Related Entries**: [See ActiveContext 2025-05-06 12:37:17], [See Task: Implement Fixes for `download_book_to_file` Errors], [See Debug Completion Report - ActiveContext 2025-05-06 12:35:22], [See SPARC MB Delegation Log Task [2025-05-06 12:31:34] Outcome]
---
### Progress - [2025-05-06 12:29:00]
- **`get_download_history` Fix Verification (TDD)**:
    - Added new unit tests to `zlibrary/src/test.py` covering:
        - Correct URL construction for `/users/downloads` endpoint in `zlibrary/profile.py`.
        - Successful fetching and parsing of mocked HTML (new and old structures) for `/users/downloads` by `DownloadsPaginator.parse_page` in `zlibrary/abs.py`.
        - Accurate extraction of download history items.
        - Handling of empty history and parse error states.
    - All new tests for `get_download_history` pass at the library level.
    - Full MCP application test suite (`npm test`) passed, indicating no regressions in other parts of the system.
    - Debug logging in `zlibrary/util.py` reviewed and deemed beneficial; recommended to keep.
- **Related Entries**: [See ActiveContext 2025-05-06 12:29:00], [See ActiveContext 2025-05-06 12:13:18] (code mode changes), [See GlobalContext Progress 2025-05-06 12:12:11] (code mode changes summary)
---
### Progress - [2025-05-06 12:12:11]
- **`get_download_history` Fix**:
    - Endpoint updated from `/users/dstats.php` to `/users/downloads` in `zlibrary/src/zlibrary/profile.py`.
    - Parser logic in `zlibrary/src/zlibrary/abs.py` (within `DownloadsPaginator.parse_page`) updated to correctly extract data (ID, date/time, title, book URL, re-download URL) from the new HTML structure (`tr.dstats-row` and its `td` children) of the `/users/downloads` page.
- **Related Entries**: [See ActiveContext 2025-05-06 12:11:44], [See GlobalContext Pattern: External API Endpoint Obsolescence - 2025-05-06 12:01:30]
---
### Progress - [2025-05-06 12:01:30]
- Diagnosed `get_download_history` empty response: Server returns 404 for `/users/dstats.php`.
- Response headers include a `Location: /users/downloads` redirect.
- Root cause: The `/users/dstats.php` endpoint is likely obsolete or incorrect.
- Recommendation: Update `zlibrary` Python library to use `/users/downloads` for download history and verify parsing logic for the new page structure.
- Related Entries: [See ActiveContext 2025-05-06 12:01:30], [See Debug Issue ZLIB-DSTATS-404]
---
### Progress - [2025-05-06 04:51:04]
- User decided to deprecate `get_recent_books` tool.
- Verification of `get_download_history` fix (Attempt 3) FAILED. `ParseError: Could not find a valid main content area for downloads list.` persists.
- Root cause for `get_download_history` may be that the Python library is not receiving the expected HTML page content, possibly due to session/login issues, rather than solely a parser selector problem in `zlibrary/src/zlibrary/abs.py`.
- Related Entries: [See ActiveContext 2025-05-06 04:51:04], [See Debug Completion 2025-05-06 04:50:12]
---
### Progress - [2025-05-06 04:50:12]
- **ParseError Fix Verification FAILED (Attempt 3):** The fix applied to `zlibrary/src/zlibrary/abs.py` for `DownloadsPaginator.parse_page` was not successful. The `get_download_history` tool still fails with `ParseError: Could not find a valid main content area for downloads list.`
- **Related Entries:** [See ActiveContext 2025-05-06 04:50:12], [See Task 2025-05-06 04:49:28], [See ActiveContext 2025-05-06 04:44:36 for original fix attempt by code mode]
---
### Progress - [2025-05-06 04:28:00]
- **ParseError Fix Verification FAILED (Attempt 2):** Attempted fixes for `ParseError`s in `get_recent_books` and `get_download_history` (related to `zlibrary/src/zlibrary/abs.py`) were not successful.
    - `get_recent_books`: Still fails with `ParseError: Could not find the book list items.` (New parsing logic for `SearchPaginator` looking for `div.itemFullText` and then `div.book-card-wrapper` or `div.book-item` elements failed).
    - `get_download_history`: Still fails with `ParseError: Could not find a valid main content area for downloads list.` (New parsing logic for `DownloadsPaginator` using `soup.body` resulted in an error because a valid content area could not be found).
- **Related Entries:** [See ActiveContext 2025-05-06 04:28:00], [See Task 2025-05-06 04:27:04], [See ActiveContext 2025-05-06 04:12:18 for attempted fix by code mode]
---
### Progress - [2025-05-06 04:06:57]
- **ParseError Fix Verification FAILED:** Attempted fixes for `ParseError`s in `get_recent_books` and `get_download_history` (related to `zlibrary/src/zlibrary/abs.py`) were not successful.
    - `get_recent_books`: Still fails with `ParseError: Could not find the book list.` (New parsing logic for `SearchPaginator` looking for `div.itemFullText` and then `z-bookcard` elements failed).
    - `get_download_history`: Fails with `AttributeError: 'NoneType' object has no attribute 'find'` (New parsing logic for `DownloadsPaginator` resulted in `soup.body` being `None`).
- **Related Entries:** [See ActiveContext 2025-05-06 04:06:31], [See Task 2025-05-06 04:05:46], [See ActiveContext 2025-05-06 03:55:15 for attempted fix by code mode]
---
### Progress - [2025-05-06 03:03:00]
- **ParseError Diagnosis Completed:** Investigated `ParseError`s for `get_recent_books` and `get_download_history`.
- **Root Cause:** HTML structural changes on the Z-Library website.
    - `get_recent_books`: `zlibrary/src/zlibrary/abs.py` (SearchPaginator) fails to find `<div id="searchResultBox">`.
    - `get_download_history`: `zlibrary/src/zlibrary/abs.py` (DownloadsPaginator) fails to find `<body>` or `<div class="dstats-table-content">`.
- **Related Entries:** [See ActiveContext 2025-05-06 03:03:00], [See Task 2025-05-06 03:01:17]
---
### Progress - [2025-05-06 01:38:00]
- **DevOps Task Completed:** Committed final Memory Bank updates (commit `53ba6e1`) reflecting the successful verification of the INT-001 fix chain. Working directory is clean.
- **Related Entries:** [See ActiveContext 2025-05-06 01:38:00]
---
${globalContextEntry}
### Progress - [2025-05-06 01:25:39]
- **DevOps Task Completed:** Committed verified regression fixes (INT-001 chain) and associated Memory Bank updates.
- **Commits:**
    - `3dd2dd6`: `fix(tests): Update assertions and deps post INT-001 fix chain` (Code fixes)
    - `09cca1b`: `chore(memory): Update MB logs for INT-001 regression fixes` (Memory Bank updates)
- **Related Entries:** [See ActiveContext 2025-05-06 01:25:13]
---
### Progress - [2025-05-06 01:22:30]
- **Final Verification Pass Completed:** Ran full test suite (`npm test`) after debug fixes for post-INT-001-REG-01 regressions. All tests passed (56 Jest tests, including implicit Pytest runs). Reviewed code changes (`requirements-dev.txt`, `__tests__/python/test_python_bridge.py`, `__tests__/index.test.js`) and confirmed alignment with debug context. Codebase is stable.
- **Related Entries:** [See ActiveContext 2025-05-06 01:22:03], [See Test Execution Results 2025-05-06 01:22:03]
---
### Progress - [2025-05-06 01:18:46]
- **Regressions Post INT-001-REG-01 Fix Resolved:** Investigated and fixed regressions reported by TDD [Ref: ActiveContext 2025-05-06 00:48:13].
    - Jest (`__tests__/zlibrary-api.test.js`): 15 failures were already resolved by INT-001-REG-01 fix.
    - Pytest (`__tests__/python/test_python_bridge.py`): 22 failures resolved by installing missing `httpx` dependency, ensuring local editable install of `./zlibrary`, and correcting outdated mock assertions/return value checks related to `save_processed_text` and `process_document`.
    - Jest (`__tests__/index.test.js`): 4 subsequent failures resolved by updating assertions to expect direct handler results instead of wrapped content.
- **INT-001 Fix Re-evaluation:** Confirmed original INT-001/INT-001-REG-01 fixes are sound and did not cause the latest regressions.
- **Verification:** Full test suite (`npm test`) now passes.
- **Related Entries:** [See ActiveContext 2025-05-06 01:18:46], [See Debug Issue REG-POST-INT001-FIX]
---
### Progress - [2025-05-05 23:42:47]
- **Regression Test FAIL (Post INT-001 Fix):** Ran full test suite (`npm test`) after fix for INT-001 (ZodError). 17 tests failed in `__tests__/zlibrary-api.test.js`. Failures indicate JSON parsing errors ("Unexpected token o in JSON") in the Node.js/Python bridge (`src/lib/zlibrary-api.ts`), suggesting the fix or related changes introduced a regression in how Python results are handled/parsed.
- **Related Entries:** [See ActiveContext 2025-05-05 23:42:47], [See Test Execution Results 2025-05-05 23:42:47]
---
### Progress - [2025-05-05 22:28:31]
- **INT-001 (ZodError) Re-investigation Resolved:** Re-investigated recurring ZodError ("Expected array, received undefined" at path 'content'). Confirmed previous fixes (capability declaration, `inputSchema` key) were still in place. Identified root cause as inconsistent `CallToolResponse` structure: error responses used `{ content: [...] }` while success responses returned the raw handler result object directly. Fixed by modifying `src/index.ts` to wrap successful results in `{ content: [result] }`. Verification via `use_mcp_tool` calls (`get_download_limits`, `search_books`) confirmed ZodError resolution.
- **Related Entries:** [See ActiveContext 2025-05-05 22:32:00], [See Debug Issue INT-001 - 2025-05-05 22:32:14], [See System Patterns 2025-05-05 22:32:14]
---
### Progress - [2025-05-05 02:00:05]
- **RAG Robustness Verification Completed (via Direct Execution):** Successfully verified EPUB, PDF, and TXT processing via direct Python execution after fixing several bugs (`TypeError`, `UnboundLocalError`, `AttributeError`). MCP tool verification remains blocked by ZodError (INT-001). Full test suite passed. Modified Python bridge to limit output during direct execution tests. [See Debug Issue RAG-Verify-01]
- **Related Entries:** [See ActiveContext 2025-05-05 01:58:04], [See Debug Issue INT-001 - 2025-04-14 18:22:33]
---
### Progress - [2025-05-02 18:30:06]
- **RAG Test Failures (ToC, PDF Integration):** Resolved externally via TDD session. Fix involved updating `is_toc_like` regex in `lib/rag_processing.py::_extract_and_format_toc`. All tests in `__tests__/python/test_rag_processing.py` now pass (49 passed, 1 xfail). [See Debug Session 2025-05-02 12:15:44 - 18:30:06]
---
### Decision Log - 2025-05-02 13:41:00
- **Decision**: Updated RooCode `mcp_settings.json` to use full paths for `node` and `npx` executables managed by NVM.
- **Rationale**: MCP servers launched via RooCode UI were failing with `SyntaxError` due to using an older system Node.js version (v12) instead of the NVM-managed v18. The RooCode execution environment did not inherit the NVM-modified `PATH`. Specifying the full path (`/home/loganrooks/.nvm/versions/node/v18.20.8/bin/node` and `/home/loganrooks/.nvm/versions/node/v18.20.8/bin/npx`) forces RooCode to use the correct version. [Related to Issue-ID: MCP-NODE-VERSION]
- **Alternatives**: Attempted sourcing `.bashrc`/`.zshrc`, downgrading dependencies (reverted).
- **Outcome**: `zlibrary-mcp` server now starts successfully. Other servers using `npx` should also use the correct version.

---
### Progress - 2025-05-02 13:41:00
- **Update**: Resolved prerequisite environment issue preventing `zlibrary-mcp` server startup within RooCode. The root cause was RooCode not using the NVM-managed Node.js version. Fix involved specifying full paths in `mcp_settings.json`. [See Decision Log - 2025-05-02 13:41:00]
- **Next Step**: Resume debugging the original RAG test failures.
- **[2025-05-01 19:28:40] - PDF Quality Heuristic Fix (Cycle 22)**
  - Status: Completed by `debug` mode.
  - Details: Resolved misclassification of `IMAGE_ONLY` PDFs in `lib/rag_processing.py::detect_pdf_quality`. Modified heuristic to prioritize very low text density. Target tests now pass.
  - Links: [Ref: ActiveContext 2025-05-01 19:28:20], [Ref: Debug Issue PDF-QUALITY-HEURISTIC-01]
- **[2025-05-01 1:54:35 PM] - TDD Cycle 22 Blockers Resolved**
  - Status: Completed by `debug` mode.
  - Details: Resolved function rename (`_analyze_pdf_quality` -> `detect_pdf_quality`) inconsistencies and Tesseract mocking issues (`TesseractNotFoundError`, `ImportError`, `TypeError`) in `lib/rag_processing.py` and `__tests__/python/test_rag_processing.py`. This unblocks TDD Cycle 22 (PDF Quality Detection).
  - Links: [Ref: ActiveContext 2025-05-01 1:54:35 PM], [Ref: Debug Issue TDD-CYCLE22-BLOCKERS]
### [2025-04-29 19:34:03] - Code - Decision: Slugify Logic
- **Decision**: Implemented `_slugify` function in `lib/rag_processing.py` to generate human-readable slugs (`author-title`) for filenames. Logic involves lowercasing, normalizing (ASCII/Unicode), replacing non-alphanumeric/non-word chars with spaces, collapsing spaces/hyphens to single hyphens, and stripping ends. Underscores are replaced in ASCII path, kept in Unicode path (`\w`).
- **Rationale**: Provides user-friendly filenames while handling various characters. Iteratively refined based on test failures.
- **Alternatives**: Simpler regex (failed edge cases), external slugify library (avoided adding dependency).
- **Impact**: Affects `save_processed_text` filename generation. Tests updated.

### [2025-04-29 19:34:03] - Code - Progress: Implemented Human-Readable Slugs
- **Status**: Completed
- **Details**: Modified `lib/rag_processing.py` (`_slugify`, `save_processed_text`) and `lib/python_bridge.py` (`download_book`) to generate filenames like `author-title-id.extension`. Updated tests in `__tests__/python/test_rag_processing.py` and `__tests__/python/test_python_bridge.py`. All relevant tests are passing.
- **Link**: [Ref: GlobalContext 2025-04-29 19:01:54]
[2025-04-28 10:40:30] - DevOps - Git Cleanup Complete - Checked status on `feature/rag-file-output`. Committed remaining uncommitted changes (code fixes, test adjustments, venv script, MB updates) in two logical commits (224de6f, b4a280c). Working directory is now clean.
[2025-04-28 12:55:24] - Integration - RAG Download Workflow Verified (SUCCESS) - Successfully tested `download_book_to_file` end-to-end on branch `feature/rag-file-output` (commit `f2d1b9c`). Fixed scraping selector in `libasync.py` and filename extension logic in `python_bridge.py`. Confirmed correct EPUB download (`downloads/3762555.epub`). [Ref: Integration Test Scenario RAG-DL-WF-01, Issue INT-RAG-DL-001 Resolved, Issue INT-RAG-FN-001 Resolved]
[2025-04-28 12:41:53] - Integration - RAG Download Workflow FAILED (Incorrect Content) - User feedback indicates `download_book_to_file` downloaded HTML instead of EPUB for book ID 3762555. Scraping logic in `libasync.py` is likely flawed. [Ref: Integration Test Scenario RAG-DL-WF-01, Issue INT-RAG-DL-001]
[2025-04-28 12:30:11] - Integration - RAG Download Workflow Verified (Premature) - Successfully tested `download_book_to_file` end-to-end on branch `feature/rag-file-output` (commit `f2d1b9c`). Fixed `AttributeError` and `TypeError` in `zlibrary/src/zlibrary/libasync.py`. Download confirmed working. [Ref: Integration Test Scenario RAG-DL-WF-01]
[2025-04-28 13:22:47] - Debug - Resolved Pytest Regression (Post-Integration) - Fixed 4 failing tests in `__tests__/python/test_python_bridge.py` by correcting outdated assertions expecting directory paths instead of full file paths. Tests verified passing. Commit: 26cd7c8. [See Issue REG-PYTEST-001]
- **[2025-04-28 22:04:00] - DocsWriter - Completed Documentation Update** - Updated `README.md` to reflect current project status, recent fixes (`get_download_history`, `get_recent_books`), tool deprecation (`get_download_info`), passing test suites, and ADR-002 alignment. Verified consistency with related architecture/spec documents.
- **[2025-04-29 09:35:19] - TDD - Refactor Completed (RAG Markdown Generation)** - Refactored `lib/python_bridge.py` and `__tests__/python/test_python_bridge.py` for clarity and standards. All tests pass. Commit: `e943016`. [Ref: ActiveContext 2025-04-29 09:35:19]
- **[2025-04-29 09:55:59] - Feature: RAG Markdown Generation - QA Testing FAILED**
  - Status: Failed QA
### [2025-04-29 19:01:54] New Objectives Post-Refinement
- **File Naming Convention:** Implement human-readable slugs (`author-title-id.extension`) for processed files to improve user experience. (Priority: High)
- **RAG Robustness Enhancement:** Improve testing with real-world documents (philosophy focus), investigate PDF extraction quality (PyMuPDF vs. alternatives like pdfminer.six), potentially add quality detection/preprocessing/OCR. (Priority: Medium/Large Effort)
- **Current State:** Refinement phase complete. Merged `feature/rag-generation` to `main`. Current commit: `647ba488186ecc9189b5d92822d52bef556c0c17`.
  - Mode: `qa-tester`
  - Details: QA testing revealed significant issues with Markdown output quality and correctness, particularly with heading levels and list formatting. See feedback for details. Feature requires refinement/debugging.
  - Commit: `e943016` (tested)
  - Related Context: [activeContext.md 2025-04-29 09:55:59], [qa-tester-feedback.md QA Findings 2025-04-29 09:55:59]
- **[2025-04-29 09:48:39] - Feature: RAG Markdown Generation - Documentation Complete**
  - Status: Completed
  - Mode: `docs-writer`
  - Details: Updated `docs/rag-pipeline-implementation-spec.md` to reflect the new Markdown output option and logic.
  - Commit: `e943016` (documented)
  - Related Context: [activeContext.md 2025-04-29 09:48:39], [docs-writer.md Documentation Plan Update 2025-04-29 09:48:39]
- **[2025-04-29 09:43:58] - Feature: RAG Markdown Generation - Final TDD Verification Complete**
### [2025-04-29 21:16:57] Decision: Version Control for Delegated Tasks
- **Decision:** Upon successful task completion and verification, delegated modes must create two separate commits:
    1. Commit for the primary work (code, documentation, etc.).
    2. Commit for the associated Memory Bank updates.
- **Rationale:** Ensures atomicity and clear separation between functional changes and context logging. Facilitates easier review and rollback if necessary.
- **Applies To:** All modes performing modifications that require version control.
  - Status: Completed
  - Mode: `tdd`
  - Details: Final verification pass completed for commit `e943016`. Test coverage and clarity deemed adequate. All tests pass. Feature ready for Completion phase.
  - Commit: `e943016` (verified)
  - Related Context: [activeContext.md 2025-04-29 09:43:58], [tdd.md Verification Summary 2025-04-29 09:43:58]
- **[2025-04-29 09:39:34] - Feature: RAG Markdown Generation - Integration Verified**
- **[2025-04-29 09:48:39] - Pattern: Configurable Output Format (RAG)**
  - Description: The RAG processing pipeline now supports configurable output formats (`txt`, `markdown`) via the `output_format` parameter in relevant functions (`process_document_for_rag`). Markdown output includes basic structural elements derived from the source document.
  - Implementation: `lib/python_bridge.py` (commit `e943016`)
### [2025-04-29 19:46:16] Milestone: Human-Readable File Slugs Implemented
- **Status:** Completed by `code` mode.
- **Commit:** `1f4f2c5` on `main`.
### [2025-04-30 04:44:05] Progress Update: RAG Robustness Implementation (Partial)
- **Status:** Partially Completed by `tdd` mode (Paused due to context limit).
- **Work Done:** Test fixture setup and image-only PDF detection implemented.
- **Commit:** `feat(rag): Add test fixture setup and image-only PDF detection` (Hash pending user confirmation).
- **Next Steps:** Delegate remaining implementation tasks (Poor Text Extraction, OCR Points, EPUB Review, Preprocessing) to `tdd`.
- **Link to Delegation:** [Ref: SPARC MB Delegation Log 2025-04-29 21:18:30]
- **Link to ActiveContext:** [Ref: ActiveContext 2025-04-30 04:44:05]
### [2025-04-29 21:10:14] Milestone: RAG Robustness Specification Complete
- **Status:** Completed by `spec-pseudocode` mode.
- **Deliverable:** `docs/rag-robustness-enhancement-spec.md` (Commit: `d96a904`)
- **Details:** Specification covers real-world testing, PDF quality analysis (PyMuPDF vs. alternatives, OCR integration), and EPUB review. Includes pseudocode and TDD anchors.
- **Memory Bank Update Commit:** `5ad414c`
- **Link to Delegation:** [Ref: SPARC MB Delegation Log 2025-04-29 19:47:12]
### Progress - [2025-05-06 01:27:34]
- **INT-001 Fix Chain Completed:** Orchestration completed for resolving the INT-001 ZodError and subsequent regressions (INT-001-REG-01, Jest/Pytest assertion/dependency issues).
- **Verification:** Fixes were verified by `debug` and `tdd` modes, confirming the full test suite (`npm test`) passes.
- **Commits:** Changes committed by `devops` mode to `feature/rag-robustness-enhancement` branch: `3dd2dd6` (code fixes), `09cca1b` (MB updates), `387d683` (final MB update).
- **Status:** Codebase stable, tests passing. Task complete.
- **Related Entries:** [See ActiveContext 2025-05-06 01:27:12], [See DevOps Completion 2025-05-06 01:27:12], [See TDD Completion 2025-05-06 01:23:32], [See Debug Completion 2025-05-06 01:20:33]
---
- **Details:** Implemented `author-slug-title-slug-book_id.extension` format in `lib/rag_processing.py` and updated callers/tests.
- **Link to Delegation:** [Ref: SPARC MB Delegation Log 2025-04-29 19:02:43]
  - Specification: `docs/rag-markdown-generation-spec.md`
  - Documentation: `docs/rag-pipeline-implementation-spec.md`
  - Status: Completed
  - Mode: `integration`
  - Details: Verified integration of commit `e943016`. Full test suite (`npm test`) passed. No regressions detected.
  - Commit: `e943016` (verified)
  - Related Context: [activeContext.md 2025-04-29 09:39:34], [integration.md Test Scenario RAG-MD-INT-VERIFY-01]
- **[2025-04-29 09:36:33] - Feature: RAG Markdown Generation - TDD Refactor Complete**
  - Status: Completed
  - Mode: `tdd`
  - Details: Refactored implementation (`lib/python_bridge.py`) and tests (`__tests__/python/test_python_bridge.py`) for clarity and maintainability. All tests pass.
  - Commit: `e943016`
  - Related Context: [activeContext.md 2025-04-29 09:36:33], [tdd.md TDD Cycle Log 2025-04-29 09:36:33]
- **[2025-04-29 11:11:06] - Debug - Resolved RAG PDF Footnote Test Failure** - Debug mode successfully identified and fixed the root cause of the `test_rag_markdown_pdf_formats_footnotes_correctly` failure. The issue was logic errors (erroneous `continue`, duplicated block, extra newline) in `lib/python_bridge.py`, not a string cleaning problem. Fixes applied. [Ref: ActiveContext 2025-04-29 11:11:06, Debug Issue RAG-PDF-FN-01]
- **[2025-04-29 10:56:55] - Debug - RAG Markdown Fix BLOCKED (Early Return)** - Debug mode returned early while attempting to fix QA failures for RAG Markdown generation (commit `e943016`). A persistent issue prevents cleaning the leading period (`.`) from footnote text during PDF processing (`lib/python_bridge.py`, `test_rag_markdown_pdf_formats_footnotes_correctly`), despite trying standard string methods (`lstrip`, `re.sub`, slicing). Requires deeper investigation. [Ref: ActiveContext 2025-04-29 10:56:55]
- **[2025-04-29 11:11:06] - Debug - Resolved RAG PDF Footnote Formatting Bug** - Fixed `test_rag_markdown_pdf_formats_footnotes_correctly` failure in `lib/python_bridge.py`. Root cause was a combination of an erroneous `continue` statement and an extra newline in the footnote separator. Test now passes. [Ref: ActiveContext 2025-04-29 11:11:06, Debug Issue RAG-PDF-FN-01]
- **[2025-04-29 16:36:11] - Fix: MCP Result Format** - Modified `src/index.ts` `tools/call` handler to return standard `{ result: value }` format. Tests passed. Commit: `47edb7a`. [Ref: ActiveContext 2025-04-29 16:36:11]
- **[2025-04-29 17:00:00] - HolisticReview - Post-Refinement Assessment Complete** - Reviewed workspace after recent refactoring/fixes. Test suite passes. Integration points verified (RAG refactor, MCP result format). Documentation updated (README, ADRs, Specs). Obsolete `get_book_by_id` references removed from tests/code. Debug logs removed, error logging improved. Minor findings: `lib/rag_processing.py` slightly over line limit, `zlibrary/src/zlibrary/abs.py` significantly over (deferred), utility script `get_venv_python_path.mjs` at root, unused Zod schema remains. Project deemed ready for final checks/deployment prep.
### Progress - [2025-05-06 01:53:52]
- **INT-001 ZodError Verification:** Successfully verified the resolution of INT-001 via a `use_mcp_tool` call to `zlibrary-mcp::get_download_limits`. The call completed without the "Expected array, received undefined" ZodError or other critical errors.
- **Related Entries:** [See ActiveContext 2025-05-06 01:53:52], [See Debug Issue INT-001 - 2025-05-05 22:28:51]
---
### Progress - [2025-05-06 02:05:11]
- **MCP Response Fix Completed:** Modified `src/index.ts` `tools/call` handler to return the raw result object (`{ content: [result] }`) instead of a stringified text object. This resolves the incorrect data return issue reported after the INT-001 fix.
- **Verification:** Build (`npm run build`) and relevant tests (`npm test __tests__/index.test.js`) passed successfully.
- **Related Entries:** [See ActiveContext 2025-05-06 02:05:11], [See System Patterns 2025-05-06 02:05:11], [See GlobalContext Progress 2025-05-05 22:28:31] (INT-001 Fix)
---
### Progress - [2025-05-06 02:24:48]
- **MCP Data Return Fix Verified:** Successfully fixed incorrect data return for `get_download_limits`. The root cause was identified in `lib/python_bridge.py`, where the `main` function was not outputting the result in the doubly-wrapped JSON structure expected by `callPythonFunction` in `src/lib/zlibrary-api.ts`.
- **Changes:**
    - Modified `lib/python_bridge.py` (lines 353-360) to ensure all Python function results are printed in the format: `json.dumps({ "content": [{ "type": "text", "text": json.dumps(actual_python_result) }] })`.
    - Reverted an earlier incorrect change in `src/index.ts` (line 331) back to `return { content: [{ type: 'text', text: JSON.stringify(result) }] };`.
- **Verification:** The fix was confirmed by a successful `use_mcp_tool` call to `get_download_limits`, which returned the correct data object. Build and unit tests also passed.
- **Related Entries:** [See ActiveContext 2025-05-06 02:24:48], [See System Patterns 2025-05-06 02:24:48], [See User Feedback 2025-05-06 02:07:05]
---
### Progress - [2025-05-06 02:40:36]
- **MCP Data Flow & RAG Tooling Fixes:**
    - Corrected Python bridge (`lib/python_bridge.py`) output to consistently use a doubly-wrapped JSON structure (`json.dumps({ "content": [{ "type": "text", "text": json.dumps(actual_python_result) }] })`) for all tool calls. This resolved the primary issue of incorrect data (e.g., status dicts) being returned to the client for tools like `get_download_limits`.
    - Fixed `asyncio` usage in `lib/rag_processing.py` (added `asyncio` import, made `process_txt` async, and correctly awaited its call in `lib/python_bridge.py`). This resolved `NameError` and `RuntimeError: asyncio.run() cannot be called from a running event loop` during `process_document_for_rag` calls.
- **Verification:**
    - `get_download_limits`, `search_books`, `full_text_search`, `process_document_for_rag`: All successfully verified via `use_mcp_tool` after fixes.
    - `get_recent_books`, `get_download_history`, `download_book_to_file`: These tools continue to fail due to errors originating from the external `zlibrary` Python library (likely website parsing/scraping issues or changes in the Z-Library website itself), not the MCP data flow.
- **Noted Issue:** User reported that `download_book_to_file` created an extensionless file named `downloads` instead of a `./downloads` directory. This is a separate issue to be investigated.
- **Related Entries:** [See ActiveContext 2025-05-06 02:40:36], [See System Patterns 2025-05-06 02:24:48], [User Feedback 2025-05-06 02:07:05], [User Feedback 2025-05-06 02:29:51], [User Feedback on downloads file]
---
## Progress
- **[2025-05-06 00:33:00] - Regression INT-001-REG-01 Resolved:** Fixed JSON parsing errors in `__tests__/zlibrary-api.test.js` caused by INT-001 fix. Required ensuring `callPythonFunction` used `text` mode with double parsing, removing extra wrapping in `src/index.ts` handlers, and correcting test mocks. Verified via `npm test __tests__/zlibrary-api.test.js`. [See Debug Issue INT-001-REG-01]
---
- **[2025-05-05 03:55:59] - DocsWriter - Documentation Update Completed (RAG Robustness)** - Updated `README.md` and `docs/rag-pipeline-implementation-spec.md` to reflect the implementation of RAG robustness enhancements (PDF quality detection, OCR, preprocessing). [Ref: Task 2025-05-05 03:46:21]
- **[2025-05-03 17:55:55] - TDD Cycle 24 (EPUB Front Matter) - Red Phase Completed** - Added failing test `test_process_epub_removes_front_matter`. [Ref: ActiveContext 2025-05-03 17:55:55]
- **[2025-05-02 05:15:30] - DevOps Task Completed (Git Debt Cleanup)** - Staged and committed remaining RAG test framework changes and MB updates. Commit: `5d156d3`. [Ref: Task 2025-05-02 05:14:35]
- **[2025-05-02 04:42:28] - DevOps Task Completed (Commit Cycle 23)** - Investigated staging/committing TDD Cycle 23 (Garbled Text). Confirmed via `git log` that changes were included in commit `13c826b` (TDD Cycle 21). No separate commit required. [Ref: Task 2025-05-02 03:16:40, ActiveContext 2025-05-02 04:42:02]
- **[2025-05-02 03:26:27] - DevOps Task Completed (Commit Cycle 22)** - Investigated staging/committing TDD Cycle 22 (PDF Quality) changes. Found they were already included in commit `13c826b`. No new commit required. [Ref: Task 2025-05-02 03:23:10]
- **[2025-05-02 03:19:43] - DevOps Task Completed** - Committed OCR refactor (TDD Cycle 21) changes to `lib/rag_processing.py` and `__tests__/python/test_rag_processing.py`. Commit: `13c826b`. [Ref: Task 2025-05-02 03:16:40]
- **[2025-05-02 02:41:32] - TDD Cycle 23 (Garbled Text Detection) Completed**
  - Status: Completed by `tdd` mode.
  - Details: Implemented heuristics (non-alpha ratio, repetition) in `lib/rag_processing.py::detect_garbled_text` to pass tests added in Red phase. Also fixed unrelated bug in `detect_pdf_quality` (empty PDF check order).
  - Links: [Ref: ActiveContext 2025-05-02 02:41:32]
- **[2025-05-02 02:33:00] - TDD Cycle 23 (Garbled Text) - Green Phase Unblocked**
  - Status: Unblocked by `debug` mode.
  - Details: Investigation revealed `detect_garbled_text` function was already present in `lib/rag_processing.py`, contrary to reports of tool failures preventing its addition. Pytest confirmed function existence and relevant test execution (xfail/xpass). 6 unrelated test failures were noted for separate investigation.
  - Links: [Ref: ActiveContext 2025-05-02 02:33:00], [Ref: Debug Issue TDD-CYCLE23-TOOL-FAILURE]
- **[2025-05-01 11:18:10] - RAG Testing Framework - TDD Cycle 13 Completed**
  - Status: Completed by `tdd` mode.
  - Details: Completed Refactor phase for Cycle 13 (Determine Pass/Fail Noise Check) using `write_to_file` workaround for previous `apply_diff` issues. Refactored `determine_pass_fail` logic and updated tests. Pytest suite passes (19/19).
  - Links: [Ref: ActiveContext 2025-05-01 11:18:10], [Ref: tdd.md TDD Cycle Log 2025-05-01 11:18:10]
- **[2025-05-01 03:08:48] - RAG Testing Framework - Conflicting Definition Resolved**
  - Status: Completed by `debug` mode.
  - Details: Resolved persistent `AssertionError` in `test_evaluate_output_returns_expected_keys`. Root cause was conflicting definitions of `evaluate_output` in `scripts/run_rag_tests.py`. Removed the duplicate definition. Test now passes, unblocking TDD Cycle 6.
  - Links: [Ref: ActiveContext 2025-05-01 03:08:28], [Ref: Debug Issue RAG-TEST-CONFLICT-01]
- **[2025-05-01 03:03:23] - RAG Testing Framework Implementation - Blocked Again**
  - Status: Blocked (Returned Early by `tdd` mode).
  - Details: Resumed implementation after mocking fix. Completed TDD Cycle 5 Refactor. Blocked during TDD Cycle 6 (Green) by persistent `AssertionError` in `test_evaluate_output_returns_expected_keys`, suggesting test runner executing outdated code despite troubleshooting. Context size reached 83%, triggering Delegate Clause. Requires investigation into test environment/caching.
  - Links: [Ref: ActiveContext 2025-05-01 03:03:51], [Ref: SPARC MB Delegation Log 2025-05-01 02:56:06], [Ref: tdd-feedback.md 2025-05-01 03:03:23]
- **[2025-05-01 03:01:49] - RAG Testing Framework Implementation - Blocked (TDD Cycle 6)**
  - Status: Blocked (Returned Early by `tdd` mode).
  - Details: Implementation resumed after mocking fix. Cycle 5 completed (Refactor: Type hints). Cycle 6 (Placeholder Structure) blocked by persistent `AssertionError` in `test_evaluate_output_returns_expected_keys`. Test environment appears to be executing outdated code despite cache clearing and reload attempts. Requires deeper investigation into Python/pytest caching or import mechanisms.
  - Links: [Ref: ActiveContext 2025-05-01 03:01:49], [Ref: tdd-feedback.md 2025-05-01 03:01:49]
- **[2025-05-01 02:55:24] - RAG Test Framework Mocking Issue Resolved**
  - Status: Completed by `debug` mode.
  - Details: Investigated persistent `StopIteration`/`RuntimeError` in `test_run_single_test_calls_processing_and_eval`. Identified root cause as mock state leakage from a preceding test using `unittest.mock.patch`. Fixed by refactoring the preceding test to use `mocker.patch` (from `pytest-mock`) for proper isolation. Test suite `__tests__/python/test_run_rag_tests.py` now passes. Commit: `eb0494c`. Blocker for RAG testing framework implementation is resolved.
  - Links: [Ref: ActiveContext 2025-05-01 02:55:24], [Ref: SPARC MB Delegation Log 2025-05-01 02:49:40], [Ref: debug.md 2025-05-01 02:55:24], [Ref: System Patterns 2025-05-01 02:55:24] (To be added)
- **[2025-05-01 02:54:03] - RAG Testing Framework Mocking Error - Resolved**
  - Status: Resolved by `debug` mode.
  - Details: Fixed persistent `StopIteration`/`RuntimeError` in `__tests__/python/test_run_rag_tests.py` by refactoring the preceding test (`test_main_loads_manifest_and_runs_tests_revised`) to use `mocker.patch` instead of `unittest.mock.patch`, preventing mock state leakage. Commit: `eb0494c`.
  - Links: [Ref: ActiveContext 2025-05-01 02:54:03], [Ref: Debug Issue RAG-MOCK-LEAK-01]
- **[2025-05-01 02:37:29] - RAG Testing Framework Implementation - Blocked**
  - Status: Blocked (Returned Early by `tdd` mode).
  - Details: Implementation of `scripts/run_rag_tests.py` structure (Cycles 1-4) completed. Blocked by persistent mocking/patching errors (`StopIteration`/`RuntimeError`) during TDD Cycle 5 (`run_single_test`). Context size also reached 54%. Requires investigation into mocking strategy or alternative testing approach for `run_single_test`.
  - Links: [Ref: ActiveContext 2025-05-01 02:37:29], [Ref: SPARC MB Delegation Log 2025-05-01 01:56:37], [Ref: tdd-feedback.md 2025-05-01 02:37:29]
- **[2025-05-01 01:52:43] - Documentation Cleanup Completed**
  - Status: Completed by `docs-writer` mode.
  - Details: Reviewed documentation files. Archived 7 obsolete files (related to old ID lookup, QA reports, etc.) to `docs/archive/`. Commit: `d05c05b`. Identified 4 files needing updates (`rag-pipeline-implementation-spec.md`, `architecture/rag-pipeline.md`, `pdf-processing-implementation-spec.md`, `zlibrary_repo_overview.md`).
  - Links: [Ref: ActiveContext 2025-05-01 01:52:43], [Ref: SPARC MB Delegation Log 2025-05-01 01:31:58]
- **[2025-05-01 01:51:18] - DevOps Task Completed** - Archived obsolete documentation files (`docs/internal-id-lookup-spec.md`, `docs/search-first-id-lookup-spec.md`, `docs/rag-output-qa-report.md`, `docs/codebase-status-report-20250414.md`, `docs/mcp-client-tool-failure-analysis.md`, `docs/mcp-server-comparison-report.md`, `docs/migration-strategy-evaluation-INT001.md`) to `docs/archive/`. Commit: `d05c05b`. [Ref: Task 2025-05-01 01:46:00]
- **[2025-05-01 01:31:01] - Feature: RAG Robustness Enhancements - Completed**
  - Status: Completed by `tdd` mode.
  - Details: Implemented EPUB handling, ToC formatting, PDF Quality Detection (with heuristic limitations noted), and OCR integration according to spec `docs/rag-robustness-enhancement-spec.md`. Test suite passes (40/42). Dependencies `pytesseract`, `pdf2image` added.
  - Links: [Ref: ActiveContext 2025-05-01 01:31:01], [Ref: SPARC MB Delegation Log 2025-04-29 21:18:30], [Ref: GlobalContext 2025-04-30 04:44:05] (Previous Partial Progress)
- **[2025-04-29 17:13:04] - Integration - Final Integration Check Completed** - Verified workspace state (commit 70687dc), sanity checked core components, reviewed documentation. Confirmed readiness post-refinement/cleanup.
- **[2025-04-29 17:05:11] - Remove Unused Zod Schema - Completed** - Removed `GetDownloadInfoParamsSchema` from `src/index.ts`. Tests passed. Commit: 70687dc. [Ref: Task 2025-04-29 17:02:59]
- **[2025-04-29 17:01:20] - Cleanup Root Utility Script - Completed** - Moved `get_venv_python_path.mjs` to `scripts/`. Verified no references and tests pass. [Ref: Task 2025-04-29 16:58:50]
- **[2025-04-29 16:31:39] - DocsWriter - Documentation Update (Deprecate `get_book_by_id`)** - Removed references to the deprecated `get_book_by_id` tool from `docs/internal-id-lookup-spec.md`, `docs/search-first-id-lookup-spec.md`, and `docs/architecture/rag-pipeline.md`. This aligns documentation with ADR-003 and code removal (commit `454c92e`).
- **[2025-04-29 16:27:00] - Code - Deprecated `get_book_by_id` Tool** - Removed tool definition, Node.js handler, Python function, and associated tests. Verified test suites pass. Commit: `454c92e`. [Ref: Task 2025-04-29 16:13:50, Decision-DeprecateGetBookByID-01]
- **[2025-04-29 15:52:56] - Refactor Python Bridge - Completed** - Extracted RAG processing logic from `lib/python_bridge.py` to `lib/rag_processing.py`. Verified with tests. Awaiting commit confirmation.
- **[2025-04-29 15:27:08] - TDD - Xfailed Test Investigation Complete** - Investigated 3 xfailed tests in `__tests__/python/test_python_bridge.py`. Confirmed they remain `XFAIL` for valid reasons. No code changes made. [Ref: ActiveContext 2025-04-29 15:27:08]
- **[2025-04-29 15:22:52] - TDD - Full Regression Test Suite Verification** - Completed full regression test (`npm test`) after debug fixes (commit `079a182`). All tests passed. No regressions found. [Ref: ActiveContext 2025-04-29 15:22:52]
- **[2025-04-29 15:19:52] - Debug - Resolved Pytest Failures (Post-ImportError Fix)** - Fixed 10 pytest failures in `__tests__/python/test_python_bridge.py` that emerged after commit `8ce158f`. Failures were due to removed helper functions, incorrect mock assertions, and outdated error handling expectations. Tests now pass (44 passed, 3 xfailed). Commit: `079a182`. [Ref: ActiveContext 2025-04-29 15:19:11, Debug Issue PYTEST-FAILURES-POST-8CE158F]
- **[2025-04-29 14:12:00] - Debug - Resolved Pytest Collection Errors** - Fixed `ImportError` (missing `process_document` function in `lib/python_bridge.py`) and subsequent `NameError` (missing `import python_bridge` in `__tests__/python/test_python_bridge.py`) that occurred during `pytest --collect-only` after `tdd` refactoring. Collection now successful. Commit: `8ce158f`. [Ref: ActiveContext 2025-04-29 14:12:00]
- **[2025-04-29 12:03:44] - Debug - Resolved Pytest Regressions (RAG Footnote Fix)** - Fixed 10 pytest failures in `__tests__/python/test_python_bridge.py` introduced after the RAG footnote fix. Failures were due to: outdated test logic assuming old download methods, incorrect error handling expectations, `UnboundLocalError` in PDF markdown formatting, and incorrect test assertions/setup. Pytest suite now passes. [Ref: ActiveContext 2025-04-29 12:03:44, Debug Issue RAG-PDF-FN-01-REGRESSION]
- **[2025-04-29 10:02:50] - Debug - Applied Fixes for RAG Markdown QA Failures** - Modified `lib/python_bridge.py` to address QA issues: applied cleaning (null chars, headers/footers) to Markdown output for PDFs, improved list detection/formatting heuristics for PDFs, added specific TOC handling for EPUB lists, and refined footnote detection/formatting for both PDF and EPUB. [Ref: ActiveContext 2025-04-29 10:02:50]
- **[2025-04-29 09:55:10] - QA - RAG Markdown Generation FAILED** - QA testing for the RAG Markdown generation feature (commit `e943016`) completed. The feature failed due to significant deviations from the specification (`docs/rag-markdown-generation-spec.md`), particularly in list and footnote generation for both PDF and EPUB, and heading detection/cleaning for PDF. See `memory-bank/feedback/qa-tester-feedback.md` [2025-04-29 09:52:00] for details.
- **[2025-04-29 09:47:33] - DocsWriter - Documented RAG Markdown Generation** - Updated `docs/rag-pipeline-implementation-spec.md` to reflect the implementation and verification of the RAG Markdown generation feature (commit `e943016`), clarifying `output_format` and linking to the relevant spec (`docs/rag-markdown-generation-spec.md`).
- **[2025-04-29 09:38:41] - Integration - Verified RAG Markdown Generation Integration** - Confirmed successful integration of the RAG Markdown structure generation feature (commit `e943016`). Full test suite (`npm test`) passed. [Ref: ActiveContext 2025-04-29 09:38:41]
- **[2025-04-29 03:01:59] - Code - TDD Green Completed (RAG Markdown Generation)** - Implemented Markdown generation logic in `lib/python_bridge.py` based on spec `docs/rag-markdown-generation-spec.md`. Pytest confirms target tests now pass (16 xpassed). Commit: `215ec6d`. [Ref: ActiveContext 2025-04-29 03:01:59]
- **[2025-04-29 03:01:59] - Code - TDD Green Completed (RAG Markdown Generation)** - Implemented Markdown generation logic in `lib/python_bridge.py` based on spec `docs/rag-markdown-generation-spec.md`. Pytest confirms target tests now pass (16 xpassed). [Ref: ActiveContext 2025-04-29 03:01:59]
- **[2025-04-29 02:51:06] - SPARC - Delegate Clause Triggered (Context 134%)** - Handing over orchestration before TDD Green phase due to high context. [Ref: ActiveContext 2025-04-29 02:51:06]
- **[2025-04-29 02:48:54] - TDD - Red Phase Completed (RAG Markdown Generation)** - Added failing tests (`@pytest.mark.xfail`) to `__tests__/python/test_python_bridge.py` for refined Markdown structure generation (PDF/EPUB). Tests confirmed xfailing. Commit: 05985b2. [Ref: ActiveContext 2025-04-29 02:48:54]
- **[2025-04-29 02:42:55] - SpecPseudo - Completed RAG Markdown Generation Specification** - Defined strategy using refined `PyMuPDF` heuristics and `BeautifulSoup` logic. Created spec `docs/rag-markdown-generation-spec.md`. [Ref: ActiveContext 2025-04-29 02:42:55]
- **[2025-04-29 02:33:00] - QA - RAG Output Re-evaluation (Commit `60c0764`)** - Re-tested `process_document_for_rag` against `docs/rag-output-quality-spec.md`. PDF processing significantly improved (noise reduced, Text PASS, MD PARTIAL/FAIL). EPUB processing unchanged (Text PASS, MD FAIL). TDD refinements did not fix Markdown structure issues. [Ref: QA Test Execution 2025-04-29 02:33:00]
- **[2025-04-28 20:49:00] - TDD - Completed `get_recent_books` Implementation** - Implemented `get_recent_books` in `lib/python_bridge.py` and added tests. Fixed regressions in `download_book` tests. All relevant tests pass. Commit: 75b6f11.
- **[2025-04-28 17:31:01] - Debug - Completed `get_download_info` Investigation** - Analyzed tool errors, dependency on ID lookup, and redundancy with ADR-002 workflow. Recommended deprecation. [See Debug Report 2025-04-28 17:31:01]
- **[2025-04-28 17:03:01] - SpecPseudo - Verified RAG Spec Alignment** - Confirmed `docs/rag-pipeline-implementation-spec.md` (v2.1) aligns with ADR-002 regarding the `download_book_to_file` workflow (using `bookDetails` from `search_books`). No changes required.
[2025-04-28 10:04:09] - Debug - Resolved Python test failures (`test_python_bridge.py`) related to PDF processing mocks during TDD Refactor phase. All Python and JS tests now pass. [See Debug Issue TDD-Refactor-Block-PyTest-20250428]
- **[2025-04-28 04:00:05] - Debug - Resolved TDD Green Phase Blockage (Python Tests)** - Investigated and fixed issues in `lib/python_bridge.py` and `__tests__/python/test_python_bridge.py` that prevented TDD Green Phase completion. Refactored tests, corrected assertions, fixed return values, and marked obsolete tests as xfail. `pytest` now exits 0. [See Issue TDD-GREEN-BLOCK-20250428]
### Product: RAG Robustness Documentation Update - [2025-05-05 03:56:18]
- **Context**: Documentation updated to reflect the implementation of RAG robustness enhancements.
- **Changes**: Updated `README.md` (status, architecture, features) and `docs/rag-pipeline-implementation-spec.md` (Python bridge details, dependencies, TDD anchors) to include PDF quality detection, conditional OCR, preprocessing (front matter/ToC), and garbled text detection.
- **Status**: Documentation Updated.
- **Related**: `README.md`, `docs/rag-pipeline-implementation-spec.md`, `docs/rag-robustness-enhancement-spec.md`, [ActiveContext 2025-05-05 03:55:29]
# Product Context
### Product: Enhanced Filename Convention Specification - [2025-05-07]
- **Context**: Specification created for generating user-readable and filesystem-safe filenames for downloaded books.
- **Format**: `LastnameFirstname_TitleOfTheBook_BookID.ext`
- **Key Features**: Detailed rules for parsing author (first author focus, lastname/firstname logic, initial handling), title slugification (spaces to underscores), BookID usage, extension handling (lowercase, default), string sanitization (invalid char removal, length limits), and fallbacks for missing data.
- **Implementation**: Pseudocode provided for a Python helper function `_create_enhanced_filename` intended for `lib/python_bridge.py`.
- **Status**: Specification Complete (Draft).
- **Related**: Task 3 in [`docs/project-plan-zlibrary-mcp.md:130-162`](docs/project-plan-zlibrary-mcp.md:130-162)
### Product: RAG Robustness Spec Update (v1.1) - [2025-04-29 23:15:00]
- **Context**: Updated `docs/rag-robustness-enhancement-spec.md` based on user feedback.
- **Changes**: Refined testing strategy to include AI-assisted quality evaluation. Added requirements and pseudocode for preprocessing (front matter removal, Title/ToC extraction and formatting). Updated pass/fail criteria and definition of done.
- **Status**: Specification Updated (Draft).
- **Related**: `docs/rag-robustness-enhancement-spec.md` (v1.1), [ActiveContext 2025-04-29 23:15:00]
<!-- Entries below should be added reverse chronologically (newest first) -->

### Product: RAG Robustness Enhancement Specification - [2025-04-29 19:54:15]
- **Context**: Specification generated to address RAG pipeline reliability and quality issues, especially with real-world PDFs/EPUBs.
- **Strategy**: Defines a real-world testing approach, PDF quality analysis (PyMuPDF investigation, quality detection, OCR integration), EPUB handling review, and includes pseudocode/TDD anchors for key components.
- **Components**: New testing framework (`scripts/run_rag_tests.py`), modifications to `lib/rag_processing.py` (`detect_pdf_quality`, `run_ocr_on_pdf`, updated `process_pdf`, `_epub_node_to_markdown`), potential new dependencies (`pytesseract`, `Pillow`/`OpenCV`).
- **Status**: Specification generated (Draft).
- **Related**: `docs/rag-robustness-enhancement-spec.md`, [ActiveContext 2025-04-29 19:54:15]
### Product: RAG Spec Update (Download Workflow) - [2025-04-24 17:33:32]
- **Context**: Updated `docs/rag-pipeline-implementation-spec.md` (to v2.1) to accurately reflect the download workflow defined in ADR-002.
- **Changes**: Clarified the two-step process (search for `bookDetails`, pass details to `download_book_to_file`, internal scraping of book page URL using selector `a.btn.btn-primary.dlButton`). Updated tool schemas, Node/Python pseudocode, and TDD anchors accordingly. Input for `download_book_to_file` changed from `id` to `bookDetails`.
- **Status**: Specification Updated (Draft).
- **Related**: ADR-002, `docs/rag-pipeline-implementation-spec.md` (v2.1)


### Product: Search-First ID Lookup Specification - [2025-04-16 18:14:19]
- **Context**: Specification generated for an alternative internal ID lookup strategy requested by the user.
- **Strategy**: Uses internal search (query=ID) via `httpx`/`BeautifulSoup` to find the book page URL, then fetches/parses that page.
- **Components**: New `_internal_search` function, modified `_internal_get_book_details_by_id` function in `lib/python_bridge.py`, new exceptions (`InternalBookNotFoundError`, `InternalParsingError`, `InternalFetchError`).
- **Status**: Specification generated (Draft).
- **Related**: `docs/search-first-id-lookup-spec.md`, Decision-SearchFirstIDLookup-01


### Pattern: RAG Markdown Generation - [2025-04-29 09:47:33]
- **Context**: Enhancing the RAG pipeline to produce structured Markdown output.
- **Problem**: Plain text output from RAG processing lacks structure (headings, lists, footnotes), limiting its usefulness for certain downstream tasks.
- **Solution**: Refined the Python bridge (`lib/python_bridge.py`) functions (`_process_pdf`, `_process_epub`) to optionally generate Markdown. Uses `PyMuPDF` heuristics (font size, flags) for PDFs and `BeautifulSoup` DOM traversal for EPUBs to map structural elements to Markdown syntax. Controlled by the `output_format` parameter ('text' or 'markdown') in `process_document` and `download_book_to_file`.
- **Components**: `lib/python_bridge.py` (updated `_process_pdf`, `_process_epub`, added `_format_pdf_markdown`, `_analyze_pdf_block`, `_epub_node_to_markdown`), `src/lib/zlibrary-api.ts` (passes `output_format`), `src/index.ts` (updated tool schemas).
- **Related**: `docs/rag-markdown-generation-spec.md`, `docs/rag-pipeline-implementation-spec.md` (updated), ActiveContext [2025-04-29 09:47:33]
### Pattern Update: Python Bridge RAG Processing - [2025-04-29 15:52:56]
#### [2025-04-29 17:14:10] Completion Phase Finalized
- **Summary:** All post-refinement cleanup tasks identified by `holistic-reviewer` [Ref: GlobalContext Progress 2025-04-29 16:57:57] have been completed (`optimizer` commits `e3b8709`, `70687dc`). Final TDD verification passed [Ref: SPARC MB Delegation Log 2025-04-29 17:07:00]. Final integration checks passed [Ref: SPARC MB Delegation Log 2025-04-29 17:10:29].
- **Status:** Workspace is stable, verified, and ready for the next stage.
- **Links:** [ActiveContext 2025-04-29 17:14:10]
- **Context**: Refactoring `lib/python_bridge.py` for modularity.
- **Problem**: `lib/python_bridge.py` exceeded line limits due to inclusion of extensive RAG document processing logic (PDF/EPUB/TXT parsing, Markdown generation, file saving).
- **Solution**: Extracted all RAG-specific functions (`process_epub`, `process_txt`, `process_pdf`, `save_processed_text`, and associated helpers like `_analyze_pdf_block`, `_format_pdf_markdown`, `_epub_node_to_markdown`, `_html_to_text`) into a new dedicated module: `lib/rag_processing.py`. The main `python_bridge.py` now imports and calls functions from this module.
### Pattern: Mock State Leakage (unittest.mock vs pytest-mock) - [2025-05-01 02:54:03]
- **Context**: Pytest suite with multiple tests using mocking (`unittest.mock`, `pytest-mock`).
- **Problem**: A test (`test_run_single_test_calls_processing_and_eval`) failed with `StopIteration`/`RuntimeError` when run as part of the suite, but passed in isolation. The error occurred within `unittest.mock` machinery, indicating an exhausted iterator `side_effect`, even though the test used `return_value` or callable `side_effect`.
- **Cause**: The preceding test (`test_main_loads_manifest_and_runs_tests_revised`) used `unittest.mock.patch` and manual mock assignment, including a list iterator `side_effect`. This state leaked into the subsequent test, corrupting the `side_effect` attribute of manually created `MagicMock` instances in that test, despite attempts to reset (`mocker.resetall`, explicit `side_effect=None`).
- **Solution**: Refactor the *preceding* test (`test_main_loads_manifest_and_runs_tests_revised`) to use `mocker.patch` (from `pytest-mock`) exclusively. This ensures proper mock isolation and cleanup between tests managed by the `pytest-mock` fixture.
### Pattern: RAG Robustness Enhancements - [2025-05-05 03:56:36]
- **Context**: Improving the reliability of the RAG document processing pipeline.
- **Problem**: Basic text extraction from PDFs and EPUBs is insufficient for real-world documents, leading to poor quality RAG input (missing text from scans, garbled text, irrelevant front matter).
- **Solution**: Implemented several enhancements in `lib/rag_processing.py`:
    - **PDF Quality Detection:** Heuristics (`detect_pdf_quality`) analyze text density, image area, and fonts to categorize PDFs (TEXT_HIGH, TEXT_LOW, IMAGE_ONLY, MIXED).
    - **Conditional OCR:** If PDF quality is low or image-only, OCR (`run_ocr_on_pdf` using `pytesseract`) is triggered to extract text from rendered page images.
    - **Preprocessing:** Logic (`identify_and_remove_front_matter`, `extract_and_format_toc`) added to remove common front matter sections and extract/format the Table of Contents.
    - **Garbled Text Detection:** Heuristics (`detect_garbled_text`) added to flag potentially poor extraction results.
- **Components**: `lib/rag_processing.py` (new functions), `lib/python_bridge.py` (orchestration), `requirements.txt` (added `pytesseract`, `Pillow`).
- **Related**: `docs/rag-robustness-enhancement-spec.md`, `docs/rag-pipeline-implementation-spec.md` (updated), [ActiveContext 2025-05-05 03:45:36]
- **Components**: `__tests__/python/test_run_rag_tests.py`
- **Related**: [Debug Issue RAG-MOCK-LEAK-01]
### Pattern: Inconsistent MCP Response Structure (Success vs. Error) - [2025-05-05 22:29:07]
- **Context**: MCP server (`zlibrary-mcp`) handling `tools/call` requests.
- **Problem**: Server returned different structures for successful responses (raw handler result) and error responses (`{ content: [{ type: 'text', ... }], isError: true }`). Client (RooCode) expected a consistent structure, specifically a top-level `content` array, leading to ZodError on successful calls.
- **Cause**: Server implementation returned handler result directly on success, violating the client's implicit schema expectation derived from the error structure.
- **Solution**: Modified the `tools/call` handler in `src/index.ts` to wrap the successful result object directly within the `content` array: `{ content: [result] }`. This satisfies the client's schema expectation while preserving the result data structure.
- **Components**: `src/index.ts` (`tools/call` handler).
- **Related**: Issue INT-001, [GlobalContext Progress 2025-05-05 22:32:14]
- **Components**: `lib/python_bridge.py` (modified), `lib/rag_processing.py` (new).
- **Impact**: Improved modularity and maintainability. Reduced `lib/python_bridge.py` line count significantly.
### Pattern: Node/Python Bridge Data Handling (MCP Response) - [2025-05-06 00:33:00]
- **Context**: Passing data from Python script (`lib/python_bridge.py`) via MCP server (`src/index.ts`) to Node.js library (`src/lib/zlibrary-api.ts`).
- **Problem**: Regression INT-001-REG-01 occurred where `zlibrary-api.ts` failed to parse JSON results. The INT-001 fix wrapped the Python result in an MCP structure (`{ content: [{ type: 'text', text: JSON.stringify(result) }] }`) within `src/index.ts`. However, `zlibrary-api.ts` was still expecting the raw JSON string from Python, leading to parsing errors.
- **Solution**:
    1.  **`src/index.ts` Handlers**: Modified handlers (e.g., `searchBooks`) to return the direct result from `zlibraryApi` functions, removing intermediate object wrapping. The main `tools/call` handler correctly stringifies this direct result into the MCP `content.text` field.
    2.  **`src/lib/zlibrary-api.ts` (`callPythonFunction`)**: Maintained `python-shell` in `text` mode. Implemented double `JSON.parse`: first parse the raw stdout string to get the MCP response object, then parse the `mcpResponseData.content[0].text` string to get the actual Python result.
    3.  **`__tests__/zlibrary-api.test.js`**: Corrected all `mockPythonShellRun.mockResolvedValueOnce` calls to resolve with `[stringified_MCP_response]`, matching the `text` mode output. Ensured unique variable names for mock helpers.
### Pattern Update: MCP Response Structure (Raw Object) - [2025-05-06 02:05:11]
- **Context**: MCP server (`zlibrary-mcp`) handling `tools/call` requests.
- **Problem**: Initial INT-001 fix wrapped successful results in `{ content: [{ type: 'text', text: JSON.stringify(result) }] }`. While resolving the ZodError, this returned stringified data, not the expected raw object, causing issues for the client (e.g., `get_download_limits` returning `{"status":"success","result_type":"dict"}`).
### Pattern Update: Node/Python Bridge Data Handling (MCP Response) - [2025-05-06 02:24:48]
- **Context**: Ensuring correct data flow from Python script (`lib/python_bridge.py`) through the Node.js layer (`src/lib/zlibrary-api.ts`, `src/index.ts`) to the MCP client.
- **Problem**: Client was receiving a stringified status dictionary (e.g., `"{'status':'success','result_type':'dict'}"`) instead of the actual tool result (e.g., download limits object). This was due to `lib/python_bridge.py` not outputting its data in the doubly-wrapped JSON structure expected by `callPythonFunction` in `src/lib/zlibrary-api.ts`.
- **Solution**:
    1.  **`lib/python_bridge.py` (`main` function)**: Modified to *always* print its output in the format `json.dumps({ "content": [{ "type": "text", "text": json.dumps(actual_python_result) }] })`. This ensures `callPythonFunction` receives the structure it expects for its initial parse.
    2.  **`src/lib/zlibrary-api.ts` (`callPythonFunction`)**: No changes needed here. It correctly performs a double parse: first to get the outer MCP object, then to extract and parse the `text` field to get the `actual_python_result`. It returns this `actual_python_result`.
    3.  **`src/index.ts` (Tool Handlers, e.g., `getDownloadLimits`)**: No changes needed. They correctly return the `actual_python_result` received from `zlibraryApi` functions.
    4.  **`src/index.ts` (`tools/call` handler)**: No changes needed to its final response structure. It correctly takes the `actual_python_result` from the specific tool handler and stringifies it into the final client response: `{ content: [{ type: 'text', text: JSON.stringify(actual_python_result) }] }`.
- **Components**: `lib/python_bridge.py`, `src/lib/zlibrary-api.ts`, `src/index.ts`.
- **Related**: [GlobalContext Progress 2025-05-06 02:24:48], [GlobalContext Pattern 2025-05-06 00:33:00] (Previous state), [User Feedback 2025-05-06 02:07:05]
---
- **Solution**: Modified the `tools/call` handler in `src/index.ts` (line 331) to return the raw result object directly within the content array: `{ content: [result] }`. This aligns with the original intent of the INT-001 fix and provides the client with the expected data structure.
- **Components**: `src/index.ts` (`tools/call` handler).
- **Related**: Issue INT-001 Follow-up, [GlobalContext Progress 2025-05-06 02:05:11], [GlobalContext Pattern 2025-05-05 22:29:07] (Previous structure)
---
- **Components**: `src/index.ts`, `src/lib/zlibrary-api.ts`, `__tests__/zlibrary-api.test.js`.
- **Related**: [Debug Issue INT-001-REG-01], [GlobalContext Progress 2025-05-06 00:33:00]
---
- **Related**: Task [Refactor Python Bridge (`lib/python_bridge.py`) 2025-04-29 15:43:24]
### Pattern: External API Endpoint Obsolescence - [2025-05-06 12:01:30]
- **Context**: Tools relying on specific URL endpoints of external services (e.g., Z-Library).
- **Problem**: External services may change their API endpoints or URL structures without notice (e.g., `/users/dstats.php` becoming `/users/downloads`). This leads to 404 errors and tool failures (e.g., `ParseError` due to empty response).
- **Detection**: Monitor for 404 errors, unexpected empty responses, or redirect headers (`Location`) in HTTP responses from external services.
- **Mitigation/Solution**:
    - Implement robust error handling to detect 404s and log redirect information.
    - Update the library/tool to use the new endpoint.
    - Verify HTML parsing logic against the new endpoint's structure.
    - Consider adding configuration for base URLs or key endpoints if changes are frequent.
- **Components**: `zlibrary/src/zlibrary/libasync.py`, `zlibrary/src/zlibrary/abs.py`, `zlibrary/src/zlibrary/profile.py`.
- **Related Issues**: [Debug Issue ZLIB-DSTATS-404]
---
# System Patterns
### Pattern: RAG Pipeline File Output - [2025-04-23 23:30:58]
### Pattern: Conflicting Function Definitions - [2025-05-01 03:09:11]
- **Context**: Python file (`scripts/run_rag_tests.py`) modified during TDD cycles.
- **Problem**: A function (`evaluate_output`) was defined twice within the same file. The second definition, likely added during a refactoring step (e.g., adding type hints), unintentionally overwrote the first definition containing the correct logic for the current TDD cycle. This caused tests to fail by executing the incorrect (overwriting) function body.
- **Cause**: Lack of awareness or check for existing function definitions before adding a new one, possibly during refactoring or merging code snippets.
- **Solution**: Identify and remove the duplicate/overwriting function definition, ensuring only the intended version remains.
- **Components**: `scripts/run_rag_tests.py`
- **Related**: [Debug Issue RAG-TEST-CONFLICT-01]
- **Context**: Processing documents (EPUB, TXT, PDF) for RAG workflows.
- **Problem**: Returning large amounts of extracted text directly via MCP tool results causes agent instability and context overload.
- **Solution**: Modify RAG processing tools (`process_document_for_rag`, combined `download_book_to_file`) to save the extracted/processed text to a dedicated file (e.g., `./processed_rag_output/<original_filename>.processed.txt`). The tools return the path (`processed_file_path`) to this output file instead of the content itself.
- **Components**: Updated `process_document_for_rag` and `download_book_to_file` tools, modifications to `lib/zlibrary-api.ts` (Node.js) and `lib/python-bridge.py` (Python - handles saving).
- **Benefits**: Prevents context overload, provides stable access to processed content for agents, decouples processing from immediate context usage.
- **Related**: Decision-RAGOutputFile-01, Intervention [2025-04-23 23:26:50], `docs/architecture/rag-pipeline.md` (v2), `docs/architecture/pdf-processing-integration.md` (v2)


### Pattern: RAG Pipeline File Output - [2025-04-23 23:29:31]
- **Context**: Redesign of RAG processing tools (`process_document_for_rag`, `download_book_to_file`) to address context overload issues.
- **Problem**: Returning large amounts of processed text directly caused agent instability.
- **Solution**: Modify tools to save processed text (EPUB/TXT/PDF) to a dedicated file (`./processed_rag_output/<original_name>.processed.txt`) and return the `processed_file_path` instead of raw text. Python bridge handles text extraction and file saving. Node.js layer returns the path(s).
- **Components**: `lib/python-bridge.py` (new `_save_processed_text` helper, modified `process_document`), `lib/zlibrary-api.ts` (updated return value handling), `index.ts` (updated tool schemas/outputs).
- **Error Handling**: File save errors in Python are caught and reported as structured errors by Node.js; raw text is not returned on save failure.
- **Related**: Decision-RAGOutputFile-01, `docs/architecture/rag-pipeline.md` (v2), `docs/architecture/pdf-processing-integration.md` (v2)


### Pattern: Node.js to Python Bridge Argument Passing (python-shell) - [2025-04-23 22:12:51]
- **Context**: Passing arguments from Node.js (`zlibrary-api.ts`) to a Python script (`python_bridge.py`) using the `python-shell` library.
- **Problem**: Passing `args: [functionName, JSON.stringify(argsObject)]` to `PythonShell` options caused the Python script (`sys.argv`) to receive the stringified object as the third argument (`sys.argv[2]`). The Python `main` function parsed this correctly, but then attempted `**args_dict` unpacking, leading to `TypeError: ... argument after ** must be a mapping, not list` because `args_dict` was derived incorrectly or used inappropriately.
- **Solution**: Ensure the `args` array in `PythonShell` options contains only the function name and the *already serialized* JSON string of arguments: `const serializedArgs = JSON.stringify(argsObject); ... options = { ..., args: [functionName, serializedArgs] };`. The Python script's `main` function should then correctly parse `sys.argv[2]` into a dictionary.
- **Related**: Issue REG-001, ActiveContext [2025-04-23 22:12:51]


### Pattern: MCP Server Rebuild/Restart Workflow (RooCode) - [2025-04-23 20:51:53]
- **Context**: Applying changes to a local MCP server (like `zlibrary-mcp`) requires a specific rebuild/restart process when used within RooCode.
- **Problem**: Running `npm run build` via `execute_command` is insufficient for RooCode to pick up changes.
- **Solution**: After modifying server source code:
    1. Run `npm run build` (or equivalent build command) via `execute_command`.
    2. **Crucially, ask the user to manually restart the specific MCP server using the restart button in the RooCode extension's MCP settings UI.** This ensures RooCode reloads the server process with the newly built code.
- **Related**: Feedback [2025-04-23 20:51:53]


### Pattern: Search-First Internal ID Lookup - [2025-04-16 18:40:05]
- **Implementation**: Implemented `_internal_search` and modified `_internal_get_book_details_by_id` in `lib/python_bridge.py` using `httpx` and `BeautifulSoup` per `docs/search-first-id-lookup-spec.md`. `_internal_search` uses the book ID as a query. `_internal_get_book_details_by_id` calls `_internal_search`, fetches the resulting book page URL, and parses it using placeholder selectors. Callers (`get_by_id`, `get_download_info`, `main`) updated to use the new function and translate `InternalBookNotFoundError` -> `ValueError`, `InternalFetchError`/`InternalParsingError` -> `RuntimeError`.
- **Status**: TDD Green Phase complete. Python tests pass (relevant ones), Node tests pass.
- **Related**: `docs/search-first-id-lookup-spec.md`, ActiveContext [2025-04-16 18:40:05], Decision-SearchFirstIDLookup-01



### Pattern Update: Internal ID-Based Book Lookup (Scraping) - [2025-04-16 08:38:32]
- **Implementation**: Implemented `_internal_get_book_details_by_id` in `lib/python_bridge.py` using `httpx`. Handles 404 as `InternalBookNotFoundError`. Callers (`get_by_id`, `get_download_info`) updated to use this function and translate errors (`InternalBookNotFoundError` -> `ValueError`, others -> `RuntimeError`).
- **Status**: TDD Green Phase complete. Python tests pass (relevant ones), Node tests pass.
- **Related**: `docs/internal-id-lookup-spec.md`, ActiveContext [2025-04-16 08:38:32]


### Pattern: Internal ID-Based Book Lookup (Scraping) - [2025-04-16 08:10:00]
- **Context**: Replacing failed external `zlibrary` ID lookups (`get_book_by_id`, `get_download_info`).
- **Problem**: External library fails due to website changes (404 on `/book/ID`, non-functional `id:` search). Slug required for direct URL is unobtainable.
- **Solution**: Implement internal fetching/parsing within `lib/python_bridge.py`. Attempt to fetch `https://<domain>/book/ID` using `httpx`. **Explicitly handle the expected 404 response as 'Book Not Found'.** If a 200 OK is received (unlikely), parse HTML with `BeautifulSoup4`.
- **Components**: New function `_internal_get_book_details_by_id` in `lib/python_bridge.py`, modifications to `get_book_by_id`/`get_download_info` callers, `httpx` dependency.
- **Limitations**: Highly susceptible to website structure changes and anti-scraping measures. Does *not* resolve the missing slug issue; relies on 404 handling.
- **Related**: Decision-InternalIDLookupURL-01, Issue-BookNotFound-IDLookup-02, ComponentSpec-InternalIDScraper-01


<!-- Entries below should be added reverse chronologically (newest first) -->
### Pattern: Direct Book Page Handling in Search Results - [2025-04-16 00:03:00]
- **Identification**: `search(q='id:...')` queries in `zlibrary` library sometimes return a direct book page HTML instead of a standard search result list, causing `ParseError` in `SearchPaginator.parse_page`.
- **Resolution**: Modified `SearchPaginator.parse_page` in `zlibrary/src/zlibrary/abs.py` to detect this case (missing `#searchResultBox` on an `id:` search URL). If detected, it attempts to parse the page directly using a new helper method `BookItem._parse_book_page_soup` (extracted from `BookItem.fetch`).
- **Related**: Issue-ParseError-IDLookup-01, ActiveContext [2025-04-16 00:02:36]


### Pattern: External Library URL Construction Error (zlibrary `get_by_id`) - [2025-04-15 21:51:00]
- **Identification**: `zlibrary.exception.ParseError` on ID lookups, confirmed 404 response due to missing slug in URL generated by `client.get_by_id`.
- **Causes**: Likely hardcoded URL format in the external `zlibrary` library's `get_by_id` method that doesn't account for required slugs.
- **Components**: `lib/python_bridge.py` (calls `client.get_by_id`), external `zlibrary` library.
    - **Resolution**: Fixed in `zlibrary/src/zlibrary/libasync.py` by modifying `get_by_id` to use `search(q=f'id:{id}', exact=True, count=1)` instead of constructing the URL directly. See ActiveContext [2025-04-16 00:02:36].

- **Resolution**: Workaround proposed (`client.search(q=f'id:{id}')`) **FAILED**. Both `get_by_id` and `id:` search trigger `ParseError`. See Decision-IDLookupStrategy-01.
- **Related**: Issue-ParseError-IDLookup-01, Decision-ParseErrorWorkaround-01
- **Last Seen**: 2025-04-15 23:10:11 (Workaround Failure)


### Pattern Update: External Library URL Construction Error (zlibrary `get_by_id`) - [2025-04-16 07:27:22]
- **Note**: The previously attempted workaround (`client.search(q=f'id:{id}')`) is **invalid**. Further investigation confirmed the Z-Library website itself no longer returns results for `id:` queries, causing the search to fail and correctly raise `BookNotFound`. This prevents discovery of the correct book page URL (with slug).



### Pattern Update: External Library URL Construction Error (zlibrary `get_by_id`) - [2025-04-16 07:23:30]
- **Note**: The previously attempted workaround (`client.search(q=f'id:{id}')`) is **invalid**. Further investigation confirmed the Z-Library website itself no longer returns results for `id:` queries, causing the search to fail and correctly raise `BookNotFound`.


### Pattern: MCP Server Implementation (CJS/SDK 1.8.0) - [2025-04-14 17:50:25]
- **Context**: Documenting and comparing MCP server implementations, focusing on CJS projects using SDK v1.8.0.
- **Findings (zlibrary-mcp)**: Uses correct SDK paths/instantiation. Tool listing currently uses dummy schemas, potentially causing client error INT-001 despite valid response structure.
- **Documentation**: See comparison report `docs/mcp-server-comparison-report.md`.
- **Related**: Issue INT-001


### Pattern: RAG Document Processing Pipeline - [2025-04-14 14:25:00] (Implementation Update)
- **Implementation Detail**: PDF processing implemented using `PyMuPDF (fitz)` library within `lib/python-bridge.py`'s `_process_pdf` function, called from `process_document`.
- **Related**: Pattern-RAGPipeline-01 (Updated), Decision-PDFLibraryChoice-01


### Pattern: RAG Document Processing Pipeline - [2025-04-14 13:50:00] (Updated)
- **Context**: Enabling AI agents to use documents from Z-Library for Retrieval-Augmented Generation (RAG).
- **Problem**: Agents need efficient ways to extract usable text content from downloaded book files (EPUB, TXT, **PDF**).
- **Solution**: Extend the `zlibrary-mcp` server with two workflows:
    1.  **Combined:** Add an optional `process_for_rag: boolean` flag to the existing `download_book_to_file` tool. If true, the tool downloads the file, immediately processes it via the Python bridge (EPUB/TXT/**PDF**), and returns both the `file_path` and `processed_text`.
    2.  **Separate:** Keep the dedicated `process_document_for_rag` tool to process already downloaded files. This tool takes a `file_path` and returns `processed_text`.
- **Components**: Updated `download_book_to_file` tool, new `process_document_for_rag` tool, modifications to `lib/zlibrary-api.js` (Node.js), updated download function and new processing function in `lib/python-bridge.py` (Python), new Python dependencies (e.g., `ebooklib`, **`PyMuPDF`**).
- **Data Flow (Combined)**: Agent -> `download_book_to_file(process_for_rag=true)` -> Server (Node -> Python: Download -> Process -> Node) -> Agent (receives path & text).
- **Data Flow (Separate)**: Agent -> `download_book_to_file` -> Server (Node -> Python -> Disk) -> Agent -> `process_document_for_rag` -> Server (Node -> Python -> Node) -> Agent (receives text).
- **Extensibility**: Python bridge allows easy addition of new format handlers.
- **Related**: Decision-RAGProcessorTech-01, Decision-CombineDownloadProcess-01, **Decision-PDFLibraryChoice-01**, MCPTool-ProcessDocRAG-01, MCPTool-DownloadBook-01 (Updated)


### Pattern: RAG Document Processing Pipeline - [2025-04-14 12:07:50] (Updated)
- **Context**: Enabling AI agents to use documents from Z-Library for Retrieval-Augmented Generation (RAG).
- **Problem**: Agents need efficient ways to extract usable text content from downloaded book files (EPUB, TXT initially).
- **Solution**: Extend the `zlibrary-mcp` server with two workflows:
    1.  **Combined:** Add an optional `process_for_rag: boolean` flag to the existing `download_book_to_file` tool. If true, the tool downloads the file, immediately processes it via the Python bridge (EPUB/TXT), and returns both the `file_path` and `processed_text`.
    2.  **Separate:** Keep the dedicated `process_document_for_rag` tool to process already downloaded files. This tool takes a `file_path` and returns `processed_text`.
- **Components**: Updated `download_book_to_file` tool, new `process_document_for_rag` tool, modifications to `lib/zlibrary-api.js` (Node.js), updated download function and new processing function in `lib/python-bridge.py` (Python), new Python dependencies (e.g., `ebooklib`).
- **Data Flow (Combined)**: Agent -> `download_book_to_file(process_for_rag=true)` -> Server (Node -> Python: Download -> Process -> Node) -> Agent (receives path & text).
- **Data Flow (Separate)**: Agent -> `download_book_to_file` -> Server (Node -> Python -> Disk) -> Agent -> `process_document_for_rag` -> Server (Node -> Python -> Node) -> Agent (receives text).
- **Extensibility**: Python bridge allows easy addition of new format handlers (e.g., PDF).
- **Related**: Decision-RAGProcessorTech-01, Decision-CombineDownloadProcess-01, MCPTool-ProcessDocRAG-01, MCPTool-DownloadBook-01 (Updated)


### Pattern: Managed Python Virtual Environment for NPM Package - [2025-04-14 03:29:08]
- **Context**: Providing a reliable Python dependency environment for a globally installed Node.js package (`zlibrary-mcp`).
### Decision-RAGOutputFile-01 - [2025-04-23 23:30:58]
- **Decision**: Redesign RAG processing tools (`process_document_for_rag`, combined `download_book_to_file`) to save processed text to a file (`./processed_rag_output/<original_filename>.processed.txt`) and return the `processed_file_path` instead of raw text content.
- **Rationale**: Addresses critical user feedback ([Ref: SPARC Feedback 2025-04-23 23:26:20]) regarding agent instability caused by context overload from large text returns. Saving to file provides a stable and scalable mechanism for agents to access processed content.
- **Alternatives Considered**: Returning truncated text (loses data), streaming text (complex agent handling), keeping original design (unstable).
- **Implementation**: Modify Python bridge (`lib/python-bridge.py`) to handle file saving. Update tool schemas and return values in Node.js layer (`lib/zlibrary-api.ts`, `src/index.ts`). Update architecture docs.
- **Related**: Pattern-RAGPipeline-FileOutput-01, Intervention [2025-04-23 23:26:50], `docs/architecture/rag-pipeline.md` (v2), `docs/architecture/pdf-processing-integration.md` (v2)


- **Problem**: Global Python installations are inconsistent; relying on `PATH` or global `pip` is fragile.
- **Solution**: Automate the creation and management of a dedicated Python virtual environment (`venv`) within a user-specific cache directory during a post-install script or first run. Install required Python packages (`zlibrary`) into this venv. Explicitly use the absolute path to the venv's Python interpreter when executing Python scripts from Node.js (`python-shell` or `child_process`).
- **Components**: New setup script/logic, `lib/zlibrary-api.js` (modified to use venv path).
- **Tradeoffs**: Requires Python 3 pre-installed by user. Adds one-time setup step. Avoids package bloat (bundling) and fragility (detection).
- **Related**: Decision-PythonEnvStrategy-01, Issue-GlobalExecFail-01

### Decision-DeprecateGetDownloadInfo-01 - [2025-04-28 17:31:01]
- **Decision**: Recommend deprecating the `get_download_info` tool.
- **Rationale**: Investigation confirmed the tool relies on the unstable ID lookup mechanism (`_find_book_by_id_via_search`). Its primary output (`download_url`) is unreliable (returned `null` during testing) and is not used by the current download workflow defined in ADR-002 (which uses scraping via `download_book`). Other metadata provided is redundant with `search_books`. The tool serves no essential purpose and adds unnecessary complexity.
- **Alternatives Considered**: Fixing (unnecessary given ADR-002), Refactoring (pointless as functionality is unused/unreliable).
- **Implementation**: Remove the tool definition from `src/index.ts`, the handler from `src/lib/zlibrary-api.ts`, the corresponding function from `lib/python_bridge.py`, and associated tests.
- **Related**: ADR-002, [Debug Report 2025-04-28 17:31:01]
# Decision Log
### Decision-DeprecateGetBookByID-01 - [2025-04-29 15:37:14]
### Decision-RAGPreprocessing-01 - [2025-04-29 23:15:00]
- **Decision**: Implement preprocessing steps in the RAG pipeline to remove front matter (excluding Title) and extract/format the Table of Contents (ToC) before main content processing.
### Decision: Filename Author Handling - [2025-05-07]
- **Decision**: For the `LastnameFirstname` component of the enhanced filename, if multiple authors are provided in the `bookDetails.author` string, only the first author will be parsed and used.
- **Rationale**: Simplifies parsing logic for the filename component while still providing primary author identification. The full author list remains available in the metadata.
- **Impact**: Filenames will reflect the first listed author.
- **Related**: Enhanced Filename Convention Specification.
- **Rationale**: User requirement to improve RAG input quality by removing irrelevant introductory sections and preserving key navigational elements (Title, ToC). Addresses potential negative impact of front matter on RAG performance.
- **Alternatives Considered**: No preprocessing (current state, suboptimal quality), manual cleaning (not scalable).
- **Implementation**: Add new functions/logic (e.g., `identify_and_remove_front_matter`, `extract_and_format_toc`) to `lib/rag_processing.py`, integrate into `process_pdf`/`process_epub`. Update specification and tests.
- **Related**: `docs/rag-robustness-enhancement-spec.md#5-preprocessing---front-matter--toc-handling`, [ActiveContext 2025-04-29 23:15:00]

### Decision-RAGTestingAI-01 - [2025-04-29 23:15:00]
- **Decision**: Incorporate AI-assisted quality evaluation into the RAG robustness testing framework for real-world documents.
- **Rationale**: User requirement for automated quality assessment beyond quantitative metrics, leveraging AI to evaluate aspects like faithfulness, readability, and correctness of complex formatting (e.g., ToC links) in processed output. Addresses limitations of purely metric-based evaluation for nuanced quality issues.
- **Alternatives Considered**: Manual evaluation only (slow, subjective), purely quantitative metrics (misses nuances).
- **Implementation**: Update testing framework (`scripts/run_rag_tests.py`) to include a step calling an AI agent (placeholder/mock initially) to evaluate processed text/markdown. Update reporting to include AI scores/feedback. Update pass/fail criteria.
- **Related**: `docs/rag-robustness-enhancement-spec.md#23-testing-methodology--metrics` (FR-TEST-11.5), [ActiveContext 2025-04-29 23:15:00]
- **Decision**: Deprecate the `get_book_by_id` MCP tool.
- **Rationale**: External Z-Library website changes prevent reliable book lookup using only an ID. Both direct `/book/ID` fetches (missing slug) and `search(id:...)` workarounds fail externally. Continuing to support the tool implies functionality that cannot be delivered and adds maintenance overhead for brittle scraping code. ADR-002 workflow already relies on `search_books`.
- **Alternatives Considered**: Refining internal scrapers (pointless if external source is broken), finding alternative library methods (unlikely), keeping tool marked as unreliable (less clear than deprecation).
- **Implementation**: Log decision in ADR-003. Subsequent tasks should remove the tool definition, handlers, Python bridge function, and associated tests. Update documentation.
- **Related**: ADR-003, ActiveContext [2025-04-29 15:37:14], ActiveContext [2025-04-16 07:27:22], Decision-DeprecateGetDownloadInfo-01
### Decision-DeprecateGetBookByID-01 - [2025-04-29 15:37:14]
- **Decision**: Deprecate the `get_book_by_id` MCP tool.
- **Rationale**: External Z-Library website changes prevent reliable book lookup using only an ID. Both direct `/book/ID` fetches (missing slug) and `search(id:...)` workarounds fail externally. Continuing to support the tool implies functionality that cannot be delivered and adds maintenance overhead for brittle scraping code. ADR-002 workflow already relies on `search_books`.
- **Alternatives Considered**: Refining internal scrapers (pointless if external source is broken), finding alternative library methods (unlikely), keeping tool marked as unreliable (less clear than deprecation).
- **Implementation**: Log decision in ADR-003. Subsequent tasks should remove the tool definition, handlers, Python bridge function, and associated tests. Update documentation.
- **Related**: ADR-003, ActiveContext [2025-04-29 15:37:14], ActiveContext [2025-04-16 07:27:22], Decision-DeprecateGetDownloadInfo-01
### Decision-DeferXfailedTests-01 - [2025-04-29 15:29:34]
- **Decision**: Defer addressing the 3 remaining xfailed tests in `__tests__/python/test_python_bridge.py` (`test_main_routes_download_book`, `test_downloads_paginator_parse_page_new_structure`, `test_downloads_paginator_parse_page_old_structure_raises_error`).
- **Rationale**: `tdd` mode confirmed these tests fail for valid, documented reasons (problematic structure, vendored library changes) [Ref: ActiveContext 2025-04-29 15:27:08]. Fixing them may require significant effort and could delay the completion of the current refinement cycle focused on the previously critical 10 failures. The rest of the test suite passes. These can be logged as technical debt.
- **Alternatives Considered**: Addressing xfails now (Option A - high effort/delay risk).
- **Implementation**: Log decision. Proceed with other refinement/completion tasks (e.g., holistic review).
- **Related**: ActiveContext [2025-04-29 15:27:08] (TDD xfail investigation)
### Decision-PrioritizeGitCleanup-01 - [2025-04-28 02:20:01]
- **Decision**: Prioritize cleaning up uncommitted changes ('git debt') before proceeding with the TDD cycle for RAG download workflow. Delegate task to `devops`.
- **Rationale**: User intervention identified significant uncommitted changes, potentially impacting stability and future work. Maintaining clean version control is crucial.
- **Alternatives Considered**: Proceeding with TDD (risks conflicts/lost work), manual cleanup (less efficient).
- **Implementation**: Delegate task to `devops` to analyze `git status`, group changes logically, and commit.
- **Related**: ActiveContext [2025-04-28 02:20:01]
### Decision-DownloadBookDeps-01 - [2025-04-24 03:18:12]
- **Decision**: Use `httpx` for async HTTP requests (with `follow_redirects=True`) and `aiofiles` for async file writing in the `download_book` implementation within the forked `zlibrary` library (`zlibrary/src/zlibrary/libasync.py`). Add `httpx` and `aiofiles` as dependencies to the forked library's `zlibrary/pyproject.toml`.
- **Rationale**: `httpx` is preferred for async requests and supports redirects. `aiofiles` is needed for non-blocking file I/O within the async method. Dependencies must be declared within the sub-project's configuration.
- **Alternatives Considered**: Using `aiohttp` (already present, but `httpx` was requested and is suitable), using standard blocking file I/O (would block the async event loop).
- **Implementation**: Added dependencies to `zlibrary/pyproject.toml`. Implemented `download_book` using these libraries.
- **Related**: ActiveContext [2025-04-24 03:49:26]


<!-- Entries below should be added reverse chronologically (newest first) -->
### Decision-DownloadScrapingStrategy-01 - [2025-04-24 16:59:28]
- **Decision**: Reaffirm the download workflow strategy implemented in `zlibrary/src/zlibrary/libasync.py::download_book` (on `feature/rag-file-output` branch). This involves: obtaining the book page URL from search/get_by_id results (`BookItem['url']`), fetching that page, parsing with BeautifulSoup, selecting the download link via CSS selector (`a.btn.btn-primary.dlButton`), extracting the `href`, and downloading from the extracted URL.
- **Rationale**: Investigation confirmed this aligns with the required strategy shift mandated by user feedback and integration failures (Ref: INT-RAG-003, SPARC Feedback 2025-04-24 16:41:02). It correctly uses the book page URL to find the actual download link, addressing the unreliability of direct ID-based URL construction.
- **Alternatives Considered**: Direct URL construction (unreliable), relying on a non-existent dedicated download info function.
- **Consequences**: More reliable than previous attempts, but dependent on website HTML structure (selector brittleness). Error handling is implemented.
- **Related**: ADR-002, ActiveContext [2025-04-24 16:59:28]


### Decision-RAGOutputFile-01 - [2025-04-23 23:29:31]
- **Decision**: Modify RAG processing tools (`process_document_for_rag`, `download_book_to_file` with `process_for_rag: true`) to save extracted text content to a file and return the file path (`processed_file_path`) instead of the raw text content.
- **Rationale**: Addresses critical feedback ([Ref: SPARC Feedback 2025-04-23 23:26:20]) regarding agent instability caused by context overload when handling large amounts of raw text returned by the tools. Returning a file path is more scalable and robust.
- **Save Location**: `./processed_rag_output/` (relative to workspace root).
- **Filename Convention**: `<original_filename>.processed.<format_extension>` (e.g., `book.epub.processed.txt`).
- **Default Format**: `.txt`.
- **Error Handling**: File save errors are explicitly handled and reported; raw text is not returned on failure.
- **Alternatives Considered**: Returning truncated text (lossy), streaming text (complex implementation), increasing agent context limits (external dependency).
- **Implementation**: Update tool schemas, Node.js handlers (`lib/zlibrary-api.ts`), Python bridge (`lib/python-bridge.py` to add saving logic), and architecture documents.
- **Related**: Pattern-RAGPipeline-FileOutput-01, `docs/architecture/rag-pipeline.md` (v2), `docs/architecture/pdf-processing-integration.md` (v2), ActiveContext [2025-04-23 23:29:31]


### Decision-SearchFirstIDLookup-01 - [2025-04-16 18:14:19]
- **Decision**: Specify the 'Search-First' internal ID lookup strategy as requested by the user. This involves using internal search (query=ID) to find the book page URL, then fetching and parsing that page using `httpx` and `BeautifulSoup`.
- **Rationale**: User explicitly requested this strategy despite known risks (search unreliability) documented in previous Memory Bank entries ([2025-04-16 07:27:22]). This specification fulfills the user's request.
- **Alternatives Considered**: Using the previously implemented internal 404-handling strategy (already exists), further debugging external library (deemed unreliable).
- **Implementation**: Specification generated in `docs/search-first-id-lookup-spec.md`. Includes pseudocode for `_internal_search`, `_internal_get_book_details_by_id`, caller modifications, exceptions, and TDD anchors.
- **Related**: `docs/search-first-id-lookup-spec.md`, ActiveContext [2025-04-16 18:13:31]


### Decision-InternalIDLookupURL-01 - [2025-04-16 08:10:00]
- **Decision**: For internal ID lookup implementation, use the URL pattern `https://<domain>/book/ID`. Explicitly handle the expected 404 response as the primary failure mode ('Book Not Found'). Use `httpx` for fetching. Add `httpx` to `requirements.txt`.
- **Rationale**: Fetching `/book/ID` confirmed to return 404 (missing slug). Searching for the slug via `id:` search is non-functional on the external site. General search is unreliable. This approach accepts the limitation and builds handling around the expected 404. `httpx` is a modern, robust async HTTP client suitable for scraping.
- **Alternatives Considered**: Attempting slug guessing (unreliable), complex search heuristics (brittle), relying solely on external library (non-functional).
- **Implementation**: Add `_internal_get_book_details_by_id` function in `python_bridge.py` using `httpx` and 404 handling. Update `requirements.txt`.
- **Related**: Pattern-InternalIDScraper-01, Issue-BookNotFound-IDLookup-02, ActiveContext [2025-04-16 08:10:00]


### Decision-IDLookupStrategy-01 - [2025-04-15 23:12:00]
- **Decision**: Adopt a sequential strategy to resolve the ID lookup `ParseError`: 1. Briefly search for alternative libraries. 2. If none found, attempt to Fork & Fix the existing `zlibrary` library (targeting URL construction/parsing). 3. If Fork & Fix fails, implement internal web scraping/parsing functions.
- **Rationale**: The previous workaround (`client.search(q='id:...')`) also failed with `ParseError`, confirming a deeper issue within the external library affecting both `get_by_id` and ID-based searches. Fork & Fix offers potential for leveraging existing code with moderate effort. Internal implementation provides full control but requires higher effort and maintenance.
- **Alternatives Considered**: Only Internal Implementation (higher initial effort), Only Find Alternative (uncertain success).
- **Implementation**: Next steps involve searching for alternatives, then potentially delegating debug/fix tasks.
- **Related**: Issue-ParseError-IDLookup-01, Decision-ParseErrorWorkaround-01 (Superseded), ActiveContext [2025-04-15 23:12:00]


### Decision-ParseErrorWorkaround-01 - [2025-04-15 21:51:00] (FAILED & Superseded)
- **Decision**: ~~Propose workaround for `zlibrary.exception.ParseError` on ID-based lookups (`get_book_by_id`, `get_download_info`) by replacing `client.get_by_id(id)` calls with `client.search(q=f'id:{id}', exact=True, count=1)`.~~ **FAILED**.
- **Rationale**: ~~Memory Bank and code review confirm `client.get_by_id` constructs an incorrect URL (missing slug), causing a 404 and subsequent `ParseError`. Using `client.search` bypasses this faulty method. Assumes search results contain sufficient data (including `download_url` for `get_download_info`). This avoids replacing the library immediately.~~ **FAILED**: Integration testing confirmed `client.search(q='id:...')` also triggers `ParseError`.
- **Alternatives Considered**: Replacing the `zlibrary` library (deferred), attempting to guess slugs (unreliable), modifying the library (no source).
- **Implementation**: ~~Modify `get_by_id` and `get_download_info` functions in `lib/python_bridge.py` to use the search logic and handle search results.~~ **FAILED**.
- **Related**: Issue-ParseError-IDLookup-01, ActiveContext [2025-04-15 21:51:00], ActiveContext [2025-04-15 23:10:11], Decision-IDLookupStrategy-01 (Supersedes this)

### Decision-VenvManagerDI-01 - [2025-04-15 04:27:00]
- **Decision**: Refactor `src/lib/venv-manager.ts` to use dependency injection for `fs` and `child_process` modules.
- **Rationale**: Persistent failures in Jest tests (`__tests__/venv-manager.test.js`) when mocking built-in modules (`fs`, `child_process`) using `jest.unstable_mockModule` or `jest.spyOn` in an ESM context. Dependency injection provides a reliable way to supply mocks during testing, bypassing ESM mocking complexities for built-ins.
- **Alternatives Considered**: Further attempts at `unstable_mockModule` (failed), `jest.spyOn` (failed), skipping tests (undesirable).
- **Implementation**: Modified `venv-manager.ts` functions to accept a `deps` object; updated tests to pass mock objects.
- **Related**: Progress [2025-04-15 04:31:00]


### Decision-JestMockingStrategy-01 - [2025-04-15 03:33:00]
- **Decision**: Refactor `__tests__/zlibrary-api.test.js` to mock the exported API functions directly using `jest.unstable_mockModule` and `jest.resetModules()`, instead of mocking the lower-level `python-shell`. For `__tests__/venv-manager.test.js`, continue attempting to fix `fs`/`child_process` mocks using `unstable_mockModule` and dynamic imports.
- **Rationale**: Mocking `python-shell` proved unreliable with `unstable_mockModule` and inconsistent `jest.resetModules()` usage, causing state bleed. Mocking the higher-level API provides better isolation and control for `zlibrary-api.test.js`. The `venv-manager.test.js` issues seemed closer to resolution with the existing `unstable_mockModule` approach, warranting further refinement attempts.
- **Alternatives Considered**: Persisting with `python-shell` mock (failed), using `spyOn` (less suitable for full module replacement in ESM), skipping tests (undesirable).
- **Related**: Progress [2025-04-15 03:41:00]


### Decision-MigrationStrategy-INT001 - [2025-04-14 18:31:26]
- **Decision**: Recommend fixing `zod-to-json-schema` implementation first within current CJS/SDK 1.8.0 setup as the primary approach to resolve INT-001. If unsuccessful, or for modernization, recommend migrating to ESM while keeping SDK 1.8.0 (Option 2), ensuring the schema fix is included.
- **Rationale**: Comparison report indicates incorrect schema generation (bypassed `zod-to-json-schema`) is the most likely cause of INT-001, not SDK version or module type alone. Fixing schema generation directly targets this. ESM migration aligns with modern standards and other examples, removing CJS/ESM interop as a variable, and is compatible with SDK 1.8.0 + `zod-to-json-schema`.
- **Alternatives Considered**: SDK Downgrade (doesn't target root cause, poor maintainability), ESM + SDK Downgrade (overly complex, highest risk).
- **Implementation (Recommended Path)**: 1. Fix `zod-to-json-schema` in `index.js`. 2. Test. 3. (If needed/desired) Migrate to ESM (update package.json, convert imports/exports, handle CJS deps, update Jest config). 4. Test thoroughly.
- **Related**: Issue INT-001, `docs/mcp-server-comparison-report.md`


### Decision-PDFLibraryChoice-01 - [2025-04-14 13:50:00]
- **Decision**: Recommend using `PyMuPDF (fitz)` for PDF text extraction within the Python bridge.
- **Rationale**: Offers superior accuracy and speed compared to `PyPDF2` and `pdfminer.six`, crucial for RAG quality. Handles complex layouts well. AGPL-3.0 license is manageable within the server-side context.
- **Alternatives Considered**: `PyPDF2` (simpler, less accurate), `pdfminer.six` (accurate, potentially more complex API).
- **Implementation**: Add `PyMuPDF` to `requirements.txt`. Implement PDF handling in `lib/python-bridge.py` using `fitz`.
- **Related**: Pattern-RAGPipeline-01 (Updated), ComponentSpec-RAGProcessorPython (Updated)


### Decision-CombineDownloadProcess-01 - [2025-04-14 12:07:50]
- **Decision**: Offer both a combined download-and-process workflow and separate download/process steps for RAG document preparation.
- **Rationale**: Provides flexibility. The combined workflow (via an option in `download_book_to_file`) is efficient for immediate use. The separate `process_document_for_rag` tool allows processing of already downloaded or existing files. Addresses user feedback for efficiency while retaining modularity.
- **Implementation**: Add `process_for_rag: boolean` parameter to `download_book_to_file`. Modify its return value to optionally include `processed_text`. Keep `process_document_for_rag` as a separate tool. Update Python bridge to handle the optional processing during download.
- **Related**: Pattern-RAGPipeline-01 (Updated), MCPTool-ProcessDocRAG-01, MCPTool-DownloadBook-01 (Updated)

### Decision-RAGProcessorTech-01 - [2025-04-14 11:41:55]
- **Decision**: Implement the RAG document content extraction/processing logic within the existing Python bridge (`lib/python-bridge.py`).
- **Rationale**: Leverages the established Python virtual environment and bridge mechanism. Python offers superior library support for diverse document formats (EPUB, TXT, future PDF) compared to Node.js. Consolidates Python-related logic.
- **Alternatives Considered**: Node.js implementation (less mature libraries for formats like EPUB), separate microservice (overkill for this stage).
- **Implementation**: Add new function(s) to `python-bridge.py` using libraries like `ebooklib`. Add corresponding calling logic in `lib/zlibrary-api.js`. Add new Python dependencies to `requirements.txt` (or equivalent).
- **Related**: Pattern-RAGPipeline-01, MCPTool-ProcessDocRAG-01


### Decision-PythonEnvStrategy-01 - [2025-04-14 03:29:29]
- **Decision**: Adopt the 'Managed Virtual Environment' strategy for handling the Python dependency (`zlibrary`) in the globally installed `zlibrary-mcp` NPM package.
- **Rationale**: Offers the best balance of reliability (isolated venv), user experience (automated setup post Python 3 install), maintainability, and package size compared to bundling, smarter detection, or rewriting.
- **Alternatives Considered**: Bundling (too large/complex build), Smarter Detection (too fragile), Rewrite in Node.js (high effort, feasibility uncertain), Migrate to Python (out of scope).
- **Implementation**: Node.js logic (post-install/first run) to detect Python 3, create/manage a venv in a cache dir, install `zlibrary` via venv pip, and use the absolute path to venv Python for `python-shell`.
### Feature: RAG Document Pipeline - PDF Processing (Task 3) - [2025-04-14 14:30:00]
- **Status**: TDD Green Phase Complete.
### Jest Test Suite Fix (TS/ESM) - [2025-04-15 05:31:00]
- **Status**: Complete.
- **Details**: All Jest test suites now pass after resolving complex mocking issues in the ESM environment. This involved multiple attempts, delegation to `debug` mode (which implemented Dependency Injection for `venv-manager`), and verification/additions by `tdd` mode.
- **Related**: ADR-001-Jest-ESM-Migration, ActiveContext [2025-04-15 05:31:00]



### Feature: Jest Test Suite Fixes (TS/ESM) - [2025-04-15 05:04:00]
- **Status**: Complete.
- **Details**: Resolved all failures in `__tests__/zlibrary-api.test.js` by refactoring mocks. Failures in `__tests__/venv-manager.test.js` were resolved by a delegated `debug` task, which refactored `src/lib/venv-manager.ts` to use Dependency Injection, bypassing Jest ESM mocking issues for built-in modules. All test suites now pass.
- **Related**: Decision-JestMockingStrategy-01, Decision-DIForVenvManager-01 (Assumed from Debug task), ActiveContext [2025-04-15 05:04:00]


- **Details**: Added `PyMuPDF` to `requirements.txt`. Implemented `_process_pdf` function and integrated it into `process_document` in `lib/python-bridge.py`. Fixed unrelated test failures in `__tests__/index.test.js` by updating outdated expectations. All tests pass (`npm test`).
- **Related**: SpecPseudo [2025-04-14 14:08:30], TDD Red [2025-04-14 14:13:42], Code Green [2025-04-14 14:30:00]
### Issue: INT-001 - Client ZodError / No Tools Found - [2025-04-14 18:23:58]
- **Status**: Debugging Halted; Root Cause Unconfirmed (Server-Side Suspected).
- **Details**: Extensive debugging (response format changes, SDK downgrade, logging, schema isolation) failed to resolve the 'No tools found' error in the client UI, despite server logs indicating ListToolsResponse generation starts. Strong suspicion of incompatibility within `zlibrary-mcp` (SDK v1.8.0/CJS/zodToJsonSchema interaction). User directed halt to debugging.
- **Related**: ActiveContext [2025-04-14 18:19:43], Debug Issue History INT-001


### Feature: Jest Test Suite Fixes (TS/ESM) - [2025-04-15 04:08:00]
### Decision: Version Control Handling in Delegations - [2025-04-28 03:19:37]
- **Context**: User provided clarification following `code` mode's early return.
- **Decision**: Updated SPARC's internal rules for instructing delegated modes on version control:
    - Standard completion: Commit before `attempt_completion`.
    - Early return: Do NOT commit before `attempt_completion`.
    - Task resumption: Do NOT clear workspace before resuming.
    - MB-only changes: Do NOT require cleanup before other tasks.
- **Rationale**: Ensure consistent and appropriate git state management by delegated modes, preventing unnecessary commits on failure and avoiding conflicts during task resumption.
- **Related**: ActiveContext [2025-04-28 03:19:37]
- **Status**: Partially Complete.
- **Details**: Resolved all failures in `__tests__/zlibrary-api.test.js`. Failures in `__tests__/venv-manager.test.js` persist despite multiple attempts using `unstable_mockModule` and `jest.spyOn` for `fs`/`child_process` mocks, adjusting error handling, and disabling Jest transforms. Root cause likely complex interaction between Jest ESM, built-in module mocking, and async rejection handling.
- **Related**: Decision-JestMockingStrategy-01, ActiveContext [2025-04-15 04:08:00]


### Feature: Jest Test Suite Fixes (TS/ESM) - [2025-04-15 04:00:00]
- **Status**: Partially Complete.
- **Details**: Resolved all failures in `__tests__/zlibrary-api.test.js` by refactoring mocks. Failures in `__tests__/venv-manager.test.js` persist despite multiple attempts (correcting `fs` mocks, adjusting error handling, disabling Jest transforms). Root cause likely complex interaction between Jest ESM, built-in module mocking (`fs`, `child_process`), and async rejection handling.
- **Related**: Decision-JestMockingStrategy-01, ActiveContext [2025-04-15 04:00:00]




### Task: Debug `BookNotFound` Error in Forked `zlibrary` Library - [2025-04-16 07:27:22]
- **Status**: Complete.
- **Details**: Added logging to `zlibrary` logger, `libasync.py`, and `abs.py`. Used `fetcher` tool to check direct website response and analyzed logs from `use_mcp_tool` call after enabling logger. Confirmed root cause: Z-Library website search (e.g., `/s/id:3433851?exact=1`) returns a standard search page with 'nothing has been found'. This prevents the library from discovering the correct book page URL (which includes a slug, e.g., `/book/ID/slug`). The library correctly parses the 'not found' response and raises `BookNotFound`. The issue is external website behavior, invalidating the previous `search(id:...)` workaround.
### Task: Version Control Cleanup - [2025-04-24 17:52:23]
- **Status**: Complete.
- **Details**: User requested immediate focus on cleaning up uncommitted Git changes before proceeding with other tasks. Halted TDD delegation for RAG spec implementation. Preparing to delegate Git status analysis and commit task to devops mode.
- **Related**: ActiveContext [2025-04-24 17:52:23]


### Task: TDD Red Phase - RAG Download Workflow (Spec v2.1) - [2025-04-24 17:59:17]
- **Status**: Failed. [See Code Early Return 2025-04-28 03:17:29]
- **Details**: Write failing tests (Red phase) for the RAG download workflow implementation, specifically focusing on the changes introduced in spec v2.1 (using `bookDetails` from `search_books`, internal scraping via `_scrape_and_download`).
### Task: Debug TDD Refactor Blockage (RAG Download Workflow) - [2025-04-28 09:22:38]
- **Status**: Pending Delegation.
- **Details**: Investigate persistent test failures across multiple suites (`__tests__/index.test.js`, `__tests__/python/test_python_bridge.py`) encountered during TDD Refactor phase ([GlobalContext Progress 2025-04-28 04:04:00]). `tdd` mode returned early, suspecting build, cache, environment, or deeper implementation issues. Debug mode should analyze failures, review `tdd` feedback, and identify/fix the root cause.
- **Related**: ActiveContext [2025-04-28 09:22:38], Commit `6746f13`, [GlobalContext Progress 2025-04-28 04:04:00] (Failed Refactor Task), `memory-bank/feedback/tdd-feedback.md` [Timestamp from TDD feedback]
### Task: TDD Refactor Phase - RAG Download Workflow (Spec v2.1) - [2025-04-28 04:04:00]
- **Status**: Failed. [See TDD Early Return 2025-04-28 09:21:23]
- **Details**: Refactor the RAG download workflow implementation (`lib/python_bridge.py`, `src/lib/zlibrary-api.ts`) and associated tests (`__tests__/python/test_python_bridge.py`, `__tests__/zlibrary-api.test.js`) following the successful Green Phase (commit `6746f13`). Ensure code clarity, maintainability, and adherence to project standards while keeping all tests passing.
- **Related**: ActiveContext [2025-04-28 04:04:00], `docs/rag-pipeline-implementation-spec.md` (latest), ADR-002, Commit `6746f13`, [GlobalContext Progress 2025-04-28 03:38:04] (Debug Task), `memory-bank/feedback/tdd-feedback.md` [Timestamp from TDD feedback]
- **Outcome**: `tdd` mode returned early due to persistent, intractable test failures across multiple suites (`__tests__/index.test.js`, `__tests__/python/test_python_bridge.py`) during refactoring. Potential build, cache, environment, or deeper implementation issues suspected.
- **Related**: ActiveContext [2025-04-24 17:59:17], `docs/rag-pipeline-implementation-spec.md` (v2.1)
### Task: Debug TDD Green Phase Blockage (RAG Download Workflow) - [2025-04-28 03:38:04]
- **Status**: Completed. [See Debug Completion 2025-04-28 04:02:58]
- **Details**: Investigate persistent failures preventing completion of TDD Green Phase for RAG download workflow. `code` mode failed twice ([GlobalContext Progress 2025-04-28 02:43:32], [GlobalContext Progress 2025-04-28 03:21:02]) due to `apply_diff` errors on `__tests__/python/test_python_bridge.py`, potentially context-related or tool-related. Debug mode should analyze the failures, review `code` mode feedback, and either fix the tests directly or diagnose the root cause.
- **Related**: ActiveContext [2025-04-28 03:38:04], `docs/rag-pipeline-implementation-spec.md` (latest), ADR-002, `memory-bank/feedback/code-feedback.md` [2025-04-28 03:17:29], `memory-bank/feedback/code-feedback.md` [2025-04-28 03:36:37], `memory-bank/mode-specific/debug.md` [2025-04-28 04:00:45]
- **Outcome**: Debug mode fixed syntax errors in `lib/python_bridge.py` and refactored/corrected tests in `__tests__/python/test_python_bridge.py` (mocking, assertions, structure). Python tests now pass, unblocking TDD Green Phase. Commit: `6746f13`.
### Task: TDD Green Phase - RAG Download Workflow (Spec v2.1) - Retry 1 - [2025-04-28 03:21:02]
- **Status**: Failed. [See Code Early Return 2025-04-28 03:37:14]
- **Details**: Retrying implementation of minimal code changes in `lib/python_bridge.py` and `src/lib/zlibrary-api.ts` to make failing tests pass, according to Spec v2.1. Previous attempt failed due to tool errors ([GlobalContext Progress 2025-04-28 02:43:32]). Delegating via `new_task` for fresh context.
- **Related**: ActiveContext [2025-04-28 03:21:02], `docs/rag-pipeline-implementation-spec.md` (latest), ADR-002, Decision-DownloadScrapingStrategy-01, `memory-bank/feedback/code-feedback.md` [2025-04-28 03:17:29], `memory-bank/feedback/code-feedback.md` [2025-04-28 03:36:37]
- **Outcome**: `code` mode returned early again due to persistent `apply_diff` failures while modifying `__tests__/python/test_python_bridge.py`. Mode incorrectly believed `write_to_file` fallback was forbidden.


- **Related**: Issue-BookNotFound-IDLookup-02, ActiveContext [2025-04-16 07:27:22]


- **Related**: Pattern-ManagedVenv-01, Issue-GlobalExecFail-01
- **Specification**: See SpecPseudo MB entry [2025-04-14 03:31:01]

# Progress
### Task: Update Project Documentation - [2025-04-28 22:19:26]
- **Status**: Completed.
- **Details**: `docs-writer` updated `README.md` to reflect recent fixes (`get_download_history`, `get_recent_books`), tool removal (`get_download_info`), and passing test suites. Commit: `0330d0977dff86e9c90fc15b022a2ace515765df`.
- **Related**: ActiveContext [2025-04-28 22:19:26], Delegation Log [2025-04-28 22:00:24]

### Task: Investigate and Fix Test Suite Issues (TDD) - [2025-04-28 21:59:35]
- **Status**: Completed.
- **Details**: `tdd` resolved TEST-TODO-DISCREPANCY/TEST-REQ-ERROR. Removed obsolete Jest tests, fixed Pytest import/parser logic. Both `npm test` &amp; `pytest` suites pass. Commit: `3e732b3`.
- **Related**: ActiveContext [2025-04-28 21:59:35], Delegation Log [2025-04-28 21:40:16]

### Task: Implement `venv-manager` TODO Tests (TDD) - [2025-04-28 21:39:08]
- **Status**: Completed.
- **Details**: `tdd` implemented 9 TODO tests in `__tests__/venv-manager.test.js`. Test suite passes. Commit assumed successful.
- **Related**: ActiveContext [2025-04-28 21:39:57], Delegation Log [2025-04-28 20:51:37]

### Task: Implement `get_recent_books` Python Bridge Function (TDD) - [2025-04-28 20:50:30]
- **Status**: Completed.
- **Details**: `tdd` implemented `get_recent_books` in `lib/python_bridge.py`. Added tests and fixed regressions. Commit: `75b6f11`.
- **Related**: ActiveContext [2025-04-28 20:50:30], Delegation Log [2025-04-28 19:11:37], Issue-RecentBooksMissing-01

### Task: Fix `get_download_history` Parser (TDD) - [2025-04-28 19:10:43]
- **Status**: Completed.
- **Details**: `tdd` updated parser logic in `zlibrary/src/zlibrary/abs.py` for new HTML structure. Added/updated tests. Commit: `9350af5`.
- **Related**: ActiveContext [2025-04-28 19:10:43], Delegation Log [2025-04-28 18:57:12], Issue-HistoryParseError-01

### Task: Investigate `get_download_history` & `get_recent_books` Errors - [2025-04-28 18:56:31]
- **Status**: Completed.
- **Details**: `debug` identified root causes: broken parser for history (Issue-HistoryParseError-01), missing function for recent books (Issue-RecentBooksMissing-01).
- **Related**: ActiveContext [2025-04-28 18:56:31], Delegation Log [2025-04-28 18:51:41]
### Task: TDD Green Phase - RAG Download Workflow (Spec v2.1) - [2025-04-28 02:43:32]
- **Status**: Pending Delegation.
- **Details**: Implement minimal code changes in `lib/python_bridge.py` and `src/lib/zlibrary-api.ts` to make the failing tests (established in Red Phase [GlobalContext Progress 2025-04-28 02:34:57]) pass, according to Spec v2.1.
- **Related**: ActiveContext [2025-04-28 02:43:32], `docs/rag-pipeline-implementation-spec.md` (latest), ADR-002, Decision-DownloadScrapingStrategy-01, `memory-bank/feedback/code-feedback.md` [2025-04-28 03:17:29]
- **Outcome**: `code` mode returned early due to persistent `apply_diff` failures while modifying `__tests__/python/test_python_bridge.py`, possibly context-related.
### Task: Update README.md - [2025-04-28 02:41:30]
- **Status**: In Progress (DocsWriter).
- **Details**: Updating main project README to reflect current status (RAG pipeline Spec v2.1, TDD Red complete), architecture (Python bridge, vendored `zlibrary` fork, ADR-002 download workflow), and setup instructions.
- **Related**: `README.md`, ADR-002, `docs/architecture/rag-pipeline.md`, `docs/rag-pipeline-implementation-spec.md`
### Task: Update README.md - [2025-04-28 02:39:11]
- **Status**: Complete. [See Docs Completion 2025-04-28 02:42:35]
- **Details**: User requested updating `README.md` to reflect current project status, including the RAG pipeline progress (Spec v2.1, TDD Red Phase complete), the inclusion of the `zlibrary` fork, and other key architectural decisions (e.g., ADR-002). This interrupts the TDD Green Phase delegation.
- **Related**: ActiveContext [2025-04-28 02:39:11], `README.md`
### Task: TDD Red Phase - RAG Download Workflow (Spec v2.1) - [2025-04-28 02:34:57]
- **Status**: Complete. (User confirmed completion 2025-04-28 02:38:09)
- **Details**: Write failing tests (Red phase) for the RAG download workflow implementation, specifically focusing on the changes introduced in spec v2.1 (using `bookDetails` from `search_books`, internal scraping via `_scrape_and_download` in Python bridge, calling `download_book` in `zlibrary` fork).
- **Related**: ActiveContext [2025-04-28 02:34:57], `docs/rag-pipeline-implementation-spec.md` (latest), ADR-002, Decision-DownloadScrapingStrategy-01
### Task: Version Control Cleanup (Git Debt) - [2025-04-28 02:32:41]
- **Status**: Complete.
- **Details**: Committed uncommitted changes (RAG tests, venv updates, MB logs, zlibrary fork) in 4 logical commits (87c4791, 61d153e, 8eb4e3b, df840fa) on branch feature/rag-file-output. Added processed_rag_output/ to .gitignore.
- **Related**: ActiveContext [2025-04-28 02:32:25], Decision-PrioritizeGitCleanup-01
### Task: Version Control Cleanup (Git Debt) - [2025-04-28 02:23:30]
- **Status**: Complete. [See DevOps Completion 2025-04-28 02:33:43]
- **Details**: DevOps analyzed `git status`, added `processed_rag_output/` to `.gitignore`, and committed changes in 5 logical commits (87c4791, 61d153e, 8eb4e3b, df840fa, 4f103f2) on `feature/rag-file-output`. Working directory clean.
- **Related**: ActiveContext [2025-04-28 02:20:01], Decision-PrioritizeGitCleanup-01
### Task: Implement `download_book` in Forked Library - [2025-04-24 03:49:26]
- **Status**: Complete.
- **Details**: Implemented the missing `download_book` async method in `zlibrary/src/zlibrary/libasync.py` using `httpx` and `aiofiles`. Added `DownloadError` exception and updated dependencies (`httpx`, `aiofiles`) in `zlibrary/pyproject.toml`. Committed changes (8a30920) to `feature/rag-file-output`. Addresses INT-RAG-003.
- **Related**: ActiveContext [2025-04-24 03:49:26], Issue INT-RAG-003


<!-- Entries below should be added reverse chronologically (newest first) -->
### Task: Re-Verify RAG `download_book_to_file` Integration - [2025-04-24 16:36:00]
- **Status**: Halted.
- **Details**: Verification blocked by intractable errors in the `zlibrary` fork's download logic (dependency issues, signature mismatches, scraping failures). Requires dedicated fix in the library before integration can proceed.
- **Related**: Issue INT-RAG-DOWNLOAD-REPLAN, ActiveContext [2025-04-24 16:36:00]


### Task: Verify RAG File Output Integration - [2025-04-24 03:07:03]
- **Status**: Partially Complete (Verification Blocked).
- **Details**: Verified `process_document_for_rag` works for PDF, EPUB, TXT on `feature/rag-file-output` branch. Output correctly saved to `./processed_rag_output/`. Verification of `download_book_to_file` (combined workflow) is blocked due to missing `download_book` method implementation in the forked `zlibrary` library (AttributeError). `npm test` passed, but with 17 TODOs (6 more than expected) and a console error about `requirements.txt` path. Memory Bank updates were successful after initial rejections.
- **Related**: ActiveContext [2025-04-24 03:06:50], Integration Issues INT-RAG-001, INT-RAG-002, INT-RAG-003, TEST-REQ-ERROR, TEST-TODO-DISCREPANCY.

### Task: RAG Pipeline - Feature Branch Creation - [2025-04-24 01:46:10]
- **Status**: Complete.
- **Details**: Created feature branch `feature/rag-file-output` after committing RAG Green Phase changes (commit d6bd8ab) and Memory Bank updates (commit 144429b) to `master`.
- **Related**: ActiveContext [2025-04-24 01:46:10]


### Task: RAG Pipeline (EPUB/TXT/PDF) - File Output Redesign - [2025-04-24 00:57:19]
- **Status**: Refinement (TDD Refactor Phase Pending).
- **Details**: Integration verification (Tasks 2 & 3) halted due to critical design flaw ([Ref: SPARC Feedback 2025-04-23 23:26:20]). Architecture redesigned ([Ref: Architect Completion 2025-04-23 23:30:58]), specifications updated ([Ref: Spec/Pseudo Completion 2025-04-23 23:40:42]), TDD Red phase completed ([Ref: TDD Completion 2025-04-23 23:51:14]), and TDD Green phase implementation completed ([Ref: Code Completion 2025-04-24 00:57:19]). Awaiting Refactor phase.
- **Related**: Decision-RAGOutputFile-01, Pattern-RAGPipeline-FileOutput-01, Intervention [2025-04-23 23:26:50]


### Task: Search-First ID Lookup (TDD Refactor Phase) - [2025-04-16 18:49:56]
- **Status**: Complete.
- **Details**: Refactored `lib/python_bridge.py` (clarity, DRY, consistency). Verified with `pytest` and `npm test` (all passing).
### Task: Debug REG-001 (Tool Call Regression) - [2025-04-23 22:12:51]
- **Status**: Complete.
- **Details**: Resolved 'Invalid tool name type' error by correcting tool name key usage (`name` vs `tool_name`) in `src/index.ts`. Resolved subsequent Python `TypeError` by fixing argument serialization/passing between Node.js (`src/lib/zlibrary-api.ts`) and Python (`lib/python_bridge.py`). Updated Jest tests (`__tests__/zlibrary-api.test.js`) to match correct argument structure. Verified with manual tool calls and `npm test`.
- **Related**: Issue REG-001, ActiveContext [2025-04-23 22:12:51]


- **Related**: ActiveContext [2025-04-16 18:49:56]



### Task: Search-First ID Lookup (TDD Green Phase) - [2025-04-16 18:40:05]
- **Status**: Complete.
- **Details**: Implemented Search-First strategy in `lib/python_bridge.py` per spec. Added `pytest-asyncio` and fixed related Python test issues. Python and Node tests pass.
- **Related**: `docs/search-first-id-lookup-spec.md`, ActiveContext [2025-04-16 18:40:05]



### Task: Search-First ID Lookup (Red Phase) - [2025-04-16 18:21:19]
- **Status**: Red Phase Complete.
- **Details**: Added 13 xfail tests to `__tests__/python/test_python_bridge.py` covering `_internal_search` and modified `_internal_get_book_details_by_id` functions per `docs/search-first-id-lookup-spec.md`. Added dummy exceptions/functions to allow test collection. Verified xfail status via pytest.
- **Related**: `docs/search-first-id-lookup-spec.md`, ActiveContext [2025-04-16 18:21:19]



### Task: Verify Internal ID Lookup Integration - [2025-04-16 18:08:00]
- **Status**: Complete.
- **Details**: Manually verified `get_book_by_id`, `get_download_info`, `download_book_to_file` consistently return 'Book ID ... not found.' error for 404 scenarios (valid/invalid IDs) using internal `httpx` logic. `npm test` passes.
- **Related**: ActiveContext [2025-04-16 18:08:00]



### Task: Internal ID Lookup (TDD Refactor Phase) - [2025-04-16 08:42:01]
- **Status**: Complete.
- **Details**: Refactored `_internal_get_book_details_by_id` in `lib/python_bridge.py` for clarity (renamed exception vars, added comments for placeholder selectors, removed redundant response check). Verified with `pytest` (PASS: 16 skipped, 13 xfailed, 4 xpassed) and `npm test` (PASS: 4 suites, 47 tests, 11 todo).
- **Related**: `docs/internal-id-lookup-spec.md`, ActiveContext [2025-04-16 08:42:01]



### Task: Internal ID Lookup (TDD Green Phase) - [2025-04-16 08:38:32]
- **Status**: Complete.
- **Details**: Implemented `_internal_get_book_details_by_id` in `lib/python_bridge.py` and updated callers (`get_by_id`, `get_download_info`) per spec. Fixed Python test errors (venv path, missing deps, exception logic, test assertions). Python & Node tests pass.
- **Related**: `docs/internal-id-lookup-spec.md`, ActiveContext [2025-04-16 08:38:32]


### Task: Internal ID Lookup (Red Phase) - [2025-04-16 08:18:43]
- **Status**: Red Phase Complete.
- **Details**: Added failing/xfail tests to `__tests__/python/test_python_bridge.py` covering `_internal_get_book_details_by_id` function (404, HTTP errors, network errors, parsing) and caller modifications (`get_by_id`, `get_download_info`). Added `httpx` dependency to `requirements.txt`.
- **Related**: `docs/internal-id-lookup-spec.md`, ActiveContext [2025-04-16 08:18:43]


### Task: Debug `BookNotFound` Error in Forked `zlibrary` Library - [2025-04-16 07:23:30]
- **Status**: Complete.
- **Details**: Added logging to `zlibrary` logger, `libasync.py`, and `abs.py`. Used `fetcher` tool to check direct website response and analyzed logs from `use_mcp_tool` call after enabling logger. Confirmed root cause: Z-Library website search (e.g., `/s/id:3433851?exact=1`) returns a standard search page with 'nothing has been found'. The library correctly parses this, finds no results, and raises `BookNotFound`. The issue is external website behavior, invalidating the previous `search(id:...)` workaround.
- **Related**: Issue-BookNotFound-IDLookup-02, ActiveContext [2025-04-16 07:23:30]


### Task: Fix `zlibrary` ID Lookup Bugs - [2025-04-16 00:03:00]
- **Status**: Complete.
- **Details**: Applied fixes to `zlibrary/src/zlibrary/libasync.py` and `zlibrary/src/zlibrary/abs.py` based on the provided strategy. `get_by_id` now uses search. `SearchPaginator.parse_page` now handles potential direct book page results from `id:` searches.
- **Related**: Issue-ParseError-IDLookup-01, Decision-IDLookupStrategy-01, ActiveContext [2025-04-16 00:02:36]


### Task: Locate `zlibrary` Source Code - [2025-04-15 23:14:52]
- **Status**: Complete.
- **Details**: Successfully located the source code repository for the external `zlibrary` Python library (v1.0.2) using `pip show zlibrary`. The repository is at `https://github.com/sertraline/zlibrary`.
- **Related**: Decision-IDLookupStrategy-01


### Feature: ID Lookup Workaround (TDD Green Phase) - [2025-04-15 22:39:35]
- **Status**: Complete.
- **Details**: Implemented search-based workaround for `get_by_id` and `get_download_info` in `lib/python_bridge.py`. Fixed associated Python tests (`__tests__/python/test_python_bridge.py`) and Node.js regressions (`__tests__/zlibrary-api.test.js`, `__tests__/python-bridge.test.js`). All tests pass.
- **Related**: Decision-ParseErrorWorkaround-01, ActiveContext [2025-04-15 22:39:35]


### Issue: `ParseError` on ID-Based Lookups - Workaround Proposed - [2025-04-15 21:51:00]
- **Status**: Investigation Complete; Workaround Proposed.
- **Details**: Diagnosed `zlibrary.exception.ParseError` affecting `get_book_by_id` and `get_download_info`. Confirmed root cause is incorrect URL construction (missing slug) in the external `zlibrary` library's `get_by_id` method. Proposed a workaround using `client.search(q=f'id:{id}')` within `lib/python_bridge.py`.
- **Related**: Issue-ParseError-IDLookup-01, Decision-ParseErrorWorkaround-01, ActiveContext [2025-04-15 21:51:00]

### Feature: PDF Processing RAG (Task 3) - AttributeError Fix - [2025-04-15 20:46:14]
- **Status**: Resolved.
- **Details**: Fixed `AttributeError: module 'fitz' has no attribute 'fitz'` (and subsequent `AttributeError: module 'fitz' has no attribute 'RuntimeException'`) in `lib/python_bridge.py` by correcting the exception handler to catch generic `RuntimeError`. Also resolved subsequent `pytest` import errors by renaming the file (`lib/python_bridge.py`) and cleaning the test file (`__tests__/python/test_python_bridge.py`). Manual verification with a valid PDF (`__tests__/assets/sample.pdf`) confirmed the tool now works correctly.
- **Related**: ActiveContext [2025-04-15 20:46:14], Debug Issue History PDF-AttrError-01


### Jest Test Suite Fix (TS/ESM) - Confirmation [2025-04-15 13:44:48]
- **Status**: Confirmed Complete.
- **Details**: After a task reset due to context window issues, confirmed via Memory Bank that all Jest tests were previously fixed and passing as of [2025-04-15 05:31:00].
- **Related**: ActiveContext [2025-04-15 13:44:30]



### Feature: Jest Test Suite Fixes (TS/ESM - venv-manager) - [2025-04-15 04:31:00]
- **Status**: Resolved.
- **Details**: Fixed 3 persistent failing tests in `__tests__/venv-manager.test.js`. Refactored `src/lib/venv-manager.ts` for dependency injection (DI) of `fs`/`child_process`, updated tests to use DI mocks, corrected `requirements.txt` path logic, and ensured clean build/cache. All tests now pass.
- **Related**: Decision-VenvManagerDI-01, ActiveContext [2025-04-15 04:31:00]


### Feature: Jest Test Suite Fixes (TS/ESM) - [2025-04-15 03:41:00]
- **Status**: Partially Complete.
- **Details**: Resolved all failures in `__tests__/zlibrary-api.test.js` by refactoring mocks to target API functions directly instead of `python-shell`. Failures in `__tests__/venv-manager.test.js` persist despite multiple attempts to fix `fs` and `child_process` mocks using `unstable_mockModule` and adjusting error handling. Root cause likely complex interaction between Jest ESM, built-in module mocking, and dynamic imports.
- **Related**: Decision-JestMockingStrategy-01


### Issue: INT-001 - Client ZodError / No Tools Found - [2025-04-14 19:36:54]
- **Status**: Investigation Concluded; Likely Client-Side Issue.
- **Details**: Exhausted server-side fixes for `index.js` based on analysis reports and external examples (correcting `zodToJsonSchema` usage, CJS import, handling empty schemas, removing try-catch). Issue persists. GitHub issue search revealed RooCode issue #2085 describing identical behavior, suggesting a regression in RooCode v3.9.0+ affecting MCP server discovery/display.
- **Related**: ActiveContext [2025-04-14 19:36:24], `docs/mcp-client-tool-failure-analysis.md`, `docs/mcp-server-comparison-report.md`, RooCode Issue #2085



### Issue: INT-001 - Client ZodError / No Tools Found - [2025-04-14 19:29:08]
- **Status**: Refining Fix Attempt (Attempt 2.1).
- **Details**: Based on analysis reports confirming dummy schemas as the likely root cause, refined the previous fix in `index.js`. Corrected the CJS import for `zod-to-json-schema` (removed `.default`) and uncommented all tools in the `toolRegistry` to ensure they are processed by the schema generation logic.
- **Related**: ActiveContext [2025-04-14 19:28:55], `docs/mcp-client-tool-failure-analysis.md`, `docs/mcp-server-comparison-report.md`



### Issue: INT-001 - Client ZodError / No Tools Found - [2025-04-14 19:26:45]
- **Status**: Fix Attempt Failed (Attempt 2).
- **Details**: Modified `index.js` ListToolsRequest handler to correctly use `zod-to-json-schema` and skip tools that fail generation. User confirmed client UI still shows 'No tools found'. The fix targeting schema generation alone was insufficient.
- **Related**: ActiveContext [2025-04-14 19:26:32], Decision-MigrationStrategy-INT001



### Documentation: MCP Server Comparison Report - [2025-04-14 17:50:25]
- **Status**: Draft Complete (Awaiting Comparison Data).
- **Details**: Created initial draft of `docs/mcp-server-comparison-report.md`. Analyzed `zlibrary-mcp` implementation (SDK v1.8.0, CJS, tool registration, schema handling). Identified dummy schema usage as potential issue related to INT-001. Report includes placeholders for comparison data from other servers.
- **Related**: ActiveContext [2025-04-14 17:49:54]


### Feature: RAG Document Pipeline - PDF Processing (Task 3) - [2025-04-14 14:50:58]
- **Status**: Integration Verification Blocked.
- **Details**: Code review confirmed `PyMuPDF` dependency and correct logic in `lib/python-bridge.py`. Dependency installation assumed correct based on prior tests. End-to-end verification (manual/automated tests) blocked by client-side ZodError (INT-001) preventing tool calls needed to obtain test data (Book IDs).
- **Related**: ActiveContext [2025-04-14 14:50:58], Issue INT-001


### Feature: RAG Document Pipeline - PDF Processing (Task 3) - [2025-04-14 14:25:00]
- **Status**: TDD Green Phase Implementation Complete.
- **Details**: Added `PyMuPDF` to `requirements.txt`. Implemented `_process_pdf` function and integrated it into `process_document` in `lib/python-bridge.py` following `docs/pdf-processing-implementation-spec.md`. Ready for test execution (`npm test`).
- **Related**: SpecPseudo [2025-04-14 14:08:30], TDD Red [2025-04-14 14:13:42], Code Green [2025-04-14 14:25:00]


### Feature: RAG Document Pipeline - PDF Processing (Task 3) - [2025-04-14 14:08:30]
- **Status**: Specification Complete.
- **Details**: Generated detailed specification and pseudocode for integrating PDF processing using PyMuPDF into the Python bridge, based on architecture doc. Saved to `docs/pdf-processing-implementation-spec.md`.
- **Related**: SpecPseudo [2025-04-14 14:08:30], Architecture `docs/architecture/pdf-processing-integration.md`


### Feature: RAG Document Pipeline (Task 2) - Integration - [2025-04-14 13:15:49]
- **Status**: Paused.
- **Details**: Integration paused due to persistent client-side ZodError ('Expected array, received undefined' at path 'content') when calling tools on zlibrary-mcp server. Error occurs even for tools returning objects. Suspected issue in client response parsing logic. Requires investigation of client-side code or MCP specification.
- **Related**: ActiveContext [2025-04-14 13:15:36]


### Feature: RAG Document Pipeline (Task 2) - [2025-04-14 12:58:00]
- **Status**: TDD Refactor Phase Complete.
- **Details**: Refactored Python bridge (`_parse_enums` helper, removed dead code) and Node API (`processDocumentForRag` argument handling, error check). Fixed associated test mocks and assertions. All tests pass.
- **Related**: SpecPseudo [2025-04-14 12:13:00], TDD Red [2025-04-14 12:23:43], Code Green [2025-04-14 12:30:35], TDD Refactor [2025-04-14 12:58:00]


### Feature: RAG Document Pipeline (Task 2) - [2025-04-14 12:30:55]
- **Status**: TDD Green Phase Implementation Complete.
- **Details**: Implemented dual workflow (combined/separate download & process) via `download_book_to_file` update and new `process_document_for_rag` tool. Updated Node.js handlers (`lib/zlibrary-api.js`) and Python bridge (`lib/python-bridge.py`) with EPUB/TXT processing logic using `ebooklib` and `BeautifulSoup`. Updated `lib/venv-manager.js` to install dependencies (`ebooklib`, `beautifulsoup4`, `lxml`) from `requirements.txt`. Test run (`npm test`) shows remaining failures are within test files (mocks, expectations), not implementation logic.
- **Related**: SpecPseudo [2025-04-14 12:13:00], TDD Red [2025-04-14 12:23:43], Code Green [2025-04-14 12:30:35]


### Feature: Global Execution Fix - [2025-04-14 10:20:37]
- **Status**: Integration Complete (Server Starts). `index.js` tests failing due to SDK refactoring.
- **Details**: Integrated `lib/venv-manager.js` changes. Refactored `index.js` to use correct MCP SDK v1.8.0 imports (`Server`, `StdioServerTransport`, types), instantiation (`new Server`), connection (`server.connect`), and tool registration (`tools/list`, `tools/call` handlers with Zod schemas). Manual tests confirm venv creation/validation and server startup. `index.js` tests require updates to match refactored SDK usage.
- **Related**: SpecPseudo [2025-04-14 03:31:01], TDD Red [2025-04-14 03:35:45], TDD Green [2025-04-14 04:11:16], TDD Refactor [2025-04-14 04:15:38], Debug [2025-04-14 10:18:16], Integration [2025-04-14 10:20:18]


### Feature: Global Execution Fix - [2025-04-14 04:11:38]
- **Status**: TDD Refactor Phase Complete.
- **Details**: Implemented `lib/venv-manager.js` and updated `index.js`, `lib/zlibrary-api.js` to use managed venv. Corrected Node SDK import. Removed obsolete `lib/python-env.js`. Added `env-paths` dependency. Refactored `venv-manager.js`, `index.js`, `zlibrary-api.js` for clarity and consistency. Updated tests in `__tests__/zlibrary-api.test.js`. All tests pass.
- **Related**: SpecPseudo [2025-04-14 03:31:01], TDD Red [2025-04-14 03:35:45], TDD Green [2025-04-14 04:11:16], TDD Refactor [2025-04-14 04:15:38]
