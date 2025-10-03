import * as fsDefault from 'fs'; // Rename default import
import * as path from 'path';
import * as childProcessDefault from 'child_process'; // Rename default import
import type { SpawnOptionsWithoutStdio, ChildProcessWithoutNullStreams } from 'child_process'; // Keep type import separate
import { fileURLToPath } from 'url';

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Dynamic import for env-paths (ESM module)
// We'll import it when needed inside getCacheDir
let envPaths: ((name: string, opts?: { suffix?: string }) => { cache: string }) | null = null;

const VENV_DIR_NAME = 'zlibrary-mcp-venv';
const CONFIG_FILE_NAME = '.venv_config';
const VENV_BIN_DIR = process.platform === 'win32' ? 'Scripts' : 'bin';

interface CommandResult {
    stdout: string;
    stderr: string;
    code: number | null; // Exit code can be null
}

// Define Dependency Interface
export interface VenvManagerDependencies {
    fs: {
        existsSync: typeof fsDefault.existsSync;
        readFileSync: typeof fsDefault.readFileSync;
        writeFileSync: typeof fsDefault.writeFileSync;
        mkdirSync: typeof fsDefault.mkdirSync;
        unlinkSync: typeof fsDefault.unlinkSync;
        rmSync: typeof fsDefault.rmSync;
    };
    child_process: {
        spawn: (command: string, args?: ReadonlyArray<string>, options?: SpawnOptionsWithoutStdio) => ChildProcessWithoutNullStreams;
        execSync: typeof childProcessDefault.execSync;
    };
}

/**
 * Runs a command asynchronously using spawn, returning a promise.
 * @param deps Injected dependencies (fs, child_process).
 * @param command The command to run.
 * @param args Array of string arguments.
 * @param options Options for spawn.
 * @param logOutput Whether to log stdout/stderr. Defaults to true.
 * @returns Promise resolving with command result.
 */
function runCommand(
    deps: VenvManagerDependencies,
    command: string,
    args: string[],
    options: SpawnOptionsWithoutStdio = {},
    logOutput: boolean = true
): Promise<CommandResult> {
    return new Promise((resolve, reject) => {
        const proc = deps.child_process.spawn(command, args, options);
        let stdout = '';
        let stderr = '';

        if (proc.stdout) {
            proc.stdout.on('data', (data) => {
                const output = data.toString();
                stdout += output;
                if (logOutput) console.log(`[${command} ${args.join(' ')}] stdout: ${output.trim()}`);
            });
        }

        if (proc.stderr) {
            proc.stderr.on('data', (data) => {
                const output = data.toString();
                stderr += output;
                if (logOutput) console.error(`[${command} ${args.join(' ')}] stderr: ${output.trim()}`);
            });
        }

        proc.on('close', (code) => {
            resolve({ stdout, stderr, code });
        });

        proc.on('error', (err) => {
            reject(new Error(`Failed to spawn command "${command}": ${err.message}`));
        });
    });
}


/**
 * Gets the application-specific cache directory.
 * @returns The path to the cache directory.
 */
// Add _testPath parameter for explicit control during testing
async function getCacheDir(): Promise<string> {
    // Always use dynamic import; Jest should intercept with the manual mock during tests.
    if (!envPaths) {
        // Use dynamic import() which returns a Promise
        const module = await import('env-paths');
        // Assuming env-paths has a default export which is the function
        envPaths = module.default;
    }
    if (!envPaths) {
        throw new Error("Failed to load env-paths module.");
    }
    // Use 'zlibrary-mcp' as the name for env-paths
    const paths = envPaths('zlibrary-mcp', { suffix: '' });
    return paths.cache;
}

/**
 * Gets the full path to the virtual environment directory.
 * @returns The path to the venv directory.
 */
async function getVenvDir(): Promise<string> {
    // Call getCacheDir without test path for normal operation
    const cacheDir = await getCacheDir();
    return path.join(cacheDir, VENV_DIR_NAME);
}

/**
 * Gets the path to the configuration file storing the venv Python path.
 * @returns The path to the config file.
 */
async function getConfigPath(): Promise<string> {
    // Call getCacheDir without test path for normal operation
    const cacheDir = await getCacheDir();
    return path.join(cacheDir, CONFIG_FILE_NAME);
}

