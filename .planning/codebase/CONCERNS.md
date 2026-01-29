# Codebase Concerns

**Analysis Date:** 2026-01-28

## Tech Debt

### Monolithic Python Bridge
**Files:** `lib/rag_processing.py` (4,968 lines)
**Issue:** Single file handles too many responsibilities: PDF extraction, EPUB parsing, footnote detection, corruption recovery, metadata generation, OCR integration
**Impact:** Difficult to test, maintain, and debug; changes in one area risk regressions in others
**Current Symptoms:**
- Footnote detection logic (lines 2920-3300) tightly coupled with footnote continuation (lines 3200+)
- OCR preprocessing (lines 4100-4200) mixed with document format detection
- Metadata generation side effects (lines 4930-4950) scattered throughout processing pipeline
**Fix Approach:**
- Gradually extract footnote detection into dedicated module
- Create `OCRProcessor` class to encapsulate OCR logic
- Separate metadata generation into standalone function
- Use dependency injection to reduce coupling

### Tight Node-Python Coupling
**Files:** `src/lib/zlibrary-api.ts`, `lib/python_bridge.py`
**Issue:** Direct PythonShell interaction without abstraction layer; Python response format changes break Node.js code
**Impact:** Any Python API change requires corresponding Node.js changes; no circuit breaker between layers
**Current Implementation:** Error handling depends on parsing specific JSON response structure from Python
**Fix Approach:**
- Create TypeScript interfaces for all Python response types
- Implement response validation with Zod schemas
- Add adapter layer to normalize responses
- Create comprehensive type definitions (`src/lib/python-responses.ts`)

### Bare Exception Handling
**Files:** `lib/booklist_tools.py:267`
**Issue:** Bare `except:` clause catches all exceptions including SystemExit, KeyboardInterrupt
```python
except:
    pass  # Authentication might succeed even if search fails
```
**Impact:** Silent failures make debugging difficult; can mask serious errors
**Risk:** System can continue in broken state without operator awareness
**Fix Approach:** Replace with specific exception handling: `except (NetworkError, AuthenticationError):`

### Missing Error Context
**Pattern:** `except Exception as e:` in 50+ locations with minimal logging
**Files:** `lib/rag_processing.py`, `lib/enhanced_metadata.py`, `lib/python_bridge.py`
**Issue:** Generic exception handlers lose critical debugging information
**Example:** Line 1924 in `rag_processing.py` logs error but not which document triggered it
**Fix Approach:**
- Create context manager for operation tracking
- Use structured logging with exception context
- Include file paths, operation stage, input parameters in logs

---

## Known Bugs

### Import Path Resolution Issues
**Files:** `lib/rag_processing.py:55-65`
**Issue:** Relative imports fail when module called from different directory
```python
from filename_utils import create_unified_filename  # Line 55: relative import
```
**Current State:** Works in tests but may fail in production if Python bridge invoked differently
**Impact:** RuntimeError on unexpected working directory changes
**Trigger:** Running Python bridge from non-standard location
**Current Mitigation:** sys.path manipulation at line 16 adds project root
**Risk:** Fragile path resolution vulnerable to deployment configuration changes

### Metadata Verification Report Duplication
**Files:** `lib/rag_processing.py:4936-4942`
**Issue:** Metadata verification report assigned twice to same dict key
```python
# Line 4937-4938
if 'verification_report' in locals() and verification_report:
    metadata['verification'] = verification_report

# Line 4941-4942 (DUPLICATE)
if verification_report:
    metadata['verification'] = verification_report
```
**Impact:** Inefficient code; second assignment overrides first
**Risk:** Indicates incomplete refactoring; may mask intended logic
**Fix:** Remove duplicate assignment block

### Inconsistent Page Number Tracking
**Files:** `lib/rag_processing.py`, `lib/footnote_continuation.py`
**Issue:** `pages` field in footnote definitions uses list format `[page_num]` but some operations expect single integer
**Current State:** FIXED (2025-10-29) but vulnerability remains for future similar issues
**Risk:** Multi-page operations may fail silently if code assumes different data type
**Recommendation:** Add runtime type checking for page tracking

---

## Security Considerations

### SEC-001: Credentials in Environment Variables
**Files:** `lib/python_bridge.py`, `src/index.ts` (environment setup)
**Risk:** Credentials exposed in process listings (`ps`, `/proc/self/environ`)
**Impact:** Privilege escalation, account compromise
**Recommendation:**
- Use OS-specific credential storage (system keychain on macOS/Windows, credentials manager on Linux)
- Implement timeout for in-memory credentials (clear after use)
- Add audit logging for credential access

