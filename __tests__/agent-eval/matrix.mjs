// Print a complete campaign manifest; never executes a model driver.
import { parseArgs } from 'node:util';
import path from 'node:path';
import { arms } from './tasks.js';
import { resolveBaselinePin } from './build-proof.js';
import { root, here } from './server.js';
const { values: o } = parseArgs({
  options: {
    'a-root': { type: 'string', default: root },
    'a-pin': { type: 'string' },
    'b-root': { type: 'string' },
    out: { type: 'string', default: 'test_output/agent-eval' },
  },
});
const commands = [];
const baseline = await resolveBaselinePin(o['a-root'], o['a-pin']);
for (const arm of arms)
  for (const driver of ['codex', 'claude'])
    for (const search of driver === 'claude' ? [false, true] : [false]) {
      const available = arm.build === 'A' || !!o['b-root'];
      const args = [
        path.join(here, 'run.mjs'),
        '--paid',
        '--arm',
        arm.id,
        '--driver',
        driver,
        '--server-root',
        arm.build === 'A'
          ? path.resolve(o['a-root'])
          : o['b-root']
            ? path.resolve(o['b-root'])
            : '<B-WORKTREE>',
        '--a-pin',
        baseline.pin,
        '--runs',
        '5',
        '--warm-runs',
        '1',
        ...(search ? ['--tool-search'] : []),
        '--out',
        path.resolve(o.out, `${arm.id}-${driver}-search-${search}.json`),
      ];
      commands.push({ available, binary: process.execPath, args });
    }
process.stdout.write(
  JSON.stringify(
    { status: 'plan only: no models launched', baselineSelection: baseline, commands },
    null,
    2,
  ) + '\n',
);
