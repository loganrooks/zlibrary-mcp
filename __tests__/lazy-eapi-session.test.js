import {
  afterAll,
  beforeAll,
  afterEach,
  beforeEach,
  expect,
  jest,
  test,
  describe,
} from '@jest/globals';
import fs from 'node:fs/promises';
import nativeFs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { EapiSessionOwner, authRejected } from '../dist/lib/eapi-session.js';
import { Rehearsal } from './rehearsal/harness.js';

jest.setTimeout(30000);

test('at-most-once owner operation never refreshes/replays after handoff rejection', async () => {
  const owner = new EapiSessionOwner();
  let logins = 0,
    operations = 0;
  const identity = 'synthetic-owner@example.invalid';
  const invoke = async (input) => {
    if (input.action === 'login') {
      logins++;
      owner.consume(
        {
          ...input,
          domain: 'synthetic.invalid',
          remix_userid: '1',
          remix_userkey: 'private-test-cookie',
        },
        identity,
        input.generation,
      );
      return { authenticated: true };
    }
    if (input.action === 'operation') {
      operations++;
      throw authRejected(input.generation, 'Authentication rejected');
    }
    return { authenticated: true };
  };
  await expect(
    owner.run(identity, invoke, { operationMode: 'at-most-once' }),
  ).rejects.toMatchObject({ context: { reason: 'auth_rejected' } });
  expect(operations).toBe(1);
  expect(logins).toBe(1);
  expect(owner.get(identity)).toBeUndefined();
});

