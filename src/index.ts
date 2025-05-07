#!/usr/bin/env node

import { z, ZodObject, ZodRawShape } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema'; // Reverted back to named import (correct for types)
import { ensureVenvReady } from './lib/venv-manager.js'; // Use .js extension
import * as fs from 'fs'; // For sync operations if any
import { appendFile as appendFileAsync, mkdir as mkdirAsync } from 'fs/promises'; // For async file logging
import * as path from 'path';
import { fileURLToPath } from 'url';

// Import SDK components using ESM syntax
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
// Import types using 'import type' for clarity
import type {
    CallToolRequest,
    ListToolsRequest,
    ListResourcesRequest,
    ListPromptsRequest,
    // ServerInfo, // Likely not exported or needed
    // ToolDefinition, // Define locally based on usage
    ServerResult // This type might be complex or different in 1.8.0, use 'any' for now if needed
    // AnyZodObject // This comes from zod, not the SDK
} from '@modelcontextprotocol/sdk/types.js';
// Import schemas directly if they are exported as values
import {
    ListToolsRequestSchema,
    CallToolRequestSchema,
    ListResourcesRequestSchema,
    ListPromptsRequestSchema
} from '@modelcontextprotocol/sdk/types.js';


// Import API handlers
import * as zlibraryApi from './lib/zlibrary-api.js'; // Use .js extension

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Define Zod schemas for tool parameters
const SearchBooksParamsSchema = z.object({
  query: z.string().describe('Search query'),
  exact: z.boolean().optional().default(false).describe('Whether to perform an exact match search'),
  fromYear: z.number().int().optional().describe('Filter by minimum publication year'),
  toYear: z.number().int().optional().describe('Filter by maximum publication year'),
  languages: z.array(z.string()).optional().default([]).describe('Filter by languages (e.g., ["english", "russian"])'),
  extensions: z.array(z.string()).optional().default([]).describe('Filter by file extensions (e.g., ["pdf", "epub"])'),
  content_types: z.array(z.string()).optional().default([]).describe('Filter by content types (e.g., ["book", "article"])'),
  count: z.number().int().optional().default(10).describe('Number of results to return per page'),
});

const FullTextSearchParamsSchema = z.object({
  query: z.string().describe('Text to search for in book content'),
  exact: z.boolean().optional().default(false).describe('Whether to perform an exact match search'),
  phrase: z.boolean().optional().default(true).describe('Whether to search for the exact phrase (requires at least 2 words)'),
  words: z.boolean().optional().default(false).describe('Whether to search for individual words'),
  languages: z.array(z.string()).optional().default([]).describe('Filter by languages (e.g., ["english", "russian"])'),
  extensions: z.array(z.string()).optional().default([]).describe('Filter by file extensions (e.g., ["pdf", "epub"])'),
  content_types: z.array(z.string()).optional().default([]).describe('Filter by content types (e.g., ["book", "article"])'),
  count: z.number().int().optional().default(10).describe('Number of results to return per page'),
});

const GetDownloadHistoryParamsSchema = z.object({
  count: z.number().int().optional().default(10).describe('Number of results to return'),
});

const GetDownloadLimitsParamsSchema = z.object({}); // No parameters

const GetRecentBooksParamsSchema = z.object({
  count: z.number().int().optional().default(10).describe('Number of books to return'),
  format: z.string().optional().describe('Filter by file format (e.g., "pdf", "epub")'),
});

const DownloadBookToFileParamsSchema = z.object({
  // id: z.string().describe('Z-Library book ID'), // Replaced by bookDetails
  // format: z.string().optional().describe('File format (e.g., "pdf", "epub")'), // Replaced by bookDetails
  bookDetails: z.object({}).passthrough().describe('The full book details object obtained from search_books'), // Changed from z.record to z.object().passthrough()
  outputDir: z.string().optional().default('./downloads').describe('Directory to save the file to (default: "./downloads")'),
  process_for_rag: z.boolean().optional().describe('Whether to process the document content for RAG after download'),
  processed_output_format: z.string().optional().describe('Desired output format for RAG processing (e.g., "text", "markdown")'), // Removed duplicate line
});

const ProcessDocumentForRagParamsSchema = z.object({
  file_path: z.string().describe('Path to the downloaded file to process'),
  output_format: z.string().optional().describe('Desired output format (e.g., "text", "markdown")') // Re-applying again: Ensure it's purely optional, no default
});

// Define a type for the handler map
type HandlerMap = {
    [key: string]: (args: any) => Promise<any>;
};

