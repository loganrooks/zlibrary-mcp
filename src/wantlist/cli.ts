#!/usr/bin/env node
import { parseArgs } from 'node:util';
import path from 'node:path';
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { AcquisitionTools } from '../lib/acquisition-tools.js';
import { invokeAcquisitionBridge } from '../lib/zlibrary-api.js';
import { errorEnvelope, ToolFailure } from '../lib/tool-errors.js';
import { runList, recordChoices } from './worker.js';
import { readState, stateDirectory } from './state.js';
import { summary, plainSummary, exitCode } from './summary.js';
import type { RunOptions, Source } from './types.js';

export async function main(argv = process.argv.slice(2)): Promise<number> {
  let json = false;
  try {
    const { values, positionals } = parseArgs({
      args: argv,
      allowPositionals: true,
      strict: true,
      options: {
        out: { type: 'string' },
        sources: { type: 'string' },
        mode: { type: 'string' },
        formats: { type: 'string' },
        language: { type: 'string' },
        reserve: { type: 'string' },
        'max-downloads': { type: 'string' },
        'max-minutes': { type: 'string' },
        'no-probe': { type: 'boolean' },
        'dry-run': { type: 'boolean' },
        'retry-not-found': { type: 'boolean' },
        'retry-failed': { type: 'boolean' },
        redo: { type: 'string', multiple: true },
        state: { type: 'string' },
        json: { type: 'boolean' },
        help: { type: 'boolean' },
      },
    });
    json = Boolean(values.json);
    if (values.help) {
      process.stdout.write(
        'zlibrary-wantlist run <list> [--sources libgen,zlibrary] [--out DIR] [--dry-run] [--json]\nzlibrary-wantlist status <list> [--state DIR] [--json]\nzlibrary-wantlist choose <list> <item_id> <a|b|c|skip|keep|retry> [--state DIR]\nSee docs/wantlist.md for all options.\n',
      );
      return 0;
    }
    const [command, file, id, choice] = positionals;
    if (
      !file ||
      !['run', 'status', 'choose'].includes(command ?? '') ||
      (command === 'choose' ? positionals.length !== 4 : positionals.length !== 2)
    )
      throw new ToolFailure(
        'invalid_argument',
        'Expected run <list>, status <list>, or choose <list> <item_id> <choice>.',
      );
    const dir = stateDirectory(path.resolve(file), values.state);
    if (command === 'choose') {
      await recordChoices(dir, { [id!]: choice! });
      process.stdout.write(`Choice recorded for ${id}. Run the list to apply it.\n`);
      return 0;
    }
    if (command === 'status') {
      const state = await readState(dir);
      if (!state) throw new ToolFailure('invalid_argument', 'No saved state for this list.');
      const result = summary(state, dir);
      process.stdout.write(json ? JSON.stringify(result) + '\n' : plainSummary(result));
      return 0;
    }
    const controller = new AbortController();
    let signals = 0;
    const onSignal = () => {
      if (++signals === 1) controller.abort();
      else process.exit(2);
    };
    process.on('SIGINT', onSignal);
    process.on('SIGTERM', onSignal);
    try {
      const split = (s: string) =>
        s
          .split(',')
          .map((v) => v.trim())
          .filter(Boolean);
      const opts: RunOptions = {
        path: file,
        state: values.state,
        output_dir: values.out,
        sources: values.sources ? (split(values.sources) as Source[]) : undefined,
        mode: values.mode as RunOptions['mode'],
        formats: values.formats ? split(values.formats) : undefined,
        language: values.language,
        reserve: values.reserve === undefined ? undefined : Number(values.reserve),
        max_downloads:
          values['max-downloads'] === undefined ? undefined : Number(values['max-downloads']),
        max_minutes:
          values['max-minutes'] === undefined ? undefined : Number(values['max-minutes']),
        probe: !values['no-probe'],
        dry_run: values['dry-run'],
        retry_not_found: values['retry-not-found'],
        retry_failed: values['retry-failed'],
        redo: values.redo,
        signal: controller.signal,
      };
      const result = await runList(new AcquisitionTools(invokeAcquisitionBridge), opts);
      process.stdout.write(json ? JSON.stringify(result) + '\n' : plainSummary(result));
      return exitCode(result);
    } finally {
      process.removeListener('SIGINT', onSignal);
      process.removeListener('SIGTERM', onSignal);
    }
  } catch (error) {
    const envelope = errorEnvelope(error, 'acquire_list');
    if (json) process.stdout.write(JSON.stringify(envelope) + '\n');
    else process.stderr.write(envelope.error.message + '\n');
    return 1;
  }
}
const canonical = (p: string) => {
  try {
    return realpathSync(p);
  } catch {
    return path.resolve(p);
  }
};
if (process.argv[1] && canonical(process.argv[1]) === canonical(fileURLToPath(import.meta.url)))
  void main().then((code) => {
    process.exitCode = code;
  });
