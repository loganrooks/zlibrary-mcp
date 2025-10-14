# Citation Inference Architecture - Probabilistic OCR Correction

**Date**: 2025-10-13
**Status**: DESIGN PHASE
**Purpose**: Modular, extensible system for citation sequence prediction and OCR correction

---

## Core Problem

### Citations Are Sequential → Enable Probabilistic Correction

**Example (Kant A Edition)**:
```
Extracted: "A 49", "A 50", "A SL", "A 52"
                            ^^^^
                         OCR error
```

**Inference Logic**:
1. Sequence pattern: A 49 → A 50 → ? → A 52
2. Expected: A 51 (simple increment)
3. OCR extracted: "A SL"
4. Visual similarity: "SL" looks like "51" (S=5, L=1)
5. **Correction**: "A SL" → "A 51" (high confidence)

### Different Systems Have Different Increment Logic

| System | Increment Pattern | Example Sequence |
|--------|------------------|------------------|
| Kant A/B | Simple numeric | A 50 → A 51 → A 52 |
| Stephanus | Letter cycling + page wrap | 245c → 245d → 245e → 246a |
| Bekker | Line numbers + column wrap | 184b15 → 184b16 → ... → 185a1 |
| Heidegger SZ | Simple numeric | SZ 41 → SZ 42 → SZ 43 |

**Need modular system**: Each citation type needs its own predictor.

---

## Architecture Design: Plugin System

### Base Class (Abstract)

```python
from abc import ABC, abstractmethod
from typing import Optional, Tuple

class CitationInferenceEngine(ABC):
    """
    Base class for citation sequence prediction and OCR correction.

    Each citation system (Kant, Stephanus, etc.) implements this interface.
    """

    def __init__(self, system_name: str):
        self.system_name = system_name
        self.sequence_history = []  # Track seen citations

    @abstractmethod
    def parse_citation(self, text: str) -> Optional[dict]:
        """
        Parse citation text into components.

        Args:
            text: Citation string (e.g., "A 50", "245c")

        Returns:
            Dict with parsed components or None if invalid
            Example: {'edition': 'A', 'number': 50}
        """
        pass

    @abstractmethod
    def predict_next(self, current: dict) -> dict:
        """
        Predict next citation in sequence.

        Args:
            current: Parsed citation dict

        Returns:
            Dict with predicted next citation
            Example: {'edition': 'A', 'number': 51}
        """
        pass

    @abstractmethod
    def format_citation(self, parsed: dict) -> str:
        """
        Format parsed citation back to string.

        Args:
            parsed: Citation dict

        Returns:
            Formatted string (e.g., "A 51")
        """
        pass

    def ocr_similarity(self, ocr_text: str, expected_text: str) -> float:
        """
        Calculate OCR visual similarity (0-1).

        Common OCR errors:
        - S ↔ 5, O ↔ 0, I ↔ 1, l ↔ 1
        - Character doubling/skipping
        - Similar shapes confused

        Returns:
            Similarity score (0 = no match, 1 = perfect match)
        """
        # Normalize
        ocr = ocr_text.upper().replace(' ', '')
        exp = expected_text.upper().replace(' ', '')

        # Exact match
        if ocr == exp:
            return 1.0

        # Character-level comparison with OCR error table
        ocr_errors = {
            'S': ['5'], 'O': ['0'], 'I': ['1', 'l'],
            'B': ['8'], 'Z': ['2'], 'G': ['6']
        }

        score = 0.0
        max_len = max(len(ocr), len(exp))

        for i in range(min(len(ocr), len(exp))):
            if ocr[i] == exp[i]:
                score += 1.0
            elif exp[i] in ocr_errors.get(ocr[i], []):
                score += 0.8  # Partial credit for known OCR error
            elif ocr[i] in ocr_errors.get(exp[i], []):
                score += 0.8

        # Length penalty
        score = score / max_len if max_len > 0 else 0

        return score

    def correct_citation(self, ocr_text: str, threshold: float = 0.7) -> Tuple[str, float]:
        """
        Attempt to correct OCR'd citation using sequence prediction.

        Algorithm:
        1. Parse OCR text (if possible)
        2. If parsing fails or low confidence:
           a. Predict next expected citation from sequence
           b. Calculate OCR similarity
           c. If similarity > threshold, use prediction
        3. Return corrected citation + confidence

        Args:
            ocr_text: OCR-extracted text
            threshold: Similarity threshold for correction

        Returns:
            (corrected_text, confidence)
        """
        # Try to parse as-is
        parsed = self.parse_citation(ocr_text)

        if parsed:
            # Valid citation, add to history
            self.sequence_history.append(parsed)
            return (ocr_text, 1.0)

        # Parsing failed - attempt correction
        if not self.sequence_history:
            # No history to predict from
            return (ocr_text, 0.0)

        # Predict what citation should be
        last_citation = self.sequence_history[-1]
        predicted = self.predict_next(last_citation)
        predicted_text = self.format_citation(predicted)

        # Check OCR similarity
        similarity = self.ocr_similarity(ocr_text, predicted_text)

        if similarity >= threshold:
            # High confidence correction
            logging.info(f"OCR corrected: '{ocr_text}' → '{predicted_text}' "
                        f"(similarity: {similarity:.2f})")
            self.sequence_history.append(predicted)
            return (predicted_text, similarity)
        else:
            # Low confidence - keep original
            logging.warning(f"OCR error detected but low confidence: '{ocr_text}' "
                          f"vs predicted '{predicted_text}' (similarity: {similarity:.2f})")
            return (ocr_text, 0.0)
```

