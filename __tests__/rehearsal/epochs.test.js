import { afterAll, beforeAll, expect, test } from '@jest/globals';
import { Rehearsal } from './harness.js';
import { expectedFixes } from './expectations.js';
let h;
const observations = {};
const reuseTest = expectedFixes.has('reuse') ? test : test.failing;
const redactionTest = expectedFixes.has('redaction') ? test : test.failing;
beforeAll(async () => {
  h = await Rehearsal.start('epochs');
});
afterAll(async () => {
  await h?.close();
});

test('E1 explicit cookie rejection with overlapping callers records one new epoch', async () => {
  await h.scenario('E1', async (connect) => {
    const c = await connect();
    await h.call(c, 'search', { sources: ['zlibrary'], query: 'warm' });
    const before = await h.stats();
    await h.mode({ mode: 'healthy', reject_epoch: true });
    const replies = await Promise.all(
      Array.from({ length: 5 }, (_, i) =>
        h.call(c, 'search', { sources: ['zlibrary'], query: `refresh-${i}` }, true),
      ),
    );
    replies.forEach((r, i) => expect(r.rows[0].title).toBe(`Rehearsal refresh-${i}`));
    const after = await h.stats();
    observations.refresh = after.logins - before.logins;
    expect(after.loginSuccesses - before.loginSuccesses).toBe(observations.refresh);
  });
});
reuseTest('E1 rejection refresh is single-flight: exactly one successful new login', () => {
  expect(observations.refresh).toBe(1);
});

for (const mode of ['timeout', 'wall', 'ambiguous400', 'success0']) {
  test(`E2 ${mode}: execute ambiguity then recovery without discarding state`, async () => {
    await h.scenario(
      `E2-${mode}`,
      async (connect) => {
        const c = await connect();
        await h.call(c, 'search', { sources: ['zlibrary'], query: 'warm' });
        const before = await h.stats();
        await h.mode({ mode });
        const reply = await h.call(c, 'search', { sources: ['zlibrary'], query: 'ambiguous' }, true);
        // success:0 is silently normalized to empty books on master; retain that observation.
        expect(Boolean(reply.error) || reply.rows?.length === 0).toBe(true);
        await h.mode({ mode: 'healthy' });
        expect((await h.call(c, 'search', { sources: ['zlibrary'], query: 'recovered' })).rows[0].title).toBe(
          'Rehearsal recovered',
        );
        observations[mode] = (await h.stats()).logins - before.logins;
      },
      { budgetMs: 6000 },
    );
  });
  reuseTest(`E2 ${mode}: ambiguous failure causes zero additional login attempts`, () => {
    expect(observations[mode]).toBe(0);
  });
}

test('E3 invalid login stops at the configured zero-retry budget', async () => {
  await h.scenario('E3', async (connect) => {
    const c = await connect();
    await h.mode({ mode: 'login400' });
    expect((await h.call(c, 'search', { sources: ['zlibrary'], query: 'invalid' }, true)).error).toBeDefined();
    expect(await h.stats()).toMatchObject({ logins: 1, loginSuccesses: 0 });
  });
});

test('TLS control rejects the disposable certificate when trust is not passed', async () => {
  await h.scenario(
    'TLS-untrusted',
    async (connect) => {
      const c = await connect();
      expect((await h.call(c, 'search', { sources: ['zlibrary'], query: 'untrusted' }, true)).error.code).toMatch(/internal|provider_unreachable/);
      expect((await h.stats()).logins).toBe(0);
    },
    { untrusted: true },
  );
});

test('Epoch scans have zero unexpected sentinel findings', () => {
  expect(h.leaks).toBe(0);
});

redactionTest('Epoch known cookie-ID log finding is absent', () => {
  expect(h.knownFindings).toBe(0);
});
