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
    it('should find a compatible python3 executable on PATH', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();
      const mockExecSync = jest.fn()
        .mockImplementationOnce(() => 'Python 3.9.1'); // Simulate finding python3

      const mockDeps = {
        fs: { /* Mock fs methods if needed by findPythonExecutable */ },
        child_process: {
          execSync: mockExecSync,
          spawn: jest.fn(), // Add spawn mock if needed
        },
      };

      // --- Dynamic Import ---
      // Mock env-paths before import
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Act ---
      const pythonPath = VenvManager.findPythonExecutable(mockDeps); // Pass mock deps

      // --- Assert ---
      expect(mockDeps.child_process.execSync).toHaveBeenCalledWith('python3 --version', expect.anything());
      expect(pythonPath).toBe('python3');
    });
    it('should throw an error if no compatible python3 is found', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();
      const mockExecSync = jest.fn()
        .mockImplementation((command) => {
          if (command.startsWith('python3 --version') || command.startsWith('python --version')) {
            throw new Error('Command failed'); // Simulate command not found or error
          }
          return ''; // Default return for other potential calls
        });

      const mockDeps = {
        fs: { /* Mock fs methods if needed */ },
        child_process: {
          execSync: mockExecSync,
          spawn: jest.fn(),
        },
      };

      // --- Dynamic Import ---
      // Mock env-paths before import
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Act & Assert ---
      expect(() => VenvManager.findPythonExecutable(mockDeps)).toThrow(
        'Could not find a valid Python 3 installation. Please ensure Python 3 is installed and accessible in your PATH.'
      );
      expect(mockDeps.child_process.execSync).toHaveBeenCalledWith('python3 --version', expect.anything());
      expect(mockDeps.child_process.execSync).toHaveBeenCalledWith('python --version', expect.anything());
    });
  });

  describe('createVenv', () => {
    it('should create the virtual environment in the correct cache directory', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockMkdirSync = jest.fn();
      const mockSpawn = jest.fn().mockImplementation((command, args) => {
        // Simulate venv creation success
        const mockProcess = {
          stdout: { on: jest.fn(), setEncoding: jest.fn() },
          stderr: { on: jest.fn(), setEncoding: jest.fn() },
          on: jest.fn((event, listener) => {
            if (event === 'close') {
              process.nextTick(() => listener(0)); // Success
            }
            return mockProcess;
          }),
        };
        return mockProcess;
      });

      const mockDeps = {
        fs: {
          existsSync: jest.fn(),
          readFileSync: jest.fn(),
          writeFileSync: jest.fn(),
          mkdirSync: mockMkdirSync,
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: jest.fn(), // Not directly used by createVenv, but might be needed by other imports
          spawn: mockSpawn,
        },
      };

      // --- Dynamic Import ---
      // Mock env-paths before import
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');
      // Need to import the *internal* createVenv for direct testing
      // This requires exporting it from the source file first.

      // --- Act ---
      const pythonExecutable = 'python3'; // Assume found by findPythonExecutable
      const venvDir = '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv'; // Expected path
      // Directly test the internal function (assuming it's exported)
      // NOTE: This will fail until createVenv is exported
      const resultPath = await VenvManager.createVenv(mockDeps, pythonExecutable, venvDir);

      // --- Assert ---
      expect(mockDeps.fs.mkdirSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache', { recursive: true });
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(
        pythonExecutable,
        ['-m', 'venv', venvDir],
        expect.anything()
      );
      const expectedVenvPythonPath = path.join(venvDir, process.platform === 'win32' ? 'Scripts' : 'bin', 'python');
      expect(resultPath).toBe(expectedVenvPythonPath);
    });
    it('should handle venv creation failures', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockMkdirSync = jest.fn();
      const mockSpawn = jest.fn().mockImplementation((command, args) => {
        // Simulate venv creation failure
        const mockProcess = {
          stdout: { on: jest.fn(), setEncoding: jest.fn() },
          stderr: { on: jest.fn((event, cb) => {
              if (event === 'data') process.nextTick(() => cb('venv creation failed'));
              return mockProcess;
          }), setEncoding: jest.fn() },
          on: jest.fn((event, listener) => {
            if (event === 'close') {
              process.nextTick(() => listener(1)); // Failure exit code
            }
            return mockProcess;
          }),
        };
        return mockProcess;
      });

      const mockDeps = {
        fs: {
          existsSync: jest.fn(),
          readFileSync: jest.fn(),
          writeFileSync: jest.fn(),
          mkdirSync: mockMkdirSync,
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: jest.fn(),
          spawn: mockSpawn,
        },
      };

      // --- Dynamic Import ---
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Act & Assert ---
      const pythonExecutable = 'python3';
      const venvDir = '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv';

      await expect(
        VenvManager.createVenv(mockDeps, pythonExecutable, venvDir)
      ).rejects.toThrow(
        'Failed during venv creation: Failed to create virtual environment (exit code 1). Stderr: venv creation failed'
      );

      // Verify mocks
      expect(mockDeps.fs.mkdirSync).toHaveBeenCalledWith('/tmp/jest-zlibrary-mcp-cache', { recursive: true });
      expect(mockDeps.child_process.spawn).toHaveBeenCalledWith(
        pythonExecutable,
        ['-m', 'venv', venvDir],
        expect.anything()
      );
    });
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
    it('should save the venv Python path to a config file', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockWriteFileSync = jest.fn();
      const mockDeps = {
        fs: {
          existsSync: jest.fn(),
          readFileSync: jest.fn(),
          writeFileSync: mockWriteFileSync, // Mock writeFileSync
          mkdirSync: jest.fn(),
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: jest.fn(),
          spawn: jest.fn(),
        },
      };

      // --- Dynamic Import ---
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');
      // NOTE: This will fail until saveVenvConfig is exported

      // --- Act ---
      const pythonPath = '/path/to/venv/bin/python';
      const configPath = '/tmp/jest-zlibrary-mcp-cache/.venv_config';
      await VenvManager.saveVenvPathConfig(mockDeps, pythonPath, configPath); // Assuming export

      // --- Assert ---
      expect(mockDeps.fs.writeFileSync).toHaveBeenCalledWith(configPath, pythonPath, 'utf8');
    });
    it('should load the venv Python path from the config file', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockPythonPath = '/path/to/valid/venv/bin/python';
      const mockConfigPath = '/tmp/jest-zlibrary-mcp-cache/.venv_config';
      const mockExistsSync = jest.fn((p) => {
        return p === mockConfigPath || p === mockPythonPath; // Config and python path exist
      });
      const mockReadFileSync = jest.fn((p, encoding) => {
        if (p === mockConfigPath && encoding === 'utf8') {
          return mockPythonPath + '\n'; // Simulate reading path with newline
        }
        return '';
      });

      const mockDeps = {
        fs: {
          existsSync: mockExistsSync,
          readFileSync: mockReadFileSync,
          writeFileSync: jest.fn(),
          mkdirSync: jest.fn(),
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: jest.fn(),
          spawn: jest.fn(),
        },
      };

      // --- Dynamic Import ---
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');
      // NOTE: This will fail until readVenvPathConfig is exported

      // --- Act ---
      const resultPath = await VenvManager.readVenvPathConfig(mockDeps); // Assuming export

      // --- Assert ---
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockConfigPath);
      expect(mockDeps.fs.readFileSync).toHaveBeenCalledWith(mockConfigPath, 'utf8');
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockPythonPath);
      expect(resultPath).toBe(mockPythonPath);
    });
    it('should return null if the config file does not exist', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockConfigPath = '/tmp/jest-zlibrary-mcp-cache/.venv_config';
      const mockExistsSync = jest.fn((p) => p !== mockConfigPath); // Config file does NOT exist
      const mockReadFileSync = jest.fn(); // Should not be called

      const mockDeps = {
        fs: {
          existsSync: mockExistsSync,
          readFileSync: mockReadFileSync,
          writeFileSync: jest.fn(),
          mkdirSync: jest.fn(),
          unlinkSync: jest.fn(),
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: jest.fn(),
          spawn: jest.fn(),
        },
      };

      // --- Dynamic Import ---
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Act ---
      const resultPath = await VenvManager.readVenvPathConfig(mockDeps);

      // --- Assert ---
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockConfigPath);
      expect(mockDeps.fs.readFileSync).not.toHaveBeenCalled();
      expect(resultPath).toBeNull();
    });
    it('should return null if the config file is invalid', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockInvalidPythonPath = '/path/to/invalid/venv/bin/python';
      const mockConfigPath = '/tmp/jest-zlibrary-mcp-cache/.venv_config';
      const mockExistsSync = jest.fn((p) => {
        if (p === mockConfigPath) return true; // Config file exists
        if (p === mockInvalidPythonPath) return false; // Python path inside is invalid
        return false;
      });
      const mockReadFileSync = jest.fn((p, encoding) => {
        if (p === mockConfigPath && encoding === 'utf8') {
          return mockInvalidPythonPath; // Return invalid path
        }
        return '';
      });
      const mockUnlinkSync = jest.fn(); // Mock unlinkSync

      const mockDeps = {
        fs: {
          existsSync: mockExistsSync,
          readFileSync: mockReadFileSync,
          writeFileSync: jest.fn(),
          mkdirSync: jest.fn(),
          unlinkSync: mockUnlinkSync, // Use the mock
          rmSync: jest.fn(),
        },
        child_process: {
          execSync: jest.fn(),
          spawn: jest.fn(),
        },
      };

      // --- Dynamic Import ---
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Act ---
      const resultPath = await VenvManager.readVenvPathConfig(mockDeps);

      // --- Assert ---
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockConfigPath);
      expect(mockDeps.fs.readFileSync).toHaveBeenCalledWith(mockConfigPath, 'utf8');
      expect(mockDeps.fs.existsSync).toHaveBeenCalledWith(mockInvalidPythonPath);
      expect(mockDeps.fs.unlinkSync).toHaveBeenCalledWith(mockConfigPath); // Verify unlink was called
      expect(resultPath).toBeNull();
    });
  });

  describe('ensureVenvReady', () => {
    it('should log warning but not throw if saving config fails', async () => {
      // --- Setup Mocks ---
      jest.resetModules();
      jest.clearAllMocks();

      const mockConfigPath = '/tmp/jest-zlibrary-mcp-cache/.venv_config';
      const mockVenvDir = '/tmp/jest-zlibrary-mcp-cache/zlibrary-mcp-venv';
      const mockVenvPythonPath = path.join(mockVenvDir, process.platform === 'win32' ? 'Scripts' : 'bin', 'python');

      const mockFsExistsSync = jest.fn().mockImplementation((p) => p !== mockConfigPath); // No config initially
      const mockFsWriteFileSync = jest.fn(() => { throw new Error('Disk full'); }); // Simulate save failure
      const mockFsMkdirSync = jest.fn();
      const mockFsReadFileSync = jest.fn();
      const mockFsUnlinkSync = jest.fn();
      const mockFsRmSync = jest.fn();
      const mockExecSync = jest.fn().mockReturnValue('Python 3.9.1'); // Found python3

      // Mock spawn: Simulate venv success (0), then pip install success (0)
      const mockSpawn = jest.fn().mockImplementation(() => {
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
      });

      const mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {}); // Spy on console.error

      const mockDeps = {
        fs: {
          existsSync: mockFsExistsSync,
          writeFileSync: mockFsWriteFileSync,
          mkdirSync: mockFsMkdirSync,
          readFileSync: mockFsReadFileSync,
          unlinkSync: mockFsUnlinkSync,
          rmSync: mockFsRmSync,
        },
        child_process: {
          execSync: mockExecSync,
          spawn: mockSpawn,
        },
      };

      // --- Dynamic Import ---
      jest.unstable_mockModule('env-paths', () => ({
        default: jest.fn(() => ({ cache: '/tmp/jest-zlibrary-mcp-cache' }))
      }));
      const VenvManager = await import('../lib/venv-manager.js');

      // --- Act & Assert ---
      // Expect it NOT to throw, as save failure is non-critical
      await expect(VenvManager.ensureVenvReady(mockDeps)).resolves.toBeUndefined();

      // Verify mocks
      expect(mockFsExistsSync).toHaveBeenCalledWith(mockConfigPath); // Checked config
      expect(mockExecSync).toHaveBeenCalled(); // Found python
      expect(mockSpawn).toHaveBeenCalledWith('python3', ['-m', 'venv', mockVenvDir], expect.anything()); // Created venv
      expect(mockSpawn).toHaveBeenCalledWith(mockVenvPythonPath, expect.arrayContaining(['install']), expect.anything()); // Installed deps
      expect(mockFsWriteFileSync).toHaveBeenCalledWith(mockConfigPath, mockVenvPythonPath, 'utf8'); // Attempted write

      // Verify console warning
      expect(mockConsoleError).toHaveBeenCalledWith(expect.stringContaining(`Warning: Failed to save venv config to ${mockConfigPath}: Disk full`));

      mockConsoleError.mockRestore(); // Restore console.error
    });
  });

  // Removed placeholder test
});