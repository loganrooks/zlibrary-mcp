import { test, expect } from '@jest/globals';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { here, root } from './server.js';

test('4318353622 actual generated B dry command resolves a pin present only at the separate A root', async () => {
  const temp = await mkdtemp(path.join(os.tmpdir(), 'eval-separate-A-'));
  const aRoot = path.join(temp, 'A-only-object-store'),
    pin = 'f'.repeat(40);
  // Bound only read-only Git object lookup. No scratch .git/index/ref writes.
  // The default clone deliberately lacks this object; only the explicit A root has it.
  const preload = (file, args) => `
    import cp from 'node:child_process'; import {syncBuiltinESMExports} from 'node:module';
    const actual=cp.execFileSync;
    cp.execFileSync=(binary,args,options)=>{
      if(binary==='git'&&args.includes(${JSON.stringify(pin + '^{commit}')})) {
        if(args[args.indexOf('-C')+1]!==${JSON.stringify(aRoot)}) throw new Error('missing A object in default clone');
        return Buffer.from(${JSON.stringify(pin + '\n')});
      }
      return actual(binary,args,options);
    }; syncBuiltinESMExports();
    process.argv=[process.execPath,...${JSON.stringify(args)}];
    await import(${JSON.stringify('file://' + file)});
  `;
  const run = (file, args) =>
    execFileSync(process.execPath, ['--input-type=module', '-e', preload(file, args)], {
      cwd: root,
      encoding: 'utf8',
      stdio: 'pipe',
    });
  try {
    const matrix = JSON.parse(
      run(path.join(here, 'matrix.mjs'), [
        '--a-root',
        aRoot,
        '--a-pin',
        pin,
        '--b-root',
        path.join(temp, 'B'),
        '--out',
        temp,
      ]),
    );
    expect(matrix.commands).toHaveLength(15);
    expect(matrix.commands.every((c) => c.args[c.args.indexOf('--a-root') + 1] === aRoot)).toBe(
      true,
    );
    const command = matrix.commands.find(
      (c) =>
        c.args[c.args.indexOf('--arm') + 1] === 'B' &&
        c.args[c.args.indexOf('--driver') + 1] === 'codex',
    );
    const args = command.args.slice(1);
    args[args.indexOf('--paid')] = '--dry-run';
    run(path.join(here, 'run.mjs'), args);
    const receipt = JSON.parse(await readFile(args[args.indexOf('--out') + 1], 'utf8'));
    expect(receipt).toMatchObject({
      baselinePin: pin,
      status: 'dry-run; no server or model started',
      baselineSelection: { root: aRoot },
    });
    const missingRoot = [...args],
      at = missingRoot.indexOf('--a-root');
    missingRoot.splice(at, 2);
    expect(() => run(path.join(here, 'run.mjs'), missingRoot)).toThrow(
      /missing A object in default clone/,
    );
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});
