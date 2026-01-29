# Phase 2: Low-Risk Dependency Upgrades - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade all non-SDK dependencies to current versions, resolve security vulnerabilities, and fix specified Python code quality issues. The MCP SDK upgrade is Phase 3 — this phase only touches env-paths, Zod, and other non-SDK packages plus Python audit/cleanup.

</domain>

<decisions>
## Implementation Decisions

### Zod 4 migration strategy
- Full migration to Zod 4 native API — clean break, no legacy patterns or compatibility wrappers
- Stricter validation is acceptable — if Zod 4 rejects inputs previously silently coerced, that's fine
- Let new error format flow through — update the single `safeParse` error formatting site (`src/index.ts:693`) to match Zod 4 API, no normalization layer
- Schemas stay in their current locations — no reorganization during this upgrade
- Type inference changes caught by TypeScript compiler — fix as encountered

### env-paths upgrade
- Just upgrade from v3 (CJS) to v4 (ESM-only) and fix any import issues
- Project already uses ESM, should be straightforward

### Security fix approach
- Vulnerability severity threshold: Claude's discretion (success criteria require zero high/critical)
- Semver ranges (^) for version pinning, not exact pins
- Transitive major version bumps: Claude judges case-by-case based on risk
- Python pip-audit scope: Claude decides based on what pip-audit covers (vendored fork deps included if they show up)

### Python code cleanup
- Bare except at `booklist_tools.py:267`: replace with most specific exception type based on code analysis
- BeautifulSoup parser: use `lxml` for all calls (already a project dependency)
- Same-file opportunistic fixes: when editing a file for required fixes, also fix similar issues in that file
- Opportunistic fix boundary: Claude judges what's safe based on test coverage (similar issues, possibly unused imports/f-strings if risk-free)
- Add targeted tests for exception handling changes to prevent regression
- Improve logging at fixed catch sites: use logging module with appropriate levels (warning/error) and include exception details

### Build artifact cleanup
- `.tsbuildinfo` added to `.gitignore` and untracked — Claude handles

### Claude's Discretion
- Lockfile handling strategy during upgrades
- Vulnerability fix aggressiveness beyond high/critical
- Transitive dependency major bump decisions
- pip-audit scope for vendored fork
- Opportunistic fix boundaries (what's safe to touch)

</decisions>

<specifics>
## Specific Ideas

- Only one Zod error formatting site exists (`src/index.ts:693`) — maps `.error.errors` with `.path` and `.message`. Update to Zod 4 API during migration.
- lxml is already a project dependency, so specifying it as BS4 parser adds no new deps.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-low-risk-dependency-upgrades*
*Context gathered: 2026-01-29*
