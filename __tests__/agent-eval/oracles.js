import { readFile, realpath } from 'node:fs/promises';
import path from 'node:path';
import { evaluateAnswer } from './answers.js';

export function dataOf(reply) {
  if (reply.structuredContent) {
    const data = reply.structuredContent;
    return Object.keys(data).length === 1 && Array.isArray(data.items) ? data.items : data;
  }
  try {
    return JSON.parse(reply.content?.find((x) => x.type === 'text')?.text ?? '{}');
  } catch {
    return {};
  }
}
export function rowsOf(data) {
  return Array.isArray(data) ? data : (data.rows ?? data.books ?? data.items ?? []);
}
export const identity = (row) =>
  String(row?.id ?? row?.identifiers?.zlibrary_id ?? '') || row?.title;
export const isGraver = (row) =>
  String(row?.id) === '202' || /letters on ethics/i.test(row?.title ?? '');
export const isCampbell = (row) =>
  String(row?.id) === '203' || /letters from a stoic/i.test(row?.title ?? '');
export const isSearch = (name) => /^(search|full_text)/.test(name);
export const isDownload = (name) => ['download', 'download_book_to_file'].includes(name);
const allowed = {
  T1: ['search', 'download', 'get_book'],
  T2: ['search', 'detail'],
  T3: ['download'],
  T4: ['limits'],
  T5: [],
  T6: ['search'],
  T7: ['history'],
  T8: ['search', 'download'],
  T9: ['search', 'download'],
  T10: ['search', 'detail', 'download'],
  T11: ['limits', 'search', 'history'],
  T12: ['search'],
};
const allowedA = {
  T1: ['search_books', 'search_multi_source', 'download_book_to_file'],
  T2: ['search_books', 'get_book_metadata'],
  T3: ['download_book_to_file'],
  T4: ['get_download_limits'],
  T5: [],
  T6: ['search_books'],
  T7: ['get_download_history'],
  T8: ['search_multi_source', 'download_book_to_file'],
  T9: ['search_books', 'search_multi_source', 'download_book_to_file'],
  T10: [],
  T11: ['get_download_limits', 'search_multi_source', 'get_download_history'],
  T12: ['search_by_author', 'search_books'],
};
const category = (name) =>
  isDownload(name)
    ? 'download'
    : isSearch(name)
      ? 'search'
      : /limits/.test(name)
        ? 'limits'
        : /history/.test(name)
          ? 'history'
          : /metadata|get_book$/.test(name)
            ? 'detail'
            : 'other';

