# Marginalia Design - Spatial Segmentation Approach

**Date**: 2025-10-13
**Status**: PROPOSED (Not yet implemented)
**Approach**: Spatial semantic segmentation (position-based, not pattern-based)

---

## Design Philosophy: Hybrid Approach

**Key Insight**: Use spatial segmentation for DETECTION, light pattern matching for CLASSIFICATION.

**Hybrid Approach**:
1. **Spatial Detection** (robust): Detect margins vs. body using x-coordinates
2. **Extract Text** (preserve): Get exact marginal text
3. **Pattern Classification** (light): Classify as citation system vs. generic note
4. **Distinct Syntax**: `{{cite: "A 50"}}` vs `{{note: "see intro"}}`
5. **Build Mappings**: Create canonical_mappings ONLY for citations

**Why This Is Optimal**:
- ✅ Spatial detection = robust, general (works for any layout)
- ✅ Pattern classification = enables citation mappings
- ✅ Distinct syntax = enables targeted search
- ✅ Citation → page/line mappings for scholarly work
- ✅ Generic notes preserved but not mapped
- ✅ Best of both worlds

---

## Problem Statement

### Complex Philosophical Texts Have Multiple Reference Systems

**Kant's Critique of Pure Reason**:
- A edition marginalia: First edition (1781) page numbers
- B edition marginalia: Second edition (1787) page numbers
- Scholars cite as "A 50/B 75" (universal citation)
- PDF page numbers: Edition-specific (e.g., Cambridge edition p. 102)

**Heidegger's Being and Time**:
- German pagination in margins
- Scholars cite German pages regardless of translation
- Example: "SZ 42" = Sein und Zeit page 42

**Plato's Dialogues**:
- Stephanus pagination: "Phaedrus 245c-246a"
- Universal across all editions/translations
- Based on 1578 Henri Estienne (Stephanus) edition

**Aristotle's Works**:
- Bekker numbers: "Physics 184b15-20"
- Column and line numbers from 1831 Bekker edition

### Current System Limitations

**What we have**:
```markdown
`[p.102]`

The transcendental unity of apperception...
```

**What we need**:
```markdown
`[p.102]` {A:50} {B:75}

The transcendental unity of apperception...
```

---

## Proposed Solution: Spatial Segmentation with Universal Syntax

### Simplified Approach

**Don't Interpret, Just Preserve**:
- Detect margins spatially (x-coordinate zones)
- Extract whatever text is there
- Mark with position context
- No pattern matching required

### Dual Syntax: Citations vs. Notes

**Citation Systems** (canonical scholarly references):
```markdown
{{cite: "A 50"}}           ← Kant A edition
{{cite: "B 75"}}           ← Kant B edition
{{cite: "SZ 42"}}          ← Heidegger German pages
{{cite: "245c"}}           ← Plato Stephanus
{{cite: "184b15"}}         ← Aristotle Bekker
```

**Generic Notes** (non-canonical marginalia):
```markdown
{{note: "See p. 30"}}      ← Cross-reference
{{note: "nb"}}             ← Nota bene
{{note: "disputed"}}       ← Editorial comment
{{note: "cf. Introduction"}} ← Internal reference
```

**PDF Page Markers** (standalone):
```markdown
`[p.102]`
```

**Position**: All marginalia inline exactly where appears (y-coordinate match)

### Combined Example (Kant Critique):
```markdown
`[p.102]`

{{cite: "A 50"}} {{cite: "B 75"}} The transcendental unity of
apperception is therefore that unity through which all the manifold
given in an intuition is united in a concept of the object.

{{cite: "A 51"}} {{cite: "B 76"}} {{note: "Key passage"}} But all
unification of representations requires a unity of consciousness...
```

**Benefits**:
- ✅ Spatial detection = robust, general
- ✅ Citation/note distinction = enables mappings
- ✅ `{{cite:}}` → indexed in canonical_mappings
- ✅ `{{note:}}` → preserved but not mapped
- ✅ Search: "Find all citations" vs "Find all notes"
- ✅ RAG can prioritize citation-marked passages

---

## Marginalia Types and Use Cases

### Type 1: Canonical Citation Systems

**Purpose**: Universal scholarly citation

**Examples**:
| Work | System | Format | Example |
|------|--------|--------|---------|
| Kant CPR | A/B editions | `{A:50}` `{B:75}` | {A:50}{B:75} |
| Heidegger BT | German pages | `{SZ:42}` | {SZ:42} |
| Plato | Stephanus | `{245c}` | {Stephanus:245c} |
| Aristotle | Bekker | `{184b15}` | {Bekker:184b15} |

