# Phase 2: Low-Risk Dependency Upgrades - Research

**Researched:** 2026-01-29
**Domain:** Node.js/Python dependency upgrades, Zod schema migration, security auditing
**Confidence:** HIGH

## Summary

This phase covers upgrading non-SDK dependencies, resolving security vulnerabilities, and fixing Python code quality issues. The most critical finding is that **Zod 4 migration is blocked by the MCP SDK** -- the current SDK (v1.8.0) depends on `zod ^3.23.8` and is incompatible with Zod 4 (causes `w._parse is not a function` errors). The SDK v2 (expected Q1 2026) will support Zod 4. This means the Zod 4 migration must be deferred to Phase 3 or done via the Zod 3.25 bridge approach (import from `zod/v4` subpath).

The env-paths upgrade from v3 to v4 requires Node.js 20+, but the project currently runs Node 18. The `.gitignore` already contains `*.tsbuildinfo` (DEP-05 is already done). Security audit shows 5 npm vulnerabilities (2 high) fixable via `npm audit fix`.

**Primary recommendation:** Use Zod 3.25 as a bridge (keeps SDK compatibility, enables `zod/v4` subpath imports for new code), upgrade env-paths only after confirming Node.js 20+ target, and focus on the security and Python quality fixes which are straightforward.

## Standard Stack

### Core
| Library | Current | Target | Purpose | Notes |
|---------|---------|--------|---------|-------|
| zod | 3.24.2 | 3.25.x | Schema validation | Bridge version; enables `zod/v4` subpath |
| zod-to-json-schema | 3.24.5 | DROP | JSON schema conversion | Deprecated; use `z.toJSONSchema()` from `zod/v4` OR keep for SDK compat |
| env-paths | 3.0.0 | 3.0.0 or 4.0.0 | OS-specific paths | v4 requires Node 20+; project on Node 18 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| zod-v3-to-v4 codemod | latest | Automated migration | `npx zod-v3-to-v4` for bulk schema changes |
| pip-audit | latest | Python vulnerability scanning | Run alongside npm audit |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Zod 3.25 bridge | Zod 4.x direct | Breaks MCP SDK 1.8.0 -- not viable until Phase 3 |
| zod-to-json-schema | z.toJSONSchema() | Native Zod 4 feature, but requires `zod/v4` import |
| @alcyone-labs/zod-to-json-schema | community fork | Zod 4 compatible, but adds new dependency |

## Architecture Patterns

### Pattern 1: Zod 3.25 Bridge Migration
**What:** Install `zod@3.25.x` which ships both Zod 3 (root) and Zod 4 (`zod/v4` subpath). Existing code continues working unchanged. New code or migrated schemas can optionally import from `zod/v4`.
**When to use:** When MCP SDK still requires Zod 3.
**Example:**
```typescript
// Existing code stays the same (imports from "zod" = Zod 3 API)
import { z, ZodObject, ZodRawShape } from 'zod';

// If needed, Zod 4 API available at subpath:
// import { z as z4 } from 'zod/v4';
```
Source: https://zod.dev/v4/versioning

### Pattern 2: Deferred Full Zod 4 Migration (Phase 3)
**What:** When upgrading MCP SDK to v2 in Phase 3, switch all imports to `zod/v4` or `zod@4.x` and apply all Zod 4 API changes at once.
**When to use:** Phase 3 when SDK v2 supports Zod 4.
**Key changes needed at that time:**
```typescript
// z.object({}).passthrough() becomes z.looseObject({})
// OLD: bookDetails: z.object({}).passthrough()
// NEW: bookDetails: z.looseObject({})

// zodToJsonSchema() becomes z.toJSONSchema()
// OLD: import { zodToJsonSchema } from 'zod-to-json-schema';
//      zodToJsonSchema(tool.schema);
// NEW: import { z } from 'zod/v4';
//      z.toJSONSchema(tool.schema);

// ZodObject/ZodRawShape may change -- verify exports exist in v4
// safeParse error.errors still has .path and .message (confirmed)
```

### Pattern 3: BeautifulSoup Parser Specification
**What:** Replace `'html.parser'` with `'lxml'` in all BeautifulSoup calls.
**When to use:** All 10 call sites across 6 files.
**Example:**
```python
# OLD
soup = BeautifulSoup(html, 'html.parser')

# NEW
soup = BeautifulSoup(html, 'lxml')
```

