# Formatting Extraction Testing Framework

**Created:** 2025-10-15
**Status:** Complete
**Purpose:** Validate RAG pipeline's ability to detect and preserve text formatting

---

## Overview

This testing framework creates **synthetic PDFs with known ground truth** for all formatting types, then validates our extraction pipeline against them. This provides objective metrics for what works and what doesn't.

---

## Quick Start

### Run Full Validation
```bash
# Create test PDFs (already done, but can regenerate)
python create_test_pdfs.py

# Run extraction tests
python test_formatting_extraction.py

# View visual summary
python visualize_test_results.py

# Read detailed report
cat test_files/FORMATTING_VALIDATION_REPORT.md
```

### Current Results Summary
```
Overall Performance:  37.5% F1 score
Perfect matches:      8/27 items (29.6%)

✅ WORKS (≥80% recall):
   - Bold (83%)
   - Italic (83%)
   - Monospaced (100%)
   - Superscript (100%)
   - Subscript (100%)

❌ DOESN'T WORK (<80% recall):
   - Strikethrough (10%) - CRITICAL GAP
   - Sous-erasure/X-marks (17%) - CRITICAL GAP
   - Underline (17%)
```

---

## Test Files

### Test PDFs (Synthetic with Ground Truth)

1. **test_digital_formatting.pdf** (2.2 KB)
   - Purpose: Born-digital formatting (font-based)
   - Contents: Bold, italic, underline, strikethrough, super/subscript, monospace
   - Result: Font formats detected ✅, line formats missed ❌

2. **test_xmarks_and_strikethrough.pdf** (1.9 KB)
   - Purpose: Visual line-based formatting (graphics)
   - Contents: 3× X-marks (sous-erasure), 2× strikethrough, 1× underline
   - Result: ALL line-based formatting missed ❌

3. **test_mixed_formatting.pdf** (2.1 KB)
   - Purpose: Complex combinations
   - Contents: Bold+strikethrough, italic+underline, bold+italic+X-marks, mixed paragraph
   - Result: Font formats detected ✅, line formats missed ❌

### Ground Truth & Results

4. **test_formatting_ground_truth.json** (3.5 KB)
   - Complete ground truth for all test PDFs
   - Format: `{pdf_name: {page: [{text, formatting, y_position}]}}`

5. **formatting_extraction_results.json** (9.2 KB)
   - Detailed test results with precision/recall/F1 per item
   - Format summary by format type
   - Overall statistics

6. **FORMATTING_VALIDATION_REPORT.md** (15 KB)
   - Comprehensive analysis of what works and what doesn't
   - Detailed findings for each format type
   - Implementation roadmap (3-week plan)
   - Quick wins and recommendations

---

## Scripts

### Core Scripts

**create_test_pdfs.py**
- Generates all 3 test PDFs using reportlab
- Creates ground truth JSON
- ~200 lines, well-documented

**test_formatting_extraction.py**
- Runs PyMuPDF extraction on test PDFs
- Compares to ground truth
- Calculates precision, recall, F1 per format type
- ~300 lines with metrics logic

**visualize_test_results.py**
- Creates ASCII bar chart of recall by format
- Detailed breakdown by test PDF
- Actionable recommendations
- ~150 lines for visualization

### Debug Scripts

**debug_pdf_formatting.py**
- Inspects raw PyMuPDF formatting data
- Shows font names, flags, sizes
- Useful for understanding what PyMuPDF sees

**debug_extraction_matching.py**
- Compares extracted data to ground truth
- Helps debug matching logic
- Shows Y-coordinate differences

---

## Key Findings

### What Works (Font-Based Formatting)

PyMuPDF detects these **natively** because they're in the PDF text attributes:

| Format | Detection Method | Flag/Pattern | Recall |
|--------|------------------|--------------|--------|
| **Bold** | Font name + flags | `flags & 16` or "bold" in name | 83% |
| **Italic** | Font name + flags | `flags & 2` or "italic"/"oblique" | 83% |
| **Monospace** | Font name + flags | `flags & 8` or "courier"/"mono" | 100% |
| **Superscript** | Flags | `flags & 1` | 100% |
| **Subscript** | Font size + position | `size < 10` and no superscript flag | 100% |

**Why these work:** They're stored as **text attributes** in the PDF structure.

---

### What Doesn't Work (Line-Based Formatting)

PyMuPDF **ignores** these because they're drawn as **graphics** (vector lines), not text attributes:

| Format | Why It Fails | Recall | Priority |
|--------|--------------|--------|----------|
| **Strikethrough** | Horizontal line drawn through text | 10% | HIGH |
| **Sous-erasure** | Diagonal X-marks drawn over text | 17% | CRITICAL |
| **Underline** | Horizontal line drawn below text | 17% | MODERATE |

**Root cause:** Our pipeline only extracts text attributes, not page graphics.

---

## Solution: Computer Vision Pipeline

### Required Implementation

**Phase 1: Line Detection (Week 1)**
```python
import cv2
import numpy as np

# 1. Render PDF page to image
pix = page.get_pixmap(dpi=300)
img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8))

# 2. Detect lines
edges = cv2.Canny(gray, 50, 150)
lines = cv2.HoughLinesP(edges, threshold=100, minLineLength=30)

# 3. Classify by angle
for line in lines:
    angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))

    if angle < 10:  # Horizontal
        # Check Y position relative to text
        if y_line ≈ y_text_center:
            → strikethrough
        elif y_line < y_text_bottom:
            → underline

    elif 30 < angle < 60:  # Diagonal
        # Check for crossing pairs
        if forms_x_pattern(line, other_lines):
            → sous-erasure
```

