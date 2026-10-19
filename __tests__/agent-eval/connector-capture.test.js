import { jest, test, expect, beforeEach, afterEach, afterAll } from '@jest/globals';
import * as actualChildProcess from 'node:child_process';
import { cp, mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { performance } from 'node:perf_hooks';

let fixture, directory;
const spawned = [];
const retained = await mkdtemp(path.join(os.tmpdir(), 'evalfx-connector-r1-capture-evidence-'));
afterAll(() => {
  process.stdout.write(`Synthetic capture attempts retained: ${retained}\n`);
});
// Only the forbidden external CLI boundary is substituted. The OS process,
// inherited pipes, capture, persistence and driver parser are the real path.
jest.unstable_mockModule('node:child_process', () => ({
  ...actualChildProcess,
  execFileSync: (binary, args, options) =>
    binary === 'codex'
      ? 'codex-cli 0.162.1\n'
      : actualChildProcess.execFileSync(binary, args, options),
  spawn: (binary, args, options) => {
    const child =
      binary === 'codex'
        ? actualChildProcess.spawn(
            fixture === null ? '/nonexistent/eval-child' : process.execPath,
            fixture === null ? [] : ['-e', fixture],
            options,
          )
        : actualChildProcess.spawn(binary, args, options);
    spawned.push(child);
    return child;
  },
}));
const { runDriver } = await import('./drivers.js');
const command = { binary: 'codex', args: [], env: {}, unsetEnv: [] };
const head = JSON.stringify({ type: 'thread.started', thread_id: 'synthetic-session' }) + '\n';
const tail =
  [
    { type: 'item.completed', item: { type: 'agent_message', text: 'complete tail' } },
    {
      type: 'turn.completed',
      usage: { input_tokens: 11, cached_input_tokens: 2, output_tokens: 3 },
    },
  ]
    .map((e) => JSON.stringify(e))
    .join('\n') + '\n';
beforeEach(async () => {
  directory = await mkdtemp(path.join(os.tmpdir(), 'eval-capture-'));
});
afterEach(async () => {
  const captures = await Promise.all(
    (await readdir(directory))
      .filter((n) => n.endsWith('.capture.json'))
      .map(async (n) => JSON.parse(await readFile(path.join(directory, n), 'utf8'))),
  );
  for (const child of spawned.splice(0)) {
    if (
      captures.some(
        (c) => c.cleanup?.pgid === child.pid && c.cleanup.success && c.cleanup.state === 'gone',
      )
    )
      continue;
    if (!child.pid) continue;
    try {
      process.kill(-child.pid, 'SIGKILL');
    } catch (error) {
      if (error.code !== 'ESRCH') throw error;
    }
  }
  await cp(directory, path.join(retained, path.basename(directory)), { recursive: true });
  await rm(directory, { recursive: true, force: true });
});
const inherited = (code) =>
  `const {spawn}=require('node:child_process');const c=spawn(process.execPath,['-e',${JSON.stringify(code)}],{stdio:['ignore',process.stdout,process.stderr]});process.stderr.write('OWNED_DESCENDANT='+c.pid+'\\n');c.unref();process.stdout.write(${JSON.stringify(head)});`;
// IPC readiness is test-only: the parent exits only after the child's TERM
// handler is installed. No signal target is learned from IPC/output.
const resistant = (redirected = false) =>
  `const {spawn}=require('node:child_process');const c=spawn(process.execPath,['-e',"process.on('SIGTERM',()=>{});setInterval(()=>{},1000);process.send('ready');process.disconnect();"],{stdio:${redirected ? "['ignore','ignore','ignore','ipc']" : "['ignore',process.stdout,process.stderr,'ipc']"}});c.once('message',()=>{c.unref();process.stdout.write(${JSON.stringify(head)}${redirected ? '+' + JSON.stringify(tail) : ''});});`;
const assertKilledOrConservativelyUnknown = (cleanup) => {
  expect(cleanup).toMatchObject({
    scope: 'owned-posix-process-group',
    termSent: true,
    killSent: true,
  });
  expect(['gone', 'unknown', 'alive-after-deadline']).toContain(cleanup.state);
  expect(cleanup.success).toBe(cleanup.state === 'gone');
  if (cleanup.state === 'unknown') expect(typeof cleanup.error).toBe('string');
};
const limits = { timeoutMs: 2000, killGraceMs: 100, drainTimeoutMs: 400 };
const expectedUsage = {
  inputTotal: 11,
  inputCacheRead: 2,
  inputUncached: 9,
  inputCacheWrite: null,
  output: 3,
  outputUncached: 3,
  outputCached: null,
  scope: 'session-cumulative',
  rawCounters: { input_tokens: 11, cached_input_tokens: 2, output_tokens: 3 },
  rawSnapshots: [{ input_tokens: 11, cached_input_tokens: 2, output_tokens: 3 }],
  cacheFirstRequest: null,
  source: 'turn.completed.usage',
};
async function failure(options = limits) {
  let error;
  try {
    await runDriver(command, 'synthetic only', directory, options);
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.driverResult).toBeDefined();
  const raw = await readFile(path.join(directory, error.driverResult.rawFiles.stdout), 'utf8');
  const telemetry = JSON.parse(
    await readFile(path.join(directory, error.driverResult.rawFiles.capture), 'utf8'),
  );
  expect(error.driverResult.usage).toBeUndefined();
  return { error, raw, telemetry };
}
test('natural quiescence admits alive then alive then ESRCH after clean drained exit without signals', async () => {
  fixture = `process.stdout.write(${JSON.stringify(head + tail)});process.stderr.write('NATURAL_STDERR\\n');`;
  const calls = [];
  let probes = 0;
  const result = await runDriver(command, 'synthetic only', directory, {
    ...limits,
    signalGroup: (pgid, signal) => {
      calls.push([pgid, signal]);
      if (signal === 0 && ++probes >= 3)
        throw Object.assign(new Error('naturally absent'), { code: 'ESRCH' });
    },
  });
  expect(result.capture).toMatchObject({
    complete: true,
    closed: true,
    code: 0,
    signal: null,
    residualGroup: false,
    cleanup: {
      state: 'gone',
      success: true,
      termSent: false,
      killSent: false,
      observations: ['alive', 'alive', 'gone'],
    },
  });
  expect(calls).toEqual(Array.from({ length: 3 }, () => [spawned.at(-1).pid, 0]));
  expect(result.usage).toEqual(expectedUsage);
  expect(await readFile(path.join(directory, result.rawFiles.stdout), 'utf8')).toBe(head + tail);
  expect(await readFile(path.join(directory, result.rawFiles.stderr), 'utf8')).toBe(
    'NATURAL_STDERR\n',
  );
  await new Promise((resolve) => setTimeout(resolve, 125));
  expect(calls).toEqual(Array.from({ length: 3 }, () => [spawned.at(-1).pid, 0]));
});
test('natural quiescence immediately absent group succeeds with exactly one owned probe', async () => {
  fixture = `process.stdout.write(${JSON.stringify(head + tail)});`;
  const calls = [];
  const result = await runDriver(command, 'synthetic only', directory, {
    ...limits,
    signalGroup: (pgid, signal) => {
      calls.push([pgid, signal]);
      throw Object.assign(new Error('absent'), { code: 'ESRCH' });
    },
  });
  expect(result.capture).toMatchObject({
    complete: true,
    residualGroup: false,
    cleanup: {
      state: 'gone',
      success: true,
      termSent: false,
      killSent: false,
      observations: ['gone'],
    },
  });
  expect(result.usage).toEqual(expectedUsage);
  await new Promise((resolve) => setTimeout(resolve, 125));
  expect(calls).toEqual([[spawned.at(-1).pid, 0]]);
});
test('natural quiescence ESRCH completing after the monotonic bound remains incomplete and stops probes', async () => {
  fixture = `process.stdout.write(${JSON.stringify(head + tail)});`;
  const calls = [];
  const { raw, telemetry } = await failure({
    ...limits,
    signalGroup: (pgid, signal) => {
      calls.push([pgid, signal]);
      if (calls.length === 1) return;
      // Deliberately delay the existing IO seam, not the child or exit premise.
      // An absence observed only after the bound must not extend admission.
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 110);
      throw Object.assign(new Error('absence observed too late'), { code: 'ESRCH' });
    },
  });
  expect(raw).toBe(head + tail);
  expect(telemetry).toMatchObject({
    complete: false,
    closed: true,
    code: 0,
    residualGroup: true,
    cleanup: {
      state: 'gone',
      success: true,
      termSent: false,
      killSent: false,
      observations: ['alive', 'gone'],
    },
  });
  await new Promise((resolve) => setTimeout(resolve, 125));
  expect(calls).toEqual([
    [spawned.at(-1).pid, 0],
    [spawned.at(-1).pid, 0],
  ]);
});
test('natural quiescence deadline alive then TERM-only gone stays residual, incomplete and usage-unadmitted', async () => {
  fixture = `process.stdout.write(${JSON.stringify(head + tail)});process.stderr.write('BOUNDED_STDERR\\n');`;
  const calls = [];
  let terminated = false;
  // Wall-clock movement must not extend the monotonic observation/cleanup bound.
  const wallClock = jest.spyOn(Date, 'now').mockReturnValue(0);
  try {
    const started = performance.now();
    const { error, raw, telemetry } = await failure({
      ...limits,
      killGraceMs: 20,
      drainTimeoutMs: 40,
      signalGroup: (pgid, signal) => {
        calls.push({ pgid, signal, at: performance.now() });
        if (signal === 'SIGTERM') terminated = true;
        else if (terminated)
          throw Object.assign(new Error('gone only after TERM'), { code: 'ESRCH' });
      },
    });
    expect(performance.now() - started).toBeLessThan(1000);
    const term = calls.find((call) => call.signal === 'SIGTERM');
    expect(term.at - calls[0].at).toBeGreaterThanOrEqual(100);
    expect(calls.every((call) => call.pgid === spawned.at(-1).pid)).toBe(true);
    expect(calls.filter((call) => call.signal).map((call) => call.signal)).toEqual(['SIGTERM']);
    expect(telemetry).toMatchObject({
      complete: false,
      closed: true,
      code: 0,
      timedOut: false,
      drainTimedOut: false,
      residualGroup: true,
      cleanup: { state: 'gone', success: true, termSent: true, killSent: false },
    });
    expect(raw).toBe(head + tail);
    expect(await readFile(path.join(directory, error.driverResult.rawFiles.stderr), 'utf8')).toBe(
      'BOUNDED_STDERR\n',
    );
    const settledCalls = [...calls];
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(calls).toEqual(settledCalls);
  } finally {
    wallClock.mockRestore();
  }
});
for (const phase of ['immediate', 'after-alive'])
  test(`natural quiescence ${phase} EPERM is unknown without any signals or usage`, async () => {
    fixture = `process.stdout.write(${JSON.stringify(head + tail)});`;
    const calls = [];
    const { telemetry } = await failure({
      ...limits,
      signalGroup: (pgid, signal) => {
        calls.push([pgid, signal]);
        if (phase === 'after-alive' && calls.length === 1) return;
        throw Object.assign(new Error('permission unknown'), { code: 'EPERM' });
      },
    });
    expect(telemetry).toMatchObject({
      complete: false,
      closed: true,
      code: 0,
      cleanup: {
        success: false,
        state: 'unknown',
        error: 'EPERM',
        termSent: false,
        killSent: false,
        observations: phase === 'immediate' ? ['unknown'] : ['alive', 'unknown'],
      },
    });
    await new Promise((resolve) => setTimeout(resolve, 125));
    expect(calls).toEqual(
      Array.from({ length: phase === 'immediate' ? 1 : 2 }, () => [spawned.at(-1).pid, 0]),
    );
  });
