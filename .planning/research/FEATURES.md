# Feature Landscape: v1.1 Quality & Expansion

**Domain:** Scholarly document extraction quality + multi-source book retrieval
**Researched:** 2026-02-01
**Overall confidence:** MEDIUM (mix of well-documented techniques and novel integration work)

---

## Feature 1: Margin Content Detection

### How It Works in Practice

Scholarly texts place reference numbering in margins: Stephanus numbers (Plato, e.g. "Republic 514a"), Bekker numbers (Aristotle, e.g. "1094a1"), Academy page numbers, line numbers, and marginal notes/glosses.

**Detection approach:** Position-based classification using PDF text coordinates.

1. **Extract all text blocks with coordinates** (PyMuPDF `page.get_text("dict")` gives bbox per span)
2. **Define margin zones** per page: left gutter (0-15% page width), right gutter (85-100%), top/bottom strips
3. **Classify margin text by pattern:**
   - Stephanus: `\d{2,3}[a-e]` (e.g. "514a", "327c")
   - Bekker: `\d{3,4}[ab]\d{1,2}` (e.g. "1094a1", "1253b14")
   - Line numbers: bare integers in left margin, incrementing (5, 10, 15...)
   - Marginal notes: longer text strings in margin zones
4. **Associate margin refs with body text** by y-coordinate proximity
5. **Output as structured metadata** rather than inline noise

**Key challenge:** Margin zones vary by publisher. Loeb Classical Library puts numbers on outer margins; Oxford Classical Texts uses inner margins. Need adaptive zone detection, not hardcoded percentages.

### Table Stakes

| Feature | Why Required | Complexity | Dependencies |
|---------|-------------|------------|-------------|
| Margin zone detection (left/right gutters) | Without this, margin text leaks into body as noise | Med | Existing PyMuPDF text extraction |
| Stephanus number pattern recognition | Most common scholarly reference for Plato | Low | Margin zone detection |
| Bekker number pattern recognition | Standard for Aristotle citations | Low | Margin zone detection |
| Line number detection (bare integers in margins) | Very common in critical editions | Low | Margin zone detection |
| Margin content exclusion from body text | The whole point -- clean body text | Med | All above |
| Margin metadata in output header | Preserve scholarly refs without polluting body | Med | Pattern recognition |

### Differentiators

| Feature | Value | Complexity |
|---------|-------|------------|
| Auto-detect margin zone widths per document | Handles varied publishers without config | High |
| Diels-Kranz fragment numbering (pre-Socratics) | Niche but valuable for philosophy use case | Low (just another pattern) |
| Cross-reference margin numbers to body paragraphs | Enable "jump to 514a" style lookup | High |
| Academy edition page breaks as structural markers | Useful for Kant, Hegel citations | Med |

### Anti-Features

| Anti-Feature | Why Avoid | Instead |
|--------------|-----------|---------|
| Full critical apparatus parsing | Enormously complex (variants, sigla, nested refs) | Just detect and separate apparatus text from body |
| Margin content OCR (scanned margins) | Existing OCR pipeline handles this; don't duplicate | Use existing OCR, then classify by position |
| Interactive margin annotation | This is a reader feature, not extraction | Output metadata only |

---

## Feature 2: Adaptive Resolution (Variable DPI)

### How It Works in Practice

Current pipeline presumably uses fixed DPI for OCR. Adaptive resolution means analyzing each page (or region) and choosing optimal DPI based on content.

**Key insight from Tesseract research:** OCR accuracy correlates most with capital letter height in pixels, not raw DPI. Optimal range is ~30-33px cap height. So:

1. **Analyze page content type** (text-heavy, image-heavy, mixed, fine print)
2. **Measure text size** if digital text layer exists (font size from metadata)
3. **For scanned pages:** Sample region, estimate character pixel height
4. **Select DPI:** Text-heavy normal font = 150-200 DPI; fine print/footnotes = 300 DPI; images with text = 300 DPI
5. **Process page at selected DPI**

**OCRmyPDF already supports `--oversample`** for upscaling low-res inputs. The project uses PyMuPDF which can render pages at arbitrary DPI via `page.get_pixmap(dpi=N)`.

### Table Stakes

