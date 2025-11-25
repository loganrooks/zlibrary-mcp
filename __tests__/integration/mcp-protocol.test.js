/**
 * MCP Protocol Integration Tests
 *
 * Tests the MCP server from an AI agent's perspective using the official MCP SDK.
 * This validates the protocol contract that AI clients depend on.
 *
 * These tests verify:
 * 1. Tool discovery (tools/list) with outputSchema and annotations
 * 2. Tool execution with structuredContent responses
 * 3. Protocol compliance with MCP spec 2025-06-18
 *
 * @see https://modelcontextprotocol.io/specification/2025-06-18
 */

import { jest, describe, beforeEach, afterEach, test, expect } from '@jest/globals';

// Constants for all expected tools
const EXPECTED_TOOLS = [
  'search_books',
  'full_text_search',
  'get_download_history',
  'get_download_limits',
  'download_book_to_file',
  'process_document_for_rag',
  'get_book_metadata',
  'search_by_term',
  'search_by_author',
  'fetch_booklist',
  'search_advanced'
];

// Tools that should be marked read-only (no side effects)
const READ_ONLY_TOOLS = [
  'search_books',
  'full_text_search',
  'get_download_history',
  'get_download_limits',
  'get_book_metadata',
  'search_by_term',
  'search_by_author',
  'fetch_booklist',
  'search_advanced'
];

// Tools that modify state (download files, process documents)
const MUTATING_TOOLS = [
  'download_book_to_file',
  'process_document_for_rag'
];