/**
 * Finds a suitable Python 3 executable path.
 * Tries 'python3' first, then 'python'.
 * @param deps Injected dependencies (fs, child_process).
 * @returns The path to the Python 3 executable.
 * @throws {Error} If no suitable Python 3 executable is found or version check fails.
 */
export function findPythonExecutable(deps: VenvManagerDependencies): string { // Removed async and Promise
    const candidates = ['python3', 'python'];
    for (const candidate of candidates) {
        try {
            // Check if command exists and is Python 3
            const versionOutput = deps.child_process.execSync(`${candidate} --version`, { encoding: 'utf8' });
            if (versionOutput.includes('Python 3.')) {
                // Verify it's executable (execSync would throw if not)
                return candidate; // Return the command name, works cross-platform
            }
        } catch (error) {
            // Command not found or failed, try next candidate
        }
    }
    throw new Error('Could not find a valid Python 3 installation. Please ensure Python 3 is installed and accessible in your PATH.');
}

/**
 * Creates the Python virtual environment.
 * @param deps Injected dependencies (fs, child_process).
 * @param pythonExecutable - The command/path of the Python 3 executable to use.
 * @param venvDir - The directory where the venv should be created.
 * @returns The path to the Python executable within the created venv.
 * @throws {Error} If venv creation fails.
 */
export async function createVenv(deps: VenvManagerDependencies, pythonExecutable: string, venvDir: string): Promise<string> {
    // console.log(`Creating Python virtual environment in: ${venvDir}...`); // Removed debug log
    // Ensure parent directory exists
    // Use await for async mkdir if available, otherwise stick to sync for simplicity here
    deps.fs.mkdirSync(path.dirname(venvDir), { recursive: true });

    try {
        const { stderr, code } = await runCommand(deps, pythonExecutable, ['-m', 'venv', venvDir]);
        if (code === 0) {
            const venvPythonPath = path.join(venvDir, VENV_BIN_DIR, 'python');
            // console.log(`Virtual environment created successfully. Python path: ${venvPythonPath}`); // Removed debug log
            return venvPythonPath;
        } else {
            throw new Error(`Failed to create virtual environment (exit code ${code}). Stderr: ${stderr}`);
        }
    } catch (error: any) { // Catch specific error type if known, else any
        // Catch spawn errors or re-throw non-zero exit code errors
        throw new Error(`Failed during venv creation: ${error.message}`);
    }
}

/**
 * Installs the required Python package(s) into the virtual environment.
 * @param deps Injected dependencies (fs, child_process).
 * @param venvPythonPath - Path to the Python executable within the venv.
 * @returns Promise resolving when installation is complete.
 * @throws {Error} If installation fails.
 */
async function installDependencies(deps: VenvManagerDependencies, venvPythonPath: string): Promise<void> {
    const installFromFile = async (filePath: string) => {
        const absolutePath = path.resolve(process.cwd(), filePath);
        if (!deps.fs.existsSync(absolutePath)) {
            console.log(`Requirements file not found at ${absolutePath}, skipping.`);
            return;
        }
        // console.log(`Installing packages from ${absolutePath} using ${venvPythonPath}...`); // Removed debug log
        try {
            // Explicitly set cwd for the pip install command
            const projectRoot = path.resolve(__dirname, '..', '..'); // Assumes src/lib/venv-manager.ts structure
            const options = { cwd: projectRoot };
            const { stderr, code } = await runCommand(deps, venvPythonPath, ['-m', 'pip', 'install', '--no-cache-dir', '--force-reinstall', '--upgrade', '-r', absolutePath], options);
            if (code === 0) {
                // console.log(`Packages from ${filePath} installed successfully.`); // Removed debug log
            } else {
                throw new Error(`Failed to install packages from ${filePath} (exit code ${code}). Stderr: ${stderr}`);
            }
        } catch (error: any) {
            // Catch spawn errors or re-throw non-zero exit code errors
            throw new Error(`Failed during pip installation from ${filePath}: ${error.message}`);
        }
    };

    // Install runtime dependencies
    await installFromFile('requirements.txt');

    // Install development dependencies
    await installFromFile('requirements-dev.txt');
}

