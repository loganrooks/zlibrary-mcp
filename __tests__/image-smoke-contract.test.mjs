import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, readFile, writeFile, readdir, rm, chmod, open } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

test('container canary records exactly one blocked attempt before reset', async () => {
  const state = await mkdtemp(path.join(tmpdir(), 'image-canary-'));
  try {
    const trap = path.join(state, 'trap.txt');
    await run(path.join(root, '.venv/bin/python'), ['__tests__/image-smoke/egress-canary.py'], {
      cwd: root,
      env: {
        PATH: process.env.PATH,
        PYTHONDONTWRITEBYTECODE: '1',
        PYTHONPATH: path.join(root, '__tests__/rehearsal'),
        REHEARSAL_ALLOWED_PORT: '1',
        REHEARSAL_EGRESS_TRAP: trap,
      },
    });
    assert.equal(await readFile(trap, 'utf8'), 'blocked outbound attempt\n');
  } finally {
    await rm(state, { recursive: true, force: true });
  }
});

test('canary rejects a connect that succeeds without touching the network', async () => {
  const result = await run(
    path.join(root, '.venv/bin/python'),
    [
      '-c',
      'import runpy,socket; socket.create_connection=lambda *a,**kw:None; runpy.run_path("__tests__/image-smoke/egress-canary.py",run_name="__main__")',
    ],
    { cwd: root, env: { PATH: process.env.PATH, PYTHONDONTWRITEBYTECODE: '1' } },
  ).catch((e) => e);
  assert.equal(result.code, 1);
  assert.match(result.stderr, /canary connection must be blocked by the rehearsal fence/);
});

test('context helper packs once or reuses exact supplied tarball bytes', async () => {
  const state = await mkdtemp(path.join(tmpdir(), 'image-context-'));
  try {
    const tarball = path.join(state, 'candidate with spaces.tgz');
    await writeFile(tarball, 'fixed candidate bytes');
    const context = path.join(state, 'context with spaces');
    await run('bash', ['scripts/prepare-image-context.sh', context, tarball], { cwd: root });
    assert.deepEqual((await readdir(context)).sort(), ['package-lock.json', 'release.tgz']);
    assert.equal(
      await readFile(path.join(context, 'release.tgz'), 'utf8'),
      'fixed candidate bytes',
    );
    assert.equal(await readFile(tarball, 'utf8'), 'fixed candidate bytes', 'input is preserved');
    assert.deepEqual(
      await readFile(path.join(context, 'package-lock.json')),
      await readFile(path.join(root, 'package-lock.json')),
    );
    const second = await run('bash', ['scripts/prepare-image-context.sh', context, tarball], {
      cwd: root,
    }).catch((e) => e);
    assert.equal(second.code, 1, 'nonempty contexts must never be overwritten');

    const packed = path.join(state, 'packed');
    await run('bash', ['scripts/prepare-image-context.sh', packed], {
      cwd: root,
      env: { ...process.env, npm_config_cache: path.join(state, 'npm-cache') },
    });
    assert.deepEqual((await readdir(packed)).sort(), ['package-lock.json', 'release.tgz']);
    const { stdout } = await run('tar', ['tzf', path.join(packed, 'release.tgz')]);
    assert.match(stdout, /package\/dist\/index.js/);
    assert.match(stdout, /package\/lib\/python_bridge.py/);
  } finally {
    await rm(state, { recursive: true, force: true });
  }
});

test('committed schema baseline matches definitions and legacy tool argument fixture', async () => {
  const { assertToolSchemas } = await import('../scripts/image-smoke-checks.mjs');
  const { TOOL_DEFINITIONS } = await import('../dist/index.js');
  const baseline = JSON.parse(
    await readFile(path.join(root, '__tests__/rehearsal/tools-schemas.json')),
  );
  assertToolSchemas(TOOL_DEFINITIONS, baseline);
  assert.deepEqual(
    baseline.map((t) => ({
      name: t.name,
      arguments: Object.keys(t.inputSchema.properties).sort(),
    })),
    JSON.parse(await readFile(path.join(root, '__tests__/rehearsal/tools-surface.json'))),
  );
  for (const mutation of ['type', 'required', 'enum', 'output']) {
    const tools = structuredClone(TOOL_DEFINITIONS);
    const download = tools.find((t) => t.name === 'download');
    if (mutation === 'type') download.inputSchema.properties.ref.type = 'number';
    if (mutation === 'required') download.inputSchema.required = [];
    if (mutation === 'enum')
      tools.find((t) => t.name === 'get_limits').inputSchema.properties.mode.enum = ['local'];
    if (mutation === 'output') delete download.outputSchema;
    assert.throws(() => assertToolSchemas(tools, baseline), /public tool schemas/, mutation);
  }
});

