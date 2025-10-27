# Advanced Footnote Features: Design Specification

**Version**: 1.0
**Date**: 2025-10-22
**Status**: Design Phase
**Priority**: HIGH (Critical for scholarly accuracy)
**Estimated Effort**: Feature 1 (2-3 days), Feature 2 (4-6 hours)

---

## Executive Summary

Two critical features identified from Kant's Critique testing:

1. **Multi-Page Footnote Continuation**: Detect and merge footnotes spanning multiple pages
2. **Note Type Classification**: Distinguish author notes from translator/editor notes

Both are essential for scholarly document processing accuracy.

---

## Requirement 1: Multi-Page Footnote Continuation

### Problem Statement

Long footnotes span multiple pages but current implementation treats them as:
- Page 1: Incomplete footnote (truncated)
- Page 2: Orphaned content (no marker)

**Example** (Kant p.64-65):
```
Page 64 bottom: "...Our age is the genuine age of criticism, to"  ← INCOMPLETE
Page 65 top:    "which everything must submit. Religion through..." ← CONTINUATION
```

### Detection Signals

**On Sender Page** (where footnote starts):
- ❌ Does NOT end with sentence-final punctuation (., !, ?)
- ✅ Ends with continuation indicators:
  - Prepositions: "to", "of", "in", "with"
  - Conjunctions: "and", "or", "but", "that", "which"
  - Articles: "the", "a", "an"
  - Hyphenation: word ends with "-"
  - Commas: mid-sentence ","

**On Receiver Page** (where it continues):
- ❌ NO marker at content start
- ✅ Footnote-style formatting (small font, bottom area)
- ✅ Starts lowercase or with conjunction/relative pronoun
- ✅ Content flows semantically from previous page

### Algorithm Design

**Phase 1: Incomplete Detection**

```python
import re
from typing import Tuple

def is_footnote_incomplete(text: str) -> Tuple[bool, float, str]:
    """
    Detect incomplete footnotes using NLP and pattern matching.

    Returns:
        (is_incomplete, confidence, reason)
    """
    text = text.rstrip()

    # Level 1: Sentence-final punctuation check
    sentence_endings = ['.', '!', '?', '."', '!"', '?"', '.")', '!)', '?)']

    for ending in sentence_endings:
        if text.endswith(ending):
            return False, 0.95, 'proper_ending'

    # Level 2: Strong continuation indicators
    strong_patterns = {
        r'\s+to$': 'infinitive_to',
        r'\s+and$': 'conjunction_and',
        r'\s+or$': 'conjunction_or',
        r'\s+that$': 'complementizer',
        r'\s+which$': 'relative_pronoun',
        r'\s+the$': 'article',
        r'\s+a$': 'article',
        r'-$': 'hyphenation',
        r',$': 'comma',
    }

    for pattern, reason in strong_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            return True, 0.92, reason

    # Level 3: Weaker indicators
    weak_patterns = {
        r'\s+(in|of|with|for|by|from|upon)$': 'preposition',
        r'\s+(is|are|was|were|be|being)$': 'copula',
        r'\s+(has|have|had)$': 'auxiliary',
    }

    for pattern, reason in weak_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            return True, 0.75, reason

    # Level 4: No punctuation at all (moderate confidence)
    if not any(p in text[-10:] for p in ['.', '!', '?', ';', ':']):
        return True, 0.60, 'no_punctuation'

    # Appears complete
    return False, 0.80, 'uncertain'
```

**Phase 2: Continuation Detection**

