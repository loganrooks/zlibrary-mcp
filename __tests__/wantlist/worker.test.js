import { test, expect, afterEach } from '@jest/globals';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { AcquisitionTools } from '../../dist/lib/acquisition-tools.js';
import { ToolFailure } from '../../dist/lib/tool-errors.js';
import { runList, recordChoices } from '../../dist/wantlist/worker.js';
import { readState, stateDirectory, sha, takeLock } from '../../dist/wantlist/state.js';
const temps = [];
afterEach(async () => {
  for (const t of temps.splice(0)) await fs.rm(t, { recursive: true, force: true });
});
async function fixture(count = 10, config = {}) {
  const temp = await fs.mkdtemp(path.join(tmpdir(), 'wantlist-unit-'));
  temps.push(temp);
  const list = path.join(temp, 'reading.txt'),
    out = path.join(temp, 'out');
  await fs.writeFile(
    list,
    Array.from({ length: count }, (_, i) => `Treatise ${i} — Writer [id=i${i}]`).join('\n'),
  );
  let busy = 0,
    overlap = false;
  const calls = [];
  let remaining = config.remaining ?? 100;
  const tools = new AcquisitionTools(
    async (op, args, options) => {
      busy++;
      if (busy > 1) overlap = true;
      calls.push({ op, args, signal: options?.signal });
      try {
        if (config.invoke) {
          const override = await config.invoke(op, args, options, calls);
          if (override !== undefined) return override;
        }
        if (op === 'get_download_limits')
          return { daily_remaining: remaining, daily_limit: 100, downloads_today: 100 - remaining };
        if (op === 'get_book_metadata_complete') return {};
        if (op === 'inspect_file')
          return (
            config.inspection ?? { status: 'unverified', reason: 'format', found: {}, checks: {} }
          );
        if (op === 'search' || op === 'search_multi_source') {
          const title = args.query ?? args.query_params?.query ?? 'Treatise';
          return {
            books: config.rows?.(title) ?? [
              {
                id: title,
                hash: 'hash',
                title,
                author: 'Writer',
                extension: 'epub',
                language: 'english',
                source: args.source ?? 'zlibrary',
              },
            ],
          };
        }
        if (op === 'acquire_book') {
          await fs.mkdir(out, { recursive: true });
          const file = path.join(out, args.request.item_id + '.epub'),
            record = file + '.acq.json';
          const data = Buffer.from(args.book_details.title);
          remaining--;
          await fs.writeFile(file, data);
          await fs.writeFile(
            record,
            JSON.stringify({
              record_version: 1,
              state: 'complete',
              path: file,
              bytes: data.length,
              sha256: sha(data),
              request: args.request,
              source: args.book_details.source,
              identifiers: { id: args.book_details.id, hash: 'hash' },
            }),
          );
          return {
            path: file,
            bytes: data.length,
            reused: false,
            transfer_skipped: false,
            verified: 'sha256',
            record,
          };
        }
        throw new Error('Unscripted operation ' + op);
      } finally {
        busy--;
      }
    },
    { ZLIBRARY_EMAIL: 'offline', ZLIBRARY_PASSWORD: 'offline' },
  );
  const options = {
    path: list,
    output_dir: out,
    sources: ['zlibrary'],
    reserve: 20,
    sleep: async () => {},
  };
  return {
    temp,
    list,
    out,
    tools,
    calls,
    options,
    dir: stateDirectory(list),
    overlap: () => overlap,
    setRemaining: (n) => (remaining = n),
  };
}
const ops = (f, op) => f.calls.filter((c) => c.op === op);
test('W1/W15 clean serial list, provenance and one receipt per item', async () => {
  const f = await fixture();
  const result = await runList(f.tools, f.options);
  expect(result.counts.fetched).toBe(10);
  expect(ops(f, 'acquire_book')).toHaveLength(10);
  expect(f.overlap()).toBe(false);
  expect(
    ops(f, 'acquire_book').every((c) => c.args.request.item_id && c.args.request.why_chosen),
  ).toBe(true);
  expect(
    (await fs.readFile(path.join(f.dir, 'receipts.v1.jsonl'), 'utf8')).trim().split('\n'),
  ).toHaveLength(10);
  expect(await fs.readFile(path.join(f.dir, 'state.v1.json'), 'utf8')).not.toMatch(/"ref"\s*:/);
});
test('W2/W3 reserve matches all, resumes only waiting items and hashes prior receipts', async () => {
  const f = await fixture(8, { remaining: 25 });
  let result = await runList(f.tools, f.options);
  expect(result.counts).toMatchObject({ fetched: 5, waiting_quota: 3 });
  expect(ops(f, 'search')).toHaveLength(8);
  expect(result.stop_reason).toBe('quota');
  f.calls.length = 0;
  f.setRemaining(30);
  result = await runList(f.tools, f.options);
  expect(result.counts).toMatchObject({ have: 5, fetched: 3 });
  expect(ops(f, 'acquire_book')).toHaveLength(3);
  expect(ops(f, 'search')).toHaveLength(3);
});
test('W5 changed lists retain unchanged items and mark removed items dropped', async () => {
  const f = await fixture(3);
  await runList(f.tools, f.options);
  f.calls.length = 0;
  await fs.writeFile(
    f.list,
    'Treatise 0 — Writer [id=i0]\nTreatise 3 — Writer [id=i3]\nTreatise 2 — Writer [id=i2]',
  );
  const r = await runList(f.tools, f.options);
  expect(r.counts).toMatchObject({ have: 2, fetched: 1, dropped: 1 });
  expect(ops(f, 'acquire_book')).toHaveLength(1);
});
test('missing or altered receipt artifact is searched again', async () => {
  const f = await fixture(1);
  await runList(f.tools, f.options);
  await fs.writeFile(path.join(f.out, 'i0.epub'), 'changed');
  f.calls.length = 0;
  const r = await runList(f.tools, f.options);
  expect(r.counts.fetched).toBe(1);
  expect(ops(f, 'search')).toHaveLength(1);
});
test('W7 choice after refs die re-finds identifiers', async () => {
  const config = {
    rows: (title) => [
      { id: 'a', hash: 'hash', title, author: 'Writer' },
      { id: 'b', hash: 'hash', title, author: 'Other' },
    ],
  };
  const f = await fixture(1, config);
  await fs.writeFile(f.list, 'Treatise 0 [id=i0]');
  const r = await runList(f.tools, f.options);
  expect(r.counts.needs_choice).toBe(1);
  await recordChoices(f.dir, { i0: 'b' });
  f.calls.length = 0;
  const r2 = await runList(f.tools, f.options);
  expect(r2.counts.fetched).toBe(1);
  expect((await readState(f.dir)).items.i0.reason).toBe('chosen');
  expect(ops(f, 'acquire_book')[0].args.book_details.id).toBe('b');
});
test('W8 choice unavailable asks without a transfer', async () => {
  const config = {
    rows: (title) => [
      { id: 'a', hash: 'hash', title, author: 'Writer' },
      { id: 'b', hash: 'hash', title, author: 'Other' },
    ],
  };
  const f = await fixture(1, config);
  await fs.writeFile(f.list, 'Treatise 0 [id=i0]');
  await runList(f.tools, f.options);
  config.rows = () => [];
  const r = await runList(f.tools, { ...f.options, choices: { i0: 'b' } });
  expect(r.needs_choice[0].reason).toBe('choice_unavailable');
  expect(ops(f, 'acquire_book')).toHaveLength(0);
});
test('W9 lease busy continues with next item', async () => {
  const f = await fixture(2, {
    invoke: (op, args) => {
      if (op === 'acquire_book' && args.request.item_id === 'i0')
        throw new ToolFailure('breaker_open', 'busy', {
          detail: { reason: 'breaker_open', request_issued: false },
        });
    },
  });
  const r = await runList(f.tools, f.options);
  expect(r.counts).toMatchObject({ retry_later: 1, fetched: 1 });
  expect((await readState(f.dir)).items.i0.reason).toBe('destination_busy');
});
test('W10 circuit waits twice and stops breaker', async () => {
  const f = await fixture(2, {
    invoke: (op) => {
      if (op === 'acquire_book')
        throw new ToolFailure('breaker_open', 'circuit', {
          detail: { reason: 'unknown' },
          retry_after_s: 1,
        });
    },
  });
  const waits = [];
  const r = await runList(f.tools, { ...f.options, sleep: async (ms) => waits.push(ms) });
  expect(r.stop_reason).toBe('breaker');
  expect(waits).toEqual([1000, 1000]);
  expect(ops(f, 'acquire_book')).toHaveLength(3);
});
test('W11 auth failed stops immediately', async () => {
  const f = await fixture(3, {
    invoke: (op) => {
      if (op === 'acquire_book') throw new ToolFailure('auth_failed', 'auth');
    },
  });
  const r = await runList(f.tools, f.options);
  expect(r.stop_reason).toBe('auth_failed');
  expect(ops(f, 'acquire_book')).toHaveLength(1);
});
test('W12 unknown outcome refreshes quota before next transfer', async () => {
  const f = await fixture(2, {
    invoke: (op, args) => {
      if (op === 'acquire_book' && args.request.item_id === 'i0')
        throw new ToolFailure('outcome_unknown', 'unknown', { retry: 'may_spend_quota' });
    },
  });
  const r = await runList(f.tools, f.options);
  expect(r.counts).toMatchObject({ retry_later: 1, fetched: 1 });
  const relevant = f.calls.filter((c) => ['acquire_book', 'get_download_limits'].includes(c.op));
  expect(relevant.map((c) => c.op)).toEqual([
    'get_download_limits',
    'acquire_book',
    'get_download_limits',
    'acquire_book',
  ]);
});
test('W13 integrity failure tries one alternative', async () => {
  const f = await fixture(1, {
    rows: (title) => [
      { id: '1', hash: 'hash', title, author: 'Writer' },
      { id: '2', hash: 'hash', title, author: 'Writer' },
    ],
    invoke: (op, args) => {
      if (op === 'acquire_book' && args.book_details.id === '1')
        throw new ToolFailure('integrity_mismatch', 'bad');
    },
  });
  const r = await runList(f.tools, f.options);
  expect(r.counts.fetched).toBe(1);
  expect(ops(f, 'acquire_book')).toHaveLength(2);
});
test('W14 dry run makes no transfer, no output folder, then real run processes it', async () => {
  const f = await fixture(2);
  let r = await runList(f.tools, { ...f.options, dry_run: true });
  expect(r.counts.fetched).toBe(2);
  expect(ops(f, 'acquire_book')).toHaveLength(0);
  expect((await readState(f.dir)).items.i0.dry_run).toBe(true);
  await expect(fs.stat(f.out)).rejects.toMatchObject({ code: 'ENOENT' });
  r = await runList(f.tools, f.options);
  expect(r.counts.fetched).toBe(2);
  expect(ops(f, 'acquire_book')).toHaveLength(2);
});
test('W16 live lock reads progress without bridge calls', async () => {
  const f = await fixture(1);
  await runList(f.tools, f.options);
  f.calls.length = 0;
  const release = await takeLock(f.dir);
  try {
    expect((await runList(f.tools, f.options)).status).toBe('running_elsewhere');
    expect(f.calls).toHaveLength(0);
  } finally {
    await release();
  }
});
test('W17 abort reaches transfer and releases run lock', async () => {
  const controller = new AbortController();
  const f = await fixture(1, {
    invoke: async (op, _args, options) => {
      if (op === 'acquire_book') {
        controller.abort();
        expect(options.signal.aborted).toBe(true);
        throw new ToolFailure('cancelled', 'cancelled');
      }
    },
  });
  const r = await runList(f.tools, { ...f.options, signal: controller.signal });
  expect(r.stop_reason).toBe('interrupted');
  expect((await readState(f.dir)).items.i0.reason).toBe('interrupted');
  await expect(fs.stat(path.join(f.dir, 'run.lock'))).rejects.toMatchObject({ code: 'ENOENT' });
});
test('W-S1 twenty items with two asks summary is bounded', async () => {
  const f = await fixture(20, {
    rows: (title) => [
      { id: title, hash: 'hash', title, author: 'Writer', language: 'english' },
      ...(['treatise 2', 'treatise 4'].includes(title)
        ? [{ id: title + 'x', hash: 'hash', title, author: 'Writer', language: 'german' }]
        : []),
    ],
  });
  const r = await runList(f.tools, f.options);
  expect(r.counts.needs_choice).toBe(2);
  expect(JSON.stringify(r).length).toBeLessThanOrEqual(2000);
});
test('quota exhausted still matches all remaining items', async () => {
  const f = await fixture(4, {
    invoke: (op, args) => {
      if (op === 'acquire_book' && args.request.item_id === 'i1')
        throw new ToolFailure('quota_exhausted', 'quota');
    },
  });
  const r = await runList(f.tools, f.options);
  expect(r.counts).toMatchObject({ fetched: 1, waiting_quota: 3 });
  expect(ops(f, 'search')).toHaveLength(4);
  expect(ops(f, 'acquire_book')).toHaveLength(2);
});
test('max downloads counts issued transfers and keeps matching', async () => {
  const f = await fixture(4);
  const r = await runList(f.tools, { ...f.options, max_downloads: 1 });
  expect(r.counts).toMatchObject({ fetched: 1, waiting_quota: 3 });
  expect(ops(f, 'search')).toHaveLength(4);
});
test('W6 valid checkpoint survives fatal scripted failure and reload', async () => {
  let crash = true;
  const f = await fixture(3, {
    invoke: (op, args) => {
      if (crash && op === 'acquire_book' && args.request.item_id === 'i1')
        throw new Error('fatal scripted failure');
    },
  });
  await runList(f.tools, f.options);
  const state = await readState(f.dir);
  expect(state.items.i0.state).toBe('fetched');
  expect(state.items.i1.state).toBe('failed');
  crash = false;
  const r = await runList(f.tools, { ...f.options, retry_failed: true });
  expect(r.counts).toMatchObject({ have: 2, fetched: 1 });
});
test('W18 local mismatch keeps artifact and queues a choice', async () => {
  const f = await fixture(1, {
    inspection: {
      status: 'mismatch',
      found: { language: 'german' },
      checks: { language: 'contradict' },
    },
  });
  const r = await runList(f.tools, f.options);
  expect(r.needs_choice[0].reason).toBe('edition_check_mismatch');
  const item = (await readState(f.dir)).items.i0;
  expect(item.path).toBeTruthy();
  expect((await fs.stat(item.path)).size).toBeGreaterThan(0);
  expect(ops(f, 'inspect_file')).toHaveLength(1);
});
test('exact probe needs affirmative file evidence; keep is explicit', async () => {
  const f = await fixture(1);
  await fs.writeFile(f.list, 'Treatise 0 — Writer [exact] [translator=Person] [id=i0]');
  let r = await runList(f.tools, f.options);
  expect(r.needs_choice[0].reason).toBe('constraint_unverified');
  expect(ops(f, 'acquire_book')).toHaveLength(1);
  r = await runList(f.tools, { ...f.options, choices: { i0: 'keep' } });
  expect(r.counts.fetched).toBe(1);
  expect((await readState(f.dir)).items.i0.reason).toBe('kept');
});
test('exact probe can settle absent catalogue constraint from file evidence', async () => {
  const f = await fixture(1, {
    inspection: { status: 'verified', found: {}, checks: { translator: 'match', work: 'match' } },
  });
  await fs.writeFile(f.list, 'Treatise 0 — Writer [exact] [translator=Person] [id=i0]');
  const r = await runList(f.tools, f.options);
  expect(r.counts.fetched).toBe(1);
  expect((await readState(f.dir)).items.i0.candidate.evidence.checked).toBe('file');
});

