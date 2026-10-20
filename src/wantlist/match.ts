import { norm, language, extractVolume } from './parse.js';
import { rank } from './rank.js';
import type { Candidate, Want, Settings } from './types.js';
export const STRONG = 0.9,
  CLOSE = 0.75;
const derivatives =
  'guide companion summary study notes sparknotes cliffsnotes introduction commentary reader readers workbook handbook analysis understanding abridged adapted adaptation selections selected excerpts'.split(
    ' ',
  );
export function teq(a: string, b: string): boolean {
  if (a === b) return true;
  if (/\d|^[ivxlcdm]+$/i.test(a) || /\d|^[ivxlcdm]+$/i.test(b)) return false;
  const max = a.length >= 9 && b.length >= 9 ? 2 : a.length >= 5 && b.length >= 5 ? 1 : 0;
  if (!max || Math.abs(a.length - b.length) > max) return false;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const next = [i];
    for (let j = 1; j <= b.length; j++)
      next[j] = Math.min(
        next[j - 1]! + 1,
        prev[j]! + 1,
        prev[j - 1]! + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    prev = next;
  }
  return prev[b.length]! <= max;
}
export function dice(a: string | string[], b: string | string[]): number {
  const x = Array.isArray(a) ? a : norm(a).split(' ').filter(Boolean),
    y = Array.isArray(b) ? b : norm(b).split(' ').filter(Boolean);
  const used = new Set<number>();
  let m = 0;
  for (const t of x) {
    const j = y.findIndex((v, i) => !used.has(i) && teq(t, v));
    if (j >= 0) {
      used.add(j);
      m++;
    }
  }
  return x.length + y.length ? (2 * m) / (x.length + y.length) : 0;
}
export function mainTitle(title: string): string {
  return norm(extractVolume(title.split(/:| — | – |\(/)[0]!).title).replace(
    /^(the|a|an|der|die|das|le|la|les|l|el|il|lo) /,
    '',
  );
}
export function surnames(author: string): string[] {
  return author
    .split(/ and |&|;/i)
    .map((p) =>
      p.includes(',')
        ? norm(p.split(',')[0])
        : (norm(p)
            .split(' ')
            .filter((t) => !['jr', 'sr', 'ii', 'iii'].includes(t))
            .at(-1) ?? ''),
    )
    .filter(Boolean);
}
export function authorMatch(request: string | undefined, candidate: string | undefined): string {
  if (!request) return 'match';
  const names = surnames(request),
    tokens = norm(candidate).split(' ');
  const matches = names.filter((n) => tokens.some((t) => teq(n, t))).length;
  return matches === names.length ? 'match' : matches ? 'partial' : 'none';
}
export function isDerivative(w: Want, c: Candidate): boolean {
  const req = norm(w.title).split(' '),
    cand = norm(c.title).split(' ');
  return (
    derivatives.some((t) => cand.includes(t) && !req.includes(t)) ||
    Boolean(
      w.author &&
      surnames(w.author).some((s) => norm(c.title).includes(s + ' s')) &&
      !norm(w.title).includes(' s'),
    )
  );
}
function score(title: string, author: string | undefined, c: Candidate) {
  const r = extractVolume(title).title,
    b = extractVolume(c.title, c.series).title;
  return {
    score: Math.max(dice(mainTitle(r), mainTitle(b)), dice(r, b)),
    author_match: authorMatch(author, c.author),
  };
}
export function classify(w: Want, candidate: Candidate): Candidate {
  let reading = score(w.title, w.author, candidate),
    orientation = 'normal';
  if (w.author) {
    const swap = score(w.author, w.title, candidate);
    if (
      (swap.author_match === 'match' ? 1 : 0) + swap.score >
      (reading.author_match === 'match' ? 1 : 0) + reading.score
    ) {
      reading = swap;
      orientation = 'swapped';
    }
  }
  const volume = extractVolume(candidate.title, candidate.series);
  let volume_status = 'ok';
  const described = extractVolume(candidate.description ?? '');
  const actual = volume.volume ?? described.volume;
  if (w.volume !== undefined)
    volume_status =
      actual === undefined ? 'volume_unverified' : actual === w.volume ? 'ok' : 'volume_mismatch';
  else if (volume.volume !== undefined && !volume.set) volume_status = 'volume_unspecified';
  const c = { ...candidate, ...reading, orientation, volume_status };
  c.derivative = isDerivative(w, c);
  const reqAuthor = orientation === 'swapped' ? w.title : w.author;
  c.author_alt =
    reading.author_match === 'none' &&
    Boolean(
      reqAuthor &&
      surnames(reqAuthor).every((n) =>
        norm(c.title + ' ' + (c.description ?? ''))
          .split(' ')
          .some((t) => teq(n, t)),
      ),
    );
  const authorOK = reading.author_match === 'match' || (w.mode === 'any' && c.author_alt);
  c.class =
    reading.score >= STRONG &&
    authorOK &&
    !c.derivative &&
    volume_status === 'ok' &&
    (!w.language || language(w.language) === language(c.language))
      ? 'strong'
      : reading.score >= CLOSE && reading.score < STRONG && authorOK
        ? 'close'
        : reading.score >= STRONG && !authorOK
          ? 'other_work'
          : 'none';
  return c;
}
function personEvidence(
  wanted: string,
  explicit: string | undefined,
  description: string | undefined,
  role: string,
): string {
  if (explicit) {
    return surnames(wanted).every((s) =>
      norm(explicit)
        .split(' ')
        .some((t) => teq(s, t)),
    )
      ? 'match'
      : 'contradict';
  }
  const found = description?.match(new RegExp(role + '\\s+([^.;\\n]+)', 'i'))?.[1];
  return found
    ? surnames(wanted).every((s) =>
        norm(found)
          .split(' ')
          .some((t) => teq(s, t)),
      )
      ? 'match'
      : 'contradict'
    : 'absent';
}
export function constraints(w: Want, c: Candidate): Candidate {
  const checks: Record<string, string> = {};
  if (w.year)
    checks.year = c.year ? (Math.abs(w.year - c.year) <= 1 ? 'match' : 'contradict') : 'absent';
  if (w.language)
    checks.language = c.language
      ? language(w.language) === language(c.language)
        ? 'match'
        : 'contradict'
      : 'absent';
  if (w.formats?.length)
    checks.formats = c.format
      ? w.formats.includes(c.format.toLowerCase())
        ? 'match'
        : 'contradict'
      : 'absent';
  if (w.volume !== undefined)
    checks.volume =
      c.volume_status === 'ok'
        ? 'match'
        : c.volume_status === 'volume_mismatch'
          ? 'contradict'
          : 'absent';
  if (w.translator)
    checks.translator = personEvidence(
      w.translator,
      c.translator ??
        (c.edition && norm(c.edition).includes(norm(w.translator)) ? c.edition : undefined),
      c.description,
      'translated by',
    );
  if (w.editor)
    checks.editor = personEvidence(w.editor, undefined, c.description, '(?:edited by|ed\\.)');
  return {
    ...c,
    checks,
    missing: Object.keys(checks).filter((k) => checks[k] === 'absent'),
    conflicts: Object.keys(checks).filter((k) => checks[k] === 'contradict'),
  };
}
export interface Decision {
  action: 'download' | 'probe' | 'ask' | 'next';
  state: string;
  reason: string;
  candidate?: Candidate;
  candidates: Candidate[];
}
export function decide(w: Want, rows: Candidate[], s: Partial<Settings> = {}): Decision {
  const all = rank(
    rows.map((c) => constraints(w, classify(w, c))),
    w,
    s,
  );
  const result = (action: Decision['action'], reason: string, subset = all): Decision => ({
    action,
    state:
      action === 'download' || action === 'probe'
        ? 'fetched'
        : action === 'next'
          ? 'not_found'
          : 'needs_choice',
    reason,
    candidate: subset[0],
    candidates: subset,
  });
  if (w.edition_note) return result('ask', 'edition_note');
  let strong = all.filter((c) => c.class === 'strong');
  // Exact candidates with an unverified volume/language still need detail evidence.
  if (w.mode === 'exact')
    strong = all.filter(
      (c) =>
        c.score! >= STRONG &&
        c.author_match === 'match' &&
        !c.derivative &&
        !['volume_mismatch', 'volume_unspecified'].includes(c.volume_status!),
    );
  if (!strong.length) {
    const reasons = [
      ['close_title', (c: Candidate) => c.class === 'close'],
      ['different_work', (c: Candidate) => c.class === 'other_work'],
      ['derivative_only', (c: Candidate) => c.derivative],
      ...['volume_mismatch', 'volume_unspecified', 'volume_unverified'].map((v) => [
        v,
        (c: Candidate) => c.volume_status === v,
      ]),
    ] as [string, (c: Candidate) => any][];
    for (const [reason, test] of reasons) if (all.some(test)) return result('ask', reason);
    return result('next', rows.length ? 'no_match' : 'no_candidates');
  }
  if (!w.language) {
    const langs = new Set(strong.map((c) => language(c.language)));
    if (langs.size > 1) {
      const filtered = s.language
        ? strong.filter((c) => language(c.language) === language(s.language))
        : [];
      if (!filtered.length) return result('ask', 'language_differs', strong);
      strong = filtered;
    }
  }
  const orientedAuthor = strong[0]?.orientation === 'swapped' ? w.title : w.author;
  if (!orientedAuthor && new Set(strong.map((c) => surnames(c.author ?? '').join(';'))).size > 1)
    return result('ask', 'different_work', strong);
  if (w.mode === 'exact') {
    const confident = strong.filter((c) => !c.missing?.length && !c.conflicts?.length);
    if (confident.length === 1) return result('download', 'exact_match', confident);
    if (confident.length > 1) {
      const editions = new Set(
        confident.map((c) =>
          JSON.stringify([norm(c.translator), norm(c.edition), norm(c.publisher), c.year]),
        ),
      );
      return editions.size === 1
        ? result('download', 'exact_match', confident)
        : result('ask', 'several_editions', confident);
    }
    const top = strong[0]!;
    if (!top.conflicts?.length && top.missing?.length && s.probe !== false)
      return result('probe', 'constraint_unverified', strong);
    return result('ask', 'constraint_unverified', strong);
  }
  const works = new Map<string, Candidate[]>();
  for (const c of strong) {
    const key = norm(c.title) + '|' + surnames(c.author ?? '').join(';');
    works.set(key, [...(works.get(key) ?? []), c]);
  }
  if (works.size > 1) {
    if (!w.year) return result('ask', 'different_work', strong);
    const groups = [...works.values()].sort(
      (a, b) =>
        Math.abs(Math.min(...a.map((c) => c.year ?? Infinity)) - w.year!) -
        Math.abs(Math.min(...b.map((c) => c.year ?? Infinity)) - w.year!),
    );
    strong = groups[0]!;
  }
  return result('download', 'auto_match', strong);
}
