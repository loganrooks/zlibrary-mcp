# Phase 16: Documentation & Distribution - Context

**Gathered:** 2026-03-19
**Status:** Ready for research

<domain>
## Phase Boundary

Create professional public-facing documentation and working distribution paths via both npm and Docker, so external users can install and use the server successfully. No new features or code changes beyond what's needed for packaging and documentation.

This phase produces the docs and packages. Phase 17 wires CI gates to validate them.

</domain>

<assumptions>
## Working Assumptions

### Architecture
- README.md already exists with substantial content (~30 lines of intro, architecture overview, recent changes) — this is a refresh, not a greenfield write
- Docker setup exists and appears functional (`docker/Dockerfile`, `docker/docker-compose.yaml`, `docker/env.example`) — verification needed, not creation
- 13 MCP tools are registered via `server.tool()` in `src/index.ts` — API docs enumerate these
- npm tarball currently packs 984 files (no `files` whitelist) — needs aggressive filtering
- Docker uses SuperGateway for HTTP transport on port 8000 with health endpoint at `/health`

### Dependencies
- Phase 15 complete — ESLint, Prettier, coverage, clean src/ are all in place
- `package.json` already has `"main": "dist/index.js"`, `"type": "module"`, `"bin"`, `"exports"` fields
- `prepublishOnly` script runs `npm run build`
- Docker Dockerfile is multi-stage (builder + runtime) based on node:22-alpine

### Sequencing
1. npm packaging first (`files` whitelist) — determines what ships
2. Docker verification — depends on knowing the final file layout
3. Documentation (README, API docs, CONTRIBUTING, CHANGELOG, architecture diagram) — can reference verified install paths
4. Install path verification — final E2E check that both paths work

### Patterns
- API docs likely belong in `docs/api.md` or inline in README
- CONTRIBUTING.md at repo root (standard convention)
- CHANGELOG.md at repo root (standard convention)
- Mermaid diagram can live in README or a separate `docs/architecture.md` linked from README

</assumptions>

<decisions>
## Implementation Decisions

### README Structure

**Derived from DOCS-01 + existing README:**
- Keep existing architecture overview and recent changes sections
- Add badges at top: CI status, npm version, license
- Add `npx` quick-start usage instructions
- Add output format description (what RAG processing produces)
- Update tool count and feature list to reflect current state (13 tools)

### API Documentation Scope

**Derived from DOCS-02:**
- Document each of the 13 MCP tools
- For each: name, description, parameters (with types), return format, example usage, error cases
- Research should extract tool definitions from `src/index.ts` to determine exact parameter schemas

### CONTRIBUTING.md Scope

**Derived from DOCS-03:**
- Setup instructions (prerequisites, clone, setup-uv.sh, npm install, npm run build)
- Test instructions (npm test, uv run pytest, fast vs full)
- PR workflow (branch naming, conventional commits, lint-staged checks)
- Code patterns (reference .claude/PATTERNS.md concepts but keep standalone)
- Architecture overview (brief, link to diagram)
- Note about `.git-blame-ignore-revs` for Prettier commit

### CHANGELOG Format

**Derived from DOCS-05:**
- Follow Keep a Changelog format (keepachangelog.com)
- Entries for v1.0 (Audit Cleanup & Modernization), v1.1 (Quality & Expansion), v1.2 (Production Readiness)
- v1.0 and v1.1 summaries from milestone archives
- v1.2 will be in-progress until Phase 17 completes

### Claude's Discretion

- Exact README section ordering and heading levels
- Whether API docs go in README or separate file (research should recommend)
- CHANGELOG detail level for v1.0/v1.1 (summary vs per-phase)
- Badge service provider (shields.io, badgen, etc.)
- Whether Mermaid diagram goes inline in README or in docs/
- Exact wording of install instructions

</decisions>

<constraints>
## Derived Constraints

### From Requirements
- npm tarball must be under 5MB with no test files or dev artifacts (DIST-01)
- Docker build path is `docker compose -f docker/docker-compose.yaml build` (DIST-02)
- npm install path: clone -> setup-uv.sh -> npm install -> npm run build -> configure MCP client (DIST-03)
- Docker install path: clone -> docker compose up -> configure MCP client with HTTP transport (DIST-04)

