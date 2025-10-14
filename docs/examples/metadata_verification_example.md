# Metadata Verification Examples

## Quick Start

### Example 1: Perfect Match

```python
api_metadata = {
    'title': 'The Burnout Society',
    'author': 'Byung-Chul Han',
    'publisher': 'Stanford University Press',
    'year': '2015',
    'isbn': '9780804795098'
}

extracted_metadata = {
    'title': 'THE BURNOUT SOCIETY',  # Case difference
    'author': 'Byung-Chul Han',
    'publisher': 'Stanford University Press',
    'year': '2015',
    'isbn': '9780804795098'
}

report = verify_metadata(api_metadata, extracted_metadata)
```

**Result:**
```json
{
  "overall_confidence": 100.0,
  "summary": "Excellent metadata quality (100.0% confidence). Verified 5 fields. No significant discrepancies found.",
  "discrepancies": []
}
```

### Example 2: Minor Discrepancies

```python
api_metadata = {
    'title': 'Capital in the Twenty-First Century',
    'author': 'Thomas Piketty',
    'publisher': 'Harvard Press',
    'year': '2014',
    'isbn': '9780674430006'
}

extracted_metadata = {
    'title': 'Capital in the 21st Century',  # Spelling difference
    'author': 'Piketty, Thomas',             # Name order reversed
    'publisher': 'Harvard University Press', # Full name
    'year': '2014',
    'isbn': '9780674430006'
}

report = verify_metadata(api_metadata, extracted_metadata)
```

**Result:**
```json
{
  "overall_confidence": 84.0,
  "summary": "Good metadata quality (84.0% confidence). Verified 5 fields. No significant discrepancies found.",
  "fields": {
    "title": {
      "confidence": 80.0,
      "match_type": "fuzzy_good",
      "trusted_source": "extracted",
      "recommendation": "Good similarity - prefer extracted title"
    },
    "author": {
      "confidence": 90.0,
      "match_type": "fuzzy_high",
      "trusted_source": "extracted",
      "recommendation": "High similarity - prefer extracted author"
    },
    "publisher": {
      "confidence": 80.0,
      "match_type": "fuzzy_good",
      "trusted_source": "extracted",
      "recommendation": "Good similarity - prefer extracted publisher"
    }
  }
}
```

### Example 3: Significant Discrepancy

```python
api_metadata = {
    'title': 'Introduction to Algorithms',
    'author': 'Cormen et al.',
    'publisher': 'MIT Press',
    'year': '2009',  # 3rd edition
    'isbn': '9780262033848'
}

extracted_metadata = {
    'title': 'Introduction to Algorithms',
    'author': 'Thomas H. Cormen',  # Only first author extracted
    'publisher': 'MIT Press',
    'year': '2022',  # 4th edition!
    'isbn': '9780262046305'
}

report = verify_metadata(api_metadata, extracted_metadata)
```

**Result:**
```json
{
  "overall_confidence": 56.0,
  "summary": "Fair metadata quality (56.0% confidence). Verified 5 fields. 2 discrepancies require review.",
  "discrepancies": [
    "year: API='2009' vs Extracted='2022'",
    "isbn: API='9780262033848' vs Extracted='9780262046305'"
  ],
  "fields": {
    "year": {
      "confidence": 0.0,
      "match_type": "none",
      "trusted_source": "review",
      "recommendation": "Significant discrepancy - manual review needed for year"
    },
    "isbn": {
      "confidence": 0.0,
      "match_type": "none",
      "trusted_source": "review",
      "recommendation": "Significant discrepancy - manual review needed for isbn"
    }
  }
}
```

**Action:** Check if API metadata is for wrong edition.

### Example 4: Missing Data

```python
api_metadata = {
    'title': 'Deep Learning',
    'author': 'Ian Goodfellow',
    'publisher': None,  # Missing
    'year': None,       # Missing
    'isbn': None        # Missing
}

extracted_metadata = {
    'title': 'Deep Learning',
    'author': 'Ian Goodfellow',
    'publisher': 'MIT Press',
    'year': '2016',
    'isbn': '9780262035613'
}

report = verify_metadata(api_metadata, extracted_metadata)
```

