// The executing evaluator, not the selected production checkout, owns this identity.
import { createHash } from 'node:crypto';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gitRead, manifestDigest } from './build-proof.js';
export const evaluatorRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const scopes = ['__tests__/agent-eval', '__tests__/rehearsal', 'package.json', 'package-lock.json'];
export const canonical = (value) =>
  JSON.stringify(value, (_key, item) =>
    item && typeof item === 'object' && !Array.isArray(item)
      ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b)))
      : item,
  );
export const digest = (value) =>
  createHash('sha256')
    .update(typeof value === 'string' || Buffer.isBuffer(value) ? value : canonical(value))
    .digest('hex');
// Only generated CPython cache files are excluded, never a whole cache directory.
const generated = (name) =>
  /(?:^|\/)__pycache__\/[^/]+\.cpython-\d+(?:\.opt-\d+)?\.pyc$/.test(name);
export async function verifyEvaluatorIdentity({
  root = evaluatorRoot,
  gitRead: readGit = gitRead,
} = {}) {
  root = await realpath(root);
  const head = readGit(root, 'rev-parse', 'HEAD');
  if (!/^[a-f0-9]{40}$/.test(head)) throw new Error('evaluator HEAD missing');
  const tracked = new Map();
  for (const entry of readGit(root, 'ls-tree', '-rz', head, '--', ...scopes)
    .split('\0')
    .filter(Boolean)) {
    const match = /^(100644|100755) blob ([a-f0-9]{40})\t(.+)$/.exec(entry);
    if (!match) throw new Error('evaluator source symlink or unsupported tracked entry');
    if (!generated(match[3])) tracked.set(match[3], match[2]);
  }
  const files = [];
  const visit = async (name) => {
    const file = path.join(root, name),
      stat = await lstat(file);
    if (stat.isSymbolicLink()) throw new Error('evaluator source symlink: ' + name);
    if (stat.isDirectory()) {
      for (const child of (await readdir(file)).sort()) await visit(name + '/' + child);
      return;
    }
    if (generated(name)) return;
    if (!stat.isFile() || !tracked.has(name))
      throw new Error('untracked evaluator source: ' + name);
    const bytes = await readFile(file),
      blob = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
    if (blob !== tracked.get(name)) throw new Error('dirty evaluator source bytes: ' + name);
    files.push({ path: name, sha256: digest(bytes) });
    tracked.delete(name);
  };
  for (const scope of scopes) await visit(scope);
  if (tracked.size) throw new Error('missing tracked evaluator source');
  files.sort((a, b) => a.path.localeCompare(b.path));
  if (readGit(root, 'rev-parse', 'HEAD') !== head)
    throw new Error('evaluator HEAD changed during identity check');
  const proof = {
    version: 1,
    status: 'verified',
    clean: true,
    root,
    head,
    files,
    sha256: manifestDigest(files),
  };
  const errors = evaluatorProofErrors(proof);
  if (errors.length) throw new Error(errors.join('; '));
  return proof;
}
export function evaluatorProofErrors(proof) {
  const files = proof?.files,
    hash = /^[a-f0-9]{64}$/;
  if (
    proof?.version !== 1 ||
    proof?.status !== 'verified' ||
    proof?.clean !== true ||
    !path.isAbsolute(proof?.root ?? '') ||
    !/^[a-f0-9]{40}$/.test(proof?.head ?? '') ||
    !Array.isArray(files) ||
    !files.length
  )
    return ['missing/unverified evaluator source identity'];
  const names = files.map((f) => f.path);
  if (
    new Set(names).size !== names.length ||
    names.join('\0') !== [...names].sort((a, b) => a.localeCompare(b)).join('\0') ||
    files.some(
      (f) =>
        !hash.test(f.sha256 ?? '') ||
        typeof f.path !== 'string' ||
        !scopes.some((s) => f.path === s || f.path.startsWith(s + '/')) ||
        f.path.split('/').some((p) => !p || p === '.' || p === '..') ||
        f.path.includes('\\'),
    ) ||
    ![
      'package.json',
      'package-lock.json',
      '__tests__/agent-eval/run.mjs',
      '__tests__/agent-eval/oracles.js',
      '__tests__/rehearsal/harness.js',
      '__tests__/rehearsal/fake_catalogue.py',
    ].every((n) => names.includes(n)) ||
    manifestDigest(files) !== proof.sha256
  )
    return ['inconsistent evaluator source manifest'];
  return [];
}
