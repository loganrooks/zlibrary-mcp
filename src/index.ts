#!/usr/bin/env node

import { z, ZodObject, ZodRawShape } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema'; // Reverted back to named import (correct for types)
// UV Migration Note: ensureVenvReady removed - user runs `uv sync` before build
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

// Phase 3 Tool Schemas
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
// Output Schemas (MCP Best Practice - helps LLMs understand response structure)
// ============================================================================

// Reusable book schema for search results
const BookResultSchema = z.object({
  id: z.string().describe('Z-Library book ID'),
  title: z.string().describe('Book title'),
  author: z.string().optional().describe('Book author(s)'),
  year: z.string().optional().describe('Publication year'),
  publisher: z.string().optional().describe('Publisher name'),
  language: z.string().optional().describe('Book language'),
  extension: z.string().optional().describe('File format (pdf, epub, etc.)'),
  filesize: z.string().optional().describe('File size'),
  pages: z.string().optional().describe('Number of pages'),
  cover: z.string().optional().describe('Cover image URL'),
  href: z.string().optional().describe('Book detail page URL'),
  hash: z.string().optional().describe('Book hash for downloads'),
});

const SearchBooksOutputSchema = z.object({
  books: z.array(BookResultSchema).describe('Array of matching books'),
  exact_matches: z.array(BookResultSchema).optional().describe('Books matching exact query'),
  fuzzy_matches: z.array(BookResultSchema).optional().describe('Books matching fuzzy query'),
});

const FullTextSearchOutputSchema = z.object({
  books: z.array(BookResultSchema).describe('Books containing the search text'),
});

const GetDownloadHistoryOutputSchema = z.object({
  books: z.array(BookResultSchema).describe('Previously downloaded books'),
});

const GetDownloadLimitsOutputSchema = z.object({
  daily_limit: z.number().optional().describe('Daily download limit'),
  downloads_today: z.number().optional().describe('Downloads used today'),
  remaining: z.number().optional().describe('Downloads remaining today'),
});

const DownloadBookToFileOutputSchema = z.object({
  file_path: z.string().describe('Path to downloaded file'),
  processed_file_path: z.string().nullable().optional().describe('Path to RAG-processed text file (if requested)'),
  processing_error: z.string().optional().describe('Error message if RAG processing failed'),
});

const ProcessDocumentForRagOutputSchema = z.object({
  processed_file_path: z.string().nullable().describe('Path to extracted text file, or null if extraction failed'),
  content: z.array(z.string()).optional().describe('Preview of extracted content'),
});

const GetBookMetadataOutputSchema = z.object({
  id: z.string().describe('Book ID'),
  title: z.string().describe('Book title'),
  author: z.string().optional().describe('Author name'),
  description: z.string().optional().describe('Book description'),
  terms: z.array(z.string()).optional().describe('Conceptual terms/tags (60+ per book)'),
  booklists: z.array(z.object({
    id: z.string(),
    hash: z.string(),
    topic: z.string(),
  })).optional().describe('Expert-curated booklists containing this book'),
  ipfs_cid: z.string().optional().describe('IPFS content identifier'),
  rating: z.number().optional().describe('Book rating'),
});

const SearchByTermOutputSchema = z.object({
  books: z.array(BookResultSchema).describe('Books matching the conceptual term'),
  term: z.string().describe('The searched term'),
});

const SearchByAuthorOutputSchema = z.object({
  books: z.array(BookResultSchema).describe('Books by the specified author'),
  author: z.string().describe('The searched author name'),
});

const FetchBooklistOutputSchema = z.object({
  books: z.array(BookResultSchema).describe('Books in the booklist'),
  topic: z.string().describe('Booklist topic'),
  total: z.number().optional().describe('Total books in booklist'),
  page: z.number().optional().describe('Current page'),
});

const SearchAdvancedOutputSchema = z.object({
  exact_matches: z.array(BookResultSchema).describe('Books matching exact query'),
  fuzzy_matches: z.array(BookResultSchema).describe('Books matching fuzzy/approximate query'),
});

// ============================================================================
// Tool Annotations (MCP Best Practice - helps AI assistants make better decisions)
// ============================================================================

