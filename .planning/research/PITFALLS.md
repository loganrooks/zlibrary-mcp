# Pitfalls Research

**Domain:** Production readiness for dual-language (TypeScript + Python) MCP server with npm publishing
**Researched:** 2026-02-11
**Confidence:** HIGH (grounded in direct codebase inspection + community evidence)

## Critical Pitfalls

### Pitfall 1: 44 MB npm Tarball Ships Test PDFs, Planning Artifacts, and Debug Scripts

**What goes wrong:**
The current `.npmignore` is a minimal 15-line blacklist. Running `npm pack --dry-run` reveals a **44.4 MB tarball with 1,017 files**. This includes:
- 43 PDF/EPUB files (22 MB Derrida PDF alone) in `test_files/`
- All 354 files from `.claude/`, `claudedocs/`, `.planning/` directories
- 10 root-level debug scripts (`debug_asterisk_full_search.py`, `test_footnote_validation.py`, etc.)
- Complete `__tests__/` directory with Python test fixtures
- `scripts/` with development validation and debugging tools
- `BUG_5_OPTIMIZATION_PLAN.md`, `CONTINUATION_INTEGRATION_SUMMARY.md`, and other internal docs
- `.serena/` directory, `.benchmarks/`, `dummy_output/`, `MagicMock/`
- `performance_baseline.json`, `footnote_validation_results.json`
- Multiple ground truth JSON files with schema versions

A published MCP server package should be under 5 MB. This is 9x over a reasonable limit.

**Why it happens:**
The `.npmignore` was written during early development and uses a blacklist approach. As the project grew from a simple MCP server to ~44K LOC with extensive test infrastructure, research docs, and AI-assistant planning files, the blacklist was never updated. The `.gitignore` excludes build artifacts but not development files (which are tracked in git but should not be published).

**How to avoid:**
Switch from `.npmignore` (blacklist) to `package.json` `"files"` field (whitelist). This is the npm-recommended approach for complex projects. A correct whitelist:
```json
{
  "files": [
    "dist/",
    "lib/",
    "zlibrary/",
    "pyproject.toml",
    "uv.lock",
    "setup-uv.sh",
    "LICENSE",
    "README.md"
  ]
}
```
Verify with `npm pack --dry-run` before every publish. Add a CI step that fails if tarball exceeds 10 MB.

**Warning signs:**
- `npm pack --dry-run | tail -5` shows file count > 50 or size > 10 MB
- Published package includes directories not needed at runtime

**Phase to address:**
npm publishing phase (should be one of the last phases, after cleanup is complete). But the `"files"` field decision must be made BEFORE repo cleanup starts, because cleanup determines what exists to be published.

---

### Pitfall 2: Conflicting Entry Points -- Legacy CJS index.js vs ESM dist/index.js

**What goes wrong:**
The project currently has THREE `index.js` files:
1. **Root `index.js`** (16 KB) -- Legacy CommonJS using `require()` and `zod-to-json-schema`
2. **`dist/index.js`** (43 KB) -- Compiled TypeScript ESM output
3. **`src/index.js`** (6 KB) -- Another compiled artifact in source

The `package.json` is contradictory:
- `"main": "index.js"` -- points to legacy CJS root file
- `"exports": { ".": "./dist/index.js" }` -- points to compiled ESM
- `"bin": { "zlibrary-mcp": "./dist/index.js" }` -- points to compiled ESM
- `"type": "module"` -- declares ESM

When npm resolves modules, the `exports` field takes precedence over `main` for modern Node.js (>=12.11.0), but tools and environments that do not support exports maps fall back to `main`. This means:
- `npx zlibrary-mcp` uses `dist/index.js` (correct)
- `require('zlibrary-mcp')` may resolve to root `index.js` (broken CJS)
- Some MCP clients may use `main` field to launch the server

Deleting the wrong `index.js` or updating `main` without testing all consumer paths will break installations.

**Why it happens:**
The project started as CJS, migrated to ESM TypeScript. The root `index.js` was the original entry point and was never removed. `src/index.js` appears to be a leftover compilation artifact (`.gitignore` excludes `*.js` in tests but not in `src/`).

**How to avoid:**
1. Remove root `index.js` (legacy CJS) and `src/index.js` (stale artifact)
2. Update `package.json`: set `"main": "dist/index.js"` to match `exports`
3. Verify `dist/index.js` has the shebang `#!/usr/bin/env node` for bin usage
4. Test with `npx .` after changes to confirm the binary still works
5. Test with `node -e "import('zlibrary-mcp')"` to verify module resolution

