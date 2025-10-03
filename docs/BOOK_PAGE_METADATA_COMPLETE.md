# Complete Book Page Metadata Specification

**Date**: 2025-01-30
**Source**: Live analysis of Hegel's "Encyclopaedia of the Philosophical Sciences"
**Page**: `https://z-library.sk/book/1252896/882753/...`

## Executive Summary

Book detail pages contain **EXTENSIVE metadata** far beyond basic bibliographic information. A comprehensive extraction can yield:
- 12 structured properties (publisher, ISBN, series, etc.)
- 816-character description
- 60+ conceptual terms
- 11+ booklist memberships
- IPFS decentralized access
- Online reader integration
- User ratings (1344 users)
- Quality scores
- Categories and classification

---

## Complete Metadata Inventory

### 1. Core Bibliographic Data

| Field | Example Value | Source | Always Present? |
|-------|---------------|--------|-----------------|
| **ID** | `1252896` | URL, download button | ✅ Yes |
| **Title** | `Encyclopaedia of the Philosophical Sciences...` | Multiple locations | ✅ Yes |
| **Authors** | `["Georg Wilhelm Friedrich Hegel", "Klaus Brinkmann", "Daniel O. Dahlstrom"]` | Schema.org JSON | ✅ Yes |
| **Year** | `2010` | bookProperty | ✅ Yes |
| **Publisher** | `Cambridge University Press` | bookProperty | ⚠️ Usually |
| **Language** | `English` | bookProperty | ✅ Yes |
| **Extension** | `PDF` | bookProperty | ✅ Yes |
| **File Size** | `16.12 MB` | bookProperty | ✅ Yes |
| **Pages** | `166` | bookProperty | ⚠️ Usually |

### 2. Identification Numbers

| Field | Example Value | Format | Purpose |
|-------|---------------|--------|---------|
| **ISBN-10** | `0521829143` | bookProperty | Standard ISBN |
| **ISBN-13** | `9780521829144` | bookProperty | Extended ISBN |
| **Book Hash** | `882753` | URL structure | Z-Library internal |
| **Download Hash** | `4ced6f` | Download link | **Different from book hash!** |
| **Terms Hash** | `d46d2b6655e98357b8b020bad751005d` | JavaScript | For term indexing |

### 3. Series and Collections

| Field | Example Value | Notes |
|-------|---------------|-------|
| **Series** | `Cambridge Hegel Translations` | bookProperty |
| **Booklists** | 11 lists (954, 361, 175... books) | z-booklist elements |
| **Categories** | `Society, Politics & Philosophy - Anthropology` | Hierarchical taxonomy |

### 4. Content Description

| Field | Character Count | Format | Usage |
|-------|-----------------|--------|-------|
| **Description** | 816 chars | Plain text | Back cover / publisher description |
| **Terms** | 60 terms | Array of keywords | Conceptual index |

**Sample Description**:
```
Hegel's Encyclopaedia Logic constitutes the foundation of the system of
philosophy presented in his Encyclopaedia of the Philosophical Sciences.
Together with his Science of Logic, it contains the most explicit formulation
of his enduringly influential dialectical method and of the categorical system
underlying his thought...
```

**Sample Terms**:
```
["absolute", "abstract", "activity", "actuality", "concrete", "content",
"determination", "dialectic", "existence", "finite", "hegel", "judgment",
"necessity", "philosophy", "reflection", "subject", "universal", ...]
```

### 5. User-Generated Content

| Field | Example Value | Source | Notes |
|-------|---------------|--------|-------|
| **User Rating** | `5.0 / 5.0` | Schema.org | Overall book rating |
| **Rating Count** | `1344 users` | Schema.org | Number of ratings |
| **Quality Score** | `5.0 / 5.0` | bookProperty | File quality rating |
| **Comments Count** | `0` (this book) | JavaScript | User reviews/comments |
| **User Tags** | Empty (personal) | bookProperty | User's own tags |

### 6. Access Options

| Method | URL/Link | Format | Notes |
|--------|----------|--------|-------|
| **Download** | `/dl/1252896/4ced6f` | Direct download | Requires detail page visit |
| **Online Reader** | `https://reader.z-library.sk/read/25be1f...` | Web reader | No download needed |
| **IPFS #1** | `QmYZ3DuD3GxJsdcadZgQjwPWKW99VxbNqgb4SV3wsfEthT` | IPFS CID | Decentralized access |
| **IPFS #2** | `bafykbzacedcc5fn2wc6v6vzkhc3rlpmhurh7drgbihwznr6ws7k3gayoavbfq` | CID Blake2b | Alternative CID format |

