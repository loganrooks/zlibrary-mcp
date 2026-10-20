import { test, expect, jest, afterEach } from '@jest/globals';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
const resources = [];
afterEach(async () => { for (const r of resources.splice(0)) await r.close(); jest.restoreAllMocks(); });
async function connect() {
  const { createServer } = await import('../dist/index.js');
  const server = createServer();
  const client = new Client({ name: 'interface-contract', version: '1' });
  resources.push(client, server);
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(b), client.connect(a)]);
  return client;
}
test('initializes source-neutral metadata and keeps credential-free local tools available', async () => {
  const client = await connect();
  expect(client.getServerVersion().name).toBe('book-acquisition');
  const result = await client.callTool({ name: 'get_limits', arguments: {} });
  expect(result.structuredContent.sources.libgen.download_available).toBe(true);
});
test('structured errors and text are identical JSON records for schema failures and unknown names', async () => {
  const client = await connect();
  for (const call of [{ name: 'search', arguments: { count: 10 } }, { name: 'never_existed', arguments: {} }]) {
    const result = await client.callTool(call);
    expect(result.isError).toBe(true);
    expect(result.structuredContent.error.code).toBe('invalid_argument');
    expect(JSON.parse(result.content[0].text)).toEqual(result.structuredContent);
  }
});
test('invalid privacy configuration is rejected before accepting requests', async () => {
  const { createServer, start } = await import('../dist/index.js');
  const previous = process.env.ZLIBRARY_SESSION_MODE;
  const log = jest.spyOn(console, 'error').mockImplementation(() => {});
  process.env.ZLIBRARY_SESSION_MODE = 'invalid-mode';
  try {
    expect(() => createServer()).toThrow(/ZLIBRARY_SESSION_MODE/);
    expect(await start({ testing: true })).toBeNull();
    expect(log).toHaveBeenCalled();
  } finally {
    if (previous === undefined) delete process.env.ZLIBRARY_SESSION_MODE;
    else process.env.ZLIBRARY_SESSION_MODE = previous;
  }
});