**Phase 2: Integration (Week 2)**
- Merge font-based formats (bold, italic) with line-based (strikethrough, X-marks)
- Add confidence scores
- Update data model

**Phase 3: Validation (Week 3)**
- Test on real philosophical texts (Derrida, Heidegger)
- Benchmark against manual annotation
- Optimize performance (<2 seconds per page)

---

## Expected Impact

### After Implementation

| Format Type | Current Recall | Expected Recall | Improvement |
|-------------|----------------|-----------------|-------------|
| Strikethrough | 10% | **90%** | +800% |
| Sous-erasure | 17% | **90%** | +429% |
| Underline | 17% | **85%** | +400% |
| **Overall F1** | **0.375** | **0.85** | **+127%** |

### Trade-offs
- **Processing time:** +1-2 seconds per page (OpenCV overhead)
- **Dependency:** OpenCV (~50 MB installed)
- **Complexity:** +200 lines of CV code

---

## Usage Examples

### Generate New Test PDFs
```python
# Modify create_test_pdfs.py to add new test cases
def create_new_test_pdf():
    c = canvas.Canvas("test_files/test_custom.pdf")

    # Add text with X-marks
    text = "Being"
    x, y = 100, 500
    c.drawString(x, y, text)

    # Draw X over it
    width = c.stringWidth(text, "Helvetica", 12)
    c.line(x-2, y-3, x+width+2, y+12)  # Diagonal /
    c.line(x-2, y+12, x+width+2, y-3)  # Diagonal \

    c.save()

# Add to ground truth JSON
ground_truth["test_custom.pdf"] = {
    "page_1": [
        {"text": "Being", "formatting": ["sous-erasure"], "y_approx": 500}
    ]
}
```

### Add New Format Type
```python
# In test_formatting_extraction.py, add detection logic:
if span["flags"] & 128:  # New flag (example)
    formats.append("new_format_type")

# In ground truth JSON:
{"text": "example", "formatting": ["new_format_type"]}

# Run tests to measure recall
python test_formatting_extraction.py
```

### Debug Specific PDF
```python
# In debug_pdf_formatting.py:
pdf_path = Path("path/to/your.pdf")
debug_pdf_formatting(pdf_path)

# Shows raw PyMuPDF data:
# - Font names
# - Flag bits
# - Sizes
# - Colors
```

---

## Integration with RAG Pipeline

### Current State
```python
# lib/rag_processing.py
def extract_text_from_pdf(pdf_path):
    # Only extracts font-based formatting
    # Missing: strikethrough, sous-erasure, underline
    ...
```

### After Implementation
```python
def extract_text_from_pdf(pdf_path, detect_visual_formatting=True):
    """
    Extract text with optional visual formatting detection.

    Args:
        pdf_path: Path to PDF
        detect_visual_formatting: If True, detect line-based formatting
                                  (requires OpenCV, ~2x slower)
    """
    # 1. Extract text with font-based formatting (current)
    text_data = extract_font_formats(pdf_path)

    # 2. Detect line-based formatting (NEW)
    if detect_visual_formatting:
        line_formats = detect_line_formats(pdf_path)
        text_data = merge_formats(text_data, line_formats)

    return text_data
```

---

## References

### Documentation
- **Comprehensive Report:** `test_files/FORMATTING_VALIDATION_REPORT.md`
- **Test Results:** `test_files/formatting_extraction_results.json`
- **Ground Truth:** `test_files/test_formatting_ground_truth.json`

### Related Work
- **Previous X-mark validation:** `test_strikethrough_detection.py` (proved X-marks are detectable)
- **PDF rendering tests:** `test_tesseract_comparison.py` (rendering quality analysis)

### External Resources
- PyMuPDF docs: https://pymupdf.readthedocs.io/en/latest/
- OpenCV Hough Lines: https://docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html
- ReportLab user guide: https://www.reportlab.com/docs/reportlab-userguide.pdf

---

## Success Criteria

### Phase 1 Complete When:
- [ ] OpenCV line detection implemented
- [ ] Can detect 90%+ of horizontal lines
- [ ] Can detect 90%+ of diagonal lines (X-marks)
- [ ] Can distinguish strikethrough from underline

### Phase 2 Complete When:
- [ ] All test PDFs pass with >80% recall per format
- [ ] Average F1 score >0.85 across all formats
- [ ] Confidence scores implemented
- [ ] Data model supports all format types

### Phase 3 Complete When:
- [ ] >85% recall on sous-erasure in real texts (Derrida/Heidegger)
- [ ] >80% recall on strikethrough in real texts
- [ ] <2 seconds per page processing time
- [ ] Manual validation on 10+ pages matches automated extraction

---

## Maintenance

### Regenerate Tests After Changes
```bash
# If you modify detection logic in test_formatting_extraction.py:
python test_formatting_extraction.py
python visualize_test_results.py

# If you change test PDFs:
python create_test_pdfs.py
python test_formatting_extraction.py
```

### Add New Test Cases
1. Edit `create_test_pdfs.py` to add new formatting scenarios
2. Update ground truth JSON
3. Run tests to validate
4. Update FORMATTING_VALIDATION_REPORT.md with findings

---

## Contact & Contribution

This testing framework was created to systematically validate formatting extraction. It provides:

✅ **Objective metrics** (precision, recall, F1)
✅ **Known ground truth** (no manual annotation needed)
✅ **Reproducible tests** (run anytime)
✅ **Clear action items** (what to fix and why)

For questions or improvements, see:
- Implementation roadmap: `test_files/FORMATTING_VALIDATION_REPORT.md`
- Test framework: `test_formatting_extraction.py`
- Visual summary: `python visualize_test_results.py`
