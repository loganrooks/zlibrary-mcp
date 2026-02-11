---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - __tests__/python/integration/conftest.py
  - lib/booklist_tools.py
autonomous: true

must_haves:
  truths:
    - "uv run pytest __tests__/python/integration/test_real_zlibrary.py --collect-only succeeds with 0 errors (all 18 tests collected)"
    - "zlib_client fixture is resolvable by every test that requests it"
    - "booklist_tools.py discover_eapi_domain() call passes required eapi_client argument"
  artifacts:
    - path: "__tests__/python/integration/conftest.py"
      provides: "zlib_client fixture definition"
      contains: "async def zlib_client"
  key_links:
    - from: "__tests__/python/integration/conftest.py"
      to: "zlibrary/src/zlibrary/eapi.py"
      via: "imports EAPIClient, calls login()"
      pattern: "from zlibrary\\.eapi import EAPIClient"
---

<objective>
Fix the missing `zlib_client` pytest fixture that causes 18 integration test errors in
`__tests__/python/integration/test_real_zlibrary.py`, and fix the pre-existing
`discover_eapi_domain()` missing-argument bug in `booklist_tools.py`.

Purpose: Restore fixture resolution so integration tests can be collected and run.
Output: New `__tests__/python/integration/conftest.py` with the fixture; patched `booklist_tools.py`.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary-standard.md
</execution_context>

<context>
@__tests__/python/integration/test_real_zlibrary.py
@lib/python_bridge.py (lines 191-260: get_eapi_client / initialize_eapi_client)
@zlibrary/src/zlibrary/eapi.py (lines 23-100: EAPIClient class, login method)
@lib/booklist_tools.py (lines 57-65: discover_eapi_domain call site)
@zlibrary/src/zlibrary/util.py (line 116: discover_eapi_domain signature requires eapi_client)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create zlib_client fixture in integration conftest.py</name>
  <files>__tests__/python/integration/conftest.py</files>
  <action>
Create a new file `__tests__/python/integration/conftest.py` with a module-scoped async
fixture named `zlib_client`.

The fixture must:

1. Import `os` and `EAPIClient` from `zlibrary.eapi`.
2. Read `ZLIBRARY_EMAIL`, `ZLIBRARY_PASSWORD`, and optionally `ZLIBRARY_EAPI_DOMAIN`
   (default `"z-library.sk"`) from environment variables.
3. Instantiate `EAPIClient(domain)`.
4. Call `await client.login(email, password)` and assert `login_result.get("success") == 1`.
5. Yield `client`.
6. In teardown, call `await client.close()`.

Use `@pytest.fixture(scope="module")` and mark it `@pytest.mark.asyncio` (or use
`async def` — pytest-asyncio handles async fixtures automatically).

IMPORTANT: The `client=` parameter in `python_bridge.search()` is documented as "Unused
(kept for backward compatibility)" — it is never actually used. The fixture's real purpose
is to serve as a pre-authenticated client that test methods receive, even though
`python_bridge.search` internally calls `get_eapi_client()`. Some tests (like
TestRealAuthentication) do NOT use `zlib_client` — they manage their own client. The fixture
only needs to exist so pytest can resolve it for the 18 test methods that declare it in
their signature.

Also add a `sys.path` insert for the `lib/` directory (same pattern used in the test file
itself at line 27) so that imports like `from zlibrary.eapi import EAPIClient` resolve
correctly when conftest is loaded.

Do NOT modify `test_real_zlibrary.py` itself.
  </action>
  <verify>
Run: `uv run pytest __tests__/python/integration/test_real_zlibrary.py --collect-only 2>&1`

Success: All tests collected with 0 errors. Specifically look for "18 tests collected"
(or the full count) and NO lines containing "fixture 'zlib_client' not found".
  </verify>
  <done>
`uv run pytest --collect-only` on the integration test file reports 0 errors and all
test items are collected. The `zlib_client` fixture resolves for every test that requests it.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix discover_eapi_domain missing argument in booklist_tools.py</name>
  <files>lib/booklist_tools.py</files>
  <action>
In `lib/booklist_tools.py` around line 62, the code calls:

```python
domain = await discover_eapi_domain()
```

But `discover_eapi_domain` (in `zlibrary/src/zlibrary/util.py:116`) requires an
`eapi_client` positional argument. This is a chicken-and-egg problem: the function
needs a client to discover a domain, but you need a domain to create a client.

Fix by replacing lines 61-64 with a simpler approach that mirrors
`initialize_eapi_client()` in `python_bridge.py` (lines 232-234):

```python
domain = os.environ.get("ZLIBRARY_EAPI_DOMAIN", "z-library.sk")
client = EAPIClient(domain)
await client.login(email, password)
should_close = True
```

Remove the `from zlibrary.util import discover_eapi_domain` import (line 61) since it is
no longer needed. Make sure `os` is imported at the top of the file (it likely already is;
verify before adding).

This matches the proven pattern from `python_bridge.py:initialize_eapi_client()` which
uses a known initial domain and discovers optimal domains post-login.
  </action>
  <verify>
Run: `uv run python -c "import lib.booklist_tools; print('import OK')"`

This confirms the module loads without syntax errors. The function itself requires
credentials at runtime, so a full functional test is not feasible without live API access.
  </verify>
  <done>
`booklist_tools.py` no longer calls `discover_eapi_domain()` without arguments. The
fallback client creation uses a known domain from environment, matching the pattern in
`python_bridge.py`.
  </done>
</task>

</tasks>

<verification>
1. `uv run pytest __tests__/python/integration/test_real_zlibrary.py --collect-only` — 0 errors, all tests collected
2. `uv run python -c "import lib.booklist_tools"` — no import errors
3. No modifications to `test_real_zlibrary.py` itself
</verification>

<success_criteria>
- All 18 integration tests in test_real_zlibrary.py are collectible (fixture resolution works)
- booklist_tools.py has no discover_eapi_domain() missing-arg bug
- No other test files are broken by these changes
</success_criteria>

<output>
After completion, create `.planning/quick/003-fix-zlib-client-fixture/003-SUMMARY.md`
</output>