```python
def detect_continuation_content(page, prev_incomplete_footnote=None) -> Optional[Dict]:
    """
    Detect orphaned content that continues previous footnote.
    """
    footnote_area = extract_footnote_area(page)

    for block in footnote_area:
        text = extract_text(block).strip()

        # Must have substantial content
        if len(text) < 10:
            continue

        # Check for marker at start (if has marker, it's a NEW footnote)
        if has_marker_at_start(text):
            continue  # Not a continuation

        # Continuation signals
        first_word = text.split()[0] if text else ""

        signals = {
            'starts_lowercase': first_word and first_word[0].islower(),
            'starts_conjunction': first_word.lower() in ['which', 'that', 'and', 'or', 'but', 'when', 'where'],
            'starts_relative': first_word.lower() in ['which', 'who', 'whom', 'whose', 'where', 'when'],
            'in_footnote_area': True,
            'no_marker': True,
            'font_matches': check_font_continuity(block, prev_incomplete_footnote),
        }

        # Compute confidence
        signal_count = sum(signals.values())
        confidence = min(0.95, signal_count / 6.0)

        if confidence > 0.60:
            return {
                'content': text,
                'bbox': block['bbox'],
                'confidence': confidence,
                'signals': signals
            }

    return None
```

**Phase 3: State Machine Implementation**

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class FootnoteWithContinuation:
    """Extended footnote data model supporting multi-page notes."""
    marker: str
    content: str
    pages: List[int]  # Pages this footnote appears on
    bboxes: List[Tuple[float, float, float, float]]  # Bbox per page
    is_complete: bool
    continuation_confidence: float = 1.0

class CrossPageFootnoteParser:
    """
    State machine for parsing footnotes across multiple pages.

    Maintains incomplete footnotes and merges continuations.
    """

    def __init__(self):
        self.incomplete_footnotes: List[FootnoteWithContinuation] = []
        self.completed_footnotes: List[FootnoteWithContinuation] = []

    def process_page(self, page, page_num: int) -> List[FootnoteWithContinuation]:
        """
        Process single page, handling continuations from previous pages.

        Returns:
            Footnotes completed on this page
        """
        completed_this_page = []

        # Step 1: Check for continuations
        if self.incomplete_footnotes:
            continuation = detect_continuation_content(
                page,
                prev_incomplete_footnote=self.incomplete_footnotes[-1]
            )

            if continuation and continuation['confidence'] > 0.60:
                # Merge with most recent incomplete footnote
                incomplete = self.incomplete_footnotes[-1]
                incomplete.content += ' ' + continuation['content']
                incomplete.pages.append(page_num)
                incomplete.bboxes.append(continuation['bbox'])
                incomplete.continuation_confidence = continuation['confidence']

                # Check if NOW complete
                is_incomplete, conf, reason = is_footnote_incomplete(incomplete.content)

                if not is_incomplete or conf < 0.60:
                    # Footnote is now complete
                    incomplete.is_complete = True
                    self.completed_footnotes.append(incomplete)
                    completed_this_page.append(incomplete)
                    self.incomplete_footnotes.pop()

        # Step 2: Detect new footnotes on this page
        new_footnotes = detect_footnotes_on_page(page, page_num)

        for fn_dict in new_footnotes:
            fn = FootnoteWithContinuation(
                marker=fn_dict['marker'],
                content=fn_dict['content'],
                pages=[page_num],
                bboxes=[fn_dict['bbox']],
                is_complete=True  # Assume complete initially
            )

            # Check if incomplete
            is_incomplete, conf, reason = is_footnote_incomplete(fn.content)

            if is_incomplete and conf > 0.70:
                fn.is_complete = False
                self.incomplete_footnotes.append(fn)
            else:
                self.completed_footnotes.append(fn)
                completed_this_page.append(fn)

        return completed_this_page

    def finalize(self) -> List[FootnoteWithContinuation]:
        """
        Call at end of document to handle any remaining incomplete footnotes.
        """
        # Any remaining incomplete footnotes are complete (end of document)
        for incomplete in self.incomplete_footnotes:
            incomplete.is_complete = True
            self.completed_footnotes.append(incomplete)

        self.incomplete_footnotes = []
        return self.completed_footnotes
