# Phase 3 MCP Tools Testing Plan

**Status**: ⏳ Awaiting MCP Server Reload
**New Tools**: 5 (get_book_metadata, search_by_term, search_by_author, fetch_booklist, search_advanced)

---

## Current Status

**MCP Server State**:
- ✅ TypeScript rebuilt with new tools
- ✅ Code merged to master
- ⏳ **Needs reload** in Claude Code to pick up new tools

**How to Reload**:
1. Restart Claude Code, OR
2. Reload MCP servers configuration

Once reloaded, 11 tools should be available (was 6).

---

## Testing Checklist

### ✅ Previously Validated Tools (6 working)

- [x] search_books - Working (tested multiple times)
- [x] full_text_search - Working (tested with "dialectic method")
- [x] download_book_to_file - Working (3 books downloaded!)
- [x] process_document_for_rag - Working (125KB text extracted)
- [x] get_download_limits - Working (997/999 shown)
- [x] get_download_history - Working (empty list)

---

### 🆕 New Tools to Test (5 pending)

#### Test 1: get_book_metadata 🔴 CRITICAL

**Purpose**: Extract 60 terms, 11 booklists, complete metadata

**Test Case**:
```typescript
mcp__zlibrary__get_book_metadata({
  bookId: "1252896",    // Hegel's Encyclopaedia
  bookHash: "882753"
})
```

**Expected Result**:
```json
{
  "terms": ["absolute", "dialectic", "reflection", ...],  // 60+ items
  "booklists": [
    {"id": "409997", "topic": "Philosophy", "quantity": 954},
    ...  // 11+ items
  ],
  "description": "...",  // 800+ chars
  "ipfs_cids": [...],    // 2 formats
  "rating": {...},
  "series": "...",
  "categories": [...],
  "isbn_10": "...",
  "isbn_13": "...",
  "quality_score": 4.5
}
```

**Validates**:
- Metadata extraction works via MCP
- 60 terms accessible to users
- 11 booklists accessible to users
- CORE VALUE PROPOSITION available

**Priority**: 🔴 CRITICAL - This is our main innovation!

---

#### Test 2: search_by_term 🔴 CRITICAL

**Purpose**: Enable conceptual navigation

**Test Case**:
```typescript
mcp__zlibrary__search_by_term({
  term: "dialectic",
  count: 5
})
```

**Expected Result**:
```json
{
  "term": "dialectic",
  "books": [
    {"id": "...", "title": "...", "url": "..."},
    ... // 5 books
  ],
  "total_results": 150
}
```

**Validates**:
- Term-based search works
- Conceptual navigation functional
- Knowledge graph building possible

**Priority**: 🔴 CRITICAL - Unique differentiator

---

#### Test 3: fetch_booklist 🔴 CRITICAL

**Purpose**: Explore expert-curated collections

**Test Case**:
```typescript
mcp__zlibrary__fetch_booklist({
  booklistId: "409997",
  booklistHash: "370858",
  topic: "philosophy",
  page: 1
})
```

**Expected Result**:
```json
{
  "booklist_id": "409997",
  "metadata": {
    "name": "Philosophy",
    "total_books": 954
  },
  "books": [
    {"id": "...", "title": "...", ...},
    ... // 25 books per page
  ],
  "page": 1
}
```

**Validates**:
- Booklist fetching works
- Collection exploration functional
- Access to 954 curated philosophy books

**Priority**: 🔴 CRITICAL - Major feature

---

#### Test 4: search_advanced 🟡 HIGH

**Purpose**: Fuzzy match detection

**Test Case**:
```typescript
mcp__zlibrary__search_advanced({
  query: "Hegelian",
  count: 10
})
```

**Expected Result**:
```json
{
  "has_fuzzy_matches": true,
  "exact_matches": [
    {"id": "...", "title": "Hegelian Philosophy", ...}
  ],
  "fuzzy_matches": [
    {"id": "...", "title": "Neo-Hegelian Studies", ...},
    {"id": "...", "title": "Hegel's Philosophy", ...}
  ],
  "total_results": 50
}
```

**Validates**:
- Fuzzy detection works
- Exact vs approximate separation
- Topic discovery enabled

**Priority**: 🟡 HIGH - Advanced feature

---

#### Test 5: search_by_author 🟡 MEDIUM

