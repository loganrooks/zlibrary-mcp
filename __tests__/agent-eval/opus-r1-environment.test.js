import { test, expect } from '@jest/globals';
import { admitReceipt, comparisonSettings } from './admission.js';
import { measured } from './receipt-controls.js';
import { arms } from './tasks.js';
import { summarize } from './report.js';
import {
  driverEnvironmentRecord,
  driverEnvironmentErrors,
  environmentPolicy,
} from './driver-environment.js';

test('S1 refuses a missing per-row environment record and refuses differing comparison environments', () => {
  const a = measured(arms[0]);
  delete a.results[0].driverEnvironment;
  expect(admitReceipt(a).eligible).toBe(false);
  const left = measured(arms[0]);
  const right = measured(arms[1], 50);
  left.driverEnvironment = { sha256: '1'.repeat(64) };
  right.driverEnvironment = { sha256: '2'.repeat(64) };
  expect(comparisonSettings(left)).not.toBe(comparisonSettings(right));
  expect(summarize([left, right]).comparisons[0].status).not.toBe('bar met');
});
test('S1 each documented routing/model value binds identity; secrets are presence-only and never read', () => {
  for (const [driver, policy] of Object.entries(environmentPolicy)) {
    const empty = driverEnvironmentRecord(driver, {});
    expect(driverEnvironmentErrors(empty, driver)).toEqual([]);
    for (const key of policy.values) {
      const value = key.endsWith('BASE_URL')
        ? 'https://routing.example.invalid/v1'
        : 'synthetic-setting';
      expect(driverEnvironmentRecord(driver, { [key]: value }).sha256).not.toBe(empty.sha256);
    }
    for (const key of policy.presence) {
      const env = Object.defineProperty({}, key, {
        enumerable: true,
        get() {
          throw new Error('secret bytes must not be inspected');
        },
      });
      const record = driverEnvironmentRecord(driver, env);
      expect(record.presence[key]).toBe(true);
      expect(record.sha256).not.toBe(empty.sha256);
      expect(record).toEqual(
        driverEnvironmentRecord(driver, { [key]: 'different synthetic secret' }),
      );
      expect(JSON.stringify(record)).not.toContain('different synthetic secret');
    }
    for (const endpoint of [
      'https://synthetic-secret@example.invalid',
      'https://example.invalid/?token=synthetic-secret',
      'https://example.invalid/#synthetic-secret',
    ]) {
      let error;
      try {
        driverEnvironmentRecord(driver, {
          [policy.values.find((k) => k.endsWith('BASE_URL'))]: endpoint,
        });
      } catch (e) {
        error = e;
      }
      expect(error?.message).toMatch(/endpoint refused/);
      expect(error?.message).not.toContain('synthetic-secret');
    }
  }
});
test('S1 real valid records refuse environment mismatch, missing records and tampering', () => {
  const bind = (r, env) => {
    r.driverEnvironment = driverEnvironmentRecord(r.driver, env);
    for (const x of r.results) x.driverEnvironment = structuredClone(r.driverEnvironment);
    return r;
  };
  const a = bind(measured(arms[0]), { ANTHROPIC_BASE_URL: 'https://a.example.invalid' });
  const b = bind(measured(arms[1], 50), { ANTHROPIC_BASE_URL: 'https://b.example.invalid' });
  expect(admitReceipt(a).eligible).toBe(true);
  expect(admitReceipt(b).eligible).toBe(true);
  expect(summarize([a, b]).comparisons[0].status).toMatch(/incompatible/);
  for (const mutate of [
    (r) => {
      delete r.driverEnvironment;
    },
    (r) => {
      delete r.results[0].driverEnvironment;
    },
    (r) => {
      r.results[0].driverEnvironment = b.driverEnvironment;
    },
    (r) => {
      r.driverEnvironment.values.ANTHROPIC_MODEL = 'tampered';
    },
    (r) => {
      r.driverEnvironment.presence.ANTHROPIC_API_KEY = 'forbidden-content';
    },
    (r) => {
      delete r.driverEnvironment.values.CLAUDE_CONFIG_DIR;
    },
  ]) {
    const changed = structuredClone(a);
    mutate(changed);
    expect(admitReceipt(changed).eligible).toBe(false);
  }
});
