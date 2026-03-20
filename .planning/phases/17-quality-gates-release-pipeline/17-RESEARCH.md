# Phase 17: Quality Gates & Release Pipeline - Research

**Researched:** 2026-03-20
**Domain:** CI/CD, GitHub Actions, npm publishing, MCP protocol smoke testing
**Confidence:** HIGH

## Summary

Phase 17 wires CI quality gates that validate the tooling and packaging established in Phases 15-16, adds a release workflow for npm publishing, and resolves GitHub Issue #11. The technical domain is well-understood: GitHub Actions YAML workflows, shell-based validation scripts, and the MCP JSON-RPC initialize handshake over stdio.

The existing CI (`ci.yml`) already runs on push/PR to master with three jobs: `test-fast`, `test-full`, `audit`. New gates add to this workflow as additional jobs. The MCP smoke test is the most technically novel requirement -- it requires piping a JSON-RPC initialize request to the server via stdin and validating the response, which the MCP specification defines precisely. The npm publish workflow should use trusted publishing with OIDC (now GA since July 2025), which is more secure than long-lived NPM_TOKEN secrets.

The README currently lists exactly 13 tools matching the 13 `server.tool()` registrations in `src/index.ts`. GATE-05 needs a validation script that extracts tool names from both sources and compares them. An important finding: LFS-tracked test PDFs exist in the repo and the current CI checkout does NOT use `lfs: true`, but the fast test suite already excludes tests that reference these files via `-m "not slow and not integration"`, so this is not a blocker.

**Primary recommendation:** Add 4-5 new CI jobs to the existing workflow for lint/format, pack validation, smoke test, and Docker build; create a separate `publish.yml` workflow with npm trusted publishing via OIDC; write a shell script for README tool validation.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### CI Gate Strategy
- All three quality gate layers required: CI regression, package integrity, doc freshness
- Gates should fail PRs, not just warn
- Each gate is a separate CI job for clear failure attribution

#### npm Publish Workflow
- Manual trigger (not semantic-release -- explicitly out of scope per REQUIREMENTS.md)
- Triggered by version tags (e.g., `v2.0.0`)
- Runs `npm publish` after build + test pass
- Requires `NPM_TOKEN` secret configured in GitHub repo settings

#### Issue #11 Resolution
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

### Deferred Ideas (OUT OF SCOPE)

- Smithery manifest for MCP registry (PKG-F01, v1.4+)
- postinstall script for Python env setup (PKG-F02, v1.4+)
- Multi-platform CI (macOS, Windows) (TEST-F01, v1.4+)
- Coverage trend graphs in CI artifacts (QUAL-F02, v1.4+)
- Per-commit quality dashboards (QUAL-F02, v1.4+)

</user_constraints>

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| GitHub Actions | N/A | CI/CD platform | Already in use; `ci.yml` exists with 3 jobs |
| `actions/checkout` | v4 | Git checkout in CI | Already used in existing workflow |
| `actions/setup-node` | v4 | Node.js 22 setup | Already used in existing workflow |
| `astral-sh/setup-uv` | v4 | UV Python env setup | Already used in existing workflow |
| ESLint | ^10.0.3 | Linting TypeScript | Already installed as devDependency |
| Prettier | ^3.8.1 | Code formatting | Already installed as devDependency |
| npm CLI | >= 11.5.1 | Package publishing with provenance | Required for trusted publishing OIDC |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `docker/setup-buildx-action` | v3 | Docker buildx for CI builds | GATE-04 Docker build job |
| `docker compose` | v2 | Multi-container orchestration | Docker health check validation |
| `jq` | Pre-installed on ubuntu-latest | JSON parsing in shell | Smoke test response validation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| npm trusted publishing (OIDC) | NPM_TOKEN secret | CONTEXT.md specifies NPM_TOKEN; trusted publishing is more secure but requires npm >= 11.5.1 and npmjs.com config. **Recommend offering both options in the workflow.** |
| Composite action for setup | Copy/paste setup steps | Composite action reduces duplication across 6+ jobs but adds indirection. **Recommend composite action.** |
| grep-based tool validation | AST parsing of TypeScript | Grep is simpler, sufficient for current codebase (all registrations are `server.tool('name_here',`). AST parsing is overkill. |

**Installation:**
No new npm packages needed. All tooling already exists in devDependencies or comes pre-installed on GitHub Actions runners.

