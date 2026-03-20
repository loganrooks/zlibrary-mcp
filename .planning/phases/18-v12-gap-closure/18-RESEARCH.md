# Phase 18: v1.2 Gap Closure - Research

**Researched:** 2026-03-20
**Domain:** Test fixes (Python/pytest), documentation cleanup, CI threshold tuning
**Confidence:** HIGH

## Summary

Phase 18 is a tech debt closure phase with six well-scoped items, all independently fixable. The research confirms that all four footnote test failures stem from a single root cause: tests access pre-v3 ground truth keys (`expected_output`, `marker_context`, `content` at top level) while the v3 schema moved these under nested objects (`marker` became `{"symbol": ..., "location_type": ...}`, `content` moved under `definition`). The ground truth JSON files themselves are valid v3 -- confirmed by 16/16 schema validation tests passing. The fix is entirely in test accessor code.

The three performance test failures are also confirmed -- they fail locally on the dev machine as well as CI, meaning the thresholds are too tight for any non-ideal environment. The documentation items (CHANGELOG links, ISSUES.md status, QUICKSTART.md removal, CONTRIBUTING.md update) are straightforward text edits with no code dependencies.

**Primary recommendation:** Fix test code accessors to match v3 ground truth schema, loosen performance thresholds with a 3x multiplier, and apply four documentation text edits. All items are independent and can be done in any order.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fix the **test code**, not the ground truth data -- tests are using pre-v3 keys (expected_output, marker_context, content) that were renamed in the v3 schema migration
- Update test assertions in test_real_footnotes.py and test_inline_footnotes.py to use correct v3 schema accessors
- Validate that the ground truth JSON files themselves are valid v3 (Phase 14 validation test should already confirm this)
- **Loosen thresholds** rather than excluding tests -- keeps validation meaningful on CI
- Use multipliers appropriate for CI runners (2-3x local thresholds) rather than removing timing assertions entirely
- CHANGELOG.md: Fix footer comparison links from v1.0.0/v1.1.0 to v1.0/v1.1 (matching actual GitHub tags)
- ISSUES.md: Mark ISSUE-DOCKER-001 as resolved (fixed by Phase 16-01)
- QUICKSTART.md: Delete entirely (superseded by README Quick Start section from Phase 16-03)
- CONTRIBUTING.md: Add Docker prerequisite note to E2E testing section

### Claude's Discretion
- Exact CI threshold multipliers for performance tests (2x, 3x, or environment-detected)
- Whether to add a CI environment variable check for conditional thresholds vs static loosening
- Order of operations across the fixes (independent items, can be batched freely)

### Deferred Ideas (OUT OF SCOPE)
- Vendored test file (zlibrary/src/test.py, 40KB) in npm tarball -- audit says "acceptable", non-blocking
- npm registry install path not documented in README -- could go in v1.3 docs refresh
- NPM_TOKEN secret not configured in GitHub repo settings -- manual ops task, not code
- CI audit job uses `|| true` (informational-only) -- acceptable for now, tighten in v1.3
- npm registry install path documentation -- future README update
</user_constraints>

## Standard Stack

Not applicable -- this phase modifies existing test files, CI configuration, and documentation only. No new libraries or dependencies are introduced.

### Tools Used
| Tool | Version | Purpose |
|------|---------|---------|
| pytest | existing | Test runner for Python tests |
| uv | existing | Python package management / test invocation |
| git | existing | File deletion (QUICKSTART.md), commits |

## Architecture Patterns

### Pattern 1: v3 Ground Truth Schema Accessor Pattern

**What:** The v3 ground truth schema restructured footnote data. Tests must navigate nested objects instead of flat top-level keys.

**v3 Schema Structure (from derrida_footnotes.json):**
```json
{
  "features": {
    "footnotes": [
      {
        "page_index": 1,
        "marker": {
          "symbol": "*",
          "location_type": "inline_body"
        },
        "definition": {
          "content": "The title of the next section..."
        },
        "note_type": "translator_note",
        "note_source": "translator"
      }
    ]
  }
}
```

**Key Mapping (old -> v3):**

