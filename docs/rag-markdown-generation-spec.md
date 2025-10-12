# RAG Markdown Generation Specification

**Version:** 1.0
**Date:** 2025-04-29
**Author:** Specification Writer (AI Mode)
**Status:** Draft

## 1. Introduction

This document outlines the implementation strategy for adding robust Markdown structure generation to the RAG processing pipeline within the `zlibrary-mcp` project. This addresses the shortcomings identified in QA report `docs/rag-output-qa-report-rerun-20250429.md`, where Markdown output for PDF and EPUB files lacked structural elements (headings, lists, footnotes) required by `docs/rag-output-quality-spec.md`.

## 2. Goal

Enhance the `_process_pdf` and `_process_epub` functions in `lib/python_bridge.py` to generate well-structured Markdown output when `output_format='markdown'` is specified, adhering to the quality criteria in `docs/rag-output-quality-spec.md`.

## 3. Chosen Strategy

Instead of introducing new major dependencies like `pypandoc` or `markdownify`, the strategy focuses on refining the existing processing logic within `lib/python_bridge.py` using the currently employed libraries:

*   **PDF Processing:** Enhance the heuristic-based approach using `PyMuPDF (fitz)`. Leverage the detailed block/span information from `page.get_text("dict")` (font size, flags, position) to implement more robust detection and formatting of headings, lists, and footnotes.
*   **EPUB Processing:** Enhance the `BeautifulSoup` parsing logic used with `ebooklib`. Implement a more structured traversal of the HTML DOM, explicitly mapping relevant tags (`h1-h6`, `ul`, `ol`, `li`, `p`, `blockquote`, `pre`, `aside[epub:type=footnote]`, `a[epub:type=noteref]`) to their Markdown equivalents, including handling for nesting and EPUB-specific footnote semantics.

## 4. Implementation Details

### 4.1. `lib/python_bridge.py` Modifications

*   **`_process_pdf(file_path_str, output_format='text')`:**
    *   Accept `output_format` parameter.
    *   If `output_format == 'markdown'`:
        *   Call a new helper function `_format_pdf_markdown(page)` for each page.
        *   `_format_pdf_markdown` will:
            *   Use `page.get_text("dict")` to get blocks and spans.
            *   Call `_analyze_pdf_block(block)` (new helper) to determine heading level, list status, etc., based on heuristics (font size, flags, text patterns).
            *   Detect footnote references/definitions using superscript flags and position.
            *   Construct Markdown lines based on analysis (e.g., `# Heading`, `* Item`, `1. Item`, `[^1]`, `[^1]: Definition`).
    *   If `output_format == 'text'`: Use existing text extraction and cleaning logic.
    *   Return the combined, cleaned content (Markdown or text).
*   **`_process_epub(file_path_str, output_format='text')`:**
    *   Accept `output_format` parameter.
    *   If `output_format == 'markdown'`:
        *   Use `BeautifulSoup` to parse HTML content from `ebooklib`.
        *   Implement/call a recursive helper `_epub_node_to_markdown(node, footnote_defs)`:
            *   Takes a BeautifulSoup node and a dictionary to store footnote definitions.
            *   Maps HTML tags (`h1-h6`, `p`, `ul`, `ol`, `li`, `blockquote`, `pre`, etc.) to Markdown.
            *   Handles list nesting (requires careful implementation).
            *   Identifies footnote references (`a[epub:type=noteref]`) and formats them (`[^1]`).
            *   Identifies footnote definitions (`aside[epub:type=footnote]`), stores them in `footnote_defs`, and returns empty string for the definition node itself.
        *   Append collected footnote definitions at the end of the document content.
    *   If `output_format == 'text'`: Use existing `soup.get_text()` logic.
    *   Return the combined, cleaned content (Markdown or text).
*   **`process_document(file_path_str, output_format='txt')`:**
    *   Accept `output_format` parameter (defaulting to 'txt').
    *   Pass the `output_format` to `_process_pdf` and `_process_epub`.
*   **`main()`:**
    *   Modify the handler for the `process_document` action to accept an optional `output_format` argument from the JSON input (defaulting to 'text') and pass it to the `process_document` function.

### 4.2. Dependencies

*   No new major Python dependencies required. Relies on existing `PyMuPDF`, `ebooklib`, `beautifulsoup4`, `lxml`.

## 5. Pseudocode

*(Refer to Memory Bank entry `memory-bank/mode-specific/spec-pseudocode.md` [2025-04-29 02:40:07] for detailed pseudocode of `_analyze_pdf_block`, `_format_pdf_markdown`, `_process_pdf` (refactored), `_epub_node_to_markdown`, `_process_epub` (refactored), and `main` update)*

## 6. TDD Anchors

*(Refer to Memory Bank entry `memory-bank/mode-specific/spec-pseudocode.md` [2025-04-29 02:40:07] for detailed TDD anchors for both PDF and EPUB processing)*

## 7. Open Questions / Risks

*   **PDF Heuristic Tuning:** The effectiveness of PDF Markdown generation heavily depends on the quality of the heuristics used to interpret font sizes, flags, and positions. These may need tuning based on testing with diverse PDFs.
*   **EPUB Nesting:** Correctly handling deeply nested lists or complex structures in EPUB HTML requires careful recursive logic in `_epub_node_to_markdown`.
*   **Table Handling:** This initial specification focuses on core structure. Table conversion to Markdown is complex and deferred, likely requiring separate heuristics or libraries. Current pseudocode doesn't explicitly handle tables.
*   **Performance:** Complex parsing logic might impact performance, especially for large documents.