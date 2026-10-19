// Synthetic receipt proof only; never runtime/model evidence.
import {
  nodeDigest,
  nodeSelectionMethod,
  nodePolicy,
  sdkImports,
  nodeExecutionPolicy,
} from './node-runtime.js';
export function syntheticNodeProof(manifests) {
  const files = [
    { path: 'index.js', sha256: '7'.repeat(64) },
    { path: 'package.json', sha256: '8'.repeat(64) },
  ];
  const locator = 'node_modules/@modelcontextprotocol/sdk';
  const identity = {
    version: 1,
    method: nodeSelectionMethod,
    policy: structuredClone(nodePolicy),
    node: {
      binarySha256: '9'.repeat(64),
      version: 'synthetic-node',
      platform: 'synthetic-platform',
      arch: 'synthetic-arch',
      abi: 'synthetic-abi',
      options: nodeExecutionPolicy,
    },
    tool: {
      files: [{ path: 'lib/index.js', sha256: 'd'.repeat(64) }],
      version: 'synthetic-npm',
      arboristVersion: 'synthetic-arborist',
      arboristSha256: 'c'.repeat(64),
      cliSha256: 'a'.repeat(64),
      guardSha256: 'b'.repeat(64),
    },
    manifests: structuredClone(
      manifests
        .filter((f) => ['package.json', 'package-lock.json'].includes(f.path))
        .sort((a, b) => a.path.localeCompare(b.path)),
    ),
    packages: [
      {
        locator,
        name: '@modelcontextprotocol/sdk',
        version: 'synthetic-sdk',
        bins: [],
        files,
        sha256: nodeDigest(files),
      },
    ],
    edges: [
      {
        from: '',
        name: '@modelcontextprotocol/sdk',
        to: locator,
        kind: 'dependency',
        optional: false,
        spec: '1.0.0',
      },
    ],
    anchors: ['evaluator', 'build'].flatMap((context) =>
      sdkImports.flatMap((specifier) =>
        ['import', 'require'].map((branch) => ({
          context,
          specifier,
          branch,
          locator,
          file: 'index.js',
        })),
      ),
    ),
  };
  const canonical = (v) =>
    JSON.stringify(v, (_k, x) =>
      x && typeof x === 'object' && !Array.isArray(x)
        ? Object.fromEntries(Object.entries(x).sort(([a], [b]) => a.localeCompare(b)))
        : x,
    );
  identity.anchors.sort((a, b) => canonical(a).localeCompare(canonical(b)));
  return {
    version: 1,
    status: 'verified',
    stable: true,
    identity,
    sha256: nodeDigest(identity),
    local: {
      root: '/synthetic/root',
      install: '/synthetic/node_modules',
      node: '/synthetic/node',
      cli: '/synthetic/npm-cli.js',
      packageRoots: [{ locator, realpath: '/synthetic/node_modules/@modelcontextprotocol/sdk' }],
    },
    audit: {
      configContentReads: 0,
      networkAttempts: 0,
      childAttempts: 0,
      writeAttempts: 0,
      unsupportedReads: 0,
      readGuardMethod: 'synthetic-guard',
    },
  };
}
