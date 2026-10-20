import { test, expect, beforeAll, afterAll } from '@jest/globals';
import { spawn } from 'node:child_process';
import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Rehearsal } from './harness.js';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let h;
beforeAll(async () => {
  h = await Rehearsal.start('wantlist');
});
afterAll(async () => {
  if (h) await h.close();
});
async function cli(args, out) {
  const home = path.join(h.temp, 'cli-home');
  await mkdir(home, { recursive: true });
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        '--import',
        path.join(root, '__tests__/rehearsal/node-isolation.mjs'),
        path.join(root, 'dist/wantlist/cli.js'),
        ...args,
      ],
      {
        cwd: home,
        env: {
          PATH: process.env.PATH,
          HOME: home,
          TMPDIR: home,
          XDG_STATE_HOME: home,
          XDG_CACHE_HOME: home,
          XDG_CONFIG_HOME: home,
          ...h.providerEnvironment({ libgen: true }),
          ZLIBRARY_OUTPUT_ROOT: out,
          ZLIBRARY_SESSION_MODE: 'memory',
          ZLIBRARY_SESSION_DIR: path.join(home, 'session'),
          ZLIBRARY_VENV_PATH: path.join(root, '.venv'),
          REHEARSAL_EGRESS_TRAP: path.join(home, 'egress-trap.txt'),
          REHEARSAL_LOG_DIR: path.join(home, 'logs'),
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    );
    let stdout = '',
      stderr = '';
    child.stdout.on('data', (d) => (stdout += d));
    child.stderr.on('data', (d) => (stderr += d));
    child.once('error', reject);
    const timer = setTimeout(() => child.kill('SIGTERM'), 45000);
    child.once('close', (code) => {
      clearTimeout(timer);
      h.scan(stdout, 'reply');
      h.scan(stderr, 'stderr');
      resolve({
        code,
        stdout,
        stderr,
        data: args.includes('--json') && stdout.trim() ? JSON.parse(stdout) : undefined,
      });
    });
  });
}
async function setup(name, text) {
  await h.mode({ mode: 'healthy', reset: true, remaining: 7 });
  const list = path.join(h.temp, name + '.txt'),
    out = path.join(h.temp, name + '-out');
  await writeFile(
    list,
    text ?? (await readFile(path.join(root, '__tests__/rehearsal/fixtures/wantlist.txt'), 'utf8')),
  );
  return { list, out, state: path.join(h.temp, name + '.wantlist') };
}
const simple =
  'Persuasion — Jane Austen\nLetters on Ethics — Seneca\nThe Human Condition — Hannah Arendt';
let healthy;
test('R-W1 healthy real CLI preserves pinned catalogue and matching rules', async () => {
  healthy = await setup('healthy');
  const r = await cli(
    ['run', healthy.list, '--sources', 'zlibrary,libgen', '--reserve', '0', '--json'],
    healthy.out,
  );
  expect(r.code).toBe(0);
  expect(r.data.counts).toMatchObject({ fetched: 6, needs_choice: 2, not_found: 1 });
  const state = JSON.parse(await readFile(path.join(healthy.state, 'state.v1.json'), 'utf8'));
  const items = Object.values(state.items);
  expect(items[0].candidate.source).toBe('zlibrary');
  expect(items[2].reason).toBe('exact_match');
  expect(items[3].reason).toBe('different_work');
  expect(items[7].candidate.orientation).toBe('swapped');
  // Swapped search parameters cannot recover rows until title-only fallback on the same first source.
  for (const i of items.filter((i) => i.state === 'fetched'))
    expect(JSON.parse(await readFile(i.record, 'utf8')).request.item_id).toBe(i.want.item_id);
});
test('R-W2 repeat CLI spends no additional quota', async () => {
  const before = await h.stats();
  const r = await cli(
    ['run', healthy.list, '--sources', 'zlibrary,libgen', '--reserve', '0', '--json'],
    healthy.out,
  );
  expect(r.code).toBe(0);
  expect((await h.stats()).quotaSpent).toBe(before.quotaSpent);
});
test('R-W3 quota parks matched items then resumes without replay', async () => {
  const f = await setup('quota', simple);
  await h.mode({ remaining: 2 });
  const args = ['run', f.list, '--sources', 'zlibrary', '--reserve', '0', '--json'];
  let r = await cli(args, f.out);
  expect(r.code).toBe(2);
  expect(r.data.counts).toMatchObject({ fetched: 2, waiting_quota: 1 });
  await h.mode({ remaining: 7 });
  r = await cli(args, f.out);
  expect(r.code).toBe(0);
  expect(r.data.counts).toMatchObject({ have: 2, fetched: 1 });
  expect((await h.stats()).quotaSpent).toBe(3);
});
test('R-W4 transfer drop records a reason and continues', async () => {
  const f = await setup('drop', simple);
  await h.mode({ mode: 'drop_transfer' });
  const r = await cli(['run', f.list, '--sources', 'zlibrary', '--reserve', '0', '--json'], f.out);
  expect(r.data.counts.failed + r.data.counts.retry_later).toBeGreaterThan(0);
});
test('R-W5 volume choice re-mints refs after restart', async () => {
  const f = await setup('choice', 'Phenomenology Studies — Catalogue Collective');
  let r = await cli(['run', f.list, '--sources', 'zlibrary', '--reserve', '0', '--json'], f.out);
  expect(r.data.needs_choice[0].reason).toBe('volume_unspecified');
  const id = r.data.needs_choice[0].item_id;
  await cli(['choose', f.list, id, 'c'], f.out);
  r = await cli(['run', f.list, '--sources', 'zlibrary', '--reserve', '0', '--json'], f.out);
  expect(r.data.counts.fetched).toBe(1);
});
test('R-W6 dry preview spends no quota or output files', async () => {
  const f = await setup('dry', simple);
  const r = await cli(
    ['run', f.list, '--sources', 'zlibrary', '--reserve', '0', '--dry-run', '--json'],
    f.out,
  );
  expect(r.code).toBe(0);
  expect((await h.stats()).quotaSpent).toBe(0);
  expect(await readdir(f.out).catch(() => [])).toEqual([]);
});
test('R-W7 CLI and state have no secret or cookie sentinel findings', async () => {
  for (const file of await readdir(healthy.state))
    if (!file.endsWith('.lock'))
      h.scan(await readFile(path.join(healthy.state, file), 'utf8'), 'reply');
  expect(h.leaks).toBe(0);
});
test('R-W8 synthetic EPUB and PDF stay unverified', async () => {
  const state = JSON.parse(await readFile(path.join(healthy.state, 'state.v1.json'), 'utf8'));
  for (const item of Object.values(state.items).filter((i) => i.path))
    expect(item.edition_check.status).toBe('unverified');
});
test('R-W9 extras off preserves exact five-tool surface', async () => {
  await h.scenario('wantlist-off', async (connect) => {
    const c = await connect();
    expect(JSON.stringify((await c.listTools()).tools)).toBe(
      JSON.stringify(
        JSON.parse(
          await readFile(path.join(root, '__tests__/wantlist/fixtures/base-tools.json'), 'utf8'),
        ),
      ),
    );
  });
});
test('R-W10 extra in real MCP completes three inline requests', async () => {
  await h.scenario(
    'wantlist-on',
    async (connect) => {
      const c = await connect();
      const listed = await c.listTools();
      expect(listed.tools).toHaveLength(6);
      const result = await h.call(c, 'acquire_list', {
        items: simple.split('\n'),
        sources: ['libgen'],
        wait_s: 50,
      });
      expect(result.status).toBe('done');
    },
    { libgen: true, extras: 'wantlist' },
  );
});
