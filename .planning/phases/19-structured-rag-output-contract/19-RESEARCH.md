# Phase 19: Structured RAG Output Contract - Research

**Researched:** 2026-04-16
**Domain:** Python structured-output pipeline, Python bridge payloads, Node/MCP contract compatibility
**Confidence:** HIGH

## Summary

Phase 19 is a contract-normalization phase, not a greenfield feature build. The Python pipeline already has most of the machinery needed for structured output:

- `lib/rag/pipeline/models.py` writes separate body, footnotes, endnotes, citations, and metadata files from `DocumentOutput.write_files()`
- `lib/rag/orchestrator.py` already merges additive fields like `metadata_file_path`, `footnotes_file_path`, and `content_types_produced` into the structured PDF result
- `__tests__/python/test_pipeline_integration.py` already verifies multi-file output exists at the Python layer

The gaps are consistency and public contract shape:

- Metadata naming is split between `_meta.json` in `DocumentOutput.write_files()` and `.metadata.json` in `lib/filename_utils.py`
- Metadata currently stores document and processing metadata, but not a normalized relative-path index of the produced output bundle
- `lib/python_bridge.py` still returns legacy `content` lines for `process_document`, while the orchestrator path is already path-first
- Several Node tests, recorded fixtures, and public docs still assume a `processed_file_path`-only result even though the backend can already expose more

**Primary recommendation:** execute Phase 19 as two sequential plans.

1. Normalize the Python output bundle and bridge payload so body, metadata, and optional footnote paths are deterministic and additive.
2. Surface that additive contract through the Node/MCP layer, recorded fixtures, and the public docs that describe these tools.

## Current State

### What Already Exists

| Surface | Evidence | Implication |
|---------|----------|-------------|
| Structured writer | `lib/rag/pipeline/models.py` | Multi-file output already exists for body, footnotes, endnotes, citations, metadata |
| Structured orchestrator result | `lib/rag/orchestrator.py` | Backend already knows how to return additive path fields |
| Integration coverage | `__tests__/python/test_pipeline_integration.py` | Python layer already has baseline tests for multi-file behavior |
| Public MCP tool | `src/index.ts` | `process_document_for_rag` is already a stable public tool, so compatibility matters |

### Contract Mismatches

| Mismatch | Evidence | Risk |
|----------|----------|------|
| Two metadata naming conventions | `_meta.json` vs `.metadata.json` | No single authoritative metadata sidecar |
| Relative links missing from metadata | metadata payload contains only nested metadata objects today | Downstream consumers must infer sibling files by filename convention |
| Legacy `content` array still returned by bridge | `lib/python_bridge.py`, recorded fixture `process_document.json` | Public contract remains ambiguous about path-first vs content-inline behavior |
| Node tests mostly assert only `processed_file_path` | `__tests__/index-handlers-extended.test.js`, `__tests__/zlibrary-api.test.js` | Additive fields can regress silently unless surfaced and tested |

## Recommended Build Order

### Plan 01: Python Bundle Normalization

Do the contract work where the files are produced:

- unify metadata file naming around one canonical sidecar
- add produced-output links into metadata using relative paths
- ensure `processed_file_path` still points at the body file
- return additive path fields from the bridge without removing current fields

### Plan 02: Node/MCP Surface Alignment

Once the Python contract is stable:

- update TypeScript return types and handler expectations
- refresh recorded fixtures and integration/unit tests
- update README/API docs so they describe the additive structured-output result instead of the older path-only/inline-content story

## Architecture Patterns

### Pattern 1: Preserve the Body Path as the Compatibility Anchor

`processed_file_path` is the field existing callers already rely on. The safest rollout is to keep it as the canonical body-text path and add sibling file paths around it.

### Pattern 2: Metadata Should Describe the Bundle, Not Just the Document

The metadata sidecar should become the single authority for:

- document metadata
- processing metadata
- relative links to the body, footnotes, endnotes, citations, and source file when available

This lets future phases consume the bundle without hard-coding filename conventions.

### Pattern 3: Keep `page_analysis_map` Out of the Public Contract for Now

Phase 21 explicitly reopens whether `page_analysis_map` belongs in scoring/reporting. Phase 19 should preserve room for that later decision, not bake it into the public metadata contract prematurely.

## Common Pitfalls

### Pitfall 1: Fixing only one of the metadata naming paths

If `DocumentOutput.write_files()` and `create_metadata_filename()` keep diverging, tests will pass in one path and fail in another. The phase must choose one canonical naming path and align both layers.

### Pitfall 2: Breaking `processed_file_path` while adding richer paths

The milestone requirement is additive compatibility. Consumers should gain `metadata_file_path` / `footnotes_file_path` style fields without losing the existing body-file anchor.

### Pitfall 3: Updating backend payloads without fixtures and docs

Recorded responses and docs currently encode the older contract. If they are not updated in the same phase, regressions will show up later as stale expectations instead of immediately as part of Phase 19.

## Genuine Gaps

No blocker-level research gaps remain for planning. The main implementation decision is which metadata filename convention becomes canonical; that is an execution choice, not a planning blocker.

## Recommendation

Proceed with two plans in two waves:

- `19-01` for Python-side output and bridge normalization
- `19-02` for Node/MCP surfacing, fixture refresh, and public contract docs
