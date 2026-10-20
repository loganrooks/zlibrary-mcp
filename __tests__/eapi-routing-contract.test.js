import { expect, test } from '@jest/globals';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { needsEapi } from '../lib/eapi-session.js';

test('Node and Python need-auth routing share the same independent case table', () => {
  const cases = [
    ['search_multi_source', { source: 'zlibrary' }, false],
    ...['libgen', 'annas', 'annas_archive', 'LiBgEn', 'ANNAS_ARCHIVE'].map((source) => [
      'download_book',
      { book_details: { source } },
      false,
    ]),
    ...['', 'zlibrary', 'unknown'].map((source) => [
      'download_book',
      { book_details: { source } },
      true,
    ]),
    ['download_book', {}, true],
    ...[
      'search',
      'full_text_search',
      'get_download_history',
      'get_download_limits',
      'get_book_metadata_complete',
      'search_by_term_bridge',
      'search_by_author_bridge',
      'search_advanced',
      'fetch_booklist_bridge',
      'get_recent_books',
      'eapi_health_check',
    ].map((name) => [name, {}, true]),
  ];
  const root = process.cwd();
  const output = execFileSync(
    path.join(root, '.venv/bin/python'),
    [
      '-c',
      'import json,sys; from python_bridge import _requires_eapi_client; cases=json.load(sys.stdin); print(json.dumps([_requires_eapi_client(name,args) for name,args,_ in cases]))',
    ],
    {
      encoding: 'utf8',
      input: JSON.stringify(cases),
      env: {
        PATH: process.env.PATH,
        PYTHONPATH: [path.join(root, 'lib'), path.join(root, 'zlibrary/src'), root].join(
          path.delimiter,
        ),
      },
    },
  );
  const expected = cases.map(([_name, _args, want]) => want);
  expect(JSON.parse(output)).toEqual(expected);
  expect(cases.map(([name, args]) => needsEapi(name, args))).toEqual(expected);
});
