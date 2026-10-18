export const requiredCases = [
  'S1 sequential calls preserve identity and download exact bytes inside temp storage',
  'S2 five concurrent slow/fast calls correlate; count logins independently',
  'S2 session reuse: exactly one login (expected failure on master)',
  'S3 two independent server processes each return their own results',
  'S4 EAPI outage opens shared breaker after five failures; local bridge shares breaker; listing survives',
  'S5 capture observed tool names and argument names (not an approved surface)',
  'Base reply stderr and output-file sentinel scan has no unprotected findings',
  'E1 explicit cookie rejection with overlapping callers records one new epoch',
  'E1 rejection refresh is single-flight: exactly one successful new login',
  ...['timeout', 'wall', 'ambiguous400', 'success0'].flatMap((mode) => [
    `E2 ${mode}: execute ambiguity then recovery without discarding state`,
    `E2 ${mode}: ambiguous failure causes zero additional login attempts`,
  ]),
  'E3 invalid login stops at the configured zero-retry budget',
  'TLS control rejects the disposable certificate when trust is not passed',
  'Epoch reply stderr and output-file sentinel scan has no unprotected findings',
];

export function assess(assertions) {
  return requiredCases.map((name) => {
    const matches = assertions.filter((a) => a.fullName === name);
    return {
      name,
      expected: 1,
      executed: matches.filter((a) => ['passed', 'failed'].includes(a.status)).length,
      status: matches.length === 1 ? matches[0].status : 'missing-or-duplicate',
    };
  });
}
