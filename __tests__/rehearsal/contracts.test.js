import { expect, test } from '@jest/globals';
import { classifySentinels } from './sentinels.js';
import { snapshotSource } from './source-identity.js';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import { waitForFakeReady } from './fake-startup.js';

const caKey = 'synthetic-private-key-material-not-a-real-key';
const log = 'client-0/logs/zlibrary_debug.log';
const knownLine = 'INFO - EAPI client authenticated (userid=rehearsal-cookie-id)';
test('C8 fake binds and loads TLS without hostname resolution', () => {
  const root = process.env.REHEARSAL_SERVER_ROOT || process.cwd();
  expect(
    execFileSync(path.join(root, '.venv/bin/python'), ['__tests__/rehearsal/startup_contract.py'], {
      encoding: 'utf8',
      env: { PATH: process.env.PATH, PYTHONDONTWRITEBYTECODE: '1' },
      timeout: 5000,
    }),
  ).toContain('succeeded without hostname resolution');
});
test('C9 startup deadline reports captured stderr and live process status', async () => {
  const child = spawn(
    process.execPath,
    ['-e', "process.stderr.write('startup-control marker\\n'); process.stdin.resume()"],
    { stdio: ['pipe', 'pipe', 'pipe'] },
  );
  let stderr = '';
  child.stderr.on('data', (data) => {
    stderr += data;
  });
  try {
    await once(child.stderr, 'data');
    await expect(waitForFakeReady(child, { timeoutMs: 25, stderr: () => stderr })).rejects.toThrow(
      /fake startup deadline exceeded.*exitCode=null.*signalCode=null.*startup-control marker/s,
    );
  } finally {
    const exited = once(child, 'exit');
    child.kill();
    await exited;
  }
});
test('C10 startup exit and spawn errors retain stderr and status', async () => {
  const child = spawn(
    process.execPath,
    ['-e', "process.stderr.write('startup-exit marker\\n'); process.exitCode=7"],
    { stdio: ['pipe', 'pipe', 'pipe'] },
  );
  let stderr = '';
  child.stderr.on('data', (data) => {
    stderr += data;
  });
  await expect(waitForFakeReady(child, { stderr: () => stderr })).rejects.toThrow(
    /fake exited before readiness.*exitCode=7.*signalCode=null.*startup-exit marker/s,
  );
  const missing = spawn('/nonexistent-rehearsal-python', [], { stdio: ['pipe', 'pipe', 'pipe'] });
  await expect(waitForFakeReady(missing)).rejects.toThrow(
    /fake spawn failed.*ENOENT.*exitCode=.*stderr=/s,
  );
});
test('C1 known cookie-ID log cannot hide password key or CA leaks', () => {
  for (const source of [log, 'stderr']) {
    const found = classifySentinels(
      `${knownLine}\nrehearsal-password-canary\nrehearsal-cookie-key-epoch-1\n${caKey}`,
      source,
      caKey,
    );
    expect(found.expected.map((f) => f.kind)).toEqual(['cookie-id']);
    expect(found.unexpected.map((f) => f.kind).sort()).toEqual([
      'ca-key',
      'cookie-key',
      'password',
    ]);
  }
});
test('C2 only known authentication output may contain the cookie ID', () => {
  for (const source of ['reply', 'client-0/logs/other.log']) {
    expect(classifySentinels(knownLine, source, caKey).unexpected).toHaveLength(1);
  }
  for (const source of [log, 'stderr']) {
    expect(
      classifySentinels('arbitrary rehearsal-cookie-id', source, caKey).unexpected,
    ).toHaveLength(1);
    const found = classifySentinels(JSON.stringify({ error: knownLine }), source, caKey);
    expect(found.unexpected).toHaveLength(0);
    expect(found.expected).toHaveLength(1);
    expect(found.knownLogCount).toBe(1);
    expect(
      classifySentinels(`${knownLine} extra=rehearsal-cookie-id`, source, caKey).unexpected,
    ).toHaveLength(1);
  }
});
test('C3 redaction expectation forbids even the known cookie-ID log', () => {
  for (const source of [log, 'stderr']) {
    const found = classifySentinels(knownLine, source, caKey, { redaction: true });
    expect(found.unexpected).toHaveLength(1);
    expect(found.expected).toHaveLength(0);
    expect(found.knownLogCount).toBe(1);
  }
});
test('C4 source snapshot detects dist lib and porcelain changes', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'rehearsal-identity-contract-'));
  try {
    await mkdir(path.join(dir, 'dist'));
    await mkdir(path.join(dir, 'lib'));
    await writeFile(path.join(dir, 'dist/index.js'), 'built-one');
    await writeFile(path.join(dir, 'lib/bridge.py'), 'bridge-one');
    const git = () => 'fixed-sha\n';
    const before = await snapshotSource(dir, git);
    await writeFile(path.join(dir, 'dist/index.js'), 'built-two');
    expect((await snapshotSource(dir, git)).trees.dist).not.toEqual(before.trees.dist);
    await writeFile(path.join(dir, 'lib/bridge.py'), 'bridge-two');
    expect((await snapshotSource(dir, git)).trees.lib).not.toEqual(before.trees.lib);
    expect(
      (
        await snapshotSource(dir, (args) =>
          args.includes('status') ? ' M example\n' : 'fixed-sha\n',
        )
      ).porcelain,
    ).not.toEqual(before.porcelain);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('C6 fake exits when its owner closes stdin', async () => {
  const { Rehearsal } = await import('./harness.js');
  const h = await Rehearsal.start('eof-contract');
  let timer;
  try {
    const exited = new Promise((resolve) => h.fake.once('exit', resolve));
    h.fake.stdin.end();
    await Promise.race([
      exited,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('fake survived EOF')), 2000);
      }),
    ]);
    expect(h.fake.exitCode).toBe(0);
  } finally {
    clearTimeout(timer);
    await h.close();
  }
});

test('C7 PID mismatch still closes every client', async () => {
  const { Rehearsal } = await import('./harness.js');
  const h = await Rehearsal.start('cleanup-contract');
  try {
    await expect(
      h.scenario('cleanup', async (connect) => {
        await Promise.all([connect(), connect()]);
        h.sessions[0].pid = -1;
      }),
    ).rejects.toThrow('Node child PID changed');
    expect(h.sessions.map((s) => s.transport.pid)).toEqual([null, null]);
  } finally {
    await h.close();
  }
});
