import { beforeEach, afterEach, test, expect } from '@jest/globals';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { tasks, arms } from './tasks.js';
import { scoreTask } from './oracles.js';

let downloads;
beforeEach(async () => {
  downloads = await mkdtemp(path.join(os.tmpdir(), 'eval-t9-'));
});
afterEach(async () => {
  await rm(downloads, { recursive: true, force: true });
});
for (const build of ['A', 'B']) {
  for (const source of ['libgen', 'zlibrary']) {
    const ids = source === 'libgen' ? ['303', '304', '305'] : ['209', '210', '211'];
    const rows = ['Pride and Prejudice', 'Middlemarch', 'On Liberty'].map((title, i) => ({
      id: ids[i],
      title,
      source,
      ...(build === 'B' ? { ref: `observed-${source}-${ids[i]}` } : {}),
    }));
    const search = (items) => ({
      name: build === 'A' ? 'search_multi_source' : 'search',
      args:
        build === 'A'
          ? { query: 'author/title variant', source }
          : { query: 'author/title variant', sources: [source] },
      reply: { structuredContent: build === 'A' ? { books: items } : { rows: items } },
    });
    const download = async (row) => {
      const file = path.join(downloads, `${row.id}.pdf`);
      await writeFile(file, `%PDF-1.4\nSynthetic fixture ${row.id}\n`);
      return {
        name: build === 'A' ? 'download_book_to_file' : 'download',
        args: build === 'A' ? { bookDetails: row } : { ref: row.ref },
        selected: row,
        observedSelection: true,
        reply: { structuredContent: { path: file } },
      };
    };
    const score = (trace) =>
      scoreTask({
        task: tasks.find((t) => t.id === 'T9'),
        arm: arms.find((a) => a.id === build),
        trace,
        downloads,
      });
    for (const interleaved of [false, true])
      test(`EVAL-C1-03 ${build}/${source} accepts three distinct matching searches ${interleaved ? 'interleaved' : 'up front'}`, async () => {
        const ds = await Promise.all(rows.map(download));
        const trace = interleaved
          ? rows.flatMap((r, i) => [search([r]), ds[i]])
          : [...rows.map((r) => search([r])), ...ds];
        expect(await score(trace)).toMatchObject({ success: true, wrong: [] });
      });
    for (const [name, searches] of [
      ['one unrelated empty search and old selections', () => [search([])]],
      ['one broad search returning all titles', () => [search(rows)]],
      ['repeated Pride-only searches', () => rows.map(() => search([rows[0]]))],
      ['downloads before matching searches', () => rows.map((r) => search([r]))],
      [
        'correct titles but different row identities',
        () => rows.map((r) => search([{ ...r, id: `other-${r.id}`, ref: `other-${r.ref}` }])),
      ],
      [
        'failed search replies with rows',
        () => rows.map((r) => ({ ...search([r]), error: 'search failed' })),
      ],
    ])
      test(`EVAL-C1-03 ${build}/${source} rejects ${name}`, async () => {
        const ds = await Promise.all(rows.map(download));
        const trace = name.startsWith('downloads before')
          ? [...ds, ...searches()]
          : [...searches(), ...ds];
        const result = await score(trace);
        expect(result.success).toBe(false);
        expect(result.files).toHaveLength(3);
        expect(result.wrong.some((w) => w.reason.includes('same-task search'))).toBe(true);
      });
    test(`EVAL-C1-03 ${build}/${source} pairs broad and narrow calls without greedy rejection`, async () => {
      const ds = await Promise.all(rows.map(download));
      expect(
        await score([search(rows.slice(0, 2)), search([rows[0]]), search([rows[2]]), ...ds]),
      ).toMatchObject({ success: true, wrong: [] });
    });
    for (const mutation of [
      'wrong bytes',
      'missing download',
      'extra duplicate download',
      'unobserved selection',
    ])
      test(`EVAL-C1-03 ${build}/${source} retains ${mutation} rejection after valid searches`, async () => {
        const ds = await Promise.all(rows.map(download));
        if (mutation === 'wrong bytes')
          await writeFile(
            ds[0].reply.structuredContent.path,
            '%PDF-1.4\nSynthetic fixture wrong\n',
          );
        if (mutation === 'missing download') ds.pop();
        if (mutation === 'extra duplicate download') ds.push(ds[0]);
        if (mutation === 'unobserved selection') ds[0].observedSelection = false;
        expect((await score([...rows.map((r) => search([r])), ...ds])).success).toBe(false);
      });
  }
}
