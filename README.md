# Z-Library MCP Server

<!-- Last Verified: 2026-02-01 -->

This Model Context Protocol (MCP) server provides access to Z-Library for AI coding assistants like Claude Code, RooCode, and Cline. It allows AI assistants to search for books, retrieve metadata, download files, and process document content for Retrieval-Augmented Generation (RAG) workflows.

## Current Status

- **Version:** 2.1.0 (Post-cleanup, EAPI migration)
- **MCP SDK:** 1.25+ (McpServer API with `server.tool()` registration)
- **Transport:** EAPI JSON endpoints (bypasses Cloudflare browser challenges)
- **Python:** UV-based dependency management, decomposed lib/rag/ modules
- **Stability:** All test suites passing
- **Branch:** `master`

### Recent Changes (Jan-Feb 2026)
- **EAPI Migration**: All API calls use Z-Library EAPI JSON endpoints (no more HTML scraping)
- **MCP SDK 1.25+**: Upgraded from 1.8, using McpServer API with `server.tool()` registration
- **Python Decomposition**: Monolithic `rag_processing.py` (4,968 lines) split into lib/rag/ domain modules (all <500 lines)
- **Health Check**: Cloudflare detection for upstream monitoring
- **12 MCP Tools**: Complete search, metadata, download, and RAG capabilities

## Architecture Overview

- **Node.js/TypeScript MCP Server**: 12 tools registered via McpServer `server.tool()` API
- **Python Bridge**: Z-Library EAPI client (httpx) + document processing (lib/rag/ modules)
- **EAPI Transport**: JSON API endpoints at `/eapi/` bypass Cloudflare browser challenges
- **UV-Based Python Environment**: Project-local `.venv/` with `uv.lock` for reproducible builds
- **Vendored Z-Library Fork**: Custom EAPI client + legacy AsyncZlib for file downloads
- **RAG Pipeline**: EPUB/PDF/TXT extraction with quality detection, output to files (not memory)

## Prerequisites

- Node.js 18 or newer
- Python 3.10 or newer
- [UV](https://docs.astral.sh/uv/) - Modern Python package manager
- Z-Library account (for authentication)

## Installation

### 1. Install UV (one-time)

```bash
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip:
pip install uv

# Or via homebrew (macOS):
brew install uv
```

### 2. Setup Project

```bash
# Clone this repository
git clone https://github.com/loganrooks/zlibrary-mcp.git
cd zlibrary-mcp

# Setup Python environment with UV
bash setup-uv.sh
# Or manually: uv sync

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build
```

## Configuration

The server requires Z-Library credentials:

```bash
export ZLIBRARY_EMAIL="your-email@example.com"
export ZLIBRARY_PASSWORD="your-password"
# Optional: Specify the Z-Library mirror domain
# export ZLIBRARY_MIRROR="https://your-mirror.example"
```

## Usage

### Starting the Server

```bash
node dist/index.js
```

### Integration with MCP Clients

**Important**: The MCP server is a **Node.js application**. UV is only used for setup.

```
Setup:  uv sync --> creates .venv/
Build:  npm run build --> compiles TypeScript to dist/
Runtime: node dist/index.js --> runs MCP server --> calls .venv/bin/python internally
```

#### Claude Code

Create or edit `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/absolute/path/to/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "your-email@example.com",
        "ZLIBRARY_PASSWORD": "your-password"
      }
    }
  }
}
```

#### RooCode / Cline

Edit `mcp_settings.json`:

```json
{
  "mcpServers": {
    "zlibrary-local": {
      "command": "node",
      "args": ["/full/path/to/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "your-email@example.com",
        "ZLIBRARY_PASSWORD": "your-password"
      },
      "transport": "stdio",
      "enabled": true
    }
  }
}
```

## Available MCP Tools (12 Total)

### Search Tools (6)

| Tool | Description |
|------|-------------|
| `search_books` | Basic search by keyword with filters |
| `full_text_search` | Search within book contents (routes through EAPI search) |
| `search_by_term` | Conceptual navigation via terms |
| `search_by_author` | Advanced author search |
| `search_advanced` | Fuzzy match detection with separate exact/fuzzy results |
| `get_recent_books` | Recently added books |

### Metadata Tools (1)

| Tool | Description |
|------|-------------|
| `get_book_metadata` | Complete metadata extraction (terms, descriptions, ratings) |

### Collection Tools (1)

| Tool | Description |
|------|-------------|
| `fetch_booklist` | Expert-curated collection contents (graceful degradation via EAPI) |

### Download & Processing Tools (2)

| Tool | Description |
|------|-------------|
| `download_book_to_file` | Download with optional RAG processing |
| `process_document_for_rag` | Extract text from EPUB/PDF/TXT |

### Utility Tools (2)

| Tool | Description |
|------|-------------|
| `get_download_limits` | Check daily download quota |
| `get_download_history` | View recent downloads |

## Development

### Running Tests

```bash
# Run all tests (Jest for Node.js + Pytest for Python)
npm test

# Python tests only
uv run pytest

# Specific Python test
uv run pytest __tests__/python/test_rag_processing.py
```

### Building

```bash
npm run build
```

## FAQ

### Why EAPI instead of HTML scraping?

Z-Library deployed Cloudflare browser challenges (Jan 2026) that block all HTML page requests from automated clients. The EAPI JSON endpoints at `/eapi/` are not subject to these challenges, providing reliable programmatic access. See `docs/adr/ADR-005-EAPI-Migration.md`.

### Why use `node` in .mcp.json instead of `uv`?

The MCP server is a Node.js application. UV is only used during setup (`uv sync`) to create `.venv/` and install Python dependencies. At runtime, Node.js runs the MCP server which calls `.venv/bin/python` internally.

### What if I move the project directory?

No problem. `.venv/` moves with the project (UV creates project-local environments).

## Contributing

Contributions are welcome. Please review the architecture documents (`docs/`) and ADRs (`docs/adr/`) before submitting a Pull Request. See `.claude/VERSION_CONTROL.md` for Git workflow and commit conventions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is provided for educational and research purposes only. Users are responsible for complying with all applicable laws and regulations regarding the downloading and use of copyrighted materials. Accessing Z-Library may be restricted in certain jurisdictions.