| Feature | Why Required | Complexity | Dependencies |
|---------|-------------|------------|-------------|
| Page-level DPI selection | Core of adaptive resolution | Med | Existing OCR pipeline |
| Text density analysis per page | Needed to make DPI decisions | Med | PyMuPDF text block extraction |
| Minimum quality threshold (don't go below 150 DPI) | Prevents garbage OCR | Low | DPI selection |

### Differentiators

| Feature | Value | Complexity |
|---------|-------|------------|
| Region-level DPI (footnotes at higher DPI than body) | Captures fine print that page-level misses | High |
| Performance budget awareness (lower DPI when speed matters) | User-configurable quality/speed tradeoff | Med |
| Automatic detection of scanned-vs-digital pages | Skip OCR entirely for digital text pages | Med (partially exists in quality analysis) |

### Anti-Features

| Anti-Feature | Why Avoid | Instead |
|--------------|-----------|---------|
| AI-based DPI prediction model | Overkill; heuristics work fine | Simple rules: small text = high DPI, large text = low DPI |
| User-specified DPI per page | No user in the loop (MCP server) | Automatic selection only |
| Super-resolution upscaling (ML-based) | Heavy dependency, marginal gain over simple oversample | Use OCRmyPDF oversample or PyMuPDF higher DPI render |

---

## Feature 3: Multi-Source Book Retrieval (Anna's Archive)

### How It Works in Practice

Anna's Archive aggregates multiple shadow libraries (Library Genesis, Sci-Hub, Z-Library mirrors, Open Library). Adding it as a source means:

1. **API access:** Anna's Archive offers a JSON API (requires donation for API key). Also available via RapidAPI wrapper (3000 free requests/month).
2. **Search:** Query by title/author/ISBN. Returns structured results with MD5 hashes.
3. **Download:** Pass MD5 to download endpoint to get direct link.
4. **Deduplication:** Same book may exist in both Z-Library and Anna's Archive. Need MD5 or title+author matching to avoid duplicates.

**Legal risk (CRITICAL):** In January 2026, Anna's Archive lost several domains (.org, .se) due to court injunction. The service migrates domains frequently. This means:
- Base URL must be configurable
- Domain discovery/fallback needed
- Service may become unavailable

**Existing MCP server:** `annas-mcp` by iosifache already exists as an MCP server for Anna's Archive. Consider whether to integrate their approach or build custom.

### Table Stakes

| Feature | Why Required | Complexity | Dependencies |
|---------|-------------|------------|-------------|
| Anna's Archive search integration | Core feature -- find books not on Z-Library | Med | API key management, HTTP client |
| Unified search results (merge Z-Lib + AA) | Users shouldn't care which source | Med | Both search APIs working |
| Source attribution in results | User needs to know provenance | Low | Result data model |
| Configurable API key (`ANNAS_SECRET_KEY`) | Required for API access | Low | Env config |
| Configurable base URL | Domain instability requires this | Low | Env config |
| Download from Anna's Archive | Search without download is useless | Med | MD5-based download flow |

### Differentiators

| Feature | Value | Complexity |
|---------|-------|------------|
| Automatic fallback (Z-Lib fails -> try AA, vice versa) | Resilience when one source is down | Med |
| Best-format selection across sources (prefer EPUB over PDF) | Better extraction quality downstream | Med |
| Source health monitoring (track which source is responding) | Proactive reliability | Med |
| Open Library integration (legal, public domain) | Adds legitimate source for older texts | Med |

### Anti-Features

| Anti-Feature | Why Avoid | Instead |
|--------------|-----------|---------|
| Scraping Anna's Archive HTML (no API) | Fragile, breaks on layout changes | Use official JSON API only |
| Embedding annas-mcp as dependency | Different architecture, unnecessary coupling | Build native integration using same API |
| Automatic domain discovery/rotation | Legal grey area; let user configure | Configurable `ANNAS_BASE_URL` env var |
| Torrent/IPFS downloads | Complexity explosion; stick to direct HTTP | Direct download links from API |

---

## Feature 4: Body Text Purity

### How It Works in Practice

"Body text purity" means extracting ONLY the main narrative/argument text, stripping ALL non-body content: headers, footers, page numbers, footnotes, margin notes, running heads, chapter titles (optionally), epigraphs, etc.

**Best current approach: PyMuPDF4LLM** -- specifically designed for LLM-ready text extraction. It automatically detects and suppresses headers, footers, and can identify footnotes.

**Layered separation strategy:**

1. **Geometric classification:** Divide page into zones (header strip, footer strip, margins, body rectangle)
2. **Font-based classification:** Headers/footers often use different fonts/sizes than body
3. **Repetition detection:** Headers/footers repeat across pages (use sequence matching like difflib)
4. **Pattern detection:** Page numbers, running heads, "Chapter X" patterns
5. **Footnote detection:** Already exists in project -- continuation and corruption recovery
6. **Margin content:** Feature 1 above
7. **Confidence scoring:** Each text block gets a "body probability" score; threshold determines inclusion

**The project already has:** footnote detection, page number detection, heading detection, TOC detection, front matter detection. Body text purity is about composing these into a unified pipeline that outputs ONLY body text.

### Table Stakes

| Feature | Why Required | Complexity | Dependencies |
|---------|-------------|------------|-------------|
| Unified non-body content filter | Compose existing detectors into single pass | Med | All existing detection modules |
| Running head removal (repeated text at top of pages) | Very common noise source | Med | Cross-page text comparison |
| Confidence-based inclusion/exclusion | Binary classification misses edge cases | Med | All detectors providing scores |
| Structured output mode (body + metadata separately) | Preserve non-body content without polluting body | Med | All detection modules |
| Regression test suite for purity | Must not lose body text while filtering | Med | Test fixtures with ground truth |

### Differentiators

| Feature | Value | Complexity |
|---------|-------|------------|
| PyMuPDF4LLM integration | Purpose-built for this exact use case; may replace custom code | Med |
| GROBID integration for academic papers | ML-based zone classification; best-in-class for papers | High |
| Per-paragraph body confidence score in output | Downstream AI can decide what to trust | Med |
| Format-specific purity profiles (novel vs. textbook vs. philosophy) | Different genres have different non-body patterns | High |

### Anti-Features

| Anti-Feature | Why Avoid | Instead |
|--------------|-----------|---------|
| Remove ALL footnotes from output | Footnotes contain valuable content for AI | Separate into footnote section, don't delete |
| Aggressive filtering (high false positive) | Losing body text is worse than including some noise | Conservative defaults, tunable threshold |
| Real-time ML classification per page | Too slow for batch processing | Heuristic rules + cross-page patterns |
| Perfect critical edition handling | Infinite complexity (apparatus, variants, witnesses) | Handle the 90% case; flag complex editions |

---

## Feature Dependencies Map

```
Feature 1 (Margin Detection)
  depends on: existing PyMuPDF text extraction, existing page number detection
  feeds into: Feature 4 (Body Text Purity)

Feature 2 (Adaptive Resolution)
  depends on: existing OCR pipeline, existing PDF quality analysis
  independent of Features 1, 3, 4

Feature 3 (Anna's Archive)
  depends on: existing search/download infrastructure, env config pattern
  independent of Features 1, 2, 4
  feeds into: existing RAG pipeline (downloaded files get processed)

Feature 4 (Body Text Purity)
  depends on: Feature 1 (margin detection), existing footnote/heading/TOC/page-number detection
  this is the integration/composition feature
```

**Recommended build order:**
1. Feature 2 (Adaptive Resolution) -- independent, improves OCR quality for everything else
2. Feature 1 (Margin Detection) -- needed by Feature 4
3. Feature 4 (Body Text Purity) -- composes all detection into unified pipeline
4. Feature 3 (Anna's Archive) -- independent, can be parallel with 1+4 but has legal risk worth deferring

---

## MVP Recommendation

**Must have for v1.1:**
- Margin zone detection + Stephanus/Bekker recognition (Features 1 table stakes)
- Body text purity pipeline composing all detectors (Feature 4 table stakes)
- Anna's Archive search + download integration (Feature 3 table stakes)

**Defer to v1.2:**
- Adaptive resolution (Feature 2) -- nice improvement but not blocking
- Cross-reference margin numbers to body (Feature 1 differentiator)
- GROBID integration (Feature 4 differentiator)
- Open Library integration (Feature 3 differentiator)

**Rationale:** The core value proposition is better text quality for AI consumption of scholarly texts. Margin detection + body purity directly serve that. Anna's Archive expands the library. Adaptive DPI is optimization, not new capability.

---

## Sources

- [Bekker numbering - Wikipedia](https://en.wikipedia.org/wiki/Bekker_numbering) (HIGH - factual reference)
- [Stephanus and Bekker Numbers - Proofed](https://proofed.com/writing-tips/citing-plato-and-aristotle-stephanus-and-bekker-numbers/) (HIGH - factual reference)
- [Oxford Scholarly Editions - Bekker navigation](https://www.oxfordscholarlyeditions.com/newsitem/221/using-bekker-numbers-to-navigate-the-works-of-aristotle) (HIGH - authoritative)
- [PyMuPDF4LLM documentation](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) (HIGH - official docs)
- [PyMuPDF header/footer removal discussion](https://github.com/pymupdf/PyMuPDF/discussions/2259) (MEDIUM - community)
- [pdf_header_and_footer_detector](https://github.com/gentrith78/pdf_header_and_footer_detector) (MEDIUM - reference implementation)
- [annas-mcp GitHub](https://github.com/iosifache/annas-mcp) (HIGH - reference implementation)
- [Anna's Archive RapidAPI](https://rapidapi.com/tribestick-tribestick-default/api/annas-archive-api) (MEDIUM - third-party wrapper)
- [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) (HIGH - official docs)
- [Tesseract optimal DPI discussion](https://groups.google.com/g/tesseract-ocr/c/Wdh_JJwnw94/m/24JHDYQbBQAJ) (MEDIUM - expert community)
- [DeepSeek OCR adaptive resolution](https://sparkco.ai/blog/deepseek-ocr-maximizing-pdf-text-extraction-accuracy) (LOW - single blog source)
- [PDFMiner text extraction](https://www.glukhov.org/post/2025/12/extract-text-from-pdf-using-pdfminer-python/) (MEDIUM - tutorial)