test('missing canary evidence fails and successful evidence is reset for the journey', async () => {
  const { resetEgressCanary } = await import('../scripts/image-smoke-checks.mjs');
  const state = await mkdtemp(path.join(tmpdir(), 'image-canary-evidence-'));
  const trap = path.join(state, 'trap.txt');
  try {
    await assert.rejects(resetEgressCanary(trap), /canary must record exactly one blocked attempt/);
    await writeFile(trap, '');
    await assert.rejects(resetEgressCanary(trap), /canary must record exactly one blocked attempt/);
    await writeFile(trap, 'blocked outbound attempt\nblocked outbound attempt\n');
    await assert.rejects(resetEgressCanary(trap), /canary must record exactly one blocked attempt/);
    await writeFile(trap, 'blocked outbound attempt\n');
    await resetEgressCanary(trap);
    assert.equal(await readFile(trap, 'utf8'), '');
  } finally {
    await rm(state, { recursive: true, force: true });
  }
});

for (const scenario of [
  'healthy',
  'classic-store',
  'changed-tag',
  'empty-tags',
  'wrong-remote',
  'no-attestation',
]) {
  test(`publication digest and provenance control: ${scenario}`, async () => {
    const state = await mkdtemp(path.join(tmpdir(), 'image-publication-'));
    const digest = 'sha256:' + 'a'.repeat(64);
    const log = path.join(state, 'docker.log');
    try {
      const docker = path.join(state, 'docker');
      // Only the Docker boundary is doubled. The actual publication scripts
      // must validate all candidates before issuing their first push.
      await writeFile(
        docker,
        `#!/usr/bin/env node
const fs = require('node:fs');
const args = process.argv.slice(2);
fs.appendFileSync(${JSON.stringify(log)}, JSON.stringify(args) + '\\n');
const scenario = ${JSON.stringify(scenario)};
const descriptor = {mediaType:'application/vnd.oci.image.index.v1+json',digest:${JSON.stringify(digest)}};
if (scenario === 'classic-store' && args[0] === 'image') fs.writeSync(1, 'null');
else if (args.includes('{{json .Provenance}}')) {
  fs.writeSync(1, JSON.stringify(scenario === 'no-attestation' ? null : {SLSA:{buildType:'https://mobyproject.org/buildkit@v1'}}));
}
else if (args[0] === 'image' || args.includes('--format')) {
  if ((scenario === 'changed-tag' && args.at(-1) === 'example.invalid/release:latest') ||
      (scenario === 'wrong-remote' && args[0] === 'buildx')) descriptor.digest = 'sha256:' + 'b'.repeat(64);
  fs.writeSync(1, JSON.stringify(descriptor));
} else if (args[0] !== 'push') throw new Error('Unexpected Docker operation');
`,
      );
      await chmod(docker, 0o755);
      // File descriptors avoid this sandbox's blocked Node pipe initialization.
      const output = await open(path.join(state, 'output'), 'w+');
      const errors = await open(path.join(state, 'errors'), 'w+');
      let result;
      try {
        const child = spawn(
          process.execPath,
          ['scripts/push-tested-image.mjs', 'zlibrary-mcp:smoke', digest],
          {
            cwd: root,
            stdio: ['ignore', output.fd, errors.fd],
            env: {
              PATH: state + path.delimiter + process.env.PATH,
              IMAGE_TAGS:
                scenario === 'empty-tags'
                  ? ''
                  : 'example.invalid/release:1.4.0\nexample.invalid/release:latest\n',
            },
          },
        );
        const code = await new Promise((resolve, reject) => {
          child.once('error', reject);
          child.once('exit', resolve);
        });
        result = { code, stderr: await readFile(path.join(state, 'errors'), 'utf8') };
      } finally {
        await output.close();
        await errors.close();
      }
      assert.equal(result.code ?? 0, scenario === 'healthy' ? 0 : 1, result.stderr);
      const calls = (
        await readFile(log, 'utf8').catch((e) => {
          if (e.code === 'ENOENT') return '';
          throw e;
        })
      )
        .trim()
        .split('\n')
        .filter(Boolean)
        .map((s) => JSON.parse(s));
      const pushes = calls.filter((args) => args[0] === 'push');
      if (scenario === 'healthy') {
        assert.deepEqual(pushes, [
          ['push', 'example.invalid/release:1.4.0'],
          ['push', 'example.invalid/release:latest'],
        ]);
        const firstPush = calls.findIndex((args) => args[0] === 'push');
        assert.equal(calls.slice(0, firstPush).filter((args) => args[0] === 'image').length, 3);
      } else if (['classic-store', 'changed-tag', 'empty-tags'].includes(scenario)) {
        assert.deepEqual(pushes, [], 'reject before any registry write');
        assert.match(result.stderr, /attested image index|tested build digest|nonempty image tags/);
      } else {
        assert.equal(pushes.length, 1, 'stop on the first remote mismatch');
        assert.match(result.stderr, /tested build digest|provenance attestation/);
      }
    } finally {
      await rm(state, { recursive: true, force: true });
    }
  });
}
