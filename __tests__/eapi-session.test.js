import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
const runPythonBridge = jest.fn();
let api, originalEnv, consoleSpy, now, clockSpy, ownerModule;
const identity = 'memory-reader@example.test';
const token = 'fake-private-cookie-marker';
const session = (generation, key = token, domain = 'memory.example.test') => ({
  identity,
  generation,
  domain,
  remix_userid: '7',
  remix_userkey: key,
});
const envelope = (value) => [
  JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(value) }] }),
];
const rejectReply = (generation) =>
  envelope({
    error: 'Authentication rejected: Expired #1',
    type: 'EAPIAuthenticationError',
    auth_rejected: { generation },
  });

beforeEach(async () => {
  originalEnv = { ...process.env };
  process.env.ZLIBRARY_EMAIL = identity;
  process.env.ZLIBRARY_PASSWORD = 'fake-password-marker';
  process.env.ZLIBRARY_SESSION_MODE = 'memory';
  process.env.RETRY_MAX_RETRIES = '0';
  delete process.env.ZLIBRARY_SESSION_LOGIN_COOLDOWN_MS;
  delete process.env.ZLIBRARY_SESSION_IDLE_MS;
  consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  now = 1000000;
  clockSpy = jest.spyOn(Date, 'now').mockImplementation(() => now);
  jest.resetModules();
  runPythonBridge.mockReset();
  jest.unstable_mockModule('../lib/venv-manager.js', () => ({
    getManagedPythonPath: async () => '/synthetic/python',
  }));
  jest.unstable_mockModule('../lib/python-runner.js', () => ({
    runPythonBridge,
    LONG_BRIDGE_TIMEOUT_MS: 2400000,
  }));
  api = await import('../lib/zlibrary-api.js');
  ownerModule = await import('../lib/eapi-session.js');
});
afterEach(() => {
  process.env = originalEnv;
  clockSpy.mockRestore();
  consoleSpy.mockRestore();
});
const call = (options) => api.getDownloadHistory({ count: 1 }, options);
function fakeBackend() {
  const counts = { login: 0, operation: 0, validate: 0 };
  runPythonBridge.mockImplementation(async (_script, options, runOptions) => {
    const input = runOptions.sessionInput;
    expect(options.args.join(' ')).not.toContain(token);
    expect(options.env?.ZLIBRARY_EAPI_SESSION).toBeUndefined();
    if (!input) return envelope([]);
    counts[input.action]++;
    if (input.action === 'login') {
      await new Promise((resolve) => setTimeout(resolve, 10));
      runOptions.onSession(session(input.generation));
      return envelope({ authenticated: true });
    }
    expect(input.remix_userkey).toBe(token);
    return envelope(input.action === 'validate' ? { authenticated: true } : []);
  });
  return counts;
}

test('six cold calls single-flight one login through a private channel', async () => {
  const counts = fakeBackend();
  expect(await Promise.all(Array.from({ length: 6 }, () => call()))).toEqual([
    [],
    [],
    [],
    [],
    [],
    [],
  ]);
  expect(counts).toEqual({ login: 1, operation: 6, validate: 0 });
  expect(JSON.stringify(consoleSpy.mock.calls)).not.toContain(token);
});

test('operation rejection makes Node refresh once on a different domain', async () => {
  const counts = fakeBackend();
  await call();
  now += 180001;
  runPythonBridge.mockImplementation(async (_script, _options, ro) => {
    const input = ro.sessionInput;
    if (input.action === 'login') {
      counts.login++;
      ro.onSession(session(input.generation, 'fresh-cookie', 'new.example.test'));
      return envelope({ authenticated: true });
    }
    if (input.remix_userkey === token) return rejectReply(input.generation);
    expect(input.domain).toBe('new.example.test');
    expect(input.authRetry).toBe(true);
    return envelope([{ id: 'fresh-result' }]);
  });
  await expect(call()).resolves.toEqual([{ id: 'fresh-result' }]);
  expect(counts.login).toBe(2);
});

test('repeated rejection has no third operation or second refresh', async () => {
  fakeBackend();
  await call();
  now += 180001;
  const actions = [];
  runPythonBridge.mockImplementation(async (_script, _options, ro) => {
    const input = ro.sessionInput;
    actions.push(input.action);
    if (input.action === 'login') {
      ro.onSession(session(input.generation, 'fresh-cookie'));
      return envelope({ authenticated: true });
    }
    return rejectReply(input.generation);
  });
  await expect(call()).rejects.toThrow(/rejected/i);
  expect(actions).toEqual(['operation', 'login', 'operation']);
});

