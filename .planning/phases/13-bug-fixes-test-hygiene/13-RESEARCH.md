# Phase 13: Bug Fixes & Test Hygiene - Research

**Researched:** 2026-02-11
**Domain:** Test infrastructure repair (Jest + Pytest), dead code removal
**Confidence:** HIGH

## Summary

Phase 13 addresses five concrete, well-scoped bugs that prevent both test suites from running clean on master. Every bug has been directly reproduced and root-caused during this research. The fixes are mechanical: update stale assertions, add pytest configuration, and remove deprecated references.

The codebase has **7 distinct test failures** across the two test runners:
- **Jest**: 5 failures across 3 test suites (paths.test.js, mcp-protocol.test.js, docker-mcp-e2e.test.js)
- **Pytest**: 2 collection errors (scripts/ directory) + 2 unregistered marker warnings that become errors under `--strict-markers`

All failures stem from code evolution outpacing test updates: the UV migration removed `requirements.txt` and `client_manager.py`, a new `search_multi_source` tool was added without updating tool count assertions, and scripts in `scripts/` were never excluded from pytest collection.

**Primary recommendation:** Fix each bug independently in requirement order (BUG-01 through BUG-04), then validate BUG-05 as a final integration check. Total scope is small -- roughly 6-8 files need edits, zero architectural decisions required.

## Standard Stack

### Core (Already in Place)
| Library | Version | Purpose | Relevant to Phase |
|---------|---------|---------|-------------------|
| Jest | (via ts-jest ESM preset) | Node.js test runner | BUG-01 test assertion fixes |
| pytest | >=8.4.0 | Python test runner | BUG-02, BUG-03 configuration |
| pytest-asyncio | >=1.2.0 | Async test support | Already registered |
| UV | system | Python dependency manager | Context for BUG-01 (removed requirements.txt) |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `uv run pytest --strict-markers` | Validates all markers registered | BUG-03 verification |
| `npm test` | Runs all Jest suites | BUG-01, BUG-05 verification |
| `grep -rn "AsyncZlib"` | Finds remaining references | BUG-04 verification |

## Architecture Patterns

### Relevant Project Structure
```
__tests__/
  *.test.js              # Jest unit tests (import from dist/)
  integration/
    mcp-protocol.test.js # Tool count assertions (FAILING)
    brk-001-reproduction.test.js
    bridge-tools.test.js
  e2e/
    docker-mcp-e2e.test.js  # Tool count assertions (FAILING)
  python/
    conftest.py          # Adds project root to sys.path
    integration/
      test_real_zlibrary.py  # Has AsyncZlib refs (BUG-04)
    test_real_world_validation.py  # Uses unregistered 'real_world' marker
    test_recall_baseline.py       # Uses unregistered 'slow' marker
scripts/
  test_marginalia_detection.py    # Collected by pytest erroneously (BUG-02)
  archive/
    test_tesseract_comparison.py  # Collected by pytest erroneously (BUG-02)
pytest.ini               # Missing markers (BUG-03)
src/lib/paths.ts         # Has stale getRequirementsTxtPath, getVenvPath (BUG-01)
```

### Pattern: Test-Code Alignment
When production code evolves (UV migration, tool additions, API removal), corresponding tests must be updated atomically. This phase is paying down that debt.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pytest collection exclusion | Custom conftest.py hooks | `testpaths` or `--ignore` in pytest.ini | Standard pytest configuration |
| Marker registration | Runtime marker creation | `markers` list in pytest.ini | Official pytest pattern |

## Bug Analysis (Verified Against Live Codebase)

### BUG-01: Jest test failures in paths.test.js (2 tests)

**Root cause:** UV migration (v2.0.0) removed `requirements.txt` and renamed `venv/` to `.venv/`. The `paths.ts` module still exports `getRequirementsTxtPath()` and `getVenvPath()` which reference files/dirs that no longer exist.

**Failing tests:**
1. `getPythonScriptPath() > should handle different script names` -- asserts `client_manager.py` exists at line 75, but this file was removed during AsyncZlib cleanup (Phase 8). The test iterates over `['python_bridge.py', 'rag_processing.py', 'enhanced_metadata.py', 'client_manager.py']` and checks `existsSync()` for each.
2. `getRequirementsTxtPath() > should return path to requirements.txt` -- asserts `requirements.txt` exists, but UV migration replaced it with `pyproject.toml`.

