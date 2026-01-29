# Phase 3: MCP SDK Upgrade - Research

**Researched:** 2026-01-29
**Domain:** MCP TypeScript SDK migration (1.8.0 to 1.25.3)
**Confidence:** HIGH

## Summary

The MCP TypeScript SDK has evolved from 1.8.0 to 1.25.3 with significant additions but maintained backward compatibility for the low-level `Server` class API. The project has two migration paths: (1) stay on the low-level `Server` class with minimal changes, or (2) adopt the high-level `McpServer` class as decided in CONTEXT.md.

The migration surface is small (only `src/index.ts` imports from the SDK). The new `McpServer` class provides `registerTool()` which accepts Zod schemas directly as `inputSchema` objects (not wrapped in `z.object()`), handles validation automatically, and simplifies handler signatures. The current codebase already uses Zod 3.25.76 which satisfies the SDK's peer dependency (`^3.25 || ^4.0`).

**Primary recommendation:** Adopt `McpServer` from `@modelcontextprotocol/sdk/server/mcp.js`, converting each tool registration to use `registerTool()` with the existing Zod schemas. This eliminates the manual `ListToolsRequestSchema`/`CallToolRequestSchema` handlers, `zodToJsonSchema` conversion, and custom tool registry. Node must be bumped from >=14 to >=18.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@modelcontextprotocol/sdk` | 1.25.3 | MCP server framework | Official SDK, fixes 2 high-severity vulnerabilities |
| `zod` | 3.25.76 (keep) | Schema validation | Already installed, satisfies SDK peer dep `^3.25 \|\| ^4.0` |
| `zod-to-json-schema` | 3.24.5+ (keep or remove) | JSON schema generation | May become unnecessary if using `McpServer.registerTool()` |

### No Longer Needed (After Migration to McpServer)
| Library/Import | Current Use | Why Removable |
|----------------|-------------|---------------|
| `zodToJsonSchema` | Manual input schema conversion | `McpServer.registerTool()` accepts Zod schemas directly |
| `ListToolsRequestSchema` | Manual tools/list handler | `McpServer` handles automatically |
| `CallToolRequestSchema` | Manual tools/call handler | `McpServer` handles automatically |
| `ListResourcesRequestSchema` | Empty resources handler | `McpServer` handles automatically |
| `ListPromptsRequestSchema` | Empty prompts handler | `McpServer` handles automatically |
| Custom `ToolDefinition` interface | Tool type definition | SDK provides this |
| Custom `ToolRegistryEntry` | Tool registry type | Replaced by `registerTool()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `McpServer` (high-level) | `Server` (low-level, keep current pattern) | Minimal code changes but misses simplification opportunity; CONTEXT.md decided on McpServer |

**Installation:**
```bash
npm install @modelcontextprotocol/sdk@1.25.3
```

## Architecture Patterns

