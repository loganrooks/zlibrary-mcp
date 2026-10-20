// Default: what master has fixed. Reuse/redaction (#248) and breaker isolation (#192);
// set REHEARSAL_EXPECT='' to rehearse a tree from before it.
const MASTER_FIXES = 'reuse,redaction,breaker';
const requested =
  process.env.REHEARSAL_EXPECT ??
  (process.env.REHEARSAL_EXPECT_REUSE === '1' ? 'reuse,redaction' : MASTER_FIXES);
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
  if (name.startsWith('S7 '))
    return expectedFixes.has('breaker') ? 'ordinary pass' : 'expected assertion failure';
  if (/survives authentication failures/.test(name)) {
    return expectedFixes.has('reuse') || expectedFixes.has('breaker')
      ? 'ordinary pass'
      : 'expected assertion failure';
  }
  const feature = /session reuse:|single-flight:|zero additional login attempts/.test(name)
    ? 'reuse'
    : /known cookie-ID log finding is absent/.test(name)
      ? 'redaction'
      : null;
  return feature && !expectedFixes.has(feature) ? 'expected assertion failure' : 'ordinary pass';
}