| Old Key (pre-v3) | v3 Accessor | Notes |
|-------------------|-------------|-------|
| `footnote["marker"]` (string) | `footnote["marker"]["symbol"]` | Marker became an object with `symbol` and `location_type` |
| `footnote["expected_output"]` | REMOVED -- no v3 equivalent | Tests should construct expected output from `marker.symbol` |
| `footnote["marker_context"]` | REMOVED -- no v3 equivalent | Tests should just verify `[^{symbol}]` appears in output |
| `footnote["content"]` | `footnote["definition"]["content"]` | Content moved under `definition` object |

**Source:** Direct inspection of `test_files/ground_truth/derrida_footnotes.json` (confirmed v3, validated by test_schema_validation.py: 16/16 tests pass)

### Pattern 2: Performance Threshold Loosening

**What:** Performance tests use `time.perf_counter()` with fixed microsecond/millisecond thresholds. CI runners and even dev machines show 2-3x variance.

**Current thresholds vs observed times:**

| Test | Current Threshold | Local (dev) Time | Ratio |
|------|-------------------|------------------|-------|
| `test_detection_long_text_scales_linearly` | <5ms | ~14ms | 2.8x |
| `test_typical_region_fast` | <1ms | ~1.95ms | 2.0x |
| `test_superscript_check_performance` | <10ms (10k checks) | ~22.8ms | 2.3x |

**Recommendation:** Use a 3x multiplier (static) rather than environment-based conditional thresholds. Rationale:
1. These tests already fail on the dev machine (not just CI), so the thresholds are objectively too tight
2. Environment detection (`os.environ.get("CI")`) adds complexity for tests that validate algorithmic scaling, not absolute speed
3. A 3x multiplier covers both local dev variance and CI runner variance while still catching genuine O(n^2) regressions

### Anti-Patterns to Avoid
- **Do not modify ground truth JSON files** -- they are valid v3 and confirmed by schema validation tests
- **Do not remove performance tests** -- loosen thresholds instead to keep regression detection
- **Do not add `pytest.mark.skip` to performance tests** -- user explicitly chose loosening over exclusion

## Don't Hand-Roll

Not applicable for this phase -- all changes are modifications to existing files, not new features.

## Common Pitfalls

### Pitfall 1: Accessing `marker` as string when it is now an object
**What goes wrong:** `footnote["marker"]` returns `{"symbol": "*", "location_type": "inline_body"}` instead of `"*"`. Using it directly in string interpolation like `f"[^{marker}]:"` produces `[^{'symbol': '*', 'location_type': 'inline_body'}]:`.
**Why it happens:** The v3 migration changed `marker` from a plain string to a nested object.
**How to avoid:** Always use `footnote["marker"]["symbol"]` to get the marker string.
**Warning signs:** `TypeError` or malformed strings in assertions.

### Pitfall 2: `expected_output` key does not exist in v3
**What goes wrong:** `KeyError: 'expected_output'` -- this field was removed entirely in the v3 schema.
**Why it happens:** The old ground truth had a precomputed `expected_output` string. v3 does not.
**How to avoid:** Construct the expected markdown from the marker symbol: `f"[^{symbol}]:"`. For content validation, use `footnote["definition"]["content"]`.
**Warning signs:** `KeyError` on `expected_output`.

### Pitfall 3: Performance thresholds too tight even after loosening
**What goes wrong:** Tests still flaky after 2x multiplier on particularly slow CI runners.
**Why it happens:** GitHub Actions `ubuntu-latest` shared runners have unpredictable load.
**How to avoid:** Use 3x multiplier. Current dev machine shows 2-2.8x over the original thresholds. 3x gives headroom for CI runners which are typically slower than dev hardware.
**Warning signs:** Intermittent failures in CI despite passing locally.

### Pitfall 4: CHANGELOG link format
**What goes wrong:** Links 404 on GitHub because tags are `v1.0` and `v1.1`, not `v1.0.0` and `v1.1.0`.
**Why it happens:** Changelog was written assuming semver tags with patch version, but actual tags omit the patch.
**How to avoid:** Check `git tag -l` output to verify exact tag names before writing comparison URLs.
**Warning signs:** GitHub returns 404 for comparison URLs.

## Code Examples

### Fix 1: test_footnote_detection_with_real_pdf (test_real_footnotes.py, lines 76-93)

**Current (broken):**
```python
for footnote in footnotes:
    marker = footnote["marker"]
    expected_output = footnote["expected_output"]
    # ...
    content_snippet = footnote["content"][:50]
```

