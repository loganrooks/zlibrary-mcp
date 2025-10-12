# Migration Strategy Evaluation Report (INT-001)

**Date:** 2025-04-14

**Objective:** Evaluate potential strategies to resolve issue INT-001 ("No tools found" in client UI) affecting `zlibrary-mcp`, considering the current architecture (SDK 1.8.0, CJS) and findings from `docs/mcp-server-comparison-report.md`.

## 1. Context & Primary Suspected Cause

**Issue:** The `zlibrary-mcp` server, despite appearing to generate and send a `ListToolsResponse`, results in the client UI displaying "No tools found" (INT-001). Debugging attempts focused on response structure and SDK versions were unsuccessful.

**Analysis based on `docs/mcp-server-comparison-report.md`:**
*   `zlibrary-mcp` currently uses `@mcp/sdk` v1.8.0 and CommonJS (CJS).
*   Crucially, the `ListToolsRequest` handler in `zlibrary-mcp/index.js` **bypasses the `zod-to-json-schema` library** and sends hardcoded, minimal dummy JSON schemas for all tools.
*   Working examples using Zod schemas (`mcp-server-sqlite-npx`, `filesystem`) **correctly use `zod-to-json-schema`** to generate the `input_schema` in their `ListToolsResponse`. This works even in `sqlite-npx` which uses SDK 1.8.0 (though with ESM).
*   Other examples using older SDKs (1.0.x) and ESM define schemas manually as plain JSON objects.
*   Debugging history confirms `zlibrary-mcp` sends a *structurally valid* JSON response, but the client still fails, strongly suggesting the *content* of the schemas (i.e., the dummy schemas) is incompatible with client expectations.

**Conclusion on Primary Cause:** The **most likely root cause** of INT-001 is the **incorrect schema generation** in `zlibrary-mcp`. By sending dummy schemas instead of properly generated JSON schemas derived from the Zod definitions via `zod-to-json-schema`, the server is likely providing data that the client cannot parse or interpret correctly, leading to the "No tools found" error. The SDK version (1.8.0) and module system (CJS) are less likely to be the *direct* cause, as `zod-to-json-schema` is confirmed functional with SDK 1.8.0 in the `sqlite-npx` example.

## 2. Primary Recommendation: Fix Schema Generation

**Action:** Modify the `ListToolsRequest` handler in `zlibrary-mcp/index.js` to correctly use `zodToJsonSchema` to generate the `input_schema` for each registered tool, replacing the current dummy schema logic.

**Rationale:**
*   **Directly Targets Cause:** Addresses the most probable root cause identified in the analysis.
*   **Lowest Risk & Effort:** Involves modifying existing code within the current architecture, minimizing the scope of change compared to major migrations. Requires ensuring `zod-to-json-schema` is correctly imported and used in CJS (`require('zod-to-json-schema').default`).
*   **Proven Approach:** Aligns with the successful implementation pattern seen in `mcp-server-sqlite-npx` and `filesystem`.

**Verification:** After implementing this fix, test thoroughly to confirm if INT-001 is resolved.

## 3. Evaluation of Alternative Migration Strategies

These strategies should be considered **only if the primary recommendation (fixing schema generation) fails** or as **subsequent modernization efforts**.

**Evaluation Criteria:**
*   **Likelihood of Resolving INT-001:** How likely is this option *alone* to fix the issue, assuming the primary fix was insufficient?
*   **Estimated Effort & Complexity:** Code changes, dependency management, testing.
*   **Risks:** Breaking changes, conflicts, migration difficulties.
*   **Maintainability:** Long-term health of the chosen stack.

---

### Option 1: SDK Downgrade (~1.0.x), Keep CJS

*   **Likelihood (Alone):** **Very Low**. Does not address the schema generation issue. Relies on chance differences in older SDK/client interaction. Examples using older SDKs used *manual* schemas, not `zod-to-json-schema`.
*   **Effort:** **Medium**. Requires SDK API adaptation, dependency checks.
*   **Risks:** **Medium**. Potential breaking changes, dependency conflicts, high risk of *not* fixing INT-001.
*   **Maintainability:** **Poor**. Locks project into an older SDK; CJS is less standard.

---

### Option 2: Migrate to ESM, Keep SDK 1.8.0

*   **Likelihood (Alone):** **Very Low**. ESM migration *alone* does not fix the schema generation logic. Its benefit is primarily architectural alignment and removing CJS/ESM interop as a variable.
*   **Likelihood (Combined with Schema Fix):** **High**. If the primary schema fix *requires* or benefits from ESM (e.g., due to subtle interop issues with `zod-to-json-schema` in CJS), this becomes viable. Aligns with `sqlite-npx` (SDK 1.8.0, ESM, working `zod-to-json-schema`).
*   **Effort:** **High**. Significant refactoring (imports, `__dirname`, CJS deps, Jest config).
*   **Risks:** **High (during migration)**. Refactoring errors, CJS interop issues, build/test adjustments.
*   **Maintainability:** **Good**. Aligns with modern Node.js standards (ESM).

---

### Option 3: Migrate to ESM + SDK Downgrade (~1.0.x)

*   **Likelihood (Alone):** **Very Low**. Combines two approaches that don't target the root cause effectively.
*   **Effort:** **Very High**. Combines efforts of both migrations.
*   **Risks:** **Highest**. Combines risks of both approaches.
*   **Maintainability:** **Mixed**. Gains ESM but uses an outdated SDK.

---

## 4. Final Recommendation Pathway

1.  **Implement Primary Recommendation:** **Fix the `zod-to-json-schema` usage** in `index.js` within the current CJS/SDK 1.8.0 environment. **Test thoroughly.** This has the highest probability of resolving INT-001 with the least disruption.
2.  **If Primary Fails (or for Modernization):** Consider **Option 2 (Migrate to ESM, Keep SDK 1.8.0)**, ensuring the correct `zod-to-json-schema` implementation is carried over or implemented during the migration. This aligns the architecture with modern standards and other examples.
3.  **Avoid Options 1 and 3:** SDK downgrade (Option 1) is unlikely to help and harms maintainability. Combining ESM migration with an SDK downgrade (Option 3) is unnecessarily complex and risky.

## 5. High-Level Steps for Recommended Pathway

**Phase 1: Fix Schema Generation (Highest Priority)**
1.  **Modify `index.js`:** In the `ListToolsRequest` handler, replace dummy schema logic with code that imports (`require('zod-to-json-schema').default`) and uses `zodToJsonSchema(tool.schema, name)` to generate `input_schema`.
2.  **Test:** Run the server and client, verifying if tools are listed correctly (INT-001 resolved).

**Phase 2: Migrate to ESM (Optional Modernization, if Phase 1 fails or desired later)**
3.  **Update `package.json`:** Set `"type": "module"`.
4.  **Convert Imports/Exports:** Change `require`/`module.exports` to `import`/`export` project-wide.
5.  **Handle CJS Dependencies:** Use dynamic `import()` if needed.
6.  **Replace `__dirname`/`__filename`:** Use `import.meta.url`.
7.  **Update Jest Configuration:** Adjust `jest.config.js` for ESM.
8.  **Thorough Testing:** Full test suite (`npm test`) and manual verification.