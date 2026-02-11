/**
 * MCP Protocol Integration Tests
 *
 * Tests the MCP server from an AI agent's perspective using the official MCP SDK.
 * This validates the protocol contract that AI clients depend on.
 *
 * These tests verify:
 * 1. Tool discovery via toolRegistry and McpServer.tool() registration
 * 2. Tool schema validation with outputSchema and annotations
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
  'get_recent_books',
  'download_book_to_file',
  'process_document_for_rag',
  'get_book_metadata',
  'search_by_term',
  'search_by_author',
  'fetch_booklist',
  'search_advanced',
  'search_multi_source'
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
  'search_advanced',
  'search_multi_source'
];

// Tools that modify state (download files, process documents)
const MUTATING_TOOLS = [
  'download_book_to_file',
  'process_document_for_rag'
];

describe('MCP Protocol Integration Tests', () => {
  let mockMcpServer;
  let registeredTools; // Map of tool name -> { description, shape, annotations, handler }

  beforeEach(() => {
    jest.resetModules();
    jest.clearAllMocks();
    registeredTools = {};
    mockMcpServer = null;

    // Mock console for cleaner test output
    console.error = jest.fn();
    console.log = jest.fn();
  });

  afterEach(() => {
    mockMcpServer = null;
  });

  /**
   * Helper to set up mocked MCP server and capture tool definitions
   */
  async function setupMockedServer() {
    const mockTransport = { send: jest.fn() };
    mockMcpServer = {
      connect: jest.fn().mockResolvedValue(undefined),
      tool: jest.fn((...args) => {
        // McpServer.tool(name, description, shape, annotations, handler)
        const name = args[0];
        const description = args[1];
        const shape = args[2];
        const annotations = args[3];
        const handler = args[4];
        registeredTools[name] = { description, shape, annotations, handler };
      }),
      close: jest.fn(),
    };

    // Mock SDK modules — McpServer from server/mcp.js
    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/mcp.js', () => ({
      McpServer: jest.fn().mockImplementation((serverInfo) => {
        mockMcpServer._serverInfo = serverInfo;
        return mockMcpServer;
      }),
    }));

    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/stdio.js', () => ({
      StdioServerTransport: jest.fn().mockImplementation(() => mockTransport),
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
    test('should expose all expected tools via toolRegistry', async () => {
      const { toolRegistry } = await setupMockedServer();

      const toolNames = Object.keys(toolRegistry);

      expect(toolNames).toHaveLength(EXPECTED_TOOLS.length);
      EXPECTED_TOOLS.forEach(expectedTool => {
        expect(toolNames).toContain(expectedTool);
      });
    });

    test('McpServer.tool() should be called for all tools (including get_recent_books)', async () => {
      await setupMockedServer();

      // 13 tools registered via server.tool()
      const registeredNames = Object.keys(registeredTools);
      expect(registeredNames.length).toBeGreaterThanOrEqual(13);

      EXPECTED_TOOLS.forEach(expectedTool => {
        expect(registeredNames).toContain(expectedTool);
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

        // Required: handler function (get_recent_books handler is only in McpServer, not toolRegistry)
        if (name !== 'get_recent_books') {
          expect(tool.handler).toBeDefined();
          expect(typeof tool.handler).toBe('function');
        }
      }
    });

    test('each tool should have description and schema', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const [name, tool] of Object.entries(toolRegistry)) {
        expect(tool.description).toBeDefined();
        expect(tool.schema).toBeDefined();
        expect(tool.schema._def).toBeDefined(); // Zod schema has _def
      }
    });
  });

  // ========================================
  // Tool Annotations Tests
  // ========================================

  describe('Tool Annotations', () => {
    test('read-only tools should have readOnlyHint: true', async () => {
      await setupMockedServer();

      for (const toolName of READ_ONLY_TOOLS) {
        const tool = registeredTools[toolName];
        expect(tool).toBeDefined();
        expect(tool.annotations?.readOnlyHint).toBe(true);
      }
    });

    test('mutating tools should have readOnlyHint: false', async () => {
      await setupMockedServer();

      for (const toolName of MUTATING_TOOLS) {
        const tool = registeredTools[toolName];
        expect(tool).toBeDefined();
        expect(tool.annotations?.readOnlyHint).toBe(false);
      }
    });

    test('external API tools should have openWorldHint: true', async () => {
      await setupMockedServer();

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
        'search_advanced',
        'search_multi_source'
      ];

      for (const toolName of externalTools) {
        const tool = registeredTools[toolName];
        expect(tool).toBeDefined();
        expect(tool.annotations?.openWorldHint).toBe(true);
      }
    });

    test('local-only tools should have openWorldHint: false', async () => {
      await setupMockedServer();

      const localOnlyTools = ['process_document_for_rag'];

      for (const toolName of localOnlyTools) {
        const tool = registeredTools[toolName];
        expect(tool).toBeDefined();
        expect(tool.annotations?.openWorldHint).toBe(false);
      }
    });

    test('pure search tools should be idempotent', async () => {
      await setupMockedServer();

      const idempotentTools = [
        'search_books',
        'full_text_search',
        'search_by_term',
        'search_by_author',
        'search_advanced',
        'search_multi_source',
        'get_book_metadata',
        'fetch_booklist',
        'process_document_for_rag'
      ];

      for (const toolName of idempotentTools) {
        const tool = registeredTools[toolName];
        expect(tool).toBeDefined();
        expect(tool.annotations?.idempotentHint).toBe(true);
      }
    });

    test('stateful tools should not be idempotent', async () => {
      await setupMockedServer();

      const nonIdempotentTools = [
        'get_download_history',
        'get_download_limits',
        'download_book_to_file'
      ];

      for (const toolName of nonIdempotentTools) {
        const tool = registeredTools[toolName];
        expect(tool).toBeDefined();
        expect(tool.annotations?.idempotentHint).toBe(false);
      }
    });

    test('all tools should have human-readable title', async () => {
      await setupMockedServer();

      for (const [name, tool] of Object.entries(registeredTools)) {
        expect(tool.annotations?.title).toBeDefined();
        expect(typeof tool.annotations.title).toBe('string');
        expect(tool.annotations.title.length).toBeGreaterThan(0);
        // Titles should be readable (no underscores)
        expect(tool.annotations.title).not.toContain('_');
      }
    });
  });

  // ========================================
  // Input/Output Schema Tests
  // ========================================

  describe('Schema Structure Validation', () => {
    test('search_books schema should define query property', async () => {
      const { toolRegistry } = await setupMockedServer();

      const searchBooks = toolRegistry['search_books'];
      expect(searchBooks.schema).toBeDefined();

      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(searchBooks.schema);

      expect(jsonSchema.properties).toBeDefined();
      expect(jsonSchema.properties.query).toBeDefined();
    });

    test('download_book_to_file schema should define bookDetails', async () => {
      const { toolRegistry } = await setupMockedServer();

      const downloadTool = toolRegistry['download_book_to_file'];
      expect(downloadTool.schema).toBeDefined();

      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(downloadTool.schema);

      expect(jsonSchema.properties).toBeDefined();
      expect(jsonSchema.properties.bookDetails).toBeDefined();
    });

    test('get_download_limits schema should be a valid object schema', async () => {
      const { toolRegistry } = await setupMockedServer();

      const limitsTool = toolRegistry['get_download_limits'];
      expect(limitsTool.schema).toBeDefined();

      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(limitsTool.schema);

      expect(jsonSchema.type).toBe('object');
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

    test('all tools should have valid Zod schemas convertible to JSON Schema', async () => {
      const { toolRegistry } = await setupMockedServer();
      const { zodToJsonSchema } = await import('zod-to-json-schema');

      for (const [name, tool] of Object.entries(toolRegistry)) {
        const jsonSchema = zodToJsonSchema(tool.schema);
        expect(jsonSchema.type).toBe('object');
        expect(jsonSchema.properties).toBeDefined();
      }
    });
  });

  // ========================================
  // Tool Handler Contract Tests
  // ========================================

  describe('Tool Handler Contract', () => {
    test('all toolRegistry entries should have callable handlers', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const [name, tool] of Object.entries(toolRegistry)) {
        if (tool.handler) {
          expect(typeof tool.handler).toBe('function');
        }
      }
    });

    test('McpServer.tool() should receive handler functions', async () => {
      await setupMockedServer();

      for (const [name, tool] of Object.entries(registeredTools)) {
        expect(typeof tool.handler).toBe('function');
      }
    });
  });

  // ========================================
  // Protocol Compliance Tests
  // ========================================

  describe('MCP Protocol Compliance', () => {
    test('McpServer should be instantiated with correct metadata', async () => {
      await setupMockedServer();

      const { McpServer } = await import('@modelcontextprotocol/sdk/server/mcp.js');
      expect(McpServer).toHaveBeenCalled();

      // McpServer takes { name, version } as single arg
      expect(mockMcpServer._serverInfo).toEqual({
        name: 'zlibrary-mcp',
        version: expect.any(String),
      });
    });

    test('server should connect to transport', async () => {
      await setupMockedServer();

      expect(mockMcpServer.connect).toHaveBeenCalled();
    });

    test('all tools should be registered via server.tool()', async () => {
      await setupMockedServer();

      // Each tool call: server.tool(name, description, shape, annotations, handler)
      for (const call of mockMcpServer.tool.mock.calls) {
        expect(typeof call[0]).toBe('string'); // name
        expect(typeof call[1]).toBe('string'); // description
        expect(typeof call[2]).toBe('object'); // shape (ZodRawShape)
        expect(typeof call[3]).toBe('object'); // annotations
        expect(typeof call[4]).toBe('function'); // handler
      }
    });
  });

  // ========================================
  // AI Agent Perspective Tests
  // ========================================

  describe('AI Agent Perspective', () => {
    test('tool descriptions should be informative for AI', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const [name, tool] of Object.entries(toolRegistry)) {
        expect(tool.description.length).toBeGreaterThanOrEqual(10);
        expect(tool.description.toLowerCase()).not.toContain('todo');
        expect(tool.description.toLowerCase()).not.toContain('placeholder');
      }
    });

    test('search tools should have filter options documented', async () => {
      const { toolRegistry } = await setupMockedServer();

      const searchBooks = toolRegistry['search_books'];
      const { zodToJsonSchema } = await import('zod-to-json-schema');
      const jsonSchema = zodToJsonSchema(searchBooks.schema);

      const hasFilters = jsonSchema.properties.languages !== undefined ||
                         jsonSchema.properties.extensions !== undefined ||
                         jsonSchema.properties.fromYear !== undefined;
      expect(hasFilters).toBe(true);
    });

    test('tool names should follow consistent naming convention', async () => {
      const { toolRegistry } = await setupMockedServer();

      for (const name of Object.keys(toolRegistry)) {
        expect(name).toMatch(/^[a-z][a-z0-9_]*$/);
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
    expect(Object.keys(toolRegistry).length).toBe(13);
  });

  test('all tools should have Zod schemas that can be converted to JSON Schema', async () => {
    const { toolRegistry } = await import('../../dist/index.js');
    const { zodToJsonSchema } = await import('zod-to-json-schema');

    for (const [name, tool] of Object.entries(toolRegistry)) {
      expect(() => zodToJsonSchema(tool.schema)).not.toThrow();

      if (tool.outputSchema) {
        expect(() => zodToJsonSchema(tool.outputSchema)).not.toThrow();
      }
    }
  });
});
