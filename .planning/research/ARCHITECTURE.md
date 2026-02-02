# Architecture Patterns — v1.1 Quality & Expansion

**Domain:** Z-Library MCP Server v1.1 feature integration
**Researched:** 2026-02-01
**Confidence:** HIGH (based on direct codebase analysis)

## Current Architecture Overview

```
MCP Client
  |
  v
src/index.ts (McpServer, Zod schemas, tool handlers)
  |
  v
src/lib/zlibrary-api.ts (callPythonFunction via PythonShell)
  |
  v
lib/python_bridge.py (dispatch: search/download/process_document/metadata)
  |                        |
  v                        v
zlibrary/src/zlibrary/     lib/rag/
  libasync.py (AsyncZlib)    orchestrator_pdf.py
  eapi.py (EAPIClient)       detection/ (footnotes, headings, toc, front_matter, page_numbers)
                              quality/ (analysis.py, pipeline.py, ocr_stage.py)
                              processors/ (pdf.py, epub, txt)
                              ocr/ (recovery, spacing, corruption)
                              xmark/ (detection)
                              utils/ (constants, cache, header, exceptions)
```

---

## Question 1: Where Does Margin Content Detection Fit?

### Integration Point

Margin detection is a **detection module** — it identifies content in PDF margins (marginalia, annotations, running headers/footers that contain substantive content). It belongs in `lib/rag/detection/` alongside existing detectors.

### New Module

**File:** `lib/rag/detection/margins.py`

**Responsibilities:**
- Detect text blocks in page margins (top/bottom/left/right regions outside main content area)
- Classify margin content: running header, running footer, marginalia (substantive), page number (already handled by `page_numbers.py`)
- Return margin regions with classification for downstream pipeline decisions

### Data Flow

```
orchestrator_pdf.py: process_pdf()
  |
  v
  For each page:
    fitz.Page.get_text("dict") -> blocks with bbox coordinates
    |
    v
  [NEW] margins.detect_margin_content(page, blocks) -> MarginClassification
    |     Uses bbox positions relative to page.rect (mediabox)
    |     Returns: {running_headers: [...], running_footers: [...], marginalia: [...]}
    |
    v
  [EXISTING] _format_pdf_markdown(page, ...)
    |     Currently processes ALL text blocks
    |     [MODIFIED] Skip running headers/footers, include marginalia
    |
    v
  [EXISTING] quality/pipeline.py: _apply_quality_pipeline()
    |     No changes needed — operates on PageRegion objects regardless of origin
```

### Integration with Existing Detection Modules

| Existing Module | Interaction with Margins |
|----------------|--------------------------|
| `page_numbers.py` | Margin detector should defer to page_numbers for numeric-only margin content. Call page_numbers first, then classify remaining margin blocks. |
| `front_matter.py` | No conflict. Front matter detection operates at document level; margin detection at page level. |
| `headings.py` | Marginalia should NOT be classified as headings even if font size is large. Margin detector runs before heading detection. |
| `footnotes.py` | Bottom-margin content that matches footnote patterns should be deferred to footnote detection. Margin detector should flag but not extract footnotes. |

### Suggested Build Order

1. Add `MarginClassification` dataclass to `lib/rag_data_models.py`
2. Create `lib/rag/detection/margins.py` with `detect_margin_content(page, blocks) -> MarginClassification`
3. Modify `lib/rag/orchestrator_pdf.py` to call margin detection before `_format_pdf_markdown`
4. Modify `lib/rag/processors/pdf.py` (`_format_pdf_markdown`) to accept margin classification and filter blocks accordingly

### Key Design Decision

**Margin detection must run BEFORE block formatting**, not as a quality pipeline stage. Reason: the quality pipeline (stages 1-3) operates on individual PageRegions after block extraction. Margin detection needs to filter WHICH blocks enter the pipeline at all. This is analogous to how `page_numbers.py` works — it runs early to remove page number blocks from content.

---

## Question 2: Adaptive Resolution in quality/pipeline.py

### Current Pipeline Structure

```
_apply_quality_pipeline(page_region, pdf_path, page_num, config, xmark_cache, ocr_cache)
  Stage 1: _stage_1_statistical_detection() — garbled text analysis
  Stage 2: _stage_2_visual_analysis() — X-mark/strikethrough detection (opencv)
  Stage 3: _stage_3_ocr_recovery() — OCR text recovery (tesseract)
```

### What Adaptive Resolution Means