---

## Specific Inference Engines

### Kant A/B Engine

```python
class KantABInferenceEngine(CitationInferenceEngine):
    """
    Inference engine for Kant's Critique A/B edition citations.

    Increment logic: Simple numeric (A 50 → A 51)
    """

    def __init__(self):
        super().__init__('kant_a_b')

    def parse_citation(self, text: str) -> Optional[dict]:
        """
        Parse: "A 50" → {'edition': 'A', 'number': 50}
        """
        match = re.match(r'^([AB])\s*(\d+)$', text.strip(), re.IGNORECASE)
        if match:
            return {
                'edition': match.group(1).upper(),
                'number': int(match.group(2))
            }
        return None

    def predict_next(self, current: dict) -> dict:
        """
        Predict: A 50 → A 51 (increment number)
        """
        return {
            'edition': current['edition'],
            'number': current['number'] + 1
        }

    def format_citation(self, parsed: dict) -> str:
        """
        Format: {'edition': 'A', 'number': 51} → "A 51"
        """
        return f"{parsed['edition']} {parsed['number']}"
```

### Stephanus Engine

```python
class StephanusInferenceEngine(CitationInferenceEngine):
    """
    Inference engine for Plato Stephanus pagination.

    Increment logic: Letter cycling (245c → 245d → 245e → 246a)
    Letters: a, b, c, d, e (then page increments)
    """

    LETTERS = ['a', 'b', 'c', 'd', 'e']

    def __init__(self):
        super().__init__('stephanus')

    def parse_citation(self, text: str) -> Optional[dict]:
        """
        Parse: "245c" → {'page': 245, 'section': 'c'}
        """
        match = re.match(r'^(\d+)([a-e])$', text.strip(), re.IGNORECASE)
        if match:
            return {
                'page': int(match.group(1)),
                'section': match.group(2).lower()
            }
        return None

    def predict_next(self, current: dict) -> dict:
        """
        Predict: 245c → 245d (next letter)
                 245e → 246a (wrap to next page)
        """
        current_letter = current['section']
        current_index = self.LETTERS.index(current_letter)

        if current_index < len(self.LETTERS) - 1:
            # Next letter in same page
            return {
                'page': current['page'],
                'section': self.LETTERS[current_index + 1]
            }
        else:
            # Wrap to next page, first letter
            return {
                'page': current['page'] + 1,
                'section': self.LETTERS[0]
            }

    def format_citation(self, parsed: dict) -> str:
        """
        Format: {'page': 245, 'section': 'd'} → "245d"
        """
        return f"{parsed['page']}{parsed['section']}"
```

### Bekker Engine