**Fix approach:**
- Remove `client_manager.py` from the test's script list (it no longer exists)
- Either: (a) Remove `getRequirementsTxtPath()` from paths.ts and its test, OR (b) Update it to point to `pyproject.toml`
- Either: (a) Update `getVenvPath()` to return `.venv` instead of `venv`, OR (b) Remove if unused

**Additional Jest failures (discovered during research):**
3. `mcp-protocol.test.js` -- `EXPECTED_TOOLS` array has 12 entries but toolRegistry now has 13 (missing `search_multi_source`)
4. `mcp-protocol.test.js` -- `toolRegistry should be importable without starting server` expects 12 tools, gets 13
5. `docker-mcp-e2e.test.js` -- `EXPECTED_TOOL_COUNT = 12` but server exposes 13 tools

**The 13th tool is `search_multi_source`** (added in quick-001 tech debt cleanup but test assertions were not updated).

**Fix approach for tool count:** Update `EXPECTED_TOOLS` array to include `search_multi_source` and update count from 12 to 13.

### BUG-02: Pytest collection errors in scripts/ (2 errors)

**Root cause:** Pytest discovers files matching `test_*.py` pattern globally. Two files in `scripts/` match this pattern:
- `scripts/test_marginalia_detection.py` -- fails to import `analyze_page_layout` from `marginalia_extraction` (function was renamed to `analyze_document_layout_adaptive`)
- `scripts/archive/test_tesseract_comparison.py` -- fails to import `pytesseract` (not in project dependencies)

These are standalone utility scripts, not tests. They should never be collected by pytest.

**Fix approach:** Add `testpaths` directive to `pytest.ini` to restrict collection to `__tests__/python/` only:
```ini
testpaths = __tests__/python
```
This is the standard pytest pattern for controlling test discovery. Alternative: add `--ignore=scripts` but `testpaths` is cleaner since it explicitly declares where tests live.

### BUG-03: Unregistered pytest markers (2 markers)

**Root cause:** `pytest.ini` only registers `integration`, `e2e`, and `performance` markers. Two additional custom markers are used but not registered:
- `real_world` -- used in `__tests__/python/test_real_world_validation.py:285`
- `slow` -- used in `__tests__/python/test_recall_baseline.py:70,115`

**Markers inventory (complete):**

| Marker | Currently Registered | Used In | Action |
|--------|---------------------|---------|--------|
| `integration` | YES | test_real_zlibrary.py, test_pipeline_integration.py | None |
| `e2e` | YES | (declared) | None |
| `performance` | YES | (declared) | None |
| `real_world` | NO | test_real_world_validation.py | Register in pytest.ini |
| `slow` | NO | test_recall_baseline.py | Register in pytest.ini |
| `asyncio` | N/A | Many files | Handled by pytest-asyncio plugin |
| `parametrize` | N/A | Several files | Built-in pytest marker |
| `skip` / `skipif` | N/A | Several files | Built-in pytest markers |
| `xfail` | N/A | test_rag_processing.py | Built-in pytest marker |

**Fix approach:** Add `real_world` and `slow` to the `markers` list in `pytest.ini`:
```ini
markers =
    integration: marks tests as integration tests requiring real Z-Library credentials
    e2e: marks tests as end-to-end workflow tests
    performance: marks tests as performance/load tests
    real_world: marks tests requiring real-world test PDFs and ground truth data
    slow: marks tests that are slow to run (deselect with '-m "not slow"')
```

### BUG-04: Deprecated AsyncZlib references

**Root cause:** AsyncZlib was the legacy download client, removed from production code in Phase 8 (v1.1). However, references remain in several locations.

**Categorized references (from full codebase grep):**

**Category A -- Active source code (MUST fix):**
| File | Line | Context | Fix |
|------|------|---------|-----|
| `setup-uv.sh:59` | Import check | `from zlibrary import AsyncZlib` | Replace with EAPIClient or Extension import |
| `scripts/fix-cache-venv.sh:58` | Import check | Same pattern | Replace or remove (script may be dead) |
| `__tests__/venv-manager.test.js:45` | Validation test | `from zlibrary import AsyncZlib; print('OK')` | Replace with `from zlibrary import Extension; print('OK')` |
| `__tests__/integration/brk-001-reproduction.test.js:97` | Error string assertion | Expects error containing `AsyncZlib` | Update expected error message |
| `__tests__/python/integration/test_real_zlibrary.py:71,73,88,91,99,101` | Integration tests | Direct `AsyncZlib()` usage | Rewrite to use EAPIClient |

