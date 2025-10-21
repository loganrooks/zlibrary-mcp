# RAG Architecture Refactoring Onboarding Document

**Agent Transition Context Document**
**Date**: 2025-10-14
**Current Token Usage**: 241k (handoff required)
**Branch**: `feature/rag-pipeline-enhancements-v2`
**Quality Score**: 41.75/100 (target: 75-85)
**Project**: 9-week incremental refactoring to fix architectural flaws

---

## Section 1: Executive Summary

### Current State

**What's Working** ✅:
- **Content Extraction**: 99%+ retention rate (excellent)
- **Text Cleanup**: Word concatenation fixed, hyphenation handled
- **Basic Structure**: Paragraphs, line breaks, basic headings
- **Metadata Generation**: YAML frontmatter with title, author, page numbers
- **OCR Pipeline**: Quality detection and ocrmypdf integration working

**What's Broken** ❌:
- **Quality Score**: 41.75/100 (failing academic use case)
- **Footnotes**: 16.7% orphaned references (refs without definitions)
- **Citations**: 8% loss rate in reference-heavy sections
- **Formatting**: 0% bold/italic preservation
- **Structure**: 70-85% heading detection accuracy (should be 90%+)

### The Problem

**This is NOT a bug problem—it's an ARCHITECTURAL problem.**

The RAG pipeline has **5 fundamental architectural flaws**:

