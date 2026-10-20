import { jest, beforeEach, afterEach, test, expect } from '@jest/globals';
import { mkdtemp, realpath, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { nodeFixture } from './node-runtime-controls.js';
const actual = await import('./node-runtime.js');
const actualEvaluator = await import('./evaluator-identity.js');
const evaluatorRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let common, selected, temp, inventoryUnavailable;
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
beforeEach(async () => {
  inventoryUnavailable = false;
  temp = await realpath(await mkdtemp(path.join(os.tmpdir(), 'node-launch-drift-')));
  common = await nodeFixture(path.join(temp, 'common'));
  selected = await nodeFixture(path.join(temp, 'selected'));
});
afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});
for (const role of ['common', 'selected'])
  test(`4318878598 actual ${role} runtime mutation refuses prelaunch and end server rechecks`, async () => {
    const s = new EvaluationServer();
    s.buildRoot = selected.root;
    s.evaluator = { sha256: 'e'.repeat(64) };
    s.node = await actual.verifyNodeRuntime({ root: common.root });
    s.buildNode = await actual.verifyNodeRuntime({ root: selected.root });
    await expect(s.assertNodeIdentity()).resolves.toHaveProperty(
      'buildNode.sha256',
      s.buildNode.sha256,
    );
    const target = role === 'common' ? common : selected;
    await writeFile(
      path.join(target.root, 'node_modules', target.sdk, 'runtime.json'),
      'changed between start and launch/end',
    );
    await expect(s.assertNodeIdentity()).rejects.toThrow(
      /Node common\/selected runtime identity drift/,
    );
    await expect(s.finishIdentity()).rejects.toThrow(
      /Node common\/selected runtime identity drift/,
    );
  }, 30000);

test('4318878598 scratch compiler proof remains independent of unavailable runtime inventory', async () => {
  inventoryUnavailable = true;
  const proof = await verifyBuildArtifacts({ buildRoot: evaluatorRoot });
  expect(proof.status).toBe('verified');
  expect(proof.compiledRuntime).toEqual(proof.selectedRuntime);
}, 30000);
