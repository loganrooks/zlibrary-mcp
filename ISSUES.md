# Z-Library MCP - Comprehensive Issues Documentation

## Executive Summary
This document provides intensive documentation of all issues, technical debt, and improvement opportunities identified in the Z-Library MCP project.

**Last Updated**: 2025-11-24
**Critical Status**: ✅ **ALL CRITICAL ISSUES RESOLVED** - Marker-pairing bug fixed, continuation tests passing

## 🔴 Active Critical Issues

*No active critical issues.*

---

## ✅ Recently Resolved Critical Issues

### ISSUE-FN-004: Marker-to-Definition Pairing Bug (FIXED - 2025-11-24)
**Component**: Footnote detection (`_find_definition_for_marker`)
**Severity**: 🔴 CRITICAL - Causes incorrect marker-content pairing → ✅ **RESOLVED**
**Impact**: Multi-page continuation fails for `*` marker in Kant 64-65
**Discovered**: 2025-11-24 ground truth verification
**Fixed**: 2025-11-24 (same session)
**Status**: ✅ **FIXED AND VALIDATED**

**Original Symptoms**:
- All markers (a, 4, 5, b, *) get paired with SAME content (the * footnote)
- Multi-page continuation works for marker `a` (alphabetically first) but not `*`
- Test `test_kant_asterisk_multipage_continuation_e2e` FAILS

**Root Cause**:
Location: `lib/rag_processing.py:_find_definition_for_marker` (lines 2920-3088)

Function found ANY marker-started block without validating marker match.

**Fix Applied**:
1. Added `_markers_are_equivalent()` function (lines 2921-2971) to validate marker matching
2. Added corruption equivalence table for symbol markers (`*` ↔ `iii`, `†` ↔ `t`, etc.)
3. Modified `_find_definition_for_marker()` to validate marker match before accepting definition
4. Added short gloss detection in `lib/footnote_continuation.py` (lines 180-190) to prevent German word glosses like "Rechtmässigkeit" from being marked incomplete

**Validation**:
- Kant 64-65 continuation test now PASSES
- `*` footnote correctly merged with page 65 continuation ("to which everything must submit")
- 57/57 footnote continuation tests passing
- 40/43 RAG processing tests passing (3 pre-existing mock issues unrelated to fix)

**Related Documentation**:
- `claudedocs/session-notes/2025-11-24-ground-truth-verification-report.md`
- `test_files/ground_truth/kant_64_65_footnotes.json` (complexity_notes section)

---

### ISSUE-FN-003: Data Contract Bug - Missing Pages Field (FIXED - 2025-10-29)
**Component**: Multi-page footnote tracking
**Severity**: 🔴 CRITICAL - **DATA CONTRACT BROKEN** → ✅ **RESOLVED**
**Impact**: CrossPageFootnoteParser couldn't track multi-page footnotes
**Discovered**: 2025-10-29 E2E test validation
**Fixed**: 2025-10-29 (current session)
**Status**: ✅ **FIXED AND VALIDATED**

**Symptoms**:
- 57/57 unit tests passing (synthetic data)
- 0/1 E2E tests passing (real PDF)
- Multi-page continuation merge completely broken
- `pages` field missing from all footnote definitions
- CrossPageFootnoteParser couldn't track which pages footnotes appeared on

**Root Cause**:
Locations: `lib/rag_processing.py:3067-3078`, `lib/rag_processing.py:3208-3220`

```python
# BROKEN: No pages field in footnote definitions
def _find_definition_for_marker(page, marker, marker_y_position, marker_patterns):
    return {
        'marker': marker,
        'content': full_content,
        # ... other fields ...
        # MISSING: 'pages' field required by CrossPageFootnoteParser
    }
```

**Problem Analysis**:
The footnote detection functions created footnote definition dicts but didn't populate the `pages` field required by CrossPageFootnoteParser for multi-page tracking.

