# Phase 14: Test Infrastructure - Research

**Researched:** 2026-02-11
**Domain:** pytest marker taxonomy, ground truth schema consolidation, CI test splitting
**Confidence:** HIGH

## Summary

Phase 14 restructures the Python test infrastructure around three axes: (1) a complete marker taxonomy so every test file declares its category, (2) consolidation of ground truth schemas from three versions (v1, v2, v3) down to v3 only, and (3) CI configuration that distinguishes fast PR tests from the full suite.

The current codebase has 865 pytest-collected tests across 37 test files (36 in `__tests__/python/` plus 1 in `__tests__/python/integration/`). Only 4 files use any taxonomy marker today. The `pytest.ini` registers 5 of the 7 required markers (missing `unit` and `ground_truth`). Three schema files coexist (`schema.json`, `schema_v2.json`, `schema_v3.json`), and the ground truth data files are a mix of v1 and partially-v3 structures. There are 10 Python files at the repo root (debug scripts and 2 test files) plus test-like scripts under `scripts/`. The current "fast" test subset (`-m "not slow and not integration"`) takes ~50-54 seconds -- well over the 30-second target -- because `test_real_world_validation.py` and `test_real_footnotes.py` process real PDFs but lack `slow` or `real_world` markers.

**Primary recommendation:** Add the two missing markers to `pytest.ini`, apply `pytestmark` module-level markers to all 37 test files using a systematic classification, mark PDF-processing tests as `slow` to bring the fast subset under 30 seconds, migrate all ground truth JSON files to v3 schema, and split CI into fast (every PR) and full (manual/nightly) jobs.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.4.0 | Test framework | Already in use, provides marker infrastructure |
| jsonschema | >=4.23.0 | JSON Schema validation | Standard Python library for Draft-07 validation; needed for TEST-04 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-benchmark | >=5.1.0 | Performance benchmarks | Already installed; performance tests use it |
| pytest-asyncio | >=1.2.0 | Async test support | Already installed; many tests are async |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsonschema | Manual validation in Python | jsonschema handles $ref, allOf, nested schemas properly; manual validation would be fragile for the complex v3 schema |
| jsonschema | pydantic model validation | Overkill for one-off schema check; jsonschema matches the JSON Schema Draft-07 files directly |

**Installation:**
```bash
uv add --dev jsonschema
```

## Architecture Patterns

### Recommended Marker Classification

Each test file gets exactly one primary marker via `pytestmark` at module level. The classification logic:

```
unit         - Tests with NO external dependencies (no real files, no network, no Z-Library)
               Uses mocks/patches exclusively. Fast by definition.

integration  - Tests requiring real Z-Library credentials or network access.
               Already used on test_real_zlibrary.py and test_pipeline_integration.py.

slow         - Tests that process real PDF files (>1 second each).
               Key trigger: any test opening a real PDF via PyMuPDF.

ground_truth - Tests that load and validate against ground truth JSON files.
               Subset of slow (always add both: [ground_truth, slow]).

real_world   - Tests that validate real-world document processing end-to-end.
               Already used on test_real_world_validation.py.

performance  - Tests using pytest-benchmark or measuring timing budgets.
               Already registered; apply to benchmark test files.

e2e          - End-to-end tests spanning the full MCP pipeline.
               Already registered; for Docker-based or full-stack tests.
```

### Pattern: Module-Level pytestmark Assignment

**What:** Every test file declares its marker(s) at module level using `pytestmark`.
**When to use:** Always. This is the canonical way to mark all tests in a file.
**Example:**
```python
# Source: https://docs.pytest.org/en/stable/example/markers.html
import pytest

# Single marker
pytestmark = pytest.mark.unit

# Multiple markers
pytestmark = [pytest.mark.slow, pytest.mark.ground_truth]
```

### Pattern: strict_markers Enforcement

**What:** Enable `strict_markers = true` in `pytest.ini` so unregistered markers cause errors.
**When to use:** After all markers are applied. Prevents drift.
**Example:**
```ini
[pytest]
strict_markers = true
markers =
    unit: pure unit tests with no external dependencies
    integration: tests requiring real Z-Library credentials
    slow: tests that process real PDF files (>1s)
    ground_truth: tests validating against ground truth JSON
    real_world: end-to-end real document validation
    performance: benchmark and timing tests
    e2e: full pipeline end-to-end tests
```

### Pattern: CI Fast/Full Test Split