### From Codebase Reality
- `package.json` has no `files` field — currently packs 984 files (everything). Must add whitelist.
- Docker Dockerfile already exists and uses multi-stage build. May already work — needs verification, not creation.
- Docker uses SuperGateway (`command: --port 8000 --host 0.0.0.0 --healthEndpoint /health --stdio "node /app/dist/index.js"`) for HTTP transport
- The `env.example` file exists in `docker/` — Docker install path has credential configuration scaffolding
- `docker-compose.test.yml` exists at repo root for E2E tests (separate from the distribution compose)
- Python files in `lib/` must be included in npm tarball (Python bridge is runtime dependency)
- `zlibrary/` vendored fork must be included in npm tarball
- `.venv/` must NOT be in tarball (user creates via setup-uv.sh)
- `pyproject.toml` and `uv.lock` must be in tarball (for uv sync)

### From Prior Decisions
- Both npm and Docker are first-class distribution channels (v1.2 deliberation)
- Phase 17 will add CI gates to validate packaging and docs — this phase just creates them
- GitHub Issue #11 is a Phase 17 target (reporter's setup path) but this phase's docs should address the underlying UX

### From Phase 15
- ESLint, Prettier, and lint-staged are now configured — CONTRIBUTING.md should reference these
- Startup credential validation exists — README should mention what happens when credentials are missing
- Coverage thresholds are enforced — CONTRIBUTING.md should mention this

</constraints>

<questions>
## Open Questions

| Question | Why It Matters | Type | Criticality | What Research Should Investigate |
|----------|----------------|------|-------------|----------------------------------|
| What files should the npm `files` whitelist include? | DIST-01 requires tarball under 5MB. Currently 984 files. Need to know which dirs/files are runtime-required (dist/, lib/, zlibrary/, pyproject.toml, uv.lock, setup-uv.sh) vs dev-only | Material | Critical | Run `npm pack --dry-run` with candidate whitelist, measure tarball size |
| Does the Docker build currently succeed? | DIST-02 requires working Docker build + health check. The Dockerfile exists but may be stale after Phase 15 changes | Material | Critical | Run `docker compose -f docker/docker-compose.yaml build` and test health endpoint |
| What HTTP transport does Docker use for MCP? | The compose file references SuperGateway but DIST-04 says "HTTP transport" — research should verify what client config looks like for Docker-based MCP | Material | Medium | Check SuperGateway docs, verify MCP client config for HTTP transport |
| Should API docs be inline in README or a separate file? | DOCS-02 requires API docs exist. If inline, README could be very long (13 tools). If separate, discoverability may suffer | Formal | Low | Check conventions in other MCP server repos |
| What v1.0 and v1.1 changes should appear in CHANGELOG? | DOCS-05 requires entries but those milestones had 43 plans across 12 phases — how much detail? | Efficient | Low | Check milestone archive summaries for high-level bullet points |

</questions>

<specifics>
## Specific Ideas

**From the deliberation (2026-03-19):**
- GitHub Issue #11 is a real user who got "server disconnected" — the README install instructions should be clear enough that this doesn't happen
- The credential validation added in Phase 15 is the first line of defense, but README should also explain the env var setup

**From codebase:**
- `docker/README.md` already exists — may contain Docker-specific docs to consolidate
- The project has extensive internal docs in `.claude/` — CONTRIBUTING.md should reference these for deep dives but remain standalone for basic contributions

</specifics>

<deferred>
## Deferred Ideas

- Smithery manifest for MCP registry integration (PKG-F01, v1.4+)
- postinstall script for automatic Python environment setup (PKG-F02, v1.4+)
- Multi-platform CI testing — macOS, Windows via WSL (TEST-F01, v1.4+)
- Auto-generated TypeDoc HTML (explicitly out of scope per requirements — hand-written API docs preferred)

</deferred>

---

*Phase: 16-documentation-distribution*
*Context gathered: 2026-03-19*
