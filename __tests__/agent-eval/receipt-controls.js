// Synthetic complete receipts for deterministic gate tests; never model evidence.
import { driverEnvironmentRecord } from './driver-environment.js';
import { syntheticNodeProof } from './node-receipt-controls.js';
import { digest } from './evaluator-identity.js';
import { pythonPolicy } from './python-runtime.js';
import { tasks } from './tasks.js';
import * as drivers from './drivers.js';
import { receiptSchemaVersion } from './admission.js';
import { artifactProofMethod, manifestDigest } from './build-proof.js';
function syntheticArtifactProof(sha, fullDist) {
  const manifest = (paths) => {
    const files = paths
      .sort((a, b) => a.localeCompare(b))
      .map((path) => ({ path, sha256: '2'.repeat(64) }));
    return { files, sha256: manifestDigest(files) };
  };
  const runtime = manifest(['index.js']);
  return {
    version: 1,
    method: artifactProofMethod,
    status: 'verified',
    identityStable: true,
    sha,
    inputs: manifest([
      'src/index.ts',
      'package-lock.json',
      'package.json',
      'tsconfig.json',
      'pyproject.toml',
      'uv.lock',
    ]),
    compiler: { version: 'synthetic-compiler-control', sha256: '3'.repeat(64), files: 1 },
    command: {
      binary: 'node',
      compiler: 'typescript/bin/tsc',
      args: [
        '--project',
        'tsconfig.json',
        '--outDir',
        'dist',
        '--incremental',
        'false',
        '--noEmitOnError',
        'true',
      ],
    },
    compiledRuntime: structuredClone(runtime),
    selectedRuntime: runtime,
    fullDist,
  };
}
export function measured(arm, input = 100) {
  const sha = (arm.build === 'A' ? 'a' : 'b').repeat(40);
  const tree = { sha256: '1'.repeat(64), files: 1 };
  const artifactProof = syntheticArtifactProof(sha, tree);
  const files = [
    'package.json',
    'package-lock.json',
    '__tests__/agent-eval/oracles.js',
    '__tests__/agent-eval/run.mjs',
    '__tests__/rehearsal/fake_catalogue.py',
    '__tests__/rehearsal/harness.js',
  ]
    .sort((a, b) => a.localeCompare(b))
    .map((path) => ({ path, sha256: '4'.repeat(64) }));
  const evaluator = {
    version: 1,
    status: 'verified',
    clean: true,
    root: '/synthetic/evaluator',
    head: 'e'.repeat(40),
    files,
    sha256: manifestDigest(files),
  };
  const filesPython = artifactProof.inputs.files.filter((f) =>
    ['pyproject.toml', 'uv.lock'].includes(f.path),
  );
  const manifests = { files: filesPython, sha256: manifestDigest(filesPython) };
  const metadata = {
    policy: pythonPolicy,
    recipe: [
      'sync',
      '--check',
      '--frozen',
      '--offline',
      '--no-default-groups',
      '--group',
      'dev',
      '--no-config',
    ],
    uv: { sha256: '5'.repeat(64), version: 'synthetic uv' },
    binarySha256: '6'.repeat(64),
    interpreter: {
      prefix: '$VENV',
      userSite: false,
      executable: '$VENV/bin/python',
      basePrefix: '$PYTHONBASE',
      version: '3.14.2',
      implementation: 'cpython',
      cacheTag: 'cpython-314',
      platform: 'darwin',
      arch: 'arm64',
      sysPath: ['$BUILDROOT', '$VENV/lib/site-packages'],
    },
    distributions: [
      {
        name: 'zlibrary',
        version: 'synthetic',
        location: '$VENV/lib/site-packages',
        directUrl: { url: 'file://$BUILDROOT/zlibrary', dir_info: { editable: true } },
      },
    ],
    imports: { zlibrary: '$BUILDROOT/zlibrary/src/zlibrary/__init__.py' },
    manifests,
  };
  const python = {
    version: 1,
    status: 'verified',
    descriptor: {
      executable: '/synthetic/.venv/bin/python',
      env: { PYTHONNOUSERSITE: '1', PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: '/synthetic' },
    },
    manifests,
    metadata,
    sha256: digest(metadata),
  };
  return {
    python,
    pythonEnd: structuredClone(python),
    pythonStable: true,
    evaluator,
    evaluatorEnd: structuredClone(evaluator),
    evaluatorStable: true,
    node: syntheticNodeProof(evaluator.files),
    nodeEnd: syntheticNodeProof(evaluator.files),
    nodeStable: true,
    schemaVersion: receiptSchemaVersion,
    status: 'measured; report comparison before deciding',
    sourceStable: true,
    fencePassed: true,
    baselinePin: 'a'.repeat(40),
    driver: 'claude',
    driverEnvironment: driverEnvironmentRecord('claude', {}),
    driverVersion: '2.1.303 (Claude Code)',
    arm,
    settings: {
      ...drivers.driverPins.claude,
      toolSearch: false,
      repetitions: 5,
      warmRuns: 1,
      temperature: 'driver default',
      cell: 'one T1–T12 episode',
      defaultOrderEnv: 'BOOK_SOURCE_DEFAULT_ORDER',
    },
    build: {
      sha,
      source: {
        sha,
        trees: {
          dist: tree,
          lib: tree,
          vendoredZlibrary: tree,
          productionInputs: {
            sha256: artifactProof.inputs.sha256,
            files: artifactProof.inputs.files.length,
          },
        },
      },
      artifactProof,
      node: syntheticNodeProof(artifactProof.inputs.files),
      nodeEnd: syntheticNodeProof(artifactProof.inputs.files),
      tools: { count: arm.history ? (arm.build === 'A' ? 12 : 5) : 4, serializedCharacters: 5000 },
    },
    results: Array.from({ length: 5 }, (_, run) =>
      [0, 1].flatMap((phaseIndex) =>
        tasks.map((t) => ({
          run,
          phase: phaseIndex === 0 ? 'cold' : 'warm',
          phaseIndex,
          task: t.id,
          session: `session-${run}`,
          driverVersion: '2.1.303 (Claude Code)',
          driverEnvironment: driverEnvironmentRecord('claude', {}),
          success: true,
          pathCorrect: true,
          answer: { status: 'correct' },
          wrongDecisions: 0,
          invalidCalls: 0,
          refUnavailable: 0,
          calls: 0,
          quotaSpent: 0,
          trace: [],
          capture: {
            cleanup: {
              scope: 'owned-posix-process-group',
              pgid: 12345,
              state: 'gone',
              termSent: false,
              killSent: false,
              reason: 'closed',
              observations: ['gone'],
              success: true,
            },
            residualGroup: false,
            complete: true,
            closed: true,
            code: 0,
            signal: null,
            timedOut: false,
            drainTimedOut: false,
          },
          providerEvents: [],
          attemptCoverage: { unavailable: [] },
          requestedModel: drivers.driverPins.claude.model,
          usage: {
            scope: 'invocation',
            inputTotal: input,
            inputUncached: input,
            inputCacheRead: 0,
            inputCacheWrite: 0,
            output: 1,
            outputCached: null,
            outputUncached: 1,
            cacheFirstRequest: 0,
            source: 'result.usage',
          },
        })),
      ),
    ).flat(),
  };
}
