# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-03-XX

### Added

- Startup credential validation with actionable error messages for missing `ZLIBRARY_EMAIL` or `ZLIBRARY_PASSWORD`
- Jest and pytest coverage thresholds to prevent test coverage regressions
- ESLint with TypeScript-aware rules for static analysis
- Prettier for consistent code formatting across the codebase
- lint-staged pre-commit hooks (ESLint, Prettier, TypeScript type-check)
- `.git-blame-ignore-revs` to exclude bulk formatting commits from blame
- CI pipeline split into fast (push/PR) and full (push-to-master) workflows
- API reference documentation for all 13 MCP tools

### Changed

- Python environment management migrated from pip/venv to UV (77% code reduction in venv-manager)
- Test infrastructure modernized: strict pytest markers, benchmark integration

### Fixed

- Jest test compatibility with Node 22 (JSON.parse error message format change)
- Pytest collection errors from scripts in test discovery path
- Removed deprecated AsyncZlib references and rewrote tests with EAPIClient
- Cleaned compiled `.js` artifacts from source tree
- Purged large blobs (74MB+) from git history via filter-repo

### Removed

- Legacy pip/venv-based Python environment management
- Deprecated AsyncZlib download client code

## [1.1.0] - 2026-02-04

### Added

- Margin content detection for scholarly PDFs (Stephanus numbering, Bekker numbering, line numbers, marginal glosses)
- Adaptive resolution pipeline with page-level DPI selection (150-400 based on content analysis)
- Region-level DPI targeting for mixed-quality PDF pages
- Unified body text detection pipeline with confidence scoring
- Non-body content separation (headers, footers, footnotes isolated from body text)
- Anna's Archive integration as alternative book source with automatic LibGen fallback
- `search_multi_source` tool for cross-source searching (Anna's Archive and LibGen)
- Source attribution in multi-source search results

### Changed

- EAPI booklist browsing improved with pagination support
- EAPI full-text search enhanced with phrase and word matching modes
- Docker configuration updated for Alpine compatibility (opencv-python-headless)

### Fixed

- Node 22 LTS compatibility issues
- Docker numpy/Alpine compilation errors
- env-paths updated to v4.0 for proper Node 22 support

### Removed

- AsyncZlib legacy download client (fully replaced by EAPI)

## [1.0.0] - 2026-02-01

### Added

- 13 MCP tools: `search_books`, `full_text_search`, `search_by_term`, `search_by_author`, `search_advanced`, `search_multi_source`, `get_recent_books`, `get_book_metadata`, `fetch_booklist`, `download_book_to_file`, `process_document_for_rag`, `get_download_limits`, `get_download_history`
- EAPI migration for all Z-Library operations (replacing web scraping)
- MCP SDK upgrade to 1.25.3 with `McpServer` API
- Python bridge decomposition (4968-line monolith split into 31 focused modules)
- RAG processing pipeline for EPUB, PDF, and TXT documents
- Enhanced metadata extraction with terms, booklists, IPFS CIDs, and ratings
- Book download with automatic filename generation from metadata
- Cloudflare detection and domain discovery for EAPI endpoints
- Integration test harness with 11 tool coverage
- CI pipeline with npm audit and Python version checks
- Pre-commit hooks via Husky
- Zod schema validation for all tool parameters

### Changed

- Migrated from web scraping to Z-Library EAPI for all operations
- Upgraded to MCP SDK 1.25.x with new `McpServer` registration API
- Python monolith `rag_processing.py` decomposed into `lib/rag/` module tree with facade re-exports
- Bare `except` clauses replaced with specific exception handling throughout Python codebase

### Fixed

- 15 npm security vulnerabilities resolved
- BeautifulSoup4 parser specification (explicit `lxml` to avoid warnings)
- BUG-X/FIX comments cleaned from production code
- Debug print statements converted to proper logging

[Unreleased]: https://github.com/loganrooks/zlibrary-mcp/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/loganrooks/zlibrary-mcp/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/loganrooks/zlibrary-mcp/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/loganrooks/zlibrary-mcp/releases/tag/v1.0.0
