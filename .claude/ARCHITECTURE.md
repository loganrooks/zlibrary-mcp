# Architecture Overview

**Last Updated**: 2025-10-21 (manual sections)
**Auto-Generated Status**: 2025-10-21 18:35 UTC
**Current Phase**: Phase 2 - RAG Pipeline Quality & Robustness

---

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client (Claude)                   │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────────────┐
│              MCP Server (Node.js/TypeScript)             │
│  - Tool registration and routing (src/index.ts)          │
│  - Client communication handling                         │
└────────────────────┬────────────────────────────────────┘
                     │ PythonShell
┌────────────────────▼────────────────────────────────────┐
│              Python Bridge (lib/)                        │
│  - Z-Library API integration (python_bridge.py)          │
│  - Document processing (rag_processing.py)               │
│  - Quality pipeline (garbled detection, X-marks, OCR)    │
└────────────────────┬────────────────────────────────────┘
                     │ EAPI (web scraping)
┌────────────────────▼────────────────────────────────────┐
│         Vendored Z-Library Fork (zlibrary/)              │
│  - Custom download logic                                 │
│  - Hydra mode domain discovery                           │
└──────────────────────────────────────────────────────────┘
```

### Data Flow Patterns

**Search**: Client → MCP → Python → Z-Library API → Results
**Download**: Client → MCP → Python → zlibrary fork → File
**RAG**: File → rag_processing.py → Quality Pipeline → Extracted Markdown → File

**Critical Design**: RAG returns **file paths**, not raw text (prevents context overflow)

---

## Current Implementation Status

**[AUTO-GENERATED SECTION - Last updated: 2025-10-21 18:35 UTC]**

### MCP Tools
- ✅ Implemented: 12/12 (100%)
  - search_books, full_text_search, get_download_history
  - get_download_limits, download_book_to_file
  - process_document_for_rag, get_book_metadata
  - search_by_term, search_by_author, fetch_booklist
  - search_advanced

### RAG Pipeline (Phase 2)
- ✅ Stage 1: Statistical garbled detection (100%)
- ✅ Stage 2: Visual X-mark detection (100%)
- 🔄 Stage 3: OCR recovery (framework complete, ML recovery pending)
- ✅ Formatting preservation: Bold, italic, strikethrough (100%)
- ⏳ Stage 4-11: Designed, not implemented

### Test Coverage
- Node.js (Jest): 78% (target: 80%)
- Python (Pytest): 82% (target: 85%)
- Real PDF Tests: 2 fixtures with ground truth validation
- Integration Tests: 49/49 passing (100%)

### Performance
- X-mark detection: 5.2ms/page (budget: <10ms) ✅
- Garbled detection: 0.75ms/region (budget: <2ms) ✅
- End-to-end processing: 11s/page (budget: <15s/page) ✅

**[END AUTO-GENERATED SECTION]**

---

## Key Design Decisions (ADRs)

### ADR-001: MCP Server Architecture
**Decision**: Node.js for MCP server, Python for document processing
**Rationale**: MCP SDK is JavaScript-first, but Python has superior document libraries
**Status**: ✅ Implemented, stable
**Location**: [docs/adr/ADR-001](../docs/adr/)

### ADR-004: Python Bridge Path Resolution
**Decision**: Keep Python scripts in `lib/`, use relative path resolution from `dist/`
**Rationale**: Single source of truth, no build duplication, dev-friendly
**Status**: ✅ Implemented, validated
**Location**: [docs/adr/ADR-004-Python-Bridge-Path-Resolution.md](../docs/adr/ADR-004-Python-Bridge-Path-Resolution.md)

### ADR-005: UV-Based Virtual Environment (v2.0.0)
**Decision**: Migrate from manual venv to UV for dependency management
**Rationale**: 2025 best practice, portable, reproducible, simplified codebase (77% reduction)
**Status**: ✅ Implemented
**Location**: [docs/MIGRATION_V2.md](../docs/MIGRATION_V2.md)

### ADR-006: Quality Pipeline Architecture
**Decision**: Sequential waterfall pipeline (Statistical → Visual → OCR)
**Rationale**: Each stage informs next, avoid false positives, preserve philosophical content
**Status**: ✅ Implemented (Stages 1-3)
**Location**: [docs/adr/ADR-006-Quality-Pipeline-Architecture.md](../docs/adr/ADR-006-Quality-Pipeline-Architecture.md)

### ADR-008: Stage 2 Independence Correction
**Decision**: X-mark detection runs independently (not conditional on garbled detection)
**Rationale**: Sous-rature PDFs have clean text with visual X-marks
**Status**: ✅ Critical architectural fix
**Location**: [docs/adr/ADR-008-Stage-2-Independence-Correction.md](../docs/adr/ADR-008-Stage-2-Independence-Correction.md)

---

## Module Structure

### Core Modules (lib/)

| Module | Responsibility | Status | Lines | Tests |
|--------|---------------|--------|-------|-------|
| `rag_processing.py` | PDF/EPUB/TXT extraction, quality pipeline | ✅ Active | ~2900 | 49 |
| `rag_data_models.py` | TextSpan, PageRegion data models | ✅ Stable | ~570 | 15 |
| `garbled_text_detection.py` | Statistical quality analysis (Stage 1) | ✅ Complete | ~280 | 12 |
| `strikethrough_detection.py` | X-mark visual detection (Stage 2) | ✅ Complete | ~530 | 14 |
| `formatting_group_merger.py` | Span grouping for markdown | ✅ Complete | ~367 | 40 |
| `marginalia_extraction.py` | Margin note detection (Stage 4) | 🔄 Designed | ~200 | 0 |
| `python_bridge.py` | Z-Library API operations | ✅ Stable | ~450 | 12 |

### Support Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `metadata_generator.py` | YAML frontmatter generation | ✅ Complete |
| `metadata_verification.py` | Extract and verify metadata | ✅ Complete |
| `filename_utils.py` | Unified filename creation | ✅ Complete |
| `quality_verification.py` | Quality checks and reporting | ✅ Complete |

---

## Technology Stack

**Runtime**:
- Node.js 18+ (MCP server)
- Python 3.9-3.13 (bridge and processing)
- UV (Python dependency management - 2025 best practice)

**Key Dependencies**:
- `@modelcontextprotocol/sdk` - MCP protocol
- `python-shell` - Node↔Python bridge
- `ebooklib` - EPUB processing
- `PyMuPDF` (fitz) - PDF extraction
- `opencv-python` - Visual X-mark detection
- `pytesseract` - OCR (optional)

**Development**:
- TypeScript, Jest (Node.js testing)
- Pytest, pytest-mock (Python testing)
- UV (dependency management)

---

## RAG Pipeline Architecture (Detailed)

### Quality Pipeline (Phase 2)

```
PDF Page
  ↓
  ├─ Stage 1: Statistical Detection
  │   ├─ Entropy analysis
  │   ├─ Symbol density
  │   ├─ Repeated character patterns
  │   └─ Output: quality_flags {'garbled', 'low_entropy', ...}
  │
  ├─ Stage 2: Visual X-Mark Detection (INDEPENDENT)
  │   ├─ OpenCV LSD line detection
  │   ├─ Diagonal line pairing (±15° from 45°)
  │   ├─ Crossing validation (proximity <20px)
  │   └─ Output: quality_flags {'sous_rature', 'strikethrough'}
  │
  └─ Stage 3: OCR Recovery
      ├─ Path A: Sous-rature (has X-marks)
      │   ├─ OCR page at 300 DPI
      │   ├─ Context-based word matching
      │   └─ Apply strikethrough formatting
      │
      └─ Path B: Corruption (garbled, no X-marks)
          ├─ OCR corrupted region
          └─ Replace with recovered text
  ↓
