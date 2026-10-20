import { afterEach, beforeEach, expect, test } from '@jest/globals';
import { mkdir, mkdtemp, realpath, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { scoreTask } from './oracles.js';
import { arms, tasks } from './tasks.js';

let temporary, canonical, downloads, inbox;
beforeEach(async () => {
  temporary = await mkdtemp(path.join(os.tmpdir(), 'eval-destination-alias-'));
  canonical = path.join(await realpath(temporary), 'downloads');
  inbox = path.join(canonical, 'inbox');
  await mkdir(inbox, { recursive: true });
  downloads = path.join(temporary, 'downloads-alias');
  await symlink(canonical, downloads, 'dir');
});
afterEach(async () => {
  await rm(temporary, { recursive: true, force: true });
});

async function score({ file = path.join(inbox, 'seneca.pdf'), bytes, args = {} } = {}) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, bytes ?? '%PDF-1.4\nSynthetic fixture 202\n');
  return scoreTask({
    task: tasks.find((t) => t.id === 'T10'),
    arm: arms.find((a) => a.id === 'B'),
    downloads,
    trace: [
      {
        name: 'download',
        args: {
          ref: 'observed-graver-ref',
          filename: 'seneca.pdf',
          output_dir: path.join(downloads, 'inbox'),
          ...args,
        },
        selected: { id: '202', title: 'Letters on Ethics: To Lucilius', extension: 'pdf' },
        observedSelection: true,
        reply: { structuredContent: { path: file } },
      },
    ],
  });
}

test('T10 accepts the canonical inbox when downloads uses an explicit directory alias', async () => {
  expect(path.resolve(downloads, 'inbox')).not.toBe(inbox);
  expect(await realpath(path.join(downloads, 'inbox'))).toBe(inbox);
  const result = await score();
  expect(result).toMatchObject({ success: true, pathCorrect: true, wrong: [] });
  expect(result.files).toEqual([
    {
      path: path.join(inbox, 'seneca.pdf'),
      bytes: Buffer.byteLength('%PDF-1.4\nSynthetic fixture 202\n'),
    },
  ]);
});

for (const [name, options] of [
  ['wrong basename', () => ({ file: path.join(inbox, 'other.pdf') })],
  [
    'wrong directory inside downloads',
    () => ({ file: path.join(canonical, 'other', 'seneca.pdf') }),
  ],
  ['outside downloads', () => ({ file: path.join(temporary, 'outside', 'seneca.pdf') })],
  ['wrong fixture bytes', () => ({ bytes: '%PDF-1.4\nSynthetic fixture 203\n' })],
])
  test(`T10 rejects ${name} despite correct requested destination`, async () => {
    const result = await score(options());
    expect(result).toMatchObject({ success: false, pathCorrect: false, files: [] });
    expect(result.wrong.map((w) => w.reason)).toEqual(['missing or wrong artifact']);
  });

test('T10 containment rejects an inbox alias escaping downloads even when directory identity matches', async () => {
  const outside = path.join(await realpath(temporary), 'outside-inbox');
  await mkdir(outside);
  await rm(inbox, { recursive: true });
  await symlink(outside, inbox, 'dir');
  expect(await realpath(path.join(downloads, 'inbox'))).toBe(outside);
  const result = await score({ file: path.join(outside, 'seneca.pdf') });
  expect(result).toMatchObject({ success: false, pathCorrect: false, files: [] });
  expect(result.wrong.map((w) => w.reason)).toEqual(['missing or wrong artifact']);
});

for (const [name, args] of [
  ['filename', () => ({ filename: 'other.pdf' })],
  ['output_dir', () => ({ output_dir: canonical })],
])
  test(`T10 rejects wrong explicit ${name} even when the artifact is correct`, async () => {
    const result = await score({ args: args() });
    expect(result).toMatchObject({ success: false, pathCorrect: false });
    expect(result.files).toHaveLength(1);
    expect(result.wrong.map((w) => w.reason)).toEqual(['wrong filename/destination']);
  });
