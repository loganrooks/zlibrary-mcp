# Phase 1: Integration Test Harness - Research

**Researched:** 2026-01-29
**Domain:** Node.js-to-Python bridge integration testing, Docker E2E, MCP protocol testing
**Confidence:** HIGH

## Summary

This phase creates an integration test harness verifying the Node.js-to-Python bridge works end-to-end for all 11 MCP tools, a Docker-based E2E test that starts the MCP server and calls a tool, and documents BRK-001 (download+RAG combined workflow bug).

The project already has partial integration tests in `__tests__/integration/` (path resolution smoke tests) and MCP protocol tests (mocked). The new work extends these to test each tool individually through the real Python bridge in two modes (recorded/live), adds Docker-based full-stack E2E using the MCP SDK's `StdioClientTransport`, and reproduces BRK-001.

**Primary recommendation:** Use Jest (existing) for integration tests, the MCP SDK's `Client` + `StdioClientTransport` for E2E tool invocation inside Docker, and static JSON fixtures for recorded mode.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jest | ^29.7.0 | Test runner | Already configured in project with ESM support |
| @modelcontextprotocol/sdk | 1.8.0 | MCP client for E2E | Already a dependency; provides `Client` + `StdioClientTransport` |
| python-shell | ^5.0.0 | Node-to-Python bridge | Already used; integration tests exercise this directly |
| Docker | Latest | E2E container | Required by CONTEXT decisions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ts-jest | ^29.3.2 | TypeScript test support | Already configured |
| docker compose | v2 | Orchestrate E2E container | If multi-container needed; otherwise plain `docker run` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jest | Vitest | Vitest is faster but project already deeply integrated with Jest ESM setup; migration cost outweighs benefit for this phase |
| Static fixtures | nock/record-replay | Record-replay adds complexity; static JSON is simpler for response shape validation |
| MCP Inspector CLI | SDK Client | Inspector is interactive; SDK Client is programmatic and testable |

**Installation:**
```bash
# No new packages needed - all already in package.json
npm install
```

## Architecture Patterns

### Recommended Project Structure
```
__tests__/
├── integration/
│   ├── python-bridge-integration.test.js   # Existing (path smoke)
│   ├── bridge-tools.test.js                # NEW: Per-tool bridge tests
│   └── brk-001-reproduction.test.js        # NEW: BRK-001 investigation
├── e2e/
│   ├── docker-mcp-e2e.test.js              # NEW: Docker E2E orchestrator
│   └── fixtures/
│       └── recorded-responses/             # NEW: Static JSON fixtures
│           ├── search.json
│           ├── full_text_search.json
│           ├── get_download_limits.json
│           └── ...
├── python/                                  # Existing Python tests
└── ...
Dockerfile.test                              # NEW: Test-only Dockerfile
docker-compose.test.yml                      # NEW: Optional orchestration
```

### Pattern 1: Two-Mode Integration Tests (Recorded + Live)
**What:** Each tool has a test that runs in recorded mode (default) verifying response shape, and live mode (--live flag) verifying real API interaction.
**When to use:** Every MCP tool integration test.
**Example:**
```javascript
// Source: Project pattern based on CONTEXT decisions
const LIVE_MODE = process.env.TEST_LIVE === 'true';

describe('search_books bridge integration', () => {
  test('returns valid response shape', async () => {
    if (!LIVE_MODE) {
      // Recorded mode: mock PythonShell to return fixture
      jest.unstable_mockModule('python-shell', () => ({
        PythonShell: { run: jest.fn().mockResolvedValue([JSON.stringify(FIXTURE)]) }
      }));
    }
    const result = await callPythonFunction('search', { query: 'test', count: 1 });
    expect(result).toHaveProperty('books');
    expect(Array.isArray(result.books)).toBe(true);
  }, LIVE_MODE ? 60000 : 10000);
});
```

