# Technical Specifications Catalog

**Purpose**: Index of all technical specifications for Z-Library MCP server
**Status**: 7 active specifications (19-36KB each)
**Last Updated**: 2025-10-21

---

## Quick Reference by Status

### ✅ Implemented and Active
- [PHASE_2_INTEGRATION_SPECIFICATION.md](#phase-2-integration-specification) - Phase 2 quality pipeline (Oct 2025)
- [RIGOROUS_REAL_WORLD_TDD_STRATEGY.md](#rigorous-real-world-tdd-strategy) - TDD testing framework

### 🔄 Partially Implemented
- [ARTICLE_SUPPORT_AND_CITATION_ARCHITECTURE.md](#article-support-and-citation-architecture) - Citation systems (planned)
- [SELECTIVE_OCR_STRATEGY.md](#selective-ocr-strategy) - OCR recovery (core implemented, refinements pending)
- [SOUS_RATURE_RECOVERY_STRATEGY.md](#sous-rature-recovery-strategy) - Strikethrough handling (core implemented)

### 📋 Planned / In Design
- [FAST_PREFILTER_ARCHITECTURE_FINAL.md](#fast-prefilter-architecture) - Performance optimization (design complete)
- [PERFORMANCE_OPTIMIZATION_CLEVER_ENGINEERING.md](#performance-optimization-clever-engineering) - Advanced optimizations (design phase)

---

## All Specifications (Alphabetical)

### Article Support and Citation Architecture
**File**: [ARTICLE_SUPPORT_AND_CITATION_ARCHITECTURE.md](ARTICLE_SUPPORT_AND_CITATION_ARCHITECTURE.md)
**Size**: 36KB (largest specification)
**Status**: 📋 Planned
**Created**: 2025-10-14

**Scope**: Comprehensive architecture for detecting and preserving academic citation systems

**Key Features**:
- Citation system detection (footnotes, endnotes, in-text)
- Reference linking and extraction
- Bibliography parsing
- Support for multiple citation styles (Chicago, MLA, APA, Harvard)

**Dependencies**:
- Builds on Phase 2 quality pipeline
- Requires enhanced metadata extraction
- Integrates with RAG data models

**Implementation Status**:
- [ ] Citation system detection
- [ ] Footnote/endnote linking
- [ ] Bibliography extraction
- [ ] Multi-style support

**Related**:
- Data Model: `lib/rag_data_models.py::NoteInfo`
- ADR: (pending - ADR-009 candidate)
- See also: [docs/CITATION_INFERENCE_ARCHITECTURE.md](../CITATION_INFERENCE_ARCHITECTURE.md)

---

### Fast Prefilter Architecture
**File**: [FAST_PREFILTER_ARCHITECTURE_FINAL.md](FAST_PREFILTER_ARCHITECTURE_FINAL.md)
**Size**: 16KB
**Status**: 📋 Design Complete, Implementation Pending
**Created**: 2025-10-18

**Scope**: High-speed prefiltering for X-mark (sous-rature) detection in PDFs

**Key Features**:
- Sub-millisecond text-based prefilter (<0.5ms target)
- Eliminates 95%+ of non-candidate blocks before expensive CV analysis
- Unicode character detection (×, x, X patterns)
- Regex pattern matching for strikethrough indicators

**Performance Targets**:
- Prefilter: <0.5ms per page
- Overall pipeline: <100ms per page (including CV when needed)
- False negative rate: <1% (never miss real sous-rature)

**Implementation Status**:
- [x] Specification complete
- [x] Performance budgets defined
- [ ] Implementation in `lib/strikethrough_detection.py`
- [ ] Integration with visual analysis pipeline
- [ ] Performance validation

**Related**:
- [ADR-006](../adr/ADR-006-Quality-Pipeline-Architecture.md) - Quality pipeline architecture
- [SOUS_RATURE_RECOVERY_STRATEGY.md](#sous-rature-recovery-strategy) - Visual detection strategy
- Performance Budget: `test_files/performance_budgets.json`

---

### Performance Optimization Clever Engineering
**File**: [PERFORMANCE_OPTIMIZATION_CLEVER_ENGINEERING.md](PERFORMANCE_OPTIMIZATION_CLEVER_ENGINEERING.md)
**Size**: 20KB
**Status**: 📋 Design Phase
**Created**: 2025-10-18

**Scope**: Advanced performance optimization strategies for RAG pipeline

**Key Strategies**:
- Lazy loading and on-demand processing
- Intelligent caching (multi-level)
- Parallel processing where safe
- Memory-efficient streaming
- Incremental processing for large PDFs

**Performance Targets**:
- 10x reduction in memory footprint (large PDFs)
- 3x speedup for multi-page processing
- <100ms overhead for quality pipeline stages

**Implementation Status**:
- [x] Profiling and bottleneck identification
- [x] Optimization strategy design
- [ ] Implementation roadmap
- [ ] Benchmarking framework
- [ ] Production rollout

**Related**:
- [FAST_PREFILTER_ARCHITECTURE_FINAL.md](#fast-prefilter-architecture) - Prefilter optimization
- Performance Budget: `test_files/performance_budgets.json`

---

### Phase 2 Integration Specification
**File**: [PHASE_2_INTEGRATION_SPECIFICATION.md](PHASE_2_INTEGRATION_SPECIFICATION.md)
**Size**: 19KB
**Status**: ✅ Implemented (Oct 2025)
**Created**: 2025-10-17

**Scope**: Integration of quality pipeline (Statistical → Visual → OCR) into RAG processing

**Key Features**:
- Three-stage quality pipeline integration
- Feature flags for backward compatibility
- Performance budgets and validation
- Real-world testing with philosophical texts

**Implementation Status**:
- [x] Stage 1: Statistical garbled detection
- [x] Stage 2: Visual analysis (X-marks, strikethrough)
- [x] Stage 3: OCR recovery (Tesseract)
- [x] Integration into `process_pdf()`
- [x] Performance validation (<100ms)
- [x] Real-world testing (Derrida, Heidegger PDFs)

**Completion**: 2025-10-19

**Related**:
- [ADR-006](../adr/ADR-006-Quality-Pipeline-Architecture.md) - Pipeline architecture
- [ADR-007](../adr/ADR-007-Phase-2-Integration-Complete.md) - Integration completion record
- [ADR-008](../adr/ADR-008-Stage-2-Independence-Correction.md) - Stage 2 correction
- Implementation: `lib/rag_processing.py`, `lib/garbled_text_detection.py`, `lib/strikethrough_detection.py`
- Status Report: [claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md](../../claudedocs/PHASE_2_INTEGRATION_COMPLETE_2025_10_18.md)

---

### Rigorous Real-World TDD Strategy
**File**: [RIGOROUS_REAL_WORLD_TDD_STRATEGY.md](RIGOROUS_REAL_WORLD_TDD_STRATEGY.md)
**Size**: 26KB
**Status**: ✅ Implemented and Active
**Created**: 2025-10-18

**Scope**: Test-driven development methodology for RAG pipeline using real PDFs (no mocks)

**Key Principles**:
1. **Real PDFs Only** - No mocked data, use actual test fixtures
2. **Ground Truth Validation** - Manual verification required
3. **No Regressions** - All tests must pass before commit
4. **Performance Budgets** - Enforced via `performance_budgets.json`

**Test Infrastructure**:
- Test PDFs: `test_files/` (Derrida, Heidegger, synthetic tests)
- Ground Truth: `test_files/ground_truth/` (manual verification)
- Performance Budgets: `test_files/performance_budgets.json`
- Pre-commit Hooks: Automated real PDF testing

**Implementation Status**:
- [x] TDD workflow defined
- [x] Real PDF test fixtures
- [x] Ground truth creation process
- [x] Performance budget framework
- [x] Pre-commit hook integration
- [x] Active use in development

**Related**:
- [.claude/TDD_WORKFLOW.md](../../.claude/TDD_WORKFLOW.md) - Workflow guide
- [.claude/RAG_QUALITY_FRAMEWORK.md](../../.claude/RAG_QUALITY_FRAMEWORK.md) - Quality framework
- [docs/TESTING_LESSONS_LEARNED.md](../TESTING_LESSONS_LEARNED.md) - Testing insights
- Test Infrastructure: `__tests__/python/`, `test_files/`

---

### Selective OCR Strategy
**File**: [SELECTIVE_OCR_STRATEGY.md](SELECTIVE_OCR_STRATEGY.md)
**Size**: 21KB
**Status**: 🔄 Core Implemented, Refinements Pending
**Created**: 2025-10-17

**Scope**: Intelligent OCR recovery for garbled text blocks using Tesseract

**Key Features**:
- Confidence-based OCR triggering (>0.8 threshold)
- Selective re-processing (block-level, not whole PDF)
- Tesseract integration with PyMuPDF
- Fallback strategies for low-confidence results

**Decision Logic**:
```
IF garbled detected AND no visual markers (X-marks)
  → Assess OCR confidence
    IF confidence > 0.8
      → Attempt Tesseract re-processing
      → IF success → Replace text, flag 'recovered'
      → IF failure → Keep original, flag 'unrecoverable'
    ELSE
      → Keep original, flag 'low_confidence'
```

**Implementation Status**:
- [x] OCR quality assessment
- [x] Tesseract integration
- [x] Block-level selective OCR
- [ ] Advanced confidence scoring
- [ ] Multi-language OCR support
- [ ] OCR preprocessing optimizations

**Related**:
- [ADR-006](../adr/ADR-006-Quality-Pipeline-Architecture.md) - Quality pipeline (Stage 3)
- [PHASE_2_INTEGRATION_SPECIFICATION.md](#phase-2-integration-specification) - Integration
- Implementation: `lib/rag_processing.py::assess_pdf_ocr_quality()`, `lib/rag_processing.py::redo_ocr_with_tesseract()`

---

### Sous-Rature Recovery Strategy
**File**: [SOUS_RATURE_RECOVERY_STRATEGY.md](SOUS_RATURE_RECOVERY_STRATEGY.md)
**Size**: 17KB
**Status**: 🔄 Core Implemented, Enhancements Pending
**Created**: 2025-10-14

**Scope**: Detection and preservation of philosophical strikethrough text (sous-rature/under erasure)

**Key Features**:
- X-mark detection (×, x, X Unicode characters)
- Visual strikethrough analysis (PyMuPDF flags)
- Preservation of intentional deletions (philosophical content)
- Distinction from OCR failures

**Detection Methods**:
1. **Text-based**: Unicode character analysis (× presence)
2. **Visual**: PyMuPDF formatting flags (strikethrough bit)
3. **Computer Vision**: Line detection algorithms (future enhancement)

**Implementation Status**:
- [x] X-mark text detection
- [x] PyMuPDF formatting flag analysis
- [x] Integration with quality pipeline (Stage 2)
- [x] Real-world validation (Derrida's *Of Grammatology*)
- [ ] Computer vision enhancements
- [ ] Multi-language support (non-ASCII X-marks)

**Critical Insight**: Visual markers (X-marks) take precedence over statistical garbled detection to preserve philosophical content.

**Related**:
- [ADR-006](../adr/ADR-006-Quality-Pipeline-Architecture.md) - Quality pipeline (Stage 2)
- [ADR-008](../adr/ADR-008-Stage-2-Independence-Correction.md) - Stage 2 independence
- Implementation: `lib/strikethrough_detection.py`, `scripts/validation/xmark_detector.py`
- Research: [claudedocs/strikethrough-research/](../../claudedocs/strikethrough-research/)
- Validation Report: [claudedocs/SOUS_RATURE_DETECTION_VALIDATION_2025_10_20.md](../../claudedocs/SOUS_RATURE_DETECTION_VALIDATION_2025_10_20.md)

---

## Specification Status Definitions

| Status | Meaning | Next Steps |
|--------|---------|------------|
| ✅ Implemented | Specification fully implemented and active | Maintenance, enhancements |
| 🔄 Partial | Core features implemented, refinements pending | Complete remaining features |
| 📋 Planned | Design complete, implementation pending | Create implementation roadmap |
| 🟡 Draft | Under development, not finalized | Review and finalize |

---

## Dependencies Between Specifications

```
RIGOROUS_REAL_WORLD_TDD_STRATEGY (testing framework)
  ↓ enables
PHASE_2_INTEGRATION_SPECIFICATION (quality pipeline)
  ↓ implements
  ├─ SELECTIVE_OCR_STRATEGY (Stage 3)
  ├─ SOUS_RATURE_RECOVERY_STRATEGY (Stage 2)
  └─ FAST_PREFILTER_ARCHITECTURE (Stage 2 optimization)
  ↓ foundation for
  ├─ ARTICLE_SUPPORT_AND_CITATION_ARCHITECTURE (future)
  └─ PERFORMANCE_OPTIMIZATION_CLEVER_ENGINEERING (ongoing)
```

---

## Implementation Roadmap

### Phase 2 (Complete) ✅
- [x] Statistical garbled detection
- [x] Visual analysis (X-marks, strikethrough)
- [x] OCR recovery (Tesseract)
- [x] Integration and validation

### Phase 3 (In Progress) 🔄
- [x] Formatting group merger (Oct 2025)
- [ ] Fast prefilter implementation
- [ ] Performance optimization rollout
- [ ] Advanced OCR confidence scoring

### Phase 4 (Planned) 📋
- [ ] Citation architecture implementation
- [ ] Article support
- [ ] Multi-language enhancements
- [ ] Computer vision strikethrough detection

---

## How to Use Specifications

### For Implementation
1. Read specification thoroughly
2. Review related ADRs for decision rationale
3. Check implementation status in this catalog
4. Follow TDD workflow ([RIGOROUS_REAL_WORLD_TDD_STRATEGY.md](RIGOROUS_REAL_WORLD_TDD_STRATEGY.md))
5. Validate against performance budgets

### For Architecture Review
1. Understand specification scope and goals
2. Review dependencies with other specs
3. Check ADRs for architectural decisions
4. Assess impact on existing systems

### For Testing
1. Identify test fixtures needed (real PDFs)
2. Create ground truth validation
3. Define performance budgets
4. Follow TDD workflow
5. Ensure no regressions

---

## Related Documentation

**Architecture Decisions**:
- [docs/adr/README.md](../adr/README.md) - All ADRs indexed
- [docs/adr/ADR-006](../adr/ADR-006-Quality-Pipeline-Architecture.md) - Quality pipeline architecture
- [docs/adr/ADR-007](../adr/ADR-007-Phase-2-Integration-Complete.md) - Phase 2 completion

**Development Guides**:
- [.claude/TDD_WORKFLOW.md](../../.claude/TDD_WORKFLOW.md) - Test-driven development workflow
- [.claude/RAG_QUALITY_FRAMEWORK.md](../../.claude/RAG_QUALITY_FRAMEWORK.md) - Quality verification
- [.claude/PATTERNS.md](../../.claude/PATTERNS.md) - Code patterns

**Project Context**:
- [.claude/PROJECT_CONTEXT.md](../../.claude/PROJECT_CONTEXT.md) - Mission and architecture principles
- [DOCUMENTATION_MAP.md](../../DOCUMENTATION_MAP.md) - Complete documentation index

---

**Metadata**:
- Created: 2025-10-21
- Last Updated: 2025-10-21
- Total Specifications: 7
- Implemented: 2 fully, 3 partially
- Planned: 2
- Maintained by: Project contributors