### Anti-Patterns to Avoid
- **Upgrading Zod to 4.x while SDK is at 1.8.0:** Causes runtime `w._parse is not a function` errors. The SDK hardcodes Zod 3 internals.
- **Using `except:` (bare except):** Catches `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit` -- use `except Exception:` at minimum.
- **Pinning exact versions:** Use `^` semver ranges per project convention.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zod 3-to-4 codemod | Manual find-replace | `npx zod-v3-to-v4` | Handles passthrough, merge, strict, deepPartial automatically |
| JSON schema from Zod | Custom converter | `z.toJSONSchema()` (Zod 4) or `zodToJsonSchema` (Zod 3) | Edge cases in schema conversion |
| Vulnerability scanning | Manual review | `npm audit` + `pip-audit` | Automated, covers transitive deps |

**Key insight:** The Zod codemod handles the mechanical migration; the real complexity is the SDK coupling.

## Common Pitfalls

### Pitfall 1: Zod 4 + MCP SDK Incompatibility
**What goes wrong:** Installing `zod@4.x` breaks the MCP SDK with `w._parse is not a function`.
**Why it happens:** SDK v1.x uses Zod 3 internal APIs (`._def`, `._parse`) that were restructured in Zod 4.
**How to avoid:** Stay on `zod@3.25.x` (bridge version) until Phase 3 SDK upgrade.
**Warning signs:** Any import from `zod` (root) that returns Zod 4 types when SDK expects Zod 3.

### Pitfall 2: env-paths v4 Requires Node 20
**What goes wrong:** `env-paths@4.0.0` fails on Node 18 environments.
**Why it happens:** v4's only breaking change is `Require Node.js 20`.
**How to avoid:** Either stay on v3 (already ESM-compatible) or upgrade Node.js first.
**Warning signs:** The project currently specifies `"engines": { "node": ">=14.0.0" }`.

### Pitfall 3: zod-to-json-schema Silently Fails with Zod 4
**What goes wrong:** Returns incomplete schema `{ "$schema": "http://json-schema.org/draft-07/schema#" }` with no properties.
**Why it happens:** `zod-to-json-schema` v3.x accesses `._def` which is moved to `._zod.def` in Zod 4.
**How to avoid:** Keep using `zod-to-json-schema` with Zod 3 schemas (root import), or switch to `z.toJSONSchema()` with Zod 4 schemas.

### Pitfall 4: Zod 4 Error Format Subtle Changes
**What goes wrong:** Error formatting code breaks or produces different output.
**Why it happens:** Zod 4 changes: `.format()` deprecated (use `z.treeifyError()`), "Required" message becomes "expected {type}, received undefined", `.error` no longer extends `Error`.
**How to avoid:** The `safeParse().error.errors` array with `.path` and `.message` still works in Zod 4. The existing error formatting site (`src/index.ts:693`) should work, but test message content changes.

### Pitfall 5: BeautifulSoup lxml Not Installed
**What goes wrong:** `FeatureNotFound` exception if lxml not available.
**Why it happens:** Switching parser from built-in `html.parser` to `lxml` requires the package.
**How to avoid:** lxml is already a project dependency -- verified. No action needed.

## Code Examples

### Bare except fix (booklist_tools.py:267)
```python
# Source: Python best practices, PEP 8
# Context: await zlib.search("init", count=1) can raise network/auth errors

# OLD (line 265-268):
try:
    await zlib.search("init", count=1)
except:
    pass  # Authentication might succeed even if search fails

# NEW:
import logging
logger = logging.getLogger(__name__)
# ...
try:
    await zlib.search("init", count=1)
except Exception as e:
    logger.warning("Initial search during authentication failed: %s", e)
    # Authentication might succeed even if search fails
```

### BeautifulSoup parser change (10 sites, 6 files)
```python
# Files affected:
# lib/booklist_tools.py: lines 91, 162
# lib/term_tools.py: line 70
# lib/author_tools.py: line 210
# lib/advanced_search.py: lines 42, 115
# lib/enhanced_metadata.py: lines 79, 435
# lib/rag_processing.py: lines 1539, 4576

# Simple find-replace across all files:
# OLD: BeautifulSoup(html, 'html.parser')
# NEW: BeautifulSoup(html, 'lxml')
# (variable name may be html_content in rag_processing.py)
```

