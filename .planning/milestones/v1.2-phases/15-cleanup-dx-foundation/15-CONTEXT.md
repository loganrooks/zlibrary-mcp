# Phase 15: Cleanup & DX Foundation - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean the repository of dead files, build artifacts, and stale history. Install developer experience tooling (ESLint, Prettier, coverage) that prevents quality regression as the project evolves. Fix the one failing test. Add startup credential validation so users get clear errors instead of deferred Python crashes.

This phase installs the tools. Phase 17 wires them into CI as enforcement gates.

</domain>

<assumptions>
## Working Assumptions

These are the starting assumptions for how this phase will be implemented. Each was examined for grey areas (see Implementation Decisions). Research and planning should validate or revise them.

### Architecture
- ESLint + Prettier added as devDependencies; configured alongside existing lint-staged (Husky)
- Current lint-staged runs `bash -c 'tsc --noEmit'` for TS and `ruff check --fix && ruff format` for Python
- Startup credential validation added to `src/index.ts` before `server.connect()` — fast check in TypeScript, Python bridge already validates on use
- Coverage uses existing Jest `--coverage` flag and pytest-cov (to be added if not present)

### Dependencies
- ESLint v9 (flat config format, `eslint.config.js`) — v8 is EOL
- `@typescript-eslint/eslint-plugin` + `@typescript-eslint/parser`
- `eslint-config-prettier` (disables formatting rules that conflict with Prettier)
- `prettier` standalone
- `pytest-cov` for Python coverage (if not already a dependency)

### Sequencing
1. Git history cleanup (batch all remaining large blobs into one filter-repo pass → one force-push)
2. File cleanup (dead files, .gitignore fixes, stale artifacts)
3. Lint/format setup (ESLint + Prettier configured, lint-staged extended)
4. Startup validation (credential check in TypeScript)
5. Jest test fix (trivial regex update)
6. Coverage baseline measurement → threshold configuration

### Patterns
- ESLint flat config (`eslint.config.js`) not deprecated `.eslintrc`
- Prettier config in `.prettierrc` or `package.json`
- `.git-blame-ignore-revs` file to preserve git blame after Prettier reformats

</assumptions>

<decisions>
## Implementation Decisions

### Lint/Format Strictness

**ESLint rule set:**
- Start with `@typescript-eslint/recommended` — the community standard
- Add `no-unused-vars` and `consistent-type-imports` per DX-01
- Do NOT start with `strict` or `stylistic` presets — risk of hundreds of violations blocking progress
- Claude's discretion on specific rule additions as long as the base is `recommended`

**Prettier configuration:**
- MUST match the existing code style (the codebase was written consistently)
- Research should analyze the existing style: tab width, semicolons, quote style, trailing commas, print width
- Prettier is configured to reflect what already exists, not impose a new standard
- After initial config, run `prettier --write` on the whole codebase as a single commit
- Add `.git-blame-ignore-revs` pointing to that commit so `git blame` skips it

**Python linting:**
- Already handled by ruff (configured in pyproject.toml, enforced via lint-staged)
- No changes needed — leave as-is

**lint-staged integration:**
- Extend existing lint-staged config to run ESLint + Prettier on TS files
- Current: `"src/**/*.{ts,js}": "bash -c 'tsc --noEmit'"` + `"*.py": ["uv run ruff check --fix", "uv run ruff format"]`
- New: add ESLint check and Prettier format for TS files alongside existing tsc check

### Startup Validation

**Scope:** Credential presence check only. Don't over-engineer.
- Check `ZLIBRARY_EMAIL` and `ZLIBRARY_PASSWORD` environment variables in TypeScript before `server.connect()`
- Emit clear, actionable error message with exact instructions (what to set, where)
- Exit with non-zero code within 2 seconds (per DX-03)
- Do NOT check: network connectivity, UV installation, Python version — these are either already handled (venv-manager) or too slow for startup

**Architecture:** TypeScript-side check for speed. Python bridge already validates on first use (defense in depth, but the TS check catches it faster for better UX).

### Git History Cleanup

**Approach:** One final filter-repo pass to purge ALL remaining large blobs not tracked by LFS.
- The credential scrub (today) already rewrote history once. Batching all remaining cleanups avoids a third force-push later.
- Scope: all blobs >1MB that are NOT current LFS pointer files
- Research should scan git history to identify all targets before execution
- This is a one-way door — must be thorough

**Known target:** 74MB Kant PDF in `test_downloads/` (identified in deliberation)
**Unknown targets:** Research should scan for any other large blobs

### Coverage Thresholds

**Approach:** Measure current coverage first, then set thresholds.
- Separate thresholds for TypeScript (Jest) and Python (pytest) — the codebases have different test density
- Set each threshold at current coverage minus 5% — catches real regressions without being brittle
- Blocking from the start (not informational) — the deliberation decided "all quality gates"
- If coverage threshold causes issues, it's a two-way door (easy to adjust)

**Edge case:** Refactoring that removes dead code can paradoxically lower coverage percentage. The 5% buffer handles this.

### Claude's Discretion

The following areas have two-way-door decisions that Claude can resolve during planning/implementation:
- Exact ESLint rule additions beyond `recommended`
- Prettier specific settings (as long as they match existing code style)
- lint-staged command ordering (ESLint before or after tsc)
- Coverage report format (lcov, text, json)
- Exact error message wording for startup validation