**Category B -- Documentation / planning / archive (ASSESS scope):**
- `.claude/PROJECT_CONTEXT.md`, `.claude/ARCHITECTURE.md`, `.claude/ROADMAP.md`, `.claude/DEBUGGING.md`
- `README.md` line 29
- `docs/` directory (multiple files)
- `.planning/` directory (multiple files)
- `claudedocs/` directory (archive)

**Category C -- Vendored library (DO NOT touch):**
- `zlibrary/src/zlibrary/__init__.py` -- This IS the library that exports `AsyncZlib`. It stays.
- `zlibrary/src/test.py` -- Tests for the vendored library. Leave as-is.
- `zlibrary/README.md` -- Vendored fork docs. Leave as-is.

**Scope decision for planner:** The success criterion states "Searching the codebase for `AsyncZlib` returns zero hits outside of git history." This needs clarification -- the vendored `zlibrary/` directory IS part of the codebase but AsyncZlib is its public API. The requirement likely means "zero hits in the project's own code" (i.e., `src/`, `lib/`, `__tests__/`, `scripts/`, setup scripts, and docs that describe the current architecture).

**Recommended interpretation:** Remove AsyncZlib from all project-owned code and docs. Leave `zlibrary/` vendored fork untouched (it exports AsyncZlib as its API -- that's correct). Update docs that describe the architecture to reflect EAPIClient-only downloads.

### BUG-05: Combined green verification

**This is a meta-requirement**, not a separate bug. It validates that BUG-01 through BUG-04 are all fixed simultaneously.

**Verification command:**
```bash
npm test && uv run pytest
```

**Additional verification for completeness:**
```bash
uv run pytest --strict-markers  # Validates BUG-03
grep -rn "AsyncZlib" --include="*.py" --include="*.ts" --include="*.js" --include="*.sh" --include="*.md" . | grep -v "zlibrary/" | grep -v "node_modules/" | grep -v ".planning/" | grep -v "claudedocs/" | grep -v "docs/archive/" | wc -l  # Should be 0
```

## Common Pitfalls

### Pitfall 1: Over-scoping AsyncZlib cleanup
**What goes wrong:** Attempting to modify vendored `zlibrary/` fork or spending excessive time on archived documentation.
**Why it happens:** The grep returns 250+ hits, creating pressure to fix everything.
**How to avoid:** Categorize references strictly (active code vs. docs vs. vendored). Only fix active code. Update live documentation (README, CLAUDE.md, .claude/ docs). Leave archives and planning history.
**Warning signs:** Editing files under `zlibrary/src/`, `claudedocs/archive/`, `.planning/phases/0[1-9]-*/`.

### Pitfall 2: Breaking the import check in setup-uv.sh
**What goes wrong:** Changing the import check in `setup-uv.sh` to a non-existent symbol.
**Why it happens:** `AsyncZlib` was the traditional "smoke test" import. Need a valid replacement.
**How to avoid:** The vendored zlibrary still exports `AsyncZlib` (it's the library's API). The import check `from zlibrary import AsyncZlib` actually STILL WORKS. The question is whether to keep testing this import or switch to something like `from zlibrary import Extension, Language`. Since the project no longer uses `AsyncZlib` directly, switch to testing imports the project actually uses: `from lib.eapi_client import EAPIClient` or `from zlibrary import Extension`.
**Warning signs:** `setup-uv.sh` failing after edit.

### Pitfall 3: Forgetting to rebuild before running Jest tests
**What goes wrong:** Editing `src/lib/paths.ts` but running Jest against stale `dist/lib/paths.js`.
**Why it happens:** Jest imports from `dist/`, not `src/`. Must run `npm run build` after TypeScript changes.
**How to avoid:** Always `npm run build && npm test` after any `.ts` file changes.

### Pitfall 4: Not updating the brk-001-reproduction test
**What goes wrong:** The brk-001 test asserts a specific error string containing "AsyncZlib". If the vendored library still uses AsyncZlib internally, this error message might still be correct at runtime.
**How to avoid:** Check whether the error message in brk-001 comes from the vendored library (acceptable) or from project code (needs update). The test at `__tests__/integration/brk-001-reproduction.test.js:97` tests a known bug reproduction -- the error comes from the vendored zlibrary. This reference may be acceptable since it's testing the library's actual error output.

### Pitfall 5: pytest testpaths breaking CI
**What goes wrong:** Adding `testpaths = __tests__/python` might miss tests in other locations.
**Why it happens:** If any legitimate tests exist outside `__tests__/python/`.
**How to avoid:** Verify all Python test files are under `__tests__/python/`. The only `test_*.py` files outside this directory are in `scripts/` and they are utility scripts, not tests.

## Code Examples

### Fix 1: pytest.ini (BUG-02 + BUG-03)
```ini
# Source: pytest official docs - https://docs.pytest.org/en/stable/reference/reference.html#ini-options-ref
[pytest]
pythonpath = . lib
asyncio_mode = auto
testpaths = __tests__/python
markers =
    integration: marks tests as integration tests requiring real Z-Library credentials (deselect with '-m "not integration"')
    e2e: marks tests as end-to-end workflow tests (deselect with '-m "not e2e"')
    performance: marks tests as performance/load tests (deselect with '-m "not performance"')
    real_world: marks tests requiring real-world test PDFs and ground truth data (deselect with '-m "not real_world"')
    slow: marks tests that are slow to run (deselect with '-m "not slow"')
```

### Fix 2: paths.test.js script list (BUG-01)
```javascript
// Before (line 71-76):
const scripts = [
  'python_bridge.py',
  'rag_processing.py',
  'enhanced_metadata.py',
  'client_manager.py'  // REMOVED -- no longer exists
];

// After:
const scripts = [
  'python_bridge.py',
  'rag_processing.py',
  'enhanced_metadata.py'
];
```

### Fix 3: paths.ts -- remove or update stale helpers (BUG-01)
```typescript
// Option A: Remove getRequirementsTxtPath entirely (requirements.txt no longer exists)
// Option B: Replace with getPyprojectTomlPath()
export function getPyprojectTomlPath(): string {
  return path.join(getProjectRoot(), 'pyproject.toml');
}

// Update getVenvPath to match UV convention (.venv not venv)
export function getVenvPath(): string {
  return path.join(getProjectRoot(), '.venv');
}
```

### Fix 4: Tool count assertions (BUG-01 extended)
```javascript
// mcp-protocol.test.js - add missing tool
const EXPECTED_TOOLS = [
  'search_books',
  'full_text_search',
  'get_download_history',
  'get_download_limits',
  'get_recent_books',
  'download_book_to_file',
  'process_document_for_rag',
  'get_book_metadata',
  'search_by_term',
  'search_by_author',
  'fetch_booklist',
  'search_advanced',
  'search_multi_source'  // Added in quick-001 tech debt cleanup
];

// docker-mcp-e2e.test.js
const EXPECTED_TOOL_COUNT = 13;  // Was 12
```

### Fix 5: AsyncZlib import check replacement (BUG-04)
```bash
# setup-uv.sh line 59 -- replace AsyncZlib import check
# Before:
if .venv/bin/python -c "from zlibrary import AsyncZlib, Extension, Language; print('zlibrary ready')" 2>&1; then

# After:
if .venv/bin/python -c "from zlibrary import Extension, Language; print('zlibrary ready')" 2>&1; then
```

### Fix 6: venv-manager.test.js AsyncZlib reference (BUG-04)
```javascript
// Before (line 45):
`"${pythonPath}" -c "from zlibrary import AsyncZlib; print('OK')"`,

// After:
`"${pythonPath}" -c "from zlibrary import Extension; print('OK')"`,
```

## Files Requiring Changes (Complete List)

| File | Bug | Change |
|------|-----|--------|
| `pytest.ini` | BUG-02, BUG-03 | Add `testpaths`, register `real_world` + `slow` markers |
| `__tests__/paths.test.js` | BUG-01 | Remove `client_manager.py` from list, update/remove requirements.txt test |
| `src/lib/paths.ts` | BUG-01 | Remove/update `getRequirementsTxtPath()`, update `getVenvPath()` |
| `dist/lib/paths.js` | BUG-01 | Rebuilt from paths.ts via `npm run build` |
| `__tests__/integration/mcp-protocol.test.js` | BUG-01 | Add `search_multi_source` to EXPECTED_TOOLS, update count |
| `__tests__/e2e/docker-mcp-e2e.test.js` | BUG-01 | Update EXPECTED_TOOL_COUNT to 13 |
| `setup-uv.sh` | BUG-04 | Replace AsyncZlib import with Extension |
| `scripts/fix-cache-venv.sh` | BUG-04 | Replace AsyncZlib import (or remove script if dead) |
| `__tests__/venv-manager.test.js` | BUG-04 | Replace AsyncZlib import check |
| `__tests__/integration/brk-001-reproduction.test.js` | BUG-04 | Assess: error comes from vendored lib, may be acceptable |
| `__tests__/python/integration/test_real_zlibrary.py` | BUG-04 | Rewrite to use EAPIClient instead of AsyncZlib |
| `README.md` | BUG-04 | Update architecture description |
| `.claude/ARCHITECTURE.md` | BUG-04 | Update to reflect EAPIClient-only downloads |
| `.claude/PROJECT_CONTEXT.md` | BUG-04 | Remove AsyncZlib references |
| `.claude/ROADMAP.md` | BUG-04 | Update download architecture description |
| `.claude/DEBUGGING.md` | BUG-04 | Update debugging examples |
| `CLAUDE.md` | BUG-04 | Minor if any -- check for AsyncZlib mentions |
| `docs/TROUBLESHOOTING.md` | BUG-04 | Update troubleshooting examples |
| `docs/MIGRATION_V2.md` | BUG-04 | Update migration docs |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requirements.txt` + `pip` | `pyproject.toml` + `uv sync` | v2.0.0 UV migration | `getRequirementsTxtPath()` broken |
| `venv/` directory | `.venv/` directory | v2.0.0 UV migration | `getVenvPath()` returns wrong path |
| AsyncZlib for downloads | EAPIClient.download_file | v1.1 Phase 8 | References lingering |
| 12 MCP tools | 13 MCP tools | quick-001 (added search_multi_source) | Tool count assertions stale |

## Open Questions

1. **AsyncZlib in brk-001-reproduction.test.js**
   - What we know: The test asserts an error string containing "AsyncZlib" that comes from the vendored library's runtime error
   - What's unclear: Whether removing this reference counts as "removing AsyncZlib from codebase" per BUG-04
   - Recommendation: Leave it -- it's testing the vendored library's actual error output. The error string comes from Python runtime, not from project code.

2. **Scope of documentation updates for BUG-04**
   - What we know: AsyncZlib appears in ~30 documentation files
   - What's unclear: Whether archived docs (claudedocs/archive/, .planning/phases/01-12/) should be updated
   - Recommendation: Only update living documentation (.claude/, README.md, docs/ non-archive). Leave historical records intact.

3. **Whether `scripts/fix-cache-venv.sh` is still needed**
   - What we know: UV migration eliminated the cache venv approach
   - What's unclear: Whether anyone still uses this script
   - Recommendation: Delete it -- it references the old cache-based venv system that UV replaced. This could also be deferred to Phase 15 (Repo Cleanup, CLEAN-01).

## Sources

### Primary (HIGH confidence)
- Live codebase analysis: `npm test` output (5 failures, 3 suites)
- Live codebase analysis: `uv run pytest` output (2 collection errors, 2 marker warnings)
- Live codebase analysis: `uv run pytest --strict-markers` output (4 errors)
- Live codebase analysis: `grep -rn AsyncZlib` (250+ hits categorized)
- File inspection: `pytest.ini`, `paths.ts`, `paths.test.js`, `mcp-protocol.test.js`, `docker-mcp-e2e.test.js`
- File inspection: `pyproject.toml` (confirms no requirements.txt)
- Runtime check: `toolRegistry` has 13 tools (search_multi_source is the 13th)

### Secondary (MEDIUM confidence)
- pytest documentation: `testpaths` and `markers` configuration
- UV documentation: `.venv` convention

## Metadata

**Confidence breakdown:**
- Bug root causes: HIGH -- all bugs directly reproduced and root-caused from live test output
- Fix approaches: HIGH -- standard configuration changes, well-understood patterns
- File change list: HIGH -- derived from direct codebase inspection
- AsyncZlib scope: MEDIUM -- the boundary between "project code" and "vendored library" needs planner judgment

**Research date:** 2026-02-11
**Valid until:** Indefinite (bugs are snapshot of current state, not version-dependent)