### Pattern 2: MCP SDK Client for Docker E2E
**What:** Use the MCP SDK's `Client` with `StdioClientTransport` to spawn the MCP server process and call tools programmatically.
**When to use:** Docker E2E test.
**Example:**
```javascript
// Source: Context7 - MCP TypeScript SDK client/stdio docs
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const client = new Client({ name: 'e2e-test', version: '1.0.0' });
const transport = new StdioClientTransport({
  command: 'node',
  args: ['dist/index.js']
});
await client.connect(transport);

const tools = await client.listTools();
expect(tools.tools.length).toBeGreaterThan(0);

const result = await client.callTool({
  name: 'get_download_limits',
  arguments: {}
});
expect(result.content).toBeDefined();

await client.close();
```

### Pattern 3: Matrix Summary Output
**What:** After all tool tests complete, output a pass/fail matrix.
**When to use:** Test suite completion.
**Example:**
```
┌─────────────────────┬──────────┬──────┐
│ Tool                │ Recorded │ Live │
├─────────────────────┼──────────┼──────┤
│ search_books        │ PASS     │ PASS │
│ full_text_search    │ PASS     │ SKIP │
│ get_download_limits │ PASS     │ FAIL │
└─────────────────────┴──────────┴──────┘
```

### Anti-Patterns to Avoid
- **Mocking the bridge in integration tests:** The whole point is testing the real bridge. Only mock the network/API layer in recorded mode, not PythonShell itself.
- **Sharing state between test tools:** Each tool test must be independent. No login state leaking.
- **Hardcoding Docker platform:** Must support both amd64 and arm64 per CONTEXT.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP client protocol | Custom JSON-RPC client | `@modelcontextprotocol/sdk` Client | Protocol is complex, SDK handles initialization handshake, tool calling, transport |
| Docker multi-platform | Platform detection scripts | `docker buildx build --platform linux/amd64,linux/arm64` | buildx handles cross-compilation natively |
| Test fixture management | Custom fixture framework | Static JSON files + Jest mock | Simple, debuggable, no extra deps |
| Python process spawning | child_process.spawn wrapper | `python-shell` (already used) | Already integrated, handles stderr, args |

**Key insight:** The MCP SDK already has a full `Client` implementation with `StdioClientTransport` that spawns a process and communicates via stdio JSON-RPC. This is exactly what Docker E2E needs.

## Common Pitfalls

### Pitfall 1: ESM Module Mocking in Jest
**What goes wrong:** `jest.mock()` doesn't work with ESM; need `jest.unstable_mockModule()`.
**Why it happens:** Project uses `"type": "module"` and `jest.config.js` has `transform: {}`.
**How to avoid:** Always use `jest.unstable_mockModule()` then dynamic `import()` after mocking.
**Warning signs:** "Cannot use import statement outside a module" or mock not taking effect.

### Pitfall 2: Python Bridge Double-JSON Parsing
**What goes wrong:** Python bridge returns `{content: [{type: 'text', text: '<JSON_STRING>'}]}` — the result is double-wrapped JSON.
**Why it happens:** MCP protocol wraps results in content array; Python bridge formats as MCP response.
**How to avoid:** Understand the two-parse flow in `zlibrary-api.ts:60-100`. Fixtures must match this exact shape.
**Warning signs:** Parse errors on valid-looking JSON, "Invalid MCP response structure" errors.

### Pitfall 3: Auth Errors vs Real Failures
**What goes wrong:** Integration tests fail because Z-Library credentials aren't set, but the bridge itself works fine.
**Why it happens:** Python bridge requires login for most operations.
**How to avoid:** In recorded mode, intercept before Python actually connects to Z-Library. In live mode, require `ZLIBRARY_EMAIL` and `ZLIBRARY_PASSWORD` env vars and skip gracefully if missing.
**Warning signs:** "Failed to login" errors in recorded mode tests.

