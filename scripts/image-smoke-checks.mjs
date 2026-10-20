import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';

export function assertToolSchemas(tools, expected) {
  const schemas = tools
    .map(({ name, inputSchema, outputSchema }) => ({
      name,
      inputSchema,
      outputSchema,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
  assert.deepEqual(schemas, expected, 'public tool schemas match the committed fixture');
}

export async function resetEgressCanary(trapPath) {
  const trap = await readFile(trapPath, 'utf8').catch((error) => {
    if (error.code === 'ENOENT') return '';
    throw error;
  });
  assert.equal(
    trap,
    'blocked outbound attempt\n',
    'canary must record exactly one blocked attempt',
  );
  await writeFile(trapPath, '');
}