```

### Edge Cases

1. **False Positive Incomplete**:
   - Footnote ends with "to" but is complete (e.g., "refer to")
   - **Mitigation**: Check next page - if no orphaned content, assume complete

2. **Multiple Continuations**:
   - Very long footnote spans 3+ pages
   - **Mitigation**: State machine handles iteratively

3. **Interleaved Footnotes**:
   - New footnote starts on page 2 before continuation appears
   - **Mitigation**: Match by font similarity and semantic coherence

### Dependencies

- **NLTK** or **spaCy**: Sentence tokenization
- **Existing**: Schema detection, corruption recovery
- **New**: Cross-page state machine

### Performance Impact

- Incomplete detection: ~2ms per footnote
- Continuation matching: ~3ms per page
- **Total overhead**: ~5ms per page ✅ (acceptable)

---

## Design: Note Type Classification

### Classification Schema

```python
from enum import Enum

class NoteType(Enum):
    """Extended note type classification."""
    AUTHOR_NOTE = "author_note"              # Original author's footnote
    TRANSLATOR_NOTE = "translator_note"       # Translator's gloss/comment
    EDITOR_NOTE = "editor_note"               # Editorial annotation
    TRANSLATOR_WORD = "translator_word"       # Single word translation
    CROSS_REFERENCE = "cross_reference"       # Internal document reference
    CITATION = "citation"                     # Bibliographic reference
    UNKNOWN = "unknown"                       # Cannot classify

class NoteSource(Enum):
    """Who created the note."""
    AUTHOR = "author"                         # Kant, Derrida, etc.
    TRANSLATOR = "translator"                 # Translation team
    EDITOR = "editor"                         # Editorial team
    MODERN_ANNOTATOR = "modern_annotator"     # Contemporary scholars
    UNKNOWN = "unknown"
```

### Classification Algorithm

**Step 1: Schema-Based Classification**

```python
def classify_by_schema(marker: str, schema_type: str, marker_info: Dict) -> NoteType:
    """
    Primary classification using marker schema.

    Heuristics learned from academic publishing conventions:
    - Alphabetic lowercase (a,b,c) → Translator notes
    - Numeric superscript (1,2,3) → Author original notes
    - Symbolic sequence (*, †, ‡) → Translator notes (modern editions)
    - Single asterisk with long content → Editor commentary
    """
    # Alphabetic lowercase → translator
    if marker.isalpha() and marker.islower() and len(marker) == 1:
        return NoteType.TRANSLATOR_NOTE

    # Numeric superscript → author
    if marker.isdigit() and marker_info.get('is_superscript', False):
        return NoteType.AUTHOR_NOTE

    # Symbolic sequence → translator (modern convention)
    if marker in ['*', '†', '‡', '§', '¶'] and schema_type == 'symbolic':
        # Exception: single * with very long content → editor
        if marker == '*' and len(marker_info.get('content', '')) > 200:
            return NoteType.EDITOR_NOTE
        return NoteType.TRANSLATOR_NOTE

    return NoteType.UNKNOWN
```

**Step 2: Content-Based Validation**

```python
def validate_classification_by_content(
    note_text: str,
    preliminary_type: NoteType
) -> Tuple[NoteType, float]:
    """
    Validate classification using content analysis.

    Signals:
    - German/foreign words → translator note
    - "See Chapter X" → cross-reference
    - Citation format → citation note
    - Editorial voice → editor note
    """
    confidence = 0.80  # Default

    # Signal 1: Single foreign word → translator word
    if len(note_text.split()) <= 3 and not note_text[0].isupper():
        return NoteType.TRANSLATOR_WORD, 0.92

    # Signal 2: Editorial indicators
    editorial_phrases = [
        'as in the first edition',
        'kant wrote',
        'kant\'s text reads',
        'we follow',
        'the editors',
        'this edition',
    ]

    if any(phrase in note_text.lower() for phrase in editorial_phrases):
        return NoteType.EDITOR_NOTE, 0.90

    # Signal 3: Translation indicators
    if any(word in note_text for word in ['literal', 'german:', 'lat:', 'greek:']):
        return NoteType.TRANSLATOR_NOTE, 0.88

    # Signal 4: Cross-reference
    if re.search(r'see\s+(chapter|section|page|note)\s+\d+', note_text, re.IGNORECASE):
        return NoteType.CROSS_REFERENCE, 0.85

    # Signal 5: Citation format
    if re.search(r'[A-Z][a-z]+,\s+\d{4}|ibid\.|op\.\s*cit\.', note_text, re.IGNORECASE):
        return NoteType.CITATION, 0.85

    # No strong signal - trust schema classification
    return preliminary_type, confidence
