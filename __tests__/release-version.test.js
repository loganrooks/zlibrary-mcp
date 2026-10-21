import { readFileSync } from 'node:fs';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { createServer } from '../dist/index.js';

const read = (file) => readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
const pkg = JSON.parse(read('package.json'));
const lock = JSON.parse(read('package-lock.json'));
const project = read('pyproject.toml').match(/^\[project\]\s*\n([\s\S]*?)(?=^\[|$(?![\s\S]))/m)?.[1];
const pythonVersion = project?.match(/^version\s*=\s*"([^"]+)"\s*$/m)?.[1];

// Catch partial release bumps: npm, its root lock entry, Python and MCP must agree.
test('release manifests agree on the package version', () => {
  expect(pkg.version).toMatch(/^\d+\.\d+\.\d+(?:-[\w.-]+)?$/);
  expect(lock.version).toBe(pkg.version);
  expect(lock.packages[''].version).toBe(pkg.version);
  expect(pythonVersion).toBe(pkg.version);
});

test('MCP initialization advertises the package release version', async () => {
  const server = createServer();
  const client = new Client({ name: 'release-version-check', version: '1' });
  const [a, b] = InMemoryTransport.createLinkedPair();
  try {
    await Promise.all([server.connect(b), client.connect(a)]);
    expect(client.getServerVersion()).toEqual({
      name: 'book-acquisition',
      version: pkg.version,
    });
  } finally {
    await client.close();
    await server.close();
  }
});
