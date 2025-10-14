# Metadata Verification System

## Overview

The metadata verification system compares Z-Library API metadata against metadata extracted directly from document content. This helps identify discrepancies and provides confidence-scored recommendations for which source to trust.

## Problem Statement

Z-Library API metadata may be incorrect or outdated due to:
- Community-contributed data with errors
- OCR mistakes in original cataloging
- Publisher changes (rebranding, mergers)
- Multiple editions with mixed metadata
- Translation/localization inconsistencies

The verification system provides automated quality checks to flag these issues.

## Architecture

### Components

1. **Extraction Functions** (`lib/metadata_verification.py`)
   - `extract_pdf_metadata()` - Extract from PDF metadata dict + front matter
   - `extract_epub_metadata()` - Extract from EPUB OPF manifest
   - `extract_txt_metadata()` - Limited extraction (filename heuristics)

2. **Verification Engine**
   - `verify_metadata()` - Compare API vs extracted with confidence scoring
   - Fuzzy matching using `difflib.SequenceMatcher`
   - Trust recommendations based on confidence thresholds

3. **Integration Point** (`lib/rag_processing.py`)
   - Automatically runs during `save_processed_text()`
   - Verification results added to metadata sidecar JSON
   - Non-blocking: failures logged but don't break processing

### Data Flow

```
Document Processing
       ↓
Extract Metadata (from document)
       ↓
Compare with API Metadata
       ↓
Generate Verification Report
       ↓
Add to Metadata Sidecar JSON
       ↓
Save Alongside Processed File
```

## Verification Report Structure

### Example Report

```json
{
  "fields": {
    "title": {
      "api_value": "The Burnout Society",
      "extracted_value": "THE BURNOUT SOCIETY",
      "confidence": 100.0,
      "match_type": "exact",
      "trusted_source": "both",
      "recommendation": "Perfect match - use either source for title"
    },
    "author": {
      "api_value": "Byung-Chul Han",
      "extracted_value": "Byung Chul Han",
      "confidence": 90.0,
      "match_type": "fuzzy_high",
      "trusted_source": "extracted",
      "recommendation": "High similarity - prefer extracted author"
    },
    "publisher": {
      "api_value": "Stanford Press",
      "extracted_value": "Stanford University Press",
      "confidence": 80.0,
      "match_type": "fuzzy_good",
      "trusted_source": "extracted",
      "recommendation": "Good similarity - prefer extracted publisher"
    },
    "year": {
      "api_value": "2015",
      "extracted_value": "2015",
      "confidence": 100.0,
      "match_type": "exact",
      "trusted_source": "both",
      "recommendation": "Perfect match - use either source for year"
    },
    "isbn": {
      "api_value": "9780804795098",
      "extracted_value": "9780804795098",
      "confidence": 100.0,
      "match_type": "exact",
      "trusted_source": "both",
      "recommendation": "Perfect match - use either source for isbn"
    }
  },
  "overall_confidence": 94.0,
  "discrepancies": [],
  "summary": "Excellent metadata quality (94.0% confidence). Verified 5 fields. No significant discrepancies found."
}
```

### Field Structure

Each verified field contains:

| Field | Type | Description |
|-------|------|-------------|
| `api_value` | string\|null | Value from Z-Library API |
| `extracted_value` | string\|null | Value extracted from document |
| `confidence` | float | Confidence score (0-100%) |
| `match_type` | string | Type of match (see below) |
| `trusted_source` | string | Recommended source to use |
| `recommendation` | string | Human-readable guidance |

### Match Types

| Match Type | Confidence | Description |
|------------|-----------|-------------|
| `exact` | 100% | Perfect match after normalization |
| `fuzzy_high` | 90% | High similarity (>0.9 ratio) |
| `fuzzy_good` | 80% | Good similarity (>0.8 ratio) |
| `fuzzy_moderate` | 70% | Moderate similarity (>0.7 ratio) |
| `substring` | 60% | One value contains the other |
| `none` | 0% | No meaningful match found |
| `api_only` | 50% | Only API has data |
| `extracted_only` | 50% | Only extracted has data |

### Trust Sources

| Source | When to Use |
|--------|-------------|
| `both` | Exact match - use either |
| `extracted` | Extracted has higher confidence (>80%) |
| `api` | Only API has data |
| `review` | Significant discrepancy - manual review needed |

## Confidence Scoring Algorithm

### Normalization

Before comparison, text is normalized:
1. Convert to lowercase
2. Remove punctuation (except hyphens)
3. Collapse whitespace
4. Trim leading/trailing spaces

### Similarity Calculation

Uses `difflib.SequenceMatcher.ratio()`:
- Ratio = 2 * M / T
- M = number of matching characters
- T = total characters in both strings

### Scoring Rules