```

**Step 3: Multi-Factor Fusion**

```python
def classify_note_comprehensive(
    marker: str,
    content: str,
    schema_type: str,
    marker_info: Dict,
    document_metadata: Dict
) -> Dict:
    """
    Comprehensive note classification using multiple signals.

    Returns classification with confidence and evidence.
    """
    # Primary classification from schema
    schema_class = classify_by_schema(marker, schema_type, marker_info)

    # Validation from content
    content_class, content_conf = validate_classification_by_content(content, schema_class)

    # Resolution if disagreement
    if schema_class != content_class:
        # Content has higher confidence for editor vs translator distinction
        if content_class in [NoteType.EDITOR_NOTE, NoteType.TRANSLATOR_WORD]:
            final_class = content_class
            final_conf = content_conf * 0.90  # Slight penalty for disagreement
        else:
            # Schema has higher confidence for author vs translator
            final_class = schema_class
            final_conf = 0.75  # Moderate confidence due to disagreement
    else:
        # Agreement - high confidence
        final_class = schema_class
        final_conf = min(0.95, content_conf * 1.10)

    return {
        'note_type': final_class,
        'confidence': final_conf,
        'evidence': {
            'schema_indicates': schema_class,
            'content_indicates': content_class,
            'marker': marker,
            'schema_type': schema_type,
        }
    }
```

### Implementation in NoteInfo

```python
# Update lib/rag_data_models.py
@dataclass
class NoteInfo:
    note_type: NoteType
    note_source: NoteSource  # NEW: who created the note
    role: NoteRole
    marker: str
    scope: NoteScope

    # Multi-page support (NEW)
    pages: List[int] = field(default_factory=list)
    is_continued: bool = False
    continued_from: Optional[str] = None
    continuation_confidence: float = 1.0

    # Classification metadata (NEW)
    classification_confidence: float = 1.0
    classification_method: str = "schema_based"
```

---

## Implementation Plan

### Phase 1: Note Type Classification (4-6 hours)

**Day 1**:
- [ ] Add `NoteSource` enum to `rag_data_models.py`
- [ ] Implement `classify_by_schema()` function
- [ ] Implement `validate_classification_by_content()`
- [ ] Integrate into `apply_corruption_recovery()`
- [ ] Unit tests for classification

**Deliverable**: Notes tagged with type (author/translator/editor)

**Test Cases**:
- Kant alphabetic → `translator_note`
- Kant numeric → `author_note`
- Kant asterisk → `editor_note`
- Derrida symbolic → `translator_note`

### Phase 2: Multi-Page Continuation (2-3 days)

**Day 1**: Incomplete detection
- [ ] Implement `is_footnote_incomplete()` with pattern matching
- [ ] Add sentence tokenization (NLTK or regex-based)
- [ ] Unit tests for incomplete detection (~20 test cases)

**Day 2**: Continuation matching
- [ ] Implement `detect_continuation_content()`
- [ ] Implement `CrossPageFootnoteParser` state machine
- [ ] Integration tests with multi-page PDFs

**Day 3**: Integration and testing
- [ ] Integrate into `process_pdf()` pipeline
- [ ] Real-world testing on Kant asterisk footnote
- [ ] Performance validation (<5ms overhead)

**Deliverable**: Multi-page footnotes correctly merged

**Test Cases**:
- Kant page 64-65 asterisk footnote (continues)
- Short footnote ending properly (no false continuation)
- Multiple continuations in sequence

---

## Test Strategy

### Test Case 1: Kant Asterisk Footnote (Multi-Page)

**Ground Truth**:
```json
{
  "marker": "*",
  "pages": [1, 2],
  "content_page1_ends": "...age of criticism, to",
  "content_page2_starts": "which everything must submit...",
  "is_continued": true,
  "note_type": "editor_note",
  "note_source": "translator",
  "full_content": "Now and again one hears...to which everything must submit. Religion..."
}
```

**Validation**:
- ✅ Detects incomplete on page 1 (ends with "to")
- ✅ Finds continuation on page 2 (starts with "which")
- ✅ Merges into single footnote
- ✅ Classifies as editor_note (long, editorial voice)

### Test Case 2: Translator Word Notes

**Ground Truth**:
```json
{
  "marker": "b",
  "content": "aufgegeben",
  "note_type": "translator_word",
  "note_source": "translator"
}
```

**Validation**:
- ✅ Alphabetic schema → translator
- ✅ Single word → translator_word subtype
- ✅ No continuation (complete)

### Test Case 3: Author Numeric Notes

**Ground Truth**:
```json
{
  "marker": "2",
  "is_superscript": true,
  "note_type": "author_note",
  "note_source": "author"
}
```

**Validation**:
- ✅ Numeric superscript → author
- ✅ Distinguished from translator alphabetic

---

## Dependencies

### Required Libraries

```python
# Option A: Regex-based (no dependencies)
import re  # Already have

