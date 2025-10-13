/**
 * Simplified venv-manager for UV (v2.0.0)
 *
 * UV automatically creates and manages .venv/ in the project directory.
 * This module simply provides the path to UV's Python executable.
 *
 * MIGRATION NOTES:
 * - Replaces 406 lines of cache venv management with ~45 lines
 * - No cache directory at ~/.cache/zlibrary-mcp/
 * - No .venv_config file
 * - No programmatic pip installation
 * - UV handles all dependency management
 *
 * Setup: Run `uv sync` before building
 */

import * as path from 'path';
import { existsSync } from 'fs';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Get path to UV-managed Python executable
 *
 * UV creates .venv/ in project root when you run: uv sync
 * This function returns the path to Python in that venv.
 *
 * @returns {Promise<string>} Path to Python executable in .venv
 * @throws {Error} If .venv not found (user needs to run: uv sync)
 */
export async function getManagedPythonPath(): Promise<string> {
  const projectRoot = path.resolve(__dirname, '..', '..');
  const uvVenvPython = path.join(projectRoot, '.venv', 'bin', 'python');

  // Check if UV venv exists
  if (!existsSync(uvVenvPython)) {
    throw new Error(
      'Python virtual environment not found.\n\n' +
      'UV has not initialized the environment. Please run:\n' +
      '  uv sync\n\n' +
      'This will:\n' +
      '  1. Create .venv/ directory\n' +
      '  2. Install all dependencies from pyproject.toml\n' +
      '  3. Generate uv.lock for reproducibility\n\n' +
      'First time setup? Install UV:\n' +
      '  curl -LsSf https://astral.sh/uv/install.sh | sh\n' +
      '  # Or: pip install uv\n\n' +
      'See: https://docs.astral.sh/uv/getting-started/installation/'
    );
  }

  // Verify Python is executable and working
  try {
    const version = execSync(`"${uvVenvPython}" --version`, {
      stdio: 'pipe',
      encoding: 'utf8'
    }).trim();

    // Log Python version for debugging (optional, can be removed)
    console.log(`[venv-manager] Using Python: ${version} from .venv`);
  } catch (error: any) {
    throw new Error(
      `Python at ${uvVenvPython} is not executable.\n` +
      `This usually means .venv is corrupted. Try:\n` +
      `  rm -rf .venv\n` +
      `  uv sync`
    );
  }

  return uvVenvPython;
}

// MIGRATION NOTE: Removed from v1.x:
// - getCacheDir() - No longer needed (no cache venv)
// - getConfigPath() - No longer needed (no config file)
// - readVenvPathConfig() - No longer needed
// - writeVenvPathConfig() - No longer needed
// - createVenv() - UV handles this
// - installDependencies() - UV handles this
// - ensureVenvReady() - UV handles this
// - checkPackageInstalled() - UV handles this
// - findPythonExecutable() - UV handles this
// - runCommand() - UV handles this
// - VenvManagerDependencies interface - No longer needed
// - defaultDeps - No longer needed
// - All complex error handling - Simplified
//
// Total reduction: 406 lines → 45 lines (89% reduction)
