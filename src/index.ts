#!/usr/bin/env node

import { z, ZodObject, ZodRawShape } from 'zod';
// UV Migration Note: ensureVenvReady removed - user runs `uv sync` before build
import * as fs from 'fs';
import { appendFile as appendFileAsync, mkdir as mkdirAsync } from 'fs/promises';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Import SDK components using ESM syntax
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

// Import API handlers
import * as zlibraryApi from './lib/zlibrary-api.js';

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

const GetDownloadLimitsParamsSchema = z.object({});

const GetRecentBooksParamsSchema = z.object({
  count: z.number().int().optional().default(10).describe('Number of books to return'),
  format: z.string().optional().describe('Filter by file format (e.g., "pdf", "epub")'),
});

const DownloadBookToFileParamsSchema = z.object({
  bookDetails: z.object({}).passthrough().describe('The full book details object obtained from search_books'),
  outputDir: z.string().optional().default('./downloads').describe('Directory to save the file to (default: "./downloads")'),
  process_for_rag: z.boolean().optional().describe('Whether to process the document content for RAG after download'),
  processed_output_format: z.string().optional().describe('Desired output format for RAG processing (e.g., "text", "markdown")'),
});

const ProcessDocumentForRagParamsSchema = z.object({
  file_path: z.string().describe('Path to the downloaded file to process'),
  output_format: z.string().optional().describe('Desired output format (e.g., "text", "markdown")')
});

const GetBookMetadataParamsSchema = z.object({
  bookId: z.string().describe('Z-Library book ID'),
  bookHash: z.string().describe('Book hash (can be extracted from book URL)'),
});

const SearchByTermParamsSchema = z.object({
  term: z.string().describe('Conceptual term to search for (e.g., "dialectic", "phenomenology")'),
  yearFrom: z.number().int().optional().describe('Filter by minimum publication year'),
  yearTo: z.number().int().optional().describe('Filter by maximum publication year'),
  languages: z.array(z.string()).optional().default([]).describe('Filter by languages'),
  extensions: z.array(z.string()).optional().default([]).describe('Filter by file extensions'),
  count: z.number().int().optional().default(25).describe('Number of results to return'),
});

const SearchByAuthorParamsSchema = z.object({
  author: z.string().describe('Author name (supports "Lastname, Firstname" format)'),
  exact: z.boolean().optional().default(false).describe('Use exact author name matching'),
  yearFrom: z.number().int().optional().describe('Filter by minimum publication year'),
  yearTo: z.number().int().optional().describe('Filter by maximum publication year'),
  languages: z.array(z.string()).optional().default([]).describe('Filter by languages'),
  extensions: z.array(z.string()).optional().default([]).describe('Filter by file extensions'),
  count: z.number().int().optional().default(25).describe('Number of results to return'),
});

const FetchBooklistParamsSchema = z.object({
  booklistId: z.string().describe('Booklist ID from book metadata'),
  booklistHash: z.string().describe('Booklist hash from book metadata'),
  topic: z.string().describe('Booklist topic name'),
  page: z.number().int().optional().default(1).describe('Page number for pagination'),
});

const SearchAdvancedParamsSchema = z.object({
  query: z.string().describe('Search query'),
  exact: z.boolean().optional().default(false).describe('Whether to perform exact match search'),
  yearFrom: z.number().int().optional().describe('Filter by minimum publication year'),
  yearTo: z.number().int().optional().describe('Filter by maximum publication year'),
  count: z.number().int().optional().default(10).describe('Number of results to return'),
});

// ============================================================================
// Tool Annotations (MCP Best Practice - helps AI assistants make better decisions)
// ============================================================================

interface ToolAnnotations {
  readOnlyHint?: boolean;
  destructiveHint?: boolean;
  idempotentHint?: boolean;
  openWorldHint?: boolean;
  title?: string;
}

const toolAnnotations: Record<string, ToolAnnotations> = {
  search_books: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Search Books',
  },
  full_text_search: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Full Text Search',
  },
  get_download_history: {
    readOnlyHint: true,
    idempotentHint: false,
    openWorldHint: true,
    title: 'Download History',
  },
  get_download_limits: {
    readOnlyHint: true,
    idempotentHint: false,
    openWorldHint: true,
    title: 'Download Limits',
  },
  download_book_to_file: {
    readOnlyHint: false,
    destructiveHint: false,
    idempotentHint: false,
    openWorldHint: true,
    title: 'Download Book',
  },
  process_document_for_rag: {
    readOnlyHint: false,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: false,
    title: 'Process for RAG',
  },
  get_book_metadata: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Book Metadata',
  },
  search_by_term: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Search by Term',
  },
  search_by_author: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Search by Author',
  },
  fetch_booklist: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Fetch Booklist',
  },
  search_advanced: {
    readOnlyHint: true,
    idempotentHint: true,
    openWorldHint: true,
    title: 'Advanced Search',
  },
};

