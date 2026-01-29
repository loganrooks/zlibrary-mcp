# Testing Patterns

**Analysis Date:** 2026-01-28

## Test Framework

**Runner (Node.js):**
- Jest ^29.7.0
- Config: `jest.config.js`
- ESM support: `ts-jest` with ESM preset
- Experimental flag required: `node --experimental-vm-modules node_modules/jest/bin/jest.js`

**Runner (Python):**
- Pytest with pytest-asyncio
- Config: `pytest.ini`
- Python path: `. lib` (project root and lib directory)
- Async mode: `asyncio_mode = auto`

**Assertion Library (Node.js):**
- Jest built-in: `expect()`, `toThrow()`, `rejects.toThrow()`, etc.

**Assertion Library (Python):**
- Pytest built-in: `assert` statements
- Mock: `unittest.mock` (Mock, patch, MagicMock, AsyncMock)

**Run Commands:**
```bash
# All tests (Node.js + Python)
npm test

# Node.js tests only
node --experimental-vm-modules node_modules/jest/bin/jest.js

# Node.js tests with coverage
node --experimental-vm-modules node_modules/jest/bin/jest.js --coverage

# Python tests only
uv run pytest
# Or manually: .venv/bin/python -m pytest

# Python tests with verbose output
uv run pytest -v

# Python tests excluding integration/e2e
uv run pytest -m "not integration and not e2e"

# Specific Python test
uv run pytest __tests__/python/test_rag_processing.py::TestProcessDocumentForRAG::test_process_epub
```

## Test File Organization

**Location (Node.js):**
- `__tests__/*.test.js` (co-located with dist output)
- Pattern: `__tests__/circuit-breaker.test.js` for `src/lib/circuit-breaker.ts`
- Import from compiled `dist/` directory: `import { CircuitBreaker } from '../dist/lib/circuit-breaker.js'`

**Location (Python):**
- `__tests__/python/*.py` (separate from source)
- Pattern: `test_rag_processing.py`, `test_real_world_validation.py`
- Fixtures: `test_files/` (ground truth PDFs and test data)

**Naming (Node.js):**
- Test files: `*.test.js` (Jest discovers these)
- Test suites: `describe('Module Name', () => { ... })`
- Test cases: `test('should do X', () => { ... })`

**Naming (Python):**
- Test files: `test_*.py` (pytest discovers these)
- Test classes: `TestClassName` (fixtures attached via methods)
- Test methods: `test_method_name_description`

**Structure (Directory):**
```
__tests__/
├── circuit-breaker.test.js
├── retry-manager.test.js
├── index.test.js
├── python/
│   ├── conftest.py
│   ├── test_real_world_validation.py
│   ├── test_rag_processing.py
│   ├── test_garbled_performance.py
│   ├── test_performance_footnote_features.py
│   ├── test_note_classification.py
│   └── test_advanced_search.py
└── (test fixtures in test_files/)
```

## Test Structure

**Suite Organization (Node.js from `__tests__/retry-manager.test.js`):**
```javascript
import { jest, describe, test, expect, beforeEach } from '@jest/globals';

describe('Retry Manager', () => {
  beforeEach(async () => {
    jest.resetModules();
    jest.clearAllMocks();
    retryManager = await import('../dist/lib/retry-manager.js');
  });

  describe('withRetry', () => {
    test('should succeed on first attempt if operation succeeds', async () => {
      const operation = jest.fn().mockResolvedValue('success');
      const result = await retryManager.withRetry(operation);
      expect(result).toBe('success');
      expect(operation).toHaveBeenCalledTimes(1);
    });
  });

  describe('isRetryableError', () => {
    test('should return false for fatal errors', () => {
      const error = { fatal: true };
      expect(retryManager.isRetryableError(error)).toBe(false);
    });
  });
});
```

