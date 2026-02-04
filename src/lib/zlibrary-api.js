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
exports.searchBooks = searchBooks;
exports.fullTextSearch = fullTextSearch;
exports.getDownloadHistory = getDownloadHistory;
exports.getDownloadLimits = getDownloadLimits;
exports.processDocumentForRag = processDocumentForRag;
exports.downloadBookToFile = downloadBookToFile;
exports.getBookMetadata = getBookMetadata;
exports.searchByTerm = searchByTerm;
exports.searchByAuthor = searchByAuthor;
exports.fetchBooklist = fetchBooklist;
exports.searchAdvanced = searchAdvanced;
exports.searchMultiSource = searchMultiSource;
var python_shell_1 = require("python-shell");
var path = require("path");
var venv_manager_js_1 = require("./venv-manager.js"); // Import ESM style
var promises_1 = require("fs/promises"); // Import fs/promises for async file operations, aliased
// Removed unused https, http imports
// path is already imported on line 2
var url_1 = require("url");
var retry_manager_js_1 = require("./retry-manager.js");
var circuit_breaker_js_1 = require("./circuit-breaker.js");
var errors_js_1 = require("./errors.js");
// Recreate __dirname for ESM
var __filename = (0, url_1.fileURLToPath)(import.meta.url);
var __dirname = path.dirname(__filename);
// Path to the Python bridge script
// Calculate path relative to the compiled JS file location (dist/lib)
// Go up two levels from dist/lib to the project root, then into the source lib dir
var BRIDGE_SCRIPT_PATH = path.resolve(__dirname, '..', '..', 'lib');
var BRIDGE_SCRIPT_NAME = 'python_bridge.py';
// Create a circuit breaker for all Python bridge operations
var pythonBridgeCircuitBreaker = new circuit_breaker_js_1.CircuitBreaker({
    threshold: parseInt(process.env.CIRCUIT_BREAKER_THRESHOLD || '5'),
    timeout: parseInt(process.env.CIRCUIT_BREAKER_TIMEOUT || '60000'),
    onStateChange: function (oldState, newState) {
        console.log("Python bridge circuit breaker: ".concat(oldState, " -> ").concat(newState));
    }
});
/**
 * Execute a Python function from the Z-Library repository
 * @param functionName - Name of the Python function to call
 * @param args - Arguments to pass to the function
 * @returns Promise resolving with the result from the Python function
 * @throws {ZLibraryError} If the Python process fails or returns an error.
 */
