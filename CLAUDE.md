# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Quick Start for Claude Code

**Essential Reading Order**:
1. `.claude/PROJECT_CONTEXT.md` - Complete project understanding
2. `ISSUES.md` - Known problems and priorities (at project root)
3. `.claude/IMPLEMENTATION_ROADMAP.md` - Concrete action plan and fixes
4. `.claude/PATTERNS.md` - Code patterns to follow
5. `.claude/DEBUGGING.md` - Troubleshooting guide
6. `.claude/VERSION_CONTROL.md` - Git workflow and best practices
7. `.claude/CI_CD.md` - CI/CD strategy and implementation
8. `.claude/MCP_SERVERS.md` - Development tools setup
9. `.claude/META_LEARNING.md` - Lessons learned and insights

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

### Path Resolution Strategy

**Design Decision**: Python scripts remain in source `lib/` directory (not copied to `dist/`)

**Runtime Path Logic**:
```typescript
// From dist/lib/python-bridge.js at runtime:
const scriptPath = path.resolve(__dirname, '..', '..', 'lib', 'python_bridge.py');

// Navigation: dist/lib/ → dist/ → project_root/ → lib/python_bridge.py
```

**Path Helper Module** (Recommended for new code):
```typescript
import { getPythonScriptPath, getPythonLibDirectory } from './lib/paths.js';

const scriptPath = getPythonScriptPath('python_bridge.py');
// Returns: /project/lib/python_bridge.py

const libDir = getPythonLibDirectory();
// Returns: /project/lib
```

**Benefits**:
- ✅ Single source of truth (Python scripts in `lib/`)
- ✅ No build process changes needed
- ✅ No file duplication
- ✅ Development-friendly (edit Python directly)

**Validation**: Build automatically validates all Python files exist (`npm run build`)

**Documentation**: See [ADR-004](docs/adr/ADR-004-Python-Bridge-Path-Resolution.md) for complete rationale and [DEPLOYMENT.md](docs/DEPLOYMENT.md) for edge cases.

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

### Git Workflow
```bash
# Create feature branch (see .claude/VERSION_CONTROL.md for naming conventions)
git checkout -b feature/your-feature-name

# Check status before committing
git status
git diff

# Stage and commit with conventional format
git add .
git commit -m "feat: add new feature" # See VERSION_CONTROL.md for commit format

# Push to remote and create PR
git push -u origin feature/your-feature-name
```

For complete Git workflow, branching strategy, and PR process, see `.claude/VERSION_CONTROL.md`.

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

### Required Variables
- `ZLIBRARY_EMAIL`: Z-Library account email
- `ZLIBRARY_PASSWORD`: Z-Library account password
- `ZLIBRARY_MIRROR`: (Optional) Custom Z-Library mirror URL

### Retry Logic Configuration (Optional)
All API operations include automatic retry with exponential backoff and circuit breaker protection.

**Retry Settings**:
- `RETRY_MAX_RETRIES` (default: `3`): Maximum retry attempts
- `RETRY_INITIAL_DELAY` (default: `1000`): Initial retry delay in ms
- `RETRY_MAX_DELAY` (default: `30000`): Maximum retry delay in ms
- `RETRY_FACTOR` (default: `2`): Exponential backoff multiplier

**Circuit Breaker Settings**:
- `CIRCUIT_BREAKER_THRESHOLD` (default: `5`): Failures before opening circuit
- `CIRCUIT_BREAKER_TIMEOUT` (default: `60000`): Time in ms before retry after circuit opens

See [docs/RETRY_CONFIGURATION.md](docs/RETRY_CONFIGURATION.md) for detailed configuration guide.

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
- Branching Strategy: See `.claude/VERSION_CONTROL.md` for feature branch conventions and workflow

## Development Ecosystem

### 📚 Essential Documentation (.claude folder)

The `.claude` folder contains comprehensive documentation for development:

- **PROJECT_CONTEXT.md**: Mission, architecture principles, domain model, performance targets
- **ISSUES.md** (root): All known issues categorized by severity with action items
- **IMPLEMENTATION_ROADMAP.md**: Concrete action plan, priority fixes, 3-week roadmap
- **PATTERNS.md**: Code patterns for error handling, logging, caching, testing
- **DEBUGGING.md**: Troubleshooting guides, diagnostic scripts, common solutions
- **VERSION_CONTROL.md**: Git workflows, branching strategy, commit conventions
- **CI_CD.md**: CI/CD pipelines, quality gates, deployment automation
- **MCP_SERVERS.md**: Playwright, SQLite, and other MCP server configurations
- **META_LEARNING.md**: Lessons learned, architectural insights, future predictions

### 🎯 Current Priorities

Check `ISSUES.md` (project root) for the complete list. Top priorities:
1. Fix venv manager test warnings (ISSUE-002)
2. Implement retry logic with exponential backoff (ISSUE-005)
3. Add fuzzy search capabilities (SRCH-001)
4. Create download queue management (DL-001)

### 🔧 Development Workflow

1. **Setup Version Control**: Create feature branch per `.claude/VERSION_CONTROL.md`
2. **Before Coding**: Read `.claude/PROJECT_CONTEXT.md` for architecture
3. **Check Issues**: Review `ISSUES.md` (root) for known problems
4. **Follow Patterns**: Use code patterns from `.claude/PATTERNS.md`
5. **Write & Test**: Implement with tests, following TDD when possible
6. **Debug Issues**: Consult `.claude/DEBUGGING.md` for solutions
7. **Commit Properly**: Use conventional commits per `.claude/VERSION_CONTROL.md`
8. **Create PR**: Follow PR template and review process in VERSION_CONTROL.md
9. **Learn & Document**: Update `.claude/META_LEARNING.md` with insights

### 🚦 Quick Status Check

```bash
# Git status - current branch and changes
git status
git branch --show-current
git diff --stat

# Run health check
bash .claude/scripts/health_check.sh

# Check for critical issues
grep "CRITICAL\|HIGH" ISSUES.md

# View recent errors
tail -f logs/error.log | grep -i error

# Check uncommitted changes before PR
git diff --check  # Check for whitespace errors
git log --oneline -5  # Review recent commits
```

For detailed Git operations, see `.claude/VERSION_CONTROL.md`.

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

## 🤝 Contributing

Before contributing to this project, please review our comprehensive version control guidelines:

📖 **Required Reading: `.claude/VERSION_CONTROL.md`**

This document covers:
- **Branching Strategy**: Feature branches, naming conventions, and workflow
- **Commit Standards**: Conventional commits format with examples
- **Pull Request Process**: Templates, review guidelines, and merge requirements
- **Code Review**: Best practices and checklist
- **Release Process**: Semantic versioning and changelog management

### Quick Contribution Steps
1. Fork the repository and clone locally
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes following patterns in `.claude/PATTERNS.md`
4. Commit using conventional format (see VERSION_CONTROL.md)
5. Push and create PR with our template
6. Ensure CI passes and address review feedback

### Development Standards
- Follow existing code patterns (`.claude/PATTERNS.md`)
- Add tests for new functionality
- Update documentation as needed
- Check for issues (`ISSUES.md`) you might address

For CI/CD pipeline details, see `.claude/CI_CD.md`.