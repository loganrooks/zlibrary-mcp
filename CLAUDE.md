# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Quick Start for Claude Code

**Essential Reading Order**:
1. `.claude/PROJECT_CONTEXT.md` - Complete project understanding
2. `.claude/ISSUES.md` - Known problems and priorities
3. `.claude/PATTERNS.md` - Code patterns to follow
4. `.claude/DEBUGGING.md` - Troubleshooting guide
5. `.claude/MCP_SERVERS.md` - Development tools setup
6. `.claude/META_LEARNING.md` - Lessons learned and insights

## Project Overview

Z-Library MCP (Model Context Protocol) server that enables AI assistants to search, download, and process books from Z-Library. The project uses a Node.js/TypeScript frontend with a Python bridge backend for document processing.

## Architecture

### Dual-Language Design
- **Node.js/TypeScript Layer** (`src/`): MCP server implementation handling tool registration and client communication
- **Python Bridge** (`lib/python_bridge.py`, `lib/rag_processing.py`): Handles Z-Library API interaction and document processing (EPUB, TXT, PDF)
- **Vendored Z-Library Fork** (`zlibrary/`): Modified fork of sertraline/zlibrary with custom download logic

### Key Components
- `src/index.ts`: MCP server entry point with tool definitions
- `src/lib/zlibrary-api.ts`: Bridge between Node.js and Python via PythonShell
- `src/lib/venv-manager.ts`: Manages Python virtual environment lifecycle
- `lib/python_bridge.py`: Core Python logic for Z-Library operations
- `lib/rag_processing.py`: Document processing for RAG workflows

### Data Flow
1. MCP client → Node.js server (tool request)
2. Node.js → Python bridge (via PythonShell)
3. Python → Z-Library API or document processing
4. Results flow back through the same chain

## Development Commands

### Setup
```bash
# Initial setup (creates venv and installs dependencies)
./setup_venv.sh

# Install Node dependencies
npm install

# Build TypeScript
npm run build
```

### Testing
```bash
# Run all tests (Jest for Node.js + Pytest for Python)
npm test

# Run Python tests only
source venv/bin/activate
pytest

# Run specific Python test
pytest __tests__/python/test_rag_processing.py::TestProcessDocumentForRAG::test_process_epub

# Run Jest tests with coverage
node --experimental-vm-modules node_modules/jest/bin/jest.js --coverage
```

### Running the Server
```bash
# Build and run
npm run build && npm start

# Or directly
node dist/index.js
```

## File Organization

- **Downloads**: Books downloaded to `./downloads/` by default
- **Processed RAG Output**: Extracted text saved to `./processed_rag_output/`
- **Test Fixtures**: Located in `test_files/` for Python tests
- **Documentation**: Architecture decisions in `docs/adr/`, specifications in `docs/`

## Environment Configuration

Required environment variables:
- `ZLIBRARY_EMAIL`: Z-Library account email
- `ZLIBRARY_PASSWORD`: Z-Library account password
- `ZLIBRARY_MIRROR`: (Optional) Custom Z-Library mirror URL

## Important Design Decisions

### ADR-002: Download Workflow
- Downloads use `bookDetails` from search results instead of direct ID lookup
- Book detail page scraping required to get actual download link

### ADR-003: ID Lookup Deprecation
- `get_book_by_id` deprecated due to unreliability
- Always use `search_books` to find books

### RAG Pipeline (v2)
- Processes documents to text files rather than returning raw text
- Returns file paths to avoid context overload
- Supports combined download+process or separate operations

## Python Virtual Environment

The project maintains its own Python venv (`.venv/`) with these key dependencies:
- Custom zlibrary fork (installed as editable: `-e ./zlibrary`)
- ebooklib (EPUB processing)
- PyMuPDF (PDF processing)
- beautifulsoup4, lxml (HTML parsing)
- httpx, aiofiles (async operations)

## Testing Strategy

