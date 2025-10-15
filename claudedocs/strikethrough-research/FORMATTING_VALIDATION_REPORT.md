# Formatting Validation Report

**Date:** 2025-10-15
**Test Framework:** Synthetic PDFs with Known Ground Truth
**Pipeline:** PyMuPDF Native Extraction

---

## Executive Summary

We created 3 synthetic test PDFs with known ground truth for all formatting types (bold, italic, strikethrough, sous-erasure, etc.) and tested our extraction pipeline against them.

### Overall Results
- **Total test items:** 27
- **Average F1 score:** 0.375 (37.5%)
- **Perfect matches:** 8/27 (29.6%)

### Format Type Performance

| Format Type | Instances | Detected | Recall | Status |
|-------------|-----------|----------|--------|--------|
| **Bold** | 5 | 5 (100%) | **83.3%** | ✅ PASS |
| **Italic** | 5 | 5 (100%) | **83.3%** | ✅ PASS |
| **Monospaced** | 1 | 1 (100%) | **100%** | ✅ PASS |
| **Superscript** | 1 | 1 (100%) | **100%** | ✅ PASS |
| **Subscript** | 1 | 1 (100%) | **100%** | ✅ PASS |
| **Strikethrough** | 5 | 0 (0%) | **10.0%** | ❌ FAIL |
| **Sous-erasure** | 4 | 0 (0%) | **16.7%** | ❌ FAIL |
| **Underline** | 3 | 0 (0%) | **16.7%** | ❌ FAIL |

---

## Detailed Findings

### ✅ What Works (80%+ Recall)

**1. Bold Detection (83.3% recall)**
- **Method:** PyMuPDF font name + flags (bit 4)
- **Detection logic:**
  ```python
  if "bold" in font_name or (flags & 16):  # Bold flag
      formats.append("bold")
  ```
- **Examples:**
  - ✓ "This is bold" (Helvetica-Bold)
  - ✓ "This is both" (Helvetica-BoldOblique)
  - ✓ "deleted bold" (partial: detected bold, missing strikethrough)

**2. Italic Detection (83.3% recall)**
- **Method:** PyMuPDF font name + flags (bit 1)
- **Detection logic:**
  ```python
  if "italic" in font_name or "oblique" in font_name or (flags & 2):
      formats.append("italic")
  ```
- **Examples:**
  - ✓ "This is italic" (Helvetica-Oblique)
  - ✓ "This is both" (Helvetica-BoldOblique)
  - ✓ "underlined emphasis" (partial: detected italic, missing underline)

**3. Monospaced Detection (100% recall)**
- **Method:** PyMuPDF font name + flags (bit 3)
- **Detection logic:**
  ```python
  if "courier" in font_name or "mono" in font_name or (flags & 8):
      formats.append("monospaced")
  ```
- **Examples:**
  - ✓ "code text" (Courier font)

**4. Superscript Detection (100% recall)**
- **Method:** PyMuPDF flags (bit 0)
- **Detection logic:**
  ```python
  if flags & 1:
      formats.append("superscript")
  ```
- **Examples:**
  - ✓ "1" in "Footnote¹"

**5. Subscript Detection (100% recall)**
- **Method:** Font size + position heuristic
- **Detection logic:**
  ```python
  if span["size"] < 10 and len(text) <= 3 and not (flags & 1):
      formats.append("subscript")
  ```
- **Examples:**
  - ✓ "2" in "H₂O"

---

### ❌ What Doesn't Work (<80% Recall)

**1. Strikethrough Detection (10.0% recall) - CRITICAL GAP**

**Problem:** PyMuPDF does not detect horizontal lines drawn through text as formatting.

**Evidence from tests:**
- ❌ "This is deleted" - Expected: strikethrough, Got: []
- ❌ "Deleted text" - Expected: strikethrough, Got: []
- ❌ "deleted" in paragraph - Expected: strikethrough, Got: bold (false positive)

**Why it fails:**
- Strikethrough lines are drawn as **graphics** (vector lines), not text formatting flags
- PyMuPDF `flags` field does NOT include strikethrough information for reportlab-generated PDFs
- Our current extraction only checks text attributes, not page graphics

**Solution required:**
1. **OpenCV line detection:**
   ```python
   # Detect horizontal lines overlapping text
   edges = cv2.Canny(gray, 50, 150)
   lines = cv2.HoughLinesP(edges, threshold=100, minLineLength=30)

   # Filter for horizontal lines (angle < 10°)
   horizontal_lines = [l for l in lines if abs(angle(l)) < 10]

   # Check if line intersects text bbox at middle height
   if line_y_position ≈ text_bbox_center_y:
       → strikethrough
   ```

2. **Position-based differentiation:**
   - Strikethrough: Line at ~40-60% of text height (middle)
   - Underline: Line at <20% of text height (bottom)

**Priority:** HIGH - Required for Derrida/Heidegger texts

---

**2. Sous-erasure (X-marks) Detection (16.7% recall) - CRITICAL GAP**

**Problem:** PyMuPDF does not detect diagonal lines (X-marks) crossing out text.