test('waiting exact probe still requires missing evidence after restart', async () => {
  const f = await fixture(1, { remaining: 20 });
  await fs.writeFile(f.list, 'Treatise 0 — Writer [exact] [translator=Person] [id=i0]');
  expect((await runList(f.tools, f.options)).counts.waiting_quota).toBe(1);
  f.setRemaining(30);
  const r = await runList(f.tools, f.options);
  expect(r.counts.needs_choice).toBe(1);
  expect(r.needs_choice[0].reason).toBe('constraint_unverified');
});
test('choice mailbox does not replay earlier choices when another item is answered', async () => {
  const f = await fixture(2, {
    rows: (title) => [
      { id: title, hash: 'hash', title, author: 'Writer' },
      { id: title + 'b', hash: 'hash', title, author: 'Writer', language: 'german' },
    ],
  });
  await runList(f.tools, f.options);
  await recordChoices(f.dir, { i0: 'a' });
  await runList(f.tools, f.options);
  f.calls.length = 0;
  await recordChoices(f.dir, { i1: 'a' });
  const r = await runList(f.tools, f.options);
  expect(ops(f, 'acquire_book')).toHaveLength(1);
  expect(r.counts).toMatchObject({ have: 1, fetched: 1 });
});

test('network retry refreshes invalid quota and obeys the issued-transfer cap', async () => {
  let first = true;
  const f = await fixture(1, {
    invoke: (op) => {
      if (op === 'acquire_book' && first) {
        first = false;
        throw new ToolFailure('provider_timeout', 'transient', { retry: 'may_spend_quota' });
      }
    },
  });
  let r = await runList(f.tools, { ...f.options, max_downloads: 1 });
  expect(ops(f, 'acquire_book')).toHaveLength(1);
  expect(r.counts.waiting_quota).toBe(1);
  const g = await fixture(1, {
    invoke: (op) => {
      if (op === 'acquire_book' && first) {
        first = false;
        throw new ToolFailure('provider_timeout', 'transient', { retry: 'may_spend_quota' });
      }
    },
  });
  first = true;
  r = await runList(g.tools, g.options);
  expect(r.counts.fetched).toBe(1);
  expect(
    g.calls.filter((c) => ['acquire_book', 'get_download_limits'].includes(c.op)).map((c) => c.op),
  ).toEqual(['get_download_limits', 'acquire_book', 'get_download_limits', 'acquire_book']);
});