test('cooldown bounds two server owners sharing an invalidating fake', async () => {
  const first = new ownerModule.EapiSessionOwner(),
    second = new ownerModule.EapiSessionOwner();
  let current = '',
    logins = 0;
  const backend = (owner) => async (input) => {
    if (input.action === 'login') {
      current = 'cookie-' + ++logins;
      owner.consume(session(input.generation, current), identity, input.generation);
      return { authenticated: true };
    }
    if (input.remix_userkey !== current)
      throw ownerModule.authRejected(input.generation, 'Expired #1');
    return 'ok';
  };
  await first.run(identity, backend(first));
  await second.run(identity, backend(second));
  await expect(first.run(identity, backend(first))).rejects.toThrow(/cooldown/i);
  for (let n = 0; n < 4; n++)
    await expect(first.run(identity, backend(first))).rejects.toThrow(/cooldown/i);
  expect(logins).toBe(2);
  expect(await second.run(identity, backend(second))).toBe('ok');
  now += 180001;
  expect(await first.run(identity, backend(first))).toBe('ok');
  expect(logins).toBe(3);
  // The second owner can now invalidate the first again, but each pays its own cooldown.
  expect(await second.run(identity, backend(second))).toBe('ok');
  await expect(first.run(identity, backend(first))).rejects.toThrow(/cooldown/i);
  expect(logins).toBe(4);
});

test('stale generation cannot overwrite or clear a newer session', () => {
  const owner = new ownerModule.EapiSessionOwner();
  const generation = owner.generationFor(identity);
  owner.consume(session(generation), identity, generation);
  const latest = owner.generationFor(identity);
  owner.consume(session(generation, 'stale'), identity, generation);
  owner.reject(identity, generation);
  expect(owner.get(identity).remix_userkey).toBe(token);
  expect(owner.generationFor(identity)).toBe(latest);
});

test('idle validation runs after the gap, not on each warm call', async () => {
  const counts = fakeBackend();
  await call();
  await call();
  expect(counts.validate).toBe(0);
  now += 300001;
  await call();
  expect(counts.validate).toBe(1);
  expect(counts.login).toBe(1);
});

test('identity change never sends a prior identity session', async () => {
  fakeBackend();
  await call();
  process.env.ZLIBRARY_EMAIL = 'other@example.test';
  let seenLogin = false;
  runPythonBridge.mockImplementation(async (_script, _opts, ro) => {
    const input = ro.sessionInput;
    if (input.action === 'login') {
      expect(input.remix_userkey).toBeUndefined();
      seenLogin = true;
      ro.onSession({
        ...session(input.generation, 'other-cookie'),
        identity: 'other@example.test',
      });
    } else expect(input.remix_userkey).toBe('other-cookie');
    return envelope([]);
  });
  await call();
  expect(seenLogin).toBe(true);
});

test('per-call mode and non-EAPI work have no session channel', async () => {
  fakeBackend();
  await call();
  runPythonBridge.mockImplementation(async (_s, options, ro) => {
    expect(ro.sessionInput).toBeUndefined();
    expect(options.env.ZLIBRARY_EAPI_SESSION).toBeUndefined();
    return envelope(
      options.args[0] === 'process_document'
        ? { processed_file_path: '/synthetic/result.txt' }
        : { books: [], sources_used: [] },
    );
  });
  await api.searchMultiSource({ query: 'offline', source: 'libgen' });
  await api.processDocumentForRag({ filePath: '/synthetic/input.txt' });
  process.env.ZLIBRARY_SESSION_MODE = 'per-call';
  await call();
  await call();
});

test.each(['', 'off', 'disk', 'false', 'unexpected'])('unknown mode %s fails loudly', (mode) => {
  process.env.ZLIBRARY_SESSION_MODE = mode;
  expect(() => ownerModule.getSessionMode()).toThrow(/ZLIBRARY_SESSION_MODE/);
});

test('queued waiter has its own deadline and never spawns', async () => {
  let release;
  runPythonBridge.mockImplementationOnce(
    (_s, _opts, ro) =>
      new Promise((resolve) => {
        release = () => {
          ro.onSession(session(ro.sessionInput.generation));
          resolve(envelope({ authenticated: true }));
        };
      }),
  );
  const first = call();
  while (!release) await new Promise((resolve) => setTimeout(resolve, 1));
  await expect(call({ timeoutMs: 10 })).rejects.toThrow(/deadline|budget|timeout/i);
  release();
  runPythonBridge.mockResolvedValue(envelope([]));
  await first;
  expect(runPythonBridge).toHaveBeenCalledTimes(2);
});

test('dead acquisition leader releases the flight and next waiter can lead', async () => {
  process.env.ZLIBRARY_SESSION_LOGIN_COOLDOWN_MS = '1';
  let attempts = 0;
  runPythonBridge.mockImplementation(async (_s, _opts, ro) => {
    if (ro.sessionInput.action === 'login') {
      attempts++;
      if (attempts === 1) {
        now += 2;
        throw new Error('leader died');
      }
      ro.onSession(session(ro.sessionInput.generation));
    }
    return envelope([]);
  });
  const results = await Promise.allSettled([call(), call()]);
  expect(results.map((r) => r.status)).toEqual(['rejected', 'fulfilled']);
  expect(attempts).toBe(2);
});

test('private marker never appears in malformed stdout errors or logs', async () => {
  fakeBackend();
  await call();
  runPythonBridge.mockResolvedValue(['not JSON ' + token]);
  const caught = await call().catch((error) => error);
  expect(JSON.stringify(caught) + JSON.stringify(consoleSpy.mock.calls)).not.toContain(token);
});

