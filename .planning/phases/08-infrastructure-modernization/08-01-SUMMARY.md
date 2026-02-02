---
phase: 08-infrastructure-modernization
plan: 01
subsystem: build-infrastructure
tags: [node22, env-paths, lts, ci, docker]
dependency_graph:
  requires: []
  provides: [node-22-runtime, env-paths-v4, ci-node-22, docker-node-22]
  affects: [08-02, 08-03]
tech_stack:
  added: [env-paths@4.0.0]
  patterns: [pure-esm-dependencies]
key_files:
  created: [.nvmrc]
  modified: [package.json, package-lock.json, .github/workflows/ci.yml, Dockerfile.test]
decisions:
  - id: INFRA-NODE22
    description: "Set engines >=22 (Node 22 LTS active until Apr 2027)"
    rationale: "Unlocks pure ESM deps, aligns with current LTS"
  - id: INFRA-ENVPATHS4
    description: "Upgrade env-paths v3 to v4 (pure ESM, no API changes)"
    rationale: "Required Node 20+, now satisfied by Node 22 target"
  - id: INFRA-TYPES-NODE22
    description: "Upgrade @types/node from ^18 to ^22"
    rationale: "Match runtime target for accurate type checking"
metrics:
  duration: ~2min
  completed: 2026-02-02
---

# Phase 08 Plan 01: Node 22 Upgrade Summary

**One-liner:** Upgrade Node runtime target to 22 LTS across package.json, CI, Docker; install env-paths v4 (pure ESM).

## What Was Done

### Task 1: Upgrade Node 22 + env-paths v4 in package.json
- Changed `engines.node` from `>=18` to `>=22`
- Upgraded `env-paths` from `^3.0.0` to `^4.0.0` (pure ESM, no API changes)
- Upgraded `@types/node` from `^18.19.4` to `^22.0.0`
- Created `.nvmrc` with `22` for local dev consistency
- Build passes, 138/139 tests pass (1 pre-existing failure in paths.test.js)
- Python tests: pre-existing collection errors in 2 script files (unrelated)
- Commit: `acc339f`

### Task 2: Update CI workflow and Docker to Node 22
- Changed CI `node-version` from `'18'` to `'22'` in both test and audit jobs
- Changed Dockerfile.test base from `node:20-slim` to `node:22-slim`
- YAML validated
- Commit: `564fa0d`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Upgraded @types/node to ^22**
- **Found during:** Task 1
- **Issue:** @types/node was pinned to ^18, would provide inaccurate types for Node 22 runtime
- **Fix:** Updated to ^22.0.0
- **Files modified:** package.json, package-lock.json

## Pre-existing Issues Noted

1. **paths.test.js** (`getRequirementsTxtPath`): Tests for `requirements.txt` which was removed during UV migration. 1 test failure pre-existing.
2. **pytest collection errors**: `scripts/archive/test_tesseract_comparison.py` and `scripts/test_marginalia_detection.py` have import errors. Pre-existing.

## Verification Results

- `npm run build` exits 0
- 138/139 Jest tests pass (1 pre-existing failure)
- `node -e "import('env-paths')..."` works correctly with v4
- No references to Node 18 or 20 in CI/Docker configs
- `grep '">=22"' package.json` confirms engine field

## Next Phase Readiness

Ready for 08-02 (numpy Docker fix) and 08-03 (EAPI gaps). No blockers introduced.
