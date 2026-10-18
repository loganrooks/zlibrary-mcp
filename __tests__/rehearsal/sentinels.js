// Return only categories and locations, never the matching synthetic values.
export function classifySentinels(text, source, caKey, { redaction = false } = {}) {
  const result = { expected: [], unexpected: [], knownLogCount: 0 };
  const probes = [
    ['identity', 'rehearsal-account@example.invalid'],
    ['password', 'rehearsal-password-canary'],
    ['cookie-key', 'rehearsal-cookie-key'],
    ['ca-key', caKey],
    ...caKey
      .split('\n')
      .filter((line) => line.length > 50)
      .map((line) => ['ca-key', line]),
  ];
  for (const [kind, sentinel] of probes) {
    if (sentinel && text.includes(sentinel) && !result.unexpected.some((f) => f.kind === kind)) {
      result.unexpected.push({ kind, source });
    }
  }
  const id = 'rehearsal-cookie-id';
  for (const line of text.split('\n').filter((line) => line.includes(id))) {
    // Python forwards the same authentication message to the debug file and
    // stderr; bridge errors can quote it. Every ID must belong to that message.
    const authenticationCount = [
      ...line.matchAll(/EAPI client authenticated \(userid=rehearsal-cookie-id\)/g),
    ].length;
    const known =
      (source === 'stderr' || /^client-\d+\/logs\/zlibrary_debug\.log$/.test(source)) &&
      authenticationCount > 0 &&
      line.split(id).length - 1 === authenticationCount;
    if (known) result.knownLogCount += authenticationCount;
    result[known && !redaction ? 'expected' : 'unexpected'].push({ kind: 'cookie-id', source });
  }
  return result;
}
