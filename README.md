# Z-Library MCP Server

This Model Context Protocol (MCP) server provides access to Z-Library for AI coding assistants like RooCode and Cline for VSCode. It allows AI assistants to search for books, retrieve metadata, download files, and process document content for Retrieval-Augmented Generation (RAG) workflows.

## Current Status (As of 2025-04-28 22:00 UTC-4)

- **Stability:** Stable. Both Node.js (`npm test`) and Python (`pytest`) test suites are passing.
- **Recent Updates:**
    - Fixed `get_download_history` parser (Commit `9350af5`).
    - Implemented `get_recent_books` tool (Commit `75b6f11`).
    - Implemented `venv-manager` tests (Commit assumed `3e732b3` or prior).
    - Resolved test suite issues (Commit `3e732b3`).
    - Deprecated and removed `get_download_info` tool (Commit `8bef4c2`).
    - RAG download workflow follows ADR-002 (Commit `f466479` or later).
    - Deprecated `get_book_by_id` tool (Commit `454c92e`, see ADR-003).
    - Refactored RAG processing logic from `python_bridge.py` to `rag_processing.py` (Commit `cf8ee5c`).
- **Branch:** `feature/rag-eval-cleanup` (Current development branch)

## Architecture Overview

This project is primarily built using **Node.js/TypeScript** and acts as an MCP server. Key architectural features include:

- **Python Bridge:** Utilizes a Python bridge (`lib/python_bridge.py` for core logic, `lib/rag_processing.py` for document processing, `src/lib/python-bridge.ts` for Node interface) to leverage Python libraries for specific tasks, notably interacting with the Z-Library website and processing document formats (EPUB, TXT, PDF).
- **Managed Python Environment:** The server manages its own Python virtual environment (`.venv`) to ensure consistent dependency handling (see `setup_venv.sh`).
- **Vendored `zlibrary` Fork:** Includes a modified fork of the `sertraline/zlibrary` Python library within the `zlibrary/` directory. This fork contains specific modifications, particularly for the book download logic which involves scraping the book's detail page to find the actual download link (see ADR-002).
- **RAG Pipeline:** Implements workflows for downloading books and processing their content (EPUB, TXT, PDF) into plain text suitable for RAG. Processed text is saved to `./processed_rag_output/` and the file path is returned to the agent to avoid context overload (see `docs/architecture/rag-pipeline.md`).

## Features

- 📚 Search for books by title, author, year, language, and format
- 📖 Get detailed book information and metadata (Note: ID-based lookup is currently unreliable due to external website changes; search is recommended)
- 🔍 Full-text search within book contents
- 📊 View download history (Parser fixed) and limits
- 📈 Get recently added books
- 💾 Download books directly to local file system (`./downloads/` by default) using `bookDetails` from search results (see ADR-002).
- ✨ Process downloaded documents (EPUB, TXT, PDF) into plain text for RAG, saving output to `./processed_rag_output/`

## Prerequisites

- Node.js 18 or newer (Updated based on recent dependencies/ESM)
- Python 3.9 or newer (Updated based on recent dependencies)
- Z-Library account (for authentication)

## Installation

```bash
# Clone this repository
git clone https://github.com/loganrooks/zlibrary-mcp.git
cd zlibrary-mcp

# Install Node.js dependencies
npm install

# Build TypeScript code
npm run build

# Run the setup script to create Python virtual environment and install Python dependencies
./setup_venv.sh
```

## Configuration

The server requires Z-Library credentials to function. Set these as environment variables:

```bash
export ZLIBRARY_EMAIL="your-email@example.com"
export ZLIBRARY_PASSWORD="your-password"
# Optional: Specify the Z-Library mirror domain if needed
# export ZLIBRARY_MIRROR="https://your-mirror.example"
```

## Usage

### Starting the Server

From the local repository root:

```bash
# Ensure you have built the code first (npm run build)
node dist/index.js
```

The server will start, connect via Stdio, and register its tools.

### Integration with RooCode / Cline

Configure the server in your AI assistant's settings. Ensure the `command` points to the correct execution path (e.g., `node /path/to/zlibrary-mcp/dist/index.js`) and provide the necessary environment variables (`ZLIBRARY_EMAIL`, `ZLIBRARY_PASSWORD`).

**Example RooCode `mcp_settings.json`:**

```json
{
  "mcpServers": {
    "zlibrary-local": { // Renamed for clarity
      "command": "node",
      "args": [
        "/full/path/to/zlibrary-mcp/dist/index.js" // Use absolute path
      ],
      "env": {
        "ZLIBRARY_EMAIL": "your-email@example.com",
        "ZLIBRARY_PASSWORD": "your-password"
        // Add ZLIBRARY_MIRROR if needed
      },
      "transport": "stdio", // Explicitly stdio
      "enabled": true
      // "alwaysAllow": [...] // Optional: Add tools to bypass confirmation
    }
  }
}
```

*(Note: Global installation (`npm install -g`) is not currently the primary recommended setup due to the complexities of managing the Python environment globally. Local development setup is preferred.)*

## Available Tools

- `search_books`: Search for books. **Recommended** for finding books and obtaining `bookDetails`.
- `get_book_by_id`: **DEPRECATED**. (Unreliable due to external site changes, use `search_books`).
- `full_text_search`: Search within book content.
- `get_download_history`: View download history (Parser fixed).
- `get_download_limits`: Check download limits.
- `get_recent_books`: Get recently added books (Implemented).
- `download_book_to_file`: Download a book using `bookDetails` from search results. Can optionally process for RAG.
- `process_document_for_rag`: Process an existing local file (EPUB, TXT, PDF) for RAG.

## Development

### Running Tests

```bash
# Run all tests (Jest for Node.js, Pytest for Python bridge)
# Both suites are currently passing.
npm test
```

### Contributing

Contributions are welcome! Please review the architecture documents (`docs/`) and ADRs (`docs/adr/`) before submitting a Pull Request. Ensure changes align with the project's direction and include relevant tests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is provided for educational and research purposes only. Users are responsible for complying with all applicable laws and regulations regarding the downloading and use of copyrighted materials. Accessing Z-Library may be restricted in certain jurisdictions.