```python
class BekkerInferenceEngine(CitationInferenceEngine):
    """
    Inference engine for Aristotle Bekker numbers.

    Increment logic: Line numbers with column wrapping
    Format: {page}{column}{line}
    Example: 184b15 → 184b16 → ... → 185a1
    """

    def __init__(self):
        super().__init__('bekker')

    def parse_citation(self, text: str) -> Optional[dict]:
        """
        Parse: "184b15" → {'page': 184, 'column': 'b', 'line': 15}
        """
        match = re.match(r'^(\d+)([ab])(\d+)$', text.strip(), re.IGNORECASE)
        if match:
            return {
                'page': int(match.group(1)),
                'column': match.group(2).lower(),
                'line': int(match.group(3))
            }
        return None

    def predict_next(self, current: dict) -> dict:
        """
        Predict: 184b15 → 184b16 (increment line)
                 184b35 → 185a1 (approximate wrap logic)
        """
        # Simple increment (actual Bekker logic is complex)
        # Columns typically have ~35 lines
        if current['line'] < 35:
            return {
                'page': current['page'],
                'column': current['column'],
                'line': current['line'] + 1
            }
        elif current['column'] == 'a':
            # Wrap to column b
            return {
                'page': current['page'],
                'column': 'b',
                'line': 1
            }
        else:
            # Wrap to next page, column a
            return {
                'page': current['page'] + 1,
                'column': 'a',
                'line': 1
            }

    def format_citation(self, parsed: dict) -> str:
        """
        Format: {'page': 184, 'column': 'b', 'line': 15} → "184b15"
        """
        return f"{parsed['page']}{parsed['column']}{parsed['line']}"
```

---

## Engine Registry (Easy Extensibility)

```python
class CitationEngineRegistry:
    """
    Registry for citation inference engines.

    Makes it easy to add new systems without modifying core code.
    """

    _engines = {}

    @classmethod
    def register(cls, system_name: str, engine_class):
        """Register a new citation engine."""
        cls._engines[system_name] = engine_class

    @classmethod
    def get_engine(cls, system_name: str) -> Optional[CitationInferenceEngine]:
        """Get engine for citation system."""
        engine_class = cls._engines.get(system_name)
        return engine_class() if engine_class else None

    @classmethod
    def list_systems(cls) -> List[str]:
        """List all registered citation systems."""
        return list(cls._engines.keys())


# Register built-in engines
CitationEngineRegistry.register('kant_a_b', KantABInferenceEngine)
CitationEngineRegistry.register('stephanus', StephanusInferenceEngine)
CitationEngineRegistry.register('bekker', BekkerInferenceEngine)

# Easy to add new engines:
# CitationEngineRegistry.register('new_system', NewSystemEngine)
```

---

## OCR Correction Pipeline

### Full Workflow

```python
def correct_citation_sequence(citations: List[str], system_name: str) -> List[Tuple[str, float]]:
    """
    Correct sequence of OCR'd citations using probabilistic inference.

    Args:
        citations: List of extracted citation strings
        system_name: Detected citation system

    Returns:
        List of (corrected_citation, confidence) tuples
    """
    engine = CitationEngineRegistry.get_engine(system_name)
    if not engine:
        logging.warning(f"No engine for system: {system_name}")
        return [(c, 0.0) for c in citations]

    corrected = []

    for citation in citations:
        corrected_text, confidence = engine.correct_citation(citation)
        corrected.append((corrected_text, confidence))

    return corrected
```

### Usage in Pipeline

```python
# After spatial extraction and classification
marginalia_extracted = [...]  # From spatial segmentation

# Detect citation system
system_info = detect_citation_systems(marginalia_extracted)
primary_system = system_info['primary_system']

if primary_system:
    # Extract only citations
    citations = [m['text'] for m in marginalia_extracted if m['type'] == 'citation']

    # Run OCR correction
    corrected = correct_citation_sequence(citations, primary_system)

    # Update marginalia with corrected values
    for i, margin in enumerate([m for m in marginalia_extracted if m['type'] == 'citation']):
        margin['text_corrected'] = corrected[i][0]
        margin['ocr_confidence'] = corrected[i][1]
```

---

## Dual Page Numbering System

### Problem: Two Page Number Systems

**PDF File Pages** (technical):
- Page 1 of file
- What PyMuPDF gives us: `page_index = 0, 1, 2, ...`
- Use: File navigation, byte offsets

**Written Page Numbers** (scholarly):
- What's printed on the page
- Front matter: "i", "ii", "iii", "iv", ...
- Main text: "1", "2", "3", ...
- Use: Print edition citation, scholarly reference

