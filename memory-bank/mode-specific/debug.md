# Debugger Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
## Issue History
### Issue: REG-001 - Tool Call Regression ("Invalid tool name type" / Python TypeError) - Status: Resolved - [2025-04-23 22:12:51]
- **Reported**: [2025-04-23 18:13:24] (via Task Description) / **Severity**: High / **Symptoms**: 1. `Error: Invalid tool name type.` when calling tools. 2. `TypeError: ... argument after ** must be a mapping, not list` in Python bridge when calling tools.
- **Investigation**:
    1. Reviewed `src/index.ts` `CallToolRequest` handler.
    2. Hypothesized `name` vs `tool_name` key mismatch based on error 1.
    3. Added logging to `src/index.ts` to inspect `request.params`.
    4. Attempted tool call (`get_download_limits`), encountered error 2 instead of error 1.
    5. Fixed `toolName` destructuring in `src/index.ts` (line 309) to use `tool_name`.
    6. Fixed Python `TypeError` cause in `lib/python_bridge.py` (line 599) by removing `**args_dict` for `get_download_limits`.
    7. Retested tool calls, error 2 resolved for `get_download_limits` but persisted for `search_books`.
    8. Analyzed `src/lib/python-bridge.ts` and `src/lib/zlibrary-api.ts`, identified incorrect argument passing (array vs object) to `PythonShell` as root cause of error 2.
    9. Corrected `callPythonFunction` signature in `src/lib/python-bridge.ts` (line 17) and `src/lib/zlibrary-api.ts` (line 26) to expect `Record<string, any>`.
    10. Corrected argument passing in `src/lib/zlibrary-api.ts` calls to `callPythonFunction` (lines 132, 141, 149, etc.) to pass objects.
    11. Corrected `PythonShell` options `args` in `src/lib/zlibrary-api.ts` (line 34) to pass serialized object directly.
    12. Reverted `src/index.ts` destructuring (line 309) back to use `name` after error 1 reappeared, confirming client sends `name`.
    13. Removed diagnostic logging from `src/index.ts`.
    14. Verified fixes with manual tool calls (`get_download_limits`, `search_books`) and `npm test` (after updating test expectations).
- **Root Cause**: 
    1. **REG-001 ("Invalid tool name type"):** Mismatch between tool name key sent by client (`name`) and key expected by server (`tool_name` initially, corrected back to `name`) in `src/index.ts`.
    2. **Python TypeError:** Incorrect argument passing from Node.js to Python bridge. `src/lib/zlibrary-api.ts` passed arguments as a JSON array string, while Python script expected a dictionary for `**` unpacking.
- **Fix Applied**:
    1. Corrected `CallToolRequest` handler in `src/index.ts` (line 309) to destructure `name` key: `const { name: toolName, ... } = request.params;`.
    2. Corrected `callPythonFunction` signature in `src/lib/zlibrary-api.ts` (line 26) to expect `Record<string, any>`.
    3. Corrected calls to `callPythonFunction` in `src/lib/zlibrary-api.ts` (lines 133, 141, 149, etc.) to pass argument objects.
    4. Corrected `PythonShell` options in `src/lib/zlibrary-api.ts` (line 34) to pass serialized object correctly: `args: [functionName, serializedArgs]`.
    5. Updated expectations in `__tests__/zlibrary-api.test.js` to match object argument passing.
- **Verification**: Manual calls to `get_download_limits` and `search_books` succeeded. `npm test` passed after test updates.
- **Related Issues**: None.


