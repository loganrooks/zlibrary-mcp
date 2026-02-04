---
phase: quick-002
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - __tests__/python/test_run_rag_tests.py
  - lib/rag/orchestrator_pdf.py
  - __tests__/python/test_quality_pipeline_integration.py
  - __tests__/python/test_rag_processing.py
  - test_files/ground_truth_loader.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "All 13 previously failing tests now pass"
    - "No new test failures introduced"
    - "OCR-dependent tests skipped gracefully when pytesseract unavailable"
  artifacts:
    - path: "__tests__/python/test_run_rag_tests.py"
      provides: "Stale zlib_client mock removed"
      contains: "# download path now uses EAPIClient"
    - path: "lib/rag/orchestrator_pdf.py"
      provides: "ZeroDivisionError guard"
      contains: "if len(doc) > 0"
    - path: "__tests__/python/test_quality_pipeline_integration.py"
      provides: "OCR skip markers"
      contains: "pytest.mark.skipif"
    - path: "test_files/ground_truth_loader.py"
      provides: "Utility file exclusion"
      contains: "schema_v2"
  key_links:
    - from: "test_run_rag_tests.py"
      to: "EAPIClient"
      via: "download_file method"
      pattern: "EAPIClient.*download"
---

<objective>
Fix 13 failing tests across 5 test files by addressing 4 distinct issues:
1. Remove stale `zlib_client` mock (replaced by EAPIClient in quick-001)
2. Guard against ZeroDivisionError when PDF has 0 pages
3. Add skip markers for OCR-dependent tests when pytesseract unavailable
4. Exclude utility/schema files from ground truth test enumeration

Purpose: Restore green test suite after quick-001 refactoring
Output: All pytest tests passing
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@__tests__/python/test_run_rag_tests.py (lines 680-710)
@lib/rag/orchestrator_pdf.py (lines 400-420)
@test_files/ground_truth_loader.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove stale zlib_client mock</name>
  <files>__tests__/python/test_run_rag_tests.py</files>
  <action>
    Remove line 692 that mocks `lib.python_bridge.zlib_client`. This mock is stale because
    quick-001 removed AsyncZlib and rewired downloads to use EAPIClient.download_file().

    The test function `test_run_single_test_with_download` should still work because:
    - Line 706 creates `mock_downloaded_path.touch()` which satisfies Path.exists()
    - The actual download code path is not exercised (mocked process_pdf returns "Processed PDF text")

    Add a comment explaining why the mock was removed:
    ```python
    # Note: zlib_client mock removed in quick-002 - download path now uses EAPIClient
    # The download itself is not tested here; we only verify the test runner flow
    ```
  </action>
  <verify>
    ```bash
    uv run pytest __tests__/python/test_run_rag_tests.py::test_run_single_test_with_download -v
    ```
    Test should pass.
  </verify>
  <done>test_run_single_test_with_download passes without stale mock</done>
</task>

<task type="auto">
  <name>Task 2: Fix ZeroDivisionError in orchestrator_pdf.py</name>
  <files>lib/rag/orchestrator_pdf.py</files>
  <action>
    At line 414, the code divides by `len(doc)` which can be 0 for empty/corrupt PDFs.

    Current code (around line 413-415):
    ```python
    logging.info(
        f"Pre-filter: {len(pages_needing_xmark_check)}/{len(doc)} pages flagged for X-mark detection "
        f"({len(pages_needing_xmark_check) / len(doc) * 100:.1f}%)"
    )
    ```

    Fix by guarding with a condition:
    ```python
    if len(doc) > 0:
        logging.info(
            f"Pre-filter: {len(pages_needing_xmark_check)}/{len(doc)} pages flagged for X-mark detection "
            f"({len(pages_needing_xmark_check) / len(doc) * 100:.1f}%)"
        )
    else:
        logging.warning("PDF has 0 pages, skipping X-mark pre-filter logging")
    ```
  </action>
  <verify>
    ```bash
    uv run pytest __tests__/python/test_rag_processing.py::test_process_pdf_triggers_ocr_on_image_only __tests__/python/test_rag_processing.py::test_process_pdf_triggers_ocr_on_poor_extraction -v 2>&1 | grep -E "(PASSED|FAILED|division by zero)"
    ```
    No "division by zero" error should appear.
  </verify>
  <done>Division by zero error eliminated</done>