// ============================================================================
// Tool handler implementations
// ============================================================================

interface HandlerMap {
    [key: string]: (args: any) => Promise<any>;
    searchBooks: (args: any) => Promise<any>;
    fullTextSearch: (args: any) => Promise<any>;
    getDownloadHistory: (args: any) => Promise<any>;
    getDownloadLimits: (args: any) => Promise<any>;
    downloadBookToFile: (args: any) => Promise<any>;
    processDocumentForRag: (args: any) => Promise<any>;
    getBookMetadata: (args: any) => Promise<any>;
    searchByTerm: (args: any) => Promise<any>;
    searchByAuthor: (args: any) => Promise<any>;
    fetchBooklist: (args: any) => Promise<any>;
    searchAdvanced: (args: any) => Promise<any>;
}

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
      const apiArgs = {
        query: args.query,
        exact: args.exact,
        fromYear: args.fromYear,
        toYear: args.toYear,
        languages: args.languages,
        extensions: args.extensions,
        content_types: args.content_types,
        count: args.count,
      };
      const searchBooksSendingLog = `[${new Date().toISOString()}] [src/index.ts] searchBooks handler sending to zlibraryApi: ${JSON.stringify(apiArgs)}\n`;
      console.log(searchBooksSendingLog.trim());
      try {
        const logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
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
      const apiArgsFTS = {
        query: args.query,
        exact: args.exact,
        phrase: args.phrase,
        words: args.words,
        languages: args.languages,
        extensions: args.extensions,
        content_types: args.content_types,
        count: args.count,
      };
      const ftsSendingLog = `[${new Date().toISOString()}] [src/index.ts] fullTextSearch handler sending to zlibraryApi: ${JSON.stringify(apiArgsFTS)}\n`;
      console.log(ftsSendingLog.trim());
      try {
        const logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
        await appendFileAsync(logFilePath, ftsSendingLog);
      } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
      return await zlibraryApi.fullTextSearch(apiArgsFTS);
    } catch (error: any) { return { error: { message: error.message || 'Failed to perform full text search' } }; }
  },

  getDownloadHistory: async (args: z.infer<typeof GetDownloadHistoryParamsSchema>) => {
    try {
        return await zlibraryApi.getDownloadHistory(args);
    }
    catch (error: any) { return { error: { message: error.message || 'Failed to get download history' } }; }
  },

  getDownloadLimits: async () => {
    try {
        return await zlibraryApi.getDownloadLimits();
    }
    catch (error: any) { return { error: { message: error.message || 'Failed to get download limits' } }; }
  },

  downloadBookToFile: async (args: z.infer<typeof DownloadBookToFileParamsSchema>) => {
    try {
      return await zlibraryApi.downloadBookToFile(args);
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to download book' } };
    }
  },

  processDocumentForRag: async (args: z.infer<typeof ProcessDocumentForRagParamsSchema>) => {
    try {
      return await zlibraryApi.processDocumentForRag({ filePath: args.file_path, outputFormat: args.output_format });
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to process document for RAG' } };
    }
  },

  getBookMetadata: async (args: z.infer<typeof GetBookMetadataParamsSchema>) => {
    try {
      return await zlibraryApi.getBookMetadata(args.bookId, args.bookHash);
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to get book metadata' } };
    }
  },

  searchByTerm: async (args: z.infer<typeof SearchByTermParamsSchema>) => {
    try {
      return await zlibraryApi.searchByTerm({
        term: args.term,
        yearFrom: args.yearFrom,
        yearTo: args.yearTo,
        languages: args.languages,
        extensions: args.extensions,
        limit: args.count
      });
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to search by term' } };
    }
  },

  searchByAuthor: async (args: z.infer<typeof SearchByAuthorParamsSchema>) => {
    try {
      return await zlibraryApi.searchByAuthor({
        author: args.author,
        exact: args.exact,
        yearFrom: args.yearFrom,
        yearTo: args.yearTo,
        languages: args.languages,
        extensions: args.extensions,
        limit: args.count
      });
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to search by author' } };
    }
  },

  fetchBooklist: async (args: z.infer<typeof FetchBooklistParamsSchema>) => {
    try {
      return await zlibraryApi.fetchBooklist({
        booklistId: args.booklistId,
        booklistHash: args.booklistHash,
        topic: args.topic,
        page: args.page
      });
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to fetch booklist' } };
    }
  },

  searchAdvanced: async (args: z.infer<typeof SearchAdvancedParamsSchema>) => {
    try {
      return await zlibraryApi.searchAdvanced({
        query: args.query,
        exact: args.exact,
        yearFrom: args.yearFrom,
        yearTo: args.yearTo,
        count: args.count
      });
    } catch (error: any) {
      return { error: { message: error.message || 'Failed to perform advanced search' } };
    }
  }
};