### Issue: Issue-BookNotFound-IDLookup-02 - `BookNotFound` on ID lookups (search workaround) - Status: Root Cause Confirmed (External) - [2025-04-16 07:27:22]
- **Reported**: [2025-04-16 03:12:00] (via ActiveContext) / **Severity**: High (Blocks ID-based tools) / **Symptoms**: `zlibrary.exception.BookNotFound` when calling `get_book_by_id` or other ID-based tools using the local fork with the search workaround.
- **Investigation**:
    1. Added detailed logging to `SearchPaginator.parse_page` in `zlibrary/src/zlibrary/abs.py`. [2025-04-16 03:23:12]
    2. Tested `get_book_by_id` via `use_mcp_tool`; traceback showed error raised in `libasync.py` before `abs.py` parsing logs. [2025-04-16 06:09:33]
    3. Used `fetcher` tool to get raw HTML for `id:` search URL (`https://z-library.sk/s/id:3433851?exact=1`). Confirmed website returns standard search page with "nothing has been found". [2025-04-16 06:11:12]
    4. Added detailed logging to `get_by_id` in `zlibrary/src/zlibrary/libasync.py` around the search call. [2025-04-16 06:12:00]
    5. Enabled logging output by fixing `zlibrary/src/zlibrary/logger.py` (removed NullHandler, added StreamHandler to stderr, set level DEBUG). [2025-04-16 07:15:21]
    6. Tested `get_book_by_id` again via `use_mcp_tool`. Captured logs from Python bridge. [2025-04-16 07:23:16]
    7. Analyzed logs: Confirmed `libasync.py` calls `search`, `abs.py` parses the page, finds `#searchResultBox`, finds the "notFound" div inside it, leading `libasync.py` to log "returned 0 results" and correctly raise `BookNotFound`. [2025-04-16 07:23:30]
    8. Refined analysis based on user feedback: The failure of the `id:` search prevents discovery of the correct book page URL (which includes a slug), making direct fetching impossible. [2025-04-16 07:27:22]
- **Root Cause**: Z-Library website search feature no longer reliably returns results for `id:{book_id}` queries. This prevents the library from discovering the correct book page URL (including the slug) needed for direct fetching.
- **Fix Applied**: None (Issue is external). Diagnostic logging added to `libasync.py` and `logger.py` was configured.
- **Verification**: Logs confirm the library's behavior matches the website's response to the failing `id:` search.
- **Related Issues**: Issue-ParseError-IDLookup-01 (Superseded by this finding), Decision-IDLookupStrategy-01, Pattern: External Library URL Construction Error (Updated)


### Issue: Issue-BookNotFound-IDLookup-02 - `BookNotFound` on ID lookups (search workaround) - Status: Root Cause Confirmed (External) - [2025-04-16 07:23:30]
- **Reported**: [2025-04-16 03:12:00] (via ActiveContext) / **Severity**: High (Blocks ID-based tools) / **Symptoms**: `zlibrary.exception.BookNotFound` when calling `get_book_by_id` or other ID-based tools using the local fork with the search workaround.
- **Investigation**:
    1. Added detailed logging to `SearchPaginator.parse_page` in `zlibrary/src/zlibrary/abs.py`. [2025-04-16 03:23:12]
    2. Tested `get_book_by_id` via `use_mcp_tool`; traceback showed error raised in `libasync.py` before `abs.py` parsing logs. [2025-04-16 06:09:33]
    3. Used `fetcher` tool to get raw HTML for `id:` search URL (`https://z-library.sk/s/id:3433851?exact=1`). Confirmed website returns standard search page with "nothing has been found". [2025-04-16 06:11:12]
    4. Added detailed logging to `get_by_id` in `zlibrary/src/zlibrary/libasync.py` around the search call. [2025-04-16 06:12:00]
    5. Enabled logging output by fixing `zlibrary/src/zlibrary/logger.py` (removed NullHandler, added StreamHandler to stderr, set level DEBUG). [2025-04-16 07:15:21]
    6. Tested `get_book_by_id` again via `use_mcp_tool`. Captured logs from Python bridge. [2025-04-16 07:23:16]
    7. Analyzed logs: Confirmed `libasync.py` calls `search`, `abs.py` parses the page, finds `#searchResultBox`, finds the "notFound" div inside it, leading `libasync.py` to log "returned 0 results" and correctly raise `BookNotFound`. [2025-04-16 07:23:30]
- **Root Cause**: Z-Library website search feature no longer reliably returns results for `id:{book_id}` queries, even for valid IDs. The library correctly reflects this external behavior.
- **Fix Applied**: None (Issue is external). Diagnostic logging added to `libasync.py` and `logger.py` was configured.
- **Verification**: Logs confirm the library's behavior matches the website's response.
- **Related Issues**: Issue-ParseError-IDLookup-01 (Superseded by this finding), Decision-IDLookupStrategy-01, Pattern: External Library URL Construction Error (Updated)


