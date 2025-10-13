# Known Test Issues

## ✅ All Issues Resolved

All previously documented test issues have been fixed.

---

## Historical Issues (Resolved)

### ~~zlibrary-api.test.js: Error message format mismatch~~ ✅ FIXED

**Test**: "should throw error if Python script returns an error object"

**Status**: ✅ **RESOLVED** (Fixed 2025-10-12)

**Original Error**:
```
Expected substring: "Python bridge execution failed for search: Something went wrong in Python"
Received message: "Something went wrong in Python"
```

**Root Cause**:
Error messages didn't include function name prefix when thrown from `PythonBridgeError`.

**Fix Applied**:
Updated `src/lib/zlibrary-api.ts` line 107 to include function name in error message:
```typescript
throw new PythonBridgeError(
  `Python bridge execution failed for ${functionName}: ${resultData.error}`,
  { functionName, args }
);
```

**Benefits**:
- ✅ Test now passes
- ✅ Better error messages for users (function name context)
- ✅ Consistent error format across all Python bridge errors

**Commit**: TBD

---

## Test Summary

**Current Status** (2025-10-12):

**Results**: ✅ **85 passed, 0 failed**

**Test Suites**: ✅ **7 passed, 7 total**

**Coverage**: 75.31% statements

**Test Categories**:
- ✅ Unit tests: All passing
- ✅ Integration tests: All passing (3 tests)
- ✅ Path-related tests: All passing
- ✅ Error handling tests: All passing

---

## Improvement Timeline

1. **Phase 1** (2025-10-12): Fixed hardcoded test paths
   - Result: 81 passed, 1 failed (pre-existing)

2. **Phase 2** (2025-10-12): Build validation + ADR + Integration tests
   - Result: 84 passed, 1 failed (pre-existing)

3. **Pre-existing Fix** (2025-10-12): Fixed error message format
   - Result: ✅ **85 passed, 0 failed**
