import { afterEach, expect, test } from '@jest/globals';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { tmpdir } from 'node:os';

const tempDirs = [];
afterEach(() => {
  for (const dir of tempDirs.splice(0)) rmSync(dir, { recursive: true, force: true });
});
function runControl(flag, env = {}, extra = []) {
  const temp = mkdtempSync(path.join(tmpdir(), 'rehearsal-runner-control-'));
  tempDirs.push(temp);
  const manifest = path.join(temp, 'manifest.json');
  const result = spawnSync(process.execPath, ['__tests__/rehearsal/run.mjs', flag, ...extra], {
    encoding: 'utf8',
    timeout: 10000,
    env: { ...process.env, ...env, REHEARSAL_RESULT_FILE: manifest },
  });
  expect(result.error).toBeUndefined();
  return { ...result, manifest: JSON.parse(readFileSync(manifest, 'utf8')) };
}

test('rehearsal deadline reports its reason and elapsed time, not zero executed cases', () => {
  const result = runControl('--self-test-deadline', { REHEARSAL_DEADLINE_MS: '40' }, [
    // On the pre-fix runner, do not run real scenarios for an unknown control flag.
    '--testNamePattern',
    '^deadline-control-no-real-rehearsal-cases$',
  ]);
  expect(result.status).toBe(1);
  expect(result.manifest).toMatchObject({
    aggregate: 'deadline_exceeded',
    terminationReason: 'deadline_exceeded',
    interrupted: true,
    deadlineMs: 40,
    resultsComplete: false,
    executedCaseCount: null,
  });
  expect(result.manifest.elapsedMs).toBeGreaterThanOrEqual(40);
  expect(result.stderr).toMatch(/deadline_exceeded.*elapsed.*budget/);
  expect(result.stdout).not.toMatch(/0\/36 required cases executed/);
});

test.each(['0', 'NaN', '600001'])(
  'invalid deadline %s retains bounded default instead of disabling the timer',
  (value) => {
    const result = runControl('--self-test-skipped', { REHEARSAL_DEADLINE_MS: value });
    expect(result.status).toBe(1); // the deliberately skipped required case still fails
    expect(result.manifest.deadlineMs).toBe(180000);
  },
);
