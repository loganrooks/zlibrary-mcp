import { PythonShell, Options as PythonShellOptions } from 'python-shell';
import * as path from 'path';
import { getManagedPythonPath } from './venv-manager.js'; // Import ESM style
import { appendFile as appendFileAsyncFS, mkdir as mkdirAsyncFS } from 'fs/promises'; // Import fs/promises for async file operations, aliased
// Removed unused https, http imports
// path is already imported on line 2
import { fileURLToPath } from 'url';
import { withRetry, isRetryableError } from './retry-manager.js';
import { CircuitBreaker } from './circuit-breaker.js';
import { ZLibraryError, PythonBridgeError } from './errors.js';

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the Python bridge script
// Calculate path relative to the compiled JS file location (dist/lib)
// Go up two levels from dist/lib to the project root, then into the source lib dir
const BRIDGE_SCRIPT_PATH = path.resolve(__dirname, '..', '..', 'lib');
const BRIDGE_SCRIPT_NAME = 'python_bridge.py';

// Create a circuit breaker for all Python bridge operations
const pythonBridgeCircuitBreaker = new CircuitBreaker({
  threshold: parseInt(process.env.CIRCUIT_BREAKER_THRESHOLD || '5'),
  timeout: parseInt(process.env.CIRCUIT_BREAKER_TIMEOUT || '60000'),
  onStateChange: (oldState, newState) => {
    console.log(`Python bridge circuit breaker: ${oldState} -> ${newState}`);
  }
});

/**
 * Execute a Python function from the Z-Library repository
 * @param functionName - Name of the Python function to call
 * @param args - Arguments to pass to the function
 * @returns Promise resolving with the result from the Python function
 * @throws {ZLibraryError} If the Python process fails or returns an error.
 */
async function callPythonFunction(functionName: string, args: Record<string, any> = {}): Promise<any> {
  // Wrap the entire operation with retry logic and circuit breaker
  return withRetry(
    async () => {
      return pythonBridgeCircuitBreaker.execute(async () => {
        try {
          // Get the python path asynchronously INSIDE the try block
          const venvPythonPath = await getManagedPythonPath();
          // Serialize arguments as JSON *before* creating options
          const serializedArgs = JSON.stringify(args);
          const options: PythonShellOptions = {
            mode: 'text', // Revert back to text mode
            pythonPath: venvPythonPath, // Use the Python from our managed venv
            scriptPath: BRIDGE_SCRIPT_PATH, // Use the calculated path to the source lib dir
            args: [functionName, serializedArgs] // Pass serialized string directly
          };

          // PythonShell.run call is already inside the try block (from line 33 in original)
          // PythonShell.run returns Promise<string[] | undefined>
          // We expect JSON, so results[0] should be the JSON string if successful
          // PythonShell with mode: 'json' should return an array of parsed JSON objects (or throw an error)
          const results = await PythonShell.run(BRIDGE_SCRIPT_NAME, options); // results will be string[] | undefined

          // Check if results exist and contain at least one element
          if (!results || results.length === 0) {
            throw new PythonBridgeError(`No output received from Python script.`, {
              functionName,
              args
            });
          }

          // Join the lines and parse manually
          const stdoutString = results.join('\n');
          let mcpResponseData: any;
          try {
            // First parse: Get the MCP response object { content: [{ type: 'text', text: '...' }] }
            mcpResponseData = JSON.parse(stdoutString);
          } catch (parseError: any) {
            throw new PythonBridgeError(
              `Failed to parse initial JSON output from Python script: ${parseError.message}`,
              { functionName, args, rawOutput: stdoutString },
              false // Parse errors are not retryable
            );
          }

          // Validate the MCP response structure and extract the nested JSON string
          if (!mcpResponseData || !Array.isArray(mcpResponseData.content) || mcpResponseData.content.length === 0 || typeof mcpResponseData.content[0].text !== 'string') {
            throw new PythonBridgeError(
              `Invalid MCP response structure received from Python script.`,
              { functionName, args, rawOutput: stdoutString },
              false // Structure errors are not retryable
            );
          }

          const nestedJsonString = mcpResponseData.content[0].text;
          let resultData: any;
          try {
            // Second parse: Get the actual result object from the nested string
            resultData = JSON.parse(nestedJsonString);
          } catch (parseError: any) {
            throw new PythonBridgeError(
              `Failed to parse nested JSON result from Python script: ${parseError.message}`,
              { functionName, args, nestedString: nestedJsonString },
              false // Parse errors are not retryable
            );
          }

          // Check if the *actual* Python result contained an error structure
          if (resultData && typeof resultData === 'object' && 'error' in resultData && resultData.error) {
            throw new PythonBridgeError(
              `Python bridge execution failed for ${functionName}: ${resultData.error}`,
              { functionName, args }
            );
          }

          // Return the successful result object from Python
          return resultData;
        } catch (err: any) {
          // Log the full error object from python-shell
          console.error(`[callPythonFunction Error - ${functionName}] Raw error object:`, err);

          // If it's already a ZLibraryError, just rethrow
          if (err instanceof ZLibraryError) {
            throw err;
          }

          // Capture stderr if available
          const stderrOutput = err.stderr ? ` Stderr: ${err.stderr}` : '';

          // Wrap in PythonBridgeError with context
          throw new PythonBridgeError(
            `Python bridge execution failed for ${functionName}: ${err.message || err}.${stderrOutput}`,
            {
              functionName,
              args,
              stderr: err.stderr,
              originalError: err
            }
          );
        }
      });
    },
    {
      maxRetries: parseInt(process.env.RETRY_MAX_RETRIES || '3'),
      initialDelay: parseInt(process.env.RETRY_INITIAL_DELAY || '1000'),
      maxDelay: parseInt(process.env.RETRY_MAX_DELAY || '30000'),
      factor: parseFloat(process.env.RETRY_FACTOR || '2'),
      shouldRetry: isRetryableError
    }
  );
}

