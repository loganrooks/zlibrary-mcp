# Architecture

**Analysis Date:** 2026-01-28

## Pattern Overview

**Overall:** Layered Model Context Protocol (MCP) server with dual-language bridge pattern

**Key Characteristics:**
- **MCP Standard Compliance**: Implements Model Context Protocol v1.8.0+ with tool registry, schema validation, and structured responses
- **Dual-Language Implementation**: Node.js/TypeScript frontend (MCP + Z-Library API layer) bridges to Python backend (document processing, web scraping)
- **Resilience Patterns**: Circuit breaker, retry with exponential backoff, and error classification for fault tolerance
- **Modular Python Processing**: Separate concern modules for RAG, metadata, validation, and specialized text processing
- **Vendored Dependency**: Custom fork of Z-Library stored in `zlibrary/` for controlled API access

## Layers

**MCP Server Layer (Node.js/TypeScript):**
- Purpose: HTTP/stdio interface for AI assistants, tool registration, parameter validation
- Location: `src/index.ts`
- Contains: Tool definitions, Zod schemas (input/output), MCP request handlers, tool annotations
- Depends on: `zlibrary-api`, MCP SDK, zod
- Used by: AI assistants via MCP protocol

**API Bridge Layer:**
- Purpose: Orchestrates communication between Node.js and Python, implements resilience patterns
- Location: `src/lib/zlibrary-api.ts`
- Contains: API handler functions (searchBooks, downloadBookToFile, processDocumentForRag), Python function calls, error handling
- Depends on: `python-bridge`, `retry-manager`, `circuit-breaker`, `errors`
- Used by: MCP tool handlers in index.ts

**Resilience Infrastructure:**
- Purpose: Provides fault tolerance through retry logic and circuit breaker pattern
- Location: `src/lib/retry-manager.ts`, `src/lib/circuit-breaker.ts`
- Contains: Exponential backoff, error classification, state machines
- Depends on: custom error types
- Used by: zlibrary-api layer (wraps all Python calls)

**Environment Management:**
- Purpose: Manages Python virtual environment lifecycle and path resolution
- Location: `src/lib/venv-manager.ts`, `src/lib/paths.ts`
- Contains: UV venv detection, Python executable resolution, path helpers
- Depends on: file system, child_process (execSync)
- Used by: Python bridge initialization

**Python Bridge Layer:**
- Purpose: Executes Python functions via PythonShell with JSON serialization
- Location: `src/lib/python-bridge.ts`
- Contains: PythonShell invocation, JSON parse/stringify, error wrapping
- Depends on: `venv-manager`, `paths`
- Used by: zlibrary-api to call Python functions

**Python Processing Layer (Python):**
- Purpose: Core Z-Library operations, document processing, RAG extraction
- Location: `lib/python_bridge.py` (main entry point)
- Contains: Search, download, metadata extraction, document processing
- Sub-modules:
  - `lib/rag_processing.py`: PDF/EPUB/TXT text extraction and cleaning
  - `lib/advanced_search.py`: Multi-parameter search logic
  - `lib/author_tools.py`: Author-specific search
  - `lib/booklist_tools.py`: Booklist exploration
  - `lib/enhanced_metadata.py`: Rich metadata extraction
  - `lib/metadata_generator.py`: Metadata sidecar creation
  - `lib/footnote_corruption_model.py`: Bayesian symbol recovery
  - `lib/note_classification.py`: Note type attribution
  - `lib/garbled_text_detection.py`: Quality validation

**Error Handling Layer:**
- Purpose: Unified error types for consistent handling and logging
- Location: `src/lib/errors.ts`
- Contains: ZLibraryError, NetworkError, AuthenticationError, DomainError, PythonBridgeError, TimeoutError
- Depends on: none
- Used by: all layers for error classification and routing

## Data Flow

**Search Flow:**
1. MCP client → `index.ts` CallToolRequest for `search_books`
2. Zod validates arguments against `SearchBooksParamsSchema`
3. `handlers.searchBooks()` → `zlibrary-api.searchBooks()`
4. `zlibrary-api` wraps call with retry/circuit-breaker
5. `python-bridge.ts` → PythonShell invokes `python_bridge.py:search()`
6. Python calls `AsyncZlib` from vendored zlibrary fork
7. Results parsed back through layers as JSON
8. MCP response with `BookResultSchema[]` sent to client

**Download + RAG Flow:**
1. MCP client → `download_book_to_file` with book details + process_for_rag=true
2. `handlers.downloadBookToFile()` → `zlibrary-api.downloadBookToFile()`
3. Python downloads to `./downloads/`
4. If process_for_rag=true: invokes `rag_processing.process_document()`
5. RAG processing extracts text, detects corruption, validates metadata
6. Output written to `./processed_rag_output/` with metadata sidecar
7. MCP response: {file_path, processed_file_path, processing_error?}

**Resilience Application:**
- All Python calls wrapped with: `withRetry(operation, {maxRetries:3, exponentialBackoff}) → circuitBreaker.execute()`
- Retry: Network errors, timeouts, server errors (5xx) → retryable
- No retry: Auth errors, validation errors, fatal errors → non-retryable
- Circuit breaker: After 5 failures in 60s, opens to prevent cascading failures