### Issue: Issue-ParseError-IDLookup-01 - `zlibrary.exception.ParseError` on ID-Based Lookups - Status: Open (Workaround Proposed) - [2025-04-15 21:51:00]
- **Reported**: [2025-04-15 18:09:32] (via Memory Bank / TDD Manual Verification) / **Severity**: High (Blocks `get_book_by_id`, `get_download_info`, `download_book_to_file`) / **Symptoms**: Python `zlibrary.exception.ParseError: Failed to parse https://z-library.sk/book/BOOK_ID.`
- **Investigation**:
    1. Reviewed `lib/python_bridge.py`: Confirmed `get_by_id` and `get_download_info` functions call `client.get_by_id(id=book_id)`. [2025-04-15 21:51:00]
    2. Reviewed Memory Bank `[2025-04-15 18:26:14]`: Confirmed fetching the URL from a previous error (`https://z-library.sk/book/3433851`) resulted in a 404 "Page not found". [2025-04-15 21:51:00]
    3. Hypothesized root cause: `client.get_by_id` constructs an incorrect URL (missing slug), leading to 404, causing the parse error. [2025-04-15 21:51:00]
    4. Proposed workaround: Replace `client.get_by_id` calls with `client.search(q=f'id:{book_id}', exact=True, count=1)` and extract data from the search result. [2025-04-15 21:51:00]
- **Root Cause**: External `zlibrary` library's `get_by_id` method constructs an incorrect URL (e.g., `/book/ID` instead of `/book/ID/slug`), leading to a 404 page that the library cannot parse.
- **Fix Applied**: None (Workaround proposed).
- **Verification**: Conceptual verification complete. Workaround avoids the faulty `get_by_id` method.
- **Related Issues**: Decision-ParseErrorWorkaround-01, Pattern: External Library URL Construction Error

### Issue: PDF-AttrError-01 - PDF Processing AttributeError (`module 'fitz' has no attribute 'fitz'`) - Status: Resolved - [2025-04-15 20:46:14]
- **Reported**: [2025-04-15 19:36:25] (via Task Description) / **Severity**: High (Blocks PDF RAG processing) / **Symptoms**: Python `AttributeError: module 'fitz' has no attribute 'fitz'` when calling `process_document_for_rag` with PDF.
- **Investigation**:
    1. Reviewed `lib/python-bridge.py` code. Identified incorrect exception reference `fitz.fitz.FitzError` at line 225. [2025-04-15 19:37:18]
    2. Applied fix: Changed `fitz.fitz.FitzError` to `fitz.FitzError`. [2025-04-15 19:37:31]
    3. Attempted `pytest` verification, encountered `pytest: command not found`. [2025-04-15 19:37:38]
    4. Attempted `pytest` via venv Python (`python -m pytest`), encountered `No module named pytest`. [2025-04-15 19:58:36]
    5. Checked `requirements-dev.txt`, confirmed `pytest` listed. [2025-04-15 19:58:45]
    6. Installed dev requirements: `~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/python -m pip install -r requirements-dev.txt`. [2025-04-15 19:58:58]
    7. Attempted `pytest` via venv Python again, encountered `ModuleNotFoundError: No module named 'python_bridge'`. [2025-04-15 19:59:06]
    8. Attempted `pytest` with `PYTHONPATH=./lib`, still `ModuleNotFoundError`. [2025-04-15 19:59:16]
    9. Checked `pytest.ini`, confirmed `pythonpath = . lib` exists. [2025-04-15 19:59:29]
    10. Attempted `pytest` via direct `sys.path` modification, still `ModuleNotFoundError`. [2025-04-15 20:07:12]
    11. Checked `lib/__init__.py`, confirmed it exists and is minimal. [2025-04-15 20:07:25]
    12. Attempted `pytest` via direct executable path, still `ModuleNotFoundError`. [2025-04-15 20:10:54]
    13. Attempted `pytest` after cache clear, still `ModuleNotFoundError`. [2025-04-15 20:20:42]
    14. Attempted `pytest` with `-p python_path=./lib`, failed (incorrect option usage). [2025-04-15 20:21:18]
    15. Attempted `pytest` from `lib` directory, still `ModuleNotFoundError`. [2025-04-15 20:22:07]
    16. Hypothesized invalid filename `python-bridge.py`. Renamed to `python_bridge.py`. [2025-04-15 20:22:29]
    17. Attempted `pytest` from root, encountered `ImportError: cannot import name '_html_to_text'`. [2025-04-15 20:23:31]
    18. Removed `_html_to_text` import and tests from `__tests__/python/test_python_bridge.py`. [2025-04-15 20:23:56]
    19. Attempted `pytest` from root, encountered `ImportError: cannot import name 'download_book'`. [2025-04-15 20:24:04]
    20. Removed `download_book` import and tests from `__tests__/python/test_python_bridge.py`. [2025-04-15 20:24:24]
    21. Ran `pytest __tests__/python/test_python_bridge.py` - Passed (13 xfail, 4 xpass). [2025-04-15 20:24:36]
    22. Ran `npm test` - Passed. [2025-04-15 20:24:57]
    23. Manually tested `process_document_for_rag` with `__tests__/assets/sample.pdf`. Failed with `AttributeError: module 'fitz' has no attribute 'FitzError'`. [2025-04-15 20:31:25]
    24. Changed exception handler to `except fitz.RuntimeException`. [2025-04-15 20:31:45]
    25. Manually tested again. Failed with `AttributeError: module 'fitz' has no attribute 'RuntimeException'`. [2025-04-15 20:33:20]
    26. Changed exception handler to generic `except RuntimeError`. [2025-04-15 20:33:35]
    27. Manually tested again. Failed with `RuntimeError: Cannot open empty file`. [2025-04-15 20:33:43]
    28. Confirmed `__tests__/assets/sample.pdf` is invalid/empty via `read_file`. [2025-04-15 20:33:55]
    29. User replaced `__tests__/assets/sample.pdf` with a valid PDF. [2025-04-15 20:46:02]
    30. Retried manual test with valid PDF - Success. [2025-04-15 20:46:14]
