# Domain Pitfalls

**Domain:** MCP Server Cleanup/Modernization
**Researched:** 2026-01-28
**Overall confidence:** HIGH (based on codebase inspection + verified documentation)

## Critical Pitfalls

### Pitfall 1: MCP SDK Server Class Migration — Low-Level API to High-Level API

**What goes wrong:** The codebase uses the low-level `Server` class with `setRequestHandler(ListToolsRequestSchema, ...)` and `setRequestHandler(CallToolRequestSchema, ...)` (see `src/index.ts:645-740`). The modern SDK provides `McpServer` with `server.registerTool()` (or the deprecated-but-functional `server.tool()`). Upgrading the SDK version without migrating the server class means you're on a supported but increasingly undocumented path. But migrating to `McpServer` requires rewriting the entire tool registration and dispatch system — it's not a drop-in replacement.

**Why it happens:** The `Server` class still works in 1.25.x, so teams bump the version, see tests pass, and move on. Then they discover `setRequestHandler` behavior has subtly changed (e.g., protocol version negotiation, capability advertisement) and things break at runtime, not compile time.

**Consequences:** Runtime failures with MCP clients. Silent capability mismatches. Tests pass but real clients reject the server.

**Prevention:**
1. Pin to an intermediate version first (e.g., 1.12.x) and validate with a real MCP client (not just unit tests)
2. Decide upfront: stay on `Server` class or migrate to `McpServer`. Don't half-migrate.
3. If migrating to `McpServer`, do it as a standalone phase AFTER the version bump is stable.

**Detection:** MCP client connection failures. Tool listings that don't match. Capability negotiation errors in debug logs.

**Phase:** SDK Upgrade phase. Decision point before starting.

---

### Pitfall 2: Zod 3 to 4 — Schema Behavior Changes Break Validation Silently

**What goes wrong:** The project uses `z.object()` schemas extensively for tool parameter validation (`src/index.ts:42-48`), and uses `zodToJsonSchema()` to convert them for MCP tool definitions. Zod 4 changes default-inside-optional behavior: `z.string().default("x").optional()` now returns the default instead of `undefined`. Also, `zodToJsonSchema` must be compatible with Zod 4's internal representation — the `zod-to-json-schema` package may need its own upgrade.

**Why it happens:** Zod 4 is semantically different but syntactically identical. Tests that check "does parsing succeed" pass; tests that check "what exact value came out" may not exist.

**Consequences:** Tool parameters silently get wrong default values. JSON Schema output changes, confusing MCP clients about expected inputs. `ZodError.errors` renamed to `ZodError.issues` breaks error handling code.

