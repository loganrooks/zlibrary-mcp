// Deterministic, fail-closed fact scoring. This is not a semantic prose judge.
const translations = [
  { translator: 'Margaret Graver and A. A. Long', year: 2015 },
  { translator: 'Robin Campbell', year: 1969 },
];
const titles = ['The Human Condition', 'The Origins of Totalitarianism', 'Eichmann in Jerusalem'];
const normalized = (value) => value.trim().replace(/\s+/g, ' ').toLowerCase();
const sorted = (values) => [...values].sort();
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function exactObject(actual, expected) {
  if (!expected || !actual || Array.isArray(actual) || typeof actual !== 'object') return false;
  if (!equal(Object.keys(actual).sort(), Object.keys(expected).sort())) return false;
  return Object.keys(expected).every((key) => {
    if (key === 'translations')
      return (
        Array.isArray(actual[key]) &&
        actual[key].length === 2 &&
        equal(
          sorted(actual[key].map((r) => r?.translator)),
          sorted(expected[key].map((r) => r.translator)),
        ) &&
        actual[key].every((row) =>
          exactObject(
            row,
            expected[key].find((e) => e.translator === row?.translator),
          ),
        )
      );
    if (key === 'titles')
      return Array.isArray(actual[key]) && equal(sorted(actual[key]), sorted(expected[key]));
    return actual[key] === expected[key];
  });
}
export function answerContract(task, arm) {
  switch (task.id) {
    case 'T2':
      return {
        translations: [
          {
            translator: 'STRING from edition details',
            year: 'INTEGER publication year for that translator',
          },
        ],
      };
    case 'T4':
      return {
        remaining: 'NUMBER from observed live limits',
        libgen_cap: 'none, number, or unknown from source capabilities',
      };
    case 'T5':
      return { full_text_search_available: 'BOOLEAN from advertised capabilities' };
    case 'T7':
      return arm.history
        ? { title: 'Being and Time', in_account_history: 'BOOLEAN from account history' }
        : { account_history_available: 'BOOLEAN from advertised tools' };
    case 'T12':
      return { titles: ['ALL observed matching book titles'] };
    case 'T10':
      return arm.build === 'A'
        ? { filename_supported: 'BOOLEAN from advertised arguments' }
        : undefined;
    default:
      return undefined;
  }
}
export function answerInstruction(task, arm) {
  const contract = answerContract(task, arm);
  return contract
    ? `\nFor deterministic answer scoring, reply with ONLY a JSON object of this shape, filling the facts from your observations (do not copy placeholder values): ${JSON.stringify(contract)}. Lists must include all matching observed facts; array examples specify item shapes, not counts. No additional prose or properties.`
    : '';
}
// JSON.parse keeps the last duplicate property. Refuse that ambiguous surface
// rather than silently discarding an earlier contradictory claim.
function duplicateKeys(text) {
  const tokens = [...text.matchAll(/"(?:\\.|[^"\\])*"|[{}\[\]:,]/g)];
  const stack = [];
  for (const token of tokens) {
    const t = token[0];
    if (t === '{') stack.push(new Set());
    else if (t === '[') stack.push(null);
    else if (t === '}' || t === ']') stack.pop();
    else if (
      t.startsWith('"') &&
      text
        .slice(token.index + t.length)
        .trimStart()
        .startsWith(':')
    ) {
      const keys = stack.at(-1),
        key = JSON.parse(t);
      if (keys?.has(key)) return true;
      keys?.add(key);
    }
  }
  return false;
}
export function evaluateAnswer({ task, arm, final, remainingBefore, rows, historyRows }) {
  if (!answerContract(task, arm)) return { status: 'not-required' };
  let expected,
    evidence = true;
  switch (task.id) {
    case 'T2':
      expected = { translations };
      evidence =
        rows.some((r) => r.title === 'Letters on Ethics: To Lucilius' && Number(r.year) === 2015) &&
        rows.some((r) => r.title === 'Letters from a Stoic' && Number(r.year) === 1969);
      break;
    case 'T4':
      expected = { remaining: remainingBefore, libgen_cap: 'none' };
      evidence = Number.isInteger(remainingBefore) && remainingBefore >= 0;
      break;
    case 'T5':
      expected = { full_text_search_available: false };
      break;
    case 'T7':
      expected = arm.history
        ? { title: 'Being and Time', in_account_history: true }
        : { account_history_available: false };
      evidence = !arm.history || historyRows.some((r) => r.title === 'Being and Time');
      break;
    case 'T12':
      expected = { titles };
      evidence = titles.every((title) => rows.some((r) => r.title === title));
      break;
    case 'T10':
      expected = { filename_supported: false };
      break;
  }
  const base = { expected, evidence };
  if (!evidence)
    return { ...base, status: 'incorrect', reason: 'required facts not observed in tool results' };
  let actual;
  const text = final.trim();
  try {
    actual = JSON.parse(text);
    if (duplicateKeys(text))
      return { ...base, status: 'manual-review', reason: 'duplicate JSON property claims' };
  } catch {
    // Full-string, documented control grammar only. No keyword/number presence test.
    const n = normalized(text);
    if (task.id === 'T2' && n === 'margaret graver and a. a. long (2015); robin campbell (1969).')
      actual = { translations };
    if (task.id === 'T4') {
      const m = /^(\d+) z-library downloads? remain\. libgen has no daily cap\.$/.exec(n);
      if (m) actual = { remaining: Number(m[1]), libgen_cap: 'none' };
    }
    if (
      task.id === 'T5' &&
      n === 'full-text search is not available; these tools search catalogue metadata only.'
    )
      actual = { full_text_search_available: false };
    if (
      task.id === 'T7' &&
      arm.history &&
      n === 'being and time is in your downloaded account history.'
    )
      actual = { title: 'Being and Time', in_account_history: true };
    if (
      task.id === 'T7' &&
      !arm.history &&
      n === 'account history is not available in this configuration.'
    )
      actual = { account_history_available: false };
    if (task.id === 'T12') {
      const parts = text
        .replace(/\.$/, '')
        .split(';')
        .map((x) => x.trim());
      if (parts.length === 3 && parts.every((t) => titles.includes(t))) actual = { titles: parts };
    }
    if (
      task.id === 'T10' &&
      arm.build === 'A' &&
      n === 'this interface cannot name the downloaded file seneca.pdf; filename is unavailable.'
    )
      actual = { filename_supported: false };
  }
  if (actual === undefined)
    return {
      ...base,
      status: 'manual-review',
      reason: 'prose outside deterministic full-answer grammar; not automatically scored',
    };
  return {
    ...base,
    status: exactObject(actual, expected) ? 'correct' : 'incorrect',
    actual,
    reason: 'exact fact/schema comparison',
  };
}
