import { PythonShell, Options as PythonShellOptions } from 'python-shell';
import * as fs from 'fs';
import * as path from 'path';
import { getManagedPythonPath } from './venv-manager.js'; // Import ESM style
import * as https from 'https';
import * as http from 'http';
import { fileURLToPath } from 'url';

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to the Python bridge script
// Calculate path relative to the compiled JS file location (dist/lib)
// Go up two levels from dist/lib to the project root, then into the source lib dir
const BRIDGE_SCRIPT_PATH = path.resolve(__dirname, '..', '..', 'lib');
const BRIDGE_SCRIPT_NAME = 'python_bridge.py';

/**
 * Execute a Python function from the Z-Library repository
 * @param functionName - Name of the Python function to call
 * @param args - Arguments to pass to the function
 * @returns Promise resolving with the result from the Python function
 * @throws {Error} If the Python process fails or returns an error.
 */
async function callPythonFunction(functionName: string, args: any[] = []): Promise<any> {
  try {
    // Get the python path asynchronously INSIDE the try block
    const venvPythonPath = await getManagedPythonPath();
    const options: PythonShellOptions = {
      mode: 'json',
      pythonPath: venvPythonPath, // Use the Python from our managed venv
      scriptPath: BRIDGE_SCRIPT_PATH, // Use the calculated path to the source lib dir
      args: [functionName, JSON.stringify(args)]
    };

    // PythonShell.run call is already inside the try block (from line 33 in original)
    // PythonShell.run returns Promise<string[] | undefined>
    // We expect JSON, so results[0] should be the JSON string if successful
    // PythonShell with mode: 'json' should return an array of parsed JSON objects (or throw an error)
    const results = await PythonShell.run(BRIDGE_SCRIPT_NAME, options); // Run the script name relative to scriptPath

    // Check if results exist and contain at least one element
    if (!results || results.length === 0) {
        throw new Error(`No valid results received from Python script. Raw: ${results}`);
    }

    // Assume the first element is the parsed JSON result
    const resultData = results[0];

    // Check if the Python script itself returned an error structure
    // Assumes python-shell in json mode provides a parsed object or throws/rejects
    if (resultData && typeof resultData === 'object' && 'error' in resultData && resultData.error) {
        throw new Error(resultData.error);
    }

    // Return the successful result from Python
    return resultData;
  } catch (err: any) {
    // Log the full error object from python-shell
    console.error(`[callPythonFunction Error - ${functionName}] Full error object:`, JSON.stringify(err, null, 2));
    // Capture stderr if available
    const stderrOutput = err.stderr ? ` Stderr: ${err.stderr}` : '';
    // Explicitly create the wrapped message and throw a new error
    const wrappedMessage = `Python bridge execution failed for ${functionName}: ${err.message || err}.${stderrOutput}`;
    throw new Error(wrappedMessage);
  }
}

// Define interfaces for function arguments for better type safety

interface SearchBooksArgs {
    query: string;
    exact?: boolean;
    fromYear?: number | null;
    toYear?: number | null;
    languages?: string[];
    extensions?: string[];
    count?: number;
}

interface FullTextSearchArgs extends SearchBooksArgs {
    phrase?: boolean;
    words?: boolean;
}

interface GetBookByIdArgs {
    id: string;
}

interface GetDownloadInfoArgs {
    id: string;
    format?: string | null;
}

interface GetDownloadHistoryArgs {
    count?: number;
}

interface GetRecentBooksArgs {
    count?: number;
    format?: string | null;
}

interface DownloadBookToFileArgs {
    id: string;
    format?: string | null;
    outputDir?: string;
    process_for_rag?: boolean;
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
  count = 10
}: SearchBooksArgs): Promise<any> {
  return await callPythonFunction('search', [
    query, exact, fromYear, toYear, languages, extensions, count
  ]);
}

/**
 * Get book details by ID
 */
export async function getBookById({ id }: GetBookByIdArgs): Promise<any> {
  return await callPythonFunction('get_by_id', [id]);
}

/**
 * Get download link for a book
 */
export async function getDownloadInfo({ id, format = null }: GetDownloadInfoArgs): Promise<any> {
  return await callPythonFunction('get_download_info', [id, format]);
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
  count = 10
}: FullTextSearchArgs): Promise<any> {
  return await callPythonFunction('full_text_search', [
    query, exact, phrase, words, languages, extensions, count
  ]);
}

/**
 * Get user's download history
 */
export async function getDownloadHistory({ count = 10 }: GetDownloadHistoryArgs): Promise<any> {
  return await callPythonFunction('get_download_history', [count]);
}

/**
 * Get user's download limits
 */
export async function getDownloadLimits(): Promise<any> {
  return await callPythonFunction('get_download_limits', []);
}

/**
 * Get recently added books
 */
export async function getRecentBooks({ count = 10, format = null }: GetRecentBooksArgs): Promise<any> {
  return await callPythonFunction('get_recent_books', [count, format]);
}


/**
 * Process a downloaded document for RAG
 */
