import { test, expect } from '@jest/globals';
import { tasks, arms } from './tasks.js';
import { scoreTask, dataOf } from './oracles.js';
import { usageFrom, commandFor } from './drivers.js';
import { summarize } from './report.js';
const arm = arms.find((a) => a.id === 'B');
const reply = (data) => ({
  content: [{ type: 'text', text: JSON.stringify(data) }],
  structuredContent: data,
});
const score = (id, trace, extra = {}) =>
  scoreTask({
    task: tasks.find((t) => t.id === id),
    arm,
    trace,
    downloads: '/tmp/not-an-artifact',
    ...extra,
  });
// A regression that only counts tool NAMES would miss these argument mutations.
test('wrong source, cursor extras and years are decisions even on correct B tool names', async () => {
  const source = await score('T8', [
    {
      name: 'search',
      args: { query: 'The Glass Orchard', sources: ['zlibrary', 'libgen'] },
      reply: reply({ rows: [] }),
    },
  ]);
  expect(
    source.wrong.some(
      (x) =>
        x.reason === 'quota-preserving source argument' && x.arguments.sources[0] === 'zlibrary',
    ),
  ).toBe(true);
  const cursor = await score(
    'T6',
    [{ name: 'search', args: { cursor: 'observed', limit: 10 }, reply: reply({ rows: [] }) }],
    { context: { cursor: 'observed' } },
  );
  expect(cursor.wrong.some((x) => x.reason.includes('cursor'))).toBe(true);
  const years = await score('T12', [
    {
      name: 'search',
      args: { author: 'Hannah Arendt', year_from: 1951, year_to: 1965 },
      reply: reply({ rows: [] }),
    },
  ]);
  expect(years.wrong.some((x) => x.reason === 'wrong year bounds')).toBe(true);
});
test('history-disabled inability succeeds; a download and quota spend cannot substitute', async () => {
  const disabled = arms.find((a) => !a.history);
  expect(
    (
      await score('T7', [], {
        arm: disabled,
        final: 'Account history is not available in this configuration.',
      })
    ).success,
  ).toBe(true);
  const bad = await score(
    'T7',
    [
      {
        name: 'download',
        args: { ref: 'invented' },
        reply: reply({ error: { code: 'ref_unavailable' } }),
      },
    ],
    { arm: disabled, quotaSpent: 1 },
  );
  expect(bad.success).toBe(false);
  expect(bad.quotaSpent).toBe(1);
  expect(bad.refUnavailable).toBe(1);
  expect(bad.wrong.some((x) => x.reason === 'forbidden quota spend')).toBe(true);
});
test('T3 re-search and wrong edition are marked, T2 cannot skip detail calls', async () => {
  const res = await score('T3', [
    { name: 'search', args: { query: 'Seneca' }, reply: reply({ rows: [] }) },
    {
      name: 'download',
      args: { ref: 'campbell' },
      selected: { title: 'Letters from a Stoic' },
      observedSelection: true,
      reply: reply({}),
    },
  ]);
  expect(res.wrong.some((x) => x.reason === 'off-oracle tool')).toBe(true);
  expect(res.wrong.some((x) => x.reason === 'wrong edition')).toBe(true);
  expect(
    (
      await score(
        'T2',
        [{ name: 'search', args: { query: 'Seneca' }, reply: reply({ rows: [] }) }],
        { final: 'Graver; Campbell' },
      )
    ).wrong.some((x) => x.reason === 'missing edition detail'),
  ).toBe(true);
});
test('usage comes from driver final usage only, without double counting assistant blocks', () => {
  const u = usageFrom('claude', [
    { type: 'assistant', message: { usage: { cache_read_input_tokens: 0 } } },
    {
      type: 'result',
      usage: {
        input_tokens: 10,
        cache_read_input_tokens: 80,
        cache_creation_input_tokens: 20,
        output_tokens: 7,
      },
    },
  ]);
  expect(u).toMatchObject({
    inputTotal: 110,
    inputUncached: 10,
    inputCacheRead: 80,
    inputCacheWrite: 20,
    output: 7,
    cacheFirstRequest: 0,
    outputCached: null,
  });
  expect(
    usageFrom('codex', [
      {
        type: 'turn.completed',
        usage: { input_tokens: 100, cached_input_tokens: 60, output_tokens: 9 },
      },
    ]),
  ).toMatchObject({
    inputTotal: 100,
    inputUncached: 40,
    inputCacheRead: 60,
    inputCacheWrite: null,
    output: 9,
  });
  expect(() => usageFrom('codex', [])).toThrow('missing');
});
test('commands pin models, search, caching and explicit resume IDs without launching drivers', () => {
  const c = commandFor({
    driver: 'claude',
    directory: '/tmp/cell',
    socketPath: '/tmp/broker',
    nonce: 'nonce',
    session: 'id',
  });
  expect(c.env.ENABLE_TOOL_SEARCH).toBe('false');
  expect(c.args).toContain('claude-opus-5-5');
  expect(c.args).toContain('--resume');
  const x = commandFor({
    driver: 'codex',
    directory: '/tmp/cell',
    socketPath: '/tmp/broker',
    nonce: 'nonce',
    session: 'id',
  });
  expect(x.args.slice(0, 2)).toEqual(['exec', 'resume']);
  expect(x.args).toContain('gpt-6.1-sol');
  expect(x.args).toContain('code_mode_tool_search');
  expect(x.args).not.toContain('tool_search');
});
test('matrix carries Q1, Q2, history-disabled arms; A exclusions survive and offline results never meet bar', () => {
  expect(tasks.map((t) => t.id)).toEqual(Array.from({ length: 12 }, (_, i) => `T${i + 1}`));
  expect(arms.some((a) => !a.textCopy)).toBe(true);
  expect(arms.some((a) => a.defaultOrder)).toBe(true);
  expect(arms.some((a) => !a.history)).toBe(true);
  expect(tasks.filter((t) => t.outsideA).map((t) => t.id)).toEqual(['T5', 'T6', 'T10']);
  expect(summarize([{ status: 'self-test pass', results: [] }]).comparisons).toEqual([]);
  expect(dataOf({ structuredContent: { items: [{ title: 'Being and Time' }] } })).toEqual([
    { title: 'Being and Time' },
  ]);
});