// Tool handler implementations
// Add explicit types for arguments where possible, or use 'any'
const handlers: HandlerMap = {
  searchBooks: async (args: z.infer<typeof SearchBooksParamsSchema>) => {
    try {
      const searchBooksReceivedArgsLog = `[${new Date().toISOString()}] [src/index.ts] searchBooks handler received Zod-parsed args: ${JSON.stringify(args)}\n`;
      console.log(searchBooksReceivedArgsLog.trim());
      try {
        const logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
        await mkdirAsync(path.dirname(logFilePath), { recursive: true });
        await appendFileAsync(logFilePath, searchBooksReceivedArgsLog);
      } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
      // Explicitly construct the object for zlibraryApi.searchBooks
      // to ensure keys match what zlibraryApi.searchBooks expects.
      // Zod schema uses 'language' (singular) and 'content_types' (plural).
      // zlibraryApi.searchBooks destructures 'language' (singular) and 'content_types' (plural).
      const apiArgs = {
        query: args.query,
        exact: args.exact,
        fromYear: args.fromYear,
        toYear: args.toYear,
        languages: args.languages,
        extensions: args.extensions,
        content_types: args.content_types, // content_types is already plural in Zod
        count: args.count,
      };
      const searchBooksSendingLog = `[${new Date().toISOString()}] [src/index.ts] searchBooks handler sending to zlibraryApi: ${JSON.stringify(apiArgs)}\n`;
      console.log(searchBooksSendingLog.trim());
      try {
        // Directory creation already handled above for this function scope
        const logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
        // Directory creation already handled above for this function scope by the first logging block
        await appendFileAsync(logFilePath, searchBooksSendingLog);
      } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
      return await zlibraryApi.searchBooks(apiArgs);
    } catch (error: any) { return { error: { message: error.message || 'Failed to search books' } }; }
  },

  fullTextSearch: async (args: z.infer<typeof FullTextSearchParamsSchema>) => {
    try {
      const ftsReceivedArgsLog = `[${new Date().toISOString()}] [src/index.ts] fullTextSearch handler received Zod-parsed args: ${JSON.stringify(args)}\n`;
      console.log(ftsReceivedArgsLog.trim());
      try {
        const logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
        await mkdirAsync(path.dirname(logFilePath), { recursive: true });
        await appendFileAsync(logFilePath, ftsReceivedArgsLog);
      } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
      // Explicitly construct the object for zlibraryApi.fullTextSearch
      const apiArgsFTS = {
        query: args.query,
        exact: args.exact,
        phrase: args.phrase,
        words: args.words,
        languages: args.languages,
        extensions: args.extensions,
        content_types: args.content_types, // content_types is already plural in Zod
        count: args.count,
      };
      const ftsSendingLog = `[${new Date().toISOString()}] [src/index.ts] fullTextSearch handler sending to zlibraryApi: ${JSON.stringify(apiArgsFTS)}\n`;
      console.log(ftsSendingLog.trim());
      try {
        // Directory creation already handled above for this function scope
        const logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
        // Directory creation already handled above for this function scope by the first logging block
        await appendFileAsync(logFilePath, ftsSendingLog);
      } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
      return await zlibraryApi.fullTextSearch(apiArgsFTS);
    } catch (error: any) { return { error: { message: error.message || 'Failed to perform full text search' } }; }
  },

  getDownloadHistory: async (args: z.infer<typeof GetDownloadHistoryParamsSchema>) => {
    try {
        // Return the result directly
        return await zlibraryApi.getDownloadHistory(args);
    }
    catch (error: any) { return { error: { message: error.message || 'Failed to get download history' } }; }
  },

  getDownloadLimits: async () => { // No args expected
    try {
        // Return the result directly
        return await zlibraryApi.getDownloadLimits();
    }
    catch (error: any) { return { error: { message: error.message || 'Failed to get download limits' } }; }
  },

  downloadBookToFile: async (args: z.infer<typeof DownloadBookToFileParamsSchema>) => {
    try {
      // Pass all args directly
      // Return the result directly
      return await zlibraryApi.downloadBookToFile(args);
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to download book' } };
    }
  },

  processDocumentForRag: async (args: z.infer<typeof ProcessDocumentForRagParamsSchema>) => {
    try {
      // Pass args object directly
      // Map snake_case arg from request to camelCase expected by function
      // Return the result directly
      return await zlibraryApi.processDocumentForRag({ filePath: args.file_path, outputFormat: args.output_format });
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to process document for RAG' } };
    }
  }
};