// Mark decisions, not only tool names: every marked value retains call/arguments.
export async function scoreTask({
  task,
  arm,
  trace,
  final = '',
  quotaSpent = 0,
  providerEvents = [],
  downloads,
  remainingBefore,
  context = {},
}) {
  const wrong = [];
  const mark = (reason, c) => wrong.push({ reason, tool: c?.name, arguments: c?.args });
  const b = arm.build === 'B';
  const selected = (c) => c.selected ?? c.args?.bookDetails ?? {};
  for (const c of trace) {
    const a = c.args ?? {},
      kind = category(c.name),
      row = selected(c);
    if (
      !(task.id === 'T7' && !arm.history ? [] : allowed[task.id]).includes(kind) ||
      (!b && !allowedA[task.id].includes(c.name))
    )
      mark('off-oracle tool', c);
    if (c.error || c.reply?.isError || dataOf(c.reply ?? {}).error) mark('invalid/error call', c);
    if (kind === 'download') {
      if (
        task.id === 'T1' &&
        (!/persuasion/i.test(row.title ?? '') || (row.format ?? row.extension) !== 'epub')
      )
        mark('wrong title/format', c);
      if (['T3', 'T10'].includes(task.id) && !isGraver(row)) mark('wrong edition', c);
      if (task.id === 'T8' && !/glass orchard/i.test(row.title ?? '')) mark('wrong title', c);
      if (!c.observedSelection)
        mark('fabricated/modified row or ref not observed in this session', c);
      if (
        task.id === 'T10' &&
        b &&
        (a.filename !== 'seneca.pdf' ||
          path.resolve(a.output_dir ?? '') !== path.resolve(downloads, 'inbox'))
      )
        mark('wrong filename/destination', c);
    }
    if (task.id === 'T6' && b && (Object.keys(a).length !== 1 || a.cursor !== context.cursor))
      mark('cursor must be the observed cursor alone', c);
    if (task.id === 'T6' && !b && (a.count !== 20 || a.query !== 'Phenomenology'))
      mark('baseline paging workaround must request twenty', c);
    if (
      task.id === 'T8' &&
      kind === 'search' &&
      (b
        ? JSON.stringify(a.sources) !== '["libgen"]'
        : c.name !== 'search_multi_source' || a.source !== 'libgen')
    )
      mark('quota-preserving source argument', c);
    if (
      task.id === 'T11' &&
      kind === 'search' &&
      (b
        ? !a.sources?.length || a.sources.includes('zlibrary')
        : c.name !== 'search_multi_source' || !['libgen', 'annas'].includes(a.source))
    )
      mark('retry exhausted source', c);
    if (
      task.id === 'T4' &&
      b &&
      (a.mode !== 'live' || (a.sources && !a.sources.includes('zlibrary')))
    )
      mark('live zlibrary limits required', c);
    if (task.id === 'T12' && kind === 'search') {
      const from = b ? a.year_from : (a.yearFrom ?? a.fromYear);
      const to = b ? a.year_to : (a.yearTo ?? a.toYear);
      if (from !== 1950 || to !== 1965) mark('wrong year bounds', c);
      if (
        !/hannah[^\w]+arendt|arendt[^\w]+hannah/i.test(
          b ? (a.author ?? '') : (a.author ?? a.query ?? ''),
        )
      )
        mark('wrong author', c);
    }
  }
  if (
    ['T8', 'T11'].includes(task.id) &&
    providerEvents.some(
      (e) =>
        e.route.startsWith('/eapi/') &&
        (task.id === 'T8' || !e.route.endsWith('/profile')) &&
        (task.id === 'T8' || !e.route.endsWith('/login')),
    )
  )
    mark('forbidden zlibrary provider operation');
  const kinds = trace.map((c) => category(c.name));
  const requireKind = (k) => {
    if (!kinds.includes(k)) mark(`missing ${k}`);
  };
  if (['T1', 'T2', 'T6', 'T8', 'T9', 'T12'].includes(task.id)) requireKind('search');
  if (['T1', 'T3', 'T8', 'T9'].includes(task.id) || (task.id === 'T10' && b))
    requireKind('download');
  if (['T4', 'T11'].includes(task.id)) requireKind('limits');
  if (task.id === 'T11') {
    requireKind('search');
    if (kinds.indexOf('limits') > kinds.indexOf('search'))
      mark('alternative search before checking limits');
  }
  if (task.id === 'T2') {
    const details = trace.filter((c) => category(c.name) === 'detail');
    if (
      !details.some((c) => isGraver(selected(c))) ||
      !details.some((c) => isCampbell(selected(c)))
    )
      mark('missing edition detail');
  }
  if (task.id === 'T7' && arm.history) requireKind('history');
  if (['T2', 'T4', 'T5', 'T7', 'T11'].includes(task.id) && quotaSpent !== 0)
    mark('forbidden quota spend');
  if (task.id === 'T12') {
    const rows = trace.flatMap((c) => rowsOf(dataOf(c.reply ?? {})));
    if (
      ![204, 205, 206].every((id) =>
        rows.some(
          (r) =>
            String(r.id) === String(id) ||
            {
              204: 'The Human Condition',
              205: 'The Origins of Totalitarianism',
              206: 'Eichmann in Jerusalem',
            }[id] === r.title,
        ),
      )
    )
      mark('missing in-range Arendt results');
    if (rows.some((r) => Number(r.year) < 1950 || Number(r.year) > 1965))
      mark('out-of-range result');
  }
  if (task.id === 'T6') {
    const rows = trace.flatMap((c) => rowsOf(dataOf(c.reply ?? {})));
    if (!rows.some((r) => /Volume 11/.test(r.title ?? ''))) mark('next page not observed');
  }
  if (task.id === 'T9') {
    const picked = trace.filter((c) => isDownload(c.name)).map(selected);
    for (const title of ['Pride and Prejudice', 'Middlemarch', 'On Liberty'])
      if (!picked.some((r) => r.title === title)) mark(`missing download ${title}`);
    if (picked.length !== 3) mark('expected three downloads');
  }
  // Success is a current artifact check, not merely a model's assertion.
  const files = [];
  for (const c of trace.filter((c) => isDownload(c.name))) {
    const data = dataOf(c.reply ?? {}),
      file = data.path ?? data.file_path;
    try {
      const actual = await realpath(file),
        root = await realpath(downloads);
      if (!actual.startsWith(root + path.sep)) throw new Error('outside artifact root');
      if (
        task.id === 'T10' &&
        b &&
        (path.basename(actual) !== 'seneca.pdf' ||
          path.dirname(actual) !== path.resolve(downloads, 'inbox'))
      )
        throw new Error('wrong materialized filename/destination');
      const bytes = await readFile(actual);
      const row = selected(c);
      const id = row.id ?? c.fixtureId;
      if (!bytes.includes(Buffer.from(`Synthetic fixture ${id}\n`)))
        throw new Error('wrong fixture bytes');
      files.push({ path: actual, bytes: bytes.length });
    } catch {
      mark('missing or wrong artifact', c);
    }
  }
  const successfulTrace = trace.filter(
    (c) => !c.error && !c.reply?.isError && !dataOf(c.reply ?? {}).error,
  );
  const answer = evaluateAnswer({
    task,
    arm,
    final,
    remainingBefore,
    rows: successfulTrace.flatMap((c) => rowsOf(dataOf(c.reply ?? {}))),
    historyRows: successfulTrace
      .filter((c) => category(c.name) === 'history')
      .flatMap((c) => rowsOf(dataOf(c.reply ?? {}))),
  });
  const pathCorrect = wrong.length === 0;
  return {
    task: task.id,
    pathCorrect,
    answer,
    outsideBar: arm.build === 'A' && !!task.outsideA,
    success: !pathCorrect
      ? false
      : answer.status === 'manual-review'
        ? null
        : ['correct', 'not-required'].includes(answer.status),
    wrongDecisions: wrong.length,
    wrong,
    calls: trace.length,
    quotaSpent,
    files,
    invalidCalls: trace.filter((c) => c.error || c.reply?.isError).length,
    refUnavailable: trace.filter((c) => dataOf(c.reply ?? {}).error?.code === 'ref_unavailable')
      .length,
  };
}
