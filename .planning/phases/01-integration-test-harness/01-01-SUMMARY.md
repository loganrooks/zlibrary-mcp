# Phase 1 Plan 1: Integration Test Harness Summary

**One-liner:** 11-tool bridge integration tests with recorded/live modes and BRK-001 investigation

## Metrics
- **Duration:** ~3 minutes
- **Completed:** 2026-01-29
- **Tasks:** 2/2

## Commits

| Hash | Description |
|------|-------------|
| 6329100 | feat(01-01): integration test harness for all 11 MCP tools |
| b12c1a9 | feat(01-01): BRK-001 reproduction test and investigation |

## Key Files

### Created
- `__tests__/integration/bridge-tools.test.js` — 11-tool integration tests (recorded + live modes)
- `__tests__/integration/brk-001-reproduction.test.js` — BRK-001 investigation test
- `__tests__/integration/fixtures/recorded-responses/*.json` — 11 recorded response fixtures

### Modified
- `package.json` — Added test:integration and test:integration:live scripts
- `ISSUES.md` — Updated BRK-001 with investigation findings

## What Was Built

1. **Recorded-mode integration tests** for all 11 MCP tools via the Python bridge:
   - search_books, full_text_search, get_download_history, get_download_limits
   - download_book_to_file, process_document_for_rag, get_book_metadata
   - search_by_term, search_by_author, fetch_booklist, search_advanced
   - Each test mocks PythonShell (ESM-compatible via jest.unstable_mockModule)
   - Validates response shape and correct bridge function name
   - Summary table printed after all tests

2. **Live-mode support** via TEST_LIVE=true environment variable
   - Skips tools requiring real credentials/files (download, process, metadata, booklist)
   - 60s timeout for live tests vs 10s for recorded

3. **BRK-001 reproduction investigation**:
   - download_book() method exists in zlibrary fork (libasync.py:368)
   - process_document() exists in python_bridge.py
   - Node.js wrapper correctly passes process_for_rag=true
   - Error handling verified: AttributeError surfaces correctly
   - Status: Code path complete; cannot fully confirm without live credentials

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use jest.unstable_mockModule for ESM mocking | Required for ESM projects; jest.mock() doesn't work |
| Switch-based tool dispatch in tests | Clearer than dynamic function lookup for 11 tools with different signatures |
| BRK-001 marked "investigated, likely resolved" | Code path exists; needs live test for full confirmation |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] npm install and tsc build required**
- **Found during:** Task 1
- **Issue:** node_modules not installed, TypeScript not compiled
- **Fix:** Ran npm install and tsc build before running tests
- **Files modified:** none (build artifacts)

## Verification

- `npm run test:integration` — 11/11 recorded-mode tests pass
- `node --experimental-vm-modules node_modules/jest/bin/jest.js --testPathPattern brk-001` — 2/2 tests pass
