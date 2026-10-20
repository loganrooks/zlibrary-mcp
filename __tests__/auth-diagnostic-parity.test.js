import { expect, test } from '@jest/globals';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import ts from 'typescript';
import { authDiagnosticsFor, safeEapiFailureEnvelope } from '../lib/auth-diagnostics.js';
import { isRetryableError, isTransientDependencyError, withRetry } from '../lib/retry-manager.js';
import { BridgeTimeoutError } from '../lib/errors.js';
import { errorEnvelope } from '../lib/tool-errors.js';

const diagnostics = {
  failure_kind: 'ambiguous_status',
  attempt: 1,
  refresh_count: 0,
  request_id: '00000000-0000-4000-8000-000000000001',
};

// Discover the actual policy lists, so additions to either boundary/retry policy
// cannot silently escape these cross-language contract checks.
function sourcePolicy(file, argument) {
  const source = ts.createSourceFile(
    file,
    readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
  );
  const found = [];
  const arrays = new Map();
  function visit(node) {
    if (
      ts.isVariableDeclaration(node) &&
      node.initializer &&
      ts.isArrayLiteralExpression(node.initializer)
    )
      arrays.set(node.name.getText(source), node.initializer);
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      node.expression.name.text === 'includes' &&
      node.arguments[0]?.getText(source) === argument
    ) {
      const receiver = node.expression.expression;
      const array = ts.isArrayLiteralExpression(receiver)
        ? receiver
        : arrays.get(receiver.getText(source));
      if (array) found.push(...array.elements.map((v) => v.text));
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  expect(found.length).toBeGreaterThan(0);
  return found;
}
function acquisitionReasons() {
  const file = 'src/lib/auth-diagnostics.ts';
  const source = ts.createSourceFile(
    file,
    readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
  );
  let reasons;
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(source) === 'messages')
      reasons = node.initializer.properties.map((p) => p.name.getText(source));
    ts.forEachChild(node, visit);
  }
  visit(source);
  expect(reasons.length).toBeGreaterThan(0);
  return reasons;
}
function python(code, args = []) {
  return JSON.parse(
    execFileSync(join(process.cwd(), '.venv/bin/python'), ['-c', code, ...args], {
      encoding: 'utf8',
      env: { ...process.env, PYTHONPATH: join(process.cwd(), 'lib') },
    }),
  );
}

test('transient type parity: Python, TypeScript and retry policy preserve the same names', async () => {
  const retryTypes = sourcePolicy('src/lib/retry-manager.ts', 'error.context?.pythonErrorType');
  const tsTypes = sourcePolicy('src/lib/auth-diagnostics.ts', 'value.type');
  const py = python(
    `import json, sys, zlibrary
from auth_diagnostics import FAILURE_TYPES, failure_type
projected = {name: failure_type(type(name, (Exception,), {})()) for name in json.loads(sys.argv[1])}
print(json.dumps({'origin': zlibrary.__file__, 'types': sorted(FAILURE_TYPES),
 'projected': projected}))`,
    [JSON.stringify(retryTypes)],
  );
  expect(py.origin).toBe(join(process.cwd(), 'zlibrary/src/zlibrary/__init__.py'));
  expect([...tsTypes].sort()).toEqual(py.types);
  expect(py.projected).toEqual(Object.fromEntries(retryTypes.map((type) => [type, type])));
  for (const type of retryTypes) {
    expect(py.projected[type]).toBe(type);
    const projected = safeEapiFailureEnvelope({ type, diagnostics });
    expect(projected.type).toBe(type);
    const error = { code: 'PYTHON_ERROR', context: { pythonErrorType: projected.type } };
    expect(isTransientDependencyError(error)).toBe(true);
    expect(isRetryableError(error)).toBe(true);
    let attempts = 0;
    await withRetry(
      async () => {
        if (++attempts === 1) throw error;
      },
      { maxRetries: 1, initialDelay: 1, shouldRetry: isRetryableError },
    );
    expect(attempts).toBe(2);
  }
  expect(safeEapiFailureEnvelope({ type: 'untrusted-type', diagnostics }).type).toBe(
    'RuntimeError',
  );
});

test('acquisition reason parity preserves Python/TypeScript envelopes, codes and recovery', () => {
  const reasons = acquisitionReasons();
  const py = python(
    `import asyncio, contextlib, io, json, sys
import python_bridge as bridge
from lib.acquisition import AcquisitionError
async def initialize(): pass
bridge.initialize_eapi_client = initialize
bridge._eapi_client = None
bridge._session_input = None
results = {}
async def run():
 for reason in json.loads(sys.argv[1]):
  async def fail(*args): raise AcquisitionError(reason, 'untrusted-provider-prose', issued=True)
  bridge._dispatch_bridge_function = fail
  sys.argv = ['python_bridge.py', 'search', '{}']
  stderr = io.StringIO()
  with contextlib.redirect_stderr(stderr):
   try: await bridge.main()
   except SystemExit as error: assert error.code == 1
  results[reason] = json.loads(stderr.getvalue().strip().splitlines()[-1])
asyncio.run(run())
print(json.dumps(results))`,
    [JSON.stringify(reasons)],
  );
  for (const reason of reasons) {
    expect(py[reason].details.reason).toBe(reason);
    expect(py[reason].diagnostics.failure_kind).toBe('ambiguous_status');
    const projected = safeEapiFailureEnvelope(py[reason]);
    expect(projected.details).toEqual({ reason, request_issued: true });
    const local = safeEapiFailureEnvelope({
      type: 'AcquisitionError',
      details: { reason, request_issued: true },
    });
    const envelope = (value) =>
      errorEnvelope(
        {
          context: {
            pythonErrorType: value.type,
            details: value.details,
            diagnostics: value.diagnostics,
          },
        },
        'download',
        'zlibrary',
      );
    const result = envelope(projected);
    const baseline = envelope(local);
    expect(result.error.code).toBe(baseline.error.code);
    expect(result.error.code).not.toBe('internal');
    expect(result.error.recovery).toBe(baseline.error.recovery);
    expect(result.error.retry).toBe(baseline.error.retry);
    expect(JSON.stringify(result)).not.toContain('untrusted-provider-prose');
  }
});

test.each(acquisitionReasons())(
  'TypeScript preserves acquisition reason %s with diagnostics',
  (reason) => {
    const projected = safeEapiFailureEnvelope({
      type: 'AcquisitionError',
      diagnostics,
      details: { reason, request_issued: true },
    });
    expect(projected.details).toEqual({ reason, request_issued: true });
  },
);

test('caller abort is cancellation, not a transport outage; real timeout stays transport', () => {
  const abort = new BridgeTimeoutError('Bridge call aborted', { reason: 'aborted' });
  abort.context.diagnostics = authDiagnosticsFor(abort, diagnostics.request_id, 1, 0);
  expect(abort.context.diagnostics.failure_kind).toBe('ambiguous_status');
  expect(errorEnvelope(abort, 'download', 'zlibrary').error.code).toBe('cancelled');
  expect(isTransientDependencyError(abort)).toBe(false);
  expect(isRetryableError(abort)).toBe(false);
  const timeout = new BridgeTimeoutError('Bridge timed out', { reason: 'timeout' });
  expect(authDiagnosticsFor(timeout, diagnostics.request_id, 1, 0).failure_kind).toBe('transport');
});
