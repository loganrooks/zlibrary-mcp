# DevOps Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
## Deployment History Log
<!-- Append deployment details using the format below -->
### Deployment: [2025-05-02 03:19:43] - RAG Processing (OCR Refactor) to feature/rag-robustness-enhancement
- **Triggered By**: User Request (Task 2025-05-02 03:16:40)
- **Status**: Success (Commit Only)
- **Duration**: N/A
- **Commit/Build ID**: `13c826b`
- **Changes**: Refactored `run_ocr_on_pdf` in `lib/rag_processing.py` to use PyMuPDF (`fitz`) instead of `pdf2image`. Updated corresponding tests in `__tests__/python/test_rag_processing.py`. (TDD Cycle 21). **Note:** This commit also inadvertently included changes for TDD Cycle 22 (PDF Quality Detection).
- **Issues Encountered**: Initial patch file application failed due to corruption/mismatch. Used `git reset` and `git add` instead.
- **Rollback Plan**: `git revert 13c826b`