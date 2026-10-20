import { test, expect } from '@jest/globals';
import { mkdtemp, realpath, writeFile, readFile, rm, mkdir } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
const guard = fileURLToPath(new URL('./node-inventory-guard.cjs', import.meta.url));
test('4318878598 deliberate forbidden synthetic content reads deny before bytes across supported Node fs methods', async () => {
  const temp = await realpath(await mkdtemp(path.join(os.tmpdir(), 'node-guard-sentinel-'))),
    scratch = path.join(temp, 'owned'),
    forbidden = path.join(temp, 'original', '.npmrc'),
    sentinel = 'SYNTHETIC_CONFIG_CANARY_NEVER_RETURN';
  try {
    await mkdir(scratch);
    await mkdir(path.dirname(forbidden));
    await writeFile(forbidden, sentinel);
    const trace = path.join(scratch, 'trace.jsonl');
    const policy = {
      scratch,
      install: path.join(scratch, 'node_modules'),
      viewInstall: path.join(scratch, 'node_modules'),
      npmRoot: path.join(scratch, 'tool'),
      manifests: [],
      trace,
    };
    const script = `const fs=require('node:fs'),fsp=require('node:fs/promises');const p=${JSON.stringify(forbidden)};(async()=>{const cases=[()=>fs.readFileSync(p),()=>new Promise((r,j)=>fs.readFile(p,e=>e?j(e):r())),()=>fs.openSync(p,'r'),()=>new Promise((r,j)=>fs.open(p,'r',e=>e?j(e):r())),()=>fs.createReadStream(p),()=>fsp.readFile(p),()=>fsp.open(p,'r')];for(const run of cases){let denied=false;try{await run();}catch(e){denied=e.code==='ENOENT';}if(!denied)throw new Error('forbidden sentinel was not denied');}process.stdout.write('7 reads denied before bytes');})();`;
    const output = execFileSync(process.execPath, ['--require', guard, '-e', script], {
      cwd: scratch,
      env: {
        PATH: path.dirname(process.execPath),
        HOME: scratch,
        EVAL_NODE_READ_POLICY: JSON.stringify(policy),
      },
      encoding: 'utf8',
      timeout: 5000,
    });
    expect(output).toBe('7 reads denied before bytes');
    expect(output).not.toContain(sentinel);
    const rows = (await readFile(trace, 'utf8')).trim().split('\n').map(JSON.parse);
    expect(rows.filter((r) => r.path === forbidden)).toHaveLength(7);
    expect(rows.some((r) => r.path === forbidden && r.allowed)).toBe(false);
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});
test('4318878598 guarded inventory blocks synthetic network and lifecycle attempts without connecting/spawning', async () => {
  const scratch = await realpath(await mkdtemp(path.join(os.tmpdir(), 'node-guard-ops-')));
  try {
    const trace = path.join(scratch, 'trace.jsonl'),
      policy = {
        scratch,
        install: scratch,
        viewInstall: scratch,
        npmRoot: scratch,
        manifests: [],
        trace,
      };
    const script = `for(const run of [()=>require('node:net').connect(9,'127.0.0.1'),()=>require('node:child_process').spawn(process.execPath,[]),()=>new(require('node:worker_threads').Worker)('bad')]){let denied=false;try{run();}catch{denied=true;}if(!denied)throw new Error('operation escaped');}process.stdout.write('blocked');`;
    expect(
      execFileSync(process.execPath, ['--require', guard, '-e', script], {
        cwd: scratch,
        env: {
          PATH: path.dirname(process.execPath),
          EVAL_NODE_READ_POLICY: JSON.stringify(policy),
        },
        encoding: 'utf8',
        timeout: 5000,
      }),
    ).toBe('blocked');
    const rows = (await readFile(trace, 'utf8')).trim().split('\n').map(JSON.parse);
    expect(
      rows.filter((r) => ['network', 'child-process'].includes(r.operation) && !r.allowed),
    ).toHaveLength(3);
  } finally {
    await rm(scratch, { recursive: true, force: true });
  }
});
test('4318878598 even allowlisted package metadata cannot be written outside owned inventory scratch', async () => {
  const temp = await realpath(await mkdtemp(path.join(os.tmpdir(), 'node-guard-writes-'))),
    scratch = path.join(temp, 'owned'),
    install = path.join(temp, 'install');
  try {
    await mkdir(scratch);
    await mkdir(install);
    const file = path.join(install, 'package.json');
    await writeFile(file, '{"original":true}');
    const trace = path.join(scratch, 'trace.jsonl'),
      policy = { scratch, install, viewInstall: install, npmRoot: scratch, manifests: [], trace };
    const script = `let blocked=0;for(const run of [()=>require('node:fs').writeFileSync(${JSON.stringify(file)},'changed'),()=>require('node:fs').openSync(${JSON.stringify(file)},'w')]){try{run();}catch{blocked++;}}if(blocked!==2)throw new Error('write escaped');process.stdout.write('writes denied');`;
    expect(
      execFileSync(process.execPath, ['--require', guard, '-e', script], {
        cwd: scratch,
        env: { EVAL_NODE_READ_POLICY: JSON.stringify(policy) },
        encoding: 'utf8',
        timeout: 5000,
      }),
    ).toBe('writes denied');
    expect(await readFile(file, 'utf8')).toBe('{"original":true}');
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
});
test('4318878598 unsupported raw/numeric-fd reads remain audited even when a tool catches denial', async () => {
  const scratch = await realpath(await mkdtemp(path.join(os.tmpdir(), 'node-guard-fds-')));
  try {
    const trace = path.join(scratch, 'trace.jsonl'),
      policy = {
        scratch,
        install: scratch,
        viewInstall: scratch,
        npmRoot: scratch,
        manifests: [],
        trace,
      };
    const script = `const fs=require('node:fs');for(const method of ['read','readSync','readv','readvSync','readFileSync']){try{fs[method](42);}catch{}}process.stdout.write('caught unsupported reads');`;
    expect(
      execFileSync(process.execPath, ['--require', guard, '-e', script], {
        cwd: scratch,
        env: { EVAL_NODE_READ_POLICY: JSON.stringify(policy) },
        encoding: 'utf8',
        timeout: 5000,
      }),
    ).toBe('caught unsupported reads');
    const rows = (await readFile(trace, 'utf8')).trim().split('\n').map(JSON.parse);
    expect(rows.filter((r) => r.operation === 'unsupported-fd-read' && !r.allowed)).toHaveLength(5);
  } finally {
    await rm(scratch, { recursive: true, force: true });
  }
});