1. **Conflating Extraction with Interpretation**: Single 200+ line function does extraction + analysis + formatting
2. **Block-Level Processing Misses Page Context**: No spatial awareness (can't find footnotes at bottom of page)
3. **Single-Pass Processing Prevents Relationship Modeling**: Can't link footnote refs to definitions
4. **Using Wrong PyMuPDF APIs**: Ignores bounding box coordinates needed for spatial analysis
5. **Detection Without Preservation**: Detects bold formatting but never applies it to output

These flaws prevent quality improvements through bug fixes alone.

### The Solution

**Architecture 3: Incremental Refactoring** (9-week timeline)

- **Not a rewrite**: Build on working extraction (99%+ retention)
- **Incremental value**: Ship improvements every 1-2 weeks
- **Low-medium risk**: Each phase independently valuable, rollback possible
- **Target quality**: 75-85 (sufficient for academic use)

### GPU Enhancement Option (Future)

**Phase 7 (Optional)**: GPU-accelerated semantic segmentation
- **When**: After Phase 6 complete and stable
- **Technology**: YOLOv8 + DocLayNet for semantic page segmentation
- **Expected improvement**: +5-10 quality points (to 80-95 range)
- **Use case**: Worth it for high-value academic/legal document processing
- **Not required**: Can achieve 75-85 quality without GPU

### Immediate Goal

**Implement Phase 1 (Weeks 1-2)**: Data Model Foundation
- Create structured data classes (TextSpan, PageRegion, Entity)
- Refactor `_analyze_pdf_block()` to return structured data
- Add backward compatibility flag
- No behavior change, just foundation for improvements

---

## Section 2: Session Accomplishments (Today's Work)

### Chronological Progress (2025-10-14)

**Early Session** (commits 425901f - d96b0fc):
1. ✅ Fixed word concatenation in `_join_lines_intelligently()` (lib/rag_processing.py:157-181)
2. ✅ Implemented citation mode with `preserve_linebreaks` parameter (lib/rag_processing.py:201)
3. ✅ Added OCR quality pipeline with ocrmypdf integration (lib/rag_processing.py:450-500)
4. ✅ Implemented ToC-based heading detection with hybrid fallback (lib/rag_processing.py:300-350)
5. ✅ Added dual page numbering: `[[PDF:5]]` and `((written:iii))` (lib/rag_processing.py:280-295)

**Mid Session** (research and analysis):
6. ✅ Researched footnote/citation handling in academic PDFs
7. ✅ Documented 5 architectural flaws preventing quality improvement
8. ✅ Compared 3 architectural solutions (Multi-Pass, Hybrid, Incremental)
9. ✅ Selected Architecture 3 (Incremental Refactoring) as lowest-risk path

**Late Session** (documentation and verification):
10. ✅ Implemented publisher extraction from front matter (lib/metadata_generator.py:45-90)
11. ✅ Created metadata verification framework (lib/metadata_verification.py - NEW FILE)
12. ✅ Created quality verification framework (.claude/RAG_QUALITY_FRAMEWORK.md - NEW FILE)
13. ✅ Documented failure modes via failure analysis (claudedocs/rag_failure_analysis.md)
14. ✅ Created 9-week architectural roadmap (claudedocs/architecture_analysis_rag_pipeline.md)

### Key File Changes

**Modified Files**:
- `lib/rag_processing.py`: Word joining, citation mode, OCR pipeline, ToC headings
- `lib/metadata_generator.py`: Publisher extraction, frontmatter generation
- `pyproject.toml` & `uv.lock`: Dependency updates

**New Files**:
- `lib/metadata_verification.py`: Metadata extraction and verification
- `lib/quality_verification.py`: Quality scoring and validation (planned, not yet created)
- `.claude/RAG_QUALITY_FRAMEWORK.md`: Quality verification framework
- `claudedocs/rag_failure_analysis.md`: Failure mode analysis
- `claudedocs/architecture_analysis_rag_pipeline.md`: Complete architectural analysis
- `claudedocs/publisher_extraction_implementation.md`: Publisher extraction docs
- `docs/METADATA_VERIFICATION.md`: Metadata verification specification
- `docs/HYBRID_TOC_EXTRACTION.md`: ToC extraction design
- `docs/IMPLEMENTATION_SUMMARY_HYBRID_TOC.md`: ToC implementation summary

**Test Files**:
- `__tests__/python/test_publisher_extraction.py`: Publisher extraction tests
- `__tests__/python/test_toc_hybrid.py`: ToC hybrid extraction tests

---

## Section 3: Current Codebase State

### Working Components

**Robust Extraction** (lib/rag_processing.py):
- ✅ `_join_lines_intelligently()` (lines 157-181): Prevents word concatenation
- ✅ `_clean_pdf_text()` (lines 184-250): Removes headers/footers, cleans null chars
- ✅ `_detect_footnotes_in_span()` (lines 403-420): Detects footnote markers (superscript)
- ✅ OCR quality detection (lines 450-475): Identifies when OCR needed
- ✅ OCR pipeline with ocrmypdf (lines 476-500): Processes scanned PDFs
- ✅ Content retention: 99%+ across diverse PDFs

**Metadata Generation** (lib/metadata_generator.py):
- ✅ `extract_title_author_from_pdf()` (lines 15-120): Extracts title/author from PDF metadata
- ✅ `extract_publisher_from_front_matter()` (lines 45-90): Publisher extraction from first 10 pages
- ✅ `generate_metadata_sidecar()` (lines 125-180): Creates JSON metadata sidecar
- ✅ `add_yaml_frontmatter_to_content()` (lines 185-220): Adds YAML frontmatter

**Metadata Verification** (lib/metadata_verification.py - NEW):
- ✅ `extract_pdf_metadata()`: Extracts metadata from PDFs
- ✅ `extract_epub_metadata()`: Extracts metadata from EPUBs
- ✅ `verify_metadata()`: Validates metadata completeness and accuracy

**Quality Framework** (.claude/RAG_QUALITY_FRAMEWORK.md):
- ✅ Sampling strategy for quality verification
- ✅ Failure mode catalog (garbled text, word concatenation, etc.)
- ✅ Quality metrics (completeness, text quality, structure, metadata)
- ✅ Automated vs manual verification workflows

### Test Coverage Status

**Well-Tested** ✅:
- Word joining logic (test_rag_processing.py::test_join_lines_intelligently)
- Basic PDF extraction (test_rag_processing.py::TestProcessDocumentForRAG)
- Metadata generation (test_metadata_generator.py)
- Publisher extraction (test_publisher_extraction.py)
- ToC extraction (test_toc_hybrid.py)

**Missing Tests** ❌:
- Footnote definition extraction (only detection tested, not linking)
- Bold/italic formatting preservation (no tests exist)
- Citation validation (count comparison not tested)
- Quality verification metrics (framework documented, not implemented)
- Multi-page footnote linking (edge case)

### Known Issues (from Quality Verification)

**Critical Issues** 🔴:
1. **Orphaned Footnote References** (16.7% failure rate):
   - Detection works: `_detect_footnotes_in_span()` finds `[^n]` markers
   - Extraction missing: No code to extract definitions from bottom of page
   - Linking missing: No code to link refs to definitions
   - **File**: lib/rag_processing.py (needs Phase 4 implementation)

2. **Citation Loss** (8% on reference-heavy pages):
   - Multi-line citations split across blocks
   - En-dash/em-dash handling in citations
   - **File**: lib/rag_processing.py:184-250 (`_clean_pdf_text`)

**Important Issues** 🟡:
3. **Bold Formatting Lost** (100% loss rate):
   - Detection works: `is_bold = bool(flags & 2)` at line 403
   - Application missing: Never wraps text in `**bold**`
   - **File**: lib/rag_processing.py (needs Phase 3 implementation)

4. **Akademie Citations Not Formatted** (marginal citations):
   - Not recognized as citations (in margins, not body)
   - Need spatial analysis (Phase 2: Layout Information)

5. **Content Loss on Some Pages** (~5% of pages):
   - Complex layouts (multi-column, sidebars)
   - Need layout-aware processing (Phase 2)

6. **Multi-line Header Splitting**:
   - Headers across multiple lines not detected as single heading
   - ToC hybrid extraction helps but not complete

---

## Section 4: Architectural Analysis Summary

### 5 Architectural Flaws Identified

**Flaw 1: Conflating Extraction with Interpretation**
- **Problem**: `_analyze_pdf_block()` has 6+ responsibilities (200+ lines)
- **Consequence**: Can't fix one aspect without breaking others
- **Violated Principle**: Separation of Concerns (SOLID)

**Flaw 2: Block-Level Processing Misses Page Context**
- **Problem**: No spatial awareness (no x/y coordinates tracked)
- **Consequence**: Can't distinguish footnote zone from body text
- **Violated Principle**: Abstraction at Right Level

**Flaw 3: Single-Pass Processing Prevents Relationship Modeling**
- **Problem**: Can't link entities not yet seen (forward references)
- **Consequence**: Can't link footnote markers to definitions
- **Violated Principle**: Data Before Operations

**Flaw 4: Using Wrong PyMuPDF APIs**
- **Problem**: Uses `get_text("dict")` but ignores bounding boxes
- **Available but unused**: `get_text_blocks()` with (x0, y0, x1, y1)
- **Violated Principle**: Use the Right Tool for the Job

**Flaw 5: Detection Without Preservation**
- **Problem**: Detects bold (line 403) but never applies to output
- **Consequence**: 0% formatting preservation
- **Violated Principle**: Information Preservation Through Pipeline

### 3 Proposed Solutions Compared

| Architecture | Time | Risk | Quality | ROI | Selected |
|--------------|------|------|---------|-----|----------|
| **Arch 1: Multi-Pass Pipeline** | 14 weeks | HIGH | 85-95 | Medium | ❌ |
| **Arch 2: Hybrid Extraction** | 13 weeks | MEDIUM-HIGH | 80-90 | Medium | ❌ |
| **Arch 3: Incremental Refactoring** | 9 weeks | LOW-MEDIUM | 75-85 | HIGH | ✅ |

### Why Architecture 3 (Incremental Refactoring) Chosen

**Decision Criteria Weighted Scoring**:
- Risk (30%): 8/10 (vs 2/10 and 4/10)
- Time to value (25%): 9/10 (vs 2/10 and 3/10)
- Expected quality (20%): 7/10 (vs 10/10 and 9/10)
- Maintainability (15%): 7/10 (vs 10/10 and 8/10)
- Team learning (10%): 9/10 (vs 4/10 and 5/10)
- **Weighted Total**: **8.0/10** (winner)

**Key Advantages**:
- ✅ Ships improvements every 1-2 weeks (incremental ROI)
- ✅ Can rollback each phase if issues discovered
- ✅ Reuses working code (99%+ content retention)
- ✅ Low-medium risk (proven Strangler Fig pattern)
- ✅ 60% code reuse (vs 0-30% for alternatives)

**Full Analysis**: See `claudedocs/architecture_analysis_rag_pipeline.md`

---

## Section 5: 9-Week Implementation Roadmap

### Phase 1: Data Model Foundation (Weeks 1-2)

**Goals**:
- Create structured data classes: `TextSpan`, `PageRegion`, `Entity`
- Refactor `_analyze_pdf_block()` to return structured data
- Add backward compatibility flag (`return_structured=True/False`)
- No behavior change, just foundation

**Deliverables**:
- `lib/rag_processing.py`: New classes and refactored function
- `__tests__/python/test_rag_processing.py`: Equivalence tests
- Documentation: Data model design doc

**Success Criteria**:
- ✅ All existing tests pass
- ✅ Old and new outputs identical (equivalence verified)
- ✅ No performance degradation (<5% slowdown acceptable)
- ✅ Code coverage maintained (≥60%)

**Estimated Effort**: 2 weeks (40-60 hours)

**Dependencies**: None (can start immediately)

**Risk Mitigation**:
- Dual implementation (old + new paths)
- Feature flag for gradual rollout
- Extensive equivalence testing
- Can rollback by setting `return_structured=False`

---

### Phase 2: Layout Information (Week 3)

**Goals**:
- Extract bounding boxes from PyMuPDF (x0, y0, x1, y1)
- Classify page regions using y-coordinates:
  - Header: y < 50 (top 50 points)
  - Footer: y > page_height - 50
  - Footnote: y > page_height * 0.85 (bottom 15%)
  - Margin: x < 50 or x > page_width - 50
  - Body: Everything else

**Deliverables**:
- `lib/rag_processing.py`: `_classify_page_regions()` function
- `__tests__/python/test_rag_processing.py`: Region classification tests
- Documentation: Layout analysis design

**Success Criteria**:
- ✅ 95%+ pages correctly classify regions
- ✅ Footnote zones detected on academic papers
- ✅ Header/footer regions identified accurately
- ✅ Enables Phase 4 (footnote extraction)

**Estimated Effort**: 1 week (20-30 hours)

**Dependencies**: Phase 1 complete (needs `PageRegion` data class)

**Risk Mitigation**:
- Start with simple y-coordinate thresholds
- Test on diverse page layouts
- Can adjust thresholds based on empirical data

**Impact**: +5 quality points (foundation for footnote extraction)

---

### Phase 3: Formatting Preservation (Week 4)

**Goals**:
- Use `TextSpan.is_bold` and `TextSpan.is_italic` metadata
- Create `FormattingApplier` class
- Wrap bold text in `**bold**`
- Wrap italic text in `*italic*`
- Handle nested formatting `***bold italic***`

**Deliverables**:
- `lib/rag_processing.py`: `FormattingApplier` class
- `__tests__/python/test_rag_processing.py`: Formatting preservation tests
- Documentation: Formatting implementation design

**Success Criteria**:
- ✅ Bold preservation: 0% → 85%+ (target 90%)
- ✅ Italic preservation: 0% → 80%+
- ✅ Nested formatting handled correctly
- ✅ Quality score: 41.75 → 56.75 (+15 points)

**Estimated Effort**: 1 week (20-30 hours)

**Dependencies**: Phase 1 complete (needs `TextSpan` data class)

**Risk Mitigation**:
- Insert as separate pass (doesn't modify extraction)
- Test independently from extraction
- Can disable via feature flag if issues

**Impact**: +15 quality points (addresses MEDIUM priority issue)

---

### Phase 4: Footnote Linking (Weeks 5-6)

**Goals**:
- Extract footnote definitions from footnote zones (Phase 2 regions)
- Create `FootnoteLinker` class
- Link footnote markers `[^1]` to definitions `[^1]: text`
- Validate all refs have defs (quality gate)

**Deliverables**:
- `lib/rag_processing.py`: `FootnoteLinker` class
- `__tests__/python/test_rag_processing.py`: Footnote linking tests
- Documentation: Footnote linking design

**Success Criteria**:
- ✅ Orphaned footnotes: 16.7% → <2%
- ✅ Footnote definitions extracted: 0% → 90%+
- ✅ Ref-def linking working (bidirectional)
- ✅ Quality score: 56.75 → 81.75 (+25 points)

**Estimated Effort**: 2 weeks (40-60 hours)

**Dependencies**: Phase 2 complete (needs region classification)

**Risk Mitigation**:
- Start with simple numbered footnotes (1, 2, 3)
- Add symbol footnotes (*, †, ‡) later
- Validate footnote pairs before markdown generation
- Fallback: inline citation if definition not found

**Impact**: +25 quality points (addresses HIGH priority issue)

---

### Phase 5: Validation Layer (Week 7)

**Goals**:
- Create `QualityValidator` class
- Check footnote integrity (all refs have defs)
- Validate citation counts (PDF vs markdown)
- Measure content retention (≥80%)
- Generate quality score (0-100)

**Deliverables**:
- `lib/quality_verification.py`: `QualityValidator` class
- `__tests__/python/test_quality_verification.py`: Validation tests
- Documentation: Quality validation design

**Success Criteria**:
- ✅ Zero invalid output shipped (quality gate enforcement)
- ✅ Citation accuracy: 92% → 98%+
- ✅ Quality score: 81.75 → 91.75 (+10 points)
- ✅ Quality reports generated automatically

**Estimated Effort**: 1 week (20-30 hours)

**Dependencies**: Phase 4 complete (needs footnote linking)

**Risk Mitigation**:
- Start with simple checks (orphaned footnotes)
- Add sophisticated validation incrementally
- Make thresholds configurable
- Non-blocking warnings for minor issues

**Impact**: +10 quality points (prevents invalid output)

---

### Phase 6: Multi-Pass Refactoring (Weeks 8-9)

**Goals**:
- Separate extraction from processing (clear pipeline)
- Create `EntityDetector` class (headings, footnotes, citations)
- Create `RelationshipLinker` class (ref ↔ def)
- Make each pass independently testable

**Deliverables**:
- `lib/rag_processing.py`: Refactored into explicit pipeline
- `__tests__/python/test_rag_processing.py`: Per-pass tests
- Documentation: Pipeline architecture

**Success Criteria**:
- ✅ Quality score: 91.75 → 96.75 (+5 points, realistic: 75-85)
- ✅ Code coverage: 60% → 80%+
- ✅ Each pass testable in isolation
- ✅ Maintainability: Significantly improved

**Estimated Effort**: 2 weeks (40-60 hours)

**Dependencies**: All previous phases complete

**Risk Mitigation**:
- Refactor incrementally (one pass at a time)
- Maintain backward compatibility
- Extensive regression testing
- Can defer if quality targets met early

**Impact**: +5 quality points (long-term maintainability)

---

### Phases Summary Table

| Phase | Duration | Risk | Quality Δ | Cumulative | Deliverable |
|-------|----------|------|-----------|------------|-------------|
| **1. Data Model** | 2 weeks | LOW | +0 | 41.75 | Foundation classes |
| **2. Layout Info** | 1 week | LOW | +5 | 46.75 | Region classification |
| **3. Formatting** | 1 week | LOW | +15 | 61.75 | Bold/italic preservation |
| **4. Footnotes** | 2 weeks | MEDIUM | +25 | 86.75 | Footnote linking |
| **5. Validation** | 1 week | LOW | +10 | 96.75 | Quality gates |
| **6. Refactoring** | 2 weeks | MEDIUM | +5 | 100+ | Clean pipeline |
| **Total** | **9 weeks** | **LOW-MED** | **+60** | **75-85** | Production-ready |

**Note**: Realistic target is 75-85 quality score (accounting for edge cases).

---

## Section 6: GPU Enhancement (Future Phase 7)

### When to Implement

**Prerequisites**:
- ✅ Phase 6 complete and stable (9 weeks)
- ✅ Quality score 75-85 achieved
- ✅ All critical issues resolved
- ✅ Production deployment successful

**Decision Criteria**:
- Volume: Processing >1000 academic PDFs/month
- Quality: Need 85-95% accuracy (beyond CPU capability)
- Resources: GPU infrastructure available (local or cloud)
- ROI: Quality improvement justifies GPU cost

### Technology Stack

**YOLOv8 + DocLayNet**:
- **YOLOv8**: State-of-the-art object detection (2023)
- **DocLayNet**: Document layout dataset (11 categories, 80k+ pages)
- **Categories**: Text, title, list, table, figure, caption, formula, footnote, section header, page header, page footer

**Implementation**:
```python
# Pseudo-code for GPU-enhanced layout segmentation
from ultralytics import YOLO

def gpu_enhanced_layout_analysis(pdf_page):
    # Convert page to image
    image = page_to_image(pdf_page)

    # Run YOLOv8 model
    model = YOLO('doclaynet-yolov8.pt')
    results = model(image)

    # Extract regions with semantic labels
    regions = []
    for detection in results:
        region = {
            'type': detection.label,  # 'footnote', 'text', 'title', etc.
            'confidence': detection.confidence,
            'bbox': detection.bbox,
            'text': extract_text_from_bbox(pdf_page, detection.bbox)
        }
        regions.append(region)

    return regions
```

### Expected Improvement

**Quality Score Impact**: +5-10 points
- Current (CPU-based): 75-85
- With GPU: 80-95

**Specific Improvements**:
- Heading detection: 70-85% → 90-95% (semantic title detection)
- Footnote extraction: 90% → 98% (explicit footnote zone detection)
- Table handling: 50% → 85% (table region detection + extraction)
- Multi-column layouts: 60% → 90% (reading order inference)

### Use Cases Where GPU is Worth It

**High-Value Scenarios** ✅:
- Academic research corpus (thousands of papers)
- Legal document processing (contracts, case law)
- Technical manuals with complex layouts
- Historical document digitization
- Multi-language document processing

**Not Worth It** ❌:
- Low volume (<100 PDFs/month)
- Simple layouts (single-column text)
- Already achieving quality targets (75-85)
- No GPU infrastructure available
- Tight budget constraints

### Implementation Effort

**Estimated Time**: 2-3 weeks
**Dependencies**: YOLOv8, DocLayNet weights, GPU (CUDA)
**Integration Points**: Replace Phase 2 (Layout Information) with GPU version

**Deliverables**:
- `lib/gpu_layout_segmentation.py`: GPU-enhanced layout analysis
- `__tests__/python/test_gpu_layout.py`: GPU layout tests
- `docs/GPU_ENHANCEMENT.md`: GPU implementation guide

---

## Section 7: Implementation Guidelines

### Use Task Agents for Complex Components

**When to Delegate to Task Agent**:
- Multi-file changes (>3 files)
- Complex refactoring (>200 lines changed)
- New feature implementation (Phase 1-6 work)
- Test suite creation (>10 test cases)

**Example**:
```
Delegate Phase 3 (Formatting Preservation) to Task agent:
- Create FormattingApplier class
- Modify _analyze_pdf_block() to use TextSpan
- Add 10+ formatting tests
- Update documentation
```

### Use Serena for Session Persistence

**Before Starting Work**:
```
1. list_memories() → Check existing context
2. read_memory("rag_refactoring_plan") → Load plan
3. read_memory("phase_1_progress") → Resume from last checkpoint
```

**During Work**:
```
1. write_memory("phase_1_progress", "Step 1.2 complete: TextSpan class created")
2. write_memory("blockers", "Issue with PyMuPDF bbox extraction on page 551")
3. write_memory("decisions", "Using feature flag return_structured for backward compatibility")
```

**After Work**:
```
1. write_memory("session_summary", "Phase 1 Step 1 complete, tests passing")
2. write_memory("next_steps", "Implement PageRegion class, then equivalence tests")
```

### Document Everything in claudedocs/

**Per-Phase Documentation**:
- `claudedocs/phase_1_data_model.md`: Data model design and implementation
- `claudedocs/phase_2_layout_info.md`: Layout classification design
- `claudedocs/phase_3_formatting.md`: Formatting preservation implementation
- `claudedocs/phase_4_footnotes.md`: Footnote linking design
- `claudedocs/phase_5_validation.md`: Quality validation implementation
- `claudedocs/phase_6_refactoring.md`: Pipeline refactoring summary

**Why claudedocs/**:
- User-facing technical documentation goes in `docs/`
- Agent/developer context goes in `claudedocs/`
- Claude Code can reference without cluttering user docs

### Follow Version Control Practices

**Branch Strategy**:
```bash
# Main branch for this work
feature/rag-architecture-refactoring-v3

# Per-phase sub-branches (optional)
feature/rag-phase-1-data-model
feature/rag-phase-2-layout-info
feature/rag-phase-3-formatting
```

**Commit Convention** (.claude/VERSION_CONTROL.md):
```bash
# Format: <type>: <description>
feat: implement TextSpan data class for formatting preservation
fix: correct bbox extraction from PyMuPDF dict
docs: add Phase 1 data model design document
test: add equivalence tests for structured output
refactor: separate extraction from formatting in _analyze_pdf_block
```

**PR Process**:
- Create PR after each phase complete
- Include quality metrics in PR description
- Run full test suite before PR
- Get review before merging to main

### Run Quality Verification After Each Phase

**After Phase 1**:
```bash
uv run pytest __tests__/python/test_rag_processing.py -v
# Verify equivalence (old vs new output identical)
```

**After Phase 3**:
```bash
uv run pytest __tests__/python/test_rag_processing.py::test_bold_preservation -v
# Verify bold formatting: 0% → 85%+
```

**After Phase 4**:
```bash
uv run pytest __tests__/python/test_rag_processing.py::test_footnote_linking -v
# Verify orphaned footnotes: 16.7% → <2%
```

**After Phase 6**:
```bash
uv run pytest
# Full test suite, verify quality score ≥75
```

### Maintain Backward Compatibility

**Feature Flags** (use environment variables):
```python
# lib/rag_processing.py
USE_STRUCTURED_DATA = os.getenv('RAG_USE_STRUCTURED_DATA', 'true') == 'true'
USE_LAYOUT_REGIONS = os.getenv('RAG_USE_LAYOUT_REGIONS', 'true') == 'true'
USE_FORMATTING_APPLIER = os.getenv('RAG_USE_FORMATTING', 'true') == 'true'
USE_FOOTNOTE_LINKER = os.getenv('RAG_USE_FOOTNOTE_LINKER', 'true') == 'true'
USE_VALIDATOR = os.getenv('RAG_USE_VALIDATOR', 'true') == 'true'

def process_pdf(pdf_path: Path) -> str:
    if not USE_STRUCTURED_DATA:
        # Fallback to old monolithic processing
        return _process_pdf_legacy(pdf_path)

    # New pipeline with feature flags
    # ...
```

**Rollback Procedure**:
1. Set environment variable: `RAG_USE_[FEATURE]=false`
2. Restart service
3. Old code path activated
4. Fix issues in new code
5. Re-enable: `RAG_USE_[FEATURE]=true`

---

## Section 8: Immediate Next Steps

### Step 1: Create Feature Branch

```bash
cd /home/rookslog/mcp-servers/zlibrary-mcp

# Create new feature branch from current state
git checkout -b feature/rag-architecture-refactoring-v3

# Verify branch
git branch --show-current
# Should show: feature/rag-architecture-refactoring-v3

# Check status
git status
# Should show clean working tree or pending changes
```

### Step 2: Implement Phase 1.1 - Create Data Model Classes

**Create new file: `lib/rag_data_models.py`**:

```python
"""
Data models for RAG pipeline structured processing.

This module defines data classes for representing text with formatting metadata,
page regions with spatial information, and entities with relationships.

Created: 2025-10-14 (Phase 1 of 9-week refactoring)
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TextSpan:
    """
    Represents a span of text with formatting metadata.

    Attributes:
        text: The text content
        is_bold: Whether text is bold (font flag & 2)
        is_italic: Whether text is italic (font flag & 1)
        font_size: Font size in points
        font_name: Font family name
        bbox: Bounding box (x0, y0, x1, y1) in page coordinates
    """
    text: str
    is_bold: bool
    is_italic: bool
    font_size: float
    font_name: str
    bbox: tuple[float, float, float, float]

@dataclass
class PageRegion:
    """
    Represents a region of a page with spatial classification.

    Attributes:
        region_type: Type of region ('header', 'body', 'footer', 'margin', 'footnote')
        spans: List of TextSpan objects in this region
        bbox: Bounding box (x0, y0, x1, y1) in page coordinates
        page_num: Page number (1-indexed)
    """
    region_type: str  # 'header', 'body', 'footer', 'margin', 'footnote'
    spans: List[TextSpan]
    bbox: tuple[float, float, float, float]
    page_num: int

@dataclass
class Entity:
    """
    Represents a document entity (heading, footnote, citation, etc.).

    Attributes:
        entity_type: Type of entity ('heading', 'footnote_ref', 'footnote_def', 'citation')
        content: Text content of entity
        metadata: Flexible dict for entity-specific data
        position: PageRegion where entity is located
    """
    entity_type: str  # 'heading', 'footnote_ref', 'footnote_def', 'citation'
    content: str
    metadata: dict
    position: Optional[PageRegion] = None
```

### Step 3: Write Tests for Data Model

**Add to `__tests__/python/test_rag_processing.py`**:

```python
def test_text_span_creation():
    """Test TextSpan data class."""
    span = TextSpan(
        text="Example text",
        is_bold=True,
        is_italic=False,
        font_size=12.0,
        font_name="Arial",
        bbox=(10.0, 20.0, 100.0, 30.0)
    )

    assert span.text == "Example text"
    assert span.is_bold == True
    assert span.is_italic == False
    assert span.font_size == 12.0
    assert span.bbox == (10.0, 20.0, 100.0, 30.0)

def test_page_region_classification():
    """Test PageRegion data class."""
    span = TextSpan("body text", False, False, 10.0, "Arial", (50, 100, 200, 110))
    region = PageRegion(
        region_type='body',
        spans=[span],
        bbox=(50, 100, 500, 700),
        page_num=1
    )

    assert region.region_type == 'body'
    assert len(region.spans) == 1
    assert region.page_num == 1
```

### Step 4: Document Progress in Serena Memories

```python
# Use Serena to persist context
write_memory("rag_refactoring_plan", "9-week incremental refactoring, currently Phase 1")
write_memory("phase_1_progress", "Step 1 complete: Data model classes created and tested")
write_memory("next_steps", "Refactor _analyze_pdf_block() to return structured data with backward compatibility")
```

### Step 5: Checkpoint After Each Sub-Phase

**After Data Model Creation**:
```bash
git add lib/rag_data_models.py __tests__/python/test_rag_processing.py
git commit -m "feat(phase-1): create TextSpan, PageRegion, Entity data classes

- Add structured data models for RAG pipeline
- TextSpan: text with formatting metadata (bold, italic, font)
- PageRegion: spatial classification (header, body, footer, footnote, margin)
- Entity: document entities (headings, footnotes, citations)
- Add tests for data model creation and validation

Phase 1 (Data Model Foundation) Step 1/3 complete
Quality impact: Foundation for Phases 2-6 (+0 points now, enables +60 later)"
```

---

## Section 9: File Manifest

### Implementation Files (lib/)

**Core RAG Processing**:
- `lib/rag_processing.py` (1000+ lines): Main RAG pipeline, needs refactoring
- `lib/rag_data_models.py` (NEW): Data model classes for structured processing
- `lib/quality_verification.py` (PLANNED): Quality validation and scoring

**Metadata & Utilities**:
- `lib/metadata_generator.py` (220 lines): Metadata extraction and frontmatter
- `lib/metadata_verification.py` (NEW, 150 lines): Metadata verification
- `lib/filename_utils.py` (100 lines): Filename generation utilities

**Python Bridge** (unchanged during refactoring):
- `lib/python_bridge.py`: Node.js ↔ Python bridge

### Test Files (__tests__/python/)

**RAG Pipeline Tests**:
- `__tests__/python/test_rag_processing.py` (500+ lines): Main test suite
- `__tests__/python/test_rag_enhancements.py`: Enhancement-specific tests
- `__tests__/python/test_quality_verification.py` (PLANNED): Quality verification tests

**Metadata Tests**:
- `__tests__/python/test_metadata_generator.py`: Metadata generation tests
- `__tests__/python/test_publisher_extraction.py`: Publisher extraction tests
- `__tests__/python/test_toc_hybrid.py`: ToC extraction tests

### Documentation (docs/ and claudedocs/)

**Architectural Analysis** (claudedocs/):
- `claudedocs/architecture_analysis_rag_pipeline.md` (1680 lines): Complete architectural analysis
- `claudedocs/rag_failure_analysis.md` (150+ lines): Failure mode analysis
- `claudedocs/publisher_extraction_implementation.md`: Publisher extraction docs
- `claudedocs/RAG_ARCHITECTURE_REFACTORING_ONBOARDING.md` (THIS FILE): Onboarding guide

**Implementation Specs** (docs/):
- `docs/METADATA_VERIFICATION.md`: Metadata verification spec
- `docs/HYBRID_TOC_EXTRACTION.md`: ToC extraction design
- `docs/IMPLEMENTATION_SUMMARY_HYBRID_TOC.md`: ToC implementation summary
- `docs/CURRENT_PIPELINE_FLOW.md`: Current pipeline flow documentation

**Quality Framework** (.claude/):
- `.claude/RAG_QUALITY_FRAMEWORK.md` (1000+ lines): Quality verification framework
- `.claude/VERSION_CONTROL.md`: Git workflow and conventions
- `.claude/PATTERNS.md`: Code patterns to follow

### Configuration Files

**Python Dependencies**:
- `pyproject.toml`: UV-based Python dependencies
- `uv.lock`: Lockfile for reproducible builds

**Node.js Dependencies** (unchanged):
- `package.json`: Node dependencies
- `package-lock.json`: NPM lockfile

### Quality Reports (generated during verification)

- `test_output/quality_report.json` (generated): Quality metrics
- `processed_rag_output/*.txt` (generated): Processed RAG output files

---

## Section 10: Context Restoration Guide

### For Fresh Agent Starting Work

**Step 1: Read This Document First** (you're here!)
- Understand current state, problem, solution approach
- Review 9-week roadmap
- Identify immediate next steps

**Step 2: Check Serena Memories**
```python
# List all available memories
list_memories()

# Read relevant memories
read_memory("rag_refactoring_plan")
read_memory("phase_1_progress")
read_memory("blockers")  # Any known blockers
read_memory("decisions")  # Key architectural decisions
```

**Step 3: Review Architectural Analysis**
- Read: `claudedocs/architecture_analysis_rag_pipeline.md`
- Understand 5 architectural flaws
- Review why Architecture 3 chosen
- Study phase-by-phase implementation plan

**Step 4: Read Quality Verification Reports**
- Review: `claudedocs/rag_failure_analysis.md`
- Understand failure modes (footnotes, citations, formatting)
- Check quality metrics (41.75/100 baseline)
- Read: `.claude/RAG_QUALITY_FRAMEWORK.md` for verification approach

**Step 5: Check Recent Commits**
```bash
# View recent work
git log --oneline -10

# Check current branch
git branch --show-current

# View uncommitted changes
git status
git diff
```

**Step 6: Run Tests to Verify Current State**
```bash
# Activate virtual environment
source .venv/bin/activate  # Or: uv sync

# Run RAG pipeline tests
uv run pytest __tests__/python/test_rag_processing.py -v

# Run all tests
uv run pytest

# Check for failures
```

**Step 7: Review Code Structure**
```bash
# View RAG processing implementation
less lib/rag_processing.py

# View current data models (if Phase 1 started)
less lib/rag_data_models.py

# View metadata generation
less lib/metadata_generator.py
```

**Step 8: Understand What's Next**
- Check Phase 1 status (complete, in-progress, or not started)
- Review immediate next steps (Section 8 of this document)
- Create plan for continuing work

### Context Restoration Checklist

- [ ] Read this onboarding document (all 10 sections)
- [ ] Check Serena memories for progress/blockers
- [ ] Review architectural analysis (5 flaws, 3 solutions, 9-week plan)
- [ ] Read quality verification reports (failure modes, metrics)
- [ ] Check recent git commits and branch status
- [ ] Run test suite to verify current state
- [ ] Review key implementation files (rag_processing.py, metadata_generator.py)
- [ ] Identify which phase you're starting (Phase 1-6)
- [ ] Create implementation plan for your work session

---

## Appendix A: Quick Reference

### Quality Score Breakdown

**Current: 41.75/100**

| Issue | Impact | Priority | Fix Phase |
|-------|--------|----------|-----------|
| Orphaned footnotes (16.7%) | -25 pts | HIGH | Phase 4 |
| Bold formatting loss (100%) | -15 pts | MEDIUM | Phase 3 |
| Citation loss (8%) | -10 pts | HIGH | Phase 5 |
| Heading detection gaps | -5 pts | MEDIUM | Phase 2/6 |
| Structure issues | -3 pts | LOW | Phase 6 |

**Target: 75-85/100**

### Key Files by Phase

**Phase 1 (Data Model)**:
- NEW: `lib/rag_data_models.py`
- MODIFY: `lib/rag_processing.py`
- TEST: `__tests__/python/test_rag_processing.py`

**Phase 2 (Layout Info)**:
- MODIFY: `lib/rag_processing.py` (add `_classify_page_regions()`)
- TEST: `__tests__/python/test_rag_processing.py`

**Phase 3 (Formatting)**:
- MODIFY: `lib/rag_processing.py` (add `FormattingApplier`)
- TEST: `__tests__/python/test_rag_processing.py`

**Phase 4 (Footnotes)**:
- MODIFY: `lib/rag_processing.py` (add `FootnoteLinker`)
- TEST: `__tests__/python/test_rag_processing.py`

**Phase 5 (Validation)**:
- NEW: `lib/quality_verification.py`
- TEST: `__tests__/python/test_quality_verification.py`

**Phase 6 (Refactoring)**:
- REFACTOR: `lib/rag_processing.py` (multi-pass pipeline)
- TEST: All tests updated for new structure

### Command Cheatsheet

```bash
# Environment
source .venv/bin/activate  # Or: uv sync

# Testing
uv run pytest  # All tests
uv run pytest __tests__/python/test_rag_processing.py -v  # RAG tests only
uv run pytest -k "test_footnote" -v  # Footnote tests only

# Git
git status  # Check status
git log --oneline -10  # Recent commits
git branch --show-current  # Current branch
git diff  # View changes

# Quality Verification
uv run pytest __tests__/python/test_rag_processing.py::TestPDFQuality -v

# Serena (from Python or via MCP)
list_memories()  # List all memories
read_memory("rag_refactoring_plan")  # Read specific memory
write_memory("phase_1_status", "Step 2 complete")  # Write memory
```

### Contact Information

**Documentation Locations**:
- Architectural analysis: `claudedocs/architecture_analysis_rag_pipeline.md`
- Quality framework: `.claude/RAG_QUALITY_FRAMEWORK.md`
- Failure analysis: `claudedocs/rag_failure_analysis.md`
- Version control: `.claude/VERSION_CONTROL.md`
- Code patterns: `.claude/PATTERNS.md`

**Key Decisions**:
- Architecture choice: Architecture 3 (Incremental Refactoring)
- Timeline: 9 weeks (6 phases)
- Quality target: 75-85 (sufficient for academic use)
- Risk level: Low-medium (incremental, rollback possible)
- GPU enhancement: Phase 7 (optional, future consideration)

---

## Document Metadata

**Created**: 2025-10-14
**Author**: Claude Code (System Architect)
**Purpose**: Agent handoff for RAG pipeline refactoring
**Status**: Complete and ready for use
**Next Update**: After Phase 1 complete (update with Phase 1 outcomes)

**Version History**:
- v1.0 (2025-10-14): Initial onboarding document created

**Related Documents**:
- `claudedocs/architecture_analysis_rag_pipeline.md`: Complete architectural analysis
- `.claude/RAG_QUALITY_FRAMEWORK.md`: Quality verification framework
- `claudedocs/rag_failure_analysis.md`: Failure mode analysis

---

**Welcome, fresh agent! You now have complete context to continue the RAG pipeline architectural refactoring. Start with Phase 1 (Data Model Foundation) and work through the 9-week roadmap systematically. Good luck!** 🚀