**What:** Two CI jobs -- fast runs on every PR, full available as manual trigger or nightly.
**When to use:** For the GitHub Actions workflow.
**Example:**
```yaml
jobs:
  test-fast:
    runs-on: ubuntu-latest
    steps:
      # ... setup steps ...
      - run: node --experimental-vm-modules node_modules/jest/bin/jest.js
      - run: uv run pytest -m "not slow and not integration"

  test-full:
    if: github.event_name == 'push' || github.event.inputs.full_suite == 'true'
    runs-on: ubuntu-latest
    steps:
      # ... setup steps ...
      - run: node --experimental-vm-modules node_modules/jest/bin/jest.js
      - run: uv run pytest
```

### Anti-Patterns to Avoid

- **Marker on individual test methods instead of module:** Use `pytestmark` for file-level classification. Only use per-method markers for exceptions (e.g., one slow test in an otherwise fast file).
- **Multiple conflicting primary markers:** A file should have ONE primary category. Composite markers are fine (e.g., `[slow, ground_truth]`), but don't mark a file as both `unit` and `integration`.
- **Forgetting `strict_markers`:** Without it, typos in marker names silently pass. Enable it at the end of the phase.

## Current State Audit

### Marker Coverage (4/37 files have taxonomy markers)

| File | Current Markers | Recommended |
|------|----------------|-------------|
| test_pipeline_integration.py | `@pytest.mark.integration` | integration |
| test_real_world_validation.py | `pytestmark = pytest.mark.real_world` | [real_world, slow, ground_truth] |
| test_recall_baseline.py | `@pytest.mark.slow` | [slow, ground_truth] |
| integration/test_real_zlibrary.py | `@pytest.mark.integration` | integration |
| test_real_footnotes.py | (none) | [slow, ground_truth] |
| test_inline_footnotes.py | (none) | slow (processes real PDFs) |
| test_garbled_performance.py | (none) | performance |
| test_performance_footnote_features.py | (none) | performance |
| test_toc_hybrid.py | (none) | slow (uses PyMuPDF on real PDFs) |
| All other 28 files | (none) | unit |

### Fast Subset Timing Problem

Current `pytest -m "not slow and not integration"` runs in ~50-54 seconds. The top time consumers:

| Test | Time | Why Slow | Fix |
|------|------|----------|-----|
| test_real_world_validation.py (entire file) | ~16s total | Processes real PDFs with PyMuPDF | Mark as `slow` |
| test_real_footnotes.py (entire file) | ~18s total | Opens real PDF, full pipeline | Mark as `slow` |
| test_inline_footnotes.py (3 tests) | ~4s | Real PDF processing in 3 methods | Mark as `slow` |
| test_toc_hybrid.py (3 classes) | ~2s | PyMuPDF on real PDFs | Mark as `slow` |
| test_phase_2_integration.py | ~3s | Opens real PDF in fixture setup | Mark as `slow` |

**Projected fast time after marking:** ~50s - 43s of slow tests = ~7s. Well under 30s target.

### Ground Truth Schema Status

| File | Conforms To | Needs Migration |
|------|------------|----------------|
| schema.json (v1) | v1 definition | DELETE |
| schema_v2.json | v2 definition | DELETE |
| schema_v3.json | v3 definition | KEEP (canonical) |
| derrida_footnotes.json | v1 (top-level `pages`, no `metadata`) | YES - migrate to v3 |
| derrida_of_grammatology.json | v1 (top-level `pages`, no `metadata`) | YES - migrate to v3 |
| heidegger_being_time.json | v1 (top-level `pages`, no `metadata`) | YES - migrate to v3 |
| heidegger_22_23_footnotes.json | v1-like (has `schema_version: "3.0"` field but v1 structure) | YES - migrate to v3 |
| derrida_footnotes_v2.json | v3-ish (has `metadata`, `note_source`) | MINOR fixes |
| kant_footnotes.json | v3-ish (has `metadata`, `note_source`) | MINOR fixes |
| kant_64_65_footnotes.json | v3-ish (has `metadata`, `note_source`) | MINOR fixes |
| body_text_baseline.json | Not a ground truth test | EXCLUDED (utility file) |
| correction_matrix.json | Not a ground truth test | EXCLUDED (utility file) |

### Files at Repo Root (to relocate)

