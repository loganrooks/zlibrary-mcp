import { test, expect } from '@jest/globals';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';

// Catch skipped preservation checks, same-size corruption and deleted sidecars.
async function seeded(run) {
  const directory = await mkdtemp(path.join(tmpdir(), 'upgrade-preservation-'));
  try {
    await mkdir(path.join(directory, 'nested'));
    await writeFile(path.join(directory, 'book.txt'), 'original');
    await writeFile(path.join(directory, 'nested', 'state.json'), '{"original":true}\n');
    await run(directory);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test('upgrade preservation allows new files but retains all original bytes', async () => {
  const { snapshotState, assertPreserved } = await import('../scripts/check-install-upgrades.mjs');
  await seeded(async directory => {
    const before = await snapshotState(directory);
    await writeFile(path.join(directory, 'new.acq.json'), '{}');
    await expect(assertPreserved(directory, before)).resolves.toBeUndefined();
  });
});

test.each(['delete-output', 'rewrite-output', 'delete-state'])(
  'upgrade preservation catches the real %s mutation', async control => {
    const { snapshotState, assertPreserved, mutatePreservedState } = await import('../scripts/check-install-upgrades.mjs');
    await seeded(async directory => {
      const before = await snapshotState(directory);
      await mutatePreservedState(control, directory, 'book.txt', 'nested/state.json');
      await expect(assertPreserved(directory, before)).rejects.toThrow(/Existing (file missing|bytes changed)/);
    });
  },
);