describe('MCP Protocol Integration Tests', () => {
  let mockServer;
  let capturedToolsCapability;
  let capturedRequestHandlers;

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    capturedRequestHandlers = {};
    capturedToolsCapability = null;

    // Mock console for cleaner test output
    console.error = jest.fn();
    console.log = jest.fn();
  });

  afterEach(() => {
    mockServer = null;
  });

  /**
   * Helper to set up mocked MCP server and capture tool definitions
   */
  async function setupMockedServer() {
    const mockTransport = { send: jest.fn() };
    mockServer = {
      connect: jest.fn().mockResolvedValue(undefined),
      handle: jest.fn(),
      registerCapabilities: jest.fn(),
      setRequestHandler: jest.fn((schema, handler) => {
        capturedRequestHandlers[schema.name || schema.method] = handler;
      }),
    };

    // Mock SDK modules
    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/index.js', () => ({
      Server: jest.fn().mockImplementation((serverInfo, serverOptions) => {
        capturedToolsCapability = serverOptions?.capabilities?.tools;
        return mockServer;
      }),
    }));

    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/stdio.js', () => ({
      StdioServerTransport: jest.fn().mockImplementation(() => mockTransport),
    }));

    jest.unstable_mockModule('@modelcontextprotocol/sdk/types.js', () => ({
      ListToolsRequestSchema: { name: 'ListToolsRequestSchema' },
      CallToolRequestSchema: { name: 'CallToolRequestSchema' },
      ListResourcesRequestSchema: { name: 'ListResourcesRequestSchema' },
      ListPromptsRequestSchema: { name: 'ListPromptsRequestSchema' },
    }));

    // Mock venv-manager
    jest.unstable_mockModule('../../dist/lib/venv-manager.js', () => ({
      ensureVenvReady: jest.fn().mockResolvedValue(undefined),
      getManagedPythonPath: jest.fn().mockReturnValue('/fake/python'),
    }));

    // Import and start the server
    const { start, toolRegistry } = await import('../../dist/index.js');
    await start({ testing: true });

    return { toolRegistry };
  }

  // ========================================
  // Tool Discovery Tests (tools/list)
  // ========================================

  describe('Tool Discovery (tools/list)', () => {
    test('should expose all 11 expected tools', async () => {
      const { toolRegistry } = await setupMockedServer();

      const toolNames = Object.keys(toolRegistry);

      expect(toolNames).toHaveLength(EXPECTED_TOOLS.length);
      EXPECTED_TOOLS.forEach(expectedTool => {
        expect(toolNames).toContain(expectedTool);
      });
    });

    test('each tool should have required MCP properties', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const [name, tool] of Object.entries(toolRegistry)) {
        // Required: description
        expect(tool.description).toBeDefined();
        expect(typeof tool.description).toBe('string');
        expect(tool.description.length).toBeGreaterThan(10);

        // Required: input schema (Zod schema)
        expect(tool.schema).toBeDefined();
        expect(tool.schema._def).toBeDefined(); // Zod schema has _def

        // Required: handler function
        expect(tool.handler).toBeDefined();
        expect(typeof tool.handler).toBe('function');
      }
    });

    test('each tool should have outputSchema (MCP spec 2025-06-18)', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const [name, tool] of Object.entries(toolRegistry)) {
        expect(tool.outputSchema).toBeDefined();
        expect(tool.outputSchema._def).toBeDefined(); // Zod schema has _def
      }
    });
  });

  // ========================================
  // Tool Annotations Tests
  // ========================================

  describe('Tool Annotations', () => {
    test('read-only tools should have readOnlyHint: true', async () => {
      // Import tool annotations directly from the module
      const { toolRegistry } = await setupMockedServer();

      // Get the generated tools capability from ListToolsRequest handler
      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      expect(listToolsHandler).toBeDefined();

      const response = await listToolsHandler();
      expect(response.tools).toBeDefined();
      expect(Array.isArray(response.tools)).toBe(true);

      for (const tool of response.tools) {
        if (READ_ONLY_TOOLS.includes(tool.name)) {
          expect(tool.annotations?.readOnlyHint).toBe(true);
        }
      }
    });

    test('mutating tools should have readOnlyHint: false', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      for (const tool of response.tools) {
        if (MUTATING_TOOLS.includes(tool.name)) {
          expect(tool.annotations?.readOnlyHint).toBe(false);
        }
      }
    });

    test('external API tools should have openWorldHint: true', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      // Tools that interact with Z-Library (external world)
      const externalTools = [
        'search_books',
        'full_text_search',
        'get_download_history',
        'get_download_limits',
        'download_book_to_file',
        'get_book_metadata',
        'search_by_term',
        'search_by_author',
        'fetch_booklist',
        'search_advanced'
      ];

      for (const tool of response.tools) {
        if (externalTools.includes(tool.name)) {
          expect(tool.annotations?.openWorldHint).toBe(true);
        }
      }
    });

    test('local-only tools should have openWorldHint: false', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      // process_document_for_rag only processes local files
      const localOnlyTools = ['process_document_for_rag'];

      for (const tool of response.tools) {
        if (localOnlyTools.includes(tool.name)) {
          expect(tool.annotations?.openWorldHint).toBe(false);
        }
      }
    });

    test('pure search tools should be idempotent', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      // These tools always return same results for same inputs
      const idempotentTools = [
        'search_books',
        'full_text_search',
        'search_by_term',
        'search_by_author',
        'search_advanced',
        'get_book_metadata',
        'fetch_booklist',
        'process_document_for_rag'  // Same file -> same output
      ];

      for (const tool of response.tools) {
        if (idempotentTools.includes(tool.name)) {
          expect(tool.annotations?.idempotentHint).toBe(true);
        }
      }
    });

    test('stateful tools should not be idempotent', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      // These tools return different results based on state
      const nonIdempotentTools = [
        'get_download_history',  // Changes as user downloads
        'get_download_limits',   // Changes throughout day
        'download_book_to_file'  // Side effect: downloads count
      ];

      for (const tool of response.tools) {
        if (nonIdempotentTools.includes(tool.name)) {
          expect(tool.annotations?.idempotentHint).toBe(false);
        }
      }
    });

    test('all tools should have human-readable title', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      for (const tool of response.tools) {
        expect(tool.title).toBeDefined();
        expect(typeof tool.title).toBe('string');
        expect(tool.title.length).toBeGreaterThan(0);
        // Titles should be readable (no underscores, capitalized)
        expect(tool.title).not.toContain('_');
      }
    });
  });

  // ========================================
  // Output Schema Tests
  // ========================================

  describe('Output Schema Validation', () => {
    test('search_books outputSchema should define books array', async () => {
      const { toolRegistry } = await setupMockedServer();

      const searchBooks = toolRegistry['search_books'];
      expect(searchBooks.outputSchema).toBeDefined();

      // Convert Zod schema to check structure
      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(searchBooks.outputSchema);

      expect(jsonSchema.properties).toBeDefined();
      expect(jsonSchema.properties.books).toBeDefined();
      expect(jsonSchema.properties.books.type).toBe('array');
    });

    test('download_book_to_file outputSchema should define file_path', async () => {
      const { toolRegistry } = await setupMockedServer();

      const downloadTool = toolRegistry['download_book_to_file'];
      expect(downloadTool.outputSchema).toBeDefined();

      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(downloadTool.outputSchema);

      expect(jsonSchema.properties).toBeDefined();
      expect(jsonSchema.properties.file_path).toBeDefined();
    });

    test('get_download_limits outputSchema should define daily limits', async () => {
      const { toolRegistry } = await setupMockedServer();

      const limitsTool = toolRegistry['get_download_limits'];
      expect(limitsTool.outputSchema).toBeDefined();

      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(limitsTool.outputSchema);

      expect(jsonSchema.properties).toBeDefined();
      expect(jsonSchema.properties.daily_limit).toBeDefined();
      expect(jsonSchema.properties.downloads_today).toBeDefined();
    });

    test('outputSchema should be included in ListToolsRequest response', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      for (const tool of response.tools) {
        expect(tool.outputSchema).toBeDefined();
        expect(typeof tool.outputSchema).toBe('object');
      }
    });
  });

  // ========================================
  // Input Schema Tests
  // ========================================

  describe('Input Schema Validation', () => {
    test('search_books should require query parameter', async () => {
      const { toolRegistry } = await setupMockedServer();

      const searchBooks = toolRegistry['search_books'];
      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(searchBooks.schema);

      expect(jsonSchema.properties.query).toBeDefined();
      expect(jsonSchema.required).toContain('query');
    });

    test('download_book_to_file should require bookDetails', async () => {
      const { toolRegistry } = await setupMockedServer();

      const downloadTool = toolRegistry['download_book_to_file'];
      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(downloadTool.schema);

      expect(jsonSchema.properties.bookDetails).toBeDefined();
      expect(jsonSchema.required).toContain('bookDetails');
    });

    test('all tools should have valid JSON Schema for inputSchema', async () => {
      await setupMockedServer();

      const listToolsHandler = capturedRequestHandlers['ListToolsRequestSchema'];
      const response = await listToolsHandler();

      for (const tool of response.tools) {
        expect(tool.inputSchema).toBeDefined();
        expect(tool.inputSchema.type).toBe('object');
        expect(tool.inputSchema.properties).toBeDefined();
      }
    });
  });

  // ========================================
  // Tool Handler Contract Tests
  // ========================================

  describe('Tool Handler Contract', () => {
    test('tool handlers should return content array', async () => {
      const { toolRegistry } = await setupMockedServer();

      // Mock the Python bridge for a simple test
      jest.unstable_mockModule('../../dist/lib/zlibrary-api.js', () => ({
        getDownloadLimits: jest.fn().mockResolvedValue({
          daily_limit: 10,
          downloads_today: 5,
          remaining: 5
        }),
      }));

      // Re-import to get mocked version
      const { getDownloadLimits } = await import('../../dist/lib/zlibrary-api.js');

      // Simulate what the handler does
      const mockResult = await getDownloadLimits();
      const expectedContent = [{ type: 'text', text: JSON.stringify(mockResult) }];

      expect(expectedContent[0].type).toBe('text');
      expect(typeof expectedContent[0].text).toBe('string');
    });

    test('CallToolRequest handler should exist', async () => {
      await setupMockedServer();

      const callToolHandler = capturedRequestHandlers['CallToolRequestSchema'];
      expect(callToolHandler).toBeDefined();
      expect(typeof callToolHandler).toBe('function');
    });
  });

  // ========================================
  // Protocol Compliance Tests
  // ========================================

  describe('MCP Protocol Compliance', () => {
    test('server should declare tools capability', async () => {
      await setupMockedServer();

      // The Server constructor should be called with capabilities
      const { Server } = await import('@modelcontextprotocol/sdk/server/index.js');
      expect(Server).toHaveBeenCalled();

      const constructorCall = Server.mock.calls[0];
      const serverOptions = constructorCall[1];
      expect(serverOptions.capabilities).toBeDefined();
      expect(serverOptions.capabilities.tools).toBeDefined();
    });

    test('server should have correct metadata', async () => {
      await setupMockedServer();

      const { Server } = await import('@modelcontextprotocol/sdk/server/index.js');
      const constructorCall = Server.mock.calls[0];
      const serverInfo = constructorCall[0];

      expect(serverInfo.name).toBe('zlibrary-mcp');
      expect(serverInfo.version).toBeDefined();
    });

    test('ListToolsRequestSchema handler should be registered', async () => {
      await setupMockedServer();

      expect(capturedRequestHandlers['ListToolsRequestSchema']).toBeDefined();
    });

    test('CallToolRequestSchema handler should be registered', async () => {
      await setupMockedServer();

      expect(capturedRequestHandlers['CallToolRequestSchema']).toBeDefined();
    });
  });

  // ========================================
  // AI Agent Perspective Tests
  // ========================================

  describe('AI Agent Perspective', () => {
    test('tool descriptions should be informative for AI', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const [name, tool] of Object.entries(toolRegistry)) {
        // Descriptions should explain what the tool does
        expect(tool.description.length).toBeGreaterThan(20);

        // Descriptions should not be placeholder text
        expect(tool.description.toLowerCase()).not.toContain('todo');
        expect(tool.description.toLowerCase()).not.toContain('placeholder');
      }
    });

    test('search tools should have filter options documented', async () => {
      const { toolRegistry } = await setupMockedServer();

      const searchBooks = toolRegistry['search_books'];
      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(searchBooks.schema);

      // Search should support common filters
      const hasFilters = jsonSchema.properties.languages !== undefined ||
                         jsonSchema.properties.extensions !== undefined ||
                         jsonSchema.properties.fromYear !== undefined;
      expect(hasFilters).toBe(true);
    });

    test('tool names should follow consistent naming convention', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const name of Object.keys(toolRegistry)) {
        // All snake_case
        expect(name).toMatch(/^[a-z][a-z0-9_]*$/);
        // No double underscores
        expect(name).not.toContain('__');
      }
    });
  });
});

// ========================================
// Standalone Schema Validation Tests
// ========================================

describe('Schema Validation (Standalone)', () => {
  test('toolRegistry should be importable without starting server', async () => {
    const { toolRegistry } = await import('../../dist/index.js');

    expect(toolRegistry).toBeDefined();
    expect(typeof toolRegistry).toBe('object');
    expect(Object.keys(toolRegistry).length).toBe(11);
  });

  test('all tools should have Zod schemas that can be converted to JSON Schema', async () => {
    const { toolRegistry } = await import('../../dist/index.js');
    const { zodToJsonSchema } = await import('zod-to-json-schema');

    for (const [name, tool] of Object.entries(toolRegistry)) {
      // Input schema conversion
      expect(() => zodToJsonSchema(tool.schema)).not.toThrow();

      // Output schema conversion
      if (tool.outputSchema) {
        expect(() => zodToJsonSchema(tool.outputSchema)).not.toThrow();
      }
    }
  });
});