PageRegion with quality_flags + formatted spans
  ↓
Formatting Group Merger
  ├─ Group consecutive spans by formatting
  ├─ Apply markdown (*italic*, **bold**, ~~strikethrough~~)
  └─ Prevent malformed output
  ↓
Markdown Output (file, not memory)
```

### Performance Optimization

**Fast Pre-Filter** (31× speedup):
- Symbol density check (0.01ms/page)
- Only run expensive X-mark detection (5ms) on flagged pages
- Result: 40× combined speedup with caching

**Parallel Detection**:
- ProcessPoolExecutor with 4 workers
- Page-level caching (detect once per page)
- 4× speedup on multi-page documents

---

## Data Models (lib/rag_data_models.py)

### Core Classes

**TextSpan** - Formatted text fragment
```python
@dataclass
class TextSpan:
    text: str
    formatting: Set[str]  # {'bold', 'italic', 'strikethrough', 'sous-erasure'}
    font_size: float
    font_name: str
    bbox: tuple[float, float, float, float]
```

**PageRegion** - Semantic block
```python
@dataclass
class PageRegion:
    region_type: str  # 'header', 'body', 'footer', 'margin', 'footnote'
    spans: List[TextSpan]
    heading_level: Optional[int]
    list_info: Optional[ListInfo]
    quality_flags: Optional[Set[str]]  # {'garbled', 'sous_rature', ...}
    quality_score: Optional[float]  # 0.0-1.0
