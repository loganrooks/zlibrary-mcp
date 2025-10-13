# Known Test Issues

## Pre-Existing Test Failures

### zlibrary-api.test.js: Error message format mismatch

**Test**: "should throw error if Python script returns an error object"

**Status**: FAILING (pre-existing issue, not related to path resolution fixes)

**Error**:
```
Expected substring: "Python bridge execution failed for search: Something went wrong in Python"
Received message: "Something went wrong in Python"
```

**Root Cause**:
The test expects error messages to include the function name prefix ("Python bridge execution failed for search:"), but the actual error thrown from `PythonBridgeError` doesn't include this prefix in all cases.

**Location**: `__tests__/zlibrary-api.test.js` line 174-176

**Fix Required**:
Update either:
1. The error message format in `src/lib/errors.ts` to consistently include function name, OR
2. The test expectation to match the actual error message format

**Impact**: Low - Does not affect runtime functionality, only test assertion

**Related Files**:
- `src/lib/errors.ts:109` - PythonBridgeError constructor
- `src/lib/zlibrary-api.ts:107` - Error throwing location

---

## Test Summary After Phase 1 Path Fixes

**Date**: 2025-10-12

**Results**: 81 passed, 1 failed (pre-existing)

**Path-Related Tests**: ✅ ALL PASSING

**Coverage**: 74.68% statements

The single failing test is unrelated to the path resolution improvements implemented in Phase 1.
