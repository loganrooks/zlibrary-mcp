import { beforeEach, afterEach, test, expect } from '@jest/globals';
import { mkdtemp, mkdir, writeFile, rm, symlink, realpath } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import * as runtime from './python-runtime.js';
import { admitReceipt } from './admission.js';
import { measured } from './receipt-controls.js';
import { digest } from './evaluator-identity.js';
import { arms } from './tasks.js';
let temp;
beforeEach(async () => {
  temp = await realpath(await mkdtemp(path.join(os.tmpdir(), 'eval-python-control-')));
});
afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});
async function fixture(name = 'A') {
  const buildRoot = path.join(temp, name),
    venv = path.join(buildRoot, '.venv'),
    executable = path.join(venv, 'bin/python');
  await mkdir(path.dirname(executable), { recursive: true });
  await mkdir(path.join(buildRoot, 'zlibrary/src/zlibrary'), { recursive: true });
  for (const name of ['pyproject.toml', 'uv.lock'])
    await writeFile(path.join(buildRoot, name), 'synthetic pinned ' + name);
  await writeFile(executable, 'synthetic interpreter bytes');
  const raw = {
    executable,
    prefix: venv,
    basePrefix: '/synthetic/base',
    version: '3.14.2',
    implementation: 'cpython',
    cacheTag: 'cpython-314',
    platform: 'darwin',
    arch: 'arm64',
    userSite: false,
    sysPath: [
      path.join(buildRoot, 'zlibrary/src'),
      buildRoot,
      path.join(venv, 'lib/python3.14/site-packages'),
    ],
    distributions: [
      {
        name: 'zlibrary',
        version: '1.0.0',
        location: path.join(venv, 'lib/python3.14/site-packages'),
        directUrl: {
          url: new URL('file://' + path.join(buildRoot, 'zlibrary')).href,
          dir_info: { editable: true },
        },
      },
    ],
    imports: { zlibrary: path.join(buildRoot, 'zlibrary/src/zlibrary/__init__.py') },
  };
  return { buildRoot, raw, executable };
}
const probe = (f) => async (binary, args, options) => {
  expect(options.timeout).toBeGreaterThan(0);
  if (args[0] === 'sync') {
    expect(args).toEqual(
      expect.arrayContaining([
        '--check',
        '--frozen',
        '--offline',
        '--no-default-groups',
        '--group',
        'dev',
      ]),
    );
    expect(args).not.toContain('--all-extras');
    expect(options.env.UV_PROJECT_ENVIRONMENT).toBe(path.join(f.buildRoot, '.venv'));
    return '';
  }
  if (binary === 'uv' && args[0] === '--version') return 'uv synthetic-control';
  expect(binary).toBe(f.executable);
  expect(options.env.PYTHONNOUSERSITE).toBe('1');
  expect(options.env.PYTHONHOME).toBeUndefined();
  return JSON.stringify(f.raw);
};
async function verify(f, extra = {}) {
  expect(runtime.verifyPythonRuntime).toBeInstanceOf(Function);
  return runtime.verifyPythonRuntime({
    buildRoot: f.buildRoot,
    probe: probe(f),
    uvIdentity: { sha256: 'a'.repeat(64), version: 'uv synthetic-control' },
    ...extra,
  });
}
test('4318353607 validated local editable descriptors normalize relocations, not production HEAD equality', async () => {
  const a = await verify(await fixture('A')),
    b = await verify(await fixture('B'));
  expect(a.status).toBe('verified');
  expect(a.sha256).toBe(b.sha256);
  expect(a.descriptor.executable).not.toBe(b.descriptor.executable);
  expect(a.manifests.files.map((f) => f.path)).toEqual(['pyproject.toml', 'uv.lock']);
});
for (const kind of [
  'foreign editable despite local import',
  'foreign prefix',
  'foreign import',
  'user site',
  'duplicate distribution',
  'dependency drift',
  'readiness failure',
  'missing environment',
  'symlink environment',
])
  test(`4318353607 ${kind} fails closed or changes compatibility`, async () => {
    const f = await fixture();
    const good = await verify(f);
    if (kind === 'foreign editable despite local import')
      f.raw.distributions[0].directUrl.url = 'file:///foreign/Park/zlibrary';
    if (kind === 'foreign prefix') f.raw.prefix = '/foreign/Park/.venv';
    if (kind === 'foreign import') f.raw.imports.zlibrary = '/foreign/Park/zlibrary/__init__.py';
    if (kind === 'user site') f.raw.userSite = true;
    if (kind === 'duplicate distribution') f.raw.distributions.push({ ...f.raw.distributions[0] });
    if (kind === 'dependency drift') {
      f.raw.distributions[0].version = '2.0.0';
      expect((await verify(f)).sha256).not.toBe(good.sha256);
      return;
    }
    if (kind === 'missing environment')
      await rm(path.join(f.buildRoot, '.venv'), { recursive: true });
    if (kind === 'symlink environment') {
      const v = path.join(f.buildRoot, '.venv');
      await rm(v, { recursive: true });
      await symlink(temp, v, 'dir');
    }
    const extra =
      kind === 'readiness failure'
        ? {
            probe: async () => {
              throw new Error('uv check would modify environment');
            },
          }
        : {};
    await expect(verify(f, extra)).rejects.toThrow();
  });
test('4318353607 manifests and interpreter byte drift change the bound proof', async () => {
  const f = await fixture(),
    first = await verify(f);
  await writeFile(path.join(f.buildRoot, 'uv.lock'), 'changed lock');
  expect((await verify(f)).sha256).not.toBe(first.sha256);
  await writeFile(f.executable, 'changed binary');
  expect((await verify(f)).sha256).not.toBe(first.sha256);
});
test('4318353607 missing/failed/drifting proof is not measurable', () => {
  for (const mutate of [
    (r) => delete r.python,
    (r) => (r.python.status = 'failed'),
    (r) => (r.pythonStable = false),
    (r) => (r.pythonEnd.sha256 = 'f'.repeat(64)),
  ]) {
    const r = measured(arms[0]);
    expect(admitReceipt(r).eligible).toBe(true);
    mutate(r);
    expect(admitReceipt(r).eligible).toBe(false);
  }
});

test('4318353607 inherited redirection/default/extras flags cannot alter the selected recipe', async () => {
  const prior = process.env.UV_ALL_EXTRAS;
  process.env.UV_ALL_EXTRAS = 'true';
  try {
    const f = await fixture();
    await verify(f, {
      probe: async (binary, args, options) => {
        expect(options.env.UV_ALL_EXTRAS).toBeUndefined();
        expect(options.env.VIRTUAL_ENV).toBeUndefined();
        return probe(f)(binary, args, options);
      },
    });
  } finally {
    if (prior === undefined) delete process.env.UV_ALL_EXTRAS;
    else process.env.UV_ALL_EXTRAS = prior;
  }
});

test('4318353607 recomputed digests cannot admit foreign or malformed normalized metadata', () => {
  for (const mutate of [
    (m) => (m.distributions[0].location = '/foreign/Park/.venv'),
    (m) => (m.interpreter.executable = '$PYTHONBASE/bin/python'),
    (m) => delete m.interpreter.version,
    (m) => (m.imports.httpx = '/foreign/Park/httpx.py'),
    (m) => m.distributions.push({ ...m.distributions[0] }),
  ]) {
    const r = measured(arms[0]);
    mutate(r.python.metadata);
    r.python.sha256 = digest(r.python.metadata);
    r.pythonEnd = structuredClone(r.python);
    expect(admitReceipt(r).eligible).toBe(false);
  }
});