### SEC-002: Unvalidated Input from Z-Library API
**Files:** `lib/python_bridge.py:300-400` (response parsing)
**Issue:** Book metadata, download URLs, HTML content parsed without validation
**Risk:**
- HTML injection if metadata displayed in UI
- URL injection if download URL used without verification
- Path traversal if filenames from API used directly in file operations
**Example:** `create_unified_filename()` at line 55 takes untrusted filename from Z-Library
**Current Mitigation:** `filename_utils.py` includes some sanitization
**Recommendation:**
- Whitelist allowed characters in filenames
- Validate URLs match expected Z-Library domains
- Sanitize HTML metadata before any use

### SEC-003: Unencrypted Local Storage
**Files:** All download/processing operations
**Issue:** Downloaded books and processed content stored unencrypted on disk
**Risk:** Sensitive academic/restricted content exposed to local attackers, disk theft
**Current Mitigation:** File permissions (user-only access to `./downloads/`)
**Recommendation:**
- Document security implications in README
- Implement optional encryption-at-rest
- Add environment variable for encrypted storage mode
- Use OS-level encryption recommendation (full disk encryption, FileVault, BitLocker)

### SEC-004: Python Subprocess Execution
**Files:** `lib/rag_processing.py:1980-1990` (subprocess.run calls), `lib/rag_processing.py:4138` (OCR subprocess)
**Risk:** Command injection if file paths contain shell metacharacters
**Current Implementation:** Uses `subprocess.run()` with `shell=False` (safe by default)
**Recommendation:** Continue using `shell=False`; validate all file paths before subprocess calls

### SEC-005: XML External Entity (XXE) in EPUB Parsing
**Files:** `lib/rag_processing.py:4500+` (EPUB processing with BeautifulSoup)
**Risk:** Malicious EPUB files with XXE payloads could read server files
**Current Implementation:** BeautifulSoup with default parser (may use vulnerable XML parser)
**Recommendation:** Use `parser='html.parser'` or `'lxml'` with XXE protection enabled

---

## Performance Bottlenecks

### PER-001: Sequential PDF Page Processing
**Files:** `lib/rag_processing.py:4700-4730`
**Issue:** PDF pages processed one-at-a-time; no parallelization for multi-page documents
**Problem:** Large PDFs (500+ pages) take proportionally longer; no progress indication
**Current Performance:** ~0.5-1 second per page on typical hardware
**Scalability Limit:** 5+ minute documents at current rates
**Improvement Path:**
- Use `ProcessPoolExecutor` for CPU-bound PDF processing
- Implement page-range batching
- Add progress callback for long operations

### PER-002: No Result Caching
**Files:** `lib/python_bridge.py` (search operations)
**Issue:** Identical searches re-executed without caching results
**Impact:** Slow performance for repeated queries; unnecessary Z-Library API load
**Example:** Searching for same author twice hits API both times
**Improvement Path:**
- Implement LRU cache for search results (with TTL)
- Store in-memory cache with optional Redis backend
- Track cache effectiveness metrics

### PER-003: Synchronous Z-Library API Calls
**Files:** `lib/python_bridge.py:600-700`
**Issue:** Uses blocking `requests`/`httpx` for API calls in async context
**Impact:** Blocks event loop during network operations; can cause timeouts in concurrent scenarios
**Current Implementation:** Some async/await usage but not comprehensive
**Fix Approach:** Ensure all I/O operations use `httpx.AsyncClient` consistently

### PER-004: Inefficient DOM Parsing
**Files:** `lib/python_bridge.py` (Z-Library response parsing)
**Issue:** Parses entire HTML responses with BeautifulSoup for every request
**Impact:** Memory usage scales with response size; slower on large result sets
**Improvement Path:**
- Cache parsed DOM structures
- Use streaming XML/JSON parser for large responses
- Extract only required fields with CSS selectors

---

## Fragile Areas

### FRAG-001: Footnote Detection Marker Position Logic
**Files:** `lib/rag_processing.py:3336-3342`
**Status:** FIXED but architecture remains fragile
**Why Fragile:**
- Marker detection depends on complex position calculations (span start, line position, marker text position)
- Multiple edge cases not fully covered (superscript markers, embedded footnotes)
- Changes to position calculation break related features (continuation, corruption recovery)
**Safe Modification:**
- Add extensive unit tests covering all position edge cases
- Create test matrix: [marker_type] × [position_in_line] × [position_in_span]
- Validate position logic before any changes
**Test Coverage Gaps:**
- No tests for markers at exact line breaks
- Limited tests for double-byte character markers
- No tests for malformed PDF position data

