"""
lib.rag - Decomposed RAG processing package.

This package contains modules extracted from the monolithic rag_processing.py.
All functions maintain their original signatures and behavior.

Subpackages:
    utils/       - Constants, exceptions, text helpers, caching, header generation
    detection/   - Footnotes, headings, TOC, page numbers, front matter
    quality/     - PDF quality analysis and multi-stage quality pipeline
    ocr/         - OCR spacing, corruption detection, quality assessment, recovery
    xmark/       - X-mark (sous-rature) detection
    processors/  - Format-specific processors (PDF, EPUB, TXT)
    orchestrator - Main entry points (process_pdf, process_document, save_processed_text)
"""
