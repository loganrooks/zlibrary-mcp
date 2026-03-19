# Phase 15: Cleanup & DX Foundation - Research

**Researched:** 2026-03-19
**Domain:** Repository hygiene, developer tooling (ESLint, Prettier, coverage), startup validation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ESLint rule set:**
- Start with `@typescript-eslint/recommended` -- the community standard
- Add `no-unused-vars` and `consistent-type-imports` per DX-01
- Do NOT start with `strict` or `stylistic` presets -- risk of hundreds of violations blocking progress
- Claude's discretion on specific rule additions as long as the base is `recommended`

**Prettier configuration:**
- MUST match the existing code style (the codebase was written consistently)
- Research should analyze the existing style: tab width, semicolons, quote style, trailing commas, print width
- Prettier is configured to reflect what already exists, not impose a new standard
- After initial config, run `prettier --write` on the whole codebase as a single commit
- Add `.git-blame-ignore-revs` pointing to that commit so `git blame` skips it

**Python linting:**
- Already handled by ruff (configured in pyproject.toml, enforced via lint-staged)
- No changes needed -- leave as-is

**lint-staged integration:**
- Extend existing lint-staged config to run ESLint + Prettier on TS files
- Current: `"src/**/*.{ts,js}": "bash -c 'tsc --noEmit'"` + `"*.py": ["uv run ruff check --fix", "uv run ruff format"]`
- New: add ESLint check and Prettier format for TS files alongside existing tsc check

**Startup Validation:**
- Credential presence check only. Don't over-engineer.
- Check `ZLIBRARY_EMAIL` and `ZLIBRARY_PASSWORD` environment variables in TypeScript before `server.connect()`
- Emit clear, actionable error message with exact instructions (what to set, where)
- Exit with non-zero code within 2 seconds (per DX-03)
- Do NOT check: network connectivity, UV installation, Python version

**Git History Cleanup:**
- One final filter-repo pass to purge ALL remaining large blobs not tracked by LFS
- Scope: all blobs >1MB that are NOT current LFS pointer files
- This is a one-way door -- must be thorough

**Coverage Thresholds:**
- Separate thresholds for TypeScript (Jest) and Python (pytest)
- Set each threshold at current coverage minus 5%
- Blocking from the start (not informational)

### Claude's Discretion
- Exact ESLint rule additions beyond `recommended`
- Prettier specific settings (as long as they match existing code style)
- lint-staged command ordering (ESLint before or after tsc)
- Coverage report format (lcov, text, json)
- Exact error message wording for startup validation

### Deferred Ideas (OUT OF SCOPE)
- CI enforcement of lint/coverage -- Phase 17 (Quality Gates)
- README badges for coverage -- Phase 16 (Documentation)
- Multi-platform testing (macOS/Windows) -- deferred to v1.4+
- postinstall script for Python setup -- deferred to v1.4+ (PKG-F02)
</user_constraints>

## Summary

This phase covers six distinct domains: git history cleanup, dead file removal, ESLint/Prettier setup, startup validation, test fix, and coverage baseline. Research confirms all decisions from CONTEXT.md are sound, with one important finding about lint-staged + ESLint v9 compatibility that was flagged as a risk and is now resolved.

The codebase investigation revealed: 8 large blobs totaling ~107MB in git history (only 1 is in the current tree), 6 stale `.js` build artifacts in `src/`, a clear code style (2-space indent, single quotes, semicolons), and a confirmed Jest coverage baseline of ~77% statements / ~79% lines. pytest-cov is NOT in the project's UV dependencies and must be added. The `src/index.js` CJS fallback is definitively stale -- the project is `"type": "module"` with all entry points via `dist/`.

**Primary recommendation:** Execute git history cleanup FIRST (one-way door), then file cleanup, then tooling setup. The filter-repo pass should target 7 specific blob SHAs from old history, plus handle the 1.4MB `__tests__/python/fixtures/rag_robustness/sample.pdf` which should be migrated to LFS.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| eslint | ^10.0.3 | TypeScript/JS linting | De facto standard; v9+ uses flat config |
| @eslint/js | ^10.0.1 | ESLint core recommended rules | Required base for flat config |
| typescript-eslint | ^8.57.1 | TypeScript-specific ESLint rules | Official TS-ESLint monorepo package |
| eslint-config-prettier | ^10.1.8 | Disable ESLint rules that conflict with Prettier | Prevents ESLint/Prettier fights |
| prettier | ^3.8.1 | Code formatter | Industry standard, zero-config |
| pytest-cov | >=7.0.0 | Python test coverage reporting | Standard pytest plugin for coverage |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| git-filter-repo | 2.47.0 (installed) | Git history rewriting | One-time blob purge |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| eslint-config-prettier | eslint-plugin-prettier | Plugin runs Prettier as ESLint rule -- slower, more coupling. Config-only approach is simpler |
| Separate ESLint + Prettier runs | eslint-plugin-prettier (combined) | Faster single-pass but tighter coupling; separate runs are the modern recommendation |

