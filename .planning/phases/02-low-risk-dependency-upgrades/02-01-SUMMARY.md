# Phase 02 Plan 01: Dependency Security Upgrades Summary

**One-liner:** Zod 3.25.76 bridge upgrade + pip-audit/npm-audit to zero high/critical vulnerabilities

## Results

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Upgrade Zod to 3.25.x and fix npm vulnerabilities | a1c8795 | Done |
| 2 | Run pip-audit on Python dependencies | 3d92c41 | Done |

## Key Changes

### Task 1: Zod + npm audit
- Upgraded zod from 3.24.2 to 3.25.76 (bridge version, Zod 3 root API preserved)
- Fixed 4 of 5 original npm audit vulnerabilities (js-yaml, qs, transitive deps)
- 1 remaining high: `@modelcontextprotocol/sdk` <= 1.25.1 (DNS rebinding + ReDoS) -- requires Phase 3 SDK migration (1.8 -> 1.25+ breaks API: `tool_name` -> `name`)
- Zero application code changes

### Task 2: pip-audit
- Fixed 11 vulnerabilities across 3 packages via UV constraint-dependencies:
  - aiohttp 3.13.0 -> 3.13.3 (8 CVEs)
  - brotli 1.1.0 -> 1.2.0 (1 CVE)
  - pdfminer.six 20250506 -> 20260107 (2 CVEs)
- Updated requires-python from >=3.9 to >=3.10 (required by pdfminer.six + ocrmypdf)
- pip-audit reports zero known vulnerabilities

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] requires-python bump to >=3.10**
- **Found during:** Task 2
- **Issue:** pdfminer.six>=20251230 requires Python>=3.10, conflicting with project's >=3.9
- **Fix:** Updated requires-python to >=3.10 (ocrmypdf already required it)
- **Files modified:** pyproject.toml
- **Commit:** 3d92c41

### Known Remaining Issue

**npm audit: 1 high vulnerability in @modelcontextprotocol/sdk**
- Cannot fix without major version upgrade (1.8 -> 1.25+) which breaks TypeScript compilation
- Deferred to Phase 3 (MCP SDK Migration) where the full API migration is planned

## Files Modified

- `package.json` - zod version bump
- `package-lock.json` - updated dependency tree
- `pyproject.toml` - added constraint-dependencies, updated requires-python
- `uv.lock` - regenerated with security-fixed versions

## Verification

- `npm run build`: passes
- `npm test`: 139 passed, 1 failed (pre-existing paths.test.js failure)
- `uv run pytest __tests__/`: 696 passed, 18 failed (pre-existing, same as baseline)
- `npm audit`: 1 high (SDK, deferred to Phase 3)
- `pip-audit`: 0 vulnerabilities

## Duration

~5.5 minutes