describe('SDK lazy acquisition with real bridge and query-sensitive loopback fake', () => {
  let h, original, home, client, server;
  beforeAll(async () => {
    h = await Rehearsal.start('agent-eval');
  });
  afterAll(async () => {
    await h.close();
  });
  beforeEach(async () => {
    original = { ...process.env };
    home = await fs.mkdtemp(path.join(os.tmpdir(), 'lazy-sdk-'));
    const downloads = path.join(home, 'downloads');
    await fs.mkdir(downloads);
    Object.assign(process.env, {
      PYTHONPATH: path.resolve('__tests__/rehearsal'),
      PYTHONDONTWRITEBYTECODE: '1',
      SSL_CERT_FILE: h.cert,
      REHEARSAL_ALLOWED_PORT: String(new URL(h.origin).port),
      REHEARSAL_EGRESS_TRAP: path.join(home, 'egress-trap.txt'),
      ZLIBRARY_EAPI_DOMAIN: h.domain,
      ZLIBRARY_EMAIL: 'rehearsal-account@example.invalid',
      ZLIBRARY_PASSWORD: 'rehearsal-password-canary',
      ZLIBRARY_OUTPUT_ROOT: downloads,
      MCP_READABLE_ROOTS: downloads,
      ZLIBRARY_SESSION_MODE: 'memory',
      RETRY_MAX_RETRIES: '0',
      PYTHON_BRIDGE_TIMEOUT: '15000',
      LOG_LEVEL: 'error',
    });
    await h.mode({ mode: 'healthy', reset: true, remaining: 8 });
    jest.resetModules();
    const { createServer } = await import('../dist/index.js');
    server = createServer();
    client = new Client({ name: 'lazy-session-real-sdk', version: '1' });
    const [a, b] = InMemoryTransport.createLinkedPair();
    await Promise.all([client.connect(a), server.connect(b)]);
  });
  afterEach(async () => {
    await client?.close();
    await server?.close();
    process.env = original;
    await fs.rm(home, { recursive: true, force: true });
  });
  const call = async (name, args) => {
    const reply = await client.callTool({ name, arguments: args });
    expect(reply.isError).not.toBe(true);
    return reply.structuredContent;
  };
  test('search then two fresh destinations keep one login and spend exactly two synthetic transfers', async () => {
    const rows = (
      await call('search', { query: 'Seneca Letters', sources: ['zlibrary'], limit: 10 })
    ).rows;
    expect(rows).toHaveLength(2);
    expect((await h.stats()).logins).toBe(1);
    for (const row of rows) await call('download', { ref: row.ref });
    const stats = await h.stats();
    expect(stats.logins).toBe(1);
    expect(stats.quotaSpent).toBe(2);
    const repeat = await call('download', { ref: rows[0].ref });
    expect(repeat.transfer_skipped).toBe(true);
    expect((await h.stats()).logins).toBe(1);
    expect((await h.stats()).quotaSpent).toBe(2);
    await expect(fs.stat(path.join(home, 'egress-trap.txt'))).rejects.toMatchObject({
      code: 'ENOENT',
    });
  });

  const book = (id) => ({
    source: 'zlibrary',
    id: String(id),
    hash: `hash${id}`,
    title: `Offline ${id}`,
    extension: 'epub',
  });
  const acquire = async (api, id, filename, options = {}) =>
    api.invokeAcquisitionBridge(
      'acquire_book',
      { book_details: book(id), output_dir: process.env.ZLIBRARY_OUTPUT_ROOT, filename },
      { timeoutMs: 15000, ...options },
    );
  test('cold distinct acquisitions and SDK search singleflight one login; same destination follower skips', async () => {
    const api = await import('../dist/lib/zlibrary-api.js');
    await h.mode({ mode: 'slow', reset: true, remaining: 8 });
    const [a, b, follower, search] = await Promise.all([
      acquire(api, 202, 'cold202.epub'),
      acquire(api, 203, 'cold203.epub'),
      acquire(api, 202, 'cold202.epub'),
      call('search', { query: 'Seneca Letters', sources: ['zlibrary'] }),
    ]);
    expect([a.transfer_skipped, follower.transfer_skipped].sort()).toEqual([false, true]);
    expect(b.transfer_skipped).toBe(false);
    expect(search.rows).toHaveLength(2);
    const stats = await h.stats();
    expect(stats.logins).toBe(1);
    expect(stats.quotaSpent).toBe(2);
  });
  test('receipt hits bypass missing credentials, unrelated pending login, and shared cooldown', async () => {
    const originalApi = await import('../dist/lib/zlibrary-api.js');
    const complete = await acquire(originalApi, 202, 'receipt.epub');
    delete process.env.ZLIBRARY_EMAIL;
    delete process.env.ZLIBRARY_PASSWORD;
    expect((await acquire(originalApi, 202, 'receipt.epub')).transfer_skipped).toBe(true);
    process.env.ZLIBRARY_EMAIL = 'rehearsal-account@example.invalid';
    process.env.ZLIBRARY_PASSWORD = 'rehearsal-password-canary';
    jest.resetModules();
    const api = await import('../dist/lib/zlibrary-api.js');
    await h.mode({ mode: 'slow' });
    // Independent fresh owner is awaiting login while this existing receipt returns.
    const pending = api.searchBooks({ query: 'slow-Seneca' }).catch((error) => error);
    expect((await acquire(api, 202, 'receipt.epub')).transfer_skipped).toBe(true);
    await pending;
    jest.resetModules();
    const failing = await import('../dist/lib/zlibrary-api.js');
    await h.mode({ mode: 'login400' });
    await expect(acquire(failing, 203, 'denied.epub')).rejects.toMatchObject({
      context: { reason: 'login_failed' },
    });
    const stats = await h.stats();
    expect((await acquire(failing, 202, 'receipt.epub')).transfer_skipped).toBe(true);
    await expect(failing.searchBooks({ query: 'Seneca Letters' })).rejects.toMatchObject({
      context: { reason: 'auth_backoff' },
    });
    await expect(acquire(failing, 203, 'cooldown.epub')).rejects.toMatchObject({
      context: { reason: 'auth_backoff' },
    });
    expect((await h.stats()).logins).toBe(stats.logins);
    expect((await h.stats()).calls['/eapi/user/profile']).toBe(stats.calls['/eapi/user/profile']);
    expect(await fs.readFile(complete.path)).toBeDefined();
  });
  test('search login failure gates fresh acquisition only after intent; invalid/foreign receipt never demands', async () => {
    const api = await import('../dist/lib/zlibrary-api.js');
    await h.mode({ mode: 'login400' });
    await expect(api.searchBooks({ query: 'Seneca Letters' })).rejects.toMatchObject({
      context: { reason: 'login_failed' },
    });
    await expect(acquire(api, 202, 'after-search.epub')).rejects.toMatchObject({
      context: { reason: 'auth_backoff' },
    });
    const target = path.join(process.env.ZLIBRARY_OUTPUT_ROOT, 'after-search.epub.acq.json');
    expect(JSON.parse(await fs.readFile(target, 'utf8')).state).toBe('intent');
    expect((await h.stats()).logins).toBe(1);
    await expect(acquire(api, 202, '../escape.epub')).rejects.toThrow();
    expect((await h.stats()).logins).toBe(1);
    await h.mode({ mode: 'healthy' });
    jest.resetModules();
    const warm = await import('../dist/lib/zlibrary-api.js');
    await acquire(warm, 202, 'foreign.epub');
    const stats = await h.stats();
    await expect(acquire(warm, 203, 'foreign.epub')).rejects.toThrow(/another selection/);
    expect((await h.stats()).logins).toBe(stats.logins);
    expect((await h.stats()).quotaSpent).toBe(stats.quotaSpent);
  });
  test('abort during real lazy login reaps both waiting acquisition and auth-control children', async () => {
    const api = await import('../dist/lib/zlibrary-api.js');
    const runner = await import('../dist/lib/python-runner.js');
    await h.mode({ mode: 'slow', reset: true });
    const controller = new AbortController();
    const outcome = acquire(api, 202, 'aborted-login.epub', { signal: controller.signal }).catch(
      (error) => error,
    );
    const end = Date.now() + 5000;
    while (!(await h.stats()).logins && Date.now() < end)
      await new Promise((resolve) => setTimeout(resolve, 10));
    expect((await h.stats()).logins).toBe(1);
    controller.abort();
    expect((await outcome).context.reason).toBe('aborted');
    expect(runner.liveChildCount()).toBe(0);
    const reply = await acquire(api, 202, 'aborted-login.epub');
    expect(reply.transfer_skipped).toBe(false);
    expect((await h.stats()).quotaSpent).toBe(1);
  });
  test('documented per-call acquisition still logs in per fresh transfer', async () => {
    process.env.ZLIBRARY_SESSION_MODE = 'per-call';
    const api = await import('../dist/lib/zlibrary-api.js');
    await acquire(api, 202, 'per202.epub');
    await acquire(api, 203, 'per203.epub');
    expect((await h.stats()).logins).toBe(2);
    expect((await h.stats()).quotaSpent).toBe(2);
  });
});

