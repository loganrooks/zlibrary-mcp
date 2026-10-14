import { jest, beforeEach, afterEach, test, expect } from '@jest/globals';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { CallToolResultSchema } from '@modelcontextprotocol/sdk/types.js';

// The result tests keep the API facade and SDK real, replacing only the
// subprocess/environment boundary. One dispatch-only test supplies the missing
// recent-books export so its registration can be checked before #171 lands.
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
  get_book_metadata: [
    { bookId: '1', bookHash: 'offline' },
    'get_book_metadata_complete',
    { title: 'Offline' },
  ],
  search_by_term: [{ term: 'offline' }, 'search_by_term_bridge', { books: [] }],
  search_by_author: [{ author: 'offline' }, 'search_by_author_bridge', { books: [] }],
  fetch_booklist: [
    { booklistId: '1', booklistHash: 'offline', topic: 'offline' },
    'fetch_booklist_bridge',
    { books: [] },
  ],
  search_advanced: [
    { query: 'offline' },
    'search_advanced',
    { exact_matches: [], fuzzy_matches: [] },
  ],
  search_multi_source: [
    { query: 'offline', source: 'libgen' },
    'search_multi_source',
    { books: [] },
  ],
};

// Measured at ec91a32 with SDK 1.30.0; each tool gets 10% headroom.
const characterBaselines = {
  search_books: 1588,
  full_text_search: 1517,
  get_download_history: 542,
  get_download_limits: 417,
  get_recent_books: 585,
  download_book_to_file: 1097,
  process_document_for_rag: 733,
  get_book_metadata: 1323,
  search_by_term: 1265,
  search_by_author: 1346,
  fetch_booklist: 848,
  search_advanced: 1092,
  search_multi_source: 993,
};

let client;
let server;
let advertised;
async function connectServer(apiOverrides) {
  await client?.close();
  await server?.close();
  jest.resetModules();
  jest.unstable_unmockModule('../lib/zlibrary-api.js');
  if (apiOverrides) {
    const actualApi = await import('../dist/lib/zlibrary-api.js');
    jest.unstable_mockModule('../lib/zlibrary-api.js', () => ({ ...actualApi, ...apiOverrides }));
  }
  const { createServer } = await import('../dist/index.js');
  expect(typeof createServer).toBe('function');
  server = createServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: 'surface-oracle', version: '1.0.0' });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  advertised = await client.listTools();
}
beforeEach(async () => {
  runBridge.mockReset();
  await connectServer();
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
    expect(JSON.stringify(tool).length).toBeLessThanOrEqual(
      Math.ceil(characterBaselines[tool.name] * 1.1),
    );
  }
});

async function callAdvertised(name, payloadOverride) {
  // A missing or miswired registration must not pass merely because an error
  // envelope is schema-valid: require successful dispatch to the real facade.
  expect(advertised.tools.some((tool) => tool.name === name)).toBe(true);
  const [args, operation, defaultPayload] = cases[name];
  const payload = payloadOverride ?? defaultPayload;
  runBridge.mockResolvedValue([
    JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(payload) }] }),
  ]);
  const result = await client.callTool({ name, arguments: args });
  expect(CallToolResultSchema.safeParse(result).success).toBe(true);
  expect(result.isError).not.toBe(true);
  expect(result.content).toEqual([{ type: 'text', text: JSON.stringify(payload) }]);
  expect(runBridge).toHaveBeenCalledTimes(1);
  expect(runBridge.mock.calls[0][1].args[0]).toBe(operation);
}

for (const name of Object.keys(cases)) {
  if (name !== 'get_recent_books' && name !== 'get_download_history') {
    test(`${name} dispatches and returns an SDK-valid result`, () => callAdvertised(name));
  }
}

test('get_recent_books registration reaches the intended handler exactly once', async () => {
  // Only the absent API export is supplied here. A miswired/removed production
  // registration must fail this ordinary test, never be inverted by .failing.
  const recentProbe = jest.fn(async (args, options) => {
    await runBridge(
      'python_bridge.py',
      { args: ['get_recent_books', JSON.stringify(args)] },
      options,
    );
    return { books: [] };
  });
  await connectServer({ getRecentBooks: recentProbe });
  await callAdvertised('get_recent_books');
  expect(recentProbe).toHaveBeenCalledTimes(1);
  expect(recentProbe).toHaveBeenCalledWith({ count: 1 }, { signal: expect.any(AbortSignal) });
});

test('get_download_history dispatches exactly once to the correct operation', () =>
  // An object avoids the independent #197 array-result defect. The real facade
  // still has to reach the runner with the history operation, not another one.
  callAdvertised('get_download_history', { books: [] }));

async function settledCall(name) {
  const [args, , payload] = cases[name];
  runBridge.mockResolvedValue([
    JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(payload) }] }),
  ]);
  return client.callTool({ name, arguments: args }).then(
    (result) => ({ result }),
    (error) => ({ error: { code: error.code, message: error.message } }),
  );
}

// https://github.com/rookslog/zlibrary-mcp/issues/171 — invert only this exact
// defect. A different error or a successful call passes the negated matcher,
// which makes test.failing itself RED instead of accepting the new regression.
test.failing('get_recent_books has only the known missing-export defect', async () => {
  expect(await settledCall('get_recent_books')).not.toEqual({
    result: {
      content: [{ type: 'text', text: 'Error: zlibraryApi.getRecentBooks is not a function' }],
      isError: true,
    },
  });
});

// https://github.com/rookslog/zlibrary-mcp/issues/197 — only the SDK's array
// structuredContent rejection is expected; dispatch is checked above normally.
test.failing('get_download_history has only the known array-result defect', async () => {
  expect(await settledCall('get_download_history')).not.toEqual({
    error: {
      code: -32602,
      message: expect.stringMatching(/structuredContent[\s\S]*received array/),
    },
  });
});
