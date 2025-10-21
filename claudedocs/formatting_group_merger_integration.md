# Formatting Group Merger Integration Guide

## Problem Summary

**Current Issue**: PyMuPDF creates separate spans per word, and applying `span.to_markdown()` individually creates malformed markdown:

```python
# Current output (WRONG):
"*The* ***End*** ***of***"  # Separate markers per word

# Should be (CORRECT):
"*The* ***End of***"  # Grouped by formatting, then formatted
```

## Solution Architecture

**New Module**: `lib/formatting_group_merger.py`
- Groups consecutive spans with identical formatting
- Applies formatting once per group (not per span)
- Preserves footnote detection logic
- Handles edge cases correctly

## Integration Steps

### Step 1: Import the New Module

**File**: `lib/rag_processing.py`
**Location**: Top of file with other imports

```python
from lib.formatting_group_merger import FormattingGroupMerger
```

### Step 2: Replace Span Processing Loop

**File**: `lib/rag_processing.py`
**Location**: Lines 1331-1370 (inside `_format_pdf_markdown` function)

**BEFORE** (Current buggy code):
```python
# Footnote Reference/Definition Detection (using superscript flag)
# Rebuild text WITH footnote markers at correct positions
processed_text_parts = []
potential_def_id = None
first_span_in_block = True
fn_id = None

# Process spans to rebuild text with footnote markers
for span in spans:
    span_text = span.get('text', '')
    flags = span.get('flags', 0)
    is_superscript = flags & 1

    # Detect both numeric (1, 2, 3) and letter (a, b, c) footnotes
    is_footnote_marker = (
        (span_text.isdigit()) or
        (len(span_text) == 1 and span_text.isalpha() and span_text.islower())
    )

    if is_superscript and is_footnote_marker:
        fn_id = span_text
        # Definition heuristic: at start of block
        if first_span_in_block and re.match(r"^[a-z0-9]+[\.\)]?\s*", text, re.IGNORECASE):
            potential_def_id = fn_id
            # For definitions, add the marker as-is (will be detected later)
            processed_text_parts.append(span_text)
        else:
            # Reference: insert markdown footnote marker
            processed_text_parts.append(f"[^{fn_id}]")
    else:
        # Regular text: apply formatting before adding
        formatted_text = _apply_formatting_to_text(span_text, span.get('formatting', set()))
        processed_text_parts.append(formatted_text)

    first_span_in_block = False

# Join parts and clean up spacing
processed_text = ''.join(processed_text_parts)
# Clean up multiple spaces
processed_text = re.sub(r'\s+', ' ', processed_text).strip()
```

**AFTER** (Fixed with formatting groups):
```python
# Footnote Reference/Definition Detection (using superscript flag)
# Use formatting group merger to prevent malformed markdown
merger = FormattingGroupMerger()
processed_text, potential_def_id = merger.process_spans_to_markdown(
    spans=spans,
    is_first_block=True,  # Needed for footnote definition detection
    block_text=text  # Full block text for definition heuristic
)

# Clean up multiple spaces
processed_text = re.sub(r'\s+', ' ', processed_text).strip()
```

**Lines to Replace**: 1331-1370 (40 lines replaced with 9 lines)

### Step 3: Remove Deprecated Helper Function (Optional)

**File**: `lib/rag_processing.py`
**Location**: Lines 1117-1167 (`_apply_formatting_to_text` function)

**Decision**: Can remove or keep for backward compatibility
- **Remove**: If confident no other code calls this function
- **Keep**: Add deprecation warning and redirect to new module

**Recommended**: Keep initially with deprecation notice:
```python
def _apply_formatting_to_text(text: str, formatting: set) -> str:
    """
    DEPRECATED: Use FormattingGroupMerger instead.

    This function is kept for backward compatibility but should not be used
    for new code. It applies formatting per-span, which creates malformed
    markdown when PyMuPDF creates per-word spans.

    Use lib.formatting_group_merger.FormattingGroupMerger for proper grouping.
    """
    import warnings
    warnings.warn(
        "_apply_formatting_to_text is deprecated. Use FormattingGroupMerger instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing implementation ...
```

## Integration Points

### Where Spans Come From

The `spans` variable comes from PyMuPDF text extraction:

```python
# From _format_pdf_markdown() around line 1260
block = block_dict['blocks'][text_block_idx]
lines = block.get('lines', [])

# Extract spans from lines
spans = []
for line in lines:
    for span in line.get('spans', []):
        spans.append(span)
```

### What Gets Passed to Merger

The merger expects PyMuPDF span dicts with these keys:
- `text`: str - The text content
- `flags`: int - PyMuPDF flags (bit 0 = superscript)
- `formatting`: Set[str] - Already extracted formatting set
  - Extracted earlier in the function (around line 1250)
  - Contains: `{'bold', 'italic', 'strikethrough', etc.}`

### Return Values

`merger.process_spans_to_markdown()` returns:
- `processed_text`: str - Markdown with proper formatting groups
- `potential_def_id`: Optional[str] - Footnote ID if definition detected

## Testing Strategy

### Unit Tests

```bash
# Run formatting group merger tests
pytest __tests__/python/test_formatting_group_merger.py -v

# Expected: 50+ tests pass
```

### Integration Testing

Create test case in `__tests__/python/test_rag_processing.py`:

```python
def test_formatting_groups_prevent_malformed_markdown(tmp_path):
    """Test that formatting groups prevent malformed markdown."""
    # Create test PDF with per-word formatting
    pdf_path = tmp_path / "formatted_text.pdf"

    # Process with RAG pipeline
    result = process_document_for_rag(str(pdf_path), output_format='markdown')

    # Verify grouped formatting (not per-word)
    assert '***End of***' in result  # Grouped
    assert '***End*** ***of***' not in result  # Not per-word
```