**Installation:**
```bash
npm install --save-dev eslint @eslint/js typescript-eslint eslint-config-prettier prettier
uv add --dev pytest-cov
```

## Architecture Patterns

### Pattern 1: ESLint v9 Flat Config with TypeScript
**What:** Single `eslint.config.js` file using the flat config array format.
**When to use:** All new ESLint setups (flat config is default since ESLint v9.0.0).
**Key detail:** Since `package.json` has `"type": "module"`, use `.js` extension (not `.mjs`).

```javascript
// eslint.config.js
// Source: https://typescript-eslint.io/getting-started/
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import eslintConfigPrettier from 'eslint-config-prettier/flat';

export default tseslint.config(
  eslint.configs.recommended,
  tseslint.configs.recommended,
  eslintConfigPrettier,
  {
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': 'error',
    },
  },
  {
    ignores: ['dist/', 'node_modules/', 'coverage/', '__tests__/', '__mocks__/', 'scripts/'],
  },
);
```

**Critical:** Use `tseslint.config()` helper (not raw array). It handles the TypeScript parser setup automatically.

### Pattern 2: Prettier Configuration Matching Existing Style
**What:** `.prettierrc` configured to match the codebase's existing conventions.
**Existing style determined from codebase analysis:**

| Convention | Value | Evidence |
|-----------|-------|----------|
| Indent | 2 spaces | `cat -A` on TS files shows 2-space indent (no tab characters) |
| Semicolons | Yes | 84 semicoloned lines vs 110 without (the "without" are mostly `{`, `}`, blank) |
| Quote style | Single quotes | 120 single-quote occurrences vs 3 double-quote in sampled files |
| Trailing commas | ES5 style | Commas in function params, object props; standard TS convention |
| Print width | 100 | Longest lines reach 300+ chars, but these are in `src/index.ts` tool descriptions -- Prettier default 80 is too narrow for this codebase |

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "tabWidth": 2,
  "printWidth": 100,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "always"
}
```

**Recommendation:** `printWidth: 100` is a judgment call. The existing code has some very long lines (300+ chars in tool description strings), but those are unusual. Most code fits within 100 chars. Prettier will wrap the outliers, which is acceptable. Going with 80 would cause excessive reformatting of normal code.

### Pattern 3: lint-staged Configuration for ESLint + Prettier + tsc
**What:** Extended lint-staged config that runs all three tools on staged TS files.

```json
{
  "lint-staged": {
    "src/**/*.ts": [
      "eslint --fix",
      "prettier --write",
      "bash -c 'tsc --noEmit'"
    ],
    "*.py": [
      "uv run ruff check --fix",
      "uv run ruff format"
    ]
  }
}
```

**Key findings about lint-staged + ESLint v9:**
- lint-staged automatically appends staged file paths to commands
- Use `eslint --fix` (NOT `eslint --fix .` or `eslint --fix **/*.ts`)
- The lint-staged issue #1409 was a user config error, not a compatibility bug
- ESLint v9 flat config works with lint-staged when commands are correctly configured

**Order recommendation:** ESLint first (catches logic errors), then Prettier (formats), then tsc (type-checks the final result). ESLint `--fix` may change code, Prettier then normalizes formatting, tsc validates types on the final output.

### Pattern 4: Startup Credential Validation
**What:** Fast environment variable check before MCP server connects.
**Where:** `src/index.ts`, before `server.connect()` call.

```typescript
// Validate required credentials before server startup
function validateCredentials(): void {
  const email = process.env.ZLIBRARY_EMAIL;
  const password = process.env.ZLIBRARY_PASSWORD;

  if (!email || !password) {
    const missing = [];
    if (!email) missing.push('ZLIBRARY_EMAIL');
    if (!password) missing.push('ZLIBRARY_PASSWORD');

    console.error(
      `\nError: Missing required environment variable(s): ${missing.join(', ')}\n\n` +
      `To fix this, set the following in your MCP client configuration:\n` +
      `  "env": {\n` +
      `    "ZLIBRARY_EMAIL": "your-email@example.com",\n` +
      `    "ZLIBRARY_PASSWORD": "your-password"\n` +
      `  }\n\n` +
      `See README.md for detailed setup instructions.\n`
    );
    process.exit(1);
  }
}
```

### Pattern 5: .git-blame-ignore-revs
**What:** File that tells `git blame` to skip specific commits (like mass reformatting).

```
# .git-blame-ignore-revs
# Prettier initial formatting pass
<commit-sha-of-prettier-reformat>
```

Then configure locally:
```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

### Anti-Patterns to Avoid
- **Running Prettier through ESLint (`eslint-plugin-prettier`):** Slower, more coupling, harder to debug. Use separate tools.
- **Using `eslint .` in lint-staged:** lint-staged already passes file paths. Adding `.` causes it to lint the entire project.
- **Setting coverage threshold at exact current value:** Any minor refactoring will break CI. Always use a buffer.
- **Removing `src/index.js` without updating .gitignore first:** tsc will regenerate it on next build.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TypeScript linting rules | Custom ESLint plugin | `tseslint.configs.recommended` | Hundreds of rules maintained by community |
| Code formatting | Manual style guide enforcement | Prettier | Eliminates all formatting debates |
| ESLint + Prettier conflict resolution | Manual rule disabling | `eslint-config-prettier/flat` | Automatically detects and disables conflicting rules |
| Git history blob analysis | Manual `git log` parsing | `git-filter-repo --analyze` | Produces complete blob size report |
| Coverage thresholds | Custom scripts | Jest `coverageThreshold` + pytest `--cov-fail-under` | Built-in, maintained, well-documented |

**Key insight:** The lint/format toolchain has a well-established composition pattern (ESLint for logic, Prettier for formatting, eslint-config-prettier to resolve conflicts). Deviating from this causes subtle rule conflicts.

## Common Pitfalls

### Pitfall 1: ESLint v9 Flat Config + lint-staged File Path Confusion
**What goes wrong:** ESLint silently processes zero files when lint-staged passes file paths that don't match flat config's file patterns.
**Why it happens:** ESLint v9 flat config uses `files` arrays in config objects. If your config only specifies `files: ['src/**/*.ts']` and lint-staged passes absolute paths, they may not match.
**How to avoid:** Do NOT add explicit `files` patterns in ESLint config when using lint-staged. Let the default matching work. lint-staged already filters by its own glob patterns.
**Warning signs:** Pre-commit hook runs instantly with no output (ESLint matched zero files).

