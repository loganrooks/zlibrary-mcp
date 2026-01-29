# Requirements: Z-Library MCP Audit Cleanup

**Defined:** 2026-01-28
**Core Value:** Bring codebase to clean, current, maintainable state before new feature development

## v1 Requirements

### Integration Testing

- [ ] **TEST-01**: Integration smoke test that invokes real PythonShell bridge from Node.js
- [ ] **TEST-02**: Docker-based E2E test that starts MCP server and calls a tool

### Dependency Updates

- [ ] **DEP-01**: Update env-paths 3.0 to 4.0
- [ ] **DEP-02**: Migrate Zod 3.x to 4.x (replace `z.object({}).passthrough()` with `z.looseObject({})`, verify `ZodObject`/`ZodRawShape` exports, update `zod-to-json-schema`)
- [ ] **DEP-03**: Update MCP SDK 1.8.0 to latest (verify import paths, test with real MCP client, decide Server vs McpServer class)
- [ ] **DEP-04**: Run npm audit and pip-audit; fix high/critical vulnerabilities
- [ ] **DEP-05**: Add .tsbuildinfo to .gitignore

### Code Quality

- [ ] **QUAL-01**: Fix bare exception handler in booklist_tools.py:267
- [ ] **QUAL-02**: Decompose rag_processing.py into modular package (rag/ with processors, detection, quality, ocr, xmark, utils submodules)
- [ ] **QUAL-03**: Create facade in rag_processing.py that re-exports public API (zero breakage to existing imports)
- [ ] **QUAL-04**: Clean up resolved BUG-X FIX comments
- [ ] **QUAL-05**: Convert DEBUG comments to proper logging
- [ ] **QUAL-06**: Specify parser in BeautifulSoup calls (XXE prevention)

### Branch Cleanup

- [ ] **GIT-01**: Delete 5 merged remote branches
- [ ] **GIT-02**: Delete obsolete self-modifying-system branch
- [ ] **GIT-03**: Port metadata scraping tool from get_metadata branch
- [ ] **GIT-04**: Port enhanced filename conventions from get_metadata branch
- [ ] **GIT-05**: Port author/title in search results from get_metadata branch
- [ ] **GIT-06**: Delete get_metadata branch after port complete

### Documentation

- [ ] **DOC-01**: Update ROADMAP.md to reflect Phase 2 completion and current state
- [ ] **DOC-02**: Update PROJECT_CONTEXT.md with v2.0.0 status (UV migration)
- [ ] **DOC-03**: Update ARCHITECTURE.md with current test coverage and components
- [ ] **DOC-04**: Update VERSION_CONTROL.md and CI_CD.md to current dates
- [ ] **DOC-05**: Triage ISSUES.md (close ISSUE-002, update ISSUE-008/009 partial status, update SRCH-001/RAG-002)
- [ ] **DOC-06**: Add "Last Verified" timestamps to technical docs
- [ ] **DOC-07**: Install pre-commit hooks (scripts exist, need linking)

### Infrastructure

- [ ] **INFRA-01**: Add npm audit + pip-audit to CI pipeline
- [ ] **INFRA-02**: Add Python version check to setup script
- [ ] **INFRA-03**: Verify BRK-001 (download+RAG combined workflow) status

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Feature Development

- **FEAT-01**: Download queue management (DL-001)
- **FEAT-02**: Search result caching layer
- **FEAT-03**: Semantic chunking for RAG pipeline
- **FEAT-04**: Marginalia/citation pipeline integration
- **FEAT-05**: Multi-column layout detection
- **FEAT-06**: Adaptive resolution pipeline (72→150→300 DPI)
- **FEAT-07**: OS keychain for credentials

### Developer Experience

- **DX-01**: Hot reload for Python changes
- **DX-02**: Performance profiling tools
- **DX-03**: Development fixtures/mocks
- **DX-04**: Documentation archival automation

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rewrite Python bridge in TypeScript | Massive scope; Python has better doc-processing libs |
| Add new MCP tools (beyond get_metadata port) | Cleanup scope, not feature scope |
| Migrate test framework | Jest + Pytest work fine at 78%/82% coverage |
| Refactor TypeScript architecture | TS layer is thin, not the problem |
| Push to 100% test coverage | 78-82% is healthy; diminishing returns |
| ML-based text recovery | Research task, not cleanup |
| Upgrade TypeScript to latest minor | ^5.5.3 is fine; no urgent reason |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 1 | Pending |
| DEP-01 | Phase 2 | Pending |
| DEP-02 | Phase 2 | Pending |
| DEP-03 | Phase 3 | Pending |
| DEP-04 | Phase 2 | Pending |
| DEP-05 | Phase 2 | Pending |
| QUAL-01 | Phase 2 | Pending |
| QUAL-02 | Phase 4 | Pending |
| QUAL-03 | Phase 4 | Pending |
| QUAL-04 | Phase 4 | Pending |
| QUAL-05 | Phase 4 | Pending |
| QUAL-06 | Phase 2 | Pending |
| GIT-01 | Phase 5 | Pending |
| GIT-02 | Phase 5 | Pending |
| GIT-03 | Phase 5 | Pending |
| GIT-04 | Phase 5 | Pending |
| GIT-05 | Phase 5 | Pending |
| GIT-06 | Phase 5 | Pending |
| DOC-01 | Phase 6 | Pending |
| DOC-02 | Phase 6 | Pending |
| DOC-03 | Phase 6 | Pending |
| DOC-04 | Phase 6 | Pending |
| DOC-05 | Phase 6 | Pending |
| DOC-06 | Phase 6 | Pending |
| DOC-07 | Phase 6 | Pending |
| INFRA-01 | Phase 6 | Pending |
| INFRA-02 | Phase 6 | Pending |
| INFRA-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-28*
*Last updated: 2026-01-28 after initial definition*
