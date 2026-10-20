import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, readFile, writeFile, chmod, rm, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
for (const [image, expected] of [
  ['healthy', null],
  ['wrong-version', /package version/],
  ['wrong-tools', /five public tools/],
  ['wrong-schema', /public tool schemas/],
  ['missing-canary', /canary must record exactly one blocked attempt/],
  ['wrong-envelope', /search rows/],
  ['no-contact', /fake provider search/],
  ['egress', /egress attempt/],
  ['stdout-noise', /only valid MCP messages/],
]) {
  test(`image smoke CLI ${image}: real SDK/bridge journey and cleanup`, { timeout: 40000 }, async () => {
    const state = await mkdtemp(path.join(tmpdir(), 'image-smoke-contract-'));
    try {
      const command = path.join(state, 'docker');
      const shim = await readFile(path.join(root, '__tests__/image-smoke/fake-docker.cjs'), 'utf8');
      await writeFile(command, shim
        .replace('process.env.IMAGE_SMOKE_TEST_ROOT', JSON.stringify(root))
        .replace('process.env.IMAGE_SMOKE_TEST_STATE', JSON.stringify(state)));
      await chmod(command, 0o755);
      let result;
      try {
        result = await run(process.execPath, ['scripts/image-smoke.mjs', image], {
          cwd: root,
          timeout: 30000,
          env: {
            PATH: state + path.delimiter + process.env.PATH,
          },
        });
      } catch (error) {
        result = error;
      }
      if (expected) {
        assert.equal(result.code, 1, result.stderr);
        assert.match(result.stderr, expected);
      } else {
        assert.equal(result.code ?? 0, 0, result.stderr);
        assert.match(result.stdout, /Image smoke passed/);
      }
      assert.deepEqual((await readdir(state)).filter((f) => f.endsWith('.json')), [],
        'all owned container processes must be cleaned up');
    } finally {
      await rm(state, { recursive: true, force: true });
    }
  });
}
