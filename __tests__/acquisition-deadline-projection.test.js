import { expect, test } from '@jest/globals';
import { classifyFailure } from '../dist/lib/tool-errors.js';
import { safeEapiFailureEnvelope } from '../dist/lib/auth-diagnostics.js';

// Pin the intentionally retained PR-153 inner-walk remap, not an acquisition timeout.
test('inner-walk search exhaustion retains provider_timeout and safe later retry', () => {
  const failure = classifyFailure(
    {
      context: {
        details: {
          operation: 'search',
          failures: [
            { provider: 'libgen', host: 'mirror.invalid', reason: 'read_timeout' },
            { provider: 'libgen', host: '', reason: 'walk_budget_exhausted' },
          ],
        },
      },
    },
    'search',
    'libgen',
  );
  expect(failure.code).toBe('provider_timeout');
  expect(failure.info.retry).toBe('safe');
  expect(failure.info.detail.reason).toBe('walk_budget_exhausted');
  expect(failure.info.attempts).toEqual([
    { source: 'libgen', outcome: 'failed', code: 'provider_timeout', reason: 'read_timeout' },
    {
      source: 'libgen',
      outcome: 'failed',
      code: 'provider_timeout',
      reason: 'walk_budget_exhausted',
    },
  ]);
});

test('inner-walk Annas download child exhaustion retains provider_timeout and quota-aware retry', () => {
  const failure = classifyFailure(
    {
      context: {
        details: {
          operation: 'download',
          failures: [{ provider: 'annas', host: '', reason: 'walk_budget_exhausted' }],
        },
      },
    },
    'download',
    'annas',
  );
  expect(failure.code).toBe('provider_timeout');
  expect(failure.info.retry).toBe('may_spend_quota');
  expect(failure.info.detail.reason).toBe('walk_budget_exhausted');
  expect(failure.info.attempts).toEqual([
    {
      source: 'annas',
      outcome: 'failed',
      code: 'provider_timeout',
      reason: 'walk_budget_exhausted',
    },
  ]);
});

test.each([true, false, undefined])(
  'local budget projection issuance=%s has noncontradictory wording',
  (issued) => {
    const details = {
      reason: 'walk_budget_exhausted',
      ...(issued === undefined ? {} : { request_issued: issued }),
    };
    const result = safeEapiFailureEnvelope({
      type: 'AcquisitionError',
      error: 'untrusted prose',
      details,
    });
    expect(result).toEqual({
      error:
        issued === false
          ? 'Acquisition deadline exhausted; try again later'
          : 'Acquisition deadline exhausted',
      type: 'AcquisitionError',
      details,
    });
  },
);