**Representation in Main Text**:
```markdown
{A:50} The transcendental unity of apperception {A:51} is therefore that unity...
```

**In Metadata**:
```json
{
  "citation_system": {
    "type": "kant_a_b",
    "editions": {
      "A": {"year": 1781, "full_name": "First Edition"},
      "B": {"year": 1787, "full_name": "Second Edition"}
    },
    "marginaliadetected": true,
    "marginalia_count": 247
  },
  "canonical_page_mapping": {
    "A:50": {"pdf_page": 102, "line_start": 1450},
    "B:75": {"pdf_page": 102, "line_start": 1450}
  }
}
```

### Type 2: Section/Chapter References

**Purpose**: Navigate within work structure

**Examples**:
```markdown
{Part.I} {Book.II} {Chapter.3}
```

**Or combined**:
```markdown
{I.II.3} First Analogy of Experience...
```

### Type 3: Annotations and Notes

**Purpose**: Editorial notes, translator notes, glosses

**Examples**:
```markdown
The Dasein {{trans: "being-there" in German}} exists...

{{editor: "This passage disputed by scholars"}}
```

### Type 4: Cross-References

**Purpose**: Internal references within work

**Examples**:
```markdown
As discussed above {see:A:25} the categories...

{{cf: "Second Analogy"}}
```

---

## Extraction Strategy (Spatial Segmentation)

### Step 1: Analyze Page Layout

```python
def analyze_page_layout(page: fitz.Page) -> dict:
    """
    Perform spatial semantic segmentation of page.

    Analyzes text block positions to identify zones.

    Returns:
        {
            'body_zone': {'x_start': 100, 'x_end': 500},
            'left_margin': {'x_start': 0, 'x_end': 90},
            'right_margin': {'x_start': 510, 'x_end': 595},
            'page_width': 595,
            'page_height': 842
        }
    """
    blocks = page.get_text("dict")['blocks']

    # Collect all x-coordinates
    x_positions = []
    for block in blocks:
        if block['type'] == 0:  # Text block
            bbox = block['bbox']
            x_positions.append(bbox[0])  # Left edge
            x_positions.append(bbox[2])  # Right edge

    # Analyze distribution
    # Body text typically clustered in center
    # Margins have sparse, consistent x-positions

    # Calculate zones (simple heuristic):
    # - Left margin: x < 15% of page width
    # - Right margin: x > 85% of page width
    # - Body: middle 70%
```

### Step 2: Classify Text Blocks by Zone

```python
def classify_text_blocks(page: fitz.Page, zones: dict) -> dict:
    """
    Classify each text block as body, left-margin, or right-margin.

    Returns:
        {
            'body': [
                {'text': '...', 'y': 450, 'bbox': [...]}
            ],
            'margin_left': [
                {'text': 'A 50', 'y': 452, 'bbox': [...]}
            ],
            'margin_right': [
                {'text': 'note', 'y': 460, 'bbox': [...]}
            ]
        }
    """
    classified = {'body': [], 'margin_left': [], 'margin_right': []}

    for block in page.get_text("dict")['blocks']:
        if block['type'] != 0:
            continue

        bbox = block['bbox']
        x_left = bbox[0]
        y_mid = (bbox[1] + bbox[3]) / 2
        text = extract_text_from_block(block)

        # Classify by x-position
        if x_left < zones['left_margin']['x_end']:
            classified['margin_left'].append({
                'text': text,
                'y': y_mid,
                'bbox': bbox
            })
        elif x_left > zones['right_margin']['x_start']:
            classified['margin_right'].append({
                'text': text,
                'y': y_mid,
                'bbox': bbox
            })
        else:
            classified['body'].append({
                'text': text,
                'y': y_mid,
                'bbox': bbox
            })

    return classified
```

### Step 3: Align Marginalia with Body Text

**Vertical Position Matching**:
```python
def align_marginalia_with_body(classified: dict, tolerance: int = 10) -> list:
    """
    Match marginalia to body text using y-coordinate proximity.

    Args:
        classified: Output from classify_text_blocks()
        tolerance: Vertical pixels tolerance for matching

    Returns:
        [
            {
                'text': 'The transcendental unity...',
                'y': 450,
                'marginalia': [
                    {'side': 'left', 'text': 'A 50', 'y': 452},
                    {'side': 'right', 'text': 'note', 'y': 460}
                ]
            },
            ...
        ]
    """
    aligned = []

    for body_block in classified['body']:
        body_y = body_block['y']
        matched_marginalia = []

        # Find left margin items near this y-position
        for margin in classified['margin_left']:
            if abs(margin['y'] - body_y) <= tolerance:
                matched_marginalia.append({
                    'side': 'left',
                    'text': margin['text'].strip(),
                    'y': margin['y']
                })

        # Find right margin items near this y-position
        for margin in classified['margin_right']:
            if abs(margin['y'] - body_y) <= tolerance:
                matched_marginalia.append({
                    'side': 'right',
                    'text': margin['text'].strip(),
                    'y': margin['y']
                })

        aligned.append({
            'text': body_block['text'],
            'y': body_y,
            'marginalia': matched_marginalia
        })

    return aligned
```

