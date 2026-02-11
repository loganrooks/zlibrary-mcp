# Architecture Patterns

**Domain:** MCP Server with Dual-Language RAG Pipeline (v1.2 Production Readiness)
**Researched:** 2026-02-11
**Confidence:** HIGH (based on deep analysis of existing codebase, not external sources)

## Current Architecture Overview

The Z-Library MCP server is a dual-language system:

```
MCP Client (AI Assistant)
    |
    v  (JSON-RPC over stdio)
Node.js/TypeScript MCP Server  [src/index.ts]
    |
    v  (spawn + JSON over stdout/stderr)
Python Bridge  [lib/python_bridge.py]
    |
    +---> Z-Library EAPI  [zlibrary/ vendored fork]
    +---> RAG Pipeline    [lib/rag/ decomposed modules]
    +---> Multi-Source     [lib/sources/ adapters]
```

### Component Inventory (Current State)

| Layer | Location | Files | Purpose |
|-------|----------|-------|---------|
| MCP Server | `src/index.ts` | 1 | Tool registration, schema validation, stdio transport |
| TS Bridge | `src/lib/python-bridge.ts` | 1 | Spawns Python, JSON serialization |
| TS Utilities | `src/lib/*.ts` | 5 | paths, venv-manager, retry, circuit-breaker, errors |
| TS API Layer | `src/lib/zlibrary-api.ts` | 1 | Maps tool calls to Python bridge calls |
| Python Bridge | `lib/python_bridge.py` | 1 | Dispatches function calls, JSON IO |
| RAG Facade | `lib/rag_processing.py` | 1 (201 lines) | Backward-compatible re-export module |
| RAG Pipeline | `lib/rag/` | 31 modules | Detection, quality, OCR, resolution, pipeline |
| Sources | `lib/sources/` | 6 modules | Anna's Archive, LibGen, routing |
| Top-level Lib | `lib/*.py` | ~15 modules | Tools, metadata, quality, detection |
| Vendored Dep | `zlibrary/` | fork | Z-Library EAPI client |

### Data Flow: RAG Processing

```
download_book_to_file (MCP tool)
  -> zlibraryApi.downloadBookToFile()
    -> callPythonFunction("download_book_to_file", args)
      -> python_bridge.py dispatch
        -> EAPI download to ./downloads/
        -> process_document() [lib/rag/orchestrator.py]
          -> process_pdf_structured() [lib/rag/orchestrator_pdf.py]
            -> run_document_pipeline() [lib/rag/pipeline/runner.py]
              Phase 1: Document-level detectors (TOC, page numbers, front matter)
              Phase 2: Page-level detectors (footnotes, margins, headings)
              Phase 3: Compositor resolves conflicts
              Phase 4: Writer builds DocumentOutput
            -> DocumentOutput.write_files()
              -> body.md
              -> body_footnotes.md (if present)
              -> body_meta.json
          -> save_processed_text() with metadata sidecar
```

### Build/Runtime Path Strategy

```
Source:  src/**/*.ts  --tsc-->  dist/**/*.js
         lib/**/*.py  (NOT copied, stays in source)

Runtime: dist/lib/python-bridge.js
           path.resolve(__dirname, '..', '..', 'lib', 'python_bridge.py')
           = project_root/lib/python_bridge.py
```

This is a critical architectural invariant: Python scripts are NEVER in dist/. The postbuild step (`scripts/validate-python-bridge.js`) validates this.

---

## v1.2 Integration Analysis

### Feature 1: Test Reorganization

**Current State (Problems):**
- Jest tests: `__tests__/*.test.js` (flat, 8 files)
- Jest integration: `__tests__/integration/` (4 files + fixtures)
- Jest E2E: `__tests__/e2e/` (1 Docker test)
- Pytest tests: `__tests__/python/` (35+ test files, flat)
- Pytest fixtures: `__tests__/python/fixtures/rag_robustness/`
- Ground truth: `test_files/ground_truth/` (3 schema versions: v1, v2, v3)
- Test PDFs: `test_files/*.pdf` (real PDFs at root of test_files)
- Additional test data: `test_data/` (2 files, separate from test_files)
- Stale debug scripts at root: 7 `debug_*.py` files, 2 `test_*.py` files

