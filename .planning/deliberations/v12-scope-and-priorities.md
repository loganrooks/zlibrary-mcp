# Deliberation: v1.2 Scope — Ship a Solid Base for Deployment and Contribution

**Date:** 2026-03-19
**Status:** Concluded
**Trigger:** User strategic assessment — "where are we at and what should we do next?" with emphasis on deployment readiness, CI, testing, organization, and enabling external contributors
**Affects:** v1.2 milestone scope (phases 15-19), potentially v1.3 planning
**Related:**
- .planning/ROADMAP.md (v1.2 phases 15-19)
- .planning/REQUIREMENTS.md (35 requirements, 11 completed)
- .planning/STATE.md (Phase 14 complete, 21% of v1.2)

## Situation

The project has shipped two feature milestones (v1.0 Audit Cleanup, v1.1 Quality & Expansion) totaling 12 phases and 43 plans. The v1.2 milestone ("Production Readiness") is 21% complete — phases 13-14 (bug fixes + test infrastructure) are done, with 5 phases remaining (15-19).

The user's priorities have crystallized: this should be a deployable, contributable MCP server. The remaining v1.2 roadmap includes both infrastructure work (phases 15, 18, 19) and feature refinement (phases 16-17: structured RAG output and quality scoring). The question is whether these feature phases belong in the critical path.

### Evidence Base