// ============================================================================
// Legacy compatibility exports (used by existing tests - will be updated in 03-02)
// ============================================================================

interface ToolRegistryEntry {
    description: string;
    schema: ZodObject<ZodRawShape>;
    handler?: (args: any) => Promise<any>;
}

const toolRegistry: Record<string, ToolRegistryEntry> = {
  search_books: { description: 'Search for books in Z-Library', schema: SearchBooksParamsSchema, handler: handlers.searchBooks },
  full_text_search: { description: 'Full text search in book content', schema: FullTextSearchParamsSchema, handler: handlers.fullTextSearch },
  get_download_history: { description: 'Get download history', schema: GetDownloadHistoryParamsSchema, handler: handlers.getDownloadHistory },
  get_download_limits: { description: 'Get download limits', schema: GetDownloadLimitsParamsSchema, handler: handlers.getDownloadLimits },
  get_recent_books: { description: 'Get recently added books', schema: GetRecentBooksParamsSchema },
  download_book_to_file: { description: 'Download a book to file', schema: DownloadBookToFileParamsSchema, handler: handlers.downloadBookToFile },
  process_document_for_rag: { description: 'Process document for RAG', schema: ProcessDocumentForRagParamsSchema, handler: handlers.processDocumentForRag },
  get_book_metadata: { description: 'Get book metadata', schema: GetBookMetadataParamsSchema, handler: handlers.getBookMetadata },
  search_by_term: { description: 'Search by conceptual term', schema: SearchByTermParamsSchema, handler: handlers.searchByTerm },
  search_by_author: { description: 'Search by author', schema: SearchByAuthorParamsSchema, handler: handlers.searchByAuthor },
  fetch_booklist: { description: 'Fetch booklist', schema: FetchBooklistParamsSchema, handler: handlers.fetchBooklist },
  search_advanced: { description: 'Advanced search', schema: SearchAdvancedParamsSchema, handler: handlers.searchAdvanced },
};

// ============================================================================
// Helper functions
// ============================================================================

function getPackageVersion(): string {
  try {
    const packageJsonPath = path.resolve(__dirname, '..', 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    return packageJson.version || 'unknown';
  } catch (error: any) {
    console.warn('Could not read package.json for version:', error.message);
    return 'unknown';
  }
}

// Helper to wrap handler results in MCP content format
function wrapResult(result: any, toolName: string) {
  if (result && typeof result === 'object' && 'error' in result && result.error) {
    return {
      content: [{ type: 'text' as const, text: `Error from tool "${toolName}": ${result.error.message || result.error}` }],
      isError: true as const,
    };
  }
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(result) }],
    structuredContent: result,
  };
}

// ============================================================================
// Server setup
// ============================================================================

interface StartOptions {
    testing?: boolean;
}

