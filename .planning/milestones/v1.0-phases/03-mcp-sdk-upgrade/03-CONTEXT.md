# Phase 3: MCP SDK Upgrade - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the MCP server framework from SDK 1.8.0 to latest stable, maintaining protocol compatibility with MCP clients (Claude Desktop and Claude Code). Also resolves the remaining npm audit high-severity vulnerability from the old SDK. No new tool capabilities or features.

</domain>

<decisions>
## Implementation Decisions

### Migration approach
- Big-bang upgrade to latest stable SDK in one shot (no intermediate versions)
- Adopt the new recommended server class (e.g., McpServer) rather than using legacy Server class with compat imports
- Target the latest stable release (not pinned to 1.25.x — whatever is current at execution time)
- If Node 20+ is required by the new SDK, bump the Node requirement (Node 18 EOL was April 2025)
- Document any response format changes that occur during the upgrade

### Compatibility verification
- Run all existing tests (Jest + Pytest + integration + Docker E2E) as automated verification
- Manual verification also required: start server in Claude Desktop and Claude Code, invoke a tool
- User will perform manual verification themselves (knows the steps)
- Plan should include Claude Desktop MCP server config snippet for setup
- All 14 tools must work — no tool is expendable, all equally critical
- Run Python tests too even though they shouldn't be affected by the SDK change

### Fallback strategy
- No hard deadline — quality over speed
- Document any response format changes for downstream awareness
- No regressions acceptable on any tool

### Claude's Discretion
- Tool registration pattern: adopt new SDK idiom vs minimal adaptation (based on how different the API is)
- Zod version resolution: align to SDK's needs or keep current (based on actual compatibility)
- env-paths v4 upgrade: bundle into this phase if Node bump happens and it's trivial, or defer
- Docker/CI Node version updates: handle in same phase or separate step (based on dependency chain)
- E2E test client SDK version: upgrade together or keep old client (based on test reliability needs)
- Test adaptation: allow test changes vs use shims (balance stability vs clean code)
- Fixture regeneration: re-record if needed vs keep stable (based on what actually changes)
- New tests: add protocol-level tests only if coverage gaps are found
- OOM concern: include as a build verification check but don't optimize preemptively
- Fallback on blocker: try next-latest stable vs stop and reassess (pragmatic approach)
- Handler extraction: only if the new SDK naturally supports modular registration

</decisions>

<specifics>
## Specific Ideas

- User uses both Claude Desktop and Claude Code as MCP clients — both need verification
- Claude Desktop is not currently configured for this server — setup instructions needed in plan
- The migration surface is small: only `src/index.ts` imports from `@modelcontextprotocol/sdk` (Server, StdioServerTransport, type schemas)
- STATE.md notes this is HIGH risk due to "Server class migration decision" — research should investigate the actual API diff

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-mcp-sdk-upgrade*
*Context gathered: 2026-01-29*