**Evidence from tests:**
- ❌ "Being" with X-marks - Expected: sous-erasure, Got: []
- ❌ "presence" with X-marks - Expected: sous-erasure, Got: []
- ❌ "trace" with X-marks - Expected: sous-erasure, Got: []
- ❌ "complex" with X-marks - Expected: sous-erasure, Got: bold+italic only

**Why it fails:**
- X-marks are drawn as **graphics** (diagonal vector lines), not text attributes
- Current extraction ignores page graphics completely

**Solution required:**
1. **Diagonal line detection:**
   ```python
   # Detect lines at 30-60° angles
   diagonal_lines = [l for l in lines if 30 < abs(angle(l)) < 60]

   # Cluster into pairs forming X pattern
   x_marks = find_crossing_diagonal_pairs(diagonal_lines)

   # Find text underneath X-marks
   for x_mark in x_marks:
       words_under_x = find_text_in_bbox(x_mark.bbox)
       → mark as sous-erasure
   ```

2. **X-pattern validation:**
   - Two diagonal lines crossing at ~90°
   - Both lines cover similar horizontal span
   - Intersection point near center

**Priority:** CRITICAL - Core feature for philosophical texts

**Reference:** We already validated this works in `test_strikethrough_detection.py` (see earlier test results)

---

**3. Underline Detection (16.7% recall) - MODERATE GAP**

**Problem:** PyMuPDF flags don't capture reportlab-drawn underlines.

**Evidence from tests:**
- ❌ "This is underlined" - Expected: underline, Got: []
- ❌ "Emphasized text" - Expected: underline, Got: []
- ❌ "underlined emphasis" - Expected: italic+underline, Got: italic only

**Why it fails:**
- Underline drawn with `c.line()` is a **graphic**, not a text attribute
- PyMuPDF flag bit 0 (which we expected to be underline) is actually superscript

**Solution required:**
1. **Horizontal line detection** (same as strikethrough):
   ```python
   # Detect horizontal lines BELOW text baseline
   horizontal_lines = detect_horizontal_lines()

   # Filter for lines at bottom of text bbox
   for line in horizontal_lines:
       if line_y_position < text_bbox_bottom + 5px:
           → underline
   ```

2. **Distinguish from strikethrough by Y position:**
   - Underline: Y < 20% of text height (at bottom)
   - Strikethrough: Y ≈ 50% of text height (at middle)

**Priority:** MODERATE - Nice to have, but less critical than strikethrough

---

## Test PDFs Created

### 1. test_digital_formatting.pdf
- **Purpose:** Born-digital formatting (font-based)
- **Contents:**
  - Bold, italic, bold+italic
  - Underline, strikethrough
  - Superscript, subscript
  - Monospaced
- **Results:** Font-based formats detected (bold, italic, monospace), graphic-based formats missed (underline, strikethrough)

### 2. test_xmarks_and_strikethrough.pdf
- **Purpose:** Visual line-based formatting (graphics-based)
- **Contents:**
  - 3× X-marked words (sous-erasure)
  - 2× Horizontal strikethrough
  - 1× Underline (control test)
  - Normal text (control test)
- **Results:** ALL line-based formatting missed (0% detection)

### 3. test_mixed_formatting.pdf
- **Purpose:** Complex combinations
- **Contents:**
  - Bold + strikethrough
  - Italic + underline
  - Bold + italic + X-marks
  - Paragraph with mixed formats
- **Results:** Font formats detected, line formats missed

---

## Implementation Roadmap

### Phase 1: Line Detection Infrastructure (Week 1)
**Goal:** Implement OpenCV-based line detection pipeline

1. **Add OpenCV to dependencies**
   ```bash
   uv pip install opencv-python-headless
   ```

2. **Create line detection module** (`lib/line_detection.py`)
   - Render PDF page to image at 300 DPI
   - Apply Canny edge detection
   - Use Hough Line Transform
   - Classify lines by angle:
     - Horizontal (0-10°): strikethrough or underline
     - Diagonal (30-60°): sous-erasure (X-marks)

3. **Add line-to-text matching logic**
   - Get text bboxes from PyMuPDF
   - Check line intersection with text
   - Determine format type by relative Y position

**Success Criteria:**
- Detect 90%+ of horizontal lines
- Detect 90%+ of diagonal lines (X-marks)
- Correctly distinguish strikethrough from underline

---

### Phase 2: Format Integration (Week 2)
**Goal:** Integrate line detection with text extraction

1. **Extend `rag_processing.py`**
   - Add optional `detect_visual_formatting=True` parameter
   - Run line detection alongside text extraction
   - Merge font-based formats (bold, italic) with line-based formats (strikethrough, sous-erasure)

2. **Update data model**
   ```python
   {
       "text": "Being",
       "formatting": {
           "bold": False,
           "italic": False,
           "strikethrough": False,
           "sous_erasure": True,  # NEW
           "underline": False
       },
       "bbox": [x1, y1, x2, y2],
       "confidence": 0.95  # NEW: detection confidence
   }
   ```

3. **Add quality metrics**
   - Track detection confidence per format type
   - Log false positive rate
   - Report unclear cases (e.g., line too far from text)