### Step 4: Inject Universal Markers

**Universal Inline Injection**:
```markdown
`[p.102]`

{{margin: "A 50"}} {{margin: "B 75"}} The transcendental unity of
apperception is therefore that unity through which all the manifold
given in an intuition is united in a concept of the object.

{{margin: "A 51"}} {{margin: "B 76"}} But all unification...
```

**Key Points**:
- ALL marginalia uses `{{margin: "exact text"}}`
- Position: Exactly inline where it appears vertically
- No interpretation of what "A 50" means
- Preserves raw marginal content
- User/RAG interprets meaning from context

---

## Proposed Marker Syntax (Simplified)

### Design Principles
1. **Universal format** for all marginalia (don't distinguish types)
2. **Spatial approach** (position-based, not pattern-based)
3. **Readable** in plain text
4. **Parseable** with simple regex
5. **Non-intrusive** to RAG processing

### Syntax Specification

**PDF Pages** (edition-specific, standalone):
```
Format: `[p.N]`
Example: `[p.102]`
Position: Start of page (on own line)
```

**ALL Marginalia** (universal, inline):
```
Format: {{margin: "exact text"}}
Examples:
  {{margin: "A 50"}}          ← Kant A edition
  {{margin: "B 75"}}          ← Kant B edition
  {{margin: "SZ 42"}}         ← Heidegger German pages
  {{margin: "245c"}}          ← Plato Stephanus
  {{margin: "See note 12"}}   ← Generic cross-ref
  {{margin: "nb"}}            ← Generic note
Position: Exactly inline where appears (y-coordinate match)
```

**No Interpretation**:
- Don't parse "A 50" as Kant-specific
- Don't distinguish canonical vs. notes
- Just preserve spatial position and text
- Interpretation happens at query/usage time

### Combined Examples

**Kant's Critique of Pure Reason**:
```markdown
`[p.102]`

{{margin: "A 50"}} {{margin: "B 75"}} The transcendental unity of
apperception is therefore that unity through which all the manifold
given in an intuition is united in a concept of the object.

{{margin: "A 51"}} {{margin: "B 76"}} But all unification of
representations requires a unity of consciousness in the synthesis...
```

**Heidegger's Being and Time**:
```markdown
`[p.58]`

{{margin: "SZ 41"}} Dasein is an entity which does not just occur among
other entities. {{margin: "SZ 42"}} Rather it is ontically distinguished...
```

**Plato's Phaedrus**:
```markdown
`[p.45]`

{{margin: "245c"}} The soul that has lost its wings wanders until it settles
on something solid, {{margin: "245d"}} where it takes up its abode...
```

**Generic Marginalia**:
```markdown
{{margin: "See Introduction"}} This argument presupposes {{margin: "cf. p. 30"}}
the distinction between...
```

---

## Metadata Representation (With Citation System Detection)

### Citation System Detection in Metadata

```json
{
  "document_type": "book",

  "citation_systems": {
    "detected": ["kant_a_b"],
    "primary": "kant_a_b",
    "confidence": 0.95,
    "counts": {
      "kant_a_b": 247,
      "stephanus": 0,
      "bekker": 0
    },
    "description": "Kant's Critique A/B editions (1781/1787)"
  },

  "canonical_mappings": {
    "A 50": {
      "pdf_page": 102,
      "line_start": 1450,
      "line_end": 1455,
      "text_sample": "The transcendental unity of apperception..."
    },
    "B 75": {
      "pdf_page": 102,
      "line_start": 1450,
      "line_end": 1455,
      "text_sample": "The transcendental unity of apperception..."
    }
  },

  "marginalia_statistics": {
    "total_marginalia": 259,
    "citations": 247,
    "notes": 12,
    "left_margin": 247,
    "right_margin": 12
  }
}
```

### Easy Extensibility

**To Add New Citation System** (just update `marginalia_extraction.py`):

```python
CITATION_PATTERNS = {
    # ... existing patterns ...

    'aquinas_summa': {
        'pattern': r'^(I|II|III)(-|,)\s*\d+,\s*\d+$',
        'description': 'Aquinas Summa Theologica',
        'examples': ['I-II, 91, 2', 'I, 2, 3']
    },

    'descartes_meditations': {
        'pattern': r'^(Med\.|Meditation)\s*[IVX]+$',
        'description': 'Descartes Meditations',
        'examples': ['Med. II', 'Meditation III']
    }
}
```

**System auto-detected** from extracted marginalia, recorded in metadata.
```

---

## Extraction Implementation Plan

### Step 1: Margin Zone Detection

```python
def detect_margin_zones(page: fitz.Page) -> dict:
    """
    Identify margin zones based on text distribution.

    Returns:
        {
            'left_margin': (x_start, x_end),
            'right_margin': (x_start, x_end),
            'body': (x_start, x_end),
            'top_margin': (y_start, y_end),
            'bottom_margin': (y_start, y_end)
        }
    """
    # Analyze text block positions across page
    # Identify consistent margin zones
    # Body text typically in center 60-70% of page width
```

### Step 2: Marginalia Pattern Recognition

```python
def parse_marginalia_text(text: str, system: str) -> dict:
    """
    Parse marginalia text based on citation system.

    Args:
        text: Extracted margin text (e.g., "A 50", "245c")
        system: Citation system type ('kant_a_b', 'stephanus', etc.)

    Returns:
        {
            'edition': 'A',  # or 'B', or None
            'number': '50',
            'subsection': None,  # or 'c', 'b15', etc.
            'formatted': '{A:50}'
        }
    """
    patterns = {
        'kant_a_b': r'^([AB])\s*(\d+)$',
        'stephanus': r'^(\d+)([a-e])$',
        'bekker': r'^(\d+)([ab])(\d+)$',
        'german_pages': r'^(\d+)$'
    }
```

### Step 3: Spatial Alignment

```python
def align_marginalia_with_text(body_blocks: list, margin_blocks: list) -> list:
    """
    Match marginalia to corresponding body text using y-coordinates.

    Algorithm:
    1. For each marginalia block, get y-coordinate
    2. Find body text block with closest y-coordinate
    3. Insert marginalia marker at start of that block
    4. Handle multiple marginalia at same position (A/B pairs)

    Returns:
        [
            {
                'text': 'Body text here...',
                'marginalia': ['{A:50}', '{B:75}'],
                'position': {'y': 450, 'line': 1450}
            },
            ...
        ]
    """
```

### Step 4: Markdown Injection

```python
def inject_marginalia_markers(text: str, marginalia: list) -> str:
    """
    Inject marginalia markers inline at appropriate positions.

    Input text:
        "The transcendental unity of apperception is therefore..."

    Marginalia at position:
        ['{A:50}', '{B:75}']

    Output:
        "{A:50} {B:75} The transcendental unity of apperception is therefore..."
    """
```

---

## Testing Strategy

### Test Documents Needed

**1. Kant's Critique of Pure Reason**:
- Preferably Cambridge edition (has A/B marginalia)
- Test extraction of dual edition references
- Verify mapping accuracy

**2. Simpler Test Case**:
- Create mock PDF with margin text
- Known positions and content
- Verify detection and extraction

**3. Edge Cases**:
- Marginalia with line breaks
- Multiple marginalia at same height
- Faint or small margin text (OCR quality)
- Margin numbers vs. body text numbers (disambiguation)

### Test Validation

**Extract and Verify**:
```python
def test_kant_marginalia_extraction():
    """
    Test extraction from Kant's Critique.

    Expected:
    - Detect A/B citation system
    - Extract ~200-300 marginalia markers
    - Align with correct text passages
    - Generate canonical_mappings in metadata
    """
```

**Search and Retrieval**:
```python
def test_search_by_canonical_reference():
    """
    Test finding text by canonical reference.

    Query: "Find passage at A:50"
    Expected: Return correct text with context
    """
```

---

## Implementation Phases

### Phase 1: Detection (High Priority)
- [x] Design marginalia syntax
- [ ] Implement margin zone detection
- [ ] Implement citation system identification
- [ ] Test with Kant Critique

### Phase 2: Extraction (High Priority)
- [ ] Implement spatial alignment algorithm
- [ ] Implement pattern parsing for different systems
- [ ] Inject markers into markdown
- [ ] Generate canonical mappings in metadata

### Phase 3: Validation (Medium Priority)
- [ ] Test with multiple philosophical works
- [ ] Verify citation accuracy
- [ ] Compare with print editions
- [ ] Scholar feedback

### Phase 4: Advanced Features (Future)
- [ ] Auto-detect citation system
- [ ] Cross-reference validation
- [ ] Citation format converters
- [ ] RAG-optimized search by canonical reference

---

## Syntax Disambiguation

### Problem: Multiple Bracket Types

**Current concern**: `[p.N]` for pages, need different format for marginalia

**Solution: Three distinct formats**:

1. **Square brackets with backticks**: `` `[p.N]` `` → PDF page numbers
2. **Curly braces**: `{A:50}` → Canonical marginalia
3. **Double curly**: `{{note: "..."}}` → Annotations

**Visual distinction**: Clear at a glance, parseable with regex

### Regex Patterns

```python
# PDF page markers
PAGE_PATTERN = r'`\[p\.(\d+)\]`'

# Canonical marginalia
MARGINALIA_PATTERN = r'\{([A-Z]+):(\w+)\}'  # {A:50}, {SZ:42}

# Annotations
ANNOTATION_PATTERN = r'\{\{(\w+): "([^"]+)"\}\}'  # {{note: "text"}}
```

---

## RAG Implications

### Search Capabilities Enabled

**By PDF Page**:
```
Query: "Find page 102"
Regex: `\[p\.102\]`
```

**By Canonical Reference**:
```
Query: "Find A:50 in Kant"
Regex: \{A:50\}
Return: Text + context + PDF page mapping
```

**By Annotation**:
```
Query: "Find translator notes"
Regex: \{\{trans: .+\}\}
```

### Metadata-Enhanced Search

```python
def search_by_canonical_ref(ref: str, metadata: dict) -> dict:
    """
    Search using canonical reference.

    Input: "A:50"
    Process:
        1. Look up in canonical_mappings
        2. Get PDF page and line numbers
        3. Extract text from processed markdown
        4. Return with context

    Output:
        {
            'canonical_ref': 'A:50',
            'pdf_page': 102,
            'lines': (1450, 1455),
            'text': 'The transcendental unity...',
            'context_before': '...',
            'context_after': '...'
        }
    """
```

---

## User Workflow Examples

### Citing Kant in Academic Paper

**Traditional Citation**:
```
Kant argues that "the transcendental unity of apperception" (CPR A 50/B 75)
```

**With Our System**:
1. Search metadata for `A:50` → get line numbers
2. Extract text from line 1450-1455
3. Verify against `B:75` (should be same passage)
4. Copy exact text for quotation
5. Use canonical citation in paper

### RAG Query Example

**User**: "What does Kant say about apperception at A:50?"

**System**:
1. Parse query → canonical ref = "A:50"
2. Load metadata → `canonical_mappings['A:50']` → line 1450
3. Extract text from processed markdown
4. Return: "The transcendental unity of apperception is therefore..."

---

## Open Questions

**1. Marginalia Positioning**:
- Start of paragraph? Or exact inline position?
- Current proposal: Start of paragraph/block for readability

**2. Multiple Marginalia**:
- `{A:50}{B:75}` together? Or `{A:50} {B:75}` with space?
- Proposal: Space between for readability

**3. Marginalia Spans**:
- How to handle "A 50-51" (spans multiple numbers)?
- Proposal: `{A:50-51}` or `{A:50}` at start, `{A:51}` at transition

**4. Missing Marginalia**:
- What if PDF marginalia is incomplete/damaged?
- Proposal: Log gaps, don't interpolate

**5. Annotation Content**:
- Allow newlines in annotations?
- Proposal: Use JSON escaping for complex content

---

## Benefits

**For Scholars**:
✅ Universal citations work across editions
✅ Find passages by canonical reference
✅ Preserve scholarly apparatus
✅ Cross-reference between editions

**For RAG**:
✅ Multiple search indices (PDF page + canonical ref)
✅ Richer context for retrieval
✅ Metadata enables smart search
✅ Supports specialized philosophical queries

**For This Project**:
✅ Differentiation from basic PDF processors
✅ Serves serious academic use case
✅ Positions as scholarly tool
✅ Expands to any discipline with canonical refs

---

## Next Steps

1. **Immediate**: Download Kant's Critique with A/B marginalia
2. **Test**: Attempt detection and extraction
3. **Validate**: Compare with print edition
4. **Iterate**: Refine based on results
5. **Generalize**: Apply to Heidegger, Plato, etc.

**This is a significant enhancement that would make this tool invaluable for philosophy research.**
