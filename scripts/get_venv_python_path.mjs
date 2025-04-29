// get_venv_python_path.mjs
// Purpose: Get the path to the Python executable in the managed venv

// Use dynamic import for ESM compatibility if needed, but assuming direct import works post-build
import { getManagedPythonPath } from './dist/lib/venv-manager.js'; // Use compiled JS path

async function main() {
  try {
    // We assume ensureVenvReady() has run previously and the config exists.
    // If this script fails, it might indicate the venv setup needs to be triggered.
    const pythonPath = await getManagedPythonPath();
    console.log(pythonPath); // Print *only* the path for easy capture
  } catch (error) {
    console.error('Error getting Python path:', error);
    process.exit(1); // Exit with error code if path retrieval fails
  }
}

main();