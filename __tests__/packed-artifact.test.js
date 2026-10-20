import { test, expect } from '@jest/globals';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { inspectInstalledPackage } from '../scripts/check-packed-artifact.mjs';

// These controls catch omitted runtime assets, not just an allowlist typo.
async function layout(omit, run) {
  const root = await mkdtemp(path.join(tmpdir(), 'packed-layout-'));
  try {
    const manifest = {
      bin: { 'zlibrary-mcp': 'dist/index.js' },
      scripts: {
        doctor: 'uv run --no-dev python scripts/check_upstream.py && node scripts/release-audit.mjs',
        validate: 'node scripts/validate-python-bridge.js',
        // Contributor commands deliberately need an unpacked source checkout.
        test: 'node __tests__/rehearsal/run.mjs',
      },
    };
    for (const file of [
      'lib/python_bridge.py', 'dist/index.js', 'scripts/check_upstream.py',
      'scripts/release-audit.mjs', 'scripts/validate-python-bridge.js',
    ]) {
      if (file === omit) continue;
      await mkdir(path.dirname(path.join(root, file)), { recursive: true });
      await writeFile(path.join(root, file), 'fixture');
    }
    await writeFile(path.join(root, 'package.json'), JSON.stringify(manifest));
    await run(root);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
}

test.each([
  ['lib/python_bridge.py', 'Required packed asset missing: lib/python_bridge.py'],
  ['scripts/check_upstream.py', 'Advertised target missing (doctor): scripts/check_upstream.py'],
  ['scripts/release-audit.mjs', 'Advertised target missing (doctor): scripts/release-audit.mjs'],
  ['scripts/validate-python-bridge.js', 'Advertised target missing (validate): scripts/validate-python-bridge.js'],
  ['dist/index.js', 'Advertised target missing (bin:zlibrary-mcp): dist/index.js'],
])('refuses an installed package missing %s', async (file, message) => {
  await layout(file, async root => {
    await expect(inspectInstalledPackage(root)).rejects.toThrow(message);
  });
});

test('checks all installed runtime targets without requiring contributor-only tests', async () => {
  await layout(undefined, async root => {
    const inspected = await inspectInstalledPackage(root);
    expect(inspected.targets).toEqual(expect.arrayContaining([
      { owner: 'doctor', target: 'scripts/check_upstream.py' },
      { owner: 'doctor', target: 'scripts/release-audit.mjs' },
      { owner: 'validate', target: 'scripts/validate-python-bridge.js' },
    ]));
  });
});

// npm 10 can print a prepare diagnostic before its JSON despite --ignore-scripts.
// A real child emits the noisy output and materializes a tarball; no registry used.
test('pack discovery tolerates non-JSON npm stdout and requests scripts disabled in env', async () => {
  const { packArtifact } = await import('../scripts/check-packed-artifact.mjs');
  const { chmod } = await import('node:fs/promises');
  const root = await mkdtemp(path.join(tmpdir(), 'packed-noisy-npm-'));
  try {
    const bin = path.join(root, 'bin');
    const destination = path.join(root, 'artifacts');
    await mkdir(bin);
    await mkdir(destination);
    const npm = path.join(bin, 'npm');
    await writeFile(npm, `#!${process.execPath}\nimport fs from 'node:fs';\nimport path from 'node:path';\nconst dest = process.argv[process.argv.indexOf('--pack-destination') + 1];\nif (process.env.npm_config_ignore_scripts !== 'true') process.exit(23);\nfs.writeFileSync(path.join(dest, 'fixture.tgz'), 'packed');\nprocess.stdout.write('HUSKY=0 skip install[{"filename":"fixture.tgz"}]\\n');\n`);
    await chmod(npm, 0o755);
    expect(await packArtifact(destination, { PATH: `${bin}${path.delimiter}${process.env.PATH}` }))
      .toBe(path.join(destination, 'fixture.tgz'));
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

// A failed body transfer must not turn search/detail success into acquisition success.
test('fake dropped-transfer mode preserves search but serves no LibGen bytes', async () => {
  const { Rehearsal } = await import('./rehearsal/harness.js');
  const https = await import('node:https');
  const h = await Rehearsal.start('packed-drop-control');
  try {
    const mode = await h.request('/__mode', { mode: 'drop_transfer' }, true);
    expect(mode.status).toBe(200);
    const fetch = route => new Promise((resolve, reject) => {
      const req = https.get(h.origin + route, { agent: h.agent }, res => {
        const chunks = [];
        res.on('data', chunk => chunks.push(chunk));
        res.on('end', () => resolve({ status: res.statusCode, bytes: Buffer.concat(chunks) }));
      });
      req.on('error', reject);
      req.setTimeout(3000, () => req.destroy(new Error('fake response timeout')));
    });
    const search = await fetch('/libgen/index.php?req=Persuasion');
    expect(search.status).toBe(200);
    expect(search.bytes.toString()).toContain('Persuasion');
    // MD5 of the fixed synthetic Persuasion bytes, computed independently here.
    const { createHash } = await import('node:crypto');
    const bytes = Buffer.concat([Buffer.from([0x50, 0x4b, 3, 4]), Buffer.from('Synthetic fixture 301\n'.repeat(60))]);
    const md5 = createHash('md5').update(bytes).digest('hex');
    const transfer = await fetch(`/libgen/get.php?md5=${md5}&key=fixture`);
    expect(transfer.status).toBe(503);
    expect(transfer.bytes.length).toBe(0);
  } finally {
    await h.close();
  }
});

test('shared LibGen seam routes httpx resolver and streamed bytes to the HTTPS fake', async () => {
  const { Rehearsal } = await import('./rehearsal/harness.js');
  const { execFileSync } = await import('node:child_process');
  const h = await Rehearsal.start('packed-httpx-control');
  try {
    const trap = path.join(h.temp, 'egress.txt');
    await writeFile(trap, '');
    const result = execFileSync(path.resolve('.venv/bin/python'), ['-c', `
import asyncio, httpx
async def main():
 async with httpx.AsyncClient() as client:
  response = await client.get('https://libgen.li/ads.php?md5=0123456789abcdef0123456789abcdef')
  assert response.status_code == 200 and 'GET' in response.text
  async with client.stream('GET', 'https://libgen.li/get.php?md5=0123456789abcdef0123456789abcdef&key=fixture') as response:
   chunks = [chunk async for chunk in response.aiter_bytes()]
   assert response.status_code == 200 and len(b''.join(chunks)) > 0
asyncio.run(main())
print('httpx resolver reached fixture')
`], { encoding: 'utf8', timeout: 5000, env: {
      PATH: process.env.PATH,
      ...h.providerEnvironment({ libgen: true, credentials: false }),
      REHEARSAL_EGRESS_TRAP: trap,
    } });
    expect(result).toContain('httpx resolver reached fixture');
    expect(await readFile(trap, 'utf8')).toBe('');
    expect((await h.stats()).calls['/libgen/ads.php']).toBe(1);
    expect((await h.stats()).calls['/libgen/get.php']).toBe(1);
  } finally {
    await h.close();
  }
});
