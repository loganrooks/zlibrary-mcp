# Feature Landscape: Codebase Cleanup/Modernization

**Domain:** Codebase health remediation for Z-Library MCP server (C+ audit grade)
**Researched:** 2026-01-28
**Overall confidence:** HIGH (based on direct codebase inspection, not external sources)

---

## Table Stakes

Features that MUST be done or the cleanup is incomplete. Without these, the codebase remains in its degraded state.

| # | Feature | Why Required | Complexity | Completeness Criteria |
|---|---------|-------------|------------|----------------------|
| T1 | **Dependency updates (MCP SDK)** | 17 versions behind (1.8.0 -> 1.25.3). Security/compat risk. | Med | All deps at latest compatible version; `npm audit` clean; tests pass |
| T2 | **Zod major version upgrade** | Zod 4.x is out (currently ^3.24). Major version = breaking changes accumulate. | Med | Zod 4.x installed; all schemas validated; zod-to-json-schema compatible |
| T3 | **Stale branch cleanup** | 6 stale remote branches, oldest from Apr 2025. Cognitive overhead. | Low | Only master + any active WIP branches remain; deleted branches documented |
| T4 | **Port get_metadata features** | Valuable unmerged work: metadata scraping, enhanced filenames, author/title in search (4 commits). Losing this = wasted effort. | Med-High | All 4 commits' features on master with tests passing; branch deleted |
| T5 | **Documentation freshness pass** | .claude/ docs are 3+ months stale. They reference deprecated approaches, old branches, wrong priorities. | Med | All .claude/*.md reflect current state; no references to dead branches/old issues; ROADMAP.md current |
| T6 | **Python monolith decomposition (Phase 1)** | rag_processing.py is 4968 lines. Unmaintainable. At minimum, extract logical modules. | High | rag_processing.py split into <=500-line modules with clear responsibilities; all tests pass; no behavior changes |
| T7 | **ISSUES.md triage** | 25 open issues. Some likely resolved, duplicated, or obsolete after months. | Low | Each issue verified current or closed; priorities re-ranked; count reduced |

### Order of Operations (Table Stakes)

```
T3 (branch cleanup) ──> T4 (port get_metadata) ──> T1+T2 (dep updates, parallel)
                                                         │
T7 (issue triage, independent) ────────────────────────  │
T5 (doc freshness, after T3+T4 so docs reflect reality)──┘
T6 (monolith decomposition, after deps stable)
```

**Rationale:** Clean branches first so you know what code matters. Port valuable work before deleting its branch. Update deps before refactoring (refactor against current APIs). Docs last because everything else changes the state they describe.

---

## Differentiators

Things that elevate this from "minimal cleanup" to "quality modernization." Not required, but the codebase is meaningfully better with them.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---------|-------------------|------------|-------|
| D1 | **CI/CD pipeline activation** | Automated quality gates prevent regression after cleanup | Med | .claude/CI_CD.md exists but pipeline may not be active; verify and activate |
| D2 | **Pre-commit hooks for lint/test** | Prevents new technical debt accumulation | Low | husky + lint-staged; run tests on changed files |
| D3 | **Python type hints + mypy** | 6k lines of Python with no type checking = bugs hiding | Med | Add type hints to public interfaces; mypy in CI |
| D4 | **Consolidate test infrastructure** | Jest + Pytest both healthy but no unified "run everything" with coverage reporting | Low | Single `npm test` runs both with combined coverage report |
| D5 | **Node.js engine version bump** | Currently `>=14.0.0` -- Node 14 is EOL since Apr 2023. Should be >=18 or >=20. | Low | Update engines field; verify no Node 14 compat hacks remain |
| D6 | **ADR review/cleanup** | Architecture Decision Records may reference obsolete decisions | Low | Review each ADR; mark superseded ones; ensure current decisions documented |
| D7 | **env-paths major update** | env-paths 3.x -> 4.x available | Low | Check breaking changes; update if straightforward |

---

## Anti-Features

Things to deliberately NOT do during this cleanup. Common traps that bloat scope.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Rewrite Python bridge in TypeScript** | Massive scope; Python has better doc-processing libs; this is the core value prop | Decompose the Python, don't replace it |
| **Add new MCP tools** | Cleanup scope, not feature scope. New tools = new surface area to maintain | Track in backlog; defer to post-cleanup milestone |
| **Migrate to different test framework** | Jest + Pytest work fine (78%/82% coverage). Migration is churn, not value | Keep existing frameworks; improve coverage if easy |
| **Refactor TypeScript architecture** | TS layer is thin (MCP server + bridge). Not the problem. | Focus energy on the 5k-line Python monolith |
| **Build download queue (DL-001)** | Listed in priorities but is a feature, not cleanup | Move to post-cleanup backlog |
| **Add fuzzy search (SRCH-001)** | Feature work, not cleanup | Move to post-cleanup backlog |
| **Perfect documentation** | Docs good enough to be accurate > docs that are exhaustive and pretty | Update for accuracy; don't rewrite for style |
| **100% test coverage** | 78-82% is healthy. Pushing to 100% has diminishing returns during cleanup | Fix any tests broken by refactoring; don't add coverage for coverage's sake |
| **Upgrade TypeScript to latest** | Currently ^5.5.3. TS 5.x is fine; no urgent reason to chase latest minor | Only upgrade if something requires it |

---

## Feature Dependencies

```
T3 (branch cleanup)
 └──> T4 (port get_metadata) -- must know branch state before porting
       └──> T1 (MCP SDK update) -- port first, then update APIs
             └──> T6 (monolith split) -- refactor against current deps

T2 (Zod 4) ──> T4 (port get_metadata) -- schemas may need Zod 4 compat
               independent of T1 otherwise

T7 (issue triage) -- fully independent, do anytime
T5 (doc freshness) -- do LAST (reflects final state)

D1-D7 -- all independent of each other; do after table stakes
```

---

## Cleanup Completeness Criteria

The cleanup is "done" when:

1. **Zero stale branches** -- only master and any active WIP
2. **All deps current** -- `npm outdated` shows nothing; `uv` deps current
3. **No monolith** -- largest Python file <=500 lines
4. **Docs match reality** -- .claude/ docs reference only current state
5. **Issues triaged** -- each issue verified, prioritized, or closed
6. **get_metadata merged** -- valuable work preserved on master
7. **Tests still pass** -- no regressions (78%+ Node, 82%+ Python)
8. **Node engine realistic** -- >=18 in engines field

The cleanup is "excellent" (differentiator level) when additionally:

9. **CI runs on PR** -- automated quality gate
10. **Pre-commit hooks active** -- lint + test on commit
11. **Python has type hints** -- at least public interfaces
12. **Single test command** -- `npm test` covers everything with reporting

---

## Sources

- Direct codebase inspection (HIGH confidence -- all findings verified against actual files)
- `npm outdated` output for dependency versions
- `git branch -a` and `git log` for branch state
- `wc -l` for monolith size verification
- No external sources needed; this is project-specific analysis