**Suite Organization (Python from `__tests__/python/test_advanced_search.py`):**
```python
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from lib.advanced_search import (
    detect_fuzzy_matches_line,
    separate_exact_and_fuzzy_results,
    search_books_advanced
)

class TestFuzzyMatchesLineDetection:
    """Tests for detecting the fuzzy matches divider in search results."""

    def test_detect_fuzzy_matches_line_present(self):
        """Should detect fuzzyMatchesLine when present in HTML."""
        html = '''<div class="fuzzyMatchesLine">Maybe you are looking for these:</div>'''
        result = detect_fuzzy_matches_line(html)
        assert result is True

    def test_detect_fuzzy_matches_line_absent(self):
        """Should return False when no fuzzyMatchesLine present."""
        result = detect_fuzzy_matches_line("<div></div>")
        assert result is False
```

**Patterns:**

**Setup/Teardown (Node.js):**
- `beforeEach()` for test isolation: reset modules, clear mocks, reinitialize
- `afterAll()` for cleanup (if needed)
- Module resets inside tests to avoid ESM caching issues

**Setup/Teardown (Python):**
- `conftest.py` for shared configuration (`pytest` auto-discovers)
- Test-specific setup: fixture methods or class `setup_method()`
- Ground truth loader in `test_files/ground_truth_loader.py`

**Assertion Patterns (Node.js from `__tests__/circuit-breaker.test.js`):**
```javascript
// Direct assertions
expect(breaker.getState()).toBe('CLOSED');
expect(breaker.getFailureCount()).toBe(0);

// Promise assertions
await expect(breaker.execute(operation)).rejects.toThrow('Circuit breaker is OPEN');

// Spy/mock assertions
expect(operation).toHaveBeenCalledTimes(2);
expect(operation).toHaveBeenCalledWith(expectedArg);

// State inspection assertions
expect(onStateChange).toHaveBeenCalledWith('CLOSED', 'OPEN');
```

**Assertion Patterns (Python):**
```python
assert result is True
assert result is False
assert error.code == 'NETWORK_ERROR'
assert len(result) > 100
assert distance < 100
```

## Mocking

**Framework (Node.js):** Jest built-in mocking

**Mocking Functions (Node.js from `__tests__/retry-manager.test.js`):**
```javascript
// Function mock that succeeds
const operation = jest.fn().mockResolvedValue('success');

// Function mock that fails then succeeds
const operation = jest.fn()
  .mockRejectedValueOnce(new Error('First failure'))
  .mockRejectedValueOnce(new Error('Second failure'))
  .mockResolvedValueOnce('success');

// Spy/callback mock
const onRetry = jest.fn((attempt, error, delay) => {
  delays.push(delay);
});
```

**Mocking Modules (Node.js from `__tests__/index.test.js`):**
```javascript
jest.unstable_mockModule('@modelcontextprotocol/sdk/server/index.js', () => ({
  Server: jest.fn().mockImplementation((serverInfo, serverOptions) => {
    capturedServerArgs = serverOptions;
    return mockServer;
  }),
}));

// Reset modules before test to apply mocks
jest.resetModules();
const module = await import('../dist/index.js');
```

**Mocking in Python:** `unittest.mock` (Mock, MagicMock, patch, AsyncMock)

**What to Mock:**
- External API calls (network operations)
- File system operations in unit tests
- Third-party library interactions
- Slow operations (unless testing real-world scenarios)

**What NOT to Mock:**
- Business logic (core algorithm/state machine behavior)
- Real file I/O in integration/E2E tests
- Error conditions in end-to-end tests
- Python bridge calls (integration tests use real bridge)

**Real-World Testing Philosophy (from `test_real_world_validation.py`):**
> NO MOCKING - Tests entire pipeline with actual PDFs and documented ground truth.
> Purpose: Prevent hallucinations, catch architectural flaws, validate assumptions.

## Fixtures and Factories

**Test Data (Python from `test_files/ground_truth_loader.py`):**
```python
def load_ground_truth(test_name: str) -> dict:
    """Load ground truth JSON for a test PDF."""
    gt_file = Path('test_files/ground_truth') / f'{test_name}.json'
    with open(gt_file) as f:
        return json.load(f)

# Usage in test
gt = load_ground_truth('derrida_of_grammatology')
pdf_path = Path(gt['pdf_file'])
assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"
```

