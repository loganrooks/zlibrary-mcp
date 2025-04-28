// get_venv_path.mjs
import { ensureVenvReady, getManagedPythonPath } from './dist/lib/venv-manager.js';

try {
  await ensureVenvReady(); // Make sure venv is set up
  const pythonPath = await getManagedPythonPath();
  console.log(pythonPath); // Print the path to stdout
} catch (error) {
  console.error('Failed to get venv path:', error);
  process.exit(1);
}