</task>

<task type="auto">
  <name>Task 3: Add OCR skipif markers to quality pipeline tests</name>
  <files>__tests__/python/test_quality_pipeline_integration.py</files>
  <action>
    Add pytest skip markers to 3 tests that expect OCR recovery behavior but fail when
    pytesseract is not installed. The code correctly returns `recovery_unavailable` instead
    of `recovery_needed` when OCR is unavailable - this is correct behavior, not a bug.

    At top of file, add the skip condition:
    ```python
    import shutil

    TESSERACT_AVAILABLE = shutil.which('tesseract') is not None
    skip_without_tesseract = pytest.mark.skipif(
        not TESSERACT_AVAILABLE,
        reason="Tesseract OCR not installed - OCR recovery tests skipped"
    )
    ```

    Add `@skip_without_tesseract` decorator to these 3 tests:
    - `test_stage_3_low_confidence_skips_recovery` (around line 340)
    - `test_stage_3_high_confidence_needs_recovery` (around line 350)
    - `test_pipeline_proceeds_to_stage_3` (around line 430)
  </action>
  <verify>
    ```bash
    uv run pytest __tests__/python/test_quality_pipeline_integration.py -v 2>&1 | grep -E "(PASSED|FAILED|SKIPPED|skip)"
    ```
    3 tests should show SKIPPED (or PASSED if tesseract is installed).
  </verify>
  <done>OCR-dependent tests skip gracefully when tesseract unavailable</done>
</task>

<task type="auto">
  <name>Task 4: Exclude utility files from ground truth enumeration</name>
  <files>test_files/ground_truth_loader.py</files>
  <action>
    Update `list_ground_truth_tests()` to exclude utility/schema files that aren't valid test cases.

    Current code (line 194-195):
    ```python
    gt_files = gt_dir.glob('*.json')
    return [f.stem for f in gt_files if f.name != 'schema.json']
    ```

    Updated code:
    ```python
    # Utility files that are not actual ground truth test cases
    EXCLUDED_FILES = {
        'schema.json',           # JSON schema definition
        'schema_v2.json',        # JSON schema v2
        'schema_v3.json',        # JSON schema v3
        'body_text_baseline.json',   # Recall baseline data
        'correction_matrix.json',    # Validation results
    }

    gt_files = gt_dir.glob('*.json')
    return [f.stem for f in gt_files if f.name not in EXCLUDED_FILES]
    ```
  </action>
  <verify>
    ```bash
    uv run pytest __tests__/python/test_real_world_validation.py::TestRealWorldPerformance -v 2>&1 | grep -E "(PASSED|FAILED|schema|baseline|correction)"
    ```
    No tests for schema_v2, schema_v3, body_text_baseline, or correction_matrix should appear.
  </verify>
  <done>Ground truth enumeration excludes utility files</done>
</task>

</tasks>

<verification>
Run full test suite to verify no regressions:
```bash
uv run pytest __tests__/python/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass (with OCR tests skipped if tesseract unavailable)
</verification>

<success_criteria>
- [ ] `test_run_single_test_with_download` passes (stale mock removed)
- [ ] No ZeroDivisionError in orchestrator_pdf.py
- [ ] 3 OCR tests skip gracefully when tesseract unavailable
- [ ] Ground truth enumeration excludes 5 utility files
- [ ] Full pytest suite passes with no failures
</success_criteria>

<output>
After completion, create `.planning/quick/002-test-fixes/002-SUMMARY.md`
</output>