// Define interfaces for function arguments for better type safety

interface SearchBooksArgs {
    query: string;
    exact?: boolean;
    fromYear?: number | null;
    toYear?: number | null;
    languages?: string[];
    extensions?: string[];
    content_types?: string[];
    count?: number;
}

interface FullTextSearchArgs extends SearchBooksArgs {
    phrase?: boolean;
    words?: boolean;
}

interface GetDownloadInfoArgs {
    id: string;
    format?: string | null;
}

interface GetDownloadHistoryArgs {
    count?: number;
}

interface DownloadBookToFileArgs {
    // id: string; // Replaced by bookDetails
    // format?: string | null; // Replaced by bookDetails
    bookDetails: Record<string, any>; // Expect the full book details object
    outputDir?: string;
    process_for_rag?: boolean;
    processed_output_format?: string;
}

interface ProcessDocumentForRagArgs {
    filePath: string;
    outputFormat?: string;
}


/**
 * Search for books in Z-Library
 */
export async function searchBooks({
  query,
  exact = false,
  fromYear = null,
  toYear = null,
  languages = [],
  extensions = [],
  content_types = [],
  count = 10
}: SearchBooksArgs): Promise<any> {
  // Pass arguments as an object matching Python function signature
  // Python bridge main() expects 'language' (singular) and 'content_types'
  const pythonArgs = {
    query: query,
    exact: exact,
    from_year: fromYear,
    to_year: toYear,
    languages: languages,
    extensions: extensions,
    content_types: content_types,
    count: count
  };
  // Moved logging to after pythonArgs is defined
  const searchBooksPythonArgsLog = `[${new Date().toISOString()}] Node.js searchBooks: Sending to callPythonFunction: ${JSON.stringify(pythonArgs)}\n`;
  console.log(searchBooksPythonArgsLog.trim());
  try {
    const logFilePath = path.resolve(__dirname, '..', '..', 'logs', 'nodejs_debug.log');
    await mkdirAsyncFS(path.dirname(logFilePath), { recursive: true });
    await appendFileAsyncFS(logFilePath, searchBooksPythonArgsLog);
  } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
  return await callPythonFunction('search', pythonArgs);
}
/**
 * Perform full text search
 */
