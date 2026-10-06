// Fails if a built site contains synthetic fixture content. Run after `npm run build`.
// Contract code legitimately mentions the word "synthetic"; these markers occur only in fixtures/stages.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = process.argv[2] ?? 'dist';
const markers = ['Synthetic Alpha', 'synthetic-party-', 'synthetic-election', 'synthetic-electorate-', 'synthetic-dry-run', 'synthetic-placeholder-v1', 'UNVERIFIED-PLACEHOLDER-synthetic-only', 'synthetic-pollster'];
const walk = dir => readdirSync(dir).flatMap(n => { const p = join(dir, n); return statSync(p).isDirectory() ? walk(p) : [p]; });
const hits = [];
for (const file of walk(root)) {
  if (/synthetic/i.test(file)) hits.push(`${file} (file name)`);
  const text = readFileSync(file, 'utf8');
  for (const m of markers) if (text.includes(m)) hits.push(`${file} contains "${m}"`);
}
if (hits.length) { console.error(`Synthetic fixture content found in ${root}:\n${hits.join('\n')}`); process.exit(1); }
console.log(`No synthetic fixture content in ${root}.`);
