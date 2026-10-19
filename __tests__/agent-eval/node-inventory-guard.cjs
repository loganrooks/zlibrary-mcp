// Isolated npm subprocess only. Deny before content opens; never log contents.
'use strict';
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const { fileURLToPath } = require('node:url');
const originalAppend = fs.appendFileSync.bind(fs);
const originalRealpath = fs.realpathSync.bind(fs);
const policy = JSON.parse(process.env.EVAL_NODE_READ_POLICY);
const inside = (root, name) => name === root || name.startsWith(root + path.sep);
let count = 0;
const trace = (operation, name, allowed) => {
  if (++count > 40000) throw new Error('inventory read trace bound exceeded');
  originalAppend(policy.trace, JSON.stringify({ operation, path: name, allowed }) + '\n');
};
const check = (value, operation) => {
  if (typeof value === 'number') {
    trace('unsupported-fd-read', '[fd]', false);
    throw new Error('unclassified inventory fd read');
  }
  const name = path.resolve(
    value instanceof URL ? fileURLToPath(value) : Buffer.isBuffer(value) ? value.toString() : value,
  );
  let actual;
  try {
    actual = originalRealpath(name);
  } catch {
    actual = name;
  }
  const owned = inside(policy.scratch, name) && inside(policy.scratch, actual);
  const forbidden =
    /(?:^|[\\/])(?:\.?npmrc|\.env(?:\.[^\\/]*)?|\.netrc|credentials?(?:\.[^\\/]*)?|id_(?:rsa|dsa|ed25519)(?:\.[^\\/]*)?|.*\.(?:pem|key|p12|pfx))$/i.test(
      name,
    );
  const metadata =
    (inside(policy.install, actual) || (inside(policy.viewInstall, name) && actual === name)) &&
    ['package.json', '.package-lock.json'].includes(path.basename(name));
  const tool =
    inside(policy.npmRoot, actual) &&
    !forbidden &&
    !actual
      .split(path.sep)
      .some((p) => /^(?:tests?|__tests__|fixtures?|examples?|docs?)$/.test(p)) &&
    /\.(?:js|mjs|cjs|json|node|wasm)$/.test(actual);
  const manifest = policy.manifests.includes(actual);
  const allowed = (owned || metadata || tool || manifest) && (!forbidden || owned);
  trace(operation, name, allowed);
  if (!allowed) throw Object.assign(new Error('inventory content read denied'), { code: 'ENOENT' });
};
for (const name of ['readFileSync', 'readFile', 'openSync', 'open', 'createReadStream']) {
  const original = fs[name];
  fs[name] = function (file, ...args) {
    check(file, name);
    return original.call(this, file, ...args);
  };
}
for (const name of ['readFile', 'open']) {
  const original = fsp[name];
  fsp[name] = async function (file, ...args) {
    check(file, 'promises.' + name);
    return original.call(this, file, ...args);
  };
}
require('node:module').syncBuiltinESMExports();
// No lifecycle/network fallback, even if npm's offline policy regresses.
for (const module of ['node:child_process']) {
  const cp = require(module);
  for (const name of ['spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync', 'fork'])
    cp[name] = () => {
      trace('child-process', '[blocked]', false);
      throw new Error('inventory child process forbidden');
    };
}
const denyNetwork = () => {
  trace('network', '[blocked]', false);
  throw new Error('inventory network forbidden');
};
require('node:net').Socket.prototype.connect = denyNetwork;
require('node:tls').connect = denyNetwork;
require('node:dns').lookup = denyNetwork;
require('node:dgram').createSocket = denyNetwork;
const workers = require('node:worker_threads');
workers.Worker = class {
  constructor() {
    trace('child-process', '[worker-blocked]', false);
    throw new Error('inventory worker forbidden');
  }
};
// Metadata-operation failures are locators/codes only, never file contents.
for (const name of ['stat', 'lstat', 'readdir', 'realpath']) {
  const original = fsp[name];
  fsp[name] = async function (file, ...args) {
    try {
      return await original.call(this, file, ...args);
    } catch (error) {
      trace('metadata.' + name + ':' + (error.code ?? 'unknown'), String(file), false);
      throw error;
    }
  };
}
// npm is inventory-only: target-install writes are never allowed. Cache/log writes
// may occur only in the owned scratch root. This remains API instrumentation.
const writable = (value) => {
  const name = path.resolve(
    value instanceof URL ? fileURLToPath(value) : Buffer.isBuffer(value) ? value.toString() : value,
  );
  let actual;
  try {
    actual = originalRealpath(name);
  } catch {
    actual = path.join(originalRealpath(path.dirname(name)), path.basename(name));
  }
  if (!inside(policy.scratch, name) || !inside(policy.scratch, actual)) {
    trace('write-denied', name, false);
    throw new Error('inventory writes outside scratch forbidden');
  }
};
for (const name of [
  'writeFileSync',
  'writeFile',
  'appendFileSync',
  'appendFile',
  'mkdirSync',
  'mkdir',
  'rmSync',
  'rm',
  'unlinkSync',
  'unlink',
  'rmdirSync',
  'rmdir',
  'truncateSync',
  'truncate',
  'chmodSync',
  'chmod',
  'createWriteStream',
]) {
  const original = fs[name];
  if (original)
    fs[name] = function (file, ...args) {
      writable(file);
      return original.call(this, file, ...args);
    };
}
for (const name of [
  'writeFile',
  'appendFile',
  'mkdir',
  'rm',
  'unlink',
  'rmdir',
  'truncate',
  'chmod',
]) {
  const original = fsp[name];
  if (original)
    fsp[name] = async function (file, ...args) {
      writable(file);
      return original.call(this, file, ...args);
    };
}
for (const name of ['openSync', 'open']) {
  const original = fs[name];
  fs[name] = function (file, flags, ...args) {
    if (
      typeof flags === 'number'
        ? flags !== fs.constants.O_RDONLY
        : !['r', 'rs', 'sr'].includes(flags ?? 'r')
    )
      writable(file);
    return original.call(this, file, flags, ...args);
  };
}
{
  const original = fsp.open;
  fsp.open = async function (file, flags, ...args) {
    if (
      typeof flags === 'number'
        ? flags !== fs.constants.O_RDONLY
        : !['r', 'rs', 'sr'].includes(flags ?? 'r')
    )
      writable(file);
    return original.call(this, file, flags, ...args);
  };
}
require('node:module').syncBuiltinESMExports();

// Unsupported raw fd reads fail closed; the observed inventory uses path APIs.
for (const name of ['read', 'readSync', 'readv', 'readvSync'])
  fs[name] = () => {
    trace('unsupported-fd-read', '[fd]', false);
    throw new Error('unsupported raw inventory fd read');
  };
for (const name of [
  'renameSync',
  'rename',
  'copyFileSync',
  'copyFile',
  'linkSync',
  'link',
  'symlinkSync',
  'symlink',
]) {
  const original = fs[name];
  if (original)
    fs[name] = function (from, to, ...args) {
      writable(from);
      writable(to);
      return original.call(this, from, to, ...args);
    };
}
for (const name of ['rename', 'copyFile', 'link', 'symlink']) {
  const original = fsp[name];
  if (original)
    fsp[name] = async function (from, to, ...args) {
      writable(from);
      writable(to);
      return original.call(this, from, to, ...args);
    };
}
require('node:module').syncBuiltinESMExports();
