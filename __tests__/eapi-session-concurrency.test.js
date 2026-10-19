import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { EapiSessionOwner, authRejected } from '../lib/eapi-session.js';
import { PythonBridgeError } from '../lib/errors.js';
const identity = 'concurrent-reader@example.test';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const record = (input, key = 'cookie-old', domain = 'old.example.test') => ({
  identity,
  generation: input.generation,
  domain,
  remix_userid: '7',
  remix_userkey: key,
});
let previousEnv, now, clock;
beforeEach(() => {
  previousEnv = { ...process.env };
  delete process.env.ZLIBRARY_SESSION_LOGIN_COOLDOWN_MS;
  now = 1000000;
  clock = jest.spyOn(Date, 'now').mockImplementation(() => now);
});
afterEach(() => {
  process.env = previousEnv;
  clock.mockRestore();
});

test('cold callers share acquisition but their operations overlap and correlate', async () => {
  const owner = new EapiSessionOwner();
  let logins = 0,
    inflight = 0,
    max = 0;
  const invoke = (label) => async (input) => {
    if (input.action === 'login') {
      logins++;
      await sleep(10);
      owner.consume(record(input), identity, input.generation);
      return;
    }
    inflight++;
    max = Math.max(max, inflight);
    await sleep(label === 0 ? 25 : 10);
    inflight--;
    return label;
  };
  expect(
    await Promise.all(Array.from({ length: 6 }, (_, n) => owner.run(identity, invoke(n)))),
  ).toEqual([0, 1, 2, 3, 4, 5]);
  expect(logins).toBe(1);
  expect(max).toBeGreaterThan(1);
});

test('a long operation does not block a warm search', async () => {
  const owner = new EapiSessionOwner();
  let release;
  const login = async (input) => {
    if (input.action === 'login') owner.consume(record(input), identity, input.generation);
    return 'warm';
  };
  await owner.run(identity, login);
  const long = owner.run(
    identity,
    async () =>
      new Promise((resolve) => {
        release = resolve;
      }),
  );
  while (!release) await sleep(1);
  const fast = owner.run(identity, async () => 'search');
  let observed;
  try {
    observed = await Promise.race([fast, sleep(25).then(() => 'blocked')]);
  } finally {
    release('download');
    await long;
    await fast;
  }
  expect(observed).toBe('search');
});

test('overlapping immediate rejections share exactly one refresh on a new domain', async () => {
  const owner = new EapiSessionOwner();
  let logins = 0,
    active = 0,
    maxLogin = 0;
  const invoke = async (input) => {
    if (input.action === 'login') {
      logins++;
      active++;
      maxLogin = Math.max(maxLogin, active);
      await sleep(10);
      owner.consume(
        record(
          input,
          logins === 1 ? 'cookie-old' : 'cookie-new',
          logins === 1 ? 'old.example.test' : 'new.example.test',
        ),
        identity,
        input.generation,
      );
      active--;
      return;
    }
    if (input.remix_userkey === 'cookie-old') {
      await sleep(10);
      throw authRejected(input.generation, 'Authentication rejected');
    }
    expect(input.domain).toBe('new.example.test');
    expect(input.authRetry).toBe(true);
    return 'fresh';
  };
  // Acquire without rejecting the initial warm operation.
  await owner.run(identity, async (input) => (input.action === 'login' ? invoke(input) : 'warm'));
  expect(await Promise.all(Array.from({ length: 6 }, () => owner.run(identity, invoke)))).toEqual(
    Array(6).fill('fresh'),
  );
  expect(logins).toBe(2);
  expect(maxLogin).toBe(1);
});

test('failed login backoff grows, reports its cause and resets after success', async () => {
  const owner = new EapiSessionOwner();
  let attempts = 0,
    healthy = false,
    rejectNext = false;
  const invoke = async (input) => {
    if (input.action === 'login') {
      attempts++;
      if (!healthy)
        throw new PythonBridgeError(
          'login refused',
          { reason: 'login_failed', loginStatus: 401, loginToken: 'Invalid credentials #1' },
          false,
        );
      owner.consume(record(input, 'accepted-' + attempts), identity, input.generation);
      return;
    }
    if (rejectNext) {
      rejectNext = false;
      throw authRejected(input.generation, 'Authentication rejected');
    }
    return 'ok';
  };
  for (const seconds of [30, 60, 120, 180, 180]) {
    await expect(owner.run(identity, invoke)).rejects.toThrow();
    const count = attempts;
    await expect(owner.run(identity, invoke)).rejects.toThrow(
      new RegExp('HTTP 401.*Invalid credentials #1.*' + seconds + ' s'),
    );
    expect(attempts).toBe(count);
    now += seconds * 1000;
  }
  healthy = true;
  await expect(owner.run(identity, invoke)).resolves.toBe('ok');
  rejectNext = true;
  await expect(owner.run(identity, invoke)).resolves.toBe('ok');
  expect(attempts).toBe(7);
});

