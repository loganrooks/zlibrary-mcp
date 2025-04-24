#!/usr/bin/env node

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const mcpTypes = require('@modelcontextprotocol/sdk/types.js');
const z = require('zod');
const zodToJsonSchema = require('zod-to-json-schema').default; // Using .default as confirmed necessary

// --- Minimal Server Setup ---

// Define schema for the echo tool
const EchoParamsSchema = z.object({
  message: z.string().describe('The message to echo back'),
});

// Create the server instance
const server = new Server(
  {
    name: "minimal-test-server",
    version: "0.0.1",
    description: "A minimal MCP server for testing tool listing",
  },
  {
    capabilities: {
      tools: {}, // Enable tools capability
      resources: {}, // Add empty resources capability
      prompts: {},   // Add empty prompts capability
    },
  },
);

// --- Request Handlers ---

// ListTools handler
server.setRequestHandler(mcpTypes.ListToolsRequestSchema, async () => {
  // console.error('[Minimal Server] Received ListToolsRequest'); // REMOVED LOG
  try {
    const tools = [
      {
        name: "echo",
        description: "Echoes back the provided message.",
        // Generate schema directly, let errors propagate
        input_schema: zodToJsonSchema(EchoParamsSchema),
      },
    ];
    // console.error('[Minimal Server] Sending tools:', JSON.stringify(tools)); // REMOVED LOG
    return { tools };
  } catch (error) {
    // console.error('[Minimal Server] Error generating schema:', error); // REMOVED LOG
    // Return empty list on error for this test
    return { tools: [] };
  }
});

// CallTool handler
server.setRequestHandler(mcpTypes.CallToolRequestSchema, async (request) => {
  // console.error('[Minimal Server] Received CallToolRequest:', JSON.stringify(request.params)); // REMOVED LOG
  const { tool_name, arguments: args } = request.params;

  if (tool_name === 'echo') {
    const validationResult = EchoParamsSchema.safeParse(args);
    if (!validationResult.success) {
      const errorDetails = validationResult.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join('; ');
      // console.error('[Minimal Server] Invalid arguments:', errorDetails); // REMOVED LOG
      return { error: { message: `Invalid arguments: ${errorDetails}` } };
    }
    const result = { content: [{ type: "text", text: `Echo: ${validationResult.data.message}` }] };
    // console.error('[Minimal Server] Sending result:', JSON.stringify(result)); // REMOVED LOG
    return result;
  } else {
    // console.error('[Minimal Server] Unknown tool:', tool_name); // REMOVED LOG
    return { error: { message: `Unknown tool: ${tool_name}` } };
  }
});

// ListResources handler (required by SDK >= 1.8.0 even if empty)
server.setRequestHandler(mcpTypes.ListResourcesRequestSchema, async () => {
  // console.error('[Minimal Server] Received ListResourcesRequest'); // REMOVED LOG
  return { resources: [] };
});

// ListPrompts handler (required by SDK >= 1.8.0 even if empty)
server.setRequestHandler(mcpTypes.ListPromptsRequestSchema, async () => {
  // console.error('[Minimal Server] Received ListPromptsRequest'); // REMOVED LOG
  return { prompts: [] };
});


// --- Start Server ---
async function start() {
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    // console.error('[Minimal Server] Minimal MCP server is running via Stdio...'); // REMOVED LOG
  } catch (error) {
    // console.error('[Minimal Server] Failed to start:', error); // REMOVED LOG - Errors should still go to stderr implicitly
    process.exit(1);
  }
}

start();