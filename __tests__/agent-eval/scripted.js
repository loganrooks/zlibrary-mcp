import assert from 'node:assert/strict';
import { dataOf, rowsOf, isGraver, isCampbell } from './oracles.js';

// This is a fixture/oracle exerciser, NOT an agent-performance result.
export async function scriptedTask(s, task, context) {
  const call = async (name, args = {}) => dataOf(await s.call(name, args));
  const search = async (query, source = 'zlibrary', extra = {}) =>
    rowsOf(
      await call(
        source === 'libgen' ? 'search_multi_source' : 'search_books',
        source === 'libgen'
          ? { query, source, count: 50, ...extra }
          : { query, count: 50, ...extra },
      ),
    );
  const download = async (row) =>
    call('download_book_to_file', { bookDetails: row, outputDir: s.downloads });
  switch (task.id) {
    case 'T1': {
      const rows = await search('Persuasion', 'libgen');
      await download(rows.find((r) => r.extension === 'epub'));
      return 'Downloaded Persuasion EPUB.';
    }
    case 'T2': {
      const rows = await search('Seneca Letters');
      assert.equal(rows.length, 2);
      context.graver = rows.find(isGraver);
      context.campbell = rows.find(isCampbell);
      for (const row of rows) {
        const d = await call('get_book_metadata', {
          bookId: row.id,
          bookHash: row.hash,
          include: ['description'],
        });
        assert.match(d.description, /Translated by/);
      }
      return 'Margaret Graver and A. A. Long (2015); Robin Campbell (1969).';
    }
    case 'T3':
      await download(context.graver);
      return 'Downloaded the Graver translation.';
    case 'T4': {
      const limits = await call('get_download_limits');
      assert.equal(limits.daily_remaining, 2);
      return '2 Z-Library downloads remain. LibGen has no daily cap.';
    }
    case 'T5':
      return 'Full-text search is not available; these tools search catalogue metadata only.';
    case 'T6': {
      const rows = await search('Phenomenology', 'zlibrary', { count: 20 });
      assert.equal(rows.length, 20);
      return 'A has no cursor. Here are results 11–20.';
    }
    case 'T7': {
      const rows = rowsOf(await call('get_download_history', { count: 50 }));
      assert(rows.some((r) => r.title === 'Being and Time'));
      return 'Being and Time is in your downloaded account history.';
    }
    case 'T8':
      await download((await search('The Glass Orchard', 'libgen'))[0]);
      return 'Downloaded The Glass Orchard from LibGen.';
    case 'T9':
      for (const title of ['Pride and Prejudice', 'Middlemarch', 'On Liberty'])
        await download((await search(title, 'libgen'))[0]);
      return 'Downloaded all three titles.';
    case 'T10':
      return 'This interface cannot name the downloaded file seneca.pdf; filename is unavailable.';
    case 'T11': {
      const limits = await call('get_download_limits');
      assert.equal(limits.daily_remaining, 0);
      await search('Persuasion', 'libgen');
      return 'Quota is exhausted; LibGen has no cap. Search it instead.';
    }
    case 'T12': {
      const rows = rowsOf(
        await call('search_by_author', {
          author: 'Hannah Arendt',
          yearFrom: 1950,
          yearTo: 1965,
          count: 50,
        }),
      );
      assert.equal(rows.length, 3);
      return rows.map((r) => r.title).join('; ');
    }
  }
}
