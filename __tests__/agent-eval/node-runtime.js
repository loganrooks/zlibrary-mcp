// Builtin-only sampled installed runtime-code/data identity; not loaded-memory or supply-chain attestation.
import * as fs from 'node:fs/promises';
import { constants } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
const canonical = (value) =>
  JSON.stringify(value, (_k, v) =>
    v && typeof v === 'object' && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)))
      : v,
  );
export const nodeDigest = (value) =>
  createHash('sha256')
    .update(Buffer.isBuffer(value) || typeof value === 'string' ? value : canonical(value))
    .digest('hex');
const inside = (root, name) =>
  typeof name === 'string' && (name === root || name.startsWith(root + path.sep));
const hash = /^[a-f0-9]{64}$/;
const safe = (name) =>
  typeof name === 'string' &&
  !path.isAbsolute(name) &&
  !name.includes('\\') &&
  name.split('/').every((p) => p && p !== '.' && p !== '..');
const guard = fileURLToPath(new URL('./node-inventory-guard.cjs', import.meta.url));
export const nodeSelectionMethod =
  'guarded-npm-arborist-loadActual-production-graph+native-real-root-sdk-resolution+classified-runtime-bytes-v1';
export const nodePolicy = {
  version: 1,
  selection: nodeSelectionMethod,
  omit: ['dev'],
  offline: true,
  ignoreScripts: true,
  config:
    'owned-empty-only; guarded Node fs content reads; observed-tool instrumentation, NOT OS isolation',
  runtimeExtensions: [
    '.js',
    '.mjs',
    '.cjs',
    '.json',
    '.node',
    '.wasm',
    '.css',
    '.html',
    '.xml',
    '.yaml',
    '.yml',
    '.csv',
    '.txt',
    '.svg',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.webp',
    '.ico',
    '.bin',
    '.dat',
  ],
  declaredExtensionlessBins: true,
  declaredRuntimeEntries: {
    version: 1,
    roles: ['main', 'exports', 'local imports'],
    conditions: [
      'node',
      'node-addons',
      'import',
      'require',
      'default',
      'module-sync when require_module enabled',
    ],
    typesAndInactiveCustomConditions: 'ignored; custom Node conditions refused',
    wildcards:
      'one wildcard in final target segment; static role/escape checks only; native anchors unchanged',
    closure: 'declaration classification, NOT full dynamic import/dataflow closure',
  },
  interiorLinks: false,
  topLevelSharedMapping:
    'physical node_modules basename required; physical package boundaries rechecked; shared install requires npm-accepted existing hidden lock; hidden-lock-absent shared topology fails closed',
  guardMethods: [
    'fs.readFileSync',
    'fs.readFile',
    'fs.openSync',
    'fs.open',
    'fs.createReadStream',
    'fs.promises.readFile',
    'fs.promises.open',
  ],
  unsupportedFdReads: 'deny read/readSync/readv/readvSync and numeric content handles',
  inventoryRecipe: {
    api: 'npm-bundled @npmcli/arborist.loadActual',
    path: 'selected actual root',
    offline: true,
    ignoreScripts: true,
    audit: false,
    fund: false,
    global: false,
    workspaces: false,
    packageLock: true,
    configLoader: false,
    customResolver: false,
    environment:
      'minimal PATH + owned scratch HOME/TMPDIR/XDG_CONFIG_HOME/cache; no inherited npm/Node options',
  },
  guardBoundary:
    'preloaded observed-tool JavaScript API instrumentation; native internal resolution is not traced; NOT adversarial OS isolation',
};
export const nodeExecutionPolicy =
  'no NODE_OPTIONS/NODE_PATH/loaders/preloads/conditions/preserve-symlinks overrides; only runner vm-modules/input-type flags; owned fence preload separately common-source-bound';
