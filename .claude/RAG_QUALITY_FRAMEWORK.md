# RAG Quality Verification Framework

## Purpose

This document establishes a systematic approach to verifying RAG (Retrieval-Augmented Generation) pipeline quality for the Z-Library MCP server. Quality verification is critical for ensuring reliable document processing across diverse PDF, EPUB, and TXT sources.

## Philosophy

### Why Systematic Verification Matters

**Core Principle**: *Failure happens silently in RAG pipelines.* A PDF may appear to process successfully while producing unusable output—garbled text, missing content, corrupted formatting, or OCR failures that degrade downstream AI performance.

**Quality vs Functionality**:
- ✅ **Wrong Question**: "Does it work?"
- ✅ **Right Question**: "How well does it work, and under what conditions?"

**Detection Philosophy**:
- **Early Detection**: Catch issues during development, not in production
- **Systematic Testing**: Use representative samples, not cherry-picked success cases
- **Evidence-Based**: Verify against actual PDF content, not assumptions
- **Honest Assessment**: Document limitations transparently

### Quality Dimensions

| Dimension | What We Measure | Why It Matters |
|-----------|----------------|----------------|
| **Completeness** | Text extraction coverage | Missing content breaks RAG context |
| **Accuracy** | Fidelity to source material | Errors propagate to AI responses |
| **Structure** | Heading, list, formatting preservation | Structure aids retrieval and comprehension |
| **Readability** | Word spacing, line breaks, hyphenation | Poor formatting confuses embeddings |
| **Metadata** | Title, author, page tracking | Essential for citations and provenance |
| **Robustness** | Performance across PDF types | Edge cases reveal design weaknesses |

## Framework Components

### 1. Sampling Strategy

**Objective**: Select pages that reveal quality across diverse content types and edge cases.

#### Systematic Sampling Protocol

```python
# Recommended sampling for quality verification
def get_quality_sample_pages(pdf_path: Path, sample_size: int = 5) -> list[int]:
    """
    Select representative pages for quality verification.

    Returns page numbers (0-indexed) covering:
    - First page (title, metadata, formatting)
    - Last page (references, indices)
    - Random middle pages (body content)
    - Special content (tables, figures, equations if known)
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if total_pages <= sample_size:
        return list(range(total_pages))

    sample_pages = [
        0,                              # First page (title, metadata)
        total_pages - 1,                # Last page (references, index)
    ]

    # Random middle pages for body content
    middle_start = max(1, total_pages // 4)
    middle_end = min(total_pages - 1, 3 * total_pages // 4)
    middle_pages = random.sample(
        range(middle_start, middle_end),
        min(sample_size - 2, middle_end - middle_start)
    )

    sample_pages.extend(middle_pages)
    return sorted(set(sample_pages))
```

#### Content Type Coverage

Ensure samples include:
- **Text-heavy pages**: Dense paragraphs (test extraction accuracy)
- **Structural pages**: Headings, lists, nested content (test structure detection)
- **Special content**: Tables, equations, code blocks (test edge cases)
- **Layout variations**: Two-column, margin notes, sidebars (test layout handling)
- **First/last pages**: Title pages, references, indices (test metadata extraction)

### 2. Failure Mode Catalog

**Objective**: Enumerate known failure patterns to systematically check for regressions.

#### Critical Failure Modes

| Failure Mode | Detection Method | Severity | Example |
|--------------|------------------|----------|---------|
| **Garbled Text** | Check char diversity, Unicode patterns | 🔴 Critical | `��������` or `ïðñòó` |
| **Word Concatenation** | Analyze space density, common words | 🔴 Critical | `Thisisasentence` |
| **Missing Content** | Compare char density to visual analysis | 🔴 Critical | 10 chars/page for dense text |
| **Broken Headings** | Verify heading detection in ToC pages | 🟡 Important | Headers missed or mis-leveled |
| **List Corruption** | Check list marker detection | 🟡 Important | Bullets/numbers lost |
| **Metadata Loss** | Verify title, author, page numbers | 🟡 Important | Missing frontmatter |
| **OCR Failure** | Compare OCR to direct text extraction | 🟡 Important | OCR worse than direct extraction |
| **Encoding Issues** | Check for replacement chars, mojibake | 🔴 Critical | `â€™` instead of `'` |

