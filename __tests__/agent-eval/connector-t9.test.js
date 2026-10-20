import { beforeEach, afterEach, test, expect } from '@jest/globals';
import { mkdtemp, writeFile, rm, readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';
import ts from 'typescript';
import { z } from 'zod';
import { root } from './server.js';
import os from 'node:os';
import path from 'node:path';
import { tasks, arms } from './tasks.js';
import { scoreTask } from './oracles.js';

let downloads;
// Read, but never start, the actual current A declarations. Evaluating the
// isolated Zod initializer has no server/provider side effects. On B integration
// this A-only static check is inapplicable; the pinned A runtime gate is separate.
const sourceText = await readFile(path.join(root, 'src/index.ts'), 'utf8');
const parsed = ts.createSourceFile('index.ts', sourceText, ts.ScriptTarget.Latest, true);
const schemas = {};
for (const statement of parsed.statements)
  if (ts.isVariableStatement(statement))
    for (const declaration of statement.declarationList.declarations)
      if (
        ['SearchBooksParamsSchema', 'SearchMultiSourceParamsSchema'].includes(
          declaration.name.getText(parsed),
        )
      )
        schemas[declaration.name.getText(parsed)] = vm.runInNewContext(
          declaration.initializer.getText(parsed),
          { z },
        );
const catalogue = JSON.parse(
  execFileSync(
    path.join(root, '.venv/bin/python'),
    [
      '-B',
      '-c',
      `import sys,json;sys.path.insert(0,${JSON.stringify(path.join(root, '__tests__/rehearsal'))});from fake_catalogue import select;print(json.dumps({s:[select(t,source=s)[0] for t in ['Pride and Prejudice','Middlemarch','On Liberty']] for s in ['zlibrary','libgen']}))`,
    ],
    { encoding: 'utf8', env: { PATH: process.env.PATH, PYTHONDONTWRITEBYTECODE: '1' } },
  ),
);
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
      ...catalogue[source][i],
      id: ids[i],
      title,
      source,
      ...(build === 'B' ? { ref: `observed-${source}-${ids[i]}` } : {}),
    }));
    const search = (items) => ({
      name:
        build === 'A' ? (source === 'zlibrary' ? 'search_books' : 'search_multi_source') : 'search',
      args:
        build === 'A'
          ? {
              query: items.length === 1 ? items[0].title : 'Jane Austen',
              ...(source === 'libgen' ? { source } : {}),
            }
          : { query: items.length === 1 ? items[0].title : 'Jane Austen', sources: [source] },
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
        if (build === 'A' && schemas.SearchBooksParamsSchema) {
          for (const c of trace.filter((c) => c.name.startsWith('search'))) {
            const schema =
              c.name === 'search_books'
                ? schemas.SearchBooksParamsSchema
                : schemas.SearchMultiSourceParamsSchema;
            expect(schema.safeParse(c.args).success).toBe(true);
            expect(c.args.query).toBe(c.reply.structuredContent.books[0].title);
          }
          expect(
            schemas.SearchMultiSourceParamsSchema.safeParse({
              query: 'Pride and Prejudice',
              source: 'zlibrary',
            }).success,
          ).toBe(false);
        }
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