### Pitfall 2: filter-repo Corrupting LFS Pointers
**What goes wrong:** Using filename-based removal (e.g., `--path test_files/`) would affect current LFS pointer files.
**Why it happens:** filter-repo operates on paths. The same path (`test_files/DerridaJacques...pdf`) exists in old commits as a real blob AND in current commits as an LFS pointer.
**How to avoid:** Target by BLOB SHA, not by filename. Use `--strip-blobs-bigger-than 1M` combined with `--blob-callback` that skips LFS pointers, OR target specific blob SHAs from the analysis below.
**Warning signs:** After filter-repo, `git lfs ls-files` shows fewer files than before.

### Pitfall 3: Prettier Reformatting Breaking Existing Tests
**What goes wrong:** Prettier rewrites files in `__tests__/` or changes string literals in ways that break test assertions.
**Why it happens:** Prettier may reformat template literals, string concatenations, or test fixture data.
**How to avoid:** Exclude `__tests__/` from Prettier, OR include it but run tests after reformatting. Since tests are `.js` files (not `.ts`), they may not need Prettier.
**Warning signs:** Tests pass before Prettier, fail after.

### Pitfall 4: Coverage Threshold Blocks on Dead Code Removal
**What goes wrong:** Removing untested dead code actually lowers coverage percentage (numerator unchanged, denominator shrinks proportionally less).
**Why it happens:** If you remove 100 lines of untested code from a file with 80% coverage, the remaining code may have a different coverage ratio.
**How to avoid:** Set threshold 5% below current baseline. This is already the decided approach.
**Warning signs:** CI fails after a cleanup-only PR.