export async function fullTextSearch({
  query,
  exact = false,
  phrase = true,
  words = false,
  languages = [],
  extensions = [],
  content_types = [],
  count = 10
}: FullTextSearchArgs): Promise<any> {
  // Pass arguments as an object matching Python function signature
  // Python bridge main() expects 'language' (singular) and 'content_types'
  const pythonArgsFTS = {
    query: query,
    exact: exact,
    phrase: phrase,
    words: words,
    languages: languages,
    extensions: extensions,
    content_types: content_types,
    count: count
  };
  // Moved logging to after pythonArgsFTS is defined
  const ftsPythonArgsLog = `[${new Date().toISOString()}] Node.js fullTextSearch: Sending to callPythonFunction: ${JSON.stringify(pythonArgsFTS)}\n`;
  console.log(ftsPythonArgsLog.trim());
  try {
    const logFilePath = path.resolve(__dirname, '..', '..', 'logs', 'nodejs_debug.log');
    await mkdirAsyncFS(path.dirname(logFilePath), { recursive: true });
    await appendFileAsyncFS(logFilePath, ftsPythonArgsLog);
  } catch (e) { console.error('Failed to write to logs/nodejs_debug.log', e); }
  return await callPythonFunction('full_text_search', pythonArgsFTS);
}

/**
 * Get user's download history
 */
export async function getDownloadHistory({ count = 10 }: GetDownloadHistoryArgs): Promise<any> {
  // Pass arguments as an object matching Python function signature
  return await callPythonFunction('get_download_history', { count });
}

/**
 * Get user's download limits
 */
export async function getDownloadLimits(): Promise<any> {
  // Pass arguments as an object matching Python function signature
  return await callPythonFunction('get_download_limits', {});
}


/**
 * Process a downloaded document for RAG
 */
export async function processDocumentForRag({ filePath, outputFormat = 'txt' }: ProcessDocumentForRagArgs): Promise<{ processed_file_path: string | null; content?: string[] }> { // Updated return type
  if (!filePath) {
    throw new Error("Missing required argument: filePath");
  }
  console.log(`Calling Python bridge to process document: ${filePath}`);
  // Ensure the file path is absolute or correctly relative for the Python script
  const absoluteFilePath = path.resolve(filePath);
  // Pass arguments as an object matching Python function signature
  const result = await callPythonFunction('process_document', { file_path_str: absoluteFilePath, output_format: outputFormat });

  // Check if the Python script returned an error structure
  if (result && result.error) {
      throw new Error(`Python processing failed: ${result.error}`);
  }

  // Check for the expected processed_file_path key's presence.
  // Allow null value as valid (e.g., for image PDFs).
  // Throw error only if the key is completely missing.
  if (!result || !('processed_file_path' in result)) {
       throw new Error(`Invalid response from Python bridge during processing. Missing processed_file_path key.`);
   }
  // No error thrown if key exists, even if value is null.
  // Return the full result object from Python
  return result; // Return the whole object { processed_file_path: ..., content: ... }
}

// Removed unused generateSafeFilename function

/**
 * Download a book directly to a file
 */