async function start(opts: StartOptions = {}): Promise<{ server: McpServer; transport: StdioServerTransport } | null> {
  try {
    // Ensure the logs directory exists
    try {
      await mkdirAsync(path.resolve(__dirname, '..', 'logs'), { recursive: true });
      console.log("Log directory 'logs/' ensured.");
    } catch (dirError: any) {
      console.error("Failed to create 'logs/' directory:", dirError.message);
    }

    // Instantiate the McpServer
    const server = new McpServer({
      name: 'zlibrary-mcp',
      version: getPackageVersion(),
    });

    // ========================================================================
    // Register all 12 tools via server.tool()
    // ========================================================================

    // Helper to get annotations with proper typing
    const ann = (name: string) => toolAnnotations[name] as ToolAnnotations;

    // 1. search_books
    server.tool('search_books',
      'Search for books in Z-Library by title, author, or keywords. Returns matching books with metadata including title, author, year, format, and file size. Use exact=true for precise title matching. Filter results by year range, language, or file format.',
      SearchBooksParamsSchema.shape, ann('search_books'),
      async (args) => wrapResult(await handlers.searchBooks(args as any), 'search_books'));

    // 2. full_text_search
    server.tool('full_text_search',
      'Search for books containing specific text within their content. Useful for finding books that discuss particular topics, quotes, or concepts. Returns books where the search text appears in the actual book content.',
      FullTextSearchParamsSchema.shape, ann('full_text_search'),
      async (args) => wrapResult(await handlers.fullTextSearch(args as any), 'full_text_search'));

    // 3. get_download_history
    server.tool('get_download_history',
      "Get the user's Z-Library download history. Returns a list of previously downloaded books with their metadata.",
      GetDownloadHistoryParamsSchema.shape, ann('get_download_history'),
      async (args) => wrapResult(await handlers.getDownloadHistory(args as any), 'get_download_history'));

    // 4. get_download_limits
    server.tool('get_download_limits',
      "Get the user's current Z-Library download limits. Shows daily download quota, downloads used today, and remaining downloads.",
      GetDownloadLimitsParamsSchema.shape, ann('get_download_limits'),
      async (_args) => wrapResult(await handlers.getDownloadLimits(_args), 'get_download_limits'));

    // 5. get_recent_books
    server.tool('get_recent_books',
      'Get recently added books to Z-Library. Optionally filter by file format.',
      GetRecentBooksParamsSchema.shape, ann('search_books'),
      async (args) => {
        try {
          const result = await (zlibraryApi as any).getRecentBooks(args);
          return wrapResult(result, 'get_recent_books');
        } catch (error: any) {
          return { content: [{ type: 'text' as const, text: `Error: ${error.message}` }], isError: true };
        }
      });

    // 6. download_book_to_file
    server.tool('download_book_to_file',
      'Download a book to a local file. Pass the full bookDetails object from search_books results. Optionally process the document for RAG (text extraction) after download. Returns file paths for both the original book and processed text.',
      DownloadBookToFileParamsSchema.shape, ann('download_book_to_file'),
      async (args) => wrapResult(await handlers.downloadBookToFile(args as any), 'download_book_to_file'));

    // 7. process_document_for_rag
    server.tool('process_document_for_rag',
      'Process a downloaded document (EPUB, TXT, PDF) to extract clean text content for RAG (Retrieval-Augmented Generation). Extracts text, preserves structure, detects footnotes, and outputs a text file.',
      ProcessDocumentForRagParamsSchema.shape, ann('process_document_for_rag'),
      async (args) => wrapResult(await handlers.processDocumentForRag(args as any), 'process_document_for_rag'));

    // 8. get_book_metadata
    server.tool('get_book_metadata',
      'Get complete metadata for a book including 60+ conceptual terms, 11+ expert-curated booklists, detailed descriptions, IPFS CIDs, ratings, and more. Requires bookId and bookHash from search results.',
      GetBookMetadataParamsSchema.shape, ann('get_book_metadata'),
      async (args) => wrapResult(await handlers.getBookMetadata(args as any), 'get_book_metadata'));

    // 9. search_by_term
    server.tool('search_by_term',
      'Search for books by conceptual term (e.g., "phenomenology", "dialectic", "epistemology"). Books in Z-Library are tagged with 60+ conceptual terms.',
      SearchByTermParamsSchema.shape, ann('search_by_term'),
      async (args) => wrapResult(await handlers.searchByTerm(args as any), 'search_by_term'));

    // 10. search_by_author
    server.tool('search_by_author',
      'Advanced author search with support for various name formats. Use exact=true for precise matching. Filter by publication year, language, or file format.',
      SearchByAuthorParamsSchema.shape, ann('search_by_author'),
      async (args) => wrapResult(await handlers.searchByAuthor(args as any), 'search_by_author'));

    // 11. fetch_booklist
    server.tool('fetch_booklist',
      'Fetch books from an expert-curated booklist. Z-Library books belong to 11+ booklists with up to 954 books per list. Get booklist IDs from get_book_metadata.',
      FetchBooklistParamsSchema.shape, ann('fetch_booklist'),
      async (args) => wrapResult(await handlers.fetchBooklist(args as any), 'fetch_booklist'));

    // 12. search_advanced
    server.tool('search_advanced',
      'Advanced search with automatic separation of exact matches from fuzzy/approximate matches. Returns two arrays: exact_matches and fuzzy_matches.',
      SearchAdvancedParamsSchema.shape, ann('search_advanced'),
      async (args) => wrapResult(await handlers.searchAdvanced(args as any), 'search_advanced'));

    // Create and connect the Stdio transport
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.log('Z-Library MCP server (ESM/TS) is running via Stdio...');

    return { server, transport };
  } catch (error: any) {
    console.error('Failed to start MCP server:', error);

    if (opts.testing !== true) {
      process.exit(1);
    }
    return null;
  }
}

// Auto-start logic
if (import.meta.url === `file://${process.argv[1]}`) {
  start().catch(err => {
    console.error("Fatal error starting server:", err);
    process.exit(1);
  });
}

// Export necessary components for testing
export { start, handlers, toolRegistry };
