import { readFile } from 'node:fs/promises';
import { summarize } from './report.js';
const files = process.argv.slice(2);
if (!files.length) throw new Error('usage: node report.mjs receipt.json [...]');
const receipts = await Promise.all(files.map(async (p) => JSON.parse(await readFile(p, 'utf8'))));
process.stdout.write(JSON.stringify(summarize(receipts), null, 2) + '\n');