export const sdkImports = [
  '@modelcontextprotocol/sdk/client/index.js',
  '@modelcontextprotocol/sdk/client/stdio.js',
  '@modelcontextprotocol/sdk/server/index.js',
  '@modelcontextprotocol/sdk/server/mcp.js',
  '@modelcontextprotocol/sdk/server/stdio.js',
  '@modelcontextprotocol/sdk/types.js',
];
export function assertNodeOptions({ execArgv = process.execArgv, env = process.env } = {}) {
  if (env.NODE_OPTIONS || env.NODE_PATH) throw new Error('unsupported Node options/path override');
  if (execArgv.some((a) => !['--experimental-vm-modules', '--input-type=module'].includes(a)))
    throw new Error('unsupported Node execution options');
}
async function findNpm() {
  for (const dir of (process.env.PATH ?? '').split(path.delimiter)) {
    const name = path.join(dir, process.platform === 'win32' ? 'npm.cmd' : 'npm');
    try {
      await fs.access(name, constants.X_OK);
      const cli = await fs.realpath(name);
      if (cli.endsWith('/npm-cli.js')) return cli;
    } catch {
      /* next explicit PATH candidate */
    }
  }
  throw new Error('unsupported npm CLI layout; absolute npm-cli.js required, no fallback');
}
const localSpec = (value) => typeof value === 'string' && /^(?:file|link|workspace):/.test(value);
function topology(manifest, lock) {
  if (manifest.workspaces || lock.lockfileVersion !== 3 || !lock.packages?.[''])
    throw new Error('unsupported workspace/lock topology');
  for (const pkg of [manifest, ...Object.values(lock.packages)]) {
    if (
      pkg.link ||
      Object.values({
        ...pkg.dependencies,
        ...pkg.optionalDependencies,
        ...pkg.peerDependencies,
        ...pkg.devDependencies,
      }).some(localSpec) ||
      localSpec(pkg.resolved)
    )
      throw new Error('unsupported local/workspace/link topology');
  }
  for (const key of [
    'dependencies',
    'optionalDependencies',
    'peerDependencies',
    'peerDependenciesMeta',
    'devDependencies',
  ])
    if (canonical(manifest[key] ?? {}) !== canonical(lock.packages[''][key] ?? {}))
      throw new Error('root lock/manifest declaration mismatch');
}
const forbidden = (name) =>
  /(?:^|\/)(?:\.?npmrc|\.env(?:\.[^/]*)?|\.netrc|credentials?(?:\.[^/]*)?|id_(?:rsa|dsa|ed25519)(?:\.[^/]*)?|[^/]+\.(?:pem|key|p12|pfx))$/i.test(
    name,
  );
const excluded = (name) =>
  name
    .split('/')
    .some((p) =>
      /^(?:node_modules|__tests__|tests?|fixtures?|examples?|docs?|coverage|\.cache|__snapshots__|\.github|\.git)$/.test(
        p,
      ),
    ) ||
  forbidden(name) ||
  /(?:\.map|\.[cm]?ts|\.flow|\.md|\.markdown|\.rst)$/i.test(name) ||
  /(?:^|\/)(?:readme[^/]*|licen[cs]e[^/]*|notice[^/]*|authors[^/]*|changelog[^/]*|history[^/]*|\.npmignore|\.gitignore|\.gitattributes|\.nycrc[^/]*|\.taprc[^/]*|\.mocharc[^/]*|\.nvmrc|\.travis\.yml|\.editorconfig|\.babelrc[^/]*|\.eslintrc[^/]*|tsconfig[^/]*|jsconfig[^/]*|(?:eslint|jest|rollup|webpack|vite)\.config\.[^/]*)$/i.test(
    name,
  );