### Jest (Node.js)
- Tests in `__tests__/*.test.js`
- Uses ESM modules (note the `--experimental-vm-modules` flag)
- Mocks Python bridge for unit testing
- Coverage reports in `coverage/`

### Pytest (Python)
- Tests in `__tests__/python/`
- Fixtures in `test_files/`
- Uses pytest-mock for mocking
- Run from project root with `pytest.ini` configuration

## MCP Tools Available

- `search_books`: Primary method for finding books
- `full_text_search`: Search within book content
- `get_download_history`: View user's download history
- `get_download_limits`: Check download limits
- `get_recent_books`: Get recently added books
- `download_book_to_file`: Download book with optional RAG processing
- `process_document_for_rag`: Process existing file for RAG

## Common Issues & Solutions

### Python Environment
- If Python bridge fails, check venv activation: `source venv/bin/activate`
- Ensure Python 3.9+ is installed
- Verify requirements: `pip install -r requirements.txt`

### Jest ESM Issues
- Tests use `.js` extensions but import TypeScript compiled to `dist/`
- Module resolution configured in `jest.config.js` moduleNameMapper

### Download Failures
- Check Z-Library credentials are set correctly
- Verify network access to Z-Library (may be blocked in some regions)
- Review `docs/adr/ADR-002-Download-Workflow-Redesign.md` for download flow

## Current Development Branch

Working on: `feature/rag-robustness-enhancement`
- Focus: PDF quality analysis and extraction improvements
- Key files: `lib/rag_processing.py`, related tests

## Development Ecosystem

### 📚 Essential Documentation (.claude folder)

The `.claude` folder contains comprehensive documentation for development:

- **PROJECT_CONTEXT.md**: Mission, architecture principles, domain model, performance targets
- **ISSUES.md**: All known issues categorized by severity with action items
- **PATTERNS.md**: Code patterns for error handling, logging, caching, testing
- **DEBUGGING.md**: Troubleshooting guides, diagnostic scripts, common solutions
- **MCP_SERVERS.md**: Playwright, SQLite, and other MCP server configurations
- **META_LEARNING.md**: Lessons learned, architectural insights, future predictions

### 🎯 Current Priorities

Check `.claude/ISSUES.md` for the complete list. Top priorities:
1. Fix venv manager test warnings (ISSUE-002)
2. Implement retry logic with exponential backoff (ISSUE-005)
3. Add fuzzy search capabilities (SRCH-001)
4. Create download queue management (DL-001)

### 🔧 Development Workflow

1. **Before Starting**: Read `.claude/PROJECT_CONTEXT.md`
2. **Check Issues**: Review `.claude/ISSUES.md` for known problems
3. **Follow Patterns**: Use code patterns from `.claude/PATTERNS.md`
4. **Debug Issues**: Consult `.claude/DEBUGGING.md` for solutions
5. **Learn from History**: Check `.claude/META_LEARNING.md` for insights

### 🚦 Quick Status Check

```bash
# Run health check
bash .claude/scripts/health_check.sh

# Check for critical issues
grep "CRITICAL\|HIGH" .claude/ISSUES.md

# View recent errors
tail -f logs/error.log | grep -i error
```

### 💡 Key Architectural Decisions

- **No Official API**: Z-Library has no public API, using EAPI via web scraping
- **Hydra Mode**: Domains change frequently, need dynamic discovery
- **Python Bridge**: Best document processing libraries are Python-based
- **File-Based RAG**: Return file paths, not raw text (prevents AI memory overflow)
- **Vendored Fork**: Custom zlibrary fork for control over critical dependency

### 🛠️ Recommended MCP Servers

For optimal development with Claude Code, configure these MCP servers:
1. **Playwright**: E2E testing of web scraping
2. **SQLite**: Local caching and metadata storage
3. **Filesystem**: Download directory management
4. **Sequential**: Complex debugging and analysis

See `.claude/MCP_SERVERS.md` for complete configuration.