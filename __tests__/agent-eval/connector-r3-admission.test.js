import { test, expect } from '@jest/globals';
import { measured } from './receipt-controls.js';
import { arms } from './tasks.js';
import { admitReceipt, comparisonSettings, cellIdentity } from './admission.js';
import { nodeDigest } from './node-runtime.js';
test('4318878598 schema5 requires common AND selected-build Node proofs; schema4 remains diagnostic', () => {
  const good = measured(arms[0]);
  expect(good.schemaVersion).toBe(5);
  expect(admitReceipt(good).eligible).toBe(true);
  for (const mutate of [
    (r) => (r.schemaVersion = 4),
    (r) => delete r.node,
    (r) => delete r.build.node,
    (r) => (r.nodeStable = false),
    (r) => (r.nodeEnd.sha256 = 'f'.repeat(64)),
    (r) => (r.build.nodeEnd.sha256 = 'f'.repeat(64)),
  ]) {
    const r = structuredClone(good);
    mutate(r);
    expect(admitReceipt(r).eligible).toBe(false);
  }
});
test('4318878598 common runtime controls comparison, selected-build runtime only controls cell identity', () => {
  const a = measured(arms[0]),
    b = measured(arms[1]);
  expect(comparisonSettings(a)).toBe(comparisonSettings(b));
  const before = cellIdentity(b);
  b.build.node.identity.node.binarySha256 = 'f'.repeat(64);
  b.build.node.sha256 = nodeDigest(b.build.node.identity);
  b.build.nodeEnd = structuredClone(b.build.node);
  expect(admitReceipt(b).eligible).toBe(true);
  expect(cellIdentity(b)).not.toBe(before);
  expect(comparisonSettings(a)).toBe(comparisonSettings(b));
  b.node.identity.node.binarySha256 = 'f'.repeat(64);
  b.node.sha256 = nodeDigest(b.node.identity);
  b.nodeEnd = structuredClone(b.node);
  expect(admitReceipt(b).eligible).toBe(true);
  expect(comparisonSettings(a)).not.toBe(comparisonSettings(b));
});
for (const [name, mutate] of [
  ['missing tool hash', (p) => delete p.identity.tool.cliSha256],
  ['unsupported execution policy', (p) => (p.identity.node.options = '--conditions=foreign')],
  ['duplicate edge', (p) => p.identity.edges.push({ ...p.identity.edges[0] })],
  ['duplicate anchor', (p) => (p.identity.anchors[0] = { ...p.identity.anchors[1] })],
  ['duplicate package', (p) => p.identity.packages.push(structuredClone(p.identity.packages[0]))],
  [
    'traversal',
    (p) => {
      p.identity.packages[0].files[0].path = '../runtime.js';
      p.identity.packages[0].sha256 = nodeDigest(p.identity.packages[0].files);
    },
  ],
  ['foreign graph edge', (p) => (p.identity.edges[0].to = 'node_modules/outside')],
  ['selected install target drift', (p) => (p.local.install = '/foreign/install')],
  ['failed config boundary', (p) => (p.audit.configContentReads = 1)],
  ['manifest mismatch', (p) => (p.identity.manifests[0].sha256 = 'f'.repeat(64))],
])
  test(`4318878598 recomputed malformed proof rejects ${name}`, () => {
    const r = measured(arms[0]);
    expect(admitReceipt(r).eligible).toBe(true);
    mutate(r.node);
    r.node.sha256 = nodeDigest(r.node.identity);
    r.nodeEnd = structuredClone(r.node);
    expect(admitReceipt(r).eligible).toBe(false);
  });