**Purpose**: Advanced author search

**Test Case**:
```typescript
mcp__zlibrary__search_by_author({
  author: "Hegel, Georg Wilhelm Friedrich",
  exact: true,
  count: 10
})
```

**Expected Result**:
```json
{
  "author": "Hegel, Georg Wilhelm Friedrich",
  "books": [
    {"id": "...", "title": "...", ...},
    ... // 10 books
  ],
  "total_results": 50
}
```

**Validates**:
- Author search works
- Name format handling
- Exact matching option

**Priority**: 🟡 MEDIUM - Has workaround (authors: syntax)

---

## Workflow Validation Tests

### After Individual Tool Tests Pass

**Test Each of the 8 Research Workflows**:

#### Workflow 1: Literature Review ✅ (Already Validated)
- search_books → download → process_for_rag
- Status: WORKING

#### Workflow 2: Citation Network 🆕
```
1. search_by_author("Hegel")
2. get_book_metadata(first book) → extract 11 booklists
3. fetch_booklist(first booklist) → get collection
4. Analyze author connections
```

#### Workflow 3: Conceptual Navigation 🆕
```
1. search_by_term("dialectic") → find 150 books
2. get_book_metadata(top book) → extract 60 terms
3. search_by_term(related term) → explore connections
4. Build conceptual graph
```

#### Workflow 4: Topic Discovery 🆕
```
1. search_advanced("Hegelian") → get exact + fuzzy
2. Analyze fuzzy matches for variations
3. Explore each variation
4. Build topic taxonomy
```

#### Workflow 5: Collection Exploration 🆕
```
1. get_book_metadata(any book) → extract 11 booklists
2. fetch_booklist(Philosophy) → 954 books
3. Filter by criteria
4. Build curated reading list
```

#### Workflow 6: RAG Knowledge Base ✅ (Already Validated)
- search → download(process_for_rag=true)
- Status: WORKING

#### Workflow 7: Comparative Analysis 🆕
```
1. search_by_author("Hegel") → works
2. search_by_author("Marx") → works
3. get_book_metadata for both → compare terms
4. Identify differences
```

#### Workflow 8: Temporal Analysis ✅ (Already Validated)
- search with year filters
- Status: WORKING

---

## Success Criteria

**Individual Tools**:
- [ ] All 5 new tools callable via MCP
- [ ] All return proper JSON structures
- [ ] No errors or crashes
- [ ] Results match Python test expectations

**Workflows**:
- [x] 3/8 workflows working (Literature Review, RAG, Temporal)
- [ ] 8/8 workflows working (all enabled by new tools)

**Performance**:
- [ ] Each tool responds in <5s
- [ ] No rate limiting issues
- [ ] No memory leaks

**Data Quality**:
- [ ] 60 terms extracted (matches our validation)
- [ ] 11 booklists extracted (matches our validation)
- [ ] All metadata fields present
- [ ] Fuzzy matching accurate

---

## Expected Timeline

**After MCP Reload**:
- Test 1 (get_book_metadata): 5 min
- Test 2 (search_by_term): 3 min
- Test 3 (fetch_booklist): 3 min
- Test 4 (search_advanced): 3 min
- Test 5 (search_by_author): 3 min
- Workflow validation: 10 min
- Documentation: 5 min

**Total**: 30-40 minutes

---

## Known Good Test Data

**For get_book_metadata**:
- Book ID: 1252896 (Hegel's Encyclopaedia)
- Hash: 882753
- Expected: 60 terms, 11 booklists

**For search_by_term**:
- Term: "dialectic"
- Expected: 150+ results

**For fetch_booklist**:
- ID: 409997
- Hash: 370858
- Topic: "philosophy"
- Expected: 954 books total

**For search_advanced**:
- Query: "Hegelian"
- Expected: Fuzzy matches present

**For search_by_author**:
- Author: "Hegel"
- Expected: 10+ results

---

## What This Proves

**Once All Tests Pass**:
- ✅ Complete TypeScript → Python bridge working
- ✅ All 186 tests validated
- ✅ All Phase 3 features accessible via MCP
- ✅ All 8 workflows enabled
- ✅ 100% of features available to users
- ✅ Production-ready system

**Grade**: A (fully validated)

---

## Next Action

**Reload MCP Server in Claude Code** to load the 5 new tools, then run the tests above.