// Define a type for the tool registry entries
// Define ToolDefinition based on usage in ListTools response
interface ToolDefinition {
    name: string;
    description?: string;
    inputSchema: any; // Use camelCase to match returned object and likely spec
}

interface ToolRegistryEntry {
    description: string;
    schema: ZodObject<ZodRawShape>; // Use ZodObject<any> or a more specific shape if possible
    handler?: (args: any) => Promise<any>; // Make handler optional in type definition
}

// Tool Registry
const toolRegistry: Record<string, ToolRegistryEntry> = {
  search_books: {
    description: 'Search for books in Z-Library',
    schema: SearchBooksParamsSchema,
    handler: handlers.searchBooks,
  },
  full_text_search: {
    description: 'Search for books containing specific text in their content',
    schema: FullTextSearchParamsSchema,
    handler: handlers.fullTextSearch,
  },
  get_download_history: {
    description: "Get user's book download history",
    schema: GetDownloadHistoryParamsSchema,
    handler: handlers.getDownloadHistory,
  },
  get_download_limits: {
    description: "Get user's current download limits",
    schema: GetDownloadLimitsParamsSchema,
    handler: handlers.getDownloadLimits,
  },
  download_book_to_file: {
    description: 'Download a book directly to a local file and optionally process it for RAG',
    schema: DownloadBookToFileParamsSchema,
    handler: handlers.downloadBookToFile,
  },
  process_document_for_rag: {
    description: 'Process a downloaded document (EPUB, TXT, PDF) to extract text content for RAG',
    schema: ProcessDocumentForRagParamsSchema,
    handler: handlers.processDocumentForRag,
  },
};

// Helper function to get version from package.json
function getPackageVersion(): string {
  try {
    // Use import.meta.url to find package.json relative to the current module
    const packageJsonPath = path.resolve(__dirname, '..', 'package.json'); // Go up one level from src/lib
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    return packageJson.version || 'unknown';
  } catch (error: any) {
    console.warn('Could not read package.json for version:', error.message);
    return 'unknown';
  }
}

interface StartOptions {
    testing?: boolean;
}

// Function to generate the tools capability object
function generateToolsCapability(): Record<string, ToolDefinition> {
    const toolsCapability: Record<string, ToolDefinition> = {};
    for (const [name, tool] of Object.entries(toolRegistry)) {
        try {
            const jsonSchema = zodToJsonSchema(tool.schema);
            toolsCapability[name] = {
                name: name,
                description: tool.description,
                inputSchema: jsonSchema, // Use camelCase
            };
        } catch (error: any) {
             console.error(`Failed to generate JSON schema for tool "${name}": ${error.message}`);
             // Optionally skip adding the tool if schema generation fails
        }
    }
    return toolsCapability;
}


