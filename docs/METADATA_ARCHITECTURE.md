# Metadata Architecture Design

**Date**: 2025-10-13
**Purpose**: Unified metadata schema supporting books, articles, and future document types

---

## Design Principles

### 1. Source Fusion Strategy

**Multiple Metadata Sources**:
1. **Z-Library API** (external, authoritative)
   - Structured data: author, title, year, ISBN, publisher
   - Verified and standardized
   - May lack detail (e.g., translator, edition specifics)

2. **OCR Extraction** (from document itself)
   - Detailed data: copyright text, dedication, epigraph, translator notes
   - May have OCR errors
   - Contains information not in API

3. **Document Analysis** (computed)
   - Word count, page count, TOC structure
   - Page-to-line mappings
   - Processing metadata

**Fusion Priority**:
```
Structured fields (author, title, year, ISBN):
  API data (primary) → OCR extraction (supplementary) → fallback to "Unknown"

Unstructured fields (copyright text, dedication):
  OCR extraction (only source) → None if not found

Computed fields (word_count, TOC):
  Document analysis (only source)
```

**Conflict Resolution**:
- If API and OCR disagree on structured field → Use API, log discrepancy
- Example: API says year=2015, OCR extracts 2010 → Use 2015, note conflict
- Store both in metadata: `"year": 2015, "year_ocr_extracted": 2010`

### 2. Terminology for Document Types

**Problem**: "frontmatter" is book-specific, doesn't apply to articles/essays.

**Solution**: Domain-specific terminology in flexible schema

```json
{
  "document_type": "book",  // or "article", "essay", "thesis", etc.

  // For books:
  "frontmatter": {
    "title_page": {...},
    "copyright_page": {...},
    "dedication": "...",
    "epigraph": "..."
  },

  // For articles:
  "article_header": {
    "title": "...",
    "authors": [...],
    "journal": "...",
    "volume": "...",
    "issue": "...",
    "pages": "...",
    "doi": "...",
    "abstract": "..."
  }
}
```

---

## Unified Metadata Schema

### Book Metadata Structure

```json
{
  "document_type": "book",
  "source": {
    "zlibrary_id": "3505318",
    "api_data": {
      "title": "The Burnout Society",
      "author": "Byung-Chul Han",
      "year": "2015",
      "isbn": "9780804795098",
      "publisher": "Stanford University Press",
      "extension": "pdf",
      "language": "English"
    },
    "original_filename": "ByungChulHan_TheBurnoutSociety_3505318.pdf"
  },

  "frontmatter": {
    "extraction_method": "ocr",  // or "epub_metadata"
    "title_page": {
      "title": "THE BURNOUT SOCIETY",
      "author": "BYUNG-CHUL HAN",
      "translator": "Translated by Erik Butler"
    },
    "copyright_page": {
      "copyright": "English translation ©2015 by the Board of Trustees...",
      "publisher": "Stanford University Press",
      "address": "Stanford, California",
      "isbn_hardcover": "978-0-8047-9508-1",
      "isbn_paperback": "978-0-8047-9509-8",
      "isbn_electronic": "978-0-8047-9510-4",
      "library_of_congress": "BF482.H35513 2015",
      "subjects": ["Fatigue", "Burn out (Psychology)", "Time pressure"]
    },
    "original_publication": {
      "title": "Müdigkeitsgesellschaft",
      "year": "2010",
      "publisher": "Matthes & Seitz Berlin"
    },
    "dedication": "...",  // If present
    "epigraph": "...",     // If present
    "acknowledgments": "..."  // If present
  },

  "toc": [
    {
      "title": "Neuronal Power",
      "level": 1,
      "page": 1,
      "line_start": 85,
      "line_end": 234
    }
  ],

  "page_line_mapping": {
    "1": {"start": 85, "end": 102},
    "2": {"start": 103, "end": 125}
  },

  "processing": {
    "date": "2025-10-13T12:00:00",
    "output_format": "markdown",
    "word_count": 17201,
    "page_count": 117,
    "corrections_applied": ["letter_spacing_correction"],
    "ocr_quality_score": 0.95,
    "extraction_confidence": {
      "frontmatter": 0.92,
      "toc": 0.98
    }
  },

  "conflicts": [
    {
      "field": "year",
      "api_value": "2015",
      "ocr_value": "2010",
      "resolution": "Used API value",
      "note": "OCR may have extracted original German publication year"
    }
  ]
}
```

