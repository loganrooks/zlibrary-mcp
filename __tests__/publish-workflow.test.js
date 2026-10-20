import { readFileSync } from 'node:fs';
import { parse } from 'yaml';

const workflow = parse(
  readFileSync(new URL('../.github/workflows/publish.yml', import.meta.url), 'utf8'),
);
const testCommands = [
  'node --experimental-vm-modules node_modules/jest/bin/jest.js',
  'uv run pytest -m "not slow and not integration" --benchmark-disable',
];

function needs(job) {
  return typeof job.needs === 'string' ? [job.needs] : (job.needs ?? []);
}

function ancestors(jobs, id, visiting = new Set()) {
  if (!jobs[id]) throw new Error(`Missing job: ${id}`);
  if (visiting.has(id)) throw new Error(`Dependency cycle: ${id}`);
  const next = new Set([...visiting, id]);
  return new Set(needs(jobs[id]).flatMap((dep) => [dep, ...ancestors(jobs, dep, next)]));
}

// Model successful completion through needs edges only. The assertions below
// exclude status-function overrides and failure-tolerant gates from this model.
// The gate result includes its test step; npm cannot publish earlier in that job.
function canPublish(jobs, publisher, gate, gateResult) {
  if (!jobs[publisher]) return false;
  if (!needs(jobs[publisher]).every((dep) => canPublish(jobs, dep, gate, gateResult))) {
    return false;
  }
  return publisher !== gate || gateResult === 'success';
}

describe('publish workflow test gate (#211)', () => {
  const { jobs } = workflow;
  const gate = 'publish-npm';
  const steps = jobs[gate].steps;
  const testStep = steps.findIndex((step) =>
    testCommands.every((command) => step.run?.split('\n').includes(command)),
  );

  test('both existing suites run before npm publication without tolerating failure', () => {
    expect(testStep).toBeGreaterThanOrEqual(0);
    const publishStep = steps.findIndex((step) => /^npm publish\s/.test(step.run ?? ''));
    expect(publishStep).toBeGreaterThan(testStep);
    expect(steps[publishStep].run).toMatch(/\s--provenance(?:\s|$)/);
    expect(steps[publishStep].if).toBeUndefined();
    expect(steps[testStep].if).toBeUndefined();
    expect(steps[testStep]['continue-on-error'] ?? false).toBe(false);
    expect(jobs[gate].if).toBeUndefined();
    expect(jobs[gate]['continue-on-error'] ?? false).toBe(false);
  });

  test('Docker transitively needs the same-run npm test gate', () => {
    expect(ancestors(jobs, 'publish-docker').has(gate)).toBe(true);
  });

  test('publish dependency paths retain success-only scheduling', () => {
    const path = new Set([gate, 'publish-docker', ...ancestors(jobs, 'publish-docker')]);
    for (const id of path) {
      expect(jobs[id]['continue-on-error'] ?? false).toBe(false);
      expect(jobs[id].if ?? '').not.toMatch(/\b(always|success|failure|cancelled)\s*\(/);
    }
  });

  test.each(['failure', 'skipped', 'cancelled', undefined])(
    'neither publisher is reachable when the test gate result is %s',
    (result) => {
      expect(canPublish(jobs, 'publish-npm', gate, result)).toBe(false);
      expect(canPublish(jobs, 'publish-docker', gate, result)).toBe(false);
    },
  );

  test('successful tests allow both publishers in the graph model', () => {
    expect(canPublish(jobs, 'publish-npm', gate, 'success')).toBe(true);
    expect(canPublish(jobs, 'publish-docker', gate, 'success')).toBe(true);
  });

  test('a missing test job fails graph validation and blocks Docker', () => {
    const missingGate = structuredClone(jobs);
    delete missingGate[gate];
    expect(() => ancestors(missingGate, 'publish-docker')).toThrow('Missing job: publish-npm');
    expect(canPublish(missingGate, 'publish-docker', gate, 'success')).toBe(false);
  });

  test('DOCKER-BYPASS restores the unsafe failed-test path', () => {
    const bypass = structuredClone(jobs);
    bypass['publish-docker'].needs = ['validate-release-notes'];
    expect(ancestors(bypass, 'publish-docker').has(gate)).toBe(false);
    expect(canPublish(bypass, 'publish-docker', gate, 'failure')).toBe(true);
  });

  test('release notes and GitHub Release ordering are preserved', () => {
    expect(needs(jobs[gate])).toContain('validate-release-notes');
    expect(needs(jobs['github-release'])).toEqual(['validate-release-notes', 'publish-npm']);
    expect(workflow.on.push.tags).toEqual(['v*']);
    for (const id of ['validate-release-notes', 'publish-docker', 'github-release']) {
      expect(jobs[id].if).toBe("startsWith(github.ref, 'refs/tags/v')");
    }
  });
});
