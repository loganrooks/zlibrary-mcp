import * as fs from 'node:fs/promises';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import type { AcquisitionTools } from '../lib/acquisition-tools.js';
import { ToolFailure, classifyFailure } from '../lib/tool-errors.js';
import { extractVolume, parseManifest } from './parse.js';
import type { Decision } from './match.js';
import { decide, classify, constraints, mainTitle } from './match.js';
import { rank, whyChosen } from './rank.js';
import {
  now,
  sha,
  stateDirectory,
  takeLock,
  readState,
  reconcile,
  save,
  receiptIndex,
  verifiedReceipt,
  durableCandidate,
} from './state.js';
import { summary, writeReports } from './summary.js';
import type {
  RunOptions,
  Settings,
  ListState,
  Item,
  ItemState,
  Candidate,
  Source,
} from './types.js';

export const CHOICES = ['a', 'b', 'c', 'skip', 'keep', 'retry'];
export function validateChoices(choices: Record<string, string>) {
  for (const v of Object.values(choices))
    if (!CHOICES.includes(v))
      throw new ToolFailure('invalid_argument', 'Choice must be a, b, c, skip, keep or retry.');
}
export async function recordChoices(dir: string, choices: Record<string, string>) {
  validateChoices(choices);
  const state = await readState(dir);
  if (!state) throw new ToolFailure('invalid_argument', 'Run the list before answering choices.');
  for (const id of Object.keys(choices))
    if (!Object.hasOwn(state.items, id))
      throw new ToolFailure('invalid_argument', 'Unknown item id.');
  // Append a mailbox rather than racing the worker's authoritative state writes.
  await fs.appendFile(
    path.join(dir, 'choices.txt'),
    Object.entries(choices)
      .map(([id, c]) => `${JSON.stringify(id)} ${c}\n`)
      .join(''),
    { mode: 0o600 },
  );
}
export async function prepare(options: RunOptions) {
  const output = path.resolve(
    options.output_dir ?? process.env.ZLIBRARY_OUTPUT_ROOT ?? 'downloads',
  );
  const text = options.path
    ? await fs.readFile(path.resolve(options.path), 'utf8')
    : JSON.stringify(options.items ?? []);
  const parsed = parseManifest(text, options.path ?? 'inline.txt', options.items);
  const sources =
    options.sources ??
    parsed.defaults.sources ??
    process.env.BOOK_SOURCE_DEFAULT_ORDER?.split(',').map((s) => s.trim());
  if (!sources?.length) throw new ToolFailure('sources_required', 'Choose the sources to search.');
  if (
    sources.length > 3 ||
    new Set(sources).size !== sources.length ||
    sources.some((s: string) => !['libgen', 'zlibrary', 'annas'].includes(s))
  )
    throw new ToolFailure(
      'invalid_argument',
      'Choose 1–3 distinct sources: libgen,zlibrary,annas.',
    );
  for (const n of ['reserve', 'max_downloads', 'max_minutes'] as const)
    if (
      options[n] !== undefined &&
      (!Number.isFinite(options[n]) ||
        options[n]! < 0 ||
        (n !== 'max_minutes' && !Number.isInteger(options[n])))
    )
      throw new ToolFailure('invalid_argument', `Invalid ${n}.`);
  if (options.mode && !['any', 'exact'].includes(options.mode))
    throw new ToolFailure('invalid_argument', 'Invalid mode.');
  validateChoices(options.choices ?? {});
  if (options.mode) for (const w of parsed.items) if (!w.edition_note) w.mode = options.mode;
  const settings: Settings = {
    sources,
    output_dir: output,
    mode: options.mode ?? parsed.defaults.mode ?? 'any',
    formats: options.formats ?? parsed.defaults.formats,
    language: options.language ?? parsed.defaults.language,
    reserve: options.reserve ?? 20,
    max_downloads: options.max_downloads,
    probe: options.probe !== false,
  };
  const list = options.path
    ? path.resolve(options.path)
    : path.join(
        output,
        '.wantlist',
        'inline-' +
          sha(
            JSON.stringify(parsed.items.map(({ line: _line, warnings: _warnings, ...w }) => w)),
          ).slice(0, 12),
      );
  const dir = options.path
    ? stateDirectory(list, options.state)
    : path.resolve(options.state ?? list);
  return { text, parsed, settings, list, dir };
}
function decode(reply: any, _op: string): any {
  if (reply.error)
    throw new ToolFailure(reply.error.code, reply.error.message, {
      ...reply.error,
      detail: reply.error.detail,
    });
  return reply;
}
function same(a: Candidate, b: Candidate) {
  return a.source === b.source && JSON.stringify(a.identifiers) === JSON.stringify(b.identifiers);
}
function candidate(tools: AcquisitionTools, row: any): Candidate {
  const held = tools.refs.get<any>(row.ref, 'r');
  const b = held.book;
  return {
    ...row,
    quality: b.quality,
    identifiers:
      held.source === 'zlibrary'
        ? { id: String(b.id), hash: b.hash ?? b.book_hash }
        : { md5: b.md5 },
  };
}

