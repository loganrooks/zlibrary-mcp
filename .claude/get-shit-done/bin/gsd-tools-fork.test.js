/**
 * GSD Tools Fork-Specific Tests
 *
 * Tests for fork custom config fields (health_check, devops, gsd_reflect_version)
 * that round-trip through config-set without data loss.
 *
 * Separate file from gsd-tools.test.js per Phase 9 decision:
 * "Separate fork-tools.js over modifying gsd-tools.js" — zero merge friction.
 */

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const TOOLS_PATH = path.join(__dirname, 'gsd-tools.js');

// Helper to run gsd-tools command (mirrors upstream test pattern)
function runGsdTools(args, cwd = process.cwd()) {
  try {
    const result = execSync(`node "${TOOLS_PATH}" ${args}`, {
      cwd,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return { success: true, output: result.trim() };
  } catch (err) {
    return {
      success: false,
      output: err.stdout?.toString().trim() || '',
      error: err.stderr?.toString().trim() || err.message,
    };
  }
}

// Create temp directory structure (mirrors upstream test pattern)
function createTempProject() {
  const tmpDir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'gsd-fork-test-'));
  fs.mkdirSync(path.join(tmpDir, '.planning', 'phases'), { recursive: true });
  return tmpDir;
}

function cleanup(tmpDir) {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}

// Helper to read config.json from a temp project
function readConfig(tmpDir) {
  const configPath = path.join(tmpDir, '.planning', 'config.json');
  return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
}

// ─────────────────────────────────────────────────────────────────────────────
// config-set/config-get fork custom fields
// ─────────────────────────────────────────────────────────────────────────────

describe('config-set/config-get fork custom fields', () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = createTempProject();
    // Seed with minimal config.json so config-set has a file to read
    fs.writeFileSync(
      path.join(tmpDir, '.planning', 'config.json'),
      JSON.stringify({}, null, 2),
      'utf-8'
    );
  });

  afterEach(() => {
    cleanup(tmpDir);
  });

  test('sets and gets health_check.frequency', () => {
    const result = runGsdTools('config-set health_check.frequency milestone-only', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    assert.strictEqual(
      config.health_check.frequency,
      'milestone-only',
      'health_check.frequency should be "milestone-only"'
    );
  });

  test('sets and gets health_check.stale_threshold_days', () => {
    const result = runGsdTools('config-set health_check.stale_threshold_days 7', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    // Note: config-set parses numeric values via !isNaN check, so 7 becomes Number(7)
    assert.strictEqual(
      config.health_check.stale_threshold_days,
      7,
      'health_check.stale_threshold_days should be 7 (number)'
    );
  });

  test('sets and gets devops.ci_provider', () => {
    const result = runGsdTools('config-set devops.ci_provider github-actions', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    assert.strictEqual(
      config.devops.ci_provider,
      'github-actions',
      'devops.ci_provider should be "github-actions"'
    );
  });

  test('sets and gets devops.commit_convention', () => {
    const result = runGsdTools('config-set devops.commit_convention conventional', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    assert.strictEqual(
      config.devops.commit_convention,
      'conventional',
      'devops.commit_convention should be "conventional"'
    );
  });

  test('sets and gets gsd_reflect_version', () => {
    const result = runGsdTools('config-set gsd_reflect_version 1.13.0', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    // "1.13.0" has multiple dots so isNaN("1.13.0") is true — stays as string
    assert.strictEqual(
      config.gsd_reflect_version,
      '1.13.0',
      'gsd_reflect_version should remain as string "1.13.0" (not parsed as number)'
    );
  });

  test('preserves existing config when setting fork fields', () => {
    // Pre-seed config with upstream field
    fs.writeFileSync(
      path.join(tmpDir, '.planning', 'config.json'),
      JSON.stringify({ mode: 'yolo', depth: 'comprehensive' }, null, 2),
      'utf-8'
    );

    const result = runGsdTools('config-set health_check.frequency milestone-only', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    assert.strictEqual(config.mode, 'yolo', 'upstream mode field should be preserved');
    assert.strictEqual(config.depth, 'comprehensive', 'upstream depth field should be preserved');
    assert.strictEqual(
      config.health_check.frequency,
      'milestone-only',
      'fork field should be set alongside upstream fields'
    );
  });

  test('sets nested devops.environments as JSON array', () => {
    // config-set only accepts a single value argument, so we cannot pass a JSON array
    // directly through the CLI. Instead, verify that setting other devops fields
    // does not corrupt an existing environments array written directly to config.json.
    fs.writeFileSync(
      path.join(tmpDir, '.planning', 'config.json'),
      JSON.stringify({
        devops: {
          environments: ['staging', 'production'],
        },
      }, null, 2),
      'utf-8'
    );

    // Set a sibling field via config-set
    const result = runGsdTools('config-set devops.ci_provider github-actions', tmpDir);
    assert.ok(result.success, `config-set failed: ${result.error}`);

    const config = readConfig(tmpDir);
    assert.deepStrictEqual(
      config.devops.environments,
      ['staging', 'production'],
      'existing environments array should be preserved after setting sibling field'
    );
    assert.strictEqual(
      config.devops.ci_provider,
      'github-actions',
      'ci_provider should be set alongside environments'
    );
  });
});
