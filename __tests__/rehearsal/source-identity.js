import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readdir, readFile, readlink, lstat } from 'node:fs/promises';
import path from 'node:path';

export async function snapshotSource(
  root,
  git = (args) =>
    execFileSync(
      'git',
      ['-C', root, '-c', 'filter.lfs.process=', '-c', 'filter.lfs.required=false', ...args],
      {
        encoding: 'utf8',
        env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' },
      },
    ),
) {
  async function treeHash(dir) {
    const hash = createHash('sha256');
    let files = 0;
    async function visit(relative) {
      for (const entry of (await readdir(path.join(dir, relative), { withFileTypes: true })).sort(
        (a, b) => a.name.localeCompare(b.name),
      )) {
        const name = path.join(relative, entry.name);
        const file = path.join(dir, name);
        if (entry.isDirectory()) await visit(name);
        else {
          hash.update(JSON.stringify([name, (await lstat(file)).mode]));
          hash.update(entry.isSymbolicLink() ? await readlink(file) : await readFile(file));
          hash.update('\0');
          files++;
        }
      }
    }
    await visit('');
    return { sha256: hash.digest('hex'), files };
  }
  return {
    sha: git(['rev-parse', 'HEAD']).trim(),
    porcelain: git(['status', '--porcelain', '--untracked-files=all']),
    trees: {
      dist: await treeHash(path.join(root, 'dist')),
      lib: await treeHash(path.join(root, 'lib')),
    },
  };
}
