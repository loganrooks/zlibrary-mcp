# System Integrator Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
### Issue: INT-RAG-DOWNLOAD-REPLAN - Intractable Download Logic Failures - Status: Open - [2025-04-24 16:36:00]
- **Identified**: [2025-04-24 16:29:56]
- **Components**: [zlibrary-mcp: download_book_to_file], [lib/python_bridge.py: download_book], [zlibrary/src/zlibrary/libasync.py: download_book]
- **Symptoms**: Repeated, cascading errors (`TypeError`, `NameError`, `AttributeError`, `ValueError`, `DownloadError`) when attempting to verify `download_book_to_file`. Errors relate to dependency installation (`aiofiles`), incorrect function call signatures between bridge and library, incorrect assumptions about available data (`download_url`), and incorrect usage/handling of the library's internal request method (`_r`).
- **Root Cause**: The core logic for downloading requires scraping the book's HTML page (from `bookDetails['url']`) to find the actual download link. Attempts to implement and fix this scraping logic within the `integration` task led to a repetitive error loop, indicating the fix requires more focused effort.
- **Resolution**: Halt current integration verification task. Delegate the implementation and isolated testing of the download URL scraping logic within `zlibrary/src/zlibrary/libasync.py` to `code`/`tdd` mode. Mark dependent test scenarios as blocked.
- **Related Issues**: INT-RAG-003, User Feedback [2025-04-24 16:29:56]


### Issue: INT-RAG-003 - AttributeError: Missing download_book method in AsyncZlib - Status: Open - [2025-04-24 03:05:26]
- **Identified**: [2025-04-24 02:55:41]
- **Components**: [lib/python_bridge.py: download_book], [zlibrary: AsyncZlib (forked)]
- **Symptoms**: Calling `download_book_to_file` tool fails with `AttributeError: 'AsyncZlib' object has no attribute 'download_book'`.
- **Root Cause**: The `download_book` method has not yet been implemented in the forked `zlibrary` Python library (in `zlibrary/src/zlibrary/`), which is called by the `download_book` function in `lib/python_bridge.py`.
- **Resolution**: Implement the `download_book` method in the forked `zlibrary` library. Verification of Task 4 (`download_book_to_file` combined workflow) is blocked until this is done.
- **Related Issues**: User Feedback [2025-04-24 03:05:26]

### Issue: TEST-REQ-ERROR - requirements.txt Not Found in Tests - Status: Open - [2025-04-24 02:57:04]
- **Identified**: [2025-04-24 02:57:04]
- **Components**: [Jest Test Suite], [src/lib/venv-manager.ts]
- **Symptoms**: `npm test` logs console error `ERROR: Could not open requirements file: [Errno 2] No such file or directory: '/home/rookslog/zlibrary-mcp/requirements.txt'` during `venv-manager.test.js` execution.
- **Root Cause**: Likely an incorrect path resolution for `requirements.txt` within the test environment setup for `venv-manager.ts`.
- **Resolution**: Investigate path logic in `venv-manager.ts` and/or test setup.
- **Related Issues**: None

### Issue: TEST-TODO-DISCREPANCY - Unexpected TODO Tests - Status: Open - [2025-04-24 02:57:04]
- **Identified**: [2025-04-24 02:57:04]
- **Components**: [Jest Test Suite], [__tests__/zlibrary-api.test.js], [__tests__/index.test.js]
- **Symptoms**: `npm test` reports 17 'todo' tests, whereas only 11 were expected (from `venv-manager.test.js`).
- **Root Cause**: Additional 'todo' tests exist in `zlibrary-api.test.js` (4) and `index.test.js` (2).
- **Resolution**: Review and address the 'todo' tests in the affected suites.
- **Related Issues**: None

### Issue: INT-RAG-002 - Stale Code Execution / Missing processed_text - Status: Resolved - [2025-04-24 02:53:26]
- **Identified**: [2025-04-24 02:37:18]
- **Components**: [zlibrary-mcp Server Process], [RooCode Extension]
- **Symptoms**: `process_document_for_rag` failed with `Invalid response from Python bridge during processing. Missing processed_text.` even after `npm run build`. Source code (TS/JS/PY) correctly used `processed_file_path`.
- **Root Cause**: Server process was likely running outdated compiled code. Build process (`npm run build`) alone is insufficient; manual server restart via RooCode UI is required.
- **Resolution**: User manually restarted the server via RooCode UI. Subsequent tool call succeeded.
- **Resolved Date**: [2025-04-24 02:53:26]

