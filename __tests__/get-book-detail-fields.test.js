import { describe, expect, test, beforeAll } from '@jest/globals';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { AcquisitionTools } from '../dist/lib/acquisition-tools.js';

// Drives get_book end to end from an offline EAPI-shaped reply (#256): the real
// Python normalizer builds the search row, the real get_book_metadata_complete
// extracts the detail through a stub client, and AcquisitionTools merges them.
const root = process.cwd();
const fixtures = JSON.parse(
  readFileSync(path.join(root, '__tests__/fixtures/eapi-book-detail.json'), 'utf8'),
);
const env = { ZLIBRARY_EMAIL: 'offline@example.invalid', ZLIBRARY_PASSWORD: 'password' };
const RETIRED = ['terms', 'booklists', 'ipfs_cids'];

function bridge(reply) {
  const script = `
import asyncio, json, sys
import python_bridge
from zlibrary.eapi import normalize_eapi_book
reply = json.load(sys.stdin)
class OfflineClient:
    async def get_book_info(self, book_id, book_hash):
        return reply
python_bridge._eapi_client = OfflineClient()
book = reply["book"]
detail = asyncio.run(python_bridge.get_book_metadata_complete(str(book["id"]), book["hash"]))
print(json.dumps({"row": normalize_eapi_book(book), "detail": detail}))
`;
  return JSON.parse(
    execFileSync(path.join(root, '.venv/bin/python'), ['-c', script], {
      encoding: 'utf8',
      input: JSON.stringify(reply),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        PATH: process.env.PATH,
        PYTHONPATH: [path.join(root, 'lib'), path.join(root, 'zlibrary/src'), root].join(
          path.delimiter,
        ),
      },
    }),
  );
}

async function getBook(reply) {
  const { row, detail } = bridge(reply);
  const tools = new AcquisitionTools(
    async (op) => (op === 'get_book_metadata_complete' ? detail : { books: [row] }),
    env,
  );
  const search = await tools.call('search', { query: 'offline', sources: ['zlibrary'] });
  return tools.call('get_book', { ref: search.rows[0].ref });
}

describe('get_book detail fields from an EAPI-shaped reply', () => {
  let book;
  beforeAll(async () => {
    book = await getBook(fixtures.complete);
  });

  test.each([
    ['isbn', '978-0-87220-070-5'],
    ['series', 'Hackett Classics'],
    ['edition', 'Revised'],
    ['translator', 'T. F. Geraets'],
    ['categories', [{ name: 'Philosophy' }, { name: 'Logic' }]],
    ['rating', { value: 4.6, count: 52 }],
    ['description', 'Part one of the Encyclopaedia of the Philosophical Sciences.'],
    ['identifiers', { id: '25601', hash: 'hash25601' }],
    ['url', '/book/25601/hash25601/the-encyclopaedia-logic.html'],
  ])('%s', (field, expected) => {
    expect(book[field]).toEqual(expected);
  });

  test('evidence.detail names exactly the fields the detail reply supplied', () => {
    expect([...book.evidence.detail].sort()).toEqual([
      'categories',
      'description',
      'edition',
      'isbn_13',
      'quality_score',
      'rating',
      'series',
      'translator',
    ]);
  });

  test('no retired field is returned or claimed as evidence', () => {
    for (const field of RETIRED) {
      expect(book).not.toHaveProperty(field);
      expect(book.evidence.detail).not.toContain(field);
    }
  });
});

test('fields the EAPI reply leaves empty stay absent from get_book', async () => {
  const book = await getBook(fixtures.sparse);
  for (const field of [
    'isbn',
    'series',
    'edition',
    'translator',
    'categories',
    'rating',
    'description',
    'description_truncated',
    ...RETIRED,
  ])
    expect(book).not.toHaveProperty(field);
  expect(book.evidence.detail).toEqual([]);
  expect(book.title).toBe('An Uncatalogued Pamphlet');
});