```

---

## Directory Structure

```
/home/rookslog/mcp-servers/zlibrary-mcp/
├── src/                          # Node.js MCP server
│   ├── index.ts                  # Entry point (tool registration)
│   └── lib/                      # Server utilities
│
├── lib/                          # Python source (NOT in dist/)
│   ├── python_bridge.py          # Z-Library API operations
│   ├── rag_processing.py         # Document extraction + quality
│   ├── rag_data_models.py        # Data structures
│   ├── garbled_text_detection.py # Stage 1
│   ├── strikethrough_detection.py # Stage 2
│   └── formatting_group_merger.py # Markdown generation
│
├── zlibrary/                     # Vendored fork (editable install)
│   └── zlibrary/                 # Modified package
│
├── __tests__/                    # Test suites
│   ├── *.test.js                 # Node.js (Jest, ESM)
│   └── python/                   # Python (Pytest)
│       ├── test_quality_pipeline_integration.py (26 tests)
│       ├── test_formatting_group_merger.py (40 tests)
│       ├── test_real_world_validation.py (9 tests)
│       └── ...
│
├── test_files/                   # Real PDFs for TDD
│   ├── ground_truth/             # Expected outputs (JSON)
│   │   ├── schema.json
│   │   ├── derrida_of_grammatology.json
│   │   └── heidegger_being_time.json
│   ├── performance_budgets.json
│   └── *.pdf                     # Test fixtures
│
├── .claude/                      # Development guides
│   ├── ROADMAP.md               # Strategic plan (THIS FILE's sibling)
│   ├── ARCHITECTURE.md          # System overview (THIS FILE)
│   ├── PROJECT_CONTEXT.md       # Mission, principles, domain model
│   ├── PATTERNS.md              # Code patterns
│   ├── TDD_WORKFLOW.md          # Real-world TDD process
│   └── ...
│
├── docs/                         # Formal documentation
│   ├── adr/                      # Architecture decisions
│   ├── specifications/           # Technical specs
│   └── ...
│
└── claudedocs/                   # Session reports, research
    ├── session-notes/            # Timestamped summaries
    ├── research/                 # Topic-specific investigations
    ├── architecture/             # Analysis documents
    ├── phase-reports/            # Phase milestones
    └── archive/                  # Historical docs (>30 days)