function callPythonFunction(functionName_1) {
    return __awaiter(this, arguments, void 0, function (functionName, args) {
        var _this = this;
        if (args === void 0) { args = {}; }
        return __generator(this, function (_a) {
            // Wrap the entire operation with retry logic and circuit breaker
            return [2 /*return*/, (0, retry_manager_js_1.withRetry)(function () { return __awaiter(_this, void 0, void 0, function () {
                    var _this = this;
                    return __generator(this, function (_a) {
                        return [2 /*return*/, pythonBridgeCircuitBreaker.execute(function () { return __awaiter(_this, void 0, void 0, function () {
                                var venvPythonPath, serializedArgs, options, results, stdoutString, mcpResponseData, nestedJsonString, resultData, err_1, stderrOutput;
                                return __generator(this, function (_a) {
                                    switch (_a.label) {
                                        case 0:
                                            _a.trys.push([0, 3, , 4]);
                                            return [4 /*yield*/, (0, venv_manager_js_1.getManagedPythonPath)()];
                                        case 1:
                                            venvPythonPath = _a.sent();
                                            serializedArgs = JSON.stringify(args);
                                            options = {
                                                mode: 'text', // Revert back to text mode
                                                pythonPath: venvPythonPath, // Use the Python from our managed venv
                                                scriptPath: BRIDGE_SCRIPT_PATH, // Use the calculated path to the source lib dir
                                                args: [functionName, serializedArgs] // Pass serialized string directly
                                            };
                                            return [4 /*yield*/, python_shell_1.PythonShell.run(BRIDGE_SCRIPT_NAME, options)];
                                        case 2:
                                            results = _a.sent();
                                            // Check if results exist and contain at least one element
                                            if (!results || results.length === 0) {
                                                throw new errors_js_1.PythonBridgeError("No output received from Python script.", {
                                                    functionName: functionName,
                                                    args: args
                                                });
                                            }
                                            stdoutString = results.join('\n');
                                            mcpResponseData = void 0;
                                            try {
                                                // First parse: Get the MCP response object { content: [{ type: 'text', text: '...' }] }
                                                mcpResponseData = JSON.parse(stdoutString);
                                            }
                                            catch (parseError) {
                                                throw new errors_js_1.PythonBridgeError("Failed to parse initial JSON output from Python script: ".concat(parseError.message), { functionName: functionName, args: args, rawOutput: stdoutString }, false // Parse errors are not retryable
                                                );
                                            }
                                            // Validate the MCP response structure and extract the nested JSON string
                                            if (!mcpResponseData || !Array.isArray(mcpResponseData.content) || mcpResponseData.content.length === 0 || typeof mcpResponseData.content[0].text !== 'string') {
                                                throw new errors_js_1.PythonBridgeError("Invalid MCP response structure received from Python script.", { functionName: functionName, args: args, rawOutput: stdoutString }, false // Structure errors are not retryable
                                                );
                                            }
                                            nestedJsonString = mcpResponseData.content[0].text;
                                            resultData = void 0;
                                            try {
                                                // Second parse: Get the actual result object from the nested string
                                                resultData = JSON.parse(nestedJsonString);
                                            }
                                            catch (parseError) {
                                                throw new errors_js_1.PythonBridgeError("Failed to parse nested JSON result from Python script: ".concat(parseError.message), { functionName: functionName, args: args, nestedString: nestedJsonString }, false // Parse errors are not retryable
                                                );
                                            }
                                            // Check if the *actual* Python result contained an error structure
                                            if (resultData && typeof resultData === 'object' && 'error' in resultData && resultData.error) {
                                                throw new errors_js_1.PythonBridgeError("Python bridge execution failed for ".concat(functionName, ": ").concat(resultData.error), { functionName: functionName, args: args });
                                            }
                                            // Return the successful result object from Python
                                            return [2 /*return*/, resultData];
                                        case 3:
                                            err_1 = _a.sent();
                                            // Log the full error object from python-shell
                                            console.error("[callPythonFunction Error - ".concat(functionName, "] Raw error object:"), err_1);
                                            // If it's already a ZLibraryError, just rethrow
                                            if (err_1 instanceof errors_js_1.ZLibraryError) {
                                                throw err_1;
                                            }
                                            stderrOutput = err_1.stderr ? " Stderr: ".concat(err_1.stderr) : '';
                                            // Wrap in PythonBridgeError with context
                                            throw new errors_js_1.PythonBridgeError("Python bridge execution failed for ".concat(functionName, ": ").concat(err_1.message || err_1, ".").concat(stderrOutput), {
                                                functionName: functionName,
                                                args: args,
                                                stderr: err_1.stderr,
                                                originalError: err_1
                                            });
                                        case 4: return [2 /*return*/];
                                    }
                                });
                            }); })];
                    });
                }); }, {
                    maxRetries: parseInt(process.env.RETRY_MAX_RETRIES || '3'),
                    initialDelay: parseInt(process.env.RETRY_INITIAL_DELAY || '1000'),
                    maxDelay: parseInt(process.env.RETRY_MAX_DELAY || '30000'),
                    factor: parseFloat(process.env.RETRY_FACTOR || '2'),
                    shouldRetry: retry_manager_js_1.isRetryableError
                })];
        });
    });
}
/**
 * Search for books in Z-Library
 */