export async function runList(tools: AcquisitionTools, options: RunOptions): Promise<any> {
  const p = await prepare(options);
  const unlock = await takeLock(p.dir);
  if (!unlock) {
    const state = await readState(p.dir);
    return summary(
      state ?? reconcile(undefined, p.parsed.items, p.list, sha(p.text), p.settings),
      p.dir,
      'running_elsewhere',
    );
  }
  let state: ListState | undefined;
  let current: Item | undefined;
  const controller = new AbortController();
  const externalAbort = () => controller.abort();
  options.signal?.addEventListener('abort', externalAbort, { once: true });
  if (options.signal?.aborted) controller.abort();
  let deadline = false;
  const timer =
    options.max_minutes === undefined
      ? undefined
      : setTimeout(() => {
          deadline = true;
          controller.abort();
        }, options.max_minutes * 60000);
  const signal = controller.signal;
  const sleeps =
    options.sleep ?? ((ms: number, s?: AbortSignal) => delay(ms, undefined, { signal: s }));
  const disabled = new Map<Source, string>();
  let issued = 0,
    zIssued = 0,
    quotaInvalid = false,
    quotaExhausted = false,
    downStreak = 0,
    internalStreak = 0;
  const transition = async (item: Item, next: ItemState, reason?: string) => {
    item.state = next;
    item.reason = reason;
    item.history.push({ at: now(), state: next, ...(reason ? { reason } : {}) });
    await save(p.dir, state!);
    await writeReports(state!, p.dir);
  };
  const readQuota = async () => {
    if (!p.settings.sources.includes('zlibrary') || disabled.has('zlibrary')) return;
    const reply = decode(
      await tools.call('get_limits', { mode: 'live', sources: ['zlibrary'] }, { signal }),
      'get_limits',
    );
    const source = reply.sources.zlibrary;
    if (source.error) {
      const e = new ToolFailure(source.error.code, source.error.message, source.error);
      if (e.code === 'credentials_missing') {
        disabled.set('zlibrary', 'config');
        return;
      }
      throw e;
    }
    state!.quota = {
      source: 'zlibrary',
      remaining: source.limit.remaining,
      basis: source.limit.kind === 'daily' ? 'observed' : 'unknown',
      as_of: source.limit.as_of ?? now(),
    };
    quotaInvalid = false;
  };
  const invoke = async <T>(op: string, work: () => Promise<T>): Promise<T> => {
    let breakerRetries = 0,
      networkRetries = 0;
    for (;;) {
      if (signal.aborted) throw new ToolFailure('cancelled', 'Run interrupted.', { retry: 'safe' });
      try {
        return await work();
      } catch (error) {
        const e = classifyFailure(error, op);
        if (
          e.code === 'breaker_open' &&
          !['breaker_open', 'auth_backoff'].includes(e.info.detail?.reason) &&
          breakerRetries++ < 2
        ) {
          await sleeps((e.info.retry_after_s ?? 60) * 1000, signal);
          continue;
        }
        if (['provider_unreachable', 'provider_timeout'].includes(e.code) && networkRetries++ < 1) {
          await sleeps(30000, signal);
          continue;
        }
        throw e;
      }
    }
  };
  const search = async (
    item: Item,
    source: Source,
    query: string,
    author?: string,
    limit = 25,
  ): Promise<Candidate[]> => {
    if (item.counts.searches >= 4) return [];
    const result = await invoke('search', async () => {
      if (item.counts.searches >= 4)
        throw new ToolFailure('provider_timeout', 'Search cap reached.', { retry: 'safe' });
      item.counts.searches++;
      await save(p.dir, state!);
      return decode(
        await tools.call(
          'search',
          {
            query: query || item.want.title,
            ...(author ? { author } : {}),
            sources: [source],
            limit,
          },
          { signal },
        ),
        'search',
      );
    });
    return result.rows.map((r: any) => candidate(tools, r));
  };
  const details = async (item: Item, rows: Candidate[]) => {
    const scored = rank(
      rows.map((c) => constraints(item.want, classify(item.want, c))),
      item.want,
      p.settings,
    );
    for (const c of scored) {
      if (item.counts.details >= 3) break;
      const eligible =
        c.score! >= 0.9 &&
        !c.derivative &&
        !c.conflicts?.length &&
        ((item.want.mode === 'exact' && c.missing?.length) ||
          c.volume_status === 'volume_unverified' ||
          c.author_match === 'none');
      if (!eligible) continue;
      const result = await invoke('get_book', async () => {
        if (item.counts.details >= 3)
          throw new ToolFailure('provider_timeout', 'Detail cap reached.', { retry: 'safe' });
        item.counts.details++;
        return decode(await tools.call('get_book', { ref: c.ref }, { signal }), 'get_book');
      });
      Object.assign(
        rows.find((r) => r.ref === c.ref)!,
        result,
        { evidence: { ...result.evidence, checked: 'detail' } },
      );
    }
  };
  const handleFailure = async (item: Item, error: unknown, source?: Source) => {
    const e = classifyFailure(error, 'download', source);
    if (!['provider_unreachable', 'provider_timeout'].includes(e.code)) downStreak = 0;
    if (e.code !== 'internal') internalStreak = 0;
    const reason = e.info.detail?.reason;
    if (signal.aborted) {
      state!.run.stop_reason = deadline ? 'deadline' : 'interrupted';
      await transition(item, 'retry_later', 'interrupted');
      return;
    }
    if (e.code === 'quota_exhausted') {
      if (!['quota_reserve', 'max_downloads'].includes(reason)) quotaExhausted = true;
      state!.run.stop_reason = 'quota';
      await transition(
        item,
        'waiting_quota',
        ['quota_reserve', 'max_downloads'].includes(reason) ? reason : 'quota_exhausted',
      );
    } else if (e.code === 'breaker_open' && reason === 'breaker_open')
      await transition(item, 'retry_later', 'destination_busy');
    else if (e.code === 'breaker_open' && reason === 'auth_backoff') {
      disabled.set(source ?? 'zlibrary', 'auth_backoff');
      state!.run.stop_reason = 'auth_backoff';
      await transition(item, 'retry_later', 'auth_backoff');
    } else if (e.code === 'breaker_open') {
      state!.run.stop_reason = 'breaker';
      await transition(item, 'retry_later', 'breaker_open');
    } else if (['provider_unreachable', 'provider_timeout'].includes(e.code)) {
      downStreak++;
      if (downStreak >= 3) state!.run.stop_reason = 'provider_down';
      await transition(item, 'retry_later', e.code);
    } else if (
      e.code === 'outcome_unknown' ||
      (e.code === 'cancelled' && e.info.retry === 'may_spend_quota')
    ) {
      quotaInvalid = true;
      await transition(item, 'retry_later', 'outcome_unknown');
    } else if (e.code === 'auth_failed') {
      state!.run.stop_reason = 'auth_failed';
      await transition(item, 'retry_later', 'auth_backoff');
    } else if (e.code === 'credentials_missing') {
      if (source) disabled.set(source, 'config');
      if (p.settings.sources.every((s) => disabled.has(s))) state!.run.stop_reason = 'config';
      await transition(item, 'failed', 'provider_error');
    } else if (e.code === 'output_refused') {
      if (e.info.detail?.destination_occupied || e.message.includes('Destination already holds'))
        await transition(item, 'needs_choice', 'destination_occupied');
      else {
        state!.run.stop_reason = 'output_refused';
        await transition(item, 'failed', 'output_refused');
      }
    } else if (e.code === 'not_found') await transition(item, 'not_found', 'gone');
    else if (['provider_error', 'integrity_mismatch'].includes(e.code))
      await transition(item, 'failed', e.code);
    else {
      internalStreak++;
      if (internalStreak >= 3) state!.run.stop_reason = 'internal';
      await transition(item, 'failed', 'internal');
    }
  };
  const consumeChoices = async () => {
    const choices: Record<string, string> = Object.create(null);
    const signatures: Record<string, string> = Object.create(null);
    let text = '';
    try {
      text = await fs.readFile(path.join(p.dir, 'choices.txt'), 'utf8');
    } catch (e: any) {
      if (e.code !== 'ENOENT') throw e;
    }
    for (const [index, line] of text.split(/\r?\n/).entries()) {
      const m = line.match(/^(".*"|\S+)\s+(a|b|c|skip|keep|retry)$/);
      if (m) {
        let id = m[1]!;
        if (id.startsWith('"')) {
          try {
            id = JSON.parse(id);
          } catch {
            continue;
          }
        }
        choices[id] = m[2]!;
        signatures[id] = sha(index + ' ' + line);
      }
    }
    const direct = options.choices ?? {};
    Object.assign(choices, direct);
    options.choices = {};
    for (const [id, choice] of Object.entries(choices)) {
      const item = Object.hasOwn(state!.items, id) ? state!.items[id] : undefined;
      if (!item || item.state === 'dropped' || item.state === 'duplicate') continue;
      // Keep an audit cursor so an old mailbox entry cannot replay on every run.
      const signature = signatures[id];
      if (!Object.hasOwn(direct, id) && (item as any).choice_signature === signature) continue;
      (item as any).choice_signature = signature;
      item.choice = choice;
    }
  };
  const processItem = async (item: Item) => {
    current = item;
    const w = item.want;
    item.counts = { searches: 0, details: 0, downloads: 0 };
    let choice = item.choice;
    delete item.choice;
    if (choice === 'skip') {
      await transition(item, 'skipped');
      return;
    }
    if (choice === 'retry') {
      choice = undefined;
      await transition(item, 'pending');
    }
    if (choice === 'keep') {
      if (item.path) {
        try {
          item.sha256 = sha(await fs.readFile(item.path));
          await transition(item, 'fetched', 'kept');
          await appendReceipt(item);
          return;
        } catch {
          /* Missing file cannot be kept. */
        }
      }
      await transition(item, 'needs_choice', 'choice_unavailable');
      return;
    }
    let selected: Candidate | undefined;
    const stored = choice
      ? item.options?.['abc'.indexOf(choice)]
      : item.state === 'waiting_quota'
        ? item.candidate
        : undefined;
    if (choice && !stored) {
      await transition(item, 'needs_choice', 'choice_unavailable');
      return;
    }
    await transition(item, 'pending');
    let rows: Candidate[] = [];
    if (stored) {
      let found = await search(item, stored.source, mainTitle(w.title), w.author);
      selected = found.find((c) => same(c, stored));
      if (!selected) {
        found = await search(item, stored.source, mainTitle(stored.title), stored.author, 50);
        selected = found.find((c) => same(c, stored));
      }
      rows = found;
      if (!selected && choice) {
        await transition(item, 'needs_choice', 'choice_unavailable');
        return;
      }
      if (!selected) item.why_chosen = 'rematched; ' + (item.why_chosen ?? '');
    }
    let decision: Decision | undefined = selected
      ? {
          action: 'download',
          state: 'fetched',
          reason: 'chosen',
          candidate: classify(w, selected),
          candidates: [classify(w, selected)],
        }
      : undefined;
    if (selected && !choice) {
      await details(item, [selected]);
      decision = decide(w, [selected], p.settings);
    }
    if (!selected) {
      for (const source of p.settings.sources) {
        if (disabled.has(source)) continue;
        try {
          const found = await search(item, source, mainTitle(w.title), w.author);
          await details(item, found);
          rows.push(...found);
          const d = decide(w, found, p.settings);
          if (['download', 'probe'].includes(d.action)) {
            decision = d;
            break;
          }
        } catch (e) {
          const failure = classifyFailure(e, 'search', source);
          if (failure.code === 'credentials_missing') {
            disabled.set(source, 'config');
            continue;
          }
          if (failure.code === 'breaker_open' && failure.info.detail?.reason === 'auth_backoff') {
            disabled.set(source, 'auth_backoff');
            state!.run.stop_reason = 'auth_backoff';
            continue;
          }
          throw failure;
        }
      }
      if (!rows.length && w.author && item.counts.searches < 4) {
        const source = p.settings.sources.find((s) => !disabled.has(s));
        if (source) {
          rows = await search(item, source, mainTitle(w.title));
          await details(item, rows);
        }
      }
      decision ??= decide(w, rows, p.settings);
    }
    if (!rows.length && p.settings.sources.every((s) => disabled.has(s))) {
      state!.run.stop_reason = state!.run.stop_reason ?? 'config';
      await transition(
        item,
        'retry_later',
        state!.run.stop_reason === 'auth_backoff' ? 'auth_backoff' : 'provider_unreachable',
      );
      return;
    }
    const d = decision!;
    item.options = rank(
      rows.map((c) => classify(w, c)),
      w,
      p.settings,
    )
      .slice(0, 3)
      .map(durableCandidate);
    if (!['download', 'probe'].includes(d.action)) {
      await transition(item, d.action === 'ask' ? 'needs_choice' : 'not_found', d.reason);
      return;
    }
    const candidates = d.candidates;
    const top = d.candidate!;
    for (
      let attempt = 0;
      attempt < Math.min(candidates.length, w.mode === 'any' ? 2 : 1);
      attempt++
    ) {
      const c = candidates[attempt]!;
      item.candidate = durableCandidate(c);
      item.why_chosen =
        (item.why_chosen?.startsWith('rematched') ? 'rematched; ' : '') +
        whyChosen(c, candidates, w, p.settings);
      if (options.dry_run) {
        item.dry_run = true;
        await transition(
          item,
          'fetched',
          d.reason === 'constraint_unverified' ? 'exact_match' : d.reason,
        );
        return;
      }
      delete item.dry_run;
      if (p.settings.max_downloads !== undefined && issued >= p.settings.max_downloads) {
        state!.run.stop_reason = 'quota';
        await transition(item, 'waiting_quota', 'max_downloads');
        return;
      }
      if (c.source === 'zlibrary') {
        if (quotaInvalid || (zIssued > 0 && zIssued % 50 === 0)) await readQuota();
        if (
          quotaExhausted ||
          (state!.quota?.remaining !== undefined && state!.quota.remaining <= p.settings.reserve)
        ) {
          state!.run.stop_reason = 'quota';
          await transition(
            item,
            'waiting_quota',
            quotaExhausted ? 'quota_exhausted' : 'quota_reserve',
          );
          return;
        }
      }
      // Persist an interrupted checkpoint before issuing. The bridge's intent receipt owns transfer recovery.
      await transition(item, 'retry_later', 'interrupted');
      try {
        const result = await invoke('download', async () => {
          try {
            if (item.counts.downloads >= 2)
              throw new ToolFailure('provider_error', 'Per-item transfer cap reached.', {
                detail: { request_issued: false },
              });
            if (p.settings.max_downloads !== undefined && issued >= p.settings.max_downloads)
              throw new ToolFailure('quota_exhausted', 'Run transfer cap reached.', {
                detail: { reason: 'max_downloads', request_issued: false },
              });
            if (c.source === 'zlibrary' && quotaInvalid) {
              await readQuota();
              if (
                state!.quota?.remaining !== undefined &&
                state!.quota.remaining <= p.settings.reserve
              )
                throw new ToolFailure('quota_exhausted', 'Quota reserve reached.', {
                  detail: { reason: 'quota_reserve', request_issued: false },
                });
            }
            const result = await tools.acquireRef(
              c.ref!,
              {
                output_dir: p.settings.output_dir,
                request: { item_id: w.item_id, why_chosen: item.why_chosen },
              },
              { signal },
            );
            if (!result.transfer_skipped) {
              item.counts.downloads++;
              issued++;
              if (c.source === 'zlibrary') zIssued++;
            }
            return result;
          } catch (error) {
            const e = classifyFailure(error, 'download', c.source);
            if (
              e.info.detail?.request_issued !== false &&
              !['breaker_open', 'credentials_missing', 'auth_failed', 'ref_unavailable'].includes(
                e.code,
              )
            ) {
              item.counts.downloads++;
              issued++;
              if (c.source === 'zlibrary') {
                zIssued++;
                quotaInvalid = true;
              }
            }
            throw e;
          }
        });
        item.path = result.path;
        item.record = result.record;
        try {
          const record = JSON.parse(await fs.readFile(result.record, 'utf8'));
          item.sha256 = record.sha256;
        } catch {
          item.sha256 = sha(await fs.readFile(result.path));
        }
        if (result.quota_estimate) state!.quota = { ...result.quota_estimate };
        downStreak = 0;
        internalStreak = 0;
        const request = {
          ...w,
          ...(c.orientation === 'swapped' ? { title: w.author, author: w.title } : {}),
        };
        const checkKey = sha(
          JSON.stringify([request, c.language, extractVolume(c.title, c.series).volume]),
        );
        const cached = state!.edition_cache[item.sha256!]?.[checkKey];
        let check = cached;
        if (!check) {
          try {
            check = await tools.inspectFile(
              {
                path: result.path,
                request,
                language: c.language,
                volume: extractVolume(c.title, c.series).volume,
              },
              { signal },
            );
          } catch {
            if (signal.aborted)
              throw new ToolFailure('cancelled', 'Run interrupted.', { retry: 'safe' });
            check = { status: 'unverified', reason: 'unreadable', found: {}, checks: {} };
          }
          (state!.edition_cache[item.sha256!] ??= {})[checkKey] = check;
        }
        item.edition_check = check;
        if (check.status === 'mismatch') {
          await transition(item, 'needs_choice', 'edition_check_mismatch');
          return;
        }
        if (d.action === 'probe' && !c.missing?.every((k) => check.checks[k] === 'match')) {
          await transition(item, 'needs_choice', 'constraint_unverified');
          return;
        }
        item.candidate = durableCandidate({ ...c, evidence: c.evidence ?? { checked: 'row' } });
        if (d.action === 'probe')
          item.candidate.evidence = { ...item.candidate.evidence, checked: 'file' };
        await transition(
          item,
          result.transfer_skipped ? 'have' : 'fetched',
          result.transfer_skipped
            ? 'receipt_identity'
            : d.reason === 'constraint_unverified'
              ? 'exact_match'
              : d.reason,
        );
        await appendReceipt(item);
        return;
      } catch (error) {
        const e = classifyFailure(error, 'download', c.source);
        if (
          w.mode === 'any' &&
          attempt === 0 &&
          candidates.length > 1 &&
          ['provider_error', 'integrity_mismatch', 'not_found'].includes(e.code) &&
          item.counts.downloads < 2
        )
          continue;
        if (e.code === 'ref_unavailable' && item.counts.searches < 4) {
          const found = await search(item, c.source, mainTitle(c.title), c.author, 50);
          const replacement = found.find((r) => same(r, c));
          if (replacement) {
            c.ref = replacement.ref;
            attempt--;
            if ((item as any).ref_researched) throw e;
            (item as any).ref_researched = true;
            continue;
          }
        }
        await handleFailure(item, e, c.source);
        return;
      }
    }
    item.candidate = durableCandidate(top);
  };
  const appendReceipt = async (item: Item) => {
    await fs.appendFile(
      path.join(p.dir, 'receipts.v1.jsonl'),
      JSON.stringify({
        item_id: item.want.item_id,
        line: item.line,
        want: item.want,
        state: item.state,
        reason: item.reason,
        record: item.record,
        path: item.path,
        sha256: item.sha256,
        source: item.candidate?.source,
        identifiers: item.candidate?.identifiers,
        why_chosen: item.why_chosen,
        edition_check: item.edition_check,
        extra: item.want.extra,
      }) + '\n',
      { mode: 0o600 },
    );
  };
  try {
    state = reconcile(await readState(p.dir), p.parsed.items, p.list, sha(p.text), p.settings);
    for (const item of Object.values(state.items)) {
      if (
        options.redo?.includes(item.want.item_id) ||
        (options.retry_not_found && item.state === 'not_found') ||
        (options.retry_failed && item.state === 'failed') ||
        item.dry_run
      ) {
        item.state = 'pending';
        item.reason = undefined;
        delete item.dry_run;
      }
    }
    await save(p.dir, state);
    await consumeChoices();
    const index = await receiptIndex(p.settings.output_dir);
    for (const item of Object.values(state.items)) {
      if (
        ['dropped', 'duplicate', 'skipped', 'needs_choice'].includes(item.state) ||
        item.choice ||
        options.redo?.includes(item.want.item_id)
      )
        continue;
      const r = await verifiedReceipt(index.get(item.want.item_id), p.settings.output_dir);
      if (r) {
        Object.assign(item, { record: r.record, path: r.path, sha256: r.sha256 });
        await transition(item, 'have', 'receipt_item');
        await appendReceipt(item);
      } else if (['fetched', 'have'].includes(item.state)) {
        await transition(item, 'pending');
      }
    }
    if (
      !Object.values(state.items).every((i) =>
        ['fetched', 'have', 'skipped', 'dropped', 'duplicate', 'not_found', 'failed'].includes(
          i.state,
        ),
      )
    )
      await readQuota();
    const ordered = Object.values(state.items).sort(
      (a, b) =>
        (a.state === 'waiting_quota' ? 0 : 1) - (b.state === 'waiting_quota' ? 0 : 1) ||
        a.line - b.line,
    );
    for (const item of ordered) {
      await consumeChoices();
      if (!['pending', 'retry_later', 'waiting_quota'].includes(item.state) && !item.choice)
        continue;
      if (signal.aborted) {
        state.run.stop_reason = deadline ? 'deadline' : 'interrupted';
        break;
      }
      try {
        await processItem(item);
        if (!['provider_unreachable', 'provider_timeout'].includes(item.reason ?? ''))
          downStreak = 0;
        if (item.reason !== 'internal') internalStreak = 0;
      } catch (e) {
        await handleFailure(item, e, item.candidate?.source);
      }
      if (
        [
          'breaker',
          'provider_down',
          'auth_failed',
          'config',
          'output_refused',
          'internal',
          'interrupted',
          'deadline',
        ].includes(state.run.stop_reason ?? '')
      )
        break;
    }
    state.run.status = 'done';
    await save(p.dir, state);
    await writeReports(state, p.dir);
    return summary(state, p.dir);
  } catch (e) {
    if (state) {
      if (signal.aborted) {
        state.run.stop_reason = deadline ? 'deadline' : 'interrupted';
        if (current) await transition(current, 'retry_later', 'interrupted');
      } else {
        state.run.stop_reason =
          classifyFailure(e, 'acquire_list').code === 'auth_failed' ? 'auth_failed' : 'config';
      }
      state.run.status = 'done';
      await save(p.dir, state);
      await writeReports(state, p.dir);
      if (signal.aborted || e instanceof ToolFailure) return summary(state, p.dir);
    }
    throw e;
  } finally {
    if (timer) clearTimeout(timer);
    options.signal?.removeEventListener('abort', externalAbort);
    await unlock();
  }
}