interface ToolAnnotations {
  readOnlyHint?: boolean;      // true = no side effects
  destructiveHint?: boolean;   // true = may delete/modify data
  idempotentHint?: boolean;    // true = same args produce same result
  openWorldHint?: boolean;     // true = interacts with external services
  title?: string;              // Human-readable display name
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
    idempotentHint: false,  // Results change as user downloads
    openWorldHint: true,
    title: 'Download History',
  },
  get_download_limits: {
    readOnlyHint: true,
    idempotentHint: false,  // Results change throughout the day
    openWorldHint: true,
    title: 'Download Limits',
  },
  download_book_to_file: {
    readOnlyHint: false,    // Creates files on disk
    destructiveHint: false, // Additive only (creates new files)
    idempotentHint: false,  // Downloads count against limits
    openWorldHint: true,
    title: 'Download Book',
  },
  process_document_for_rag: {
    readOnlyHint: false,    // Creates processed text files
    destructiveHint: false, // Additive only
    idempotentHint: true,   // Same file produces same output
    openWorldHint: false,   // Local file processing only
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
  },

  // Phase 3 Research Tools
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

// Define a type for the tool registry entries
// Define ToolDefinition based on usage in ListTools response
interface ToolDefinition {
    name: string;
    description?: string;
    inputSchema: any;
    outputSchema?: any;  // MCP spec 2025-06-18: optional output schema
    annotations?: ToolAnnotations;  // MCP spec 2025-06-18: optional annotations
    title?: string;  // MCP spec 2025-06-18: human-readable display name
}

interface ToolRegistryEntry {
    description: string;
    schema: ZodObject<ZodRawShape>;
    outputSchema?: ZodObject<ZodRawShape>;  // Output schema for responses
    handler?: (args: any) => Promise<any>;
}

// Tool Registry with output schemas (MCP Best Practice)
const toolRegistry: Record<string, ToolRegistryEntry> = {
  search_books: {
    description: 'Search for books in Z-Library by title, author, or keywords. Returns matching books with metadata including title, author, year, format, and file size. Use exact=true for precise title matching. Filter results by year range, language, or file format.',
    schema: SearchBooksParamsSchema,
    outputSchema: SearchBooksOutputSchema,
    handler: handlers.searchBooks,
  },
  full_text_search: {
    description: 'Search for books containing specific text within their content. Useful for finding books that discuss particular topics, quotes, or concepts. Returns books where the search text appears in the actual book content.',
    schema: FullTextSearchParamsSchema,
    outputSchema: FullTextSearchOutputSchema,
    handler: handlers.fullTextSearch,
  },
  get_download_history: {
    description: "Get the user's Z-Library download history. Returns a list of previously downloaded books with their metadata. Useful for finding books the user has already accessed.",
    schema: GetDownloadHistoryParamsSchema,
    outputSchema: GetDownloadHistoryOutputSchema,
    handler: handlers.getDownloadHistory,
  },
  get_download_limits: {
    description: "Get the user's current Z-Library download limits. Shows daily download quota, downloads used today, and remaining downloads. Check this before downloading to avoid hitting limits.",
    schema: GetDownloadLimitsParamsSchema,
    outputSchema: GetDownloadLimitsOutputSchema,
    handler: handlers.getDownloadLimits,
  },
  download_book_to_file: {
    description: 'Download a book to a local file. Pass the full bookDetails object from search_books results. Optionally process the document for RAG (text extraction) after download. Returns file paths for both the original book and processed text.',
    schema: DownloadBookToFileParamsSchema,
    outputSchema: DownloadBookToFileOutputSchema,
    handler: handlers.downloadBookToFile,
  },
  process_document_for_rag: {
    description: 'Process a downloaded document (EPUB, TXT, PDF) to extract clean text content for RAG (Retrieval-Augmented Generation). Extracts text, preserves structure, detects footnotes, and outputs a text file. Use this on already-downloaded books.',
    schema: ProcessDocumentForRagParamsSchema,
    outputSchema: ProcessDocumentForRagOutputSchema,
    handler: handlers.processDocumentForRag,
  },
  // Phase 3 Research Tools
  get_book_metadata: {
    description: 'Get complete metadata for a book including 60+ conceptual terms, 11+ expert-curated booklists, detailed descriptions, IPFS CIDs, ratings, and more. Requires bookId and bookHash from search results. Use terms to discover related books.',
    schema: GetBookMetadataParamsSchema,
    outputSchema: GetBookMetadataOutputSchema,
    handler: handlers.getBookMetadata,
  },
  search_by_term: {
    description: 'Search for books by conceptual term (e.g., "phenomenology", "dialectic", "epistemology"). Books in Z-Library are tagged with 60+ conceptual terms, enabling semantic navigation through academic concepts and topics.',
    schema: SearchByTermParamsSchema,
    outputSchema: SearchByTermOutputSchema,
    handler: handlers.searchByTerm,
  },
  search_by_author: {
    description: 'Advanced author search with support for various name formats ("Lastname, Firstname" or "Firstname Lastname"). Use exact=true for precise matching. Filter by publication year, language, or file format.',
    schema: SearchByAuthorParamsSchema,
    outputSchema: SearchByAuthorOutputSchema,
    handler: handlers.searchByAuthor,
  },
  fetch_booklist: {
    description: 'Fetch books from an expert-curated booklist. Z-Library books belong to 11+ booklists with up to 954 books per list. Get booklist IDs from get_book_metadata. Great for discovering related books on a topic.',
    schema: FetchBooklistParamsSchema,
    outputSchema: FetchBooklistOutputSchema,
    handler: handlers.fetchBooklist,
  },
  search_advanced: {
    description: 'Advanced search with automatic separation of exact matches from fuzzy/approximate matches. Returns two arrays: exact_matches (precise title/author matches) and fuzzy_matches (related results). Better for understanding result quality.',
    schema: SearchAdvancedParamsSchema,
    outputSchema: SearchAdvancedOutputSchema,
    handler: handlers.searchAdvanced,
  },
};