### FRAG-002: Footnote Continuation Multi-Page Tracking
**Files:** `lib/footnote_continuation.py`, `lib/rag_processing.py:3000-3100`
**Why Fragile:**
- Data contract requires exact field structure (`pages`, `marker`, `actual_marker`, `is_complete`)
- Any missing field silently breaks downstream processing
- Complex state machine for tracking partial footnotes across pages
**Safe Modification:**
- Use runtime validation: `FootnoteSchemaValidator.validate()` at every transition point
- Add state diagram documentation
- Create comprehensive integration tests with real multi-page PDFs
**Test Coverage Gaps:**
- Only 1 multi-page E2E test (Kant 64-65)
- No tests for out-of-order pages
- No tests for footnotes spanning 3+ pages

### FRAG-003: Corruption Recovery Symbol Mapping
**Files:** `lib/footnote_corruption_model.py`
**Why Fragile:**
- Hardcoded corruption mappings (line 50+) may not reflect actual PDF rendering differences
- Bayesian inference depends on prior probabilities that may need tuning per PDF type
- No validation that recovered markers are actually in original text
**Safe Modification:**
- Document corruption mappings with PDF examples
- Add empirical validation: check if recovered marker exists in text
- Implement feedback loop to improve mapping accuracy
**Test Coverage Gaps:**
- Limited to 2 test PDFs (Derrida, Kant)
- No corruption mapping tests for non-academic texts
- No systematic tests for symbol variants

### FRAG-004: OCR Quality Assessment
**Files:** `lib/rag_processing.py:4140-4200`
**Why Fragile:**
- Quality score calculation (line 4180+) uses heuristics (word count, confidence, garbled text detection)
- No absolute threshold for "acceptable" quality
- OCR tool availability varies by system (`tesseract`, `ocrmypdf`)
**Safe Modification:**
- Document quality scoring rationale with examples
- Add optional human review step for borderline quality (0.4-0.6 range)
- Create quality score calibration tests
**Test Coverage Gaps:**
- No tests for PDFs with mixed quality pages
- Limited tests for non-English OCR
- No tests for very small/large text in PDFs

---

## Scaling Limits

### SCALE-001: Memory Usage with Large PDFs
**Current Capacity:** ~500 MB single PDF before memory pressure
**Limit:** Out of memory errors with 2+ GB PDFs
**Scaling Path:**
- Implement streaming page processing instead of loading full PDF
- Use temporary file buffers for intermediate results
- Implement memory monitoring with automatic garbage collection

### SCALE-002: Download Queue Limits
**Current Capacity:** Single-threaded downloads; no queue management
**Limit:** Cannot queue multiple book downloads
**Scaling Path:** Implement `src/lib/download-queue.ts` with configurable concurrency
- Queue depth: 10-50 items
- Concurrent downloads: 2-5 (avoid Z-Library rate limiting)
- Persistence: Save queue state to disk for recovery

### SCALE-003: Search Result Handling
**Current Capacity:** ~1000 results per search
**Limit:** UI performance degradation with very large result sets
**Current Implementation:** Returns all results in single response
**Scaling Path:**
- Implement pagination in Z-Library API wrapper
- Add streaming search results capability
- Implement server-side filtering/ranking

---

## Dependencies at Risk

### DEP-001: Vendored ZLibrary Fork
**Package:** `zlibrary/` (custom fork of sertraline/zlibrary)
**Risk:** May diverge significantly from upstream; Z-Library API changes require fork updates
**Current Status:** 2025-01-28 snapshot; unclear how often upstream is merged
**Mitigation Path:**
- Establish process to track upstream changes
- Create GitHub Actions workflow to detect breaking changes
- Document fork modifications vs upstream in `docs/FORK_CHANGES.md`
- Consider upstream contribution of useful enhancements

### DEP-002: Python Package Version Pinning
**Files:** `pyproject.toml`, `uv.lock`
**Issue:** Some Python dependencies may have security vulnerabilities
**Current Implementation:** UV handles dependency resolution; uv.lock pins versions
**Recommendation:**
- Enable automated security scanning (Dependabot for Python)
- Regular audit: `safety check` or equivalent
- Document known vulnerabilities in `SECURITY.md`