### Pitfall 4: Docker Build Context Size
**What goes wrong:** Docker build takes forever or fails due to large context.
**Why it happens:** `node_modules/`, `.venv/`, `downloads/`, test fixtures included.
**How to avoid:** Use `.dockerignore` to exclude `node_modules/`, `.venv/`, `downloads/`, `processed_rag_output/`, `coverage/`, `.git/`.
**Warning signs:** Build context >500MB, slow image pushes.

### Pitfall 5: UV/Venv in Docker
**What goes wrong:** Python bridge can't find dependencies inside Docker.
**Why it happens:** `venv-manager.ts` looks for `.venv/bin/python` relative to project root.
**How to avoid:** Dockerfile must run `uv sync` to create `.venv/` and install deps. Ensure `pyproject.toml`, `uv.lock`, and `zlibrary/` (vendored) are in the image.
**Warning signs:** `ImportError` for zlibrary, httpx, etc. inside container.

### Pitfall 6: Stdio Transport in Docker
**What goes wrong:** MCP client can't communicate with server inside Docker via stdio.
**Why it happens:** Docker `run` with stdio requires `-i` flag and proper signal handling.
**How to avoid:** Two approaches: (A) Run E2E test script INSIDE Docker, or (B) Use `docker exec` / pipe. Option A is simpler.
**Warning signs:** Connection timeout, "No output received from Python script".

## Code Examples

### Complete Tool List for Integration Tests
```javascript
// All Python bridge function names and their MCP tool counterparts
const TOOL_BRIDGE_MAP = {
  'search_books':           { fn: 'search', minArgs: { query: 'test', count: 1 } },
  'full_text_search':       { fn: 'full_text_search', minArgs: { query: 'test', count: 1 } },
  'get_download_history':   { fn: 'get_download_history', minArgs: { count: 1 } },
  'get_download_limits':    { fn: 'get_download_limits', minArgs: {} },
  'download_book_to_file':  { fn: 'download_book', minArgs: { book_details: {}, output_dir: '/tmp' } },
  'process_document_for_rag': { fn: 'process_document', minArgs: { file_path_str: '/tmp/test.pdf' } },
  'get_book_metadata':      { fn: 'get_book_metadata_complete', minArgs: { book_details: {} } },
  'search_by_term':         { fn: 'search_by_term_bridge', minArgs: { term: 'test' } },
  'search_by_author':       { fn: 'search_by_author_bridge', minArgs: { author: 'test' } },
  'fetch_booklist':         { fn: 'fetch_booklist_bridge', minArgs: { url: 'https://example.com' } },
  'search_advanced':        { fn: 'search_advanced', minArgs: { query: 'test' } },
};
```

### Recorded Response Fixture Shape
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"books\": [{\"title\": \"Test Book\", \"author\": \"Author\", \"year\": 2020}], \"count\": 1}"
    }
  ]
}
```
Note: The outer JSON is parsed first (MCP response), then `content[0].text` is parsed again (actual result).

### BRK-001 Reproduction Test Skeleton
```javascript
// BRK-001: download_book with process_for_rag=true
// Known issue: AttributeError when calling missing method in forked zlibrary
describe('BRK-001: Download + RAG Combined Workflow', () => {
  test('reproduce: download_book with process_for_rag=true', async () => {
    try {
      const result = await callPythonFunction('download_book', {
        book_details: { /* minimal valid book details */ },
        output_dir: '/tmp/brk001-test',
        process_for_rag: true,
        processed_output_format: 'txt'
      });
      // If it succeeds, BRK-001 is resolved
      console.log('BRK-001: RESOLVED - download+RAG workflow succeeded');
    } catch (error) {
      // Document the exact error
      console.log('BRK-001: REPRODUCED');
      console.log('Error:', error.message);
      console.log('Stack:', error.stack);
      // Test passes either way - this is investigation, not fix
    }
  }, 60000);
});
```

### Dockerfile.test Skeleton
```dockerfile
# Multi-platform: linux/amd64, linux/arm64
FROM node:20-slim AS base

