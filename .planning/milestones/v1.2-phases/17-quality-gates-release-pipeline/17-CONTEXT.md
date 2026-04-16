# Phase 17: Quality Gates & Release Pipeline - Context

**Gathered:** 2026-03-20
**Status:** Ready for research

<domain>
## Phase Boundary

Wire CI quality gates that validate what Phases 15-16 created (linting, packaging, docs, Docker). Add a release workflow for npm publishing. Resolve GitHub Issue #11. After this phase, the project is shippable.

This phase adds CI enforcement and release automation. It does NOT create new tooling (ESLint, Prettier, coverage — Phase 15), documentation (README, API docs — Phase 16), or packaging (files whitelist, Docker — Phase 16). It validates and gates what already exists.

</domain>

<assumptions>
## Working Assumptions

### Architecture
- CI workflow lives in `.github/workflows/ci.yml` (already exists with test-fast, test-full, audit jobs)
- New CI jobs extend the existing workflow or add new workflow files
- npm publish workflow is a separate file (e.g., `.github/workflows/publish.yml`) triggered by version tags
- The MCP initialize handshake for smoke test requires a short-lived server process that responds to JSON-RPC

### Dependencies
- Phase 15 delivered: ESLint, Prettier, lint-staged, coverage thresholds, startup credential validation
- Phase 16 delivered: README with tool list, docs/api.md, CONTRIBUTING.md, CHANGELOG.md, npm `files` whitelist (416KB tarball), Docker build verified
- Existing CI: test-fast (Jest + pytest fast), test-full (all tests), audit (npm audit + pip-audit)

### Sequencing
1. Lint/format CI gate (GATE-01) — add ESLint + Prettier check job
2. Package integrity gate (GATE-02) — add npm pack size/content check
3. Startup smoke test (GATE-03) — boot server, MCP initialize, exit
4. Docker CI gate (GATE-04) — build + health check
5. README tool validation (GATE-05) — script to compare README tool list vs registered tools
6. npm publish workflow (GATE-06) — separate workflow, version tag trigger
7. Issue #11 resolution (GATE-07) — verify setup path, respond to issue

</assumptions>

<decisions>
## Implementation Decisions

### CI Gate Strategy

**Derived from v1.2 deliberation (2026-03-19):**
- All three quality gate layers required: CI regression, package integrity, doc freshness
- Gates should fail PRs, not just warn
- Each gate is a separate CI job for clear failure attribution

### npm Publish Workflow

**Derived from GATE-06 + requirements:**
- Manual trigger (not semantic-release — explicitly out of scope per REQUIREMENTS.md)
- Triggered by version tags (e.g., `v2.0.0`)
- Runs `npm publish` after build + test pass
- Requires `NPM_TOKEN` secret configured in GitHub repo settings

### Issue #11 Resolution

**Derived from GATE-07 + issue content:**
- Issue #11 ("Is this still a working MCP?") shows "server disconnected" in Claude Desktop
- Root cause: likely missing credentials (Phase 15 added clear error messaging for this)
- Resolution: respond to issue with updated setup instructions, link to README install path
- The updated README (Phase 16) + credential validation (Phase 15) already address the underlying problem

### Claude's Discretion

- Exact CI job names and step ordering
- Whether to use a composite action for shared setup steps (checkout, setup-node, setup-uv, npm ci, uv sync)
- Smoke test implementation details (how to boot server, send MCP initialize, verify response, exit)
- README tool validation script approach (grep-based, AST-based, or simple count comparison)
- Whether Docker CI builds on every PR or only push-to-master (GATE-04 says "push to master" but research can recommend)
- npm publish workflow extras (provenance, dry-run on PR, etc.)

</decisions>

<constraints>
## Derived Constraints

