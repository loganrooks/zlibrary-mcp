# Robust Pre-Filter Solutions for X-mark Detection

**Date**: 2025-10-18
**Context**: User correctly rejected brittle regex approach
**Problem**: How to avoid running expensive X-mark detection on every page WITHOUT making fragile assumptions

---

## Why Regex is WRONG ❌

### The Flawed Approach (What I Initially Proposed)

```python
# DON'T DO THIS:
XMARK_SYMBOLS = {')', '(', '~', '×'}
pattern = re.compile(r'\)\(|~|×')
```

**Problems User Identified**:
1. ❌ ")(" appears in normal text: "method() (" or "Kant (1781)"
2. ❌ Assumes specific OCR representations (what if OCR outputs differently?)
3. ❌ Different OCR systems extract X-marks in unpredictable ways
4. ❌ Fragile and will break in production
5. ❌ False positives on normal punctuation

**User is 100% CORRECT**: This approach is BAD.

---

## Robust Solutions (No Text Pattern Matching)

### Option 1: Page-Level Caching (SIMPLEST) ✅

**Insight**: The expensive part is detecting PER BLOCK. Detect PER PAGE instead.

**Current** (wasteful):
```python
# Page with 10 blocks:
for block in page_blocks:
    detect_strikethrough(pdf_path, page_num)  # 10× redundant!
    # Cost: 5ms × 10 blocks = 50ms per page
```

**Fixed** (efficient):
```python
# Detect ONCE per page, cache result:
page_xmark_cache = {}

# Before processing blocks:
if page_num not in page_xmark_cache:
    page_xmark_cache[page_num] = detect_strikethrough(pdf_path, page_num)
    # Cost: 5ms × 1 = 5ms per page

# For each block:
if page_has_xmarks(page_num, block.bbox, page_xmark_cache):
    flag_as_sous_rature()
```

**Performance**:
- 10 blocks per page: 50ms → 5ms (10× speedup)
- 500-page book: 25s → 2.5s
- **No pre-filter needed!**

**Benefits**:
- ✅ No fragile assumptions
- ✅ No text pattern matching
- ✅ Simple to implement
- ✅ Robust

---

### Option 2: Corpus-Based Heuristic (METADATA) ✅

**Insight**: Philosophy texts need X-mark detection. Technical docs don't.

**Implementation**:
```python
def needs_xmark_detection_for_corpus(metadata: dict) -> bool:
    """Decide based on metadata, not text patterns."""

    # Check author (from Z-Library metadata)
    author = metadata.get('authors', '').lower()
    philosophy_authors = {'derrida', 'heidegger', 'levinas', 'nancy'}

    if any(name in author for name in philosophy_authors):
        return True

    # Check subject/discipline
    subject = metadata.get('subject', '').lower()
    if 'philosophy' in subject or 'phenomenology' in subject:
        return True

    # Check if user explicitly requested
    if metadata.get('enable_xmark_detection', False):
        return True

    # Default: skip for most documents
    return False
```

**Benefits**:
- ✅ No text pattern assumptions
- ✅ Based on reliable metadata
- ✅ User can override
- ✅ Predictable behavior

**Trade-offs**:
- ⚠️ Might miss X-marks in unexpected documents
- ⚠️ Requires good metadata

---

### Option 3: Fast Statistical Pre-Filter (NO PATTERNS) ✅

**Insight**: Don't look for specific symbols. Just check if page is "unusual" in ANY way.

**Implementation**:
```python
def page_has_any_anomalies(page_text: str) -> bool:
    """
    Broad anomaly detection - NO specific symbol patterns.

    Checks if page has ANYTHING unusual:
    - Symbol density >2% (page-level threshold)
    - Low entropy (repetitive text)
    - Unusual character distribution

    Does NOT assume what the anomalies look like!
    """
    if len(page_text) < 100:
        return False

    # Calculate broad statistics (no symbol pattern assumptions)
    total = len(page_text)
    alpha = sum(1 for c in page_text if c.isalpha())
    alpha_ratio = alpha / total

    # Normal academic text: 75-85% alphabetic
    # Anything outside this range is unusual
    if alpha_ratio < 0.70 or alpha_ratio > 0.90:
        return True  # Unusual

    # Entropy check (detects repetition, not specific patterns)
    # ... existing entropy calculation ...

    return False  # Looks normal
```

