import { jest, describe, beforeAll, afterAll, afterEach, test, expect } from '@jest/globals';
import { mkdtemp, realpath, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { nodeFixture } from './node-runtime-controls.js';
const actual = await import('./node-runtime.js');
const actualEvaluator = await import('./evaluator-identity.js');
const evaluatorRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let common,
  selected,
  inventoryUnavailable = false;
// Only clean-Git evaluator admission and the module-root locator are substituted.
// Node inventory, byte hashing and the actual server recheck methods remain real.
// This does not claim a committed positive startup from this dirty worktree.
jest.unstable_mockModule('./evaluator-identity.js', () => ({
  ...actualEvaluator,
  verifyEvaluatorIdentity: async () => ({ sha256: 'e'.repeat(64) }),
}));
jest.unstable_mockModule('./node-runtime.js', () => ({
  ...actual,
  verifyNodeRuntime: (options) => {
    if (inventoryUnavailable) throw new Error('runtime inventory deliberately unavailable');
    return actual.verifyNodeRuntime({
      ...options,
      root: options.root === evaluatorRoot ? common.root : options.root,
    });
  },
}));
const { EvaluationServer, verifyBuildArtifacts } = await import('./server.js');
describe('4318878598 actual runtime drift at server lifecycle boundaries', () => {
  let temp, node, buildNode;
  // The immutable baseline is captured once. Every boundary below still runs
  // the real inventory and byte recheck; no recheck proof is mocked or cached.
  beforeAll(async () => {
    temp = await realpath(await mkdtemp(path.join(os.tmpdir(), 'node-launch-drift-')));
    common = await nodeFixture(path.join(temp, 'common'));
    selected = await nodeFixture(path.join(temp, 'selected'));
    node = await actual.verifyNodeRuntime({ root: common.root });
    buildNode = await actual.verifyNodeRuntime({ root: selected.root });
  }, 30000);
  afterEach(async () => {
    // These tests are sequential. Restore the only mutated bytes even when a
    // drift assertion fails, so neither role can contaminate the next case.
    for (const target of [common, selected]) {
      if (target)
        await writeFile(
          path.join(target.root, 'node_modules', target.sdk, 'runtime.json'),
          '{"runtime":"original"}',
        );
    }
  });
  afterAll(async () => {
    if (temp) await rm(temp, { recursive: true, force: true });
  });
  function serverWithBaseline() {
    const s = new EvaluationServer();
    s.buildRoot = selected.root;
    s.evaluator = { sha256: 'e'.repeat(64) };
    s.node = node;
    s.buildNode = buildNode;
    return s;
  }
  test('unchanged common and selected runtimes pass the server recheck', async () => {
    const s = serverWithBaseline();
    await expect(s.assertNodeIdentity()).resolves.toHaveProperty(
      'buildNode.sha256',
      s.buildNode.sha256,
    );
  }, 30000);
  // Each deadline covers one real boundary check (two full runtime proofs),
  // instead of setup + positive + prelaunch + end (eight proofs per case).
  for (const role of ['common', 'selected']) {
    for (const boundary of ['assertNodeIdentity', 'finishIdentity']) {
      test(`${role} runtime mutation refuses ${boundary}`, async () => {
        const s = serverWithBaseline();
        for (const fixture of [common, selected]) {
          expect(
            await readFile(
              path.join(fixture.root, 'node_modules', fixture.sdk, 'runtime.json'),
              'utf8',
            ),
          ).toBe('{"runtime":"original"}');
        }
        const target = role === 'common' ? common : selected;
        await writeFile(
          path.join(target.root, 'node_modules', target.sdk, 'runtime.json'),
          'changed between start and launch/end',
        );
        await expect(s[boundary]()).rejects.toThrow(/Node common\/selected runtime identity drift/);
      }, 30000);
    }
  }
});

test('4318878598 scratch compiler proof remains independent of unavailable runtime inventory', async () => {
  inventoryUnavailable = true;
  try {
    const proof = await verifyBuildArtifacts({ buildRoot: evaluatorRoot });
    expect(proof.status).toBe('verified');
    expect(proof.compiledRuntime).toEqual(proof.selectedRuntime);
  } finally {
    inventoryUnavailable = false;
  }
}, 30000);
