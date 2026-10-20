import { createHash } from 'node:crypto';
import { extname } from 'node:path';
import { ToolFailure } from '../lib/tool-errors.js';
import type { Want } from './types.js';

export function norm(value: unknown): string {
  return String(value ?? '')
    .replace(
      /[ßæœøł&]/gi,
      (c) => ({ ß: 'ss', æ: 'ae', œ: 'oe', ø: 'o', ł: 'l', '&': ' and ' })[c.toLowerCase()]!,
    )
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}
const languages: Record<string, string[]> = {
  english: ['en', 'eng'],
  german: ['de', 'deu', 'ger', 'deutsch'],
  french: ['fr', 'fra', 'fre'],
  italian: ['it', 'ita'],
  spanish: ['es', 'spa'],
  latin: ['la', 'lat'],
  greek: ['el', 'ell', 'grc'],
  russian: ['ru', 'rus'],
  portuguese: ['pt', 'por'],
  dutch: ['nl', 'nld', 'dut'],
};
export function language(s: unknown): string {
  const n = norm(s);
  return Object.entries(languages).find(([k, v]) => k === n || v.includes(n))?.[0] ?? n;
}
function volumeNumber(s: string): number {
  if (/^\d+$/.test(s)) return Number(s);
  const words = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
  if (words.includes(s)) return words.indexOf(s) + 1;
  const digits: Record<string, number> = { i: 1, v: 5, x: 10, l: 50, c: 100 };
  let value = 0;
  for (let i = 0; i < s.length; i++)
    value += (digits[s[i]!] ?? 0) * ((digits[s[i + 1]!] ?? 0) > (digits[s[i]!] ?? 0) ? -1 : 1);
  return value;
}
export function extractVolume(title: string, series = '') {
  const pattern =
    /\b(?:vol(?:ume)?|v|bd|band|tome?|tomo|t|part|pt|book|bk|teil|livre)\.?\s*([0-9]+|[ivxlc]+|one|two|three|four|five|six|seven|eight|nine|ten)\b/gi;
  const combined = title + ' ' + series;
  const set = /\bvols?\.?\s*\d+\s*[-–&,]\s*\d+|\bcomplete\b|\bin \d+ volumes\b|\bcollected\b/i.test(
    combined,
  );
  const match = pattern.exec(combined);
  return {
    volume: match ? volumeNumber(match[1]!.toLowerCase()) : undefined,
    set,
    title: title
      .replace(pattern, '')
      .replace(/[\s,]+$/, '')
      .trim(),
  };
}
function base32(buffer: Buffer) {
  let bits = 0,
    value = 0,
    out = '';
  const alphabet = 'abcdefghijklmnopqrstuvwxyz234567';
  for (const b of buffer) {
    value = (value << 8) | b;
    bits += 8;
    while (bits >= 5) {
      out += alphabet[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits) out += alphabet[(value << (5 - bits)) & 31];
  return out;
}
const aliases: Record<string, string> = {
  name: 'title',
  authors: 'author',
  creator: 'author',
  lang: 'language',
  format: 'formats',
  extension: 'formats',
  edition: 'mode',
  vol: 'volume',
  why: 'notes',
  id: 'item_id',
  work_id: 'item_id',
  wanted_edition: 'edition_note',
};
const known = new Set([
  'title',
  'author',
  'year',
  'language',
  'formats',
  'mode',
  'volume',
  'translator',
  'editor',
  'notes',
  'item_id',
  'edition_note',
]);
const list = (v: any): string[] =>
  (Array.isArray(v) ? v : String(v).split(','))
    .map((s: any) => String(s).trim().toLowerCase())
    .filter(Boolean);
function structured(raw: Record<string, any>, line: number, defaults: Record<string, any>): Want {
  const data: Record<string, any> = {};
  const extra: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(raw)) {
    const key = aliases[k.toLowerCase().trim()] ?? k.toLowerCase().trim();
    if (known.has(key)) data[key] = v;
    else extra[k] = v;
  }
  if (!String(data.title ?? '').trim())
    throw new ToolFailure('invalid_argument', `Missing title at line ${line}.`);
  const w: Want = {
    item_id: '',
    title: String(data.title).trim(),
    mode: data.mode || defaults.mode || 'any',
    extra,
    line,
    warnings: [],
  };
  for (const key of ['author', 'translator', 'editor', 'notes', 'edition_note'] as const)
    if (data[key] != null && String(data[key]).trim()) w[key] = String(data[key]).trim();
  if (!['any', 'exact'].includes(w.mode))
    throw new ToolFailure('invalid_argument', `Invalid mode at line ${line}.`);
  if (data.language) w.language = language(data.language);
  if (data.formats) w.formats = list(data.formats);
  for (const key of ['year', 'volume'] as const)
    if (data[key] !== undefined && data[key] !== '') {
      if (!Number.isInteger(Number(data[key])) || Number(data[key]) < 1)
        throw new ToolFailure('invalid_argument', `Invalid ${key} at line ${line}.`);
      w[key] = Number(data[key]);
    }
  const extracted = extractVolume(w.title);
  w.volume ??= extracted.volume;
  if (w.edition_note) w.mode = 'exact';
  w.item_id = String(
    data.item_id ||
      'w' +
        base32(
          createHash('sha256')
            .update([norm(w.title), norm(w.author), w.volume ?? '', w.language ?? ''].join(' | '))
            .digest(),
        ).slice(0, 10),
  );
  return w;
}
function plain(text: string, line: number, defaults: Record<string, any>): Want {
  text = text.trim().replace(/^(?:(?:[-*+] |\d+[.)] |\[[ xX]\] ))+/, '');
  const data: Record<string, any> = {};
  const warnings: string[] = [];
  const opts: string[] = [];
  while (/\s*\[([^\]]+)\]\s*$/.test(text)) {
    const m = text.match(/\s*\[([^\]]+)\]\s*$/)!;
    opts.unshift(m[1]!);
    text = text.slice(0, m.index).trim();
  }
  for (const opt of opts) {
    if (['any', 'exact'].includes(opt)) data.mode = opt;
    else if (['epub', 'pdf'].includes(opt)) data.formats = opt;
    else {
      const pos = opt.indexOf('=');
      const key = opt.slice(0, pos);
      const mapped =
        (
          { lang: 'language', vol: 'volume', id: 'item_id', note: 'notes' } as Record<
            string,
            string
          >
        )[key] ?? key;
      if (pos > 0 && known.has(mapped)) data[mapped] = opt.slice(pos + 1);
      else {
        data.notes = [data.notes, opt].filter(Boolean).join('; ');
        warnings.push(`Unknown option: ${opt}`);
      }
    }
  }
  text = text.replace(/^[*_'"“”]+|[*_'"“”]+$/g, '').replace(/[ .]+$/, '');
  const year = text.match(/\s*\((\d{4})\)$/);
  if (year) {
    data.year ??= year[1];
    text = text.slice(0, year.index).trim();
  }
  let split = -1,
    len = 0;
  for (const sep of [' — ', ' – ', ' -- ', ' - ']) {
    split = text.indexOf(sep);
    if (split >= 0) {
      len = sep.length;
      break;
    }
  }
  if (split < 0) {
    const m = [...text.matchAll(/ by /gi)].at(-1);
    if (m) {
      split = m.index!;
      len = m[0].length;
    }
  }
  data.title = (split < 0 ? text : text.slice(0, split))
    .replace(/^[*_'"“”]+|[*_'"“”]+$/g, '')
    .trim();
  if (split >= 0)
    data.author = text
      .slice(split + len)
      .replace(/^[*_'"“”]+|[*_'"“”]+$/g, '')
      .trim();
  const w = structured(data, line, defaults);
  w.warnings = warnings;
  return w;
}
// Quoted CSV/TSV supports embedded delimiters, quotes and newlines.
function delimited(text: string, delimiter: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [],
    value = '',
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i]!;
    if (c === '"') {
      if (quoted && text[i + 1] === '"') {
        value += '"';
        i++;
      } else quoted = !quoted;
    } else if (c === delimiter && !quoted) {
      row.push(value);
      value = '';
    } else if (c === '\n' && !quoted) {
      row.push(value.replace(/\r$/, ''));
      rows.push(row);
      row = [];
      value = '';
    } else value += c;
  }
  if (quoted) throw new ToolFailure('invalid_argument', 'Unclosed quoted field.');
  if (value || row.length) {
    row.push(value.replace(/\r$/, ''));
    rows.push(row);
  }
  return rows;
}
export function parseManifest(
  text: string,
  filename = 'list.txt',
  inline?: (string | Record<string, any>)[],
) {
  const defaults: Record<string, any> = {};
  const items: Want[] = [];
  const ext = extname(filename).toLowerCase();
  if (inline)
    inline.forEach((v, i) =>
      items.push(
        typeof v === 'string' ? plain(v, i + 1, defaults) : structured(v, i + 1, defaults),
      ),
    );
  else if (['.csv', '.tsv'].includes(ext)) {
    const rows = delimited(text.replace(/^\uFEFF/, ''), ext === '.csv' ? ',' : '\t');
    const header = rows.shift();
    if (!header) throw new ToolFailure('invalid_argument', 'Header required.');
    rows.forEach((r, i) => {
      if (r.some(Boolean))
        items.push(
          structured(Object.fromEntries(header.map((k, j) => [k, r[j] ?? ''])), i + 2, defaults),
        );
    });
  } else
    text
      .replace(/^\uFEFF/, '')
      .split(/\r?\n/)
      .forEach((s, i) => {
        if (!s.trim()) return;
        if (ext === '.jsonl') {
          try {
            items.push(structured(JSON.parse(s), i + 1, defaults));
          } catch (e) {
            if (e instanceof ToolFailure) throw e;
            throw new ToolFailure('invalid_argument', `Invalid JSON at line ${i + 1}.`);
          }
          return;
        }
        if (s.trim().startsWith('#')) {
          const m = s.match(/^\s*#\s*(mode|formats|language|sources):\s*(.+)$/i);
          if (m)
            defaults[m[1]!.toLowerCase()] = ['formats', 'sources'].includes(m[1]!.toLowerCase())
              ? list(m[2])
              : m[2]!.trim().toLowerCase();
          return;
        }
        items.push(plain(s, i + 1, defaults));
      });
  const seen = new Set<string>();
  for (const w of items) {
    if (seen.has(w.item_id)) w.duplicate = w.item_id;
    seen.add(w.item_id);
  }
  return { items, defaults };
}
