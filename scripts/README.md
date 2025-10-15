# Scripts Directory

Organized collection of utility and validation scripts for the Z-Library MCP project.

## Directory Structure

```
scripts/
├── validation/     # Production validation and test generation
├── debugging/      # Debugging utilities
├── extraction/     # Page extraction utilities
└── archive/        # Historical development scripts (reference only)
```

---

## Production Scripts

### validation/

**Purpose**: Active scripts used for validation and testing in production workflows

- **`xmark_detector.py`** - Main X-mark (sous rature) detection script
  - Detects strikethrough text in philosophical texts
  - Uses PyMuPDF for PDF analysis
  - Production-ready validation tool

- **`create_test_pdfs.py`** - Generate test PDFs with various formatting
  - Creates PDFs with strikethrough, italics, bold
  - Used for regression testing
  - Configurable test case generation

- **`test_formatting_extraction.py`** - Validate formatting extraction
  - Tests formatting detection accuracy
  - Compares against ground truth
  - Quality assurance for RAG pipeline

### debugging/

**Purpose**: Utilities for troubleshooting extraction and formatting issues

- **`debug_extraction_matching.py`** - Debug extraction match logic
- **`debug_pdf_formatting.py`** - Debug PDF formatting detection

### extraction/

**Purpose**: Page extraction and manipulation utilities

- **`extract_specific_pages.py`** - Extract specific pages from PDFs
  - Used for creating test fixtures
  - Supports page range extraction

---

## Archive Scripts

### archive/

**Purpose**: Historical development and research scripts (kept for reference)

These scripts were used during the development and research phase. They are preserved for:
- Historical reference
- Understanding evolution of solutions
- Potential future insights

**Do not use in production** - Use scripts in `validation/` instead.

**Contents**:
- `test_strikethrough_detection.py` - Early strikethrough experiments
- `test_specific_pages_analysis.py` - Page-level analysis prototype
- `search_sous_rature.py` - Initial sous rature search
- `dump_derrida_pages.py` - Page extraction utility
- `analyze_extracted_pages.py` - Page analysis tool
- `test_xmark_detection_engineering.py` - Engineering development version
- `test_line_classification.py` - Line classification experiments
- `test_pymupdf_strikethrough.py` - PyMuPDF strikethrough tests
- `visualize_line_detection.py` - Line detection visualization
- `visualize_test_results.py` - Test result visualization
- `test_tesseract_comparison.py` - Tesseract OCR comparison tests

---

## Other Scripts (Root Level)

Scripts in the root `scripts/` directory are legacy utilities that may still be in use:

- `create_mock_pdf.py` - Mock PDF generation
- `run_rag_tests.py` - RAG test runner
- `test_marginalia_detection.py` - Marginalia detection tests
- `validate-python-bridge.js` - Python bridge validation
- `fix-cache-venv.sh` - Venv cache fix utility
- `get_venv_python_path.mjs` - Get venv Python path

---

## Usage Guidelines

### For Production Work
1. Use scripts in `validation/` directory
2. Run `xmark_detector.py` for X-mark detection
3. Use `create_test_pdfs.py` for test case generation
4. Validate with `test_formatting_extraction.py`

### For Debugging
1. Check `debugging/` directory for relevant utilities
2. Use debug scripts to troubleshoot specific issues
3. Add new debug utilities to `debugging/` directory

### For Reference
1. Check `archive/` for historical context
2. Do not modify archived scripts
3. Extract useful patterns for new implementations

---

## Next Steps

1. **Clean Up Root**: Consider moving remaining root-level scripts to appropriate subdirectories
2. **Documentation**: Update any references to old script paths in documentation
3. **Testing**: Verify all moved scripts still work from new locations
4. **Deprecation**: Mark archived scripts with deprecation notices if needed

---

## Related Documentation

- `/WORKSPACE_ORGANIZATION.md` - Complete organization report
- `/claudedocs/strikethrough-research/` - Research documentation
- `/test_files/` - Test fixtures and PDFs

---

**Last Updated**: 2025-10-15
