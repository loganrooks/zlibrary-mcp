import { jest, test, expect, beforeEach, afterEach } from '@jest/globals';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { AjvJsonSchemaValidator } from '@modelcontextprotocol/sdk/validation/ajv';
import { ErrorEnvelopeSchema } from '../dist/lib/tool-errors.js';
const run = jest.fn();
jest.unstable_mockModule('../lib/venv-manager.js', () => ({ getManagedPythonPath: async () => '/offline/python' }));
jest.unstable_mockModule('../lib/python-runner.js', () => ({ runPythonBridge: run, LONG_BRIDGE_TIMEOUT_MS: 2400000 }));
const { createServer } = await import('../dist/index.js');
let server, client, previous;
const book = { id: '1', hash: 'abc', title: 'Book', author: 'Author', extension: 'pdf', source: 'zlibrary' };
const encode = value => [JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(value) }] })];
beforeEach(async () => {
  previous = { ...process.env };
  process.env.ZLIBRARY_SESSION_MODE = 'per-call';
  process.env.ZLIBRARY_EMAIL = 'offline@example.invalid'; process.env.ZLIBRARY_PASSWORD = 'offline-password';
  process.env.RETRY_MAX_RETRIES = '3';
  run.mockReset();
  server = createServer(); client = new Client({ name: 'boundary', version: '1' });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([client.connect(a), server.connect(b)]);
});
afterEach(async () => { await client.close(); await server.close(); process.env = previous; });
const call = async (name, args = {}) => (await client.callTool({ name, arguments: args })).structuredContent;
test('tools/list stays under 6500 characters with success/error output schemas', async () => {
  const list = await client.listTools();
  expect(JSON.stringify(list).length).toBeLessThan(6500);
  expect(list.tools.map(t => t.name)).toEqual(['search', 'get_book', 'download', 'get_limits', 'get_history']);
  for (const t of list.tools) expect(t.outputSchema.oneOf).toHaveLength(2);
});
test('search forwards all normalized filters, author, limit and page through the real facade', async () => {
  run.mockResolvedValue(encode({ books: [book] }));
  const result = await call('search', { query: 'title', author: 'Writer', sources: ['zlibrary'], exact: true, year_from: 1900, year_to: 2000, languages: ['english'], formats: ['pdf'], limit: 3 });
  expect(JSON.parse(run.mock.calls[0][1].args[1])).toEqual({ query: 'title', author: 'Writer', exact: true, from_year: 1900, to_year: 2000, languages: ['english'], extensions: ['pdf'], count: 3, page: 1 });
  expect(result.rows[0]).toMatchObject({ title: 'Book', source: 'zlibrary' });
  expect(result.rows[0].id).toBeUndefined();
});
test('get_book and download rehydrate only held refs, and fresh downloads use the guarded bridge path', async () => {
  run.mockImplementation(async (_script, options) => encode(options.args[0] === 'search' ? { books: [book] } : options.args[0] === 'get_book_metadata_complete' ? { description: 'Details' } : { path: '/offline/book.pdf', bytes: 12, verified: 'sha256', reused: false, transfer_skipped: false, record: '/offline/book.pdf.acq.json' }));
  const ref = (await call('search', { query: 'Book', sources: ['zlibrary'] })).rows[0].ref;
  expect((await call('get_book', { ref })).description).toBe('Details');
  const download = await call('download', { ref, output_dir: '/offline', filename: 'chosen.epub' });
  expect(download.verified).toBe('sha256');
  expect(run.mock.calls[2][1].args[0]).toBe('acquire_book');
  expect(JSON.parse(run.mock.calls[2][1].args[1])).toMatchObject({ book_details: book, output_dir: '/offline', filename: 'chosen.epub', request: { ref, query: 'Book' } });
});
test('history pagination forwards the page and replay does not consume it', async () => {
  run.mockResolvedValue(encode([book]));
  const first = await call('get_history', { limit: 1 });
  await call('get_history', { cursor: first.next_cursor });
  await call('get_history', { cursor: first.next_cursor });
  expect(run.mock.calls.map(c => JSON.parse(c[1].args[1]))).toEqual([{ count: 1, page: 1 }, { count: 1, page: 2 }, { count: 1, page: 2 }]);
});
test('local mode makes no bridge call, live mode translates quota fields', async () => {
  await call('get_limits'); expect(run).not.toHaveBeenCalled();
  run.mockResolvedValue(encode({ daily_limit: 10, downloads_today: 3, daily_remaining: 7 }));
  expect((await call('get_limits', { mode: 'live', sources: ['zlibrary'] })).sources.zlibrary.limit).toMatchObject({ per_day: 10, used_today: 3, remaining: 7 });
});
test('download bridge failure never automatically retries or exposes stderr secrets', async () => {
  run.mockResolvedValueOnce(encode({ books: [book] }));
  const ref = (await call('search', { query: 'Book', sources: ['zlibrary'] })).rows[0].ref;
  run.mockRejectedValue(Object.assign(new Error('provider SECRET'), { stderr: JSON.stringify({ error: 'SECRET', details: { provider: 'zlibrary', reason: 'read_timeout' } }) }));
  const result = await call('download', { ref });
  expect(result.error.retry).toBe('may_spend_quota');
  expect(ErrorEnvelopeSchema.safeParse(result).success).toBe(true);
  expect(JSON.stringify(result)).not.toContain('SECRET');
  expect(run).toHaveBeenCalledTimes(2); // one search, one transfer attempt, no automatic quota spend
});

test('error envelopes are validated independently of SDK isError bypass', async () => {
  const validator = new AjvJsonSchemaValidator();
  const list = await client.listTools();
  const result = await client.callTool({ name: 'search', arguments: { limit: 0 } });
  const validate = validator.getValidator(list.tools.find(t => t.name === 'search').outputSchema);
  expect(validate(result.structuredContent).valid).toBe(true);
  expect(validate({ error: { code: 'invalid_argument' } }).valid).toBe(false);
  expect(ErrorEnvelopeSchema.safeParse({ error: { ...result.structuredContent.error, retry: 'probably' } }).success).toBe(false);
});
