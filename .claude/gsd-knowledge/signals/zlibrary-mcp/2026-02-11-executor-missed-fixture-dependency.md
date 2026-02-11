---
id: sig-2026-02-11-executor-missed-fixture-dependency
type: signal
project: zlibrary-mcp
tags: [executor, regression, dependency-analysis, integration-tests, fixture, verification-gap]
created: 2026-02-11T00:00:00Z
updated: 2026-02-11T00:00:00Z
durability: convention
status: active
severity: critical
signal_type: deviation
phase: 13
plan: 02
polarity: negative
source: manual
occurrence_count: 1
related_signals: []
---

## What Happened

Executor 13-02 removed AsyncZlib from `TestRealAuthentication` class in `test_real_zlibrary.py` but failed to update or recreate the `zlib_client` fixture that 16 other integration test classes depend on. This broke all integration tests that use the fixture (18 errors across `TestRealBasicSearch`, `TestRealTermSearch`, `TestRealAuthorSearch`, `TestRealMetadataExtraction`, `TestRealWorldEdgeCases`, `TestDownloadOperations`, and `TestPerformanceMetrics`).

The regression went undetected through two verification layers:
1. **Executor verification**: Ran `uv run pytest` without Z-Library credentials, so integration tests were skipped entirely (they have a `skipif` guard on `ZLIBRARY_EMAIL`/`ZLIBRARY_PASSWORD`).
2. **Phase verifier**: Also ran without credentials and reported 5/5 must-haves passed.

The full integration suite (with credentials) revealed the regression: `fixture 'zlib_client' not found` on every test that depended on it.

## Context

Phase 13, Plan 02: "Remove deprecated AsyncZlib references." The plan specified rewriting `TestRealAuthentication` to use `EAPIClient` but did not explicitly call out the `zlib_client` fixture as a shared dependency consumed by other test classes. The executor followed the plan's task scope literally without analyzing downstream dependents of the symbols it modified.

## Potential Cause

**Root cause: Symbol-level changes made without analyzing downstream dependents.**

The `zlib_client` fixture was a shared dependency consumed by multiple test classes. Removing it (or failing to recreate it with EAPIClient) without updating all consumers violated dependency awareness. This is a planning gap (the plan should have identified all `zlib_client` consumers) compounded by an executor gap (the executor should have checked for references before removing/not-replacing the fixture).

**Contributing factor: Verification blind spot.** Integration tests gated behind credentials are invisible to standard CI-style verification. The verifier confirmed "all tests pass" but only ran the non-integration subset. There is no mechanism to flag that a class of tests was entirely skipped during verification.

**Actionable convention:** When removing or replacing a shared symbol (fixture, class, function), always run `find_referencing_symbols` or equivalent grep to identify all consumers before making changes. Plans that modify shared symbols should explicitly list all dependent files.
