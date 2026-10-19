// Synthetic on-disk npm graph, never an install/provider/model.
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
export async function nodeFixture(root) {
  const sdk = '@modelcontextprotocol/sdk';
  const definitions = {
    [`node_modules/${sdk}`]: {
      name: sdk,
      version: '1.0.0',
      type: 'module',
      bin: { 'fixture-sdk': 'bin/sdk-run' },
      dependencies: { 'fixture-dep': '^1.0.0' },
      peerDependencies: { 'fixture-peer': '^2.0.0', 'fixture-absent': '^1.0.0' },
      peerDependenciesMeta: { 'fixture-absent': { optional: true } },
      optionalDependencies: { 'fixture-optional': '^1.0.0' },
      exports: {
        './client/index.js': { import: './dist/esm/client.js', require: './dist/cjs/client.cjs' },
        './client/stdio.js': { import: './dist/esm/stdio.js', require: './dist/cjs/stdio.cjs' },
        './server/mcp.js': { import: './dist/esm/mcp.js', require: './dist/cjs/mcp.cjs' },
        './server/stdio.js': { import: './dist/esm/stdio.js', require: './dist/cjs/stdio.cjs' },
        './server/index.js': { import: './dist/esm/server.js', require: './dist/cjs/server.cjs' },
        './types.js': { import: './dist/esm/types.js', require: './dist/cjs/types.cjs' },
      },
    },
    'node_modules/fixture-dep': { name: 'fixture-dep', version: '2.0.0', main: 'index.js' },
    [`node_modules/${sdk}/node_modules/fixture-dep`]: {
      name: 'fixture-dep',
      version: '1.0.0',
      main: 'index.js',
      dependencies: { 'fixture-leaf': '^1.0.0' },
    },
    'node_modules/fixture-leaf': { name: 'fixture-leaf', version: '1.0.0', main: 'index.js' },
    'node_modules/fixture-peer': { name: 'fixture-peer', version: '2.0.0', main: 'index.js' },
    'node_modules/fixture-optional': {
      name: 'fixture-optional',
      version: '1.0.0',
      main: 'index.js',
    },
    'node_modules/fixture-dev': { name: 'fixture-dev', version: '1.0.0', main: 'index.js' },
  };
  const manifest = {
    name: 'synthetic-node-proof',
    version: '1.0.0',
    type: 'module',
    bin: { 'fixture-sdk': 'bin/sdk-run' },
    dependencies: { [sdk]: '1.0.0', 'fixture-dep': '2.0.0', 'fixture-peer': '2.0.0' },
    devDependencies: { 'fixture-dev': '1.0.0' },
  };
  const lock = {
    name: manifest.name,
    version: manifest.version,
    lockfileVersion: 3,
    requires: true,
    packages: {
      '': manifest,
      ...Object.fromEntries(
        Object.entries(definitions).map(([name, pkg]) => [
          name,
          {
            ...pkg,
            dev: pkg.name === 'fixture-dev',
            resolved: `https://registry.invalid/${pkg.name}-${pkg.version}.tgz`,
          },
        ]),
      ),
    },
  };
  const put = async (name, bytes) => {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), bytes);
  };
  await put('package.json', JSON.stringify(manifest));
  await put('package-lock.json', JSON.stringify(lock));
  for (const [name, pkg] of Object.entries(definitions)) {
    await put(name + '/package.json', JSON.stringify(pkg));
    await put(name + '/index.js', 'module.exports="synthetic runtime";\n');
  }
  for (const name of ['client', 'stdio', 'mcp', 'server', 'types']) {
    await put(`node_modules/${sdk}/dist/esm/${name}.js`, 'export const marker="esm-original";\n');
    await put(`node_modules/${sdk}/dist/cjs/${name}.cjs`, 'exports.marker="cjs-original";\n');
  }
  await put(
    `node_modules/${sdk}/node_modules/fixture-dep/index.js`,
    "module.exports='nested:'+require('fixture-leaf');\n",
  );
  await put(
    `node_modules/${sdk}/dist/esm/client.js`,
    "import dep from 'fixture-dep';import peer from 'fixture-peer';export const marker='esm-original';export const graph=[dep,peer];\n",
  );
  await put(`node_modules/${sdk}/bin/sdk-run`, '#!/usr/bin/env node\nprocess.exit(0);\n');
  await put(`node_modules/${sdk}/runtime.json`, '{"runtime":"original"}');
  await put(`node_modules/${sdk}/runtime.wasm`, 'synthetic wasm bytes (not executed)');
  await put(`node_modules/${sdk}/runtime.node`, 'synthetic native bytes (not executed)');
  await put(`node_modules/${sdk}/runtime.css`, 'body { color: black; }');
  for (const name of [
    '.env',
    '.npmrc',
    'credentials.json',
    'fixtures/auth.json',
    'test/private.key',
    'docs/secret.txt',
    'node_modules/fixture-dev/cache.json',
  ])
    await put(
      name.startsWith('node_modules/') ? name : `node_modules/${sdk}/${name}`,
      'FORBIDDEN OR EXCLUDED CONTENT — never read',
    );
  await put('.npmrc', 'ORIGINAL PROJECT CONFIG MUST NEVER BE READ');
  const refreshInventory = () =>
    put(
      'node_modules/.package-lock.json',
      JSON.stringify({
        ...lock,
        packages: Object.fromEntries(Object.entries(lock.packages).filter(([name]) => name)),
      }),
    );

  return { root, sdk, definitions, manifest, lock, put, refreshInventory };
}
