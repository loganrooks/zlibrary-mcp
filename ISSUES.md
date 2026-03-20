# Z-Library MCP - Issues & Technical Debt

<!-- Last Verified: 2026-03-20 -->

## Executive Summary

**Last Updated**: 2026-03-20
**Status**: v1.2 Production Readiness (17 phases complete). CI gates active. 7 test-full failures tracked (ISSUE-GT-001, ISSUE-PERF-001). test-fast (PR gate) is green.

---

## Resolved Issues

### ISSUE-API-001: Z-Library Cloudflare Bot Protection [RESOLVED]
**Severity**: Was CRITICAL
**Resolution**: EAPI migration (Phase 7, Feb 2026). All API calls now use EAPI JSON endpoints which bypass Cloudflare browser challenges. Health check with Cloudflare detection added.
**ADR**: [ADR-005-EAPI-Migration](docs/adr/ADR-005-EAPI-Migration.md)

### ISSUE-002: Venv Manager Test Failures [CLOSED]
**Severity**: Was High
**Resolution**: UV migration (Phase 2, Jan 2026) eliminated the entire venv manager complexity. Code reduced 77% (406 to 92 lines), tests reduced 90% (833 to 85 lines). The undefined `.trim()` error and venv creation failures no longer occur.

### ISSUE-005: Missing Error Recovery Mechanisms [RESOLVED]
**Resolution**: Retry logic with exponential backoff (`src/lib/retry-manager.ts`), circuit breaker pattern (`src/lib/circuit-breaker.ts`). Configurable via environment variables.

### ISSUE-006: Test Suite Warnings [RESOLVED]
**Resolution**: All warning scenarios covered with proper tests. 28/28 tests passing.

### ISSUE-007: Documentation Gaps [RESOLVED]
**Resolution**: 10 ADRs documented (ADR-001 through ADR-010). Comprehensive `.claude/` docs. Phase 6 documentation cleanup complete.

### ISSUE-FN-001 through ISSUE-FN-004: Footnote Detection Bugs [RESOLVED]
**Resolution**: All 4 footnote critical bugs fixed (Oct-Nov 2025). Marker detection, data contract, corruption recovery, and pairing all working.
**Note**: Footnote *detection* is fixed, but 4 footnote *tests* are broken — see ISSUE-GT-001 below.

---

## Open Issues

### ISSUE-001: No Official Z-Library API
**Severity**: Medium (downgraded from Critical after EAPI migration)
**Impact**: Core functionality relies on reverse-engineered EAPI
**Status**: Mitigated by EAPI transport + health check monitoring
**Mitigation**: EAPI JSON endpoints are more stable than HTML scraping. Health check detects upstream changes. Future: Anna's Archive as alternative source.

### ISSUE-003: Z-Library Infrastructure Changes (Hydra Mode)
**Severity**: Medium
**Impact**: Domain discovery and session management
**Status**: Handled by vendored zlibrary fork with EAPI client
**Note**: EAPI endpoints appear more stable than HTML pages for Hydra mode domains.

### ISSUE-008: Performance Optimizations Needed
**Severity**: Low
**Remaining**:
- No result caching layer (search results, metadata)
- No performance profiling tools
**Resolved items**:
- HTTP connection pooling (shared httpx.AsyncClient)
- Parallel processing (ProcessPoolExecutor for CPU-bound work)

### ISSUE-009: Development Experience Issues
**Severity**: Low
**Remaining**:
- No hot reload for Python changes
- No performance profiling tools
- Limited development fixtures/mocks
**Resolved items**:
- Debug mode with verbose logging (`ZLIBRARY_DEBUG=1`)

### ISSUE-GT-001: Footnote Tests Broken by Ground Truth v3 Migration
**Severity**: Medium
**Component**: `__tests__/python/test_real_footnotes.py`, `__tests__/python/test_inline_footnotes.py`
**Status**: Open — discovered 2026-03-20 during Phase 17 CI setup
**Impact**: 4 tests fail in test-full CI. test-fast is unaffected (these are marked `slow`/`ground_truth`).
**Root Cause**: Phase 14 migrated ground truth files from v1/v2 to v3 schema, but 4 footnote tests still reference v1/v2 keys that no longer exist:

| Test | Missing Key | v3 Equivalent |
|------|-------------|---------------|
| `test_footnote_detection_with_real_pdf` | `footnote["expected_output"]` | No direct equivalent — test needs rewrite to check `definition.content` |
| `test_footnote_marker_in_body_text` | `footnote["marker_context"]` | `footnote["marker"]` is now `{"symbol": "*", "location_type": "..."}` |
| `test_footnote_content_extraction` | `footnote["content"]` | `footnote["definition"]["content"]` |
| `test_derrida_traditional_footnotes_regression` | `footnote["expected_output"]` | Same as above |