test('a queued deadline cannot release the active leader to a later caller', async () => {
  const owner = new ownerModule.EapiSessionOwner();
  let release,
    operations = 0;
  const backend = async (input) => {
    if (input.action === 'login') {
      await new Promise((resolve) => {
        release = resolve;
      });
      owner.consume(session(input.generation), identity, input.generation);
    } else operations++;
    return 'ok';
  };
  const first = owner.run(identity, backend);
  while (!release) await new Promise((resolve) => setTimeout(resolve, 1));
  await expect(owner.run(identity, backend, { timeoutMs: 10 })).rejects.toThrow(/deadline/i);
  const third = owner.run(identity, backend);
  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(operations).toBe(0);
  release();
  await first;
  await third;
  expect(operations).toBe(2);
});

test('timed-out leader releases flight and late acquisition is fenced', async () => {
  process.env.ZLIBRARY_SESSION_LOGIN_COOLDOWN_MS = '1';
  const owner = new ownerModule.EapiSessionOwner();
  let late,
    attempts = 0;
  const backend = async (input) => {
    if (input.action === 'login') {
      attempts++;
      if (attempts === 1) {
        await new Promise((resolve) => {
          late = () => {
            owner.consume(session(input.generation, 'late-cookie'), identity, input.generation);
            resolve();
          };
        });
      } else owner.consume(session(input.generation, 'current-cookie'), identity, input.generation);
    }
    return 'ok';
  };
  const first = owner.run(identity, backend, { timeoutMs: 10 });
  await expect(first).rejects.toThrow(/deadline/i);
  now += 2;
  await expect(owner.run(identity, backend)).resolves.toBe('ok');
  late();
  await new Promise((resolve) => setTimeout(resolve, 1));
  expect(owner.get(identity).remix_userkey).toBe('current-cookie');
  expect(attempts).toBe(2);
});

test('a queued caller aborts without spawning a child', async () => {
  const owner = new ownerModule.EapiSessionOwner();
  let release,
    attempts = 0;
  const backend = async (input) => {
    attempts++;
    if (input.action === 'login') {
      await new Promise((resolve) => {
        release = resolve;
      });
      owner.consume(session(input.generation), identity, input.generation);
    }
    return 'ok';
  };
  const first = owner.run(identity, backend);
  while (!release) await new Promise((resolve) => setTimeout(resolve, 1));
  const controller = new AbortController();
  const queued = owner.run(identity, backend, { signal: controller.signal });
  controller.abort();
  await expect(queued).rejects.toThrow(/aborted/i);
  release();
  await first;
  expect(attempts).toBe(2);
});

test('unset mode defaults to memory', () => {
  delete process.env.ZLIBRARY_SESSION_MODE;
  expect(ownerModule.getSessionMode()).toBe('memory');
});

test.each(['timeout', 'HTTP 513 DiamWall', 'HTTP 503', 'HTML HTTP 200'])(
  'operation uncertainty %s retains the owner session without login',
  async (message) => {
    const counts = fakeBackend();
    await call();
    runPythonBridge.mockRejectedValueOnce(new Error(message));
    await expect(call()).rejects.toThrow(message);
    fakeBackend();
    await call();
    expect(counts.login).toBe(1);
    expect(
      runPythonBridge.mock.calls.filter((args) => args[2].sessionInput.action === 'login'),
    ).toHaveLength(1);
  },
);

test('intentional auth retry bypasses retry multiplication and breaker accounting', async () => {
  process.env.RETRY_MAX_RETRIES = '3';
  process.env.CIRCUIT_BREAKER_THRESHOLD = '1';
  // Re-import so the threshold applies to this server owner.
  jest.resetModules();
  api = await import('../lib/zlibrary-api.js');
  fakeBackend();
  await call();
  now += 180001;
  const actions = [];
  runPythonBridge.mockImplementation(async (_script, _options, ro) => {
    const input = ro.sessionInput;
    actions.push(input.action);
    if (input.action === 'login') {
      ro.onSession(session(input.generation, 'new-cookie'));
      return envelope({ authenticated: true });
    }
    if (input.remix_userkey === token) return rejectReply(input.generation);
    throw new Error('network retry must not multiply this operation');
  });
  await expect(call()).rejects.toThrow(/network/);
  expect(actions).toEqual(['operation', 'login', 'operation']);
  runPythonBridge.mockResolvedValue(envelope([]));
  await expect(call()).resolves.toEqual([]);
});

test.each([
  [JSON.stringify({ unexpected: token })],
  [JSON.stringify({ content: [{ type: 'text', text: 'invalid ' + token }] })],
])('malformed public envelopes cannot echo a known private marker', async (...lines) => {
  fakeBackend();
  await call();
  runPythonBridge.mockResolvedValue(lines);
  const error = await call().catch((error) => error);
  expect(error).toBeInstanceOf(Error);
  expect(
    String(error.stack) + JSON.stringify(error) + JSON.stringify(consoleSpy.mock.calls),
  ).not.toContain(token);
});
