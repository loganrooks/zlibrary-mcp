# DevOps Specific Memory
<!-- Entries below should be added reverse chronologically (newest first) -->
## Deployment History Log
### Deployment: [2025-05-02 05:15:30] - RAG Test Framework &amp; MB Updates to feature/rag-robustness-enhancement
- **Triggered By**: User Request (Task 2025-05-02 05:14:35)
- **Status**: Success (Commit Only)
- **Duration**: N/A
- **Commit/Build ID**: `5d156d3`
- **Changes**: Staged and committed remaining changes from RAG testing framework development and Memory Bank updates, including: `__tests__/python/test_run_rag_tests.py`, `memory-bank/feedback/devops-feedback.md`, `memory-bank/feedback/tdd-feedback.md`, `memory-bank/globalContext.md`, `memory-bank/mode-specific/debug.md`, `memory-bank/mode-specific/tdd.md`, `__tests__/python/conftest.py`, `scripts/__init__.py`, `scripts/run_rag_tests.py`, `scripts/sample_manifest.json`.
- **Issues Encountered**: None (Previous Git staging issues did not recur).
- **Rollback Plan**: `git revert 5d156d3`
<!-- Append deployment details using the format below -->
### Deployment: [2025-05-02 03:19:43] - RAG Processing (OCR Refactor) to feature/rag-robustness-enhancement
- **Triggered By**: User Request (Task 2025-05-02 03:16:40)
- **Status**: Success (Commit Only)
- **Duration**: N/A
- **Commit/Build ID**: `13c826b`
- **Changes**: Refactored `run_ocr_on_pdf` in `lib/rag_processing.py` to use PyMuPDF (`fitz`) instead of `pdf2image`. Updated corresponding tests in `__tests__/python/test_rag_processing.py`. (TDD Cycle 21). **Note:** This commit also inadvertently included changes for TDD Cycle 22 (PDF Quality Detection).
- **Issues Encountered**: Initial patch file application failed due to corruption/mismatch. Used `git reset` and `git add` instead.
- **Rollback Plan**: `git revert 13c826b`