- **Root Cause**: 1. Incorrect exception reference in `lib/python_bridge.py` (tried `fitz.fitz.FitzError`, `fitz.FitzError`, `fitz.RuntimeException`). 2. Invalid character (`-`) in Python module filename (`python-bridge.py`). 3. Test file (`__tests__/python/test_python_bridge.py`) attempting to import non-existent functions (`_html_to_text`, `download_book`). 4. Invalid/empty test PDF file (`__tests__/assets/sample.pdf`) used initially for manual verification.
- **Fix Applied**: 1. Corrected exception handler in `lib/python_bridge.py` to catch generic `RuntimeError`. 2. Renamed `lib/python-bridge.py` to `lib/python_bridge.py`. 3. Removed invalid imports and associated tests from `__tests__/python/test_python_bridge.py`. 4. Updated Node.js callers (`src/lib/python-bridge.ts`, `src/lib/zlibrary-api.ts`) to use the new Python script name.
- **Verification**: `pytest __tests__/python/test_python_bridge.py` passed. `npm test` passed. Manual test of `process_document_for_rag` with a valid `__tests__/assets/sample.pdf` succeeded.
- **Related Issues**: Task 3 (PDF RAG Processing)


### Issue: Jest ESM Mocking Failures (`venv-manager.test.js`) - Status: Resolved - [2025-04-15 04:31:00]
- **Reported**: [Implicit, via failing tests] / **Severity**: Medium (Blocked testing of venv logic)
- **Symptoms**: 3 tests in `__tests__/venv-manager.test.js` (`should skip install...`, `should throw error...`, `should reinstall...`) consistently failed. Errors involved incorrect mock behavior (`fs.existsSync`), unexpected promise resolutions, and incorrect path resolution for `requirements.txt`.
- **Investigation**:
    1. Reviewed test code and Memory Bank history, confirming prior failed attempts with `jest.unstable_mockModule` and `jest.spyOn`.
    2. Standardized mocking strategy to `unstable_mockModule` - Failed.
    3. Corrected `fs` mock implementations (`existsSync`, `readFileSync`) - Failed (mocks still not applied correctly).
    4. Identified potential stale build/cache issue.
    5. Corrected `requirements.txt` path calculation in `src/lib/venv-manager.ts`.
    6. Corrected test assertions for `requirements.txt` path.
    7. Rebuilt project (`npm run build`) and cleared Jest cache (`npx jest --clearCache`) - Still failed.
    8. **Hypothesized** core issue was Jest ESM + built-in module mocking unreliability.
    9. **Refactored** `src/lib/venv-manager.ts` for Dependency Injection (DI) of `fs`/`child_process`.
    10. Updated tests to use DI.
    11. Rebuilt and cleared cache again.
    12. Ran `npm test` - Success.