/**
 * Saves the path to the venv Python executable to the config file.
 * @param deps Injected dependencies (fs, child_process).
 * @param venvPythonPath - The path to save.
 */
export async function saveVenvPathConfig(deps: VenvManagerDependencies, venvPythonPath: string): Promise<void> {
    const configPath = await getConfigPath();
    try {
        deps.fs.writeFileSync(configPath, venvPythonPath, 'utf8');
        // console.log(`Saved venv Python path to ${configPath}`); // Removed debug log
    } catch (error: any) {
        console.error(`Warning: Failed to save venv config to ${configPath}: ${error.message}`);
        // Non-fatal, but setup will run again next time.
    }
}

/**
 * Reads the saved venv Python executable path from the config file.
 * @param deps Injected dependencies (fs, child_process).
 * @returns The saved path, or null if not found or invalid.
 */
export async function readVenvPathConfig(deps: VenvManagerDependencies): Promise<string | null> {
    const configPath = await getConfigPath();
    try {
        if (deps.fs.existsSync(configPath)) {
            const configContent = deps.fs.readFileSync(configPath, 'utf8');
            // Check if config content is valid before trimming
            if (!configContent || typeof configContent !== 'string') {
                console.warn(`Invalid or empty venv config at ${configPath}`);
                deps.fs.unlinkSync(configPath); // Remove invalid config
                return null;
            }
            const venvPythonPath = configContent.trim();
            // Basic validation: check if the file exists
            if (deps.fs.existsSync(venvPythonPath)) {
                // console.log(`Read venv Python path from config: ${venvPythonPath}`); // Removed debug log
                return venvPythonPath;
            } else {
                // console.warn(`Configured venv Python path not found: ${venvPythonPath}. Re-running setup.`); // Already commented
                deps.fs.unlinkSync(configPath); // Remove invalid config
                return null;
            }
        }
    } catch (error: any) {
        console.error(`Warning: Failed to read or validate venv config from ${configPath}: ${error.message}`);
    }
    return null;
}

/**
 * Checks if the required package is installed in the venv.
 * @param deps Injected dependencies (fs, child_process).
 * @param venvPythonPath - Path to the Python executable within the venv.
 * @returns True if the package is installed, false otherwise.
 */
async function checkPackageInstalled(deps: VenvManagerDependencies, venvPythonPath: string): Promise<boolean> {
    // Check for a key runtime package and a key dev package
    const runtimePackage = 'zlibrary';
    const devPackage = 'pytest';
    // console.log(`Checking if key packages '${runtimePackage}' and '${devPackage}' are installed in ${venvPythonPath}...`); // Removed debug log
    try {
        // Check runtime package
        const { code: runtimeCode } = await runCommand(deps, venvPythonPath, ['-m', 'pip', 'show', runtimePackage], {}, false);
        if (runtimeCode !== 0) {
             // console.log(`Key runtime package '${runtimePackage}' not found (pip show exit code ${runtimeCode}). Assuming requirements need installation.`); // Removed debug log
             return false;
        }
         // console.log(`Key runtime package '${runtimePackage}' is installed.`); // Removed debug log

        // Check dev package
        const { code: devCode } = await runCommand(deps, venvPythonPath, ['-m', 'pip', 'show', devPackage], {}, false);
         if (devCode !== 0) {
             // console.log(`Key dev package '${devPackage}' not found (pip show exit code ${devCode}). Assuming requirements need installation.`); // Removed debug log
             return false;
         }
         // console.log(`Key dev package '${devPackage}' is installed.`); // Removed debug log

        // If both checks pass
        return true;
    } catch (error: any) {
        console.error(`Failed to run pip show check: ${error.message}`);
        return false; // Assume not installed if check fails
    }
}


// Default dependencies using the actual modules
const defaultDeps: VenvManagerDependencies = {
    fs: fsDefault,
    child_process: childProcessDefault,
};

/**
 * Ensures the Python virtual environment is set up and dependencies are installed.
 * Stores the path to the venv's Python executable for later use.
 * Uses default dependencies unless others are provided (for testing).
 * @param deps Optional injected dependencies (fs, child_process). Defaults to real modules.
 * @throws {Error} If setup fails at any critical step.
 */
