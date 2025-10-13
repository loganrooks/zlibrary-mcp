# Z-Library MCP Server

This Model Context Protocol (MCP) server provides access to Z-Library for AI coding assistants like RooCode and Cline for VSCode. It allows AI assistants to search for books, retrieve metadata, download files, and process document content for Retrieval-Augmented Generation (RAG) workflows.

## Current Status (As of 2025-05-05 03:45 UTC-4)

- **Stability:** Stable. Both Node.js (`npm test`) and Python (`pytest`) test suites are passing.
- **Recent Updates:**
    - **RAG Robustness Enhancements Implemented:** Added PDF quality detection, conditional OCR (via Tesseract), EPUB front matter/ToC handling, and garbled text detection to improve processing reliability (See `docs/rag-robustness-enhancement-spec.md`). [Ref: ActiveContext 2025-05-05 03:45:36]
    - Refactored RAG processing logic into `lib/rag_processing.py`.
    - Fixed various test suite issues and regressions across multiple TDD cycles.
    - Deprecated `get_book_by_id` (ADR-003) and `get_download_info` tools.
    - RAG download workflow follows ADR-002.
- **Branch:** `main` (Assumed, pending confirmation of merge)

## Architecture Overview

This project is primarily built using **Node.js/TypeScript** and acts as an MCP server. Key architectural features include:

- **Python Bridge:** Utilizes a Python bridge (`lib/python_bridge.py` for interfacing, `lib/rag_processing.py` for core document processing, `src/lib/python-bridge.ts` for Node interface) to leverage Python libraries for specific tasks, notably interacting with the Z-Library website and processing document formats (EPUB, TXT, PDF).
- **Managed Python Environment:** The server manages its own Python virtual environment (`.venv`) to ensure consistent dependency handling (see `setup_venv.sh`).
- **Vendored `zlibrary` Fork:** Includes a modified fork of the `sertraline/zlibrary` Python library within the `zlibrary/` directory. This fork contains specific modifications, particularly for the book download logic which involves scraping the book's detail page to find the actual download link (see ADR-002).
- **RAG Pipeline:** Implements workflows for downloading books and processing their content (EPUB, TXT, PDF) into plain text or Markdown suitable for RAG. Includes robustness features like PDF quality detection, conditional OCR, front matter removal, and ToC extraction. Processed text is saved to `./processed_rag_output/` and the file path is returned to the agent to avoid context overload (see `docs/architecture/rag-pipeline.md`).

## Features

### Core Search Capabilities
- 📚 **Basic Search** - Search by title, author, year, language, and format
- 🔍 **Full-Text Search** - Search within book contents
- 🏷️ **Term-Based Search** - Navigate by conceptual terms (60+ per book)
- 👤 **Advanced Author Search** - Support for various name formats and exact matching
- 🔎 **Advanced Search** - Fuzzy match detection and separation
- 📚 **Booklist Exploration** - Access expert-curated collections (up to 954 books/list)

### Metadata Extraction
- 📊 **Complete Metadata** - Extract 60+ conceptual terms per book
- 📚 **Booklist Discovery** - Find 11+ curated collections per book
- 📝 **Rich Descriptions** - 800+ character descriptions
- 🔗 **IPFS Support** - Decentralized access via 2 CID formats
- ⭐ **Quality Metrics** - Ratings, quality scores, bibliographic data

### Download & Processing
- 💾 **Smart Downloads** - Download PDF/EPUB with intelligent filename generation
- ✨ **RAG Processing** - Extract clean text from EPUB/PDF for AI applications
- 📊 **Quality Detection** - Automatic OCR for image-based PDFs
- 🧹 **Text Preprocessing** - Front matter removal, ToC extraction, formatting

### Research Workflows
Enables 8 comprehensive research workflows:
1. Literature Review - Automated corpus building
2. Citation Network Mapping - Intellectual genealogy
3. Conceptual Navigation - Knowledge graph traversal
4. Topic Discovery - Fuzzy matching and variations
5. Collection Exploration - Expert-curated lists
6. RAG Knowledge Base - Vector database preparation
7. Comparative Analysis - Cross-author studies
8. Temporal Analysis - Idea evolution tracking

## Prerequisites

- Node.js 18 or newer
- Python 3.9 or newer
- [UV](https://docs.astral.sh/uv/) - Modern Python package manager (v2.0.0+)
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

See [UV installation guide](https://docs.astral.sh/uv/getting-started/installation/) for more options.

### 2. Setup Project

```bash
# Clone this repository
git clone https://github.com/loganrooks/zlibrary-mcp.git
cd zlibrary-mcp

# Setup Python environment with UV (fast!)
bash setup-uv.sh
# Or manually: uv sync

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build
```

**That's it!** UV handles all Python dependency management automatically.

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

## Available MCP Tools (11 Total)

### Search Tools (6)

1. **`search_books`** - Basic search by keyword with filters
   - Parameters: query, exact, fromYear, toYear, languages, extensions, count
   - Returns: List of books with complete metadata (title, authors, year, etc.)

2. **`full_text_search`** - Search within book contents
   - Parameters: query, phrase, words, languages, extensions, count
   - Returns: Books containing the searched text

3. **`search_by_term`** ✨ NEW - Conceptual navigation via 60+ terms per book
   - Parameters: term (e.g., "dialectic"), yearFrom, yearTo, languages, count
   - Returns: Books tagged with the conceptual term

4. **`search_by_author`** ✨ NEW - Advanced author search
   - Parameters: author (supports "Lastname, Firstname"), exact, yearFrom, count
   - Returns: Author's works with metadata

5. **`search_advanced`** ✨ NEW - Fuzzy match detection
   - Parameters: query, exact, yearFrom, yearTo, count
   - Returns: Separate exact_matches and fuzzy_matches arrays

6. ~~`get_book_by_id`~~ - **DEPRECATED** (use search_books instead)

### Metadata Tools (1)

7. **`get_book_metadata`** ✨ NEW - Complete metadata extraction
   - Parameters: bookId, bookHash
   - Returns: 60+ terms, 11+ booklists, descriptions, IPFS CIDs, ratings, series, ISBNs
   - **Core Feature**: Enables conceptual navigation and collection discovery

### Collection Tools (1)

8. **`fetch_booklist`** ✨ NEW - Expert-curated collection contents
   - Parameters: booklistId, booklistHash, topic, page
   - Returns: Books from collections (e.g., Philosophy: 954 books)

### Download & Processing Tools (2)

9. **`download_book_to_file`** - Download with optional RAG processing
   - Parameters: bookDetails, outputDir, process_for_rag, processed_output_format
   - Returns: file_path and optional processed_file_path

10. **`process_document_for_rag`** - Extract text from EPUB/PDF/TXT
    - Parameters: file_path, output_format
    - Returns: Processed text file path (125KB+ clean text)

### Utility Tools (2)

11. **`get_download_limits`** - Check daily download quota
12. **`get_download_history`** - View recent downloads

**Total**: 11 MCP tools providing complete research acceleration capabilities

### Key Capabilities

**60 Terms Per Book**: Navigate by philosophical/technical concepts
**11 Booklists Per Book**: Explore expert-curated collections
**8 Research Workflows**: Literature review, citation networks, conceptual navigation, etc.
**15-360x Faster**: Compared to manual research

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