# Option B: NLP-based (better accuracy)
pip install nltk  # Sentence tokenization
# OR
pip install spacy  # More sophisticated NLP
```

**Recommendation**: Start with regex-based (no new dependencies), add NLP if needed for accuracy.

### Data Model Updates

```python
# lib/rag_data_models.py
from enum import Enum

class NoteSource(Enum):
    AUTHOR = "author"
    TRANSLATOR = "translator"
    EDITOR = "editor"
    MODERN_ANNOTATOR = "modern_annotator"
    UNKNOWN = "unknown"

# Update NoteInfo dataclass (already exists, needs fields added)
```

---

## Performance Considerations

| Operation | Complexity | Time (est) | Impact |
|-----------|------------|------------|--------|
| Incomplete detection | O(1) per footnote | ~1ms | Minimal |
| Continuation matching | O(1) per page | ~2ms | Minimal |
| Content classification | O(1) per footnote | ~1ms | Minimal |
| **Total Overhead** | O(n) pages | **~4ms/page** | ✅ Acceptable |

**Memory**: O(k) where k = max concurrent incomplete footnotes (typically 1-2)

---

## Edge Cases to Handle

### Multi-Page Continuations

1. **Very Long Footnotes** (3+ pages)
   - Solution: Iterative state machine
   - Test: Find 600+ word footnote in corpus

2. **False Incomplete Detection**
   - Example: "refers to" at end but is complete
   - Solution: Check next page, if no continuation found, mark complete

3. **Continuation Ambiguity**
   - Multiple incomplete footnotes on same page
   - Solution: Match by font similarity and marker sequence

### Note Type Classification

1. **Mixed Authorship**
   - Translator adds to author's note
   - Solution: Primary source classification + metadata flag

2. **Modern Scholarly Editions**
   - Multiple layers of notes (author + translator + editor + modern scholar)
   - Solution: Support note hierarchy in data model

3. **Ambiguous Markers**
   - Same marker used for different types
   - Solution: Content-based classification takes precedence

---

## Output Format

### Markdown Representation

```markdown
## Footnotes

### Author Notes (Kant)

[^2]: Beginning of the world discussion...
[^3]: Metaphysical principles...

### Translator Notes

[^a]: aufgegeben (German: "given up")
[^b]: Vermögen (German: "capacity")

### Editor Notes

