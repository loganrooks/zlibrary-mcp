import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

function milestone(title, open = 0) {
  return { number: 1, title, description: 'Map: #201', open_issues: open, state: 'open' };
}

// Execute the real audit with real files and subprocesses. Only the Git/GitHub
// command boundary is replaced: no tags, auth-cache access or network calls.
function audit({ tags = ['1.4.0'], milestones = [milestone('v1.4 — original')], ...extra } = {}) {
  const root = mkdtempSync(path.join(tmpdir(), 'release-audit-test-'));
  try {
    mkdirSync(path.join(root, 'scripts'));
    mkdirSync(path.join(root, 'bin'));
    copyFileSync(
      new URL('../scripts/release-audit.mjs', import.meta.url),
      path.join(root, 'scripts/release-audit.mjs'),
    );
    writeFileSync(path.join(root, 'package.json'), JSON.stringify({ version: '1.4.1' }));
    writeFileSync(
      path.join(root, 'CHANGELOG.md'),
      '## [Unreleased]\n\nPending work.\n\n## [1.4.10]\n\nNotes.\n\n## [1.4.1]\n\nNotes.\n\n## [1.4.0]\n\nNotes.\n',
    );
    writeFileSync(path.join(root, 'fixture.json'), JSON.stringify({ tags, milestones, ...extra }));
    const command = `#!${process.execPath}
const fs = require('node:fs');
const path = require('node:path');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixture.json'), 'utf8'));
const args = process.argv.slice(2);
const tool = path.basename(process.argv[1]);
let result;
if (tool === 'git') {
  if (args[0] === 'tag' && args[1] === '--list') result = fixture.tags.map(v => 'v' + v).join('\\n');
  else if (args[0] === 'log') result = '2026-09-01T00:00:00Z';
  else if (args[0] === 'rev-list') result = '0';
  else if (args[0] === 'for-each-ref') result = '';
} else if (tool === 'gh') {
  if (args[0] === 'auth' && args[1] === 'status') result = 'fixture authentication';
  else if (args[0] === 'release' && args[1] === 'list') result = JSON.stringify(fixture.tags.map(v => ({ tagName: 'v' + v, isDraft: false })));
  else if (args[0] === 'api' && args[1] === 'repos/:owner/:repo/milestones?state=all&per_page=100' && !fixture.failMilestones) result = JSON.stringify(fixture.milestones);
  else if (args[0] === 'issue' && args[1] === 'list') result = JSON.stringify(args.includes('closed') ? (fixture.closedIssues ?? []) : []);
  else if (args[0] === 'pr' && args[1] === 'list') result = JSON.stringify(fixture.prs ?? []);
}
if (result === undefined) { console.error('Rejected fixture command: ' + tool + ' ' + args.join(' ')); process.exit(86); }
process.stdout.write(result);
`;
    for (const tool of ['git', 'gh']) {
      writeFileSync(path.join(root, 'bin', tool), command, { mode: 0o755 });
    }
    const result = spawnSync(process.execPath, [path.join(root, 'scripts/release-audit.mjs')], {
      cwd: root,
      encoding: 'utf8',
      timeout: 15000,
      env: { ...process.env, CI: '1', PATH: path.join(root, 'bin') },
    });
    if (result.error) throw result.error;
    return { status: result.status, output: result.stdout + result.stderr };
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

describe('release audit patch milestone identity', () => {
  test('an untagged patch milestone is distinct from the shipped minor milestone', () => {
    const result = audit({
      milestones: [milestone('v1.4 — original'), milestone('v1.4.1 — interim', 1)],
    });
    expect(result.status).toBe(0);
    expect(result.output).not.toContain('already tagged');
    expect(result.output).not.toContain('milestones claim release slot');
  });

  test('an exact patch milestone accounts for its tag without a minor milestone', () => {
    const result = audit({ tags: ['1.4.1'], milestones: [milestone('v1.4.1 — interim')] });
    expect(result.status).toBe(0);
    expect(result.output).not.toContain('no milestone claims');
  });

  test('a tag owned by an exact patch milestone does not ship an open minor milestone', () => {
    const result = audit({
      tags: ['1.4.1'],
      milestones: [milestone('v1.4 — future', 2), milestone('v1.4.1 — interim')],
    });
    expect(result.status).toBe(0);
    expect(result.output).not.toContain('already tagged');
  });

  test('patch 1.4.1 does not ship the later patch 1.4.10', () => {
    const result = audit({
      tags: ['1.4.1'],
      milestones: [milestone('v1.4.1 — interim'), milestone('v1.4.10 — later', 1)],
    });
    expect(result.status).toBe(0);
  });

  test('a tagged patch still fails when its exact milestone has open issues', () => {
    const result = audit({ tags: ['1.4.1'], milestones: [milestone('v1.4.1 — interim', 1)] });
    expect(result.status).toBe(1);
    expect(result.output).toContain('has 1 open issue(s), but v1.4.1 is already tagged');
  });

  test.each(['v1.4', 'v1.4.1'])('duplicate %s milestones still fail', (slot) => {
    const result = audit({
      tags: [],
      milestones: [milestone(`${slot} — first`), milestone(`${slot} — second`)],
    });
    expect(result.status).toBe(1);
    expect(result.output).toContain(`2 milestones claim release slot ${slot}:`);
  });

  test('legacy minor milestones still account for tags without an exact patch slot', () => {
    expect(audit().status).toBe(0);
    const result = audit({ milestones: [milestone('v1.4 — original', 1)] });
    expect(result.status).toBe(1);
    expect(result.output).toContain('has 1 open issue(s), but v1.4 is already tagged');
  });

  test('a tag without either an exact patch or legacy minor milestone still fails', () => {
    const result = audit({ milestones: [] });
    expect(result.status).toBe(1);
    expect(result.output).toContain('is tagged but no milestone claims');
  });

  test('patch milestones still require a map issue', () => {
    const result = audit({
      tags: [],
      milestones: [{ ...milestone('v1.4.1 — interim'), description: '' }],
    });
    expect(result.status).toBe(1);
    expect(result.output).toContain('version-numbered but names no map issue');
  });

  test('the unchanged PR-age rule still fails an old PR even with recent activity', () => {
    const result = audit({
      prs: [
        {
          number: 999,
          title: 'old fixture PR',
          state: 'OPEN',
          isDraft: false,
          createdAt: new Date(Date.now() - 20 * 86400000).toISOString(),
          updatedAt: new Date().toISOString(),
          author: { login: 'fixture' },
          headRefName: 'fix/fixture',
          mergeable: 'MERGEABLE',
          isCrossRepository: false,
        },
      ],
    });
    expect(result.status).toBe(1);
    expect(result.output).toContain('has been open 20 days (active today)');
  });

  test('authenticated GitHub query failures still fail closed', () => {
    const result = audit({ failMilestones: true });
    expect(result.status).toBe(1);
    expect(result.output).toContain('GitHub query failed');
    expect(result.output).toContain('INCOMPLETE');
  });

  test('closed issues without a milestone still fail', () => {
    const result = audit({
      closedIssues: [
        {
          number: 999,
          title: 'unassigned fixture issue',
          milestone: null,
          closedAt: '2026-09-01T00:00:00Z',
        },
      ],
    });
    expect(result.status).toBe(1);
    expect(result.output).toContain('Closed issue #999');
    expect(result.output).toContain('carries no milestone');
  });
});
