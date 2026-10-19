import { beforeAll, afterAll, test, expect } from '@jest/globals';
import { cp, mkdtemp, mkdir, rm, symlink, writeFile, readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import * as server from './server.js';
import { admitReceipt } from './admission.js';
import { measured } from './receipt-controls.js';
import { arms, baselinePin } from './tasks.js';
import { manifestDigest } from './build-proof.js';

let scratch, clean;
beforeAll(async () => {
  scratch = await mkdtemp(path.join(os.tmpdir(), 'eval-compiled-control-'));
  for (const name of ['src', 'tsconfig.json', 'package.json', 'package-lock.json'])
    await cp(path.join(server.root, name), path.join(scratch, name), { recursive: true });
  await symlink(path.join(server.root, 'node_modules'), path.join(scratch, 'node_modules'), 'dir');
  clean = path.join(scratch, 'clean-dist');
  execFileSync(
    process.execPath,
    [
      path.join(server.root, 'node_modules/typescript/bin/tsc'),
      '--project',
      path.join(scratch, 'tsconfig.json'),
      '--outDir',
      clean,
      '--incremental',
      'false',
      '--noEmitOnError',
      'true',
    ],
    { encoding: 'utf8' },
  );
});
afterAll(async () => {
  await rm(scratch, { recursive: true, force: true });
});
const verify = async (distRoot) => {
  expect(server.verifyBuildArtifacts).toBeInstanceOf(Function);
  return server.verifyBuildArtifacts({ buildRoot: server.root, distRoot });
};
test('EVAL-C1-01 independent clean compiled control proves exact executable artifacts', async () => {
  const proof = await verify(clean);
  expect(proof).toMatchObject({
    status: 'verified',
    identityStable: true,
    sha: server.gitRead(server.root, 'rev-parse', 'HEAD'),
  });
  expect(proof.compiledRuntime).toEqual(proof.selectedRuntime);
  expect(proof.selectedRuntime.files.some((f) => f.path === 'index.js')).toBe(true);
  expect(proof.inputs.files.map((f) => f.path)).toEqual(
    expect.arrayContaining(['src/index.ts', 'tsconfig.json', 'package.json', 'package-lock.json']),
  );
});
for (const mutation of ['wrong', 'stale', 'extra', 'missing', 'symlink'])
  test(`EVAL-C1-01 rejects actual ${mutation} runtime artifacts in disposable scratch`, async () => {
    const selected = path.join(scratch, mutation);
    await cp(clean, selected, { recursive: true });
    if (mutation === 'wrong')
      await writeFile(path.join(selected, 'index.js'), 'throw new Error("wrong build");\n');
    if (mutation === 'stale')
      await writeFile(
        path.join(selected, 'lib/errors.js'),
        (await readFile(path.join(selected, 'lib/errors.js'), 'utf8')) + '\n// stale revision\n',
      );
    if (mutation === 'extra')
      await writeFile(path.join(selected, 'untracked-runtime.js'), 'export const stale = true;\n');
    if (mutation === 'missing') await rm(path.join(selected, 'lib/errors.js'));
    if (mutation === 'symlink') {
      await rm(path.join(selected, 'index.js'));
      await symlink(path.join(clean, 'index.js'), path.join(selected, 'index.js'));
    }
    await expect(verify(selected)).rejects.toThrow(/runtime|artifact|symlink/);
  });
test('EVAL-C1-01 old unproven and malformed proof receipts remain diagnostic', () => {
  const legacy = measured(arms[0]);
  legacy.schemaVersion = 2;
  delete legacy.build.artifactProof;
  expect(admitReceipt(legacy).eligible).toBe(false);
  const missing = measured(arms[0]);
  delete missing.build.artifactProof;
  expect(admitReceipt(missing).eligible).toBe(false);
});
for (const [name, mutate] of [
  [
    'compiler missing',
    (r) => {
      delete r.build.artifactProof.compiler;
    },
  ],
  [
    'wrong proof revision',
    (r) => {
      r.build.artifactProof.version = 0;
    },
  ],
  [
    'wrong source SHA',
    (r) => {
      r.build.artifactProof.sha = 'c'.repeat(40);
    },
  ],
  [
    'unstable verification',
    (r) => {
      r.build.artifactProof.identityStable = false;
    },
  ],
  [
    'wrong runtime digest',
    (r) => {
      r.build.artifactProof.selectedRuntime.sha256 = 'f'.repeat(64);
    },
  ],
  [
    'extra runtime entry',
    (r) => {
      const m = r.build.artifactProof.selectedRuntime;
      m.files.push({ path: 'other.js', sha256: 'f'.repeat(64) });
      m.sha256 = manifestDigest(m.files);
    },
  ],
  [
    'wrong full dist',
    (r) => {
      r.build.artifactProof.fullDist = { sha256: 'f'.repeat(64), files: 1 };
    },
  ],
  [
    'missing source binding',
    (r) => {
      delete r.build.source.trees.productionInputs;
    },
  ],
  [
    'lock input missing',
    (r) => {
      const m = r.build.artifactProof.inputs;
      m.files = m.files.filter((f) => f.path !== 'package-lock.json');
      m.sha256 = manifestDigest(m.files);
    },
  ],
  [
    'runtime traversal',
    (r) => {
      const p = r.build.artifactProof;
      for (const m of [p.compiledRuntime, p.selectedRuntime]) {
        m.files[0].path = '../index.js';
        m.sha256 = manifestDigest(m.files);
      }
    },
  ],
  [
    'incomplete stream',
    (r) => {
      r.results[0].capture.complete = false;
    },
  ],
  [
    'missing stream proof',
    (r) => {
      delete r.results[0].capture;
    },
  ],
])
  test(`EVAL-C1-01/04 admission rejects ${name}`, () => {
    const r = measured(arms[0]);
    expect(admitReceipt(r)).toMatchObject({ eligible: true });
    mutate(r);
    expect(admitReceipt(r).eligible).toBe(false);
  });
test('EVAL-C1-02 default matrix resolves compatible A or rejects nonbaseline production', () => {
  const head = server.gitRead(server.root, 'rev-parse', 'HEAD');
  const compatible = !server.gitRead(
    server.root,
    'diff',
    '--name-only',
    baselinePin,
    head,
    '--',
    'src',
    'lib',
    'zlibrary',
    'tsconfig.json',
    'package.json',
    'package-lock.json',
  );
  const run = () =>
    execFileSync(process.execPath, [path.join(server.here, 'matrix.mjs')], {
      encoding: 'utf8',
      stdio: 'pipe',
    });
  if (!compatible) {
    expect(run).toThrow(/not source-equivalent/);
    return;
  }
  const plan = JSON.parse(run());
  expect(plan.commands).toHaveLength(15);
  expect(new Set(plan.commands.map((c) => c.args[c.args.indexOf('--a-pin') + 1]))).toEqual(
    new Set([head]),
  );
});
test('EVAL-C1-01 startup pin failure persists a failed schema-3 receipt without launching', async () => {
  const out = path.join(scratch, 'startup-failed.json');
  expect(() =>
    execFileSync(
      process.execPath,
      [
        path.join(server.here, 'run.mjs'),
        '--self-test',
        '--a-pin',
        'e2517b3e347584333f9c127a0217a3c574f6a22e',
        '--out',
        out,
      ],
      { encoding: 'utf8', stdio: 'pipe' },
    ),
  ).toThrow(/pinned commit/);
  const r = JSON.parse(await readFile(out, 'utf8'));
  expect(r).toMatchObject({
    schemaVersion: 3,
    status: 'failed',
    sourceStable: false,
    fencePassed: false,
    results: [],
  });
  expect(admitReceipt(r).eligible).toBe(false);
});
