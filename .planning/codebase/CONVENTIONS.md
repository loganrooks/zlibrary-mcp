# Coding Conventions

**Analysis Date:** 2026-01-28

## Naming Patterns

**Files:**
- TypeScript files: `kebab-case` (e.g., `retry-manager.ts`, `circuit-breaker.ts`, `zlibrary-api.ts`)
- Python files: `snake_case` (e.g., `rag_processing.py`, `garbled_text_detection.py`)
- Test files: `test_*.py` (Python) or `*.test.js` (Node.js)

**Functions:**
- TypeScript/JavaScript: `camelCase` (e.g., `withRetry`, `getManagedPythonPath`, `callPythonFunction`)
- Python: `snake_case` (e.g., `process_pdf`, `detect_garbled_text`, `load_ground_truth`)
- Private methods: prefix with `_` (e.g., `_onSuccess()`, `_transitionTo()`)

**Variables:**
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `BRIDGE_SCRIPT_PATH`, `OCR_AVAILABLE`, `PYMUPDF_AVAILABLE`)
- Local variables: `camelCase` (TypeScript/JS), `snake_case` (Python)
- Configuration objects: `camelCase` (e.g., `retryOptions`, `circuitBreakerOptions`)

**Types:**
- Interface names: `PascalCase` (e.g., `ErrorContext`, `RetryOptions`, `CircuitBreakerOptions`)
- Class names: `PascalCase` (e.g., `ZLibraryError`, `CircuitBreaker`, `NetworkError`)
- Enum/union types: `PascalCase` (e.g., `CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN'`)

## Code Style

**Formatting:**
- No specific formatter configured (.prettierrc not present)
- Code uses 2-space indentation throughout
- Lines wrap at ~100-120 characters (observed in source files)
- Imports grouped by: external libraries, then local modules

**Linting:**
- No ESLint config present (.eslintrc not found)
- TypeScript strict mode enabled in `tsconfig.json` with:
  - `"strict": true`
  - `"noImplicitAny": true`
  - `"noUncheckedIndexedAccess": true`

**Module System:**
- ESM (ES Modules) throughout Node.js code
- All imports use `.js` extension for local files (required for ESM): `import * as zlibraryApi from './lib/zlibrary-api.js'`
- `"type": "module"` in package.json
- `import type` for TypeScript types: `import type { CallToolRequest } from '@modelcontextprotocol/sdk/types.js'`

## Import Organization

**Order (TypeScript/JavaScript):**
1. Built-in Node.js modules (`fs`, `path`, `url`, etc.)
2. External npm packages (`zod`, `python-shell`, SDK imports)
3. Local project modules (relative imports with `./`)
4. Type imports (`import type { ... }`)

**Path Aliases:**
- No path aliases configured in `tsconfig.json` (commented out)
- All imports use relative paths: `../lib/`, `./lib/`

**Example from `src/index.ts`:**
```typescript
import { z, ZodObject, ZodRawShape } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import * as fs from 'fs';
import { appendFile as appendFileAsync } from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import type { CallToolRequest } from '@modelcontextprotocol/sdk/types.js';

import * as zlibraryApi from './lib/zlibrary-api.js';
```

## Error Handling

**Custom Error Classes (see `src/lib/errors.ts`):**
- Extend from base `ZLibraryError` class with properties:
  - `code: string` - error classification code (e.g., 'NETWORK_ERROR', 'AUTH_ERROR')
  - `context?: ErrorContext` - enriched context object with metadata
  - `retryable: boolean` - whether operation should be retried
  - `fatal: boolean` - whether error is unrecoverable

- Specific error types for categories:
  - `NetworkError` - network operations fail
  - `AuthenticationError` - auth fails (non-retryable)
  - `DomainError` - Z-Library domain unavailable
  - `PythonBridgeError` - Python process fails
  - `TimeoutError` - operations exceed time limit

**Pattern: Error Context Enrichment (from `src/lib/errors.ts`):**
```typescript
static fromError(error: any, context?: ErrorContext): ZLibraryError {
  if (error instanceof ZLibraryError) {
    return error;
  }
  const message = error.message || String(error);
  const code = error.code || 'UNKNOWN_ERROR';
  const retryable = !['AUTH_ERROR', 'FORBIDDEN', 'INVALID_INPUT'].includes(code);

  return new ZLibraryError(message, code, {
    ...context,
    originalError: error,
    stack: error.stack,
    timestamp: new Date().toISOString()
  }, retryable);
}
```

**Retry Logic Pattern (see `src/lib/retry-manager.ts`):**
- `withRetry()` function wraps async operations with exponential backoff
- Respects `shouldRetry` predicate to skip non-retryable errors
- Supports custom `onRetry` callback for monitoring
- Default: 3 retries, 1000ms initial delay, 30000ms max, 2x backoff factor