### Real-World Verification

Test with actual philosophy PDFs:
1. Derrida texts (sous rature - strikethrough)
2. Heidegger translations (italics for German terms)
3. Academic papers (bold + italic for emphasis)

## Performance Considerations

### Before (Inefficient):
- **Complexity**: O(n) where n = number of spans
- **Markdown ops**: n individual `to_markdown()` calls
- **String joins**: n string concatenations

### After (Optimized):
- **Complexity**: O(n) where n = number of spans (same)
- **Markdown ops**: k `apply_formatting_to_group()` calls where k = number of groups
- **String joins**: k string concatenations (k << n typically)

**Typical Improvement**:
- 100 spans with 10 formatting changes
- Before: 100 formatting ops, 100 joins
- After: 10 formatting ops, 10 joins
- **90% reduction** in formatting operations

### Memory Impact

**Before**:
- List of n formatted strings in memory

**After**:
- List of k FormattingGroup objects (smaller)
- Each group has: text (str), formatting (Set[str]), 2 booleans
- **Negligible increase** (~50 bytes per group)

## Edge Cases Handled

### 1. Footnotes Interrupting Formatted Runs

**Input**:
```python
spans = [
    {'text': 'Bold ', 'formatting': {'bold'}},
    {'text': 'text', 'formatting': {'bold'}},
    {'text': '1', 'flags': 1},  # Footnote
    {'text': ' more ', 'formatting': {'bold'}},
    {'text': 'bold', 'formatting': {'bold'}},
]
```

**Output**: `**Bold text**[^1] **more bold**`
- Footnote correctly breaks bold group into two separate groups

### 2. Whitespace Preservation

**Input**:
```python
spans = [
    {'text': '  bold  ', 'formatting': {'bold'}},
]
```

**Output**: `  **bold**  `
- Whitespace stays outside formatting markers (prevents malformed markdown)

### 3. Mixed Formatting

**Input**:
```python
spans = [
    {'text': 'The ', 'formatting': {'italic'}},
    {'text': 'End ', 'formatting': {'bold', 'italic'}},
    {'text': 'of ', 'formatting': {'bold', 'italic'}},
]
```

**Output**: `*The* ***End of***`
- Different formatting = separate groups
- Same formatting = merged group

### 4. Footnote Definitions vs References

**Input** (first span in block):
```python
spans = [
    {'text': '1', 'flags': 1},  # At block start
    {'text': '. See page 42.', 'formatting': set()},
]
block_text = '1. See page 42.'
```

**Output**: `1. See page 42.`, `potential_def_id='1'`
- Detected as definition (not reference)
- Returns footnote ID for storage in `footnote_defs` dict

## Backward Compatibility

### Existing Code Impact

**Zero impact** on existing code:
- New module is self-contained
- Only `_format_pdf_markdown()` modified
- All other functions unchanged
- Tests should still pass

### API Changes

**None**:
- Public API unchanged
- Internal implementation detail only
- `process_document_for_rag()` signature unchanged

### Deprecation Path

If removing `_apply_formatting_to_text()`:
1. **Phase 1** (current): Add deprecation warning
2. **Phase 2** (2 weeks): Mark as private `__apply_formatting_to_text`
3. **Phase 3** (1 month): Remove function entirely

## Validation Checklist

Before merging:

- [ ] All unit tests pass (`pytest __tests__/python/test_formatting_group_merger.py`)
- [ ] Integration tests pass (`pytest __tests__/python/test_rag_processing.py`)
- [ ] Real PDF test (Derrida, Heidegger, academic paper)
- [ ] No regressions (existing tests still pass)
- [ ] Performance validated (no slowdown)
- [ ] Documentation updated
- [ ] Code reviewed

## Rollback Plan

If issues occur after deployment:

1. **Immediate**: Revert lines 1331-1370 to old implementation
2. **Investigation**: Review failed test cases
3. **Fix**: Update `FormattingGroupMerger` logic
4. **Retest**: Full test suite
5. **Redeploy**: With fixes

**Rollback Risk**: Low
- Changes isolated to single function
- Easy to revert (git revert)
- No database/API changes

## Future Enhancements

### Phase 1 (Current)
- ✅ Basic grouping by identical formatting
- ✅ Footnote detection and handling
- ✅ Whitespace preservation

### Phase 2 (Future)
- [ ] Smart whitespace normalization (collapse multiple spaces)
- [ ] Markdown escaping for special chars
- [ ] Custom formatting rules (e.g., different markers for sous rature)

### Phase 3 (Future)
- [ ] Performance optimization (caching)
- [ ] Configurable formatting preferences
- [ ] Support for custom markdown dialects

## Questions & Answers

### Q: Why not use TextSpan.to_markdown()?

**A**: `TextSpan.to_markdown()` operates on individual spans. When PyMuPDF creates per-word spans, this creates malformed markdown:
- `span1.to_markdown() + span2.to_markdown()` → `"***End*** ***of***"` (wrong)
- Group first, then format → `"***End of***"` (correct)

### Q: What about performance?

**A**: Negligible impact. Actually **faster** because:
- Fewer formatting operations (k groups vs n spans)
- Fewer string concatenations
- Same O(n) complexity

### Q: Will this break existing PDFs?

**A**: No. Logic is more correct:
- Before: malformed markdown (worked by accident in some cases)
- After: properly grouped markdown (always correct)

### Q: What if footnote detection breaks?

**A**: Preserved exactly:
- Same logic for detecting footnotes
- Same `isdigit()` and `isalpha()` checks
- Same definition vs reference heuristic
- Just better organized

## Contact

For questions or issues:
- File issue: `ISSUES.md`
- Debug: `.claude/DEBUGGING.md`
- Patterns: `.claude/PATTERNS.md`
