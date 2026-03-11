#!/usr/bin/env node
// Check project version vs installed version in background, write result to cache
// Called by SessionStart hook - runs once per session
// Does NOT perform migration -- only detects and caches

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

const homeDir = os.homedir();
const cwd = process.cwd();
const cacheDir = path.join(homeDir, '.claude', 'cache');
const cacheFile = path.join(cacheDir, 'gsd-version-check.json');

// VERSION file locations (check project first, then global)
const projectVersionFile = path.join(cwd, '.claude', 'get-shit-done', 'VERSION');
const globalVersionFile = path.join(homeDir, '.claude', 'get-shit-done', 'VERSION');

// Project config location
const projectConfigFile = path.join(cwd, '.planning', 'config.json');

// Ensure cache directory exists
if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}

// Run check in background (spawn background process, windowsHide prevents console flash)
const child = spawn(process.execPath, ['-e', `
  const fs = require('fs');

  const cacheFile = ${JSON.stringify(cacheFile)};
  const projectVersionFile = ${JSON.stringify(projectVersionFile)};
  const globalVersionFile = ${JSON.stringify(globalVersionFile)};
  const projectConfigFile = ${JSON.stringify(projectConfigFile)};

  // Read installed version (project-local first, then global)
  let installed = '0.0.0';
  try {
    if (fs.existsSync(projectVersionFile)) {
      installed = fs.readFileSync(projectVersionFile, 'utf8').trim();
    } else if (fs.existsSync(globalVersionFile)) {
      installed = fs.readFileSync(globalVersionFile, 'utf8').trim();
    }
  } catch (e) {}

  // Read project version from config.json gsd_reflect_version field
  let project = '0.0.0';
  let configExists = false;
  try {
    if (fs.existsSync(projectConfigFile)) {
      configExists = true;
      const config = JSON.parse(fs.readFileSync(projectConfigFile, 'utf8'));
      if (config.gsd_reflect_version) {
        project = config.gsd_reflect_version;
      }
      // If gsd_reflect_version absent, project stays "0.0.0" (pre-tracking)
    }
  } catch (e) {
    // JSON parse failure or read error -- skip migration check
  }

  // Compare versions (simple numeric dot-separated comparison)
  function versionGreaterThan(a, b) {
    const pa = a.split('.').map(Number);
    const pb = b.split('.').map(Number);
    for (let i = 0; i < 3; i++) {
      const va = pa[i] || 0;
      const vb = pb[i] || 0;
      if (va > vb) return true;
      if (va < vb) return false;
    }
    return false;
  }

  // Only flag migration if config.json exists (project is initialized)
  const needsMigration = configExists && versionGreaterThan(installed, project);

  const result = {
    project_needs_migration: needsMigration,
    installed: installed,
    project: project,
    project_config: configExists ? projectConfigFile : null,
    checked: Math.floor(Date.now() / 1000)
  };

  fs.writeFileSync(cacheFile, JSON.stringify(result));
`], {
  stdio: 'ignore',
  windowsHide: true
});

child.unref();