### Issue: INT-RAG-001 - NameError: name 'os' is not defined - Status: Resolved - [2025-04-24 02:36:53]
- **Identified**: [2025-04-24 02:36:06]
- **Components**: [lib/python_bridge.py]
- **Symptoms**: Calling `process_document_for_rag` failed with `NameError: name 'os' is not defined`.
- **Root Cause**: `import os` statement was missing or commented out in `lib/python_bridge.py`.
- **Resolution**: Added `import os` at the top of `lib/python_bridge.py`.
- **Resolved Date**: [2025-04-24 02:36:53]


## Integration Issues Log
### Issue: RAG-VERIFY-BLK-01 - RAG Verification Blocked by ID Lookup Failure - Status: Open - [2025-04-23 23:18:00]
- **Identified**: [2025-04-23 23:17:00]
- **Components**: [zlibrary-mcp: download_book_to_file], [lib/python_bridge.py: _internal_search]
- **Symptoms**: Attempts to verify RAG EPUB/TXT processing (Task 2) by calling `download_book_to_file` (with or without `process_for_rag: true`) fail with `ValueError: Book ID ... not found.`.
- **Root Cause**: The underlying 'Search-First' ID lookup strategy in `lib/python_bridge.py` fails to find book links on the search results page (`/s/BOOK_ID`) using current selectors (`#searchResultBox .book-item`), preventing download by ID.
- **Resolution**: Verification blocked. Debugging of ID lookup deferred per user instruction. Requires investigation/fix of selectors or lookup strategy in `lib/python_bridge.py`.
- **Related Issues**: [Issue-BookNotFound-IDLookup-02 (Assumed ID)], [ActiveContext 2025-04-23 23:17:00]


<!-- Append issues using the format below -->
### Issue: INT-001 - Client ZodError on Tool Call - Status: Open - [2025-04-14 13:16:12]
- **Identified**: [2025-04-14 13:10:48]
- **Components**: MCP Client (RooCode), zlibrary-mcp Server
- **Symptoms**: Client throws `ZodError: Expected array, received undefined` at path `content` when parsing `CallToolResponse` from `zlibrary-mcp`, even for tools returning objects (e.g., `get_download_limits`, `search`).
- **Root Cause**: Suspected client-side parsing logic incorrectly expects the `content` field in the response to *always* be an array, failing validation when it's an object.
- **Resolution**: Paused integration task. Needs investigation of client-side parsing code or MCP specification regarding `CallToolResponse` structure. **Blocked Task 3 (PDF Integration) verification [2025-04-14 14:50:58].**
- **Resolved Date**: N/A


## Integration Test Scenarios
### Scenario: RAG File Output - process_document_for_rag (TXT) - [2025-04-24 02:54:55]
- **Components**: [zlibrary-mcp: process_document_for_rag], [lib/python_bridge.py: process_document, _process_txt, _save_processed_text]
- **Steps**: 1. Call `process_document_for_rag` with `file_path: "test_files/sample.txt"`. 2. Read `processed_rag_output/sample.txt.processed.text`.
- **Expected**: Tool returns `{"processed_file_path": "processed_rag_output/sample.txt.processed.text"}`. Output file contains original text.
- **Status**: Manual
- **Last Run**: [2025-04-24 02:54:55] - PASS

### Scenario: RAG File Output - process_document_for_rag (EPUB) - [2025-04-24 02:54:23]
- **Components**: [zlibrary-mcp: process_document_for_rag], [lib/python_bridge.py: process_document, _process_epub, _save_processed_text]
- **Steps**: 1. Call `process_document_for_rag` with `file_path: "test_files/sample.epub"`. 2. Read `processed_rag_output/sample.epub.processed.text`.
- **Expected**: Tool returns `{"processed_file_path": "processed_rag_output/sample.epub.processed.text"}`. Output file contains extracted text.
- **Status**: Manual
- **Last Run**: [2025-04-24 02:54:23] - PASS

