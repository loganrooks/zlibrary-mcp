import { jest, describe, beforeEach, test, expect, it } from '@jest/globals';
import { fileURLToPath } from 'url';
import * as path from 'path';
import * as fs from 'fs'; // Move fs import to top
import * as childProcess from 'child_process'; // Re-add child_process import

// Helper function to create a mock spawn implementation
// Removed complex mockSpawnImplementation helper


// import * as VenvManager from '../lib/venv-manager.js'; // Will use dynamic import

// Manual mock for env-paths in __mocks__/env-paths.js is used automatically by Jest.
// No need for jest.mock() here.


// Removed top-level __dirname calculation; will use process.cwd()


// Top-level mocks for fs and child_process removed - will use inline mocking

describe('VenvManager', () => {
  // Removed top-level variable declarations for mocks

  beforeEach(() => {
    // jest.* calls moved inside tests
    // jest.resetModules(); // Moved inside tests
    // jest.clearAllMocks(); // Moved inside tests

    // Mock assignments removed - will be handled inside tests
  });

  describe('findPythonExecutable', () => {
    // These tests still rely on execSync, keep child_process mock here for now
    // TODO: Refactor findPythonExecutable to use runCommand async?
    it.todo('should find a compatible python3 executable on PATH');
    it.todo('should throw an error if no compatible python3 is found');
  });

  describe('createVenv', () => {
    it.todo('should create the virtual environment in the correct cache directory');
    it.todo('should handle venv creation failures');
  });

  describe('ensureVenvReady (Dependency Installation)', () => {
    test('should run full setup (create venv, install deps) if no config exists', async () => {
      // --- Setup Mocks for this test ---
      jest.resetModules(); // Re-introduce resetModules
      jest.clearAllMocks();

      const mockFsExistsSync = jest.fn().mockImplementation((p) => p !== '/mock/cache/dir/.venv_config'); // No config file
      const mockFsWriteFileSync = jest.fn();
      const mockFsMkdirSync = jest.fn();
      const mockExecSync = jest.fn().mockReturnValue('Python 3.9.1'); // Found python3

      // Mock spawn: Simulate venv success (0), then pip install success (0)
      const mockSpawn = jest.fn().mockImplementation(() => {
        const mockProcess = {
          stdout: { on: jest.fn(), setEncoding: jest.fn() },
          stderr: { on: jest.fn(), setEncoding: jest.fn() },
          on: jest.fn((event, listener) => {
            // Simulate successful close event immediately for simplicity in this test
            if (event === 'close') {
              process.nextTick(() => listener(0)); // Simulate exit code 0
            }
            return mockProcess; // Return self for chaining
          }),
          // Add other methods if needed, e.g., kill
        };
        return mockProcess;
      });

      // --- Create Mock Dependencies ---
      const mockDeps = {
        fs: {
          existsSync: mockFsExistsSync,
          writeFileSync: mockFsWriteFileSync,
          mkdirSync: mockFsMkdirSync,
          readFileSync: jest.fn(), // Not needed for this path
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: mockExecSync,
          spawn: mockSpawn,
        },
      };
      // Explicitly mock env-paths BEFORE importing venv-manager
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));

      // --- Dynamic Import ---
      const VenvManager = await import('../lib/venv-manager.js');
      // No longer need to import fs/child_process here for mocking


      // --- Act ---
      const expectedRequirementsPath = path.resolve(process.cwd(), 'requirements.txt'); // Use cwd() for root
      // const VenvManager = await import('../lib/venv-manager.js'); // Removed duplicate import
      await VenvManager.ensureVenvReady(mockDeps); // Pass mock deps

      // --- Assert ---
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config');
      expect(mockDeps.child_process.execSync).toHaveBeenCalledWith('python3 --version', expect.anything());
      // Check spawn calls
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith('python3', ['-m', 'venv', '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv'], expect.anything());
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(
        '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv/bin/python',
        // Correct the expected path for requirements.txt
        ['-m', 'pip', 'install', '--no-cache-dir', '--force-reinstall', '--upgrade', '-r', path.resolve(process.cwd(), 'requirements.txt')],
        expect.anything()
      );
      expect(mockDeps.fs.writeFileSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config', '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv/bin/python', 'utf8');
    });

    test('should skip install if config exists and package check passes', async () => {
      // --- Setup Mocks for this test ---
      // jest.resetModules(); // Removed to test if unstable_mockModule persists
      jest.clearAllMocks();

      const mockVenvPythonPath = '/valid/venv/bin/python';
      // Mocks will be defined in mockDeps

      // Mock spawn: Simulate pip show success (0)
      const mockSpawn = jest.fn().mockImplementation(() => {
        const mockProcess = {
          stdout: { on: jest.fn(), setEncoding: jest.fn() },
          stderr: { on: jest.fn(), setEncoding: jest.fn() },
          on: jest.fn((event, listener) => {
            // Simulate successful close event immediately for pip show success
            if (event === 'close') {
              process.nextTick(() => listener(0)); // Simulate exit code 0
            }
            return mockProcess; // Return self for chaining
          }),
        };
        return mockProcess;
      });

      // Need execSync mock here because findPythonExecutable might still be called internally
      const mockExecSync = jest.fn().mockReturnValue('Python 3.9.1');

      // --- Create Mock Dependencies ---
      const mockFsExistsSync = jest.fn((p) => {
        if (p === '/tmp/jest-zlibrary-mcp-cache/.venv_config') return true;
        if (p === mockVenvPythonPath) return true;
        if (p === '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv') return true;
        return false;
      });
      const mockFsReadFileSync = jest.fn((p, encoding) => {
        if (p === '/tmp/jest-zlibrary-mcp-cache/.venv_config' && encoding === 'utf8') {
          return mockVenvPythonPath;
        }
        if (p.endsWith('requirements.txt')) {
             try { return jest.requireActual('fs').readFileSync(p, encoding); } catch { return ''; }
        }
        return '';
      });

      const mockDeps = {
        fs: {
          existsSync: mockFsExistsSync,
          readFileSync: mockFsReadFileSync,
          writeFileSync: jest.fn(),
          mkdirSync: jest.fn(),
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: mockExecSync, // Still needed if findPythonExecutable is called internally
          spawn: mockSpawn,
        },
      };
      // env-paths is mocked via __mocks__

      // --- Dynamic Import ---
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Spies removed, using unstable_mockModule ---

      // --- Act ---
      await VenvManager.ensureVenvReady(mockDeps); // Pass mock deps

      // --- Assert ---
      // Assert on the mocked fs module directly
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config');
      expect(mockDeps.fs.readFileSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config', 'utf8');
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockVenvPythonPath);
      // Check spawn call for pip show
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(mockVenvPythonPath, ['-m', 'pip', 'show', 'zlibrary'], {});
      // Ensure pip install was NOT called via spawn
      expect(mockDeps.child_process.spawn).not.toHaveBeenCalledWith(
          mockVenvPythonPath,
          expect.arrayContaining(['install', '-r']),
          expect.anything()
      );
      // findPythonExecutable might be called depending on internal logic, ensure mock exists
    });

    test('should throw error if install dependencies fails during initial setup', async () => {
      // --- Setup Mocks for this test ---
      // jest.resetModules(); // Removed to test if unstable_mockModule persists
      jest.clearAllMocks();

      const expectedRequirementsPath = path.resolve(process.cwd(), 'requirements.txt'); // Use cwd() for root
      // Simulate non-zero exit code instead of 'error' event
      const mockFsExistsSync = jest.fn().mockImplementation((p) => p !== '/mock/cache/dir/.venv_config'); // No config
      const mockFsWriteFileSync = jest.fn();
      const mockFsMkdirSync = jest.fn();
      const mockExecSync = jest.fn().mockReturnValue('Python 3.9.1'); // Found python3

      // Mock spawn: Simulate venv success (0), then pip install failure (exit code 1)
      const mockSpawn = jest.fn()
        .mockImplementationOnce(() => { // First call: venv creation (success)
          const mockProcess = {
            stdout: { on: jest.fn(), setEncoding: jest.fn() },
            stderr: { on: jest.fn(), setEncoding: jest.fn() },
            on: jest.fn((event, listener) => {
              if (event === 'close') {
                process.nextTick(() => listener(0)); // Simulate exit code 0
              }
              return mockProcess;
            }),
          };
          return mockProcess;
        })
        .mockImplementationOnce(() => { // Second call: pip install (failure)
          const mockProcess = {
            stdout: { on: jest.fn(), setEncoding: jest.fn() },
            // Update simulated stderr to match the path correction
            stderr: { on: jest.fn((event, cb) => {
                if (event === 'data') process.nextTick(() => cb(`ERROR: Could not open requirements file: [Errno 2] No such file or directory: '${path.resolve(process.cwd(), 'requirements.txt')}'`));
                return mockProcess;
            }), setEncoding: jest.fn() },
            on: jest.fn((event, listener) => {
              if (event === 'close') {
                process.nextTick(() => listener(1)); // Simulate exit code 1
              }
              // No 'error' event simulation here
              return mockProcess;
            }),
          };
          return mockProcess;
        });

      // --- Create Mock Dependencies ---
      const mockDeps = {
        fs: {
          existsSync: mockFsExistsSync,
          writeFileSync: mockFsWriteFileSync,
          mkdirSync: mockFsMkdirSync,
          readFileSync: jest.fn(), // Not needed for this path
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: mockExecSync,
          spawn: mockSpawn,
        },
      };
      // env-paths is mocked via __mocks__

      // --- Dynamic Import ---
      const VenvManager = await import('../lib/venv-manager.js');


      // REMOVED jest.spyOn calls previously here
      // --- Act & Assert ---
      // Expect the error message originating from the rejected runCommand promise (due to non-zero exit code), wrapped by ensureVenvReady
      try {
          await VenvManager.ensureVenvReady(mockDeps); // Pass mock deps
          // If it reaches here, the test failed because it didn't throw
          throw new Error('ensureVenvReady should have rejected but resolved instead.');
      } catch (error) {
          expect(error).toBeInstanceOf(Error);
          // Update expected error message to match corrected stderr simulation
          // Adjust regex to match the actual error structure ("from requirements.txt" part)
          const expectedReqPath = path.resolve(process.cwd(), 'requirements.txt');
          expect(error.message).toMatch(new RegExp(`^Failed to set up Python environment: Failed during pip installation from requirements\\.txt: Failed to install packages from requirements\\.txt \\(exit code 1\\)\\. Stderr: ERROR: Could not open requirements file: \\[Errno 2\\] No such file or directory: '${expectedReqPath.replace(/\\/g, '\\\\')}'\\. Please ensure Python 3 and venv are correctly installed and try again\\.$`));
      }

      // Verify mocks
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config');
      expect(mockDeps.child_process.execSync).toHaveBeenCalledWith('python3 --version', expect.anything());
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith('python3', ['-m', 'venv', '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv'], expect.anything());
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(
        '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv/bin/python',
        // Correct the expected path for requirements.txt
        ['-m', 'pip', 'install', '--no-cache-dir', '--force-reinstall', '--upgrade', '-r', path.resolve(process.cwd(), 'requirements.txt')],
        expect.anything()
      );
      expect(mockDeps.fs.writeFileSync).not.toHaveBeenCalled();
    });

    test('should reinstall if config exists but package check fails', async () => {
        // --- Setup Mocks for this test ---
        // jest.resetModules(); // Removed for consistency with unstable_mockModule
        jest.clearAllMocks();

        const mockVenvPythonPath = '/valid/but/needs/reinstall/bin/python';
        const expectedRequirementsPath = path.resolve(process.cwd(), 'requirements.txt'); // Use cwd() for root
        // Use the path derived from the env-paths mock
        // Mock functions will be defined inline below

        // Mock spawn: Simulate pip show failure (1), then pip install success (0)
        // Mock spawn: Check args to return correct mock behavior
        const mockSpawn = jest.fn().mockImplementation((command, args) => {
            const mockProcess = {
                stdout: { on: jest.fn(), setEncoding: jest.fn() },
                stderr: { on: jest.fn(), setEncoding: jest.fn() },
                on: jest.fn((event, listener) => {
                    let exitCode = 0;
                    // Simulate pip show failing (exit 1)
                    if (args.includes('show') && args.includes('zlibrary')) {
                        exitCode = 1;
                    }
                    // Simulate pip install succeeding (exit 0) - default
                    if (event === 'close') {
                        process.nextTick(() => listener(exitCode));
                    }
                    return mockProcess;
                }),
            };
            return mockProcess;
        });

        // Need execSync mock here as findPythonExecutable might be called
        const mockExecSync = jest.fn().mockReturnValue('Python 3.9.1');

        // --- Create Mock Dependencies ---
        const expectedReqPath = path.resolve(process.cwd(), 'requirements.txt');
        const expectedDevReqPath = path.resolve(process.cwd(), 'requirements-dev.txt');
        const mockFsExistsSync = jest.fn((p) => {
          if (p === '/tmp/jest-zlibrary-mcp-cache/.venv_config') return true;
          if (p === mockVenvPythonPath) return true;
          if (p === '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv') return true;
          // Explicitly handle requirements paths
          if (p === expectedReqPath) return true;
          if (p === expectedDevReqPath) return true; // Also handle dev requirements
          return false;
        });
        const mockFsReadFileSync = jest.fn((p, encoding) => {
          if (p === '/tmp/jest-zlibrary-mcp-cache/.venv_config' && encoding === 'utf8') {
            return mockVenvPythonPath;
          }
          if (p.endsWith('requirements.txt')) {
               try { return jest.requireActual('fs').readFileSync(p, encoding); } catch { return ''; }
          }
          return '';
        });
        const mockFsUnlinkSync = jest.fn();
        const mockFsRmSync = jest.fn();

        const mockDeps = {
          fs: {
            existsSync: mockFsExistsSync,
            readFileSync: mockFsReadFileSync,
            writeFileSync: jest.fn(),
            mkdirSync: jest.fn(),
            unlinkSync: mockFsUnlinkSync, // Use specific mock
            rmSync: mockFsRmSync,       // Use specific mock
          },
          child_process: {
            execSync: mockExecSync, // Still needed if findPythonExecutable is called internally
            spawn: mockSpawn,
          },
        };
        // env-paths is mocked via __mocks__

        // --- Dynamic Import ---
        const VenvManager = await import('../lib/venv-manager.js');

        // --- Act ---
        await VenvManager.ensureVenvReady(mockDeps); // Pass mock deps


      // REMOVED jest.spyOn calls previously here
        // --- Assert ---
        expect(mockDeps.fs.existsSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config');
        expect(mockDeps.fs.readFileSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config', 'utf8');
        expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockVenvPythonPath);
        // Check spawn call for pip show
        expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(mockVenvPythonPath, ['-m', 'pip', 'show', 'zlibrary'], {});
        // Check spawn call for pip install WAS made
        expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(
            mockVenvPythonPath,
            // Correct the expected path for requirements.txt
            ['-m', 'pip', 'install', '--no-cache-dir', '--force-reinstall', '--upgrade', '-r', path.resolve(process.cwd(), 'requirements.txt')],
            expect.anything()
        );
        // Optionally verify cleanup mocks if needed
        // expect(mockDeps.fs.unlinkSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/.venv_config');
        // expect(mockDeps.fs.rmSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv', expect.anything());
        // findPythonExecutable might be called, ensure mock exists
    });
  });

  describe('Configuration Management', () => {
    it.todo('should save the venv Python path to a config file');
    it.todo('should load the venv Python path from the config file');
    it.todo('should return null if the config file does not exist');
    it.todo('should return null if the config file is invalid');
  });

  describe('ensureVenvReady', () => {
    it.todo('should run the full setup flow (detect, create, install, save)');
    it.todo('should be idempotent (detect existing venv and config)');
    it.todo('should handle errors during any step of the setup flow');
  });

  // Removed placeholder test
});