### DEP-003: ebooklib for EPUB Processing
**Status:** Maintained but niche library
**Risk:** May not receive updates for new EPUB standards
**Alternative:** `epub` package or Calibre (heavyweight)
**Recommendation:** Monitor for EPUB3 support issues; have backup extraction strategy

### DEP-004: Node.js SDK Version
**Files:** `package.json:32` - `@modelcontextprotocol/sdk:1.8.0`
**Issue:** MCP spec evolving; breaking changes possible in future versions
**Current Status:** Version 1.8.0 is reasonably stable
**Recommendation:** Pin version explicitly; test before upgrading to 2.x

---

## Test Coverage Gaps

### TEST-001: Error Path Coverage
**Affected:** Node.js side error handling
**Gap:** Network timeout scenarios not tested; partial download recovery untested
**Current Tests:** `__tests__/zlibrary-api.test.js` has 28 tests (good), but error scenarios limited
**Priority:** HIGH - Error handling is critical for resilience
**Recommendation:** Add tests for:
- Timeout scenarios (30s+ delays)
- Partial failures (some Z-Library mirrors down)
- Concurrent request failures
- Circuit breaker state transitions

### TEST-002: Real PDF E2E Coverage
**Affected:** RAG processing pipeline
**Gap:** Only 2 real test PDFs (Derrida, Kant); doesn't cover typical academic/technical texts
**Current Tests:** 40+ RAG tests but mostly synthetic
**Priority:** HIGH - Real PDFs reveal issues synthetic tests miss
**Recommendation:** Add test PDFs:
- Technical manual (different layout)
- Scanned book (OCR required)
- Non-English text (language detection)
- Complex tables (layout preservation)

### TEST-003: Z-Library API Changes
**Gap:** No monitoring for breaking API changes; tests use mocked responses
**Current Implementation:** Mocks prevent real API verification
**Priority:** MEDIUM - API changes would break entire system
**Recommendation:**
- Monthly integration tests against production Z-Library (with rate limiting)
- Version detection to identify API changes
- Alerts when response format changes

### TEST-004: Performance Regression Testing
**Gap:** No performance benchmarks; can't detect slowdowns from changes
**Current Implementation:** `scripts/profile_performance.py` exists but not in CI
**Priority:** MEDIUM
**Recommendation:**
- Add performance budget: `test_files/performance_budgets.json`
- CI check compares current performance against baseline
- Alert on 10%+ degradation

### TEST-005: Security Testing
**Gap:** No OWASP testing; no injection vulnerability tests
**Current Implementation:** Static code review only
**Priority:** MEDIUM - See SEC-002 through SEC-005
**Recommendation:**
- Add security test suite for input validation
- Implement SAST (Static Application Security Testing) in CI
- Consider penetration testing before major releases

---

## Missing Critical Features

### FEAT-001: Download Queue Management
**Problem:** Can't queue multiple downloads or batch operations
**Blocks:** Automation of downloading entire author's works
**Current Workaround:** Manual sequential downloads
**Implementation:** Create `src/lib/download-queue.ts` with:
- In-memory queue + disk persistence
- Configurable concurrency (respect Z-Library rate limits)
- Pause/resume capability
- Progress tracking

### FEAT-002: Incremental OCR Processing
**Problem:** Full OCR of large PDFs takes hours; no way to resume interrupted OCR
**Blocks:** Processing of scanned books
**Current Implementation:** All-or-nothing OCR
**Recommendation:** Implement page-range OCR with checkpoint saving

### FEAT-003: Language Detection
**Problem:** Can't automatically identify document language
**Blocks:** Multilingual RAG pipelines
**Current Workaround:** Manual language specification
**Implementation:** Use `langdetect` or `textblob` library

### FEAT-004: Document Structure Extraction
**Problem:** Table of Contents extraction limited; no section/chapter boundaries
**Blocks:** Hierarchical chunking for RAG
**Current Implementation:** Basic PyMuPDF ToC extraction
**Recommendation:** Enhance with heuristic detection of chapter breaks

### FEAT-005: Format-Specific Optimizations
**Problem:** No special handling for technical books (code, equations, tables)
**Blocks:** Proper processing of programming books, math textbooks
**Current Implementation:** Generic text extraction
**Recommendation:** Add format profiles for common book types

---

## Monitoring & Observability Gaps