```python
if normalized_match:
    confidence = 100%
elif similarity > 0.9:
    confidence = 90%
elif similarity > 0.8:
    confidence = 80%
elif similarity > 0.7:
    confidence = 70%
elif substring_match:
    confidence = 60%
else:
    confidence = 0%
```

### Trust Logic

```python
if confidence >= 80:
    trusted_source = "extracted"  # Prefer document content
elif api_value and not extracted_value:
    trusted_source = "api"  # Use available data
elif extracted_value and not api_value:
    trusted_source = "extracted"  # Use available data
else:
    trusted_source = "review"  # Manual review needed
```

## Extraction Methods

### PDF Extraction

**Sources (priority order):**
1. PDF metadata dictionary (`doc.metadata`)
2. Front matter text patterns (first 5 pages)

**Fields extracted:**
- **Title**: Metadata dict or first page capitalized text
- **Author**: Metadata dict author field
- **Publisher**: Copyright page patterns ("Published by X", "X Press")
- **Year**: Copyright dates (© YYYY), publication dates
- **ISBN**: ISBN patterns in front matter

### EPUB Extraction

**Source:** OPF manifest Dublin Core metadata

**Fields extracted:**
- **Title**: `DC:title` element
- **Author**: `DC:creator` element
- **Publisher**: `DC:publisher` element
- **Year**: `DC:date` element (extract year)
- **ISBN**: `DC:identifier` elements (filter for ISBN)

### TXT Extraction

**Source:** Filename heuristics only

**Fields extracted:**
- **Title**: Cleaned filename (very limited)
- Other fields: Not available

## Usage Examples

### Basic Usage

```python
from metadata_verification import (
    extract_pdf_metadata,
    verify_metadata
)

# Extract from document
extracted = extract_pdf_metadata(Path("book.pdf"))

# API metadata
api_metadata = {
    'title': 'The Burnout Society',
    'author': 'Byung-Chul Han',
    'publisher': 'Stanford Press',
    'year': '2015',
    'isbn': '9780804795098'
}

# Verify
report = verify_metadata(api_metadata, extracted)

print(f"Confidence: {report['overall_confidence']}%")
print(f"Summary: {report['summary']}")

# Check specific field
title_info = report['fields']['title']
print(f"Title confidence: {title_info['confidence']}%")
print(f"Recommendation: {title_info['recommendation']}")
```

### Integration with RAG Pipeline

The verification system is automatically integrated into `process_document()`:

```python
# Verification runs automatically during document processing
result = await process_document(
    file_path="book.pdf",
    output_format="markdown",
    book_details=book_details  # API metadata
)

# Verification report saved to metadata sidecar
metadata_path = result['metadata_file_path']
# Contains 'verification' section with full report
```

### Accessing Verification Results

```python
import json

# Read metadata sidecar
with open('metadata.json', 'r') as f:
    metadata = json.load(f)

# Access verification report
verification = metadata.get('verification', {})

if verification:
    print(f"Overall confidence: {verification['overall_confidence']}%")

    # Check for discrepancies
    if verification['discrepancies']:
        print("Discrepancies found:")
        for discrepancy in verification['discrepancies']:
            print(f"  - {discrepancy}")

    # Review low-confidence fields
    for field, info in verification['fields'].items():
        if info['confidence'] < 70:
            print(f"Low confidence: {field}")
            print(f"  API: {info['api_value']}")
            print(f"  Extracted: {info['extracted_value']}")
            print(f"  Recommendation: {info['recommendation']}")
```

## Quality Interpretation

### Confidence Ranges

| Range | Quality | Action |
|-------|---------|--------|
| 90-100% | Excellent | Trust metadata fully |
| 70-89% | Good | Review minor discrepancies |
| 50-69% | Fair | Verify critical fields manually |
| 0-49% | Poor | Manual review required |

### Common Discrepancy Patterns

1. **Publisher Abbreviations**
   - API: "MIT Press"
   - Extracted: "Massachusetts Institute of Technology Press"
   - Confidence: 80% (fuzzy_good)
   - Action: Prefer extracted (full name)

2. **Author Name Formatting**
   - API: "Smith, John"
   - Extracted: "John Smith"
   - Confidence: 90% (fuzzy_high)
   - Action: Prefer extracted (natural format)

3. **Title Case Differences**
   - API: "the burnout society"
   - Extracted: "The Burnout Society"
   - Confidence: 100% (exact after normalization)
   - Action: Use either

4. **Year Discrepancies**
   - API: "2015" (original edition)
   - Extracted: "2017" (reprint)
   - Confidence: 0% (none)
   - Action: Manual review (edition mismatch)

## Limitations

### PDF Limitations
- Front matter extraction depends on document structure
- OCR-scanned PDFs may have garbled metadata
- Multi-author works may only show first author
- Publisher detection relies on common patterns

