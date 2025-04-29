import { getManagedPythonPath } from './dist/lib/venv-manager.js'; // Assuming compiled JS is in dist
import * as path from 'path';

async function main() {
  try {
    const pythonPath = await getManagedPythonPath();
    // Construct path to pytest within the venv's bin directory
    const venvDir = path.dirname(path.dirname(pythonPath)); // Go up two levels (from /bin/python)
    const pytestPath = path.join(venvDir, 'bin', 'pytest'); // Assuming Linux/macOS 'bin' dir
    console.log(pytestPath); // Output just the path
  } catch (error) {
    console.error("Error getting pytest path:", error);
    process.exit(1);
  }
}

main();