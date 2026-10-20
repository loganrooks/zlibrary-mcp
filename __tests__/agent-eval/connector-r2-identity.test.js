import { beforeEach, afterEach, test, expect } from '@jest/globals';
import { mkdtemp, mkdir, writeFile, symlink, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import * as server from './server.js';
import { admitReceipt, comparisonSettings } from './admission.js';
import { measured } from './receipt-controls.js';
import { syntheticNodeProof } from './node-receipt-controls.js';
import { arms } from './tasks.js';

let temp;
beforeEach(async () => {
  temp = await mkdtemp(path.join(os.tmpdir(), 'eval-common-tree-'));
});
afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});
const entries = {
  'package.json': '{"name":"synthetic-common","version":"1.0.0"}\n',
  'package-lock.json': '{"lockfileVersion":3}\n',
  '__tests__/agent-eval/run.mjs': 'export const prompt = "synthetic";\n',
  '__tests__/agent-eval/oracles.js': 'export const score = true;\n',
  '__tests__/rehearsal/harness.js': 'export const harness = true;\n',
  '__tests__/rehearsal/fake_catalogue.py': 'synthetic_catalogue = True\n',
};
async function fixture(root, head = 'a'.repeat(40), changes = {}) {
  const committed = { ...entries, ...changes };
  for (const [name, bytes] of Object.entries(committed)) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), bytes);
  }
  const gitRead = (_root, ...args) => {
    if (args[0] === 'rev-parse') return head;
    if (args[0] === 'status') return '';
    if (args[0] === 'ls-tree')
      return (
        Object.entries(committed)
          .filter(([name]) =>
            args
              .slice(args.indexOf('--') + 1)
              .some((scope) => name === scope || name.startsWith(scope + '/')),
          )
          .map(
            ([name, bytes]) =>
              `100644 blob ${createHash('sha1')
                .update(`blob ${Buffer.byteLength(bytes)}\0`)
                .update(bytes)
                .digest('hex')}\t${name}`,
          )
          .join('\0') + '\0'
      );
    throw new Error('unexpected read-only fixture Git operation');
  };
  return { root, gitRead };
}
const verify = (options) => {
  expect(server.verifyEvaluatorIdentity).toBeInstanceOf(Function);
  return server.verifyEvaluatorIdentity(options);
};
test('4318353602 relocated identical committed common source is compatible despite different HEAD locators', async () => {
  const a = await verify(await fixture(path.join(temp, 'A'), 'a'.repeat(40))),
    b = await verify(await fixture(path.join(temp, 'B'), 'b'.repeat(40)));
  expect(a).toMatchObject({ status: 'verified', clean: true, head: 'a'.repeat(40) });
  expect(b.head).not.toBe(a.head);
  expect(b.sha256).toBe(a.sha256);
});
for (const mutation of [
  'dirty scorer hidden from status',
  'extra ignored code',
  'symlink',
  'missing tracked source',
  'code inside pycache',
])
  test(`4318353602 rejects ${mutation}`, async () => {
    const options = await fixture(temp),
      target = path.join(temp, '__tests__/agent-eval/oracles.js');
    if (mutation === 'dirty scorer hidden from status') await writeFile(target, 'changed scoring');
    if (mutation === 'extra ignored code')
      await writeFile(path.join(temp, '__tests__/agent-eval/extra.js'), 'untracked ignored code');
    if (mutation === 'symlink') {
      await rm(target);
      await symlink(path.join(temp, '__tests__/agent-eval/run.mjs'), target);
    }
    if (mutation === 'missing tracked source') await rm(target);
    if (mutation === 'code inside pycache') {
      await mkdir(path.join(temp, '__tests__/agent-eval/__pycache__'));
      await writeFile(path.join(temp, '__tests__/agent-eval/__pycache__/hidden.js'), 'code');
    }
    await expect(verify(options)).rejects.toThrow(/evaluator|source|symlink|tracked/);
  });
