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
export function answerContract(task) {
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
      return { remaining: 'NUMBER', cap: 'NUMBER, "none", or "unknown"' };
    case 'T5':
    case 'T10':
      return { answer: 'BOOLEAN' };
    case 'T7':
      return { answer: 'BOOLEAN, or null if unable to determine' };
    case 'T12':
      return { titles: ['ALL observed matching book titles'] };
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
  if (!answerContract(task, arm) || (task.id === 'T10' && arm.build !== 'A'))
    return { status: 'not-required' };
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
  const base = {
    expected,
    evidence,
    ...(task.id === 'T7' && !arm.history ? { outcome: 'inability' } : {}),
  };
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
      [
        'account history is not available in this configuration.',
        'i cannot tell.',
        'i cannot determine that.',
      ].includes(n)
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
  // Neutral instructions are shared by every arm. Accept the former exact JSON
  // schemas as a compatibility grammar, not as instructions to the driver.
  const keysAre = (...keys) =>
    actual &&
    typeof actual === 'object' &&
    !Array.isArray(actual) &&
    equal(Object.keys(actual).sort(), keys.sort());
  if (task.id === 'T4' && keysAre('remaining', 'cap'))
    actual = { remaining: actual.remaining, libgen_cap: actual.cap };
  if (keysAre('answer')) {
    if (task.id === 'T5') actual = { full_text_search_available: actual.answer };
    else if (task.id === 'T10') actual = { filename_supported: actual.answer };
    else if (task.id === 'T7' && arm.history)
      actual = { title: 'Being and Time', in_account_history: actual.answer };
    else if (task.id === 'T7' && actual.answer === null)
      actual = { account_history_available: false };
  }
  return {
    ...base,
    status:
      exactObject(actual, expected) ||
      (task.id === 'T4' &&
        arm.build === 'A' &&
        exactObject(actual, { ...expected, libgen_cap: 'unknown' }))
        ? 'correct'
        : 'incorrect',
    actual,
    reason: 'exact fact/schema comparison',
  };
}
