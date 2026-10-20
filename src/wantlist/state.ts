import * as fs from 'node:fs/promises';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { ToolFailure } from '../lib/tool-errors.js';
import type { Candidate, ListState, Item, Want, Settings } from './types.js';
export const now = () => new Date().toISOString();
export const sha = (data: string | Buffer) => createHash('sha256').update(data).digest('hex');
export const stateDirectory = (listPath: string, override?: string) =>
  path.resolve(
    override ?? path.join(path.dirname(listPath), path.parse(listPath).name + '.wantlist'),
  );
export function durableCandidate(c: Candidate): Candidate {
  const copy = { ...c };
  delete copy.ref;
  delete copy.description;
  return copy;
}
export async function atomicJSON(file: string, value: unknown) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const temporary = file + '.' + randomUUID() + '.tmp';
  const h = await fs.open(temporary, 'wx', 0o600);
  try {
    await h.writeFile(JSON.stringify(value, (_k, v) => (_k === 'ref' ? undefined : v), 2) + '\n');
    await h.sync();
  } finally {
    await h.close();
  }
  try {
    await fs.rename(temporary, file);
    const d = await fs.open(path.dirname(file), 'r');
    try {
      await d.sync();
    } finally {
      await d.close();
    }
  } catch (e) {
    await fs.unlink(temporary).catch(() => {});
    throw e;
  }
}
export async function readState(dir: string): Promise<ListState | undefined> {
  try {
    const state = JSON.parse(await fs.readFile(path.join(dir, 'state.v1.json'), 'utf8'));
    if (state.state_version !== 1 || !state.items || !state.run) throw new Error('schema');
    return state;
  } catch (e: any) {
    if (e.code === 'ENOENT') return undefined;
    throw new ToolFailure(
      'invalid_argument',
      'Cannot read want-list state; preserve it for diagnosis.',
    );
  }
}
export async function takeLock(dir: string): Promise<(() => Promise<void>) | undefined> {
  await fs.mkdir(dir, { recursive: true });
  const file = path.join(dir, 'run.lock');
  const token = randomUUID();
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const h = await fs.open(file, 'wx', 0o600);
      try {
        await h.writeFile(JSON.stringify({ pid: process.pid, at: now(), token }));
        await h.sync();
      } finally {
        await h.close();
      }
      return async () => {
        try {
          if (JSON.parse(await fs.readFile(file, 'utf8')).token === token) await fs.unlink(file);
        } catch (e: any) {
          if (e.code !== 'ENOENT') throw e;
        }
      };
    } catch (e: any) {
      if (e.code !== 'EEXIST') throw e;
    }
    const before = await fs.stat(file).catch(() => undefined);
    if (!before) continue;
    let existing: any;
    try {
      existing = JSON.parse(await fs.readFile(file, 'utf8'));
    } catch {
      return undefined;
    }
    if (!Number.isInteger(existing.pid) || existing.pid < 1) return undefined;
    try {
      process.kill(existing.pid, 0);
      return undefined;
    } catch (e: any) {
      if (e.code !== 'ESRCH') return undefined;
    }
    const after = await fs.stat(file).catch(() => undefined);
    if (after && before.ino === after.ino && before.mtimeMs === after.mtimeMs)
      await fs.unlink(file).catch(() => {});
  }
  return undefined;
}
export function reconcile(
  old: ListState | undefined,
  wants: Want[],
  file: string,
  hash: string,
  settings: Settings,
): ListState {
  const at = now();
  const items: Record<string, Item> = Object.create(null);
  for (const w of wants) {
    const key = w.duplicate ? w.item_id + '#duplicate:' + w.line : w.item_id;
    const prior = old && Object.hasOwn(old.items, key) ? old.items[key] : undefined;
    items[key] = prior
      ? { ...prior, want: w, line: w.line, mode: w.mode }
      : {
          line: w.line,
          want: w,
          mode: w.mode,
          state: w.duplicate ? 'duplicate' : 'pending',
          counts: { searches: 0, details: 0, downloads: 0 },
          history: [],
        };
    if (w.duplicate) {
      items[key]!.state = 'duplicate';
      items[key]!.reason = undefined;
    } else if (items[key]!.state === 'dropped') {
      items[key]!.state = 'pending';
      items[key]!.reason = undefined;
    }
  }
  for (const [key, item] of Object.entries(old?.items ?? {}))
    if (!Object.hasOwn(items, key))
      items[key] = {
        ...item,
        state: 'dropped',
        reason: undefined,
        history: [...item.history, { at, state: 'dropped' }],
      };
  return {
    state_version: 1,
    list: { path: file, sha256: hash, parsed_at: at },
    settings,
    run: { pid: process.pid, started_at: at, updated_at: at, status: 'running' },
    items,
    edition_cache: old?.edition_cache ?? {},
  };
}
export async function receiptIndex(directory: string): Promise<Map<string, any[]>> {
  const index = new Map<string, any[]>();
  const files = await fs.readdir(directory).catch((e) => {
    if (e.code === 'ENOENT') return [];
    throw e;
  });
  for (const name of files.filter((f) => f.endsWith('.acq.json'))) {
    try {
      const file = path.join(directory, name);
      const r = JSON.parse(await fs.readFile(file, 'utf8'));
      if (
        r.record_version === 1 &&
        r.state === 'complete' &&
        typeof r.request?.item_id === 'string' &&
        /^[a-f0-9]{64}$/.test(r.sha256)
      )
        index.set(r.request.item_id, [
          ...(index.get(r.request.item_id) ?? []),
          { ...r, record: file },
        ]);
    } catch {
      /* An incomplete/foreign sidecar is not authority. */
    }
  }
  return index;
}
export async function verifiedReceipt(
  records: any[] | undefined,
  output: string,
): Promise<any | undefined> {
  const root = await fs.realpath(output).catch(() => undefined);
  if (!root) return;
  for (const r of records ?? []) {
    try {
      const file = await fs.realpath(r.path);
      const relative = path.relative(root, file);
      if (relative.startsWith('..') || path.isAbsolute(relative)) continue;
      const data = await fs.readFile(file);
      if (data.length === r.bytes && sha(data) === r.sha256) return { ...r, path: file };
    } catch {
      /* Missing or changed file must be acquired again. */
    }
  }
}
export async function save(dir: string, state: ListState) {
  state.run.updated_at = now();
  await atomicJSON(path.join(dir, 'state.v1.json'), state);
}
