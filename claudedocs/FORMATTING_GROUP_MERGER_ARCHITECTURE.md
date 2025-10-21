# Formatting Group Merger: Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG Pipeline                              │
│                    (lib/rag_processing.py)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ PyMuPDF spans (per-word)
                                │ [{'text': 'End ', 'formatting': {'bold'}}, ...]
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              FormattingGroupMerger                                │
│         (lib/formatting_group_merger.py)                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Step 1: create_groups()                               │    │
│  │  ┌──────────────────────────────────────────────────┐ │    │
│  │  │ Input: 100 spans (per-word from PyMuPDF)         │ │    │
│  │  │ Process: Group by identical formatting           │ │    │
│  │  │ Output: 10 FormattingGroups                      │ │    │
│  │  └──────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Step 2: apply_formatting_to_group()                   │    │
│  │  ┌──────────────────────────────────────────────────┐ │    │
│  │  │ Input: FormattingGroup(text='End of', fmt=bold)  │ │    │
│  │  │ Process: Apply markdown markers                  │ │    │
│  │  │ Output: "**End of**"                             │ │    │
│  │  └──────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ Formatted markdown
                                │ "*The* ***End of***"
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Final Output                                  │
│                  (markdown text file)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Before vs After

### BEFORE (Buggy Implementation)

```
PyMuPDF Extraction
       │
       ▼
┌──────────────┐
│ Span: "End " │  ←─── Per-word span
│ fmt: {bold}  │
└──────────────┘
       │
       ▼ _apply_formatting_to_text()
"**End**"
       │
       ▼
┌──────────────┐
│ Span: "of "  │  ←─── Per-word span
│ fmt: {bold}  │
└──────────────┘
       │
       ▼ _apply_formatting_to_text()
"**of**"
       │
       ▼ Join: "**End** **of**"  ←── WRONG! Should be "**End of**"

Problem: Formatting applied BEFORE grouping
```

### AFTER (Fixed Implementation)

```
PyMuPDF Extraction
       │
       ▼
┌──────────────┐  ┌──────────────┐
│ Span: "End " │  │ Span: "of "  │  ←─── Per-word spans
│ fmt: {bold}  │  │ fmt: {bold}  │
└──────────────┘  └──────────────┘
       │                 │
       └────────┬────────┘
                ▼ FormattingGroupMerger.create_groups()
       ┌─────────────────┐
       │ Group: "End of "│  ←─── Grouped by identical formatting
       │ fmt: {bold}     │
       └─────────────────┘
                │
                ▼ FormattingGroupMerger.apply_formatting_to_group()
          "**End of**"  ←── CORRECT! Formatted once per group
```

## Class Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    FormattingGroup                             │
│                      (dataclass)                               │
├───────────────────────────────────────────────────────────────┤
│ + text: str                                                    │
│ + formatting: Set[str]                                         │
│ + is_footnote: bool = False                                    │
│ + footnote_id: Optional[str] = None                            │
└───────────────────────────────────────────────────────────────┘
                              ▲
                              │ Creates
                              │
┌───────────────────────────────────────────────────────────────┐
│              FormattingGroupMerger                             │
│                     (class)                                    │
├───────────────────────────────────────────────────────────────┤
│ + create_groups(spans, is_first_block, block_text)            │
│   → List[FormattingGroup]                                      │
│                                                                │
│ + apply_formatting_to_group(group)                             │
│   → str                                                        │
│                                                                │
│ + process_spans_to_markdown(spans, is_first_block, block_text)│
│   → Tuple[str, Optional[str]]                                  │
└───────────────────────────────────────────────────────────────┘
```

## Algorithm: Group Creation

```
┌─────────────────────────────────────────────────────────────┐
│ create_groups(spans) Algorithm                               │
└─────────────────────────────────────────────────────────────┘

Input: List of PyMuPDF spans
       [
         {'text': 'The ', 'formatting': {'italic'}, 'flags': 0},
         {'text': 'End ', 'formatting': {'bold', 'italic'}, 'flags': 0},
         {'text': 'of ', 'formatting': {'bold', 'italic'}, 'flags': 0},
         {'text': '1', 'formatting': set(), 'flags': 1},  ← Footnote
       ]

Process:
  ┌──────────────────────────────────────────────────┐
  │ For each span:                                   │
  │                                                  │
  │ 1. Is it a footnote?                            │
  │    (superscript flag + isdigit/isalpha)         │
  │    ├─ YES → Finalize current group              │
  │    │         Create footnote group               │
  │    └─ NO  → Continue to step 2                  │
  │                                                  │
  │ 2. Does formatting match current group?         │
  │    (Set equality: formatting == current_fmt)    │
  │    ├─ YES → Append to current group             │
  │    └─ NO  → Finalize current group              │
  │              Start new group                     │
  └──────────────────────────────────────────────────┘

