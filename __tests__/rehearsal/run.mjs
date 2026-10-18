import { spawnSync, execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { assess, requiredCases } from './cases.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const serverRoot = path.resolve(process.env.REHEARSAL_SERVER_ROOT || root);
const started = new Date().toISOString();
const recordDir = await mkdtemp(path.join(tmpdir(), 'rehearsal-records-'));
const output = path.join(recordDir, 'jest.json');
const selfTest = process.argv.includes('--self-test-skipped');
let exitCode;
try {
  let result;
  let assertions;
  if (selfTest) {
    assertions = requiredCases.map((fullName, i) => ({
      fullName,
      status: i === 0 ? 'pending' : 'passed',
    }));
    result = { status: 0 };
  } else {
    result = spawnSync(
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
        env: { ...process.env, REHEARSAL_RECORD_DIR: recordDir },
        timeout: 115000,
      },
    );
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
  exitCode = result.status === 0 && complete ? 0 : 1;
  const manifest = {
    started,
    finished: new Date().toISOString(),
    sourceSha: execFileSync('git', ['-C', serverRoot, 'rev-parse', 'HEAD'], {
      encoding: 'utf8',
      env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' },
    }).trim(),
    builtServerSha256: createHash('sha256')
      .update(await readFile(path.join(serverRoot, 'dist/index.js')))
      .digest('hex'),
    serverRoot,
    reuseExpected: process.env.REHEARSAL_EXPECT_REUSE === '1',
    aggregate:
      exitCode === 0
        ? process.env.REHEARSAL_EXPECT_REUSE === '1'
          ? 'pass'
          : 'pass with expected master failures'
        : 'fail',
    expectedCaseCount: requiredCases.length,
    executedCaseCount: cases.reduce((n, c) => n + c.executed, 0),
    selfTestSkipped: selfTest,
    cases: cases.map((c) => ({
      ...c,
      expectedOutcome:
        process.env.REHEARSAL_EXPECT_REUSE !== '1' &&
        /exactly one login|single-flight:|zero additional login attempts|scan has no unprotected/.test(
          c.name,
        )
          ? 'expected assertion failure on master'
          : 'ordinary pass',
    })),
    suites,
  };
  const manifestPath = path.resolve(
    process.env.REHEARSAL_RESULT_FILE || path.join(root, 'test_output/rehearsal-manifest.json'),
  );
  await mkdir(path.dirname(manifestPath), { recursive: true });
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  process.stdout.write(
    `Rehearsal aggregate: ${manifest.aggregate}; ${manifest.executedCaseCount}/${manifest.expectedCaseCount} required cases executed.\n`,
  );
} finally {
  await rm(recordDir, { recursive: true, force: true });
}
process.exitCode = exitCode;
