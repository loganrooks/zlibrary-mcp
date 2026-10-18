import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { assess, requiredCases } from './cases.js';
import { snapshotSource } from './source-identity.js';
import { expectedFixes, expectedOutcome } from './expectations.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const serverRoot = path.resolve(process.env.REHEARSAL_SERVER_ROOT || root);
const started = new Date().toISOString();
const runTemp = await mkdtemp(path.join(tmpdir(), 'rehearsal-run-'));
const recordDir = path.join(runTemp, 'records');
const stateDir = path.join(runTemp, 'states');
await mkdir(recordDir);
await mkdir(stateDir);
const output = path.join(recordDir, 'jest.json');
const selfTest = process.argv.includes('--self-test-skipped');
const sourceDriftTest = process.argv.includes('--self-test-source-drift');
let exitCode;
try {
  const sourceStart = await snapshotSource(serverRoot);
  let result;
  let assertions;
  if (selfTest || sourceDriftTest) {
    assertions = requiredCases.map((fullName, i) => ({
      fullName,
      status: selfTest && i === 0 ? 'pending' : 'passed',
    }));
    result = { status: 0 };
  } else {
    result = await new Promise((resolve) => {
      const child = spawn(
        process.execPath,
        [
          '--experimental-vm-modules',
          path.join(root, 'node_modules/jest/bin/jest.js'),
          '--config',
          path.join(root, '__tests__/rehearsal/jest.config.js'),
          '--json',
          '--outputFile',
          output,
          ...process.argv.slice(2),
        ],
        {
          cwd: root,
          stdio: 'inherit',
          env: { ...process.env, REHEARSAL_RECORD_DIR: recordDir, REHEARSAL_TEMP_ROOT: stateDir },
        },
      );
      let interrupted = false;
      let killTimer;
      const stop = () => {
        interrupted = true;
        child.kill('SIGTERM');
        killTimer ??= setTimeout(() => child.kill('SIGKILL'), 2000);
      };
      process.once('SIGTERM', stop);
      process.once('SIGINT', stop);
      const timer = setTimeout(stop, 115000);
      const finish = (status) => {
        clearTimeout(timer);
        clearTimeout(killTimer);
        process.removeListener('SIGTERM', stop);
        process.removeListener('SIGINT', stop);
        resolve({ status: interrupted ? null : status });
      };
      child.once('error', () => finish(null));
      child.once('exit', (status) => finish(status));
    });
    try {
      const report = JSON.parse(await readFile(output, 'utf8'));
      assertions = report.testResults.flatMap((t) => t.assertionResults);
    } catch {
      assertions = [];
    }
  }
  const cases = assess(assertions);
  const complete =
    assertions.length === requiredCases.length &&
    cases.every((c) => c.executed === c.expected && c.status === 'passed');
  const suites = {};
  for (const file of await readdir(recordDir)) {
    if (file !== 'jest.json' && file.endsWith('.json'))
      suites[file.slice(0, -5)] = JSON.parse(await readFile(path.join(recordDir, file), 'utf8'));
  }
  let sourceEnd;
  let sourceEndError = false;
  try {
    sourceEnd = await snapshotSource(serverRoot);
    if (sourceDriftTest) sourceEnd.trees.lib.sha256 = 'injected-drift';
  } catch {
    sourceEndError = true;
  }
  const sourceStable = !sourceEndError && JSON.stringify(sourceStart) === JSON.stringify(sourceEnd);
  const unexpectedSentinels = Object.values(suites).reduce(
    (n, suite) => n + suite.sentinelFindings,
    0,
  );
  exitCode = result.status === 0 && complete && sourceStable && unexpectedSentinels === 0 ? 0 : 1;
  const manifest = {
    started,
    finished: new Date().toISOString(),
    serverRoot,
    sourceStart,
    sourceEnd,
    sourceEndError,
    sourceStable,
    expectedFixes: [...expectedFixes],
    aggregate: exitCode === 0 ? 'pass (expectations are per-fix)' : 'fail',
    expectedCaseCount: requiredCases.length,
    executedCaseCount: cases.reduce((n, c) => n + c.executed, 0),
    unexpectedSentinels,
    selfTestSkipped: selfTest,
    selfTestSourceDrift: sourceDriftTest,
    cases: cases.map((c) => ({ ...c, expectedOutcome: expectedOutcome(c.name) })),
    suites,
    tempRoot: runTemp,
  };
  const manifestPath = path.resolve(
    process.env.REHEARSAL_RESULT_FILE || path.join(root, 'test_output/rehearsal-manifest.json'),
  );
  await mkdir(path.dirname(manifestPath), { recursive: true });
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  process.stdout.write(
    `Rehearsal aggregate: ${manifest.aggregate}; ${manifest.executedCaseCount}/${manifest.expectedCaseCount} required cases executed; source stable: ${sourceStable}.\n`,
  );
} finally {
  await rm(runTemp, { recursive: true, force: true });
}
process.exitCode = exitCode;