## Architecture Patterns

### Recommended CI Workflow Structure

```
.github/
  workflows/
    ci.yml                  # Existing + new gate jobs
    publish.yml             # New: npm publish on version tags
  actions/
    setup/
      action.yml            # New: composite action for shared setup
```

### Pattern 1: Composite Action for Shared Setup

**What:** Extract the repeated checkout + setup-node + setup-uv + npm ci + uv sync steps into a reusable composite action at `.github/actions/setup/action.yml`.
**When to use:** When 5+ jobs share identical setup steps (this CI will have 6-8 jobs).
**Example:**
```yaml
# .github/actions/setup/action.yml
# Source: https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action
name: 'Project Setup'
description: 'Checkout, install Node.js, UV, and dependencies'
inputs:
  node-version:
    description: 'Node.js version'
    default: '22'
  build:
    description: 'Run npm build after install'
    default: 'true'
runs:
  using: 'composite'
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
    - uses: astral-sh/setup-uv@v4
    - run: npm ci
      shell: bash
    - run: uv sync
      shell: bash
    - run: npm run build
      shell: bash
      if: inputs.build == 'true'
```

### Pattern 2: MCP Smoke Test via Stdio Pipe

**What:** Boot the MCP server, send an initialize JSON-RPC request via stdin, validate the response contains expected fields, then send `initialized` notification and close stdin.
**When to use:** GATE-03 -- verifying the server boots, completes the MCP handshake, and exits cleanly.
**Example:**
```bash
# Source: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
# Send initialize request + initialized notification, then close stdin
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"ci-smoke-test","version":"0.0.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  | timeout 15 node dist/index.js 2>/dev/null \
  | head -1 \
  | jq -e '.result.protocolVersion and .result.serverInfo.name == "zlibrary-mcp"'
```

**Critical detail:** The server validates credentials on startup. For the smoke test in CI, we must either:
1. Set dummy `ZLIBRARY_EMAIL` and `ZLIBRARY_PASSWORD` env vars (server validates presence, not correctness, at startup), OR
2. Use the `testing` mode if exported (the `start()` function accepts `{ testing: true }` to skip credential validation).

Option 1 is simpler for CI -- set dummy env vars since we only need to verify the MCP handshake, not actual Z-Library API calls. The `validateCredentials()` function in `src/index.ts` checks for non-empty strings only.

### Pattern 3: README Tool Validation Script

