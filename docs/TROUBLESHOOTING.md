# Troubleshooting Guide

Common issues and solutions for Z-Library MCP server.

---

## ImportError: cannot import name from 'zlibrary'

### Symptom

MCP tools fail with:
```
ImportError: cannot import name 'Extension' from 'zlibrary' (unknown location)
```

### Causes

#### Cause 1: Stale Cache Venv After Project Move

**Description**: The venv-manager uses a shared cache venv at `~/.cache/zlibrary-mcp/` instead of the project-local `venv/`. If you move the project directory, the editable zlibrary install in the cache venv points to the old location.

**How to Diagnose**:
```bash
# Check cache venv zlibrary location
~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/pip show zlibrary

# Look for:
# Location: /old/path/to/project/zlibrary  ← WRONG
# Should be: /current/path/to/project/zlibrary
```

**Solution**: Reinstall zlibrary in cache venv

**Quick Fix** (Run from project root):
```bash
bash scripts/fix-cache-venv.sh
```

**Manual Fix**:
```bash
# Get current project location
PROJECT_ROOT=$(pwd)

# Reinstall zlibrary in cache venv
~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/pip install -e "$PROJECT_ROOT/zlibrary" --force-reinstall --no-deps

# Verify
~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/python -c "from zlibrary import Extension; print('✅ Fixed')"
```

**Then**: Restart Claude Code in your workspace

---

#### Cause 2: Cache Venv Not Initialized

**Description**: The cache venv doesn't exist or wasn't properly initialized.

**How to Diagnose**:
```bash
ls ~/.cache/zlibrary-mcp/zlibrary-mcp-venv/
# If doesn't exist or empty → not initialized
```

**Solution**: Run initial setup
```bash
cd /path/to/zlibrary-mcp
npm run build  # Creates and initializes cache venv
```

---

#### Cause 3: Python Version Mismatch

**Description**: Cache venv created with different Python version than current system.

**How to Diagnose**:
```bash
~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/python --version
python3 --version

# If versions don't match or cache Python doesn't work → version issue
```

**Solution**: Recreate cache venv
```bash
rm -rf ~/.cache/zlibrary-mcp/
npm run build  # Recreates with current Python
```

---

## Python bridge script not found at: .../lib/python_bridge.py

### Symptom

Error message shows:
```
Python bridge script not found at: /path/to/dist/lib/python_bridge.py
This usually indicates a build or installation issue.
```

### Cause

Build didn't complete successfully or Python scripts are missing.

### Solution

**Verify files exist**:
```bash
npm run validate

# Should show:
# ✅ lib/python_bridge.py
# ✅ lib/rag_processing.py
# etc.
```

**Rebuild if needed**:
```bash
npm run build
```

**Check source files**:
```bash
ls -la lib/*.py
# All Python files should be present
```

---

## Virtual environment configuration is missing or invalid

### Symptom

```
Error: Virtual environment configuration is missing or invalid.
Please run the setup process again.
```

### Cause

Config file at `~/.cache/zlibrary-mcp/.venv_config` is missing or points to non-existent Python.

### Solution

**Check config**:
```bash
cat ~/.cache/zlibrary-mcp/.venv_config
# Should show path to cache venv Python

ls -la "$(cat ~/.cache/zlibrary-mcp/.venv_config)"
# Python should exist at that path
```

**Fix by rebuilding**:
```bash
rm ~/.cache/zlibrary-mcp/.venv_config
npm run build  # Recreates config
```

---

## MCP Tools Work Locally But Fail in Claude Code

### Symptom

Direct execution works:
```bash
node dist/index.js
# Works ✅
```

But MCP calls from Claude Code fail.

### Causes

1. **Different working directory**: Claude Code may run from different directory
2. **Environment variables**: ZLIBRARY_EMAIL/PASSWORD not set in .mcp.json
3. **Permission issues**: Cache venv not readable

### Solution

**Check .mcp.json configuration**:
```json
{
  "mcpServers": {
    "zlibrary": {
      "command": "node",
      "args": ["/absolute/path/to/zlibrary-mcp/dist/index.js"],
      "env": {
        "ZLIBRARY_EMAIL": "your-email@example.com",
        "ZLIBRARY_PASSWORD": "your-password"
      }
    }
  }
}
```

**Important**:
- Use ABSOLUTE path to `dist/index.js`
- Include credentials in env block
- Restart Claude Code after changes

---

## After Moving Project Directory

If you've moved the project from one location to another:

### Steps to Fix

1. **Update cache venv** (run from new location):
   ```bash
   bash scripts/fix-cache-venv.sh
   ```

2. **Verify build**:
   ```bash
   npm run validate
   ```

3. **Update .mcp.json** in your workspaces:
   ```json
   "args": ["/new/absolute/path/to/zlibrary-mcp/dist/index.js"]
   ```

4. **Restart Claude Code**

---

## Testing the MCP Server

### Test 1: Direct Execution

```bash
cd /path/to/zlibrary-mcp
export ZLIBRARY_EMAIL="your-email"
export ZLIBRARY_PASSWORD="your-password"
node dist/index.js
```

Should show:
```
Z-Library MCP server (ESM/TS) is running via Stdio...
```

---

### Test 2: Python Bridge Direct Call

```bash
~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/python \
  /path/to/zlibrary-mcp/lib/python_bridge.py \
  get_download_limits \
  '{}'
```

Should return JSON with download limits (not ImportError).

---

### Test 3: Via MCP (from another workspace)

1. Create test `.mcp.json` (or use existing)
2. Start Claude Code
3. Try: "Search Z-Library for test query"
4. Should work without ImportError

---

## Quick Diagnostic Commands

```bash
# Check which Python venv-manager is using
cat ~/.cache/zlibrary-mcp/.venv_config

# Check if that Python works
$(cat ~/.cache/zlibrary-mcp/.venv_config) -c "from zlibrary import Extension; print('OK')"

# Check zlibrary installation location
~/.cache/zlibrary-mcp/zlibrary-mcp-venv/bin/pip show zlibrary | grep Location

# Run build validation
npm run validate

# Run integration tests
npm test __tests__/integration/
```

---

## Getting Help

If issues persist:

1. Run diagnostics:
   ```bash
   bash scripts/fix-cache-venv.sh  # Attempts automatic fix
   npm run validate                 # Checks files
   npm test                        # Runs tests
   ```

2. Check logs (if enabled):
   ```bash
   tail -f logs/nodejs_debug.log
   ```

3. Report issue with diagnostics:
   - https://github.com/loganrooks/zlibrary-mcp/issues

---

**Last Updated**: 2025-10-12
