---
status: testing
phase: 05-feature-porting-branch-cleanup
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: 2026-02-01T12:00:00Z
updated: 2026-02-01T12:00:00Z
---

## Current Test

number: 1
name: Tiered metadata response with include parameter
expected: |
  Calling `get_book_metadata` without an `include` parameter returns only core scalar fields (id, title, author, year, publisher, language, pages, isbn, rating, cover, categories, extension, filesize, series). Adding `include: ["terms", "booklists"]` returns those additional groups alongside the core fields.
awaiting: user response

## Tests

### 1. Tiered metadata response with include parameter
expected: Calling `get_book_metadata` without `include` returns only core scalar fields. Adding `include: ["terms", "booklists"]` returns those additional groups alongside core fields.
result: [pending]

### 2. Filename disambiguation with year and language
expected: When downloading a book, the saved filename includes year and language when available, in format `Author_Title_Year_Lang_BookID.ext` (e.g. `Author_Title_2020_engli_12345.epub`).
result: [pending]

### 3. Search results include title and author fields
expected: Calling `search_books` returns results where each book has explicit `title` (string) and `author` (string) fields in addition to existing `name` and `authors` fields.
result: [pending]

### 4. Stale remote branches deleted
expected: Running `git branch -r` shows only `origin/HEAD -> origin/master` and `origin/master`. No other remote branches exist.
result: [pending]

### 5. Dead code removed
expected: Searching the codebase for `_create_enhanced_filename` and `_sanitize_component` in `lib/` returns no results. These functions no longer exist.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0

## Gaps

[none yet]