export async function processDocumentForRag({ filePath, outputFormat = 'text' }: ProcessDocumentForRagArgs): Promise<any> {
  if (!filePath) {
    throw new Error("Missing required argument: filePath");
  }
  console.log(`Calling Python bridge to process document: ${filePath}`);
  // Ensure the file path is absolute or correctly relative for the Python script
  const absoluteFilePath = path.resolve(filePath);
  const result = await callPythonFunction('process_document', [absoluteFilePath, outputFormat]);
  // Add check for missing processed_text after successful Python call
  if (!result?.processed_text) { // Check for null or undefined processed_text
      throw new Error(`Invalid response from Python bridge during processing. Missing processed_text.`);
  }
  return result;
}

/**
 * Helper function to generate a safe filename from book info.
 */
function generateSafeFilename(id: string, format: string | null, downloadInfo: any): string {
    const title = (downloadInfo.title || `book_${id}`) // Fallback title
      .replace(/[/\\?%*:|"<>]/g, '-') // Replace invalid characters
      .substring(0, 100); // Limit length

    const fileExt = (downloadInfo.format || format || 'unknown').toLowerCase(); // Ensure extension
    return `${title}.${fileExt}`;
}

/**
 * Download a book directly to a file
 */
export async function downloadBookToFile({
    id,
    format = null,
    outputDir = './downloads',
    process_for_rag = false
}: DownloadBookToFileArgs): Promise<any> { // Added process_for_rag
  try {
    // First get the download info (includes URL)
    console.log(`[downloadBookToFile - ${id}] Attempting to get download info...`);
    const downloadInfo = await getDownloadInfo({ id, format }); // Pass args object
    console.log(`[downloadBookToFile - ${id}] Got download info:`, downloadInfo ? JSON.stringify(downloadInfo).substring(0, 100) + '...' : 'null/undefined');

    if (!downloadInfo || downloadInfo.error) {
      throw new Error(downloadInfo.error || 'Failed to get download info');
    }

    if (!downloadInfo.download_url) {
      throw new Error('No download URL available for this book');
    }

    // Create output directory if it doesn't exist
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Generate filename using helper
    const filename = generateSafeFilename(id, format, downloadInfo);
    const outputPath = path.join(outputDir, filename);

    // Download the file
    await downloadFile(downloadInfo.download_url, outputPath);

    let processed_text: string | null = null;
    if (process_for_rag) {
        console.log(`Processing downloaded file for RAG: ${outputPath}`);
        try {
            const processingResult = await processDocumentForRag({ filePath: outputPath }); // Pass object
            if (processingResult && !processingResult.error) {
                processed_text = processingResult.processed_text;
                console.log(`Successfully processed file for RAG.`);
            } else {
                console.warn(`Failed to process file for RAG: ${processingResult?.error || 'Unknown error'}`);
                // Proceed with download result, but log the warning
            }
        } catch (processingError: any) {
             console.warn(`Error during RAG processing: ${processingError.message}`);
        }
    }

    const result: any = { // Define result type more explicitly if possible
      success: true,
      title: downloadInfo.title || `book_${id}`,
      format: (downloadInfo.format || format || 'unknown').toLowerCase(), // Use consistent extension logic
      path: outputPath,
      size: downloadInfo.filesize, // May be undefined
    };

    if (processed_text !== null) {
        result.processed_text = processed_text;
    }

    return result;

  } catch (error: any) {
    // Throw an error instead of returning an object
    throw new Error(`Failed to download book: ${error.message || 'Unknown error'}`);
  }
}

/**
 * Helper function to download a file from URL
 */
function downloadFile(url: string, outputPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // Determine protocol (http or https)
    const protocol = url.startsWith('https:') ? https : http;

    // Create file stream
    const fileStream = fs.createWriteStream(outputPath);

    // Make request
    const request = protocol.get(url, (response) => {
      // Check for redirect
      if (response.statusCode && response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        // Follow redirect
        console.log(`Redirecting download to: ${response.headers.location}`);
        return downloadFile(response.headers.location, outputPath)
          .then(resolve)
          .catch(reject);
      }

      // Check for error
      if (response.statusCode !== 200) {
        reject(new Error(`Failed to download file, status: ${response.statusCode}`));
        response.resume(); // Consume response data to free up memory
        return;
      }

      // Pipe response to file
      response.pipe(fileStream);

      // Handle events
      fileStream.on('finish', () => {
        fileStream.close((closeErr) => { // Pass potential close error to reject
            if (closeErr) {
                reject(closeErr);
            } else {
                resolve();
            }
        });
      });
    });

    // Handle request errors
    request.on('error', (err) => {
      try {
        if (fs.existsSync(outputPath)) {
            fs.unlinkSync(outputPath); // Remove partial file
        }
      } catch (unlinkErr) {
          console.error(`Error removing partial file ${outputPath}: ${unlinkErr}`);
      }
      reject(err);
    });

    // Handle file errors
    fileStream.on('error', (err) => {
       try {
        if (fs.existsSync(outputPath)) {
            fs.unlinkSync(outputPath); // Remove partial file
        }
      } catch (unlinkErr) {
          console.error(`Error removing partial file ${outputPath}: ${unlinkErr}`);
      }
      reject(err);
    });
  });
}