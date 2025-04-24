#!/usr/bin/env node

// Import SDK components using ESM syntax
// Note the different import path for McpServer in v1.0.x
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
// zod-to-json-schema might not be needed if server.tool handles it internally in v1.0.x
// We will omit it for this minimal test, as older examples didn't always use it explicitly
// import zodToJsonSchema from "zod-to-json-schema";

// --- Minimal Server Setup (ESM, SDK v1.0.4 style) ---

// Define schema for the echo tool
const EchoParamsSchema = z.object({
  message: z.string().describe('The message to echo back'),
});

// Create the server instance
// SDK v1.0.x uses McpServer and registers tools differently
const server = new McpServer({
  name: "minimal-esm-test-server",
  version: "0.0.1",
  description: "A minimal ESM MCP server for testing tool listing (SDK v1.0.4)",
  // Capabilities are often implicitly defined by registering tools/resources in v1.0.x
});

// --- Register Tool (SDK v1.0.x style) ---
// The .tool() method in v1.0.x likely handles schema conversion internally
server.tool(
  "echo", // Tool name
  EchoParamsSchema, // Zod schema for input
  async ({ message }) => { // Handler function
    // console.error('[Minimal ESM Server] Echo called with:', message); // Keep logs commented out
    return {
      content: [{ type: "text", text: `Echo: ${message}` }]
    };
  }
);

// --- Start Server ---
async function start() {
  try {
    const transport = new StdioServerTransport();
    // Connect method might differ slightly or might not be needed if transport handles it
    // Based on v1.0.x examples, often just transport.start() was used,
    // but server.connect(transport) is the pattern in later versions and might be backward compatible.
    // Let's try server.connect first.
    await server.connect(transport);
    // console.error('[Minimal ESM Server] Minimal MCP server (ESM, SDK v1.0.4) is running via Stdio...'); // Keep logs commented out
  } catch (error) {
    console.error('[Minimal ESM Server] Failed to start:', error); // Log critical start errors
    process.exit(1);
  }
}

start();

// Export might not be needed for a simple executable script
// export { server };