### From Codebase Reality
- CI already has 3 jobs: test-fast, test-full, audit — new gates add to this, not replace
- ESLint is at `eslint.config.js` (flat config), Prettier at `.prettierrc` — CI just runs `npx eslint src/` and `npx prettier --check src/`
- npm pack produces 416KB tarball — GATE-02 threshold is 10MB, well within margin
- Docker compose file at `docker/docker-compose.yaml` — GATE-04 runs `docker compose -f docker/docker-compose.yaml build`
- Server entry point is `dist/index.js` — smoke test boots this
- MCP SDK uses JSON-RPC over stdio — smoke test sends `{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.0.0"}},"id":1}` and expects a response
- 13 MCP tools registered in `src/index.ts` via `server.tool()` — README has a tool reference table

### From Prior Decisions
- Coverage thresholds already enforced locally by Jest and pytest (Phase 15) — CI just needs `--coverage` (already in npm test script)
- `prepublishOnly` runs build — npm publish workflow inherits this
- GitHub Issue #11 is OPEN, reporter is `@gizmo66` (based on issue listing)

### From Requirements (Out of Scope)
- semantic-release explicitly rejected in REQUIREMENTS.md — simple tag-triggered publish
- Full Zod 4 migration deferred — MCP SDK depends on Zod 3.25.x
- Multi-platform CI (macOS/Windows) deferred to v1.4+

</constraints>

<questions>
## Open Questions

| Question | Why It Matters | Type | Criticality | What Research Should Investigate |
|----------|----------------|------|-------------|----------------------------------|
| What does an MCP initialize handshake look like over stdio for GATE-03? | Smoke test must send initialize and verify response. Need exact JSON-RPC payload and expected response format | Material | Critical | Check MCP SDK source or docs for initialize handshake format; test locally with `echo '...' \| node dist/index.js` |
| Should lint/format/pack checks run on PRs only, or also on push to master? | GATE-01 says "every PR" but existing CI runs on both push and PR. Consistency matters | Efficient | Low | Check current CI trigger pattern, recommend consistent approach |
| Does the existing CI workflow support LFS checkout for test fixtures? | Tests reference LFS-tracked PDFs. If CI doesn't have `lfs: true`, tests may fail with pointer files instead of real data | Material | Medium | Check if `actions/checkout` in ci.yml uses `lfs: true`, verify test-fast doesn't hit LFS files |
| How to validate README tool list against registered tools programmatically? | GATE-05 requires automated divergence detection. Could be a simple script or a CI step | Formal | Medium | Research approaches: grep README for tool names, grep src/index.ts for server.tool() calls, compare sets |

</questions>

<guardrails>
## Epistemic Guardrails

- **Do not assume MCP initialize works over simple pipe.** The MCP server may buffer or require specific stdio setup. Research must verify the smoke test approach actually works before planning relies on it.
- **Do not assume Docker build works in GitHub Actions.** It was verified locally but CI runners may differ (disk space, layer caching, build time limits). Research should check if there are CI-specific Docker build concerns.
- **Issue #11 resolution is a human interaction, not just code.** The response must be respectful, helpful, and reference the actual setup instructions — not just close the issue.

</guardrails>

<specifics>
## Specific Ideas

**From the v1.2 deliberation:**
- This is the final phase of v1.2. After this, the project is shippable.
- The CHANGELOG has a `[2.0.0]` entry with placeholder date `2026-03-XX` — this phase should finalize the date.

**From GitHub Issue #11:**
- Reporter: "Is this still a working MCP?" with screenshot of "server disconnected"
- The credential validation (Phase 15) now gives a clear error instead of silent disconnect
- The README (Phase 16) now has step-by-step setup instructions
- Response should acknowledge the issue, link to updated docs, and explain the credential requirement

</specifics>

<deferred>
## Deferred Ideas

- Smithery manifest for MCP registry (PKG-F01, v1.4+)
- postinstall script for Python env setup (PKG-F02, v1.4+)
- Multi-platform CI (macOS, Windows) (TEST-F01, v1.4+)
- Coverage trend graphs in CI artifacts (QUAL-F02, v1.4+)
- Per-commit quality dashboards (QUAL-F02, v1.4+)

</deferred>

---

*Phase: 17-quality-gates-release-pipeline*
*Context gathered: 2026-03-20*
