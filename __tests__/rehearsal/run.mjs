import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';
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
const deadlineTest = process.argv.includes('--self-test-deadline');
const configuredDeadline = Number(process.env.REHEARSAL_DEADLINE_MS);
const deadlineMs =
  Number.isSafeInteger(configuredDeadline) && configuredDeadline > 0 && configuredDeadline <= 600000
    ? configuredDeadline
    : deadlineTest
      ? 25
      : 180000;
let exitCode;
try {
  const sourceStart = await snapshotSource(serverRoot);
  let result;
  let assertions;
  let suiteTimings = [];
  let resultsAvailable = false;
  if (selfTest || sourceDriftTest) {
    assertions = requiredCases.map((fullName, i) => ({
      fullName,
      status: selfTest && i === 0 ? 'pending' : 'passed',
    }));
    result = { status: 0, elapsedMs: 0, interrupted: false, terminationReason: null };
    resultsAvailable = true;
  } else {
    result = await new Promise((resolve) => {
      const executionStarted = performance.now();
      const child = spawn(
        process.execPath,
        deadlineTest
          ? ['-e', 'process.stdin.resume()']
          : [
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
          // The control child follows this owner's stdin pipe even if the owner dies.
          stdio: deadlineTest ? ['pipe', 'inherit', 'inherit'] : 'inherit',
          env: { ...process.env, REHEARSAL_RECORD_DIR: recordDir, REHEARSAL_TEMP_ROOT: stateDir },
        },
      );
      let terminationReason = null;
      let killTimer;
      let finished = false;
      const stop = (reason) => {
        terminationReason ??= reason;
        child.kill('SIGTERM');
        killTimer ??= setTimeout(() => child.kill('SIGKILL'), 2000);
      };
      const onSignal = () => stop('interrupted');
      process.once('SIGTERM', onSignal);
      process.once('SIGINT', onSignal);
      const timer = setTimeout(() => stop('deadline_exceeded'), deadlineMs);
      const finish = (status, signal = null) => {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        clearTimeout(killTimer);
        process.removeListener('SIGTERM', onSignal);
        process.removeListener('SIGINT', onSignal);
        resolve({
          status: terminationReason ? null : status,
          signal,
          interrupted: terminationReason !== null,
          terminationReason,
          elapsedMs: Math.round(performance.now() - executionStarted),
        });
      };
      child.once('error', () => finish(null));
      child.once('exit', (status, signal) => finish(status, signal));
    });
    try {
      const report = JSON.parse(await readFile(output, 'utf8'));
      assertions = report.testResults.flatMap((t) => t.assertionResults);
      suiteTimings = report.testResults.map((suite) => ({
        file: path.basename(suite.name),
        durationMs: suite.endTime - suite.startTime,
      }));
      resultsAvailable = true;
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
    aggregate:
      result.terminationReason === 'deadline_exceeded'
        ? 'deadline_exceeded'
        : exitCode === 0
          ? 'pass (expectations are per-fix)'
          : 'fail',
    deadlineMs,
    elapsedMs: result.elapsedMs,
    interrupted: result.interrupted,
    terminationReason: result.terminationReason,
    childSignal: result.signal ?? null,
    resultsAvailable,
    resultsComplete: complete,
    suiteTimings,
    expectedCaseCount: requiredCases.length,
    executedCaseCount: resultsAvailable ? cases.reduce((n, c) => n + c.executed, 0) : null,
    unexpectedSentinels,
    selfTestSkipped: selfTest,
    selfTestSourceDrift: sourceDriftTest,
    selfTestDeadline: deadlineTest,
    cases: cases.map((c) => ({
      ...c,
      expectedOutcome: expectedOutcome(c.name),
      durationMs: assertions.find((a) => a.fullName === c.name)?.duration ?? null,
    })),
    suites,
    tempRoot: runTemp,
  };
  const manifestPath = path.resolve(
    process.env.REHEARSAL_RESULT_FILE || path.join(root, 'test_output/rehearsal-manifest.json'),
  );
  await mkdir(path.dirname(manifestPath), { recursive: true });
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  if (result.interrupted) {
    process.stderr.write(
      `Rehearsal ${result.terminationReason}; elapsed ${result.elapsedMs} ms; budget ${deadlineMs} ms; results available: ${resultsAvailable}; required cases complete: ${complete}.\n`,
    );
    process.stdout.write(
      `Rehearsal aggregate: ${manifest.aggregate}; ${result.terminationReason}; source stable: ${sourceStable}.\n`,
    );
  } else {
    const progress = resultsAvailable
      ? `${manifest.executedCaseCount}/${manifest.expectedCaseCount} required cases executed`
      : 'Jest results unavailable';
    process.stdout.write(
      `Rehearsal aggregate: ${manifest.aggregate}; ${progress}; source stable: ${sourceStable}.\n`,
    );
  }
} finally {
  await rm(runTemp, { recursive: true, force: true });
}
process.exitCode = exitCode;
