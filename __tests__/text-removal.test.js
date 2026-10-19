process.env.ZLIBRARY_SESSION_MODE = 'per-call';
import { jest, test, expect, afterEach } from '@jest/globals';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

const runBridge = jest.fn();
jest.unstable_mockModule('../lib/venv-manager.js', () => ({
  getManagedPythonPath: jest.fn().mockResolvedValue('/offline/python'),
}));
jest.unstable_mockModule('../lib/python-runner.js', () => ({
  runPythonBridge: runBridge, LONG_BRIDGE_TIMEOUT_MS: 2400000,
}));
const { createServer } = await import('../dist/index.js');
const api = await import('../dist/lib/zlibrary-api.js');
let client, server;
afterEach(async () => { await client?.close(); await server?.close(); runBridge.mockReset(); });
async function connect() {
  server = createServer();
  client = new Client({ name: 'saved-download-contract', version: '1' });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(b), client.connect(a)]);
}
const bookDetails = { id: '1', hash: 'offline' };
for (const legacy of [
  { process_for_rag: true }, { process_for_rag: 'false' }, { process_for_rag: null },
  { processed_output_format: 'txt' }, { processed_output_format: null },
  { process_for_rag: false, processed_output_format: 'markdown' },
]) {
  test(`SDK rejects saved processing request before any subprocess: ${JSON.stringify(legacy)}`, async () => {
    await connect();
    const result = await client.callTool({ name: 'download_book_to_file', arguments: { bookDetails, ...legacy } });
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toMatch(/text processing was removed in 2\.0/i);
    expect(runBridge).not.toHaveBeenCalled();
  });
  test(`direct API rejects saved request: ${JSON.stringify(legacy)}`, async () => {
    await expect(api.downloadBookToFile({ bookDetails, ...legacy })).rejects.toThrow(/text processing was removed in 2\.0/i);
    expect(runBridge).not.toHaveBeenCalled();
  });
}
test('SDK passes raw false to admission and ignores it without forwarding processing fields', async () => {
  await connect();
  runBridge.mockResolvedValue([JSON.stringify({ content: [{ type: 'text', text: JSON.stringify({ file_path: '/offline/book.pdf' }) }] })]);
  const result = await client.callTool({ name: 'download_book_to_file', arguments: { bookDetails, process_for_rag: false } });
  expect(result.isError).not.toBe(true);
  expect(result.structuredContent).toEqual({ file_path: '/offline/book.pdf' });
  expect(JSON.parse(runBridge.mock.calls[0][1].args[1])).toEqual({ book_details: bookDetails, output_dir: './downloads' });
});
test('unknown download fields fail before subprocess', async () => {
  await connect();
  const result = await client.callTool({ name: 'download_book_to_file', arguments: { bookDetails, typo: true } });
  expect(result.isError).toBe(true);
  expect(runBridge).not.toHaveBeenCalled();
});
test('tool listing no longer advertises processing and removed calls are unknown', async () => {
  await connect();
  const tools = await client.listTools();
  expect(tools.tools).toHaveLength(12);
  expect(JSON.stringify(tools)).not.toMatch(/process_for_rag|processed_output_format|process_document_for_rag/);
  const removed = await client.callTool({ name: 'process_document_for_rag', arguments: { file_path: '/offline/book.pdf' } });
  expect(removed.isError).toBe(true);
  expect(runBridge).not.toHaveBeenCalled();
});
test('stale backend processing bundles cannot escape the acquisition-only API', async () => {
  runBridge.mockResolvedValue([JSON.stringify({ content: [{ type: 'text', text: JSON.stringify({
    file_path: '/offline/book.pdf', processed_file_path: '/offline/body.txt',
  }) }] })]);
  await expect(api.downloadBookToFile({ bookDetails })).rejects.toThrow(/unexpected.*processing/i);
});
