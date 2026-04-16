---
phase: 15-cleanup-dx-foundation
plan: 03
model: claude-opus-4-6
context_used_pct: 25
subsystem: developer-experience
tags: [eslint, prettier, lint-staged, code-quality, formatting]
requires:
  - phase: 15-02
    provides: clean git status with no stale build artifacts in src/
provides:
  - ESLint v9+ flat config with @typescript-eslint/recommended for TypeScript linting
  - Prettier config matching existing code style, enforced via lint-staged
  - lint-staged pipeline running eslint, prettier, and tsc on staged TypeScript files
  - .git-blame-ignore-revs for skipping formatting commit in git blame
affects: [all-typescript-source, ci-pipeline, developer-workflow]
tech-stack:
  added: [eslint@10, "@eslint/js", typescript-eslint@8, eslint-config-prettier, prettier@3]
  patterns: [flat-config-eslint, lint-staged-pipeline, blame-ignore-revs]
key-files:
  created:
    - eslint.config.js
    - .prettierrc
    - .prettierignore
    - .git-blame-ignore-revs
  modified:
    - package.json
    - package-lock.json
    - src/lib/python-bridge.ts
    - src/lib/venv-manager.ts
    - src/lib/zlibrary-api.ts
key-decisions:
  - "no-explicit-any set to off — codebase uses any extensively in Python bridge layer"
  - "Prettier config matches existing conventions (2-space, single quotes, semicolons, printWidth 100) to minimize diff churn"
  - "lint-staged order: eslint --fix first (logic), prettier --write second (formatting), tsc --noEmit last (type-check final output)"
patterns-established:
  - "ESLint flat config: single eslint.config.js with tseslint.config() composition"
  - "Prettier integration: eslint-config-prettier disables conflicting ESLint formatting rules"
  - "Error cause chaining: throw new Error(msg, { cause: error }) for preserving stack traces"
duration: 6min
completed: 2026-03-19
---

# Phase 15 Plan 03: ESLint + Prettier Configuration Summary

**ESLint v9+ and Prettier configured with lint-staged enforcement and blame-ignore-revs for TypeScript source**

## Performance
- **Duration:** 6min
- **Tasks:** 2/2 completed
- **Files modified:** 9

## Accomplishments
- Installed and configured ESLint v9+ with @typescript-eslint/recommended, consistent-type-imports, and eslint-config-prettier
- Created Prettier config matching existing code conventions (minimal formatting diff)
- Extended lint-staged to run eslint --fix, prettier --write, and tsc --noEmit on staged .ts files
- Fixed 6 ESLint errors in source code: async promise executor antipattern, unused variables, missing error cause chains, consistent-type-imports
- Created .git-blame-ignore-revs pointing to the formatting commit for clean git blame output
- All 139 tests pass, build succeeds, zero ESLint errors, zero Prettier issues

## Task Commits
1. **Task 1: Install and configure ESLint + Prettier with lint-staged integration** - `881221e`
2. **Task 2: Run Prettier across codebase and create blame-ignore-revs** - `7545b22`

## Files Created/Modified
- `eslint.config.js` - ESLint v9 flat config with TypeScript, Prettier integration
- `.prettierrc` - Prettier settings matching existing code style
- `.prettierignore` - Excludes dist, vendored code, Python, test files, docs
- `.git-blame-ignore-revs` - Points to Prettier formatting commit for clean blame
- `package.json` - Updated lint-staged config and devDependencies
- `package-lock.json` - Lockfile with new devDependencies
- `src/lib/python-bridge.ts` - Refactored async promise executor to await-then-wrap pattern
- `src/lib/venv-manager.ts` - Added error cause chain, removed unused catch parameter type
- `src/lib/zlibrary-api.ts` - Added error cause chain, removed unused interface and variable, import type fix

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Refactored async promise executor in python-bridge.ts**
- **Found during:** Task 1 (ESLint error `no-async-promise-executor`)
- **Issue:** `callPythonFunction` used an async function as Promise executor, which is an antipattern that can swallow errors
- **Fix:** Moved `await getManagedPythonPath()` and validation before the Promise constructor, leaving only synchronous spawn + event listeners in the executor
- **Files modified:** `src/lib/python-bridge.ts`

**2. [Rule 1 - Bug] Added error cause chains in venv-manager.ts and zlibrary-api.ts**
- **Found during:** Task 1 (ESLint error `preserve-caught-error`)
- **Issue:** Re-thrown errors lost the original stack trace
- **Fix:** Added `{ cause: error }` option to `new Error()` calls
- **Files modified:** `src/lib/venv-manager.ts`, `src/lib/zlibrary-api.ts`

**3. [Rule 1 - Bug] Removed unused code in zlibrary-api.ts**
- **Found during:** Task 1 (ESLint error `no-unused-vars`)
- **Issue:** `GetDownloadInfoArgs` interface and `logId` variable were dead code
- **Fix:** Removed both
- **Files modified:** `src/lib/zlibrary-api.ts`

**4. [Rule 1 - Bug] Prettier formatting already applied via lint-staged during Task 1 commit**
- **Found during:** Task 2
- **Issue:** Task 2 expected to run Prettier as a separate formatting pass, but lint-staged in Task 1's commit already ran `prettier --write` on all staged .ts files
- **Fix:** No separate formatting commit needed; Prettier config was designed to match existing style so changes were minimal. `.git-blame-ignore-revs` points to Task 1's commit (881221e)
- **Impact:** None -- outcome identical to plan intent

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
DX-01 (ESLint) and DX-02 (Prettier) are fully satisfied. Plan 15-04 (coverage thresholds, startup validation) can proceed. The lint-staged pipeline is ready to enforce code quality on all future commits.

## Self-Check: PASSED
