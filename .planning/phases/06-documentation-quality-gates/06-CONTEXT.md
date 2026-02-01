# Phase 6: Documentation & Quality Gates - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Update all documentation to reflect the current post-cleanup codebase state (phases 1-7 complete, EAPI migration done, Python monolith decomposed, MCP SDK 1.25+). Install pre-commit hooks and CI pipeline to prevent future drift. Clean up ISSUES.md to reflect resolved/changed issues.

</domain>

<decisions>
## Implementation Decisions

### Doc scope & depth
- Claude determines which .claude/ docs are stale enough to warrant updating (not limited to the 4 in success criteria)
- Claude decides per-doc whether to archive (`.claude/archive/`) or delete obsolete docs, with bias toward archiving meaningful content
- Claude decides appropriate level of historical context per doc (current state vs brief history)
- Claude decides "Last Verified" line approach (manual vs automated)
- Claude decides whether CLAUDE.md structure needs restructuring or just reference updates
- Claude evaluates claudedocs/ per-item: archive useful history, delete noise
- Backfill ADRs for key Phase 1-7 decisions (EAPI migration, Python decomposition, MCP SDK upgrade)
- README.md must be updated to reflect current project state (UV, EAPI, MCP SDK 1.25+, decomposed Python)

### Pre-commit hooks
- Claude decides what hooks enforce (lint scope, test scope) and tooling (Husky vs alternatives)
- Claude decides whether Python linting (ruff/black) is included alongside TypeScript
- Hooks block commits on failure, but `--no-verify` bypass is available for WIP commits

### CI pipeline design
- Claude decides CI platform, pipeline steps, trigger strategy, and artifact generation
- Claude decides env verification level and branch protection rules
- Claude decides whether integration tests run in CI (security vs coverage tradeoff)
- Unit tests only in CI — no Z-Library credentials as CI secrets (user confirmed after re-read)

### ISSUES.md cleanup
- Re-triage all open issue severities against post-cleanup state
- Capture all known issues discovered during phases 1-7 (including Docker numpy issue, etc.)
- Claude decides handling of resolved issues (Resolved section vs deletion)
- Claude decides level of detail for partially-implemented items (SRCH-001, RAG-002)
- Claude decides whether to annotate Z-Library-specific assumptions (relevant for future Anna's Archive expansion)
- Claude decides where to capture future Anna's Archive direction (ISSUES.md vs elsewhere)

### Claude's Discretion
- Which specific docs warrant full rewrite vs refresh vs archive vs delete
- "Last Verified" implementation approach
- CLAUDE.md restructuring decision
- Pre-commit hook tooling and scope
- CI platform, triggers, steps, artifacts, branch protection
- ISSUES.md resolved issue handling format
- Partial issue detail level
- Z-Library-specific annotation approach

</decisions>

<specifics>
## Specific Ideas

- User plans to extend beyond Z-Library to Anna's Archive in the future — docs and issues should be aware of this without scope-creeping into it
- User prefers "you decide" for most implementation details — high trust in Claude's judgment for this phase

</specifics>

<deferred>
## Deferred Ideas

- Anna's Archive multi-source support — future milestone, not this phase. Captured for awareness.

</deferred>

---

*Phase: 06-documentation-quality-gates*
*Context gathered: 2026-02-01*
