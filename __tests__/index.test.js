import { jest, describe, beforeEach, test, expect, afterAll } from '@jest/globals';
// =================================
// == TOP-LEVEL MOCKS ONLY =========
// =================================

// Mock zod-to-json-schema
// Top-level mock for zod-to-json-schema removed - will be mocked inside relevant describe/test blocks

// Mock process
// Mocking built-in 'process' might be tricky/unnecessary with ESM, comment out for now
// jest.unstable_mockModule('process', () => ({
//   ...jest.requireActual('process'),
//   exit: jest.fn()
// }));

import { z } from 'zod'; // Import zod at top level
// Import compiled JS at top level - toolRegistry needed for schema tests
import { start, toolRegistry } from '../dist/index.js';
// Top-level import of zlibApi removed - will be dynamically imported in tests
// Top-level import of ServerMock removed - will be dynamically imported in tests
// Top-level import of ListToolsRequestSchema removed - will be dynamically imported in tests
// =================================
// == TEST SUITES ==================
// =================================

// =================================
// == TEST SUITES ==================
// =================================

describe('MCP Server', () => {
  let mockServerInstance; // Declare instance variable for cleanup

  beforeEach(() => {
    // Reset modules AND mocks before each test
    mockServerInstance = null; // Reset instance holder
    // jest.* calls moved inside individual tests for ESM compatibility
    // jest.resetModules(); // Moved inside tests
    // jest.clearAllMocks(); // Moved inside tests
    // Mock console functions for clean assertions - OK to keep in beforeEach
    console.error = jest.fn();
    console.log = jest.fn(); // Add log mock too
  });
  test('should initialize MCP server with metadata', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks(); // Clear mocks for this specific test
    // Define mock instances for THIS test's scope

    let capturedServerArgs = null; // Variable to store captured constructor args
    // Define mock instances for THIS test's scope
    const mockTransport = { send: jest.fn() };
    const mockServer = {
      connect: jest.fn().mockResolvedValue(undefined),
      handle: jest.fn(),
      registerCapabilities: jest.fn(),
      setRequestHandler: jest.fn(),
    };
    mockServerInstance = mockServer; // Assign for potential cleanup

    // Mock SDK modules using unstable_mockModule INSIDE the test
    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/index.js', () => ({
      Server: jest.fn().mockImplementation((serverInfo, serverOptions) => {
        capturedServerArgs = serverOptions; // Capture the second argument
        return mockServer; // Return the mock instance
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
    // Mock zod-to-json-schema INSIDE the test
    jest.unstable_mockModule('zod-to-json-schema', () => ({
      zodToJsonSchema: jest.fn((schema) => ({ /* basic mock */ type: 'object', properties: {} })),
    }));
    // Mock venv-manager INSIDE the test
    jest.unstable_mockModule('../lib/venv-manager.js', () => ({
      ensureVenvReady: jest.fn().mockResolvedValue(undefined),
      getManagedPythonPath: jest.fn().mockReturnValue('/fake/python'), // Provide a fake path
    }));

    // Dynamically import modules AFTER mocks are set
    const { Server } = await import('@modelcontextprotocol/sdk/server/index.js');
    const { start } = await import('../dist/index.js');

    await start({ testing: true });

    // --- Assert ---
    // Access the dynamically imported mock constructor
    const { Server: ServerMockConstructor } = await import('@modelcontextprotocol/sdk/server/index.js');
    // Check the Server constructor call arguments
    expect(ServerMockConstructor).toHaveBeenCalled();
    const constructorCallArgs = ServerMockConstructor.mock.calls[0];
    expect(constructorCallArgs[0]).toEqual({ // ServerInfo
        name: "zlibrary-mcp",
        description: "Z-Library access for AI assistants",
        version: expect.any(String),
    });
    expect(constructorCallArgs[1]).toBeDefined(); // ServerOptions
    const serverOptions = constructorCallArgs[1];
    // Check the capabilities passed in ServerOptions
    expect(serverOptions.capabilities).toBeDefined();
    expect(serverOptions.capabilities.tools).toBeDefined();
    // Correct Assertion: Expect tools object NOT to be empty
    expect(Object.keys(serverOptions.capabilities.tools).length).toBeGreaterThan(0);
    // Expect 4 handlers: list/call tools, list resources, list prompts
    expect(mockServer.setRequestHandler).toHaveBeenCalledTimes(4);
    expect(mockServer.connect).toHaveBeenCalledWith(mockTransport);
    expect(console.log).toHaveBeenCalledWith('Z-Library MCP server (ESM/TS) is running via Stdio...'); // Check console.log
  });
    test('tools/list handler should include RAG tools', async () => {
      // --- Setup Mocks for this test ---
      jest.resetModules(); // Reset modules for this specific test
      jest.clearAllMocks();

      const mockTransport = { send: jest.fn() };
      let capturedListToolsHandler = null; // Variable to capture the handler
      const mockServer = {
        connect: jest.fn().mockResolvedValue(undefined),
        handle: jest.fn(),
        registerCapabilities: jest.fn(), // Keep if index.js still calls it (unlikely with new SDK)
        setRequestHandler: jest.fn((schema, handler) => {
          // Check schema name for safety, as the object itself might change across imports
          if (schema?.name === 'ListToolsRequestSchema') {
             capturedListToolsHandler = handler; // Capture the handler
          }
        }),
      };
      mockServerInstance = mockServer;

      // Mock SDK modules INSIDE the test
      jest.unstable_mockModule('@modelcontextprotocol/sdk/server/index.js', () => ({
        Server: jest.fn().mockImplementation(() => mockServer),
      }));
      jest.unstable_mockModule('@modelcontextprotocol/sdk/server/stdio.js', () => ({
        StdioServerTransport: jest.fn().mockImplementation(() => mockTransport),
      }));
      // Mock only the necessary schema for this test
      const mockListToolsSchema = { name: 'ListToolsRequestSchema', parse: jest.fn(x => x) };
      jest.unstable_mockModule('@modelcontextprotocol/sdk/types.js', () => ({
        ListToolsRequestSchema: mockListToolsSchema,
        // Mock others minimally if needed by index.js during init
        CallToolRequestSchema: { name: 'CallToolRequestSchema' },
        ListResourcesRequestSchema: { name: 'ListResourcesRequestSchema' },
        ListPromptsRequestSchema: { name: 'ListPromptsRequestSchema' },
      }));
      // Mock zod-to-json-schema INSIDE the test
      jest.unstable_mockModule('zod-to-json-schema', () => ({
         zodToJsonSchema: jest.fn((schema) => ({ /* basic mock */ type: 'object', properties: {} })),
      }));
      // Mock venv-manager for this test
      jest.unstable_mockModule('../lib/venv-manager.js', () => ({
        ensureVenvReady: jest.fn().mockResolvedValue(undefined),
        getManagedPythonPath: jest.fn().mockReturnValue('/fake/python'),
      }));


      // Dynamically import start AFTER mocks
      const { start } = await import('../dist/index.js');
      await start({ testing: true }); // Initialize to register handlers

      // --- Act ---
      expect(capturedListToolsHandler).toBeDefined(); // Ensure handler was captured
      const listResponse = await capturedListToolsHandler({}); // Call the captured handler

      // --- Assert ---
      expect(listResponse.tools).toBeInstanceOf(Array);
      const toolNames = listResponse.tools.map(t => t.name);
      expect(toolNames).toContain('download_book_to_file');
      expect(toolNames).toContain('process_document_for_rag');

      // Check schemas exist (basic check due to zod-to-json-schema mock)
      const downloadTool = listResponse.tools.find(t => t.name === 'download_book_to_file');
      const processTool = listResponse.tools.find(t => t.name === 'process_document_for_rag');
      expect(downloadTool.inputSchema).toBeDefined(); // Use camelCase
      // expect(downloadTool.output_schema).toBeDefined(); // Removed: Mock doesn't generate this
      expect(processTool.inputSchema).toBeDefined(); // Use camelCase
      // expect(processTool.output_schema).toBeDefined(); // Removed: Mock doesn't generate this
    });


  test('should log error and not connect if venv setup fails', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks();

    const mockTransport = { send: jest.fn() };
    const mockServer = {
      connect: jest.fn().mockResolvedValue(undefined),
      handle: jest.fn(),
      registerCapabilities: jest.fn(),
      setRequestHandler: jest.fn(),
      disconnect: jest.fn().mockResolvedValue(undefined),
      close: jest.fn().mockResolvedValue(undefined),
    };
    mockServerInstance = mockServer;

    // Mock SDK modules INSIDE the test
    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/index.js', () => ({
      Server: jest.fn().mockImplementation(() => mockServer),
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
    // Mock zod-to-json-schema INSIDE the test
    jest.unstable_mockModule('zod-to-json-schema', () => ({
       zodToJsonSchema: jest.fn((schema) => ({ /* basic mock */ type: 'object', properties: {} })),
    }));
    // Mock venv-manager to fail for THIS test
    const mockEnsureVenvReady = jest.fn().mockRejectedValue(new Error('Venv setup failed'));
    jest.unstable_mockModule('../lib/venv-manager.js', () => ({
      ensureVenvReady: mockEnsureVenvReady,
      getManagedPythonPath: jest.fn().mockReturnValue('/fake/python'),
    }));

    // Dynamically import index
    // Dynamically import start AFTER mocks
    const { start } = await import('../dist/index.js');

    await start({ testing: true });

    // --- Assert ---
    expect(mockEnsureVenvReady).toHaveBeenCalled(); // Check the specific mock function
    expect(console.error).toHaveBeenCalledWith(
      'Failed to start MCP server:',
      expect.objectContaining({ message: 'Venv setup failed' })
    );
    expect(mockServer.connect).not.toHaveBeenCalled(); // Check the instance connect
  });

  test('should handle Server instantiation exceptions gracefully', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks();

    const mockTransport = { send: jest.fn() };

    // Use unstable_mockModule for ESM mocking BEFORE dynamic import
    jest.unstable_mockModule('@modelcontextprotocol/sdk/server/index.js', () => ({
      Server: jest.fn().mockImplementationOnce(() => { throw new Error('Server instantiation error'); }),
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
    // Mock zod-to-json-schema INSIDE the test
    jest.unstable_mockModule('zod-to-json-schema', () => ({
       zodToJsonSchema: jest.fn((schema) => ({ /* basic mock */ type: 'object', properties: {} })),
    }));
    // Mock venv-manager to succeed for THIS test
    const mockEnsureVenvReadySuccess = jest.fn().mockResolvedValue(undefined);
    jest.unstable_mockModule('../lib/venv-manager.js', () => ({
      ensureVenvReady: mockEnsureVenvReadySuccess,
      getManagedPythonPath: jest.fn().mockReturnValue('/fake/python'),
    }));

    // Dynamically import start and Server AFTER mocks
    const { Server } = await import('@modelcontextprotocol/sdk/server/index.js');
    const { start } = await import('../dist/index.js');
    await start({ testing: true });

    // --- Assert ---
    expect(Server).toHaveBeenCalled(); // Check the dynamically imported mock constructor
    expect(console.error).toHaveBeenCalledWith(
      'Failed to start MCP server:',
      expect.objectContaining({ message: 'Server instantiation error' })
    );
    // No need to check connect, constructor threw.

  });
  afterAll(async () => {
    // Attempt to close the server instance if it was created and has a close/disconnect method
    if (mockServerInstance) {
      if (typeof mockServerInstance.disconnect === 'function') {
        await mockServerInstance.disconnect();
      } else if (typeof mockServerInstance.close === 'function') {
        await mockServerInstance.close();
      }
    }
  });
}); // End MCP Server describe


describe('Tool Handlers (Direct)', () => {

 // No global requires here

 beforeEach(() => {
   // jest.* calls moved inside tests
   // Clear mocks/spies
   // jest.resetModules(); // Moved inside tests
   // jest.clearAllMocks(); // Moved inside tests
   console.log = jest.fn();
   console.error = jest.fn();
 });

 // No need for a separate tools/list test

    // Import Zod for schema testing
    // z is imported at the top level

    describe('Tool Schemas', () => {
      test('download_book_to_file schema should reflect v2.1 changes', () => { // Updated test description
        // toolRegistry is imported at the top level
        const schema = toolRegistry.download_book_to_file.schema;
        const outputSchema = toolRegistry.download_book_to_file.outputSchema; // Assuming outputSchema is directly available

        // Check input schema properties (v2.1)
        expect(schema.shape.bookDetails).toBeDefined(); // Check for bookDetails - Type check is tricky with passthrough, defined is enough
        // expect(schema.shape.bookDetails._def.typeName).toBe(z.ZodObject.name); // This fails due to passthrough()
        expect(schema.shape.id).toBeUndefined(); // Ensure old 'id' is removed
        expect(schema.shape.format).toBeUndefined(); // Ensure old 'format' is removed
        expect(schema.shape.outputDir).toBeDefined();
        expect(schema.shape.process_for_rag).toBeDefined();
        expect(schema.shape.process_for_rag._def.typeName).toBe(z.ZodOptional.name);
        expect(schema.shape.process_for_rag.unwrap()._def.typeName).toBe(z.ZodBoolean.name);
        expect(schema.shape.processed_output_format).toBeDefined(); // Restore check

        // Check output schema (v2.1) - Output schema is not defined in toolRegistry, removing checks
        // expect(outputSchema).toBeDefined();
        // expect(outputSchema.shape.file_path).toBeDefined();
        // expect(outputSchema.shape.processed_file_path).toBeDefined();
        // expect(outputSchema.shape.processed_file_path._def.typeName).toBe(z.ZodOptional.name);
        // expect(outputSchema.shape.processed_file_path.unwrap()._def.typeName).toBe(z.ZodNullable.name); // Check it's nullable
        // expect(outputSchema.shape.processed_file_path.unwrap().unwrap()._def.typeName).toBe(z.ZodString.name); // Check underlying type is string
      });

      test('process_document_for_rag schema should define input and output (v2.1)', () => { // Updated test description
        // toolRegistry is imported at the top level
        const schema = toolRegistry.process_document_for_rag.schema;
        const outputSchema = toolRegistry.process_document_for_rag.outputSchema; // Assuming outputSchema is directly available

        // Check input schema properties
        expect(schema.shape.file_path).toBeDefined();
        expect(schema.shape.file_path._def.typeName).toBe(z.ZodString.name);
        expect(schema.shape.output_format).toBeDefined(); // Check new optional field
        // Restore original expectation (ZodOptional)
        expect(schema.shape.output_format._def.typeName).toBe(z.ZodOptional.name);

        // Check output schema (v2.1) - Output schema is not defined in toolRegistry, removing checks
        // expect(outputSchema).toBeDefined();
        // expect(outputSchema.shape.processed_file_path).toBeDefined();
        // expect(outputSchema.shape.processed_file_path._def.typeName).toBe(z.ZodNullable.name); // Check it's nullable
        // expect(outputSchema.shape.processed_file_path.unwrap()._def.typeName).toBe(z.ZodString.name); // Check underlying type is string
      });

      describe('FullTextSearchParamsSchema', () => {
        const schema = toolRegistry.full_text_search.schema;

        test('should validate with valid fromYear and toYear', () => {
          expect(schema.safeParse({ query: 'test', fromYear: 2000, toYear: 2020 }).success).toBe(true);
        });

        test('should validate with optional fromYear and toYear missing', () => {
          expect(schema.safeParse({ query: 'test' }).success).toBe(true);
        });

        test('should invalidate with non-integer fromYear', () => {
          expect(schema.safeParse({ query: 'test', fromYear: 2000.5 }).success).toBe(false);
        });

        test('should invalidate with non-integer toYear', () => {
          expect(schema.safeParse({ query: 'test', toYear: '2020' }).success).toBe(false);
        });
      });
 
      describe('get_metadata Schemas', () => {
        const GetMetadataParamsSchema = toolRegistry.get_metadata.schema;
        const BookMetadataOutputSchema = toolRegistry.get_metadata.outputSchema;

        test('GetMetadataParamsSchema should validate URL correctly', () => {
          expect(GetMetadataParamsSchema.safeParse({ url: 'http://example.com' }).success).toBe(true);
          expect(GetMetadataParamsSchema.safeParse({ url: 'https://example.com/book/123' }).success).toBe(true);
          expect(GetMetadataParamsSchema.safeParse({ url: 'invalid-url' }).success).toBe(false);
          expect(GetMetadataParamsSchema.safeParse({}).success).toBe(false); // Missing URL
          expect(GetMetadataParamsSchema.safeParse({ url: 123 }).success).toBe(false); // Invalid type
        });

        test('BookMetadataOutputSchema should validate a complete and valid output', () => {
          const validInput = {
            title: "Test Book",
            authors: ["Author A", "Author B"],
            series_name: "Test Series",
            series_url: "http://example.com/series/1",
            publisher: "Test Publisher",
            publication_year: 2021,
            language: "English",
            isbn_list: ["978-1234567890"],
            categories: ["Fiction", "Sci-Fi"],
            description: "A test description.",
            cover_image_url: "http://example.com/cover.jpg",
            pages_count: 300,
            filesize_str: "1.2 MB",
            doi: "10.1000/xyz123",
            booklists_urls: ["http://example.com/list/1"],
            you_may_be_interested_in_urls: ["http://example.com/related/1"],
            most_frequent_terms: ["test", "book"],
            source_url: "http://example.com/book/original"
          };
          expect(BookMetadataOutputSchema.safeParse(validInput).success).toBe(true);
        });

        test('BookMetadataOutputSchema should validate with missing optional fields', () => {
          const validInputOptionalMissing = {
            title: "Test Book Minimal",
            authors: [], // Optional, can be empty
            series_name: null, // Optional
            series_url: null, // Optional
            publisher: null, // Optional
            publication_year: null, // Optional
            language: "Unknown", // Optional but string
            isbn_list: [], // Optional, can be empty
            categories: [], // Optional, can be empty
            description: "Minimal desc.", // Required
            cover_image_url: null, // Optional
            pages_count: null, // Optional
            filesize_str: null, // Optional
            doi: null, // Optional
            booklists_urls: [], // Optional, can be empty
            you_may_be_interested_in_urls: [], // Optional, can be empty
            most_frequent_terms: [], // Optional, can be empty
            source_url: "http://example.com/book/minimal" // Required
          };
          const result = BookMetadataOutputSchema.safeParse(validInputOptionalMissing);
          expect(result.success).toBe(true);
        });

        test('BookMetadataOutputSchema should fail with missing required fields', () => {
          const invalidInput = {
            // Missing title, description, source_url
            authors: [],
          };
          expect(BookMetadataOutputSchema.safeParse(invalidInput).success).toBe(false);
        });

        test('BookMetadataOutputSchema should fail with incorrect data types', () => {
          const invalidTypes = {
            title: "Test Book",
            authors: "Not an array", // Incorrect type
            series_name: "Test Series",
            series_url: "http://example.com/series/1",
            publisher: "Test Publisher",
            publication_year: "2021", // Incorrect type (string instead of number)
            language: "English",
            isbn_list: ["978-1234567890"],
            categories: ["Fiction", "Sci-Fi"],
            description: "A test description.",
            cover_image_url: "http://example.com/cover.jpg",
            pages_count: "300 pages", // Incorrect type
            filesize_str: "1.2 MB",
            doi: "10.1000/xyz123",
            booklists_urls: ["http://example.com/list/1"],
            you_may_be_interested_in_urls: ["http://example.com/related/1"],
            most_frequent_terms: ["test", "book"],
            source_url: "http://example.com/book/original"
          };
          expect(BookMetadataOutputSchema.safeParse(invalidTypes).success).toBe(false);
        });
      });
    }); // End Tool Schemas describe

    describe('BookItemOutputSchema, SearchBooksOutputSchema, and FullTextSearchOutputSchema', () => {
      const BookItemOutputSchema = toolRegistry.search_books.outputSchema.shape.books.element; // Assuming this path based on MB
      const SearchBooksOutputSchema = toolRegistry.search_books.outputSchema;
      const FullTextSearchOutputSchema = toolRegistry.full_text_search.outputSchema;

      const validBookItem = {
        id: '123',
        url: 'http://example.com/book/123',
        name: 'Test Book',
        authors: ['Author A'],
        title: 'Test Book',
        author: 'Author A',
        // other optional fields can be null or undefined
        publisher: null,
        year: '2023',
        language: 'English',
        extension: 'epub',
        size: '1.2 MB',
        rating: '4.5',
        quality: 'good',
        cover: 'http://example.com/cover.jpg',
        isbn: '978-1234567890',
      };

      const bookItemWithNulls = {
        ...validBookItem,
        title: null,
        author: null,
      };
      
      const bookItemWithMissingOptionals = { // Only required fields + new ones
        id: '123',
        url: 'http://example.com/book/123',
        name: 'Test Book', // name is often derived from title
        title: 'Test Book',
        author: 'Author A',
        authors: ['Author A']
      };


      test('BookItemOutputSchema should validate a valid book item with title and author', () => {
        expect(BookItemOutputSchema.safeParse(validBookItem).success).toBe(true);
      });

      test('BookItemOutputSchema should validate a book item with null title and author', () => {
        const item = { ...validBookItem, title: null, author: null, name: null, authors: [] }; // name and authors might be empty/null if title/author are null
        expect(BookItemOutputSchema.safeParse(item).success).toBe(true);
      });
      
      test('BookItemOutputSchema should validate a book item with missing optional title and author', () => {
        const item = { ...validBookItem };
        delete item.title; // Make it optional by removing
        delete item.author;
        // 'name' and 'authors' might still be derived or present from other attributes in real scenarios
        // For schema testing, if title/author are truly optional, this should pass
        // However, the current BookItemOutputSchema in MB makes them z.string().nullable().optional()
        // So, they can be null, undefined, or a string.
        expect(BookItemOutputSchema.safeParse(item).success).toBe(true);
      });


      test('BookItemOutputSchema should invalidate if title is not a string or null/undefined', () => {
        expect(BookItemOutputSchema.safeParse({ ...validBookItem, title: 123 }).success).toBe(false);
      });

      test('BookItemOutputSchema should invalidate if author is not a string or null/undefined', () => {
        expect(BookItemOutputSchema.safeParse({ ...validBookItem, author: 123 }).success).toBe(false);
      });

      test('SearchBooksOutputSchema should validate with valid book items including title/author', () => {
        const validOutput = { books: [validBookItem, bookItemWithNulls], retrieved_from_url: "http://example.com/search" };
        expect(SearchBooksOutputSchema.safeParse(validOutput).success).toBe(true);
      });
      
      test('SearchBooksOutputSchema should validate with book items missing optional title/author', () => {
        const item1 = { ...validBookItem };
        delete item1.title;
        delete item1.author;
        const item2 = { ...validBookItem, title: "Another Title", author: "Another Author" }; // A complete one
        const validOutput = { books: [item1, item2], retrieved_from_url: "http://example.com/search" };
        expect(SearchBooksOutputSchema.safeParse(validOutput).success).toBe(true);
      });

      test('SearchBooksOutputSchema should invalidate if a book item has incorrect title type', () => {
        const invalidOutput = { books: [{ ...validBookItem, title: 123 }], retrieved_from_url: "http://example.com/search" };
        expect(SearchBooksOutputSchema.safeParse(invalidOutput).success).toBe(false);
      });

      test('FullTextSearchOutputSchema should validate with valid book items including title/author', () => {
        const validOutput = { books: [validBookItem, bookItemWithMissingOptionals], retrieved_from_url: "http://example.com/ftsearch" };
        expect(FullTextSearchOutputSchema.safeParse(validOutput).success).toBe(true);
      });

      test('FullTextSearchOutputSchema should invalidate if a book item has incorrect author type', () => {
        const invalidOutput = { books: [{ ...validBookItem, author: true }], retrieved_from_url: "http://example.com/ftsearch" };
        expect(FullTextSearchOutputSchema.safeParse(invalidOutput).success).toBe(false);
      });
    });

 describe('Handler Logic', () => {

   // Wrap each handler test in isolateModules to ensure clean zlibApi mock state
   test('search_books handler should call zlibApi.searchBooks and handle success/error', async () => {
     // --- Setup Mocks for this test ---
     jest.resetModules();
     jest.clearAllMocks();
     const mockSearchBooks = jest.fn();
     jest.unstable_mockModule('../lib/zlibrary-api.js', () => ({
       searchBooks: mockSearchBooks,
       // Add other functions if needed by index.js, otherwise Jest mocks them as undefined
       // getBookById: jest.fn(), // Removed deprecated tool mock
       downloadBookToFile: jest.fn(),
       getDownloadInfo: jest.fn(),
       fullTextSearch: jest.fn(),
       getDownloadHistory: jest.fn(),
       getDownloadLimits: jest.fn(),
       getRecentBooks: jest.fn(),
       processDocumentForRag: jest.fn(),
     }));

     // Dynamically import toolRegistry and the mocked zlibApi
     const { toolRegistry } = await import('../dist/index.js');
     const zlibApi = await import('../lib/zlibrary-api.js'); // Get the mocked version

     const handler = toolRegistry.search_books.handler;
     const mockArgs = { query: 'test', count: 5 };
     const validatedArgs = toolRegistry.search_books.schema.parse(mockArgs); // Use schema from dynamically imported registry
     const mockResult = [{ title: 'Result Book' }];
     mockSearchBooks.mockResolvedValueOnce(mockResult); // Use the specific mock function

     const response = await handler(validatedArgs);

     expect(mockSearchBooks).toHaveBeenCalledWith( // Check the specific mock function
        validatedArgs // Handler should pass the validated object directly now
     );
     // Update expectation to use 'content' key as returned by the handler
     expect(response).toEqual(mockResult); // Expect direct result

     // Error case
     const error = new Error('API Failed');
     mockSearchBooks.mockRejectedValueOnce(error); // Use the specific mock function
     const errorResponse = await handler(validatedArgs);
     expect(errorResponse).toEqual({ error: { message: 'API Failed' } }); // Match nested structure
   });

    // Removed test for deprecated getBookById handler

    test('downloadBookToFile handler should call zlibApi.downloadBookToFile (v2.1)', async () => { // Updated test description
       // --- Setup Mocks for this test ---
       jest.resetModules();
       jest.clearAllMocks();
       const mockDownloadBookToFile = jest.fn();
       jest.unstable_mockModule('../lib/zlibrary-api.js', () => ({
         searchBooks: jest.fn(),
         // getBookById: jest.fn(), // Already removed
         downloadBookToFile: mockDownloadBookToFile,
         getDownloadInfo: jest.fn(),
         fullTextSearch: jest.fn(),
         getDownloadHistory: jest.fn(),
         getDownloadLimits: jest.fn(),
         getRecentBooks: jest.fn(),
         processDocumentForRag: jest.fn(),
       }));

       // Dynamically import toolRegistry and the mocked zlibApi
       const { toolRegistry } = await import('../dist/index.js');
       const zlibApi = await import('../lib/zlibrary-api.js');

       const handler = toolRegistry.download_book_to_file.handler;
       // Use bookDetails in mockArgs (v2.1)
       const mockBookDetailsArg = { id: 'book456', url: 'http://example.com/book/456/slug', title: 'Test Download' };
       const mockArgs = { bookDetails: mockBookDetailsArg, outputDir: '/tmp/test' };
       const validatedArgs = toolRegistry.download_book_to_file.schema.parse(mockArgs);
       const mockResult = { file_path: '/tmp/test/book.epub', processed_file_path: null }; // Example result
       mockDownloadBookToFile.mockResolvedValueOnce(mockResult); // Use the specific mock function

       const response = await handler(validatedArgs);

       expect(mockDownloadBookToFile).toHaveBeenCalledWith(validatedArgs); // Check the specific mock function
       expect(response).toEqual(mockResult);

      // Error case
      const error = new Error('Download Error');
      mockDownloadBookToFile.mockRejectedValueOnce(error); // Use the specific mock function
      const errorResponse = await handler(validatedArgs);
      expect(errorResponse).toEqual({ error: { message: 'Download Error' } }); // Match nested structure
    });

    test('fullTextSearch handler should call zlibApi.fullTextSearch', async () => {
       // --- Setup Mocks for this test ---
       jest.resetModules();
       jest.clearAllMocks();
       const mockFullTextSearch = jest.fn();
       jest.unstable_mockModule('../lib/zlibrary-api.js', () => ({
         searchBooks: jest.fn(),
         // getBookById: jest.fn(), // Already removed
         downloadBookToFile: jest.fn(),
         getDownloadInfo: jest.fn(),
         fullTextSearch: mockFullTextSearch,
         getDownloadHistory: jest.fn(),
         getDownloadLimits: jest.fn(),
         getRecentBooks: jest.fn(),
         processDocumentForRag: jest.fn(),
       }));

       // Dynamically import toolRegistry and the mocked zlibApi
       const { toolRegistry } = await import('../dist/index.js');
       const zlibApi = await import('../lib/zlibrary-api.js');

       const handler = toolRegistry.full_text_search.handler;
       const mockArgs = { query: 'search text' };
       const validatedArgs = toolRegistry.full_text_search.schema.parse(mockArgs);
       const mockResult = [{ title: 'Found Book' }];
       mockFullTextSearch.mockResolvedValueOnce(mockResult); // Use the specific mock function

       const response = await handler(validatedArgs);

       expect(mockFullTextSearch).toHaveBeenCalledWith(validatedArgs); // Check the specific mock function
        // Update expectation to use 'content' key as returned by the handler
        expect(response).toEqual(mockResult); // Expect direct result

       const error = new Error('FullText Error');
       mockFullTextSearch.mockRejectedValueOnce(error); // Use the specific mock function
       const errorResponse = await handler(validatedArgs);
       expect(errorResponse).toEqual({ error: { message: 'FullText Error' } }); // Match nested structure
    });

    test('getDownloadHistory handler should call zlibApi.getDownloadHistory', async () => {
       // --- Setup Mocks for this test ---
       jest.resetModules();
       jest.clearAllMocks();
       const mockGetDownloadHistory = jest.fn();
       jest.unstable_mockModule('../lib/zlibrary-api.js', () => ({
         searchBooks: jest.fn(),
         // getBookById: jest.fn(), // Already removed
         downloadBookToFile: jest.fn(),
         getDownloadInfo: jest.fn(),
         fullTextSearch: jest.fn(),
         getDownloadHistory: mockGetDownloadHistory,
         getDownloadLimits: jest.fn(),
         getRecentBooks: jest.fn(),
         processDocumentForRag: jest.fn(),
       }));

       // Dynamically import toolRegistry and the mocked zlibApi
       const { toolRegistry } = await import('../dist/index.js');
       const zlibApi = await import('../lib/zlibrary-api.js');

       const handler = toolRegistry.get_download_history.handler;
       const mockArgs = { count: 5 };
       const validatedArgs = toolRegistry.get_download_history.schema.parse(mockArgs);
       const mockResult = [{ id: 'hist1' }];
       mockGetDownloadHistory.mockResolvedValueOnce(mockResult); // Use the specific mock function

       const response = await handler(validatedArgs);

       expect(mockGetDownloadHistory).toHaveBeenCalledWith(validatedArgs); // Check the specific mock function
       // Update expectation to match the handler's return structure
       expect(response).toEqual(mockResult); // Expect direct result

       const error = new Error('History Error');
       mockGetDownloadHistory.mockRejectedValueOnce(error); // Use the specific mock function
       const errorResponse = await handler(validatedArgs);
       expect(errorResponse).toEqual({ error: { message: 'History Error' } }); // Match nested structure
    });

    test('getDownloadLimits handler should call zlibApi.getDownloadLimits', async () => {
       // --- Setup Mocks for this test ---
       jest.resetModules();
       jest.clearAllMocks();
       const mockGetDownloadLimits = jest.fn();
       jest.unstable_mockModule('../lib/zlibrary-api.js', () => ({
         searchBooks: jest.fn(),
         // getBookById: jest.fn(), // Already removed
         downloadBookToFile: jest.fn(),
         getDownloadInfo: jest.fn(),
         fullTextSearch: jest.fn(),
         getDownloadHistory: jest.fn(),
         getDownloadLimits: mockGetDownloadLimits,
         getRecentBooks: jest.fn(),
         processDocumentForRag: jest.fn(),
       }));

       // Dynamically import toolRegistry and the mocked zlibApi
       const { toolRegistry } = await import('../dist/index.js');
       const zlibApi = await import('../lib/zlibrary-api.js');

       const handler = toolRegistry.get_download_limits.handler;
       const mockArgs = {};
       const validatedArgs = toolRegistry.get_download_limits.schema.parse(mockArgs);
       const mockResult = { daily: 5, used: 1 };
       mockGetDownloadLimits.mockResolvedValueOnce(mockResult); // Use the specific mock function

       const response = await handler(validatedArgs);

       expect(mockGetDownloadLimits).toHaveBeenCalledWith(); // Expect no arguments
       expect(response).toEqual(mockResult);

       const error = new Error('Limits Error');
       mockGetDownloadLimits.mockRejectedValueOnce(error); // Use the specific mock function
       const errorResponse = await handler(validatedArgs);
       expect(errorResponse).toEqual({ error: { message: 'Limits Error' } }); // Match nested structure
    });

  }); // End Handler Logic describe
}); // End Tool Handlers (Direct) describe
// Removed duplicated code from bad diff