for (const kind of ['nonzero', 'signal', 'runtime-error'])
  test(`natural quiescence never delays strict cleanup after ${kind}`, async () => {
    fixture =
      `process.stdout.write(${JSON.stringify(head + tail)});` +
      (kind === 'nonzero'
        ? 'process.exitCode=27;'
        : kind === 'signal'
          ? "process.kill(process.pid,'SIGTERM');"
          : "throw new Error('synthetic runtime failure');");
    const calls = [];
    let terminated = false;
    const { raw, telemetry } = await failure({
      ...limits,
      killGraceMs: 20,
      drainTimeoutMs: 40,
      signalGroup: (pgid, signal) => {
        calls.push([pgid, signal]);
        if (signal === 'SIGTERM') terminated = true;
        else if (terminated) throw Object.assign(new Error('gone'), { code: 'ESRCH' });
      },
    });
    // Exactly the initial and re-signal ownership probes precede strict TERM:
    // no natural observation phase for unsuccessful direct leaders.
    expect(calls.slice(0, 3)).toEqual(
      [0, 0, 'SIGTERM'].map((signal) => [spawned.at(-1).pid, signal]),
    );
    expect(telemetry).toMatchObject({
      complete: false,
      closed: true,
      residualGroup: true,
      code: kind === 'signal' ? null : kind === 'nonzero' ? 27 : 1,
      signal: kind === 'signal' ? 'SIGTERM' : null,
      cleanup: { state: 'gone', termSent: true, killSent: false },
    });
    expect(raw).toBe(head + tail);
  });