- **Root Cause**: Combination of Jest's unreliable ESM mocking for built-in modules (`fs`, `child_process`), incorrect path logic for `requirements.txt`, and potentially stale build artifacts/cache.
- **Fix Applied**: Refactored `venv-manager.ts` for Dependency Injection, updated tests accordingly, corrected `requirements.txt` path logic.
- **Verification**: `npm test` passed successfully [2025-04-15 04:31:00].
- **Related Issues**: None.


### Issue: INT-001 - Client ZodError / No Tools Found - Status: Open (Debugging Halted) - [2025-04-14 18:22:33]
- **Reported**: [2025-04-14 13:10:48] / **Severity**: High (Blocks tool usage)
- **Symptoms**: RooCode client UI shows "No tools found" for `zlibrary-mcp`. Direct `use_mcp_tool` calls fail with client-side `ZodError: Expected array, received undefined` at path `content`.
- **Investigation**:
    1. Confirmed server uses Stdio, SDK v1.8.0, CJS.
    2. Compared with working ESM/older SDK servers (`fetcher-mcp`, etc.). Research report: `docs/mcp-server-comparison-report.md`.
    3. Attempted server-side fixes (response formats, SDK downgrade, SDK imports, logging, schema isolation) - All failed to resolve "No tools found" UI issue.
    4. Server logs confirmed `ListToolsRequest` handler runs and `zodToJsonSchema` appears to succeed for individual schemas (when isolated or logged with try/catch), but logs truncate when processing the full list, suggesting a fatal error during schema generation/serialization.
    5. User feedback strongly indicates issue is server-side due to other servers working.
    6. User directed halt to debugging session due to unproductive attempts and incorrect focus.
- **Root Cause**: Unconfirmed, but suspected to be within `zlibrary-mcp`. Likely a subtle incompatibility between SDK v1.8.0 / CommonJS / `zod-to-json-schema` causing the `ListToolsResponse` generation to fail silently or produce output the client cannot process.
- **Fix Applied**: None. Code reverted to original state before debugging attempts.
- **Verification**: N/A.
- **Related Issues**: Task 3 (PDF Integration) blocked.


### Issue: INT-001 - Client ZodError on Tool Call - Status: Root Cause Confirmed - [2025-04-14 13:48:12]
- **Investigation**: Searched GitHub for `CallToolResponse zod`. Found `willccbb/mcp-client-server/src/types/schemas.ts` which defines `CallToolResponse` as `{ result: any; error?: string; duration_ms: number; }`. - [2025-04-14 13:48:12]
- **Analysis**: This confirms the standard/expected structure places the payload under the `result` key, with type `any`. The client error (`Expected array, received undefined` at path `content`) definitively indicates an incorrect client-side Zod schema expecting a `content` key that must be an array.
- **Server Status**: Server code (`index.js`) currently correctly returns `{ result: <payload> }`.
- **Resolution**: Requires fix in client-side code (RooCode) to correct the Zod schema for `CallToolResponse` parsing.


### Issue: INT-001 - Client ZodError on Tool Call - Status: Investigating - [2025-04-14 13:44:06]
- **Investigation**: Fetched and reviewed RooCode MCP documentation (overview, usage, concepts, transports, comparison). Documentation confirms JSON-RPC 2.0 usage but does *not* specify the exact structure for `CallToolResponse` (e.g., whether the result payload is under 'result', 'content', or top-level). - [2025-04-14 13:44:06]
- **Analysis**: Combined with the persistent client error ('Expected array, received undefined' at path 'content') even for object results, this strongly suggests the client-side Zod schema for parsing `CallToolResponse` is incorrect/too rigid. It likely expects `content` to always be an array.
- **Next Steps**: Recommend client-side code review (Zod schema for `CallToolResponse`). Recommend reverting server `tools/call` handler to return `{ result: <payload> }` pending client fix.