function searchBooks(_a) {
    return __awaiter(this, arguments, void 0, function (_b) {
        var pythonArgs, searchBooksPythonArgsLog, logFilePath, e_1;
        var query = _b.query, _c = _b.exact, exact = _c === void 0 ? false : _c, _d = _b.fromYear, fromYear = _d === void 0 ? null : _d, _e = _b.toYear, toYear = _e === void 0 ? null : _e, _f = _b.languages, languages = _f === void 0 ? [] : _f, _g = _b.extensions, extensions = _g === void 0 ? [] : _g, _h = _b.content_types, content_types = _h === void 0 ? [] : _h, _j = _b.count, count = _j === void 0 ? 10 : _j;
        return __generator(this, function (_k) {
            switch (_k.label) {
                case 0:
                    pythonArgs = {
                        query: query,
                        exact: exact,
                        from_year: fromYear,
                        to_year: toYear,
                        languages: languages,
                        extensions: extensions,
                        content_types: content_types,
                        count: count
                    };
                    searchBooksPythonArgsLog = "[".concat(new Date().toISOString(), "] Node.js searchBooks: Sending to callPythonFunction: ").concat(JSON.stringify(pythonArgs), "\n");
                    console.log(searchBooksPythonArgsLog.trim());
                    _k.label = 1;
                case 1:
                    _k.trys.push([1, 4, , 5]);
                    logFilePath = path.resolve(__dirname, '..', '..', 'logs', 'nodejs_debug.log');
                    return [4 /*yield*/, (0, promises_1.mkdir)(path.dirname(logFilePath), { recursive: true })];
                case 2:
                    _k.sent();
                    return [4 /*yield*/, (0, promises_1.appendFile)(logFilePath, searchBooksPythonArgsLog)];
                case 3:
                    _k.sent();
                    return [3 /*break*/, 5];
                case 4:
                    e_1 = _k.sent();
                    console.error('Failed to write to logs/nodejs_debug.log', e_1);
                    return [3 /*break*/, 5];
                case 5: return [4 /*yield*/, callPythonFunction('search', pythonArgs)];
                case 6: return [2 /*return*/, _k.sent()];
            }
        });
    });
}
/**
 * Perform full text search
 */
function fullTextSearch(_a) {
    return __awaiter(this, arguments, void 0, function (_b) {
        var pythonArgsFTS, ftsPythonArgsLog, logFilePath, e_2;
        var query = _b.query, _c = _b.exact, exact = _c === void 0 ? false : _c, _d = _b.phrase, phrase = _d === void 0 ? true : _d, _e = _b.words, words = _e === void 0 ? false : _e, _f = _b.languages, languages = _f === void 0 ? [] : _f, _g = _b.extensions, extensions = _g === void 0 ? [] : _g, _h = _b.content_types, content_types = _h === void 0 ? [] : _h, _j = _b.count, count = _j === void 0 ? 10 : _j;
        return __generator(this, function (_k) {
            switch (_k.label) {
                case 0:
                    pythonArgsFTS = {
                        query: query,
                        exact: exact,
                        phrase: phrase,
                        words: words,
                        languages: languages,
                        extensions: extensions,
                        content_types: content_types,
                        count: count
                    };
                    ftsPythonArgsLog = "[".concat(new Date().toISOString(), "] Node.js fullTextSearch: Sending to callPythonFunction: ").concat(JSON.stringify(pythonArgsFTS), "\n");
                    console.log(ftsPythonArgsLog.trim());
                    _k.label = 1;
                case 1:
                    _k.trys.push([1, 4, , 5]);
                    logFilePath = path.resolve(__dirname, '..', '..', 'logs', 'nodejs_debug.log');
                    return [4 /*yield*/, (0, promises_1.mkdir)(path.dirname(logFilePath), { recursive: true })];
                case 2:
                    _k.sent();
                    return [4 /*yield*/, (0, promises_1.appendFile)(logFilePath, ftsPythonArgsLog)];
                case 3:
                    _k.sent();
                    return [3 /*break*/, 5];
                case 4:
                    e_2 = _k.sent();
                    console.error('Failed to write to logs/nodejs_debug.log', e_2);
                    return [3 /*break*/, 5];
                case 5: return [4 /*yield*/, callPythonFunction('full_text_search', pythonArgsFTS)];
                case 6: return [2 /*return*/, _k.sent()];
            }
        });
    });
}
/**
 * Get user's download history
 */