test('EVAL-C1-04 real descendant final usage/stdout/stderr drains after parent exit', async () => {
  fixture = inherited(
    `setTimeout(()=>{process.stdout.write(${JSON.stringify(tail)});process.stderr.write('DELAYED_STDERR\\n');},120);`,
  );
  const result = await runDriver(command, 'synthetic only', directory, limits);
  expect(result).toMatchObject({
    final: 'complete tail',
    session: 'synthetic-session',
    usage: { inputTotal: 11, output: 3 },
    capture: {
      complete: true,
      closed: true,
      code: 0,
      residualGroup: false,
      cleanup: { state: 'gone', success: true, termSent: false, killSent: false },
    },
  });
  expect(result.usage).toEqual(expectedUsage);
  expect(await readFile(path.join(directory, result.rawFiles.stdout), 'utf8')).toBe(head + tail);
  expect(await readFile(path.join(directory, result.rawFiles.stderr), 'utf8')).toMatch(
    /^OWNED_DESCENDANT=\d+\nDELAYED_STDERR\n$/,
  );
});
test('EVAL-C1-04 never-closing inherited pipes fail bounded with partial raw output', async () => {
  fixture = inherited('setInterval(()=>{},1000);');
  const started = Date.now();
  const { raw, telemetry } = await failure({ ...limits, drainTimeoutMs: 100 });
  expect(Date.now() - started).toBeLessThan(1800);
  expect(raw).toBe(head);
  expect(telemetry).toMatchObject({ complete: false, drainTimedOut: true, code: 0 });
});
test('EVAL-C1-04 timeout escalates a TERM-ignoring child and retains output', async () => {
  fixture = `process.on('SIGTERM',()=>{});process.stdout.write(${JSON.stringify(head)});setInterval(()=>{},1000);`;
  const { raw, telemetry } = await failure({ ...limits, timeoutMs: 150 });
  expect(raw).toBe(head);
  expect(telemetry).toMatchObject({ complete: false, timedOut: true, signal: 'SIGKILL' });
});
test('EVAL-C1-04 signal termination cannot be promoted to successful telemetry', async () => {
  fixture = `process.stdout.write(${JSON.stringify(head + tail)});process.kill(process.pid,'SIGTERM');`;
  const { raw, telemetry } = await failure();
  expect(raw).toBe(head + tail);
  expect(telemetry).toMatchObject({ signal: 'SIGTERM', code: null, closed: true });
});
test('EVAL-C1-04 spawn errors retain failed capture and raw files', async () => {
  fixture = null;
  const { raw, telemetry } = await failure();
  expect(raw).toBe('');
  expect(telemetry.complete).toBe(false);
  expect(telemetry.spawnError).toContain('ENOENT');
});
test('EVAL-C1-04 malformed completed telemetry retains unique raw files and fails parsing', async () => {
  fixture = `process.stdout.write('malformed-final-json\\n');`;
  const { raw, telemetry } = await failure();
  expect(raw).toBe('malformed-final-json\n');
  expect(telemetry).toMatchObject({ complete: true, closed: true, code: 0 });
});