### EPUB Limitations
- Metadata quality depends on publisher tooling
- Some fields may be missing or empty
- Multiple identifiers may cause confusion

### TXT Limitations
- No embedded metadata to extract
- Filename-only extraction is unreliable
- Cannot extract most fields

### General Limitations
- Fuzzy matching may produce false positives
- Different editions may have legitimate discrepancies
- Translation/localization differences not handled
- No semantic understanding (e.g., "Dr." vs "Doctor")

## Future Enhancements

### Planned Features
1. **Semantic Matching**: Use embeddings for better similarity
2. **Edition Detection**: Identify edition mismatches vs errors
3. **Multi-language Support**: Handle translated titles/names
4. **Author Disambiguation**: Use ORCID/ISNI identifiers
5. **Confidence Tuning**: Machine learning for scoring
6. **Batch Verification**: Process multiple documents at once

### Configuration Options (Future)
```python
verify_metadata(
    api_metadata,
    extracted_metadata,
    config={
        'confidence_threshold': 0.7,  # Minimum confidence
        'prefer_extracted': True,      # Default to extracted
        'strict_mode': False,          # Require exact matches
        'fuzzy_ratio': 0.8,           # Similarity threshold
    }
)
```

## Troubleshooting

### No Metadata Extracted

**Symptom**: `extracted_metadata` is empty

**Causes**:
- Missing dependencies (PyMuPDF, ebooklib)
- Corrupted document file
- No embedded metadata in document
- Unsupported document format

**Solution**:
```python
# Check dependencies
import sys
print("PyMuPDF available:", "fitz" in sys.modules)
print("ebooklib available:", "ebooklib" in sys.modules)

# Verify file integrity
from pathlib import Path
file_path = Path("book.pdf")
print(f"File exists: {file_path.exists()}")
print(f"File size: {file_path.stat().st_size} bytes")
```

### Low Confidence Scores

**Symptom**: All fields showing <50% confidence

**Causes**:
- Significant metadata discrepancies
- Different editions (API vs downloaded)
- OCR errors in document metadata
- Language/translation differences

**Solution**:
1. Manually verify 1-2 fields against document
2. Check for edition mismatch (year, ISBN)
3. Review API source quality
4. Consider manual metadata correction

### Verification Failures

**Symptom**: Verification step logs warnings/errors

**Causes**:
- Exception during extraction
- Invalid document format
- Missing required fields

**Solution**: Check logs for specific error messages
```bash
grep "metadata" logs/rag_processing.log | grep -i "error\|warning"
```

## Testing

### Unit Tests

```python
# Test extraction
def test_extract_pdf_metadata():
    metadata = extract_pdf_metadata(Path("test.pdf"))
    assert metadata['title'] is not None
    assert metadata['author'] is not None

# Test verification
def test_verify_exact_match():
    api = {'title': 'Test Book'}
    extracted = {'title': 'Test Book'}
    report = verify_metadata(api, extracted)
    assert report['fields']['title']['confidence'] == 100.0

# Test fuzzy matching
def test_verify_fuzzy_match():
    api = {'title': 'The Test Book'}
    extracted = {'title': 'Test Book, The'}
    report = verify_metadata(api, extracted)
    assert report['fields']['title']['confidence'] >= 80.0
```

### Integration Tests

```bash
# Test with real document
uv run pytest __tests__/python/test_metadata_verification.py -v

# Test with multiple formats
uv run pytest __tests__/python/test_metadata_verification.py::test_all_formats -v
```

## Performance Considerations

### Execution Time
- PDF extraction: ~50-200ms (depends on page count)
- EPUB extraction: ~20-50ms
- TXT extraction: <10ms
- Verification: <5ms per field

### Memory Usage
- Minimal: Only front matter text loaded for PDF
- EPUB: Full manifest loaded (typically <100KB)
- No caching: Each call extracts fresh

### Optimization Tips
1. **Batch Processing**: Extract once, verify multiple times
2. **Parallel Execution**: Run extraction in thread pool
3. **Caching**: Cache extraction results for same document
4. **Lazy Loading**: Skip extraction if API confidence is high

## References

### Related Documentation
- [RAG Processing Pipeline](./RAG_PIPELINE.md)
- [Metadata Generation](./METADATA_GENERATION.md)
- [Quality Analysis](./QUALITY_ANALYSIS.md)

### External Resources
- [PyMuPDF Metadata](https://pymupdf.readthedocs.io/en/latest/document.html#Document.metadata)
- [EPUB OPF Specification](http://idpf.org/epub/20/spec/OPF_2.0.1_draft.htm)
- [Dublin Core Metadata](https://www.dublincore.org/specifications/dublin-core/)
- [Python difflib](https://docs.python.org/3/library/difflib.html)
