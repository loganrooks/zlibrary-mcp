/**
 * Path Resolution Helpers
 *
 * Centralized path resolution logic for the Z-Library MCP server.
 * Handles paths between compiled TypeScript (dist/) and source files (lib/, etc.)
 *
 * Path Strategy:
 * - TypeScript compiles to dist/
 * - Python scripts remain in source lib/
 * - Resolution: dist/lib/ → ../../ → project root → lib/
 *
 * See: docs/adr/ADR-004-Python-Bridge-Path-Resolution.md
 */

import * as path from 'path';
import { fileURLToPath } from 'url';

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Get the project root directory (parent of dist/)
 *
 * At runtime:
 * - This module is at: dist/lib/paths.js
 * - Go up: dist/lib/ → dist/ → project root
 *
 * @returns {string} Absolute path to project root
 *
 * @example
 * const root = getProjectRoot();
 * // /home/user/zlibrary-mcp
 */
export function getProjectRoot(): string {
  // From dist/lib/paths.js: ../ = dist/, ../ = project root
  return path.resolve(__dirname, '..', '..');
}

/**
 * Get path to a Python script in the lib/ directory
 *
 * Python scripts are kept in source lib/ directory (single source of truth).
 * This function resolves from compiled dist/lib/ to source lib/.
 *
 * @param {string} scriptName - Name of the Python script (e.g., 'python_bridge.py')
 * @returns {string} Absolute path to the Python script
 *
 * @example
 * const bridgePath = getPythonScriptPath('python_bridge.py');
 * // /home/user/zlibrary-mcp/lib/python_bridge.py
 *
 * @example
 * const ragPath = getPythonScriptPath('rag_processing.py');
 * // /home/user/zlibrary-mcp/lib/rag_processing.py
 */
export function getPythonScriptPath(scriptName: string): string {
  return path.join(getProjectRoot(), 'lib', scriptName);
}

/**
 * Get the lib/ directory path (for PythonShell scriptPath)
 *
 * @returns {string} Absolute path to lib/ directory
 *
 * @example
 * const libDir = getPythonLibDirectory();
 * // /home/user/zlibrary-mcp/lib
 */
export function getPythonLibDirectory(): string {
  return path.join(getProjectRoot(), 'lib');
}

/**
 * Get path to package.json
 *
 * @returns {string} Absolute path to package.json
 *
 * @example
 * const pkgPath = getPackageJsonPath();
 * // /home/user/zlibrary-mcp/package.json
 */
export function getPackageJsonPath(): string {
  return path.join(getProjectRoot(), 'package.json');
}

/**
 * Get path to pyproject.toml
 *
 * @returns {string} Absolute path to pyproject.toml
 *
 * @example
 * const tomlPath = getPyprojectTomlPath();
 * // /home/user/zlibrary-mcp/pyproject.toml
 */
export function getPyprojectTomlPath(): string {
  return path.join(getProjectRoot(), 'pyproject.toml');
}

/**
 * Get path to venv directory
 *
 * @returns {string} Absolute path to .venv directory
 *
 * @example
 * const venvPath = getVenvPath();
 * // /home/user/zlibrary-mcp/.venv
 */
export function getVenvPath(): string {
  return path.join(getProjectRoot(), '.venv');
}

// Re-export path for convenience
export { path };