Adaptive resolution adjusts OCR/image processing DPI based on document quality characteristics detected in earlier stages. Low-quality scans need higher DPI; clean PDFs need less.

### Integration Point

Adaptive resolution modifies **Stage 3 (OCR recovery)** and the image conversion step. Currently in `lib/rag/quality/ocr_stage.py`.

### Recommended Approach

**File:** Modify `lib/rag/quality/ocr_stage.py` (not a new module)

**Add to `QualityPipelineConfig`** in `lib/rag/quality/pipeline.py`:
```python
# Adaptive resolution settings
adaptive_resolution: bool = True
min_dpi: int = 150
max_dpi: int = 600
default_dpi: int = 300
```

**Logic flow:**
```
Stage 1 output (quality_score) + Stage 2 output (xmark detection confidence)
  |
  v
[NEW] _determine_optimal_dpi(quality_score, xmark_result, config) -> int
  |     quality_score < 0.3 -> max_dpi (600)  [heavily garbled]
  |     quality_score < 0.7 -> 400             [moderate quality]
  |     quality_score >= 0.7 -> min_dpi (150)  [clean text, OCR just for verification]
  |     xmark detected -> at least 300         [need clear line detection]
  |
  v
Stage 3: _stage_3_ocr_recovery() uses determined DPI for convert_from_path()
```

### No Structural Changes Needed

The pipeline already passes `quality_score` and `xmark_result` into Stage 3. Adaptive resolution is a **parameter calculation** before the existing OCR call, not a new pipeline stage. Add `_determine_optimal_dpi()` as a helper in `ocr_stage.py`.

---

## Question 3: Second Book Source (Anna's Archive) Architecture

### Current Source Architecture

```
python_bridge.py
  +-- AsyncZlib (login, search, download) — zlibrary/src/zlibrary/libasync.py
  +-- EAPIClient (search, metadata, download link) — zlibrary/src/zlibrary/eapi.py
```

The bridge currently hard-codes Z-Library as the only source. `callPythonFunction` in Node dispatches to one Python bridge, which uses one source.

### Recommended Architecture: Source Abstraction Layer

**New files:**
- `lib/sources/__init__.py`
- `lib/sources/base.py` — Abstract base class
- `lib/sources/zlibrary.py` — Z-Library adapter (wraps existing EAPIClient)
- `lib/sources/annas_archive.py` — Anna's Archive adapter
- `lib/sources/registry.py` — Source registry and routing

```python
# lib/sources/base.py
class BookSource(ABC):
    name: str
    @abstractmethod
    async def search(query, filters) -> List[BookResult]
    @abstractmethod
    async def get_metadata(book_id, book_hash) -> BookMetadata
    @abstractmethod
    async def get_download_link(book_id, book_hash) -> str
    @abstractmethod
    async def download(book_id, book_hash, output_dir) -> Path
    @abstractmethod
    async def login(credentials) -> bool

# lib/sources/registry.py
class SourceRegistry:
    sources: Dict[str, BookSource]
    def register(source: BookSource)
    def get(name: str) -> BookSource
    async def search_all(query, filters) -> Dict[str, List[BookResult]]
```

### Integration with Existing Code

**Minimal disruption approach:**

1. `lib/sources/zlibrary.py` wraps the existing `EAPIClient` behind the `BookSource` interface
2. `lib/python_bridge.py` gets a new optional `source` parameter on search/download functions
3. Default source = "zlibrary" (backward compatible)
4. Node-side `src/lib/zlibrary-api.ts` passes optional `source` parameter
5. `src/index.ts` adds `source` as optional Zod parameter on search/download tools

### Anna's Archive Specifics

Anna's Archive has no official API. Integration options:
- Scraping search results (fragile, ToS concerns)
- Tor hidden service access
- Z-Library bridge (AA often mirrors Z-Library content)

**Confidence: MEDIUM** — AA integration feasibility depends on their current access patterns, which change frequently. Recommend a research spike before implementation.

### Data Flow with Two Sources

```
MCP Client: search_books(query, source="annas_archive")
  v
src/index.ts -> zlibrary-api.ts -> callPythonFunction("search", {source: "annas_archive"})
  v
python_bridge.py: search() checks args_dict.get("source", "zlibrary")
  v
sources/registry.py -> sources/annas_archive.py -> HTTP request
  v
Normalize response to common BookResult format -> return to Node
```

---

## Question 4: Removing AsyncZlib While Keeping Downloads

### Current Dependency Chain