test('4318353637 TERM-resistant inherited-pipe child after leader exit is group-killed and recorded', async () => {
  fixture = resistant();
  const { telemetry } = await failure({ ...limits, drainTimeoutMs: 100 });
  assertKilledOrConservativelyUnknown(telemetry.cleanup);
  expect(telemetry.closed).toBe(true);
  expect(telemetry.complete).toBe(false);
});
test('4318353637 drained zero-exit leader cannot hide redirected-stdio residual child', async () => {
  fixture = resistant(true);
  const { telemetry } = await failure({ ...limits, drainTimeoutMs: 300 });
  expect(telemetry).toMatchObject({
    closed: true,
    code: 0,
    complete: false,
    residualGroup: true,
    cleanup: { scope: 'owned-posix-process-group' },
  });
  assertKilledOrConservativelyUnknown(telemetry.cleanup);
});
test('4318878598 immediate pre-child identity rejection prevents the model-boundary spawn', async () => {
  const before = spawned.length;
  await expect(
    runDriver(command, 'synthetic prompt', directory, {
      beforeSpawn: () => {
        throw new Error('Node selected runtime identity drift');
      },
    }),
  ).rejects.toThrow(/Node selected runtime identity drift/);
  expect(spawned).toHaveLength(before);
  expect(await readdir(directory)).toEqual([]);
});