function getDownloadHistory(_a) {
    return __awaiter(this, arguments, void 0, function (_b) {
        var _c = _b.count, count = _c === void 0 ? 10 : _c;
        return __generator(this, function (_d) {
            switch (_d.label) {
                case 0: return [4 /*yield*/, callPythonFunction('get_download_history', { count: count })];
                case 1: 
                // Pass arguments as an object matching Python function signature
                return [2 /*return*/, _d.sent()];
            }
        });
    });
}
/**
 * Get user's download limits
 */
function getDownloadLimits() {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, callPythonFunction('get_download_limits', {})];
                case 1: 
                // Pass arguments as an object matching Python function signature
                return [2 /*return*/, _a.sent()];
            }
        });
    });
}
/**
 * Process a downloaded document for RAG
 */
function processDocumentForRag(_a) {
    return __awaiter(this, arguments, void 0, function (_b) {
        var absoluteFilePath, result;
        var filePath = _b.filePath, _c = _b.outputFormat, outputFormat = _c === void 0 ? 'txt' : _c;
        return __generator(this, function (_d) {
            switch (_d.label) {
                case 0:
                    if (!filePath) {
                        throw new Error("Missing required argument: filePath");
                    }
                    console.log("Calling Python bridge to process document: ".concat(filePath));
                    absoluteFilePath = path.resolve(filePath);
                    return [4 /*yield*/, callPythonFunction('process_document', { file_path_str: absoluteFilePath, output_format: outputFormat })];
                case 1:
                    result = _d.sent();
                    // Check if the Python script returned an error structure
                    if (result && result.error) {
                        throw new Error("Python processing failed: ".concat(result.error));
                    }
                    // Check for the expected processed_file_path key's presence.
                    // Allow null value as valid (e.g., for image PDFs).
                    // Throw error only if the key is completely missing.
                    if (!result || !('processed_file_path' in result)) {
                        throw new Error("Invalid response from Python bridge during processing. Missing processed_file_path key.");
                    }
                    // No error thrown if key exists, even if value is null.
                    // Return the full result object from Python
                    return [2 /*return*/, result]; // Return the whole object { processed_file_path: ..., content: ... }
            }
        });
    });
}
// Removed unused generateSafeFilename function
/**
 * Download a book directly to a file
 */
function downloadBookToFile(_a) {
    return __awaiter(this, arguments, void 0, function (_b) {
        var logId, result, error_1;
        var 
        // id, // Replaced by bookDetails
        // format = null, // Replaced by bookDetails
        bookDetails = _b.bookDetails, // Use bookDetails object
        _c = _b.outputDir, // Use bookDetails object
        outputDir = _c === void 0 ? './downloads' : _c, _d = _b.process_for_rag, process_for_rag = _d === void 0 ? false : _d, _e = _b.processed_output_format, processed_output_format = _e === void 0 ? 'txt' : _e;
        return __generator(this, function (_f) {
            switch (_f.label) {
                case 0:
                    _f.trys.push([0, 2, , 3]);
                    logId = (bookDetails && bookDetails.id) ? bookDetails.id : 'unknown_id';
                    return [4 /*yield*/, callPythonFunction('download_book', {
                            book_details: bookDetails, // Pass the whole object
                            // book_id: id, // Removed
                            // format: format, // Removed
                            output_dir: outputDir,
                            process_for_rag: process_for_rag,
                            processed_output_format: processed_output_format
                        })];
                case 1:
                    result = _f.sent();
                    // Check if the Python script returned an error structure
                    if (result && result.error) {
                        throw new Error("Python download/processing failed: ".concat(result.error));
                    }
                    // Validate the response structure
                    if (!result || !result.file_path) { // Compat check
                        throw new Error("Invalid response from Python bridge: Missing original file_path.");
                    }
                    // If processing was requested but the processed path is missing (and not explicitly null), it's an error
                    // Note: Python bridge now returns null if processing fails or yields no text, which is handled correctly here.
                    if (process_for_rag && !('processed_file_path' in result)) {
                        throw new Error("Invalid response from Python bridge: Processing requested but processed_file_path key is missing.");
                    }
                    // Return the result object containing file_path and optional processed_file_path/processing_error
                    return [2 /*return*/, {
                            file_path: result.file_path,
                            processed_file_path: result.processed_file_path, // Will be string path or null
                            processing_error: result.processing_error // Will be string or undefined
                        }];
                case 2:
                    error_1 = _f.sent();
                    // Re-throw errors from callPythonFunction or validation checks
                    throw new Error("Failed to download book: ".concat(error_1.message || 'Unknown error'));
                case 3: return [2 /*return*/];
            }
        });
    });
}
/**
 * Phase 3 Research Tools - Exported wrappers for advanced search and metadata features
 */