#### Failure Mode Detection Code

```python
def detect_failure_modes(extracted_text: str, page_num: int) -> dict:
    """
    Systematically check for known failure modes.

    Returns dict with failure indicators and severity.
    """
    failures = {}

    # 1. Garbled text detection
    char_diversity = len(set(extracted_text)) / max(len(extracted_text), 1)
    if char_diversity < 0.15:
        failures['garbled_text'] = {
            'severity': 'CRITICAL',
            'detail': f'Char diversity {char_diversity:.2%} below threshold',
            'page': page_num
        }

    # 2. Word concatenation detection
    space_ratio = extracted_text.count(' ') / max(len(extracted_text), 1)
    if space_ratio < 0.05:
        failures['word_concatenation'] = {
            'severity': 'CRITICAL',
            'detail': f'Space ratio {space_ratio:.2%} suggests missing word boundaries',
            'page': page_num
        }

    # 3. Check for replacement characters (encoding issues)
    if '�' in extracted_text or '\ufffd' in extracted_text:
        failures['encoding_issue'] = {
            'severity': 'CRITICAL',
            'detail': f'Unicode replacement char found (bad encoding)',
            'page': page_num
        }

    # 4. Empty or near-empty extraction
    if len(extracted_text.strip()) < 50:
        failures['missing_content'] = {
            'severity': 'CRITICAL',
            'detail': f'Only {len(extracted_text)} chars extracted',
            'page': page_num
        }

    return failures
```

### 3. Quality Metrics

**Objective**: Quantify extraction quality with actionable, comparable metrics.

#### Primary Metrics

```python
class QualityMetrics:
    """Quality metrics for RAG extraction assessment."""

    def __init__(self, pdf_path: Path, extracted_text: str):
        self.pdf_path = pdf_path
        self.extracted_text = extracted_text
        self.doc = fitz.open(pdf_path)

    def compute_all_metrics(self) -> dict:
        """Compute comprehensive quality metrics."""
        return {
            'completeness': self.completeness_score(),
            'text_quality': self.text_quality_score(),
            'structure_preservation': self.structure_score(),
            'metadata_quality': self.metadata_score(),
            'overall_grade': self.overall_grade()
        }

    def completeness_score(self) -> float:
        """
        Measure extraction completeness (0.0-1.0).

        Compares extracted char count to visual char count estimate.
        """
        visual_chars = sum(
            len(page.get_text("text")) for page in self.doc
        )
        extracted_chars = len(self.extracted_text)

        return min(extracted_chars / max(visual_chars, 1), 1.0)

    def text_quality_score(self) -> float:
        """
        Measure text quality (0.0-1.0).

        Based on:
        - Character diversity (0.15+ expected)
        - Space ratio (0.05+ expected)
        - Common word frequency
        - Lack of garbled patterns
        """
        char_diversity = len(set(self.extracted_text)) / max(len(self.extracted_text), 1)
        space_ratio = self.extracted_text.count(' ') / max(len(self.extracted_text), 1)

        # Check for common English words (heuristic for language coherence)
        common_words = {'the', 'and', 'of', 'to', 'in', 'a', 'is', 'that', 'for', 'it'}
        words = set(self.extracted_text.lower().split())
        common_word_ratio = len(words & common_words) / len(common_words)

        # Weighted scoring
        scores = {
            'char_diversity': min(char_diversity / 0.15, 1.0) * 0.3,
            'space_ratio': min(space_ratio / 0.05, 1.0) * 0.3,
            'common_words': common_word_ratio * 0.4
        }

        return sum(scores.values())

    def structure_score(self) -> float:
        """
        Measure structure preservation (0.0-1.0).

        Checks for:
        - Markdown heading markers (# ## ###)
        - List markers (- * 1. 2.)
        - Paragraph breaks
        """
        has_headings = bool(re.search(r'^#{1,6}\s+\w+', self.extracted_text, re.MULTILINE))
        has_lists = bool(re.search(r'^[\-\*\d+\.]\s+\w+', self.extracted_text, re.MULTILINE))
        has_paragraphs = bool(re.search(r'\n\n', self.extracted_text))

        score = 0.0
        if has_headings: score += 0.4
        if has_lists: score += 0.3
        if has_paragraphs: score += 0.3

        return score

    def metadata_score(self) -> float:
        """
        Measure metadata quality (0.0-1.0).

        Checks for YAML frontmatter with required fields.
        """
        if not self.extracted_text.startswith('---\n'):
            return 0.0

        required_fields = {'title', 'source_file', 'total_pages'}
        optional_fields = {'author', 'year', 'language'}

        # Extract frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---', self.extracted_text, re.DOTALL)
        if not frontmatter_match:
            return 0.0

        frontmatter = frontmatter_match.group(1)
        fields_present = set(re.findall(r'^(\w+):', frontmatter, re.MULTILINE))

        required_score = len(fields_present & required_fields) / len(required_fields)
        optional_score = len(fields_present & optional_fields) / len(optional_fields)

        return required_score * 0.7 + optional_score * 0.3

    def overall_grade(self) -> str:
        """
        Compute letter grade (A-F) based on metrics.

        Grading scale:
        - A (90-100%): Excellent quality, production-ready
        - B (80-89%): Good quality, minor issues acceptable
        - C (70-79%): Acceptable quality, review recommended
        - D (60-69%): Poor quality, significant issues present
        - F (<60%): Failed extraction, unusable
        """
        metrics = self.compute_all_metrics()

        # Weighted average (completeness and text_quality are most critical)
        overall = (
            metrics['completeness'] * 0.35 +
            metrics['text_quality'] * 0.35 +
            metrics['structure_preservation'] * 0.15 +
            metrics['metadata_quality'] * 0.15
        )

        if overall >= 0.9: return 'A'
        if overall >= 0.8: return 'B'
        if overall >= 0.7: return 'C'
        if overall >= 0.6: return 'D'
        return 'F'
```