```

---

## Key Architectural Patterns

### 1. File-Based RAG (Not Memory)
**Pattern**: Return file paths, not raw text
**Rationale**: Prevents AI context overflow on large documents
**Implementation**: `rag_processing.py` writes to `processed_rag_output/`, returns path

### 2. Quality Pipeline (Sequential Waterfall)
**Pattern**: Statistical → Visual → OCR (each stage informs next)
**Rationale**: Avoid false positives, preserve intentional deletions (sous-rature)
**Implementation**: Stages 1-3 in `rag_processing.py:_apply_quality_pipeline()`

### 3. Dual-Language Bridge
**Pattern**: Node.js MCP layer, Python processing layer
**Rationale**: Leverage best tools for each domain
**Implementation**: PythonShell communication, UV-managed venv

### 4. Ground Truth Validation
**Pattern**: Real PDFs with documented expected outputs
**Rationale**: Prevent hallucinations, catch architectural errors early
**Implementation**: `test_files/ground_truth/*.json`, TDD workflow

### 5. Span Grouping for Formatting
**Pattern**: Group consecutive spans with identical formatting before applying markdown
**Rationale**: PyMuPDF creates per-word spans; naive formatting creates malformed output
**Implementation**: `formatting_group_merger.py` (40 tests, 100% passing)

---

## Performance Architecture

### Budgets (Hard Constraints)

Defined in: `test_files/performance_budgets.json`

| Operation | Budget | Current | Status |
|-----------|--------|---------|--------|
| X-mark detection (per page) | <10ms | 5.2ms | ✅ Under budget |
| Garbled detection (per region) | <2ms | 0.75ms | ✅ Under budget |
| Search latency (p95) | <2s | ~1.2s | ✅ Under budget |
| Download (<10MB book) | <10s | ~6s | ✅ Under budget |
| RAG processing (per page) | <15s | ~11s | ✅ Under budget |

### Optimization Strategies

1. **Page-Level Caching**: Detect X-marks once per page, reuse for all blocks (10× speedup)
2. **Parallel Detection**: ProcessPoolExecutor, 4 workers (4× speedup)
3. **Fast Pre-Filter**: Symbol density check before expensive detection (31× speedup on X-marks)
4. **Combined Effect**: 40× speedup on quality pipeline

---

## Security Architecture

### Credential Management
- ✅ Environment variables only (ZLIBRARY_EMAIL, ZLIBRARY_PASSWORD)
- ✅ Never committed to git (.env in .gitignore)
- ✅ No hardcoded credentials

### Sandboxing
- ✅ Python bridge runs in isolated venv (.venv/)
- ✅ Download directory configurable (default: ./downloads/)
- ✅ No arbitrary code execution

### Error Handling
- ✅ Circuit breaker pattern for API failures
- ✅ Retry logic with exponential backoff
- ✅ Graceful degradation (OCR optional)

---

## Testing Architecture

### Test Pyramid

```
       /\
      /E2E\          Integration Tests (12)
     /------\        - Real Z-Library API calls
    /  INT  \        - Network-dependent
   /----------\
  / UNIT TESTS \     Unit Tests (477)
 /--------------\    - Mocked dependencies
/________________\   - Fast, reliable
```

### TDD Workflow (Phase 2+)

**Pattern**: Ground Truth → Failing Test → Implementation → Validation

1. Acquire **real PDF** with feature (e.g., sous-rature)
2. Create **ground truth** JSON with expected outputs
3. Write **failing test** using real PDF (NO MOCKS)
4. Implement until test passes
5. **Manual verification**: Side-by-side PDF vs output review
6. **Performance validation**: Check against budgets

**Location**: `.claude/TDD_WORKFLOW.md`

---

## Component Responsibilities

| Component | Responsibility | Technology | Status |
|-----------|---------------|------------|--------|
| MCP Server | Tool routing, client comm | Node.js/TypeScript | ✅ Stable |
| Python Bridge | Z-Library API, document processing | Python 3.9+ | ✅ Stable |
| zlibrary Fork | Download logic, domain discovery | Python (vendored) | ✅ Stable |
| RAG Pipeline | Extraction + quality analysis | Python | 🔄 Phase 2 |
| Quality Stage 1 | Garbled detection (statistical) | Python | ✅ Complete |
| Quality Stage 2 | X-mark detection (visual) | Python + OpenCV | ✅ Complete |
| Quality Stage 3 | OCR recovery | Python + Tesseract | 🔄 Framework |
| Formatting Merger | Span grouping, markdown generation | Python | ✅ Complete |
| Virtual Env | Dependency isolation | UV | ✅ Complete |

---

## Future Architecture

### Planned Enhancements (Backlog)

**Stage 4-11** (Designed, Not Implemented):
- Stage 4: Marginalia extraction
- Stage 5: Citation extraction and linking
- Stage 6: Footnote/endnote detection and matching
- Stage 7: Hierarchical heading detection
- Stage 8: List structure preservation
- Stage 9: Table extraction
- Stage 10: Image/figure handling
- Stage 11: Cross-reference resolution

**Performance**:
- Adaptive resolution (72→150→300 DPI escalation)
- Metadata-based corpus filtering (skip non-philosophy docs)
- Caching layer for search results

**ML Integration**:
- Image inpainting for sous-rature text recovery
- NLP-based word prediction from context
- Ensemble approach with confidence scoring

---

## Technical Debt

**Active Debt** (prioritized):
1. **OCR text recovery**: Needs ML models (2-4 week research)
2. **Circuit breaker refinement**: Add per-endpoint configuration
3. **Caching layer**: Search results and metadata caching
4. **Fuzzy search**: Implementation pending

**See**: [ISSUES.md](../ISSUES.md) for complete tracking

---

## Integration Points

### MCP Protocol
- Standard tool call/response pattern
- JSON-RPC 2.0 communication
- Streaming support for long operations

### Z-Library EAPI
- Web scraping (BeautifulSoup)
- Hydra mode domain discovery
- Rate limiting and retry logic

### Document Libraries
- ebooklib (EPUB)
- PyMuPDF (PDF)
- pytesseract (OCR, optional)
- opencv-python (image analysis)

---

## Monitoring & Observability

**Logging**:
- Structured logging throughout
- Log levels: DEBUG (development), INFO (production)
- Performance metrics logged per operation

**Quality Gates**:
- Pre-commit: Real PDF tests + performance validation
- CI/CD: Full test suite + coverage reports
- Manual: Side-by-side PDF verification

---

## Quick Reference

- **Add New ADR**: See [docs/adr/README.md](../docs/adr/README.md)
- **Update This File**: Edit manual sections, run `update_architecture_status.sh` for auto sections
- **Session State**: Use `/sc:load` and `/sc:save` with Serena memory
- **Roadmap**: See [ROADMAP.md](ROADMAP.md) for strategic plan

---

**Navigation**:
- ← [ROADMAP.md](ROADMAP.md) - Strategic planning
- → [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) - Mission and domain model
- ↓ [PATTERNS.md](PATTERNS.md) - Code patterns to follow
