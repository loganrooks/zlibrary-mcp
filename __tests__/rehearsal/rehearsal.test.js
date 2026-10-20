import { afterAll, beforeAll, expect, test } from '@jest/globals';
import { readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { performance } from 'node:perf_hooks';
import { Rehearsal } from './harness.js';
import { expectedFixes } from './expectations.js';

let h;
let concurrentLogins;
beforeAll(async () => {
  h = await Rehearsal.start();
});
afterAll(async () => {
  await h?.close();
});

test('S1 sequential calls preserve identity and download exact bytes inside temp storage', async () => {
  await h.scenario('S1', async (connect) => {
    const c = await connect();
    const search = await h.call(c, 'search_books', { query: 'sequential' });
    expect(search.books).toHaveLength(1);
    expect(search.books[0].title).toBe('Rehearsal sequential');
    const metadata = await h.call(c, 'get_book_metadata', {
      bookId: '101',
      bookHash: 'hash101',
      include: ['description'],
    });
    expect(metadata.description).toBe('Details for rehearsal book 101');
    const limits = await h.call(c, 'get_download_limits');
    expect(limits).toMatchObject({ daily_limit: 10, daily_remaining: 7 });
    const result = await h.call(c, 'download_book_to_file', {
      bookDetails: search.books[0],
      outputDir: h.downloads,
      process_for_rag: false,
    });
    const file = await realpath(result.file_path);
    expect(file.startsWith((await realpath(h.downloads)) + path.sep)).toBe(true);
    expect(await readFile(file, 'utf8')).toBe('Offline rehearsal book 101.\n');
    const history = await h.call(c, 'get_download_history', { count: 1 });
    expect(history[0].id).toBe('101');
  });
});

test('S2 five concurrent slow/fast calls correlate; count logins independently', async () => {
  await h.scenario('S2', async (connect) => {
    const c = await connect();
    const queries = ['slow-first', 'fast-second', 'slow-third', 'fast-fourth', 'fast-fifth'];
    const replies = await Promise.all(queries.map((query) => h.call(c, 'search_books', { query })));
    replies.forEach((reply, i) => expect(reply.books[0].title).toBe(`Rehearsal ${queries[i]}`));
    const stats = await h.stats();
    expect(h.sessions).toHaveLength(1);
    expect(h.sessions[0].transport.pid).toBe(h.sessions[0].pid);
    expect(stats.maxInflight).toBeGreaterThan(1);
    concurrentLogins = stats.logins;
    expect(concurrentLogins).toBeGreaterThan(0);
  });
});

const loginTest = expectedFixes.has('reuse') ? test : test.failing;
const redactionTest = expectedFixes.has('redaction') ? test : test.failing;
const sourceSurvivalTest =
  expectedFixes.has('reuse') || expectedFixes.has('breaker') ? test : test.failing;
let localResult;
let alternateResult;
loginTest('S2 session reuse: exactly one login (expected failure on master)', () => {
  expect(concurrentLogins).toBe(1);
});

test('S3 two independent server processes each return their own results', async () => {
  await h.scenario('S3', async (connect) => {
    const clients = await Promise.all([connect(), connect()]);
    const replies = await Promise.all(
      clients.map((c, i) => h.call(c, 'search_books', { query: `host-${i}` })),
    );
    replies.forEach((r, i) => expect(r.books[0].title).toBe(`Rehearsal host-${i}`));
    expect((await h.stats()).logins).toBe(2);
  });
});

test('S4 authentication outage respects the selected login policy; listing survives', async () => {
  await h.scenario(
    'S4',
    async (connect) => {
      const c = await connect();
      await h.mode({ mode: 'unauthorized' });
      const reuse = expectedFixes.has('reuse');
      const started = Date.now();
      let cooldownStart;
      for (let i = 0; i < 5; i++) {
        const reply = await h.call(c, 'get_download_limits', {}, true);
        expect(reply.error.message).toMatch(
          reuse ? /rejected the login|authentication/i : /401|authentication/i,
        );
        if (reuse) {
          const stats = await h.stats();
          expect(stats.logins).toBeGreaterThan(0);
          expect(stats.logins).toBeLessThanOrEqual(1);
          expect(stats.loginSuccesses).toBe(0);
          if (cooldownStart) expect(stats).toEqual(cooldownStart);
          else cooldownStart = stats;
        }
      }
      const before = await h.stats();
      const blocked = await h.call(c, 'get_download_limits', {}, true);
      expect(blocked.error.message).toMatch(
        reuse ? /rejected the login|authentication/i : /circuit breaker.*open/i,
      );
      expect(await h.stats()).toEqual(before);
      const cooldownObservedMs = Date.now() - started;
      // v3's first failed-login window is 30 seconds; do not cross its expiry.
      if (reuse) expect(cooldownObservedMs).toBeLessThan(30000);
      const removed = await c.callTool({ name: 'process_document_for_rag', arguments: { file_path: '/unused' } });
      localResult = removed;
      expect(removed.isError).toBe(true);
      expect(await h.stats()).toEqual(before);
      h.scan(await c.listTools());
      expect((await c.listTools()).tools.length).toBeGreaterThan(0);
      alternateResult = await h.call(
        c,
        'search_multi_source',
        { query: 'fixture', source: 'libgen', count: 1 },
        true,
      );
      h.note('S4', {
        loginPolicy: reuse ? 'authentication cooldown' : 'master shared breaker',
        breaker: reuse
          ? 'not required to open on authentication failures'
          : 'OPEN after five failures',
        ...(reuse
          ? {
              cooldownUpstreamBefore: cooldownStart,
              cooldownUpstreamAfter: before,
              cooldownObservedMs,
              authenticationRepliesChecked: 6,
            }
          : {}),
        removedProcessing: 'unknown tool; no provider contact',
        toolsList: 'works',
        alternateSources: alternateResult.error
          ? 'Library Genesis blocked'
          : 'Library Genesis works',
      });
    },
    { libgen: true },
  );
});

test('S5 capture observed tool names and argument names (not an approved surface)', async () => {
  await h.scenario('S5', async (connect) => {
    const c = await connect();
    const listed = await c.listTools();
    h.scan(listed);
    const surface = listed.tools
      .map((t) => ({ name: t.name, arguments: Object.keys(t.inputSchema.properties ?? {}).sort() }))
      .sort((a, b) => a.name.localeCompare(b.name));
    expect(surface.some((t) => t.name === 'search_books' && t.arguments.includes('query'))).toBe(
      true,
    );
    expect(surface).toEqual(
      JSON.parse(await readFile(new URL('./tools-surface.json', import.meta.url), 'utf8')),
    );
    await h.captureSurface(surface);
  });
});

test('Base scans have zero unexpected sentinel findings', () => {
  expect(h.leaks).toBe(0);
});

redactionTest('Base known cookie-ID log finding is absent', () => {
  expect(h.knownFindings).toBe(0);
});
test('S4 removed processing call cannot contact providers during authentication failures', () => {
  expect(localResult.isError).toBe(true);
});
test('C5 fake rejects a search without cookies', async () => {
  await h.mode({ mode: 'healthy', reset: true });
  expect((await h.request('/eapi/book/search', { message: 'no-cookie' }, true)).status).toBe(401);
});

sourceSurvivalTest('S4 Library Genesis search survives authentication failures', () => {
  expect(alternateResult.error).toBeUndefined();
  expect(alternateResult.books[0]).toMatchObject({
    title: 'Rehearsal LibGen fixture',
    source: 'libgen',
    md5: '0123456789abcdef0123456789abcdef',
  });
});
test('S6 healthy Library Genesis search reaches the real parser and fixture', async () => {
  await h.scenario(
    'S6',
    async (connect) => {
      const c = await connect();
      const result = await h.call(c, 'search_multi_source', {
        query: 'fixture',
        source: 'libgen',
        count: 1,
      });
      expect(result.books[0]).toMatchObject({
        title: 'Rehearsal LibGen fixture',
        source: 'libgen',
        md5: '0123456789abcdef0123456789abcdef',
      });
      expect((await h.stats()).calls['/libgen/index.php']).toBe(1);
      expect((await h.stats()).logins).toBe(0);
    },
    { libgen: true },
  );
});

const breakerTest = expectedFixes.has('breaker') ? test : test.failing;
breakerTest(
  'S7 transient EAPI outage opens only EAPI; Library Genesis survives and saved processing is refused',
  async () => {
    await h.scenario(
      'S7',
      async (connect) => {
        const started = performance.now();
        const c = await connect();
        const search = await h.call(c, 'search_books', { query: 'warm-session' });
        expect((await h.stats()).logins).toBe(1);
        await h.mode({ mode: 'server503' });
        const warmed = performance.now();
        // Independent warmed failures can overlap; await all five before probing OPEN.
        const replies = await Promise.all(
          Array.from({ length: 5 }, () => h.call(c, 'search_books', { query: 'outage' }, true)),
        );
        for (const reply of replies) {
          expect(reply.error.message).toMatch(/503/);
          expect(reply.error.message).not.toMatch(/authentication|rejected the login/i);
        }
        const failed = performance.now();
        const before = await h.stats();
        expect(before.logins).toBe(1);
        expect(before.calls['/eapi/book/search']).toBe(6); // warm call + five outages
        const blocked = await h.call(c, 'search_books', { query: 'blocked' }, true);
        expect(blocked.error.message).toMatch(/circuit breaker.*open/i);
        expect(await h.stats()).toEqual(before);
        const alternate = await h.call(c, 'search_multi_source', {
          query: 'fixture',
          source: 'libgen',
          count: 1,
        });
        expect(alternate.books[0]).toMatchObject({
          title: 'Rehearsal LibGen fixture',
          source: 'libgen',
        });
        const beforeRefusal = await h.stats();
        const refused = await h.call(
          c,
          'download_book_to_file',
          {
            bookDetails: search.books[0],
            outputDir: h.downloads,
            process_for_rag: true,
          },
          true,
        );
        expect(refused.error.message).toMatch(/text processing was removed in 2\.0/i);
        expect(await h.stats()).toEqual(beforeRefusal);
        expect(await readdir(h.downloads)).toEqual([]);
        const after = await h.stats();
        expect(after.logins).toBe(1);
        expect(after.calls['/eapi/book/search']).toBe(6);
        expect(after.calls['/libgen/index.php']).toBe(1);
        h.scan(await c.listTools());
        h.note('S7', {
          outage: 'HTTP 503 (non-auth)',
          breaker: 'EAPI OPEN after five failures',
          blockedCallDispatched: false,
          savedProcessing: 'refused before authentication or transfer; no files created',
          alternateSources: 'Library Genesis works',
          toolsList: 'works',
          timingMs: {
            connectAndWarm: Math.round(warmed - started),
            fiveOutages: Math.round(failed - warmed),
            blockedProbeAndFallback: Math.round(performance.now() - failed),
          },
        });
      },
      { libgen: true },
    );
  },
);