### 4. Automated vs Manual Verification

**Objective**: Balance automation speed with human judgment for comprehensive quality assessment.

#### Automated Verification

**Use Cases**:
- Regression testing (every commit, PR)
- Bulk PDF processing validation
- Continuous integration quality gates
- Quick sanity checks during development

**Automated Checks** (Fast, Objective):
```python
def automated_quality_check(pdf_path: Path, output_path: Path) -> dict:
    """
    Fast automated quality verification.

    Returns pass/fail status with objective metrics.
    Suitable for CI/CD integration.
    """
    with open(output_path, 'r') as f:
        extracted_text = f.read()

    metrics = QualityMetrics(pdf_path, extracted_text).compute_all_metrics()
    failures = detect_failure_modes(extracted_text, page_num=0)

    # Quality gates
    checks = {
        'completeness_pass': metrics['completeness'] >= 0.8,
        'text_quality_pass': metrics['text_quality'] >= 0.7,
        'no_critical_failures': not any(
            f['severity'] == 'CRITICAL' for f in failures.values()
        ),
        'overall_grade': metrics['overall_grade']
    }

    checks['all_pass'] = all([
        checks['completeness_pass'],
        checks['text_quality_pass'],
        checks['no_critical_failures']
    ])

    return {
        'pass': checks['all_pass'],
        'metrics': metrics,
        'failures': failures,
        'checks': checks
    }
```

#### Manual Verification

**Use Cases**:
- Investigating automated test failures
- Validating new extraction algorithms
- Edge case analysis (complex layouts, special content)
- Quality assurance before major releases

**Manual Review Checklist**:
1. ✅ **Visual Comparison**: Open PDF side-by-side with extracted text
2. ✅ **Content Accuracy**: Spot-check paragraphs match source
3. ✅ **Structure Fidelity**: Verify headings, lists, emphasis preserved
4. ✅ **Edge Cases**: Check tables, figures, equations, code blocks
5. ✅ **Metadata Correctness**: Validate title, author, page numbers
6. ✅ **Citation Readiness**: Confirm page markers accurate for citations

