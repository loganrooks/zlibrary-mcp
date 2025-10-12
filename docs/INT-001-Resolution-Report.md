# INT-001: MCP Server Tool Listing Failure - Resolution Report

**Date:** 2025-04-14

**Author:** Auto-Coder (Mode: code)

## 1. Problem Summary

Issue INT-001 involved the `zlibrary-mcp` server failing to have its tools listed in the RooCode client UI. This occurred despite the server successfully connecting to the client and having been migrated to TypeScript/ESM using `@modelcontextprotocol/sdk` version 1.8.0. Notably, tools from *other* configured MCP servers were listed correctly, indicating the problem was specific to `zlibrary-mcp`'s implementation or its interaction with the client, rather than a general client failure.

## 2. Initial State & Constraints

*   **Project:** `zlibrary-mcp`
*   **Language/Runtime:** TypeScript compiled to ESM JavaScript (`"type": "module"` in `package.json`, `tsconfig.json` configured for `NodeNext`).
*   **SDK:** `@modelcontextprotocol/sdk` v1.8.0.
*   **Build:** `npm run build` (using `tsc`) completed successfully, outputting JS files to `dist/`.
*   **Configuration:** `mcp_settings.json` confirmed to correctly point to `dist/index.js` with `"shell": true`.
*   **Environment:** Other MCP servers (e.g., `github`, `filesystem`, `puppeteer`) were functioning correctly and listing their tools in the same RooCode client instance.

## 3. Debugging Process & Attempts

The core strategy adopted for this specific task (after previous unsuccessful attempts noted in the Memory Bank) was to compare `zlibrary-mcp/src/index.ts` against a known working TS/ESM MCP server using SDK v1.8.0+, specifically `wonderwhy-er/DesktopCommanderMCP/src/server.ts`.

**Attempt 1: Aligning `zodToJsonSchema` and `registerCapabilities`**

*   **Observation:** Comparison revealed two immediate differences:
    1.  `zlibrary-mcp` had a potentially redundant `server.registerCapabilities({...})` call *after* server instantiation.
    2.  `zlibrary-mcp` passed an extra `name` argument to `zodToJsonSchema(tool.schema, name)` in the `ListToolsRequest` handler, whereas the working example did not.
*   **Reasoning:** Hypothesized that either the redundant call or the extra argument was causing incompatibility. The goal was to align `zlibrary-mcp` more closely with the working example.
*   **Action:** Removed the `server.registerCapabilities()` call and removed the second `name` argument from the `zodToJsonSchema()` call. Rebuilt the project.
*   **Result:** **Failure.** The server failed to start entirely, throwing an error: `Error: Server does not support tools (required for tools/list)`.

**Attempt 2: Correcting Capability Declaration**

*   **Observation:** The error from Attempt 1 indicated that the server instance, at the point of setting up the `ListToolsRequest` handler, did not have the `tools` capability enabled. Re-examining the `new Server()` constructor call revealed the issue.
*   **Reasoning:** The working example passed server info (name, version) as the *first* argument and server options (including `capabilities`) as the *second* argument to `new Server()`. Our code was only passing the first argument. Removing the redundant `registerCapabilities` call in Attempt 1, without ensuring capabilities were declared correctly at instantiation, resulted in no capabilities being enabled at all.
*   **Action:** Modified the `new Server()` call in `src/index.ts` to include the second argument containing the `capabilities: { tools: {}, resources: {}, prompts: {} }` object. Rebuilt the project.
*   **Result:** **Partial Success.** The server started successfully, but the tools were still not listed in the RooCode UI.

**Attempt 3: Isolating Schema Generation (Diagnostic)**

*   **Observation:** Tools still not listed despite correct capability declaration and `zodToJsonSchema` call structure.
*   **Reasoning:** Hypothesized that while the *call* to `zodToJsonSchema` was now correct, the *output* for one or more of our specific Zod schemas might be subtly incompatible with the client's parser, or that our previous complex error handling/empty schema check within the handler was masking an issue.
*   **Action:** As a diagnostic step, modified the `ListToolsRequest` handler to bypass `zodToJsonSchema` entirely and return a static, known-good empty schema (`{ type: "object", properties: {}, required: [] }`) for *all* tools. Rebuilt the project.
*   **Result:** **Failure.** Tools were still not listed. This indicated that the issue was not related to the dynamic generation of schemas via `zodToJsonSchema` or the specific Zod definitions themselves.

**Attempt 4: Identifying Key Name Mismatch (Discovery & Final Fix)**