```
python_bridge.py
  imports: AsyncZlib (line 13: from zlibrary import AsyncZlib)
  uses: AsyncZlib for login (cookie extraction), download_book()

AsyncZlib.login() -> sets cookies, creates EAPIClient internally
AsyncZlib.search() -> delegates to self._eapi.search() (already EAPI)
AsyncZlib.download_book() -> self._eapi.get_download_link() then httpx stream
```

**Key finding:** AsyncZlib is already a thin wrapper. Its download_book() method (libasync.py lines 357-440) does:
1. Call `self._eapi.get_download_link(book_id, book_hash)` — available directly on EAPIClient
2. Stream download via httpx with cookies — easily extracted

Meanwhile, `python_bridge.py` already has its own `initialize_eapi_client()` (lines 186-236) that creates a standalone EAPIClient with login and domain discovery, independent of AsyncZlib.

### What AsyncZlib Still Provides

| Capability | AsyncZlib | Standalone EAPIClient | Gap |
|-----------|-----------|----------------------|-----|
| Login | rpc.php POST + cookie jar | `/eapi/user/login` POST | None — EAPI login works independently |
| Search | Delegates to _eapi.search() | .search() directly | None |
| Download link | Delegates to _eapi.get_download_link() | .get_download_link() directly | None |
| File streaming | httpx stream with cookies | Need to extract ~25 lines | Small |
| Domain discovery | Via _eapi.get_domains() | .get_domains() directly | None |

### Removal Strategy

**Phase 1: Extract download to standalone function**

**New file:** `lib/sources/download.py` (or inline in python_bridge.py)

```python
async def stream_download(eapi_client: EAPIClient, book_id: int, book_hash: str,
                          output_dir: str, extension: str) -> str:
    """Download book using EAPI client for auth and download link."""
    dl_resp = await eapi_client.get_download_link(book_id, book_hash)
    download_url = dl_resp.get("file", {}).get("downloadLink") or dl_resp.get("downloadLink", "")
    # ... stream download logic (copy from libasync.py lines 418-440)
```

**Phase 2: Update python_bridge.py**

- Line 13: Remove `from zlibrary import AsyncZlib`
- Line 36: Remove `zlib_client = None`
- Line 472: Replace `zlib.download_book()` with `stream_download(_eapi_client, ...)`
- Update `lib/client_manager.py`: Remove AsyncZlib client management

**Phase 3: Clean up vendored fork**

- `zlibrary/src/zlibrary/__init__.py`: Remove AsyncZlib export (keep EAPIClient)
- Optionally remove libasync.py entirely

### What Breaks

| File | Line | Current | Fix |
|------|------|---------|-----|
| `lib/python_bridge.py` | 13 | `from zlibrary import AsyncZlib` | Remove import |
| `lib/python_bridge.py` | 490 | `await zlib.download_book(...)` | Use `stream_download(_eapi_client, ...)` |
| `lib/client_manager.py` | all | `get_default_client()` returns AsyncZlib | Return EAPIClient or remove module |
| Tests mocking AsyncZlib | various | Mock `zlibrary.AsyncZlib` | Mock new download function |

### What Does NOT Break

- All search operations (already use `_eapi_client` directly in python_bridge.py)
- All metadata operations (already use `_eapi_client`)
- All Node.js code (calls same Python functions via PythonShell)
- RAG pipeline (no dependency on zlibrary package)

---

## Question 5: Node 20+ Upgrade Impact

### Current State

- `package.json`: `"engines": { "node": ">=18" }`
- `tsconfig.json`: `"target": "ES2022"`, `"module": "NodeNext"`
- `@types/node`: `^18.19.4`
- Uses ESM (`"type": "module"`)
- Jest requires `--experimental-vm-modules`

### Breaking Changes Assessment

| Area | Impact | Notes |
|------|--------|-------|
| ESM support | None | Stable in both 18 and 20 |
| `--experimental-vm-modules` (Jest) | None | Still experimental in Node 20; stable in 22 |
| `fetch` global | None | Project uses PythonShell, not fetch |
| `fs/promises` | None | Stable in both |
| `python-shell@5.0.0` | None | Pure JS, no native addons |
| `@modelcontextprotocol/sdk@^1.25.3` | None | Standard ESM package |
| `zod@^3.25.76` | None | Pure JS |

### What Actually Breaks

**Almost nothing.** The codebase uses standard Node.js APIs and ESM.

Update items:
1. `package.json` engines: `"node": ">=20"`
2. `@types/node`: `"^20.11.0"` (accurate type definitions)
3. Run `npm test` to verify

