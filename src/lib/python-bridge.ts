import { spawn } from 'child_process';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { getManagedPythonPath } from './venv-manager.js'; // Import from the TS file

// Recreate __dirname for ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Execute a Python function from the python_bridge.py script.
 * @param functionName - Name of the Python function to call.
 * @param args - Arguments to pass to the function.
 * @returns Promise resolving with the result from the Python function.
 * @throws {Error} If the Python process fails or returns an error.
 */
export async function callPythonFunction(functionName: string, args: Record<string, any> = {}): Promise<any> {
  return new Promise(async (resolve, reject) => { // Make the promise executor async
    try {
      // Get the path to the managed Python executable
      const pythonExecutable = await getManagedPythonPath();

      // Path to the Python bridge script
      // Navigate from dist/lib/ up to project root, then into source lib/ directory
      // This keeps Python scripts in a single source of truth location (lib/)
      const scriptPath = path.resolve(__dirname, '..', '..', 'lib', 'python_bridge.py');

      // Serialize arguments as JSON
      const serializedArgs = JSON.stringify(args);

      // Spawn Python process using the venv Python
      const pythonProcess = spawn(pythonExecutable, [
        scriptPath,
        functionName,
        serializedArgs
      ]);

      let result = '';
      let errorOutput = '';

      // Collect output
      if (pythonProcess.stdout) {
        pythonProcess.stdout.on('data', (data) => {
          result += data.toString();
        });
      }

      if (pythonProcess.stderr) {
        pythonProcess.stderr.on('data', (data) => {
          errorOutput += data.toString();
        });
      }

      // Handle process completion
      pythonProcess.on('close', (code) => {
        if (code === 0) {
          try {
            // Parse the JSON result
            const parsedResult = JSON.parse(result);
            resolve(parsedResult);
          } catch (e: any) {
            // If parsing fails, reject with potentially useful raw output
            reject(new Error(`Failed to parse Python result JSON: ${e.message}. Raw output: ${result}. Stderr: ${errorOutput}`));
          }
        } else {
          reject(new Error(`Python process exited with code ${code}: ${errorOutput}. Raw stdout: ${result}`));
        }
      });

      pythonProcess.on('error', (err) => {
        reject(new Error(`Failed to start Python process: ${err.message}`));
      });

    } catch (error: any) {
      // Catch errors from getManagedPythonPath or spawn
      reject(new Error(`Error setting up or running Python process: ${error.message}`));
    }
  });
}