# Install UV for Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python
RUN apt-get update && apt-get install -y python3 python3-venv && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first (cache layer)
COPY pyproject.toml uv.lock ./
COPY zlibrary/ ./zlibrary/
COPY lib/ ./lib/
RUN uv sync

# Node deps
COPY package.json package-lock.json ./
RUN npm ci

# Source and build
COPY src/ ./src/
COPY tsconfig.json ./
RUN npm run build

# E2E test entry
COPY __tests__/e2e/ ./__tests__/e2e/
CMD ["node", "--experimental-vm-modules", "node_modules/jest/bin/jest.js", "--testPathPattern", "e2e"]
```

### npm Script Configuration
```json
{
  "scripts": {
    "test:integration": "node --experimental-vm-modules node_modules/jest/bin/jest.js --testPathPattern 'integration' --forceExit",
    "test:integration:live": "TEST_LIVE=true npm run test:integration",
    "test:e2e": "docker compose -f docker-compose.test.yml up --build --abort-on-container-exit",
    "test:e2e:local": "node --experimental-vm-modules node_modules/jest/bin/jest.js --testPathPattern 'e2e' --forceExit"
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `jest.mock()` | `jest.unstable_mockModule()` | Jest 29+ with ESM | Must use dynamic imports after mock setup |
| MCP Inspector CLI (interactive) | SDK Client (programmatic) | MCP SDK 1.x | E2E tests can be fully automated |
| `pip install` in Docker | `uv sync` in Docker | UV 2024+ | Faster, reproducible Python deps |
| `docker build` single platform | `docker buildx` multi-platform | Docker BuildKit | Required for arm64 support |

**Deprecated/outdated:**
- `jest.mock()` for ESM modules: Use `jest.unstable_mockModule()` instead
- MCP Inspector for automated testing: Use SDK Client programmatically

## Open Questions

1. **Docker base image with UV pre-installed?**
   - What we know: UV can be copied from `ghcr.io/astral-sh/uv:latest` as shown above
   - What's unclear: Whether `node:20-slim` has sufficient Python 3.9+ or needs separate Python install
   - Recommendation: Use `node:20-slim` + install Python via apt. UV is copied from its official image.

2. **Which tool to test in Docker E2E?**
   - What we know: `get_download_limits` is the lightest API call but requires auth
   - What's unclear: Whether any tool works without Z-Library credentials
   - Recommendation: E2E should test tool listing (no auth needed) plus one tool call. If no creds, skip tool call but verify `listTools` returns 11 tools.

3. **BRK-001 exact reproduction conditions**
   - What we know: "AttributeError when calling missing method in forked zlibrary" during `download_book` with `process_for_rag=true`
   - What's unclear: Whether the vendored zlibrary fork has been updated since this was reported (issue from pre-2026)
   - Recommendation: First attempt reproduction with live credentials; if AttributeError is gone, document as resolved with evidence

## Sources

### Primary (HIGH confidence)
- `/modelcontextprotocol/typescript-sdk` via Context7 - Client + StdioClientTransport usage patterns
- Project codebase analysis - Existing test infrastructure, bridge architecture, tool map
- `ISSUES.md:425-435` - BRK-001 bug description

### Secondary (MEDIUM confidence)
- `package.json` - Current dependency versions and scripts
- `jest.config.js` - ESM configuration and module mapping
- `venv-manager.ts` - UV-based Python path resolution

### Tertiary (LOW confidence)
- Docker multi-stage build with UV - Based on UV docs pattern, not verified in this project

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project, verified via package.json and codebase
- Architecture: HIGH - Pattern derived from existing code + MCP SDK docs via Context7
- Pitfalls: HIGH - Identified from actual codebase analysis (ESM config, double-JSON, auth flow)

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (stable domain, no fast-moving dependencies)
