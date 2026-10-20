import { expect, test } from '@jest/globals';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPythonBridge } from '../lib/python-runner.js';

// Catches line-only tail bounds: one huge line used to bypass the capture limit.
test('retained stderr is bounded by UTF-8 bytes and by lines, including malformed oversized envelopes', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'i251-bounds-'));
  try {
    writeFileSync(
      join(directory, 'failure.py'),
      'import sys\nfor i in range(200): print("界"*1000, file=sys.stderr)\nprint("{\\\"error\\\":\\\""+"x"*40000, file=sys.stderr)\nsys.exit(1)\n',
    );
    const error = await runPythonBridge(
      'failure.py',
      { pythonPath: join(process.cwd(), '.venv/bin/python'), scriptPath: directory, mode: 'text' },
      { timeoutMs: 5000 },
    ).catch((e) => e);
    expect(error).toBeInstanceOf(Error);
    expect(Buffer.byteLength(error.stderr)).toBeLessThanOrEqual(8192);
    expect(error.stderr.split('\n').length).toBeLessThanOrEqual(32);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('signalled EAPI children do not retain raw stderr in the error context', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'i251-signal-'));
  try {
    writeFileSync(
      join(directory, 'killed.py'),
      'import os,signal,sys\nprint("i251-token",file=sys.stderr,flush=True)\nos.kill(os.getpid(),signal.SIGTERM)\n',
    );
    const error = await runPythonBridge(
      'killed.py',
      {
        pythonPath: join(process.cwd(), '.venv/bin/python'),
        scriptPath: directory,
        mode: 'text',
        env: { ...process.env, ZLIBRARY_DIAGNOSTIC_EAPI: '1' },
      },
      { timeoutMs: 5000 },
    ).catch((e) => e);
    expect(error.code).toBe('BRIDGE_KILLED');
    expect(String(error.stack) + JSON.stringify(error)).not.toContain('i251-token');
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
