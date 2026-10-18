const requested =
  process.env.REHEARSAL_EXPECT ??
  (process.env.REHEARSAL_EXPECT_REUSE === '1' ? 'reuse,redaction' : '');
export const expectedFixes = new Set(
  requested
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean),
);
for (const fix of expectedFixes) {
  if (!['reuse', 'redaction', 'breaker'].includes(fix))
    throw new Error('Unknown rehearsal expectation switch');
}
export function expectedOutcome(name) {
  const feature = /session reuse:|single-flight:|zero additional login attempts/.test(name)
    ? 'reuse'
    : /known cookie-ID log finding is absent/.test(name)
      ? 'redaction'
      : /independent of EAPI breaker/.test(name)
        ? 'breaker'
        : null;
  return feature && !expectedFixes.has(feature) ? 'expected assertion failure' : 'ordinary pass';
}
