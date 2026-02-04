"use strict";
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
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getManagedPythonPath = getManagedPythonPath;
var path = require("path");
var fs_1 = require("fs");
var child_process_1 = require("child_process");
var url_1 = require("url");
// Recreate __dirname for ESM
var __filename = (0, url_1.fileURLToPath)(import.meta.url);
var __dirname = path.dirname(__filename);
/**
 * Get path to UV-managed Python executable
 *
 * UV creates .venv/ in project root when you run: uv sync
 * This function returns the path to Python in that venv.
 *
 * @returns {Promise<string>} Path to Python executable in .venv
 * @throws {Error} If .venv not found (user needs to run: uv sync)
 */
function getManagedPythonPath() {
    return __awaiter(this, void 0, void 0, function () {
        var projectRoot, uvVenvPython, version;
        return __generator(this, function (_a) {
            projectRoot = path.resolve(__dirname, '..', '..');
            uvVenvPython = path.join(projectRoot, '.venv', 'bin', 'python');
            // Check if UV venv exists
            if (!(0, fs_1.existsSync)(uvVenvPython)) {
                throw new Error('Python virtual environment not found.\n\n' +
                    'UV has not initialized the environment. Please run:\n' +
                    '  uv sync\n\n' +
                    'This will:\n' +
                    '  1. Create .venv/ directory\n' +
                    '  2. Install all dependencies from pyproject.toml\n' +
                    '  3. Generate uv.lock for reproducibility\n\n' +
                    'First time setup? Install UV:\n' +
                    '  curl -LsSf https://astral.sh/uv/install.sh | sh\n' +
                    '  # Or: pip install uv\n\n' +
                    'See: https://docs.astral.sh/uv/getting-started/installation/');
            }
            // Verify Python is executable and working
            try {
                version = (0, child_process_1.execSync)("\"".concat(uvVenvPython, "\" --version"), {
                    stdio: 'pipe',
                    encoding: 'utf8'
                }).trim();
                // Log Python version for debugging (optional, can be removed)
                console.log("[venv-manager] Using Python: ".concat(version, " from .venv"));
            }
            catch (error) {
                throw new Error("Python at ".concat(uvVenvPython, " is not executable.\n") +
                    "This usually means .venv is corrupted. Try:\n" +
                    "  rm -rf .venv\n" +
                    "  uv sync");
            }
            return [2 /*return*/, uvVenvPython];
        });
    });
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