**Ground truth file**: `test_files/ground_truth/derrida_footnotes.json`
**Schema change**: v3 restructured footnotes — `marker` became an object (was string), `content` moved under `definition`, `expected_output` removed entirely.
**Fix**: Update tests to use v3 schema accessors. Estimated: 30min. Natural fit for v1.3 (RAG pipeline refinement) or a standalone quick fix.

### ISSUE-PERF-001: Performance Tests Flaky on CI Runners
**Severity**: Low
**Component**: `__tests__/python/test_garbled_performance.py`, `__tests__/python/test_superscript_detection.py`
**Status**: Open — discovered 2026-03-20
**Impact**: 3 tests fail on GitHub Actions runners (slower than dev hardware). Pass locally.
**Tests**:
- `test_detection_long_text_scales_linearly` — expects <5ms, gets ~9ms on CI
- `test_typical_region_fast` — expects <1ms, gets ~1.4ms on CI
- `test_superscript_check_performance` — expects <10ms, gets ~12ms on CI
**Mitigation**: test-fast CI excludes `performance`-marked tests. test_garbled_performance.py was already marked; test_superscript_detection.py::TestPerformance was marked during Phase 17.
**Fix**: Either loosen thresholds (2x for CI) or permanently exclude from CI via marker. These tests validate developer-machine performance, not CI performance.

### ISSUE-DOCKER-001: Docker numpy/Alpine Compilation
**Severity**: Low
**Component**: docker/Dockerfile
**Status**: Pre-existing issue discovered during Phase 4
**Impact**: Production Docker build fails on numpy compilation with Alpine base
**Workaround**: Use non-Alpine base image or pre-built wheels

### ISSUE-AUDIT-001: pip-audit False Positives for Vendored Fork
**Severity**: Low
**Component**: zlibrary/ vendored fork
**Status**: Known limitation
**Impact**: pip-audit reports vulnerabilities for the vendored zlibrary package that are false positives (custom fork, not the upstream package)
**Workaround**: Exclude vendored package from audit or add to allowlist

---

## Technical Debt

### Architecture
1. **Tight Coupling**: Node.js and Python layers coupled through PythonShell (acceptable trade-off)
2. **Legacy Facades**: rag_processing.py still exists as facade delegating to lib/rag/ (intentional for backward compat)

### Testing
1. **No Performance Tests**: Missing load testing, stress testing
2. **Limited E2E with Live Credentials**: Full workflow needs `TEST_LIVE=true`

### Code Quality
1. **Inconsistent Error Handling**: Mix of exceptions across Python modules
2. **Magic Numbers**: Some hardcoded timeouts/limits remain

---

## Improvement Opportunities

### Search Enhancements
- **SRCH-001**: Fuzzy/approximate matching - *Partially implemented* (search_advanced tool provides fuzzy detection)
- **SRCH-002**: Missing advanced filters (size, quality, edition)
- **SRCH-003**: No search result ranking/scoring

### Download Management
- **DL-001**: No queue management for batch downloads
- **DL-002**: Cannot resume interrupted downloads

### RAG Processing
- **RAG-001**: No semantic chunking strategies
- **RAG-002**: OCR for scanned PDFs - *Partially implemented* (framework exists, ML models pending)
- **RAG-005**: No support for MOBI, AZW3, DJVU formats

---

## Broken Functionality

### BRK-001: Download Book Combined Workflow
**Status**: Investigated (2026-01-29) - Code path exists, likely resolved
**Note**: Cannot fully confirm without live credentials. Needs `TEST_LIVE=true` with real book.

### BRK-002: Book ID Lookup
**Status**: Deprecated (ADR-003). Use search_books instead.

### BRK-003: History Parser
**Status**: Fragile. Parser may break with EAPI response format changes.

---

## Future Direction

### Anna's Archive Expansion
- Planned as additional/alternative book source
- Reduces single-source risk (Z-Library availability)
- Architecture supports adding new backends behind service layer
- Would provide broader book coverage and redundancy

---

## Security Considerations

### SEC-001: Credential Storage
**Status**: Environment variables (standard practice for MCP servers)
**Risk**: Low (credentials in process env, not persisted)

### SEC-002: Input Validation
**Status**: EAPI JSON transport provides some inherent sanitization vs raw HTML injection
**Risk**: Low

---

*Document maintained as part of Phase 6 documentation quality gates.*
*Next Review: As needed when new issues discovered.*