**What:** Shell script that extracts tool names from `src/index.ts` and `README.md`, compares them as sets, and exits non-zero if they diverge.
**When to use:** GATE-05 CI job.
**Example:**
```bash
#!/usr/bin/env bash
# scripts/validate-readme-tools.sh
set -euo pipefail

# Extract tool names from server.tool() registrations in source
SRC_TOOLS=$(grep -oP "server\.tool\(\s*'\\K[^']+" src/index.ts | sort)

# Extract tool names from README table rows (backtick-wrapped)
README_TOOLS=$(grep -oP '^\| `\K[a-z_]+(?=`)' README.md | sort)

# Compare
DIFF=$(diff <(echo "$SRC_TOOLS") <(echo "$README_TOOLS") || true)

if [ -n "$DIFF" ]; then
  echo "ERROR: README tool list diverges from registered tools"
  echo "$DIFF"
  exit 1
fi

echo "OK: README lists all $(echo "$SRC_TOOLS" | wc -l) registered tools"
```

### Pattern 4: npm Publish Workflow with Tag Trigger

**What:** Separate workflow file triggered by version tags that builds, tests, and publishes to npm.
**When to use:** GATE-06.
**Example:**
```yaml
# .github/workflows/publish.yml
# Source: https://docs.npmjs.com/trusted-publishers/
name: Publish to npm

on:
  push:
    tags: ['v*']
  workflow_dispatch:

permissions:
  id-token: write  # Required for npm trusted publishing (OIDC)
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          registry-url: 'https://registry.npmjs.org'
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm run build
      - run: npm test
      - run: npm publish --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

**Note on auth strategy:** The CONTEXT.md specifies `NPM_TOKEN` secret. The workflow above supports both:
- **With NPM_TOKEN secret:** Traditional token-based auth (works immediately).
- **With trusted publishing configured on npmjs.com:** OIDC-based auth; the `--provenance` flag attaches provenance attestation. Requires npm >= 11.5.1 and trusted publisher config at `npmjs.com/package/zlibrary-mcp/access`.

### Anti-Patterns to Avoid

- **Monolithic CI job:** Don't put all gates in a single job. Each gate as a separate job gives clear failure attribution (locked decision).
- **Skipping `npm ci` for `npm install`:** CI must use `npm ci` for reproducible, clean installs.
- **Using `actions/checkout` without `lfs: true` for test-full:** The `test-full` job runs all tests including those referencing LFS-tracked PDFs. Add `lfs: true` to the checkout step for `test-full` (but NOT needed for fast tests or gate jobs).
- **Hardcoding tool count instead of comparing sets:** GATE-05 should compare the actual tool name sets, not just counts. A renamed tool would pass a count check but fail a set comparison.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Docker layer caching in CI | Custom cache management | `docker/setup-buildx-action@v3` with `docker/build-push-action@v5` and GHA cache | Docker's official actions handle cache invalidation, multi-stage builds, and `mode=max` for intermediate layers |
| npm provenance attestation | Manual SLSA signing | `npm publish --provenance` with `id-token: write` permission | npm handles OIDC token exchange and Sigstore signing automatically |
| CI setup deduplication | Shell scripts sourced across jobs | GitHub Actions composite action | Native Actions feature, version-controlled, documented inputs/outputs |
| JSON-RPC response validation | Custom parser | `jq` (pre-installed on ubuntu-latest) | Handles edge cases in JSON parsing, `-e` flag exits non-zero on null/false |

**Key insight:** GitHub Actions has mature built-in mechanisms for every concern in this phase. The main risk is over-engineering (writing custom scripts for problems that Actions already solves) or under-engineering (copy-pasting setup steps across 6+ jobs).

## Common Pitfalls

### Pitfall 1: MCP Server Hangs in CI (No stdin EOF)

**What goes wrong:** The MCP server uses `StdioServerTransport` which reads from stdin indefinitely. If the smoke test doesn't close stdin, the server never exits, and the CI step times out.
**Why it happens:** Stdio-based servers wait for the client to close the input stream (per MCP spec shutdown semantics).
**How to avoid:** Use `echo '...' | timeout 15 node dist/index.js` -- the pipe closes stdin after echo completes, and `timeout` enforces a hard deadline.
**Warning signs:** CI job runs for the full step timeout (6+ minutes by default).

### Pitfall 2: Credential Validation Blocks Smoke Test

**What goes wrong:** The server's `validateCredentials()` function calls `process.exit(1)` if `ZLIBRARY_EMAIL` or `ZLIBRARY_PASSWORD` are missing, preventing the MCP handshake from ever starting.
**Why it happens:** Phase 15 added startup credential validation (correct behavior for production, problematic for CI smoke test).
**How to avoid:** Set dummy env vars in the smoke test step: `env: { ZLIBRARY_EMAIL: "ci@test.com", ZLIBRARY_PASSWORD: "ci-test-password" }`. The validation only checks for non-empty strings, not actual credential validity.
**Warning signs:** Smoke test exits with code 1 before any JSON-RPC output appears.

### Pitfall 3: Docker Build Fails on GitHub Actions Runners

**What goes wrong:** The multi-stage Docker build (node:22-alpine + SuperGateway) may fail due to disk space or network issues when pulling base images.
**Why it happens:** GitHub Actions runners have ~14GB free disk space. The Docker build involves downloading node:22-alpine (~180MB), the SuperGateway image, and installing UV + npm dependencies inside the container.
**How to avoid:** Use `docker/setup-buildx-action` with GHA cache backend for layer caching. This caches intermediate layers so subsequent builds only rebuild changed layers.
**Warning signs:** Build step takes > 5 minutes or fails with "no space left on device".

### Pitfall 4: npm publish --provenance Requires npm >= 11.5.1

**What goes wrong:** The `--provenance` flag silently does nothing or errors on older npm versions.
**Why it happens:** Node.js 22 ships with npm 10.x by default; trusted publishing needs npm 11.5.1+.
**How to avoid:** Add `npm install -g npm@latest` step before publishing, or verify `npm --version` in CI.
**Warning signs:** Published package shows no provenance badge on npmjs.com.

### Pitfall 5: Composite Action Path Resolution

**What goes wrong:** Referencing `.github/actions/setup` with `uses: ./.github/actions/setup` fails if the path is wrong.
**Why it happens:** Composite actions referenced from the same repo must use the `./` prefix and the exact directory path containing `action.yml`.
**How to avoid:** Always verify the directory structure: `.github/actions/setup/action.yml` must exist at that exact path.
**Warning signs:** "Can't find 'action.yml'" error in CI logs.

### Pitfall 6: LFS Files Not Checked Out for Full Test Suite

**What goes wrong:** `test-full` job runs all pytest tests including those that reference LFS-tracked PDFs, but `actions/checkout@v4` does not fetch LFS files by default.
**Why it happens:** Git LFS requires explicit `lfs: true` parameter on checkout action.
**How to avoid:** Add `lfs: true` to the checkout step in the `test-full` job. NOT needed for `test-fast` (which excludes slow/integration tests) or the new gate jobs (which don't run tests against PDFs).
**Warning signs:** Tests fail with "git-lfs filter-process: git-lfs: not found" or receive pointer files instead of real PDFs.

## Code Examples

Verified patterns from official sources:

### GATE-01: ESLint + Prettier CI Check

```yaml
# Source: existing eslint.config.js (flat config) and .prettierrc
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: ./.github/actions/setup
      with:
        build: 'false'  # Linting doesn't need build
    - run: npx eslint src/
    - run: npx prettier --check src/
```

Note: Prettier's `--check` flag exits non-zero on format violations without modifying files. The `.prettierignore` already excludes dist/, node_modules/, zlibrary/, lib/, etc.

### GATE-02: npm pack Size and Content Validation

```yaml
# Source: npm CLI documentation
pack-check:
  runs-on: ubuntu-latest
  steps:
    - uses: ./.github/actions/setup
    - name: Check tarball size
      run: |
        npm pack --dry-run 2>&1 | tee pack-output.txt
        SIZE=$(grep "package size" pack-output.txt | grep -oP '[\d.]+\s*[kMG]B' | head -1)
        echo "Package size: $SIZE"
        # Extract numeric KB value for comparison
        SIZE_BYTES=$(npm pack 2>/dev/null | xargs -I{} stat --format="%s" {} 2>/dev/null || echo "0")
        if [ "$SIZE_BYTES" -gt 10485760 ]; then
          echo "ERROR: Tarball exceeds 10MB ($SIZE_BYTES bytes)"
          exit 1
        fi
    - name: Check excluded patterns
      run: |
        npm pack --dry-run 2>&1 | grep -v "^npm notice" > /dev/null
        # Verify no unexpected files in tarball
        TARBALL=$(npm pack 2>/dev/null)
        tar tzf "$TARBALL" | grep -E '\.(env|log|test\.|spec\.)' && {
          echo "ERROR: Tarball contains excluded patterns"
          rm -f "$TARBALL"
          exit 1
        } || true
        rm -f "$TARBALL"
```

Current tarball: 416.8 KB (well under 10MB threshold).

### GATE-03: MCP Initialize Smoke Test

```bash
# Source: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
# The MCP initialize request per spec version 2025-11-25
INIT_REQUEST='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"ci-smoke-test","version":"0.0.0"}}}'
INIT_NOTIFICATION='{"jsonrpc":"2.0","method":"notifications/initialized"}'

# Send request + notification, close stdin, capture first line of stdout
RESPONSE=$(printf '%s\n%s\n' "$INIT_REQUEST" "$INIT_NOTIFICATION" \
  | timeout 15 node dist/index.js 2>/dev/null \
  | head -1)

# Validate response structure
echo "$RESPONSE" | jq -e '
  .jsonrpc == "2.0" and
  .id == 1 and
  .result.protocolVersion != null and
  .result.serverInfo.name == "zlibrary-mcp" and
  .result.capabilities.tools != null
'
```

**Protocol version note:** The MCP spec currently at `2025-11-25`. The `@modelcontextprotocol/sdk` version `^1.25.3` installed in this project supports this protocol version. The server responds with its supported version via capability negotiation.

### GATE-04: Docker Build + Health Check

```yaml
# Source: docker/docker-compose.yaml (existing healthcheck definition)
docker:
  runs-on: ubuntu-latest
  if: github.event_name == 'push'  # Only on push to master, not PRs
  steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-buildx-action@v3
    - name: Build Docker image
      run: docker build -t zlibrary-mcp:ci -f docker/Dockerfile .
    - name: Verify image runs
      run: |
        docker run --rm zlibrary-mcp:ci node -e "console.log('OK')"
```

**Recommendation:** Run Docker build only on push to master (not PRs) since it's slow (~2-5 min) and Phase 16's `docker-compose.yaml` healthcheck uses SuperGateway's `/health` endpoint which requires Z-Library credentials. A basic "image builds and node works" check is sufficient for CI.

### GATE-05: README Tool Validation

```bash
#!/usr/bin/env bash
# scripts/validate-readme-tools.sh
set -euo pipefail

# Extract tool names from server.tool() calls in source
SRC_TOOLS=$(grep -oP "server\.tool\(\s*['\"]\\K[^'\"]+" src/index.ts | sort)

# Extract tool names from README backtick-wrapped entries in table rows
README_TOOLS=$(grep -oP '^\| `\K[a-z_]+(?=`)' README.md | sort)

SRC_COUNT=$(echo "$SRC_TOOLS" | wc -l)
README_COUNT=$(echo "$README_TOOLS" | wc -l)

echo "Source tools ($SRC_COUNT):"
echo "$SRC_TOOLS"
echo ""
echo "README tools ($README_COUNT):"
echo "$README_TOOLS"
echo ""

# Compare sets
DIFF=$(diff <(echo "$SRC_TOOLS") <(echo "$README_TOOLS") || true)

if [ -n "$DIFF" ]; then
  echo "FAIL: README tool list does not match registered tools"
  echo ""
  echo "Diff (< = in source only, > = in README only):"
  echo "$DIFF"
  exit 1
fi

echo "PASS: All $SRC_COUNT tools documented in README"
```

### GATE-06: Publish Workflow

```yaml
# .github/workflows/publish.yml
name: Publish to npm

on:
  push:
    tags: ['v*']
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: npm  # Optional: for deployment protection rules
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          registry-url: 'https://registry.npmjs.org'
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm run build
      - run: npm test
      - name: Upgrade npm for provenance support
        run: npm install -g npm@latest
      - name: Publish with provenance
        run: npm publish --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### GATE-07: Issue #11 Response Template

```markdown
Hi @Torrchy, thanks for reporting this!

The "server disconnected" error happens when the MCP server can't start --
most commonly because Z-Library credentials aren't configured. We've recently
improved the error messaging (v2.0.0) so the server now gives a clear,
actionable message instead of silently disconnecting.

**To fix this:**

1. Make sure you have a Z-Library account
2. Add your credentials to your MCP client config:

\```json
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/path/to/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "your-email@example.com",
        "ZLIBRARY_PASSWORD": "your-password"
      }
    }
  }
}
\```

See the updated [README](https://github.com/loganrooks/zlibrary-mcp#quick-start)
for full setup instructions.

If you're still seeing issues after adding credentials, please let us know and
we'll help debug further!
```

**Note:** CONTEXT.md listed the reporter as `@gizmo66`, but the actual Issue #11 reporter is `@Torrchy` (confirmed via GitHub API).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Long-lived NPM_TOKEN | npm trusted publishing (OIDC) | July 2025 (GA) | More secure -- short-lived tokens, no secret rotation needed. Requires npm >= 11.5.1. |
| Manual `npm publish` | CI-triggered publish on version tags | Standard practice | Reproducible releases, provenance attestation, no local publish risk |
| Single monolithic CI job | Separate jobs per concern | GitHub Actions best practice | Clear failure attribution, parallel execution, faster feedback |
| `docker build` in CI | `docker/setup-buildx-action` with GHA cache | 2023+ | Layer caching reduces build times by up to 90% on subsequent runs |
| MCP spec `2024-11-05` | MCP spec `2025-11-25` | Nov 2025 | Adds tasks, elicitation, icons. Initialize handshake format unchanged but capabilities expanded. |

**Deprecated/outdated:**
- NPM automation tokens without provenance: Still work but npm will increasingly push toward trusted publishing. Support both for now.
- `docker build` without buildx: Works but misses caching opportunities in CI.

## Open Questions

### Resolved

- **MCP initialize handshake format:** The MCP specification (2025-11-25) defines the exact JSON-RPC payloads. Client sends `initialize` request with `protocolVersion`, `capabilities`, and `clientInfo`; server responds with `protocolVersion`, `capabilities`, and `serverInfo`; client sends `notifications/initialized`. See Code Examples GATE-03.
- **Should lint/format run on PRs only or also push?** Current CI triggers on both push and PR. For consistency, new gate jobs should follow the same pattern. Lint/format/pack/smoke should run on both. Docker build should run on push only (it's slow).
- **LFS checkout concern:** The `test-fast` job uses `-m "not slow and not integration"` which excludes tests that reference LFS-tracked PDFs. New gate jobs don't run those tests either. Only `test-full` needs `lfs: true` -- and should get it added (not a Phase 17 requirement but a good improvement).
- **README vs source tool count:** Both currently show exactly 13 tools. The validation script should compare by name set, not just count.
- **Issue #11 reporter:** CONTEXT.md assumed `@gizmo66` but actual reporter is `@Torrchy` (user ID 147045457). Issue has 0 comments, is still open, created 2026-02-27.

### Genuine Gaps

| Question | Criticality | Recommendation |
|----------|-------------|----------------|
| Does `timeout` + pipe correctly handle MCP server shutdown on GitHub Actions runners? | Medium | Test locally first with `echo '...' \| timeout 15 node dist/index.js` before committing to CI. Accept risk -- if the approach doesn't work, fall back to a Node.js script that spawns the server as a child process. |
| Does the server emit non-JSON output to stdout that would break `jq` parsing? | Medium | The server uses `console.log()` for debug messages -- but these go to stderr (stdout is reserved for JSON-RPC in MCP stdio transport). Verify by checking `StdioServerTransport` behavior. Accept risk -- add `2>/dev/null` to suppress stderr. |
| Will npm >= 11.5.1 be available via `npm install -g npm@latest` on actions/setup-node? | Low | `actions/setup-node@v4` installs Node 22 with npm 10.x. Running `npm install -g npm@latest` upgrades to 11.x+. This is a standard CI pattern. Accept risk. |

### Still Open

- Whether the SuperGateway base image `ghcr.io/supercorp-ai/supergateway:3.4.3` is stable enough for CI builds (it's a third-party image). If it becomes unavailable, Docker builds will break. This is a pre-existing concern, not introduced by Phase 17.

## Sources

### Primary (HIGH confidence)
- [MCP Specification 2025-11-25 - Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) - Initialize handshake exact format, shutdown semantics
- [MCP Specification 2025-11-25 - Base Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic) - JSON-RPC message format
- Existing codebase: `src/index.ts` (13 `server.tool()` registrations), `eslint.config.js`, `.prettierrc`, `docker/Dockerfile`, `docker/docker-compose.yaml`, `.github/workflows/ci.yml`
- `package.json` - Current dependencies, scripts, version 2.0.0
- GitHub API `repos/loganrooks/zlibrary-mcp/issues/11` - Issue details, reporter @Torrchy

### Secondary (MEDIUM confidence)
- [npm Trusted Publishing Docs](https://docs.npmjs.com/trusted-publishers/) - OIDC publishing configuration
- [Phil Nash - npm Trusted Publishing](https://philna.sh/blog/2026/01/28/trusted-publishing-npm/) - Practical workflow examples, npm version requirement (>= 11.5.1)
- [GitHub Docs - Creating Composite Actions](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action) - Composite action structure
- [Docker Build CI - GitHub Actions Cache](https://docs.docker.com/build/ci/github-actions/cache/) - GHA cache backend for Docker layer caching
- [npm Trusted Publishing GA Announcement](https://github.blog/changelog/2025-07-31-npm-trusted-publishing-with-oidc-is-generally-available/) - OIDC availability confirmation

### Tertiary (LOW confidence)
- [npm Provenance Attestation Docs](https://docs.npmjs.com/generating-provenance-statements/) - Provenance details (not directly tested in this project)

## Knowledge Applied

Checked knowledge base (`~/.gsd/knowledge/index.md`), no relevant lessons or spikes found for this phase's domain (CI/CD, GitHub Actions, npm publishing). The KB contains only signals, no distilled lessons or spike decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools already exist in the project or are standard GitHub Actions
- Architecture: HIGH - Patterns derived from existing CI workflow, MCP spec, and official GitHub Actions docs
- Pitfalls: HIGH - Pitfalls identified from codebase analysis (credential validation, LFS, stdio behavior) and verified against MCP spec and GitHub Actions docs

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (30 days -- CI tooling is stable; MCP spec version is locked at 2025-11-25)