**Manual Review Protocol**:
```bash
# 1. Process PDF with quality report
uv run pytest __tests__/python/test_rag_processing.py::test_quality_verification -v

# 2. Open PDF in viewer
evince test_files/sample.pdf &

# 3. Open extracted text in editor
code processed_rag_output/sample.txt

# 4. Compare visually:
#    - First page (metadata, title)
#    - Random middle pages (body content)
#    - Last page (references, index)
#    - Special content (tables, figures)

# 5. Document findings in quality report
# See QUALITY_REPORTS.md template
```

## Usage Guidelines

### During Development

**When to Run Quality Checks**:
- ✅ Before committing changes to extraction logic
- ✅ After modifying PDF parsing code
- ✅ When adding new features (headings, lists, tables)
- ✅ After dependency updates (PyMuPDF, ebooklib)
- ✅ When investigating user-reported issues

**Development Workflow**:
```bash
# 1. Make changes to rag_processing.py
vim lib/rag_processing.py

# 2. Run focused quality tests
uv run pytest __tests__/python/test_rag_processing.py::TestPDFQuality -v

# 3. Review failure modes
cat test_output/quality_report.json | jq '.failures'

# 4. Fix issues, iterate until quality gates pass

# 5. Run full test suite
uv run pytest

# 6. Commit with quality metrics in PR description
git add lib/rag_processing.py __tests__/python/test_rag_processing.py
git commit -m "feat: improve PDF heading detection

Quality metrics:
- Completeness: 95%
- Text quality: 92%
- Structure: 88%
- Overall: Grade A

Tested on 10 diverse PDFs (academic, technical, scanned)."
```

### Interpreting Quality Reports

**Quality Report Structure**:
```json
{
  "pdf_path": "test_files/sample.pdf",
  "metrics": {
    "completeness": 0.95,
    "text_quality": 0.92,
    "structure_preservation": 0.88,
    "metadata_quality": 1.0,
    "overall_grade": "A"
  },
  "failures": {},
  "checks": {
    "completeness_pass": true,
    "text_quality_pass": true,
    "no_critical_failures": true,
    "overall_grade": "A",
    "all_pass": true
  },
  "recommendations": [
    "Quality excellent - no action needed"
  ]
}
```

**Interpreting Scores**:

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| **0.9-1.0 (A)** | Excellent extraction quality | ✅ Production-ready, no action |
| **0.8-0.89 (B)** | Good quality, minor issues | ⚠️ Review, but acceptable |
| **0.7-0.79 (C)** | Acceptable, notable issues | ⚠️ Investigate, fix if possible |
| **0.6-0.69 (D)** | Poor quality, major issues | 🔴 Fix required before merge |
| **<0.6 (F)** | Failed extraction | 🔴 Unusable, major fix needed |

**Common Failure Patterns**:

1. **Low Completeness (< 0.8)**:
   - **Cause**: Missing pages, corrupted PDF, OCR failure
   - **Action**: Check PDF integrity, try OCR alternatives, verify page count

2. **Low Text Quality (< 0.7)**:
   - **Cause**: Garbled text, encoding issues, word concatenation
   - **Action**: Check encoding, test alternative extraction methods, verify font embedding

3. **Low Structure Score (< 0.5)**:
   - **Cause**: Headings/lists not detected, poor markdown conversion
   - **Action**: Tune font-size thresholds, improve heading detection heuristics

4. **Critical Failures**:
   - **Garbled Text**: Unreadable output, requires encoding/extraction fix
   - **Word Concatenation**: Missing spaces, adjust line-joining logic
   - **Missing Content**: Check for image-only PDFs, enable OCR if needed

### When to Investigate vs Accept Limitations

**Investigate Further** (Priority Fix Required):
- 🔴 Critical failures present (garbled, concatenated, missing content)
- 🔴 Overall grade D or F
- 🔴 Regression from previous quality baseline
- 🔴 Affects majority of test PDFs (>50%)