**Proposed Structure:**

```
__tests__/
  node/                          # Renamed from root-level .test.js files
    unit/
      circuit-breaker.test.js
      paths.test.js
      retry-manager.test.js
      venv-manager.test.js
    integration/
      bridge-tools.test.js
      mcp-protocol.test.js
      python-bridge-integration.test.js
      brk-001-reproduction.test.js
      fixtures/                  # Existing recorded responses stay here
    e2e/
      docker-mcp-e2e.test.js
  python/
    unit/                        # Pure logic tests (no real PDFs)
      test_garbled_text_detection.py
      test_filename_utils.py
      test_rag_data_models.py
      test_note_classification.py
      ...
    integration/                 # Tests using real PDFs
      test_pipeline_integration.py
      test_real_footnotes.py
      test_real_world_validation.py
      test_real_zlibrary.py
      ...
    performance/                 # Benchmarks and perf tests
      test_garbled_performance.py
      test_performance_footnote_features.py
    fixtures/                    # Test fixtures (existing + consolidated)
      rag_robustness/
      recorded_responses/
  ground_truth/                  # UNIFIED - moved from test_files/ground_truth/
    schema.json                  # Single canonical schema (v3, retired v1/v2)
    corpora/                     # Per-book ground truth data
      derrida_footnotes.json
      heidegger_being_time.json
      kant_footnotes.json
      ...
    baseline_texts/              # Expected output baselines
    pdfs/                        # Test PDFs (consolidated from test_files/ + test_data/)
```

**Integration Points (files that change):**
- `jest.config.js`: Update `testMatch` patterns for new `__tests__/node/` structure
- `pytest.ini`: Update `testpaths` and possibly add `markers` for unit/integration/performance
- `.github/workflows/ci.yml`: No change (already runs `jest` and `pytest` at root level)
- `conftest.py`: Update project root path computation (stays the same since we use `os.path`)
- Individual test files: Update `import` paths for fixtures when moved from `test_files/` to `__tests__/ground_truth/`

**Structural Impact:** MEDIUM. ~45 file moves, config changes to jest.config.js and pytest.ini. No source code changes in `lib/` or `src/`. Tests themselves need minor fixture path updates.

**Dependency on other features:** None. Can be done first as foundation.

### Feature 2: Structured RAG Output

**Current State:**
- `DocumentOutput` dataclass in `lib/rag/pipeline/models.py` already has: `body_text`, `footnotes`, `endnotes`, `citations`, `document_metadata`, `processing_metadata`
- `DocumentOutput.write_files()` already writes: `{stem}.md` (body), `{stem}_footnotes.md`, `{stem}_endnotes.md`, `{stem}_citations.md`, `{stem}_meta.json`
- `save_processed_text()` in `lib/rag/orchestrator.py` calls `doc_output.write_files()` and also writes its own metadata sidecar via `metadata_generator.py`
- Result: DUPLICATE metadata files. `DocumentOutput.write_files()` writes `{stem}_meta.json` and `save_processed_text()` writes a separate `{stem}_meta.json` via `metadata_generator.py`. These two have DIFFERENT schemas.

**Problem: Two Metadata Systems**

1. **Pipeline metadata** (`lib/rag/pipeline/writer.py::format_metadata_sidecar`):
   ```json
   {
     "title": "",
     "toc": {...},
     "front_matter": {...},
     "page_count": N,
     "processing": {"total_blocks": N, "classifications": [...]}
   }
   ```

