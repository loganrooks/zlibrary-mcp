import { test, expect } from '@jest/globals';
import { admitReceipt } from './admission.js';
import { measured } from './receipt-controls.js';
import { arms } from './tasks.js';

for (const [name, mutate] of [
  [
    'TERM sent',
    (c) => {
      c.termSent = true;
    },
  ],
  [
    'KILL sent',
    (c) => {
      c.killSent = true;
    },
  ],
  [
    'missing TERM flag',
    (c) => {
      delete c.termSent;
    },
  ],
  [
    'missing KILL flag',
    (c) => {
      delete c.killSent;
    },
  ],
  [
    'non-closed reason',
    (c) => {
      c.reason = 'timeout';
    },
  ],
  [
    'missing reason',
    (c) => {
      delete c.reason;
    },
  ],
  [
    'unknown observation',
    (c) => {
      c.observations = ['unknown', 'gone'];
    },
  ],
  [
    'alive final observation',
    (c) => {
      c.observations = ['gone', 'alive'];
    },
  ],
  [
    'missing observations',
    (c) => {
      delete c.observations;
    },
  ],
  [
    'empty observations',
    (c) => {
      c.observations = [];
    },
  ],
])
  test('S3 capture consistency refuses ' + name, () => {
    const receipt = measured(arms[1]);
    expect(admitReceipt(receipt).eligible).toBe(true);
    mutate(receipt.results[0].capture.cleanup);
    expect(admitReceipt(receipt).eligible).toBe(false);
  });
