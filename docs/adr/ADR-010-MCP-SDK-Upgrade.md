# ADR-010: MCP SDK Upgrade to 1.25+

**Date:** 2026-01-30

**Status:** Accepted

## Context

The project was using `@modelcontextprotocol/sdk` version 1.8.0, which had a known high-severity security vulnerability and used the older `Server` class API with manual tool registration via `setRequestHandler`. The MCP SDK had evolved significantly, introducing the `McpServer` class with a simpler `server.tool()` registration API.

## Decision

Upgrade from MCP SDK 1.8.0 to 1.25+ and migrate to the McpServer API:

1. **Replace `Server` with `McpServer`** from `@modelcontextprotocol/sdk/server/mcp.js`
2. **Replace `setRequestHandler` with `server.tool()`** for each of the 12 tools
3. **Use `Schema.shape` (ZodRawShape)** for tool parameter schemas (not `z.object()`)
4. **Remove `zod-to-json-schema`** dependency -- McpServer handles schema conversion internally
5. **Preserve legacy `toolRegistry` export** for test backward compatibility (cleaned up in follow-up)

## Consequences

### Positive
- **Security vulnerability resolved**: High-severity CVE in SDK 1.8 eliminated
- **Simplified tool registration**: `server.tool()` is more concise than manual request handlers
- **Removed dependency**: `zod-to-json-schema` no longer needed
- **12 tools registered**: All tools (search_books, full_text_search, get_download_history, get_download_limits, get_recent_books, download_book_to_file, process_document_for_rag, get_book_metadata, search_by_term, search_by_author, search_advanced, fetch_booklist)

### Negative
- **Test pattern change**: Tests now mock `server.tool()` calls instead of request handlers
- **Schema shape requirement**: Must pass `Schema.shape` not `z.object()` to `server.tool()`

### Neutral
- **No functional changes**: Same 12 tools with same behavior, just different registration API