2. **Orchestrator metadata** (`lib/metadata_generator.py::generate_metadata_sidecar`):
   ```json
   {
     "document_type": "book",
     "source": {"zlibrary_id": ..., "original_filename": ..., "format": ...},
     "frontmatter": {"title": ..., "author": ..., "publisher": ..., ...},
     "toc": [...],
     "page_line_mapping": {...},
     "processing": {"date": ..., "word_count": ..., "page_count": ...},
     "verification": {...}
   }
   ```

**Proposed Architecture:**

Merge the two metadata systems into a single, comprehensive metadata sidecar:

```
processed_rag_output/
  author_title_id.pdf.processed.md       # Body text (clean for RAG)
  author_title_id.pdf.footnotes.md       # Footnotes by page
  author_title_id.pdf.endnotes.md        # Endnotes (if present)
  author_title_id.pdf.citations.md       # Citations (if present)
  author_title_id.pdf.meta.json          # SINGLE unified metadata
```

**Unified `meta.json` schema:**

```json
{
  "version": "1.0",
  "source": {
    "zlibrary_id": "3505318",
    "original_filename": "book.pdf",
    "format": "pdf"
  },
  "document": {
    "title": "The Burnout Society",
    "author": "Byung-Chul Han",
    "publisher": "Stanford University Press",
    "year": "2015",
    "isbn": "9780804795098"
  },
  "structure": {
    "toc": [...],
    "front_matter": {...},
    "page_count": 117,
    "page_line_mapping": {...}
  },
  "output_files": {
    "body": "author_title_id.pdf.processed.md",
    "footnotes": "author_title_id.pdf.footnotes.md",
    "metadata": "author_title_id.pdf.meta.json"
  },
  "quality": {
    "overall_score": 0.92,
    "content_types_produced": ["body", "footnotes"],
    "ocr_quality_score": null,
    "corrections_applied": []
  },
  "processing": {
    "date": "2026-02-11T...",
    "word_count": 28500,
    "pipeline_metadata": {
      "total_blocks": 450,
      "classifications": [...]
    }
  },
  "verification": {
    "api_vs_extracted": {...}
  }
}
```

**Integration Points (files that change):**
- `lib/rag/pipeline/models.py`: Modify `DocumentOutput.write_files()` to use unified naming
- `lib/rag/pipeline/writer.py`: Modify `format_metadata_sidecar()` to include both metadata sources
- `lib/rag/orchestrator.py`: Simplify `save_processed_text()` -- delegate ALL file writing to `DocumentOutput.write_files()`, remove duplicate metadata generation
- `lib/metadata_generator.py`: Merge useful fields into the pipeline writer, mark module for deprecation
- `lib/python_bridge.py`: No change (already returns result dict from `process_document`)
- `src/lib/zlibrary-api.ts`: No change (passes through Python response)

**Structural Impact:** MEDIUM. Changes are localized to 4-5 Python files. The key refactor is making `DocumentOutput.write_files()` the single authority for output, with the orchestrator's `save_processed_text()` becoming a thin wrapper.

**Dependency:** Should be done AFTER test reorganization (to have proper test infrastructure for validating output format changes).

### Feature 3: Quality Scoring in CI

**Current State:**
- `lib/quality_verification.py`: Standalone module (750 lines), compares PDF vs markdown output, generates `QualityReport` with scored issues
- `lib/rag/quality/pipeline.py`: 3-stage quality pipeline (statistical detection, visual X-mark analysis, OCR recovery) -- this runs DURING processing, not as post-hoc validation
- `test_files/ground_truth/`: Human-verified ground truth data with v3 schema including footnote markers, bboxes, corruption models
- No automated quality scoring in CI today
- `lib/rag/quality/analysis.py`: PDF quality detection (density, image ratio)

**Proposed Architecture:**

Two distinct quality systems:

1. **Processing-time quality** (existing, runs during RAG pipeline):
   - Garbled text detection, X-mark analysis, OCR recovery
   - Already integrated in `_apply_quality_pipeline()`
   - No changes needed

