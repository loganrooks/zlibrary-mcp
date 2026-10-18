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
const breakerTest = expectedFixes.has('breaker') ? test : test.failing;
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

test('S4 EAPI outage opens EAPI breaker after five failures; listing survives', async () => {
  await h.scenario(
    'S4',
    async (connect) => {
      const c = await connect();
      await h.mode({ mode: 'unauthorized' });
      for (let i = 0; i < 5; i++) {
        const reply = await h.call(c, 'get_download_limits', {}, true);
        expect(reply.error.message).toMatch(/401|authentication/i);
      }
      const before = await h.stats();
      const blocked = await h.call(c, 'get_download_limits', {}, true);
      expect(blocked.error.message).toMatch(/circuit breaker.*open/i);
      expect(await h.stats()).toEqual(before);
      const file = path.join(h.downloads, 'local.txt');
      await writeFile(file, 'local reader survives');
      const local = await h.call(c, 'process_document_for_rag', { file_path: file }, true);
      localResult = local;
      h.scan(await c.listTools());
      expect((await c.listTools()).tools.length).toBeGreaterThan(0);
      alternateResult = await h.call(
        c,
        'search_multi_source',
        { query: 'fixture', source: 'libgen', count: 1 },
        true,
      );
      h.note('S4', {
        breaker: 'OPEN after five failures',
        localBridge: local.error ? 'blocked' : 'works',
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
breakerTest('S4 local document processing is independent of EAPI breaker', () => {
  expect(localResult.error).toBeUndefined();
});
test('C5 fake rejects a search without cookies', async () => {
  await h.mode({ mode: 'healthy', reset: true });
  expect((await h.request('/eapi/book/search', { message: 'no-cookie' }, true)).status).toBe(401);
});

breakerTest('S4 Library Genesis search is independent of EAPI breaker', () => {
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