**Accept as Known Limitation** (Document, Monitor):
- 🟡 Edge case failure on 1 specific PDF type (e.g., heavily annotated, scanned)
- 🟡 Structure detection issues in complex layouts (2-column with sidebar)
- 🟡 Minor metadata missing on unconventional PDFs
- 🟡 Acceptable quality trade-off (e.g., OCR speed vs accuracy)

**Documentation Template for Known Limitations**:
```markdown
## Known Limitation: Two-Column Layout Heading Detection

**Issue**: Headings in multi-column PDFs sometimes mis-detected or missed
**Severity**: Low (affects ~5% of PDFs, body text extraction unaffected)
**Workaround**: Manual review of extracted headings for complex layouts
**Fix Status**: Tracked in ISSUE-RAG-007, requires advanced layout analysis
**Acceptance Criteria**:
  - Completeness >= 90% (text extraction works)
  - Text quality >= 85% (body content readable)
  - Structure score may be lower (50-70%) but documented

**Example PDFs**: `test_files/complex_layout.pdf`, `test_files/journal_article.pdf`
```

### Prioritizing Fixes by Severity

**Critical Priority** (Fix Before Merge):
- Garbled text or encoding issues
- Word concatenation (missing spaces)
- Completeness < 80% on standard PDFs
- Any failure affecting >50% of test PDFs

**High Priority** (Fix in Current Sprint):
- Text quality < 70%
- Structure detection failing (headings, lists missed)
- Metadata missing on standard PDFs
- Regression from previous version

**Medium Priority** (Fix in Next Release):
- Structure score < 60% on complex layouts
- Edge case failures (<10% of PDFs)
- Performance issues (slow extraction)
- Minor metadata inconsistencies

**Low Priority** (Track, Fix if Easy):
- Optional metadata missing
- Minor formatting inconsistencies
- Known limitations with workarounds
- Cosmetic issues (extra whitespace)

## Integration with Development Workflow

### Pre-Commit Quality Checks

**Objective**: Catch quality regressions before code reaches repository.

**Pre-Commit Hook** (`.git/hooks/pre-commit`):
```bash
#!/bin/bash
# Quality gate for RAG processing changes

# Check if rag_processing.py was modified
if git diff --cached --name-only | grep -q "lib/rag_processing.py"; then
    echo "RAG processing modified, running quality checks..."

    # Run quality verification tests
    uv run pytest __tests__/python/test_rag_processing.py::TestPDFQuality -v --tb=short

    if [ $? -ne 0 ]; then
        echo "❌ Quality checks failed. Fix issues before committing."
        echo "Review test output above for details."
        exit 1
    fi

    echo "✅ Quality checks passed"
fi

exit 0
```

### CI/CD Integration

**GitHub Actions Workflow** (`.github/workflows/quality-check.yml`):
```yaml
name: RAG Quality Verification

on:
  pull_request:
    paths:
      - 'lib/rag_processing.py'
      - '__tests__/python/test_rag_processing.py'
      - 'lib/filename_utils.py'
      - 'lib/metadata_generator.py'

jobs:
  quality-check:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install UV
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Install dependencies
      run: uv sync

    - name: Run quality verification tests
      run: |
        uv run pytest __tests__/python/test_rag_processing.py::TestPDFQuality \
          -v --tb=short --junitxml=quality-report.xml

    - name: Generate quality report
      run: |
        uv run python scripts/generate_quality_report.py \
          --output quality-summary.md

    - name: Comment PR with quality metrics
      uses: actions/github-script@v6
      if: always()
      with:
        script: |
          const fs = require('fs');
          const report = fs.readFileSync('quality-summary.md', 'utf8');

          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## RAG Quality Report\n\n${report}`
          });

    - name: Fail if quality gates not met
      run: |
        uv run python scripts/check_quality_gates.py \
          --report quality-report.xml \
          --min-grade B
```

### Regression Testing

**Objective**: Ensure new changes don't degrade quality on previously-working PDFs.

**Regression Test Suite**:
```python
# __tests__/python/test_rag_regression.py

