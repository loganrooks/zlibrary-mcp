# Phase 5: Feature Porting & Branch Cleanup - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Port valuable unmerged features from the `get_metadata` branch onto master (get_metadata tool, enhanced filenames, search result enrichment), then delete all stale remote branches. Re-implement rather than rebase due to 75-commit drift since the branch diverged.

</domain>

<decisions>
## Implementation Decisions

### Metadata tool response
- **Tiered response**: practical default (core scalar fields) + full mode (nested objects for terms, booklists, IPFS CIDs, ratings)
- **Selective inclusion**: `include` parameter allowing users to request specific field groups on top of the practical default
- **Nested structure for full mode**: terms as `[{name, count}]`, booklists as `[{id, hash, title, bookCount}]` — preserves relationships needed for downstream tool calls (e.g., `fetch_booklist`)
- **Error handling**: based on best practices, not inherited from existing codebase patterns

### Claude's Discretion (Metadata)
- Selective field inclusion interface design (e.g., `include` array vs detail enum)
- Error response structure (best practices over existing patterns)
- Input interface: bookId+hash vs full bookDetails object

### Filename conventions
- **CamelCase format**: user prefers `OrwellGeorge_1984.epub` style with underscore separators between components
- **Disambiguation fields**: include year, language, publisher as available to differentiate editions/translations
- **Fallback behavior**: Claude to design sensible fallback when author/title data is missing
- **Applies to new downloads only** (existing files untouched)

### Claude's Discretion (Filenames)
- Exact field ordering and inclusion logic for disambiguation
- Truncation rules for long titles/author names
- Fallback strategy for missing metadata
- Filesystem-safe character handling

### Search result enrichment
- **All search tools enriched equally**: search_books, full_text_search, search_advanced, search_by_author, search_by_term — every tool returning book results gets author/title fields
- **Missing field handling**: Claude decides null vs omit based on best practices
- **Backward compatibility**: Claude decides additive vs restructure based on best practices
- **Additional fields beyond author/title**: Claude extracts whatever is reliably available

### Branch cleanup
- **Quick review of self-modifying-system** before deletion — check for salvageable ideas
- **Delete scope**: all 6 non-master remote branches (5 merged + self-modifying-system + get_metadata after porting)
- **Local cleanup**: Claude's discretion
- **Branch governance**: Claude's discretion (likely deferred to Phase 6)

### Claude's Discretion (General)
- Technical implementation approach for all ported features
- Architecture decisions for integrating new tools
- Test strategy for ported features
- Whether to restructure search responses or keep additive

</decisions>

<specifics>
## Specific Ideas

- User prefers CamelCase filenames: `OrwellGeorge_1984.epub` style (not hyphenated or space-separated)
- Disambiguation matters: different translations, editions, publishers should be distinguishable by filename
- Error handling throughout should follow best practices, not necessarily match existing codebase patterns
- Metadata tool should support both quick lookups (practical default) and deep dives (full with nested data)

</specifics>

<deferred>
## Deferred Ideas

- **Batch rename tool**: tool to rename previously downloaded files to the new naming convention — new capability, not part of porting
- **Branch protection rules**: governance/enforcement belongs in Phase 6 (Documentation & Quality Gates)

</deferred>

---

*Phase: 05-feature-porting-branch-cleanup*
*Context gathered: 2026-02-01*