### Risk Assessment: LOW

Node 18 to 20 is a minor upgrade with no known breaking changes for this codebase.

---

## Component Boundaries Summary

### New Components

| Component | Location | Purpose | Depends On |
|-----------|----------|---------|------------|
| Margin detector | `lib/rag/detection/margins.py` | Classify margin content | PyMuPDF (fitz), rag_data_models |
| Adaptive DPI helper | `lib/rag/quality/ocr_stage.py` (modify) | Calculate OCR resolution | Existing pipeline config |
| Source abstraction | `lib/sources/` (new package) | Multi-source book access | httpx |
| Download extractor | `lib/sources/download.py` | Standalone EAPI download | EAPIClient, httpx, aiofiles |
| Anna's Archive adapter | `lib/sources/annas_archive.py` | AA search/download | httpx |

### Modified Components

| Component | File | Change |
|-----------|------|--------|
| PDF orchestrator | `lib/rag/orchestrator_pdf.py` | Call margin detection before formatting |
| PDF formatter | `lib/rag/processors/pdf.py` | Accept margin classification, filter blocks |
| Quality config | `lib/rag/quality/pipeline.py` | Add adaptive resolution settings to dataclass |
| OCR stage | `lib/rag/quality/ocr_stage.py` | Add `_determine_optimal_dpi()` helper |
| Python bridge | `lib/python_bridge.py` | Source parameter, remove AsyncZlib |
| Client manager | `lib/client_manager.py` | Remove AsyncZlib dependency |
| Data models | `lib/rag_data_models.py` | Add MarginClassification dataclass |
| Node API | `src/lib/zlibrary-api.ts` | Pass source parameter |
| MCP tools | `src/index.ts` | Add source to Zod schemas |
| Package config | `package.json` | Node 20+ engine, @types/node bump |

## Build Order (Dependencies)

```
Phase A (independent, can parallelize):
  A1. Node 20+ upgrade (package.json, @types/node, test)
  A2. Margin detection module (lib/rag/detection/margins.py + data models)
  A3. Adaptive resolution (modify ocr_stage.py + pipeline.py config)

Phase B (depends on nothing new):
  B1. Extract download function from AsyncZlib -> lib/sources/download.py
  B2. Remove AsyncZlib from python_bridge.py, update client_manager.py

Phase C (depends on Phase B):
  C1. Source abstraction layer (lib/sources/base.py, registry.py)
  C2. Z-Library adapter (wraps existing EAPIClient)
  C3. Anna's Archive adapter (research spike needed first)

Phase D (depends on Phase A2):
  D1. Integrate margin detection into orchestrator_pdf.py
  D2. Update _format_pdf_markdown to use margin classification
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Coupling Anna's Archive to Z-Library internals
**What:** Making AA adapter depend on zlibrary/ vendored code
**Why bad:** Different APIs, different auth, different data formats
**Instead:** Clean `BookSource` interface; each adapter is self-contained

### Anti-Pattern 2: Margin detection inside quality pipeline
**What:** Adding margin detection as Stage 0 in `_apply_quality_pipeline`
**Why bad:** Quality pipeline operates on individual PageRegions. Margin detection needs to filter WHICH blocks become PageRegions. Wrong abstraction level.
**Instead:** Margin detection in orchestrator, before block-level processing

### Anti-Pattern 3: Big bang AsyncZlib removal
**What:** Removing AsyncZlib and adding Anna's Archive in one step
**Why bad:** Two large changes compound risk. Download breakage blocks everything.
**Instead:** Extract download first, verify, then add source abstraction

### Anti-Pattern 4: Over-engineering source abstraction before second source exists
**What:** Building full registry/plugin system before Anna's Archive is proven feasible
**Why bad:** YAGNI. AA may not be viable due to access pattern changes.
**Instead:** Extract download, add simple source parameter routing. Build full abstraction only when AA adapter works.

## Sources

- Direct codebase analysis (HIGH confidence)
- `lib/rag/quality/pipeline.py` lines 252-318: 3-stage waterfall pipeline structure
- `zlibrary/src/zlibrary/libasync.py` lines 357-440: AsyncZlib.download_book() delegates to EAPIClient
- `zlibrary/src/zlibrary/eapi.py` lines 130-132: EAPIClient.get_download_link()
- `lib/python_bridge.py` lines 186-236: Standalone EAPIClient initialization (independent of AsyncZlib)
- `lib/python_bridge.py` lines 454-534: download_book() uses AsyncZlib via client_manager