**Warning signs:**
- `ls *.js` in project root shows non-config JavaScript files
- `main` and `exports` in package.json point to different files
- MCP client fails to start server after install

**Phase to address:**
Repo cleanup phase. This must be fixed BEFORE npm publishing phase.

---

### Pitfall 3: Test Reorganization Breaks CI in Three Independent Ways

**What goes wrong:**
Moving or renaming test files triggers three distinct failure modes simultaneously:

**a) Jest moduleNameMapper paths break:**
The jest.config.js has hardcoded path mappings:
```javascript
moduleNameMapper: {
  '^../lib/(.*)\\.js$': '<rootDir>/dist/lib/$1.js',
  '^../(dist/)?index\\.js$': '<rootDir>/dist/index.js',
}
```
If tests move from `__tests__/` to `__tests__/unit/` or `tests/`, these relative path patterns (`^../lib/`) stop matching. Every import in every moved test silently resolves to the wrong file or fails.

**b) Pytest pythonpath breaks:**
The `pytest.ini` sets `pythonpath = . lib`. If Python tests move directories, the relative path from the test to `lib/` changes. Additionally, `conftest.py` in `__tests__/python/` provides fixtures -- moving tests without moving conftest breaks fixture resolution.

**c) CI workflow hardcodes paths:**
The GitHub Actions `ci.yml` runs bare `uv run pytest` which uses `pytest.ini` for discovery. If test directory names change, pytest must be reconfigured, or collection errors multiply. Currently 2 collection errors already exist (`scripts/archive/test_tesseract_comparison.py` and `scripts/test_marginalia_detection.py` are collected by pytest despite not being in the test directory).

All three break independently. Fixing one does not fix the others. If tests are moved in a single commit without updating all three configurations, CI goes red and stays red across multiple fix attempts.

**Why it happens:**
Dual test framework projects have configuration scattered across `jest.config.js`, `pytest.ini`, `tsconfig.json`, and `.github/workflows/ci.yml`. Each uses different path resolution logic. Developers fix one and commit, then discover the next breakage in CI.

**How to avoid:**
1. Create a branch specifically for test reorganization -- do NOT mix with feature work
2. Update all four config files (jest.config.js, pytest.ini, tsconfig.json exclude, ci.yml) in the SAME commit
3. Run `npm test` (Jest) AND `uv run pytest` locally before pushing
4. Fix the existing 2 pytest collection errors FIRST (add `testpaths` to `pytest.ini` or move/delete the offending scripts)
5. If renaming `__tests__/` to `tests/`, update `.gitignore` entries that reference `__tests__/`

**Warning signs:**
- CI passes Jest but fails pytest (or vice versa)
- `uv run pytest --co -q` shows collection errors
- Tests pass locally but fail in CI (different working directory)

**Phase to address:**
Test infrastructure phase -- must be the FIRST phase. Everything else depends on green CI.

---

### Pitfall 4: Breaking RAG Output Format Without Consumer Migration Path

**What goes wrong:**
The current RAG pipeline outputs two files per processed document:
- `{filename}.processed.markdown` (body text)
- `{filename}.metadata.json` (metadata)

If v1.2 introduces structured output (e.g., splitting body.md into sections, adding quality scores to metadata, renaming files to `body.md` + `_meta.json`), any MCP client that reads the old format breaks silently. The MCP tool `process_document_for_rag` returns file paths in its response -- if those path patterns change, clients that parse the response break too.

Worse: the Python bridge returns results as JSON through stdout. If the JSON schema changes (adding fields is safe, removing/renaming is breaking), the TypeScript layer that parses it via PythonShell may throw on unexpected structure.

**Why it happens:**
Internal refactoring of output format feels like "just improving code" rather than an API change. But MCP tool responses ARE the API surface. Any change to the content or path pattern of returned files is a breaking change for consumers.

**How to avoid:**
1. Document the current output format as v1 contract BEFORE changing anything
2. When adding quality scores or structured output, ADD new fields/files -- do not remove or rename existing ones
3. If the output directory structure must change, implement version detection: check for old format, emit deprecation warning, support both for one version
4. Add integration test that verifies the exact JSON structure returned by `process_document_for_rag` tool -- this test becomes the contract guardian
5. In the MCP tool response, include a `format_version` field so clients can adapt

