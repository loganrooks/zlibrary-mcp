---
phase: 17-quality-gates-release-pipeline
plan: 01
model: claude-sonnet-4-6
context_used_pct: 22
subsystem: ci-cd
tags: github-actions, ci, lint, eslint, prettier, docker, mcp, smoke-test
requires:
  - phase: 15-code-quality-toolchain
    provides: ESLint, Prettier, lint-staged configured in package.json
  - phase: 16-documentation-distribution
    provides: README with 13-tool table, Dockerfile under docker/
provides:
  - Reusable composite setup action (.github/actions/setup/action.yml)
  - Shell script validating tool list parity between source and README
  - 5 CI quality gate jobs (lint, pack-check, smoke-test, docker, docs-check)
affects: ci, quality-gates, release-pipeline
tech-stack:
  added: docker/setup-buildx-action@v3
  patterns: composite-action, ci-gate-per-job, smoke-test-via-stdin-pipe
key-files:
  created:
    - .github/actions/setup/action.yml
    - scripts/validate-readme-tools.sh
  modified:
    - .github/workflows/ci.yml
key-decisions:
  - "Composite action includes checkout step — callers use 'uses: ./.github/actions/setup' directly without a separate checkout step"
  - "docs-check scopes README extraction to 'Available MCP Tools' section via sed range to avoid spurious matches from config-var tables"
  - "smoke-test uses dummy credentials (ci@test.com / ci-test-password) to pass startup validation without real Z-Library access"
  - "docker job restricted to push-to-master via 'if: github.event_name == push' to avoid slow builds on every PR"
patterns-established:
  - "CI gate per job: each quality check is a separate named job for clear failure attribution"
  - "Reusable composite action: shared setup steps extracted to .github/actions/setup to eliminate duplication"
duration: 3min
completed: 2026-03-20
---

# Phase 17 Plan 01: Quality Gate Jobs Summary

**5 CI quality gate jobs added (lint, pack-check, smoke-test, docker, docs-check) using a reusable composite setup action and a tool-validation shell script.**

## Performance
- **Duration:** 3 minutes
- **Tasks:** 3 completed
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- Created reusable composite action at `.github/actions/setup/action.yml` that encapsulates checkout, Node.js 22, UV, npm ci, uv sync, and optional build — eliminating duplication across 5 new CI jobs
- Created `scripts/validate-readme-tools.sh` that extracts 13 tool names from `server.tool()` calls in `src/index.ts` and compares against the README Available MCP Tools section; exits 0 on match, exits 1 with diff on divergence
- Added 5 new CI gate jobs to `ci.yml`: lint (ESLint + Prettier), pack-check (tarball under 10MB, no excluded files), docs-check (tool list validation), smoke-test (MCP JSON-RPC initialize handshake), docker (image build on push-to-master)

## Task Commits
1. **Task 1: Composite action and validation script** - `bd5b0d2`
2. **Task 2: lint, pack-check, docs-check jobs** - `34fb773`
3. **Task 3: smoke-test and docker jobs** - `489ce67`

## Files Created/Modified
- `.github/actions/setup/action.yml` - Reusable composite action with checkout, node 22, uv, npm ci, uv sync, conditional build
- `scripts/validate-readme-tools.sh` - Shell script comparing tool names in src/index.ts vs README.md Available MCP Tools section
- `.github/workflows/ci.yml` - Extended from 3 jobs to 8 jobs; added lint, pack-check, docs-check, smoke-test, docker gates

## Decisions & Deviations

No deviations from plan.

Key decisions during execution:
- Composite action's first step is `actions/checkout@v4` — jobs reference the action directly without a separate checkout step, as specified in the plan
- README tool extraction uses `sed -n '/## Available MCP Tools/,/^## /p'` to scope to that section only, preventing false positives from config-var tables (which would have matched 22 rows instead of 13)
- pack-check uses a multi-step inline shell script to pack, check size, scan for excluded patterns, then clean up — all in one `run:` block for atomicity

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Phase 17 Plan 02 (release tagging and publish) can proceed. The CI gates established here will automatically validate every future PR and push to master.
