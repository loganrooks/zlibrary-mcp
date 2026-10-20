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
// The gate result includes its test step; both registries are in its dependent job.
function canPublish(jobs, publisher, gate, gateResult) {
  if (!jobs[publisher]) return false;
  if (!needs(jobs[publisher]).every((dep) => canPublish(jobs, dep, gate, gateResult))) {
    return false;
  }
  return publisher !== gate || gateResult === 'success';
}

describe('publish workflow test gate (#211)', () => {
  const { jobs } = workflow;
  const gate = 'prepare-release';
  const steps = jobs[gate]?.steps ?? [];
  const testStep = steps.findIndex((step) =>
    testCommands.every((command) => step.run?.split('\n').includes(command)),
  );

  test('both existing suites run before npm publication without tolerating failure', () => {
    expect(testStep).toBeGreaterThanOrEqual(0);
    const publishSteps = jobs['publish-packages'].steps;
    const publishStep = publishSteps.find((step) => /^npm publish\s/.test(step.run ?? ''));
    expect(ancestors(jobs, 'publish-packages').has(gate)).toBe(true);
    expect(publishStep.run).toMatch(/\s--provenance(?:\s|$)/);
    expect(publishStep.if).toBeUndefined();
    expect(steps[testStep].if).toBeUndefined();
    expect(steps[testStep]['continue-on-error'] ?? false).toBe(false);
    expect(jobs[gate].if).toBeUndefined();
    expect(jobs[gate]['continue-on-error'] ?? false).toBe(false);
  });

  test('Docker transitively needs the same-run npm test gate', () => {
    expect(ancestors(jobs, 'publish-packages').has(gate)).toBe(true);
  });

  test('publish dependency paths retain success-only scheduling', () => {
    const path = new Set([gate, 'publish-packages', ...ancestors(jobs, 'publish-packages')]);
    for (const id of path) {
      expect(jobs[id]['continue-on-error'] ?? false).toBe(false);
      expect(jobs[id].if ?? '').not.toMatch(/\b(always|success|failure|cancelled)\s*\(/);
    }
  });

  test.each(['failure', 'skipped', 'cancelled', undefined])(
    'neither publisher is reachable when the test gate result is %s',
    (result) => {
      expect(canPublish(jobs, 'publish-packages', gate, result)).toBe(false);
    },
  );

  test('successful tests allow both publishers in the graph model', () => {
    expect(canPublish(jobs, 'publish-packages', gate, 'success')).toBe(true);
  });

  test('a missing test job fails graph validation and blocks Docker', () => {
    const missingGate = structuredClone(jobs);
    delete missingGate[gate];
    expect(() => ancestors(missingGate, 'publish-packages')).toThrow(
      'Missing job: prepare-release',
    );
    expect(canPublish(missingGate, 'publish-packages', gate, 'success')).toBe(false);
  });

  test('DOCKER-BYPASS restores the unsafe failed-test path', () => {
    const bypass = structuredClone(jobs);
    bypass['publish-packages'].needs = ['validate-release-notes'];
    expect(ancestors(bypass, 'publish-packages').has(gate)).toBe(false);
    expect(canPublish(bypass, 'publish-packages', gate, 'failure')).toBe(true);
  });

  test('release notes and GitHub Release ordering are preserved', () => {
    expect(needs(jobs[gate])).toContain('validate-release-notes');
    expect(needs(jobs['github-release'])).toEqual(['validate-release-notes', 'publish-packages']);
    expect(workflow.on.push.tags).toEqual(['v*']);
    for (const id of ['validate-release-notes', 'publish-packages', 'github-release']) {
      expect(jobs[id].if).toBe("startsWith(github.ref, 'refs/tags/v')");
    }
  });
});

function assertImageGate(jobs) {
  const job = jobs['publish-packages'];
  expect(job['continue-on-error'] ?? false).toBe(false);
  const steps = job.steps;
  const build = steps.findIndex((s) => s.uses?.startsWith('docker/build-push-action@'));
  const identity = steps.findIndex((s) => s.id === 'image-identity');
  const smoke = steps.findIndex((s) => s.run?.startsWith('node scripts/image-smoke.mjs '));
  const npm = steps.findIndex((s) => s.run?.startsWith('npm publish '));
  const push = steps.findIndex((s) => s.run?.startsWith('node scripts/push-tested-image.mjs '));
  expect(build).toBeGreaterThanOrEqual(0);
  expect(identity).toBeGreaterThan(build);
  expect(smoke).toBeGreaterThan(identity);
  expect(npm).toBeGreaterThan(smoke);
  expect(push).toBeGreaterThan(npm);
  for (const i of [build, identity, smoke, npm, push]) {
    expect(steps[i].if).toBeUndefined();
    expect(steps[i]['continue-on-error'] ?? false).toBe(false);
  }
  expect(steps[build].with.load).toBe(true);
  expect(steps[build].with.push).toBe(false);
  expect(steps[build].with.provenance).toBe('mode=min');
  expect(steps[build].id).toBe('build');
  expect(steps[identity].run).toBe(
    'node scripts/image-identity.mjs zlibrary-mcp:smoke "$TESTED_DIGEST"',
  );
  expect(steps[identity].env.TESTED_DIGEST).toBe('${{ steps.build.outputs.digest }}');
  expect(steps[smoke].run).toBe('node scripts/image-smoke.mjs zlibrary-mcp:smoke');
  expect(steps[push].env.TESTED_DIGEST).toBe('${{ steps.build.outputs.digest }}');
  expect(steps[push].env.IMAGE_TAGS).toBe('${{ steps.meta.outputs.tags }}');
  expect(steps[build].with.tags).toContain('zlibrary-mcp:smoke');
  expect(steps[build].with.context).toBe('${{ runner.temp }}/image-context');
  expect(steps[build].with['build-args']).toBe('BUILD_INPUT=packed');
  const docker = steps.find((s) => s.uses?.startsWith('docker/setup-docker-action@'));
  expect(JSON.parse(docker.with['daemon-config']).features['containerd-snapshotter']).toBe(true);
}

describe('release image gate (#291 F1/F2/F5/F6)', () => {
  test('build, identity, smoke, npm publication and attested image push are ordered', () => {
    assertImageGate(workflow.jobs);
  });

  test.each([
    'early-push',
    'tolerated-smoke',
    'conditional-smoke',
    'npm-before-smoke',
    'push-before-smoke',
    'no-provenance',
  ])('%s is rejected', (mutation) => {
    const jobs = structuredClone(workflow.jobs);
    const steps = jobs['publish-packages'].steps;
    const build = steps.find((s) => s.uses?.startsWith('docker/build-push-action@'));
    const smoke = steps.find((s) => s.run?.startsWith('node scripts/image-smoke.mjs '));
    if (mutation === 'early-push') build.with.push = true;
    if (mutation === 'tolerated-smoke') smoke['continue-on-error'] = true;
    if (mutation === 'conditional-smoke') smoke.if = 'false';
    if (mutation === 'no-provenance') build.with.provenance = false;
    if (mutation.endsWith('before-smoke')) {
      const i = steps.findIndex((s) =>
        s.run?.startsWith(
          mutation.startsWith('npm') ? 'npm publish ' : 'node scripts/push-tested-image.mjs ',
        ),
      );
      const [publisher] = steps.splice(i, 1);
      steps.splice(steps.indexOf(smoke), 0, publisher);
    }
    expect(() => assertImageGate(jobs)).toThrow();
  });

  test('tag patterns and latest behavior stay fixed', () => {
    const meta = workflow.jobs['publish-packages'].steps.find((s) => s.id === 'meta');
    expect(meta.with.tags.trim().split('\n')).toEqual([
      'type=semver,pattern={{version}}',
      'type=semver,pattern={{major}}.{{minor}}',
      "type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/v') }}",
    ]);
    expect(workflow.on.workflow_dispatch).toBeNull();
  });

  test('CI and publish share the context helper and release packs only once', () => {
    const ci = parse(readFileSync(new URL('../.github/workflows/ci.yml', import.meta.url), 'utf8'));
    const ciContext = ci.jobs.docker.steps.find((s) =>
      s.run?.includes('scripts/prepare-image-context.sh'),
    );
    const publishContext = workflow.jobs['publish-packages'].steps.find((s) =>
      s.run?.includes('scripts/prepare-image-context.sh'),
    );
    expect(ciContext).toBeDefined();
    expect(publishContext.run).toContain('release-package/*.tgz');
    expect(
      workflow.jobs['prepare-release'].steps.filter((s) => s.run?.includes('npm pack')),
    ).toHaveLength(1);
    expect(workflow.jobs['publish-packages'].steps.some((s) => s.run?.includes('npm pack'))).toBe(
      false,
    );
  });
});
