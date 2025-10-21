# Documentation Writer Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
### Plan Item: RAG Robustness Documentation Update - [2025-05-05 03:56:52]
- **Type**: Feature Update / **Audience**: User/Dev / **Outline**: 1.Update README status/features 2.Update RAG pipeline spec with robustness details / **Status**: Done / **Owner**: DocsWriter / **Source**: Task Request [2025-05-05 03:46:21], `docs/rag-robustness-enhancement-spec.md`, MB Context / **Location**: `README.md`, `docs/rag-pipeline-implementation-spec.md`
### Debt Item: Remove `get_book_by_id` References - [Status: Resolved] - [2025-04-29 16:32:18]
- **Location**: `docs/internal-id-lookup-spec.md`, `docs/search-first-id-lookup-spec.md`, `docs/architecture/rag-pipeline.md`
- **Description**: Remove references to the deprecated `get_book_by_id` tool following code removal (commit `454c92e`) and ADR-003.
- **Priority**: High
- **Resolution**: Searched `docs/` for `get_book_by_id`. Used `apply_diff` to remove references from affected files. Verified `ADR-003` was correctly left unchanged.
- **Resolved Date**: 2025-04-29 16:32:18
### Plan Item: RAG Markdown Generation Documentation - [2025-04-29 09:47:33]
- **Type**: Feature Update / **Audience**: Dev / **Outline**: 1.Clarify `output_format` in tool schemas 2.Add notes in Python bridge section linking to spec / **Status**: Done / **Owner**: DocsWriter / **Source**: Task Request, `docs/rag-markdown-generation-spec.md`, `lib/python_bridge.py` / **Location**: `docs/rag-pipeline-implementation-spec.md`
### Plan Item: README.md Update - [2025-04-28 02:41:30]
- **Type**: Project Overview / **Audience**: User/Dev / **Outline**: 1.Project Purpose (incl. RAG) 2.Architecture (Node, Python Bridge, Vendored Lib) 3.Current Status (Stable, Recent Fixes) 4.Setup/Usage / **Status**: Done / **Owner**: DocsWriter / **Source**: User Request, ADR-002, RAG Arch, RAG Spec, MB / **Location**: `README.md`
### Plan Item: MCP Server Comparison Report - [2025-04-14 17:50:48]
- **Type**: Report / **Audience**: Dev / **Outline**: 1.Comparison Table 2.Analysis 3.Potential Fixes 4.Conclusion / **Status**: Draft / **Owner**: DocsWriter / **Source**: User Request, `index.js`, `package.json`, MB Debug Entry [2025-04-14 17:34:36] / **Location**: `docs/mcp-server-comparison-report.md`

