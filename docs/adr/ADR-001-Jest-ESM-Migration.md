# ADR-001: Migrate Jest Configuration to ES Modules (ESM)

**Date:** 2025-04-14

**Status:** Proposed

## Context

The `zlibrary-mcp` project has been migrated to use TypeScript compiled to ES Modules (ESM), with `"type": "module"` set in `package.json` and `"module": "NodeNext"` in `tsconfig.json`.

Following the resolution of INT-001 (MCP tool listing failure), an attempt to run the test suite via `npm test` failed during the configuration loading phase with the error: `ReferenceError: module is not defined in ES module scope`.

This error occurs because the existing Jest configuration file (`jest.config.js`) uses CommonJS syntax (`module.exports`), which is incompatible when Node.js attempts to load it as an ES module due to the project-wide `"type": "module"` setting.

## Decision Drivers

*   **Consistency:** The project's source code is now ESM; the test configuration should align for consistency and maintainability.
*   **Functionality:** The test suite is currently broken and needs to be runnable to ensure code quality and prevent regressions.
*   **Modern Standards:** ESM is the standard module system for modern JavaScript and Node.js.
*   **Tooling Support:** Jest and `ts-jest` provide explicit (though sometimes experimental) support for ESM.

## Considered Options

1.  **Migrate Jest Config to ESM Syntax:** Modify `jest.config.js` to use `export default { ... }` and update internal `ts-jest` configuration according to official guides.
2.  **Use `.cjs` Extension:** Rename `jest.config.js` to `jest.config.cjs` to force Node.js to load it as a CommonJS module.
3.  **Revert Project to CommonJS:** Undo the entire ESM migration for the project source code and configuration.

## Decision

**Chosen Option:** Option 1 - **Migrate Jest Config to ESM Syntax.**

**Rationale:**
*   This approach maintains consistency with the project's overall ESM direction.
*   It directly addresses the root cause of the configuration loading error (syntax incompatibility).
*   While potentially requiring more upfront configuration adjustments (for `ts-jest` and Node flags) compared to Option 2, it avoids the inconsistency of mixing module types in configuration.
*   Option 3 (reverting to CJS) was rejected as it undoes significant modernization work and the root causes of the original INT-001 issue were found to be independent of the module system.

## Implementation Plan

1.  **Modify `jest.config.js` Syntax:** Change `module.exports = { ... }` to `export default { ... }`.
2.  **Verify `tsconfig.json`:** Ensure `"isolatedModules": true` is set in `compilerOptions` as recommended by the `ts-jest` guide for hybrid module values like `NodeNext`.
3.  **Update `ts-jest` Configuration (in `jest.config.js`):** Adopt the recommended ESM preset approach:
    *   Import `createDefaultEsmPreset` from `ts-jest`.
    *   Replace the manual `transform` and `extensionsToTreatAsEsm` configuration with `...createDefaultEsmPreset()`. Potentially add the `useESM: true` flag within the preset options if needed, although the preset should handle this.
4.  **Update `package.json` Test Script:** Modify the `"test"` script to include the necessary Node.js flag: `"test": "node --experimental-vm-modules node_modules/jest/bin/jest.js --coverage"`.
5.  **Run Tests (`npm test`):** Execute the test suite.
6.  **Diagnose & Fix Failures:** Systematically address any test failures, likely related to ESM mocking, import paths (requiring `.js` extensions), or outdated assertions.

## Consequences

*   The immediate `ReferenceError` during config loading will be resolved.
*   Further test failures related to Jest's ESM handling (mocking, module resolution) are expected and will require subsequent debugging and fixes in test files (`__tests__/**/*.test.js`) and potentially mocks (`__mocks__/`).
*   The test setup will be fully aligned with the project's ESM standard.