**IPFS Access**:
```
ipfs://QmYZ3DuD3GxJsdcadZgQjwPWKW99VxbNqgb4SV3wsfEthT
# or via gateway
https://ipfs.io/ipfs/QmYZ3DuD3GxJsdcadZgQjwPWKW99VxbNqgb4SV3wsfEthT
```

### 7. Taxonomic Classification

#### Categories (Hierarchical)
```
Society, Politics & Philosophy
  └─ Anthropology
```

**Category URL**: `/category/95/Society-Politics--Philosophy-Anthropology`

#### Terms (Conceptual)

60 terms extracted, including:
- **Hegelian concepts**: dialectic, sublated, determinations, moments
- **Philosophical terms**: reflection, necessity, actuality, objectivity
- **Logical terms**: judgment, syllogism, universal, particular

### 8. Collection Memberships

**11 Booklists** this book appears in:

| List Name | Books | List ID | URL |
|-----------|-------|---------|-----|
| Philosophy | 954 | 409997 | `/booklist/409997/370858/philosophy.html` |
| Logique Mathématique | 361 | 574373 | `/booklist/574373/556ded/...` |
| Cambridge series | 75 | 621565 | `/booklist/621565/008fd7/...` |
| Hegel | 4 | 2702442 | `/booklist/2702442/b73b47/hegel.html` |
| Marx | 196 | 2146969 | `/booklist/2146969/129bd8/marx.html` |
| ... | ... | ... | ... |

---

## Metadata Extraction Priorities

### High Priority (Core Research Value)

1. **Description** (816 chars) - Essential for understanding content
2. **Terms** (60 items) - Enables concept-based discovery
3. **Booklists** (11 lists) - Expert-curated context
4. **Authors** (with URLs) - Author-centric research
5. **Categories** - Taxonomic classification
6. **ISBN-13** - Cross-reference with other systems
7. **Series** - Find related volumes

### Medium Priority (Enhanced Discovery)

8. **Rating & Count** (5.0, 1344 users) - Quality indicator
9. **Quality Score** - File quality assessment
10. **Publisher** - Publisher-focused research
11. **Year** - Temporal analysis
12. **Language** - Language-specific research

### Low Priority (Alternative Access)

13. **IPFS CIDs** (2 formats) - Decentralized backup
14. **Online Reader URL** - Preview without download
15. **Download Hash** - Direct download
16. **Pages** - Length consideration
17. **File Size** - Storage planning

### Optional (User-Specific)

18. **Comments** - User reviews (often empty)
19. **User Tags** - Personal organization
20. **Similar Books** - May be lazy-loaded

---

## Parsing Implementation Strategy

### Method 1: HTML Parsing (Primary)

```python
from bs4 import BeautifulSoup

def extract_complete_metadata(html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')

    metadata = {}

    # 1. Structured properties
    for prop in soup.find_all('div', class_=re.compile(r'bookProperty')):
        label = prop.find('div', class_='property_label').text.strip().rstrip(':')
        value = prop.find(['div', 'span'], class_='property_value').text.strip()
        metadata[label.lower().replace(' ', '_')] = value

    # 2. Terms
    term_links = soup.find_all('a', href=re.compile(r'^/terms/'))
    metadata['terms'] = sorted(set([
        link.get('href').split('/terms/')[-1]
        for link in term_links
    ]))

    # 3. Booklists
    booklists = []
    for bl in soup.find_all('z-booklist'):
        booklists.append({
            'id': bl.get('id'),
            'topic': bl.get('topic'),
            'quantity': int(bl.get('quantity', 0)),
            'url': f"{mirror}{bl.get('href')}"
        })
    metadata['booklists'] = booklists

    # 4. Download link
    dl_button = soup.find('a', class_='addDownloadedBook')
    if dl_button:
        metadata['download_link'] = dl_button.get('href')

    # 5. Online reader
    reader = soup.find('a', class_=re.compile(r'reader-link'))
    if reader:
        metadata['online_reader_url'] = reader.get('href')

    # 6. IPFS CIDs
    ipfs_cids = []
    for cid_span in soup.find_all('span', class_='z-copy-icon'):
        cid = cid_span.get('data-copy')
        if cid and ('Qm' in cid or 'bafy' in cid):
            ipfs_cids.append(cid)
    metadata['ipfs_cids'] = ipfs_cids

    # 7. Categories
    cat_links = soup.find_all('a', href=re.compile(r'^/category/'))
    metadata['categories'] = [
        {'name': link.text.strip(), 'url': link.get('href')}
        for link in cat_links
    ]

    return metadata
```