### Pitfall 5: `src/index.js` Regenerated by tsc
**What goes wrong:** After deleting `src/index.js`, the next `npm run build` regenerates `.js` files in `src/` because `tsconfig.json` has `"rootDir": "./src"` and `"outDir": "./dist"`.
**Why it happens:** tsc with `"allowJs": true` may process existing `.js` files. But the real issue is that old `.js` files were manually placed in `src/` -- tsc does NOT output to `src/`. The `.gitignore` must be updated BEFORE or simultaneously with deletion to prevent the files from showing as untracked again.
**Resolution:** The `.js` files in `src/` are stale artifacts, not tsc output (tsc outputs to `dist/`). Deleting them and adding `src/**/*.js` to `.gitignore` is correct. tsc will NOT regenerate them.

## Code Examples

### Jest Coverage Threshold Configuration
```javascript
// In jest.config.js -- add to existing config
// Source: Jest documentation, coverageThreshold
{
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'json-summary'],
  collectCoverageFrom: [
    'dist/**/*.js',
    '!dist/**/*.test.js',
    '!dist/**/*.d.ts',
  ],
  coverageThreshold: {
    global: {
      statements: 72,  // Current 76.86% minus 5%
      branches: 66,    // Current 71.06% minus 5%
      functions: 56,    // Current 61.25% minus 5%
      lines: 74,        // Current 79.16% minus 5%
    },
  },
}
```

### pytest Coverage Configuration
```ini
# In pytest.ini or pyproject.toml [tool.pytest.ini_options]
# After measuring baseline, add:
# --cov=lib --cov-report=term-missing --cov-fail-under=XX
```

### Node 22 JSON.parse Error Fix
```javascript
// OLD (fails on Node 22):
.toThrow(/Failed to parse initial JSON output from Python script: Unexpected token T in JSON at position 0/);

// NEW (works on Node 22+):
.toThrow(/Failed to parse initial JSON output from Python script:/);
// Or more precisely:
.toThrow(/Failed to parse initial JSON output from Python script: Unexpected token/);
```
Node 22 changed `JSON.parse` error messages from `"Unexpected token T in JSON at position 0"` to `"Unexpected token 'T', \"This is not JSON\" is not valid JSON"`. The fix is to make the regex match only the stable prefix.

### filter-repo Blob Purge Command
```bash
# Dry-run analysis first
git filter-repo --analyze

# Target specific blobs by SHA (safe for LFS)
git filter-repo \
  --strip-blobs-with-ids <(echo "9053b7405ece754dc52012b774a0a0c0fdd583a3
f274e990d307b47cef6985e7e7e2cc9c2a6707c1
bc9e3c167424010c523edb74ef8b1e961dc5ba8f
7eae90c48bcd35648bdc967b051ce0879033ff44
170b5a3d9f95b25e62e7df3a4a4bed740ae05c3b
f008f2389440939917a351bfe76fdbbe11363bed
54242e3d67c91dfa35d291148ac1b008b7769acc") \
  --force
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.eslintrc.json` / `.eslintrc.js` | `eslint.config.js` (flat config) | ESLint v9 (April 2024) | Must use flat config; legacy format deprecated |
| `@typescript-eslint/eslint-plugin` + `@typescript-eslint/parser` as separate packages | `typescript-eslint` unified package | typescript-eslint v8 (2024) | Single import, simpler config |
| `eslint-config-prettier` default import | `eslint-config-prettier/flat` import | eslint-config-prettier v9+ | Must use `/flat` suffix for flat config |
| `JSON.parse` error: `"Unexpected token X in JSON at position N"` | `"Unexpected token 'X', \"...\" is not valid JSON"` | Node 22 | Tests matching old format break |

**Deprecated/outdated:**
- `.eslintrc.*` files: Use `eslint.config.js` instead
- ESLint v8: EOL, though still functional
- `@typescript-eslint/eslint-plugin` as standalone: Use unified `typescript-eslint` package

## Codebase Investigation Results

### Large Blobs in Git History (CLEAN-05)

| Blob SHA | Size | Path | In Current Tree? | Action |
|----------|------|------|-------------------|--------|
| `9053b740` | 74 MB | `test_downloads/Kant...pdf` | No | Purge via filter-repo |
| `f274e990` | 21 MB | `test_files/Derrida...pdf` | No (now LFS pointer) | Purge old blob |
| `bc9e3c16` | 4 MB | `test_files/Margins...pdf` | No (now LFS pointer) | Purge old blob |
| `7eae90c4` | 3 MB | `test_files/Heidegger...pdf` | No (now LFS pointer) | Purge old blob |
| `170b5a3d` | 2 MB | `test_files/kant_pages_80_85.pdf` | No (now LFS pointer) | Purge old blob |
| `f008f238` | 1.3 MB | `test_files/ground_truth/...Derrida.txt` | YES | Purge (text file, regenerable) |
| `54242e3d` | 1 MB | `test_files/ground_truth/...Margins.txt` | YES | Purge (text file, regenerable) |
| `384912c7` | 1.4 MB | `__tests__/python/fixtures/sample.pdf` | YES, NOT LFS tracked | Migrate to LFS |

