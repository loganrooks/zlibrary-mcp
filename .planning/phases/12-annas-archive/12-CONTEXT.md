# Phase 12: Anna's Archive Integration - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can search and download books from Anna's Archive (or alternative digital archive) as a fallback source when Z-Library is unavailable, with clear source attribution. Research spike determines feasibility and go/no-go. If Anna's Archive is not viable, pivot to other free digital archives.

</domain>

<decisions>
## Implementation Decisions

### Fallback trigger logic
- Fallback activates on: Z-Lib errors/timeouts, empty results, proactive rate-limit detection, and manual override
- Manual override via `source` parameter on search tools (e.g., `source: 'annas_archive' | 'zlibrary' | 'auto'`)
- Default source is `auto` (Z-Library primary), but primary source is configurable via env var
- Optional parallel mode: user can opt into querying both sources and getting merged results
- On mid-search fallback: clean switch — discard partial Z-Lib results, return only alternative source results

### Source attribution & result merging
- Clean switch on fallback — no partial result mixing
- In parallel mode, deduplication and result limits are Claude's discretion
- Schema normalization and source indicator approach are Claude's discretion based on what the API actually returns

### Go/no-go criteria
- Legal risk tolerance: match Z-Library approach (undocumented APIs acceptable if stable and widely used)
- **Hard constraint: free sources only — no paid APIs**
- Minimum feature parity for "go": must support both search AND download
- API stability assessment: Claude evaluates whether instability is mitigatable
- Research strategy (Anna's-first vs comparative): Claude's discretion
- Rate limit evaluation: Claude assesses whether alternative's limits make it a useful fallback

### No-go pivot strategy
- If Anna's Archive is not feasible, pivot to researching other free digital archives
- Claude discovers alternative candidates during research spike (no predetermined list)
- Goal is to find at least one viable free alternative source — phase doesn't close without exploration

### Configuration & user control
- Full control desired: URL, credentials (if needed), preferred source, fallback enable/disable, timeouts
- Configurable primary source via env var (default Z-Library)
- Auth pattern, kill switch, config granularity, status tooling, download directory organization: Claude's discretion based on what emerges from research

### Claude's Discretion
- Retry behavior before fallback (fail fast vs use existing retry/circuit-breaker)
- Whether fallback applies to downloads (depends on research spike findings)
- Which search tools get fallback (depends on alternative's capabilities)
- Auto-promote to alternative during Z-Lib outage behavior
- Logging/notification level when fallback activates
- Download source inference from book metadata vs explicit parameter
- Result schema (unified vs source-specific extras)
- Source indicator format (metadata field vs human-readable note)
- Per-tool config granularity vs global config
- Health-check/status tool value assessment
- Download directory organization (source-aware folders vs single folder)

</decisions>

<specifics>
## Specific Ideas

- User explicitly wants to avoid paid APIs — this is a hard constraint, not a preference
- The `source` parameter approach was specifically chosen over creating separate tools
- Configurable primary source was chosen over fixed Z-Library-first priority
- Parallel mode (query both sources) was explicitly requested as an option

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-annas-archive*
*Context gathered: 2026-02-02*
