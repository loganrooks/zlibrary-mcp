# Inline Footnote Architecture Gap Analysis

**Date**: 2025-10-28
**Critical Discovery**: Kant uses **inline footnotes** (mid-page), not bottom footnotes
**Impact**: Current 80% threshold architecture completely misses inline footnotes

---

## Critical Discovery

### The Myth: "Footnotes are at page bottom"

**Assumed**:
```
┌─────────────────┐
│                 │
│   BODY TEXT     │ ← 80% of page
│                 │
├─────────────────┤
│  footnotes here │ ← Bottom 20%
└─────────────────┘
```

**Reality (Kant edition)**:
```
┌─────────────────┐
│                 │
│   BODY TEXT     │
│                 │
│   * footnote    │ ← INLINE! (y=435, mid-page)
│   text here...  │
│                 │
│   MORE BODY     │
└─────────────────┘
```

### Evidence

**Page 2 asterisk footnote**:
- Y-position: 435.97 (BODY area)
- Page height: 649.13
- Threshold: 519.31 (80%)
- Classification: **BODY** (not footnote)
- Result: **IGNORED**

**This is NOT a "markerless continuation" problem** - it's an **inline footnote placement** problem.

---

## Architectural Implications

### Current System Fails For:

1. **Inline footnotes** (Kant-style mid-page annotations)
2. **Sidebar footnotes** (marginal glosses)
3. **Interleaved footnotes** (alternating with body text)
4. **Wraparound footnotes** (continuing alongside body)

### Current System Works For:

1. **Bottom footnotes** (Derrida-style page-bottom placement)
2. **Separated footnotes** (clear spatial boundary)
3. **Traditional layouts** (body top, notes bottom)

---

## Root Cause Analysis

### The 80% Threshold Assumption

```python
# lib/rag_processing.py:2909-2918
footnote_threshold = page_height * 0.80  # ← HARD-CODED ASSUMPTION

for block in blocks:
    y_pos = block["bbox"][1]

    if y_pos < footnote_threshold:
        body_text_blocks.append(block)  # ← Kant asterisk goes here
    else:
        footnote_text_blocks.append(block)  # ← Never reached
```

**Why this exists**:
- Reasonable assumption for traditional academic layouts
- Works for Derrida (bottom footnotes)
- Fails for Kant (inline footnotes)

**Why it's wrong**:
- Not all footnotes are at page bottom
- Spatial position != semantic role
- Layout varies by publisher/edition

---

## Solution: Marker-Driven Footnote Extraction

### Core Insight

**Don't rely on spatial position** - use **markers to find footnotes**.

```python
# NEW APPROACH
def _detect_footnotes_in_page(page, page_num):
    # Step 1: Find ALL markers (in body text)
    markers = scan_body_for_markers(page)  # Existing logic

    # Step 2: For each marker, find corresponding definition
    definitions = []
    for marker in markers:
        # Search ENTIRE page for definition starting with this marker
        definition = find_definition_for_marker(page, marker)
        if definition:
            definitions.append(definition)

    return {'markers': markers, 'definitions': definitions}
```

### Algorithm: find_definition_for_marker()

```python
def find_definition_for_marker(page, marker_info):
    """
    Search entire page for text block starting with marker.

    Args:
        page: PyMuPDF page object
        marker_info: Dict with marker text and position

    Returns:
        Dict with definition content or None
    """
    marker_text = marker_info['marker']
    marker_y = marker_info['bbox'][1]  # Y-position of marker

    # Search all blocks on page (not just bottom 20%)
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        for line in block.get("lines", []):
            line_text = extract_line_text(line)

            # Check if line starts with marker
            # Pattern: "marker [. \t] content"
            pattern = rf'^{re.escape(marker_text)}[\.\s\t]'
            match = re.match(pattern, line_text)

            if match:
                # Found definition!
                # Extract remaining content after marker
                content = line_text[match.end():].strip()

                # Check if definition is BELOW marker position
                # (prevents false positives from marker itself)
                block_y = block['bbox'][1]
                if block_y > marker_y:
                    return {
                        'marker': marker_text,
                        'content': content,
                        'bbox': block['bbox'],
                        'potential_continuation': False
                    }

    return None  # Definition not found on this page
```

---

## Two-Pass Detection (Revised)

### Pass 1: Marker-Driven Extraction

**For each marker found in body**:
1. Search ENTIRE page for definition (not just bottom 20%)
2. Match by marker text at line start
3. Validate position (definition y > marker y)
4. Extract content after marker

### Pass 2: Markerless Content (Continuations)