**Total savings estimate:** ~107 MB removed from pack file (currently 111.5 MB).

**LFS Safety:** The 5 PDF blobs from old history are completely separate objects from current LFS pointers. Current LFS pointers are tiny (<200 bytes) with different SHA values. Targeting old blob SHAs is safe.

**Current non-LFS large file:** `__tests__/python/fixtures/rag_robustness/sample.pdf` (1.4 MB) exists in the current tree without LFS tracking. Either migrate to LFS or accept the size.

### Dead Files in src/ (CLEAN-02)

| File | Size | Type | Action |
|------|------|------|--------|
| `src/index.js` | 43 KB | CJS compiled output | Remove -- stale artifact; project is ESM with `"type": "module"`, entry point is `dist/index.js` |
| `src/lib/circuit-breaker.js` | 6.5 KB | tsc output | Remove -- build artifact |
| `src/lib/errors.js` | 5.8 KB | tsc output | Remove -- build artifact |
| `src/lib/retry-manager.js` | 7.4 KB | tsc output | Remove -- build artifact |
| `src/lib/venv-manager.js` | 6.4 KB | tsc output | Remove -- build artifact |
| `src/lib/zlibrary-api.js` | 28.5 KB | tsc output | Remove -- build artifact |
| `src/zlibrary_mcp.egg-info/` | directory | setuptools artifact | Remove -- auto-generated |

**Confirmation on src/index.js:** This is NOT a CJS entry point. It is a stale artifact from an old CJS build. Evidence:
1. `package.json` has `"type": "module"` -- Node treats all `.js` as ESM
2. `"main": "dist/index.js"` and `"exports"` point to `dist/`
3. `src/index.js` starts with `"use strict"` and `var __awaiter` (CJS/CommonJS patterns) -- incompatible with `"type": "module"`
4. `dist/index.js` uses `import` syntax (proper ESM)
5. No file in the project references `src/index.js`

### .gitignore Gaps (CLEAN-03)

Current `.gitignore` is missing:
- `src/**/*.js` -- prevents tsc output artifacts from appearing as untracked
- `src/**/*.js.map` -- source maps in src (though tsc outputs to dist)
- `src/**/*.egg-info/` -- setuptools auto-generated directory

### setup_venv.sh Status (CLEAN-04)

Already removed in commit `d122c07`. No action needed -- this requirement is already satisfied.

### Existing Code Style Analysis (for Prettier config)

| Property | Value | Method |
|----------|-------|--------|
| Indentation | 2 spaces | `cat -A` shows no tab characters; 2-space nesting |
| Semicolons | Always | Consistent across all `.ts` files |
| Quote style | Single quotes | 120 single vs 3 double in sampled imports/strings |
| Trailing commas | Yes (ES5-style) | Function params and object properties |
| Print width | ~100 | Most lines under 100; outliers are description strings |
| Bracket spacing | Yes | `{ key: value }` pattern throughout |
| Arrow parens | Always | `(x) => ...` pattern observed |

### Jest Coverage Baseline (measured)

| Metric | Value | Threshold (minus 5%) |
|--------|-------|----------------------|
| Statements | 76.86% | 72% |
| Branches | 71.06% | 66% |
| Functions | 61.25% | 56% |
| Lines | 79.16% | 74% |

**Note:** 1 test fails (DX-05 target). Coverage numbers are from the passing 138 tests.

### pytest-cov Status

pytest-cov v7.0.0 is installed in the system Python but NOT in the project's UV environment. Must be added:
```bash
uv add --dev pytest-cov
```

Python test count: 881 tests collected (0.98s). Coverage baseline needs measurement after pytest-cov is added to UV deps.

### Failing Test (DX-05)

**File:** `__tests__/zlibrary-api.test.js`, line 194
**Test name:** "should throw error if Python script returns non-JSON string"
**Root cause:** Node 22 changed `JSON.parse` error message format
- Old (Node <22): `Unexpected token T in JSON at position 0`
- New (Node 22+): `Unexpected token 'T', "This is not JSON" is not valid JSON`
**Fix:** Change regex to match only the stable prefix: `/Failed to parse initial JSON output from Python script: Unexpected token/`

## Open Questions

