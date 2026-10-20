#!/usr/bin/env node
// Run last, after the tested image has been pushed and checked in GHCR.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

const run = promisify(execFile);

async function main(args) {
  assert.equal(args.length, 1, 'expected exactly one release tarball');
  const tarball = path.resolve(args[0]);
  const integrity = `sha512-${createHash('sha512')
    .update(await readFile(tarball))
    .digest('base64')}`;
  const { stdout: metadata } = await run('tar', ['-xOf', tarball, 'package/package.json']);
  const { name, version } = JSON.parse(metadata);
  assert.equal(name, 'zlibrary-mcp', 'expected the release package');
  assert.match(
    version,
    /^\d+\.\d+\.\d+(?:-[\da-zA-Z.-]+)?(?:\+[\da-zA-Z.-]+)?$/,
    'expected an exact release version',
  );
  const spec = `${name}@${version}`;
  let published;
  try {
    const { stdout } = await run('npm', ['view', spec, 'dist.integrity', '--json']);
    published = JSON.parse(stdout);
    assert.equal(
      published,
      integrity,
      `${spec} already exists with different or missing integrity`,
    );
  } catch (error) {
    // Only an explicit registry E404 permits publication. Auth/network/parse
    // failures and an existing version with other bytes must fail closed.
    let code;
    try {
      code = JSON.parse(error.stdout).error?.code;
    } catch {
      // Preserve the original error below.
    }
    if (code !== 'E404') {
      if (code) throw new Error(`npm registry lookup failed (${code})`, { cause: error });
      throw error;
    }
  }
  if (published === integrity) {
    process.stdout.write(
      `${spec} already has the release tarball integrity; skipping npm publish.\n`,
    );
    return;
  }
  const result = await run('npm', ['publish', tarball, '--provenance'], {
    timeout: 300000,
    maxBuffer: 8 * 1024 * 1024,
  });
  process.stdout.write(result.stdout);
  process.stderr.write(result.stderr);
}

main(process.argv.slice(2)).catch((error) => {
  process.stderr.write(`npm publication failed: ${error.message}\n`);
  process.exitCode = 1;
});