### Method 2: JavaScript Extraction (for description, rating)

```python
import re

def extract_javascript_metadata(html: str) -> dict:
    js_metadata = {}

    # Description
    desc_match = re.search(r'"description":"([^"]+(?:\\.[^"]*)*)"', html)
    if desc_match:
        js_metadata['description'] = desc_match.group(1).replace('\\"', '"')

    # Rating
    rating_match = re.search(r'"ratingValue":\s*"([^"]+)"', html)
    count_match = re.search(r'"ratingCount":\s*(\d+)', html)
    if rating_match and count_match:
        js_metadata['rating'] = {
            'value': float(rating_match.group(1)),
            'count': int(count_match.group(1))
        }

    # Quality
    quality_match = re.search(r'"quality":"([^"]+)"', html)
    if quality_match:
        js_metadata['quality_score'] = float(quality_match.group(1))

    # Terms hash
    terms_hash_match = re.search(r'"terms_hash":"([^"]+)"', html)
    if terms_hash_match:
        js_metadata['terms_hash'] = terms_hash_match.group(1)

    return js_metadata
```

---

## Complete Metadata Schema

```typescript
interface CompleteBookMetadata {
  // === CORE IDENTIFIERS ===
  id: string;                      // "1252896"
  book_hash: string;               // "882753" (from URL)
  download_hash: string;           // "4ced6f" (from download link)
  terms_hash: string;              // "d46d2b..." (for indexing)

  // === BIBLIOGRAPHIC ===
  title: string;
  authors: Author[];               // With name + URL
  year: number;
  publisher?: string;
  series?: string;
  edition?: string;

  // === IDENTIFICATION ===
  isbn_10?: string;
  isbn_13?: string;
  doi?: string;                    // For academic articles

  // === PHYSICAL/FILE ===
  language: string;
  extension: string;               // "PDF", "EPUB", etc.
  filesize: string;                // "16.12 MB"
  pages?: number;

  // === CONTENT ===
  description: string;             // Full text description
  content_type: "Books" | "Articles" | "Comics" | ...;

  // === CONCEPTUAL ===
  terms: string[];                 // 60+ conceptual terms
  categories: Category[];          // Hierarchical classification

  // === COLLECTIONS ===
  booklists: Booklist[];           // 11+ curated lists

  // === QUALITY METRICS ===
  rating: {
    value: number;                 // 0.0 - 5.0
    count: number;                 // Number of user ratings
  };
  quality_score?: number;          // File quality (0.0 - 5.0)
  downloads?: number;              // Download count (if visible)

  // === ACCESS OPTIONS ===
  download_link: string;           // "/dl/{id}/{hash}"
  online_reader_url?: string;      // Web reader URL
  ipfs_cids: string[];             // Decentralized access (2 formats)

  // === USER INTERACTION ===
  comments_count?: number;
  user_tags?: string[];            // Personal tags (if logged in)

  // === URLS ===
  book_url: string;                // Detail page URL
  author_urls: string[];           // Author profile URLs
  category_urls: string[];         // Category browse URLs
}

interface Author {
  name: string;
  url: string;                     // Profile: /author/{name}
}

interface Category {
  name: string;
  url: string;                     // Browse: /category/{id}/{name}
  level?: number;                  // Hierarchy depth
}

interface Booklist {
  id: string;
  hash: string;
  topic: string;                   // Display name
  quantity: number;                // Total books in list
  url: string;                     // Full URL
}
```

---

## Data Extraction Points

### HTML Elements

