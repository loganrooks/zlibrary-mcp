// Selected interpreter + resolved dependency METADATA proof, not package payload attestation.
import { execFileSync } from 'node:child_process';
import { lstat, readFile, realpath, mkdtemp, rm, access } from 'node:fs/promises';
import { constants } from 'node:fs';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import path from 'node:path';
import { evaluatorRoot, digest, canonical } from './evaluator-identity.js';
import { manifestDigest } from './build-proof.js';
export const pythonPolicy = {
  defaultGroups: false,
  groups: ['dev'],
  extras: [],
  frozen: true,
  offline: true,
  checkOnly: true,
  noUserSite: true,
};
const checkArgs = [
  'sync',
  '--check',
  '--frozen',
  '--offline',
  '--no-default-groups',
  '--group',
  'dev',
  '--no-config',
];
const invoke = (binary, args, options) =>
  execFileSync(binary, args, {
    ...options,
    encoding: 'utf8',
    stdio: 'pipe',
    maxBuffer: 8 * 1024 * 1024,
  });
const inside = (root, file) =>
  typeof file === 'string' && (file === root || file.startsWith(root + path.sep));
export function pythonDescriptor(buildRoot, commonRoot = evaluatorRoot) {
  return {
    executable: path.join(
      buildRoot,
      '.venv',
      process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
    ),
    env: {
      PYTHONDONTWRITEBYTECODE: '1',
      PYTHONNOUSERSITE: '1',
      PYTHONPATH: [
        path.join(commonRoot, '__tests__/agent-eval'),
        path.join(commonRoot, '__tests__/rehearsal'),
        path.join(buildRoot, 'zlibrary/src'),
        buildRoot,
      ].join(path.delimiter),
    },
  };
}
async function findUv() {
  for (const dir of (process.env.PATH ?? '').split(path.delimiter)) {
    const name = path.join(dir, process.platform === 'win32' ? 'uv.exe' : 'uv');
    try {
      await access(name, constants.X_OK);
      return await realpath(name);
    } catch {
      /* try next PATH entry */
    }
  }
  throw new Error('Python proof requires existing uv executable; no install attempted');
}
export async function verifyPythonRuntime({
  buildRoot,
  commonRoot = evaluatorRoot,
  probe = invoke,
  uvIdentity,
} = {}) {
  buildRoot = await realpath(buildRoot);
  commonRoot = await realpath(commonRoot);
  const venv = path.join(buildRoot, '.venv'),
    stat = await lstat(venv);
  if (stat.isSymbolicLink() || !stat.isDirectory() || (await realpath(venv)) !== venv)
    throw new Error('selected Python environment must be local, not a foreign symlink');
  const descriptor = pythonDescriptor(buildRoot, commonRoot),
    binary = await realpath(descriptor.executable),
    binarySha256 = digest(await readFile(binary));
  const files = [];
  for (const name of ['pyproject.toml', 'uv.lock']) {
    if (!(await lstat(path.join(buildRoot, name))).isFile())
      throw new Error('Python manifest symlink');
    files.push({ path: name, sha256: digest(await readFile(path.join(buildRoot, name))) });
  }
  const manifests = { files, sha256: manifestDigest(files) },
    uv = uvIdentity ? 'uv' : await findUv(),
    scratch = await mkdtemp(path.join(os.tmpdir(), 'eval-python-check-'));
  try {
    // An allowlist, not an inherited env with redirection flags subtracted. --check never syncs.
    const env = {
      PATH: process.env.PATH,
      HOME: scratch,
      TMPDIR: scratch,
      XDG_CONFIG_HOME: scratch,
      XDG_CACHE_HOME: scratch,
      UV_CACHE_DIR: scratch,
      UV_PROJECT_ENVIRONMENT: venv,
      UV_PYTHON: descriptor.executable,
      UV_PYTHON_DOWNLOADS: 'never',
      UV_OFFLINE: '1',
      UV_NO_CONFIG: '1',
      ...descriptor.env,
    };
    const options = { cwd: scratch, env, timeout: 15000 };
    const uvProof = uvIdentity ?? {
      sha256: digest(await readFile(uv)),
      version: String(await probe(uv, ['--version'], options)).trim(),
    };
    if (!/^[a-f0-9]{64}$/.test(uvProof.sha256 ?? '') || !uvProof.version)
      throw new Error('missing uv identity');
    await probe(uv, [...checkArgs, '--project', buildRoot], options);
    const raw = JSON.parse(
      await probe(
        descriptor.executable,
        ['-c', await readFile(new URL('./python-probe.py', import.meta.url), 'utf8')],
        options,
      ),
    );
    if (raw.executable !== descriptor.executable || raw.prefix !== venv || raw.userSite !== false)
      throw new Error('foreign launcher/prefix or user-site Python policy');
    for (const key of ['basePrefix', 'version', 'implementation', 'cacheTag', 'platform', 'arch'])
      if (typeof raw[key] !== 'string' || !raw[key])
        throw new Error('incomplete Python interpreter metadata');
    if (
      !Array.isArray(raw.sysPath) ||
      raw.sysPath.some(
        (p) =>
          typeof p !== 'string' ||
          (p && ![buildRoot, venv, commonRoot, raw.basePrefix].some((root) => inside(root, p))),
      )
    )
      throw new Error('foreign Python import path');
    if (!Array.isArray(raw.distributions) || !raw.distributions.length)
      throw new Error('missing distribution metadata');
    const seen = new Set(),
      sourceMetadata = [],
      installedMetadata = [];
    // Validate origins BEFORE normalization; local PYTHONPATH cannot rescue a foreign editable.
    const distributions = [];
    for (const d of raw.distributions) {
      if (typeof d.name !== 'string' || !d.name || typeof d.version !== 'string' || !d.version)
        throw new Error('incomplete Python distribution');
      const name = d.name.toLowerCase().replace(/[-_.]+/g, '-'),
        location = await realpathOrLexical(d.location, probe !== invoke),
        key = name + '\0' + location;
      if (seen.has(key)) throw new Error('duplicate Python distribution');
      seen.add(key);
      if (!inside(venv, location)) {
        if (name !== 'zlibrary' || location !== path.join(buildRoot, 'zlibrary/src') || d.directUrl)
          throw new Error('foreign distribution metadata origin');
        sourceMetadata.push(d);
        distributions.push({ ...d, name });
        continue;
      }
      if (installedMetadata.some((item) => item.name === name))
        throw new Error('duplicate installed Python distribution');
      installedMetadata.push({ ...d, name });
      if (d.directUrl) {
        const url = new URL(d.directUrl.url);
        if (url.username || url.password) throw new Error('credentialed distribution origin');
        if (url.protocol === 'file:') {
          const origin = await realpathOrLexical(fileURLToPath(url), probe !== invoke);
          if (
            name !== 'zlibrary' ||
            origin !== path.join(buildRoot, 'zlibrary') ||
            d.directUrl.dir_info?.editable !== true
          )
            throw new Error('foreign editable distribution origin');
        } else if (d.directUrl.dir_info?.editable || name === 'zlibrary')
          throw new Error('invalid editable distribution origin');
      }
      if (name === 'zlibrary' && (!d.directUrl || d.directUrl.dir_info?.editable !== true))
        throw new Error('missing local editable zlibrary');
      distributions.push({ ...d, name });
    }
    if (
      sourceMetadata.length > 1 ||
      installedMetadata.filter((d) => d.name === 'zlibrary').length !== 1 ||
      sourceMetadata.some(
        (d) => d.version !== installedMetadata.find((d) => d.name === 'zlibrary')?.version,
      ) ||
      !inside(
        path.join(buildRoot, 'zlibrary/src/zlibrary'),
        await realpathOrLexical(raw.imports?.zlibrary, probe !== invoke),
      )
    )
      throw new Error('foreign/missing zlibrary import');
    for (const [name, origin] of Object.entries(raw.imports ?? {}))
      if (name !== 'zlibrary' && !inside(venv, await realpathOrLexical(origin, probe !== invoke)))
        throw new Error('foreign dependency import');
    if (
      probe === invoke &&
      !['httpx', 'aiofiles', 'bs4', 'lxml', 'dotenv', 'libgen_api_enhanced'].every(
        (n) => raw.imports[n],
      )
    )
      throw new Error('missing required dependency imports');
    const normalize = (value) => {
      if (Array.isArray(value)) return value.map(normalize);
      if (value && typeof value === 'object')
        return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, normalize(v)]));
      if (typeof value !== 'string') return value;
      // Role-specific common paths take precedence even when A buildRoot == evaluatorRoot.
      for (const [from, to] of [
        [path.join(commonRoot, '__tests__/agent-eval'), '$EVALUATORROOT/__tests__/agent-eval'],
        [path.join(commonRoot, '__tests__/rehearsal'), '$EVALUATORROOT/__tests__/rehearsal'],
        [venv, '$VENV'],
        [buildRoot, '$BUILDROOT'],
        [raw.basePrefix, '$PYTHONBASE'],
      ]) {
        if (inside(from, value)) return to + value.slice(from.length);
        if (value.startsWith('file://')) {
          let local;
          try {
            local = fileURLToPath(value);
          } catch {
            continue;
          }
          if (inside(from, local)) return 'file://' + to + local.slice(from.length);
        }
      }
      return value;
    };
    distributions.sort(
      (a, b) => a.name.localeCompare(b.name) || a.location.localeCompare(b.location),
    );
    const metadata = normalize({
      policy: pythonPolicy,
      recipe: checkArgs,
      uv: uvProof,
      binarySha256,
      interpreter: {
        executable: raw.executable,
        prefix: raw.prefix,
        basePrefix: raw.basePrefix,
        version: raw.version,
        implementation: raw.implementation,
        cacheTag: raw.cacheTag,
        platform: raw.platform,
        arch: raw.arch,
        userSite: raw.userSite,
        sysPath: raw.sysPath,
      },
      distributions,
      imports: raw.imports,
      manifests,
    });
    metadata.distributions.sort(
      (a, b) => a.name.localeCompare(b.name) || a.location.localeCompare(b.location),
    );
    // Re-read non-metadata bytes around the bounded readiness/probe operation.
    if (
      (!uvIdentity && digest(await readFile(uv)) !== uvProof.sha256) ||
      digest(await readFile(binary)) !== binarySha256 ||
      (await realpath(descriptor.executable)) !== binary ||
      files.some((f) => !f.sha256)
    )
      throw new Error('Python interpreter changed during proof');
    for (const f of files)
      if (digest(await readFile(path.join(buildRoot, f.path))) !== f.sha256)
        throw new Error('Python manifests changed during proof');
    return {
      version: 1,
      status: 'verified',
      descriptor,
      binary,
      manifests,
      metadata,
      sha256: digest(metadata),
      boundary:
        'Selected interpreter and resolved dependency METADATA only; not installed payload/.pth/stdlib/shared-library identity, hermeticity, supply-chain attestation, or independent per-process Python attestation.',
    };
  } finally {
    await rm(scratch, { recursive: true, force: true });
  }
}
async function realpathOrLexical(value, synthetic) {
  if (typeof value !== 'string' || !path.isAbsolute(value))
    throw new Error('invalid Python metadata path');
  return synthetic ? path.resolve(value) : realpath(value);
}
export function pythonProofErrors(proof, build) {
  const fail = (message) => ['Python metadata proof: ' + message];
  if (
    proof?.version !== 1 ||
    proof.status !== 'verified' ||
    !proof.metadata ||
    proof.sha256 !== digest(proof.metadata) ||
    !path.isAbsolute(proof.descriptor?.executable ?? '')
  )
    return fail('missing/unverified metadata identity');
  const m = proof.metadata;
  if (
    canonical(m.policy) !== canonical(pythonPolicy) ||
    canonical(m.recipe) !== canonical(checkArgs) ||
    !/^[a-f0-9]{64}$/.test(m.binarySha256 ?? '') ||
    !/^[a-f0-9]{64}$/.test(m.uv?.sha256 ?? '') ||
    !m.uv.version ||
    m.interpreter?.prefix !== '$VENV' ||
    m.interpreter.userSite !== false ||
    !m.distributions?.length ||
    !m.distributions.some(
      (d) =>
        d.name === 'zlibrary' &&
        d.directUrl?.url === 'file://$BUILDROOT/zlibrary' &&
        d.directUrl.dir_info?.editable === true,
    ) ||
    !m.imports?.zlibrary?.startsWith('$BUILDROOT/zlibrary/src/zlibrary/')
  )
    return fail('inconsistent normalized policy/metadata');
  const interpreter = m.interpreter;
  if (
    !['version', 'implementation', 'cacheTag', 'platform', 'arch'].every(
      (k) => typeof interpreter[k] === 'string' && interpreter[k],
    ) ||
    interpreter.basePrefix !== '$PYTHONBASE' ||
    !['$VENV/bin/python', '$VENV/Scripts/python.exe'].includes(interpreter.executable) ||
    !Array.isArray(interpreter.sysPath) ||
    interpreter.sysPath.some(
      (p) =>
        typeof p !== 'string' ||
        (p &&
          !['$VENV', '$BUILDROOT', '$EVALUATORROOT', '$PYTHONBASE'].some((root) =>
            inside(root, p),
          )),
    ) ||
    proof.descriptor.env?.PYTHONNOUSERSITE !== '1' ||
    proof.descriptor.env?.PYTHONDONTWRITEBYTECODE !== '1' ||
    !proof.descriptor.env?.PYTHONPATH
  )
    return fail('incomplete launcher/interpreter policy');
  const installed = new Set(),
    unique = new Set(),
    source = [];
  const order = [];
  for (const d of m.distributions) {
    if (
      typeof d.name !== 'string' ||
      d.name !== d.name.toLowerCase().replace(/[-_.]+/g, '-') ||
      !d.name ||
      typeof d.version !== 'string' ||
      !d.version ||
      typeof d.location !== 'string' ||
      d.location.split('/').includes('..')
    )
      return fail('invalid distribution metadata');
    const key = d.name + '\0' + d.location;
    if (unique.has(key)) return fail('duplicate distribution metadata');
    unique.add(key);
    order.push(key);
    if (!inside('$VENV', d.location)) {
      if (d.name !== 'zlibrary' || d.location !== '$BUILDROOT/zlibrary/src' || d.directUrl)
        return fail('foreign distribution metadata');
      source.push(d);
      continue;
    }
    if (installed.has(d.name)) return fail('duplicate installed distribution');
    installed.add(d.name);
    if (
      d.name === 'zlibrary' &&
      (d.directUrl?.url !== 'file://$BUILDROOT/zlibrary' || d.directUrl.dir_info?.editable !== true)
    )
      return fail('foreign editable origin');
    if (d.directUrl && d.name !== 'zlibrary') {
      let url;
      try {
        url = new URL(d.directUrl.url);
      } catch {
        return fail('invalid distribution URL');
      }
      if (
        url.protocol === 'file:' ||
        url.username ||
        url.password ||
        d.directUrl.dir_info?.editable
      )
        return fail('foreign distribution URL');
    }
  }
  const sorted = [...m.distributions]
    .sort((a, b) => a.name.localeCompare(b.name) || a.location.localeCompare(b.location))
    .map((d) => d.name + '\0' + d.location);
  if (
    canonical(order) !== canonical(sorted) ||
    !installed.has('zlibrary') ||
    source.length > 1 ||
    source.some(
      (d) =>
        d.version !==
        m.distributions.find((d) => d.name === 'zlibrary' && inside('$VENV', d.location))?.version,
    )
  )
    return fail('noncanonical distribution inventory');
  if (
    Object.entries(m.imports).some(
      ([name, origin]) =>
        typeof origin !== 'string' ||
        origin.split('/').includes('..') ||
        !inside(name === 'zlibrary' ? '$BUILDROOT/zlibrary/src/zlibrary' : '$VENV', origin),
    )
  )
    return fail('foreign normalized import');
  if (
    proof.manifests?.files?.length !== 2 ||
    canonical(proof.manifests.files.map((f) => f.path)) !==
      canonical(['pyproject.toml', 'uv.lock']) ||
    proof.manifests.files.some((f) => !/^[a-f0-9]{64}$/.test(f.sha256 ?? '')) ||
    proof.manifests?.sha256 !== manifestDigest(proof.manifests?.files ?? []) ||
    canonical(m.manifests) !== canonical(proof.manifests) ||
    !['pyproject.toml', 'uv.lock'].every((n) =>
      proof.manifests.files.some(
        (f) =>
          f.path === n &&
          build?.artifactProof?.inputs?.files?.some((b) => b.path === n && b.sha256 === f.sha256),
      ),
    )
  )
    return fail('manifest/build binding mismatch');
  return [];
}
