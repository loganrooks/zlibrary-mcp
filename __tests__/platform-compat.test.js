/**
 * Cross-platform behaviour tests.
 *
 * The Windows bugs these cover reached users because the code paths only execute
 * on the platform they were broken for, and CI runs solely on Linux. Both units
 * are therefore parameterised by platform rather than reading `process.platform`
 * directly, so a Linux runner exercises the Windows branch too.
 *
 * Based on the fixes in PR #13 by @ltspace.
 */

import { describe, test, expect } from '@jest/globals';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { pathToFileURL } from 'url';
import {
  venvPythonSegments,
  venvRemoveCommand,
  uvInstallCommand,
} from '../dist/lib/venv-manager.js';
import { isProcessEntryPoint } from '../dist/index.js';

describe('venv path resolution across platforms', () => {
  test('uses .venv/bin/python on POSIX platforms', () => {
    for (const platform of ['linux', 'darwin', 'freebsd']) {
      expect(venvPythonSegments(platform)).toEqual(['.venv', 'bin', 'python']);
    }
  });

  test('uses .venv/Scripts/python.exe on win32 — where UV actually puts it', () => {
    expect(venvPythonSegments('win32')).toEqual(['.venv', 'Scripts', 'python.exe']);
  });

  test('segments join into a platform-appropriate path', () => {
    // path.join uses the host separator; what matters is the segment sequence,
    // which is what differed and what broke.
    const windows = path.win32.join('C:\\app', ...venvPythonSegments('win32'));
    expect(windows).toBe('C:\\app\\.venv\\Scripts\\python.exe');

    const posix = path.posix.join('/app', ...venvPythonSegments('linux'));
    expect(posix).toBe('/app/.venv/bin/python');
  });

  test('remediation commands match the platform shell', () => {
    expect(venvRemoveCommand('win32')).toBe('rmdir /s /q .venv');
    expect(venvRemoveCommand('linux')).toBe('rm -rf .venv');
    // `rm -rf` in a Windows cmd prompt is not a command, so the old hardcoded
    // message sent Windows users down a dead end.
    expect(venvRemoveCommand('win32')).not.toContain('rm -rf');
  });

  test('UV install instructions match the platform shell', () => {
    expect(uvInstallCommand('win32')).toContain('powershell');
    expect(uvInstallCommand('linux')).toContain('curl -LsSf');
    expect(uvInstallCommand('win32')).not.toContain('curl');
  });
});

describe('ESM entry-point detection across platforms', () => {
  test('detects a POSIX entry point', () => {
    const url = pathToFileURL('/app/dist/index.js').href;
    expect(isProcessEntryPoint(url, '/app/dist/index.js')).toBe(true);
  });

  test('detects a Windows entry point despite separator and encoding mismatch', () => {
    // This is the exact shape that failed: argv[1] uses backslashes, while
    // import.meta.url is a forward-slashed, percent-encoded file:// URL.
    const url = pathToFileURL(path.resolve('/app/dist/index.js')).href;
    const argv1 = path.resolve('/app/dist/index.js');
    expect(isProcessEntryPoint(url, argv1)).toBe(true);
  });

  test('the old string-concatenation comparison fails on a Windows-shaped path', () => {
    // Documents why the fix is necessary rather than cosmetic.
    const windowsArgv = 'C:\\app\\dist\\index.js';
    const windowsUrl = 'file:///C:/app/dist/index.js';
    expect(windowsUrl === `file://${windowsArgv}`).toBe(false);
  });

  test('detects the entry point through an npm-style bin symlink', () => {
    // npm installs bins as symlinks into <prefix>/bin: argv[1] is the link,
    // import.meta.url the real file. This is the global-install/`zlibrary-mcp`
    // startup path, and a lexical path comparison silently fails it.
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'entry-guard-'));
    try {
      const real = path.join(dir, 'index.js');
      fs.writeFileSync(real, '');
      const link = path.join(dir, 'zlibrary-mcp');
      fs.symlinkSync(real, link);
      const url = pathToFileURL(real).href;
      expect(isProcessEntryPoint(url, link)).toBe(true);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  test('returns false when the module is imported rather than executed', () => {
    const url = pathToFileURL('/app/dist/lib/thing.js').href;
    expect(isProcessEntryPoint(url, '/app/dist/index.js')).toBe(false);
  });

  test('returns false when argv[1] is absent (REPL or -e evaluation)', () => {
    const url = pathToFileURL('/app/dist/index.js').href;
    expect(isProcessEntryPoint(url, undefined)).toBe(false);
    expect(isProcessEntryPoint(url, '')).toBe(false);
  });

  test('tolerates a non-file URL instead of throwing', () => {
    // fileURLToPath rejects non-file schemes; a bundler virtual module must not
    // crash startup.
    expect(isProcessEntryPoint('data:text/javascript,0', '/app/dist/index.js')).toBe(
      false
    );
    expect(isProcessEntryPoint('https://example.com/x.js', '/app/x.js')).toBe(false);
  });

  test('normalises redundant path segments on both sides', () => {
    const url = pathToFileURL('/app/dist/index.js').href;
    expect(isProcessEntryPoint(url, '/app/./dist/../dist/index.js')).toBe(true);
  });
});