```html
<!-- Main container -->
<div class="bookDetailsBox">

  <!-- Each property -->
  <div class="bookProperty property_{field}">
    <div class="property_label">{Label}:</div>
    <div class="property_value">{Value}</div>
  </div>

</div>

<!-- Download button -->
<a class="addDownloadedBook"
   href="/dl/{id}/{download_hash}"
   data-book_id="{id}"
   data-isbn="{isbn}">

<!-- Online reader -->
<a class="reader-link" href="{reader_url}">

<!-- IPFS -->
<span class="z-copy-icon" data-copy="{cid}">

<!-- Terms (scattered throughout page) -->
<a href="/terms/{term}">{term}</a>

<!-- Booklists (in carousel) -->
<z-booklist
  id="{list_id}"
  href="/booklist/{id}/{hash}/{name}.html"
  topic="{display_name}"
  quantity="{book_count}">
```

### JavaScript Objects

```javascript
// Embedded in page
const CurrentBook = new Book({
  "id": "1252896",
  "title": "...",
  "terms_hash": "d46d2b...",
  // More fields
});

// Schema.org structured data
<script type="application/ld+json">
{
  "@type": "Book",
  "name": "...",
  "author": [{
    "@type": "Person",
    "name": "Georg Wilhelm Friedrich Hegel",
    "url": "https://z-library.sk/author/..."
  }],
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "5.0",
    "ratingCount": 1344
  },
  "description": "..."
}
</script>
```

---

## What's NOT Available

❌ **Table of Contents** - Not present on this page
❌ **Preview/Sample** - No sample pages
❌ **Citation Information** - No BibTeX or formatted citations
❌ **Similar Books** - Carousel present but may be lazy-loaded
❌ **User Reviews Text** - Comments section empty for this book
❌ **Edition Details** - No explicit edition numbering
❌ **Translator** - Not in structured fields (may be in description)

---

## Recommended Extraction Approach

### Tier 1: Always Extract (Essential)
```python
essential = [
    'id', 'title', 'authors', 'year', 'language',
    'extension', 'filesize', 'download_link',
    'description', 'terms', 'booklists'
]
```

### Tier 2: Extract When Available (Important)
```python
important = [
    'isbn_13', 'isbn_10', 'publisher', 'series',
    'pages', 'categories', 'rating', 'ipfs_cids',
    'online_reader_url'
]
```

### Tier 3: Extract If Needed (Optional)
```python
optional = [
    'quality_score', 'comments_count', 'user_tags',
    'terms_hash', 'content_type'
]
```

---

## Updated `get_book_metadata` Interface

```typescript
interface GetBookMetadataParams {
  book_id: string;
  book_hash?: string;              // Optional, will fetch if not provided

  // Control what to extract
  include_description?: boolean;   // Default: true
  include_terms?: boolean;         // Default: true
  include_booklists?: boolean;     // Default: true
  include_ipfs?: boolean;          // Default: true
  include_categories?: boolean;    // Default: true
  include_rating?: boolean;        // Default: true

  // Advanced options
  max_terms?: number;              // Limit terms returned (default: all)
  max_booklists?: number;          // Limit booklists (default: all)
}

interface CompleteBookMetadata {
  // Core
  id: string;
  title: string;
  authors: Array<{name: string, url: string}>;
  year: number;
  language: string;
  extension: string;
  filesize: string;

  // Identification
  isbn_10?: string;
  isbn_13?: string;
  book_hash: string;
  download_hash: string;
  terms_hash?: string;

  // Publishing
  publisher?: string;
  series?: string;
  pages?: number;

  // Content
  description?: string;            // 816 chars average
  content_type?: string;

  // Classification
  terms?: string[];                // 60+ terms
  categories?: Array<{name: string, url: string}>;

  // Collections
  booklists?: Array<{
    id: string;
    hash: string;
    topic: string;
    quantity: number;
    url: string;
  }>;

  // Quality
  rating?: {
    value: number;                 // 0.0 - 5.0
    count: number;                 // Number of raters
  };
  quality_score?: number;          // 0.0 - 5.0

  // Access
  download_link: string;           // "/dl/{id}/{hash}"
  book_url: string;                // Detail page URL
  online_reader_url?: string;      // Web reader
  ipfs_cids?: string[];            // Decentralized access

  // Statistics
  comments_count?: number;
  downloads_count?: number;

  // User-specific
  user_tags?: string[];
}
```

---

## Performance Considerations

### Extraction Cost

**Full metadata extraction**:
- 1 HTTP request (detail page)
- ~200KB HTML
- ~2 seconds parsing time
- Returns ~2KB structured JSON

**Cost-Benefit**: Very favorable - single request yields comprehensive data

### Caching Strategy

