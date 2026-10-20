import { test, expect } from '@jest/globals';
import { AcquisitionTools } from '../../dist/lib/acquisition-tools.js';
import { classifyFailure, errorEnvelope } from '../../dist/lib/tool-errors.js';

test('internal acquireRef adds only item provenance and preserves download bookkeeping', async () => {
  const calls = [];
  const tools = new AcquisitionTools(
    async (op, args) => {
      calls.push([op, args]);
      if (op === 'search') return { books: [{ id: '1', hash: 'a', title: 'Book' }] };
      return {
        path: '/book',
        bytes: 1,
        reused: false,
        transfer_skipped: false,
        verified: 'sha256',
        record: '/book.acq.json',
      };
    },
    { ZLIBRARY_EMAIL: 'offline', ZLIBRARY_PASSWORD: 'offline' },
  );
  const { rows } = await tools.call('search', { query: 'Book', sources: ['zlibrary'] });
  await tools.acquireRef(rows[0].ref, { request: { item_id: 'w1', why_chosen: 'any: title 1' } });
  expect(calls.at(-1)[1].request).toEqual({
    ref: rows[0].ref,
    query: 'Book',
    item_id: 'w1',
    why_chosen: 'any: title 1',
  });
  expect(
    (await tools.call('download', { ref: rows[0].ref, request: { item_id: 'w1' } })).error.code,
  ).toBe('invalid_argument');
});

test('lease, circuit and auth backoff survive classification as distinguishable reasons', () => {
  const failures = [
    { context: { details: { reason: 'breaker_open', request_issued: false } } },
    { code: 'CIRCUIT_BREAKER_OPEN', context: { retryAfterMs: 1200 } },
    { context: { details: { reason: 'auth_backoff', request_issued: false } } },
  ].map((e) => errorEnvelope(classifyFailure(e, 'download', 'zlibrary'), 'download').error);
  expect(failures.map((e) => e.code)).toEqual(['breaker_open', 'breaker_open', 'breaker_open']);
  expect(failures.map((e) => e.detail.reason)).toEqual(['breaker_open', 'unknown', 'auth_backoff']);
  expect(failures[1].retry_after_s).toBe(2);
});