Data contract requirements:
- ✅ `is_complete`: boolean (already present)
- ❌ `pages`: list[int] (MISSING - this bug)

Without `pages` field:
- Parser couldn't track which pages a footnote spanned
- Multi-page merge logic completely broken
- Unit tests passed (synthetic data doesn't test this)
- E2E tests failed (real PDFs revealed the bug)

**The Fix**:
1. Updated `_find_definition_for_marker` signature to accept `page_num`
2. Added `'pages': [page_num]` to footnote definition return dict
3. Updated `_find_markerless_content` signature to accept `page_num`
4. Added `'pages': [page_num]` to markerless footnote definitions
5. Updated all 4 call sites to pass `page_num` parameter

```python
# FIXED: Pages field populated
def _find_definition_for_marker(page, marker, marker_y_position, marker_patterns, page_num):
    return {
        'marker': marker,
        'content': full_content,
        # ... other fields ...
        'pages': [page_num]  # CRITICAL: Enable multi-page tracking
    }
```

**Validation**:
- ✅ `test_pipeline_sets_pages_field` now PASSES
- ✅ All footnotes have `pages: [page_num]` field
- ✅ No regressions: 57/57 continuation tests still passing
- ✅ Improvement: 30/37 → 33/37 inline tests passing

**Files Modified**:
- `lib/rag_processing.py`:
  - Line 2917: `_find_definition_for_marker` signature + `pages` field (line 3078)
  - Line 3084: `_find_markerless_content` signature + `pages` field (line 3221)
  - Lines 3582, 3598, 3607, 3611: Updated all call sites to pass `page_num`

**Lesson Learned**:
Unit tests can pass while E2E tests fail. This bug was completely invisible to synthetic unit tests but immediately caught by real PDF E2E tests.

---

### ISSUE-FN-002: Corruption Recovery Not Integrated with Continuation Parser (FIXED - 2025-10-29)
**Component**: Footnote continuation tracking + corruption recovery
**Severity**: 🔴 CRITICAL - **CORRUPTION RECOVERY BROKEN** → ✅ **RESOLVED**
**Impact**: Corrupted markers in final output (`[^a]:` instead of `[^*]:`)
**Discovered**: 2025-10-29 test validation
**Fixed**: 2025-10-29 (commit TBD)
**Status**: ✅ **FIXED AND VALIDATED**

**Symptoms**:
- Corruption recovery worked on per-page level (detected 'a' → '*', 't' → '†')
- Final PDF output showed raw corrupted markers (`[^a]:`, `[^t]:`)
- Derrida test expecting `[^*]:` and `[^†]:` but getting corrupted versions
- 6/37 inline footnote tests failing due to corruption recovery integration

**Root Cause**:
Location: `lib/footnote_continuation.py:569`

```python
marker = footnote_dict.get('marker')  # ❌ Gets raw marker, not corrected
```

**Problem Analysis**:
The continuation parser was extracting the raw `marker` field from footnote dicts instead of `actual_marker` (the corrected version from corruption recovery).

Flow:
1. `_detect_footnotes_in_page()` detects raw marker 'a'
2. `apply_corruption_recovery()` adds `actual_marker: '*'` to definition dict ✅
3. `CrossPageFootnoteParser.process_page()` creates `FootnoteWithContinuation`
4. Line 569: `marker = footnote_dict.get('marker')` → Gets 'a' instead of '*' ❌
5. `_footnote_with_continuation_to_dict()` returns dict with raw marker 'a' ❌
6. Final markdown shows `[^a]:` instead of `[^*]:`  ❌

**The Fix**:
```python
# CRITICAL FIX: Use actual_marker from corruption recovery if available
marker = footnote_dict.get('actual_marker', footnote_dict.get('marker'))
```

**Validation**:
- ✅ Derrida test now passes: `[^*]:` and `[^†]:` in output
- ✅ 30/37 inline footnote tests passing (81% pass rate)
- ✅ 672/698 overall tests passing (96.3% pass rate)
- ✅ Corruption recovery integrated end-to-end

**Files Modified**:
- `lib/footnote_continuation.py`: Line 569 (use actual_marker with fallback)

---

### ISSUE-FN-001: Marker Detection Completely Broken (FIXED - 2025-10-28)
**Component**: Footnote detection (marker-driven architecture)
**Severity**: 🔴 CRITICAL - **SYSTEM BLOCKER** → ✅ **RESOLVED**
**Impact**: 0% footnote detection success rate → 93% test pass rate (148/159)
**Discovered**: 2025-10-28 comprehensive validation
**Fixed**: 2025-10-28 (commit 0058994)
**Status**: ✅ **FIXED AND VALIDATED**

**Symptoms**:
- Derrida PDF: 0/2 footnotes detected (expected: asterisk, dagger with corruption recovery)
- Traditional footnote detection completely broken
- Symbolic markers (*, †, ‡) not detected at all
- Regression tests failing: 3/8 in test_real_footnotes.py
- New tests failing: 8/37 in test_inline_footnotes.py
- **Total impact**: 11/159 tests failing due to this single bug

**Root Cause**:
Location: `lib/rag_processing.py:3336-3342`

```python
is_at_block_start = (line_idx == 0 and span_start_pos == 0)

if is_at_block_start and block_starts_with_marker and not is_superscript:
    # Skip: This is the start of a footnote definition, not a marker reference
    continue
```

**Problem Analysis**:
The filter logic confuses TWO different scenarios:

**Scenario A** (Definition Start - SHOULD SKIP):
```
* The title of the next section is...
```
- Marker IS first character of span text
- Should NOT be detected (it's the definition)

**Scenario B** (Body Marker - SHOULD DETECT):
```
The Outside and the Inside *
```
- Marker is at END of span text
- span_start_pos = 0 (span is first in line)
- **BUG**: Code checks span position, not marker position within span
- Should be detected but gets rejected

**Visual Evidence** (Derrida PDF page 1):
```
Extracted: "The Outside and the Inside * "
Expected: Asterisk detected as body marker (ground truth: "section_heading_suffix")
Actual: Asterisk skipped (incorrectly classified as definition start)
Result: 0% detection rate
```

**Why This is Critical**:
1. **Complete system failure**: 0% success on production PDFs
2. **Not just inline**: Traditional footnotes also broken
3. **Major regression**: Previous working functionality destroyed
4. **Blocks everything**: Continuation, classification, all downstream features blocked
5. **Unusable system**: Cannot detect ANY footnotes (symbolic, numeric, alphabetic)

**Fix Required**:
```python
# WRONG (current - checks span position in line):
is_at_block_start = (line_idx == 0 and span_start_pos == 0)

# CORRECT (proposed - check marker position in span text):
marker_is_first_char_in_span = text.strip().startswith(marker_text)
is_at_definition_start = (line_idx == 0 and marker_is_first_char_in_span)
```

**Resolution Summary**:
The bug was fixed by changing the marker position check from span position to marker text position.

**Fix Applied** (commit 0058994):
```python
# BEFORE (buggy):
is_at_block_start = (line_idx == 0 and span_start_pos == 0)

# AFTER (correct):
span_text_clean = text.strip()
marker_pattern_at_start = bool(re.match(r'^[*†‡§¶#\d]+', span_text_clean))
is_at_definition_start = (line_idx == 0 and marker_pattern_at_start)
```

**Validation Results**:
- ✅ Derrida PDF: 3 markers detected (was 0)
- ✅ test_real_footnotes.py: 5/8 passing (improved from 3/8)
- ✅ test_inline_footnotes.py: 29/37 passing (same, blocked by corruption recovery)
- ✅ test_footnote_continuation.py: 57/57 passing (no regression)
- ✅ test_note_classification.py: 39/39 passing (no regression)
- ✅ test_performance_footnote_features.py: 18/18 passing (no regression)
- ✅ **Overall**: 148/159 passing (93% pass rate)

**Remaining Work**:
11 tests still failing, primarily due to corruption recovery feature (expects "\*" but gets "a"):
- 3 tests in test_real_footnotes.py (corruption recovery needed)
- 8 tests in test_inline_footnotes.py (corruption + other features)

**Next Steps**:
- Implement corruption recovery to map "a"→"\*", "t"→"†"
- Fix spatial threshold calculations
- Achieve 100% test pass rate (159/159)

**Reference**: See `claudedocs/session-notes/2025-10-28-issue-fn-001-fix-summary.md` for complete details

---

## 🟠 High Priority Issues (P1) - Major Functionality

### ISSUE-001: No Official Z-Library API
**Severity**: Critical
**Impact**: Core functionality relies on web scraping
**Location**: Entire project architecture
**Details**:
- Z-Library has no official public API as of 2025
- Using internal EAPI through reverse-engineering
- Subject to breaking changes without notice
- May require frequent maintenance when Z-Library updates

**Mitigation Strategy**:
- Implement robust error handling for DOM changes
- Create abstraction layer for easy updates
- Monitor community EAPI documentation
- Implement circuit breaker pattern for graceful degradation

### ISSUE-002: Venv Manager Test Failures
**Severity**: High
**Impact**: Test suite reliability compromised
**Location**: `src/lib/venv-manager.ts`, `__tests__/venv-manager.test.js`
**Stack Trace**:
```
console.error
  [python3 -m venv /tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv] stderr: venv creation failed
  at error (src/lib/venv-manager.ts:74:40)

Warning: Failed to read or validate venv config from /tmp/jest-zlibrary-mcp-cache/.venv_config:
Cannot read properties of undefined (reading 'trim')
  at error (src/lib/venv-manager.ts:255:17)
```

**Root Cause**:
- Venv creation fails in test environment
- Config reading attempts to trim undefined values
- Missing null checks in error paths

### ISSUE-003: Z-Library Infrastructure Changes (Hydra Mode)
**Severity**: High
**Impact**: Domain discovery and session management
**Location**: Connection logic, authentication
**Details**:
- May 2024: FBI domain seizures forced "Hydra mode"
- Each user gets personalized domains
- Domains change frequently
- Need dynamic domain discovery mechanism

## 🟡 Medium Priority Issues

### ISSUE-004: Incomplete RAG Processing TODOs
**Severity**: Low (downgraded - these are minor enhancements)
**Location**: `lib/rag_processing.py`
**Line Numbers**: 400, 1484, 4792
**TODOs Found**:
```python
# Line 400: TODO: Use block['bbox'][0] (x-coordinate) to infer indentation/nesting
# Line 1484: TODO: Implement proper Markdown table conversion later if needed
# Line 4792: TODO: Calculate OCR quality score if OCR was used
```

**Impact**:
- Minor: Indentation inference for structured documents (optional enhancement)
- Minor: Markdown table conversion (edge case)
- Minor: OCR quality score tracking (diagnostic enhancement)

### ~~ISSUE-005: Missing Error Recovery Mechanisms~~ ✅ RESOLVED
**Severity**: Medium → **RESOLVED** (2025-09-30)
**Impact**: Poor resilience to transient failures
**Locations**: Multiple
**Resolution**:
- ✅ Implemented retry logic with exponential backoff (`src/lib/retry-manager.ts`)
- ✅ Added circuit breaker pattern (`src/lib/circuit-breaker.ts`)
- ✅ Created custom error classes with context (`src/lib/errors.ts`)
- ✅ Integrated into all API operations (`src/lib/zlibrary-api.ts`)
- ✅ Comprehensive test coverage (96.96% retry, 100% circuit breaker)
- ✅ Configurable via environment variables
- 📚 Documentation: `docs/RETRY_CONFIGURATION.md`

### ~~ISSUE-006: Test Suite Warnings~~ ✅ RESOLVED
**Severity**: Medium → **RESOLVED** (2025-11-24)
**Location**: `__tests__/zlibrary-api.test.js`
**Resolution**:
- ✅ Added test for stderr handling (`should include stderr in error message`)
- ✅ Added test for non-zero exit codes (`should handle PythonShell non-zero exit code error`)
- ✅ Added test for timeout scenarios (`should handle PythonShell timeout error`)
- ✅ Existing tests cover: no output (line 201), malformed JSON (line 183)
- ✅ All 28 tests passing

## 🟢 Low Priority Issues

### ~~ISSUE-007: Documentation Gaps~~ ✅ RESOLVED
**Severity**: Low → **RESOLVED** (2025-11-24)
**Resolution**:
- ✅ 8 ADRs documented in `docs/adr/` (ADR-001 through ADR-008)
- ✅ Error codes documented in `docs/RETRY_CONFIGURATION.md`
- ✅ API specs in `docs/get-book-metadata-spec.md`, `docs/rag-pipeline-implementation-spec.md`
- ✅ Comprehensive `.claude/` documentation (PROJECT_CONTEXT, ARCHITECTURE, PATTERNS, etc.)

### ISSUE-008: Performance Optimizations Needed
**Severity**: Low
**Areas**:
- ~~No HTTP connection pooling~~ ✅ Resolved (2025-11-24) - Added shared `httpx.AsyncClient` with connection pooling
  - `get_http_client()` returns shared client with keepalive connections
  - `close_http_client()` for cleanup
  - Connection limits: 5 keepalive, 10 max, 30s expiry
- ~~Sequential processing~~ ✅ Resolved - `ProcessPoolExecutor` used for CPU-bound work
- No result caching layer (remaining item)
- ~~Inefficient DOM parsing~~ (no evidence of issues)

### ISSUE-009: Development Experience Issues
**Severity**: Low
**Problems**:
- No hot reload for Python changes
- ~~Missing debug mode with verbose logging~~ ✅ Resolved (2025-11-24)
  - Set `ZLIBRARY_DEBUG=1` or `DEBUG=1` to enable verbose logging
  - Debug mode adds function names, line numbers to log output
  - `is_debug_mode()` helper function available
- No performance profiling tools
- Lack of development fixtures/mocks

## 📊 Technical Debt Inventory

### Architecture Debt
1. **Tight Coupling**: Node.js and Python layers tightly coupled through PythonShell
2. **No Abstraction Layer**: Direct EAPI calls without service layer
3. **Monolithic Python Bridge**: `python_bridge.py` handles too many responsibilities
4. **Missing Interfaces**: No TypeScript interfaces for Python responses

### Testing Debt
1. **Insufficient Integration Tests**: Limited E2E testing of full workflows
2. **No Performance Tests**: Missing load testing, stress testing
3. **Mock Data Outdated**: Test fixtures don't reflect current Z-Library responses
4. **Coverage Gaps**: Key error paths untested

### Code Quality Debt
1. **Inconsistent Error Handling**: Mix of exceptions, callbacks, promises
2. **Magic Numbers**: Hardcoded timeouts, limits throughout code
3. **Missing Type Safety**: Python side lacks type hints
4. **No Code Formatting**: Inconsistent style between files

## 🔧 Broken Functionality

### BRK-001: Download Book Combined Workflow
**Status**: Partially broken
**Location**: `download_book_to_file` with `process_for_rag=true`
**Issue**: AttributeError when calling missing method in forked zlibrary
**Memory Bank Reference**: INT-RAG-003

### BRK-002: Book ID Lookup
**Status**: Deprecated
**Location**: `get_book_by_id`
**Issue**: Unreliable due to Z-Library changes
**ADR Reference**: ADR-003

### BRK-003: History Parser
**Status**: Fixed but fragile
**Location**: `get_download_history`
**Issue**: Parser breaks with DOM changes
**Commit**: 9350af5 (temporary fix)

## 🎯 Improvement Opportunities

### Search Enhancements
- **SRCH-001**: No fuzzy/approximate matching
- **SRCH-002**: Missing advanced filters (size, quality, edition)
- **SRCH-003**: No search result ranking/scoring
- **SRCH-004**: Cannot search within results
- **SRCH-005**: No "did you mean" suggestions

### Download Management
- **DL-001**: No queue management for batch downloads
- **DL-002**: Cannot resume interrupted downloads
- **DL-003**: No bandwidth throttling options
- **DL-004**: Missing parallel download capability
- **DL-005**: No automatic format preference (PDF > EPUB > TXT)

### RAG Processing
- **RAG-001**: No semantic chunking strategies
- **RAG-002**: Missing OCR for scanned PDFs
- **RAG-003**: No language detection
- **RAG-004**: Cannot extract document structure (TOC, chapters)
- **RAG-005**: No support for MOBI, AZW3, DJVU formats

### User Experience
- **UX-001**: No progress indicators for long operations
- **UX-002**: Cryptic error messages
- **UX-003**: No operation history/audit log
- **UX-004**: Cannot cancel in-progress operations
- **UX-005**: No batch operation support

## 📈 Metrics and Monitoring Gaps

### Missing Metrics
- Request success/failure rates
- Average response times
- Domain availability tracking
- Download success rates by format
- RAG processing times by document type
- Cache hit/miss ratios
- Error frequency by type

### Missing Monitoring
- Health check endpoint
- Domain rotation effectiveness
- Memory usage tracking
- Python bridge performance
- Queue depth monitoring
- Rate limit tracking

## 🚨 Security Considerations

### SEC-001: Credential Storage
**Issue**: Credentials stored in environment variables
**Risk**: Exposed in process listings
**Recommendation**: Use secure credential storage

### SEC-002: No Request Validation
**Issue**: User input passed directly to EAPI
**Risk**: Injection attacks possible
**Recommendation**: Input sanitization layer

### SEC-003: Unencrypted Local Storage
**Issue**: Downloaded books stored unencrypted
**Risk**: Sensitive content exposure
**Recommendation**: Optional encryption at rest

## 🔄 Dependency Issues

### Python Dependencies
- `zlibrary` fork may diverge from upstream
- No version pinning in requirements.txt
- Missing security update monitoring

### Node Dependencies
- Some packages outdated
- No automated dependency updates
- Missing vulnerability scanning

## 📝 Action Items Summary

### Immediate (This Week)
1. Fix venv manager test failures
2. Add comprehensive error handling
3. Implement retry logic
4. Document all error codes

### Short Term (2 Weeks)
1. Add fuzzy search
2. Create download queue
3. Implement caching layer
4. Add progress indicators

### Medium Term (1 Month)
1. Refactor Python bridge
2. Add comprehensive testing
3. Implement monitoring
4. Create abstraction layers

### Long Term (3 Months)
1. Architecture redesign
2. Performance optimization
3. Advanced RAG features
4. Full API documentation

## 🔍 Investigation Required

### INV-001: Domain Rotation Strategy
Need to research optimal domain discovery and rotation strategies for Hydra mode.

### INV-002: CAPTCHA Handling
Investigate CAPTCHA detection and potential solving strategies.

### INV-003: Rate Limiting Behavior
Determine actual rate limits through empirical testing.

### INV-004: Session Lifecycle
Understand session timeout and renewal requirements.

## 📚 Related Documentation

- [ADR-002: Download Workflow Redesign](docs/adr/ADR-002-Download-Workflow-Redesign.md)
- [ADR-003: Handle ID Lookup Failure](docs/adr/ADR-003-Handle-ID-Lookup-Failure.md)
- [RAG Pipeline Architecture](docs/architecture/rag-pipeline.md)
- [Memory Bank Issues](memory-bank/mode-specific/integration.md)

---

*Document Generated: 2025-09-30*
*Version: 1.0.0*
*Next Review: 2025-10-07*