```typescript
// Cache complete metadata for 6 hours
cache.set(`book:${id}:complete`, metadata, 21600);

// Cache individual sections separately
cache.set(`book:${id}:terms`, metadata.terms, 86400);         // 24h
cache.set(`book:${id}:booklists`, metadata.booklists, 86400); // 24h
cache.set(`book:${id}:description`, metadata.description, 86400);
```

---

## Research Workflow Applications

### 1. Concept Mapping

```typescript
// Build concept map from a book
const book = await get_book_metadata({
  book_id: "1252896",
  include_terms: true
});

// Explore each term
for (const term of book.terms.slice(0, 10)) {
  const term_books = await explore_term({ term, limit: 5 });
  // Build graph: book → term → related books
}
```

### 2. Collection Discovery

```typescript
// Find all collections containing a book
const book = await get_book_metadata({
  book_id: "1252896",
  include_booklists: true
});

// Explore related collections
for (const list of book.booklists) {
  if (list.quantity < 100) {  // Manageable size
    const list_books = await get_booklist({
      list_id: list.id,
      list_hash: list.hash
    });
    // Download entire curated collection
  }
}
```

### 3. Author Network

```typescript
// Get all works by book's authors
const book = await get_book_metadata({ book_id: "1252896" });

for (const author of book.authors) {
  const author_works = await search_books_advanced({
    query: `author:${author.name}`,
    exact_limit: 50
  });
  // Build author corpus
}
```

### 4. Decentralized Access

```typescript
// Access via IPFS without Z-Library
const book = await get_book_metadata({
  book_id: "1252896",
  include_ipfs: true
});

const ipfs_url = `ipfs://${book.ipfs_cids[0]}`;
// Use IPFS client or gateway
const gateway_url = `https://ipfs.io/ipfs/${book.ipfs_cids[0]}`;
```

---

## Comparison: Current vs Complete Implementation

### Current `get_book_by_id` (Deprecated)

Returns:
- Basic book info only
- No description
- No terms
- No booklists
- **Limited value for research**

### Proposed `get_book_metadata` (Comprehensive)

Returns:
- ✅ All 12 structured properties
- ✅ 816-char description
- ✅ 60+ conceptual terms
- ✅ 11+ booklist memberships
- ✅ Multiple access options (download, reader, IPFS)
- ✅ Quality metrics (rating, quality score)
- ✅ Categories and classification
- **Massive value for research workflows**

---

## Implementation Priority

### Phase 1: Core Metadata
- Properties extraction (already working)
- Description extraction
- Download link (already working)

### Phase 2: Research Features
- Terms extraction (60+ per book)
- Booklists extraction (11+ per book)
- Author extraction with URLs

### Phase 3: Quality & Access
- Rating/quality scores
- IPFS CIDs
- Online reader URL
- Categories

### Phase 4: Advanced
- Comments/reviews (when present)
- Similar books (lazy-loaded)
- User-specific data (tags)

---

## Testing Strategy

### Test with Multiple Book Types

1. **Philosophy book** (current): Rich metadata, many terms, multiple lists
2. **Novel**: Different structure, fewer terms, different lists
3. **Technical book**: Different categories, different terms
4. **Article**: Different schema, DOI instead of ISBN
5. **Comic**: Minimal metadata
6. **Foreign language book**: Language-specific considerations

### Test Data Fixtures

Create `test_files/book_pages/`:
- `philosophy_rich_metadata.html` - Current Hegel book
- `novel_basic_metadata.html` - Fiction with minimal metadata
- `article_doi.html` - Academic article structure
- `no_description.html` - Book without description
- `no_booklists.html` - Book not in any lists
- `many_authors.html` - Book with 5+ authors

---

## Conclusion

Book detail pages contain **significantly more metadata** than currently extracted. A comprehensive `get_book_metadata` tool should extract:

**Minimum 15 fields**:
1. ID, title, authors, year, language
2. Extension, filesize, download_link
3. Description, terms, booklists
4. ISBN-13, publisher, categories
5. Rating

**Optimal 25+ fields**:
- Everything above PLUS
- Series, pages, quality score
- IPFS CIDs, online reader
- Author URLs, category URLs
- Comments count, user tags
- Multiple ISBNs, terms hash

This rich metadata enables sophisticated research workflows: concept mapping, collection building, author studies, citation analysis, and knowledge graph construction.

---

**Recommendation**: Implement comprehensive extraction to unlock Z-Library's full research potential.