**State Management:**
- **Stateless**: MCP server maintains no per-client state
- **Transient**: Book download/processing creates local files (downloads/, processed_rag_output/)
- **No caching**: Each request freshly executes against Z-Library API
- **Error context**: Errors carry metadata (functionName, args, stderr) for debugging

## Key Abstractions

**Tool Registry (toolRegistry):**
- Purpose: Declares all available MCP tools with schemas and handlers
- Examples: `toolRegistry.search_books`, `toolRegistry.download_book_to_file`
- Pattern: `{description, schema, outputSchema, handler}` tuple
- Usage: Generated into MCP tools capability at server startup

**Zod Schemas:**
- Purpose: Runtime parameter validation for tool inputs/outputs
- Examples: `SearchBooksParamsSchema`, `DownloadBookToFileParamsSchema`
- Pattern: Define with `z.object({...})`, parse with `schema.safeParse(args)`
- Benefit: Type-safe, generates JSON Schema automatically for MCP clients

**Error Hierarchy (ZLibraryError):**
- Purpose: Uniform error classification for routing and retry logic
- Subclasses: NetworkError, AuthenticationError, DomainError, PythonBridgeError, TimeoutError
- Pattern: Errors carry `{code, context, retryable, fatal}` metadata
- Usage: `isRetryableError()` classifies to determine retry vs. fail-fast

**Circuit Breaker (CircuitBreaker class):**
- Purpose: Prevents cascading failures by stopping requests to failing service
- States: CLOSED → HALF_OPEN (timeout) → OPEN (failures exceed threshold)
- Pattern: `pythonBridgeCircuitBreaker.execute(operation)` throws if OPEN
- Configuration: threshold=5 failures, timeout=60s before retry

**Retry Manager (withRetry function):**
- Purpose: Implements exponential backoff for transient failures
- Pattern: `await withRetry(operation, {maxRetries:3, initialDelay:1000, factor:2})`
- Callback: `onRetry(attempt, error, delay)` for logging/metrics
- Configuration: Env vars for RETRY_MAX_RETRIES, RETRY_INITIAL_DELAY, RETRY_MAX_DELAY, RETRY_FACTOR

## Entry Points

**MCP Server Entry Point:**
- Location: `src/index.ts`
- Triggers: Node.js process launch → `start()` async function
- Responsibilities:
  1. Ensure logs directory exists
  2. Generate tool capability object (Zod schemas → JSON Schema)
  3. Create Server instance with MCP ServerInfo + capabilities
  4. Register request handlers for tools/list, tools/call, resources/list, prompts/list
  5. Connect to StdioServerTransport
  6. Log ready message

**Tool Handler Pattern:**
- Location: `index.ts` handlers object
- Example: `handlers.searchBooks(args) → zlibrary-api.searchBooks(args) → callPythonFunction('search', ...)`
- Validation: Zod parses args, handler catches errors, returns `{error}` or result
- Wrapping: MCP response format: `{content: [{type:'text', text:JSON.stringify(result)}], structuredContent: result}`

**CLI Invocation:**
- File: `index.js` (ESM wrapper, minimal)
- Command: `node dist/index.js`
- Auto-detection: Entry point checks `import.meta.url === file://${process.argv[1]}` to auto-start

## Error Handling

**Strategy:** Layered error classification with context preservation

**Patterns:**
- **Try/catch with wrapping**: Catch low-level errors, wrap in domain-specific error types
- **Error context**: Attach {functionName, args, stderr, originalError} for debugging
- **Retryable vs fatal**: Classify at error creation, use in retry logic
- **MCP response format**: Errors returned as `{error: {message, code?, context?}}` to tool handlers
- **Logging**: Console.error for critical failures, contextual metadata for investigation
- **Circuit breaker integration**: Errors trigger failure counting, state transitions logged

**Example error flow:**
1. Python script times out → PythonShell throws error with stderr
2. Catch in `callPythonFunction()` → wrap as `PythonBridgeError({retryable: true})`
3. Retry logic sees `retryable: true` → schedules retry with backoff
4. After max retries → error propagates to tool handler
5. Tool handler catches → returns `{error: {message}}` to MCP client

## Cross-Cutting Concerns

**Logging:**
- Console methods (console.log, console.error) for real-time visibility
- File logging to `logs/nodejs_debug.log` for handler args/responses (optional)
- Python uses logging module (configured at startup: DEBUG or INFO level)

**Validation:**
- Zod schemas validate all tool inputs before handler execution
- `schema.safeParse(args)` returns validation errors in structured format
- MCP returns validation failures as `{isError: true, content}` responses

**Authentication:**
- Z-Library credentials via environment variables: ZLIBRARY_EMAIL, ZLIBRARY_PASSWORD
- Credentials passed to Python bridge which authenticates with Z-Library API
- No session management (stateless); credentials validated on each API call
- AuthenticationError marks failures as non-retryable, fatal

---

*Architecture analysis: 2026-01-28*
