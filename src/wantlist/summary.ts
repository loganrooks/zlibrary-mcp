import path from 'node:path';
import * as fs from 'node:fs/promises';
import type { ListState, ItemState } from './types.js';
const states: ItemState[] = [
  'fetched',
  'have',
  'needs_choice',
  'waiting_quota',
  'retry_later',
  'not_found',
  'failed',
  'skipped',
  'pending',
  'dropped',
  'duplicate',
];
const wantText = (i: any) => i.want.title + (i.want.author ? ' — ' + i.want.author : '');
export function summary(state: ListState, dir: string, status = state.run.status): any {
  const items = Object.values(state.items);
  const counts = Object.fromEntries(
    states.map((s) => [s, items.filter((i) => i.state === s).length]),
  );
  const reply: any = {
    list: state.list.path,
    status,
    ...(state.run.stop_reason ? { stop_reason: state.run.stop_reason } : {}),
    counts,
    ...(state.quota ? { quota: state.quota } : {}),
    files: Object.fromEntries(
      ['state', 'receipts', 'needs_choice', 'report'].map((k, i) => [
        k,
        path.join(dir, ['state.v1.json', 'receipts.v1.jsonl', 'needs_choice.md', 'report.md'][i]!),
      ]),
    ),
  };
  for (const key of ['needs_choice', 'not_found', 'failed']) {
    const all = items.filter((i) => i.state === key);
    reply[key] = all.slice(0, 10).map((i) => ({
      item_id: i.want.item_id,
      line: i.line,
      want: wantText(i),
      reason: i.reason,
      ...(key === 'needs_choice'
        ? {
            options: (i.options ?? []).slice(0, 3).map((c, j) =>
              Object.fromEntries(
                Object.entries({
                  key: 'abc'[j],
                  title: c.title,
                  author: c.author,
                  year: c.year,
                  language: c.language,
                  format: c.format,
                  source: c.source,
                }).filter(([, v]) => v !== undefined),
              ),
            ),
          }
        : {}),
    }));
    if (all.length > 10) (reply.more ??= {})[key] = all.length - 10;
  }
  return reply;
}
const cell = (s: unknown) =>
  String(s ?? '')
    .replaceAll('|', '\\|')
    .replace(/[\r\n]+/g, ' ');
export async function writeReports(state: ListState, dir: string) {
  const items = Object.values(state.items);
  const counts = summary(state, dir).counts;
  const report =
    `# Want-list report\n\n${Object.entries(counts)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ')}\n\n| Line | Want | State | Reason | File |\n|---|---|---|---|---|\n` +
    items
      .map(
        (i) =>
          `| ${i.line} | ${cell(wantText(i))} | ${i.state} | ${i.reason ?? ''} | ${cell(i.path)} |`,
      )
      .join('\n') +
    '\n';
  let needs = '# Choices\n\n';
  for (const i of items.filter((i) => i.state === 'needs_choice')) {
    needs += `## ${cell(i.want.item_id)} — line ${i.line}\n\n${cell(wantText(i))}\n\n${i.reason?.replaceAll('_', ' ')}\n\n`;
    for (const [j, c] of (i.options ?? []).slice(0, 3).entries())
      needs += `${'abc'[j]}) ${cell([c.title, c.author, c.year, c.language, c.format, c.pages, c.translator, c.edition, c.source].filter((v) => v !== undefined).join(' · '))}\n\n`;
    const quote = (s: string) => "'" + s.replaceAll("'", "'\\''") + "'";
    needs += `Answer: \`zlibrary-wantlist choose ${quote(state.list.path)} ${quote(i.want.item_id)} a --state ${quote(dir)}\`\n\nOptions: ${(
      i.options ?? []
    )
      .slice(0, 3)
      .map((_, j) => 'abc'[j])
      .join(', ')}, ${i.path ? 'keep, ' : ''}skip, retry.\n\n`;
  }
  await fs.writeFile(path.join(dir, 'needs_choice.md'), needs, { mode: 0o600 });
  await fs.writeFile(path.join(dir, 'report.md'), report, { mode: 0o600 });
}
export function plainSummary(s: any): string {
  return `${s.list}: ${Object.values(s.counts).reduce((a: any, b: any) => a + b, 0)} items. ${s.counts.fetched} fetched, ${s.counts.have} already here, ${s.counts.needs_choice} need you, ${s.counts.not_found} not found.${s.quota ? ` ${s.quota.source} quota ${s.quota.remaining ?? 'unknown'} (${s.quota.basis}).` : ''}\n${s.stop_reason ? 'Stopped: ' + s.stop_reason + '\n' : ''}${s.needs_choice.map((i: any) => `line ${i.line} ${i.want}: ${i.reason}\n`).join('')}Details: ${s.files.report}\n`;
}
export function exitCode(s: any): number {
  return !s.stop_reason
    ? s.status === 'running_elsewhere'
      ? 0
      : s.counts?.retry_later || s.counts?.waiting_quota || s.counts?.pending
        ? 2
        : 0
    : ['auth_failed', 'config', 'output_refused', 'internal'].includes(s.stop_reason)
      ? 1
      : 2;
}