// These cases run unchanged on hosted Windows with Python3.10/3.13.
describe('native protocol real Node/Python pipes', () => {
  let directory,
    runner,
    diagnosticEvents,
    diagnosticCase = 0;
  const diagnostics = process.env.LAZY_PROTOCOL_DIAGNOSTICS === '1';
  const input = {
    identity: 'offline@example.invalid',
    generation: 0,
    action: 'operation',
    domain: 'offline.invalid',
    remix_userid: '7',
    remix_userkey: 'native-secret-canary',
  };
  const pythonPath =
    process.env.LAZY_PROTOCOL_PYTHON ||
    path.resolve(process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
  const options = (mode) => ({
    pythonPath,
    scriptPath: path.resolve('__tests__/fixtures'),
    args: [mode, directory],
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
  });
  const run = (mode, extra = {}) =>
    runner.runPythonBridge('lazy-session-worker.py', options(mode), {
      timeoutMs: 4000,
      onSessionNeeded: (c) => c.grant(input),
      ...extra,
      onProtocolDiagnostic:
        diagnostics || extra.onProtocolDiagnostic
          ? (event) => {
              if (diagnostics && diagnosticEvents.length < 768) diagnosticEvents.push(event);
              extra.onProtocolDiagnostic?.(event);
            }
          : undefined,
    });
  const observe = (child) => {
    if (!diagnostics) return;
    const started = performance.now();
    let sequence = 0;
    const mark = (phase, count, error) => {
      if (diagnosticEvents.length >= 768) return;
      diagnosticEvents.push({
        phase,
        sequence: ++sequence,
        elapsedMs: Math.max(0, Math.round(performance.now() - started)),
        ...(count === undefined ? {} : { count: Math.min(8193, count) }),
        ...(error
          ? {
              code: ['EPIPE', 'ECONNRESET', 'ERR_STREAM_DESTROYED'].includes(error.code)
                ? error.code
                : 'OTHER',
            }
          : {}),
      });
    };
    child.stdio[4].on('data', (chunk) => mark('request-data', chunk.length));
    for (const event of ['end', 'close', 'error'])
      child.stdio[4].on(event, (error) =>
        mark(`request-${event}`, undefined, event === 'error' ? error : undefined),
      );
    for (const event of ['finish', 'close', 'error'])
      child.stdin.on(event, (error) =>
        mark(`stdin-${event}`, undefined, event === 'error' ? error : undefined),
      );
    child.on('exit', () => mark('child-exit'));
    child.on('close', () => mark('child-close'));
  };
  const waitFile = async (name) => {
    const end = Date.now() + 3000;
    while (Date.now() < end) {
      try {
        return await fs.readFile(path.join(directory, name), 'utf8');
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
      await new Promise((r) => setTimeout(r, 10));
    }
    throw new Error(`Missing synthetic marker ${name}`);
  };
  beforeEach(async () => {
    directory = await fs.mkdtemp(path.join(os.tmpdir(), 'native-lazy-'));
    diagnosticEvents = [];
    diagnosticCase++;
    runner = await import('../dist/lib/python-runner.js');
  });
  afterEach(async () => {
    if (diagnostics) {
      let python = [];
      try {
        python = (await fs.readFile(path.join(directory, 'protocol-diagnostic.jsonl'), 'utf8'))
          .trim()
          .split('\n')
          .filter(Boolean)
          .slice(-768)
          .map((line) => JSON.parse(line));
      } catch (error) {
        if (error.code !== 'ENOENT') python = [{ phase: 'diagnostic-file', state: 'invalid' }];
      }
      const artifact = {
        case: diagnosticCase,
        parent: diagnosticEvents,
        python,
        liveChildren: runner.liveChildCount(),
      };
      const serialized = JSON.stringify(artifact, null, 2);
      expect(serialized).not.toContain(input.remix_userkey);
      expect(serialized).not.toContain('recovered-private-canary');
      expect(serialized).not.toContain('canary-not-public');
      await fs.mkdir('test_output/native-protocol', { recursive: true });
      await fs.writeFile(
        `test_output/native-protocol/case-${diagnosticCase}.json`,
        serialized + '\n',
      );
    }
    expect(runner.liveChildCount()).toBe(0);
    await fs.rm(directory, { recursive: true, force: true });
  });
  test('held lease + durable intent precede one grant; fragmented terminal update; receipt emits neither', async () => {
    let demands = 0;
    const updates = [];
    const first = await run('operation', {
      onSession: (u) => updates.push(u),
      onSessionNeeded: (c) => {
        demands++;
        // Synchronous files inspected before granting the waiting child.
        expect(nativeFs.readFileSync(path.join(directory, 'admitted'), 'utf8')).toBe(
          'intent+lease',
        );
        expect(
          JSON.parse(nativeFs.readFileSync(path.join(directory, 'synthetic.epub.acq.json'), 'utf8'))
            .state,
        ).toBe('intent');
        c.grant(input);
      },
    });
    expect(JSON.parse(first[0]).transfer_skipped).toBe(false);
    expect(updates).toHaveLength(1);
    expect(updates[0].validate_next).toBe(true);
    const repeat = await run('operation', {
      onSession: (u) => updates.push(u),
      onSessionNeeded: () => {
        demands++;
        throw new Error('Receipt requested auth');
      },
    });
    expect(JSON.parse(repeat[0]).transfer_skipped).toBe(true);
    expect(demands).toBe(1);
    expect(updates).toHaveLength(1);
    expect(await fs.readFile(path.join(directory, 'transfers'), 'utf8')).toBe('1\n');
  });
  test('diagnostic callback observes only bounded protocol metadata', async () => {
    const events = [];
    await run('operation', {
      onProtocolDiagnostic(event) {
        events.push(event);
      },
    });
    expect(events.some((event) => event.phase === 'request-data')).toBe(true);
    expect(events.some((event) => event.phase === 'request-end')).toBe(true);
    // Observational close can follow the already-decoded successful result.
    // Await that event in this test; do not change product completion semantics.
    const closeDeadline = performance.now() + 1000;
    while (
      !events.some((event) => event.phase === 'child-close') &&
      performance.now() < closeDeadline
    )
      await new Promise((resolve) => setTimeout(resolve, 5));
    expect(events.some((event) => event.phase === 'child-close')).toBe(true);
    expect(JSON.stringify(events)).not.toContain(input.remix_userkey);
    const fields = new Set([
      'phase',
      'sequence',
      'elapsedMs',
      'demanded',
      'granted',
      'settled',
      'count',
      'code',
      'errno',
    ]);
    expect(events.length).toBeLessThanOrEqual(256);
    expect(events.every((event) => Object.keys(event).every((field) => fields.has(field)))).toBe(
      true,
    );
    expect(
      events.every(
        (event) => Number.isInteger(event.sequence) && event.sequence > 0 && event.elapsedMs >= 0,
      ),
    ).toBe(true);
  });
  test('diagnostic callback failure cannot change the real private handoff outcome', async () => {
    const result = await run('operation', {
      onProtocolDiagnostic() {
        throw new Error('private-observer-canary');
      },
    });
    expect(JSON.parse(result[0]).transfer_skipped).toBe(false);
  });
  test('fragmented request is accepted once', async () => {
    let demands = 0;
    await run('request-fragmented', {
      onSessionNeeded: (c) => {
        demands++;
        nativeFs.writeFileSync(path.join(directory, 'parent-observed-demand'), 'yes');
        c.grant(input);
      },
    });
    expect(demands).toBe(1);
    expect(await fs.readFile(path.join(directory, 'parent-observed-demand'), 'utf8')).toBe('yes');
  });
  test.each(['duplicate', 'oversize', 'malformed', 'version', 'partial'])(
    'rejects %s request before grant and reaps child',
    async (mode) => {
      let demands = 0;
      let failure;
      try {
        await run(`request-${mode}`, {
          onSessionNeeded: () => {
            demands++;
          },
        });
      } catch (error) {
        failure = error;
      }
      expect(failure?.message).toBe('Invalid private session request');
      expect(JSON.stringify(failure)).not.toContain('canary-not-public');
      expect(demands).toBe(0);
    },
  );
  test.each(['early-update', 'duplicate-update', 'double-grant'])(
    'rejects %s without leaking bearer',
    async (mode) => {
      let failure;
      try {
        await run(mode === 'double-grant' ? 'operation' : mode, {
          onSessionNeeded: (c) => {
            c.grant(input);
            if (mode === 'double-grant') c.grant(input);
          },
        });
      } catch (error) {
        failure = error;
      }
      expect(failure?.message).toMatch(/Invalid private session/);
      expect(JSON.stringify(failure)).not.toContain(input.remix_userkey);
    },
  );
  test('delivered and recovered key canaries never survive a child error', async () => {
    let error;
    try {
      await run('leaked-error');
    } catch (failure) {
      error = failure;
    }
    expect(error).toBeInstanceOf(Error);
    expect(JSON.stringify(error)).not.toContain(input.remix_userkey);
    expect(JSON.stringify(error)).not.toContain('recovered-private-canary');
  });
  test('parent denial remains authoritative, no transfer and next call can reclaim lease', async () => {
    const denial = new Error('Synthetic owner cooldown');
    await expect(run('operation', { onSessionNeeded: (c) => c.deny(denial) })).rejects.toBe(denial);
    await expect(fs.stat(path.join(directory, 'transfers'))).rejects.toMatchObject({
      code: 'ENOENT',
    });
    await run('operation');
  });
  test.each(['demand', 'granted'])(
    'caller abort at %s reaps child, removes listener and releases lease',
    async (phase) => {
      const controller = new AbortController();
      const promise = run('stall', {
        signal: controller.signal,
        onSessionNeeded: (c) => {
          if (phase === 'demand') controller.abort();
          else c.grant(input);
        },
      });
      const outcome = promise.catch((error) => error);
      if (phase === 'granted') {
        await waitFile('granted');
        controller.abort();
      }
      const error = await outcome;
      expect(error.context.reason).toBe('aborted');
      expect(JSON.stringify(error)).not.toContain(input.remix_userkey);
      const { getEventListeners } = await import('node:events');
      expect(getEventListeners(controller.signal, 'abort')).toHaveLength(0);
      await run('operation');
      expect(
        (await fs.readFile(path.join(directory, 'transfers'), 'utf8')).trim().split('\n'),
      ).toHaveLength(phase === 'granted' ? 2 : 1);
    },
  );
  test('private auth-control abort also waits for actual child exit', async () => {
    const controller = new AbortController();
    const pending = runner
      .runPythonBridge('lazy-session-worker.py', options('control'), {
        sessionInput: { action: 'login' },
        signal: controller.signal,
        timeoutMs: 4000,
      })
      .catch((error) => error);
    await waitFile('control-ready');
    controller.abort();
    expect((await pending).context.reason).toBe('aborted');
    expect(runner.liveChildCount()).toBe(0);
    if (process.platform !== 'win32') expect(await waitFile('control-cleaned')).toBe('yes');
  });
  test('unanswered demand expires and reaps without transfer', async () => {
    await expect(
      run('operation', { timeoutMs: 350, onSessionNeeded: () => {} }),
    ).rejects.toMatchObject({ context: { reason: 'timeout' } });
    await expect(fs.stat(path.join(directory, 'transfers'))).rejects.toMatchObject({
      code: 'ENOENT',
    });
    await run('operation');
  });
  test.each(['fragmented', 'empty', 'duplicate', 'oversize', 'denied', 'partial', 'timeout'])(
    'Python asynchronous reply parser: %s',
    async (kind) => {
      const { spawn } = await import('node:child_process');
      const child = spawn(
        pythonPath,
        [path.resolve('__tests__/fixtures/lazy-session-worker.py'), 'reply', directory],
        { stdio: ['overlapped', 'pipe', 'pipe', 'pipe', 'pipe'] },
      );
      observe(child);
      let stdout = '',
        stderr = '',
        demand = '';
      child.stdout.on('data', (c) => {
        stdout += c;
      });
      child.stderr.on('data', (c) => {
        stderr += c;
      });
      child.stdin.on('error', () => {});
      const closed = new Promise((resolve, reject) => {
        child.on('error', reject);
        child.on('close', (code) => resolve(code));
      });
      await new Promise((resolve) => {
        child.stdio[4].on('data', (c) => {
          demand += c;
        });
        child.stdio[4].on('end', resolve);
      });
      expect(JSON.parse(demand)).toEqual({ v: 1, type: 'session_needed' });
      const frame = JSON.stringify({ v: 1, type: 'session', input }) + '\n';
      if (kind === 'fragmented') {
        for (const char of frame) {
          child.stdin.write(char);
        }
        child.stdin.end();
      } else if (kind === 'empty') child.stdin.end();
      else if (kind === 'duplicate') child.stdin.end(frame + frame);
      else if (kind === 'oversize') child.stdin.end('private-canary'.repeat(700) + '\n');
      else if (kind === 'denied')
        child.stdin.end('{"v":1,"type":"denied","code":"auth_unavailable"}\n');
      else if (kind === 'partial') child.stdin.end(frame.trim());
      expect(await closed).toBe(0);
      const result = JSON.parse(stdout);
      if (kind === 'fragmented') expect(result).toEqual({ ok: true });
      else
        expect(result.error).toBe(
          kind === 'denied'
            ? 'Private session request denied'
            : kind === 'timeout'
              ? 'Private session reply deadline exceeded'
              : 'Invalid private session reply',
        );
      expect(stdout + stderr).not.toContain(input.remix_userkey);
      expect(stdout + stderr).not.toContain('private-canary');
    },
  );
  test.each([
    'valid',
    'without-eof',
    'empty',
    'duplicate',
    'denied',
    'partial',
    'abort',
    'read-abort',
  ])('diagnostic reader-connected stdin independent of fd4 EOF: %s', async (kind) => {
    const { spawn } = await import('node:child_process');
    const child = spawn(
      pythonPath,
      [path.resolve('__tests__/fixtures/lazy-session-worker.py'), 'probe-reply', directory],
      {
        stdio: ['overlapped', 'pipe', 'pipe', 'pipe', 'pipe'],
        env: { ...process.env, LAZY_PROTOCOL_DIAGNOSTICS: '1' },
      },
    );
    observe(child);
    child.stdio[4].resume();
    child.stdio[3].resume();
    let stderr = '';
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });
    child.stdin.on('error', () => {});
    let output = '',
      firstLine;
    const ready = new Promise((resolve) => {
      firstLine = resolve;
    });
    child.stdout.on('data', (chunk) => {
      output += chunk;
      if (output.includes('\n')) firstLine(JSON.parse(output.split('\n')[0]));
    });
    const closed = new Promise((resolve, reject) => {
      child.on('error', reject);
      child.on('close', (code) => {
        firstLine(undefined);
        resolve(code);
      });
    });
    try {
      // Test-only rendezvous after connect. Never used by the runner/owner:
      // product demand still requires the entire fd4 frame AND EOF.
      expect(await ready).toEqual({ reader_connected: true });
      const frame = JSON.stringify({ v: 1, type: 'session', input }) + '\n';
      if (kind === 'abort') child.kill('SIGTERM');
      else if (kind === 'read-abort') {
        child.stdin.write(frame.slice(0, 7));
        const deadline = performance.now() + 750;
        let received = false;
        while (!received && performance.now() < deadline) {
          const trace = await fs.readFile(
            path.join(directory, 'protocol-diagnostic.jsonl'),
            'utf8',
          );
          received = trace
            .trim()
            .split('\n')
            .map((line) => JSON.parse(line))
            .some((event) => event.phase === 'input-read' && event.state === 'done');
          if (!received) await new Promise((resolve) => setTimeout(resolve, 5));
        }
        expect(received).toBe(true);
        child.kill('SIGTERM');
      } else if (kind === 'valid') {
        for (const char of frame) child.stdin.write(char);
        child.stdin.end();
      } else if (kind === 'without-eof') child.stdin.write(frame);
      else if (kind === 'duplicate') child.stdin.end(frame + frame);
      else if (kind === 'partial') child.stdin.end(frame.trim());
      else if (kind === 'empty') child.stdin.end();
      else child.stdin.end('{"v":1,"type":"denied","code":"auth_unavailable"}\n');
      const code = await closed;
      if (kind !== 'abort' && kind !== 'read-abort') {
        expect(code).toBe(0);
        const reply = JSON.parse(output.trim().split('\n')[1]);
        expect(reply).toEqual(
          kind === 'valid'
            ? { ok: true }
            : {
                error:
                  kind === 'denied'
                    ? 'Private session request denied'
                    : kind === 'without-eof'
                      ? 'Private session reply deadline exceeded'
                      : 'Invalid private session reply',
              },
        );
      }
      expect(output + stderr).not.toContain(input.remix_userkey);
    } finally {
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
      await closed;
    }
  });
});