**Fixed (v3 accessors):**
```python
for footnote in footnotes:
    marker_symbol = footnote["marker"]["symbol"]
    definition_content = footnote["definition"]["content"]

    # Check that footnote appears in markdown format
    assert f"[^{marker_symbol}]:" in result or f"[^{marker_symbol}]" in result, (
        f"Footnote marker '{marker_symbol}' not found in output."
    )

    # Check that content is present
    content_snippet = definition_content[:50]
    assert content_snippet in result, (
        f"Footnote content not found for marker '{marker_symbol}'."
    )
```

### Fix 2: test_footnote_marker_in_body_text (test_real_footnotes.py, lines 125-133)

**Current (broken):**
```python
for footnote in footnotes:
    marker = footnote["marker"]
    _context = footnote["marker_context"]
```

**Fixed (v3 accessors):**
```python
for footnote in footnotes:
    marker_symbol = footnote["marker"]["symbol"]
    # marker_context was removed in v3 -- just verify marker reference exists
    assert f"[^{marker_symbol}]" in result, (
        f"Footnote marker reference [^{marker_symbol}] not found in body text"
    )
```

### Fix 3: test_footnote_content_extraction (test_real_footnotes.py, lines 147-163)

**Current (broken):**
```python
for footnote in footnotes:
    marker = footnote["marker"]
    content = footnote["content"]
```

**Fixed (v3 accessors):**
```python
for footnote in footnotes:
    marker_symbol = footnote["marker"]["symbol"]
    content = footnote["definition"]["content"]
```

### Fix 4: test_derrida_traditional_footnotes_regression (test_inline_footnotes.py, lines 1215-1221)

**Current (broken):**
```python
for footnote in ground_truth["features"]["footnotes"]:
    marker = footnote["marker"]
    expected_output = footnote["expected_output"]
```

**Fixed (v3 accessors):**
```python
for footnote in ground_truth["features"]["footnotes"]:
    marker_symbol = footnote["marker"]["symbol"]
    definition_content = footnote["definition"]["content"]

    assert f"[^{marker_symbol}]:" in result or definition_content[:50] in result, (
        f"Derrida footnote '{marker_symbol}' not found (REGRESSION)"
    )
```

### Fix 5: test_no_hallucinated_footnotes marker extraction (test_real_footnotes.py, line 100)

This line also accesses `footnote["marker"]` for the expected_markers list:

**Current:**
```python
expected_markers = [fn["marker"] for fn in footnotes]
```

**Fixed:**
```python
expected_markers = [fn["marker"]["symbol"] for fn in footnotes]
```

### Fix 6: Performance threshold loosening (test_garbled_performance.py)

**test_detection_long_text_scales_linearly (line 90-92):**
```python
# OLD: assert large_time < 0.005
assert large_time < 0.015, (
    f"Large text took {large_time * 1000:.2f}ms (should be <15ms)"
)
```

**test_typical_region_fast (line 164):**
```python
# OLD: assert avg_time < 0.001
assert avg_time < 0.003, (
    f"Typical region took {avg_time * 1000:.2f}ms (target: <3ms)"
)
```

### Fix 7: Performance threshold loosening (test_superscript_detection.py)

**test_superscript_check_performance (line 348-349):**
```python
# OLD: assert elapsed < 0.010
assert elapsed < 0.030, (
    f"10k superscript checks should be <30ms, got {elapsed * 1000:.2f}ms"
)
```

### Fix 8: CHANGELOG footer links (CHANGELOG.md, lines 101-104)

**Current (broken):**
```markdown
[2.0.0]: https://github.com/loganrooks/zlibrary-mcp/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/loganrooks/zlibrary-mcp/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/loganrooks/zlibrary-mcp/releases/tag/v1.0.0
```

**Fixed:**
```markdown
[2.0.0]: https://github.com/loganrooks/zlibrary-mcp/compare/v1.1...v2.0.0
[1.1.0]: https://github.com/loganrooks/zlibrary-mcp/compare/v1.0...v1.1
[1.0.0]: https://github.com/loganrooks/zlibrary-mcp/releases/tag/v1.0
```

Note: `v2.0.0` tag does not yet exist (Unreleased). The `[2.0.0]` link will only resolve after the tag is created. The `v1.0` and `v1.1` tags exist and are confirmed via `git tag -l`.