import pytest
from pathlib import Path
import json

# Baseline quality metrics for known PDFs
BASELINE_METRICS = {
    "test_files/academic_paper.pdf": {
        "completeness": 0.95,
        "text_quality": 0.92,
        "structure_preservation": 0.88,
        "overall_grade": "A"
    },
    "test_files/technical_manual.pdf": {
        "completeness": 0.93,
        "text_quality": 0.90,
        "structure_preservation": 0.85,
        "overall_grade": "A"
    },
    # Add more baseline PDFs
}

TOLERANCE = 0.05  # Allow 5% variance

@pytest.mark.parametrize("pdf_path,baseline", BASELINE_METRICS.items())
def test_regression_quality_maintained(pdf_path, baseline):
    """
    Verify quality metrics don't regress on baseline PDFs.

    Fails if current extraction quality drops >5% from baseline.
    """
    from rag_processing import process_document_for_rag_with_metadata

    # Process PDF
    output_path = process_document_for_rag_with_metadata(Path(pdf_path))

    # Compute current metrics
    with open(output_path, 'r') as f:
        extracted_text = f.read()

    current_metrics = QualityMetrics(Path(pdf_path), extracted_text).compute_all_metrics()

    # Check for regression
    for metric, baseline_value in baseline.items():
        if metric == 'overall_grade':
            continue  # Check grade separately

        current_value = current_metrics[metric]
        degradation = baseline_value - current_value

        assert degradation <= TOLERANCE, (
            f"Regression detected in {metric}: "
            f"baseline={baseline_value:.2%}, current={current_value:.2%}, "
            f"degradation={degradation:.2%} (max allowed={TOLERANCE:.2%})"
        )

    # Overall grade should not drop more than one letter
    grade_order = ['F', 'D', 'C', 'B', 'A']
    baseline_idx = grade_order.index(baseline['overall_grade'])
    current_idx = grade_order.index(current_metrics['overall_grade'])

    assert current_idx >= baseline_idx - 1, (
        f"Overall grade regressed: {baseline['overall_grade']} → {current_metrics['overall_grade']}"
    )
```

### Quality Gates for PR Merging

**Merge Requirements** (enforced in PR template):

**Must Pass** (Blocking):
- ✅ All quality verification tests pass
- ✅ No new critical failures introduced
- ✅ No regressions on baseline PDFs (>5% drop)
- ✅ Overall grade >= B on test suite
- ✅ Manual review completed for complex changes

**Recommended** (Non-Blocking):
- ⚠️ Quality metrics included in PR description
- ⚠️ New test PDFs added for new edge cases
- ⚠️ Documentation updated for known limitations
- ⚠️ Performance benchmarks included if relevant

**PR Template Snippet**:
```markdown
## Quality Verification

### Automated Tests
- [ ] All quality tests pass (`pytest __tests__/python/test_rag_processing.py::TestPDFQuality`)
- [ ] No regressions on baseline PDFs
- [ ] Overall grade >= B

### Quality Metrics
| Metric | Score | Status |
|--------|-------|--------|
| Completeness | 95% | ✅ |
| Text Quality | 92% | ✅ |
| Structure | 88% | ✅ |
| Overall Grade | A | ✅ |

### Test Coverage
- [x] Tested on 10 diverse PDFs (academic, technical, scanned)
- [x] Edge cases covered: multi-column, complex layouts, special characters
- [ ] Known limitations documented (if any)

### Manual Review
- [x] Visual comparison completed for sample PDFs
- [x] Citation accuracy verified
- [x] Metadata correctness confirmed
```

## Best Practices

### 1. Test on Multiple PDFs (Not Just One)

**Anti-Pattern** ❌:
```python
# Only testing on one "golden" PDF
def test_pdf_extraction():
    output = process_pdf("test_files/perfect_sample.pdf")
    assert "expected content" in output