Output: List of FormattingGroups
        [
          FormattingGroup(text='The ', formatting={'italic'}),
          FormattingGroup(text='End of ', formatting={'bold','italic'}),
          FormattingGroup(text='[^1]', is_footnote=True, footnote_id='1'),
        ]

Complexity: O(n) single pass
Memory: O(k) where k = number of groups
```

## Algorithm: Formatting Application

```
┌─────────────────────────────────────────────────────────────┐
│ apply_formatting_to_group(group) Algorithm                   │
└─────────────────────────────────────────────────────────────┘

Input: FormattingGroup
       text='  End of  '
       formatting={'bold', 'italic'}

Process:
  ┌──────────────────────────────────────────────────┐
  │ 1. Handle edge cases                             │
  │    - Empty text → return as-is                  │
  │    - Whitespace-only → return as-is             │
  │    - Footnote → return as-is (already formatted)│
  │                                                  │
  │ 2. Strip whitespace (preserve position)         │
  │    leading = '  '                               │
  │    text_stripped = 'End of'                     │
  │    trailing = '  '                              │
  │                                                  │
  │ 3. Apply formatting to stripped text            │
  │    if bold and italic:                          │
  │       formatted = '***End of***'                │
  │    elif bold:                                   │
  │       formatted = '**End of**'                  │
  │    elif italic:                                 │
  │       formatted = '*End of*'                    │
  │                                                  │
  │ 4. Restore whitespace OUTSIDE markers           │
  │    result = leading + formatted + trailing      │
  │    result = '  ***End of***  '                  │
  └──────────────────────────────────────────────────┘

Output: Formatted markdown string
        '  ***End of***  '

Key Insight: Whitespace OUTSIDE markers prevents malformed markdown
```

## Sequence Diagram: Full Pipeline

```
┌─────────┐         ┌──────────────┐         ┌─────────────────┐
│   RAG   │         │   PyMuPDF    │         │ FormattingGroup │
│Pipeline │         │              │         │     Merger      │
└────┬────┘         └──────┬───────┘         └────────┬────────┘
     │                     │                          │
     │ Extract text        │                          │
     ├────────────────────>│                          │
     │                     │                          │
     │ Return spans        │                          │
     │<────────────────────┤                          │
     │                     │                          │
     │ Create groups       │                          │
     ├──────────────────────────────────────────────>│
     │                     │                          │
     │                     │  Group consecutive spans │
     │                     │  with same formatting    │
     │                     │                          │
     │ Return groups       │                          │
     │<──────────────────────────────────────────────┤
     │                     │                          │
     │ Apply formatting    │                          │
     ├──────────────────────────────────────────────>│
     │                     │                          │
     │                     │  Apply markdown to each  │
     │                     │  group (not each span)   │
     │                     │                          │
     │ Return markdown     │                          │
     │<──────────────────────────────────────────────┤
     │                     │                          │
     │ Write to file       │                          │
     │                     │                          │
```

## Edge Case: Footnote Interrupts Formatted Run

```
Input Spans:
┌──────────────┐  ┌──────────────┐  ┌───────┐  ┌──────────────┐  ┌──────────────┐
│ "Bold "      │  │ "text"       │  │  "1"  │  │ " more "     │  │ "bold"       │
│ fmt: {bold}  │  │ fmt: {bold}  │  │ flags:│  │ fmt: {bold}  │  │ fmt: {bold}  │
│              │  │              │  │   1   │  │              │  │              │
└──────────────┘  └──────────────┘  └───────┘  └──────────────┘  └──────────────┘
                                        ▲
                                   Footnote!

Grouping Process:
┌──────────────────────────┐           ┌─────────┐           ┌──────────────────────────┐
│ Group 1:                 │           │ Group 2:│           │ Group 3:                 │
│ "Bold text"              │           │ "[^1]"  │           │ " more bold"             │
│ fmt: {bold}              │           │footnote │           │ fmt: {bold}              │
└──────────────────────────┘           └─────────┘           └──────────────────────────┘

Output:
"**Bold text**[^1] **more bold**"
       ▲            ▲       ▲
    Group 1     Footnote  Group 3

Key: Footnote breaks formatting group into two separate groups
```

## Performance Comparison

```
┌──────────────────────────────────────────────────────────────┐
│ Scenario: 100 spans, 10 formatting changes                   │
└──────────────────────────────────────────────────────────────┘

BEFORE (Per-span formatting):
  ┌────┐ ┌────┐ ┌────┐     ┌────┐
  │ S1 │ │ S2 │ │ S3 │ ... │S100│  ← 100 spans
  └─┬──┘ └─┬──┘ └─┬──┘     └─┬──┘
    │      │      │           │
    ▼      ▼      ▼           ▼
  ┌────┐ ┌────┐ ┌────┐     ┌────┐
  │ F1 │ │ F2 │ │ F3 │ ... │F100│  ← 100 format ops
  └────┘ └────┘ └────┘     └────┘

  Total: 100 formatting operations