| Source | What it shows | Corroborated? | Signal ID |
|--------|--------------|---------------|-----------|
| `npm pack --dry-run` | 976 files shipped, no `files` field in package.json | Yes (verified: `files` field is `undefined`) | informal |
| `.github/workflows/ci.yml` | 3-job CI exists (test-fast, test-full, audit) but no release/publish workflow | Yes (read file directly) | informal |
| `package.json` | `bin`, `main`, `exports` properly configured; `prepublishOnly` runs build | Yes (verified via node -e) | informal |
| `tsconfig.json` | outDir=dist, rootDir=src — confirms src/lib/*.js are misplaced build artifacts | Yes (read file) | informal |
| Test count | 928 tests (129 Jest + 799 pytest), 15 Python modules lack dedicated tests | Yes (file enumeration) | informal |
| Docker setup | Production Dockerfile + SuperGateway + docker-compose with health checks exist | Yes (read files) | informal |
| Codebase structure | Clean dual-language architecture, well-decomposed lib/rag/ (31 modules) | Yes (directory scan) | informal |
| No startup credential validation | Server starts successfully without ZLIBRARY_EMAIL/PASSWORD; fails on first API call | Yes (read src/index.ts) | informal |
| No ESLint/Prettier | TypeScript checked via tsc only; no style enforcement for JS/TS | Yes (no config files found) | informal |
| No CONTRIBUTING.md | No contributor guide exists; .claude/ docs are internal-facing | Yes (file search) | informal |
| No CHANGELOG.md | No changelog; commit convention defined but not automated | Yes (file search) | informal |
| GitHub Issue #11 | Real user ("Torrchy") got "server disconnected" in Claude — filed 2026-02-27, no response | Yes (gh issue view 11) | informal |

## Framing

**Core question:** How should we scope and sequence the remaining v1.2 work to build a solid foundation for both external deployment and developer contribution, and what (if anything) should be deferred?

**Adjacent questions:**
- Is the RAG pipeline output quality sufficient to ship without phases 16-17?
- What's the minimum viable contributor experience? (docs, linting, CI, test clarity)
- Should the npm package story be simplified (e.g., postinstall script for Python setup)?
- How do we handle multi-platform support (macOS/Windows) given the Python dependency?
- Should we add code style tooling (ESLint/Prettier) as part of this base?

## Analysis

### Option A: Narrow v1.2 to Infrastructure Only — Defer RAG Refinements to v1.3

- **Claim:** Remove phases 16 (Structured RAG Output) and 17 (Quality Scoring) from v1.2. Resequence as: 15 (Cleanup) → 18 (Documentation) → 19 (Packaging). Ship v1.2 as "production-ready base." Move phases 16-17 to v1.3 as "RAG Pipeline Refinement."
- **Grounds:** The current RAG pipeline already works — v1.1 produces body.md + _meta.json output. Phases 16-17 refine this (unified schema, automated scoring) but aren't blocking anyone from using the server. Meanwhile, the deployment blockers (976-file npm package, no contributor docs, no release automation) are real barriers.
- **Warrant:** External users and contributors interact with the deployment surface (install, configure, contribute) before they interact with RAG quality internals. Shipping the infrastructure base first unblocks adoption; RAG refinements can follow.
- **Rebuttal:** If RAG output quality is the project's core differentiator, shipping without quality scoring means you can't prevent regressions. A contributor might break the pipeline without knowing. Also, structured output (phase 16) changes the API surface, which is harder to do after people start depending on current format.
- **Qualifier:** Probably the right call — the RAG pipeline has 799 tests and 34/34 recall regression tests already, so quality isn't unguarded.

### Option B: Keep All 5 Phases but Resequence for Deployment Priority

- **Claim:** Keep phases 15-19 but reorder: 15 (Cleanup) → 19 (Packaging) → 18 (Docs) → 16 (Structured Output) → 17 (Quality Scoring). This front-loads deployment readiness while keeping RAG work in v1.2.
- **Grounds:** Phase 19 (Packaging) solves the most critical deployment blocker (`files` field, npm publish, CI pipeline). Moving it before documentation means you can ship a working npm package sooner, then polish docs and RAG after.
- **Warrant:** The packaging work is mechanical and well-scoped. Getting it done early means everything after it is already "shippable" — each subsequent phase just improves what's already deployable.
- **Rebuttal:** Phase 18 (Documentation) is a dependency for Phase 19 in the current roadmap — README badges, API docs, and contributor guide are part of what makes a published package usable. Publishing without docs is shipping an empty box.
- **Qualifier:** Presumably good if we partially decouple: do the packaging-critical parts of docs (README, API reference) alongside Phase 19, then do contributor guide and architecture docs separately.

### Option C: Expand v1.2 Scope — Add Developer Experience Phase

- **Claim:** Add a new phase (15.5 or post-15) focused on developer experience: ESLint + Prettier, coverage reporting in CI, CONTRIBUTING.md, `npm run setup` convenience script, startup validation. Then continue with 16-19.
- **Grounds:** The codebase has no JS/TS linting beyond tsc. No code style enforcement. No contributor guide. Coverage isn't tracked. These gaps are all "contributor friction" — they make it harder for others to participate confidently.
- **Warrant:** Developer experience is multiplicative: every hour invested in DX pays back across every contributor hour. For an open-source MCP server, this is arguably more important than RAG refinements.
- **Rebuttal:** Adding scope to an already-long milestone (7 phases, 5 remaining) risks scope creep. ESLint/Prettier can be introduced as part of Phase 15 (Cleanup) without a separate phase. And the project currently has one contributor (the user), so "enabling contributors" is speculative.
- **Qualifier:** Probably over-engineering the milestone structure. The DX improvements are real but can be folded into existing phases.

## Tensions

1. **Ship fast vs. ship complete**: Narrowing scope (Option A) gets something out the door but defers quality infrastructure. Keeping everything (Option B) means a longer timeline to first external release.

2. **Current users vs. future contributors**: The user currently uses this as a personal MCP server. Optimizing for external deployment is forward-looking — but that's exactly what they're asking for.

3. **RAG output format stability**: Phase 16 changes the output structure. If someone builds on the current format and Phase 16 changes it later, that's a breaking change. But if no one is using it yet externally, the window for breaking changes is now.

4. **Feature phases as deployment dependencies**: Phase 16 (structured output) arguably IS deployment-relevant — it defines the API contract external users will depend on. Quality scoring (Phase 17) is purely internal infrastructure.

## Recommendation

**Decision: Option A — Thorough Infrastructure Focus**

Narrow v1.2 to deployment + contribution readiness. Defer RAG pipeline refinements (structured output, quality scoring) to v1.3. But "narrow" means scope, not effort — the execution is thorough.

### Scope Decisions

**Kept in v1.2:**
- Repo cleanup (Phase 15 as planned)
- Developer experience: ESLint + Prettier, startup validation, CONTRIBUTING.md
- Documentation: README rewrite, API docs, CHANGELOG, architecture diagram
- Packaging: npm `files` field, pack size validation, npm publish workflow
- Docker: verify and document both install paths (npm + Docker) as first-class
- Quality gates: CI regression prevention, package integrity checks, doc freshness automation
- Issue #11 response: diagnose and fix the "server disconnected" experience

**Deferred to v1.3 (RAG Pipeline Refinement):**
- Phase 16: Structured RAG Output (body.md + footnotes.md + metadata.json)
- Phase 17: Quality Scoring (automated precision/recall)

**Rationale:** The RAG pipeline works (799 tests, 34/34 recall passing). The deployment surface is what's broken (issue #11). Fix the surface first, refine internals after.

### Quality Gates Architecture

The user specifically asked for quality gates that prevent degradation over time. This means the v1.2 deliverable isn't just "fix the current state" but "build the automation that keeps it fixed." Three layers:

**Layer 1: CI Catches Regressions (every PR)**
- TypeScript type-check (tsc --noEmit) — already exists
- ESLint + Prettier check — NEW
- Jest + Pytest fast suite — already exists
- npm audit + pip-audit — already exists
- Coverage thresholds (fail if coverage drops) — NEW

**Layer 2: Package Integrity (every PR + release)**
- `npm pack --dry-run` size check (fail if >10MB) — NEW
- Startup smoke test (server boots, responds to MCP handshake, exits cleanly) — NEW
- Build validation (all critical files present) — already exists
- Docker build + health check — NEW in CI

**Layer 3: Doc Freshness (every PR that touches src/)**
- Check that README tool list matches registered MCP tools — NEW
- Check that .env.example lists all referenced env vars — NEW
- Validate setup instructions against actual setup script — aspirational, may be manual gate

### Phase Structure

The old phases 15-19 are replaced by:

1. **Phase 15: Cleanup & DX Foundation** — gitignore fixes, dead file removal, ESLint + Prettier, startup credential validation, coverage reporting
2. **Phase 16: Documentation & Distribution** — README rewrite, API docs, CONTRIBUTING.md, CHANGELOG, npm `files` field, Docker verification, both install paths documented and tested
3. **Phase 17: Quality Gates & Release Pipeline** — CI quality gates (all three layers), release automation (semantic-release or manual workflow), npm publish workflow, respond to issue #11

This preserves the existing phase numbering continuation while replacing the content.

## Predictions

**If adopted, we predict:**

| ID | Prediction | Observable by | Falsified if |
|----|-----------|---------------|-------------|
| P1 | `npm pack` drops from 976 files to <50 files, tarball <5MB | `npm pack --dry-run` after Phase 16 | Still >100 files or >10MB |
| P2 | A new contributor can clone, setup, and run tests within 30 minutes using CONTRIBUTING.md alone | Manual test with fresh checkout on macOS | Setup takes >1 hour or requires undocumented steps |
| P3 | No external users hit "server disconnected" with no diagnostic info after Phase 15 | Issue tracker + startup behavior | Bug report about cryptic error with no guidance |
| P4 | CI catches a real regression (lint, type, test, or package size) within the first 5 PRs after quality gates ship | PR history after Phase 17 | 10+ PRs merge with no gate ever triggering |
| P5 | Issue #11 reporter can successfully install and run the server using updated docs | GitHub issue #11 thread | Reporter confirms still broken or no response |
| P6 | Docker and npm install paths both verified working in CI | CI workflow logs | Either path untested or broken in CI |

## Decision Record

**Decision:** Narrow v1.2 to thorough production readiness (3 infrastructure phases). Defer RAG refinements to v1.3.
**Decided:** 2026-03-19
**Implemented via:** Phases 15-17 (replacing old phases 15-19). Old phases 16-17 move to v1.3.
**Signals addressed:** GitHub Issue #11 (real user deployment failure)
