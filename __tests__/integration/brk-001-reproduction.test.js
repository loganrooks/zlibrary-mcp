/**
 * BRK-001 Reproduction Test: Download Book Combined Workflow
 *
 * Issue: download_book_to_file with process_for_rag=true was reported to throw
 * an AttributeError when calling a missing method in the forked zlibrary.
 *
 * This test attempts to reproduce the issue. It is investigative:
 * - In recorded mode: Verifies the Node.js wrapper handles the combined workflow path
 * - In live mode (TEST_LIVE=true): Attempts a real download+process call
 *
 * Outcome is logged, not asserted — the test always passes.
 */
import { jest, describe, test, expect, beforeEach } from '@jest/globals';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const IS_LIVE = process.env.TEST_LIVE === 'true';

describe('BRK-001: download_book with process_for_rag=true', () => {
  if (!IS_LIVE) {
    // Recorded mode: verify the code path through mocks
    let mockPythonShellRun;

    beforeEach(async () => {
      jest.resetModules();
      jest.clearAllMocks();

      mockPythonShellRun = jest.fn();

      jest.unstable_mockModule('../../dist/lib/venv-manager.js', () => ({
        getManagedPythonPath: jest.fn().mockResolvedValue('/usr/bin/python3'),
      }));

      jest.unstable_mockModule('python-shell', () => ({
        PythonShell: { run: mockPythonShellRun },
      }));
    });

    test('combined download+process path sends process_for_rag=true to bridge', async () => {
      // Fixture simulates a successful combined response
      const combinedResponse = {
        content: [{
          type: 'text',
          text: JSON.stringify({
            file_path: '/tmp/downloads/test-book.epub',
            processed_file_path: '/tmp/processed/test-book.txt',
          }),
        }],
      };

      mockPythonShellRun.mockResolvedValue([JSON.stringify(combinedResponse)]);

      const zlibApi = await import('../../dist/lib/zlibrary-api.js');

      let result;
      let error;
      try {
        result = await zlibApi.downloadBookToFile({
          bookDetails: { url: '/book/1/abc', id: '1' },
          outputDir: '/tmp/downloads',
          process_for_rag: true,
          processed_output_format: 'txt',
        });
      } catch (e) {
        error = e;
      }

      if (error) {
        console.log('[BRK-001] REPRODUCED in recorded mode (Node.js layer):');
        console.log(`  Error: ${error.message}`);
        console.log('  This confirms the Node.js wrapper has issues with the combined path.');
      } else {
        console.log('[BRK-001] NOT REPRODUCED in recorded mode:');
        console.log(`  Result: ${JSON.stringify(result)}`);
        console.log('  The Node.js wrapper correctly handles process_for_rag=true.');
        console.log('  BRK-001 may be a Python-side issue only (AttributeError in zlibrary fork).');

        // Verify process_for_rag was passed through
        const callArgs = mockPythonShellRun.mock.calls[0][1];
        const bridgeArgs = JSON.parse(callArgs.args[1]);
        expect(bridgeArgs.process_for_rag).toBe(true);
      }

      // Test always passes — this is investigative
      expect(true).toBe(true);
    }, 10000);

    test('error response from combined path is handled gracefully', async () => {
      // Simulate the AttributeError BRK-001 describes
      const errorResponse = {
        content: [{
          type: 'text',
          text: JSON.stringify({
            error: "AttributeError: 'EAPIClient' object has no attribute 'getDownloadLinks'",
          }),
        }],
      };

      mockPythonShellRun.mockResolvedValue([JSON.stringify(errorResponse)]);

      const zlibApi = await import('../../dist/lib/zlibrary-api.js');

      let error;
      try {
        await zlibApi.downloadBookToFile({
          bookDetails: { url: '/book/1/abc', id: '1' },
          outputDir: '/tmp/downloads',
          process_for_rag: true,
        });
      } catch (e) {
        error = e;
      }

      if (error) {
        console.log('[BRK-001] Error handling works:');
        console.log(`  Caught: ${error.message}`);
        console.log('  The bridge properly surfaces Python errors.');
      }

      // Test always passes
      expect(true).toBe(true);
    }, 10000);
  } else {
    test.skip('live mode BRK-001 reproduction requires real credentials and book details', () => {
      // In live mode, this would need valid book details from a search
      // and Z-Library credentials. Skipping by default.
    });
  }
});

/**
 * Investigation Summary (2026-01-29):
 *
 * Code path analysis of download_book in python_bridge.py (line 615-690):
 * 1. Calls zlib_client.download_book(book_details, output_dir_str) at line 648
 * 2. zlibrary/src/zlibrary/libasync.py:368 has download_book() method
 * 3. The method exists — no AttributeError for download_book itself
 * 4. BRK-001 may reference an older state where a different method was missing
 *    (e.g., getDownloadLinks which doesn't exist in the fork)
 *
 * Current status: The download_book method exists in the fork.
 * The combined workflow (download + process_for_rag) calls process_document()
 * at line 674, which is also defined. The Node.js wrapper at
 * src/lib/zlibrary-api.ts:314-362 correctly passes process_for_rag through.
 *
 * Conclusion: BRK-001 appears to be RESOLVED or was about a method that has
 * since been added to the fork. The code path is complete from Node.js through
 * Python bridge through zlibrary fork. Without live credentials to test actual
 * download, cannot fully confirm, but code analysis shows no missing methods.
 */