| File | Current Location | Destination | Rationale |
|------|-----------------|-------------|-----------|
| test_footnote_validation.py | repo root | scripts/archive/ | Debug/validation script, not a pytest test |
| test_kant_page2_debug.py | repo root | scripts/archive/ | Debug script, not a pytest test |
| debug_asterisk_full_search.py | repo root | scripts/debugging/ | Debug script |
| debug_find_asterisk_anywhere.py | repo root | scripts/debugging/ | Debug script |
| debug_kant_page2_asterisk.py | repo root | scripts/debugging/ | Debug script |
| debug_kant_page3_content.py | repo root | scripts/debugging/ | Debug script |
| debug_page2_block10_11.py | repo root | scripts/debugging/ | Debug script |
| debug_page3_block8_full.py | repo root | scripts/debugging/ | Debug script |
| debug_page3_continuation.py | repo root | scripts/debugging/ | Debug script |
| multi_corpus_validation.py | repo root | scripts/validation/ | Validation script |

### CI Current State

The `.github/workflows/ci.yml` runs ALL tests (both Jest and pytest) in a single job with no marker filtering. The `audit` job runs separately. There is no fast/full distinction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation | Custom dict-checking code | `jsonschema.validate()` | v3 schema has `$ref`, `allOf`, `definitions` -- manual validation would miss edge cases |
| Marker enforcement | grep-based CI check | `strict_markers = true` in pytest.ini | pytest's built-in enforcement is authoritative and catches issues at collection time |
| Test timing analysis | Custom timing framework | `pytest --durations=N` + marker-based selection | Built-in pytest feature, no custom code needed |

**Key insight:** The marker taxonomy is a configuration problem, not a code problem. The work is classification (deciding which marker each file gets) and mechanical application (adding `pytestmark` lines).

## Common Pitfalls

### Pitfall 1: Marking Tests as `unit` When They Read Real Files
**What goes wrong:** A test marked `unit` opens a real PDF from `test_files/`, making the "fast" suite slow.
**Why it happens:** Confusion between "uses mocks" and "doesn't need network." File I/O with real PDFs is slow.
**How to avoid:** Any test that opens a file from `test_files/` with PyMuPDF/fitz gets `slow`. Unit tests use ONLY synthetic data or mocks.
**Warning signs:** Fast suite takes >30 seconds after marking.

### Pitfall 2: Breaking Ground Truth Loader During Schema Migration
**What goes wrong:** `ground_truth_loader.py` validates schema loosely; after migration, tests that previously worked may fail if validation becomes strict.
**Why it happens:** The loader's `_validate_ground_truth_schema()` currently only requires `pdf_file`. Making it v3-strict would break tests.
**How to avoid:** Migrate data files first, then update the loader, then add the validation test. Run tests after each step.
**Warning signs:** `test_real_world_validation.py` failures after schema changes.

### Pitfall 3: Forgetting `strict_markers` Causes Silent Drift
**What goes wrong:** New test files are added without markers, and nobody notices.
**Why it happens:** Without `strict_markers`, unregistered markers are silently ignored.
**How to avoid:** Enable `strict_markers = true` as the LAST step of the phase, after all markers are applied.
**Warning signs:** `pytest --strict-markers` fails on any test file.

### Pitfall 4: CI Fast Job Still Runs Slow Tests
**What goes wrong:** The CI fast job uses `-m "not slow and not integration"` but some slow tests lack the `slow` marker.
**Why it happens:** Marker application was incomplete.
**How to avoid:** Verify fast subset timing locally before updating CI: `time uv run pytest -m "not slow and not integration" -p no:benchmark --tb=no -q`
**Warning signs:** CI fast job takes >30 seconds.

### Pitfall 5: Ground Truth Files Referencing Non-Existent PDFs After Migration
**What goes wrong:** Migrated ground truth JSON has `pdf_file` paths that don't resolve.
**Why it happens:** Schema migration changes structure but not file references; OR the PDFs were never committed.
**How to avoid:** The validation test should check both schema conformance AND that referenced PDF files exist.
**Warning signs:** `test_real_world_validation.py::TestRealWorldPerformance::test_processing_time_within_budget` failures.

## Code Examples

### Adding jsonschema Dependency

```bash
uv add --dev jsonschema
```

### Schema Validation Test (TEST-04)

```python
# Source: jsonschema library docs
import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError

GROUND_TRUTH_DIR = Path("test_files/ground_truth")
SCHEMA_PATH = GROUND_TRUTH_DIR / "schema_v3.json"

# Files that are NOT ground truth test cases (utility files)
EXCLUDED_FILES = {
    "schema_v3.json",
    "body_text_baseline.json",
    "correction_matrix.json",
}


def get_ground_truth_files():
    """List all ground truth JSON files that should conform to v3 schema."""
    return [
        f for f in GROUND_TRUTH_DIR.glob("*.json")
        if f.name not in EXCLUDED_FILES
    ]


@pytest.fixture(scope="module")
def v3_schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.mark.parametrize(
    "gt_file",
    get_ground_truth_files(),
    ids=lambda f: f.stem,
)
def test_ground_truth_conforms_to_v3_schema(v3_schema, gt_file):
    """Every ground truth JSON file must validate against schema_v3.json."""
    with open(gt_file) as f:
        data = json.load(f)
    validate(instance=data, schema=v3_schema)
```