**Result:**
```json
{
  "overall_confidence": 75.0,
  "summary": "Good metadata quality (75.0% confidence). Verified 5 fields. No significant discrepancies found.",
  "fields": {
    "publisher": {
      "api_value": null,
      "extracted_value": "MIT Press",
      "confidence": 50.0,
      "match_type": "extracted_only",
      "trusted_source": "extracted",
      "recommendation": "Use extracted publisher (no API data available)"
    },
    "year": {
      "api_value": null,
      "extracted_value": "2016",
      "confidence": 50.0,
      "match_type": "extracted_only",
      "trusted_source": "extracted",
      "recommendation": "Use extracted year (no API data available)"
    }
  }
}
```

**Action:** Extracted metadata fills in missing API fields.

## Integration Example

### Automatic Verification in RAG Pipeline

```python
# Document processing with book_details from API
result = await process_document(
    file_path="deep_learning.pdf",
    output_format="markdown",
    book_details={
        'title': 'Deep Learning',
        'author': 'Ian Goodfellow',
        'publisher': 'MIT Press',
        'year': '2016',
        'isbn': '9780262035613'
    }
)

# Verification automatically runs and is saved to metadata sidecar
print(f"Processed: {result['processed_file_path']}")
print(f"Metadata: {result['metadata_file_path']}")

# Read verification results
import json
with open(result['metadata_file_path'], 'r') as f:
    metadata = json.load(f)

verification = metadata.get('verification', {})
if verification:
    print(f"Confidence: {verification['overall_confidence']}%")
    print(f"Summary: {verification['summary']}")

    # Check for issues
    if verification['discrepancies']:
        print("\n⚠️  Discrepancies found:")
        for disc in verification['discrepancies']:
            print(f"  - {disc}")
```

## Decision Logic Examples

### Example: Trust Extracted Metadata

```python
def get_trusted_value(field_name, verification_report):
    """Get the trusted value for a field based on verification."""
    field_info = verification_report['fields'].get(field_name, {})

    if field_info['trusted_source'] == 'extracted':
        return field_info['extracted_value']
    elif field_info['trusted_source'] == 'api':
        return field_info['api_value']
    elif field_info['trusted_source'] == 'both':
        # Prefer extracted for consistency
        return field_info['extracted_value'] or field_info['api_value']
    else:
        # Manual review needed - return both
        return {
            'api': field_info['api_value'],
            'extracted': field_info['extracted_value'],
            'needs_review': True
        }

# Usage
title = get_trusted_value('title', report)
author = get_trusted_value('author', report)
```

### Example: Quality Gates

```python
def check_metadata_quality(verification_report):
    """Check if metadata meets quality standards."""
    confidence = verification_report['overall_confidence']

    if confidence >= 90:
        return "PASS", "Excellent metadata quality"
    elif confidence >= 70:
        return "PASS", "Good metadata quality - minor issues"
    elif confidence >= 50:
        return "WARN", "Fair metadata quality - review recommended"
    else:
        return "FAIL", "Poor metadata quality - manual review required"

# Usage
status, message = check_metadata_quality(report)
if status == "FAIL":
    print(f"❌ {message}")
    # Trigger manual review workflow
elif status == "WARN":
    print(f"⚠️  {message}")
    # Log for periodic review
else:
    print(f"✅ {message}")
```

### Example: Batch Processing with Quality Tracking

```python
import asyncio
from pathlib import Path

async def process_library_with_verification(file_paths, api_metadata_list):
    """Process multiple documents and track verification quality."""
    results = []

    for file_path, api_metadata in zip(file_paths, api_metadata_list):
        try:
            result = await process_document(
                file_path=str(file_path),
                output_format="markdown",
                book_details=api_metadata
            )

            # Load verification results
            with open(result['metadata_file_path'], 'r') as f:
                metadata = json.load(f)

            verification = metadata.get('verification', {})
            results.append({
                'file': file_path.name,
                'confidence': verification.get('overall_confidence', 0),
                'discrepancies': len(verification.get('discrepancies', [])),
                'needs_review': verification.get('overall_confidence', 0) < 50
            })

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            results.append({
                'file': file_path.name,
                'error': str(e)
            })

    # Generate summary report
    print("\n📊 Verification Summary:")
    print(f"Total documents: {len(results)}")

    review_needed = [r for r in results if r.get('needs_review', False)]
    print(f"Requires review: {len(review_needed)}")

    avg_confidence = sum(r['confidence'] for r in results if 'confidence' in r) / len(results)
    print(f"Average confidence: {avg_confidence:.1f}%")

    return results

# Usage
files = list(Path("downloads").glob("*.pdf"))
api_data = [get_api_metadata(f) for f in files]
results = asyncio.run(process_library_with_verification(files, api_data))
```