</decisions>

<research_questions>
## Research Questions

Questions that emerged from grey area analysis. Phase research should investigate these.

| Question | Why It Matters | Type | Criticality |
|----------|----------------|------|-------------|
| Is ESLint v9 flat config compatible with lint-staged? | lint-staged passes individual files to ESLint. v9 changed file matching semantics — staged files might be silently skipped if glob patterns don't match | Material | Critical |
| What large blobs exist in git history beyond the known 74MB Kant PDF? | filter-repo is a one-way door (force-push). Must identify ALL targets before executing to avoid a third history rewrite | Material | Critical |
| Does filter-repo blob removal interact safely with LFS pointer files? | Our repo uses LFS for test_files/*.pdf. Blob removal must not corrupt LFS pointers in current commits | Material | Critical |
| What is the current test coverage for Jest and pytest? | Need baseline measurements to set thresholds. Can't configure DX-04 without knowing where we are | Material | Medium |
| Is pytest-cov already a dependency, or does it need to be added? | Coverage reporting requires the right tooling | Material | Low |
| What is the existing code style (tab width, semicolons, quotes, trailing commas)? | Prettier must match existing style, not impose new one. Research should sample 5-10 TS files to determine conventions | Formal | Medium |
| Does running ESLint + Prettier + tsc in lint-staged cause unacceptable pre-commit delay? | If pre-commit takes >10 seconds, developers will use --no-verify. Need to know if we should run tools in parallel or use eslint-plugin-prettier | Efficient | Medium |
| What dead files exist at repo root and in src/? | CLEAN-01 and CLEAN-02 require identifying targets. Research should enumerate candidates | Material | Medium |

</research_questions>

<failure_modes>
## Failure Modes

Identified risks with the obvious approach. Research and planning should address these.

1. **Prettier reformats everything → git blame destroyed**
   - Mitigation: `.git-blame-ignore-revs` file. Standard practice but must be set up correctly.
   - Must be documented in CONTRIBUTING.md (Phase 16) so contributors configure it locally.

2. **ESLint v9 + lint-staged incompatibility**
   - lint-staged passes staged file paths to ESLint. v9's flat config may not match individual file paths the same way.
   - Mitigation: Research should verify compatibility. Fallback: use ESLint v8 if v9 causes issues (v8 still works, just deprecated).

3. **Coverage threshold too tight → false blocks on refactoring**
   - Removing dead code or consolidating functions can reduce line count without reducing test quality.
   - Mitigation: 5% buffer below current baseline. Easy to adjust if needed.

4. **filter-repo corrupts LFS pointers**
   - Blob removal targeting old non-LFS binaries might accidentally touch LFS pointer files if the same filename was used.
   - Mitigation: Research should check blob SHAs vs LFS pointers. filter-repo can target specific blob hashes rather than filename patterns.

5. **Pre-commit hook becomes too slow**
   - Currently: tsc + ruff (fast). Adding: ESLint + Prettier. If combined >10s, developers bypass hooks.
   - Mitigation: Measure. If slow, consider running Prettier through ESLint (single pass) or only running ESLint on changed files.

</failure_modes>

<specifics>
## Specific Ideas

**From the deliberation (2026-03-19):**
- Issue #11 exists: real user got "server disconnected" — startup validation is the first line of defense
- 5 compiled .js files in `src/lib/` are currently untracked (circuit-breaker.js, errors.js, retry-manager.js, venv-manager.js, zlibrary-api.js) — these are build artifacts from tsc
- The credential scrub already rewrote history today — batch any remaining cleanup to minimize force-pushes
- `src/zlibrary_mcp.egg-info/` should also be gitignored (auto-generated by setuptools)

**From codebase investigation:**
- 928 total tests (129 Jest + 799 pytest) — coverage baseline likely high for Python, lower for TypeScript
- Node 22 changed `JSON.parse` error message format — the failing test expects old format: `Unexpected token T in JSON at position 0` vs new: `Unexpected token 'T', "This is not JSON" is not valid JSON`
- `src/index.js` exists as CJS fallback — needs determination: keep (document) or remove (dist/index.js is the entry point)

</specifics>

<deferred>
## Deferred Ideas

- **CI enforcement of lint/coverage** — Phase 17 (Quality Gates) will wire these tools into GitHub Actions
- **README badges for coverage** — Phase 16 (Documentation) will add badges once coverage is tracked
- **Multi-platform testing (macOS/Windows)** — deferred to v1.4+ per REQUIREMENTS.md
- **postinstall script for Python setup** — deferred to v1.4+ (PKG-F02)

</deferred>

<open_questions>
## Open Questions

| Question | Why It Matters | Criticality | Status |
|----------|----------------|-------------|--------|
| Should `src/index.js` (CJS fallback) be kept or removed? | CLEAN-02 says "src/ contains zero .js files" but this file may serve as npm CJS entry point | Critical | Pending — research should check if any consumer relies on CJS |
| Are there any other secrets or sensitive data in git history beyond the password we already scrubbed? | Another force-push is costly to coordinate. Must be comprehensive this time | Critical | Pending — research should scan |
| Does the existing eslint-config in any related project (e.g., serena, claude-enhanced) provide a reusable config? | Could save setup time and maintain consistency across the user's projects | Low | Pending — research can check |

</open_questions>

---

*Phase: 15-cleanup-dx-foundation*
*Context gathered: 2026-03-19*