*   **Observation:** With schema generation ruled out, a meticulous comparison of the *structure* of the object returned by the `ListToolsRequest` handler was performed. The working example used `inputSchema` (camelCase) as the key for the tool's input schema definition. Our code was using `input_schema` (snake_case).
*   **Reasoning:** The MCP specification likely mandates camelCase (`inputSchema`) for this key. This mismatch would prevent the client from correctly identifying the input schema for each tool. A subsequent TypeScript error (`Property 'input_schema' is missing...`) confirmed a mismatch between our local `ToolDefinition` interface and the object we were trying to return after fixing the key name in the return statement.
*   **Action:**
    1.  Restored the use of `zodToJsonSchema` (reverting the diagnostic change from Attempt 3).
    2.  Corrected the key in the return object within the `.map()` function in the `ListToolsRequest` handler to `inputSchema`.
    3.  Corrected the corresponding key in the local `ToolDefinition` interface definition to `inputSchema`.
    4.  Rebuilt the project.
*   **Result:** **Success.** The user confirmed the server connected and all tools were listed correctly in the RooCode UI.

## 4. Root Cause Analysis

The failure of `zlibrary-mcp` tools to list in RooCode (INT-001) stemmed from **two critical deviations** from the expected MCP SDK v1.8.0 implementation pattern, as observed in the working `DesktopCommanderMCP` example:

1.  **Incorrect Capability Declaration:** The `capabilities` object (defining `tools`, `resources`, `prompts`) was not passed correctly as the *second argument* to the `new Server(serverInfo, serverOptions)` constructor. This meant the server instance was not properly initialized with tool support, leading to the "Server does not support tools" error when attempting to set request handlers *after* the redundant `registerCapabilities` call was removed.
2.  **Incorrect Schema Key Name:** The `ListToolsRequest` handler was constructing the tool definition objects using the key `input_schema` (snake_case) for the JSON schema, whereas the client and likely the MCP specification expect `inputSchema` (camelCase). This mismatch prevented the client from correctly parsing the tool definitions received from the server, even though the server was sending a structurally valid response.

The combination of these issues resulted in the observed behavior: the server could connect (basic transport worked), but the client could not interpret the tool list correctly.

**Note on CJS vs. ESM:** It's important to clarify that these root causes (incorrect capability declaration via the `new Server()` constructor and the `inputSchema` key name mismatch) are related to the specific API and protocol requirements of SDK v1.8.0 and MCP, respectively. They are **not inherently tied to the choice between CommonJS (CJS) and ES Modules (ESM)**. A CJS implementation using SDK v1.8.0 would have needed these same corrections to function properly. The migration to ESM was pursued for modernization and alignment with working examples, but did not, in itself, fix the core blocking issues of INT-001.

## 5. Crucial Code Sections for Stability

To prevent regression of this issue, the following sections in `src/index.ts` (based on the final fixed version) are critical and should be maintained:

1.  **Server Instantiation (Lines ~252-265):**
    ```typescript
    const server = new Server(
      { // ServerInfo
        name: "zlibrary-mcp",
        description: "Z-Library access for AI assistants",
        version: getPackageVersion()
      },
      { // ServerOptions - Capabilities MUST be declared here
        capabilities: {
          tools: {},
          resources: {},
          prompts: {}
        }
      }
    );
    ```
    *Crucially, the `capabilities` object must be present in the second argument.*

2.  **`ListToolsRequest` Handler Return Object (Lines ~277-284):**
    ```typescript
      const tools = Object.entries(toolRegistry).map(([name, tool]) => {
        const jsonSchema = zodToJsonSchema(tool.schema);
        return {
          name: name,
          description: tool.description,
          inputSchema: jsonSchema, // MUST be inputSchema (camelCase)
        };
      });
    ```
    *Crucially, the key for the schema must be `inputSchema`.*

3.  **`ToolDefinition` Interface (Lines ~168-172):**
    ```typescript
    interface ToolDefinition {
        name: string;
        description?: string;
        inputSchema: any; // MUST be inputSchema (camelCase)
    }
    ```
    *Crucially, the local interface used for type checking must match the expected return structure, using `inputSchema`.*

## 6. Conclusion

The resolution of INT-001 highlights the importance of strictly adhering to the implementation patterns and expected data structures dictated by the specific version of the MCP SDK being used. Comparing against a known working example was essential in identifying the subtle but critical deviations in capability declaration and response object key naming that caused the tool listing failure.