### Scenario: RAG File Output - process_document_for_rag (PDF) - [2025-04-24 02:53:48]
- **Components**: [zlibrary-mcp: process_document_for_rag], [lib/python_bridge.py: process_document, _process_pdf, _save_processed_text]
- **Steps**: 1. Call `process_document_for_rag` with `file_path: "test_files/sample.pdf"`. 2. Read `processed_rag_output/sample.pdf.processed.text`.
- **Expected**: Tool returns `{"processed_file_path": "processed_rag_output/sample.pdf.processed.text"}`. Output file contains extracted text.
- **Status**: Manual
- **Last Run**: [2025-04-24 02:53:48] - PASS (after fixing INT-RAG-001, INT-RAG-002)

### Scenario: RAG File Output - download_book_to_file (Combined) - [2025-04-24 02:56:35]
- **Components**: [zlibrary-mcp: download_book_to_file], [lib/python_bridge.py: download_book], [zlibrary: AsyncZlib (forked)]
- **Steps**: 1. Call `download_book_to_file` with `process_for_rag: true` for EPUB/TXT/PDF IDs. 2. Verify original file exists. 3. Verify processed file exists in `./processed_rag_output/`. 4. Read processed file.
- **Expected**: Tool returns `{"file_path": "...", "processed_file_path": "..."}`. Both files exist and processed file contains text.
  - Blocked by INT-RAG-DOWNLOAD-REPLAN.
- **Status**: Blocked
- **Last Run**: [2025-04-24 02:55:41] - FAIL (Blocked by INT-RAG-003: `AttributeError` due to missing `download_book` method in forked library)


<!-- Append test scenarios using the format below -->
### Scenario: PDF Processing (Task 3) - [2025-04-14 14:50:58]
- **Components**: [zlibrary-mcp: download_book_to_file, process_document_for_rag], [lib/python-bridge.py: _process_pdf]
- **Steps**: 1. Combined Workflow (Std PDF) 2. Separate Workflow (Std PDF) 3. Error Handling (Encrypted) 4. Error Handling (Image) 5. Error Handling (Not Found)
- **Expected**: Success with text/path for standard, specific errors for error cases.
- **Status**: Blocked
 - Blocked by ID lookup failure (RAG-VERIFY-BLK-01).
- **Last Run**: N/A - Blocked by client issue INT-001 preventing acquisition of test Book IDs.


### Integration: Global Execution Fix - [2025-04-14 10:20:48]
- **Components Integrated**: `lib/venv-manager.js`, `index.js`, `lib/zlibrary-api.js`.
- **Verification**: Manual run (`rm -rf ~/.cache/zlibrary-mcp && node index.js`) confirmed successful venv creation, dependency installation (`zlibrary`), and server startup via Stdio transport. Core logic (`ensureVenvReady`, `getManagedPythonPath`) functions correctly.
- **Issues Encountered**: 
    - Multiple SDK import errors (`ERR_PACKAGE_PATH_NOT_EXPORTED`, `TypeError: createServer is not a function`, `TypeError: server.start is not a function`) due to SDK structure and CommonJS interop. Resolved by using correct import paths (`@modelcontextprotocol/sdk/server/index.js`, `@modelcontextprotocol/sdk/server/stdio.js`, `@modelcontextprotocol/sdk/types.js`), instantiating `Server` class, and using `StdioServerTransport` with `server.connect()`.
    - `ERR_REQUIRE_ESM` for `env-paths`. Resolved by using dynamic `import()` in `lib/venv-manager.js` and making dependent functions async.
    - SDK schema loading issue (`TypeError: Cannot read properties of undefined (reading 'shape')`) for `ListToolsRequestSchema`/`CallToolRequestSchema`. Debugged via separate task (`Issue-MCP-SDK-CJS-Import`), root cause identified as incorrect schema names in `index.js` (`ToolsList...` vs `ListTools...`). Corrected names.
- **Test Status**: `npm test` shows failures in `__tests__/index.test.js` due to necessary SDK refactoring (mocks need updating). Other test suites pass. Tests hung after completion (requires separate investigation).
- **Dependency Map**: No changes to inter-service dependencies. Updated internal dependency on `@modelcontextprotocol/sdk` v1.8.0, `zod`, `zod-to-json-schema`.
- **Integration Points**: 
    - `index.js` -> `lib/venv-manager.js` (`ensureVenvReady`)
    - `lib/zlibrary-api.js` -> `lib/venv-manager.js` (`getManagedPythonPath`)
    - `index.js` -> `@modelcontextprotocol/sdk` (Server, StdioTransport, Types)
    - `index.js` -> `lib/zlibrary-api.js` (Tool handlers)