```

**Best Practice** ✅:
```python
# Test on diverse PDF types
@pytest.mark.parametrize("pdf_path", [
    "test_files/academic_paper.pdf",      # Text-heavy, scholarly
    "test_files/technical_manual.pdf",    # Tables, diagrams
    "test_files/scanned_book.pdf",        # OCR required
    "test_files/complex_layout.pdf",      # Multi-column, sidebars
    "test_files/special_chars.pdf",       # Unicode, equations
])
def test_pdf_extraction_diverse(pdf_path):
    output = process_pdf(pdf_path)
    metrics = compute_quality_metrics(pdf_path, output)
    assert metrics['overall_grade'] in ['A', 'B']
```

### 2. Sample Pages Systematically

**Anti-Pattern** ❌:
```python
# Only checking pages that you know work well
def test_extraction():
    check_page(5)   # Cherry-picked page
    check_page(10)  # Another cherry-picked page
```

**Best Practice** ✅:
```python
# Systematic sampling covering edge cases
def test_extraction():
    pages = [
        0,                    # First page (title, metadata)
        len(pdf) - 1,         # Last page (index, references)
        *random.sample(       # Random middle pages
            range(1, len(pdf) - 1),
            k=min(5, len(pdf) - 2)
        )
    ]
    for page_num in pages:
        check_page(page_num)
```

### 3. Verify Against Actual PDF Content

**Anti-Pattern** ❌:
```python
# Testing against your assumptions, not reality
def test_heading_detection():
    output = extract_pdf("sample.pdf")
    assert "# Chapter 1" in output  # Assumed heading
```

**Best Practice** ✅:
```python
# Verify against actual PDF visual content
def test_heading_detection():
    output = extract_pdf("sample.pdf")

    # Open PDF, manually verify heading on page 5
    # Document expected result based on visual inspection
    page_5 = get_page_text(output, page=5)

    # This is what we SEE in the PDF viewer:
    # Large bold text "Introduction" at top of page 5
    assert "# Introduction" in page_5or "## Introduction" in page_5  # Verified against PDF
```

### 4. Document Known Limitations Honestly

**Anti-Pattern** ❌:
```python
# Silently skipping failing tests
@pytest.mark.skip("Complex layouts not supported yet")
def test_complex_layout():
    pass
```

**Best Practice** ✅:
```python
# Document limitation with context and acceptance criteria
@pytest.mark.xfail(
    reason="Multi-column with sidebar detection requires advanced layout analysis (ISSUE-RAG-007)",
    strict=False  # Don't fail if it unexpectedly passes
)
def test_complex_layout():
    """
    Known Limitation: Complex two-column layouts with sidebars.

    Current behavior:
    - Body text extraction works (completeness >= 90%)
    - Heading detection may miss some headers
    - Reading order may be incorrect in sidebar content

    Acceptance criteria:
    - Completeness >= 85%
    - Text quality >= 80%
    - Critical content (body text) extracted correctly

    Related: ISSUE-RAG-007 (tracked in backlog)
    """
    output = extract_pdf("test_files/complex_layout.pdf")
    metrics = compute_quality_metrics("test_files/complex_layout.pdf", output)

    # Relaxed criteria for known limitation
    assert metrics['completeness'] >= 0.85
    assert metrics['text_quality'] >= 0.80
    # Structure score may be lower, document this
```

### 5. Check Edge Cases Explicitly

**Anti-Pattern** ❌:
```python
# Only testing happy path
def test_pdf_extraction():
    output = extract_pdf("normal_document.pdf")
    assert len(output) > 0
