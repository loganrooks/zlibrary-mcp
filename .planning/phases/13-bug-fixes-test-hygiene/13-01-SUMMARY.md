---
phase: 13-bug-fixes-test-hygiene
plan: 01
subsystem: testing-infrastructure
tags: [jest, pytest, test-hygiene, bug-fix, CI]
requires:
  - phase: 12
    provides: "Completed v1.1 codebase with 13 MCP tools and UV-based Python management"
provides:
  - "Green Jest test suite (12 suites, 139 tests)"
  - "Correct pytest collection restricted to __tests__/python/"
  - "All 5 pytest markers registered for --strict-markers"
  - "Updated path helpers matching UV conventions (pyproject.toml, .venv)"
  - "Tool count assertions matching 13 registered tools"
  - "Fixed lint-staged pre-commit hook for TypeScript files"
affects: [CI, testing, developer-experience]
tech-stack:
  added: []
  patterns: ["lint-staged bash wrapper for tsc"]
key-files:
  created: []
  modified:
    - pytest.ini
    - src/lib/paths.ts
    - __tests__/paths.test.js
    - __tests__/integration/mcp-protocol.test.js
    - __tests__/e2e/docker-mcp-e2e.test.js
    - package.json
key-decisions:
  - "Replace getRequirementsTxtPath with getPyprojectTomlPath to match UV migration"
  - "Wrap lint-staged tsc in bash -c to prevent file argument pass-through"
patterns-established:
  - "lint-staged TypeScript: Use bash -c wrapper to prevent tsc receiving file args"
duration: 20min
completed: 2026-02-11
---

# Phase 13 Plan 01: Fix Test Failures Summary

**Fix 7 test failures across Jest and pytest: stale path assertions, missing tool counts, pytest collection errors, and unregistered markers**

## Performance
- **Duration:** 20 minutes
- **Tasks:** 2/2 completed
- **Files modified:** 6

## Accomplishments
- Fixed pytest collecting test-like scripts from scripts/ directory by adding `testpaths = __tests__/python`
- Registered `real_world` and `slow` markers for `--strict-markers` compliance (865 tests collected)
- Replaced `getRequirementsTxtPath()` with `getPyprojectTomlPath()` to match UV migration
- Updated `getVenvPath()` to return `.venv` instead of `venv` (UV convention)
- Removed nonexistent `client_manager.py` from paths test assertions
- Added `search_multi_source` to all 4 tool assertion arrays (EXPECTED_TOOLS, READ_ONLY_TOOLS, externalTools, idempotentTools)
- Updated tool count from 12 to 13 across mcp-protocol and docker e2e tests
- Fixed lint-staged pre-commit hook that failed when staging TypeScript files

## Task Commits
1. **Task 1: Fix pytest configuration (BUG-02 + BUG-03)** - `2b39f78`
2. **Task 2: Fix Jest test failures (BUG-01)** - `bd68945`

## Files Created/Modified
- `pytest.ini` - Added testpaths restriction and registered real_world/slow markers
- `src/lib/paths.ts` - Replaced getRequirementsTxtPath with getPyprojectTomlPath, updated getVenvPath to .venv
- `__tests__/paths.test.js` - Aligned imports and assertions with pyproject.toml and removed client_manager.py
- `__tests__/integration/mcp-protocol.test.js` - Added search_multi_source to all tool arrays, updated counts to 13
- `__tests__/e2e/docker-mcp-e2e.test.js` - Updated EXPECTED_TOOL_COUNT from 12 to 13
- `package.json` - Fixed lint-staged tsc invocation with bash -c wrapper

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Completeness] Added search_multi_source to externalTools and idempotentTools arrays**
- **Found during:** Task 2
- **Issue:** Plan only specified adding to EXPECTED_TOOLS and READ_ONLY_TOOLS, but the tool also has openWorldHint: true and idempotentHint: true annotations that are checked in separate test arrays
- **Fix:** Added search_multi_source to externalTools and idempotentTools arrays for complete annotation test coverage
- **Files modified:** __tests__/integration/mcp-protocol.test.js
- **Commit:** bd68945

**2. [Rule 3 - Blocking] Fixed lint-staged pre-commit hook breaking on TypeScript file commits**
- **Found during:** Task 2 (commit attempt)
- **Issue:** lint-staged config `"src/**/*.{ts,js}": "npm run build"` passes file paths as args to tsc, which causes tsc to ignore tsconfig.json and fail with "import.meta not allowed" error
- **Fix:** Changed to `"bash -c 'tsc --noEmit'"` which prevents argument pass-through and uses project tsconfig
- **Files modified:** package.json
- **Commit:** bd68945

## Verification Results
- `npm run build` - PASS (15/15 files validated)
- `npm test` - PASS (12 suites, 139 tests, 0 failures)
- `uv run pytest --strict-markers --collect-only` - PASS (865 tests collected, 0 errors)
- No scripts/ directory tests collected
- All 5 markers registered (integration, e2e, performance, real_world, slow)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
CI foundation is green. Both test runners pass. Ready for remaining v1.2 phases.

## Self-Check: PASSED
- All 6 modified files exist on disk
- Both task commits verified (2b39f78, bd68945)
- Summary file created at expected path