### Fix 9: ISSUES.md ISSUE-DOCKER-001 (move to Resolved section)

Move ISSUE-DOCKER-001 from "Open Issues" to "Resolved Issues" and add resolution note:
```markdown
### ISSUE-DOCKER-001: Docker numpy/Alpine Compilation [RESOLVED]
**Severity**: Was Low
**Resolution**: Phase 16-01 switched Docker base image to non-Alpine (debian-slim) with pre-built wheels, eliminating numpy compilation failures.
```

### Fix 10: CONTRIBUTING.md Docker prerequisite

Add Docker note to the E2E testing section (after the `npm run test:e2e` command block, around line 93-96):
```markdown
### End-to-End (Docker)

**Prerequisites**: Docker must be installed and running.

```bash
npm run test:e2e
```
```

### Fix 11: QUICKSTART.md deletion

```bash
git rm QUICKSTART.md
```

Confirmed: QUICKSTART.md is not referenced from README.md, CHANGELOG.md, package.json, or any other tracked file. Safe to delete.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat footnote keys (`marker`, `content`, `expected_output`) | Nested v3 schema (`marker.symbol`, `definition.content`) | Phase 14 (v3 migration) | 4 tests broken by key rename |
| Tight absolute performance thresholds | Needs 3x loosened thresholds | This phase | 3 tests fail locally and CI |

**Deprecated/outdated:**
- `expected_output` field: Removed in v3 schema. No replacement -- tests should construct expected strings from `marker.symbol`.
- `marker_context` field: Removed in v3 schema. No replacement -- tests should verify marker presence directly.

## Open Questions

1. **Should v2.0.0 tag be created?**
   - What we know: CHANGELOG references `[2.0.0]` section, but `git tag -l` shows only `v1.0` and `v1.1`. The Unreleased link already points to `compare/v2.0.0...HEAD`.
   - What's unclear: Whether the v2.0.0 release is planned as part of this phase or later.
   - Recommendation: Out of scope for Phase 18. The CHANGELOG link fix addresses v1.0/v1.1 tags only. Tag creation is a release process step.

## Sources

### Primary (HIGH confidence)
- `test_files/ground_truth/derrida_footnotes.json` -- Direct inspection of v3 schema structure
- `__tests__/python/test_schema_validation.py` -- 16/16 tests pass, confirming all ground truth files are valid v3
- `git tag -l` output -- Tags are `v1.0` and `v1.1` (not `v1.0.0`/`v1.1.0`)
- Local test execution -- All 4 footnote tests confirmed failing with exact KeyError messages
- Local test execution -- All 3 performance tests confirmed failing with exact timing data
- `pytest.ini` -- Marker configuration verified (performance marker exists)
- `.github/workflows/ci.yml` -- test-fast excludes `performance` marker; test-full runs all
- `QUICKSTART.md` -- Confirmed exists, confirmed not referenced from any other tracked file

### Verification
- `test_real_footnotes.py::test_footnote_detection_with_real_pdf` -> `KeyError: 'expected_output'` at line 79
- `test_real_footnotes.py::test_footnote_marker_in_body_text` -> `KeyError: 'marker_context'` at line 127
- `test_real_footnotes.py::test_footnote_content_extraction` -> `KeyError: 'content'` at line 149
- `test_inline_footnotes.py::test_derrida_traditional_footnotes_regression` -> `KeyError: 'expected_output'` at line 1217
- `test_garbled_performance.py::test_detection_long_text_scales_linearly` -> `14.09ms > 5ms threshold`
- `test_garbled_performance.py::test_typical_region_fast` -> `1.95ms > 1ms threshold`
- `test_superscript_detection.py::test_superscript_check_performance` -> `22.81ms > 10ms threshold`

## Metadata

**Confidence breakdown:**
- Footnote test fixes: HIGH -- exact error messages confirmed by running tests, v3 schema inspected directly, mapping is unambiguous
- Performance threshold fixes: HIGH -- exact timing data obtained locally, 3x multiplier verified against observed ratios
- Documentation fixes: HIGH -- tag names confirmed via git, QUICKSTART.md non-references confirmed via grep, ISSUES.md status verified against Phase 16 work

**Research date:** 2026-03-20
**Valid until:** No expiration -- this research covers specific code changes with verified data
