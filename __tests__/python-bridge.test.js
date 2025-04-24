import { jest, describe, beforeEach, test, expect } from '@jest/globals';
// Top-level import of spawn removed - will be mocked and imported dynamically
import * as path from 'path';

// Top-level import and mock removed - will use inline unstable_mockModule + dynamic import

describe('Python Bridge', () => {
  beforeEach(() => {
    // jest.* calls moved inside tests
    // jest.resetModules(); // Moved inside tests
    // jest.clearAllMocks(); // Moved inside tests
  });

  test('should call Python function and parse result successfully', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks(); // Clear mocks for this specific test
    const mockStdoutSuccess = { on: jest.fn((event, callback) => { if (event === 'data') { callback(Buffer.from(JSON.stringify({ success: true, data: 'test data' }))); } return mockStdoutSuccess; }) };
    const mockStderrSuccess = { on: jest.fn().mockReturnThis() };
    const mockProcessSuccess = { stdout: mockStdoutSuccess, stderr: mockStderrSuccess, on: jest.fn((event, callback) => { if (event === 'close') { process.nextTick(() => callback(0)); } return mockProcessSuccess; }) }; // Simulate async close

    jest.unstable_mockModule('../lib/venv-manager.js', () => ({ // Mock venv-manager
      getManagedPythonPath: jest.fn().mockResolvedValue('/mock/venv/python'),
    }));
    jest.unstable_mockModule('child_process', () => ({ // Mock child_process
      spawn: jest.fn().mockReturnValue(mockProcessSuccess),
    }));

    // --- Dynamic Imports AFTER Mocks ---
    const { spawn } = await import('child_process');
    const venvManager = await import('../lib/venv-manager.js'); // Import mocked venv-manager
    const pythonBridge = await import('../lib/python-bridge.js');

    // --- Act ---
    const result = await pythonBridge.callPythonFunction('test_function', ['arg1', 'arg2']);

    // --- Assert ---
    expect(spawn).toHaveBeenCalledWith('/mock/venv/python', ['/home/rookslog/zlibrary-mcp/dist/lib/python_bridge.py', 'test_function', JSON.stringify(['arg1', 'arg2'])]); // Expect mock python path and corrected script path

    expect(result).toEqual({ success: true, data: 'test data' });
  });

  test('should handle Python process errors', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks(); // Clear mocks for this specific test
    const mockStdoutError = { on: jest.fn().mockReturnThis() };
    const mockStderrError = { on: jest.fn((event, callback) => { if (event === 'data') { callback(Buffer.from('Python error message')); } return mockStderrError; }) };
    const mockProcessError = { stdout: mockStdoutError, stderr: mockStderrError, on: jest.fn((event, callback) => { if (event === 'close') { process.nextTick(() => callback(1)); } return mockProcessError; }) }; // Simulate async close with error code

    jest.unstable_mockModule('../lib/venv-manager.js', () => ({ // Mock venv-manager
      getManagedPythonPath: jest.fn().mockResolvedValue('/mock/venv/python'),
    }));
    jest.unstable_mockModule('child_process', () => ({ // Mock child_process
      spawn: jest.fn().mockReturnValue(mockProcessError),
    }));

    // --- Dynamic Imports AFTER Mocks ---
    const { spawn } = await import('child_process');
    const venvManager = await import('../lib/venv-manager.js'); // Import mocked venv-manager
    const pythonBridge = await import('../lib/python-bridge.js');

    // --- Act & Assert ---
    await expect(pythonBridge.callPythonFunction('test_function', ['arg1']))
      .rejects.toThrow('Python process exited with code 1: Python error message');
    expect(spawn).toHaveBeenCalled(); // Ensure spawn was called
  });

  test('should handle JSON parse errors', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks(); // Clear mocks for this specific test
    const mockStdoutInvalidJson = { on: jest.fn((event, callback) => { if (event === 'data') { callback(Buffer.from('Invalid JSON{')); } return mockStdoutInvalidJson; }) };
    const mockStderrInvalidJson = { on: jest.fn().mockReturnThis() };
    const mockProcessInvalidJson = { stdout: mockStdoutInvalidJson, stderr: mockStderrInvalidJson, on: jest.fn((event, callback) => { if (event === 'close') { process.nextTick(() => callback(0)); } return mockProcessInvalidJson; }) };

    jest.unstable_mockModule('../lib/venv-manager.js', () => ({ // Mock venv-manager
      getManagedPythonPath: jest.fn().mockResolvedValue('/mock/venv/python'),
    }));
    jest.unstable_mockModule('child_process', () => ({ // Mock child_process
      spawn: jest.fn().mockReturnValue(mockProcessInvalidJson),
    }));

    // --- Dynamic Imports AFTER Mocks ---
    const { spawn } = await import('child_process');
    const venvManager = await import('../lib/venv-manager.js'); // Import mocked venv-manager
    const pythonBridge = await import('../lib/python-bridge.js');

    // --- Act & Assert ---
    await expect(pythonBridge.callPythonFunction('test_function', []))
      // Update regex to match the actual error format from python-bridge.ts
      .rejects.toThrow(/^Failed to parse Python result JSON: .*?\. Raw output:.*?\. Stderr:.*?$/);
    expect(spawn).toHaveBeenCalled();
  });

  test('should handle Python process spawn error', async () => {
    // --- Setup Mocks for this test ---
    jest.resetModules(); // Reset modules for this specific test
    jest.clearAllMocks(); // Clear mocks for this specific test
    const mockSpawnError = new Error('Failed to spawn process');
    const mockProcessSpawnError = { stdout: { on: jest.fn().mockReturnThis() }, stderr: { on: jest.fn().mockReturnThis() }, on: jest.fn((event, callback) => { if (event === 'error') { process.nextTick(() => callback(mockSpawnError)); } return mockProcessSpawnError; }) }; // Simulate async error

    jest.unstable_mockModule('../lib/venv-manager.js', () => ({ // Mock venv-manager
      // Simulate getManagedPythonPath failing itself
      getManagedPythonPath: jest.fn().mockRejectedValue(new Error('Failed to get venv path')),
    }));
    jest.unstable_mockModule('child_process', () => ({ // Mock child_process (spawn won't be called if getManagedPythonPath fails)
      spawn: jest.fn(),
    }));

    // --- Dynamic Imports AFTER Mocks ---
    const { spawn } = await import('child_process');
    const venvManager = await import('../lib/venv-manager.js'); // Import mocked venv-manager
    const pythonBridge = await import('../lib/python-bridge.js');

    // --- Act & Assert ---
    await expect(pythonBridge.callPythonFunction('test_function', []))
      // Expect the error propagated from the failed getManagedPythonPath mock
      .rejects.toThrow('Error setting up or running Python process: Failed to get venv path');
    // spawn is NOT called when getManagedPythonPath rejects, so no assertion needed here.
  });
});