**Warning signs:**
- `process_document_for_rag` returns different JSON keys than tests expect
- Integration tests pass but manual MCP client testing shows wrong output
- TypeScript bridge throws "Cannot read property of undefined" on Python response

**Phase to address:**
Structured RAG output phase -- must come AFTER test infrastructure is stable, so integration tests can guard the contract.

---

### Pitfall 5: Deleting Files That Are Secretly Imported at Runtime

**What goes wrong:**
Repo cleanup targets obvious candidates for deletion: debug scripts, old validation files, duplicate docs. But some files that look like development artifacts are actually imported at runtime:
- `lib/rag_processing.py` is a "facade" that delegates to `lib/rag/` -- deleting it as "old monolith code" breaks the Python bridge which imports it directly
- `lib/__init__.py` makes `lib/` a Python package -- deleting it as "boilerplate" breaks all imports
- Root-level `index.js` is referenced by `"main"` in package.json -- deleting it without updating package.json breaks CJS consumers
- `zlibrary/` vendored fork is an editable install (`-e ./zlibrary` in pyproject.toml) -- moving it breaks the UV dependency resolution
- `setup-uv.sh` is referenced in installation docs and possibly user setups

Additionally, the `scripts/validate-python-bridge.js` is run as a `postbuild` hook. Deleting or moving it without updating `package.json` breaks the build.

**Why it happens:**
With 1,017 files across TypeScript and Python, it is impossible to visually determine which files are runtime dependencies. Python's dynamic imports and the PythonShell bridge add invisible dependency chains that do not show up in TypeScript's `import` statements or `tsconfig.json`.

**How to avoid:**
1. Before deleting ANY Python file, search for it in three places: `import` statements, PythonShell `scriptPath` arguments, and pytest fixtures
2. Before deleting ANY JavaScript/TypeScript file, check `package.json` (scripts, bin, main, exports), `jest.config.js`, and `tsconfig.json`
3. Create a dependency map BEFORE cleanup: `grep -r "import\|require\|scriptPath" lib/ src/ __tests__/`
4. Delete in small batches (5-10 files), run full test suite between batches
5. Safe deletion order: docs first (no imports), then scripts (check package.json), then source files (highest risk)

**Warning signs:**
- Build fails with "postbuild script not found"
- Python bridge throws ModuleNotFoundError at runtime (not at import time)
- `uv sync` fails with "package not found" after moving vendored dependency

**Phase to address:**
Repo cleanup phase. Must come AFTER test infrastructure is green (so deletions can be validated). Must come BEFORE npm publishing (so only needed files are published).

---

### Pitfall 6: Quality Scoring Creates Flaky CI From Non-Deterministic Outputs

**What goes wrong:**
Automated quality scoring for RAG output introduces non-determinism into CI. PDF extraction is inherently non-deterministic across:
- Different PyMuPDF versions (text extraction order can change)
- Different OS character encoding defaults
- Different PDF renderer backends

If quality scoring thresholds are set based on one environment's output (e.g., developer's machine), CI running on Ubuntu GitHub Actions with different library versions may produce slightly different scores, causing intermittent test failures.

Additionally, ground truth files in `test_files/ground_truth/` currently have THREE schema versions (`schema.json`, `schema_v2.json`, `schema_v3.json`). If quality scoring references the wrong schema version, scores are calculated against incorrect expectations.

**Why it happens:**
Quality scoring feels like "just adding a number" but it creates a floating-point comparison problem. A 0.85 quality score on macOS might be 0.83 on Linux. Hard threshold (e.g., `assert score >= 0.85`) passes locally, fails in CI.

**How to avoid:**
1. Use score RANGES not exact thresholds: `assert 0.75 <= score <= 1.0` for CI gates
2. Pin PyMuPDF version exactly in `pyproject.toml` (currently `>=1.26.0` -- pin to `==1.26.x`)
3. Consolidate ground truth schemas to a single version BEFORE adding scoring
4. Make quality scoring informational in CI first (log scores, do not gate on them) for at least 2 weeks of data collection
5. If gating, use percentile-based thresholds from collected data, not absolute numbers
6. Mark scoring tests with a custom pytest marker and allow CI to soft-fail them initially: `pytest -m "not quality_gate" && pytest -m quality_gate || true`