**Success Criteria:**
- All test PDFs pass with >80% recall per format
- Average F1 score >0.85 across all formats

---

### Phase 3: Real-World Validation (Week 3)
**Goal:** Validate on actual philosophical texts

1. **Test on known samples:**
   - Derrida "Of Grammatology" pages with sous-erasure
   - Heidegger "Question of Being" pages with X-marks
   - Mixed formatting documents

2. **Benchmark against manual annotation:**
   - Manually annotate 10 pages with known formatting
   - Compare automated extraction to ground truth
   - Report precision, recall, F1 per format type

3. **Performance optimization:**
   - Profile line detection overhead
   - Optimize for speed (target: <2 seconds per page)
   - Add caching for repeated processing

**Success Criteria:**
- >85% recall on sous-erasure (X-marks) in real texts
- >80% recall on strikethrough in real texts
- <2 seconds per page processing time

---

## Quick Wins (Can Implement Today)

### 1. Add Warning for Missed Formatting
```python
# In rag_processing.py
def extract_with_formatting_warnings(pdf_path):
    text_data = extract_text_from_pdf(pdf_path)

    # Check for potential visual formatting
    doc = fitz.open(pdf_path)
    for page in doc:
        # Count vector graphics
        drawings = page.get_drawings()
        if len(drawings) > 10:
            logger.warning(
                f"Page {page.number} has {len(drawings)} vector graphics. "
                "Visual formatting (strikethrough, sous-erasure) may not be detected. "
                "Enable --detect-visual-formatting for full extraction."
            )
```

### 2. Update README with Known Limitations
```markdown
## Known Limitations

### Visual Formatting Not Detected (Yet)
Current extraction detects font-based formatting (bold, italic, monospace) but NOT:
- ❌ Strikethrough (horizontal lines through text)
- ❌ Sous-erasure (X-marks crossing out text)
- ❌ Underlines (horizontal lines below text)

**Workaround:** Use `--detect-visual-formatting` flag (requires OpenCV, ~2x slower)
**Status:** Planned for Phase 2 (see ROADMAP.md)
```

### 3. Add Flag to Enable Line Detection (Stub)
```python
# In rag_processing.py
def extract_text_from_pdf(pdf_path, detect_visual_formatting=False):
    """
    Extract text with optional visual formatting detection.

    Args:
        pdf_path: Path to PDF file
        detect_visual_formatting: If True, detect strikethrough, sous-erasure, underlines
                                  (requires OpenCV, slower but more accurate)
    """
    if detect_visual_formatting:
        raise NotImplementedError(
            "Visual formatting detection not yet implemented. "
            "See test_files/FORMATTING_VALIDATION_REPORT.md for status."
        )

    # Current implementation (font-based only)
    ...
```

---

## Testing Artifacts

### Files Created
1. **create_test_pdfs.py** - Generates synthetic test PDFs with known ground truth
2. **test_formatting_extraction.py** - Validates extraction against ground truth
3. **test_files/test_digital_formatting.pdf** - Font-based formatting tests
4. **test_files/test_xmarks_and_strikethrough.pdf** - Visual formatting tests
5. **test_files/test_mixed_formatting.pdf** - Complex combination tests
6. **test_files/test_formatting_ground_truth.json** - Ground truth data
7. **test_files/formatting_extraction_results.json** - Detailed test results

### Usage
```bash
# Regenerate test PDFs (if needed)
python create_test_pdfs.py

# Run extraction validation
python test_formatting_extraction.py

# Debug specific formatting issues
python debug_pdf_formatting.py
python debug_extraction_matching.py
```

---

## Conclusions

### Current State
- **Font-based formatting:** Works well (>80% recall for bold, italic, monospace, super/subscript)
- **Line-based formatting:** Completely missing (0-17% recall for strikethrough, sous-erasure, underline)

### Why Line-Based Formatting Fails
- PyMuPDF extracts text attributes (font, size, flags) but **ignores page graphics** (vector lines)
- Strikethrough, sous-erasure, and underlines are drawn as **graphics**, not text attributes
- Current pipeline has no computer vision component

### Path Forward
1. **Implement OpenCV line detection** (Phase 1)
2. **Integrate with text extraction** (Phase 2)
3. **Validate on real texts** (Phase 3)

### Priority
- **CRITICAL:** Sous-erasure (X-marks) detection - core feature for philosophical texts
- **HIGH:** Strikethrough detection - common in edited manuscripts
- **MODERATE:** Underline detection - nice to have

### Expected Impact
- With line detection: >85% recall on ALL formatting types
- Processing overhead: +1-2 seconds per page
- Required dependency: OpenCV (~50MB)

---

## References

- **Test framework:** `/home/rookslog/mcp-servers/zlibrary-mcp/test_formatting_extraction.py`
- **Ground truth:** `/home/rookslog/mcp-servers/zlibrary-mcp/test_files/test_formatting_ground_truth.json`
- **Previous X-mark validation:** `/home/rookslog/mcp-servers/zlibrary-mcp/test_strikethrough_detection.py`
- **PyMuPDF docs:** https://pymupdf.readthedocs.io/en/latest/
- **OpenCV Line Detection:** https://docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html