AFTER (Grouped formatting):
  ┌────┬────┬────┐     ┌────┐
  │ S1 │ S2 │ S3 │ ... │S100│  ← 100 spans
  └─┬──┴──┬─┴──┬─┘     └─┬──┘
    │     │    │          │
    ▼     ▼    ▼          ▼
  ┌───┐ ┌───┐ ┌───┐ ... ┌───┐
  │G1 │ │G2 │ │G3 │ ... │G10│  ← 10 groups
  └─┬─┘ └─┬─┘ └─┬─┘     └─┬─┘
    │     │     │          │
    ▼     ▼     ▼          ▼
  ┌───┐ ┌───┐ ┌───┐     ┌───┐
  │F1 │ │F2 │ │F3 │ ... │F10│  ← 10 format ops
  └───┘ └───┘ └───┘     └───┘

  Total: 10 formatting operations

  Improvement: 90% reduction (10 vs 100)
```

## Test Coverage Map

```
┌─────────────────────────────────────────────────────────────┐
│                   Test Coverage                              │
└─────────────────────────────────────────────────────────────┘

FormattingGroupMerger
├── create_groups()
│   ├── ✅ Single span (no formatting)
│   ├── ✅ Consecutive same formatting (merge)
│   ├── ✅ Different formatting (separate groups)
│   ├── ✅ Footnote reference (separate group)
│   ├── ✅ Footnote definition (block start)
│   ├── ✅ Alternating formatting (multiple groups)
│   ├── ✅ Empty spans list
│   └── ✅ Letter footnote markers (a, b, c)
│
├── apply_formatting_to_group()
│   ├── ✅ No formatting (plain text)
│   ├── ✅ Bold formatting (**)
│   ├── ✅ Italic formatting (*)
│   ├── ✅ Bold+italic formatting (***)
│   ├── ✅ Strikethrough formatting (~~)
│   ├── ✅ Whitespace preservation (outside markers)
│   ├── ✅ Leading whitespace
│   ├── ✅ Trailing whitespace
│   ├── ✅ Whitespace-only unchanged
│   ├── ✅ Empty text unchanged
│   ├── ✅ Footnote group (as-is)
│   ├── ✅ Sous-erasure (Derrida)
│   ├── ✅ Underline (<u>)
│   ├── ✅ Superscript (^)
│   └── ✅ Subscript (~)
│
└── process_spans_to_markdown() [Integration]
    ├── ✅ Basic sentence with formatting
    ├── ✅ Sentence with footnote reference
    ├── ✅ Footnote definition block
    ├── ✅ Complex formatting mix
    ├── ✅ Multiple consecutive footnotes
    ├── ✅ Formatted text with footnote
    ├── ✅ Whitespace handling
    └── ✅ Empty spans list

Edge Cases
├── ✅ Single character spans
├── ✅ Only whitespace spans
├── ✅ Unicode text (différance, über, 漢字)
├── ✅ Special markdown characters (*, _, **)
└── ✅ Nested formatting attempt

Performance
├── ✅ Large number of spans (100+)
└── ✅ Very long consecutive group (1000 spans)

Total: 40/40 tests PASSING ✅
```

## File Structure

```
zlibrary-mcp/
├── lib/
│   ├── rag_processing.py          ← Integration point (lines 1331-1370)
│   ├── formatting_group_merger.py ← NEW: Core implementation
│   └── rag_data_models.py         ← Used: TextSpan, FormattingGroup
│
├── __tests__/python/
│   ├── test_rag_processing.py     ← Existing tests (ensure no regressions)
│   └── test_formatting_group_merger.py ← NEW: 40 comprehensive tests
│
└── claudedocs/
    ├── FORMATTING_GROUP_MERGER_SOLUTION.md        ← Complete documentation
    ├── FORMATTING_GROUP_MERGER_QUICKSTART.md     ← 5-minute guide
    ├── FORMATTING_GROUP_MERGER_ARCHITECTURE.md   ← This file
    └── formatting_group_merger_integration.md     ← Detailed integration
```

## Deployment Flow

```
┌──────────────┐
│ Development  │
└──────┬───────┘
       │
       │ 1. Implement FormattingGroupMerger
       ▼
┌──────────────┐
│   Testing    │
└──────┬───────┘
       │
       │ 2. Run 40 unit tests (all pass)
       ▼
┌──────────────┐
│ Integration  │
└──────┬───────┘
       │
       │ 3. Modify rag_processing.py (40 lines → 9 lines)
       ▼
┌──────────────┐
│ Validation   │
└──────┬───────┘
       │
       │ 4. Run integration tests (no regressions)
       ▼
┌──────────────┐
│ Real PDF     │
│   Testing    │
└──────┬───────┘
       │
       │ 5. Test with Derrida, Heidegger PDFs
       ▼
┌──────────────┐
│  Production  │
└──────────────┘
```

---

*Architecture Version: 1.0*
*Last Updated: 2025-10-21*