**Warning signs:**
- CI test failures that pass on retry without code changes
- Quality scores differ by more than 5% between local and CI
- Multiple ground truth schema versions referenced by different tests

**Phase to address:**
Quality scoring phase -- must come AFTER ground truth consolidation and AFTER test infrastructure stabilization. Consider making it an informational-only phase first, gating phase later.

---

### Pitfall 7: npm postinstall Python Environment Bootstrap Fails Silently

**What goes wrong:**
The zlibrary-mcp package requires Python with UV to function. After `npm install zlibrary-mcp`, the user must also run `uv sync` or `setup-uv.sh` to create the `.venv/` with Python dependencies. If this step is missed, the MCP server starts but crashes on first tool invocation with an unhelpful Python error.

Alternatives are equally dangerous:
- A `postinstall` script that runs `uv sync` will fail if UV is not installed, failing the entire npm install
- A `postinstall` script that runs `pip install` ignores the vendored zlibrary editable install
- Checking for Python at startup adds 2-3 seconds of latency to every MCP server start

**Why it happens:**
npm's package lifecycle assumes Node.js-only dependencies. Dual-language packages that require system-level tooling (Python, UV) have no standard mechanism for dependency bootstrapping. The MCP protocol's stdio transport makes it hard to communicate setup failures to users -- the server just fails to respond.

**How to avoid:**
1. Add a `postinstall` script that CHECKS (does not install): verify UV exists, verify `.venv/` exists, emit clear instructions if missing
2. In the MCP server startup (`src/index.ts`), add a health check that verifies Python venv before registering tools -- fail fast with a clear error message
3. Document the two-step install in README: `npm install zlibrary-mcp && cd node_modules/zlibrary-mcp && bash setup-uv.sh`
4. Consider shipping a `bin/setup` script that handles the Python setup separately
5. Test the install flow from scratch in a clean Docker container

**Warning signs:**
- `npm install` succeeds but `npx zlibrary-mcp` crashes immediately
- Error messages reference Python paths that do not exist
- Users open issues about "server not responding" (actually a Python crash hidden by stdio transport)

**Phase to address:**
npm publishing phase. Must include a documented "install verification" step.

---

### Pitfall 8: Fixing Existing Bugs Breaks Tests That Depend on Broken Behavior

**What goes wrong:**
The project has known bugs that tests have been written around:

1. **paths.test.js fails** because `getRequirementsTxtPath()` references `requirements.txt` (deleted during UV migration) and `getVenvPath()` references `venv` (now `.venv`). Tests check for file existence -- fixing the functions to reference `pyproject.toml` and `.venv` means updating the functions AND the test expectations. But other code may depend on the old paths.

2. **mcp-protocol.test.js fails** with "Expected length: 12, Received length: 13" -- tests expect 11 tools but 13 now exist (after v1.1 added tools). Fixing the test means updating the expected count, but the test name says "11 expected tools" which is now wrong.

3. **2 pytest collection errors** on `scripts/archive/test_tesseract_comparison.py` and `scripts/test_marginalia_detection.py` -- these are scripts that happen to match pytest's test discovery pattern but are not actual test files. "Fixing" by adding them to testpaths exclusion could hide real test files.

If multiple bug fixes are mixed into a single commit, it becomes impossible to determine whether a new test failure is from the fix or from an introduced regression.

**Why it happens:**
Tests often encode the current behavior, not the correct behavior. After extended development (44K LOC, 103 commits in v1.1 alone), tests accumulate assumptions about the environment that become invisible contracts.

**How to avoid:**
1. Fix each bug in its own commit with a clear test update in the same commit
2. For paths.test.js: update the functions FIRST (change `requirements.txt` to `pyproject.toml`, `venv` to `.venv`), then update the test assertions
3. For mcp-protocol.test.js: do NOT hardcode tool counts -- use `expect(tools.length).toBeGreaterThanOrEqual(11)` or dynamically detect
4. For pytest collection: add `testpaths = __tests__/python` to `pytest.ini` to explicitly scope test discovery
5. Run the full test suite between each individual bug fix to isolate regressions

**Warning signs:**
- A "simple fix" changes more than 3 files
- Fixing one test causes a different test to fail
- Test names no longer match what they test ("should expose 11 tools" but expects 12)

**Phase to address:**
Bug fixes should be the FIRST thing in v1.2, done in the test infrastructure phase before any new features. Fix known bugs, get to green CI, then stabilize.

---

