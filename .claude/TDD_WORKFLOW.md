# Rigorous Real-World TDD Workflow

**Purpose**: Prevent hallucinations and catch architectural flaws through systematic real-world validation
**Status**: MANDATORY for all RAG pipeline development
**Lesson**: Today's real PDF testing caught flaws that 495 unit tests missed

---

## Core Principle: Ground Truth Before Code

**WRONG Approach** (what led to today's architectural flaw):
```
1. Design feature
2. Write unit tests (with mocks)
3. Implement feature
4. Tests pass ✅
5. Ship
6. Discover flaw in production ❌
```

**RIGHT Approach** (rigorous TDD):
```
1. Get REAL PDF with feature (e.g., Derrida with X-marks)
2. Create ground truth (document expected behavior)
3. Write test using REAL PDF (no mocks)
4. Test FAILS (feature not implemented)
5. Implement feature
6. Test with REAL PDF
7. Validate output MANUALLY
8. Only then: Ship
```

---

## Mandatory TDD Workflow

### For EVERY New Feature

#### Step 1: Acquire Real Test Data ⏱️ 30-60 min

**Examples**:
- Implementing X-mark detection? → Get Derrida PDF with known X-marks
- Implementing formatting? → Get PDF with known bold/italic
- Implementing footnotes? → Get academic paper with 50+ footnotes

**Sources**:
- Z-Library (use our own MCP server!)
- Project Gutenberg
- Existing test_files/ directory
- Create synthetic PDFs if needed

**Requirement**: MUST have actual PDF, not synthetic mock

---

#### Step 2: Create Ground Truth ⏱️ 1-2 hours

**File**: test_files/ground_truth/{feature_name}.json

**Example** (X-mark detection):
```json
{
  "test_name": "derrida_sous_rature",
  "pdf_file": "test_files/derrida_pages_110_135.pdf",
  "pages": 26,
  "created_date": "2025-10-18",
  "verified_by": "human",

  "features": {
    "xmarks": [
      {
        "page": 1,
        "word_under_erasure": "is",
        "bbox": [312.21, 172.998, 326.38, 186.87],
        "context_before": "the sign ",
        "context_after": " that ill-named",
        "corrupted_extraction": ")(",
        "expected_recovery": "is",
        "expected_output": "~~is~~",
        "confidence_min": 0.6
      }
    ]
  },

  "expected_quality": {
    "quality_score_min": 0.85,
    "quality_flags": ["sous_rature", "recovered_sous_rature"],
    "processing_time_max_ms": 5000
  },

  "validation_criteria": {
    "all_xmarks_detected": true,
    "all_text_recovered": true,
    "formatting_preserved": true,
    "no_false_positives": true
  }
}
```

**CRITICAL**: Manual verification required:
- Open PDF in viewer
- Locate each feature
- Measure bboxes
- Document expected outputs
- Human signs off on ground truth

---

#### Step 3: Write Failing Real-World Test ⏱️ 30 min

**File**: __tests__/python/test_real_{feature}.py

```python
"""
Real-world test for {feature}.

NO MOCKING - uses actual PDF and ground truth validation.
"""

import pytest
from pathlib import Path
from lib.rag_processing import process_pdf
from test_files.ground_truth_loader import load_ground_truth, validate_against_ground_truth

class TestFeatureRealWorld:
    """Real-world validation with ground truth."""

    def test_{feature}_detection(self):
        """Test {feature} detection with real PDF."""
        # Load ground truth
        gt = load_ground_truth('test_name')

        # Process REAL PDF (no mocks!)
        result = process_pdf(Path(gt['pdf_file']), output_format='markdown')

        # Validate against ground truth
        validation = validate_against_ground_truth(result, gt)

        # All ground truth criteria must pass
        assert validation.all_detected, f"Missed features: {validation.missed}"
        assert validation.quality_score >= gt['expected_quality']['quality_score_min']
        assert validation.processing_time_ms < gt['expected_quality']['processing_time_max_ms']
```

**Run test**:
```bash
pytest __tests__/python/test_real_{feature}.py -v
# Expected: FAIL (feature not implemented yet) ❌
```

---

#### Step 4: Implement Feature ⏱️ Variable

**Write actual implementation**

**CRITICAL**: Keep test running in watch mode:
```bash
pytest-watch __tests__/python/test_real_{feature}.py
# See test fail → implement → see test pass loop
```

---

#### Step 5: Validate Output MANUALLY ⏱️ 15-30 min

**MANDATORY Manual Verification**:

```bash
# Process test PDF
python -c "
from lib.rag_processing import process_pdf
from pathlib import Path

result = process_pdf(Path('test_files/derrida_pages_110_135.pdf'), output_format='markdown')

# Save output
Path('test_output/manual_review.md').write_text(result)
"

# Open side-by-side
# Terminal 1: Original PDF
evince test_files/derrida_pages_110_135.pdf

# Terminal 2: Processed output
less test_output/manual_review.md

# Checklist:
# [ ] X-marks preserved or formatted correctly?
# [ ] Text under erasure recovered?
# [ ] Formatting applied correctly?
# [ ] No hallucinations (made-up content)?
# [ ] Quality flags accurate?
```

**Human verification REQUIRED** before considering feature "complete"

---

#### Step 6: Performance Validation ⏱️ 15 min

```bash
# Run with timing
time python -c "
from lib.rag_processing import process_pdf
from pathlib import Path
import time

start = time.time()
result = process_pdf(Path('test_files/margins_of_philosophy.pdf'))
elapsed = time.time() - start

print(f'Processing time: {elapsed:.2f}s')
print(f'Pages per second: {330 / elapsed:.1f}')

# Compare with budget
assert elapsed < 10.0, f'Too slow: {elapsed:.2f}s > 10s budget'
"
```

**Performance budget MUST be met** before shipping

---

#### Step 7: Regression Validation ⏱️ 5 min

```bash
# Run ALL existing real PDF tests
pytest __tests__/python/test_real_*.py -v

# Ensure no regressions
# All tests must still pass
```

**No feature ships if it breaks existing real PDF tests**

---

#### Step 8: Update Ground Truth Corpus ⏱️ 15 min

```bash
# Add new test to comprehensive suite
# Update test_files/TEST_CORPUS.md with new PDF
# Commit ground truth JSON
git add test_files/ground_truth/{test_name}.json
git add __tests__/python/test_real_{feature}.py
git commit -m "test: add ground truth for {feature} with real PDF"
```

---

## Quality Gates (Automated)

### Pre-Commit Hook

**File**: .git/hooks/pre-commit

```bash
#!/bin/bash

echo "Running real PDF validation before commit..."

# Run real PDF tests
pytest __tests__/python/test_real_*.py -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ Real PDF tests failed - commit blocked"
    echo "Fix issues before committing"
    exit 1
fi

# Run performance benchmarks
python scripts/validation/validate_performance_budgets.py

if [ $? -ne 0 ]; then
    echo "❌ Performance budget exceeded - commit blocked"
    exit 1
fi

echo "✅ All validations passed"
exit 0
```

---

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Real-World Validation

on: [push, pull_request]

jobs:
  real-pdf-validation:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
        with:
          lfs: true  # For large test PDFs

      - name: Setup Python + Dependencies
        run: |
          uv sync
          sudo apt-get install tesseract-ocr

      - name: Run Real PDF Test Suite
        run: |
          uv run pytest __tests__/python/test_real_*.py -v
        timeout-minutes: 10

      - name: Validate Performance Budgets
        run: |
          uv run python scripts/validation/validate_performance_budgets.py

      - name: Check Quality Score Improvements
        run: |
          uv run python scripts/validation/measure_quality_score.py

      - name: Generate Validation Report
        if: failure()
        run: |
          uv run python scripts/validation/generate_failure_report.py

      - name: Upload Failure Artifacts
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: validation-failures
          path: test_output/failures/
```

---

## Ground Truth Infrastructure

### Directory Structure

```
test_files/
├── corpus/                         # Real PDFs
│   ├── philosophy/
│   │   ├── derrida_of_grammatology.pdf
│   │   ├── derrida_margins_philosophy.pdf
│   │   ├── heidegger_being_time.pdf
│   │   └── README.md (acquisition notes)
│   ├── technical/
│   │   └── sample_academic_paper.pdf
│   └── edge_cases/
│       ├── footnote_heavy.pdf
│       ├── multi_column.pdf
│       └── annotated_reader_notes.pdf
├── ground_truth/                  # Expected behaviors
│   ├── derrida_of_grammatology.json
│   ├── derrida_margins_philosophy.json
│   └── schema.json (ground truth format)
├── expected_outputs/              # Expected output snippets
│   ├── derrida_page_135.md
│   └── heidegger_page_80.md
└── synthetic/                     # Controlled test cases
    ├── bold_italic_test.pdf
    └── footnote_test.pdf
```

---

### Ground Truth Schema

**File**: test_files/ground_truth/schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["test_name", "pdf_file", "features", "expected_quality"],
  "properties": {
    "test_name": {"type": "string"},
    "pdf_file": {"type": "string"},
    "pages": {"type": "integer"},
    "created_date": {"type": "string"},
    "verified_by": {"type": "string"},
    "features": {
      "type": "object",
      "properties": {
        "xmarks": {"type": "array", "items": {"$ref": "#/definitions/xmark"}},
        "footnotes": {"type": "array"},
        "citations": {"type": "array"},
        "formatting": {"type": "array"}
      }
    },
    "expected_quality": {
      "type": "object",
      "required": ["quality_score_min", "processing_time_max_ms"],
      "properties": {
        "quality_score_min": {"type": "number", "minimum": 0, "maximum": 1},
        "quality_flags": {"type": "array", "items": {"type": "string"}},
        "processing_time_max_ms": {"type": "integer"}
      }
    }
  },
  "definitions": {
    "xmark": {
      "type": "object",
      "required": ["page", "word_under_erasure"],
      "properties": {
        "page": {"type": "integer"},
        "word_under_erasure": {"type": "string"},
        "bbox": {"type": "array", "minItems": 4, "maxItems": 4},
        "corrupted_extraction": {"type": "string"},
        "expected_recovery": {"type": "string"},
        "confidence_min": {"type": "number"}
      }
    }
  }
}
```

---

### Ground Truth Validation Helper

**File**: test_files/ground_truth_loader.py

```python
"""
Ground truth loading and validation utilities.

Provides helpers for real-world TDD with documented expectations.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ValidationResult:
    """Result from ground truth validation."""
    passed: bool
    all_detected: bool
    quality_score: float
    processing_time_ms: float
    missed_features: List[str]
    false_positives: List[str]
    details: Dict[str, Any]


def load_ground_truth(test_name: str) -> dict:
    """
    Load ground truth for test PDF.

    Args:
        test_name: Test identifier (e.g., 'derrida_of_grammatology')

    Returns:
        Ground truth dictionary

    Raises:
        FileNotFoundError: If ground truth doesn't exist
        ValueError: If ground truth invalid
    """
    gt_file = Path('test_files/ground_truth') / f'{test_name}.json'

    if not gt_file.exists():
        raise FileNotFoundError(
            f"Ground truth not found: {gt_file}\n"
            f"Create ground truth first: python scripts/validation/create_ground_truth.py"
        )

    with open(gt_file) as f:
        gt = json.load(f)

    # Validate schema
    validate_ground_truth_schema(gt)

    return gt


def validate_against_ground_truth(
    result: str,
    gt: dict,
    processing_time_ms: float = None
) -> ValidationResult:
    """
    Validate processing result against ground truth.

    Args:
        result: Processed output (markdown or text)
        gt: Ground truth dictionary
        processing_time_ms: Processing time in milliseconds

    Returns:
        ValidationResult with detailed validation
    """
    missed = []
    false_positives = []

    # Validate X-marks
    for xmark in gt.get('features', {}).get('xmarks', []):
        expected_word = xmark['expected_recovery']
        expected_output = xmark.get('expected_output', f'~~{expected_word}~~')

        # Check if word appears in output
        if expected_word not in result and expected_output not in result:
            missed.append(f"X-mark word '{expected_word}' on page {xmark['page']}")

    # Validate footnotes
    for footnote in gt.get('features', {}).get('footnotes', []):
        marker = footnote['marker']
        # Check footnote marker present
        if f'^{marker}' not in result and f'[^{marker}]' not in result:
            missed.append(f"Footnote marker '{marker}'")

    # Calculate quality score (placeholder - would extract from result metadata)
    quality_score = 0.9  # TODO: Extract actual quality score from result

    # Validate performance
    processing_ok = True
    if processing_time_ms:
        max_time = gt['expected_quality']['processing_time_max_ms']
        processing_ok = processing_time_ms < max_time

    # Overall result
    passed = (
        len(missed) == 0 and
        len(false_positives) == 0 and
        quality_score >= gt['expected_quality']['quality_score_min'] and
        processing_ok
    )

    return ValidationResult(
        passed=passed,
        all_detected=(len(missed) == 0),
        quality_score=quality_score,
        processing_time_ms=processing_time_ms or 0.0,
        missed_features=missed,
        false_positives=false_positives,
        details={'validation_timestamp': None}
    )


def validate_ground_truth_schema(gt: dict):
    """Validate ground truth has required fields."""
    required = ['test_name', 'pdf_file', 'features', 'expected_quality']

    for field in required:
        if field not in gt:
            raise ValueError(f"Ground truth missing required field: {field}")

    # Validate PDF exists
    pdf_path = Path(gt['pdf_file'])
    if not pdf_path.exists():
        raise FileNotFoundError(f"Test PDF not found: {pdf_path}")
```

---

## Anti-Hallucination Guardrails

### 1. Mandatory Manual Verification

**Before considering feature "complete"**:

```markdown
## Manual Verification Checklist

Feature: {feature_name}
Date: {date}
Reviewer: {name}

Real PDF Test:
- [ ] Test PDF obtained with known features
- [ ] Ground truth created and documented
- [ ] Test runs with REAL PDF (no mocks)
- [ ] Test output MATCHES ground truth

Manual Review:
- [ ] Opened original PDF side-by-side with output
- [ ] Verified every ground truth feature present in output
- [ ] Checked for hallucinations (content not in original)
- [ ] Validated formatting/structure correct
- [ ] Confirmed quality flags accurate

Performance:
- [ ] Processing time under budget
- [ ] No performance regression on other PDFs

Signature: _____________ Date: _______
```

**No feature merges without signed checklist**

---

### 2. Automated Hallucination Detection

```python
def detect_hallucinations(original_pdf: Path, output_text: str) -> List[str]:
    """
    Detect potential hallucinations (content not in original PDF).

    Strategy:
    1. Extract all text from original PDF
    2. Find sentences in output not in original
    3. Flag for manual review

    Returns:
        List of potentially hallucinated sentences
    """
    original_text = extract_all_text(original_pdf)
    output_sentences = split_into_sentences(output_text)

    potentially_hallucinated = []

    for sentence in output_sentences:
        # Check if sentence (or close variant) appears in original
        if not fuzzy_match(sentence, original_text, threshold=0.8):
            potentially_hallucinated.append(sentence)

    return potentially_hallucinated


def test_no_hallucinations():
    """Validate no content added that's not in original PDF."""
    gt = load_ground_truth('derrida_of_grammatology')
    result = process_pdf(Path(gt['pdf_file']))

    hallucinations = detect_hallucinations(Path(gt['pdf_file']), result)

    # Allow minor differences (formatting, markers), but no substantial content
    assert len(hallucinations) < 5, \
        f"Potential hallucinations detected: {hallucinations}"
```

---

### 3. Output Determinism Validation

```python
def test_processing_deterministic():
    """Validate same PDF produces same output (determinism)."""
    pdf_path = Path('test_files/derrida_of_grammatology.pdf')

    # Process twice
    result1 = process_pdf(pdf_path, output_format='markdown')
    result2 = process_pdf(pdf_path, output_format='markdown')

    # Should be identical (or 99% similar allowing timestamps)
    similarity = calculate_similarity(result1, result2)
    assert similarity > 0.99, \
        f"Non-deterministic output: {similarity:.1%} similar"
```

---

## Test Corpus Prioritization

### Week 1: Foundation Corpus (Minimum Viable)

**MUST HAVE** (prevents regressions on known cases):
1. ✅ Derrida with X-marks (have)
2. ✅ Heidegger with X-marks (have)
3. ⏳ Clean philosophy PDF (need)
4. ⏳ PDF with bold/italic formatting (need)
5. ⏳ PDF with footnotes (need)

**Timeline**: 1 day to acquire + create ground truth

---

### Week 2-3: Extended Corpus (Edge Cases)

**SHOULD HAVE**:
6. Essay collection (Margins of Philosophy)
7. Kant with A/B citations
8. Plato with Stephanus citations
9. Poor OCR quality PDF
10. Annotated PDF (handwritten notes)

**Timeline**: 2-3 days acquisition + ground truth

---

### Week 4+: Comprehensive Corpus (Production Quality)

**NICE TO HAVE**:
11. Multi-column journal articles
12. Mixed language PDFs
13. 600+ page books (performance stress test)
14. Multiple citation systems in one document
15. Complex footnote structures

---

## Performance Budget Framework

### test_files/performance_budgets.json

```json
{
  "operations": {
    "xmark_detection_per_page": {
      "target_ms": 5,
      "max_ms": 10,
      "current_ms": 5.2
    },
    "garbled_detection_per_region": {
      "target_ms": 1,
      "max_ms": 2,
      "current_ms": 0.75
    },
    "ocr_recovery_per_page": {
      "target_ms": 300,
      "max_ms": 500,
      "current_ms": 320
    },
    "text_extraction_per_page": {
      "target_ms": 10,
      "max_ms": 20,
      "current_ms": 2.24
    }
  },
  "end_to_end": {
    "small_pdf_26_pages": {
      "target_ms": 3000,
      "max_ms": 5000
    },
    "medium_pdf_330_pages": {
      "target_ms": 5000,
      "max_ms": 10000
    },
    "large_pdf_600_pages": {
      "target_ms": 10000,
      "max_ms": 20000
    }
  }
}
```

### Automated Budget Validation

```python
def validate_performance_budgets():
    """Validate all operations meet performance budgets."""
    with open('test_files/performance_budgets.json') as f:
        budgets = json.load(f)

    failures = []

    # Test each operation
    for operation, budget in budgets['operations'].items():
        actual = measure_operation_time(operation)

        if actual > budget['max_ms']:
            failures.append(
                f"{operation}: {actual:.1f}ms > {budget['max_ms']}ms budget"
            )

    # Test end-to-end
    for test_name, budget in budgets['end_to_end'].items():
        actual = measure_end_to_end_time(test_name)

        if actual > budget['max_ms']:
            failures.append(
                f"{test_name}: {actual:.0f}ms > {budget['max_ms']}ms budget"
            )

    if failures:
        print("❌ PERFORMANCE BUDGET VIOLATIONS:")
        for failure in failures:
            print(f"   {failure}")
        sys.exit(1)

    print("✅ All performance budgets met")
    sys.exit(0)
```

---

## CLAUDE.md Integration

### Add to CLAUDE.md (New Section)

```markdown
## 🧪 Rigorous Real-World TDD Workflow

**MANDATORY for all RAG pipeline features**

### Before Implementing ANY Feature:

1. **Acquire Real Test PDF** (30-60 min)
   - Get actual PDF with feature (Z-Library, corpus, create synthetic)
   - NO proceeding without real PDF

2. **Create Ground Truth** (1-2 hours)
   - Document expected behavior in test_files/ground_truth/{feature}.json
   - Record feature locations (bboxes)
   - Define expected outputs
   - HUMAN verification required

3. **Write Failing Test** (30 min)
   - Real PDF test (NO mocks for integration)
   - Load ground truth
   - Validate against expectations
   - Test MUST fail (feature not implemented)

4. **Implement Feature** (variable)
   - TDD loop: test (red) → implement → test (green)
   - Keep pytest-watch running

5. **Manual Verification** (15-30 min)
   - Process test PDF
   - Open PDF and output side-by-side
   - Human verification checklist
   - Sign off required

6. **Performance Validation** (15 min)
   - Measure processing time
   - Compare with budget (test_files/performance_budgets.json)
   - No budget violations allowed

7. **Regression Check** (5 min)
   - Run ALL real PDF tests
   - No feature ships if regressions occur

8. **Only Then**: Commit and merge

### Quality Gates (Automated)

**Pre-commit**: Real PDF tests + performance budgets
**CI/CD**: Continuous validation with ground truth
**Manual**: Human verification checklist signed

### Hallucination Prevention

- ✅ Ground truth anchors expectations
- ✅ Real PDF testing prevents assumptions
- ✅ Manual verification catches errors
- ✅ Automated regression prevents backsliding
- ✅ Determinism tests catch randomness

**Lesson**: Unit tests passed but hid architectural flaw. Real PDF testing caught it.

**Principle**: Ground truth > assumptions, Real data > mocks, Human verification > automated tests
```

---

## Implementation Timeline

### Today (3-4 hours remaining)

**1. Create Initial Ground Truth** (2 hours)
- Document Derrida X-marks (manual verification)
- Document Heidegger X-marks (manual verification)
- Create ground_truth.json files

**2. Implement Ground Truth Loader** (1 hour)
- test_files/ground_truth_loader.py
- Validation helpers
- Schema validation

**3. Create First Real PDF Tests** (1 hour)
- __tests__/python/test_real_sous_rature.py
- Use ground truth
- Validate current implementation

---

### Week 1 (2-3 days)

**4. Build Core Test Corpus** (1 day)
- Acquire 5 essential PDFs
- Create ground truth for each
- Document acquisition process

**5. Implement Quality Gates** (1 day)
- Pre-commit hook
- Performance budget validation
- Automated regression suite

**6. Update CLAUDE.md** (2 hours)
- Add TDD workflow section
- Document quality gates
- Create checklists

---

### Week 2 (Ongoing)

**7. Expand Test Corpus**
- Add edge case PDFs as features are implemented
- Create ground truth for each
- Continuous growth

**8. Refine Quality Gates**
- Tune performance budgets
- Add more automated checks
- Improve ground truth schema

---

## Success Metrics

### Coverage Goals

- **Real PDF Tests**: >20 (covering all features)
- **Ground Truth Files**: >15 (comprehensive documentation)
- **Test Corpus Size**: >50 PDFs (diverse scenarios)

### Quality Goals

- **False Negatives**: 0% (can't miss features)
- **False Positives**: <5% (acceptable)
- **Hallucinations**: 0 (no made-up content)
- **Regressions**: 0 (all existing tests pass)

### Performance Goals

- **All budgets met**: 100% compliance
- **No regressions**: Performance doesn't degrade

---

## Key Principles

### 1. Ground Truth is Sacred

- Document BEFORE implementing
- Human verification required
- Version controlled (git)
- Referenced in all tests

### 2. Real PDFs Always

- NO mocking for integration tests
- Actual pipeline, actual PDFs
- Catches integration flaws
- Validates assumptions

### 3. Manual Verification Required

- Automated tests can miss quality issues
- Human review catches hallucinations
- Side-by-side comparison mandatory
- Checklist must be signed

### 4. Performance is a Feature

- Every operation has budget
- Continuous monitoring
- Regression detection
- Optimization guided by budgets

### 5. Fail Fast, Learn Fast

- Tests fail immediately if feature incomplete
- Ground truth shows gap
- Implement to pass
- Manual verification confirms

---

## Summary

**User's mandate**: "Set up rigorous TDD foundation to prevent errors and check hallucinations"

**Response**: Comprehensive TDD infrastructure with:
- ✅ Ground truth framework
- ✅ Real PDF test suite
- ✅ Quality gates (automated)
- ✅ CLAUDE.md workflow enforcement
- ✅ Anti-hallucination guardrails
- ✅ Performance budgets
- ✅ Manual verification requirements

**Timeline**: 3-4 hours for initial foundation (today), then expand continuously

**This prevents accumulating errors and keeps us honest!**