2. **Post-processing quality scoring** (NEW, runs in CI):
   ```
   scripts/ci/
     quality_score.py        # Entry point for CI
   lib/quality/
     scorer.py               # Precision/recall against ground truth
     ground_truth_loader.py  # Loads and validates ground truth JSON
     report.py               # Generates CI-friendly output (JSON + summary)
   ```

**Quality Scoring Algorithm:**

```python
# For each ground truth corpus:
#   1. Run RAG pipeline on test PDF
#   2. Parse output files (body.md, footnotes.md, meta.json)
#   3. Compare against ground truth:
#      - Footnote detection: precision/recall of detected vs expected footnotes
#      - Body text: similarity score (existing SequenceMatcher approach)
#      - Metadata accuracy: field-level comparison
#   4. Aggregate into per-corpus and overall scores
#   5. Fail CI if score < threshold
```

**CI Integration:**

```yaml
# .github/workflows/ci.yml additions:
quality:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '22'
    - uses: astral-sh/setup-uv@v4
    - run: uv sync
    - run: uv run python scripts/ci/quality_score.py --threshold 0.80 --output quality-report.json
    - uses: actions/upload-artifact@v4
      with:
        name: quality-report
        path: quality-report.json
```

**Integration Points (files that change):**
- NEW: `scripts/ci/quality_score.py` (entry point)
- NEW: `lib/quality/scorer.py`, `lib/quality/ground_truth_loader.py`, `lib/quality/report.py`
- MODIFY: `.github/workflows/ci.yml` (add quality job)
- REUSE: `lib/quality_verification.py` (existing comparison logic, refactored into `lib/quality/`)
- MOVE: Ground truth data from `test_files/ground_truth/` to `__tests__/ground_truth/`

**Structural Impact:** LOW-MEDIUM. New files in `lib/quality/` and `scripts/ci/`. Existing `lib/quality_verification.py` gets refactored but functionality preserved. CI workflow gets one new job.

**Dependency:** Depends on test reorganization (ground truth location), and partially on structured RAG output (to know what output files to validate).

### Feature 4: Repo Cleanup

**Current State -- Items to Remove/Move:**

Root-level artifacts (clearly dead):
- `debug_asterisk_full_search.py` -- debug script
- `debug_find_asterisk_anywhere.py` -- debug script
- `debug_kant_page2_asterisk.py` -- debug script
- `debug_kant_page3_content.py` -- debug script
- `debug_page2_block10_11.py` -- debug script
- `debug_page3_block8_full.py` -- debug script
- `debug_page3_continuation.py` -- debug script
- `test_footnote_validation.py` -- root-level test (should be in __tests__)
- `test_kant_page2_debug.py` -- root-level debug test
- `multi_corpus_validation.py` -- validation script (move to scripts/)
- `footnote_validation_results.json` -- output artifact
- `performance_baseline.json` -- should be in test_files/ or __tests__/
- `BUG_5_OPTIMIZATION_PLAN.md` -- stale issue doc
- `CONTINUATION_INTEGRATION_SUMMARY.md` -- stale session note
- `DOCUMENTATION_MAP.md` -- stale (docs reorganized in v1.0)
- `VALIDATION_SUMMARY.md` -- stale validation report
- `QUICKSTART.md` -- fold into README.md or docs/
- `MagicMock/` -- pytest artifact directory
- `__pycache__/` at root -- cache directory
- `dummy_output/` -- test artifact
- `.benchmarks/` -- empty directory

Source artifacts to clean:
- `src/*.js`, `src/lib/*.js` -- compiled JS in source directory (should only be in dist/)
- `src/zlibrary_mcp.egg-info/` -- Python packaging artifact in TS source dir
- `index.js` at root -- stale entry point (should be dist/index.js)
- `requirements-dev.txt` -- superseded by pyproject.toml [tool.uv.dev-dependencies]
- `setup_venv.sh` -- superseded by setup-uv.sh