**Location:**
- `test_files/` - Real PDF files and test resources
- `test_files/ground_truth/` - Ground truth JSON files with expected results
- `test_files/ground_truth_loader.py` - Loader utilities
- `__tests__/python/conftest.py` - Pytest configuration

**Fixture Pattern (Pytest):**
```python
@pytest.fixture
def sample_config():
    return {
        'min_line_length': 10,
        'diagonal_tolerance': 15,
        'proximity_threshold': 20
    }
```

## Coverage

**Requirements:**
- No explicit coverage threshold enforced
- Coverage reports generated but not blocked

**View Coverage (Node.js):**
```bash
node --experimental-vm-modules node_modules/jest/bin/jest.js --coverage
# Output in: coverage/
```

**Pytest Markers (from `pytest.ini`):**
```python
@pytest.mark.integration   # Requires real Z-Library credentials
@pytest.mark.e2e           # End-to-end workflow tests
@pytest.mark.performance   # Performance/load tests
```

**Skip/Run Markers:**
```bash
# Run only unit tests (skip integration/e2e)
pytest -m "not integration and not e2e"

# Run only integration tests
pytest -m "integration"
```

## Test Types

**Unit Tests (Node.js):**
- Scope: Individual functions/classes in isolation
- Mocking: External dependencies mocked
- Examples: `__tests__/retry-manager.test.js`, `__tests__/circuit-breaker.test.js`
- Approach: Jest with jest.fn() mocks for callbacks and operations
- File: `src/lib/retry-manager.ts` → test `__tests__/retry-manager.test.js`

**Unit Tests (Python):**
- Scope: Individual functions with mock external calls
- Mocking: httpx, file I/O, external services
- Examples: `__tests__/python/test_advanced_search.py`
- Approach: `unittest.mock` (Mock, MagicMock, patch decorators)

**Integration Tests:**
- Scope: Python bridge + Z-Library API interaction
- Mocking: Minimal (use real credentials from env vars)
- Marker: `@pytest.mark.integration`
- Requires: `ZLIBRARY_EMAIL`, `ZLIBRARY_PASSWORD` env vars
- File examples: Real PDF processing tests

**E2E Tests:**
- Scope: Complete workflow from MCP client request → Z-Library search/download → file storage
- Mocking: None (full pipeline)
- Marker: `@pytest.mark.e2e`
- File examples: `test_real_world_validation.py` (end-to-end PDF processing)

**Real-World Validation Tests (Python from `test_real_world_validation.py`):**
```python
def test_derrida_xmark_detection_real(self):
    """
    Test X-mark detection with REAL Derrida PDF - END-TO-END pipeline test.
    Validates: Processing completes, X-marks detected, performance within budget
    NOTE: Does NOT validate text recovery (that's a separate hard ML problem)
    NO MOCKS - tests complete pipeline
    """
    gt = load_ground_truth('derrida_of_grammatology')
    pdf_path = Path(gt['pdf_file'])
    assert pdf_path.exists(), f"Test PDF not found: {pdf_path}"

    start = time.time()
    result = process_pdf(pdf_path, output_format='markdown')
    elapsed_ms = (time.time() - start) * 1000

    assert result, "Processing returned empty result"
    assert len(result) > 100, "Output suspiciously short"

    max_time = gt['expected_quality']['processing_time_max_ms']
    assert elapsed_ms < max_time, \
        f"Too slow: {elapsed_ms:.0f}ms > {max_time}ms budget"
```

## Common Patterns

**Async Testing (Node.js from `__tests__/retry-manager.test.js`):**
```javascript
test('should retry on failure and eventually succeed', async () => {
  const operation = jest.fn()
    .mockRejectedValueOnce(new Error('First failure'))
    .mockResolvedValueOnce('success');

  const result = await retryManager.withRetry(operation, {
    maxRetries: 3,
    initialDelay: 10,
    factor: 1
  });

  expect(result).toBe('success');
  expect(operation).toHaveBeenCalledTimes(2);
});
```

