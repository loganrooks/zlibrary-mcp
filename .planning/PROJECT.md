# Z-Library MCP — Audit Cleanup & Modernization

## What This Is

A cleanup and modernization effort for the Z-Library MCP server, driven by comprehensive audits (health, issues, branches, roadmap) conducted on 2026-01-28. The project addresses technical debt, stale documentation, outdated dependencies, monolithic architecture, and branch hygiene — plus ports valuable unmerged features from the `get_metadata` branch.

## Core Value

Bring the codebase to a clean, current, maintainable state so that future feature development starts from a solid foundation — not 3-month-stale docs and a 5000-line monolith.

## Requirements

### Validated

- ✓ MCP server builds and runs — existing
- ✓ Search, download, and RAG processing functional — existing
- ✓ Retry logic with exponential backoff and circuit breaker — existing
- ✓ UV-based Python dependency management (v2.0.0) — existing
- ✓ Real PDF test corpus with ground truth validation — existing
- ✓ Comprehensive footnote system (continuation, corruption recovery) — existing
- ✓ Docker containerization — existing
- ✓ MCP protocol enhancements (outputSchema, structuredContent) — existing
- ✓ Advanced search with exact/fuzzy separation — existing
- ✓ Debug mode with verbose logging — existing
- ✓ HTTP connection pooling — existing

### Active

**Documentation & Docs Hygiene**
- [ ] Update all stale .claude/*.md docs (ROADMAP, ARCHITECTURE, PROJECT_CONTEXT, VERSION_CONTROL) to reflect current state
- [ ] Rewrite ROADMAP.md to reflect Phase 2 completion and actual current priorities
- [ ] Update ISSUES.md: close ISSUE-002 (v2.0.0), update ISSUE-008/009 partial status, update SRCH-001/RAG-002 to partially implemented
- [ ] Add "Last Verified" timestamps to technical docs

**Branch Cleanup**
- [ ] Delete 5 merged remote branches (development, phase-3-research, rag-eval-cleanup, rag-pipeline-enhancements-v2, rag-robustness-enhancement)
- [ ] Delete obsolete self-modifying-system branch
- [ ] Port get_metadata features to master (metadata scraping tool, enhanced filenames, author/title in search results)

**Code Quality**
- [ ] Fix bare exception handler in booklist_tools.py:267
- [ ] Refactor monolithic rag_processing.py (4968 lines) into modular processors (pdf, epub, txt, footnote detection, OCR)
- [ ] Clean up resolved BUG-X FIX comments (convert to CHANGELOG entries or remove)
- [ ] Convert DEBUG comments to proper logging
- [ ] Standardize Python import style (relative vs absolute)

**Dependency Updates**
- [ ] Update MCP SDK (1.8.0 → latest)
- [ ] Update env-paths (3.0 → 4.0)
- [ ] Migrate Zod 3.x → 4.x (breaking changes)
- [ ] Run npm audit and pip-audit for security vulnerabilities
- [ ] Add .tsbuildinfo to .gitignore

**Infrastructure & DX**
- [ ] Install pre-commit hooks (scripts exist but aren't linked)
- [ ] Verify BRK-001 (download+RAG combined workflow) still reproduces
- [ ] Add Python version check to setup script

**Security**
- [ ] Replace bare except with specific exception handling
- [ ] Run security scanners (npm audit, safety check)
- [ ] Specify parser in BeautifulSoup calls (XXE prevention)

### Out of Scope

- New feature development (search enhancements, download queue, RAG chunking, etc.) — this is cleanup only
- OS keychain for credentials — security improvement but too large for cleanup scope
- ML-based text recovery — research task, not cleanup
- Marginalia/citation pipeline integration — designed but not broken, separate effort
- Zod 4.x migration may be deferred if breaking changes are too extensive — evaluate during dependency phase

## Context

- Project graded C+ overall by health audit (functional but needs refactoring)
- Documentation is 3-4 months stale (last updated Oct 2025)
- rag_processing.py is 4968 lines with 11 high-complexity functions (process_pdf: 59 branches)
- MCP SDK is 17 versions behind; Zod is 2 major versions behind
- 5 merged branches and 1 obsolete branch cluttering remote
- get_metadata branch has valuable features (metadata tool, enhanced filenames, author/title search) that never got merged
- All critical bugs are resolved; test suite is healthy (78% Node.js, 82% Python coverage)
- Existing codebase map available at .planning/codebase/

## Constraints

- **No regressions**: All existing tests must continue passing after every change
- **Incremental commits**: Each logical change committed separately for easy rollback
- **Test-first for refactoring**: Existing tests must pass before and after each extraction from rag_processing.py
- **Dependency updates staged**: One dependency at a time with full test suite between stages

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Include get_metadata port | Valuable features that never got merged; 75 commits behind so manual port needed | — Pending |
| Manual port over rebase for get_metadata | 75-commit drift makes rebase risky; manual port allows incremental testing | — Pending |
| Full scope (all audit recommendations) | User wants everything addressed, not just quick wins | — Pending |
| Defer Zod 4.x if too disruptive | Breaking changes may cascade; evaluate during dependency phase | — Pending |

---
*Last updated: 2026-01-28 after initialization*