### Module-Level Marker Application

```python
# For a unit test file (e.g., test_filename_utils.py)
import pytest

pytestmark = pytest.mark.unit

# ... rest of test file unchanged ...
```

```python
# For a slow + ground_truth file (e.g., test_real_footnotes.py)
import pytest

pytestmark = [pytest.mark.slow, pytest.mark.ground_truth]

# ... rest of test file unchanged ...
```

### Updated pytest.ini

```ini
[pytest]
pythonpath = . lib
asyncio_mode = auto
testpaths = __tests__/python
strict_markers = true
markers =
    unit: pure unit tests with mocked dependencies, no file I/O on real test data
    integration: tests requiring real Z-Library credentials or network access (deselect with '-m "not integration"')
    slow: tests processing real PDF/EPUB files via PyMuPDF (deselect with '-m "not slow"')
    ground_truth: tests validating output against ground truth JSON files (deselect with '-m "not ground_truth"')
    real_world: end-to-end validation with real-world documents (deselect with '-m "not real_world"')
    performance: benchmark and timing budget tests (deselect with '-m "not performance"')
    e2e: full MCP pipeline end-to-end tests (deselect with '-m "not e2e"')
```

### CI Configuration (Fast + Full)

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]
  workflow_dispatch:
    inputs:
      full_suite:
        description: 'Run full test suite including slow tests'
        type: boolean
        default: false

jobs:
  test-fast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm run build
      - run: node --experimental-vm-modules node_modules/jest/bin/jest.js
      - run: uv run pytest -m "not slow and not integration"

  test-full:
    if: >
      github.event_name == 'push' ||
      (github.event_name == 'workflow_dispatch' && github.event.inputs.full_suite == 'true')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm run build
      - run: node --experimental-vm-modules node_modules/jest/bin/jest.js
      - run: uv run pytest

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - uses: astral-sh/setup-uv@v4
      - run: npm ci
      - run: uv sync
      - run: npm audit --omit=dev --audit-level=high
      - run: uv run pip-audit || true
