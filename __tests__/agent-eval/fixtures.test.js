import { test, expect } from '@jest/globals';
import { execFileSync } from 'node:child_process';
import { root } from './server.js';
import path from 'node:path';
// Real selection logic, synthetic data; no bridge mocks and no outbound calls.
test('fixed catalogue distinguishes queries, modes, translators, history, filters and pages', () => {
  const result = execFileSync(
    path.join(root, '.venv/bin/python'),
    [
      '-c',
      `
import sys, hashlib
sys.path.insert(0, '${path.join(root, '__tests__/rehearsal')}')
from fake_catalogue import select, HISTORY, LIBGEN, payload
assert select('totally unknown zqxv') == []
assert select('Being and Time') == []
assert any(b['title'] == 'Being and Time' for b in HISTORY)
assert len(select('Persuasion')) == 1
assert select('Persuasion', mode='empty') == []
assert select('Persuasion', fields={'extensions[]':['epub']}) == []
assert select('Persuasion', source='libgen')[0]['extension'] == 'epub'
assert len(select('Seneca Letters')) == 2
assert {b['translator'] for b in select('Seneca Letters')} == {'Margaret Graver and A. A. Long', 'Robin Campbell'}
assert len(select('Hannah Arendt', fields={'yearFrom':['1950'], 'yearTo':['1965']})) == 3
assert select('Persuasion', fields={'languages[]':['russian']}) == []
assert select('Persuasion Jane Austen', fields={'e':['1']})[0]['id'] == 201
assert select('Persuasion Jane', fields={'e':['1']}) == []
first=select('Phenomenology', fields={'limit':['10']})
second=select('Phenomenology', fields={'limit':['10'],'page':['2']})
assert len(first) == len(second) == 10 and first[0]['id'] != second[0]['id']
assert second == select('Phenomenology', fields={'limit':['10'],'page':['2']})
assert select('Phenomenology', fields={'limit':['10'],'page':['7']}) == []
for b in LIBGEN[:-1]: assert b['md5'] == hashlib.md5(payload(b)).hexdigest()
print('catalogue contract pass')
`,
    ],
    { encoding: 'utf8', env: { PATH: process.env.PATH, PYTHONDONTWRITEBYTECODE: '1' } },
  );
  expect(result.trim()).toBe('catalogue contract pass');
});