### Extraction Strategy

```python
def extract_written_page_number(page) -> Optional[str]:
    """
    Extract written page number from PDF page.

    Looks in typical locations:
    - Top center (header)
    - Bottom center (footer)
    - Top/bottom corners

    Returns:
        Written page number as string (e.g., "xvii", "42", None)
    """
    # Get text with position info
    blocks = page.get_text("dict")['blocks']

    page_rect = page.rect
    page_height = page_rect.height

    # Header zone: top 10% of page
    header_y_max = page_height * 0.1

    # Footer zone: bottom 10% of page
    footer_y_min = page_height * 0.9

    # Look for small text blocks in header/footer
    candidates = []

    for block in blocks:
        if block.get('type') != 0:
            continue

        bbox = block['bbox']
        y_mid = (bbox[1] + bbox[3]) / 2

        # Check if in header or footer
        if y_mid < header_y_max or y_mid > footer_y_min:
            text = extract_text_from_block(block).strip()

            # Check if looks like page number
            if is_page_number_pattern(text):
                candidates.append({
                    'text': text,
                    'y': y_mid,
                    'position': 'header' if y_mid < header_y_max else 'footer'
                })

    # Return most likely candidate
    if candidates:
        # Prefer footer over header (common convention)
        footer_nums = [c for c in candidates if c['position'] == 'footer']
        if footer_nums:
            return footer_nums[0]['text']
        return candidates[0]['text']

    return None


def is_page_number_pattern(text: str) -> bool:
    """
    Check if text looks like a page number.

    Patterns:
    - Arabic numerals: "42", "107"
    - Roman numerals: "i", "xvii", "XXIII"
    - With dashes: "- 42 -"
    """
    text = text.strip().strip('-').strip()

    # Arabic numerals
    if re.match(r'^\d+$', text):
        return True

    # Roman numerals
    if re.match(r'^[ivxlcdm]+$', text, re.IGNORECASE):
        return True

    return False
```

### Dual Page Representation

**In Markdown**:
```markdown
`[pdf:102|written:92]`

{{cite: "A 50"}} The transcendental unity...
```

**Or separate**:
```markdown
`[pdf:102]` `[written:92]`

{{cite: "A 50"}} The transcendental unity...
```

**In Metadata**:
```json
{
  "page_numbering": {
    "pdf_pages": 250,
    "written_page_ranges": [
      {"type": "roman", "pdf_start": 1, "pdf_end": 10, "written_start": "i", "written_end": "x"},
      {"type": "arabic", "pdf_start": 11, "pdf_end": 250, "written_start": "1", "written_end": "240"}
    ]
  },

  "page_mappings": {
    "1": {"pdf": 11, "written": "1"},
    "2": {"pdf": 12, "written": "2"},
    "92": {"pdf": 102, "written": "92"}
  }
}
```

---

## Comprehensive Information Preservation

### What Humans Get from Physical Books

**Current Status**:
- ✅ Text content
- ✅ Headings (H1-H6)
- ✅ Lists (ordered/unordered)
- ✅ Footnotes
- ✅ TOC structure
- ✅ PDF page numbers
- ✅ Marginalia (with this design)
- ⚠️ Written page numbers (proposed)
- ❌ Bold/italic emphasis
- ❌ Images/diagrams
- ❌ Tables
- ❌ Epigraphs
- ❌ Running headers
- ❌ Indentation/block quotes
- ❌ Font changes (e.g., Greek text)

### Enhancement Roadmap

**Phase 1 (Current)**: Structure + Citations
- ✅ Headings, lists, paragraphs
- ✅ Page markers
- ✅ Marginalia extraction
- ✅ Citation inference (proposed)

**Phase 2**: Typography + Layout
- Text emphasis: `**bold**`, `*italic*`
- Block quotes: `>` markdown
- Indentation preservation
- Tables (markdown tables)

**Phase 3**: Rich Content
- Images: `![Figure 1](path)` with extraction
- Diagrams: Reference to extracted files
- Mathematical notation: LaTeX
- Special characters: Greek, mathematical symbols

**Phase 4**: Scholarly Apparatus
- Epigraphs: Extract to metadata
- Running headers: Track section context
- Bibliography: Extract citations
- Index: Preserve if present