[^*]: Now and again one hears complaints about the superficiality of our age's way
of thinking, and about the decay of well-grounded science...
*[Continues from previous page]*
...to which everything must submit. Religion through its holiness and legislation
through its majesty commonly seek to exempt themselves from it.
*Pages: 64-65*
```

### JSON Representation

```json
{
  "footnotes": [
    {
      "marker": "*",
      "note_type": "editor_note",
      "note_source": "translator",
      "content": "Full merged content...",
      "pages": [64, 65],
      "is_continued": true,
      "continuation_confidence": 0.92,
      "classification_confidence": 0.88
    }
  ]
}
```

---

## Validation Strategy

### Automated Validation (Level 1)

```python
def validate_footnote_continuations(footnotes: List[FootnoteWithContinuation]):
    """
    Automated checks for continuation logic.
    """
    issues = []

    # Check 1: No orphaned continuations
    for fn in footnotes:
        if fn.is_continued and len(fn.pages) < 2:
            issues.append(f"Footnote {fn.marker} marked as continued but only on 1 page")

    # Check 2: Continuation confidence thresholds
    low_conf = [fn for fn in footnotes if fn.is_continued and fn.continuation_confidence < 0.60]
    if low_conf:
        issues.append(f"{len(low_conf)} continuations with low confidence - flag for review")

    # Check 3: Schema consistency within note type
    author_markers = [fn.marker for fn in footnotes if fn.note_type == NoteType.AUTHOR_NOTE]
    if author_markers and not all(m.isdigit() for m in author_markers):
        issues.append("Author notes have non-numeric markers (schema inconsistency)")

    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'review_needed': len(low_conf) if 'low_conf' in locals() else 0
    }
```

### Agent Verification (Level 2)

Use Claude agent to verify:
- Multi-page footnotes read coherently
- Note type assignments make sense
- No semantic breaks in continuations

### Human Review (Level 3)

Flag for human review if:
- Continuation confidence < 0.60
- Classification disagreement (schema vs content)
- Very long continuations (>3 pages)

---

## Implementation Checklist

### Pre-Implementation

- [ ] Review this design document
- [ ] Decide on NLP library (regex vs NLTK vs spaCy)
- [ ] Update `rag_data_models.py` with new fields
- [ ] Create test fixtures (multi-page footnotes)

### Implementation (Priority Order)

**Week 1**:
- [ ] Feature 2: Note type classification (easier, 4-6 hours)
  - [ ] Implement classification functions
  - [ ] Integrate into pipeline
  - [ ] Unit tests (15-20 tests)
  - [ ] Validate on Kant + Derrida

**Week 2**:
- [ ] Feature 1: Multi-page continuations (harder, 2-3 days)
  - [ ] Implement incomplete detection
  - [ ] Implement continuation matching
  - [ ] State machine integration
  - [ ] Real-world testing on Kant asterisk footnote

### Post-Implementation

- [ ] Update ground truth schema v2
- [ ] Add tests to `test_real_footnotes.py`
- [ ] Update `PFES_TIER1_IMPLEMENTATION.md`
- [ ] Performance benchmarking
- [ ] Create ADR documenting design decisions

---

## Success Metrics

### Feature 1: Multi-Page Continuations

- ✅ Detects 95%+ of incomplete footnotes
- ✅ <5% false positives on continuation detection
- ✅ Handles 1-5 page spans
- ✅ Performance overhead <5ms per page

### Feature 2: Note Type Classification

- ✅ 90%+ accuracy on author vs translator distinction
- ✅ 85%+ accuracy on detailed type classification
- ✅ Confidence scores calibrated (low confidence → review)
- ✅ No performance overhead (classification during parsing)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| False incomplete detection | Medium | Medium | Conservative thresholds + next-page validation |
| Continuation mismatch | Low | High | Font similarity + semantic checks |
| Type misclassification | Low | Low | Content validation + confidence scores |
| Performance degradation | Low | Medium | Profile and optimize |
| Complex edge cases | Medium | Medium | Comprehensive test suite |

---

## Next Steps

**Option A: Implement Both Features** (3-4 days)
- Full implementation with testing
- Production-ready multi-page + classification

**Option B: Implement Classification Only** (6 hours)
- Quick win, high value
- Defer continuations to later

**Option C: Design Review First** (1 hour)
- Review this spec
- Refine algorithms
- Then implement

**Recommendation**: **Option C → Option B → Option A**
- Review design carefully (you emphasized this)
- Implement easy feature first (classification)
- Then tackle complex feature (continuations)

---

**Status**: Ready for design review and implementation planning
**Complexity**: Medium (both features are implementable with existing tools)
**Value**: Very High (critical for scholarly accuracy)
