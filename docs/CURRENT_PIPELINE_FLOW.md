# Current RAG Pipeline Flow (As Implemented)

**Generated**: 2025-10-13
**Status**: INCORRECT - Does not match user requirements

---

## What I Implemented (WRONG)

### Filename Format
**Current**: `han-burnout-society-3505318.pdf`
- Lowercase slugs
- Dashes as separators
- Author lastname only

**YOU WANTED**: `ByungChulHan_TheBurnoutSociety_3505318.pdf`
- CamelCase names/titles
- Underscores as separators
- Full author name (not just lastname)

### Main Markdown Output
**Current**: Includes YAML frontmatter
```markdown
---
title: The Burnout Society
author: Byung-Chul Han
---

`[p.1]`

Content...
```

**YOU WANTED**: CLEAN markdown (no front matter clutter)
```markdown
`[p.1]`

Content...
```

### Front Matter Handling
**Current**: Added to main markdown as YAML frontmatter

**YOU WANTED**: Extracted and moved to separate metadata JSON file ONLY

---

## Current Pipeline Flow

### PDF Processing (`process_pdf`)
1. Open PDF with PyMuPDF
2. For each page:
   - Extract with `_format_pdf_markdown(page)` (block analysis)
   - Add page marker: `` `[p.{N}]` ``
   - Append to content
3. Preprocess: `_identify_and_remove_front_matter()` + `_extract_and_format_toc()`
4. **Add YAML frontmatter** ← WRONG (you don't want this)
5. Save to: `{author-slug}-{title-slug}-{id}.pdf.processed.markdown` ← WRONG FORMAT
6. Generate metadata sidecar JSON

### EPUB Processing (`process_epub`)
1. Read EPUB with ebooklib
2. For each section/item:
   - Add section marker: `` `[section.{N}: {item_name}]` ``
   - Convert HTML to markdown
3. Preprocess same as PDF
4. **Add YAML frontmatter** ← WRONG
5. Save to: `{author-slug}-{title-slug}-{id}.epub.processed.markdown` ← WRONG FORMAT
6. Generate metadata sidecar JSON

### Download (`download_book`)
1. Download from Z-Library
2. Rename to: `{author-slug}-{title-slug}-{id}.{ext}` ← WRONG FORMAT
3. Optionally process for RAG

---

## What You Actually Requested

### Filename Format
```
ByungChulHan_TheBurnoutSociety_3505318.pdf
ByungChulHan_TheBurnoutSociety_3505318.pdf.processed.markdown
ByungChulHan_TheBurnoutSociety_3505318.pdf.metadata.json
```

**Requirements**:
- CamelCase for author names (remove spaces, capitalize each word)
- CamelCase for book titles (same logic)
- Underscores between components
- Consistent across download, RAG, and metadata files

### Main Markdown Output (CLEAN for RAG)
```markdown
`[p.1]`

Every age has its signature afflictions...

`[p.2]`

Thus, a bacterial age existed...
```

**Requirements**:
- NO YAML frontmatter
- NO front matter content (copyright, publisher, etc.)
- ONLY the actual book text
- Page markers for citations
- Clean and optimized for RAG ingestion

### Metadata Sidecar (ALL metadata here)
```json
{
  "frontmatter": {
    "title": "The Burnout Society",
    "author": "Byung-Chul Han",
    "translator": "Erik Butler",
    "publisher": "Stanford University Press",
    "copyright": "...",
    "isbn": "..."
  },
  "toc": [...],
  "page_line_mapping": {...}
}
```

**Requirements**:
- Extract front matter FROM main markdown
- Store in metadata JSON
- Include TOC with page AND line numbers
- Include page-to-line mappings

### PDF OCR Requirements
- Detect and fix letter spacing ("T H E" → "THE")
- Run OCR again if quality is poor
- Preserve page numbers
- Extract front matter to metadata (not main doc)

---

## What I Got Wrong

1. ❌ **Filename format**: Used lowercase-dashes instead of CamelCase_Underscores
2. ❌ **YAML frontmatter**: Added to main doc (you wanted CLEAN doc)
3. ❌ **Front matter**: Didn't extract/remove properly (still in main doc)
4. ✅ **Page markers**: Correct
5. ✅ **Section markers**: Correct
6. ✅ **OCR letter spacing**: Correct
7. ✅ **Metadata sidecar**: Correct concept, wrong execution
8. ✅ **PDF pipeline architecture**: Fixed correctly

---

## Next Actions Required

1. Fix filename generation to CamelCase_Underscores
2. Remove YAML frontmatter from main output
3. Enhance front matter extraction (copyright, publisher, etc.)
4. Move extracted front matter to metadata JSON ONLY
5. Ensure main markdown is CLEAN (just content + page markers)
6. Update all tests
7. Show you examples before committing

---

*I apologize for misunderstanding your requirements. Let me fix this properly.*
