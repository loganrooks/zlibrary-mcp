# **Technical Investigation Report: MCP Client Failure (INT-001) \- Analysis of Tool Discovery Issues**

## **1\. Executive Summary**

This report details the investigation into issue INT-001, where the RooCode Model Context Protocol (MCP) client fails to recognize tools provided by a specific Node.js server, displaying a "No tools found" message. The server utilizes CommonJS (CJS) module syntax and version 1.8.0 of the @modelcontextprotocol/sdk. Debugging confirmed the server sends a structurally valid JSON ListToolsResponse.

The central anomaly identified is the server's current practice of sending hardcoded, minimal dummy JSON schemas (e.g., { type: "object", properties: {}, description: "..." }) within the input\_schema field for each tool. This bypasses the intended use of the zod-to-json-schema library to generate complete schemas from the server's Zod definitions. A comparable internal server using ES Modules (ESM) and correctly generating schemas via zod-to-json-schema functions without issue.

The primary hypothesis explored and validated by this investigation is that the *content*, or more accurately, the lack of meaningful detail within these dummy input\_schema objects, prevents the RooCode client from understanding how to utilize the advertised tools. While structurally valid as JSON fragments, these schemas fail to define any input parameters (properties), rendering them functionally useless for tool invocation or client-side validation.

Analysis of the MCP specification, client behavior patterns documented in guides and examples, and comparison with working implementations strongly indicates that the inadequate detail in the dummy schemas is the direct cause of the client's failure to list the tools. Secondary factors, such as potential nuances in the CJS environment or the specifics of the zod-to-json-schema library, are considered less likely to be the root cause but are relevant for implementing the corrective actions.

The primary recommendation is to **correctly implement zod-to-json-schema** within the CJS server environment. This involves removing the hardcoded dummy schemas and ensuring that complete, accurate JSON schemas, derived from the server's Zod definitions and adhering to MCP specifications, are generated and included in the ListToolsResponse. Careful verification of the generated schema structure and testing within the CJS context are crucial follow-up steps.

## **2\. Problem Context & Technical Environment**

The system under investigation is a Node.js server designed to function as an MCP provider, enabling interaction with Large Language Models (LLMs) and associated applications. Its technical stack presents specific characteristics relevant to the observed failure:

* **Server Runtime:** Node.js.  
* **Module System:** The server employs the CommonJS (CJS) module system, utilizing require for dependency management. This contrasts with the ES Modules (ESM) system (import/export) used in some comparison points.  
* **MCP Implementation:** The server leverages the @modelcontextprotocol/sdk library, specifically version 1.8.0, to handle MCP communications.1 This SDK provides abstractions for building MCP servers and clients in TypeScript/JavaScript.  
* **Schema Definition:** Tool input schemas are defined internally using the Zod library, a popular TypeScript-first schema declaration and validation tool.1

**Observed Failure (INT-001):** When the RooCode MCP client, a known consumer of MCP services 4, sends a ListToolsRequest to this server, its user interface displays an error indicating "No tools found". This failure prevents users from accessing the server's intended functionalities via the client.

**Server Behavior Analysis:** Despite the client-side error, debugging confirms the following server-side behavior:

1. The server successfully receives the ListToolsRequest from the client.  
2. The server generates and transmits a response.  
3. The transmitted response is structurally valid JSON and conforms to the overall format expected for a ListToolsResponse as defined by the MCP specification.6

**Crucial Deviation:** The core discrepancy lies in the content of the input\_schema field within the ListToolsResponse. Instead of containing detailed JSON Schema objects describing the expected inputs for each tool, the server currently sends a hardcoded, minimal dummy schema for all tools:

JSON

{  
  "type": "object",  
  "properties": {},  
  "description": "..."  
}

This implementation bypasses the intended mechanism: using the zod-to-json-schema library 7 to dynamically convert the server's internal Zod schema definitions into corresponding JSON Schema objects suitable for the input\_schema field. This bypass was likely introduced during development or debugging efforts.

**Comparison Points:** Two key comparison points provide critical context:

1. **Working Internal Server (mcp-server-sqlite-npx):**  
   * Also uses @mcp/sdk v1.8.0 and defines schemas with Zod.  
   * Crucially, it operates within an ES Modules (ESM) environment (import syntax).  
   * It **correctly utilizes zod-to-json-schema** to generate detailed input\_schema objects.  
   * This server functions correctly with the RooCode client; its tools are successfully listed and presumably usable.  
2. **Working Official Examples:**  
   * Some official MCP examples utilize older SDK versions (e.g., 1.0.x) and also run in an ESM environment.  
   * These examples define their input\_schema *manually* as plain JSON Schema objects, without involving Zod or the zod-to-json-schema library.  
   * These examples also function correctly with MCP clients.

**Initial Hypothesis:** Based on these observations, the initial hypothesis posits that the *content* of the dummy schemas is the root cause of the failure. Even though the overall response structure is valid, the lack of detail within the input\_schema (specifically, the absence of defined properties) prevents the RooCode client from correctly interpreting or validating the tools, leading it to conclude that no functional tools are available.

## **3\. Analysis of Potential Causes**

To determine the root cause of INT-001, several potential factors were investigated, drawing upon the MCP specification, library documentation, and general principles of Node.js development.

### **3.1. Impact of input\_schema Content on MCP Clients**

The investigation focused first on the most direct anomaly: the content of the input\_schema being sent.

MCP Specification Requirements:  
The formal MCP specification establishes the protocol requirements, referencing a TypeScript schema definition (schema.ts) as the authoritative source.6 While the main specification document doesn't exhaustively detail input\_schema validation rules, analysis of the referenced schema.ts 6 clarifies the structural expectations for the inputSchema field within each Tool object returned by a ListToolsResponse:

* The inputSchema **must** be a valid JSON Schema object.  
* It **must** declare type: "object", signifying that tool inputs are passed as a structured object.  
* It **may** contain a properties field, which **must** be an object. Keys within properties represent tool parameter names, and their values are JSON Schema objects defining the type and constraints for each parameter.  
* It **may** contain a required field, which **must** be an array of strings. Each string must correspond to a key defined in properties, indicating mandatory parameters.

Evaluating the dummy schema ({ type: "object", properties: {}, description: "..." }) against these requirements reveals a critical point: it *technically satisfies the minimal structural rules*. It is a JSON object, has type: "object", and includes a properties field which is an object (albeit empty). However, this minimal compliance misses the *functional purpose* of the schema. The specification defines the structure (type: "object") and the mechanism for defining parameters (properties, required). An empty properties object, while structurally permissible within JSON Schema itself, fails entirely to convey any information about the tool's expected inputs. This fundamentally undermines the schema's role in the context of tool discovery and invocation within MCP.

Client Expectations and Usage:  
MCP clients utilize the ListToolsResponse not just to see tool names, but crucially, to understand how to interact with those tools.9 The input\_schema plays a central role in this process:

* **Informing the LLM/Application:** The schema details the parameters required for a tool call. This information is often passed to the LLM (e.g., as part of a system prompt or formatted according to the LLM's function-calling API requirements) so it can generate correct tool invocation requests.9 A practical example shows tool.inputSchema being directly mapped to the parameters field for a Google Gemini function declaration.9  
* **Client-Side Representation:** Some clients automatically generate internal representations based on the received schema. For instance, the AgentIQ MCP client generates Pydantic input schemas from the server's input\_schema to facilitate interaction.12  
* **Client-Side Validation:** Development guides and best practices illustrate that clients often use the input\_schema to validate arguments *before* sending a tools/call request to the server.10 This involves parsing the JSON schema and potentially converting it into a format usable by a client-side validation library.10

Connecting the specification's intent with observed client behavior leads to a clear conclusion: clients actively parse and utilize the *content* of the input\_schema. They don't merely check for structural validity; they rely on the presence and definition of properties (and required fields) to understand the tool's interface. A schema lacking any defined properties, like the dummy schema being sent, provides no actionable information. It prevents the client from constructing a valid tool call request or performing any meaningful input validation.

Therefore, the "No tools found" error reported by the RooCode client likely signifies "No *usable* or *callable* tools found." The client, upon receiving schemas that describe tools requiring an object input (type: "object") but define zero properties (properties: {}), may reasonably conclude that these tools are improperly defined or unusable and filter them out. The core purpose of ListToolsResponse is discovery *for subsequent execution*. If the provided schema makes execution impossible to determine, the tool is functionally undiscoverable. This aligns perfectly with the observed behavior and the difference compared to the working server that provides complete schemas.

**Likelihood:** The likelihood of the inadequate dummy input\_schema content being the primary cause of INT-001 is assessed as **Very High**.

### **3.2. Investigation of zod-to-json-schema**

Although currently bypassed, the zod-to-json-schema library is the intended mechanism for schema generation and thus relevant to the solution.

Functionality and Configuration:  
The library's purpose is to convert Zod schemas into JSON Schema objects.7 It offers various configuration options, including naming strategies, definition handling, targeting specific JSON Schema versions or specifications (like OpenAPI 3.0 or OpenAI's strict mode), and error message inclusion.7  
Known Issues:  
The library's documentation acknowledges several known issues 7:

* The representation of Zod's .transform output might not align with the inferred type.  
* Non-string keys used with z.record are generally ignored due to JSON Schema limitations.  
* The OpenAI target (openaiStrictMode) is considered experimental.13  
* Potential edge cases exist with Zod v3's .isOptional() behavior if certain Zod features like preprocess are used with impure functions.  
* Support for relative JSON pointers (used with "$refStrategy": "relative") is limited in downstream tooling.

Version Compatibility:  
zod-to-json-schema aims for version alignment with Zod itself, with major/minor versions reflecting feature parity.7 It depends on the same prerequisites as Zod (TypeScript 4.5+, strict mode enabled).3 Compatibility should always be verified against the specific Zod version used in the project.  
CJS vs. ESM Considerations:  
No specific issues related to CJS versus ESM usage are explicitly documented in the library's main README or tracked issues.7 However, the library's build process includes a specific step (postcjs.ts) to inject a {"type": "commonjs"} directive into the CJS distribution's package.json.15 This indicates deliberate handling of CJS packaging. While this suggests an intent to support CJS, it doesn't preclude the possibility of subtle runtime differences or dependency interaction issues that can sometimes arise in Node.js CJS/ESM interop scenarios.16  
Relevance to INT-001:  
Since the library is currently bypassed, none of its internal issues are the direct cause of the observed failure. However, these factors are highly relevant when implementing the fix (i.e., re-introducing the library). The successful use of this library in the working ESM comparison server demonstrates its fundamental compatibility with @mcp/sdk v1.8.0. Any difficulties encountered during the reimplementation in the CJS environment might stem from version mismatches (with Zod), incorrect library configuration, or potentially subtle CJS-specific behaviors.  
**Likelihood:** The likelihood of zod-to-json-schema being the *root cause* of the current issue is **Very Low** (as it's not being used). However, the likelihood of encountering issues related to its configuration, versioning, or CJS integration *during the implementation of the fix* is assessed as **Medium**.

### **3.3. Analysis of @modelcontextprotocol/sdk v1.8.0**

The specific version of the MCP SDK used by the server was examined for potential contributions to the issue.

Version Context:  
The problematic server uses @mcp/sdk version 1.8.0. The SDK is actively developed, with version 1.9.0 being the latest mentioned in the provided materials.1  
Changes in v1.8.0:  
Available information suggests that changes introduced in v1.8.0 primarily involved improvements to an SSE (Server-Sent Events) server example and fixes related to spawning stdio servers as subprocesses on Windows.20 No evidence found in the reviewed materials points to specific changes in v1.8.0 (compared to prior versions like 1.0.x) that would fundamentally alter how ListToolsResponse schemas are handled or validated in a way that explains INT-001.20  
CJS Issue Fixed in v1.9.0:  
Version 1.9.0 addressed a CJS-specific dependency issue by updating the pkce library to version 5.0.0.19 PKCE (Proof Key for Code Exchange) is an security extension to OAuth 2.0. This fix suggests that CJS environments might have encountered issues related to authentication flows in SDK versions up to and including 1.8.0. While the ListTools operation itself typically doesn't involve active authentication negotiation, this fix serves as an indicator that the SDK's behavior could potentially differ between CJS and ESM environments, particularly concerning interactions with dependencies. It is unlikely, however, that this specific pkce issue would manifest as the "No tools found" error solely based on the content of a structurally valid ListToolsResponse.  
**Likelihood:** The likelihood of a bug or incompatibility within @mcp/sdk v1.8.0 being the direct cause of INT-001 is assessed as **Low**. This is strongly supported by the fact that the working internal comparison server uses the *exact same SDK version* (1.8.0) without exhibiting the issue.

### **3.4. Influence of CommonJS (CJS) vs. ES Modules (ESM)**

The difference in module systems between the failing server (CJS) and the working comparison server (ESM) warrants consideration.

Fundamental Differences and Interoperability:  
CJS (require, synchronous loading, module.exports) and ESM (import, asynchronous loading, export) have distinct mechanisms.16 While Node.js supports interoperability, challenges can arise, such as the "dual package hazard" where libraries supporting both formats might behave inconsistently depending on consumption.17 Proper configuration via package.json (main, module, exports fields) is crucial for libraries aiming to support both systems effectively.21 Subtle runtime differences also exist (e.g., \_\_dirname availability, top-level await).23 The ecosystem is transitioning towards ESM, but CJS remains deeply integrated, particularly in established Node.js applications.17  
Relevance to INT-001:  
Could the CJS environment introduce subtle issues affecting the SDK or schema generation?

* **Serialization:** It's conceivable, though unlikely for standard JSON serialization, that the CJS environment could cause the SDK to serialize the ListToolsResponse payload slightly differently than in ESM, potentially triggering an unexpected parsing issue on the client. However, the user report states the response *is* structurally valid JSON conforming to the spec, making this less probable.  
* **Schema Generation (Hypothetical):** If zod-to-json-schema *were* being used, the CJS environment might affect its output compared to ESM, perhaps due to how dependencies are resolved or minor runtime variations. This remains speculative as the library is currently bypassed.  
* **Development Context:** A plausible connection is that the CJS environment might have presented challenges when initially attempting to integrate zod-to-json-schema, leading developers to opt for the (now problematic) dummy schema workaround. CJS can sometimes introduce complexities with build tooling or dependencies that might be simpler in a pure ESM setup.

Considering these points, the CJS environment serves primarily as the *context* in which the failure occurs and represents a key difference from the working comparison point. It is less likely to be the *direct* cause of the client rejecting tools based on the *content* of the dummy schema, especially given the confirmation of a structurally valid response. If CJS caused a fundamental serialization flaw in the SDK, the response likely wouldn't validate against the expected structure. It's more probable that CJS-related complexities influenced the *development decision* to bypass schema generation, thereby leading indirectly to the current state.

**Likelihood:** The likelihood of the CJS environment being the *direct root cause* is assessed as **Low**. Its potential role as a *contributing factor* to the workaround or as a source of *complication during the fix* is assessed as **Medium**.

## **4\. Comparative Schema Analysis**

To visually underscore the critical difference between the schemas sent by the failing server and those expected by clients or sent by working servers, the following table compares their key characteristics against the MCP specification requirements derived from.6 Examples for "Generated" and "Manual" schemas are illustrative and based on common patterns and the requirements analysis.

| Feature | Dummy Schema (Failing CJS Server) | Generated Schema (Working ESM Server \- Illustrative) | Manual Schema (Working Old Example \- Illustrative) | MCP Spec Requirement | Client Usability Implication |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **type field value** | "object" | "object" | "object" | **Must** be "object" | Met by all examples. |
| **properties field** | Present, but empty ({}) | Present, populated (e.g., {"arg1": {...}}) | Present, populated (e.g., {"paramA": {...}}) | **May** be present; **Must** be object if present. | **Critical:** Empty properties provides no parameter info. |
| **required field** | Absent (undefined) | Present or Absent (e.g., \["arg1"\] or undefined) | Present or Absent | **May** be present; **Must** be string array if present. | Dependent on properties. |
| **Parameter Definition** | None | Detailed (types, constraints per Zod definition) | Detailed (types, descriptions manually defined) | Implicitly required via properties. | **Essential** for constructing calls & validation. |
| **Client Functional Status** | **Unusable** | **Usable** | **Usable** | N/A | Client likely filters/ignores unusable tools. |

This comparison starkly highlights the deficiency of the dummy schema. While meeting the bare minimum structural requirement of type: "object", it completely lacks the properties definitions that are present in working examples and are essential for conveying the tool's input requirements to the client. This lack of parameter information directly explains why a client, needing to know *how* to call a tool, would deem tools described by such schemas as unusable.

## **5\. Synthesis and Prioritized Findings**

Consolidating the analysis across the potential causes leads to the following conclusions:

* The fundamental issue is the server providing input\_schema definitions that lack the necessary detail for clients to understand tool usage. The dummy schemas, specifically their empty properties object, are functionally inadequate despite being structurally valid JSON fragments.  
* MCP clients, including potentially the RooCode client, demonstrably rely on the *content* of the input\_schema, particularly the properties and required fields, to determine how to formulate tool calls and perform input validation.6 The absence of this information in the dummy schemas prevents this.  
* The working ESM server, using the same @mcp/sdk v1.8.0 but providing correctly generated, detailed schemas via zod-to-json-schema, serves as strong evidence that the schema content itself is the critical differentiating factor leading to success or failure.  
* Potential issues related to the zod-to-json-schema library or the nuances of the CJS environment are secondary concerns. They are not the direct cause of the failure given the current use of dummy schemas but are important considerations for implementing the required fix.  
* The @mcp/sdk v1.8.0 is unlikely to contain a relevant bug causing this specific issue, given the working comparison server and the lack of specific evidence pointing to such a flaw in the provided materials.20

**Prioritization of Causes:** Based on the evidence and analysis, the potential causes are prioritized by likelihood:

1. **Inadequate Dummy input\_schema Content (Likelihood: Very High):** This directly aligns with the observed client behavior ("No tools found" interpreted as "No usable tools found"), the functional requirements derived from the MCP specification and client usage patterns 6, and the key difference compared to the working server.  
2. **zod-to-json-schema Issues in CJS (Likelihood: Medium \- *for the fix*):** While not the current cause, potential configuration, versioning, or CJS-specific interaction issues with this library must be considered during the implementation of the solution.  
3. **CJS Environment Nuances (Likelihood: Low \- *as root cause*):** The CJS environment might have influenced the decision to use dummy schemas or could introduce complexities during the fix, but it's unlikely to be the direct cause of the client error given the structurally valid response.  
4. **@mcp/sdk v1.8.0 Bug (Likelihood: Very Low):** Contradicted by the working ESM server on the same version and lack of specific evidence.

**Most Probable Root Cause:** The RooCode client receives the ListToolsResponse but encounters input\_schema definitions that, due to having an empty properties object, provide no information about how to call the tools. Consequently, the client interprets these tools as unusable or improperly defined and filters them out, resulting in the "No tools found" error (INT-001).

## **6\. Recommendations**

Based on the analysis, the following steps are recommended to resolve INT-001 and ensure robust MCP tool discovery:

**Immediate Remediation:**

1. **Integrate zod-to-json-schema Correctly:**  
   * Remove the hardcoded dummy input\_schema logic from the ListToolsResponse handler.  
   * Implement the necessary code to utilize the zod-to-json-schema library.7 This involves iterating through the server's tool definitions (presumably stored as Zod schemas), passing each Zod schema to zodToJsonSchema(), and placing the resulting JSON Schema object into the input\_schema field for the corresponding tool in the response payload.  
2. **Verify Library Usage in CJS:**  
   * Pay close attention to how zod-to-json-schema is imported (require syntax) and configured within the CJS environment. Reference the library's documentation and potentially compare with the working ESM server's implementation (adapting for CJS syntax).  
   * Ensure the version of zod-to-json-schema used is compatible with the project's Zod version.7 Check for any specific configuration options 7 that might be necessary or beneficial (e.g., name, definitions).  
3. **Validate Generated Schemas:**  
   * After implementing the library, intercept or log the generated ListToolsResponse payload.  
   * Manually inspect the input\_schema for several representative tools. Verify that:  
     * The schema's type is "object".  
     * The properties field is present and accurately reflects the parameters defined in the corresponding Zod schema, including correct types and constraints.  
     * The required field (if applicable) correctly lists the mandatory parameters based on the Zod definition.  
     * The overall structure conforms to JSON Schema standards and MCP expectations.6

**Testing and Verification:**

1. **Incremental Schema Test (Optional but Recommended):** As a quick validation step *before* full zod-to-json-schema integration, modify the existing *dummy* schema logic slightly. For a single tool, manually add a simple, valid property definition to the properties object (e.g., "properties": { "testParam": { "type": "string" } }). Redeploy and test if the RooCode client now lists *at least that one tool*. A positive result would rapidly confirm the client's sensitivity to the presence of content within properties.  
2. **End-to-End Test:** Once zod-to-json-schema is fully implemented and schemas are validated, perform an end-to-end test using the RooCode client. Confirm that the "No tools found" error (INT-001) is resolved and the client correctly lists the tools provided by the server.  
3. **Tool Invocation Test:** Beyond just listing, verify that the client can successfully invoke one or more tools. Successful invocation implicitly confirms that the generated schema provided sufficient information for the client and/or LLM to construct a valid tools/call request.

**Further Investigation (If Necessary):**

1. **Client-Side Logging:** If INT-001 persists even after providing complete and valid schemas, investigate options for accessing more detailed logs from the RooCode client itself. Look for specific errors related to JSON schema parsing, validation failures, or tool filtering logic. (Note: Public information on RooCode's internal diagnostics may be limited 4).  
2. **SDK Upgrade Consideration:** Evaluate upgrading the @modelcontextprotocol/sdk to version 1.9.0 or later. While unlikely to fix INT-001 directly, this would incorporate general bug fixes, including the CJS-related pkce dependency fix 19, potentially improving overall stability in the CJS environment.  
3. **Address zod-to-json-schema Issues:** If difficulties arise during the implementation of zod-to-json-schema (e.g., errors during generation, incorrect output specifically in CJS), consult the library's known issues 7 and changelog. If a new issue is suspected, report it to the library maintainers with detailed information about the CJS context, Zod version, and specific Zod schemas causing problems.

#### **Works cited**

1. modelcontextprotocol/sdk \- NPM, accessed April 14, 2025, [https://www.npmjs.com/package/@modelcontextprotocol/sdk](https://www.npmjs.com/package/@modelcontextprotocol/sdk)  
2. @modelcontextprotocol/sdk (1.8.0) \- npm Package Quality | Cloudsmith Navigator, accessed April 14, 2025, [https://cloudsmith.com/navigator/npm/@modelcontextprotocol/sdk](https://cloudsmith.com/navigator/npm/@modelcontextprotocol/sdk)  
3. Documentation \- Zod, accessed April 14, 2025, [https://zod.dev/?id=gold](https://zod.dev/?id=gold)  
4. RooVetGit/Roo-Code: Roo Code (prev. Roo Cline) gives ... \- GitHub, accessed April 14, 2025, [https://github.com/RooVetGit/Roo-Code](https://github.com/RooVetGit/Roo-Code)  
5. Bybit Server | Glama, accessed April 14, 2025, [https://glama.ai/mcp/servers/@dlwjdtn535/mcp-bybit-server](https://glama.ai/mcp/servers/@dlwjdtn535/mcp-bybit-server)  
6. Specification \- Model Context Protocol, accessed April 14, 2025, [https://spec.modelcontextprotocol.io/specification/2025-03-26/](https://spec.modelcontextprotocol.io/specification/2025-03-26/)  
7. StefanTerdell/zod-to-json-schema: Converts Zod schemas ... \- GitHub, accessed April 14, 2025, [https://github.com/StefanTerdell/zod-to-json-schema](https://github.com/StefanTerdell/zod-to-json-schema)  
8. zod-to-json-schema \- NPM, accessed April 14, 2025, [https://www.npmjs.com/package/zod-to-json-schema](https://www.npmjs.com/package/zod-to-json-schema)  
9. Model Context Protocol (MCP) an overview \- Philschmid, accessed April 14, 2025, [https://www.philschmid.de/mcp-introduction](https://www.philschmid.de/mcp-introduction)  
10. model-context-protocol-resources/guides/mcp-client-development ..., accessed April 14, 2025, [https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-client-development-guide.md](https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-client-development-guide.md)  
11. Model Context Protocol (MCP): A comprehensive introduction for developers \- Stytch, accessed April 14, 2025, [https://stytch.com/blog/model-context-protocol-introduction/](https://stytch.com/blog/model-context-protocol-introduction/)  
12. Model Context Protocol Integration — AgentIQ \- NVIDIA Docs Hub, accessed April 14, 2025, [https://docs.nvidia.com/agentiq/1.0.0/components/mcp.html](https://docs.nvidia.com/agentiq/1.0.0/components/mcp.html)  
13. transitive-bullshit/openai-zod-to-json-schema \- GitHub, accessed April 14, 2025, [https://github.com/transitive-bullshit/openai-zod-to-json-schema](https://github.com/transitive-bullshit/openai-zod-to-json-schema)  
14. Issues · StefanTerdell/zod-to-json-schema \- GitHub, accessed April 14, 2025, [https://github.com/StefanTerdell/zod-to-json-schema/issues](https://github.com/StefanTerdell/zod-to-json-schema/issues)  
15. zod-to-json-schema/postcjs.ts at master \- GitHub, accessed April 14, 2025, [https://github.com/StefanTerdell/zod-to-json-schema/blob/master/postcjs.ts](https://github.com/StefanTerdell/zod-to-json-schema/blob/master/postcjs.ts)  
16. Understanding CommonJS vs. ES Modules in JavaScript \- Syncfusion, accessed April 14, 2025, [https://www.syncfusion.com/blogs/post/js-commonjs-vs-es-modules](https://www.syncfusion.com/blogs/post/js-commonjs-vs-es-modules)  
17. \[DISCUSSION\] Module resolution: ESM vs CJS · Issue \#700 · kelektiv/node-cron \- GitHub, accessed April 14, 2025, [https://github.com/kelektiv/node-cron/issues/700](https://github.com/kelektiv/node-cron/issues/700)  
18. @modelcontextprotocol \- npm search, accessed April 14, 2025, [https://npmjs.com/search?q=%40modelcontextprotocol](https://npmjs.com/search?q=@modelcontextprotocol)  
19. MCP official typescript-sdk 1.9.0 released : r/modelcontextprotocol \- Reddit, accessed April 14, 2025, [https://www.reddit.com/r/modelcontextprotocol/comments/1ju0ly7/mcp\_official\_typescriptsdk\_190\_released/](https://www.reddit.com/r/modelcontextprotocol/comments/1ju0ly7/mcp_official_typescriptsdk_190_released/)  
20. modelcontextprotocol/typescript-sdk: The official Typescript ... \- GitHub, accessed April 14, 2025, [https://github.com/modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)  
21. Rolling (up) a multi module system (esm, cjs...) compatible npm library with TypeScript and Babel \- DEV Community, accessed April 14, 2025, [https://dev.to/remshams/rolling-up-a-multi-module-system-esm-cjs-compatible-npm-library-with-typescript-and-babel-3gjg](https://dev.to/remshams/rolling-up-a-multi-module-system-esm-cjs-compatible-npm-library-with-typescript-and-babel-3gjg)  
22. Not able to use CJS(commons) npm package in ESM(type=module) project \- Stack Overflow, accessed April 14, 2025, [https://stackoverflow.com/questions/78640760/not-able-to-use-cjscommons-npm-package-in-esmtype-module-project](https://stackoverflow.com/questions/78640760/not-able-to-use-cjscommons-npm-package-in-esmtype-module-project)  
23. Are there any compatiblity issues with using CJS and ESM modules? \- Stack Overflow, accessed April 14, 2025, [https://stackoverflow.com/questions/67716004/are-there-any-compatiblity-issues-with-using-cjs-and-esm-modules](https://stackoverflow.com/questions/67716004/are-there-any-compatiblity-issues-with-using-cjs-and-esm-modules)  
24. Why does the Node API docs still use CJS? Isn't ESM the way forward? \- Reddit, accessed April 14, 2025, [https://www.reddit.com/r/node/comments/1fvbrps/why\_does\_the\_node\_api\_docs\_still\_use\_cjs\_isnt\_esm/](https://www.reddit.com/r/node/comments/1fvbrps/why_does_the_node_api_docs_still_use_cjs_isnt_esm/)