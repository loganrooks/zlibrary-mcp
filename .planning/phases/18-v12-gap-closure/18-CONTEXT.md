# Phase 18: v1.2 Gap Closure - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Close tech debt items identified by the v1.2 milestone audit so that test-full CI is green and documentation is accurate. No new features, no architectural changes — strictly fixing broken tests, loosening flaky thresholds, and correcting stale docs.

Source: `.planning/v1.2-MILESTONE-AUDIT.md` (12 items identified, 6 in scope for this phase)

</domain>

<decisions>
## Implementation Decisions

### Footnote test fixes (ISSUE-GT-001)
- Fix the **test code**, not the ground truth data — tests are using pre-v3 keys (expected_output, marker_context, content) that were renamed in the v3 schema migration
- Update test assertions in test_real_footnotes.py and test_inline_footnotes.py to use correct v3 schema accessors
- Validate that the ground truth JSON files themselves are valid v3 (Phase 14 validation test should already confirm this)

### Performance test thresholds (ISSUE-PERF-001)
- **Loosen thresholds** rather than excluding tests — keeps validation meaningful on CI
- Use multipliers appropriate for CI runners (2-3x local thresholds) rather than removing timing assertions entirely
- Affected tests: test_garbled_performance.py (2 tests), test_superscript_detection.py::TestPerformance (1 test)

### Documentation fixes
- CHANGELOG.md: Fix footer comparison links from v1.0.0/v1.1.0 to v1.0/v1.1 (matching actual GitHub tags)
- ISSUES.md: Mark ISSUE-DOCKER-001 as resolved (fixed by Phase 16-01)
- QUICKSTART.md: Delete entirely (superseded by README Quick Start section from Phase 16-03)
- CONTRIBUTING.md: Add Docker prerequisite note to E2E testing section

### Claude's Discretion
- Exact CI threshold multipliers for performance tests (2x, 3x, or environment-detected)
- Whether to add a CI environment variable check for conditional thresholds vs static loosening
- Order of operations across the fixes (independent items, can be batched freely)

</decisions>

<specifics>
## Specific Ideas

- The 4 footnote tests fail with `KeyError: 'expected_output'`, `'marker_context'`, `'content'` — these are the exact keys to trace in the v3 ground truth schema
- Performance tests pass locally but fail on GitHub Actions runners — the fix must account for runner variance, not just local timing
- CHANGELOG links currently point to `v1.0.0...v1.1.0` but actual tags are `v1.0...v1.1`

</specifics>

<deferred>
## Deferred Ideas

From audit (not in Phase 18 scope):
- Vendored test file (zlibrary/src/test.py, 40KB) in npm tarball — audit says "acceptable", non-blocking
- npm registry install path not documented in README — could go in v1.3 docs refresh
- NPM_TOKEN secret not configured in GitHub repo settings — manual ops task, not code
- CI audit job uses `|| true` (informational-only) — acceptable for now, tighten in v1.3
- npm registry install path documentation — future README update

</deferred>

---

*Phase: 18-v12-gap-closure*
*Context gathered: 2026-03-20*