### Article Metadata Structure

```json
{
  "document_type": "article",
  "source": {
    "zlibrary_id": "1234567",
    "api_data": {
      "title": "Phenomenology and Deconstruction",
      "authors": ["Jacques Derrida", "Edmund Husserl"],
      "year": "1985",
      "language": "English"
    }
  },

  "article_header": {
    "extraction_method": "pdf_parse",
    "title": "Phenomenology and Deconstruction: A Reading of Husserl",
    "authors": [
      {
        "name": "Jacques Derrida",
        "affiliation": "École des Hautes Études en Sciences Sociales",
        "email": null
      }
    ],
    "journal": {
      "name": "Philosophy Today",
      "volume": "29",
      "issue": "2",
      "pages": "134-147",
      "issn": "0031-8256"
    },
    "doi": "10.5840/philtoday198529234",
    "abstract": "This article examines...",
    "keywords": ["phenomenology", "deconstruction", "Husserl"],
    "received_date": "1984-12-15",
    "published_date": "1985-06-01"
  },

  "toc": null,  // Articles typically don't have TOC

  "sections": [
    {"title": "Introduction", "line_start": 50},
    {"title": "Husserl's Transcendental Reduction", "line_start": 120},
    {"title": "Conclusion", "line_start": 450}
  ],

  "processing": {
    "date": "2025-10-13",
    "output_format": "markdown",
    "word_count": 6543
  }
}
```

---

## Metadata Fusion Algorithm

### Phase 1: Collect from All Sources

```python
def fuse_metadata(api_data: dict, ocr_extracted: dict, computed: dict) -> dict:
    """
    Fuse metadata from multiple sources with conflict detection.
    """
    metadata = {
        "source": {
            "zlibrary_id": api_data.get('id'),
            "api_data": api_data
        },
        "conflicts": []
    }

    # Structured fields: API takes precedence
    structured_fields = ['title', 'author', 'year', 'isbn', 'publisher']

    for field in structured_fields:
        api_value = api_data.get(field)
        ocr_value = ocr_extracted.get(field)

        if api_value and ocr_value and api_value != ocr_value:
            # Conflict detected
            metadata['conflicts'].append({
                'field': field,
                'api_value': api_value,
                'ocr_value': ocr_value,
                'resolution': 'Used API value'
            })
            final_value = api_value
        else:
            final_value = api_value or ocr_value

        if final_value:
            metadata[field] = final_value

    # Unstructured fields: OCR only
    if ocr_extracted:
        metadata['frontmatter'] = ocr_extracted.get('frontmatter', {})

    # Computed fields: Always from analysis
    metadata.update(computed)

    return metadata
```

### Phase 2: Enhanced Front Matter Extraction

**What to Extract**:

**Book Frontmatter**:
- Title page: Title, subtitle, author, translator
- Copyright page: ©, publisher, ISBN (all variants), LOC classification
- Original publication info (for translations)
- Dedication (if present)
- Epigraph (if present)
- Series information
- Edition information

**Article Header**:
- Title
- Authors with affiliations
- Journal/conference info
- Volume/issue/pages
- DOI
- Abstract
- Keywords
- Dates (received, revised, published)

### Phase 3: Detection Strategy

```python
def detect_document_type(text_sample: str, api_data: dict) -> str:
    """
    Detect if document is book, article, essay, thesis, etc.
    """
    # Check API hints
    if 'journal' in api_data or 'doi' in api_data:
        return 'article'

    # Check text patterns
    if re.search(r'(Volume|Vol\.|Issue|pp\.)\s+\d+', text_sample):
        return 'article'

    if re.search(r'(Chapter|Dedication|Copyright ©)', text_sample):
        return 'book'

    # Default
    return 'book'
```

---

## Proposed Implementation

### Filename Generation (CamelCase_Underscores)

