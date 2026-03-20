---
phase: 16-documentation-distribution
plan: 01
model: claude-opus-4-6
context_used_pct: 18
subsystem: distribution
tags: [npm, docker, packaging, distribution]
requires:
  - phase: 15-cleanup-dx-foundation
    provides: clean codebase with lint/format/coverage infrastructure
provides:
  - npm files whitelist reducing tarball from 989 files (117MB) to 126 files (416KB)
  - Docker build fix for Alpine musl compatibility (opencv/numpy exclusion)
  - Updated .dockerignore excluding __tests__ and .claude dev artifacts
affects: [package.json, docker/Dockerfile, .dockerignore]
tech-stack:
  added: []
  patterns: [npm-files-whitelist-with-negation, docker-musl-package-exclusion]
key-files:
  created: []
  modified: [package.json, .dockerignore, docker/Dockerfile]
key-decisions:
  - "Added __pycache__/.pyc negation patterns to files array since files field overrides .npmignore"
  - "Excluded opencv-python-headless and numpy from Docker build via --no-install-package (musl incompatible, runtime uses conditional imports)"
  - "Did not exclude src/ or scripts/ from .dockerignore since Dockerfile COPY depends on them for build stage"
duration: 5min
completed: 2026-03-20
---

# Phase 16 Plan 01: npm and Docker Distribution Summary

**npm tarball reduced 99.6% (117MB to 416KB) via files whitelist; Docker build fixed for Alpine musl by excluding opencv/numpy**

## Performance
- **Duration:** 5 minutes
- **Tasks:** 2/2 completed
- **Files modified:** 3

## Accomplishments
- Added `files` whitelist to package.json with negation patterns for `__pycache__`/`.pyc` exclusion
- npm tarball: 989 files (117.4MB) down to 126 files (416KB compressed, 1.5MB unpacked)
- Zero dev artifacts (`__tests__`, `test_files`, `.planning`, `claudedocs`, `__pycache__`) in tarball
- All runtime files included: `dist/`, `lib/`, `zlibrary/`, `pyproject.toml`, `uv.lock`, `setup-uv.sh`
- Docker build succeeds with opencv/numpy exclusion for Alpine musl compatibility
- Docker image verified: contains `dist/index.js`, `lib/python_bridge.py`, `.venv/`, `node_modules/`
- Updated `.dockerignore` to exclude `__tests__/` and `.claude/`

## Task Commits
1. **Task 1: Configure npm files whitelist and verify tarball** - `1e68b82`
2. **Task 2: Verify Docker build and health check** - `4adf54d`

## Files Created/Modified
- `package.json` - Added `files` array with runtime whitelist and `__pycache__`/`.pyc` negation patterns
- `.dockerignore` - Added `__tests__` and `.claude` exclusions for smaller Docker build context
- `docker/Dockerfile` - Added `--no-dev --no-install-package opencv-python-headless --no-install-package numpy` to `uv sync`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] npm files field overrides .npmignore for __pycache__ exclusion**
- **Found during:** Task 1
- **Issue:** The `files` field in package.json overrides `.npmignore`. Even though `.npmignore` had `__pycache__/`, the 70 `.pyc` files from `lib/` subdirectories were included in the tarball.
- **Fix:** Added `!**/__pycache__/` and `!**/*.pyc` negation patterns to the `files` array.
- **Files modified:** `package.json`
- **Commit:** `1e68b82`

**2. [Rule 3 - Blocking] Docker build fails on Alpine: no musl-compatible opencv/numpy wheels**
- **Found during:** Task 2
- **Issue:** `uv sync --frozen` failed in Alpine Docker image because `opencv-python-headless` has no musl-compatible wheels (only manylinux/glibc). Its transitive dependency `numpy` also failed to build from source due to missing C compiler.
- **Fix:** Added `--no-dev --no-install-package opencv-python-headless --no-install-package numpy` to the Dockerfile's `uv sync` command. Runtime code imports cv2 conditionally with graceful fallback, so X-mark detection is simply unavailable in Docker.
- **Files modified:** `docker/Dockerfile`
- **Commit:** `4adf54d`

**3. [Rule 2 - Missing functionality] .dockerignore missing __tests__ and .claude exclusions**
- **Found during:** Task 1
- **Issue:** `.dockerignore` did not exclude `__tests__/` or `.claude/` directories, causing unnecessary files in Docker build context.
- **Fix:** Added both exclusions. Did NOT exclude `src/` or `scripts/` since the Dockerfile COPY commands depend on them during the build stage.
- **Files modified:** `.dockerignore`
- **Commit:** `1e68b82`

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DIST-01 satisfied: npm tarball under 5MB (416KB) with files whitelist, no test/dev artifacts
- DIST-02 satisfied: Docker build succeeds, image contains correct runtime files
- `.dockerignore` updated and verified
- Ready for 16-02 (README/documentation) and 16-03 (quality gates)

## Self-Check: PASSED
