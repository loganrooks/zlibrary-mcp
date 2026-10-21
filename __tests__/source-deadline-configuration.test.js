import { expect, test } from '@jest/globals';
import { errorEnvelope, ERROR_CODES } from '../dist/lib/tool-errors.js';

// The code remains one of the existing 19; the recovery must address operator envs.
test.each(['search', 'download'])(
  'short %s source owner reports configuration recovery',
  (operation) => {
    const result = errorEnvelope(
      {
        context: {
          pythonErrorType: 'SourceConfigurationError',
          details: { reason: 'configuration_error', request_issued: false },
        },
      },
      operation,
      'libgen',
    );
    expect(ERROR_CODES).toHaveLength(19);
    expect(result.error.code).toBe('invalid_argument');
    expect(result.error.message).toMatch(/configuration error/i);
    expect(result.error.recovery).toContain('docs/RETRY_CONFIGURATION.md');
    expect(result.error.recovery).toContain('10000');
    expect(result.error.recovery).not.toContain('Correct the arguments');
    expect(result.error.retry).toBe('no');
  },
);

test('private failure projection retains a source configuration verdict without provider prose', async () => {
  const { safeEapiFailureEnvelope } = await import('../dist/lib/auth-diagnostics.js');
  const safe = safeEapiFailureEnvelope({
    type: 'SourceConfigurationError',
    error: 'untrusted configuration value and local path',
    details: { reason: 'configuration_error', request_issued: false },
  });
  expect(safe).toMatchObject({
    type: 'SourceConfigurationError',
    details: { reason: 'configuration_error', request_issued: false },
  });
  expect(JSON.stringify(safe)).not.toContain('untrusted');
  expect(
    errorEnvelope({ context: { pythonErrorType: safe.type, details: safe.details } }, 'download')
      .error.recovery,
  ).toContain('docs/RETRY_CONFIGURATION.md');
});