**Circuit Breaker Pattern (see `src/lib/circuit-breaker.ts`):**
- States: `CLOSED` (normal), `OPEN` (failing, reject operations), `HALF_OPEN` (recovery test)
- Transitions to OPEN after `threshold` (default 5) consecutive failures
- Transitions to HALF_OPEN after `timeout` (default 60000ms) of OPEN state
- Success on HALF_OPEN transitions back to CLOSED
- Emits `onStateChange` callback on transitions

## Logging

**Framework:** `console` (no dedicated logger framework configured)

**Patterns:**
- `console.log()` for informational messages (retry attempts, state changes)
- `console.error()` for errors and failures
- Messages include structured context as second argument:
  ```typescript
  console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms...`, {
    error: errorMessage,
    attempt: attempt + 1,
    maxRetries,
    delay
  });
  ```

**Typical logging locations:**
- `src/lib/retry-manager.ts:50-55` - retry attempts
- `src/lib/circuit-breaker.ts:88-92, 101` - circuit state changes
- `src/lib/venv-manager.ts:64` - Python environment info
- `src/lib/zlibrary-api.ts:117` - Python bridge errors

## Comments

**When to Comment:**
- JSDoc/TSDoc on public functions, classes, interfaces (comprehensive)
- Inline comments for complex logic or non-obvious behavior
- No comments for self-explanatory code (naming is preferred)

**JSDoc/TSDoc Pattern (from `src/lib/retry-manager.ts`):**
```typescript
/**
 * Execute an operation with retry logic and exponential backoff
 * @param operation - The async operation to execute
 * @param options - Retry configuration options
 * @returns Promise resolving with the operation result
 * @throws The last error if all retries are exhausted
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T>
```

**Inline Comments:**
- Used to explain non-obvious behavior or design decisions
- Example from `src/lib/zlibrary-api.ts:46-52`:
  ```typescript
  // Serialize arguments as JSON *before* creating options
  const serializedArgs = JSON.stringify(args);
  const options: PythonShellOptions = {
    mode: 'text', // Revert back to text mode
    pythonPath: venvPythonPath, // Use the Python from our managed venv
  ```

## Function Design

**Size:** Functions are concise, typically 15-50 lines
- Single responsibility principle enforced
- Helper functions for repeated logic (e.g., `isRetryableError()` in `src/lib/retry-manager.ts`)

**Parameters:**
- Use options objects for functions with multiple parameters (e.g., `RetryOptions`, `CircuitBreakerOptions`)
- Destructure options with defaults: `const { maxRetries = 3, ... } = options`
- Generic type parameters for reusable patterns: `async function withRetry<T>(operation: () => Promise<T>)`

**Return Values:**
- Always return `Promise<T>` for async operations
- Error codes/context included in exception details (not in return value)
- Return `void` for functions without meaningful output

**Example from `src/lib/circuit-breaker.ts`:**
```typescript
async execute<T>(operation: () => Promise<T>): Promise<T> {
  if (this.state === 'OPEN') {
    if (this.lastFailureTime && Date.now() - this.lastFailureTime > this.timeout) {
      this.transitionTo('HALF_OPEN');
    } else {
      throw new Error('Circuit breaker is OPEN');
    }
  }
  // ...
}
```

## Module Design

**Exports:**
- Named exports for functions/classes: `export function withRetry()`, `export class CircuitBreaker`
- Interface exports for type definitions: `export interface ErrorContext`
- No default exports (explicit named imports required)

**Barrel Files:**
- Not used in project (each module exports specific items)
- Each file in `src/lib/` is imported individually

**File Responsibilities (single responsibility per file):**
- `errors.ts` - Custom error classes only
- `retry-manager.ts` - Retry logic with exponential backoff
- `circuit-breaker.ts` - Circuit breaker state machine
- `zlibrary-api.ts` - Python bridge communication
- `venv-manager.ts` - Python environment initialization
- `paths.ts` - Path resolution utilities

## Python Conventions

**Import Organization (from `lib/rag_processing.py`):**
1. Standard library: `import asyncio`, `import re`, `import logging`
2. External packages: `import aiofiles`, `import fitz`
3. Local modules: `from lib.rag_data_models import ...`
4. Optional dependencies: Wrapped in try/except with availability flags

**Type Hints:**
- Used throughout Python code: `def process_pdf(pdf_path: Path, output_format: 'Optional[str]') -> str`
- Optional types: `Optional[Any]`, `Dict[str, Any]`, `List[Tuple[...]]`

**Error Handling (Python):**
- Custom exceptions for specific error conditions
- Context managers for resource cleanup
- TDD approach with real file testing (no mocks when possible)

---

*Conventions analysis: 2026-01-28*