test('4318353602 declared generated Python bytecode alone does not change source identity', async () => {
  const options = await fixture(temp),
    a = await verify(options);
  await mkdir(path.join(temp, '__tests__/agent-eval/__pycache__'));
  await writeFile(
    path.join(temp, '__tests__/agent-eval/__pycache__/sitecustomize.cpython-313.pyc'),
    'generated',
  );
  expect((await verify(options)).sha256).toBe(a.sha256);
});
test('4318353602 missing/dirty/drifting evaluator proof is ineligible, different scorer cannot share compatibility', () => {
  const a = measured(arms[0]),
    b = measured(arms[1]);
  a.evaluator = { status: 'verified', clean: true, sha256: '1'.repeat(64) };
  b.evaluator = { status: 'verified', clean: false, sha256: '2'.repeat(64) };
  expect(admitReceipt(b).eligible).toBe(false);
  expect(comparisonSettings(a)).not.toBe(comparisonSettings(b));
});

test('4318353602 admission rejects legacy schema 3, missing common proof and end drift', () => {
  for (const mutate of [
    (r) => (r.schemaVersion = 3),
    (r) => delete r.evaluator,
    (r) => (r.evaluator.clean = false),
    (r) => (r.evaluatorStable = false),
    (r) => (r.evaluatorEnd.sha256 = 'f'.repeat(64)),
  ]) {
    const r = measured(arms[0]);
    expect(admitReceipt(r).eligible).toBe(true);
    mutate(r);
    expect(admitReceipt(r).eligible).toBe(false);
  }
});
test('4318353602 loaded evaluator root is independent of selected server build root', async () => {
  const common = await fixture(path.join(temp, 'executing')),
    foreign = await fixture(path.join(temp, 'server'));
  await writeFile(
    path.join(foreign.root, '__tests__/agent-eval/oracles.js'),
    'unrelated selected build scorer',
  );
  const proof = await verify(common);
  expect(proof.status).toBe('verified');
  await expect(verify(foreign)).rejects.toThrow(/dirty evaluator/);
});

test('4318353602 different clean committed scorer bytes cannot share comparison eligibility settings', async () => {
  const first = await verify(await fixture(path.join(temp, 'A'), 'a'.repeat(40)));
  const different = await verify(
    await fixture(path.join(temp, 'B'), 'b'.repeat(40), {
      '__tests__/agent-eval/oracles.js': 'export const score = false;\n',
    }),
  );
  const a = measured(arms[0]),
    b = measured(arms[1]);
  for (const [receipt, proof] of [
    [a, first],
    [b, different],
  ]) {
    receipt.evaluator = proof;
    receipt.node = syntheticNodeProof(proof.files);
    receipt.nodeEnd = structuredClone(receipt.node);
    receipt.evaluatorEnd = structuredClone(proof);
    expect(admitReceipt(receipt).eligible).toBe(true);
  }
  expect(comparisonSettings(a)).not.toBe(comparisonSettings(b));
  const relocated = await verify(await fixture(path.join(temp, 'relocated'), 'c'.repeat(40)));
  b.evaluator = relocated;
  b.node = syntheticNodeProof(relocated.files);
  b.nodeEnd = structuredClone(b.node);
  b.evaluatorEnd = structuredClone(relocated);
  expect(admitReceipt(b).eligible).toBe(true);
  expect(comparisonSettings(a)).toBe(comparisonSettings(b));
});
test('4318353602 actual end scorer drift and mid-check HEAD drift fail closed', async () => {
  const options = await fixture(temp);
  await verify(options);
  await writeFile(
    path.join(temp, '__tests__/agent-eval/oracles.js'),
    'changed after initial identity',
  );
  await expect(verify(options)).rejects.toThrow(/dirty evaluator/);
  const fresh = await fixture(path.join(temp, 'fresh'));
  let reads = 0;
  await expect(
    verify({
      ...fresh,
      gitRead: (root, ...args) =>
        args[0] === 'rev-parse' && reads++ ? 'b'.repeat(40) : fresh.gitRead(root, ...args),
    }),
  ).rejects.toThrow(/HEAD changed/);
});

for (const name of ['package.json', 'package-lock.json'])
  test(`4318878598 common committed ${name} is part of actual evaluator identity`, async () => {
    const options = await fixture(path.join(temp, 'A'));
    const a = await verify(options),
      b = await verify(
        await fixture(path.join(temp, 'B'), 'b'.repeat(40), {
          [name]: 'different committed manifest\n',
        }),
      );
    expect(a.files.some((f) => f.path === name)).toBe(true);
    expect(a.sha256).not.toBe(b.sha256);
    await writeFile(path.join(temp, 'A', name), 'hidden dirty manifest');
    await expect(verify(options)).rejects.toThrow(/dirty evaluator/);
  });