test('bar compares five-run cold and warm totals, rejects wrong decisions where A median is zero', () => {
  const make = (arm, input, wrong = 0) => ({
    status: 'measured',
    driver: 'claude',
    arm,
    settings: { toolSearch: false, warmRuns: 1 },
    build: { tools: { serializedCharacters: 5000 } },
    results: Array.from({ length: 5 }, (_, run) =>
      ['cold', 'warm'].flatMap((phase) =>
        tasks.map((t) => ({
          run,
          phase,
          task: t.id,
          success: true,
          wrongDecisions: t.id === 'T1' ? wrong : 0,
          quotaSpent: 0,
          trace: [],
          usage: { inputTotal: input, output: 1, cacheFirstRequest: 0 },
        })),
      ),
    ).flat(),
  });
  const a = make(arms[0], 100),
    b = make(arms[1], 50);
  expect(summarize([a, b]).comparisons[0].status).toBe('bar met');
  const bad = make(arms[1], 50, 1);
  expect(summarize([a, bad]).comparisons[0].status).toBe('bar not met');
  const unknown = make(arms[1], 50);
  unknown.results[0].usage.cacheFirstRequest = null;
  expect(summarize([a, unknown]).comparisons[0].status).toMatch(/inconclusive/);
});

test('full-record selection equality ignores JSON key order but not changed values', async () => {
  const { canonicalRow } = await import('./server.js');
  expect(canonicalRow({ id: '202', extra: { a: 1, b: 2 } })).toBe(
    canonicalRow({ extra: { b: 2, a: 1 }, id: '202' }),
  );
  expect(canonicalRow({ id: '202' })).not.toBe(canonicalRow({ id: '203' }));
});

test('A wrong search tool is not excused merely because its result looks usable', async () => {
  const result = await score(
    'T1',
    [{ name: 'full_text_search', args: { query: 'Persuasion' }, reply: reply({ books: [] }) }],
    { arm: arms[0] },
  );
  expect(
    result.wrong.some((x) => x.reason === 'off-oracle tool' && x.tool === 'full_text_search'),
  ).toBe(true);
});