## Common Patterns

### Pattern 1: Publisher Abbreviations

```python
# API: Short form
api_metadata['publisher'] = "MIT Press"

# Extracted: Full form
extracted_metadata['publisher'] = "Massachusetts Institute of Technology Press"

# Result: 80% fuzzy_good match
# Recommendation: Prefer extracted (full name is more informative)
```

### Pattern 2: Name Order Variations

```python
# API: Last, First
api_metadata['author'] = "Smith, John"

# Extracted: First Last
extracted_metadata['author'] = "John Smith"

# Result: 90% fuzzy_high match
# Recommendation: Prefer extracted (natural reading order)
```

### Pattern 3: Edition Mismatches

```python
# API: 2nd edition
api_metadata['year'] = "2010"
api_metadata['isbn'] = "9781234567890"

# Extracted: 3rd edition
extracted_metadata['year'] = "2015"
extracted_metadata['isbn'] = "9780987654321"

# Result: 0% none match for both fields
# Recommendation: Manual review - likely edition mismatch
```

### Pattern 4: OCR Artifacts in Metadata

```python
# API: Clean
api_metadata['title'] = "Machine Learning"

# Extracted: OCR error
extracted_metadata['title'] = "Machine L earning"  # Extra space

# Result: 90% fuzzy_high match
# Recommendation: Prefer API (extracted has OCR artifact)
```

## Troubleshooting Examples

### Issue: All Fields Show 0% Confidence

**Cause:** Document is different from API description

```python
# Check file integrity
from pathlib import Path
file_path = Path("book.pdf")

# Verify it's the right file
with open(file_path, 'rb') as f:
    first_bytes = f.read(100)
    print(first_bytes)  # Should show PDF header

# Extract and compare
extracted = extract_pdf_metadata(file_path)
print("Extracted title:", extracted['title'])
print("API title:", api_metadata['title'])

# If completely different, wrong file was downloaded
```

### Issue: No Metadata Extracted

**Cause:** Missing dependencies or corrupted file

```python
# Check dependencies
try:
    import fitz
    print("✅ PyMuPDF available")
except ImportError:
    print("❌ PyMuPDF not installed")

try:
    import ebooklib
    print("✅ ebooklib available")
except ImportError:
    print("❌ ebooklib not installed")

# Check file
try:
    doc = fitz.open(str(file_path))
    print(f"✅ PDF opened: {len(doc)} pages")
    print(f"Metadata: {doc.metadata}")
    doc.close()
except Exception as e:
    print(f"❌ Cannot open PDF: {e}")
```

### Issue: Verification Shows Low Confidence for Correct Data

**Cause:** Different representations of same information

```python
# Example: Both correct but different format
api_metadata['year'] = "2023"
extracted_metadata['year'] = "© 2023"  # Has copyright symbol

# Solution: Clean extracted data before comparison
cleaned_year = re.sub(r'[^\d]', '', extracted_metadata['year'])
# Now they match: "2023" == "2023"
```

## Best Practices

1. **Always check discrepancies**: Low confidence doesn't always mean error
2. **Prefer extracted for structural fields**: Title, author, publisher from document are usually authoritative
3. **Trust API for identifiers**: ISBN, catalog IDs are usually correct in API
4. **Review edition mismatches**: Year/ISBN discrepancies often indicate wrong edition
5. **Log all verifications**: Track patterns over time to improve extraction
6. **Use confidence thresholds**: Set organizational standards for acceptable confidence
7. **Automate high-confidence cases**: Only route low-confidence to human review