export async function downloadBookToFile({
    // id, // Replaced by bookDetails
    // format = null, // Replaced by bookDetails
    bookDetails, // Use bookDetails object
    outputDir = './downloads',
    process_for_rag = false,
    processed_output_format = 'txt'
}: DownloadBookToFileArgs): Promise<{ file_path: string; processed_file_path?: string | null; processing_error?: string }> {
  try {
    const logId = (bookDetails && bookDetails.id) ? bookDetails.id : 'unknown_id'; // Use ID from details for logging (compat check)
    // console.log(`[downloadBookToFile - ${logId}] Calling Python bridge... process_for_rag=${process_for_rag}`); // Removed debug log
    // Call the Python function, passing the bookDetails object
    const result = await callPythonFunction('download_book', {
        book_details: bookDetails, // Pass the whole object
        // book_id: id, // Removed
        // format: format, // Removed
        output_dir: outputDir,
        process_for_rag: process_for_rag,
        processed_output_format: processed_output_format
    });

    // Check if the Python script returned an error structure
    if (result && result.error) {
        throw new Error(`Python download/processing failed: ${result.error}`);
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
    return {
        file_path: result.file_path,
        processed_file_path: result.processed_file_path, // Will be string path or null
        processing_error: result.processing_error // Will be string or undefined
    };

  } catch (error: any) {
    // Re-throw errors from callPythonFunction or validation checks
    throw new Error(`Failed to download book: ${error.message || 'Unknown error'}`);
  }
}

/**
 * Phase 3 Research Tools - Exported wrappers for advanced search and metadata features
 */

// Core fields always included in metadata response
const METADATA_CORE_FIELDS = new Set([
  'id', 'book_hash', 'book_url',
  'title', 'author', 'authors', 'year', 'publisher', 'language',
  'pages', 'isbn_10', 'isbn_13', 'rating', 'cover',
  'url', 'categories', 'extension', 'filesize', 'series',
]);

// Mapping from include group names to metadata field names
const METADATA_INCLUDE_MAP: Record<string, string[]> = {
  'terms': ['terms'],
  'booklists': ['booklists'],
  'ipfs': ['ipfs_cids'],
  'ratings': ['quality_score'],
  'description': ['description'],
};

function filterMetadataResponse(fullMetadata: any, include?: string[]): any {
  if (!fullMetadata || typeof fullMetadata !== 'object') return fullMetadata;

  const result: Record<string, any> = {};

  // Always include core fields
  for (const key of Object.keys(fullMetadata)) {
    if (METADATA_CORE_FIELDS.has(key)) {
      result[key] = fullMetadata[key];
    }
  }

  // Add requested optional field groups
  if (include && include.length > 0) {
    for (const group of include) {
      const fields = METADATA_INCLUDE_MAP[group];
      if (fields) {
        for (const field of fields) {
          if (field in fullMetadata) {
            result[field] = fullMetadata[field];
          }
        }
      }
    }
  }

  return result;
}

export async function getBookMetadata(bookId: string, bookHash: string, include?: string[]): Promise<any> {
  const fullMetadata = await callPythonFunction('get_book_metadata_complete', {
    book_id: bookId,
    book_hash: bookHash
  });
  return filterMetadataResponse(fullMetadata, include);
}

export async function searchByTerm(args: {
  term: string;
  yearFrom?: number;
  yearTo?: number;
  languages?: string[];
  extensions?: string[];
  limit?: number;
}): Promise<any> {
  return callPythonFunction('search_by_term_bridge', {
    term: args.term,
    year_from: args.yearFrom,
    year_to: args.yearTo,
    languages: args.languages,
    extensions: args.extensions,
    limit: args.limit || 25
  });
}

export async function searchByAuthor(args: {
  author: string;
  exact?: boolean;
  yearFrom?: number;
  yearTo?: number;
  languages?: string[];
  extensions?: string[];
  limit?: number;
}): Promise<any> {
  return callPythonFunction('search_by_author_bridge', {
    author: args.author,
    exact: args.exact || false,
    year_from: args.yearFrom,
    year_to: args.yearTo,
    languages: args.languages,
    extensions: args.extensions,
    limit: args.limit || 25
  });
}

export async function fetchBooklist(args: {
  booklistId: string;
  booklistHash: string;
  topic: string;
  page?: number;
}): Promise<any> {
  return callPythonFunction('fetch_booklist_bridge', {
    booklist_id: args.booklistId,
    booklist_hash: args.booklistHash,
    topic: args.topic,
    page: args.page || 1
  });
}

export async function searchAdvanced(args: {
  query: string;
  exact?: boolean;
  yearFrom?: number;
  yearTo?: number;
  count?: number;
}): Promise<any> {
  return callPythonFunction('search_advanced', {
    query: args.query,
    exact: args.exact || false,
    from_year: args.yearFrom,
    to_year: args.yearTo,
    count: args.count || 10
  });
}

// Removed unused downloadFile helper function