**Async Testing (Python):**
```python
@pytest.mark.asyncio
async def test_search_advanced_with_fuzzy_results(self, mock_zlib_class, mock_httpx_class):
    """Async test with mocked AsyncClient."""
    result = await search_books_advanced(
        query="test query",
        email="test@example.com"
    )
    assert result is not None
```

**Error Testing (Node.js from `__tests__/retry-manager.test.js`):**
```javascript
test('should throw error after max retries exhausted', async () => {
  const operation = jest.fn().mockRejectedValue(new Error('Persistent failure'));

  await expect(
    retryManager.withRetry(operation, {
      maxRetries: 2,
      initialDelay: 10,
      factor: 1
    })
  ).rejects.toThrow('Persistent failure');

  expect(operation).toHaveBeenCalledTimes(3); // Initial + 2 retries
});
```

**Error Testing (Python):**
```python
def test_detect_fuzzy_matches_none_html(self):
    """Should handle None HTML gracefully."""
    result = detect_fuzzy_matches_line(None)
    assert result is False
```

**State Machine Testing (Node.js from `__tests__/circuit-breaker.test.js`):**
```javascript
test('should transition to HALF_OPEN after timeout', async () => {
  const breaker = new CircuitBreaker({
    threshold: 2,
    timeout: 100
  });

  // Open the circuit with failures
  for (let i = 0; i < 2; i++) {
    try {
      await breaker.execute(failOp);
    } catch (e) {
      // Expected
    }
  }

  expect(breaker.getState()).toBe('OPEN');

  // Wait for timeout
  await new Promise(resolve => setTimeout(resolve, 150));

  // Next execute should transition to HALF_OPEN and try
  const result = await breaker.execute(successOp);
  expect(result).toBe('success');
  expect(breaker.getState()).toBe('CLOSED');
});
```

## TDD Workflow (RAG Pipeline)

**Mandatory for RAG Features (from `.claude/TDD_WORKFLOW.md`):**

1. **Acquire Real Test PDF** with target feature
2. **Create Ground Truth** (JSON with expected results):
   - Save in `test_files/ground_truth/{feature}.json`
   - Document expected values (X-mark locations, garbled text patterns, etc.)
3. **Write Failing Test** using REAL PDF:
   - No mocks (test complete pipeline)
   - Load ground truth and PDF
   - Process and validate against expected output
4. **Implement Feature** iteratively
5. **Manual Verification:**
   - Side-by-side comparison of real PDF vs. processing output
   - Screenshot validation if visual
6. **Quality Validation:**
   - Run quality checks per `.claude/RAG_QUALITY_FRAMEWORK.md`
   - Validate performance budget (`test_files/performance_budgets.json`)
7. **Regression Testing:**
   - Run ALL real PDF tests
   - Ensure no regressions introduced

**Example from `test_real_world_validation.py`:**
```python
def test_derrida_sous_rature_detection(self):
    """
    Test that X-marks (sous-rature) are correctly DETECTED.

    Ground truth: X-mark crossing out "is" at specific bbox location
    Critical: Must detect real philosophical sous-rature, not artifacts

    NOTE: Text RECOVERY under heavy X-marks is a hard ML problem requiring
    specialized models (inpainting, trained on crossed-out text, NLP prediction).
    This test verifies DETECTION accuracy only. Recovery is future work.
    """
    from lib.strikethrough_detection import detect_strikethrough_enhanced

    gt = load_ground_truth('derrida_of_grammatology')
    pdf_path = Path(gt['pdf_file'])

    for xmark in gt['features']['xmarks']:
        page_num = xmark['page']
        result = detect_strikethrough_enhanced(pdf_path, page_num, bbox=None)
        assert result.has_xmarks, f"No X-marks detected on page {page_num}"
```

---

*Testing analysis: 2026-01-28*