**Prevention:**
1. Use the [zod-v3-to-v4 codemod](https://github.com/nicoespeon/zod-v3-to-v4) for automated migration
2. Audit every `.default()` + `.optional()` combination in schemas
3. Snapshot-test the JSON Schema output of every tool before and after migration — diff must be intentional
4. Upgrade `zod-to-json-schema` in lockstep with Zod
5. Consider importing `zod/v4` explicitly during transition (subpath imports are permanent)

**Detection:** Diff JSON Schema output before/after. Test tool invocations with missing optional parameters.

**Phase:** SDK Upgrade phase, immediately after or alongside MCP SDK bump (they're coupled via Zod peer dependency).

---

### Pitfall 3: Python Monolith Decomposition — Breaking Import Chains in rag_processing.py

**What goes wrong:** `rag_processing.py` is 4,968 lines. Decomposing it into modules will break the Python bridge interface (`python_bridge.py` imports from it, and `src/lib/zlibrary-api.ts` calls Python via PythonShell with specific script paths). Every extracted module changes import paths, and the PythonShell invocation in Node.js hardcodes script paths like `lib/python_bridge.py`.

**Why it happens:** The Node.js-Python boundary is stringly-typed (PythonShell passes script paths and JSON). There's no type checking across the boundary. You refactor Python, tests pass in Python, but Node.js integration breaks because it's calling the old script path or expecting the old JSON shape.

**Consequences:** Integration failures that only surface in end-to-end testing. Python unit tests pass, Node.js unit tests pass (mocked), but the actual bridge is broken.

**Prevention:**
1. Define the Python bridge contract FIRST (script paths, function signatures, JSON schemas) — write it down
2. Keep `python_bridge.py` as the stable entry point; only refactor what it imports internally
3. Add integration tests that actually invoke PythonShell before decomposing
4. Extract one module at a time with integration test validation between each extraction
5. Never change the PythonShell entry point path during decomposition

**Detection:** Integration test failures. `PythonShell` errors about missing modules or changed function signatures.

**Phase:** Python Decomposition phase. Must have integration test harness BEFORE starting.

---

### Pitfall 4: Porting from Stale Branch — Silent Merge Conflicts in Modified Files

**What goes wrong:** `feature/rag-robustness-enhancement` is 120 commits behind master. Cherry-picking or rebasing features from it will hit merge conflicts in files that were modified on both sides. The dangerous case isn't the conflicts Git catches — it's the ones it auto-merges incorrectly (semantic conflicts where both sides changed nearby but different lines).

**Why it happens:** Git's 3-way merge is syntactic, not semantic. If master refactored a function signature and the stale branch added a call to the old signature, Git may merge cleanly but the code is broken.

**Consequences:** Compiles but crashes at runtime. Tests pass individually but fail in combination. Subtle bugs that surface weeks later.

**Prevention:**
1. Do NOT rebase or merge the stale branch directly
2. Instead: read the stale branch diff, understand the intent, then re-implement on master
3. For each feature on the stale branch, create a checklist: what was the goal, what files changed, what's the equivalent change on current master
4. Run full test suite after porting each feature (not just at the end)
5. Use `git log --oneline master..origin/feature/rag-robustness-enhancement` to inventory what's there, then triage: port / skip / rewrite

**Detection:** `git diff --stat` between branches to see overlap. Files modified on both sides are high-risk.

**Phase:** Feature Porting phase. Must follow SDK upgrade (so you port onto stable foundation).

## Moderate Pitfalls

### Pitfall 5: Documentation Batch Update — Docs Drift Back Immediately

**What goes wrong:** Batch-updating 3-month-stale docs feels productive but creates a false sense of completion. The docs describe the codebase at one point in time. If the cleanup changes architecture (SDK upgrade, Python decomposition), the freshly-updated docs are stale again within days.

**Prevention:**
1. Update docs LAST, after all code changes are complete
2. Only update docs that describe stable interfaces (API, configuration, setup)
3. For architecture docs, update them as part of the code change PR (not separately)
4. Delete docs that describe deprecated features rather than updating them

**Phase:** Documentation phase must be the FINAL phase, not parallel with code changes.

---

### Pitfall 6: Deleting Remote Branches — Losing Unmerged Work

**What goes wrong:** Deleting 6 stale remote branches seems like cleanup, but some may contain unmerged work worth porting. Once deleted, the commits are still in the reflog briefly but effectively lost for collaborators.

**Prevention:**
1. Before deleting ANY branch, run `git log master..origin/<branch> --oneline` to see unmerged commits
2. Create a manifest: for each branch, record its purpose, unmerged commit count, and decision (delete / port / archive)
3. For branches with unmerged work to port: tag them first (`git tag archive/<branch-name> origin/<branch-name>`)
4. Delete branches only after feature porting phase is complete
5. Never delete a branch that another contributor might be using — check with `git log --all --author` if needed

**Detection:** Non-zero unmerged commit count on `git log master..origin/<branch>`.

**Phase:** Branch Cleanup phase. Must happen AFTER Feature Porting phase (so you've already extracted what you need).

---

### Pitfall 7: MCP SDK TypeScript Compilation Memory Explosion

**What goes wrong:** The MCP SDK package is [known to cause severe memory consumption during TypeScript compilation](https://github.com/modelcontextprotocol/typescript-sdk/issues/985), leading to OOM errors in CI/CD. Upgrading to 1.25.x may push your build past memory limits that worked with 1.8.0.

**Prevention:**
1. Test the build locally with `NODE_OPTIONS=--max-old-space-size=4096` before pushing to CI
2. Monitor `tsc` memory usage before and after SDK upgrade
3. If OOM occurs, consider using `skipLibCheck: true` in tsconfig as a workaround
4. Pin TypeScript version — newer TS versions may interact differently with SDK types

**Detection:** CI build failures with "JavaScript heap out of memory". Local builds that are noticeably slower.

**Phase:** SDK Upgrade phase. First thing to validate after bumping the version.

---

### Pitfall 8: Test Suite Green Doesn't Mean Integration Works

**What goes wrong:** The project's Jest tests mock the Python bridge (`src/lib/zlibrary-api.ts` mocked). Python tests run independently via pytest. Neither tests the actual Node.js-to-Python integration. During cleanup, both test suites stay green while the actual bridge breaks.

**Prevention:**
1. Add at least one smoke test that runs the real PythonShell invocation
2. After each major change phase, run a manual integration test (start server, call a tool)
3. Consider a Docker-based integration test that exercises the full stack

**Detection:** Manual testing reveals failures that unit tests missed. Server starts but tools return errors.

**Phase:** Every phase — this is a cross-cutting concern. Add integration smoke test in the first phase.

## Minor Pitfalls

### Pitfall 9: `zod-to-json-schema` Version Incompatibility

**What goes wrong:** The project uses `zod-to-json-schema@^3.24.5`. This package may not support Zod 4 output formats. Upgrading Zod without checking this dependency creates runtime errors when tool schemas are generated.

**Prevention:** Check `zod-to-json-schema` compatibility matrix before upgrading Zod. The MCP SDK 1.25.x may handle schema conversion internally, making this dependency unnecessary.

**Phase:** SDK Upgrade phase, dependency audit step.

---

### Pitfall 10: Python Virtual Environment Path Assumptions

**What goes wrong:** During Python decomposition, new modules may need additional dependencies. The UV-managed `.venv/` must be updated, and `pyproject.toml` must reflect new internal package structure if creating subpackages.

**Prevention:** Run `uv sync` after any changes to Python package structure. Test that `setup-uv.sh` still works from scratch.

**Phase:** Python Decomposition phase.

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| SDK Upgrade | Server class API mismatch (P1), TS OOM (P7) | Validate with real MCP client, monitor memory |
| Zod Migration | Silent schema behavior change (P2), json-schema compat (P9) | Snapshot-test JSON Schema output, upgrade in lockstep |
| Python Decomposition | Bridge contract breakage (P3), venv issues (P10) | Keep entry point stable, integration test first |
| Feature Porting | Semantic merge conflicts (P4) | Re-implement don't rebase, test after each port |
| Branch Cleanup | Losing unmerged work (P6) | Tag before delete, manifest of decisions |
| Documentation | Immediate staleness (P5) | Do LAST, tie to code PRs |
| All Phases | Mock-only tests hide breakage (P8) | Add integration smoke test first |

## Recommended Phase Ordering (Based on Pitfall Analysis)

1. **Integration Test Harness** — prevents P3, P4, P8 from going undetected
2. **SDK + Zod Upgrade** — foundational; everything else builds on this
3. **Python Decomposition** — requires stable bridge contract
4. **Feature Porting** — requires stable codebase to port onto
5. **Branch Cleanup** — after porting extracts what's needed
6. **Documentation** — last, describes final state

## Sources

- [MCP TypeScript SDK Releases](https://github.com/modelcontextprotocol/typescript-sdk/releases) (HIGH confidence)
- [MCP Specification Changelog 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/changelog) (HIGH confidence)
- [Zod v4 Migration Guide](https://zod.dev/v4/changelog) (HIGH confidence)
- [Zod v4 Versioning](https://zod.dev/v4/versioning) (HIGH confidence)
- [zod-v3-to-v4 Codemod](https://github.com/nicoespeon/zod-v3-to-v4) (HIGH confidence)
- [Zod 3.25 includes Zod 4 causing breakage](https://github.com/colinhacks/zod/issues/4923) (HIGH confidence)
- [MCP SDK TypeScript Compilation Memory Issues](https://github.com/modelcontextprotocol/typescript-sdk/issues/985) (HIGH confidence)
- [SDK V2 Discussion](https://github.com/modelcontextprotocol/typescript-sdk/issues/809) (MEDIUM confidence)
- [Strangler Fig Pattern for Monolith Decomposition](https://medium.com/@stephen.biston/practical-monolith-decomposition-the-strangler-fig-pattern-1aa49988072f) (MEDIUM confidence)
- [Modular Monolith in Python](https://breadcrumbscollector.tech/modular-monolith-in-python/) (MEDIUM confidence)
