export const requiredCases = [
  'S7 transient EAPI outage opens only EAPI; Library Genesis survives and saved processing is refused',
  'C8 fake binds and loads TLS without hostname resolution',
  'C9 startup deadline reports captured stderr and live process status',
  'C10 startup exit and spawn errors retain stderr and status',
  'S4 Library Genesis search survives authentication failures',
  'S6 healthy Library Genesis search reaches the real parser and fixture',
  'C1 known cookie-ID log cannot hide password key or CA leaks',
  'C2 only known authentication output may contain the cookie ID',
  'C3 redaction expectation forbids even the known cookie-ID log',
  'C4 source snapshot detects dist lib and porcelain changes',
  'C5 fake rejects a search without cookies',
  'C6 fake exits when its owner closes stdin',
  'C7 PID mismatch still closes every client',
  'Base known cookie-ID log finding is absent',
  'Epoch known cookie-ID log finding is absent',
  'S4 removed processing call cannot contact providers during authentication failures',
  'S1 sequential calls preserve identity and download exact bytes inside temp storage',
  'S2 five concurrent slow/fast calls correlate; count logins independently',
  'S2 session reuse: exactly one login (expected failure on master)',
  'S3 two independent server processes each return their own results',
  'S4 authentication outage respects the selected login policy; listing survives',
  'S5 capture observed tool names and argument names (not an approved surface)',
  'Base scans have zero unexpected sentinel findings',
  'E1 explicit cookie rejection with overlapping callers records one new epoch',
  'E1 rejection refresh is single-flight: exactly one successful new login',
  ...['timeout', 'wall', 'ambiguous400', 'success0'].flatMap((mode) => [
    `E2 ${mode}: execute ambiguity then recovery without discarding state`,
    `E2 ${mode}: ambiguous failure causes zero additional login attempts`,
  ]),
  'E3 invalid login stops at the configured zero-retry budget',
  'TLS control rejects the disposable certificate when trust is not passed',
  'Epoch scans have zero unexpected sentinel findings',
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