**Consolidation Opportunities:**
- `test_files/` + `test_data/` --> `__tests__/ground_truth/pdfs/` (one location for test PDFs)
- `claudedocs/` --> `docs/internal/` (AI session notes don't need separate root dir)
- `.claude/` stays (Claude Code convention, well-documented)
- `docs/archive/` stays (historical reference per user preference)

**Proposed Clean Top-Level:**

```
zlibrary-mcp/
  .claude/              # AI assistant documentation
  .github/              # CI workflows
  .husky/               # Git hooks
  .planning/            # GSD workflow artifacts
  __tests__/            # ALL tests (node + python + ground truth)
  dist/                 # Compiled TypeScript output (gitignored)
  docker/               # Docker configurations
  docs/                 # ADRs, specs, architecture, internal notes
  lib/                  # Python source (bridge, RAG pipeline, sources)
  scripts/              # Utility and CI scripts
  src/                  # TypeScript source
  zlibrary/             # Vendored Z-Library fork
  .dockerignore
  .env.example
  .gitignore
  .mcp.json.example
  .npmignore
  .nvmrc
  CLAUDE.md
  ISSUES.md
  LICENSE
  README.md
  jest.config.js
  jest.teardown.js
  package.json
  package-lock.json
  pyproject.toml
  pytest.ini
  tsconfig.json
  uv.lock
  setup-uv.sh
```

**Integration Points:**
- `.gitignore`: Add patterns for cleaned items, remove entries for deleted files
- `.npmignore`: Update for new structure
- `CLAUDE.md`: Update file organization section
- `README.md`: Update quick start and structure references
- `pyproject.toml`: No changes needed (already correct)
- `package.json`: Remove stale `"main": "index.js"` (should point to `dist/index.js`)

**Structural Impact:** HIGH for file moves/deletes, but LOW risk (no source logic changes). Pure housekeeping.

**Dependency:** Should be done FIRST or in parallel with test reorganization (since both move files around).

### Feature 5: Documentation Generation

**Current State:**
- No automated API docs
- CLAUDE.md serves as primary developer reference (16KB, comprehensive)
- `docs/` has ADRs, architecture notes, specs, archive
- `.claude/` has workflow-specific guides (TDD, debugging, patterns, etc.)
- `claudedocs/` has AI session notes and research

**Proposed Architecture:**

```
docs/
  api/                    # Auto-generated API docs
    README.md             # Overview with tool listing
    tools/                # Per-tool documentation (from Zod schemas)
      search-books.md
      download-book.md
      process-for-rag.md
      ...
  architecture/           # Keep existing
  adr/                    # Keep existing
  specifications/         # Keep existing
  guides/
    quickstart.md         # Moved from root QUICKSTART.md
    contributing.md       # New contributor guide
    rag-output-format.md  # Documents the structured output format
  internal/               # Moved from claudedocs/
    session-notes/
    research/
    phase-reports/
  archive/                # Keep existing
```

**API Docs Generation:**

Since the MCP tools are defined with Zod schemas in `src/index.ts`, we can generate documentation from them:

```typescript
// scripts/generate-api-docs.ts (or .js)
// 1. Import tool schemas and descriptions from src/index.ts
// 2. For each tool: generate markdown with params table, description, examples
// 3. Write to docs/api/tools/
```

This is a simple script, not a framework dependency. The Zod schemas already contain descriptions for every parameter. No external doc generation tool needed.

**Integration Points:**
- NEW: `scripts/generate-api-docs.js` (runs after build, generates docs/api/)
- MODIFY: `package.json`: Add `"docs": "node scripts/generate-api-docs.js"` script
- MOVE: `QUICKSTART.md` -> `docs/guides/quickstart.md`
- MOVE: `claudedocs/` -> `docs/internal/`
- MODIFY: `README.md`: Add links to generated API docs

**Structural Impact:** LOW. New script, file moves, README update. No source logic changes.

**Dependency:** Depends on repo cleanup (to have clean docs/ structure before generating into it).

### Feature 6: npm Packaging

**Current State:**
- `package.json` has `"exports"`, `"bin"`, `"prepublishOnly"`, `"main"` fields
- `.npmignore` exists but is minimal (15 lines)
- `package.json` `"main": "index.js"` is WRONG (should be `"dist/index.js"` or removed since `exports` handles it)
- `"bin": { "zlibrary-mcp": "./dist/index.js" }` is correct
- Python `lib/` directory MUST be included in npm package (runtime dependency)
- `zlibrary/` vendored fork MUST be included (runtime dependency)
- `pyproject.toml` and `uv.lock` MUST be included (for Python env setup)

**Proposed `.npmignore`:**

```
# Development
.git/
.github/
.vscode/
.claude/
.planning/
.serena/
.husky/

# Test and debug
__tests__/
test_files/
test_data/
coverage/
*.test.js
*.test.ts

# Python build artifacts
__pycache__/
*.py[cod]
*.so
.pytest_cache/
.ruff_cache/
*.egg-info/

# Development configs
.env
.env.*
.mcp.json
tsconfig.tsbuildinfo
jest.config.js
jest.teardown.js
pytest.ini

# Documentation (not needed at runtime)
docs/
claudedocs/
CLAUDE.md
ISSUES.md
QUICKSTART.md
BUG_5_OPTIMIZATION_PLAN.md
CONTINUATION_INTEGRATION_SUMMARY.md
DOCUMENTATION_MAP.md
VALIDATION_SUMMARY.md

# Build/debug artifacts
scripts/
docker/
docker-compose.test.yml
Dockerfile.test
logs/
downloads/
processed_rag_output/
dummy_output/
MagicMock/

# Source TypeScript (dist/ has compiled JS)
src/**/*.ts

# Stale root files
debug_*.py
test_*.py
multi_corpus_validation.py
footnote_validation_results.json
performance_baseline.json
```

**What MUST be in the npm package:**

```
dist/                   # Compiled TypeScript
lib/                    # Python source (runtime dependency)
zlibrary/               # Vendored Z-Library fork
pyproject.toml          # For `uv sync` during setup
uv.lock                 # For reproducible Python env
setup-uv.sh             # Setup helper
package.json
README.md
LICENSE
.nvmrc
.env.example
.npmignore              # (excluded by npm itself)
```

**Integration Points:**
- MODIFY: `package.json`: Fix `"main"` field, add `"files"` array for explicit inclusion
- MODIFY: `.npmignore`: Comprehensive exclusion list
- MODIFY: `README.md`: Add npm install instructions
- NEW: Post-install hook consideration: `"postinstall": "bash setup-uv.sh"` (careful -- not all users have bash)

**Structural Impact:** LOW. Config file changes only. No source logic changes.

**Dependency:** Should be done LAST (after cleanup, test reorg, and structured output are stable).

---

## Recommended Architecture: Component Boundaries

### Python Layer Responsibilities

```
lib/
  python_bridge.py          # Entry point: JSON dispatch to functions
  rag_processing.py         # Facade: re-exports from lib/rag/*
  rag/
    orchestrator.py         # Main: process_document(), save_processed_text()
    orchestrator_pdf.py     # PDF-specific: process_pdf(), process_pdf_structured()
    pipeline/
      runner.py             # Detection pipeline orchestration
      compositor.py         # Conflict resolution between detectors
      models.py             # DocumentOutput, BlockClassification, ContentType
      writer.py             # Output formatting and file writing
    detection/              # Content type detectors (footnotes, margins, headings, etc.)
    quality/
      pipeline.py           # Processing-time quality (garbled, X-mark, OCR)
      analysis.py           # PDF quality detection
      scorer.py             # NEW: Post-processing quality scoring
      ground_truth_loader.py # NEW: Ground truth schema loading
      report.py             # NEW: CI reporting
    ocr/                    # OCR corruption and recovery
    resolution/             # Adaptive DPI rendering
    xmark/                  # X-mark (sous-rature) detection
    processors/             # Format-specific processors (epub, pdf, txt)
    utils/                  # Constants, text helpers, caching
  sources/                  # Multi-source search (Anna's Archive, LibGen)
  metadata_generator.py     # DEPRECATED in v1.2 (merged into pipeline/writer.py)
  quality_verification.py   # REFACTORED into lib/quality/ in v1.2
  [other top-level modules]  # Footnote tools, garbled detection, etc.
```

### TypeScript Layer Responsibilities

```
src/
  index.ts                  # MCP server, tool registration, Zod schemas
  lib/
    zlibrary-api.ts         # Tool-to-Python function mapping
    python-bridge.ts        # Python process spawning
    venv-manager.ts         # UV venv path resolution
    paths.ts                # Path resolution helpers
    circuit-breaker.ts      # Retry circuit breaker
    retry-manager.ts        # Exponential backoff retry
    errors.ts               # Error types
```

No changes to TS layer for v1.2. All v1.2 features are either Python-side or config/infra.

---

## Patterns to Follow

### Pattern 1: Single Authority for Output Files

**What:** All RAG output file writing goes through `DocumentOutput.write_files()`. The orchestrator's `save_processed_text()` becomes a thin wrapper that calls `write_files()` with enriched metadata.

**When:** Any time RAG output format changes.

**Example:**
```python
# BEFORE (v1.1 -- two parallel write paths):
saved_path = await save_processed_text(...)  # Writes body + metadata sidecar
doc_output.write_files(saved_base)           # Writes body + footnotes + meta

# AFTER (v1.2 -- single path):
doc_output.enrich_metadata(book_details, verification_report)
written_paths = doc_output.write_files(output_dir, filename_base)
# Returns: {"body": Path, "footnotes": Path, "metadata": Path, ...}
```

### Pattern 2: Ground Truth as Test Contract

**What:** Ground truth JSON files serve as the contract between the RAG pipeline and quality scoring. The schema is versioned and validated.

**When:** Adding new ground truth corpora or changing output format.

**Example:**
```python
# __tests__/ground_truth/schema.json defines the contract
# lib/quality/ground_truth_loader.py validates all corpus files against it
# lib/quality/scorer.py compares pipeline output against loaded ground truth

def load_ground_truth(corpus_dir: Path) -> List[GroundTruthCorpus]:
    schema = json.loads((corpus_dir / "schema.json").read_text())
    corpora = []
    for f in corpus_dir.glob("corpora/*.json"):
        data = json.loads(f.read_text())
        validate(data, schema)  # jsonschema validation
        corpora.append(GroundTruthCorpus.from_dict(data))
    return corpora
```

### Pattern 3: CI Quality Gate with Artifact Upload

**What:** Quality scoring runs as a separate CI job that produces a JSON artifact. The job fails if overall score drops below threshold but always uploads the report.

**When:** Every push/PR to master.

**Example:**
```yaml
quality:
  needs: test  # Only run if tests pass
  steps:
    - run: uv run python scripts/ci/quality_score.py
    - uses: actions/upload-artifact@v4
      if: always()  # Upload even on failure
      with:
        name: quality-report
        path: quality-report.json
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Duplicate Metadata Generation

**What:** Two separate systems generating metadata sidecars with different schemas.
**Why bad:** Consumers don't know which `_meta.json` to trust. Data can diverge.
**Instead:** Merge into a single `meta.json` with a versioned schema. One write path.

### Anti-Pattern 2: Root-Level Script Proliferation

**What:** Debug scripts, validation scripts, and test files at project root.
**Why bad:** Clutters the repo, confuses contributors about what's current vs stale.
**Instead:** Scripts go in `scripts/` with subdirectories (archive/, debugging/, ci/). Tests go in `__tests__/`.

### Anti-Pattern 3: Schema Version Fragmentation

**What:** Three ground truth schema versions (v1, v2, v3) all present, tests reference different versions.
**Why bad:** Unclear which schema is canonical. New tests might use wrong version.
**Instead:** Keep ONLY v3 (latest). Migrate any v1/v2 ground truth data to v3 format. Delete old schemas.

### Anti-Pattern 4: Compiled JS in Source Directory

**What:** `src/*.js` and `src/lib/*.js` files alongside `.ts` source.
**Why bad:** Confuses which files are authoritative. Can cause stale JS to be loaded.
**Instead:** Compiled output goes ONLY to `dist/`. Add `src/**/*.js` to `.gitignore`.

---

## Build Order for v1.2 Features

The following order respects dependencies:

```
Phase 1: Repo Cleanup + Test Reorganization  [parallel, foundational]
  |
  |-- 1a: Delete dead files, clean root
  |-- 1b: Move tests to new structure
  |-- 1c: Consolidate ground truth (single v3 schema)
  |-- 1d: Update jest.config.js, pytest.ini
  |
Phase 2: Structured RAG Output  [depends on test infra]
  |
  |-- 2a: Merge metadata systems (metadata_generator -> pipeline/writer)
  |-- 2b: Implement unified meta.json schema
  |-- 2c: Update DocumentOutput.write_files()
  |-- 2d: Simplify orchestrator save_processed_text()
  |
Phase 3: Quality Scoring CI  [depends on structured output + ground truth]
  |
  |-- 3a: Create lib/quality/ scoring modules
  |-- 3b: Create CI entry point script
  |-- 3c: Add quality job to ci.yml
  |
Phase 4: Documentation + Packaging  [depends on everything being stable]
  |
  |-- 4a: Generate API docs from Zod schemas
  |-- 4b: Reorganize docs/ structure
  |-- 4c: Fix package.json, update .npmignore
  |-- 4d: Refresh README.md
```

**Rationale for this order:**
1. Cleanup first because it reduces noise and establishes clean file locations
2. Test reorg in parallel with cleanup because both are structural moves with no logic changes
3. Structured output after tests because we need proper test infrastructure to validate format changes
4. Quality scoring after structured output because scoring must know the output format
5. Documentation and packaging last because everything they document must be finalized

---

## Scalability Considerations

| Concern | Current (v1.1) | v1.2 Target | Future (v2+) |
|---------|----------------|-------------|---------------|
| Test corpus size | 5 PDFs, 3 schema versions | 5+ PDFs, 1 schema | 20+ PDFs, automated corpus generation |
| Output format | body.md + meta.json (dual) | Unified multi-file with linked meta.json | Structured JSON output for LLM consumption |
| CI quality check | None | Per-corpus scoring, overall threshold | Per-commit regression detection with trend graphs |
| npm package size | ~unknown | Measured, documented | Optimized (tree-shake unused Python modules) |
| Documentation | Manual CLAUDE.md | Generated API docs + CLAUDE.md | Versioned docs with docusaurus or similar |

---

## Sources

All findings based on direct analysis of the codebase at commit `4350456`:
- `src/index.ts`: 587 lines, 13 MCP tools registered
- `lib/rag/`: 31 Python modules in 7 subpackages
- `lib/rag/pipeline/`: 4 modules (runner, compositor, models, writer) -- the core detection pipeline
- `lib/rag/orchestrator.py` + `lib/rag/orchestrator_pdf.py`: Main entry points for document processing
- `lib/metadata_generator.py`: 389 lines, YAML frontmatter + JSON sidecar generation
- `lib/quality_verification.py`: 750 lines, post-processing quality verification
- `__tests__/`: 8 JS test files + 35 Python test files
- `test_files/ground_truth/`: 3 schema versions, 15+ ground truth JSON files
- `.github/workflows/ci.yml`: 2 jobs (test, audit), no quality scoring
- `.npmignore`: 15 lines (minimal)
- `package.json`: Missing proper "main" field, has exports/bin/prepublishOnly