### OBS-001: Missing Health Check Endpoint
**Issue:** No way to verify MCP server health before use
**Current Implementation:** Server starts but may fail silently on first request
**Recommendation:** Add `health_check` MCP tool that verifies:
- Python bridge connectivity
- Z-Library API reachability
- Virtual environment functionality

### OBS-002: No Request Tracing
**Issue:** Can't correlate errors across Node-Python boundary
**Current Implementation:** Separate logs in each layer
**Recommendation:**
- Add request ID generation in Node.js
- Pass request ID to Python bridge
- Include in all log messages
- Return in error responses for debugging

### OBS-003: Missing Performance Metrics
**Gaps:**
- No timing data for Z-Library API calls
- No throughput metrics for RAG processing
- No cache effectiveness tracking
**Recommendation:** Implement Prometheus-style metrics exporting

### OBS-004: No Circuit Breaker Visibility
**Issue:** Can't see when circuit breaker opens/closes
**Current Implementation:** Circuit breaker implemented but not exposed
**Recommendation:** Add metrics for circuit breaker state changes

---

## Architectural Issues

### ARCH-001: Language Barrier Fragility
**Issue:** Node-Python communication via PythonShell is brittle
**Risk Factors:**
- JSON parsing errors break entire system
- Serialization differences (Python None vs null, etc.)
- Process spawning overhead for each operation
**Mitigation:** Already has retry logic + circuit breaker
**Long-term Solution:** Consider native Python bindings or async gRPC bridge

### ARCH-002: No Plugin System
**Issue:** Can't extend functionality without modifying core code
**Example:** Adding new document format requires editing RAG processing logic
**Impact:** Makes maintenance harder; discourages contributions
**Recommendation:** Create plugin interface for document processors:
```typescript
interface DocumentProcessor {
  canProcess(format: string): boolean;
  process(path: string): Promise<ProcessedContent>;
}
```

### ARCH-003: State Management in Single Layer
**Issue:** No persistent state; Z-Library session stored only in memory
**Risk:** Server crash loses authentication
**Impact:** Session restart needed after any crash
**Recommendation:** Implement session persistence:
- Store auth token in secure location
- Load on server restart
- Add token refresh logic

---

## Known Limitations

### LIM-001: No Fuzzy/Approximate Search
**Scope:** Search feature
**Limitation:** Search queries must match exactly (or use Z-Library's internal search)
**User Impact:** Typos in queries return 0 results instead of "Did you mean?"
**Workaround:** Manually try similar queries
**Implementation:** Add client-side fuzzy matching to search results

### LIM-002: No Search Within Results
**Scope:** Search feature
**Limitation:** Can't filter already-retrieved results without new Z-Library search
**User Impact:** Need to execute new search to narrow results
**Workaround:** Use additional search parameters to refine

### LIM-003: Limited Book Metadata
**Scope:** Book details
**Limitation:** Z-Library provides limited metadata (no ISBN verification, rating, reviews)
**Workaround:** Could supplement with Open Library API (additional latency)

### LIM-004: PDF Text Extraction Quality Varies
**Scope:** RAG processing
**Limitation:** Quality depends on PDF type (native text vs scanned image)
**Impact:** OCR quality varies; some PDFs return mostly garbage
**Current Mitigation:** Quality score in metadata indicates reliability

### LIM-005: No Support for Some Formats
**Scope:** Document processing
**Unsupported:** MOBI, AZW3, DJVU, CBR/CBZ (comics)
**Reason:** Libraries not available or complex format handling required
**User Workaround:** Convert to PDF/EPUB externally

---

## Recommendations Priority Matrix

| Concern | Severity | Effort | Priority |
|---------|----------|--------|----------|
| Bare exception handling (booklist_tools.py:267) | MEDIUM | LOW | HIGH |
| Monolithic rag_processing.py | MEDIUM | HIGH | MEDIUM |
| Missing error context logging | MEDIUM | MEDIUM | HIGH |
| E2E test coverage gaps | MEDIUM | HIGH | MEDIUM |
| Footnote detection fragility | MEDIUM | MEDIUM | MEDIUM |
| Download queue feature | LOW | HIGH | LOW |
| Performance regression testing | MEDIUM | MEDIUM | MEDIUM |
| Security test suite | MEDIUM | MEDIUM | MEDIUM |
| Memory scaling limits | LOW | MEDIUM | LOW |

---

*Concerns audit: 2026-01-28*
