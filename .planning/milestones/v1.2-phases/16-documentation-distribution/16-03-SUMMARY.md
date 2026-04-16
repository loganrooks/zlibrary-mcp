---
phase: 16-documentation-distribution
plan: 03
model: claude-opus-4-6
context_used_pct: 22
subsystem: documentation
tags: [readme, contributing, badges, mermaid, install-paths, rag-output]
requires:
  - phase: 16-documentation-distribution
    provides: "16-01 verified install paths (npm/Docker), 16-02 docs/api.md and CHANGELOG.md to link to"
provides:
  - "README.md with CI/npm/license badges, Mermaid architecture diagram, dual install paths, RAG output format section"
  - "CONTRIBUTING.md with setup, test, code style, PR workflow, and code patterns"
affects: [documentation, distribution, onboarding]
tech-stack:
  added: []
  patterns: [shields-io-badges, mermaid-architecture-diagram]
key-files:
  created:
    - CONTRIBUTING.md
  modified:
    - README.md
key-decisions:
  - "Included npm version badge since package is published (1.0.0 on npm registry)"
  - "Preserved existing FAQ section (addresses real user confusion about EAPI, Node vs UV, project portability)"
  - "Removed 'Current Status' and 'Recent Changes' sections (replaced by badges and CHANGELOG.md)"
patterns-established:
  - "README structure: badges -> quick start -> architecture diagram -> tools -> install paths -> output format -> config -> FAQ -> contributing -> license"
duration: 2min
completed: 2026-03-20
---

# Phase 16 Plan 03: README & CONTRIBUTING.md Summary

**Refreshed README with shields.io badges, Mermaid architecture diagram, and dual install paths; created CONTRIBUTING.md with complete contributor guide**

## Performance
- **Duration:** 2 minutes
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments
- Refreshed README.md (292 lines) with CI, npm version, and MIT license badges at top
- Added Mermaid flowchart diagram showing MCP client -> Node.js -> Python bridge -> EAPI data flow with both stdio and HTTP transport paths
- Documented dual install paths: Option A (local stdio with setup-uv.sh + npm) and Option B (Docker HTTP with docker-compose)
- Added MCP client config examples for Claude Code, Claude Desktop, and RooCode/Cline under both transport modes
- Added RAG output format section explaining file-based output, supported formats, quality detection, and scholarly formatting preservation
- Added configuration table with credential validation note (Phase 15 feature)
- Linked to docs/api.md for full API reference and CONTRIBUTING.md for contributor guide
- Preserved existing FAQ section and license/disclaimer
- Created CONTRIBUTING.md (203 lines) with prerequisites, clone/setup, test commands (Jest + pytest fast/full/e2e), code style (lint-staged, blame-ignore-revs), branch naming, conventional commits, PR process, code patterns, and issue reporting

## Task Commits
1. **Task 1: Refresh README.md with badges, install paths, architecture diagram, and tool overview** - `d64ed2e`
2. **Task 2: Create CONTRIBUTING.md with setup, test, and PR workflow** - `55ac1e8`

## Files Created/Modified
- `README.md` - Refreshed with badges, Mermaid diagram, dual install paths (stdio + Docker), RAG output format, config table, API docs link
- `CONTRIBUTING.md` - New contributor guide with setup, testing, code style, PR workflow, code patterns, issue reporting

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added npm version badge**
- **Found during:** Task 1
- **Issue:** Plan said to check `npm view zlibrary-mcp version` and omit badge if not published. Package is published at 1.0.0.
- **Fix:** Included npm version badge alongside CI and license badges. KB consulted, no relevant entries.
- **Files modified:** README.md
- **Commit:** d64ed2e

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DOCS-01 satisfied: README has badges, usage instructions, output format description
- DOCS-03 satisfied: CONTRIBUTING.md at repo root with complete contributor guide
- DOCS-04 satisfied: Mermaid architecture diagram in README
- DIST-03 satisfied: npm install path documented with step-by-step instructions
- DIST-04 satisfied: Docker install path documented with step-by-step instructions
- Phase 16 (all 3 plans) complete -- ready for Phase 17 (Release & Publish)

## Self-Check: PASSED

- README.md: FOUND (292 lines, >= 150 min)
- CONTRIBUTING.md: FOUND (203 lines, >= 80 min)
- Commit d64ed2e: FOUND
- Commit 55ac1e8: FOUND