// Declaration classification only: never resolve imports or open excluded targets.
async function assertDeclaredRuntimeEntries(pkg, directory) {
  const check = async (target, kind) => {
    if (
      typeof target !== 'string' ||
      !target ||
      /[\\%?#:\0]/.test(target) ||
      (kind !== 'main' && !target.startsWith('./'))
    )
      throw new Error('unsupported declared runtime entry target');
    const relative = target.replace(/^\.\//, ''),
      parts = relative.split('/'),
      pattern = relative.includes('*');
    if (
      !safe(relative) ||
      excluded(relative) ||
      (pattern &&
        (kind === 'main' ||
          relative.split('*').length !== 2 ||
          parts.slice(0, -1).some((p) => p.includes('*'))))
    )
      throw new Error('excluded/unsafe declared runtime entry target');
    if (pattern && /^(?:\.env|\.?npmrc|credentials?)/i.test(parts.at(-1)))
      throw new Error('ambiguous forbidden declared runtime entry pattern');
    const extension = path.extname(relative).toLowerCase();
    if (!pattern && extension && !nodePolicy.runtimeExtensions.includes(extension))
      throw new Error('unclassified declared runtime entry target');
    if (
      pattern &&
      extension &&
      !extension.includes('*') &&
      !nodePolicy.runtimeExtensions.includes(extension)
    )
      throw new Error('unclassified declared runtime entry pattern');
    let current = directory;
    for (let index = 0; index < parts.length; index++) {
      if (pattern && index === parts.length - 1) break;
      current = path.join(current, parts[index]);
      try {
        const stat = await fs.lstat(current);
        if (
          stat.isSymbolicLink() ||
          (index === parts.length - 1 ? !stat.isFile() : !stat.isDirectory())
        )
          throw new Error('unsupported declared runtime entry topology');
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
        break;
      }
    }
  };
  const conditions = new Set([
    'node',
    'node-addons',
    'import',
    'require',
    'default',
    ...(process.features.require_module ? ['module-sync'] : []),
  ]);
  let count = 0;
  const visit = async (value, kind, depth = 0) => {
    if (++count > 10000 || depth > 32) throw new Error('declared runtime entry declaration bound');
    if (value === null) return;
    if (typeof value === 'string') {
      await check(value, kind);
      return;
    }
    if (Array.isArray(value)) {
      for (const target of value) await visit(target, kind, depth + 1);
      return;
    }
    if (!value || typeof value !== 'object')
      throw new Error('unsupported declared runtime entry declaration');
    const entries = Object.entries(value),
      subpaths = entries.some(([key]) => key.startsWith('.'));
    if (subpaths && entries.some(([key]) => key !== '.' && !key.startsWith('./')))
      throw new Error('ambiguous declared runtime entry mapping');
    for (const [condition, target] of entries)
      if (subpaths || conditions.has(condition)) await visit(target, kind, depth + 1);
  };
  if (pkg.main !== undefined && pkg.main !== null && pkg.main !== false)
    await check(pkg.main, 'main');
  if (pkg.exports !== undefined) await visit(pkg.exports, 'exports');
  if (pkg.imports !== undefined) {
    if (!pkg.imports || Array.isArray(pkg.imports) || typeof pkg.imports !== 'object')
      throw new Error('unsupported declared runtime entry imports');
    for (const [key, target] of Object.entries(pkg.imports)) {
      if (!key.startsWith('#') || key === '#' || key.startsWith('#/'))
        throw new Error('unsupported declared runtime entry import key');
      await visit(target, 'imports');
    }
  }
}
function binFiles(pkg) {
  const bins = typeof pkg.bin === 'string' ? [pkg.bin] : Object.values(pkg.bin ?? {});
  return new Set(bins.map((n) => String(n).replace(/^\.\//, '')));
}
async function checkedDirectory(install, locator) {
  if (!safe(locator) || !locator.startsWith('node_modules/'))
    throw new Error('invalid Node package locator');
  let current = install;
  for (const part of locator.slice('node_modules/'.length).split('/')) {
    current = path.join(current, part);
    const st = await fs.lstat(current);
    if (st.isSymbolicLink() || !st.isDirectory())
      throw new Error('unsupported interior Node package link/topology');
  }
  if (!inside(install, await fs.realpath(current)))
    throw new Error('Node package escapes selected install');
  return current;
}
async function discovery({
  root,
  install,
  sharedInstall,
  manifestBytes,
  lockBytes,
  node,
  npmRoot,
  onAudit,
}) {
  const scratch = await fs.realpath(
    await fs.mkdtemp(path.join(os.tmpdir(), 'eval-node-inventory-')),
  );
  try {
    for (const [name, bytes] of [
      ['package.json', manifestBytes],
      ['package-lock.json', lockBytes],
    ])
      await fs.writeFile(path.join(scratch, name), bytes);
    await fs.symlink(install, path.join(scratch, 'node_modules'), 'dir');
    for (const name of ['userconfig', 'globalconfig'])
      await fs.writeFile(path.join(scratch, name), '');
    const policy = {
      scratch,
      install,
      viewInstall: path.join(scratch, 'node_modules'),
      npmRoot,
      manifests: [path.join(root, 'package.json'), path.join(root, 'package-lock.json')],
      trace: path.join(scratch, 'read-trace.jsonl'),
    };
    const flags = ['--require', guard];
    const env = {
      PATH: path.dirname(node),
      HOME: scratch,
      TMPDIR: scratch,
      XDG_CONFIG_HOME: scratch,
      NPM_CONFIG_CACHE: path.join(scratch, 'cache'),
      EVAL_NODE_READ_POLICY: JSON.stringify(policy),
    };
    const inventoryRecipe = {
      path: root,
      cache: path.join(scratch, 'cache'),
      offline: true,
      ignoreScripts: true,
      audit: false,
      fund: false,
      global: false,
      workspaces: false,
      packageLock: true,
    };
    const arboristEntry = path.join(npmRoot, 'node_modules/@npmcli/arborist/lib/index.js');
    const scriptInventory = `const Arborist=require(${JSON.stringify(arboristEntry)});(async()=>{const root=await new Arborist(${JSON.stringify(inventoryRecipe)}).loadActual();if(${JSON.stringify(sharedInstall)}&&!(root.meta?.hiddenLockfile&&root.meta?.loadedFromDisk))throw Object.assign(new Error('unsupported shared hidden-lock topology'),{code:'EVAL_SHARED_HIDDEN_LOCK'});const seen=new Set();let count=0;const visit=node=>{if(++count>10000||node.isLink)throw Object.assign(new Error('unsupported installed-tree link/bound'),{code:'EVAL_LINK_TOPOLOGY'});const value={name:node.package.name,version:node.package.version,path:node.path};if(seen.has(node.path))return value;seen.add(node.path);value.dependencies={};for(const edge of node.edgesOut.values()){if(edge.type==='dev')continue;if(edge.error&&!(edge.error==='MISSING'&&edge.optional)){process.stdout.write(JSON.stringify({failure:{from:node.path,name:edge.name,to:edge.to?.path,error:edge.error}}));throw Object.assign(new Error('invalid installed-tree edge'),{code:'EVAL_INVALID_EDGE'});}value.dependencies[edge.name]=edge.to?visit(edge.to):{};}return value;};process.stdout.write(JSON.stringify(visit(root)));})().catch(error=>{process.stderr.write(JSON.stringify({name:error.name,code:error.code??'EVAL_UNCLASSIFIED'}));process.exitCode=1;});`;
    let tree,
      anchors,
      stage = 'arborist';
    try {
      tree = JSON.parse(
        execFileSync(node, [...flags, '-e', scriptInventory], {
          cwd: scratch,
          env,
          encoding: 'utf8',
          timeout: 20000,
          maxBuffer: 8 * 1024 * 1024,
          stdio: 'pipe',
        }),
      );
      stage = 'native';
      // Native ESM and CJS resolution in REAL source contexts. No package execution,
      // custom import parser or manual package.json subpath resolution.
      const parents = [
        pathToFileURL(path.join(root, '__tests__/agent-eval/server.js')).href,
        pathToFileURL(path.join(root, 'dist/index.js')).href,
      ];
      const script = `import {createRequire} from 'node:module';import {pathToFileURL} from 'node:url';const result=[];for(const parent of ${JSON.stringify(parents)})for(const specifier of ${JSON.stringify(sdkImports)}){result.push({parent,specifier,branch:'import',url:import.meta.resolve(specifier,parent)});result.push({parent,specifier,branch:'require',url:pathToFileURL(createRequire(parent).resolve(specifier)).href});}process.stdout.write(JSON.stringify(result));`;
      anchors = JSON.parse(
        execFileSync(
          node,
          [...flags, '--experimental-import-meta-resolve', '--input-type=module', '-e', script],
          {
            cwd: scratch,
            env,
            encoding: 'utf8',
            timeout: 10000,
            maxBuffer: 1024 * 1024,
            stdio: 'pipe',
          },
        ),
      );
    } catch (error) {
      let issues = [];
      try {
        issues =
          JSON.parse(error.stdout)
            .problems?.map((p) =>
              /^(missing|invalid|extraneous):\s+([^\s,]+)/.exec(p)?.slice(1).join(':'),
            )
            .filter(Boolean)
            .slice(0, 8) ?? [];
      } catch {
        /* non-JSON failure */
      }
      const codes = [
        ...new Set(
          String(error.stderr ?? '').match(/\b(?:ERR_[A-Z_]+|EVAL_[A-Z_]+|E[A-Z]{3,})\b/g) ?? [],
        ),
      ].slice(0, 5);
      try {
        await onAudit?.({
          scratch,
          trace: (await fs.readFile(policy.trace, 'utf8'))
            .trim()
            .split('\n')
            .filter(Boolean)
            .map(JSON.parse),
          failed: true,
          stage,
          codes,
          summary: (() => {
            let count = 0;
            const shape = (n, depth = 0) => ({
              name: n.name,
              version: n.version,
              path: n.path,
              children:
                depth < 4 && ++count < 32
                  ? Object.fromEntries(
                      Object.entries(n.dependencies ?? {})
                        .slice(0, 16)
                        .map(([k, v]) => [k, shape(v, depth + 1)]),
                    )
                  : undefined,
            });
            try {
              const parsed = JSON.parse(error.stdout);
              return parsed.failure ?? shape(parsed);
            } catch {
              return undefined;
            }
          })(),
        });
      } catch {
        /* retain primary failure */
      }
      throw new Error(
        'guarded ' +
          stage +
          ' inventory failed, exit ' +
          (error.status ?? 'unsupported') +
          ' codes=' +
          codes.join(',') +
          ' issues=' +
          issues.join(',') +
          ' resource=' +
          (String(error.stderr ?? '').match(/resource: ['"]([^'"]+)['"]/)?.[1] ?? '[not exposed]'),
      );
    }
    const trace = (await fs.readFile(policy.trace, 'utf8'))
      .trim()
      .split('\n')
      .filter(Boolean)
      .map(JSON.parse);
    if (trace.length > 40000) throw new Error('Node read trace exceeds bound');
    const audit = {
      unsupportedReads: trace.filter((e) => e.operation === 'unsupported-fd-read').length,
      writeAttempts: trace.filter((e) => e.operation === 'write-denied').length,
      configContentReads: trace.filter(
        (e) => e.allowed && /\.?npmrc$/.test(e.path) && !inside(scratch, e.path),
      ).length,
      networkAttempts: trace.filter((e) => e.operation === 'network').length,
      childAttempts: trace.filter((e) => e.operation === 'child-process').length,
      guardedReads: trace.length,
      blocked: trace.filter((e) => !e.allowed).length,
      readGuardMethod: 'Node fs API preload + actual trace; no OS sandbox',
    };
    if (
      audit.configContentReads ||
      audit.networkAttempts ||
      audit.childAttempts ||
      audit.writeAttempts ||
      audit.unsupportedReads
    )
      throw new Error('Node inventory read/network/lifecycle boundary failed');
    await onAudit?.({ scratch, trace, audit });
    const toolFiles = [];
    for (const name of [
      ...new Set(trace.filter((e) => e.allowed && inside(npmRoot, e.path)).map((e) => e.path)),
    ].sort()) {
      const actual = await fs.realpath(name);
      if (
        !inside(npmRoot, actual) ||
        forbidden(actual) ||
        !/[.](?:js|mjs|cjs|json|node|wasm)$/.test(actual)
      )
        throw new Error('unsupported inventory tool content');
      toolFiles.push({
        path: path.relative(npmRoot, actual).split(path.sep).join('/'),
        sha256: nodeDigest(await fs.readFile(actual)),
      });
    }
    toolFiles.sort((a, b) => a.path.localeCompare(b.path));
    return { tree, anchors, scratch, audit, toolFiles };
  } finally {
    await fs.rm(scratch, { recursive: true, force: true });
  }
}
async function snapshot({ root, onRead, onAudit, readBytes }) {
  const read = async (name, kind) => {
    await onRead?.(name, kind);
    return readBytes ? readBytes(name, kind) : fs.readFile(name);
  };
  const node = await fs.realpath(process.execPath),
    cli = await findNpm(),
    npmRoot = path.dirname(path.dirname(cli)),
    install = await fs.realpath(path.join(root, 'node_modules'));
  const nodeStat = await fs.lstat(path.join(root, 'node_modules'));
  if (!nodeStat.isDirectory() && !nodeStat.isSymbolicLink())
    throw new Error('missing selected Node install');
  if (nodeStat.isSymbolicLink() && path.basename(install) !== 'node_modules')
    throw new Error('unsupported shared Node physical mapping: node_modules basename required');
  const manifests = [];
  const buffers = [];
  for (const name of ['package.json', 'package-lock.json']) {
    if (!(await fs.lstat(path.join(root, name))).isFile())
      throw new Error('Node manifest link/non-file');
    const bytes = await read(path.join(root, name), 'manifest');
    buffers.push(bytes);
    manifests.push({ path: name, sha256: nodeDigest(bytes) });
  }
  manifests.sort((a, b) => a.path.localeCompare(b.path));
  const manifest = JSON.parse(buffers[0]),
    lock = JSON.parse(buffers[1]);
  topology(manifest, lock);
  await assertDeclaredRuntimeEntries(manifest, root);
  const nodeIdentity = {
    binarySha256: nodeDigest(await read(node, 'node-binary')),
    version: process.version,
    platform: process.platform,
    arch: process.arch,
    abi: process.versions.modules,
    options: nodeExecutionPolicy,
  };
  const tool = {
    version: JSON.parse(await read(path.join(npmRoot, 'package.json'), 'inventory-tool')).version,
    cliSha256: nodeDigest(await read(cli, 'inventory-tool')),
    guardSha256: nodeDigest(await read(guard, 'inventory-tool')),
    arboristVersion: JSON.parse(
      await read(
        path.join(npmRoot, 'node_modules/@npmcli/arborist/package.json'),
        'inventory-tool',
      ),
    ).version,
    arboristSha256: nodeDigest(
      await read(
        path.join(npmRoot, 'node_modules/@npmcli/arborist/lib/index.js'),
        'inventory-tool',
      ),
    ),
  };
  const inventory = await discovery({
    root,
    install,
    sharedInstall: nodeStat.isSymbolicLink(),
    manifestBytes: buffers[0],
    lockBytes: buffers[1],
    node,
    cli,
    npmRoot,
    onAudit,
  });
  tool.files = inventory.toolFiles;
  const nodes = new Map(),
    rawEdges = new Map();
  let visited = 0;
  const locator = (name) => {
    const logical = inside(path.join(root, 'node_modules'), name)
      ? 'node_modules/' + path.relative(path.join(root, 'node_modules'), name)
      : inside(install, name)
        ? 'node_modules/' + path.relative(install, name)
        : null;
    if (logical === null || !safe(logical))
      throw new Error('npm inventory escapes selected install');
    return logical;
  };
  const visit = (n, isRoot = false) => {
    if (
      ++visited > 10000 ||
      n.link ||
      n.invalid ||
      n.extraneous ||
      n.missing ||
      n.problems?.length ||
      localSpec(n.resolved)
    )
      throw new Error('invalid/missing/link npm graph');
    const from = isRoot ? '' : locator(n.path);
    if (!isRoot) {
      if (!n.name || !n.version) throw new Error('incomplete npm package identity');
      const previous = nodes.get(from);
      if (previous && (previous.name !== n.name || previous.version !== n.version))
        throw new Error('inconsistent npm duplicate locator');
      nodes.set(from, { name: n.name, version: n.version });
    }
    for (const [name, d] of Object.entries(n.dependencies ?? {})) {
      const to = d.path ? locator(d.path) : null,
        key = from + '\0' + name,
        old = rawEdges.get(key);
      if (old && old.to !== to) throw new Error('inconsistent npm edge');
      rawEdges.set(key, { from, name, to });
      if (to) visit(d);
    }
  };
  visit(inventory.tree, true);
  const packages = [],
    edges = [],
    metadata = new Map([['', manifest]]),
    packageInputs = [];
  for (const [locator, n] of [...nodes].sort(([a], [b]) => a.localeCompare(b))) {
    const directory = await checkedDirectory(install, locator),
      bytes = await read(path.join(directory, 'package.json'), 'package-metadata'),
      pkg = JSON.parse(bytes),
      pinned = lock.packages[locator];
    if (
      pkg.name !== n.name ||
      pkg.version !== n.version ||
      !pinned ||
      pinned.version !== n.version ||
      pinned.link
    )
      throw new Error('installed package/lock graph mismatch');
    for (const key of [
      'dependencies',
      'optionalDependencies',
      'peerDependencies',
      'peerDependenciesMeta',
    ])
      if (canonical(pkg[key] ?? {}) !== canonical(pinned[key] ?? {}))
        throw new Error('installed dependency declarations differ from lock');
    await assertDeclaredRuntimeEntries(pkg, directory);
    metadata.set(locator, pkg);
    packageInputs.push({ locator, n, directory, bytes, pkg });
  }
  for (const { locator, n, directory, bytes, pkg } of packageInputs) {
    const files = [{ path: 'package.json', sha256: nodeDigest(bytes) }],
      bins = binFiles(pkg);
    const walk = async (relative = '') => {
      for (const entry of (await fs.readdir(path.join(directory, relative))).sort()) {
        const name = relative ? relative + '/' + entry : entry;
        if (name === 'package.json' || excluded(name)) continue;
        const file = path.join(directory, name),
          st = await fs.lstat(file);
        if (st.isSymbolicLink()) throw new Error('runtime package interior link');
        if (st.isDirectory()) {
          await walk(name);
          continue;
        }
        if (!st.isFile()) throw new Error('unsupported runtime package file');
        if (
          !nodePolicy.runtimeExtensions.includes(path.extname(name).toLowerCase()) &&
          !bins.has(name)
        )
          throw new Error('unclassified runtime asset: ' + n.name + '/' + name);
        files.push({ path: name, sha256: nodeDigest(await read(file, 'runtime-payload')) });
        if (files.length > 50000) throw new Error('runtime package file bound exceeded');
      }
    };
    await walk();
    files.sort((a, b) => a.path.localeCompare(b.path));
    for (const bin of bins)
      if (!safe(bin) || excluded(bin) || !files.some((f) => f.path === bin))
        throw new Error('unbound/forbidden declared runtime bin');
    packages.push({
      locator,
      name: n.name,
      version: n.version,
      bins: [...bins].sort(),
      files,
      sha256: nodeDigest(files),
    });
  }
  for (const [from, pkg] of metadata) {
    const names = new Set([
      ...Object.keys(pkg.dependencies ?? {}),
      ...Object.keys(pkg.optionalDependencies ?? {}),
      ...Object.keys(pkg.peerDependencies ?? {}),
    ]);
    for (const name of names) {
      const optional =
          Object.hasOwn(pkg.optionalDependencies ?? {}, name) ||
          pkg.peerDependenciesMeta?.[name]?.optional === true,
        kind = Object.hasOwn(pkg.optionalDependencies ?? {}, name)
          ? 'optional'
          : Object.hasOwn(pkg.dependencies ?? {}, name)
            ? 'dependency'
            : 'peer',
        found = rawEdges.get(from + '\0' + name);
      if (!found?.to && !optional) throw new Error('missing required installed edge');
      if (found?.to && !nodes.has(found.to)) throw new Error('edge outside selected graph');
      edges.push({
        from,
        name,
        to: found?.to ?? null,
        kind,
        optional,
        spec:
          pkg.optionalDependencies?.[name] ??
          pkg.dependencies?.[name] ??
          pkg.peerDependencies?.[name],
      });
      rawEdges.delete(from + '\0' + name);
    }
  }
  if (rawEdges.size) throw new Error('undeclared npm graph edge');
  edges.sort((a, b) => canonical(a).localeCompare(canonical(b)));
  const anchors = [];
  for (const a of inventory.anchors) {
    const physical = await fs.realpath(fileURLToPath(a.url)).catch(() => {
      throw new Error('missing native runtime anchor');
    });
    if (!inside(install, physical)) throw new Error('native import escapes selected install');
    const relative = 'node_modules/' + path.relative(install, physical).split(path.sep).join('/');
    const owner = packages
      .filter((p) => relative.startsWith(p.locator + '/'))
      .sort((a, b) => b.locator.length - a.locator.length)[0];
    const file = owner && relative.slice(owner.locator.length + 1);
    if (!owner?.files.some((f) => f.path === file))
      throw new Error('native import anchor not bound to runtime bytes');
    anchors.push({
      context: a.parent.includes('/__tests__/') ? 'evaluator' : 'build',
      specifier: a.specifier,
      branch: a.branch,
      locator: owner.locator,
      file,
    });
  }
  anchors.sort((a, b) => canonical(a).localeCompare(canonical(b)));
  const identity = {
    version: 1,
    method: nodeSelectionMethod,
    policy: nodePolicy,
    node: nodeIdentity,
    tool,
    manifests,
    packages,
    edges,
    anchors,
  };
  return {
    version: 1,
    status: 'verified',
    identity,
    sha256: nodeDigest(identity),
    local: {
      root,
      install,
      node,
      cli,
      packageRoots: packages.map((p) => ({
        locator: p.locator,
        realpath: path.join(install, p.locator.slice('node_modules/'.length)),
      })),
    },
    audit: inventory.audit,
  };
}
export async function verifyNodeRuntime(options = {}) {
  assertNodeOptions(options.execution);
  const root = await fs.realpath(options.root),
    before = await snapshot({ ...options, root });
  await options.beforeRecheck?.();
  if ((await fs.realpath(path.join(root, 'node_modules'))) !== before.local.install)
    throw new Error('Node selected install target drift during verification');
  const after = await snapshot({ ...options, root });
  if (before.sha256 !== after.sha256 || canonical(before.local) !== canonical(after.local))
    throw new Error('Node runtime graph/payload/locator drift during verification');
  return { ...after, stable: true };
}
export function nodeProofErrors(proof, manifestFiles) {
  const fail = (reason) => ['Node runtime proof: ' + reason];
  const id = proof?.identity;
  if (
    proof?.version !== 1 ||
    proof.status !== 'verified' ||
    proof.stable !== true ||
    !id ||
    id.version !== 1 ||
    id.method !== nodeSelectionMethod ||
    canonical(id.policy) !== canonical(nodePolicy) ||
    proof.sha256 !== nodeDigest(id)
  )
    return fail('missing/legacy/unverified identity');
  if (
    !hash.test(id.node?.binarySha256 ?? '') ||
    !id.node.version ||
    !id.node.platform ||
    !id.node.arch ||
    !id.node.abi ||
    id.node.options !== nodeExecutionPolicy ||
    !hash.test(id.tool?.cliSha256 ?? '') ||
    !hash.test(id.tool?.guardSha256 ?? '') ||
    !id.tool.version ||
    !id.tool.arboristVersion ||
    !hash.test(id.tool.arboristSha256 ?? '') ||
    proof.audit?.configContentReads !== 0 ||
    proof.audit.networkAttempts !== 0 ||
    proof.audit.childAttempts !== 0 ||
    proof.audit.writeAttempts !== 0 ||
    proof.audit.unsupportedReads !== 0 ||
    !Array.isArray(id.tool.files) ||
    !id.tool.files.length ||
    id.tool.files.some((f) => !safe(f.path) || !hash.test(f.sha256))
  )
    return fail('missing Node/tool/options/read guard identity');
  if (
    !Array.isArray(id.manifests) ||
    id.manifests.length !== 2 ||
    !['package.json', 'package-lock.json'].every((n) =>
      id.manifests.some(
        (f) =>
          f.path === n &&
          hash.test(f.sha256) &&
          manifestFiles?.some((m) => m.path === n && m.sha256 === f.sha256),
      ),
    )
  )
    return fail('manifest binding mismatch');
  if (
    !Array.isArray(id.packages) ||
    !id.packages.length ||
    !Array.isArray(id.edges) ||
    !Array.isArray(id.anchors) ||
    id.anchors.length !== sdkImports.length * 4
  )
    return fail('missing dependency graph/native anchors');
  const locators = new Set();
  for (const p of id.packages) {
    if (
      !safe(p.locator) ||
      !p.locator.startsWith('node_modules/') ||
      locators.has(p.locator) ||
      !p.name ||
      !p.version ||
      !Array.isArray(p.files) ||
      !p.files.length ||
      p.sha256 !== nodeDigest(p.files) ||
      !p.files.some((f) => f.path === 'package.json') ||
      new Set(p.files.map((f) => f.path)).size !== p.files.length ||
      !Array.isArray(p.bins) ||
      p.bins.some((n) => !safe(n) || excluded(n) || !p.files.some((f) => f.path === n)) ||
      p.files.some(
        (f) =>
          !safe(f.path) ||
          !hash.test(f.sha256) ||
          excluded(f.path) ||
          (!nodePolicy.runtimeExtensions.includes(path.extname(f.path)) &&
            !p.bins.includes(f.path)),
      )
    )
      return fail('invalid package runtime manifest');
    locators.add(p.locator);
  }
  if (
    !proof.local ||
    !['root', 'install', 'node', 'cli'].every(
      (k) => typeof proof.local[k] === 'string' && path.isAbsolute(proof.local[k]),
    ) ||
    !Array.isArray(proof.local.packageRoots)
  )
    return fail('missing absolute local topology');
  if (new Set(id.tool.files.map((f) => f.path)).size !== id.tool.files.length)
    return fail('duplicate inventory tool file');
  if (
    proof.local.packageRoots.length !== locators.size ||
    new Set(proof.local.packageRoots.map((p) => p.locator)).size !== locators.size ||
    proof.local.packageRoots.some(
      (p) =>
        !locators.has(p.locator) ||
        p.realpath !== path.join(proof.local.install, p.locator.slice('node_modules/'.length)),
    )
  )
    return fail('physical package topology mismatch');
  const edgeKeys = id.edges.map((e) => e.from + '\0' + e.name),
    anchorKeys = id.anchors.map((a) => a.context + '\0' + a.specifier + '\0' + a.branch);
  if (new Set(edgeKeys).size !== edgeKeys.length || new Set(anchorKeys).size !== anchorKeys.length)
    return fail('duplicate edge/native anchor');
  const ordered = (items, key) =>
    canonical(items.map(key)) ===
    canonical([...items].sort((a, b) => key(a).localeCompare(key(b))).map(key));
  if (
    !ordered(id.tool.files, (f) => f.path) ||
    !ordered(id.packages, (p) => p.locator) ||
    !id.packages.every((p) => ordered(p.files, (f) => f.path)) ||
    !ordered(id.edges, canonical) ||
    !ordered(id.anchors, canonical) ||
    !ordered(id.manifests, (f) => f.path)
  )
    return fail('noncanonical runtime manifest/graph');
  for (const e of id.edges)
    if (
      (e.from && !locators.has(e.from)) ||
      (e.to !== null && !locators.has(e.to)) ||
      (e.to === null && !e.optional) ||
      !e.name ||
      !['dependency', 'optional', 'peer'].includes(e.kind) ||
      typeof e.optional !== 'boolean' ||
      typeof e.spec !== 'string' ||
      localSpec(e.spec)
    )
      return fail('invalid dependency edge');
  for (const a of id.anchors)
    if (
      !sdkImports.includes(a.specifier) ||
      !['import', 'require'].includes(a.branch) ||
      !['evaluator', 'build'].includes(a.context) ||
      !id.packages.some((p) => p.locator === a.locator && p.files.some((f) => f.path === a.file))
    )
      return fail('invalid native import anchor');
  return [];
}
