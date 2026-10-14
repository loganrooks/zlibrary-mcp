import { jest, beforeEach, afterEach, test, expect } from '@jest/globals';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { CallToolResultSchema } from '@modelcontextprotocol/sdk/types.js';

// Only the subprocess/environment boundary is replaced: the API facade,
// registrations, SDK validation, serialization and client remain real.
const runBridge = jest.fn();
jest.unstable_mockModule('../lib/venv-manager.js', () => ({
  getManagedPythonPath: jest.fn().mockResolvedValue('/offline/python'),
}));
jest.unstable_mockModule('../lib/python-runner.js', () => ({
  runPythonBridge: runBridge,
  LONG_BRIDGE_TIMEOUT_MS: 2400000,
}));

const cases = {
  search_books: [{ query: 'offline' }, 'search', { books: [] }],
  full_text_search: [{ query: 'offline phrase' }, 'full_text_search', { books: [] }],
  get_download_history: [{ count: 1 }, 'get_download_history', []],
  get_download_limits: [{}, 'get_download_limits', { daily_limit: 10, remaining: 10 }],
  get_recent_books: [{ count: 1 }, 'get_recent_books', { books: [] }],
  download_book_to_file: [
    { bookDetails: { id: '1', hash: 'offline' } },
    'download_book',
    { file_path: '/offline/book.pdf' },
  ],
  process_document_for_rag: [
    { file_path: '/offline/book.pdf' },
    'process_document',
    { processed_file_path: '/offline/book.txt' },
  ],
  get_book_metadata: [{ bookId: '1', bookHash: 'offline' }, 'get_book_metadata_complete', { title: 'Offline' }],
  search_by_term: [{ term: 'offline' }, 'search_by_term_bridge', { books: [] }],
  search_by_author: [{ author: 'offline' }, 'search_by_author_bridge', { books: [] }],
  fetch_booklist: [{ booklistId: '1', booklistHash: 'offline', topic: 'offline' }, 'fetch_booklist_bridge', { books: [] }],
  search_advanced: [{ query: 'offline' }, 'search_advanced', { exact_matches: [], fuzzy_matches: [] }],
  search_multi_source: [{ query: 'offline', source: 'libgen' }, 'search_multi_source', { books: [] }],
};

// Measured at ec91a32 with SDK 1.30.0; each tool gets 10% headroom.
const characterBaselines = {
  search_books: 1588, full_text_search: 1517, get_download_history: 542,
  get_download_limits: 417, get_recent_books: 585, download_book_to_file: 1097,
  process_document_for_rag: 733, get_book_metadata: 1323, search_by_term: 1265,
  search_by_author: 1346, fetch_booklist: 848, search_advanced: 1092, search_multi_source: 993,
};

let client;
let server;
let advertised;
beforeEach(async () => {
  runBridge.mockReset();
  const { createServer } = await import('../dist/index.js');
  expect(typeof createServer).toBe('function');
  server = createServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: 'surface-oracle', version: '1.0.0' });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  advertised = await client.listTools();
});
afterEach(async () => {
  await client?.close();
  await server?.close();
  client = server = undefined;
});

test('tools/list has a fixture for every advertised tool and bounded schema cost', () => {
  // Catches new unexercised tools and schema/description bloat. Baseline from
  // #196: 13,346 total characters at f779ee3; ±10% is the accepted envelope.
  expect(advertised.tools.map((tool) => tool.name).sort()).toEqual(Object.keys(cases).sort());
  const total = JSON.stringify(advertised).length;
  expect(total).toBeGreaterThanOrEqual(Math.floor(13346 * 0.9));
  expect(total).toBeLessThanOrEqual(Math.ceil(13346 * 1.1));
  for (const tool of advertised.tools) {
    expect(JSON.stringify(tool).length).toBeLessThanOrEqual(Math.ceil(characterBaselines[tool.name] * 1.1));
  }
});

async function callAdvertised(name) {
  // A missing or miswired registration must not pass merely because an error
  // envelope is schema-valid: require successful dispatch to the real facade.
  expect(advertised.tools.some((tool) => tool.name === name)).toBe(true);
  const [args, operation, payload] = cases[name];
  runBridge.mockResolvedValue([JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(payload) }] })]);
  const result = await client.callTool({ name, arguments: args });
  expect(CallToolResultSchema.safeParse(result).success).toBe(true);
  expect(result.isError).not.toBe(true);
  expect(result.content).toEqual([{ type: 'text', text: JSON.stringify(payload) }]);
  expect(runBridge).toHaveBeenCalledTimes(1);
  expect(runBridge.mock.calls[0][1].args[0]).toBe(operation);
}

for (const name of Object.keys(cases)) {
  if (name === 'get_recent_books') {
    // https://github.com/rookslog/zlibrary-mcp/issues/171 — callable API export restored.
    test(`${name} dispatches and returns an SDK-valid result`, () => callAdvertised(name));
  } else if (name === 'get_download_history') {
    // https://github.com/rookslog/zlibrary-mcp/issues/197 — array structuredContent.
    test.failing(`${name} dispatches and returns an SDK-valid result`, () => callAdvertised(name));
  } else {
    test(`${name} dispatches and returns an SDK-valid result`, () => callAdvertised(name));
  }
}
