import { test, expect } from '@jest/globals';
import { RefStore } from '../dist/lib/refs.js';
import { ToolFailure, errorEnvelope, ErrorEnvelopeSchema } from '../dist/lib/tool-errors.js';

test('closed error envelopes independently validate retry semantics and sanitized messages', () => {
  const envelope = errorEnvelope(new ToolFailure('outcome_unknown', 'Reply lost', {
    source: 'zlibrary', retry: 'may_spend_quota', detail: { reason: 'read_timeout' },
  }), 'download');
  expect(ErrorEnvelopeSchema.safeParse(envelope).success).toBe(true);
  expect(ErrorEnvelopeSchema.safeParse({ error: { ...envelope.error, code: 'new_code' } }).success).toBe(false);
  expect(envelope.error.attempts).toEqual([]);
});

test('refs survive reconnect, classify restart and wrong kind, and expire under shared LRU pressure', () => {
  const store = new RefStore({ nonce: 1n, capacity: 2, tombstones: 1 });
  const ref = store.mint('r', { title: 'First' });
  expect(store.get(ref, 'r').title).toBe('First');
  expect(() => new RefStore({ nonce: 2n }).get(ref, 'r')).toThrow(/other_process/);
  expect(() => store.get(ref, 'c')).toThrow(/kind/);
  const cursor = store.mint('c', { page: 2 });
  store.mint('r', { title: 'Second' });
  expect(() => store.get(ref, 'r')).toThrow(/expired/);
  expect(store.get(cursor, 'c').page).toBe(2);
  expect(() => store.get('r' + store.nonce + 'zzz', 'r')).toThrow(/unknown/);
});

test('forced counter collision after a tombstone has aged out refuses reissue', () => {
  const store = new RefStore({ nonce: 1n, capacity: 1, tombstones: 1 });
  store.mint('r', { title: 'First' });
  store.mint('r', { title: 'Second' });
  store.mint('r', { title: 'Third' });
  store.counter = 0n; // fault injection: monotonic high-water mark must win over bounded tombstones
  expect(() => store.mint('r', { title: 'Wrong' })).toThrow(/counter/);
});

test('forced cross-generation suffix collision checks nonce before table lookup', () => {
  const a = new RefStore({ nonce: 1n });
  const b = new RefStore({ nonce: 2n });
  const old = a.mint('r', { title: 'Old' });
  b.mint('r', { title: 'New' });
  expect(() => b.get(old, 'r')).toThrow(/other_process/);
  // Equal 64-bit nonces retain the documented 2^-64 aliasing bound, not an impossible absolute promise.
  const equal = new RefStore({ nonce: 1n, counter: 1n });
  equal.mint('r', { title: 'Different counter' });
  expect(() => equal.get(old, 'r')).toThrow(/unknown/);
});

test('only the allowlisted login certificate cause becomes typed TLS evidence', () => {
  const tls = errorEnvelope({ context: {
    reason: 'login_failed', pythonErrorType: 'ConnectError',
    loginToken: 'TLS certificate verification failed',
  } }, 'search', 'zlibrary');
  expect(tls.error).toMatchObject({
    source: 'zlibrary', code: 'provider_unreachable', retry: 'safe', detail: { reason: 'tls_error' },
  });
  expect(ErrorEnvelopeSchema.safeParse(tls).success).toBe(true);
  const unrelated = errorEnvelope({ context: {
    reason: 'internal', loginToken: 'SECRET ssl certificate https://private.invalid',
  } }, 'search', 'zlibrary');
  expect(unrelated.error).toMatchObject({ code: 'internal', detail: { reason: 'internal' } });
  expect(JSON.stringify([tls, unrelated])).not.toMatch(/SECRET|private\.invalid/);
});
