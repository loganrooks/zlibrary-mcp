import { test, expect } from '@jest/globals';
import { parseManifest, norm, extractVolume, language } from '../../dist/wantlist/parse.js';
import { teq, dice, classify, decide, isDerivative } from '../../dist/wantlist/match.js';
import { rank, whyChosen } from '../../dist/wantlist/rank.js';
const want = (s = 'Being and Time — Heidegger') => parseManifest(s).items[0];
const row = (extra = {}) => ({
  source: 'zlibrary',
  identifiers: { id: '1', hash: 'h' },
  title: 'Being and Time',
  author: 'Martin Heidegger',
  language: 'english',
  format: 'pdf',
  year: 2010,
  ...extra,
});
test.each([' — ', ' – ', ' -- ', ' - ', ' by '])('separator %s', (sep) =>
  expect(want('Title' + sep + 'Author')).toMatchObject({ title: 'Title', author: 'Author' }),
);
test('plain directives, markers, year, options, warnings and stable IDs', () => {
  const p = parseManifest(
    '# mode: exact\n# language: english\n# formats: epub,pdf\n# sources: libgen,zlibrary\n- [ ] *Being and Time* — Heidegger (1927) [pdf] [vol=2] [translator=Stambaugh] [weird]\nBeing and Time — Heidegger (2010) [any] [vol=2] [epub]',
  );
  expect(p.defaults).toMatchObject({
    mode: 'exact',
    sources: ['libgen', 'zlibrary'],
    formats: ['epub', 'pdf'],
  });
  expect(p.items[0]).toMatchObject({
    title: 'Being and Time',
    year: 1927,
    mode: 'exact',
    volume: 2,
    translator: 'Stambaugh',
    notes: 'weird',
  });
  expect(p.items[0].warnings).toHaveLength(1);
  expect(p.items[1].item_id).toBe(p.items[0].item_id);
  expect(p.items[1].duplicate).toBe(p.items[0].item_id);
});
test('CSV aliases, quoted delimiters/newlines and exact WANTED provenance', () => {
  const p = parseManifest(
    'name,creator,format,work_id,wanted_edition,operator_ratification\n"Title, subtitle",Someone,"epub,pdf",mine,Edition please,yes\n',
    'list.csv',
  );
  expect(p.items[0]).toMatchObject({
    item_id: 'mine',
    title: 'Title, subtitle',
    formats: ['epub', 'pdf'],
    mode: 'exact',
    extra: { operator_ratification: 'yes' },
  });
  expect(
    parseManifest('title\twork_id\twanted_edition\nTitle\tid1\tSpecial', 'WANTED.tsv').items[0],
  ).toMatchObject({ item_id: 'id1', mode: 'exact' });
  expect(
    parseManifest('{"title":"Title","id":"i","foo":"bar"}', 'list.jsonl').items[0].extra,
  ).toEqual({ foo: 'bar' });
});
test('normalization and volume extractor', () => {
  expect(norm('Gödel, Æther & Łódź ß œ ø')).toBe('godel aether and lodz ss oe o');
  expect(teq('Nietzsche', 'Nietzche')).toBe(true);
  expect(teq('2', '3')).toBe(false);
  expect(teq('viii', 'vii')).toBe(false);
  expect(extractVolume('Capital, Vol. II')).toMatchObject({ volume: 2, title: 'Capital' });
  expect(extractVolume('Collected Papers')).toMatchObject({ set: true });
});
test.each([
  ['a b', 'a b', 1],
  ['a b', 'a', 2 / 3],
  ['a b c', 'a b d', 2 / 3],
  ['a', 'b', 0],
  ['a b', 'b a', 1],
  ['a a', 'a', 2 / 3],
])('Dice %s / %s', (a, b, n) => expect(dice(a, b)).toBe(n));
test.each([
  'guide',
  'companion',
  'summary',
  'study',
  'notes',
  'sparknotes',
  'cliffsnotes',
  'introduction',
  'commentary',
  'reader',
  'readers',
  'workbook',
  'handbook',
  'analysis',
  'understanding',
  'abridged',
  'adapted',
  'adaptation',
  'selections',
  'selected',
  'excerpts',
])('derivative %s', (t) =>
  expect(isDerivative(want(), row({ title: 'Being and Time ' + t }))).toBe(true),
);
test('possessive and requested derivative', () => {
  expect(isDerivative(want(), row({ title: "Heidegger's Being and Time" }))).toBe(true);
  expect(isDerivative(want('A Guide — Heidegger'), row({ title: 'A Guide' }))).toBe(false);
});
test.each([
  ['en', 'english'],
  ['ger', 'german'],
  ['fre', 'french'],
  ['ita', 'italian'],
  ['spa', 'spanish'],
  ['lat', 'latin'],
  ['grc', 'greek'],
  ['rus', 'russian'],
  ['por', 'portuguese'],
  ['dut', 'dutch'],
])('language %s', (s, n) => expect(language(s)).toBe(n));
const cases = [
  ['one strong', want(), [row()], {}, 'download', 'auto_match'],
  [
    'format translations',
    want(),
    [row(), row({ format: 'epub', identifiers: { id: '2' } })],
    {},
    'download',
    'auto_match',
  ],
  [
    'original year',
    want('Being and Time — Heidegger (1927)'),
    [row()],
    {},
    'download',
    'auto_match',
  ],
  ['wrong author', want(), [row({ author: 'Nobody' })], {}, 'ask', 'different_work'],
  ['guide', want(), [row({ title: 'Being and Time: A Guide' })], {}, 'ask', 'derivative_only'],
  [
    'unspecified volume',
    want(),
    [row({ title: 'Being and Time Vol. 1' })],
    {},
    'ask',
    'volume_unspecified',
  ],
  [
    'different volume',
    want('Being and Time — Heidegger [vol=2]'),
    [row({ title: 'Being and Time Vol. 1' })],
    {},
    'ask',
    'volume_mismatch',
  ],
  [
    'unverified volume',
    want('Being and Time — Heidegger [vol=2]'),
    [row()],
    {},
    'ask',
    'volume_unverified',
  ],
  [
    'equal volume',
    want('Being and Time — Heidegger [vol=2]'),
    [row({ title: 'Being and Time Vol. II' })],
    {},
    'download',
    'auto_match',
  ],
  [
    'set okay',
    want(),
    [row({ title: 'Being and Time: Complete in 2 volumes' })],
    {},
    'download',
    'auto_match',
  ],
  ['two languages', want(), [row(), row({ language: 'german' })], {}, 'ask', 'language_differs'],
  [
    'default language',
    want(),
    [row(), row({ language: 'german' })],
    { language: 'english' },
    'download',
    'auto_match',
  ],
  [
    'explicit language',
    want('Being and Time — Heidegger [lang=german]'),
    [row({ language: 'de' })],
    {},
    'download',
    'auto_match',
  ],
  [
    'wrong language',
    want('Being and Time — Heidegger [lang=german]'),
    [row()],
    {},
    'next',
    'no_match',
  ],
  ['close', want(), [row({ title: 'Being Time' })], {}, 'ask', 'close_title'],
  ['swap', want('Heidegger — Being and Time'), [row()], {}, 'download', 'auto_match'],
  [
    'anonymous split',
    want('Being and Time'),
    [row(), row({ author: 'Other' })],
    {},
    'ask',
    'different_work',
  ],
  ['no candidates', want(), [], {}, 'next', 'no_candidates'],
  [
    'unrelated',
    want(),
    [row({ title: 'Something Else', author: 'Other' })],
    {},
    'next',
    'no_match',
  ],
  [
    'exact simple',
    want('Being and Time — Heidegger [exact]'),
    [row()],
    {},
    'download',
    'exact_match',
  ],
  [
    'translator description',
    want('Being and Time — Heidegger [exact] [translator=Stambaugh]'),
    [row({ description: 'Translated by Joan Stambaugh.' })],
    {},
    'download',
    'exact_match',
  ],
  [
    'translator absent',
    want('Being and Time — Heidegger [exact] [translator=Stambaugh]'),
    [row()],
    {},
    'probe',
    'constraint_unverified',
  ],
  [
    'editor absent',
    want('Being and Time — Heidegger [exact] [editor=Someone]'),
    [row()],
    {},
    'probe',
    'constraint_unverified',
  ],
  [
    'editor description',
    want('Being and Time — Heidegger [exact] [editor=Someone]'),
    [row({ description: 'Edited by Someone.' })],
    {},
    'download',
    'exact_match',
  ],
  [
    'translator conflict',
    want('Being and Time — Heidegger [exact] [translator=Stambaugh]'),
    [row({ translator: 'Robinson' })],
    {},
    'ask',
    'constraint_unverified',
  ],
  [
    'no probe',
    want('Being and Time — Heidegger [exact] [editor=Someone]'),
    [row()],
    { probe: false },
    'ask',
    'constraint_unverified',
  ],
  [
    'differing editions',
    want('Being and Time — Heidegger [exact]'),
    [row({ edition: 'First' }), row({ edition: 'Second', identifiers: { id: '2' } })],
    {},
    'ask',
    'several_editions',
  ],
  [
    'same editions',
    want('Being and Time — Heidegger [exact]'),
    [row(), row({ identifiers: { id: '2' } })],
    {},
    'download',
    'exact_match',
  ],
  [
    'edition note',
    parseManifest('{"title":"Being and Time","wanted_edition":"special"}', 'list.jsonl').items[0],
    [row()],
    {},
    'ask',
    'edition_note',
  ],
  [
    'year conflict exact',
    want('Being and Time — Heidegger (1927) [exact]'),
    [row()],
    {},
    'ask',
    'constraint_unverified',
  ],
  [
    'year tolerance',
    want('Being and Time — Heidegger (2009) [exact]'),
    [row()],
    {},
    'download',
    'exact_match',
  ],
  [
    'author alternative',
    want('Collected Papers — Peirce'),
    [row({ title: 'Collected Papers: Peirce', author: 'Editor' })],
    {},
    'download',
    'auto_match',
  ],
  [
    'exact alt forbidden',
    want('Collected Papers — Peirce [exact]'),
    [row({ title: 'Collected Papers: Peirce', author: 'Editor' })],
    {},
    'ask',
    'different_work',
  ],
];
test.each(cases)('decision: %s', (_n, w, rows, settings, action, reason) =>
  expect(decide(w, rows, settings)).toMatchObject({ action, reason }),
);
test('swapped orientation recorded', () =>
  expect(classify(want('Heidegger — Being and Time'), row()).orientation).toBe('swapped'));
test.each([
  ['format', { format: 'epub' }, { format: 'pdf' }],
  ['language', { language: 'english' }, { language: 'german' }],
  ['quality', { quality: 2 }, { quality: 1 }],
  ['pages', { pages: 200 }, { pages: 100 }],
  ['year', { year: 2020 }, { year: 2010 }],
  ['source', { source: 'libgen' }, { source: 'zlibrary' }],
  ['identifier', { identifiers: { id: '1' } }, { identifiers: { id: '2' } }],
])('ranking key %s and explanation', (key, a, b) => {
  const s = { language: 'english', sources: ['libgen', 'zlibrary'] },
    w = want();
  const rows = [row(b), row(a)],
    sorted = rank(rows, w, s);
  expect(sorted[0]).toBe(rows[1]);
  expect(whyChosen(sorted[0], sorted, w, s)).toContain('chose by ' + key);
});