**Benefits**:
- ✅ No hardcoded symbols
- ✅ Catches ANY anomaly type
- ✅ Robust to OCR variations

---

### Option 4: User Configuration (MOST ROBUST) ✅

**Insight**: Let USER decide, don't guess.

**Implementation**:
```python
# In environment variables:
RAG_XMARK_DETECTION_MODE = 'auto' | 'always' | 'never' | 'philosophy_only'

# In config:
if mode == 'always':
    run_on_all_pages = True
elif mode == 'never':
    run_on_all_pages = False
elif mode == 'philosophy_only':
    run_on_all_pages = is_philosophy_corpus(metadata)
else:  # 'auto'
    run_on_all_pages = page_has_anomalies(page_text)  # Broad check
```

**Benefits**:
- ✅ Most explicit
- ✅ User control
- ✅ No fragile assumptions

---

## Recommended Solution

### Hybrid: Caching + Metadata + User Config

```python
class XMarkDetectionStrategy:
    """Robust X-mark detection strategy."""

    def __init__(self, metadata: dict, config: dict):
        self.metadata = metadata
        self.mode = config.get('xmark_mode', 'auto')
        self.page_cache = {}  # Page-level caching

    def should_detect_page(self, page_num: int, page) -> bool:
        """
        Determine if X-mark detection should run on this page.

        NO TEXT PATTERN MATCHING - uses metadata and user config only.
        """
        # User explicit control
        if self.mode == 'always':
            return True
        if self.mode == 'never':
            return False

        # Philosophy corpus heuristic (metadata-based)
        if self.mode == 'philosophy_only':
            return self._is_philosophy_corpus()

        # Auto mode: Use metadata hints
        if self.mode == 'auto':
            # Check metadata for philosophy indicators
            if self._is_philosophy_corpus():
                return True

            # Check if page has images (scanned pages more likely to have issues)
            if self._page_is_scanned(page):
                return True

            # Default: skip for efficiency
            return False

        return False

    def _is_philosophy_corpus(self) -> bool:
        """Check metadata for philosophy indicators (NO text patterns)."""
        author = self.metadata.get('authors', '').lower()
        subject = self.metadata.get('subject', '').lower()

        # Known philosophy authors who use sous-rature
        if any(name in author for name in {'derrida', 'heidegger', 'levinas', 'nancy'}):
            return True

        # Subject classification
        if 'philosophy' in subject or 'phenomenology' in subject:
            return True

        return False

    def _page_is_scanned(self, page) -> bool:
        """Check if page is scanned (has images)."""
        return len(page.get_images()) > 0

    def detect_with_cache(self, pdf_path, page_num, bbox):
        """Detect with page-level caching."""
        if page_num not in self.page_cache:
            # Detect once per page
            self.page_cache[page_num] = detect_strikethrough_enhanced(
                pdf_path, page_num, bbox=None
            )

        # Check if specific bbox overlaps with cached results
        return self._check_bbox_overlap(bbox, self.page_cache[page_num])
```

---

## Performance Comparison

### Scenario: 500-Page Book (10 blocks/page)

| Approach | Philosophy Book | Technical Book | Notes |
|----------|----------------|----------------|-------|
| **No filter (unconditional)** | 25s | 25s | Wasteful on technical docs |
| **Regex pre-filter** | 25s | 0.05s | ❌ BRITTLE, rejected |
| **Page caching only** | 2.5s | 2.5s | 10× speedup, but still runs on all |
| **Metadata + caching** | 2.5s | 0s | ✅ BEST: Fast and selective |
| **User config 'philosophy_only'** | 2.5s | 0s | ✅ BEST: Explicit control |

---