test('a delayed stale rejection retries the newer session without another login', async () => {
  const owner = new EapiSessionOwner();
  let logins = 0,
    release;
  const acquire = async (input) => {
    logins++;
    owner.consume(
      record(input, logins === 1 ? 'cookie-old' : 'cookie-new'),
      identity,
      input.generation,
    );
  };
  await owner.run(identity, async (input) => (input.action === 'login' ? acquire(input) : 'warm'));
  const delayed = owner.run(identity, async (input) => {
    if (input.remix_userkey === 'cookie-old')
      await new Promise((resolve) => {
        release = resolve;
      });
    if (input.remix_userkey === 'cookie-old')
      throw authRejected(input.generation, 'Authentication rejected');
    return input.remix_userkey;
  });
  while (!release) await sleep(1);
  const current = owner.run(identity, async (input) => {
    if (input.action === 'login') return acquire(input);
    if (input.remix_userkey === 'cookie-old')
      throw authRejected(input.generation, 'Authentication rejected');
    return input.remix_userkey;
  });
  const result = await Promise.race([current, sleep(30).then(() => 'blocked')]);
  release();
  expect(await delayed).toBe('cookie-new');
  expect(await current).toBe('cookie-new');
  expect(result).toBe('cookie-new');
  expect(logins).toBe(2);
});

test('a second quick rejection is bounded until a refreshed session survives', async () => {
  const owner = new EapiSessionOwner();
  let logins = 0,
    rejectNext = false;
  const invoke = async (input) => {
    if (input.action === 'login') {
      logins++;
      owner.consume(record(input, 'cookie-' + logins), identity, input.generation);
      return;
    }
    if (rejectNext) {
      rejectNext = false;
      throw authRejected(input.generation, 'Authentication rejected');
    }
    return 'ok';
  };
  await owner.run(identity, invoke);
  rejectNext = true;
  await owner.run(identity, invoke);
  expect(logins).toBe(2);
  rejectNext = true;
  await expect(owner.run(identity, invoke)).rejects.toMatchObject({
    context: { reason: 'auth_backoff' },
  });
  expect(logins).toBe(2);
  now += 30000;
  await owner.run(identity, invoke);
  expect(logins).toBe(3);
  rejectNext = true;
  await expect(owner.run(identity, invoke)).rejects.toThrow(/60 s/);
  now += 60000;
  await owner.run(identity, invoke);
  expect(logins).toBe(4);
  now += 180001;
  await owner.run(identity, invoke);
  rejectNext = true;
  await owner.run(identity, invoke);
  expect(logins).toBe(5);
});

test('the operation budget starts after acquisition has completed', async () => {
  const owner = new EapiSessionOwner();
  const value = await owner.run(
    identity,
    async (input) => {
      if (input.action === 'login') {
        await sleep(25);
        owner.consume(record(input), identity, input.generation);
        return;
      }
      await sleep(25);
      return 'complete';
    },
    { timeoutMs: 40 },
  );
  expect(value).toBe('complete');
});

test('business success-zero forces next-call profile validation without login', async () => {
  const owner = new EapiSessionOwner();
  let logins = 0,
    profiles = 0,
    businessFailure = true;
  const invoke = async (input) => {
    if (input.action === 'login') {
      logins++;
      owner.consume(record(input), identity, input.generation);
      return;
    }
    if (input.action === 'validate') {
      profiles++;
      return;
    }
    return businessFailure ? { success: 0, error: 'Unknown expiry' } : { success: 1 };
  };
  await owner.run(identity, invoke);
  businessFailure = false;
  await owner.run(identity, invoke);
  expect(logins).toBe(1);
  expect(profiles).toBe(1);
});

test('aborting one warm operation does not fence a peer domain update', async () => {
  const owner = new EapiSessionOwner();
  await owner.run(identity, async (input) => {
    if (input.action === 'login') owner.consume(record(input), identity, input.generation);
    return 'warm';
  });
  const controller = new AbortController();
  let releaseCancelled, releasePeer;
  const cancelled = owner.run(
    identity,
    async () =>
      new Promise((resolve) => {
        releaseCancelled = resolve;
      }),
    { signal: controller.signal },
  );
  const peer = owner.run(
    identity,
    async (input) =>
      new Promise((resolve) => {
        releasePeer = () => {
          owner.consume(
            record(input, 'cookie-old', 'peer.example.test'),
            identity,
            input.generation,
          );
          resolve('peer');
        };
      }),
  );
  while (!releaseCancelled || !releasePeer) await sleep(1);
  controller.abort();
  await expect(cancelled).rejects.toThrow(/aborted/i);
  releasePeer();
  expect(await peer).toBe('peer');
  releaseCancelled('late');
  expect(owner.get(identity).domain).toBe('peer.example.test');
});

test('an acquisition deadline also backs off repeated failed login attempts', async () => {
  const owner = new EapiSessionOwner();
  let late;
  await expect(
    owner.run(
      identity,
      async (input) =>
        new Promise((resolve) => {
          late = () => {
            owner.consume(record(input), identity, input.generation);
            resolve();
          };
        }),
      { timeoutMs: 10 },
    ),
  ).rejects.toThrow(/deadline/i);
  const backend = async (input) => {
    if (input.action === 'login')
      owner.consume(record(input, 'new-cookie'), identity, input.generation);
    return 'ok';
  };
  await expect(owner.run(identity, backend)).rejects.toMatchObject({
    context: { reason: 'auth_backoff' },
  });
  late();
  now += 30000;
  await expect(owner.run(identity, backend)).resolves.toBe('ok');
});
