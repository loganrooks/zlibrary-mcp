# Z-Library MCP - Comprehensive Issues Documentation

## Executive Summary
This document provides intensive documentation of all issues, technical debt, and improvement opportunities identified in the Z-Library MCP project as of 2025-09-30.

## 🔴 Critical Issues

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
**Severity**: Medium
**Location**: `lib/rag_processing.py`
**Line Numbers**: 132, 154, 563
**TODOs Found**:
```python
# Line 132: TODO: Consider adding more levels or refining based on document analysis
# Line 154: TODO: Use block['bbox'][0] (x-coordinate) to infer indentation/nesting
# Line 563: TODO: Add more heuristics (e.g., gibberish patterns, layout analysis)
```

**Impact**:
- PDF quality detection incomplete
- Missing indentation inference for structured documents
- Limited gibberish/corrupted text detection

### ISSUE-005: Missing Error Recovery Mechanisms
**Severity**: Medium
**Impact**: Poor resilience to transient failures
**Locations**: Multiple
**Details**:
- No retry logic with exponential backoff
- Missing circuit breaker implementation
- No fallback mechanisms for domain failures
- Insufficient error context in exceptions

### ISSUE-006: Test Suite Warnings
**Severity**: Medium
**Location**: `__tests__/zlibrary-api.test.js:230`
**TODO**: Add tests for PythonShell.run errors
- Missing tests for non-zero exit codes
- No stderr handling tests
- No malformed JSON response tests
- Missing timeout scenario tests

## 🟢 Low Priority Issues

### ISSUE-007: Documentation Gaps
**Severity**: Low
**Locations**: Various
**Missing Documentation**:
- API error codes and meanings
- Rate limiting behavior
- Session lifecycle management
- Domain rotation strategies
- Caching strategies

### ISSUE-008: Performance Optimizations Needed
**Severity**: Low
**Areas**:
- No connection pooling
- Sequential processing where parallel possible
- No result caching layer
- Inefficient DOM parsing in some areas

### ISSUE-009: Development Experience Issues
**Severity**: Low
**Problems**:
- No hot reload for Python changes
- Missing debug mode with verbose logging
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