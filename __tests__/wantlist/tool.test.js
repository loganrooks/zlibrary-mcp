import { test, expect, afterEach } from '@jest/globals';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { readFile, mkdtemp, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { AcquisitionTools } from '../../dist/lib/acquisition-tools.js';
import { ERROR_CODES } from '../../dist/lib/tool-errors.js';
import { createServer, TOOL_DEFINITIONS } from '../../dist/index.js';
import { ListRuns, LIST_INPUT, LIST_TOOL } from '../../dist/wantlist/tool.js';
const cleanup = [];
const saved = process.env.ZLIBRARY_EXTRAS;
afterEach(async () => {
  if (saved === undefined) delete process.env.ZLIBRARY_EXTRAS;
  else process.env.ZLIBRARY_EXTRAS = saved;
  for (const fn of cleanup.splice(0)) await fn();
});
async function client() {
  const c = new Client({ name: 'wantlist-test', version: '1' }),
    s = createServer();
  const [a, b] = InMemoryTransport.createLinkedPair();
  await s.connect(a);
  await c.connect(b);
  cleanup.push(
    () => c.close(),
    () => s.close(),
  );
  return c;
}
test('C1/C2 extras off: byte-identical base snapshot and 19 error codes', async () => {
  delete process.env.ZLIBRARY_EXTRAS;
  const c = await client();
  const tools = (await c.listTools()).tools;
  const fixture = JSON.parse(
    await readFile(new URL('../fixtures/tools-surface-v2.json', import.meta.url), 'utf8'),
  );
  const rehearsal = JSON.parse(
    await readFile(new URL('../rehearsal/tools-surface.json', import.meta.url), 'utf8'),
  );
  const compact = tools
    .map((t) => ({ name: t.name, arguments: Object.keys(t.inputSchema.properties).sort() }))
    .sort((a, b) => a.name.localeCompare(b.name));
  const base = JSON.parse(
    await readFile(new URL('./fixtures/base-tools.json', import.meta.url), 'utf8'),
  );
  expect(tools).toHaveLength(5);
  expect(compact).toEqual(fixture);
  expect(compact).toEqual(rehearsal);
  expect(JSON.stringify(tools)).toBe(JSON.stringify(base));
  expect(JSON.stringify({ tools })).toHaveLength(6493);
  expect(ERROR_CODES).toHaveLength(19);
  expect(TOOL_DEFINITIONS).toHaveLength(5);
  const r = await c.callTool({
    name: 'acquire_list',
    arguments: { items: ['Title'], sources: ['libgen'] },
  });
  expect(r.isError).toBe(true);
});
test('extra registration is opt-in and uses bounded strict schema', async () => {
  process.env.ZLIBRARY_EXTRAS = 'unknown, wantlist';
  const c = await client();
  expect((await c.listTools()).tools).toHaveLength(6);
  expect(LIST_TOOL.description.length).toBeLessThan(400);
  for (const input of [
    {},
    { path: 'a', items: ['b'] },
    { items: [] },
    { items: Array(201).fill('x') },
    { items: ['x'], wait_s: 51 },
    { items: ['x'], unknown: 1 },
  ])
    expect(LIST_INPUT.safeParse(input).success).toBe(false);
  expect((await c.callTool({ name: 'acquire_list', arguments: { items: [] } })).isError).toBe(true);
});
test('background calls share one worker, return progress then complete', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'wantlist-tool-'));
  cleanup.push(() => rm(temp, { recursive: true, force: true }));
  let release;
  const gate = new Promise((r) => (release = r));
  let calls = 0;
  const tools = new AcquisitionTools(async (op) => {
    if (op === 'search_multi_source') {
      calls++;
      await gate;
      return { books: [] };
    }
    throw new Error(op);
  }, {});
  const runs = new ListRuns(tools),
    args = { items: ['Not Here'], sources: ['libgen'], output_dir: temp, wait_s: 0 };
  let a = await runs.call(args);
  expect(a.status).toBe('running');
  await new Promise((r) => setTimeout(r, 30));
  const b = await runs.call(args);
  expect(b.status).toBe('running');
  release();
  a = await runs.call({ ...args, wait_s: 1 });
  expect(a.status).toBe('done');
  expect(a.counts.not_found).toBe(1);
  expect(calls).toBe(1);
});
test('source configuration rejected before any invoke or state write', async () => {
  const tools = new AcquisitionTools(async () => {
    throw new Error('unexpected provider');
  }, {});
  const runs = new ListRuns(tools);
  const r = await runs.call({ items: ['Title'], output_dir: '/tmp/wantlist-no-source' });
  expect(r.error.code).toBe('sources_required');
});
test('CLI sources validation and status work without providers', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'wantlist-cli-'));
  cleanup.push(() => rm(temp, { recursive: true, force: true }));
  await writeFile(path.join(temp, 'list.txt'), 'Title');
  // The worker configuration path, used by CLI main, is exercised without process spawning.
  const tools = new AcquisitionTools(async () => {
    throw new Error('unexpected provider');
  }, {});
  const runs = new ListRuns(tools);
  expect(
    (await runs.call({ path: path.join(temp, 'list.txt'), sources: [], wait_s: 0 })).error.code,
  ).toBe('invalid_argument');
});
