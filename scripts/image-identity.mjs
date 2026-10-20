#!/usr/bin/env node
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const indexTypes = new Set([
  'application/vnd.oci.image.index.v1+json',
  'application/vnd.docker.distribution.manifest.list.v2+json',
]);

export async function assertImageIdentity(image, digest) {
  assert.match(digest ?? '', /^sha256:[a-f0-9]{64}$/, 'expected tested build digest');
  assert(image && !image.startsWith('-'), 'expected a local image reference');
  const { stdout } = await run(
    'docker',
    ['image', 'inspect', '--format', '{{json .Descriptor}}', image],
    { timeout: 10000 },
  );
  const descriptor = JSON.parse(stdout);
  assert(indexTypes.has(descriptor?.mediaType), 'containerd must retain the attested image index');
  assert.equal(descriptor.digest, digest, `${image} must match the tested build digest`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  assertImageIdentity(process.argv[2], process.argv[3]).catch((error) => {
    process.stderr.write(`Image identity failed: ${error.message}\n`);
    process.exitCode = 1;
  });
}