### npm audit fix
```bash
# Current state: 5 vulnerabilities (2 high: js-yaml, qs)
# Both fixable via:
npm audit fix

# Then verify:
npm audit  # should show 0 high/critical
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `z.object({}).passthrough()` | `z.looseObject({})` | Zod 4 (2025) | API change, old still works as legacy |
| `zodToJsonSchema()` | `z.toJSONSchema()` | Zod 4 (2025) | zod-to-json-schema deprecated |
| `.format()` / `.flatten()` on ZodError | `z.treeifyError()` / `z.prettifyError()` | Zod 4 (2025) | Old methods deprecated |
| `._def` internal access | `._zod.def` | Zod 4 (2025) | Breaks libraries using internals |

**Deprecated/outdated:**
- `zod-to-json-schema`: Maintainer stopped updates Nov 2025. Use Zod 4 native `z.toJSONSchema()`.
- `.passthrough()` / `.strict()`: Legacy in Zod 4, replaced by `z.looseObject()` / `z.strictObject()`.

## Open Questions

1. **Should Zod migration happen in Phase 2 at all?**
   - What we know: MCP SDK 1.8.0 requires Zod 3. Zod 3.25 is a bridge that keeps root import as Zod 3. Full Zod 4 migration requires SDK v2.
   - What's unclear: Whether the phase requirements (DEP-02) intended a full Zod 4 migration or just preparation.
   - Recommendation: In Phase 2, upgrade to `zod@3.25.x` (safe, no code changes needed). Defer the actual `.passthrough()` -> `z.looseObject()` and `zodToJsonSchema` -> `z.toJSONSchema()` changes to Phase 3 when SDK is upgraded. Alternatively, if Phase 2 must do the Zod 4 API migration, use `zod/v4` subpath imports only in application code (not in SDK-facing code).

2. **Should env-paths be upgraded to v4?**
   - What we know: v4's only change is requiring Node 20+. Project currently on Node 18.
   - What's unclear: Whether the Node.js version will be upgraded before this phase.
   - Recommendation: Skip env-paths upgrade unless Node 20+ is confirmed. The project already uses ESM, so v3 works fine. Update `engines` field if Node is upgraded.

3. **How to handle `zod-to-json-schema` during the bridge period?**
   - What we know: It works with Zod 3 schemas (root import). It fails silently with Zod 4 schemas.
   - Recommendation: Keep `zod-to-json-schema` during Phase 2 since SDK still uses Zod 3. Remove it in Phase 3 when migrating to `z.toJSONSchema()`.

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/zod_dev_v4` - passthrough deprecation, looseObject, error format changes, breaking changes
- Context7 `/stefanterdell/zod-to-json-schema` - API usage and configuration
- [Zod v4 Changelog](https://zod.dev/v4/changelog) - comprehensive migration guide
- [Zod v4 JSON Schema](https://zod.dev/json-schema) - z.toJSONSchema() API
- [Zod v4 Versioning](https://zod.dev/v4/versioning) - 3.25 bridge strategy

### Secondary (MEDIUM confidence)
- [MCP SDK Zod 4 Issue #555](https://github.com/modelcontextprotocol/typescript-sdk/issues/555) - SDK Zod 4 support tracking
- [MCP SDK Zod 4 Incompatibility #1429](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1429) - confirmed runtime breakage
- [env-paths GitHub Releases](https://github.com/sindresorhus/env-paths/releases) - v4 requires Node 20
- [zod-v3-to-v4 codemod](https://github.com/nicoespeon/zod-v3-to-v4) - automated migration tool

### Tertiary (LOW confidence)
- WebSearch for MCP SDK v2 timeline (Q1 2026 estimate from community)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified via Context7, npm, and official docs
- Architecture: HIGH - Zod bridge pattern documented officially, SDK incompatibility confirmed via GitHub issues
- Pitfalls: HIGH - runtime errors confirmed by multiple users, env-paths Node req verified

**Research date:** 2026-01-29
**Valid until:** 2026-02-28 (30 days; Zod/SDK landscape evolving)

---

## Revised Phase 2 Scope Recommendation

Given findings, the planner should consider splitting DEP-02 (Zod 4 migration):

**Phase 2 (safe):**
- Upgrade `zod` from `3.24.2` to `3.25.x` (no code changes, bridge version)
- Keep `zod-to-json-schema` (still works with Zod 3 root import)
- Fix npm audit vulnerabilities (`npm audit fix`)
- Run `pip-audit` and fix any issues
- Add `.tsbuildinfo` to `.gitignore` -- **ALREADY DONE** (line 6)
- Fix bare `except:` in `booklist_tools.py:267`
- Change all `BeautifulSoup(html, 'html.parser')` to `BeautifulSoup(html, 'lxml')` (10 sites, 6 files)
- env-paths: stay at v3 unless Node 20+ confirmed

**Phase 3 (with SDK upgrade):**
- Upgrade MCP SDK to v2
- Switch Zod imports to `zod/v4` or `zod@4.x`
- Replace `z.object({}).passthrough()` with `z.looseObject({})`
- Replace `zodToJsonSchema()` with `z.toJSONSchema()`
- Remove `zod-to-json-schema` dependency
- Verify/update `ZodObject`/`ZodRawShape` exports
- Update error formatting if needed
