import { z } from 'zod';
import type { Tool } from '@modelcontextprotocol/sdk/types.js';
import type { AcquisitionTools } from '../lib/acquisition-tools.js';
import { INPUTS } from '../lib/acquisition-tools.js';
import { errorEnvelope, ToolFailure } from '../lib/tool-errors.js';
import { runList, prepare } from './worker.js';
import { readState, reconcile, sha } from './state.js';
import { summary } from './summary.js';
import type { RunOptions } from './types.js';

export const LIST_INPUT = z
  .object({
    path: z.string().min(1).optional(),
    items: z
      .array(z.union([z.string().min(1), z.record(z.string(), z.unknown())]))
      .min(1)
      .max(200)
      .optional(),
    output_dir: z.string().min(1).optional(),
    sources: INPUTS.search.shape.sources,
    mode: z.enum(['any', 'exact']).optional(),
    choices: z
      .record(z.string(), z.enum(['a', 'b', 'c', 'skip', 'keep', 'retry']))
      .refine((v) => Object.keys(v).length <= 50)
      .optional(),
    dry_run: z.boolean().optional(),
    wait_s: z.number().int().min(0).max(50).default(20),
  })
  .strict()
  .refine((v) => Boolean(v.path) !== Boolean(v.items), 'Pass path or items, exactly one.');
const json = z.toJSONSchema(LIST_INPUT);
delete json.$schema;
export const LIST_TOOL: Tool = {
  name: 'acquire_list',
  description:
    'Opt-in extra. Fetch a reading list: pass a server list path or up to 200 items ("Title — Author"). Items are matched by stated rules, downloaded with receipts and quota rules, or queued with a reason. Call again for progress or choices; it never starts a second run. Details are server files; replies list only what needs you.',
  inputSchema: json as Tool['inputSchema'],
  annotations: {
    readOnlyHint: false,
    destructiveHint: false,
    idempotentHint: false,
    openWorldHint: true,
  },
};
export function wantlistEnabled() {
  return (process.env.ZLIBRARY_EXTRAS ?? '')
    .split(',')
    .map((s) => s.trim())
    .includes('wantlist');
}

export class ListRuns {
  private active = new Map<
    string,
    { promise: Promise<any>; options: RunOptions; controller: AbortController }
  >();
  constructor(private tools: AcquisitionTools) {}
  stop() {
    for (const entry of this.active.values()) entry.controller.abort();
  }
  async call(raw: unknown): Promise<any> {
    try {
      const parsed = LIST_INPUT.safeParse(raw);
      if (!parsed.success)
        throw new ToolFailure('invalid_argument', 'Arguments do not match acquire_list schema.');
      const { wait_s, ...args } = parsed.data;
      const p = await prepare(args);
      let entry = this.active.get(p.dir);
      if (entry) {
        entry.options.choices = { ...entry.options.choices, ...args.choices };
      } else {
        const controller = new AbortController();
        const options: RunOptions = { ...args, signal: controller.signal };
        const promise = runList(this.tools, options).catch((e) => errorEnvelope(e, 'acquire_list'));
        entry = { promise, options, controller };
        this.active.set(p.dir, entry);
        const registered = entry;
        void promise.finally(() => {
          if (this.active.get(p.dir) === registered) this.active.delete(p.dir);
        });
      }
      let timer: ReturnType<typeof setTimeout> | undefined;
      const result = await Promise.race([
        entry.promise,
        new Promise<undefined>((resolve) => {
          timer = setTimeout(() => resolve(undefined), wait_s * 1000);
        }),
      ]);
      if (timer) clearTimeout(timer);
      if (result) return result;
      const state =
        (await readState(p.dir)) ??
        reconcile(undefined, p.parsed.items, p.list, sha(p.text), p.settings);
      return summary(state, p.dir, state.run.status === 'done' ? 'done' : 'running');
    } catch (e) {
      return errorEnvelope(e, 'acquire_list');
    }
  }
}