### Pitfall 9: Documentation Overhaul Produces Stale Docs That Mislead Future Development

**What goes wrong:**
The project has documentation in FIVE locations:
1. `.claude/` (13 files, 1.9 MB) -- AI assistant guides
2. `claudedocs/` (30+ files, 4.5 MB) -- session notes, analyses, research
3. `docs/` (40+ files, 1.3 MB) -- specs, ADRs, architecture
4. Root level (CLAUDE.md, README.md, QUICKSTART.md, DOCUMENTATION_MAP.md, ISSUES.md)
5. `.planning/` (40+ files, 1.5 MB) -- GSD planning artifacts

A documentation "overhaul" typically consolidates and rewrites. The pitfall: consolidated docs become stale within one development cycle because:
- The new docs describe the code AS IT WAS when written, not as it evolves
- Generated API docs from code comments require re-running after every change
- If docs are auto-generated, important context written by humans gets overwritten
- Multiple doc locations persist because different tools (Claude, GSD, developers) expect different paths

**Why it happens:**
Documentation overhauls are satisfying one-time projects. But docs are only valuable when maintained. The current 5-location sprawl happened because each tool created its own documentation home. Consolidation without changing the tools that create docs means the sprawl returns.

**How to avoid:**
1. Do NOT consolidate all docs into one location. Instead, define ownership: `.claude/` for AI context (updated by Claude), `docs/` for user-facing docs (updated by devs), `.planning/` for project management (updated by GSD)
2. Delete `claudedocs/` entirely -- it is archived session notes, not living documentation
3. Move root-level docs (`QUICKSTART.md`, `DOCUMENTATION_MAP.md`, `BUG_5_OPTIMIZATION_PLAN.md`, etc.) into `docs/` or delete
4. Keep CLAUDE.md at root (MCP ecosystem convention) but make it reference docs/ rather than duplicating content
5. For any doc that references code paths or configuration: add a `<!-- verify: command -->` comment with a check command. A CI step can run these periodically.

**Warning signs:**
- Same information documented in 3+ places with different versions
- Docs reference files that no longer exist
- README installation instructions differ from QUICKSTART.md instructions

**Phase to address:**
Documentation phase -- should come AFTER repo cleanup (so docs describe the final state) and AFTER test stabilization (so doc examples are verified).

---

### Pitfall 10: Husky Pre-Commit Runs lint-staged Which Triggers Full TypeScript Build

**What goes wrong:**
The current pre-commit hook runs `npx lint-staged`, which is configured to:
```json
"lint-staged": {
  "src/**/*.{ts,js}": "npm run build",
  "*.py": ["uv run ruff check --fix", "uv run ruff format"]
}
```

The `npm run build` runs the FULL TypeScript compilation (`tsc`) on EVERY commit that touches any `.ts` or `.js` file in `src/`. This takes 5-15 seconds depending on the machine. For a v1.2 phase that involves heavy code changes (test reorganization, source cleanup), this means every commit attempt runs a full build.

When combined with test infrastructure changes, this creates a feedback loop: fix test config, try to commit, build fails because source is in flux, cannot commit the fix.

**Why it happens:**
lint-staged was configured to ensure broken TypeScript never gets committed. This is correct for a stable codebase, but during active refactoring phases, it creates friction. The build also runs `postbuild` (validate-python-bridge.js) which checks for file existence -- if files are being moved, validation fails.

**How to avoid:**
1. During refactoring phases, temporarily change lint-staged to run `tsc --noEmit` (type-check without build) instead of `npm run build`
2. Or use `--no-verify` flag explicitly for WIP commits during active reorganization (document this practice)
3. Keep the full build check in CI as the safety net
4. After refactoring is complete, restore the full build in lint-staged

**Warning signs:**
- Developers skipping pre-commit with `--no-verify` on every commit (means the hook is too aggressive)
- Pre-commit takes more than 10 seconds
- Pre-commit fails on intermediate states during multi-file refactoring

