import { beforeEach, afterEach, test, expect } from '@jest/globals';
import os from 'node:os';
import path from 'node:path';
import {
  mkdtemp,
  realpath,
  rm,
  readFile,
  writeFile,
  rename,
  symlink,
  mkdir,
  lstat,
} from 'node:fs/promises';
import * as runtime from './node-runtime.js';
import { execFileSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { nodeFixture } from './node-runtime-controls.js';

// onRead also observes the selected Node/npm tools. Only package payloads have
// package-relative exclusion roles; absolute tool/checkout ancestors are not payloads.
function readSpyRoles({ root, node, cli, packageRoots }) {
  const npmRoot = path.dirname(path.dirname(cli));
  return {
    manifests: ['package.json', 'package-lock.json'].map((name) => path.join(root, name)),
    node,
    tools: [
      path.join(npmRoot, 'package.json'),
      cli,
      fileURLToPath(new URL('./node-inventory-guard.cjs', import.meta.url)),
      path.join(npmRoot, 'node_modules/@npmcli/arborist/package.json'),
      path.join(npmRoot, 'node_modules/@npmcli/arborist/lib/index.js'),
    ],
    packages: [...packageRoots].sort((a, b) => b.length - a.length),
  };
}
function assertReadSpyRole({ name, kind }, roles) {
  const reject = () => {
    throw new Error(`unexpected ${kind} content read: ${name}`);
  };
  if (typeof name !== 'string' || !path.isAbsolute(name) || path.resolve(name) !== name)
    return reject();
  switch (kind) {
    case 'manifest':
      if (!roles.manifests.includes(name)) reject();
      break;
    case 'node-binary':
      if (name !== roles.node) reject();
      break;
    case 'inventory-tool':
      if (!roles.tools.includes(name)) reject();
      break;
    case 'package-metadata':
      if (!roles.packages.some((root) => name === path.join(root, 'package.json'))) reject();
      break;
    case 'runtime-payload': {
      // Most-specific owner: selected nested dependencies are separate packages;
      // an unselected nested node_modules path must not inherit its parent's role.
      const owner = roles.packages.find((root) => name.startsWith(root + path.sep));
      if (!owner) return reject();
      const relative = path.relative(owner, name);
      if (
        relative === 'package.json' ||
        relative
          .split(path.sep)
          .some((part) =>
            /^(?:node_modules|__tests__|tests?|fixtures?|examples?|docs?|coverage|\.?cache|__snapshots__|\.github|\.git|fixture-dev)$/.test(
              part,
            ),
          ) ||
        /(?:^|\/)(?:\.?npmrc|\.env(?:\.[^/]*)?|\.netrc|credentials?(?:\.[^/]*)?|id_(?:rsa|dsa|ed25519)(?:\.[^/]*)?|[^/]+\.(?:pem|key|p12|pfx))$/i.test(
          relative,
        ) ||
        /(?:\.map|\.[cm]?ts|\.flow|\.md|\.markdown|\.rst)$/i.test(relative)
      )
        reject();
      break;
    }
    default:
      reject();
  }
}
let temp;
beforeEach(async () => {
  temp = await realpath(await mkdtemp(path.join(os.tmpdir(), 'eval-node-proof-')));
});
afterEach(async () => {
  await rm(temp, { recursive: true, force: true });
});
test('4318878598 real isolated npm inventory binds runtime bytes, nested duplicate/peer/optional graph and native SDK anchors', async () => {
  const f = await nodeFixture(temp);
  expect(runtime.verifyNodeRuntime).toBeInstanceOf(Function);
  const proof = await runtime.verifyNodeRuntime({ root: f.root });
  expect(proof.status).toBe('verified');
  expect(proof.identity.packages).toHaveLength(6);
  expect(
    proof.identity.packages.some(
      (p) => p.locator.includes('/sdk/node_modules/fixture-dep') && p.version === '1.0.0',
    ),
  ).toBe(true);
  expect(proof.identity.edges.some((e) => e.name === 'fixture-peer' && e.kind === 'peer')).toBe(
    true,
  );
  expect(
    proof.identity.edges.some((e) => e.name === 'fixture-absent' && e.to === null && e.optional),
  ).toBe(true);
  expect(proof.identity.anchors.length).toBeGreaterThan(5);
  expect(proof.audit.configContentReads).toBe(0);
  expect(proof.audit.networkAttempts).toBe(0);
  expect(proof.audit.childAttempts).toBe(0);
}, 30000);

for (const name of [
  'dist/esm/client.js',
  'dist/cjs/client.cjs',
  'runtime.json',
  'runtime.wasm',
  'runtime.node',
  'runtime.css',
  'bin/sdk-run',
  'node_modules/fixture-dep/index.js',
  'LEAF',
])
  test(`4318878598 same-version/lock ${name} runtime bytes change identity`, async () => {
    const f = await nodeFixture(temp),
      first = await runtime.verifyNodeRuntime({ root: temp });
    const file =
      name === 'LEAF'
        ? path.join(temp, 'node_modules/fixture-leaf/index.js')
        : path.join(temp, 'node_modules', f.sdk, name);
    await writeFile(file, 'changed same-version runtime bytes');
    const after = await runtime.verifyNodeRuntime({ root: temp });
    expect(after.identity.manifests).toEqual(first.identity.manifests);
    expect(after.sha256).not.toBe(first.sha256);
  }, 30000);
test('4318878598 actual synthetic ESM import changes while manifest/lock/version stay fixed; proof cannot match', async () => {
  const f = await nodeFixture(temp),
    first = await runtime.verifyNodeRuntime({ root: temp }),
    file = path.join(temp, 'node_modules', f.sdk, 'dist/esm/client.js');
  const run = () =>
    execFileSync(
      process.execPath,
      [
        '--input-type=module',
        '-e',
        `import {marker} from ${JSON.stringify(pathToFileURL(file).href)};process.stdout.write(marker);`,
      ],
      { encoding: 'utf8', env: { PATH: process.env.PATH }, timeout: 5000 },
    );
  expect(run()).toBe('esm-original');
  await writeFile(file, 'export const marker="esm-changed";');
  expect(run()).toBe('esm-changed');
  const after = await runtime.verifyNodeRuntime({ root: temp });
  expect(after.identity.manifests).toEqual(first.identity.manifests);
  expect(after.sha256).not.toBe(first.sha256);
}, 30000);
test('4318878598 relocated identical ordinary install and shared top-level install symlink normalize equally', async () => {
  const a = await nodeFixture(path.join(temp, 'A')),
    b = await nodeFixture(path.join(temp, 'B'));
  const first = await runtime.verifyNodeRuntime({ root: a.root });
  await a.refreshInventory();
  await mkdir(path.join(temp, 'shared'));
  await rename(path.join(a.root, 'node_modules'), path.join(temp, 'shared/node_modules'));
  await symlink(path.join(temp, 'shared/node_modules'), path.join(a.root, 'node_modules'), 'dir');
  const shared = await runtime.verifyNodeRuntime({ root: a.root }),
    relocated = await runtime.verifyNodeRuntime({ root: b.root });
  const nativeGraph = (root) =>
    execFileSync(
      process.execPath,
      [
        '--input-type=module',
        '-e',
        `import {graph} from ${JSON.stringify(pathToFileURL(path.join(root, 'node_modules', a.sdk, 'dist/esm/client.js')).href)};process.stdout.write(JSON.stringify(graph));`,
      ],
      { env: { PATH: process.env.PATH }, encoding: 'utf8', timeout: 5000 },
    );
  expect(nativeGraph(a.root)).toBe(
    JSON.stringify(['nested:synthetic runtime', 'synthetic runtime']),
  );
  expect(nativeGraph(b.root)).toBe(nativeGraph(a.root));
  expect(shared.sha256).toBe(first.sha256);
  expect(relocated.sha256).toBe(first.sha256);
  expect(shared.local.install).not.toBe(relocated.local.install);
}, 30000);
for (const ancestor of ['ordinary', 'hostedtoolcache'])
  test(`4318878598 content read spies exclude forbidden files, dev runtime/cache, docs and source maps before reads (${ancestor})`, async () => {
    const selectedRoot = path.join(temp, ancestor);
    const f = await nodeFixture(selectedRoot),
      reads = [],
      traces = [];
    await f.put(`node_modules/${f.sdk}/ignored.js.map`, 'unread map');
    await f.put(`node_modules/${f.sdk}/.cache/private.json`, 'unread cache');
    const proof = await runtime.verifyNodeRuntime({
      root: selectedRoot,
      onRead: (name, kind) => reads.push({ name, kind }),
      onAudit: ({ trace }) => traces.push(...trace),
    });
    const packageRoots = Object.keys(f.definitions)
      .filter((locator) => locator !== 'node_modules/fixture-dev')
      .map((locator) => path.join(selectedRoot, locator));
    expect(proof.local.packageRoots.map((p) => p.realpath).sort()).toEqual(
      [...packageRoots].sort(),
    );
    const roles = readSpyRoles({
      root: selectedRoot,
      node: await realpath(process.execPath),
      cli: proof.local.cli,
      packageRoots,
    });
    expect([...new Set(reads.map((r) => r.kind))].sort()).toEqual(
      ['manifest', 'node-binary', 'inventory-tool', 'package-metadata', 'runtime-payload'].sort(),
    );
    for (const read of reads) assertReadSpyRole(read, roles);
    for (const [kind, names] of [
      ['manifest', roles.manifests],
      ['node-binary', [roles.node]],
      ['inventory-tool', roles.tools],
      ['package-metadata', packageRoots.map((root) => path.join(root, 'package.json'))],
      [
        'runtime-payload',
        [
          path.join(selectedRoot, 'node_modules', f.sdk, 'dist/esm/client.js'),
          path.join(selectedRoot, 'node_modules', f.sdk, 'node_modules/fixture-dep/index.js'),
        ],
      ],
    ])
      for (const name of names) expect(reads).toContainEqual({ name, kind });
    const forbidden = [
      '.env',
      '.npmrc',
      'credentials.json',
      'fixtures/auth.json',
      'test/private.key',
      'docs/secret.txt',
      '.cache/private.json',
      'ignored.js.map',
    ].map((name) => path.join(selectedRoot, 'node_modules', f.sdk, name));
    forbidden.push(
      path.join(selectedRoot, '.npmrc'),
      path.join(selectedRoot, 'node_modules/fixture-dev/index.js'),
      path.join(selectedRoot, 'node_modules/fixture-dev/cache.json'),
    );
    for (const name of forbidden) {
      expect((await lstat(name)).isFile()).toBe(true);
      expect(reads.some((read) => read.name === name)).toBe(false);
    }
    expect(traces.some((r) => r.allowed && r.path === path.join(selectedRoot, '.npmrc'))).toBe(
      false,
    );
    expect(
      traces.some(
        (r) => r.allowed && r.path.includes('/fixture-dev/') && !r.path.endsWith('/package.json'),
      ),
    ).toBe(false);
  }, 30000);
test('read-spy role oracle rejects forbidden relative payloads, outside paths and unknown kinds', () => {
  const root = path.join(temp, 'hostedtoolcache'),
    sdk = path.join(root, 'node_modules/@modelcontextprotocol/sdk'),
    nested = path.join(sdk, 'node_modules/fixture-dep'),
    cli = path.join(temp, 'hostedtoolcache/tool/npm/bin/npm-cli.js'),
    roles = readSpyRoles({
      root,
      node: path.join(temp, 'hostedtoolcache/bin/node'),
      cli,
      packageRoots: [sdk, nested],
    });
  for (const [kind, name] of [
    ['manifest', roles.manifests[0]],
    ['node-binary', roles.node],
    ['inventory-tool', cli],
    ['package-metadata', path.join(sdk, 'package.json')],
    ['runtime-payload', path.join(sdk, 'dist/client.js')],
    ['runtime-payload', path.join(nested, 'index.js')],
  ])
    expect(() => assertReadSpyRole({ name, kind }, roles)).not.toThrow();
  const rejected = [
    ...[
      '.env',
      '.env.local',
      '.npmrc',
      'credentials.json',
      'fixtures/auth.json',
      'test/private.key',
      'docs/secret.txt',
      '.cache/private.json',
      'ignored.js.map',
      'node_modules/unselected/index.js',
    ].map((name) => ['runtime-payload', path.join(sdk, name)]),
    ['runtime-payload', path.join(nested, 'docs/secret.txt')],
    ['runtime-payload', path.join(root, 'node_modules/fixture-dev/index.js')],
    ['runtime-payload', path.join(temp, 'outside/index.js')],
    ['runtime-payload', path.join(sdk + '-outside', 'index.js')],
    ['runtime-payload', roles.node],
    ['manifest', path.join(root, '.npmrc')],
    ['package-metadata', path.join(root, 'node_modules/fixture-dev/package.json')],
    ['inventory-tool', path.join(path.dirname(cli), '.npmrc')],
    ['node-binary', path.join(path.dirname(roles.node), 'other-node')],
    ['unknown-kind', path.join(sdk, 'dist/client.js')],
  ];
  for (const [kind, name] of rejected)
    expect(() => assertReadSpyRole({ name, kind }, roles)).toThrow(/unexpected .* content read/);
});
for (const kind of [
  'unclassified asset',
  'runtime link',
  'package link',
  'missing runtime',
  'missing package',
  'workspace',
  'file dependency',
  'lock link',
  'lock mismatch',
  'external fallback',
])
  test(`4318878598 ${kind} fails closed without fallback`, async () => {
    const f = await nodeFixture(temp),
      sdk = path.join(temp, 'node_modules', f.sdk);
    if (kind === 'unclassified asset')
      await f.put(`node_modules/${f.sdk}/required.opaque`, 'must not be silently excluded');
    if (kind === 'runtime link') {
      await rm(path.join(sdk, 'runtime.json'));
      await symlink(path.join(temp, 'package.json'), path.join(sdk, 'runtime.json'));
    }
    if (kind === 'package link') {
      await rename(path.join(temp, 'node_modules/fixture-leaf'), path.join(temp, 'foreign-leaf'));
      await symlink(
        path.join(temp, 'foreign-leaf'),
        path.join(temp, 'node_modules/fixture-leaf'),
        'dir',
      );
    }
    if (kind === 'missing runtime') await rm(path.join(sdk, 'dist/esm/client.js'));
    if (kind === 'missing package')
      await rm(path.join(temp, 'node_modules/fixture-peer'), { recursive: true });
    if (kind === 'workspace') {
      f.manifest.workspaces = ['packages/*'];
      await writeFile(path.join(temp, 'package.json'), JSON.stringify(f.manifest));
    }
    if (kind === 'file dependency') {
      f.manifest.dependencies.other = 'file:../outside';
      await writeFile(path.join(temp, 'package.json'), JSON.stringify(f.manifest));
    }
    if (kind === 'lock link') {
      f.lock.packages['node_modules/fixture-leaf'].link = true;
      await writeFile(path.join(temp, 'package-lock.json'), JSON.stringify(f.lock));
    }
    if (kind === 'lock mismatch') {
      f.lock.packages['node_modules/fixture-peer'].version = '99.0.0';
      await writeFile(path.join(temp, 'package-lock.json'), JSON.stringify(f.lock));
    }
    if (kind === 'external fallback') {
      await rename(sdk, path.join(temp, 'external-sdk'));
      await symlink(path.join(temp, 'external-sdk'), sdk, 'dir');
    }
    await expect(runtime.verifyNodeRuntime({ root: temp })).rejects.toThrow(
      /Node|npm|runtime|workspace|link|lock|inventory/,
    );
  }, 30000);
test('4318878598 before/end runtime mutation and install-target swap cannot claim stability', async () => {
  const f = await nodeFixture(path.join(temp, 'A'));
  await expect(
    runtime.verifyNodeRuntime({
      root: f.root,
      beforeRecheck: () =>
        writeFile(path.join(f.root, 'node_modules', f.sdk, 'runtime.json'), 'changed during proof'),
    }),
  ).rejects.toThrow(/drift/);
  await nodeFixture(path.join(temp, 'B'));
  await expect(
    runtime.verifyNodeRuntime({
      root: f.root,
      beforeRecheck: async () => {
        await rename(path.join(f.root, 'node_modules'), path.join(temp, 'old-install'));
        await symlink(path.join(temp, 'B/node_modules'), path.join(f.root, 'node_modules'), 'dir');
      },
    }),
  ).rejects.toThrow(/drift/);
}, 30000);
for (const execution of [
  { env: { NODE_OPTIONS: '--require /untrusted.js' }, execArgv: [] },
  { env: { NODE_PATH: '/foreign' }, execArgv: [] },
  { env: {}, execArgv: ['--conditions=alternate'] },
  { env: {}, execArgv: ['--preserve-symlinks'] },
  { env: {}, execArgv: ['--import', '/foreign.mjs'] },
  { env: {}, execArgv: ['--loader', '/foreign.mjs'] },
])
  test('4318878598 unsupported Node execution policy refuses before inventory', async () => {
    const f = await nodeFixture(temp);
    let read = false;
    await expect(
      runtime.verifyNodeRuntime({
        root: f.root,
        execution,
        onRead: () => {
          read = true;
        },
      }),
    ).rejects.toThrow(/unsupported Node/);
    expect(read).toBe(false);
  });
test('4318878598 selected executable byte identity is load bearing (bounded read adapter, no binary edit)', async () => {
  await nodeFixture(temp);
  const first = await runtime.verifyNodeRuntime({ root: temp }),
    changed = await runtime.verifyNodeRuntime({
      root: temp,
      readBytes: async (name, kind) => {
        const bytes = await readFile(name);
        return kind === 'node-binary'
          ? Buffer.concat([bytes, Buffer.from('synthetic changed binary identity')])
          : bytes;
      },
    });
  expect(first.sha256).not.toBe(changed.sha256);
}, 30000);
test('4318878598 ancestor SDK fallback is denied before outside metadata bytes; failure cleanup leaves target unchanged', async () => {
  const f = await nodeFixture(path.join(temp, 'selected')),
    audits = [];
  await rename(path.join(f.root, 'node_modules'), path.join(temp, 'node_modules'));
  await mkdir(path.join(f.root, 'node_modules'));
  const marker = path.join(temp, 'node_modules/fixture-leaf/index.js'),
    before = await readFile(marker);
  await expect(
    runtime.verifyNodeRuntime({ root: f.root, onAudit: (result) => audits.push(result) }),
  ).rejects.toThrow(/inventory|outside|missing/);
  expect(audits.length).toBeGreaterThan(0);
  for (const audit of audits) {
    expect(
      audit.trace.some((r) => r.allowed && r.path.startsWith(path.join(temp, 'node_modules'))),
    ).toBe(false);
    await expect(readFile(path.join(audit.scratch, 'package.json'))).rejects.toMatchObject({
      code: 'ENOENT',
    });
  }
  expect(await readFile(marker)).toEqual(before);
}, 30000);

test('4318878598 shared top-level install without accepted hidden lock fails closed (lead disposition)', async () => {
  const f = await nodeFixture(path.join(temp, 'A'));
  await mkdir(path.join(temp, 'shared'));
  await rename(path.join(f.root, 'node_modules'), path.join(temp, 'shared/node_modules'));
  await symlink(path.join(temp, 'shared/node_modules'), path.join(f.root, 'node_modules'), 'dir');
  await expect(runtime.verifyNodeRuntime({ root: f.root })).rejects.toThrow(
    /EVAL_SHARED_HIDDEN_LOCK/,
  );
}, 30000);

test('4318878598 arbitrary physical shared-install basename is refused even with hidden metadata', async () => {
  const f = await nodeFixture(path.join(temp, 'A'));
  await f.refreshInventory();
  await rename(path.join(f.root, 'node_modules'), path.join(temp, 'shared-install'));
  await symlink(path.join(temp, 'shared-install'), path.join(f.root, 'node_modules'), 'dir');
  await expect(runtime.verifyNodeRuntime({ root: f.root })).rejects.toThrow(/physical mapping/);
}, 30000);

test('entry-guard actual SDK transitive main in excluded docs refuses before payload reads', async () => {
  const f = await nodeFixture(temp),
    leaf = path.join(temp, 'node_modules/fixture-leaf');
  const pkg = JSON.parse(await readFile(path.join(leaf, 'package.json'), 'utf8'));
  pkg.main = 'docs/runtime.cjs';
  await writeFile(path.join(leaf, 'package.json'), JSON.stringify(pkg));
  await f.put('node_modules/fixture-leaf/docs/runtime.cjs', 'module.exports="runtime-one";');
  const actual = () =>
    execFileSync(
      process.execPath,
      [
        '--input-type=module',
        '-e',
        `import {graph} from ${JSON.stringify(pathToFileURL(path.join(temp, 'node_modules', f.sdk, 'dist/esm/client.js')).href)};process.stdout.write(graph[0]);`,
      ],
      { encoding: 'utf8', env: { PATH: process.env.PATH }, timeout: 5000 },
    );
  expect(actual()).toBe('nested:runtime-one');
  await f.put('node_modules/fixture-leaf/docs/runtime.cjs', 'module.exports="runtime-two";');
  expect(actual()).toBe('nested:runtime-two');
  const reads = [];
  await expect(
    runtime.verifyNodeRuntime({ root: temp, onRead: (name, kind) => reads.push({ name, kind }) }),
  ).rejects.toThrow(/declared runtime entry/);
  expect(reads.some((r) => r.kind === 'runtime-payload')).toBe(false);
  expect(reads.some((r) => r.name.endsWith('/docs/runtime.cjs'))).toBe(false);
}, 30000);

for (const [label, declaration] of [
  [
    'nested runtime export',
    { exports: { '.': { import: { default: './docs/runtime.cjs' }, require: './index.js' } } },
  ],
  ['runtime export array', { exports: { '.': ['./index.js', './fixtures/runtime.js'] } }],
  ['unsafe outside export', { exports: { '.': './../outside.js' } }],
  ['encoded outside export', { exports: { '.': './%2e%2e/outside.js' } }],
  [
    'local import excluded',
    { imports: { '#runtime': { node: './docs/runtime.cjs', default: './index.js' } } },
  ],
  ['local import outside', { imports: { '#runtime': '../outside.js' } }],
  ['forbidden main', { main: 'credentials.json' }],
  ['directory main', { main: './lib-entry' }],
  ['excluded wildcard export', { exports: { './*': './docs/*.cjs' } }],
  ['ambiguous directory wildcard', { exports: { './*': './*/entry.cjs' } }],
  ['declaration used as runtime export', { exports: { '.': { default: './index.d.ts' } } }],
  ['unclassified declared main', { main: 'entry.opaque' }],
])
  test(`entry-guard rejects ${label} without excluded content reads`, async () => {
    const f = await nodeFixture(temp),
      leaf = path.join(temp, 'node_modules/fixture-leaf'),
      pkg = JSON.parse(await readFile(path.join(leaf, 'package.json'), 'utf8'));
    Object.assign(pkg, declaration);
    await writeFile(path.join(leaf, 'package.json'), JSON.stringify(pkg));
    await f.put(
      'node_modules/fixture-leaf/lib-entry/index.js',
      'module.exports="directory entry";',
    );
    const reads = [];
    await expect(
      runtime.verifyNodeRuntime({ root: temp, onRead: (name, kind) => reads.push({ name, kind }) }),
    ).rejects.toThrow(/declared runtime entry/);
    expect(reads.some((r) => r.kind === 'runtime-payload')).toBe(false);
  }, 30000);

test('entry-guard types-only declaration branches remain excluded while safe runtime exports/imports are bound', async () => {
  const f = await nodeFixture(temp),
    file = path.join(temp, 'node_modules', f.sdk, 'package.json'),
    pkg = JSON.parse(await readFile(file, 'utf8'));
  pkg.types = './docs/types.d.ts';
  pkg.typings = './fixtures/types.d.ts';
  for (const value of Object.values(pkg.exports)) {
    value.types = { import: './docs/types.d.ts', require: './fixtures/types.d.cts' };
  }
  pkg.imports = {
    '#runtime': {
      types: './docs/types.d.ts',
      node: './runtime.json',
      default: './dist/esm/client.js',
    },
  };
  await writeFile(file, JSON.stringify(pkg));
  await f.put(`node_modules/${f.sdk}/docs/types.d.ts`, 'unread declarations');
  const reads = [];
  const first = await runtime.verifyNodeRuntime({
    root: temp,
    onRead: (name, kind) => reads.push({ name, kind }),
  });
  expect(first.status).toBe('verified');
  expect(reads.some((r) => r.name.endsWith('/docs/types.d.ts'))).toBe(false);
  await writeFile(
    path.join(temp, 'node_modules', f.sdk, 'runtime.json'),
    '{"changed":"safe local import data"}',
  );
  expect((await runtime.verifyNodeRuntime({ root: temp })).sha256).not.toBe(first.sha256);
}, 30000);
test('entry-guard main through parent link refuses before any runtime payload content', async () => {
  const f = await nodeFixture(temp),
    leaf = path.join(temp, 'node_modules/fixture-leaf'),
    pkg = JSON.parse(await readFile(path.join(leaf, 'package.json'), 'utf8'));
  pkg.main = './local/entry.cjs';
  await writeFile(path.join(leaf, 'package.json'), JSON.stringify(pkg));
  await f.put('outside/entry.cjs', 'module.exports="outside declared target";');
  await symlink(path.join(temp, 'outside'), path.join(leaf, 'local'), 'dir');
  const reads = [];
  await expect(
    runtime.verifyNodeRuntime({ root: temp, onRead: (name, kind) => reads.push({ name, kind }) }),
  ).rejects.toThrow(/declared runtime entry/);
  expect(reads.some((r) => r.kind === 'runtime-payload')).toBe(false);
}, 30000);
test('entry-guard inactive custom TS branch stays nonruntime; enabling its condition is refused', async () => {
  const f = await nodeFixture(temp),
    file = path.join(temp, 'node_modules/fixture-leaf/package.json'),
    pkg = JSON.parse(await readFile(file, 'utf8'));
  pkg.exports = {
    '.': {
      '@fixture/source': './docs/source.ts',
      source: './docs/source.ts',
      default: './index.js',
    },
  };
  await writeFile(file, JSON.stringify(pkg));
  await f.put('node_modules/fixture-leaf/docs/source.ts', 'unread inactive source');
  const reads = [];
  await expect(
    runtime.verifyNodeRuntime({ root: temp, onRead: (name, kind) => reads.push({ name, kind }) }),
  ).resolves.toHaveProperty('status', 'verified');
  expect(reads.some((r) => r.name.endsWith('/docs/source.ts'))).toBe(false);
  await expect(
    runtime.verifyNodeRuntime({
      root: temp,
      execution: { env: {}, execArgv: ['--conditions=source'] },
    }),
  ).rejects.toThrow(/unsupported Node/);
}, 30000);
test('entry-guard module-sync runtime branch follows selected Node capability', async () => {
  await nodeFixture(temp);
  const file = path.join(temp, 'node_modules/fixture-leaf/package.json'),
    pkg = JSON.parse(await readFile(file, 'utf8'));
  pkg.exports = { '.': { 'module-sync': './docs/runtime.cjs', default: './index.js' } };
  await writeFile(file, JSON.stringify(pkg));
  if (process.features.require_module)
    await expect(runtime.verifyNodeRuntime({ root: temp })).rejects.toThrow(
      /declared runtime entry/,
    );
  else
    await expect(runtime.verifyNodeRuntime({ root: temp })).resolves.toHaveProperty(
      'status',
      'verified',
    );
}, 30000);