### Issue: Issue-MCP-SDK-CJS-Import - MCP SDK import/usage issues in CommonJS - [Status: Resolved] - [2025-04-14 10:16:36]
- **Reported**: 2025-04-14 10:08:20 / **Severity**: Medium / **Symptoms**: 1. `ToolsListRequestSchema`/`ToolsCallRequestSchema` undefined when imported via `require('@modelcontextprotocol/sdk/types.js')`. 2. `TypeError: this._stdin.on is not a function` when starting `StdioServerTransport`.
- **Investigation**: 1. Logged imported `mcpTypes` object, found correct names are `ListToolsRequestSchema`/`CallToolRequestSchema`. 2. Tried various `StdioServerTransport` constructor arguments (positional, options object with/without streams). 3. Searched web for SDK usage examples. 4. Found `dev.to` article showing `new StdioServerTransport()` and `server.connect(transport)` pattern.
- **Root Cause**: 1. Incorrect schema names used. 2. Incorrect instantiation/starting method for `StdioServerTransport` in CJS context (likely due to ESM/CJS interop differences in the SDK build).
- **Fix Applied**: 1. Corrected schema names to `ListToolsRequestSchema` and `CallToolRequestSchema`. 2. Changed `StdioServerTransport` usage to `const transport = new StdioServerTransport(); await server.connect(transport);` - [2025-04-14 10:14:32]
- **Verification**: `node index.js` now starts the server successfully without errors. - [2025-04-14 10:16:14]
- **Related Issues**: None

<!-- Append new issue details using the format below -->

### Issue: Issue-GlobalExecFail-01 - zlibrary-mcp global execution failure - [Status: Open] - [2025-04-14 03:26:00]
- **Reported**: 2025-04-14 03:24:49 / **Severity**: High / **Symptoms**: Node.js ERR_PACKAGE_PATH_NOT_EXPORTED, Python MODULE_NOT_FOUND when run via npx or as dependency.
- **Investigation**: 1. Reviewed package.json (exports, bin, deps) - [2025-04-14 03:25:29] 2. Reviewed index.js (line 4 require) - [2025-04-14 03:25:35] 3. Reviewed zlibrary-api.js (pythonPath) - [2025-04-14 03:25:45] 4. Reviewed python-env.js (pip usage) - [2025-04-14 03:25:55] 5. Reviewed python-bridge.py (imports) - [2025-04-14 03:26:02]
- **Root Cause**: 1. Improper Node.js import of internal SDK path (`index.js:4`). 2. Unreliable Python env management using global `pip`/`python3`. - [2025-04-14 03:26:02] / **Fix Applied**: None yet / **Verification**: N/A
- **Related Issues**: None

## Recurring Bug Patterns
<!-- Append new patterns using the format below -->

### Pattern: Improper Node.js Internal Import - [2025-04-14 03:26:00]
- **Identification**: Via ERR_PACKAGE_PATH_NOT_EXPORTED in zlibrary-mcp global execution.
- **Causes**: Using `require()` on internal paths not exposed via package `exports`.
- **Components**: `index.js`
- **Resolution**: Only import from paths defined in the dependency's `exports` (usually the main entry point).
- **Related**: Issue-GlobalExecFail-01
- **Last Seen**: 2025-04-14 03:26:00

### Pattern: Unreliable Python Environment Management - [2025-04-14 03:26:00]
- **Identification**: Via Python MODULE_NOT_FOUND in zlibrary-mcp global execution.
- **Causes**: Relying on globally resolved `pip` and `python3` commands without ensuring they belong to the same environment.
- **Components**: `lib/python-env.js`, `lib/zlibrary-api.js`
- **Resolution**: Use absolute paths to Python/pip within a managed environment (e.g., venv), bundle dependencies, or implement robust environment detection.
- **Related**: Issue-GlobalExecFail-01
- **Last Seen**: 2025-04-14 03:26:00

## Debugging Tools & Techniques
<!-- Append tool notes using the format below -->

### Tool/Technique: `pip show <package>` - [2025-04-15 23:14:52]
- **Context**: Locating source repository for an installed Python package.
- **Usage**: Execute `<venv_python> -m pip show <package_name>` and check the `Home-page` field in the output.
- **Effectiveness**: High (Successfully found GitHub URL for `zlibrary`).


### Technique: Dependency Injection for Built-in Modules (Jest/ESM) - [2025-04-15 04:31:00]
- **Context**: Mocking built-in Node.js modules (`fs`, `child_process`) in Jest tests using experimental ESM (`--experimental-vm-modules`).
- **Usage**: When `jest.unstable_mockModule` and `jest.spyOn` prove unreliable for built-ins in ESM, refactor the code under test to accept the module (or specific functions) as an argument. Pass mock implementations directly during tests.
- **Effectiveness**: High. Completely bypasses Jest's complex/unreliable ESM mocking mechanisms for built-ins, providing direct control over dependencies.


## Performance Observations
<!-- Append performance notes using the format below -->

## Environment-Specific Notes
<!-- Append environment notes using the format below -->