---

## Modular Design Benefits

### Easy to Add New Citation Systems

**Step 1**: Define patterns
```python
CITATION_PATTERNS = {
    'new_system': {
        'pattern': r'^REGEX$',
        'description': 'System description',
        'examples': ['ex1', 'ex2']
    }
}
```

**Step 2**: Implement engine
```python
class NewSystemEngine(CitationInferenceEngine):
    def parse_citation(self, text): ...
    def predict_next(self, current): ...
    def format_citation(self, parsed): ...
```

**Step 3**: Register
```python
CitationEngineRegistry.register('new_system', NewSystemEngine)
```

**Done!** System automatically:
- Detects new citation type
- Applies OCR correction
- Builds canonical mappings
- Records in metadata

---

## Edge Cases to Handle

### OCR Errors

**Missing characters**: "A 5" vs "A 50"
- Confidence low if length mismatch significant

**Extra characters**: "A 500" vs "A 50"
- Check sequence gap size

**Character substitution**: "A SL" vs "A 51"
- Use similarity scoring

**Complete garbage**: "XYZ 123"
- Don't correct if similarity < threshold

### Sequence Gaps

**Missing citations**: A 50 → A 52 (no A 51)
- Valid if page skipped
- Don't force-correct
- Log as potential issue

**Multiple citations same line**:
```
{{cite: "A 50"}} {{cite: "B 75"}} Text...
```
- Both valid (parallel editions)
- Track separately

### Ambiguous Patterns

**Simple numbers**: "42"
- Could be: Heidegger SZ, page number, generic note
- Context matters (detect primary system first)
- If uncertain, mark as `{{note: "42"}}`

### Layout Variations

**Center marginalia**: Text in center, not sides
- Header/footer detection
- Section numbers
- Treat as body text unless clearly marginal

**Multi-column texts**: Body text in columns
- Adjust zone detection
- Multiple body zones possible

---

## Metadata Schema (Complete)

```json
{
  "document_type": "book",

  "page_numbering": {
    "pdf_pages": 250,
    "written_pages": 240,
    "written_page_ranges": [
      {"type": "roman", "pdf": [1, 10], "written": ["i", "x"]},
      {"type": "arabic", "pdf": [11, 250], "written": ["1", "240"]}
    ],
    "mappings": {
      "pdf_to_written": {"1": "i", "11": "1", "102": "92"},
      "written_to_pdf": {"i": 1, "1": 11, "92": 102}
    }
  },

  "citation_systems": {
    "detected": ["kant_a_b"],
    "primary": "kant_a_b",
    "confidence": 0.95,
    "description": "Kant's Critique A/B editions"
  },

  "canonical_mappings": {
    "A 50": {
      "pdf_page": 102,
      "written_page": "92",
      "line_start": 1450,
      "text_sample": "..."
    }
  },

  "marginalia_statistics": {
    "total": 259,
    "citations": 247,
    "notes": 12,
    "ocr_corrected": 15,
    "correction_confidence_avg": 0.87
  },

  "ocr_corrections": [
    {
      "original": "A SL",
      "corrected": "A 51",
      "confidence": 0.92,
      "pdf_page": 103,
      "method": "sequence_prediction"
    }
  ]
}
```

---

## Implementation Priority

**Phase 1** (Foundation):
1. Implement base CitationInferenceEngine class
2. Implement KantABInferenceEngine
3. Implement CitationEngineRegistry
4. Test with simple sequence

**Phase 2** (Core Systems):
5. Implement StephanusInferenceEngine
6. Implement BekkerInferenceEngine
7. Implement written page number extraction
8. Integrate into main pipeline

**Phase 3** (Refinement):
9. Add more citation systems as needed
10. Tune OCR similarity thresholds
11. Handle edge cases
12. Real-world testing with Kant, Plato, etc.

---

## Testing Strategy

**Unit Tests**:
- Each engine: parse → predict → format
- OCR similarity scoring
- Edge cases (gaps, errors, ambiguity)

**Integration Tests**:
- Full sequence correction
- System detection
- Dual page numbering

**Real-World Tests**:
- Kant's Critique (A/B system)
- Plato dialogue (Stephanus)
- Heidegger (German pages)

---

**This design is modular, extensible, and handles the complexity properly.**