```

## Ground Truth v1-to-v3 Migration Pattern

### v1 Structure (to migrate FROM)
```json
{
  "test_name": "...",
  "pdf_file": "...",
  "pages": 2,
  "created_date": "2025-10-20",
  "verified_by": "human",
  "features": { ... },
  "expected_quality": { ... }
}
```

### v3 Structure (to migrate TO)
```json
{
  "test_name": "...",
  "pdf_file": "...",
  "metadata": {
    "pages": 2,
    "created_date": "2025-10-20",
    "verified_by": "human"
  },
  "features": { ... },
  "expected_quality": { ... }
}
```

**Key differences v1 -> v3:**
1. `pages`, `created_date`, `verified_by`, `description` move INTO `metadata` object
2. `metadata` becomes required
3. Footnotes gain `note_source`, `classification_confidence`, `classification_method` (required in v3 schema)
4. `note_type` is deprecated but kept for backward compat

**Migration strategy for footnotes:** Files without footnotes (derrida_of_grammatology, heidegger_being_time) only need the metadata restructure. Files with footnotes need the v3 footnote fields added. For files where classification data is unknown, use `"note_source": "author"`, `"classification_confidence": 0.5`, `"classification_method": "manual_verification"` as sensible defaults.

**Important:** The `ground_truth_loader.py` `_validate_ground_truth_schema()` function currently only requires `pdf_file`. After migration, update it to check for `metadata` as well. The `load_ground_truth()` function references `schema.json` in its error message -- update that to `schema_v3.json`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No marker taxonomy | Partial markers (5 registered, 4 files use them) | Phase 13 (2026-02-11) | Phase 13 established foundation; Phase 14 completes it |
| Three schema versions coexisting | Should be single v3 schema | Needs Phase 14 | Reduces confusion, enables validation |
| Single CI job runs all tests | Should split fast/full | Needs Phase 14 | Faster PR feedback loop |

## Open Questions

1. **Should `test_real_world_validation.py` use `ground_truth` marker in addition to `real_world`?**
   - What we know: It loads ground truth files via `load_ground_truth()` and processes real PDFs.
   - What's unclear: Whether `real_world` is sufficient or if `ground_truth` adds value for filtering.
   - Recommendation: Apply both `[real_world, slow, ground_truth]` for maximum filtering flexibility.

2. **Should v3 schema `required` fields for footnotes be relaxed?**
   - What we know: v3 schema requires `note_source`, `classification_confidence`, `classification_method` on every footnote. Some ground truth files have footnotes without these fields.
   - What's unclear: Whether to add these fields to existing footnotes or relax the schema.
   - Recommendation: Add the fields to data files with sensible defaults. Keep the schema strict -- it's the definition of "v3 complete."

3. **Should benchmark tests be disabled in the fast CI run?**
   - What we know: pytest-benchmark adds ~5 seconds of overhead even when benchmark tests pass quickly. The `-p no:benchmark` flag disables the plugin entirely.
   - What's unclear: Whether disabling benchmarks in fast mode is acceptable.
   - Recommendation: Use `--benchmark-disable` flag in the fast CI job rather than `-p no:benchmark` to still collect benchmark-decorated tests but skip actual benchmarking.

4. **What about the `test_data/` directory at repo root?**
   - What we know: `test_data/` contains `3402079.epub` and `3505318.pdf` -- older test fixtures separate from `test_files/`.
   - What's unclear: Whether any tests reference `test_data/` or if it's orphaned.
   - Recommendation: Check references; if orphaned, move contents to `test_files/` or delete.

## Detailed Test File Classification

### Files to Mark as `unit` (27 files)

These files use mocks/patches exclusively and don't open real test data files:

- test_adaptive_integration.py
- test_annas_adapter.py
- test_author_tools.py
- test_booklist_tools.py
- test_compositor.py
- test_eapi_download.py
- test_enhanced_metadata.py
- test_filename_utils.py
- test_footnote_continuation.py
- test_formatting_group_merger.py
- test_garbled_text_detection.py
- test_libgen_adapter.py
- test_margin_detection.py
- test_margin_integration.py
- test_metadata_generator.py
- test_note_classification.py
- test_ocr_quality.py
- test_publisher_extraction.py
- test_python_bridge.py
- test_quality_pipeline_integration.py
- test_rag_data_models.py
- test_rag_enhancements.py
- test_rag_processing.py
- test_resolution_analyzer.py
- test_resolution_renderer.py
- test_run_rag_tests.py
- test_source_router.py
- test_superscript_detection.py
- test_term_tools.py

### Files to Mark as `slow` (processes real PDFs)

- test_real_footnotes.py -- `[slow, ground_truth]`
- test_inline_footnotes.py -- `slow` (some methods process real PDFs)
- test_toc_hybrid.py -- `slow` (PyMuPDF on real PDFs, also has skipif)
- test_phase_2_integration.py -- `slow` (opens real PDF with fitz.open in fixture, ~3s)

### Files to Mark as `[real_world, slow, ground_truth]`

- test_real_world_validation.py -- already has `real_world`, add `slow` and `ground_truth`

### Files to Mark as `[slow, ground_truth]`

- test_recall_baseline.py -- already has `slow`, add `ground_truth`

### Files to Mark as `performance`

- test_garbled_performance.py -- `performance` (uses timing assertions)
- test_performance_footnote_features.py -- `performance`

### Files Already Correctly Marked

- test_pipeline_integration.py -- `integration` (correct)
- integration/test_real_zlibrary.py -- `integration` (correct)

## Sources

### Primary (HIGH confidence)
- `/websites/pytest_en_stable` - Context7: marker registration, strict_markers, pytestmark module-level, INI configuration
- Codebase audit: direct inspection of all 37 test files, pytest.ini, CI config, ground truth files

### Secondary (MEDIUM confidence)
- jsonschema library (`/python-jsonschema/jsonschema`) - Context7: validates JSON Schema Draft-07, the format used by all three schema files
- GitHub Actions `workflow_dispatch` with inputs - standard GHA feature for manual triggers

### Tertiary (LOW confidence)
- None. All findings are from direct codebase inspection or verified documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest markers are well-documented; jsonschema is the standard Python JSON Schema library
- Architecture: HIGH - marker classification based on direct inspection of every test file
- Pitfalls: HIGH - identified from actual timing data (50s fast suite) and schema analysis
- Ground truth migration: HIGH - inspected every JSON file's actual structure vs v3 schema requirements
- CI split: MEDIUM - standard GitHub Actions pattern, but this project has no prior CI split experience

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable -- pytest markers and JSON Schema don't change rapidly)
