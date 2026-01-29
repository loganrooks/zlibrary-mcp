# Stack Migration Research

**Date**: 2026-01-28
**Scope**: Dependency upgrades and Python decomposition for Z-Library MCP cleanup
**Current state**: MCP SDK 1.8.0, Zod 3.24.2, env-paths 3.0.0, Python monolith 4968 lines

---

## 1. @modelcontextprotocol/sdk: 1.8.0 to 1.25.3

**Risk: HIGH** -- 17 versions behind, multiple breaking changes, Zod coupling

### Breaking Changes Affecting This Project

| Version | Change | Impact on This Project |
|---------|--------|----------------------|
| 1.10.0 | Streamable HTTP transport added (replaces SSE) | Low -- project uses StdioServerTransport only |
| 1.23.0 | Zod v4 support added (imports from `zod/v4` internally) | HIGH -- forces Zod upgrade decision |
| 1.24.x | Server class refactored to be framework-agnostic; Express moved to separate module | Low -- project uses raw Server class |
| 1.25.0 | Removed loose/passthrough types not in MCP spec; added Task types; spec compliance tightened | MEDIUM -- `z.object({}).passthrough()` in `DownloadBookToFileParamsSchema` may be affected |
| 1.25.0 | Protocol version bumped to `2025-11-25` | Low -- automatic |

### Import Path Changes

The project currently imports from:
```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListToolsRequestSchema, CallToolRequestSchema, ... } from '@modelcontextprotocol/sdk/types.js';
```

These paths may have changed in v1.25.x. The SDK was restructured with separate middleware packages. Verify that `/server/index.js`, `/server/stdio.js`, and `/types.js` subpath exports still exist.

### Known Issues with Upgrade

- **TypeScript compilation memory**: SDK v1.25.x causes severe memory consumption during TS compilation (OOM in CI). Monitor CI after upgrade.
- **JSON Schema draft**: SDK generates draft-07 via zod-to-json-schema; modern MCP clients expect draft-2020-12. The project explicitly uses `zod-to-json-schema` -- may need to update that too.
- **Dual Zod versions**: If project stays on Zod 3 while SDK uses Zod 4 internally, TypeScript TS2589 errors can occur from multiple zod versions in dependency tree.

### Migration Steps

1. Read full release notes: https://github.com/modelcontextprotocol/typescript-sdk/releases
2. Upgrade Zod FIRST (see section 2) -- SDK 1.23+ expects Zod v3.25+ minimum
3. `npm install @modelcontextprotocol/sdk@latest`
4. Fix any import path breakages (check subpath exports)
5. Replace `z.object({}).passthrough()` if MCP spec compliance enforcement rejects it
6. Verify `zod-to-json-schema` compatibility with new SDK version
7. Run full test suite; check for TS compilation memory issues
8. Test with actual MCP client (Claude Desktop) to verify protocol negotiation

### What NOT To Do

- Do NOT upgrade SDK before upgrading Zod -- will cause dual-version TypeScript errors
- Do NOT assume import paths are stable -- verify subpath exports after install
- Do NOT skip testing with a real MCP client -- protocol version negotiation changed

---

## 2. Zod 3.24.2 to Zod 4.x

**Risk: MEDIUM** -- Breaking changes exist but project usage is straightforward

### Project's Current Zod Usage (from `src/index.ts`)

```typescript
import { z, ZodObject, ZodRawShape } from 'zod';

// Patterns used:
z.object({ ... })
z.string().describe(...)
z.boolean().optional().default(false).describe(...)
z.number().int().optional().describe(...)
z.array(z.string()).optional().default([]).describe(...)
z.object({}).passthrough().describe(...)  // bookDetails
```

### Breaking Changes That Affect This Project

| Change | Impact | Fix |
|--------|--------|-----|
| `z.object({}).passthrough()` deprecated | Direct hit on `DownloadBookToFileParamsSchema` | Replace with `z.looseObject({})` |
| Error customization API (`message` to `error`) | Low -- project uses `.describe()` not custom errors | No change needed |
| `z.record()` requires two args | Check if used anywhere | Grep found no usage |
| `ZodObject` type export | May move or change | Verify `ZodObject` still exported from `'zod'` |

### No Impact (Project Does NOT Use These)

- `z.string().email()` / `.uuid()` / `.url()` (format methods moved to top-level) -- not used
- `z.function()` redesign -- not used
- `.merge()` deprecation -- not used
- `.strip()`, `.nonstrict()`, `.deepPartial()` removal -- not used
- `z.nativeEnum()` deprecation -- not used
- `z.refine()` type narrowing change -- not used

### Migration Steps

1. Upgrade: `npm install zod@latest`
2. Replace `z.object({}).passthrough()` with `z.looseObject({})` in `src/index.ts:78`
3. Verify `ZodObject` and `ZodRawShape` are still exported (used in line 3)
4. Update `zod-to-json-schema` to latest compatible version
5. Run type check: `npx tsc --noEmit`
6. Run tests

### Migration Tool Available

A codemod exists: https://www.hypermod.io/explore/zod-v4 -- but given the small surface area in this project, manual migration is safer and takes ~15 minutes.

### What NOT To Do

- Do NOT use `zod/v4` subpath import -- use the main `zod` export after upgrading to v4
- Do NOT upgrade zod-to-json-schema independently -- version must match Zod version

---

## 3. env-paths 3.0.0 to 4.0.0

**Risk: LOW** -- Only breaking change is Node.js version requirement

### Breaking Changes