// Core fields always included in metadata response
var METADATA_CORE_FIELDS = new Set([
    'id', 'book_hash', 'book_url',
    'title', 'author', 'authors', 'year', 'publisher', 'language',
    'pages', 'isbn_10', 'isbn_13', 'rating', 'cover',
    'url', 'categories', 'extension', 'filesize', 'series',
]);
// Mapping from include group names to metadata field names
var METADATA_INCLUDE_MAP = {
    'terms': ['terms'],
    'booklists': ['booklists'],
    'ipfs': ['ipfs_cids'],
    'ratings': ['quality_score'],
    'description': ['description'],
};
function filterMetadataResponse(fullMetadata, include) {
    if (!fullMetadata || typeof fullMetadata !== 'object')
        return fullMetadata;
    var result = {};
    // Always include core fields
    for (var _i = 0, _a = Object.keys(fullMetadata); _i < _a.length; _i++) {
        var key = _a[_i];
        if (METADATA_CORE_FIELDS.has(key)) {
            result[key] = fullMetadata[key];
        }
    }
    // Add requested optional field groups
    if (include && include.length > 0) {
        for (var _b = 0, include_1 = include; _b < include_1.length; _b++) {
            var group = include_1[_b];
            var fields = METADATA_INCLUDE_MAP[group];
            if (fields) {
                for (var _c = 0, fields_1 = fields; _c < fields_1.length; _c++) {
                    var field = fields_1[_c];
                    if (field in fullMetadata) {
                        result[field] = fullMetadata[field];
                    }
                }
            }
        }
    }
    return result;
}
function getBookMetadata(bookId, bookHash, include) {
    return __awaiter(this, void 0, void 0, function () {
        var fullMetadata;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, callPythonFunction('get_book_metadata_complete', {
                        book_id: bookId,
                        book_hash: bookHash
                    })];
                case 1:
                    fullMetadata = _a.sent();
                    return [2 /*return*/, filterMetadataResponse(fullMetadata, include)];
            }
        });
    });
}
function searchByTerm(args) {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, callPythonFunction('search_by_term_bridge', {
                    term: args.term,
                    year_from: args.yearFrom,
                    year_to: args.yearTo,
                    languages: args.languages,
                    extensions: args.extensions,
                    limit: args.limit || 25
                })];
        });
    });
}
function searchByAuthor(args) {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, callPythonFunction('search_by_author_bridge', {
                    author: args.author,
                    exact: args.exact || false,
                    year_from: args.yearFrom,
                    year_to: args.yearTo,
                    languages: args.languages,
                    extensions: args.extensions,
                    limit: args.limit || 25
                })];
        });
    });
}
function fetchBooklist(args) {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, callPythonFunction('fetch_booklist_bridge', {
                    booklist_id: args.booklistId,
                    booklist_hash: args.booklistHash,
                    topic: args.topic,
                    page: args.page || 1
                })];
        });
    });
}
function searchAdvanced(args) {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, callPythonFunction('search_advanced', {
                    query: args.query,
                    exact: args.exact || false,
                    from_year: args.yearFrom,
                    to_year: args.yearTo,
                    count: args.count || 10
                })];
        });
    });
}
function searchMultiSource(args) {
    return __awaiter(this, void 0, void 0, function () {
        return __generator(this, function (_a) {
            return [2 /*return*/, callPythonFunction('search_multi_source', {
                    query: args.query,
                    source: args.source || 'auto',
                    count: args.count || 10
                })];
        });
    });
}
// Removed unused downloadFile helper function