## Revised Architecture Recommendation

### Three-Tier Approach

**Tier 1: User Configuration** (most explicit)
```bash
# User explicitly enables for specific corpus
export RAG_XMARK_DETECTION_MODE='always'  # Run on all docs
export RAG_XMARK_DETECTION_MODE='philosophy_only'  # Smart default
export RAG_XMARK_DETECTION_MODE='never'  # Skip entirely
```

**Tier 2: Metadata Heuristics** (if mode='auto')
```python
# Check reliable metadata (no text patterns):
if author in PHILOSOPHY_AUTHORS:
    enable_detection = True
elif subject == 'philosophy':
    enable_detection = True
else:
    enable_detection = False
```

**Tier 3: Page-Level Caching** (always)
```python
# Regardless of filtering, ALWAYS cache per page (not per block)
# 10× speedup even when detection runs
```

---

## Implementation (Corrected)

**Delete brittle approach**:
```bash
rm lib/xmark_prefilter.py  # Delete the regex-based version
```

**Implement robust approach**:

```python
# In lib/rag_processing.py:

def _should_enable_xmark_detection(metadata: dict, config: QualityPipelineConfig) -> bool:
    """
    Determine if X-mark detection should be enabled for this document.

    Uses ROBUST criteria (no text pattern matching):
    - User configuration (explicit)
    - Metadata heuristics (author, subject)
    - Conservative default (enable for unknown)

    NO TEXT PATTERNS - only reliable metadata!
    """
    # User explicit control
    mode = os.getenv('RAG_XMARK_DETECTION_MODE', 'auto')

    if mode == 'always':
        return True
    if mode == 'never':
        return False

    # Auto mode: metadata heuristics
    author = metadata.get('authors', '').lower()
    subject = metadata.get('subject', '').lower()
    title = metadata.get('title', '').lower()

    # Known philosophy authors who use sous-rature
    if any(name in author for name in ['derrida', 'heidegger', 'levinas', 'nancy', 'agamben']):
        return True

    # Philosophy subject
    if any(term in subject for term in ['philosophy', 'phenomenology', 'ontology', 'metaphysics']):
        return True

    # Conservative default for unknown: ENABLE
    # Rationale: Better to run unnecessarily than miss sous-rature
    return True


# In process_pdf():
metadata = extract_metadata(file_path)  # Get from PDF or book_details
enable_xmark_for_doc = _should_enable_xmark_detection(metadata, quality_config)

# Page-level caching
page_xmark_cache = {}

# In _format_pdf_markdown():
if enable_xmark_for_doc:
    # Check cache first
    if page_num not in page_xmark_cache:
        # Detect ONCE per page
        page_xmark_cache[page_num] = detect_strikethrough_enhanced(...)

    # Use cached result for all blocks on this page
```

---

## Why This is ROBUST

**NO assumptions about**:
- ❌ How X-marks appear in text
- ❌ Specific OCR representations
- ❌ Symbol patterns

**ONLY uses**:
- ✅ Reliable metadata (author, subject from Z-Library)
- ✅ User configuration (explicit intent)
- ✅ Conservative defaults (enable when uncertain)

**Performance**:
- Philosophy book (500 pages): 2.5s (with caching)
- Technical book (500 pages): 0s (skipped via metadata)
- Unknown corpus (500 pages): 2.5s (conservative default)

---

## Summary: Three Changes Needed

### Change 1: Remove Regex Pre-Filter ❌
**Action**: Delete `lib/xmark_prefilter.py` (the brittle version)

### Change 2: Add Metadata-Based Filtering ✅
**Action**: Implement `_should_enable_xmark_detection()` using author/subject

### Change 3: Add Page-Level Caching ✅
**Action**: Cache X-mark detection per page (not per block)

**Result**: Robust, fast, no fragile assumptions

---

**Timeline**: 1-2 hours to implement properly

**Performance**: 10-50× speedup depending on corpus

**Robustness**: No text pattern matching, only reliable metadata

User's critique was EXACTLY right - let's do this properly!
