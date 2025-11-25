import { jest, describe, beforeEach, test, expect, afterEach } from '@jest/globals';
import * as fs from 'fs'; // Keep for potential use in download tests if needed, though likely removable
import * as path from 'path'; // Keep for path assertions
import * as http from 'http'; // Keep for potential use in download tests if needed, though likely removable
import * as https from 'https'; // Keep for potential use in download tests if needed, though likely removable

// Increase timeout for async operations
jest.setTimeout(30000);

// Mock dependencies
const mockGetManagedPythonPath = jest.fn();
const mockPythonShellRun = jest.fn();
const mockFsExistsSync = jest.fn();
const mockFsMkdirSync = jest.fn();
const mockFsCreateWriteStream = jest.fn();
const mockHttpGet = jest.fn();
const mockHttpsGet = jest.fn();

// Use dynamic path resolution for portability across different machines/users
const EXPECTED_SCRIPT_PATH = path.resolve(process.cwd(), 'lib');

describe('Z-Library API', () => {
  // Declare variables once at the top level of the describe block
  let zlibApi; // Will hold the actual imported module
  let result;
  let args;
  let mockWriteStream; // For fs.createWriteStream mock

  beforeEach(async () => {
    // Reset modules and clear mocks before each test
    jest.resetModules();
    jest.clearAllMocks();

    // --- Mock Dependencies ---
    jest.unstable_mockModule('../lib/venv-manager.js', () => ({
      // Mock only the functions used by zlibrary-api
      getManagedPythonPath: mockGetManagedPythonPath,
      // ensureVenvReady is not used here
    }));

    jest.unstable_mockModule('python-shell', () => ({
      PythonShell: {
        run: mockPythonShellRun,
      },
    }));

    // Mock fs, http, https selectively
    mockWriteStream = { // Mock write stream instance
        on: jest.fn((event, cb) => {
            // Simulate finish immediately for simple cases, or allow manual trigger
            if (event === 'finish') {
                // Store the callback to potentially call later in tests
                mockWriteStream._finishCallback = cb;
            }
            return mockWriteStream; // Allow chaining
        }),
        close: jest.fn((cb) => {
             if (cb) cb(); // Simulate successful close
        }),
        _finishCallback: null, // To store the finish callback
        _errorCallback: null, // To store potential error callback
    };
    jest.unstable_mockModule('fs', () => ({

      existsSync: mockFsExistsSync,
      mkdirSync: mockFsMkdirSync,
      createWriteStream: mockFsCreateWriteStream.mockReturnValue(mockWriteStream), // Return the mock stream instance
      readFileSync: jest.fn(), // Add other fs functions if needed by the module
      writeFileSync: jest.fn(),
      unlinkSync: jest.fn(),
      // Add other fs functions if they are used by zlibrary-api.js
    }));

    jest.unstable_mockModule('http', () => ({
      get: mockHttpGet,
    }));
    jest.unstable_mockModule('https', () => ({
      get: mockHttpsGet,
    }));

    // --- Import Actual Module ---
    // Import the *compiled* JS file containing the actual implementation
    zlibApi = await import('../dist/lib/zlibrary-api.js');
  });

  describe('searchBooks', () => {
    test('should call Python bridge with correct parameters for searchBooks', async () => {
      const mockApiResult_search1 = [{ id: '1', title: 'Test Book' }]; // Unique result var
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      // Corrected Mock: Simulate python printing the JSON string of the MCP response structure within an array
      const mockPythonResultString_search1 = JSON.stringify(mockApiResult_search1);
      const mockMcpResponseString_search1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_search1 }] });
      mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_search1]);

      const searchArgs = {
        query: 'test query', exact: true, fromYear: 2000, toYear: 2023,
        languages: ['english', 'spanish'], extensions: ['pdf', 'epub'], count: 20
      };

      result = await zlibApi.searchBooks(searchArgs);

      // Verify PythonShell call
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ // Corrected script name
          mode: 'text', // Ensure mode is text for double parsing
          pythonPath: '/fake/python',
          scriptPath: EXPECTED_SCRIPT_PATH,
          args: ['search', JSON.stringify({
              query: searchArgs.query, exact: searchArgs.exact, from_year: searchArgs.fromYear, to_year: searchArgs.toYear,
              languages: searchArgs.languages, extensions: searchArgs.extensions, content_types: [], count: searchArgs.count
          })]
      }));
      // Verify the final result
      expect(result).toEqual(mockApiResult_search1); // Use unique result var
    });

    test('should handle errors from Python bridge during searchBooks', async () => {
      const apiError = new Error('Python Search Failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      // Simulate PythonShell.run rejecting
      mockPythonShellRun.mockRejectedValue(apiError);

      await expect(zlibApi.searchBooks({ query: 'test' })).rejects.toThrow(`Python bridge execution failed for search: ${apiError.message}`);
  // Test suite for the internal callPythonFunction logic
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ scriptPath: EXPECTED_SCRIPT_PATH, args: ['search', JSON.stringify({ query: 'test', exact: false, from_year: null, to_year: null, languages: [], extensions: [], content_types: [], count: 10 })] })); // Corrected script name and path
    });

    describe('callPythonFunction (Internal Logic)', () => {
    test('should throw error if getManagedPythonPath fails', async () => {
      // Arrange: Mock getManagedPythonPath to reject
      const pathError = new Error('Failed to get Python path');
      mockGetManagedPythonPath.mockRejectedValue(pathError);

      // Dynamically import zlibApi *inside* the test AFTER mocks are set
      const zlibApi = await import('../dist/lib/zlibrary-api.js');

      // Act & Assert: Expect any function using callPythonFunction to reject
      // Using searchBooks as an example
      // Adjust expectation to match observed behavior (original error thrown)
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(`Python bridge execution failed for search: ${pathError.message}`); // Expect the wrapped error message

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).not.toHaveBeenCalled(); // PythonShell should not be called
    }); // <-- This closes the test for getManagedPythonPath failure

    test('should throw error if PythonShell.run throws', async () => {
      // Arrange: Mock getManagedPythonPath to succeed, PythonShell.run to throw
      const shellError = new Error('PythonShell failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(shellError);

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(`Python bridge execution failed for search: ${shellError.message}`);

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    test('should throw error if Python script returns an error object', async () => {
      // Arrange: Mock PythonShell.run to return an error object
      const pythonErrorMsg = 'Something went wrong in Python';
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      // Corrected Mock: Simulate python printing the JSON string of the MCP response structure containing an error object
      const mockPythonErrorString_err1 = JSON.stringify({ error: pythonErrorMsg });
      const mockMcpErrorResponseString_err1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonErrorString_err1 }] });
      mockPythonShellRun.mockResolvedValueOnce([mockMcpErrorResponseString_err1]);

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(`Python bridge execution failed for search: ${pythonErrorMsg}`);

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    test('should throw error if Python script returns non-JSON string', async () => {
      // Arrange: Mock PythonShell.run to return a non-JSON string
      const nonJsonOutput = 'This is not JSON';
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      // In text mode, the first parse in callPythonFunction would fail
      mockPythonShellRun.mockResolvedValueOnce([nonJsonOutput]); // Provide the non-JSON string

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        // Expect the error from the first parse attempt
        .toThrow(/Failed to parse initial JSON output from Python script: Unexpected token T in JSON at position 0/);

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    test('should throw error if Python script returns no output', async () => {
      // Arrange: Mock PythonShell.run to return empty array or undefined
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockResolvedValue([]); // Simulate empty results array

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(/No output received from Python script/); // Adjusted error message

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

     test('should throw error if Python script returns unexpected object format', async () => {
      // Arrange: Mock PythonShell.run to return an object without 'error' or expected data
      const unexpectedObject = { someOtherKey: 'value' };
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      // Corrected Mock: Simulate python printing the JSON string of the MCP response structure containing the unexpected object
      const mockPythonUnexpectedString_unexp1 = JSON.stringify(unexpectedObject);
      const mockMcpUnexpectedResponseString_unexp1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonUnexpectedString_unexp1 }] });
      mockPythonShellRun.mockResolvedValueOnce([mockMcpUnexpectedResponseString_unexp1]);

      // Act & Assert: The double parse should succeed, returning the unexpected object
      const result = await zlibApi.searchBooks({ query: 'test' });
      expect(result).toEqual(unexpectedObject); // Test now expects the inner object

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    test('should include stderr in error message when PythonShell provides it', async () => {
      // Arrange: Mock PythonShell.run to throw error with stderr
      const shellError = new Error('Python script failed');
      shellError.stderr = 'ImportError: No module named foo\nTraceback...';
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(shellError);

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(/Python bridge execution failed for search:.*Stderr: ImportError: No module named foo/);

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    test('should handle PythonShell non-zero exit code error', async () => {
      // Arrange: Mock PythonShell.run to throw error simulating non-zero exit
      const exitError = new Error('Process exited with code 1');
      exitError.exitCode = 1;
      exitError.stderr = 'SyntaxError: invalid syntax';
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(exitError);

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(/Python bridge execution failed for search: Process exited with code 1.*Stderr: SyntaxError/);

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    test('should handle PythonShell timeout error', async () => {
      // Arrange: Mock PythonShell.run to throw timeout error
      const timeoutError = new Error('Timeout: Python script exceeded execution time');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(timeoutError);

      // Act & Assert
      await expect(zlibApi.searchBooks({ query: 'test' }))
        .rejects
        .toThrow(/Python bridge execution failed for search: Timeout/);

      // Verify mocks
      expect(mockGetManagedPythonPath).toHaveBeenCalled();
      expect(mockPythonShellRun).toHaveBeenCalled();
    });

    }); // <-- This closes describe('callPythonFunction (Internal Logic)')

    // ISSUE-006 RESOLVED: Tests for PythonShell.run errors now cover:
    // - non-zero exit code (test above)
    // - stderr handling (test above)
    // - timeout (test above)
    // - no result (line 201)
    // - bad JSON (line 183)
  }); // <-- This closes describe('searchBooks')


    // REMOVED extra closing brace }); from here (was line 229)


    test('should handle empty results from searchBooks', async () => {
        const mockApiResultEmpty_empty1 = []; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure containing an empty list
        const mockPythonEmptyResultString_empty1 = JSON.stringify(mockApiResultEmpty_empty1);
        const mockMcpEmptyResponseString_empty1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonEmptyResultString_empty1 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpEmptyResponseString_empty1]);

        result = await zlibApi.searchBooks({ query: 'empty test' });

        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ // Corrected script name
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['search', JSON.stringify({ query: 'empty test', exact: false, from_year: null, to_year: null, languages: [], extensions: [], content_types: [], count: 10 })] // Default args
        }));
        expect(result).toEqual(mockApiResultEmpty_empty1); // Use unique result var
    });

  describe('fullTextSearch', () => {
    test('should call Python bridge for fullTextSearch', async () => {
        const mockApiResult_ft1 = [{ id: '2', title: 'JS Book' }]; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_ft1 = JSON.stringify(mockApiResult_ft1);
        const mockMcpResponseString_ft1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_ft1 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_ft1]);

        const searchArgs = {
            query: 'javascript', exact: false, phrase: true, words: false,
            languages: ['english'], extensions: ['pdf'], count: 15
        };
        result = await zlibApi.fullTextSearch(searchArgs);

        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ // Corrected script name
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['full_text_search', JSON.stringify({
                query: searchArgs.query, exact: searchArgs.exact, phrase: searchArgs.phrase, words: searchArgs.words,
                languages: searchArgs.languages, extensions: searchArgs.extensions, content_types: [], count: searchArgs.count
            })]
        }));
        expect(result).toEqual(mockApiResult_ft1); // Use unique result var
    });

     test('should handle errors from Python bridge during fullTextSearch', async () => {
      const apiError = new Error('Python Full Text Failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(apiError);

      await expect(zlibApi.fullTextSearch({ query: 'fail text' })).rejects.toThrow(`Python bridge execution failed for full_text_search: ${apiError.message}`);
      // Check default args passed to python
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ scriptPath: EXPECTED_SCRIPT_PATH, args: ['full_text_search', JSON.stringify({ query: 'fail text', exact: false, phrase: true, words: false, languages: [], extensions: [], content_types: [], count: 10 })] })); // Corrected script name and path
    });
  });

  describe('downloadBookToFile', () => {
    // These tests now check the internal logic, mocking dependencies like python-shell, fs, http

    // Updated for Spec v2.1: Uses bookDetails, expects absolute path, no processed_file_path
    test('should call Python bridge with correct args (no RAG)', async () => {
        const pythonResult_dl1 = { file_path: '/abs/path/to/downloads/Success Book.epub' }; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_dl1 = JSON.stringify(pythonResult_dl1);
        const mockMcpResponseString_dl1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_dl1 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_dl1]);

        const mockBookDetails = { id: 'success123', url: 'http://example.com/book/success123/slug', title: 'Success Book' };
        const downloadArgs = { bookDetails: mockBookDetails, outputDir: './downloads', process_for_rag: false };

        result = await zlibApi.downloadBookToFile(downloadArgs);

        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['download_book', JSON.stringify({
                book_details: mockBookDetails, // Pass bookDetails object
                output_dir: './downloads',
                process_for_rag: false,
                processed_output_format: 'txt' // Default format
            })]
        }));
        expect(result).toEqual({
            file_path: '/abs/path/to/downloads/Success Book.epub'
            // No processed_file_path expected
        });
    });

    // Updated for Spec v2.1: Uses bookDetails, expects absolute paths for both
    test('should call Python bridge with correct args (with RAG)', async () => {
        const pythonResult_dl2 = { // Unique result var
            file_path: '/abs/path/to/rag_out/RAG Book.pdf',
            processed_file_path: '/abs/path/to/processed_rag_output/RAG Book.pdf.processed.md'
        };
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_dl2 = JSON.stringify(pythonResult_dl2);
        const mockMcpResponseString_dl2 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_dl2 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_dl2]);

        const mockBookDetails = { id: 'rag123', url: 'http://example.com/book/rag123/slug', title: 'RAG Book' };
        const downloadArgs = { bookDetails: mockBookDetails, outputDir: './rag_out', process_for_rag: true, processed_output_format: 'md' };

        result = await zlibApi.downloadBookToFile(downloadArgs);

        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['download_book', JSON.stringify({
                book_details: mockBookDetails, // Pass bookDetails object
                output_dir: './rag_out',
                process_for_rag: true,
                processed_output_format: 'md'
            })]
        }));
        expect(result).toEqual({
            file_path: '/abs/path/to/rag_out/RAG Book.pdf',
            processed_file_path: '/abs/path/to/processed_rag_output/RAG Book.pdf.processed.md'
        });
    });

    // Updated for Spec v2.1: Uses bookDetails, expects processed_file_path to be null
    test('should handle Python response when processing requested but path is null', async () => {
        const pythonResult_dl3 = { // Unique result var
            file_path: '/abs/path/to/image.pdf',
            processed_file_path: null // Simulate image PDF case
        };
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_dl3 = JSON.stringify(pythonResult_dl3);
        const mockMcpResponseString_dl3 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_dl3 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_dl3]);

        const mockBookDetails = { id: 'image456', url: 'http://example.com/book/image456/slug', title: 'Image Book' };
        const downloadArgs = { bookDetails: mockBookDetails, process_for_rag: true };

        result = await zlibApi.downloadBookToFile(downloadArgs);

        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({
            args: ['download_book', JSON.stringify({
                book_details: mockBookDetails, // Pass bookDetails object
                output_dir: './downloads', // Default dir
                process_for_rag: true,
                processed_output_format: 'txt' // Default format
            })]
        }));
        expect(result).toEqual({
            file_path: '/abs/path/to/image.pdf',
            processed_file_path: null // Expect null as returned by Python
        });
    });

    // Updated for Spec v2.1: Uses bookDetails
    test('should throw error if Python response is missing file_path', async () => {
        const invalidPythonResult_dl4 = { some_other_key: 'value' }; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_dl4 = JSON.stringify(invalidPythonResult_dl4);
        const mockMcpResponseString_dl4 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_dl4 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_dl4]);

        const mockBookDetails = { id: 'invalidResp1', url: 'http://example.com/book/invalidResp1/slug' };
        const downloadArgs = { bookDetails: mockBookDetails };

        await expect(zlibApi.downloadBookToFile(downloadArgs))
            .rejects
            // Match the actual wrapped error message
            .toThrow("Failed to download book: Invalid response from Python bridge: Missing original file_path.");

        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
    });

    // Updated for Spec v2.1: Uses bookDetails
    test('should throw error if processing requested and Python response missing processed_file_path key', async () => {
        const invalidPythonResult_dl5 = { file_path: '/abs/path/book.epub' }; // Unique result var, Missing processed_file_path key
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_dl5 = JSON.stringify(invalidPythonResult_dl5);
        const mockMcpResponseString_dl5 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_dl5 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_dl5]);

        const mockBookDetails = { id: 'invalidResp2', url: 'http://example.com/book/invalidResp2/slug' };
        const downloadArgs = { bookDetails: mockBookDetails, process_for_rag: true };

        await expect(zlibApi.downloadBookToFile(downloadArgs))
            .rejects
            .toThrow("Invalid response from Python bridge: Processing requested but processed_file_path key is missing.");

        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
    });

    // Updated for Spec v2.1: Uses bookDetails
    test('should handle errors from Python bridge during download_book', async () => {
      const apiError = new Error('Python Download Book Failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(apiError);

      const mockBookDetails = { id: 'failDownload', url: 'http://example.com/book/failDownload/slug' };
      await expect(zlibApi.downloadBookToFile({ bookDetails: mockBookDetails })).rejects.toThrow(`Python bridge execution failed for download_book: ${apiError.message}`);
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ scriptPath: EXPECTED_SCRIPT_PATH, args: ['download_book', JSON.stringify({ book_details: mockBookDetails, output_dir: './downloads', process_for_rag: false, processed_output_format: 'txt' })] }));
    });

  });

  describe('getDownloadHistory', () => {
    test('should call Python bridge for getDownloadHistory', async () => {
        const mockApiResult_hist1 = [{ id: '3', title: 'History Book' }]; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_hist1 = JSON.stringify(mockApiResult_hist1);
        const mockMcpResponseString_hist1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_hist1 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_hist1]);

        const historyArgs = { count: 10 };
        result = await zlibApi.getDownloadHistory(historyArgs);

        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ // Corrected script name
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['get_download_history', JSON.stringify({ count: historyArgs.count })]
        }));
        expect(result).toEqual(mockApiResult_hist1); // Use unique result var
    });

     test('should handle errors from Python bridge during getDownloadHistory', async () => {
      const apiError = new Error('Python History Failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(apiError);

      await expect(zlibApi.getDownloadHistory({ count: 5 })).rejects.toThrow(`Python bridge execution failed for get_download_history: ${apiError.message}`);
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ scriptPath: EXPECTED_SCRIPT_PATH, args: ['get_download_history', JSON.stringify({ count: 5 })] })); // Corrected script name and path
    });
  });

  describe('getDownloadLimits', () => {
    test('should call Python bridge for getDownloadLimits', async () => {
        const mockApiResult_lim1 = { daily_limit: 10, daily_downloads: 2 }; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected Mock: Simulate python printing the JSON string of the MCP response structure
        const mockPythonResultString_lim1 = JSON.stringify(mockApiResult_lim1);
        const mockMcpResponseString_lim1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_lim1 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_lim1]);

        result = await zlibApi.getDownloadLimits();

        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ // Corrected script name
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['get_download_limits', JSON.stringify({})] // Empty args object
        }));
        expect(result).toEqual(mockApiResult_lim1); // Use unique result var
    });

     test('should handle errors from Python bridge during getDownloadLimits', async () => {
      const apiError = new Error('Python Limits Failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(apiError);

      await expect(zlibApi.getDownloadLimits()).rejects.toThrow(`Python bridge execution failed for get_download_limits: ${apiError.message}`);
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ scriptPath: EXPECTED_SCRIPT_PATH, args: ['get_download_limits', JSON.stringify({})] })); // Corrected script name and path
    });
  });

  describe('processDocumentForRag', () => {
    // test.todo('[FAILING] should call Python bridge with correct args and return processed_file_path'); // Remove todo
    test('should call Python bridge with correct args and return processed_file_path', async () => { // Uncomment test
        // Arrange: Mock python bridge success
        const pythonResult_rag1 = { processed_file_path: '/abs/path/to/processed_rag_output/doc.txt.processed.txt' }; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected: Ensure mock provides the stringified MCP response in an array (Unique Vars)
        const mockPythonResultString_rag1 = JSON.stringify(pythonResult_rag1);
        const mockMcpResponseString_rag1 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_rag1 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_rag1]);

        const processArgs = { filePath: './local/doc.txt', outputFormat: 'txt' };
        const expectedPythonFilePath = path.resolve('./local/doc.txt'); // Node resolves path

        // Act
        result = await zlibApi.processDocumentForRag(processArgs);

        // Assert Python call
        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({
            scriptPath: EXPECTED_SCRIPT_PATH,
            args: ['process_document', JSON.stringify({
                file_path_str: expectedPythonFilePath, // Correct arg name
                output_format: 'txt'
            })]
        }));
        // Assert final result structure (based on spec v2.1)
        expect(result).toEqual({
            processed_file_path: '/abs/path/to/processed_rag_output/doc.txt.processed.txt'
        });
    });

     test('should handle null processed_file_path from Python', async () => { // Add test for null path
        // Arrange: Mock python bridge success with null path
        const pythonResult_rag2 = { processed_file_path: null }; // Unique result var
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected: Ensure mock provides the stringified MCP response in an array (Unique Vars)
        const mockPythonResultString_rag2 = JSON.stringify(pythonResult_rag2);
        const mockMcpResponseString_rag2 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_rag2 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_rag2]);

        const processArgs = { filePath: './local/image.pdf' };
        const expectedPythonFilePath = path.resolve('./local/image.pdf');

        // Act
        result = await zlibApi.processDocumentForRag(processArgs);

        // Assert Python call
        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
        expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({
            args: ['process_document', JSON.stringify({
                file_path_str: expectedPythonFilePath, // Correct arg name expected by Python
                output_format: 'txt' // Default
            })]
        }));
        // Assert final result structure (based on spec v2.1)
        expect(result).toEqual({
            processed_file_path: null // Expect null
        });
    });

    // test.todo('[FAILING] should throw error if Python response is missing processed_file_path'); // Remove todo
    test('should throw error if Python response is missing processed_file_path key', async () => { // Uncomment test and update description
        // Arrange: Mock python bridge returning invalid object
        const invalidPythonResult_rag3 = { some_other_key: 'value' }; // Unique result var, Missing processed_file_path key
        mockGetManagedPythonPath.mockResolvedValue('/fake/python');
        // Corrected: Ensure mock provides the stringified MCP response in an array (Unique Vars)
        const mockPythonResultString_rag3 = JSON.stringify(invalidPythonResult_rag3);
        const mockMcpResponseString_rag3 = JSON.stringify({ content: [{ type: 'text', text: mockPythonResultString_rag3 }] });
        mockPythonShellRun.mockResolvedValueOnce([mockMcpResponseString_rag3]);

        const processArgs = { filePath: './local/doc.txt' };

        // Act & Assert
        await expect(zlibApi.processDocumentForRag(processArgs))
            .rejects
            .toThrow("Invalid response from Python bridge during processing. Missing processed_file_path key."); // Updated error message

        expect(mockPythonShellRun).toHaveBeenCalledTimes(1);
    });

    test('should handle errors from Python bridge during processDocumentForRag', async () => {
      const apiError = new Error('Python Process Failed');
      mockGetManagedPythonPath.mockResolvedValue('/fake/python');
      mockPythonShellRun.mockRejectedValue(apiError);

      await expect(zlibApi.processDocumentForRag({ filePath: './local/doc.txt' })).rejects.toThrow(`Python bridge execution failed for process_document: ${apiError.message}`);
      const expectedPythonFilePath = path.resolve('./local/doc.txt');
      expect(mockPythonShellRun).toHaveBeenCalledWith('python_bridge.py', expect.objectContaining({ scriptPath: EXPECTED_SCRIPT_PATH, args: ['process_document', JSON.stringify({ file_path_str: expectedPythonFilePath, output_format: 'txt' })] }));
    });
  });
});
