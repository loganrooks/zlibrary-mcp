import { afterAll, beforeAll, expect, test } from '@jest/globals';
import { readFile, realpath, writeFile } from 'node:fs/promises';
import path from 'node:path';
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
    const search = await h.call(c, 'search', { sources: ['zlibrary'], query: 'sequential' });
    expect(search.rows).toHaveLength(1);
    expect(search.rows[0].title).toBe('Rehearsal sequential');
    const metadata = await h.call(c, 'get_book', {
      ref: search.rows[0].ref,
    });
    expect(metadata.description).toBe('Details for rehearsal book 101');
    const limits = await h.call(c, 'get_limits', { mode: 'live', sources: ['zlibrary'] });
    expect(limits.sources.zlibrary.limit).toMatchObject({ per_day: 10, remaining: 7 });
    const result = await h.call(c, 'download', {
      ref: search.rows[0].ref,
      output_dir: h.downloads,
    });
    const file = await realpath(result.path);
    expect(file.startsWith((await realpath(h.downloads)) + path.sep)).toBe(true);
    expect(await readFile(file, 'utf8')).toBe('Offline rehearsal book 101.\n');
    const history = await h.call(c, 'get_history', { limit: 1 });
    const historyDetail = await h.call(c, 'get_book', { ref: history.rows[0].ref });
    expect(historyDetail.identifiers.id).toBe('101');
  });
});

test('S2 five concurrent slow/fast calls correlate; count logins independently', async () => {
  await h.scenario('S2', async (connect) => {
    const c = await connect();
    const queries = ['slow-first', 'fast-second', 'slow-third', 'fast-fourth', 'fast-fifth'];
    const replies = await Promise.all(queries.map((query) => h.call(c, 'search', { query, sources: ['zlibrary'] })));
    replies.forEach((reply, i) => expect(reply.rows[0].title).toBe(`Rehearsal ${queries[i]}`));
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
let alternateDetail;
loginTest('S2 session reuse: exactly one login (expected failure on master)', () => {
  expect(concurrentLogins).toBe(1);
});

test('S3 two independent server processes each return their own results', async () => {
  await h.scenario('S3', async (connect) => {
    const clients = await Promise.all([connect(), connect()]);
    const replies = await Promise.all(
      clients.map((c, i) => h.call(c, 'search', { sources: ['zlibrary'], query: `host-${i}` })),
    );
    replies.forEach((r, i) => expect(r.rows[0].title).toBe(`Rehearsal host-${i}`));
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
        const reply = { error: (await h.call(c, 'get_limits', { mode: 'live', sources: ['zlibrary'] })).sources.zlibrary.error };
        expect(['auth_failed', 'breaker_open']).toContain(reply.error.code);
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
      const blocked = { error: (await h.call(c, 'get_limits', { mode: 'live', sources: ['zlibrary'] })).sources.zlibrary.error };
      expect(blocked.error.code).toBe('breaker_open');
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
        'search',
        { query: 'fixture', sources: ['libgen'], limit: 1 },
        true,
      );
      if (!alternateResult.error) {
        alternateDetail = await h.call(c, 'get_book', { ref: alternateResult.rows[0].ref });
      }
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
    expect(surface.some((t) => t.name === 'search' && t.arguments.includes('query'))).toBe(
      true,
    );
    expect(surface.map(t => t.name)).toEqual(['download', 'get_book', 'get_history', 'get_limits', 'search']);
    expect(JSON.stringify(listed).length).toBeLessThan(6500);
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
  expect(alternateDetail.identifiers.md5).toBe('0123456789abcdef0123456789abcdef');
  expect(alternateResult.rows[0]).toMatchObject({
    title: 'Rehearsal LibGen fixture',
    source: 'libgen',
  });
});
test('S6 healthy Library Genesis search reaches the real parser and fixture', async () => {
  await h.scenario(
    'S6',
    async (connect) => {
      const c = await connect();
      const result = await h.call(c, 'search', {
        query: 'fixture',
        sources: ['libgen'],
        limit: 1,
      });
      expect(result.rows[0]).toMatchObject({
        title: 'Rehearsal LibGen fixture',
        source: 'libgen',
          });
      const detail = await h.call(c, 'get_book', { ref: result.rows[0].ref });
      expect(detail.identifiers.md5).toBe('0123456789abcdef0123456789abcdef');
      expect((await h.stats()).calls['/libgen/index.php']).toBe(1);
      expect((await h.stats()).logins).toBe(0);
    },
    { libgen: true },
  );
});

test('I1 five-tool download repeat hashes disk and avoids authentication and transfer', async () => {
  await h.scenario('I1', async connect => {
    const c = await connect();
    const found = await h.call(c, 'search', { query: 'receipt', sources: ['zlibrary'], limit: 1 });
    const args = { ref: found.rows[0].ref, output_dir: h.downloads };
    const first = await h.call(c, 'download', args);
    const before = await h.stats();
    const repeat = await h.call(c, 'download', args);
    expect(repeat).toMatchObject({ path: first.path, transfer_skipped: true, reused: false, verified: 'sha256' });
    expect(await h.stats()).toEqual(before);
    const record = JSON.parse(await readFile(repeat.record, 'utf8'));
    expect(record).toMatchObject({ state: 'complete', record_version: 1, identifiers: { id: '101', hash: 'hash101' } });
  });
});
test('I2 lost-reply cursor replay repeats position and local limits cost no upstream call', async () => {
  await h.scenario('I2', async connect => {
    const c = await connect();
    const before = await h.stats();
    await h.call(c, 'get_limits', {});
    const missing = await h.call(c, 'search', { query: 'cursor' }, true);
    expect(missing.error.code).toBe('sources_required');
    expect(await h.stats()).toEqual(before);
    const first = await h.call(c, 'search', { query: 'cursor', sources: ['zlibrary'], limit: 1 });
    const cursor = first.next_cursor;
    const lost = await h.call(c, 'search', { cursor });
    const replay = await h.call(c, 'search', { cursor });
    expect(replay.rows.map(r => r.title)).toEqual(lost.rows.map(r => r.title));
    const at = await h.stats();
    const invalid = await h.call(c, 'search', { cursor, limit: 2 }, true);
    expect(invalid.error.code).toBe('invalid_argument');
    expect(await h.stats()).toEqual(at);
  });
});