**For blocks WITHOUT marker at start**:
1. Check if in "footnote context" (near other footnotes)
2. Tag as `potential_continuation: True`
3. Let continuation parser merge with incomplete notes

---

## Implementation Plan

### Phase 1: Remove Threshold Dependency

```python
def _detect_footnotes_in_page(page, page_num):
    # OLD: Threshold-based separation
    # footnote_threshold = page_height * 0.80  # ← REMOVE THIS

    # NEW: Marker-driven extraction
    body_markers = scan_body_for_markers(page)
    definitions = []

    for marker in body_markers:
        # Search ENTIRE page for definition
        definition = find_definition_for_marker(page, marker)
        if definition:
            definitions.append(definition)
```

### Phase 2: Handle Markerless Continuations

```python
# After extracting all marked definitions
markerless_candidates = find_markerless_content_near_definitions(page, definitions)

for candidate in markerless_candidates:
    candidate['potential_continuation'] = True
    definitions.append(candidate)
```

### Phase 3: Spatial Heuristics (Optional)

**For finding markerless continuations**:
```python
def find_markerless_content_near_definitions(page, definitions):
    """
    Find text blocks WITHOUT markers that are spatially near definitions.
    These are likely continuations.
    """
    if not definitions:
        return []

    # Get spatial envelope of all definitions
    min_y = min(d['bbox'][1] for d in definitions)
    max_y = max(d['bbox'][3] for d in definitions)

    # Search within this Y-range
    candidates = []
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        block_y = block['bbox'][1]
        if min_y <= block_y <= max_y:
            # Check if block starts with marker
            has_marker = block_starts_with_marker(block)
            if not has_marker:
                # Markerless content in footnote area
                candidates.append({
                    'marker': None,
                    'content': extract_block_text(block),
                    'bbox': block['bbox'],
                    'potential_continuation': True
                })

    return candidates
```

---

## Backward Compatibility

### Derrida Fixture (Bottom Footnotes)

**Will still work**:
1. Markers detected in body (existing logic)
2. Definitions found at page bottom (new search spans entire page)
3. No spatial dependency broken

### Kant Fixture (Inline Footnotes)

**Will now work**:
1. Asterisk marker detected in body
2. Definition found mid-page (new capability!)
3. Continuation on next page (existing logic)

---

## Testing Strategy

### Unit Tests

1. **Test marker-driven extraction**:
   ```python
   def test_find_inline_footnote():
       # Page with mid-page footnote
       result = _detect_footnotes_in_page(page, 1)

       assert len(result['definitions']) > 0
       assert result['definitions'][0]['marker'] == '*'
   ```

2. **Test continuation merge**:
   ```python
   def test_inline_footnote_continuation():
       results = process_pdf('kant_80_85.pdf')
       asterisk = find_footnote_by_marker(results, '*')

       assert asterisk['pages'] == [2, 3]
       assert "criticism, to which everything" in asterisk['content']
   ```

### Regression Tests

1. **Derrida** (bottom footnotes) - must still pass
2. **Kant** (inline footnotes) - must now pass
3. **All 96 tests** - no regressions

---

## Performance Impact

| Operation | Current | With Marker-Driven | Budget |
|-----------|---------|-------------------|--------|
| Footnote detection | 3-5ms | 4-7ms | <10ms ✅ |
| Full-page search | N/A | +1-2ms | <5ms ✅ |
| **Total per page** | **3-5ms** | **5-9ms** | **<12ms ✅** |

---

## Risks & Mitigations

### Risk 1: False Positives

**Problem**: Marker in body text doesn't mean definition exists

**Mitigation**:
- Validate definition position (y > marker y)
- Check for content after marker (min 3 chars)
- Confidence scoring

### Risk 2: Performance Degradation

**Problem**: Searching entire page instead of bottom 20%

**Mitigation**:
- Early exit on match
- Cache block positions
- Optimize regex matching

### Risk 3: Breaking Derrida

**Problem**: Removing threshold might break existing logic

**Mitigation**:
- Marker-driven extraction is superset of threshold
- Derrida definitions still found (at page bottom)
- Comprehensive regression testing

---

## Next Steps

1. ✅ **Analysis complete** (this document)
2. ⏳ **Implement marker-driven extraction** (`find_definition_for_marker()`)
3. ⏳ **Remove threshold dependency** (optional - can keep as optimization)
4. ⏳ **Add markerless content detection** (continuations)
5. ⏳ **Test on Kant + Derrida** (inline + bottom footnotes)
6. ⏳ **Validate all 96 tests** (no regressions)

---

**Status**: Architecture redesign required, ready for implementation