```

**Best Practice** ✅:
```python
# Explicit edge case testing
@pytest.mark.parametrize("edge_case", [
    "empty_pages.pdf",           # PDF with blank pages
    "image_only.pdf",            # Scanned document, no text layer
    "password_protected.pdf",    # Encrypted PDF
    "corrupted_metadata.pdf",    # Missing/broken metadata
    "huge_file.pdf",             # Large PDF (>100 pages)
    "unicode_heavy.pdf",         # Non-ASCII characters
    "equation_heavy.pdf",        # Mathematical equations
])
def test_edge_cases(edge_case):
    """Test known edge cases with documented expected behavior."""
    try:
        output = extract_pdf(f"test_files/edge_cases/{edge_case}")
        # Edge cases may have lower quality, document expectations
        metrics = compute_quality_metrics(edge_case, output)

        if "image_only" in edge_case:
            # OCR required, lower completeness acceptable
            assert metrics['completeness'] >= 0.70
        elif "password_protected" in edge_case:
            # Should fail gracefully
            pytest.fail("Should have raised PasswordProtectedError")
        else:
            # Standard quality expected
            assert metrics['overall_grade'] in ['A', 'B', 'C']

    except ExpectedError as e:
        # Document expected failures
        logger.info(f"Edge case {edge_case} failed as expected: {e}")
```

## Quality Report Template

**Template for documenting quality assessments**:

```markdown
# RAG Quality Report: [Feature/Fix Description]

**Date**: 2025-10-14
**Author**: [Your Name]
**Branch**: feature/pdf-heading-detection
**Commit**: abc1234

## Summary

Brief description of changes and their impact on quality.

## Test Coverage

### PDFs Tested
- [x] `test_files/academic_paper.pdf` - Text-heavy scholarly paper
- [x] `test_files/technical_manual.pdf` - Tables, diagrams, code blocks
- [x] `test_files/scanned_book.pdf` - OCR-processed scanned pages
- [x] `test_files/complex_layout.pdf` - Multi-column with sidebars
- [x] `test_files/special_chars.pdf` - Unicode, equations, symbols

### Quality Metrics

| PDF | Completeness | Text Quality | Structure | Grade | Status |
|-----|--------------|--------------|-----------|-------|--------|
| academic_paper.pdf | 95% | 92% | 88% | A | ✅ Pass |
| technical_manual.pdf | 93% | 90% | 85% | A | ✅ Pass |
| scanned_book.pdf | 75% | 82% | 65% | C | ⚠️ Acceptable |
| complex_layout.pdf | 88% | 85% | 60% | B | ⚠️ Known limitation |
| special_chars.pdf | 96% | 94% | 90% | A | ✅ Pass |

## Failures Detected

### Critical Failures
- None

### Important Issues
- **Complex Layout Heading Detection**: Headings in multi-column layouts occasionally missed
  - **Severity**: Low (affects ~5% of pages)
  - **Workaround**: Body text extraction unaffected
  - **Status**: Documented as known limitation (ISSUE-RAG-007)

## Manual Verification

- [x] Visual comparison completed for all test PDFs
- [x] Citation accuracy verified on sample pages
- [x] Metadata correctness confirmed
- [x] Edge cases documented

## Regression Check

- [x] No regressions on baseline PDFs
- [x] Quality maintained or improved across all metrics

## Recommendations

1. ✅ **Merge**: Quality gates passed, no blocking issues
2. ⚠️ **Monitor**: Complex layout heading detection (low priority fix)
3. 📝 **Document**: Update known limitations in README

## Baseline Update

New baseline metrics recorded for regression testing:
- `academic_paper.pdf`: A grade (95% completeness)
- `technical_manual.pdf`: A grade (93% completeness)

---

*Quality framework version: 1.0*
*Generated: 2025-10-14*
```

## Summary

**Quality verification is not optional—it's essential for RAG pipeline reliability.**

This framework provides:
- ✅ **Systematic sampling** to catch failures across diverse PDFs
- ✅ **Failure mode catalog** for comprehensive issue detection
- ✅ **Quantitative metrics** for objective quality assessment
- ✅ **Automated + manual** verification for balanced coverage
- ✅ **CI/CD integration** to prevent regressions
- ✅ **Best practices** to guide development

**Remember**:
- Test on multiple PDFs, not just one
- Sample systematically, not cherry-picked pages
- Verify against actual PDF content, not assumptions
- Document limitations honestly
- Check edge cases explicitly

**Quality is a process, not a checklist.** Use this framework as a living guide, adapting it as you discover new failure modes and edge cases.

---

*For questions or improvements, see `.claude/PATTERNS.md` and `.claude/META_LEARNING.md`*