```python
def to_camel_case(text: str) -> str:
    """Convert 'Byung-Chul Han' → 'ByungChulHan'"""
    words = re.sub(r'[^A-Za-z0-9\s]', ' ', text).split()
    return ''.join(word.capitalize() for word in words if word)

def create_unified_filename(book_details: dict) -> str:
    """
    Create: ByungChulHan_TheBurnoutSociety_3505318.pdf
    """
    author_camel = to_camel_case(book_details.get('author', 'UnknownAuthor'))
    title_camel = to_camel_case(book_details.get('title', 'UntitledBook'))
    book_id = str(book_details.get('id', 'NoID'))
    extension = book_details.get('extension', 'pdf')

    return f"{author_camel}_{title_camel}_{book_id}.{extension}"
```

### Main Markdown (CLEAN)

```markdown
`[p.1]`

Every age has its signature afflictions.

`[p.2]`

Thus, a bacterial age existed...
```

**NO**:
- ❌ YAML frontmatter
- ❌ Copyright text
- ❌ Publisher info
- ❌ Dedication/epigraph

**YES**:
- ✅ Page markers
- ✅ Main book text only
- ✅ TOC (if formatted as content)

### Metadata Sidecar (Flexible Schema)

```json
{
  "document_type": "book",  // or "article", "essay"

  "source": {
    "zlibrary": {
      "id": "3505318",
      "title": "The Burnout Society",
      "author": "Byung-Chul Han",
      "year": "2015",
      "isbn": "9780804795098",
      "publisher": "Stanford University Press"
    }
  },

  "extracted": {
    "method": "pdf_ocr",  // or "epub_metadata"
    "confidence": 0.92,

    "book_frontmatter": {  // Only if document_type == "book"
      "title_page": {
        "main_title": "THE BURNOUT SOCIETY",
        "subtitle": null,
        "author": "BYUNG-CHUL HAN",
        "translator": "Translated by Erik Butler"
      },
      "copyright_page": {
        "copyright_text": "English translation ©2015...",
        "publisher_full": "Stanford University Press, Stanford, California",
        "isbn": {
          "hardcover": "978-0-8047-9508-1",
          "paperback": "978-0-8047-9509-8",
          "electronic": "978-0-8047-9510-4"
        },
        "library_of_congress": {
          "call_number": "BF482.H35513 2015",
          "subjects": ["Fatigue", "Burn out (Psychology)", "Time pressure"]
        }
      },
      "original_publication": {
        "title": "Müdigkeitsgesellschaft",
        "year": "2010",
        "publisher": "Matthes & Seitz Berlin"
      },
      "dedication": "...",  // if present
      "epigraph": {         // if present
        "text": "...",
        "attribution": "..."
      },
      "series": "Cultural Memory in the Present"  // if present
    },

    "article_header": null  // Only if document_type == "article"
  },

  "fused": {
    // Canonical fields after fusion
    "title": "The Burnout Society",
    "author": "Byung-Chul Han",
    "translator": "Erik Butler",
    "publisher": "Stanford University Press",
    "year": "2015",
    "isbn": "9780804795098",  // Primary ISBN
    "all_isbns": ["978-0-8047-9508-1", "978-0-8047-9509-8", "978-0-8047-9510-4"]
  },

  "conflicts": [
    {
      "field": "year",
      "api_value": "2015",
      "extracted_value": "2010",
      "resolution": "api_value",
      "explanation": "API shows English edition (2015), extracted shows German original (2010)"
    }
  ],

  "toc": [...],
  "page_line_mapping": {...},
  "processing": {...}
}
```

---

## Article-Specific Schema

For when Z-Library adds article support:

