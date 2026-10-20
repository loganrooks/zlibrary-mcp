#!/usr/bin/env node
/* global process, setTimeout, clearTimeout */
// Offline installed-package smoke. Dependency installation may use registries;
// the installed runtime is credential-free and fenced against provider egress.
import assert from 'node:assert/strict';
import { spawn, execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import { access, mkdtemp, mkdir, readFile, realpath, rm, stat, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const rehearsal = path.join(root, '__tests__/rehearsal');

export async function inspectInstalledPackage(directory) {
  const manifest = JSON.parse(await readFile(path.join(directory, 'package.json'), 'utf8'));
  const targets = Object.entries(
    typeof manifest.bin === 'string' ? { [manifest.name]: manifest.bin } : (manifest.bin ?? {}),
  ).map(([name, target]) => ({ owner: `bin:${name}`, target }));
  for (const [name, command] of Object.entries(manifest.scripts ?? {})) {
    // Build/test/prepare commands are documented source-checkout commands.
    if (!/^(doctor(?::.*)?|validate(?::.*)?|postbuild|audit:release|start)$/.test(name)) continue;
    const paths = command.match(/(?:scripts|dist)\/[^\s"';&|]+\.(?:m?js|py|sh)\b/g);
    assert(paths?.length, `Cannot inspect advertised command (${name}): ${command}`);
    targets.push(...paths.map((target) => ({ owner: name, target })));
  }
  for (const { owner, target } of targets) {
    const file = path.resolve(directory, target);
    assert(file.startsWith(directory + path.sep), `Target escapes installed package: ${target}`);
    assert(
      await stat(file).then(
        (s) => s.isFile(),
        () => false,
      ),
      `Advertised target missing (${owner}): ${target}`,
    );
  }
  assert(
    await stat(path.join(directory, 'lib/python_bridge.py')).then(
      (s) => s.isFile(),
      () => false,
    ),
    'Required packed asset missing: lib/python_bridge.py',
  );
  return { manifest, targets };
}

async function run(command, args, options = {}) {
  process.stdout.write(`> ${command} ${args.join(' ')}\n`);
  try {
    const result = await execute(command, args, {
      timeout: 180000,
      maxBuffer: 4 * 1024 * 1024,
      ...options,
    });
    process.stdout.write(result.stdout);
    process.stderr.write(result.stderr);
    return result.stdout;
  } catch (error) {
    process.stdout.write(error.stdout ?? '');
    process.stderr.write(error.stderr ?? '');
    throw error;
  }
}

async function protocolSmoke(bin, cwd, env, expected, version) {
  // Spawn the npm-created executable link itself, not node <source>/dist/index.js.
  await access(bin);
  const child = spawn(bin, [], { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
  const closed = once(child, 'close');
  // Attach handlers before any asynchronous work or failed spawn can surface.
  closed.catch(() => {});
  let stderr = '';
  let failure;
  let nextId = 0;
  let responses = 0;
  const pending = new Map();
  const fail = (error) => {
    failure ??= error;
    for (const request of pending.values()) request.reject(error);
    pending.clear();
  };
  child.stderr.on('data', (data) => {
    stderr += data;
  });
  child.once('error', fail);
  child.stdin.on('error', fail);
  child.once('close', (code, signal) => {
    if (pending.size)
      fail(new Error(`Installed bin exited during request (${code}/${signal}): ${stderr}`));
  });
  const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  lines.on('line', (line) => {
    try {
      const message = JSON.parse(line); // No grep/filter: even blank/log lines fail.
      assert.equal(message.jsonrpc, '2.0');
      assert(message.method || Object.hasOwn(message, 'id'), 'Invalid JSON-RPC envelope');
      if (Object.hasOwn(message, 'id')) {
        const request = pending.get(message.id);
        assert(request, `Unexpected response ID: ${message.id}`);
        assert(!message.error, JSON.stringify(message.error));
        assert(Object.hasOwn(message, 'result'), 'Response has no result');
        pending.delete(message.id);
        responses++;
        request.resolve(message.result);
      }
    } catch (error) {
      fail(error);
    }
  });
  async function request(method, params) {
    if (failure) throw failure;
    const id = ++nextId;
    let timer;
    try {
      return await new Promise((resolve, reject) => {
        pending.set(id, { resolve, reject });
        timer = setTimeout(
          () => fail(new Error(`Installed MCP request timed out: ${method}; ${stderr}`)),
          15000,
        );
        child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
      });
    } finally {
      clearTimeout(timer);
    }
  }
  try {
    const initialized = await request('initialize', {
      protocolVersion: '2025-11-25',
      capabilities: {},
      clientInfo: { name: 'packed-install-smoke', version: '1' },
    });
    assert.equal(initialized.serverInfo.name, 'book-acquisition');
    assert.equal(initialized.serverInfo.version, version);
    child.stdin.write(
      JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n',
    );
    const listed = await request('tools/list', {});
    const surface = listed.tools
      .map((tool) => ({
        name: tool.name,
        arguments: Object.keys(tool.inputSchema.properties ?? {}).sort(),
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
    assert.deepEqual(surface, expected, 'Installed tools differ from the 2.0 fixture');
    const limits = await request('tools/call', {
      name: 'get_limits',
      arguments: { mode: 'local' },
    });
    assert(!limits.isError, 'Local limits returned a tool error');
    const data = JSON.parse(limits.content[0].text);
    assert.deepEqual(data, limits.structuredContent);
    assert.equal(data.sources.libgen.download_available, true);
    assert.equal(data.sources.zlibrary.configured, false);
    process.stdout.write(
      `Installed bin: initialize, tools/list (${surface.length} tools), get_limits local passed.\n`,
    );
  } finally {
    child.stdin.end();
    const kill = setTimeout(() => child.kill('SIGTERM'), 1000);
    const force = setTimeout(() => child.kill('SIGKILL'), 3000);
    try {
      const [code, signal] = await closed;
      assert.equal(signal, null, `Installed bin needed forced cleanup: ${stderr}`);
      assert.equal(code, 0, `Installed bin exited nonzero: ${stderr}`);
    } finally {
      clearTimeout(kill);
      clearTimeout(force);
      lines.close();
    }
  }
  if (failure) throw failure;
  assert.equal(responses, 3);
}

export async function main(args = process.argv.slice(2)) {
  assert(
    args.includes('--offline-providers'),
    'Required: --offline-providers (live providers are not supported)',
  );
  const control = args.find((arg) => arg.startsWith('--control='))?.split('=')[1];
  assert(
    !control || ['missing-bridge', 'missing-script'].includes(control),
    'Unknown failure control',
  );
  assert(
    args.every((arg) => arg === '--offline-providers' || arg === `--control=${control}`),
    'Unknown argument',
  );
  // macOS exposes /var via /private/var; ESM resolves the physical path.
  const temporary = await realpath(await mkdtemp(path.join(tmpdir(), 'zlib-packed-')));
  try {
    const home = path.join(temporary, 'home');
    const prefix = path.join(temporary, 'prefix');
    await mkdir(home);
    await mkdir(prefix);
    // Do not inherit credentials, source defaults, Python paths, Node preloads,
    // user npm config, or account/session state from the operator's environment.
    const env = {
      PATH: `${path.dirname(process.execPath)}${path.delimiter}${process.env.PATH}`,
      HOME: home,
      TMPDIR: temporary,
      XDG_CONFIG_HOME: home,
      XDG_CACHE_HOME: home,
      XDG_STATE_HOME: home,
      HUSKY: '0',
      npm_config_cache: path.join(temporary, 'npm-cache'),
      npm_config_userconfig: path.join(temporary, 'npmrc'),
      npm_config_globalconfig: path.join(temporary, 'global-npmrc'),
      UV_CACHE_DIR: path.join(temporary, 'uv-cache'),
      UV_PYTHON_INSTALL_DIR: path.join(temporary, 'python'),
      PYTHONDONTWRITEBYTECODE: '1',
    };
    const packed = JSON.parse(
      await run('npm', ['pack', '--ignore-scripts', '--json', '--pack-destination', temporary], {
        cwd: root,
        env,
      }),
    );
    assert.equal(packed.length, 1, 'Expected exactly one packed artifact');
    const tarball = path.join(temporary, packed[0].filename);
    if (control) {
      const scratch = path.join(temporary, 'damaged');
      await mkdir(scratch);
      await run('tar', ['xzf', tarball, '-C', scratch], { env });
      const omitted =
        control === 'missing-bridge' ? 'lib/python_bridge.py' : 'scripts/check_upstream.py';
      await rm(path.join(scratch, 'package', omitted));
      await run('tar', ['czf', tarball, '-C', scratch, 'package'], { env });
      process.stdout.write(
        `Failure control: removed ${omitted} from the tarball before install.\n`,
      );
    }
    process.stdout.write(
      `Tarball SHA-256: ${createHash('sha256')
        .update(await readFile(tarball))
        .digest('hex')}\n`,
    );
    await run(
      'npm',
      [
        'install',
        '--prefix',
        prefix,
        '--ignore-scripts',
        '--no-audit',
        '--no-fund',
        '--package-lock=false',
        tarball,
      ],
      { cwd: prefix, env },
    );
    const installed = path.join(prefix, 'node_modules/zlibrary-mcp');
    const { manifest, targets } = await inspectInstalledPackage(installed);
    process.stdout.write(`Installed target checks: ${JSON.stringify(targets)}\n`);
    // README Quick Start, with --no-dev: no test/processing extras or hand-added deps.
    await run('bash', ['setup-uv.sh', '--no-dev'], { cwd: installed, env });
    const python = path.join(installed, '.venv/bin/python');
    const trap = path.join(temporary, 'egress.txt');
    const runtime = {
      ...env,
      PYTHONPATH: rehearsal,
      NODE_OPTIONS: `--import=${path.join(rehearsal, 'node-isolation.mjs')}`,
      REHEARSAL_EGRESS_TRAP: trap,
      REHEARSAL_LOG_DIR: path.join(home, 'logs'),
      ZLIBRARY_SESSION_DIR: path.join(home, 'sessions'),
      LOG_LEVEL: 'info',
    };
    await mkdir(runtime.REHEARSAL_LOG_DIR);
    // Fail if either startup fence did not load: both attempts must be blocked
    // and counted. No allowed fake port => all IP/TCP destinations are refused.
    await writeFile(trap, '');
    await run(
      process.execPath,
      [
        '--input-type=module',
        '-e',
        "import net from 'node:net'; try { net.connect(443, '192.0.2.1'); process.exitCode=1; } catch (e) { if (!e.message.includes('rehearsal blocks')) throw e; }",
      ],
      { cwd: home, env: runtime },
    );
    await run(
      python,
      [
        '-c',
        "import socket\ntry:\n socket.create_connection(('192.0.2.1', 443))\n raise AssertionError('Python fence not loaded')\nexcept RuntimeError as e:\n assert 'rehearsal blocked' in str(e)\n",
      ],
      { cwd: home, env: runtime },
    );
    assert.equal(
      (await readFile(trap, 'utf8')).trim().split('\n').length,
      2,
      'Both network fences must fire',
    );
    await writeFile(trap, '');
    await run(
      python,
      [
        '-c',
        "import importlib.util, pathlib, sys, zlibrary\nroot = pathlib.Path(sys.argv[1]).resolve()\nassert root in pathlib.Path(zlibrary.__file__).resolve().parents\nassert importlib.util.find_spec('pytest') is None\nsys.path.insert(0, str(root / 'lib'))\nimport python_bridge\nassert pathlib.Path(python_bridge.__file__).resolve() == root / 'lib/python_bridge.py'\nprint('Installed core-only Python bridge imports passed')",
        installed,
      ],
      { cwd: home, env: runtime },
    );
    await run(
      process.execPath,
      [
        '--input-type=module',
        '-e',
        "import { pathToFileURL } from 'node:url'; import assert from 'node:assert/strict'; const root = process.argv[1]; const paths = await import(pathToFileURL(root + '/dist/lib/paths.js')); const venv = await import(pathToFileURL(root + '/dist/lib/venv-manager.js')); assert.equal(paths.getPythonScriptPath('python_bridge.py'), root + '/lib/python_bridge.py'); assert.equal(await venv.getManagedPythonPath(), root + '/.venv/bin/python');",
        installed,
      ],
      { cwd: home, env: runtime },
    );
    await run('npm', ['run', 'validate'], { cwd: installed, env: runtime });
    const bin = path.join(prefix, 'node_modules/.bin/zlibrary-mcp');
    assert.equal(await realpath(bin), path.join(installed, manifest.bin['zlibrary-mcp']));
    const expected = JSON.parse(
      await readFile(path.join(root, '__tests__/fixtures/tools-surface-v2.json'), 'utf8'),
    );
    await protocolSmoke(bin, home, runtime, expected, manifest.version);
    assert.equal(await readFile(trap, 'utf8'), '', 'Installed runtime attempted provider egress');
    process.stdout.write(
      'PASS: exact packed package installed clean; offline runtime had zero egress attempts.\n',
    );
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    process.stderr.write(`Packed artifact check failed: ${error.message}\n`);
    process.exitCode = 1;
  });
}