export async function ensureVenvReady(deps: VenvManagerDependencies = defaultDeps): Promise<void> {
    // console.log('Ensuring Python virtual environment is ready...'); // Removed debug log
    let venvPythonPath = await readVenvPathConfig(deps);

    if (venvPythonPath) {
        // Config exists, verify package installation
        const isInstalled = await checkPackageInstalled(deps, venvPythonPath);
        if (isInstalled) {
            // console.log('Venv and package already configured and valid.'); // Removed debug log
            return; // Already set up
        } else {
            // console.log(`Key package not found in configured venv. Re-installing from requirements.txt...`); // Removed debug log
            try {
                await installDependencies(deps, venvPythonPath);
                // console.log('Venv re-validated successfully.'); // Removed debug log
                return; // Setup complete after re-install
            } catch (installError: any) {
                console.error(`Failed to reinstall packages from requirements.txt: ${installError.message}. Attempting full venv recreation.`);
                // Proceed to delete and recreate venv
                venvPythonPath = null; // Force recreation logic
                venvPythonPath = null; // Force recreation logic
                try {
                    const venvDir = await getVenvDir(); // getVenvDir doesn't need deps
                    if (deps.fs.existsSync(venvDir)) {
                        console.log(`Removing existing invalid venv: ${venvDir}`);
                        deps.fs.rmSync(venvDir, { recursive: true, force: true });
                    }
                    const configPath = await getConfigPath(); // getConfigPath doesn't need deps
                     if (deps.fs.existsSync(configPath)) {
                        deps.fs.unlinkSync(configPath);
                    }
                } catch (cleanupError: any) {
                    throw new Error(`Failed to clean up existing invalid venv before recreation: ${cleanupError.message}`);
                }
            }
        }
    }

    // If we reach here, venvPythonPath is null (no config or config was invalid/package missing and reinstall failed)
    // console.log('Setting up new Python virtual environment...'); // Removed debug log
    try { // Restore outer try block
        const pythonExecutable = await findPythonExecutable(deps);
        const venvDir = await getVenvDir();

        // Clean up potentially incomplete venv dir if it exists
        if (deps.fs.existsSync(venvDir)) {
             // console.log(`Removing potentially incomplete venv directory: ${venvDir}`); // Removed debug log
             deps.fs.rmSync(venvDir, { recursive: true, force: true });
        }

        venvPythonPath = await createVenv(deps, pythonExecutable, venvDir);
        // Add non-null assertion as createVenv guarantees a string on success, and throws on failure
        await installDependencies(deps, venvPythonPath!);
        // Add non-null assertion
        await saveVenvPathConfig(deps, venvPythonPath!);
        // console.log('Python virtual environment setup complete.'); // Removed debug log
    } catch (error: any) { // Restore outer catch block
        console.error(`Critical error during venv setup: ${error.message}`);
        // Use throw (original behavior)
        throw new Error(`Failed to set up Python environment: ${error.message}. Please ensure Python 3 and venv are correctly installed and try again.`);
    }
}

/**
 * Gets the path to the managed Python executable within the venv.
 * Assumes ensureVenvReady() has been called successfully before.
 * Uses default dependencies unless others are provided (for testing).
 * @param deps Optional injected dependencies (fs, child_process). Defaults to real modules.
 * @returns The path to the venv's Python executable.
 * @throws {Error} If the config file is missing or invalid (should not happen if ensureVenvReady succeeded).
 */
export async function getManagedPythonPath(deps: VenvManagerDependencies = defaultDeps): Promise<string> {
    const venvPythonPath = await readVenvPathConfig(deps);
    if (!venvPythonPath) {
        // This should ideally not happen if ensureVenvReady was called and succeeded.
        throw new Error('Virtual environment configuration is missing or invalid. Please run the setup process again.');
    }
    return venvPythonPath;
}

// Export internal functions for potential testing/debugging - these now require deps
// Consider removing this export or adapting tests if they use it
// export const _internalVenvManager = {
//     findPythonExecutable,
//     getVenvDir,
//     getConfigPath,
//     checkPackageInstalled
// };