### Resolved
- **Is ESLint v9 flat config compatible with lint-staged?** YES. The GitHub issue #1409 was a user configuration error. lint-staged passes file paths to commands; ESLint receives them correctly as long as you use `eslint --fix` (not `eslint --fix .`).
- **Does filter-repo blob removal interact safely with LFS pointer files?** YES, when targeting by blob SHA. The old pre-LFS blobs have completely different SHAs from current LFS pointers. Targeting specific blob SHAs cannot corrupt current LFS content.
- **Should src/index.js be kept or removed?** REMOVE. It is a stale CJS artifact incompatible with the project's ESM setup. No consumer references it.
- **Is pytest-cov already a dependency?** NO. It exists in the system Python but not in the project's UV environment. Must be added with `uv add --dev pytest-cov`.
- **What is the existing code style?** 2-space indent, single quotes, semicolons, ES5 trailing commas, ~100 char line width.
- **Is setup_venv.sh already removed?** YES, already removed in commit d122c07.
- **Are there secrets in git history beyond the already-scrubbed password?** No additional secrets found. The `password=""` references in `python_bridge.py` are empty placeholder arguments, not credentials.

### Genuine Gaps
| Question | Criticality | Recommendation |
|----------|-------------|----------------|
| What is the pytest coverage baseline? | Medium | Measure after adding pytest-cov to UV deps (first task of coverage setup) |
| How long does ESLint + Prettier + tsc take in lint-staged? | Low | Measure after setup; if >10s, optimize. Accept-risk for now. |
| Should `__tests__/python/fixtures/rag_robustness/sample.pdf` (1.4MB) be migrated to LFS? | Low | Migrate during filter-repo pass for consistency. Accept-risk if deferred. |
| Should ground truth `.txt` files (>1MB) be tracked as-is or gitignored? | Low | Accept as-is -- they are text, not binary, and are needed for test assertions |

### Still Open
- Does the existing eslint-config in related projects (serena, claude-enhanced) provide a reusable config? (LOW priority -- checked CONTEXT.md, deemed not worth investigating for a single project)

## Sources

### Primary (HIGH confidence)
- [typescript-eslint.io/getting-started](https://typescript-eslint.io/getting-started/) -- flat config setup, package structure, recommended presets
- [github.com/prettier/eslint-config-prettier](https://github.com/prettier/eslint-config-prettier) -- flat config import pattern (`/flat` suffix)
- [github.com/lint-staged/lint-staged/issues/1409](https://github.com/lint-staged/lint-staged/issues/1409) -- ESLint v9 compatibility confirmed (CLOSED, user error)
- Codebase investigation: `git rev-list --objects --all`, `git lfs ls-files`, `cat -A`, `npm test --coverage`, `node -e "JSON.parse()"` -- all run directly on this repo

### Secondary (MEDIUM confidence)
- [eslint.org/blog/2025/05/eslint-v9.0.0-retrospective](https://eslint.org/blog/2025/05/eslint-v9.0.0-retrospective/) -- ESLint v9 ecosystem maturity
- [eslint.org/docs/latest/use/migrate-to-9.0.0](https://eslint.org/docs/latest/use/migrate-to-9.0.0) -- migration guide for flat config
- npm registry version checks: eslint@10.0.3, typescript-eslint@8.57.1, prettier@3.8.1

### Tertiary (LOW confidence)
- None -- all findings verified against official sources or direct codebase investigation

## Knowledge Applied

Checked knowledge base (`~/.gsd/knowledge/index.md`), no relevant lessons or spikes found for this phase's domain. The KB contains only unprocessed signals (122 signals, 0 lessons, 0 spikes).

One signal of minor relevance: `sig-2026-03-19-gsd-hooks-esm-commonjs-conflict` from this project (the ESM/CJS conflict that was already fixed). This reinforces the finding that `src/index.js` (CJS artifact) is stale and should be removed in an ESM project.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- verified against official docs and npm registry
- Architecture: HIGH -- patterns verified from typescript-eslint.io and eslint-config-prettier repos; code style determined from direct codebase analysis
- Pitfalls: HIGH -- lint-staged/ESLint v9 issue confirmed closed; filter-repo/LFS interaction verified by comparing blob SHAs
- File cleanup targets: HIGH -- directly inspected filesystem and git history
- Coverage baseline: HIGH for Jest (measured), MEDIUM for pytest (needs measurement after pytest-cov install)
- Test fix: HIGH -- Node 22 error format confirmed by running `node -e "JSON.parse('...')"` on the actual runtime

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable tooling, 30-day validity)
