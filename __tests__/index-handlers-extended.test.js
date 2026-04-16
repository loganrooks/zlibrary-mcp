import { jest, describe, beforeEach, test, expect } from '@jest/globals';

// ============================================================================
// Tests for uncovered handler paths in src/index.ts
// Covers: processDocumentForRag, getBookMetadata, searchByTerm, searchByAuthor,
//         fetchBooklist, searchAdvanced, searchMultiSource handlers
//         + wrapResult helper (error and success paths)
//         + toolRegistry entries for newer tools
// ============================================================================

describe('Tool Handlers - Extended Coverage', () => {

  beforeEach(() => {
    console.log = jest.fn();
    console.error = jest.fn();
  });

  // Helper: creates a mock zlibrary-api module and imports fresh handlers
  async function setupWithMocks(overrides = {}) {
    jest.resetModules();
    jest.clearAllMocks();

    const defaults = {
      searchBooks: jest.fn(),
      fullTextSearch: jest.fn(),
      getDownloadHistory: jest.fn(),
      getDownloadLimits: jest.fn(),
      downloadBookToFile: jest.fn(),
      processDocumentForRag: jest.fn(),
      getBookMetadata: jest.fn(),
      searchByTerm: jest.fn(),
      searchByAuthor: jest.fn(),
      fetchBooklist: jest.fn(),
      searchAdvanced: jest.fn(),
      searchMultiSource: jest.fn(),
      getRecentBooks: jest.fn(),
    };

    const mocks = { ...defaults, ...overrides };

    jest.unstable_mockModule('../lib/zlibrary-api.js', () => mocks);

    const { toolRegistry, handlers } = await import('../dist/index.js');
    return { toolRegistry, handlers, mocks };
  }

  describe('processDocumentForRag handler', () => {
    test('should call zlibApi.processDocumentForRag with mapped args on success', async () => {
      const mockProcessDoc = jest.fn().mockResolvedValue({
        processed_file_path: '/output/doc.txt',
        metadata_file_path: '/output/doc.metadata.json',
        content_types_produced: ['body'],
        output_files: {
          body: '/output/doc.txt',
          metadata: '/output/doc.metadata.json',
        },
      });
      const { toolRegistry } = await setupWithMocks({ processDocumentForRag: mockProcessDoc });

      const handler = toolRegistry.process_document_for_rag.handler;
      const args = { file_path: '/input/doc.epub', output_format: 'markdown' };
      const validatedArgs = toolRegistry.process_document_for_rag.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockProcessDoc).toHaveBeenCalledWith({
        filePath: '/input/doc.epub',
        outputFormat: 'markdown',
      });
      expect(response).toEqual({
        processed_file_path: '/output/doc.txt',
        metadata_file_path: '/output/doc.metadata.json',
        content_types_produced: ['body'],
        output_files: {
          body: '/output/doc.txt',
          metadata: '/output/doc.metadata.json',
        },
      });
    });

    test('should return error object on failure', async () => {
      const mockProcessDoc = jest.fn().mockRejectedValue(new Error('Process failed'));
      const { toolRegistry } = await setupWithMocks({ processDocumentForRag: mockProcessDoc });

      const handler = toolRegistry.process_document_for_rag.handler;
      const args = { file_path: '/input/doc.epub' };
      const validatedArgs = toolRegistry.process_document_for_rag.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Process failed' } });
    });
  });

  describe('getBookMetadata handler', () => {
    test('should call zlibApi.getBookMetadata with correct args on success', async () => {
      const mockGetMeta = jest.fn().mockResolvedValue({
        title: 'Test Book', author: 'Author', terms: ['philosophy'],
      });
      const { toolRegistry } = await setupWithMocks({ getBookMetadata: mockGetMeta });

      const handler = toolRegistry.get_book_metadata.handler;
      const args = { bookId: '123', bookHash: 'abc', include: ['terms'] };
      const validatedArgs = toolRegistry.get_book_metadata.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockGetMeta).toHaveBeenCalledWith('123', 'abc', ['terms']);
      expect(response).toEqual({
        title: 'Test Book', author: 'Author', terms: ['philosophy'],
      });
    });

    test('should return error object on failure', async () => {
      const mockGetMeta = jest.fn().mockRejectedValue(new Error('Metadata failed'));
      const { toolRegistry } = await setupWithMocks({ getBookMetadata: mockGetMeta });

      const handler = toolRegistry.get_book_metadata.handler;
      const args = { bookId: '123', bookHash: 'abc' };
      const validatedArgs = toolRegistry.get_book_metadata.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Metadata failed' } });
    });
  });

  describe('searchByTerm handler', () => {
    test('should call zlibApi.searchByTerm with mapped args on success', async () => {
      const mockSearchTerm = jest.fn().mockResolvedValue([{ title: 'Phenomenology Book' }]);
      const { toolRegistry } = await setupWithMocks({ searchByTerm: mockSearchTerm });

      const handler = toolRegistry.search_by_term.handler;
      const args = { term: 'phenomenology', yearFrom: 1900, yearTo: 2020, languages: ['english'], extensions: ['pdf'], count: 15 };
      const validatedArgs = toolRegistry.search_by_term.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockSearchTerm).toHaveBeenCalledWith({
        term: 'phenomenology',
        yearFrom: 1900,
        yearTo: 2020,
        languages: ['english'],
        extensions: ['pdf'],
        limit: 15,
      });
      expect(response).toEqual([{ title: 'Phenomenology Book' }]);
    });

    test('should return error object on failure', async () => {
      const mockSearchTerm = jest.fn().mockRejectedValue(new Error('Term search failed'));
      const { toolRegistry } = await setupWithMocks({ searchByTerm: mockSearchTerm });

      const handler = toolRegistry.search_by_term.handler;
      const args = { term: 'dialectic' };
      const validatedArgs = toolRegistry.search_by_term.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Term search failed' } });
    });
  });

  describe('searchByAuthor handler', () => {
    test('should call zlibApi.searchByAuthor with mapped args on success', async () => {
      const mockSearchAuthor = jest.fn().mockResolvedValue([{ title: 'Hegel Book' }]);
      const { toolRegistry } = await setupWithMocks({ searchByAuthor: mockSearchAuthor });

      const handler = toolRegistry.search_by_author.handler;
      const args = { author: 'Hegel', exact: true, yearFrom: 1800, yearTo: 1900, languages: ['german'], extensions: ['epub'], count: 10 };
      const validatedArgs = toolRegistry.search_by_author.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockSearchAuthor).toHaveBeenCalledWith({
        author: 'Hegel',
        exact: true,
        yearFrom: 1800,
        yearTo: 1900,
        languages: ['german'],
        extensions: ['epub'],
        limit: 10,
      });
      expect(response).toEqual([{ title: 'Hegel Book' }]);
    });

    test('should return error object on failure', async () => {
      const mockSearchAuthor = jest.fn().mockRejectedValue(new Error('Author search failed'));
      const { toolRegistry } = await setupWithMocks({ searchByAuthor: mockSearchAuthor });

      const handler = toolRegistry.search_by_author.handler;
      const args = { author: 'Kant' };
      const validatedArgs = toolRegistry.search_by_author.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Author search failed' } });
    });
  });

  describe('fetchBooklist handler', () => {
    test('should call zlibApi.fetchBooklist with mapped args on success', async () => {
      const mockFetchList = jest.fn().mockResolvedValue({ books: [{ title: 'Listed Book' }], total: 1 });
      const { toolRegistry } = await setupWithMocks({ fetchBooklist: mockFetchList });

      const handler = toolRegistry.fetch_booklist.handler;
      const args = { booklistId: 'bl1', booklistHash: 'hash1', topic: 'philosophy', page: 2 };
      const validatedArgs = toolRegistry.fetch_booklist.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockFetchList).toHaveBeenCalledWith({
        booklistId: 'bl1',
        booklistHash: 'hash1',
        topic: 'philosophy',
        page: 2,
      });
      expect(response).toEqual({ books: [{ title: 'Listed Book' }], total: 1 });
    });

    test('should return error object on failure', async () => {
      const mockFetchList = jest.fn().mockRejectedValue(new Error('Booklist failed'));
      const { toolRegistry } = await setupWithMocks({ fetchBooklist: mockFetchList });

      const handler = toolRegistry.fetch_booklist.handler;
      const args = { booklistId: 'bl1', booklistHash: 'hash1', topic: 'test' };
      const validatedArgs = toolRegistry.fetch_booklist.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Booklist failed' } });
    });
  });

  describe('searchAdvanced handler', () => {
    test('should call zlibApi.searchAdvanced with mapped args on success', async () => {
      const mockAdvanced = jest.fn().mockResolvedValue({
        exact_matches: [{ title: 'Exact' }],
        fuzzy_matches: [{ title: 'Fuzzy' }],
      });
      const { toolRegistry } = await setupWithMocks({ searchAdvanced: mockAdvanced });

      const handler = toolRegistry.search_advanced.handler;
      const args = { query: 'being and time', exact: true, yearFrom: 1927, yearTo: 1927, count: 5 };
      const validatedArgs = toolRegistry.search_advanced.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockAdvanced).toHaveBeenCalledWith({
        query: 'being and time',
        exact: true,
        yearFrom: 1927,
        yearTo: 1927,
        count: 5,
      });
      expect(response).toEqual({
        exact_matches: [{ title: 'Exact' }],
        fuzzy_matches: [{ title: 'Fuzzy' }],
      });
    });

    test('should return error object on failure', async () => {
      const mockAdvanced = jest.fn().mockRejectedValue(new Error('Advanced search failed'));
      const { toolRegistry } = await setupWithMocks({ searchAdvanced: mockAdvanced });

      const handler = toolRegistry.search_advanced.handler;
      const args = { query: 'test' };
      const validatedArgs = toolRegistry.search_advanced.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Advanced search failed' } });
    });
  });

  describe('searchMultiSource handler', () => {
    test('should call zlibApi.searchMultiSource with mapped args on success', async () => {
      const mockMulti = jest.fn().mockResolvedValue([{ title: 'Multi Book', source: 'libgen' }]);
      const { toolRegistry } = await setupWithMocks({ searchMultiSource: mockMulti });

      const handler = toolRegistry.search_multi_source.handler;
      const args = { query: 'philosophy', source: 'libgen', count: 20 };
      const validatedArgs = toolRegistry.search_multi_source.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(mockMulti).toHaveBeenCalledWith({
        query: 'philosophy',
        source: 'libgen',
        count: 20,
      });
      expect(response).toEqual([{ title: 'Multi Book', source: 'libgen' }]);
    });

    test('should return error object on failure', async () => {
      const mockMulti = jest.fn().mockRejectedValue(new Error('Multi-source failed'));
      const { toolRegistry } = await setupWithMocks({ searchMultiSource: mockMulti });

      const handler = toolRegistry.search_multi_source.handler;
      const args = { query: 'test' };
      const validatedArgs = toolRegistry.search_multi_source.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Multi-source failed' } });
    });
  });

  describe('toolRegistry entries for newer tools', () => {
    test('search_by_term registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.search_by_term;
      expect(entry.description).toBeDefined();
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });

    test('search_by_author registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.search_by_author;
      expect(entry.description).toBeDefined();
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });

    test('fetch_booklist registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.fetch_booklist;
      expect(entry.description).toBeDefined();
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });

    test('search_advanced registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.search_advanced;
      expect(entry.description).toBeDefined();
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });

    test('search_multi_source registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.search_multi_source;
      expect(entry.description).toBeDefined();
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });

    test('get_book_metadata registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.get_book_metadata;
      expect(entry.description).toBeDefined();
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });

    test('process_document_for_rag registry entry should have description, schema, and handler', async () => {
      const { toolRegistry } = await setupWithMocks();
      const entry = toolRegistry.process_document_for_rag;
      expect(entry.description).toBeDefined();
      expect(entry.description).toContain('metadata');
      expect(entry.schema).toBeDefined();
      expect(typeof entry.handler).toBe('function');
    });
  });

  describe('Handler error message fallbacks', () => {
    test('processDocumentForRag handler should use fallback message when error has no message', async () => {
      const mockProcessDoc = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ processDocumentForRag: mockProcessDoc });

      const handler = toolRegistry.process_document_for_rag.handler;
      const args = { file_path: '/input/doc.epub' };
      const validatedArgs = toolRegistry.process_document_for_rag.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to process document for RAG' } });
    });

    test('getBookMetadata handler should use fallback message when error has no message', async () => {
      const mockGetMeta = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ getBookMetadata: mockGetMeta });

      const handler = toolRegistry.get_book_metadata.handler;
      const args = { bookId: '1', bookHash: 'h' };
      const validatedArgs = toolRegistry.get_book_metadata.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to get book metadata' } });
    });

    test('searchByTerm handler should use fallback message when error has no message', async () => {
      const mockSearchTerm = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ searchByTerm: mockSearchTerm });

      const handler = toolRegistry.search_by_term.handler;
      const args = { term: 'test' };
      const validatedArgs = toolRegistry.search_by_term.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to search by term' } });
    });

    test('searchByAuthor handler should use fallback message when error has no message', async () => {
      const mockSearchAuthor = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ searchByAuthor: mockSearchAuthor });

      const handler = toolRegistry.search_by_author.handler;
      const args = { author: 'test' };
      const validatedArgs = toolRegistry.search_by_author.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to search by author' } });
    });

    test('fetchBooklist handler should use fallback message when error has no message', async () => {
      const mockFetch = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ fetchBooklist: mockFetch });

      const handler = toolRegistry.fetch_booklist.handler;
      const args = { booklistId: 'bl1', booklistHash: 'hash1', topic: 'test' };
      const validatedArgs = toolRegistry.fetch_booklist.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to fetch booklist' } });
    });

    test('searchAdvanced handler should use fallback message when error has no message', async () => {
      const mockAdvanced = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ searchAdvanced: mockAdvanced });

      const handler = toolRegistry.search_advanced.handler;
      const args = { query: 'test' };
      const validatedArgs = toolRegistry.search_advanced.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to perform advanced search' } });
    });

    test('searchMultiSource handler should use fallback message when error has no message', async () => {
      const mockMulti = jest.fn().mockRejectedValue({});
      const { toolRegistry } = await setupWithMocks({ searchMultiSource: mockMulti });

      const handler = toolRegistry.search_multi_source.handler;
      const args = { query: 'test' };
      const validatedArgs = toolRegistry.search_multi_source.schema.parse(args);
      const response = await handler(validatedArgs);

      expect(response).toEqual({ error: { message: 'Failed to search multi-source' } });
    });
  });
});
