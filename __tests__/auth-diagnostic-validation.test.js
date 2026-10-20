import { expect, test } from '@jest/globals';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { runPythonBridge } from '../lib/python-runner.js';
import { parseBridgeErrorEnvelope } from '../lib/python-bridge.js';
import { errorEnvelope } from '../lib/tool-errors.js';

const diagnostics = {
  failure_kind: 'ambiguous_status',
  attempt: 1,
  refresh_count: 0,
  request_id: '00000000-0000-4000-8000-000000000001',
};
const cases = ['ValueError', 'TypeError'].flatMap((type) =>
  [
    ['absent', {}, 'local'],
    ['null', { diagnostics: null }, 'rejected'],
    ['false', { diagnostics: false }, 'rejected'],
    ['zero', { diagnostics: 0 }, 'rejected'],
    ['empty string', { diagnostics: '' }, 'rejected'],
    ['array', { diagnostics: [] }, 'rejected'],
    ['incomplete', { diagnostics: { failure_kind: 'transport', attempt: 1 } }, 'rejected'],
    ['invalid kind', { diagnostics: { ...diagnostics, failure_kind: 'unknown' } }, 'rejected'],
    ['unknown version', { diagnostics: { ...diagnostics, version: 2 } }, 'rejected'],
    ['valid', { diagnostics }, 'diagnosed'],
  ].map(([name, fields, outcome]) => ({
    type,
    name,
    record: { error: 'untrusted-argument-prose', type, ...fields },
    outcome,
  })),
);

function publicError(parsed) {
  return errorEnvelope(
    {
      context: {
        pythonErrorType: parsed?.type,
        details: parsed?.details,
        diagnostics: parsed?.diagnostics,
      },
    },
    'search',
    'zlibrary',
  ).error;
}

// Catches malformed/version-mismatched diagnostics being laundered into a local
// invalid_argument verdict. Valid diagnostics and truly absent fields are controls.
test.each(cases)('parser handles $type with $name diagnostics', ({ record, outcome }) => {
  const parsed = parseBridgeErrorEnvelope(JSON.stringify(record));
  if (outcome === 'rejected') {
    expect(parsed).toBeNull();
    expect(publicError(parsed).code).toBe('internal');
  } else if (outcome === 'local') {
    expect(parsed.type).toBe(record.type);
    expect(parsed).not.toHaveProperty('diagnostics');
    expect(publicError(parsed).code).toBe('invalid_argument');
  } else {
    expect(parsed.diagnostics).toEqual(diagnostics);
    expect(parsed).not.toHaveProperty('details');
    expect(JSON.stringify(parsed)).not.toContain('untrusted-argument-prose');
  }
});

test.each(cases)(
  'runner handles $type with $name diagnostics',
  async ({ record, outcome }) => {
    const directory = mkdtempSync(join(tmpdir(), 'i305-validation-'));
    try {
      writeFileSync(
        join(directory, 'failure.py'),
        'import sys\nprint(sys.argv[1], file=sys.stderr)\nsys.exit(1)\n',
      );
      const failure = await runPythonBridge(
        'failure.py',
        {
          pythonPath: join(process.cwd(), '.venv/bin/python'),
          scriptPath: directory,
          mode: 'text',
          args: [JSON.stringify(record)],
          env: { ...process.env, ZLIBRARY_DIAGNOSTIC_EAPI: '1' },
        },
        { timeoutMs: 5000 },
      ).catch((error) => error);
      expect(failure).toBeInstanceOf(Error);
      expect(String(failure.stack) + JSON.stringify(failure)).not.toContain(
        'untrusted-argument-prose',
      );
      const parsed = parseBridgeErrorEnvelope(failure.stderr);
      if (outcome === 'rejected') {
        expect(failure.stderr).toBe('');
        expect(parsed).toBeNull();
        expect(publicError(parsed).code).toBe('internal');
      } else if (outcome === 'local') {
        expect(JSON.parse(failure.stderr)).toEqual({
          error: 'Invalid bridge arguments',
          type: record.type,
          details: { reason: 'invalid_argument', request_issued: false },
        });
        expect(publicError(parsed)).toMatchObject({
          code: 'invalid_argument',
          detail: { reason: 'invalid_argument', request_issued: false },
        });
      } else {
        expect(parsed.diagnostics).toEqual(diagnostics);
        expect(parsed).not.toHaveProperty('details');
      }
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  },
);