```json
{
  "document_type": "article",

  "source": {
    "zlibrary": {
      "id": "7890123",
      "title": "Phenomenology and Deconstruction",
      "authors": ["Jacques Derrida"],
      "year": "1985"
    }
  },

  "extracted": {
    "method": "pdf_parse",

    "article_header": {
      "title": "Phenomenology and Deconstruction: A Reading of Husserl",
      "subtitle": null,
      "authors": [
        {
          "name": "Jacques Derrida",
          "affiliation": "École des Hautes Études en Sciences Sociales",
          "corresponding": true
        }
      ],
      "journal": {
        "name": "Philosophy Today",
        "abbreviation": "Phil. Today",
        "volume": "29",
        "issue": "2",
        "pages": {"start": 134, "end": 147},
        "issn": "0031-8256"
      },
      "doi": "10.5840/philtoday198529234",
      "urls": {
        "canonical": "https://...",
        "pdf": "https://..."
      },
      "dates": {
        "received": "1984-12-15",
        "revised": "1985-01-20",
        "accepted": "1985-02-10",
        "published": "1985-06-01"
      },
      "abstract": "This article examines the relationship between...",
      "keywords": ["phenomenology", "deconstruction", "Husserl", "intentionality"],
      "acknowledgments": "The author thanks...",
      "funding": null,
      "citations": {
        "total": 45,
        "self_citations": 3
      }
    },

    "book_frontmatter": null  // Only for books
  },

  "fused": {
    "title": "Phenomenology and Deconstruction: A Reading of Husserl",
    "authors": ["Jacques Derrida"],
    "year": "1985",
    "journal": "Philosophy Today",
    "doi": "10.5840/philtoday198529234"
  },

  "sections": [  // Articles have sections, not TOC
    {"title": "Introduction", "line_start": 50},
    {"title": "Husserl's Transcendental Reduction", "line_start": 120},
    {"title": "Deconstructive Reading", "line_start": 280},
    {"title": "Conclusion", "line_start": 450}
  ],

  "processing": {
    "date": "2025-10-13",
    "word_count": 6543
  }
}
```

---

## Field Mapping (Citation Formats)

### For Citation Generators

The metadata should support multiple citation formats:

**Chicago**:
```
Han, Byung-Chul. The Burnout Society. Translated by Erik Butler.
Stanford: Stanford University Press, 2015.
```

**BibTeX**:
```bibtex
@book{han2015burnout,
  title={The Burnout Society},
  author={Han, Byung-Chul},
  translator={Butler, Erik},
  year={2015},
  publisher={Stanford University Press},
  address={Stanford, CA},
  isbn={978-0-8047-9509-8}
}
```

**All data needed is in metadata sidecar.**

---

## Front Matter Extraction Strategy

### For PDFs

**1. Detect front matter pages** (usually first 1-10 pages):
```python
def detect_frontmatter_pages(doc):
    """
    Heuristics:
    - Page with "Copyright ©"
    - Page with ISBN
    - Page with "All rights reserved"
    - Page with "Library of Congress"
    - Typically pages 1-5 of document
    """
```

**2. Extract structured data**:
```python
def extract_copyright_page(page_text):
    """
    Parse copyright page for:
    - Copyright statement (© year, holder)
    - Publisher name and address
    - ISBN(s) - all variants
    - Library of Congress info
    - Edition information
    """
```

**3. Remove from main content**:
- Front matter pages NOT included in main markdown
- Stored ONLY in metadata sidecar

### For EPUBs

**1. Use EPUB metadata** (already structured):
```python
book.get_metadata('DC', 'title')
book.get_metadata('DC', 'creator')  # Author
book.get_metadata('DC', 'publisher')
book.get_metadata('DC', 'date')
book.get_metadata('DC', 'identifier')  # ISBN
```

**2. Extract from content** (if needed):
- Parse first few items for copyright/dedication
- Usually in separate XHTML files

---

## Implementation Priority

### Phase 1 (Now):
1. ✅ Fix filename to CamelCase_Underscores
2. ✅ Remove YAML frontmatter from main doc
3. ✅ Basic front matter extraction (copyright, ISBN, publisher)
4. ✅ Store extracted data in metadata sidecar

### Phase 2 (Future):
1. Enhanced OCR front matter extraction
2. Article header detection and parsing
3. DOI extraction for articles
4. Citation format generators (BibTeX, CSL JSON)

### Phase 3 (When articles added):
1. Document type detection
2. Article-specific schema
3. Section extraction for articles
4. Journal metadata parsing

---

## Questions for Clarification

**1. Filename Format - Exact Specification:**
- Author: "Byung-Chul Han" → "ByungChulHan" (remove ALL spaces/hyphens)?
- Or: "ByungChul-Han" (preserve meaningful hyphens)?
- Multiple authors: "Derrida_Nancy" or "DerridaNancy"?

**2. Front Matter Extraction Priority:**
- Should I extract front matter NOW (Phase 1)?
- Or just prepare the schema and extract later?

**3. Main Markdown Content:**
- Should TOC formatted as markdown be included? Or removed?
- Should chapter headings be included? Or removed?

**4. Metadata Terminology:**
- Use "book_frontmatter" and "article_header" as shown?
- Or different naming convention?

Please clarify and I'll implement exactly what you want!
