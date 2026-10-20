import { jest, test, expect } from '@jest/globals';
import * as childProcess from 'node:child_process';
import { EventEmitter } from 'node:events';
import { PassThrough } from 'node:stream';
import { arms } from './tasks.js';
let spawned = 0,
  versionCalls = 0,
  mode = 'normal';
jest.unstable_mockModule('node:child_process', () => ({
  ...childProcess,
  execFileSync: () => {
    versionCalls++;
    throw new Error('no actual driver permitted');
  },
  spawn: () => {
    spawned++;
    if (mode === 'throw') throw new Error('synthetic spawn throw');
    const child = new EventEmitter();
    child.pid = mode === 'no-pid' ? undefined : 76543;
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    setImmediate(() => {
      child.stdout.end();
      child.stderr.end();
      child.emit('exit', 0, null);
      child.emit('close', 0, null);
    });
    return child;
  },
}));
const { captureChild, runDriver } = await import('./drivers.js');
const { measured } = await import('./receipt-controls.js');
const { admitReceipt } = await import('./admission.js');
const options = { stdio: ['ignore', 'pipe', 'pipe'] };
test('4318353637 unsupported platform refuses before CLI version or model invocation', async () => {
  await expect(runDriver({ binary: 'codex' }, '', '.', { platform: 'win32' })).rejects.toThrow(
    /POSIX/,
  );
  expect(versionCalls).toBe(0);
  expect(spawned).toBe(0);
});
test('4318353637 EPERM probe is unknown/fail closed with no dangerous follow-on signals', async () => {
  const signals = [];
  const result = await captureChild('synthetic', [], options, {
    timeoutMs: 100,
    killGraceMs: 20,
    drainTimeoutMs: 30,
    signalGroup: (pgid, signal) => {
      signals.push([pgid, signal]);
      throw Object.assign(new Error('denied'), { code: 'EPERM' });
    },
  });
  expect(result.capture).toMatchObject({
    complete: false,
    cleanup: { success: false, state: 'unknown', error: 'EPERM' },
  });
  expect(signals).toEqual([[76543, 0]]);
});
test('4318353637 signal error fails closed and never signals any stdout-selected PID', async () => {
  const signals = [];
  const result = await captureChild('synthetic', [], options, {
    timeoutMs: 100,
    killGraceMs: 20,
    drainTimeoutMs: 30,
    signalGroup: (pgid, signal) => {
      signals.push([pgid, signal]);
      if (signal) throw Object.assign(new Error('denied'), { code: 'EPERM' });
    },
  });
  expect(result.capture.cleanup).toMatchObject({
    success: false,
    state: 'unknown',
    error: 'EPERM',
  });
  expect(signals.every(([pgid]) => pgid === 76543)).toBe(true);
  expect(signals.filter(([, s]) => s)).toEqual([[76543, 'SIGTERM']]);
});
test('4318353637 zombie/alive-after-KILL observation has bounded conservative failure', async () => {
  const signals = [],
    start = Date.now();
  const result = await captureChild('synthetic', [], options, {
    timeoutMs: 100,
    killGraceMs: 20,
    drainTimeoutMs: 40,
    signalGroup: (pgid, signal) => signals.push([pgid, signal]),
  });
  expect(Date.now() - start).toBeLessThan(500);
  expect(result.capture.cleanup).toMatchObject({
    success: false,
    state: 'alive-after-deadline',
    termSent: true,
    killSent: true,
  });
  expect(signals.filter(([, s]) => s).map(([, s]) => s)).toEqual(['SIGTERM', 'SIGKILL']);
});
test('4318353637 ESRCH stops all future signals immediately', async () => {
  const signals = [];
  const result = await captureChild('synthetic', [], options, {
    timeoutMs: 100,
    killGraceMs: 20,
    drainTimeoutMs: 30,
    signalGroup: (pgid, signal) => {
      signals.push([pgid, signal]);
      throw Object.assign(new Error('gone'), { code: 'ESRCH' });
    },
  });
  expect(result.capture).toMatchObject({
    complete: true,
    cleanup: { success: true, state: 'gone', termSent: false, killSent: false },
  });
  expect(signals).toEqual([[76543, 0]]);
});
test('4318353637 missing/unknown cleanup and residual group cannot be admitted', () => {
  for (const mutate of [
    (c) => delete c.cleanup,
    (c) => (c.cleanup.success = false),
    (c) => (c.cleanup.state = 'unknown'),
    (c) => (c.cleanup.pgid = null),
    (c) => (c.residualGroup = true),
  ]) {
    const r = measured(arms[0]);
    expect(admitReceipt(r).eligible).toBe(true);
    mutate(r.results[0].capture);
    expect(admitReceipt(r).eligible).toBe(false);
  }
});

for (const failure of ['throw', 'no-pid'])
  test(`4318353637 ${failure} never signals an unowned/missing PGID`, async () => {
    mode = failure;
    const signals = [];
    try {
      const r = await captureChild('synthetic', [], options, {
        timeoutMs: 100,
        killGraceMs: 20,
        drainTimeoutMs: 30,
        signalGroup: (...args) => signals.push(args),
      });
      expect(r.capture.complete).toBe(false);
      expect(r.capture.cleanup).toMatchObject({
        success: false,
        state: 'no-owned-pgid',
        pgid: null,
      });
      expect(signals).toEqual([]);
    } finally {
      mode = 'normal';
    }
  });
