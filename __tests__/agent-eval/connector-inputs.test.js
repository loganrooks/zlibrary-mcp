import { jest, beforeEach, afterEach, test, expect } from '@jest/globals';
import * as actualChildProcess from 'node:child_process';
import { cp, mkdtemp, mkdir, rm, symlink, writeFile } from 'node:fs/promises';
import { appendFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { baselinePin } from './tasks.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
let scratch, race, hideStatus, historicalSha;
// Read-only Git uses the real repository/index and a disposable work-tree mirror.
// No .git file, index, object, ref, or selected source/dist is written by this test.
jest.unstable_mockModule('node:child_process', () => ({
  ...actualChildProcess,
  execFileSync(binary, args, options) {
    if (binary === 'git' && args[0] === '-C' && args[1] === scratch) {
      if ((hideStatus || historicalSha) && args.includes('status')) return Buffer.from('');
      if (historicalSha && args.includes('rev-parse') && args.at(-1) === 'HEAD')
        return Buffer.from(historicalSha + '\n');
      args = ['-C', root, '--work-tree=' + scratch, ...args.slice(2)];
    }
    const result = actualChildProcess.execFileSync(binary, args, options);
    if (race && binary === process.execPath && args[0].endsWith('/bin/tsc')) {
      appendFileSync(path.join(scratch, 'src/index.ts'), '\n// changed during verification\n');
      race = false;
    }
    return result;
  },
}));
const { pinnedInputs, resolveBaselinePin, verifyBuildArtifacts } = await import('./build-proof.js');
beforeEach(async () => {
  scratch = await mkdtemp(path.join(os.tmpdir(), 'eval-input-mirror-'));
  race = false;
  hideStatus = false;
  historicalSha = undefined;
  for (const name of [
    'src',
    'lib',
    'zlibrary',
    'tsconfig.json',
    'package.json',
    'package-lock.json',
    'pyproject.toml',
    'uv.lock',
    'dist',
    '.gitignore',
  ])
    await cp(path.join(root, name), path.join(scratch, name), { recursive: true });
  await symlink(path.join(root, 'node_modules'), path.join(scratch, 'node_modules'), 'dir');
  // Prove each mirror begins clean, so a negative cannot pass on setup dirt.
  await pinnedInputs(scratch);
});
afterEach(async () => {
  await rm(scratch, { recursive: true, force: true });
});
for (const name of [
  'src/index.ts',
  'tsconfig.json',
  'package.json',
  'package-lock.json',
  'pyproject.toml',
  'uv.lock',
])
  test(`EVAL-C1-01 rejects dirty ${name} before compilation`, async () => {
    await writeFile(path.join(scratch, name), 'dirty source/config');
    await expect(verifyBuildArtifacts({ buildRoot: scratch })).rejects.toThrow(/dirty/);
  });
test('EVAL-C1-01 untracked TypeScript input fails closed', async () => {
  await writeFile(path.join(scratch, 'src/untracked.ts'), 'export const unknown = true;');
  await expect(pinnedInputs(scratch)).rejects.toThrow(/dirty/);
});
test('EVAL-C1-01 pinned blob comparison catches dirty bytes even when status omits them', async () => {
  await writeFile(path.join(scratch, 'src/index.ts'), 'hidden source dirt');
  hideStatus = true;
  await expect(pinnedInputs(scratch)).rejects.toThrow(/dirty pinned source\/config bytes/);
});
test('EVAL-C1-01 actual compiler failure rejects without touching selected dist', async () => {
  await rm(path.join(scratch, 'node_modules'));
  const compiler = path.join(scratch, 'node_modules/typescript');
  await mkdir(path.join(compiler, 'bin'), { recursive: true });
  await mkdir(path.join(compiler, 'lib'));
  await writeFile(path.join(compiler, 'package.json'), '{"version":"synthetic-failing-compiler"}');
  await writeFile(path.join(compiler, 'bin/tsc'), 'throw new Error("SYNTHETIC_COMPILER_FAILURE");');
  await expect(verifyBuildArtifacts({ buildRoot: scratch })).rejects.toThrow(
    /pinned TypeScript compilation failed/,
  );
});
test('EVAL-C1-01 source changes during actual clean compilation fail closed', async () => {
  race = true;
  await expect(verifyBuildArtifacts({ buildRoot: scratch })).rejects.toThrow(
    /dirty|identity changed/,
  );
}, 30000);
test('EVAL-C1-02 default baseline refuses incompatible source before any launch', async () => {
  await writeFile(
    path.join(scratch, 'src/index.ts'),
    'interface-shaped different production input',
  );
  await expect(resolveBaselinePin(scratch)).rejects.toThrow(/dirty|not source-equivalent/);
});
test('EVAL-C1-02 clean but historically different production cannot silently become default A', async () => {
  historicalSha = actualChildProcess
    .execFileSync('git', ['-C', root, 'rev-parse', `${baselinePin}^`], { encoding: 'utf8' })
    .trim();
  for (const name of ['src', 'lib', 'zlibrary'])
    await rm(path.join(scratch, name), { recursive: true, force: true });
  const archive = actualChildProcess.execFileSync(
    'git',
    [
      '-C',
      root,
      'archive',
      historicalSha,
      'src',
      'lib',
      'zlibrary',
      'tsconfig.json',
      'package.json',
      'package-lock.json',
      'pyproject.toml',
      'uv.lock',
    ],
    { maxBuffer: 16 * 1024 * 1024 },
  );
  actualChildProcess.execFileSync('tar', ['-xf', '-', '-C', scratch], { input: archive });
  // The metadata adapter selects the archived commit; actual bytes still have
  // to match all of that commit's Git blobs before the baseline comparison.
  expect((await pinnedInputs(scratch)).sha).toBe(historicalSha);
  await expect(resolveBaselinePin(scratch)).rejects.toThrow(/not source-equivalent/);
});