| Change | Impact |
|--------|--------|
| Requires Node.js 20+ | Verify project's minimum Node version; if already on 20+, zero impact |

### API Changes

None. The API is identical between v3 and v4.

### Migration Steps

1. Verify project runs on Node.js 20+
2. `npm install env-paths@latest`
3. No code changes needed

---

## 4. Python Monolith Decomposition (rag_processing.py: 4968 lines, 55 functions)

**Risk: MEDIUM** -- Refactoring risk, but no external dependency changes

### Recommended Module Structure

Based on Python modular monolith best practices, split by domain responsibility:

```
lib/
  rag/
    __init__.py          # Public API (re-exports from submodules)
    extraction.py        # Text extraction (EPUB, PDF, TXT)
    processing.py        # Document processing pipeline
    chunking.py          # Text chunking and segmentation
    quality.py           # Quality analysis and scoring
    formatting.py        # Output formatting and cleanup
    utils.py             # Shared utilities (encoding detection, etc.)
    types.py             # Shared types/dataclasses
  python_bridge.py       # Unchanged -- calls into rag package
```

### Decomposition Strategy

1. **Identify clusters**: Group the 55 functions by call graph proximity and domain
2. **Extract types first**: Move dataclasses/TypedDicts to `types.py`
3. **Extract utilities**: Pure functions with no domain logic to `utils.py`
4. **Split by format**: PDF extraction, EPUB extraction, TXT extraction are natural boundaries
5. **Extract pipeline**: The main orchestration functions stay in `processing.py`
6. **Preserve public API**: `__init__.py` re-exports everything `python_bridge.py` calls
7. **Update imports in python_bridge.py**: Change `from rag_processing import X` to `from rag import X`

### Key Principles

- **Preserve the public API**: `python_bridge.py` should need minimal changes
- **No circular imports**: Dependency direction must be: processing -> extraction -> utils -> types
- **Test in parallel**: Keep `rag_processing.py` intact until new modules pass all tests
- **One PR per extraction**: Don't do it all at once

### What NOT To Do

- Do NOT split into one-function-per-file -- leads to circular import hell in Python
- Do NOT change function signatures during decomposition -- separate concern
- Do NOT delete `rag_processing.py` until the new package passes 100% of existing tests
- Do NOT decompose and change behavior simultaneously

---

## 5. Dependency Security Scanning

### npm audit

```bash
# Add to CI pipeline
npm audit --audit-level=high    # Fail on high/critical only
npm audit --json                # Machine-readable for dashboards

# Fix automatically (safe fixes only)
npm audit fix                   # Non-breaking fixes
npm audit fix --force           # Breaking fixes (use with caution)
```

### pip-audit

```bash
# Install
uv pip install pip-audit

# Run audit
pip-audit                       # Audit current environment
pip-audit --fix                 # Auto-fix vulnerabilities
pip-audit --json                # Machine-readable output
pip-audit -r requirements.txt   # Audit from requirements file

# CI integration
pip-audit --strict              # Exit non-zero on any finding
```

### Recommended CI Configuration

```yaml
# Add to GitHub Actions workflow
security-audit:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm audit --audit-level=high
    - run: uv run pip-audit --strict
```

### Best Practices

- Run both `npm audit` and `pip-audit` in CI on every PR
- Set `--audit-level=high` for npm to avoid blocking on low-severity advisories
- Use `pip-audit --ignore-vuln VULN-ID` for acknowledged false positives (document in code)
- Schedule weekly full audits beyond CI (cron job) for newly discovered CVEs

---

## 6. Recommended Upgrade Order

**Sequence matters.** Dependencies between upgrades dictate order.

| Step | Action | Risk | Time Est. | Depends On |
|------|--------|------|-----------|------------|
| 1 | env-paths 3.0 to 4.0 | LOW | 15 min | Nothing |
| 2 | Zod 3.x to 4.x | MEDIUM | 1 hour | Nothing |
| 3 | zod-to-json-schema update | LOW | 15 min | Step 2 |
| 4 | MCP SDK 1.8.0 to 1.25.x | HIGH | 2-4 hours | Steps 2, 3 |
| 5 | Add npm audit + pip-audit to CI | LOW | 30 min | Nothing (parallel) |
| 6 | Python decomposition (multi-PR) | MEDIUM | 4-8 hours | Nothing (parallel) |

### Critical Path

**env-paths (15 min) -> Zod (1 hr) -> zod-to-json-schema (15 min) -> MCP SDK (2-4 hr)**

Python decomposition and security scanning are independent and can proceed in parallel with the JS/TS upgrades.

---

## Sources

- [MCP TypeScript SDK Releases](https://github.com/modelcontextprotocol/typescript-sdk/releases)
- [MCP Specification Changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog)
- [Zod v4 Migration Guide](https://zod.dev/v4/changelog)
- [Zod v4 Release Notes](https://zod.dev/v4)
- [env-paths GitHub](https://github.com/sindresorhus/env-paths)
- [env-paths v4.0.0 Release](https://github.com/sindresorhus/env-paths/releases/tag/v4.0.0)
- [npm audit Documentation](https://docs.npmjs.com/cli/v9/commands/npm-audit/)
- [pip-audit on PyPI](https://pypi.org/project/pip-audit/)
- [Kraken Technologies: Python Monolith Organization](https://blog.europython.eu/kraken-technologies-how-we-organize-our-very-large-pythonmonolith/)
- [Modular Monolith in Python](https://breadcrumbscollector.tech/modular-monolith-in-python/)
