import { language } from './parse.js';
import type { Candidate, Settings, Want } from './types.js';
export const RANK_KEYS = [
  'format',
  'language',
  'quality',
  'pages',
  'year',
  'source',
  'identifier',
] as const;
function keys(c: Candidate, w: Want, s: Partial<Settings>): (number | string)[] {
  const formats = w.formats ?? s.formats ?? ['epub', 'pdf'];
  const f = c.format?.toLowerCase() ?? '';
  return [
    f === 'djvu' ? 1000 : formats.includes(f) ? formats.indexOf(f) : formats.length,
    language(c.language) === language(w.language ?? s.language) ? 0 : 1,
    -Number(c.quality ?? 0),
    -Number(c.pages ?? 0),
    -Number(c.year ?? 0),
    s.sources?.indexOf(c.source) ?? 0,
    c.source + ':' + JSON.stringify(c.identifiers),
  ];
}
export function rank(candidates: Candidate[], w: Want, s: Partial<Settings> = {}) {
  return [...candidates].sort((a, b) => {
    const x = keys(a, w, s),
      y = keys(b, w, s);
    for (let i = 0; i < x.length; i++) {
      if (x[i] !== y[i])
        return typeof x[i] === 'number'
          ? Number(x[i]) - Number(y[i])
          : String(x[i]) < String(y[i])
            ? -1
            : 1;
    }
    return 0;
  });
}
export function whyChosen(c: Candidate, others: Candidate[], w: Want, s: Partial<Settings> = {}) {
  const runner = others.find((v) => v !== c);
  const a = keys(c, w, s),
    b = runner ? keys(runner, w, s) : a;
  const separator = runner
    ? (RANK_KEYS[a.findIndex((v, i) => v !== b[i])] ?? 'identifier')
    : 'only candidate';
  return `${w.mode}: title ${(c.score ?? 0).toFixed(2)}, author ${c.author_match ?? 'none'}; ${Math.max(0, others.length - 1)} alternatives; chose by ${separator}${separator === 'format' ? ` (${c.format})` : ''}${c.orientation === 'swapped' ? '; read as Author — Title' : ''}`;
}