**Phase to address:**
Acknowledge during test infrastructure phase. Adjust lint-staged config at phase start, restore at phase end.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Blacklist `.npmignore` instead of whitelist `files` | Easier to write initially | Ships 44 MB of test PDFs and internal docs | Never for published packages |
| Hardcoded tool count in tests (`toHaveLength(12)`) | Easy assertion | Breaks every time a tool is added | Never -- use dynamic counts |
| Three ground truth schema versions | Backward compat | Tests reference wrong schema, scoring is inconsistent | Only during migration, consolidate ASAP |
| `"main": "index.js"` pointing to legacy CJS | Preserves old behavior | Confuses module resolution, ships dead code | Never after ESM migration |
| Root-level debug scripts | Quick debugging | Pollutes project root, ships in npm package | Only on branches, never on master |
| Python facade in `rag_processing.py` | Backward compat for imports | Two files to maintain, confusion about which is canonical | Acceptable for one version, then remove |

## Integration Gotchas

Common mistakes when connecting to external services in this project's context.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PythonShell bridge | Assuming Python errors will be caught by Node.js try/catch | PythonShell emits errors on stderr -- must listen to `pythonShell.on('error')` and `pythonShell.on('stderr')` separately |
| UV venv in npm package | Assuming `.venv/` exists after `npm install` | Check for `.venv/` at startup, emit clear error with setup instructions |
| Vendored zlibrary fork | Moving `zlibrary/` directory without updating `pyproject.toml` sources | The `tool.uv.sources` config has a relative path `"./zlibrary"` -- must move both together |
| GitHub Actions CI | Assuming `uv` is available | Must use `astral-sh/setup-uv@v4` action before any `uv` commands |
| MCP client tool discovery | Changing tool names or schemas without versioning | MCP clients cache tool lists -- renamed tools appear as "new" while old tool calls fail |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full TypeScript build in pre-commit | 15s commit times | Use `tsc --noEmit` for type-checking only | Any project with >20 TypeScript files |
| pytest collecting scripts/ directory | 2 extra seconds + collection errors | Add `testpaths` to pytest.ini | When scripts/ grows beyond 10 files |
| 44 MB npm tarball | Slow install, registry rejection | Whitelist with `"files"` field | npm rejects packages >50 MB |
| Ground truth PDFs in test suite | CI downloads 40 MB of fixtures per run | Store large fixtures in Git LFS or separate fixture package | When CI runner disk fills or download times exceed timeout |

## Security Mistakes

Domain-specific security issues for this project.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Publishing `.env.example` with real credential patterns | Users copy-paste and expose credentials | Use generic placeholders: `YOUR_EMAIL_HERE` not `user@example.com` |
| npm tarball includes `.planning/config.json` | Exposes project management details, model choices | Whitelist `"files"` in package.json |
| PythonShell passes user input to Python eval | Command injection via search queries | Verify python_bridge.py uses JSON parsing, never `eval()` |
| Vendored zlibrary fork may contain hardcoded test credentials | Credential exposure in npm package | Audit `zlibrary/src/test.py` before publishing (40 KB file) |
| MCP server runs with user's full filesystem access | Malicious input could write to arbitrary paths | Validate download directory is under allowed path, not `/` or `~` |

## UX Pitfalls

