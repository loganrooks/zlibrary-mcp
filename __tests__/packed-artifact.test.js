import { test, expect } from '@jest/globals';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
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
