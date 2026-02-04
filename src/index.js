#!/usr/bin/env node
"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.toolRegistry = exports.handlers = void 0;
exports.start = start;
var zod_1 = require("zod");
// UV Migration Note: ensureVenvReady removed - user runs `uv sync` before build
var fs = require("fs");
var promises_1 = require("fs/promises");
var path = require("path");
var url_1 = require("url");
// Import SDK components using ESM syntax
var mcp_js_1 = require("@modelcontextprotocol/sdk/server/mcp.js");
var stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
// Import API handlers
var zlibraryApi = require("./lib/zlibrary-api.js");
// Recreate __dirname for ESM
var __filename = (0, url_1.fileURLToPath)(import.meta.url);
var __dirname = path.dirname(__filename);
// Define Zod schemas for tool parameters
var SearchBooksParamsSchema = zod_1.z.object({
    query: zod_1.z.string().describe('Search query'),
    exact: zod_1.z.boolean().optional().default(false).describe('Whether to perform an exact match search'),
    fromYear: zod_1.z.number().int().optional().describe('Filter by minimum publication year'),
    toYear: zod_1.z.number().int().optional().describe('Filter by maximum publication year'),
    languages: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by languages (e.g., ["english", "russian"])'),
    extensions: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by file extensions (e.g., ["pdf", "epub"])'),
    content_types: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by content types (e.g., ["book", "article"])'),
    count: zod_1.z.number().int().optional().default(10).describe('Number of results to return per page'),
});
var FullTextSearchParamsSchema = zod_1.z.object({
    query: zod_1.z.string().describe('Text to search for in book content'),
    exact: zod_1.z.boolean().optional().default(false).describe('Whether to perform an exact match search'),
    phrase: zod_1.z.boolean().optional().default(true).describe('Whether to search for the exact phrase (requires at least 2 words)'),
    words: zod_1.z.boolean().optional().default(false).describe('Whether to search for individual words'),
    languages: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by languages (e.g., ["english", "russian"])'),
    extensions: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by file extensions (e.g., ["pdf", "epub"])'),
    content_types: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by content types (e.g., ["book", "article"])'),
    count: zod_1.z.number().int().optional().default(10).describe('Number of results to return per page'),
});
var GetDownloadHistoryParamsSchema = zod_1.z.object({
    count: zod_1.z.number().int().optional().default(10).describe('Number of results to return'),
});
var GetDownloadLimitsParamsSchema = zod_1.z.object({});
var GetRecentBooksParamsSchema = zod_1.z.object({
    count: zod_1.z.number().int().optional().default(10).describe('Number of books to return'),
    format: zod_1.z.string().optional().describe('Filter by file format (e.g., "pdf", "epub")'),
});
var DownloadBookToFileParamsSchema = zod_1.z.object({
    bookDetails: zod_1.z.object({}).passthrough().describe('The full book details object obtained from search_books'),
    outputDir: zod_1.z.string().optional().default('./downloads').describe('Directory to save the file to (default: "./downloads")'),
    process_for_rag: zod_1.z.boolean().optional().describe('Whether to process the document content for RAG after download'),
    processed_output_format: zod_1.z.string().optional().describe('Desired output format for RAG processing (e.g., "text", "markdown")'),
});
var ProcessDocumentForRagParamsSchema = zod_1.z.object({
    file_path: zod_1.z.string().describe('Path to the downloaded file to process'),
    output_format: zod_1.z.string().optional().describe('Desired output format (e.g., "text", "markdown")')
});
var GetBookMetadataParamsSchema = zod_1.z.object({
    bookId: zod_1.z.string().describe('Z-Library book ID'),
    bookHash: zod_1.z.string().describe('Book hash (can be extracted from book URL)'),
    include: zod_1.z.array(zod_1.z.enum(['terms', 'booklists', 'ipfs', 'ratings', 'description'])).optional()
        .describe('Optional field groups to include beyond core defaults. Core always includes: title, author, year, publisher, language, pages, isbn, rating, cover, categories, extension, filesize. Use include to add: terms (conceptual keywords), booklists (curated collections), ipfs (IPFS CIDs), ratings (quality_score), description (full text description).'),
});
var SearchByTermParamsSchema = zod_1.z.object({
    term: zod_1.z.string().describe('Conceptual term to search for (e.g., "dialectic", "phenomenology")'),
    yearFrom: zod_1.z.number().int().optional().describe('Filter by minimum publication year'),
    yearTo: zod_1.z.number().int().optional().describe('Filter by maximum publication year'),
    languages: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by languages'),
    extensions: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by file extensions'),
    count: zod_1.z.number().int().optional().default(25).describe('Number of results to return'),
});
var SearchByAuthorParamsSchema = zod_1.z.object({
    author: zod_1.z.string().describe('Author name (supports "Lastname, Firstname" format)'),
    exact: zod_1.z.boolean().optional().default(false).describe('Use exact author name matching'),
    yearFrom: zod_1.z.number().int().optional().describe('Filter by minimum publication year'),
    yearTo: zod_1.z.number().int().optional().describe('Filter by maximum publication year'),
    languages: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by languages'),
    extensions: zod_1.z.array(zod_1.z.string()).optional().default([]).describe('Filter by file extensions'),
    count: zod_1.z.number().int().optional().default(25).describe('Number of results to return'),
});
var FetchBooklistParamsSchema = zod_1.z.object({
    booklistId: zod_1.z.string().describe('Booklist ID from book metadata'),
    booklistHash: zod_1.z.string().describe('Booklist hash from book metadata'),
    topic: zod_1.z.string().describe('Booklist topic name'),
    page: zod_1.z.number().int().optional().default(1).describe('Page number for pagination'),
});
var SearchAdvancedParamsSchema = zod_1.z.object({
    query: zod_1.z.string().describe('Search query'),
    exact: zod_1.z.boolean().optional().default(false).describe('Whether to perform exact match search'),
    yearFrom: zod_1.z.number().int().optional().describe('Filter by minimum publication year'),
    yearTo: zod_1.z.number().int().optional().describe('Filter by maximum publication year'),
    count: zod_1.z.number().int().optional().default(10).describe('Number of results to return'),
});
var SearchMultiSourceParamsSchema = zod_1.z.object({
    query: zod_1.z.string().describe('Search query'),
    source: zod_1.z.enum(['auto', 'annas', 'libgen']).optional().default('auto').describe('Source selection: auto (Anna\'s Archive if key available, else LibGen), annas (force Anna\'s Archive), or libgen (force LibGen)'),
    count: zod_1.z.number().int().optional().default(10).describe('Maximum number of results to return'),
});
var toolAnnotations = {
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
    search_multi_source: {
        readOnlyHint: true,
        idempotentHint: true,
        openWorldHint: true,
        title: 'Multi-Source Search',
    },
};
var handlers = {
    searchBooks: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var searchBooksReceivedArgsLog, logFilePath, e_1, apiArgs, searchBooksSendingLog, logFilePath, e_2, error_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 11, , 12]);
                    searchBooksReceivedArgsLog = "[".concat(new Date().toISOString(), "] [src/index.ts] searchBooks handler received Zod-parsed args: ").concat(JSON.stringify(args), "\n");
                    console.log(searchBooksReceivedArgsLog.trim());
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 4, , 5]);
                    logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
                    return [4 /*yield*/, (0, promises_1.mkdir)(path.dirname(logFilePath), { recursive: true })];
                case 2:
                    _a.sent();
                    return [4 /*yield*/, (0, promises_1.appendFile)(logFilePath, searchBooksReceivedArgsLog)];
                case 3:
                    _a.sent();
                    return [3 /*break*/, 5];
                case 4:
                    e_1 = _a.sent();
                    console.error('Failed to write to logs/nodejs_debug.log', e_1);
                    return [3 /*break*/, 5];
                case 5:
                    apiArgs = {
                        query: args.query,
                        exact: args.exact,
                        fromYear: args.fromYear,
                        toYear: args.toYear,
                        languages: args.languages,
                        extensions: args.extensions,
                        content_types: args.content_types,
                        count: args.count,
                    };
                    searchBooksSendingLog = "[".concat(new Date().toISOString(), "] [src/index.ts] searchBooks handler sending to zlibraryApi: ").concat(JSON.stringify(apiArgs), "\n");
                    console.log(searchBooksSendingLog.trim());
                    _a.label = 6;
                case 6:
                    _a.trys.push([6, 8, , 9]);
                    logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
                    return [4 /*yield*/, (0, promises_1.appendFile)(logFilePath, searchBooksSendingLog)];
                case 7:
                    _a.sent();
                    return [3 /*break*/, 9];
                case 8:
                    e_2 = _a.sent();
                    console.error('Failed to write to logs/nodejs_debug.log', e_2);
                    return [3 /*break*/, 9];
                case 9: return [4 /*yield*/, zlibraryApi.searchBooks(apiArgs)];
                case 10: return [2 /*return*/, _a.sent()];
                case 11:
                    error_1 = _a.sent();
                    return [2 /*return*/, { error: { message: error_1.message || 'Failed to search books' } }];
                case 12: return [2 /*return*/];
            }
        });
    }); },
    fullTextSearch: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var ftsReceivedArgsLog, logFilePath, e_3, apiArgsFTS, ftsSendingLog, logFilePath, e_4, error_2;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 11, , 12]);
                    ftsReceivedArgsLog = "[".concat(new Date().toISOString(), "] [src/index.ts] fullTextSearch handler received Zod-parsed args: ").concat(JSON.stringify(args), "\n");
                    console.log(ftsReceivedArgsLog.trim());
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 4, , 5]);
                    logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
                    return [4 /*yield*/, (0, promises_1.mkdir)(path.dirname(logFilePath), { recursive: true })];
                case 2:
                    _a.sent();
                    return [4 /*yield*/, (0, promises_1.appendFile)(logFilePath, ftsReceivedArgsLog)];
                case 3:
                    _a.sent();
                    return [3 /*break*/, 5];
                case 4:
                    e_3 = _a.sent();
                    console.error('Failed to write to logs/nodejs_debug.log', e_3);
                    return [3 /*break*/, 5];
                case 5:
                    apiArgsFTS = {
                        query: args.query,
                        exact: args.exact,
                        phrase: args.phrase,
                        words: args.words,
                        languages: args.languages,
                        extensions: args.extensions,
                        content_types: args.content_types,
                        count: args.count,
                    };
                    ftsSendingLog = "[".concat(new Date().toISOString(), "] [src/index.ts] fullTextSearch handler sending to zlibraryApi: ").concat(JSON.stringify(apiArgsFTS), "\n");
                    console.log(ftsSendingLog.trim());
                    _a.label = 6;
                case 6:
                    _a.trys.push([6, 8, , 9]);
                    logFilePath = path.resolve(__dirname, '..', 'logs', 'nodejs_debug.log');
                    return [4 /*yield*/, (0, promises_1.appendFile)(logFilePath, ftsSendingLog)];
                case 7:
                    _a.sent();
                    return [3 /*break*/, 9];
                case 8:
                    e_4 = _a.sent();
                    console.error('Failed to write to logs/nodejs_debug.log', e_4);
                    return [3 /*break*/, 9];
                case 9: return [4 /*yield*/, zlibraryApi.fullTextSearch(apiArgsFTS)];
                case 10: return [2 /*return*/, _a.sent()];
                case 11:
                    error_2 = _a.sent();
                    return [2 /*return*/, { error: { message: error_2.message || 'Failed to perform full text search' } }];
                case 12: return [2 /*return*/];
            }
        });
    }); },
    getDownloadHistory: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_3;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.getDownloadHistory(args)];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_3 = _a.sent();
                    return [2 /*return*/, { error: { message: error_3.message || 'Failed to get download history' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    getDownloadLimits: function () { return __awaiter(void 0, void 0, void 0, function () {
        var error_4;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.getDownloadLimits()];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_4 = _a.sent();
                    return [2 /*return*/, { error: { message: error_4.message || 'Failed to get download limits' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    downloadBookToFile: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_5;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.downloadBookToFile(args)];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_5 = _a.sent();
                    return [2 /*return*/, { error: { message: error_5.message || 'Failed to download book' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    processDocumentForRag: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_6;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.processDocumentForRag({ filePath: args.file_path, outputFormat: args.output_format })];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_6 = _a.sent();
                    return [2 /*return*/, { error: { message: error_6.message || 'Failed to process document for RAG' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    getBookMetadata: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_7;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.getBookMetadata(args.bookId, args.bookHash, args.include)];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_7 = _a.sent();
                    return [2 /*return*/, { error: { message: error_7.message || 'Failed to get book metadata' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    searchByTerm: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_8;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.searchByTerm({
                            term: args.term,
                            yearFrom: args.yearFrom,
                            yearTo: args.yearTo,
                            languages: args.languages,
                            extensions: args.extensions,
                            limit: args.count
                        })];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_8 = _a.sent();
                    return [2 /*return*/, { error: { message: error_8.message || 'Failed to search by term' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    searchByAuthor: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_9;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.searchByAuthor({
                            author: args.author,
                            exact: args.exact,
                            yearFrom: args.yearFrom,
                            yearTo: args.yearTo,
                            languages: args.languages,
                            extensions: args.extensions,
                            limit: args.count
                        })];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_9 = _a.sent();
                    return [2 /*return*/, { error: { message: error_9.message || 'Failed to search by author' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    fetchBooklist: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_10;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.fetchBooklist({
                            booklistId: args.booklistId,
                            booklistHash: args.booklistHash,
                            topic: args.topic,
                            page: args.page
                        })];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_10 = _a.sent();
                    return [2 /*return*/, { error: { message: error_10.message || 'Failed to fetch booklist' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    searchAdvanced: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_11;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.searchAdvanced({
                            query: args.query,
                            exact: args.exact,
                            yearFrom: args.yearFrom,
                            yearTo: args.yearTo,
                            count: args.count
                        })];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_11 = _a.sent();
                    return [2 /*return*/, { error: { message: error_11.message || 'Failed to perform advanced search' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); },
    searchMultiSource: function (args) { return __awaiter(void 0, void 0, void 0, function () {
        var error_12;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 2, , 3]);
                    return [4 /*yield*/, zlibraryApi.searchMultiSource({
                            query: args.query,
                            source: args.source,
                            count: args.count
                        })];
                case 1: return [2 /*return*/, _a.sent()];
                case 2:
                    error_12 = _a.sent();
                    return [2 /*return*/, { error: { message: error_12.message || 'Failed to search multi-source' } }];
                case 3: return [2 /*return*/];
            }
        });
    }); }
};
exports.handlers = handlers;
var toolRegistry = {
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
    search_multi_source: { description: 'Multi-source search', schema: SearchMultiSourceParamsSchema, handler: handlers.searchMultiSource },
};
exports.toolRegistry = toolRegistry;
// ============================================================================
// Helper functions
// ============================================================================
function getPackageVersion() {
    try {
        var packageJsonPath = path.resolve(__dirname, '..', 'package.json');
        var packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
        return packageJson.version || 'unknown';
    }
    catch (error) {
        console.warn('Could not read package.json for version:', error.message);
        return 'unknown';
    }
}
// Helper to wrap handler results in MCP content format
function wrapResult(result, toolName) {
    if (result && typeof result === 'object' && 'error' in result && result.error) {
        return {
            content: [{ type: 'text', text: "Error from tool \"".concat(toolName, "\": ").concat(result.error.message || result.error) }],
            isError: true,
        };
    }
    return {
        content: [{ type: 'text', text: JSON.stringify(result) }],
        structuredContent: result,
    };
}
function start() {
    return __awaiter(this, arguments, void 0, function (opts) {
        var dirError_1, server, ann, transport, error_13;
        var _this = this;
        if (opts === void 0) { opts = {}; }
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    _a.trys.push([0, 6, , 7]);
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 3, , 4]);
                    return [4 /*yield*/, (0, promises_1.mkdir)(path.resolve(__dirname, '..', 'logs'), { recursive: true })];
                case 2:
                    _a.sent();
                    console.log("Log directory 'logs/' ensured.");
                    return [3 /*break*/, 4];
                case 3:
                    dirError_1 = _a.sent();
                    console.error("Failed to create 'logs/' directory:", dirError_1.message);
                    return [3 /*break*/, 4];
                case 4:
                    server = new mcp_js_1.McpServer({
                        name: 'zlibrary-mcp',
                        version: getPackageVersion(),
                    });
                    ann = function (name) { return toolAnnotations[name]; };
                    // 1. search_books
                    server.tool('search_books', 'Search for books in Z-Library by title, author, or keywords. Returns matching books with metadata including title (string), author (string), name, authors (array), year, format, and file size. Use exact=true for precise title matching. Filter results by year range, language, or file format.', SearchBooksParamsSchema.shape, ann('search_books'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.searchBooks(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'search_books'])];
                        }
                    }); }); });
                    // 2. full_text_search
                    server.tool('full_text_search', 'Search for books containing specific text within their content. Returns books with title (string), author (string), name, authors (array), and other metadata. Useful for finding books that discuss particular topics, quotes, or concepts.', FullTextSearchParamsSchema.shape, ann('full_text_search'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.fullTextSearch(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'full_text_search'])];
                        }
                    }); }); });
                    // 3. get_download_history
                    server.tool('get_download_history', "Get the user's Z-Library download history. Returns a list of previously downloaded books with their metadata.", GetDownloadHistoryParamsSchema.shape, ann('get_download_history'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.getDownloadHistory(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'get_download_history'])];
                        }
                    }); }); });
                    // 4. get_download_limits
                    server.tool('get_download_limits', "Get the user's current Z-Library download limits. Shows daily download quota, downloads used today, and remaining downloads.", GetDownloadLimitsParamsSchema.shape, ann('get_download_limits'), function (_args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.getDownloadLimits(_args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'get_download_limits'])];
                        }
                    }); }); });
                    // 5. get_recent_books
                    server.tool('get_recent_books', 'Get recently added books to Z-Library. Optionally filter by file format.', GetRecentBooksParamsSchema.shape, ann('search_books'), function (args) { return __awaiter(_this, void 0, void 0, function () {
                        var result, error_14;
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    _a.trys.push([0, 2, , 3]);
                                    return [4 /*yield*/, zlibraryApi.getRecentBooks(args)];
                                case 1:
                                    result = _a.sent();
                                    return [2 /*return*/, wrapResult(result, 'get_recent_books')];
                                case 2:
                                    error_14 = _a.sent();
                                    return [2 /*return*/, { content: [{ type: 'text', text: "Error: ".concat(error_14.message) }], isError: true }];
                                case 3: return [2 /*return*/];
                            }
                        });
                    }); });
                    // 6. download_book_to_file
                    server.tool('download_book_to_file', 'Download a book to a local file. Pass the full bookDetails object from search_books results. Optionally process the document for RAG (text extraction) after download. Returns file paths for both the original book and processed text.', DownloadBookToFileParamsSchema.shape, ann('download_book_to_file'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.downloadBookToFile(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'download_book_to_file'])];
                        }
                    }); }); });
                    // 7. process_document_for_rag
                    server.tool('process_document_for_rag', 'Process a downloaded document (EPUB, TXT, PDF) to extract clean text content for RAG (Retrieval-Augmented Generation). Extracts text, preserves structure, detects footnotes, and outputs a text file.', ProcessDocumentForRagParamsSchema.shape, ann('process_document_for_rag'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.processDocumentForRag(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'process_document_for_rag'])];
                        }
                    }); }); });
                    // 8. get_book_metadata
                    server.tool('get_book_metadata', 'Get metadata for a book. By default returns core fields (title, author, year, publisher, language, pages, isbn, rating, cover, categories). Use the include parameter to add optional field groups: terms (60+ conceptual keywords), booklists (11+ curated collections), ipfs (IPFS CIDs), ratings (quality score), description (full text). Requires bookId and bookHash from search results.', GetBookMetadataParamsSchema.shape, ann('get_book_metadata'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.getBookMetadata(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'get_book_metadata'])];
                        }
                    }); }); });
                    // 9. search_by_term
                    server.tool('search_by_term', 'Search for books by conceptual term (e.g., "phenomenology", "dialectic", "epistemology"). Returns books with title (string), author (string), and other metadata. Books in Z-Library are tagged with 60+ conceptual terms.', SearchByTermParamsSchema.shape, ann('search_by_term'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.searchByTerm(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'search_by_term'])];
                        }
                    }); }); });
                    // 10. search_by_author
                    server.tool('search_by_author', 'Advanced author search with support for various name formats. Returns books with title (string), author (string), and other metadata. Use exact=true for precise matching. Filter by publication year, language, or file format.', SearchByAuthorParamsSchema.shape, ann('search_by_author'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.searchByAuthor(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'search_by_author'])];
                        }
                    }); }); });
                    // 11. fetch_booklist
                    server.tool('fetch_booklist', 'Fetch books from an expert-curated booklist. Z-Library books belong to 11+ booklists with up to 954 books per list. Get booklist IDs from get_book_metadata.', FetchBooklistParamsSchema.shape, ann('fetch_booklist'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.fetchBooklist(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'fetch_booklist'])];
                        }
                    }); }); });
                    // 12. search_advanced
                    server.tool('search_advanced', 'Advanced search with automatic separation of exact matches from fuzzy/approximate matches. Returns two arrays: exact_matches and fuzzy_matches, each containing books with title (string), author (string), and other metadata.', SearchAdvancedParamsSchema.shape, ann('search_advanced'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.searchAdvanced(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'search_advanced'])];
                        }
                    }); }); });
                    // 13. search_multi_source
                    server.tool('search_multi_source', 'Search for books across Anna\'s Archive and LibGen. Alternative to Z-Library EAPI. Returns books with md5, title, author, year, extension, size, source, download_url. Use source=auto to prefer Anna\'s Archive with LibGen fallback, or force a specific source.', SearchMultiSourceParamsSchema.shape, ann('search_multi_source'), function (args) { return __awaiter(_this, void 0, void 0, function () { var _a; return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                _a = wrapResult;
                                return [4 /*yield*/, handlers.searchMultiSource(args)];
                            case 1: return [2 /*return*/, _a.apply(void 0, [_b.sent(), 'search_multi_source'])];
                        }
                    }); }); });
                    transport = new stdio_js_1.StdioServerTransport();
                    return [4 /*yield*/, server.connect(transport)];
                case 5:
                    _a.sent();
                    console.log('Z-Library MCP server (ESM/TS) is running via Stdio...');
                    return [2 /*return*/, { server: server, transport: transport }];
                case 6:
                    error_13 = _a.sent();
                    console.error('Failed to start MCP server:', error_13);
                    if (opts.testing !== true) {
                        process.exit(1);
                    }
                    return [2 /*return*/, null];
                case 7: return [2 /*return*/];
            }
        });
    });
}
// Auto-start logic
if (import.meta.url === "file://".concat(process.argv[1])) {
    start().catch(function (err) {
        console.error("Fatal error starting server:", err);
        process.exit(1);
    });
}
