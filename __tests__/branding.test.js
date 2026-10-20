/** Run by the ordinary CI Jest job; no live network or packed-file mutation. */
import { test, expect } from '@jest/globals';
import { readFileSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { TOOL_DEFINITIONS } from '../dist/index.js';
const banned = /\b(?:rag|process_for_rag|processed_rag_output|scholar|philosophy scholar|classical|margin tag|Aristotle)\b/gi;
function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    if (entry.name === '__pycache__') return [];
    const file = path.join(directory, entry.name);
    return entry.isDirectory() ? files(file) : /\.(ts|py)$/.test(file) ? [file] : [];
  });
}
test('branding scan: live source, README, API, tool list and npm pack names are neutral', () => {
  const findings = [];
  for (const file of [...files('src'), ...files('lib'), 'README.md', 'docs/api.md']) {
    const matches = readFileSync(file, 'utf8').match(banned);
    if (matches) findings.push({ file, matches });
  }
  const packed = execFileSync('npm', ['pack', '--dry-run', '--ignore-scripts', '--json'], {
    encoding: 'utf8', env: { ...process.env, npm_config_cache: '/tmp/iface-npm-cache' },
  });
  for (const [file, text] of [['tools/list', JSON.stringify({ tools: TOOL_DEFINITIONS })], ['npm pack', packed]]) {
    const matches = text.match(banned);
    if (matches) findings.push({ file, matches });
  }
  expect(findings).toEqual([]);
});
