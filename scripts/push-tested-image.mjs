#!/usr/bin/env node
// Publication only: run after image-identity, image-smoke and npm publication.
// Never rebuild or pass --platform (which would drop the attestation index).
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { assertImageIdentity } from './image-identity.mjs';

const run = promisify(execFile);

async function main(image, digest) {
  const tags = (process.env.IMAGE_TAGS ?? '')
    .split('\n')
    .map((t) => t.trim())
    .filter(Boolean);
  assert(tags.length > 0 && tags.every((t) => !t.startsWith('-')), 'expected nonempty image tags');
  // Validate EVERY local tag before the first write to a registry.
  await assertImageIdentity(image, digest);
  for (const tag of tags) await assertImageIdentity(tag, digest);
  for (const tag of tags) {
    const result = await run('docker', ['push', tag], {
      timeout: 300000,
      maxBuffer: 8 * 1024 * 1024,
    });
    process.stdout.write(result.stdout);
    process.stderr.write(result.stderr);
    const { stdout } = await run(
      'docker',
      ['buildx', 'imagetools', 'inspect', '--format', '{{json .Manifest}}', tag],
      { timeout: 30000 },
    );
    assert.equal(JSON.parse(stdout).digest, digest, 'registry must retain the tested build digest');
    const { stdout: provenance } = await run(
      'docker',
      ['buildx', 'imagetools', 'inspect', '--format', '{{json .Provenance}}', tag],
      { timeout: 30000 },
    );
    assert(
      Object.keys(JSON.parse(provenance)?.SLSA ?? {}).length > 0,
      'registry must retain the BuildKit provenance attestation',
    );
  }
}

main(process.argv[2], process.argv[3]).catch((error) => {
  process.stderr.write(`Image publication failed: ${error.message}\n`);
  process.exitCode = 1;
});
