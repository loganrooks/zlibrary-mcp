# Phase 1: Integration Test Harness - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Safety net for detecting Node.js-to-Python bridge breakage across all subsequent phases. Covers integration tests for each MCP tool, a Docker-based E2E test, and BRK-001 investigation. Does NOT include fixing BRK-001, adding new tools, or CI/CD pipeline setup (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Test scope & coverage
- Test each MCP tool individually through the Python bridge (not just a smoke test)
- Two test modes: recorded responses (default) and live API calls (via `--live` flag)
- Live mode performs full downloads to verify end-to-end, including file creation
- Recorded mode verifies bridge invocation and response shape without network calls

### Docker E2E approach
- Z-Library credentials passed via environment variables at runtime (`docker run -e`)
- Dockerfile must support multi-platform builds (amd64 + arm64)
- E2E test starts the MCP server inside Docker and invokes at least one tool

### Failure reporting
- Integration tests block PR merges from day one (required, not advisory)
- On failure: include detailed diagnostics (Python stderr, bridge response, environment info)
- Summary output includes a matrix view showing each tool x test mode with pass/fail status

### BRK-001 investigation
- Reproduce the download+RAG combined workflow bug with a dedicated test
- Full root cause investigation — no time-box, investigate until cause is identified
- Document findings in both ISSUES.md (formal bug report with repro steps + root cause) and inline test comments
- Do NOT fix BRK-001 in this phase — reproduce, investigate, and document only

### Claude's Discretion
- Test framework choice (Jest vs Vitest — evaluate against existing setup)
- Fixture approach for recorded responses (static files vs record/replay)
- Dockerfile scope (test-only vs production-ready)
- Docker orchestration (compose vs script)
- MCP client for E2E (Inspector CLI vs custom test script)
- E2E protocol testing depth
- Docker build strategy (full build vs cached base)
- Test timeouts per test type
- Output format (standard runner vs JUnit XML)
- Matrix summary format (ASCII table vs markdown)
- Bridge health preflight check
- Python environment capture on failure
- BRK-001 format investigation scope

</decisions>

<specifics>
## Specific Ideas

- Matrix view at end of test run showing tool x mode (recorded/live) pass/fail status
- Live mode should actually download a file to verify the full bridge path
- BRK-001 findings should feed back into ISSUES.md with full root cause analysis

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-integration-test-harness*
*Context gathered: 2026-01-29*