Common user experience mistakes for MCP server packages.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent failure when Python venv is missing | Server appears to start but every tool call fails | Fail fast at startup with clear "Run setup-uv.sh" message |
| Changing tool names between versions | Claude/Cline integrations break silently | Keep old tool names as aliases for one version cycle |
| Output format change breaks MCP client parsing | Client shows raw error instead of book data | Version output format, support old format for one cycle |
| Requiring Node 22+ without checking | Cryptic ESM errors on Node 18/20 | `engines` field already correct, but add runtime version check in startup |
| npm package requires manual Python setup | User installs via npm, expects it to work | Clear error message at startup, or document two-step install prominently |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **npm publish:** Package seems small -- verify with `npm pack --dry-run` that test PDFs are excluded
- [ ] **Test reorganization:** Jest passes -- verify pytest ALSO passes (separate test runner, separate config)
- [ ] **Bug fixes:** paths.test.js passes -- verify the PATH FUNCTIONS still work at runtime (test checks existence, runtime uses the path)
- [ ] **Documentation cleanup:** README is updated -- verify CLAUDE.md, QUICKSTART.md, and docs/ all agree
- [ ] **Quality scoring:** Scores look good locally -- verify they are reproducible on Ubuntu CI runner
- [ ] **Repo cleanup:** No TypeScript errors -- verify Python imports still resolve (PythonShell runtime errors not caught by tsc)
- [ ] **Entry point fix:** `npx zlibrary-mcp` works -- verify `require('zlibrary-mcp')` also resolves correctly
- [ ] **Ground truth consolidation:** Schema v3 is active -- verify no test still references schema v1 or v2
- [ ] **Pre-commit hooks:** lint-staged passes -- verify it does not run full build during active refactoring phases
- [ ] **Vendored fork:** `uv sync` works -- verify after any directory moves that `tool.uv.sources` path is still valid

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 44 MB package published to npm | LOW | `npm unpublish zlibrary-mcp@version` (within 72 hours), fix `files` field, republish with bumped version |
| Tests broken after reorganization | MEDIUM | `git stash` changes, fix config files first in isolation, then replay reorganization |
| RAG output format broke consumers | HIGH | Cannot un-break consumers. Must publish patch release with backward-compatible format. Introduce versioned output alongside. |
| Deleted runtime-needed file | LOW | `git checkout -- path/to/file` if uncommitted. If committed and pushed, revert commit. |
| Flaky quality scoring in CI | LOW | Add `|| true` to quality scoring step in CI, making it informational while investigating |
| Python env missing after npm install | MEDIUM | Add startup health check, publish clear error message, update README with troubleshooting |
| Published .env or credentials | CRITICAL | Rotate ALL credentials immediately. `npm unpublish` if within window. Cannot undo exposure. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Test reorganization breaks CI (Pitfall 3) | Phase 1: Test Infrastructure | `npm test && uv run pytest` both pass, 0 collection errors |
| Fixing bugs introduces regressions (Pitfall 8) | Phase 1: Test Infrastructure / Bug Fixes | Each bug fix is one commit, full suite green between fixes |
| Pre-commit friction during refactoring (Pitfall 10) | Phase 1: Test Infrastructure | lint-staged adjusted to `tsc --noEmit` during refactoring |
| RAG output format breaks consumers (Pitfall 4) | Phase 2: Structured RAG Output | Integration test pins exact JSON structure of tool response |
| Quality scoring flaky in CI (Pitfall 6) | Phase 3: Quality Scoring | Scores logged for 2 weeks before gating. Range thresholds, not exact. |
| Deleting needed files (Pitfall 5) | Phase 4: Repo Cleanup | Dependency map created before deletion. Small batches with test runs. |
| Docs drift from code (Pitfall 9) | Phase 5: Documentation | `claudedocs/` deleted. Doc ownership defined. Verify commands in doc comments. |
| Conflicting entry points (Pitfall 2) | Phase 4: Repo Cleanup | `main` and `exports` both point to `dist/index.js`. Root `index.js` deleted. |
| 44 MB npm tarball (Pitfall 1) | Phase 6: npm Publishing | `"files"` whitelist in package.json. CI fails if tarball > 10 MB. |
| Python env bootstrap (Pitfall 7) | Phase 6: npm Publishing | Clean Docker install test. Startup health check. Clear error messages. |

## Sources

- Direct codebase inspection: `npm pack --dry-run` output showing 1,017 files / 44.4 MB tarball (PRIMARY SOURCE)
- Direct codebase inspection: `package.json` conflicting `main` vs `exports` fields
- Direct codebase inspection: Jest and pytest test failures and collection errors
- Direct codebase inspection: Ground truth schema versions v1/v2/v3
- [npm Files & Ignores documentation](https://github.com/npm/cli/wiki/Files-&-Ignores) -- `files` field vs `.npmignore` behavior
- [npm package.json files field docs](https://docs.npmjs.com/cli/v7/configuring-npm/package-json/) -- whitelist approach recommended
- [Pytest Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) -- pythonpath and test discovery configuration
- [Atlassian: Taming Test Flakiness](https://www.atlassian.com/blog/atlassian-engineering/taming-test-flakiness-how-we-built-a-scalable-tool-to-detect-and-manage-flaky-tests) -- flakiness scoring approaches
- [Backward Compatibility in Schema Evolution](https://www.dataexpert.io/blog/backward-compatibility-schema-evolution-guide) -- additive-only changes principle
- [Semgrep: Malicious MCP Server on npm](https://semgrep.dev/blog/2025/so-the-first-malicious-mcp-server-has-been-found-on-npm-what-does-this-mean-for-mcp-security/) -- MCP security considerations
- [MCP Server Publishing Guide](https://modelcontextprotocol.info/tools/registry/publishing/) -- MCP publishing best practices

---
*Pitfalls research for: v1.2 Production Readiness of zlibrary-mcp (dual TypeScript + Python MCP server)*
*Researched: 2026-02-11*