// Helper function to get version from package.json
function getPackageVersion(): string {
  try {
    // Use import.meta.url to find package.json relative to the current module
    // At runtime: Go up one level from dist/ to project root
    const packageJsonPath = path.resolve(__dirname, '..', 'package.json');
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

// Function to generate the tools capability object with MCP spec compliance
function generateToolsCapability(): Record<string, ToolDefinition> {
    const toolsCapability: Record<string, ToolDefinition> = {};
    for (const [name, tool] of Object.entries(toolRegistry)) {
        try {
            const inputJsonSchema = zodToJsonSchema(tool.schema);
            const annotations = toolAnnotations[name];

            const toolDef: ToolDefinition = {
                name: name,
                description: tool.description,
                inputSchema: inputJsonSchema,
            };

            // Add output schema if defined (MCP spec 2025-06-18)
            if (tool.outputSchema) {
                toolDef.outputSchema = zodToJsonSchema(tool.outputSchema);
            }

            // Add annotations if defined (MCP spec 2025-06-18)
            if (annotations) {
                toolDef.annotations = annotations;
                // Title from annotations takes precedence
                if (annotations.title) {
                    toolDef.title = annotations.title;
                }
            }

            toolsCapability[name] = toolDef;
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

    // UV Migration Note: venv management is now external via `uv sync`
    // No need to call ensureVenvReady() - venv is expected to exist
    // User must run: uv sync before building

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
        console.log(`Calling handler for tool "${toolName}"`);
        const result = await tool.handler(validationResult.data);

        // Check if the handler returned an error object itself
        if (result && typeof result === 'object' && 'error' in result && result.error) {
           console.error(`Handler for tool "${toolName}" returned error:`, result.error.message || result.error);
           return { content: [{ type: 'text', text: `Error from tool "${toolName}": ${result.error.message || result.error}` }], isError: true };
        }
        console.log(`Handler for tool "${toolName}" completed successfully.`);

        // MCP Best Practice: Return both text content AND structuredContent
        // - content[].text: Stringified JSON for backward compatibility
        // - structuredContent: Parsed object for clients that support it (MCP 2025-06-18)
        const stringifiedResult = JSON.stringify(result);
        return {
          content: [{ type: 'text', text: stringifiedResult }],
          structuredContent: result  // MCP spec 2025-06-18: structured data for modern clients
        };
      } catch (error: any) {
        // Catch errors thrown by the handler
        console.error(`Error calling tool "${toolName}":`, error);
        return { content: [{ type: 'text', text: `Error calling tool "${toolName}": ${error.message || 'Unknown error'}` }], isError: true };
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