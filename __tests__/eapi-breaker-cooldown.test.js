import { afterEach, beforeEach, expect, jest, test } from '@jest/globals';
import { CircuitBreaker } from '../dist/lib/circuit-breaker.js';
import { EapiSessionOwner } from '../dist/lib/eapi-session.js';

const identity = 'offline@example.invalid';
let saved;
beforeEach(() => {
  saved = { ...process.env };
  process.env.ZLIBRARY_SESSION_LOGIN_COOLDOWN_MS = '180000';
});
afterEach(() => {
  jest.restoreAllMocks();
  process.env = saved;
});

test.each([false, true])(
  'an OPEN EAPI breaker leaves login cooldown untouched (prior failed login: %s)',
  async (priorLoginFailure) => {
    // Real owner + breaker, no process or provider calls. A fixed clock keeps
    // the 30s login cooldown distinct from the 60s breaker timeout.
    let now = 1000000;
    jest.spyOn(Date, 'now').mockImplementation(() => now);
    jest.spyOn(console, 'error').mockImplementation(() => {});
    const owner = new EapiSessionOwner();
    const breaker = new CircuitBreaker({ threshold: 1, timeout: 60000 });
    let down = true;
    let logins = 0;
    const backend = (input) =>
      breaker.execute(async () => {
        if (down) throw new Error('offline outage');
        if (input.action === 'login') {
          logins++;
          owner.consume(
            {
              ...input,
              domain: 'offline.invalid',
              remix_userid: 'offline-user',
              remix_userkey: 'offline-key',
            },
            identity,
            input.generation,
          );
        }
        return 'ok';
      });
    if (priorLoginFailure) {
      await expect(owner.run(identity, backend)).rejects.toThrow('offline outage');
      await expect(owner.run(identity, backend)).rejects.toMatchObject({
        context: { reason: 'auth_backoff', retryAfterMs: 30000 },
      });
      now += 30001;
    } else {
      await expect(
        breaker.execute(async () => {
          throw new Error('offline outage');
        }),
      ).rejects.toThrow('offline outage');
    }
    expect(breaker.getState()).toBe('OPEN');
    await expect(owner.run(identity, backend)).rejects.toMatchObject({
      code: 'CIRCUIT_BREAKER_OPEN',
    });
    // Recovery can proceed immediately; the refusal did not start or extend
    // a login episode that outlives the actual dependency outage.
    breaker.reset();
    down = false;
    await expect(owner.run(identity, backend)).resolves.toBe('ok');
    expect(logins).toBe(1);
  },
);