### Pattern 1: McpServer Tool Registration
**What:** Register tools using `McpServer.registerTool()` instead of manual request handler wiring
**When to use:** All 11 tools in the server
**Example:**
```typescript
// Source: Context7 - MCP TypeScript SDK docs
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import * as z from 'zod';

const server = new McpServer({
    name: 'zlibrary-mcp',
    version: getPackageVersion()
});

// registerTool signature:
//   registerTool(name, { title?, description, inputSchema, outputSchema?, annotations? }, handler)
// inputSchema is an object of Zod types (NOT wrapped in z.object())
// Handler receives parsed args directly, returns { content: [...], structuredContent?: ... }

server.registerTool(
    'search_books',
    {
        title: 'Search Books',
        description: 'Search for books in Z-Library...',
        inputSchema: {
            query: z.string().describe('Search query'),
            exact: z.boolean().optional().default(false).describe('Exact match'),
            // ... rest of params
        },
        outputSchema: {
            books: z.array(BookResultSchema),
            // ...
        },
        annotations: {
            readOnlyHint: true,
            idempotentHint: true,
            openWorldHint: true,
        }
    },
    async ({ query, exact, ...rest }) => {
        const result = await zlibraryApi.searchBooks({ query, exact, ...rest });
        return {
            content: [{ type: 'text', text: JSON.stringify(result) }],
            structuredContent: result
        };
    }
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Pattern 2: Error Handling in McpServer Tools
**What:** McpServer catches handler errors and returns proper MCP error responses
**When to use:** All tools — can simplify existing try/catch blocks
**Example:**
```typescript
// If handler throws, McpServer wraps it as an error response automatically.
// For custom error objects (like the current { error: { message: ... } } pattern),
// the handler should return { content: [{ type: 'text', text: errorMsg }], isError: true }
```

### Pattern 3: Accessing Low-Level Server from McpServer
**What:** `McpServer` exposes the underlying `Server` via `server.server`
**When to use:** If custom low-level handler registration is needed for any edge case
**Example:**
```typescript
// Source: Context7 - McpServer docs
const mcpServer = new McpServer({ name: 'test', version: '1.0.0' });
// Access low-level server:
mcpServer.server.setRequestHandler(SomeSchema, handler);
```

### Anti-Patterns to Avoid
- **Passing `z.object()` to `inputSchema`:** The `registerTool` `inputSchema` expects a plain object of Zod types, NOT wrapped in `z.object()`. Pass `{ query: z.string() }` not `z.object({ query: z.string() })`.
- **Manual zodToJsonSchema conversion:** McpServer handles schema conversion internally. Don't convert Zod to JSON Schema manually.
- **Mixing Server and McpServer for tool registration:** Use one approach. McpServer internally creates a Server, so don't create both.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tool listing/calling protocol | Custom `setRequestHandler` for ListTools/CallTools | `McpServer.registerTool()` | SDK handles JSON-RPC routing, validation, error formatting |
| Input validation | Manual `safeParse` + error formatting | `McpServer` built-in validation | Zod validation is automatic with registerTool |
| JSON Schema generation | `zodToJsonSchema()` call per tool | `McpServer` internal conversion | SDK handles the Zod-to-JSON-Schema conversion |
| Tool capability object | `generateToolsCapability()` function | `McpServer` constructor capabilities | SDK manages capability negotiation |

**Key insight:** The current `src/index.ts` has ~250 lines of boilerplate (tool registry, capability generation, request handler wiring, manual validation) that `McpServer.registerTool()` replaces entirely.

## Common Pitfalls

### Pitfall 1: inputSchema Format Difference
**What goes wrong:** Passing a `z.object()` to `registerTool`'s `inputSchema` instead of a plain object of Zod types
**Why it happens:** The current code uses `z.object({...})` for schemas, and it's natural to pass those directly
**How to avoid:** Extract the inner shape: if you have `const Schema = z.object({ query: z.string() })`, pass `{ query: z.string() }` or `Schema.shape` to `inputSchema`
**Warning signs:** TypeScript compilation errors about schema type mismatch

### Pitfall 2: CallToolRequest `name` vs `tool_name` Field
**What goes wrong:** The current code accesses `request.params.name` for tool name. SDK versions may have changed this field.
**Why it happens:** Protocol spec evolution between 1.8.0 and 1.25.x
**How to avoid:** With McpServer, this is irrelevant — the SDK routes to the correct handler automatically
**Warning signs:** N/A if using McpServer

### Pitfall 3: Node.js Version Requirement
**What goes wrong:** SDK 1.25.3 requires Node >=18, but `package.json` currently says `>=14`
**Why it happens:** SDK raised minimum Node requirement
**How to avoid:** Bump `engines.node` to `>=18` in package.json. Current environment is Node 18.19.1 which satisfies this.
**Warning signs:** CI failures if CI uses Node < 18

### Pitfall 4: TypeScript Target and ES2020 Requirement
**What goes wrong:** SDK 1.25.0 updated TypeScript config to ES2020 for AJV imports
**Why it happens:** Internal dependency requirements
**How to avoid:** Current tsconfig targets ES2022 which is fine (superset of ES2020). No change needed.
**Warning signs:** AJV-related compilation errors

### Pitfall 5: Strict Type Enforcement in 1.25.0
**What goes wrong:** SDK 1.25.0 enforces spec compliance by "removing loose/passthrough types not allowed/defined by MCP spec"
**Why it happens:** Protocol conformance tightening
**How to avoid:** Ensure returned objects match expected MCP types exactly. The current `structuredContent` and `content` array patterns already match.
**Warning signs:** TypeScript errors on `ServerResult` type or response objects

### Pitfall 6: Test Mock Breakage
**What goes wrong:** Tests that mock `Server` constructor or `setRequestHandler` break when switching to `McpServer`
**Why it happens:** Different import path (`server/mcp.js` vs `server/index.js`) and different API surface
**How to avoid:** Update test mocks to match `McpServer` import path and constructor. The integration test (`mcp-protocol.test.js`) mocks `Server` — must update.
**Warning signs:** Test failures with "cannot find module" or "constructor is not a function"

### Pitfall 7: `zod-to-json-schema` May Become Unnecessary
**What goes wrong:** Keeping `zod-to-json-schema` as a dependency when it's no longer used
**Why it happens:** Forgetting to clean up after McpServer handles schema conversion
**How to avoid:** After migration, check if `zodToJsonSchema` is still imported anywhere. If not, remove the dependency.
**Warning signs:** Unused dependency in `package.json`

## Code Examples

### Current Code (Server low-level) → Target Code (McpServer)

**Before (current `src/index.ts` pattern):**
```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema, CallToolRequestSchema, ... } from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
    { name: "zlibrary-mcp", version: "2.0.0" },
    { capabilities: { tools: toolsCapabilityObject, resources: {}, prompts: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools: Object.values(toolsCapabilityObject) };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const tool = toolRegistry[name];
    const validationResult = tool.schema.safeParse(args);
    // ... manual validation, routing, error handling
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

**After (McpServer high-level):**
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new McpServer({
    name: 'zlibrary-mcp',
    version: getPackageVersion()
});

// Each tool registered individually — SDK handles listing, routing, validation
server.registerTool(
    'search_books',
    {
        title: 'Search Books',
        description: '...',
        inputSchema: {
            query: z.string().describe('Search query'),
            exact: z.boolean().optional().default(false).describe('Exact match'),
            fromYear: z.number().int().optional().describe('Min year'),
            // ...
        },
        annotations: { readOnlyHint: true, idempotentHint: true, openWorldHint: true }
    },
    async (args) => {
        try {
            const result = await zlibraryApi.searchBooks(args);
            if (result?.error) {
                return { content: [{ type: 'text', text: `Error: ${result.error.message}` }], isError: true };
            }
            return {
                content: [{ type: 'text', text: JSON.stringify(result) }],
                structuredContent: result
            };
        } catch (error) {
            return { content: [{ type: 'text', text: `Error: ${error.message}` }], isError: true };
        }
    }
);

// Repeat for all 11 tools...

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Claude Desktop MCP Config Snippet
```json
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/absolute/path/to/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "your-email",
        "ZLIBRARY_PASSWORD": "your-password"
      }
    }
  }
}
```

## State of the Art

| Old Approach (SDK 1.8.0) | Current Approach (SDK 1.25.3) | When Changed | Impact |
|---------------------------|-------------------------------|--------------|--------|
| `Server` class with manual `setRequestHandler` | `McpServer` with `registerTool/registerResource/registerPrompt` | ~SDK 1.10+ | Major simplification, eliminates boilerplate |
| Manual `zodToJsonSchema` conversion | SDK-internal Zod-to-JSON-Schema | Built into McpServer | Can remove `zod-to-json-schema` dependency |
| `capabilities: { tools: {object} }` in constructor | Auto-managed capabilities from registered tools | McpServer design | No manual capability wiring |
| Zod v3 only | Zod v3.25+ or v4.0+ | SDK 1.23.0 | Current zod@3.25.76 is compatible |
| Node >=14 | Node >=18 | SDK engine requirement | Must bump `engines.node` |
| Protocol 2024-11-05 | Protocol 2025-11-25 | SDK 1.24+ | New protocol version, backward compatible |

**Deprecated/outdated:**
- The `Server` class is NOT deprecated — it's the "low-level" API. `McpServer` is the "high-level" wrapper.
- Both are officially supported. The project chose to adopt `McpServer` per CONTEXT.md decisions.

## Migration Scope Analysis

### Files Requiring Changes
| File | Change Type | Complexity |
|------|------------|------------|
| `src/index.ts` | Major rewrite: Server→McpServer, tool registration | HIGH (but mechanical) |
| `package.json` | Dependency version bump, engines.node bump | LOW |
| `__tests__/index.test.js` | Update mocks for McpServer import/API | MEDIUM |
| `__tests__/integration/mcp-protocol.test.js` | Update mocks for McpServer import/API | MEDIUM |
| `__tests__/e2e/docker-mcp-e2e.test.js` | May need Node version bump in Dockerfile | LOW |

### Files NOT Requiring Changes
- `src/lib/zlibrary-api.ts` — No SDK imports
- `lib/python_bridge.py` — Python layer unaffected
- `lib/rag_processing.py` — Python layer unaffected
- All Python tests — Unaffected (but should run to confirm)
- `src/lib/paths.ts` — No SDK imports
- `src/lib/venv-manager.ts` — No SDK imports
- `src/lib/retry-manager.ts` — No SDK imports

### Vulnerability Resolution
The upgrade from 1.8.0 to 1.25.3 resolves:
- **GHSA-w48q-cv73-mx4w** (HIGH): DNS rebinding protection not enabled by default (fixed in 1.25.2+)
- **GHSA-8r9q-7v3j-jr4g** (HIGH): ReDoS vulnerability (fixed in 1.25.2+)

Both affect `@modelcontextprotocol/sdk <=1.25.1`, so 1.25.3 resolves them.

## Open Questions

1. **`registerTool` inputSchema format with `.optional().default()` Zod types**
   - What we know: inputSchema takes `{ key: z.type() }` objects. Current code uses `.optional().default()` chains.
   - What's unclear: Whether default values are preserved/used by McpServer's internal validation the same way as manual `safeParse`
   - Recommendation: Test with one tool first (e.g., `get_download_limits` which has no params). Verify defaults work by testing `search_books` with partial args. Confidence: MEDIUM — likely works since McpServer uses Zod internally, but needs validation.

2. **`outputSchema` support in `registerTool`**
   - What we know: Context7 examples show `outputSchema` as a parameter to `registerTool`. Current code defines output schemas.
   - What's unclear: Exact version this was added; whether it's the same format as inputSchema
   - Recommendation: Include output schemas in registerTool calls. If TypeScript complains, remove them (they're optional per MCP spec). Confidence: HIGH.

3. **`structuredContent` in return value**
   - What we know: Context7 examples show `{ content: [...], structuredContent: output }` as the return format from tool handlers
   - What's unclear: Whether this is supported/required at all SDK versions between 1.8 and 1.25
   - Recommendation: Keep returning structuredContent. It matches current behavior and Context7 examples. Confidence: HIGH.

4. **`zod-to-json-schema` removal feasibility**
   - What we know: McpServer handles schema conversion internally. The dependency may become unused.
   - What's unclear: Whether any test code or other files still reference `zodToJsonSchema`
   - Recommendation: After migration, grep for `zodToJsonSchema` usage. If none, remove the dependency. Confidence: HIGH.

## Sources

### Primary (HIGH confidence)
- Context7 `/modelcontextprotocol/typescript-sdk` — McpServer API, registerTool examples, Server vs McpServer patterns
- `npm info @modelcontextprotocol/sdk@1.25.3` — peer dependencies (`zod: ^3.25 || ^4.0`), engines (`node: >=18`), peerDependenciesMeta
- `npm audit` — Confirmed 2 high-severity vulnerabilities fixed by upgrade to >=1.25.2
- `npm view @modelcontextprotocol/sdk versions` — Latest stable is 1.25.3

### Secondary (MEDIUM confidence)
- GitHub releases page (`/modelcontextprotocol/typescript-sdk/releases`) — Breaking changes summary across versions
- GitHub CLAUDE.md — Architecture layers, Server vs McpServer relationship

### Tertiary (LOW confidence)
- None — all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via npm registry and Context7
- Architecture: HIGH — multiple Context7 examples confirm McpServer.registerTool pattern
- Pitfalls: HIGH — derived from actual codebase analysis + SDK documentation
- inputSchema format details: MEDIUM — consistent across examples but nuances with defaults untested

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (stable SDK, slow release cadence)
