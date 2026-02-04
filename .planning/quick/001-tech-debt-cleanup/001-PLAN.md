---
phase: quick
plan: 001
type: execute
wave: 1
depends_on: []
files_modified:
  - src/index.ts
  - src/lib/zlibrary-api.ts
  - lib/client_manager.py
  - lib/advanced_search.py
  - __tests__/python/test_client_manager.py
  - __tests__/python/test_advanced_search.py
  - __tests__/python/integration/test_real_zlibrary.py
autonomous: true

must_haves:
  truths:
    - "search_multi_source MCP tool is callable and returns book results"
    - "Deprecated AsyncZlib code is removed from codebase"
    - "All tests pass after removal"
  artifacts:
    - path: "src/index.ts"
      provides: "search_multi_source tool registration"
      contains: "search_multi_source"
    - path: "src/lib/zlibrary-api.ts"
      provides: "searchMultiSource bridge function"
      exports: ["searchMultiSource"]
  key_links:
    - from: "src/index.ts"
      to: "src/lib/zlibrary-api.ts"
      via: "handler calls searchMultiSource"
      pattern: "zlibraryApi\\.searchMultiSource"
    - from: "src/lib/zlibrary-api.ts"
      to: "lib/python_bridge.py"
      via: "callPythonFunction('search_multi_source')"
      pattern: "search_multi_source"
---

<objective>
Wire search_multi_source as MCP tool AND remove deprecated AsyncZlib code.

Purpose: Tech debt cleanup - expose Phase 12 Anna's Archive/LibGen integration as MCP tool, remove dead code that was deprecated in Phase 08.
Output: New search_multi_source tool available to MCP clients, cleaner codebase without deprecated AsyncZlib wrappers.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@src/index.ts
@src/lib/zlibrary-api.ts
@lib/python_bridge.py (lines 882-934 for search_multi_source)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire search_multi_source MCP tool</name>
  <files>src/lib/zlibrary-api.ts, src/index.ts</files>
  <action>
1. In src/lib/zlibrary-api.ts, add searchMultiSource function:
   - Interface: SearchMultiSourceArgs { query: string; source?: 'auto' | 'annas' | 'libgen'; count?: number }
   - Function calls callPythonFunction('search_multi_source', {...})
   - Returns { books: BookResult[]; sources_used: string[] }

2. In src/index.ts:
   - Add SearchMultiSourceParamsSchema (Zod schema) with:
     - query: z.string().describe('Search query')
     - source: z.enum(['auto', 'annas', 'libgen']).optional().default('auto').describe('Source selection')
     - count: z.number().int().optional().default(10).describe('Max results')
   - Add handler searchMultiSource in handlers object
   - Add toolAnnotations entry (readOnlyHint: true, idempotentHint: true, openWorldHint: true)
   - Add toolRegistry entry
   - Register tool #13 via server.tool() with description: 'Search for books across Anna\'s Archive and LibGen. Alternative to Z-Library EAPI. Returns books with md5, title, author, year, extension, size, source, download_url.'
  </action>
  <verify>
    - `npm run build` succeeds without errors
    - Tool appears in toolRegistry with 13 entries
  </verify>
  <done>search_multi_source tool registered and callable through MCP protocol</done>
</task>

<task type="auto">
  <name>Task 2: Remove deprecated AsyncZlib code</name>
  <files>lib/client_manager.py, lib/advanced_search.py, __tests__/python/test_client_manager.py, __tests__/python/test_advanced_search.py, __tests__/python/integration/test_real_zlibrary.py</files>
  <action>
1. Delete deprecated Python modules:
   - rm lib/client_manager.py
   - rm lib/advanced_search.py

2. Delete associated test files:
   - rm __tests__/python/test_client_manager.py
   - rm __tests__/python/test_advanced_search.py

3. Update integration test file:
   - In __tests__/python/integration/test_real_zlibrary.py:
     - Remove imports: `from lib.client_manager import ZLibraryClient` (line 76)
     - Remove imports: `from lib import client_manager` (line 97-100)
     - Remove test methods: test_advanced_search_detects_fuzzy (lines 477-495)
     - Remove test methods: test_advanced_search_no_fuzzy (lines 497+)
     - Remove any client_manager.reset_default_client() calls in fixtures
  </action>
  <verify>
    - Files no longer exist: `ls lib/client_manager.py lib/advanced_search.py` returns "No such file"
    - Test files removed: `ls __tests__/python/test_client_manager.py __tests__/python/test_advanced_search.py` returns "No such file"
    - No import errors: `uv run python -c "import lib.python_bridge"` succeeds
  </verify>
  <done>All deprecated AsyncZlib code and tests removed from codebase</done>
</task>

<task type="auto">
  <name>Task 3: Verify all tests pass</name>
  <files>-</files>
  <action>
Run the full test suite to confirm nothing is broken:
1. Run Python tests: `uv run pytest --ignore=__tests__/python/integration/`
2. Run TypeScript build: `npm run build`
3. Verify no imports fail at runtime

Note: Integration tests require credentials and network, skip those. Unit tests must all pass.
  </action>
  <verify>
    - `uv run pytest --ignore=__tests__/python/integration/ -v` passes
    - `npm run build` succeeds
  </verify>
  <done>All unit tests pass, build succeeds, tech debt cleanup complete</done>
</task>

</tasks>

<verification>
1. Build verification: `npm run build` completes without errors
2. Python import test: `uv run python -c "from lib.python_bridge import search_multi_source; print('OK')"`
3. Test suite: `uv run pytest --ignore=__tests__/python/integration/` passes
4. File cleanup confirmed: deprecated files no longer exist
</verification>

<success_criteria>
- search_multi_source tool registered in MCP server (tool #13)
- TypeScript API wrapper exports searchMultiSource function
- lib/client_manager.py and lib/advanced_search.py deleted
- Associated test files deleted
- Integration tests updated (advanced_search tests removed)
- All remaining tests pass
- Build succeeds
</success_criteria>

<output>
After completion, create `.planning/quick/001-tech-debt-cleanup/001-SUMMARY.md`
</output>