async function start(opts: StartOptions = {}): Promise<{ server: Server; transport: StdioServerTransport } | null> {
    // --- RAW INPUT LOGGING REMOVED ---
  try {
    // Ensure the logs directory exists
    try {
      await mkdirAsync(path.resolve(__dirname, '..', 'logs'), { recursive: true });
      console.log("Log directory 'logs/' ensured.");
    } catch (dirError: any) {
      console.error("Failed to create 'logs/' directory:", dirError.message);
      // Decide if this is fatal or if we can continue without file logging
    }

    // Ensure the Python virtual environment is ready
    await ensureVenvReady();

    // Generate the tools capability object BEFORE creating the server
    const toolsCapabilityObject = generateToolsCapability();

    // Instantiate the Server class
    const server = new Server(
      { // ServerInfo
        name: "zlibrary-mcp",
        description: "Z-Library access for AI assistants",
        version: getPackageVersion()
      },
      { // ServerOptions - Pass the generated tools object
        capabilities: {
          tools: toolsCapabilityObject, // Pass the generated object
          resources: {},
          prompts: {}
        }
      }
    );

    // Enable tools capability - This is done via constructor now

    // Implement tools/list handler
    // Use the locally defined ToolDefinition type
    server.setRequestHandler(ListToolsRequestSchema, async (request: ListToolsRequest): Promise<{ tools: ToolDefinition[] }> => {
      console.log('Received tools/list request'); // Use console.log for info
      // The tools are already defined in the capability object, just return them
      const tools = Object.values(toolsCapabilityObject); // Get values from the pre-generated object
      console.log(`Responding to tools/list with ${tools.length} tools.`);
      return { tools };
    });

    // Implement tools/call handler
    server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest): Promise<ServerResult> => {
      console.log(`Received tools/call request for: ${request.params.tool_name}`); // Reverted log
      const { name: toolName, arguments: args } = request.params; // Use 'name' again, matching fetcher-mcp
      // Ensure toolName is a string before indexing
      if (typeof toolName !== 'string') { // Check toolName type
          console.error(`Invalid tool name type: ${typeof toolName}`); // Log toolName type
          return { content: [{ type: 'text', text: `Error: Invalid tool name type.` }], isError: true };
      }
      const tool = toolRegistry[toolName]; // Use toolName for lookup

      if (!tool) {
        console.error(`Tool "${toolName}" not found.`); // Use toolName in error
        // Return error in the format { content: [...], isError: true }
        return { content: [{ type: 'text', text: `Error: Tool "${toolName}" not found.` }], isError: true }; // Use toolName in error
      }

      // Validate arguments using Zod schema
      const validationResult = tool.schema.safeParse(args);

      if (!validationResult.success) {
        const errorDetails = validationResult.error.errors.map(e => `${e.path.join('.')}: ${e.message}`).join('; ');
        console.error(`Invalid arguments for tool "${toolName}": ${errorDetails}`); // Use toolName in error
        // Return error in the format { content: [...], isError: true }
        return { content: [{ type: 'text', text: `Error: Invalid arguments for tool "${toolName}": ${errorDetails}` }], isError: true }; // Use toolName in error
      }

      // Add check to ensure handler exists before calling
      if (!tool.handler) {
          console.error(`Handler for tool "${toolName}" is not defined.`); // Use toolName in error
          return { content: [{ type: 'text', text: `Error: Handler not implemented for tool "${toolName}".` }], isError: true }; // Use toolName in error
      }

      // Add check to ensure handler exists before calling - REMOVED DUPLICATE CHECK

      try {
        // Call the actual tool handler with validated arguments
        console.log(`Calling handler for tool "${toolName}"`); // Use toolName in log
        const result = await tool.handler(validationResult.data);

        // Check if the handler returned an error object itself
        if (result && typeof result === 'object' && 'error' in result && result.error) {
           console.error(`Handler for tool "${toolName}" returned error:`, result.error.message || result.error); // Use toolName in error
           // Return error in the format { content: [...], isError: true }
           return { content: [{ type: 'text', text: `Error from tool "${toolName}": ${result.error.message || result.error}` }], isError: true }; // Use toolName in error
        }
        console.log(`Handler for tool "${toolName}" completed successfully.`); // Use toolName in log
        // Return the actual result object directly, assuming SDK handles wrapping
        // Wrap the successful result to ensure 'content' is always an array
        // matching the structure expected by the client (based on ZodError)
        // Note: Stringifying the result prevents ZodError but might require client-side parsing.
        const stringifiedResult = JSON.stringify(result);
        return { content: [{ type: 'text', text: stringifiedResult }] };
      } catch (error: any) {
        // Catch errors thrown by the handler
        console.error(`Error calling tool "${toolName}":`, error); // Use toolName in error
        // Return error in the format { content: [...], isError: true }
        return { content: [{ type: 'text', text: `Error calling tool "${toolName}": ${error.message || 'Unknown error'}` }], isError: true }; // Use toolName in error
      }
    });

     // Add handlers for resources/list and prompts/list (required by SDK >= 1.8.0)
    server.setRequestHandler(ListResourcesRequestSchema, async (request: ListResourcesRequest) => {
        console.log('Received resources/list request');
        return { resources: [] }; // Return empty list
    });

    server.setRequestHandler(ListPromptsRequestSchema, async (request: ListPromptsRequest) => {
        console.log('Received prompts/list request');
        return { prompts: [] }; // Return empty list
    });


    // Create and connect the Stdio transport
    const transport = new StdioServerTransport();

    // --- RAW INPUT LOGGING REMOVED FROM HERE ---
    await server.connect(transport);
    console.log('Z-Library MCP server (ESM/TS) is running via Stdio...'); // Use console.log

    return { server, transport };
  } catch (error: any) {
    console.error('Failed to start MCP server:', error);

    // Allow tests to bypass process.exit
    if (opts.testing !== true) {
      process.exit(1);
    }
    return null;
  }
}

// Auto-start logic needs adjustment for ESM
// Check if the current module URL is the main module URL
if (import.meta.url === `file://${process.argv[1]}`) {
  start().catch(err => {
    console.error("Fatal error starting server:", err);
    process.exit(1);
  });
}

// Export necessary components for potential testing
export { start, handlers, toolRegistry };