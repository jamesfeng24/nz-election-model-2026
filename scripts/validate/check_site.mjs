// Checks the built public site (default site/): every page present with relative asset paths, nothing synthetic,
// nothing that names the tooling, and nothing but the site and the published forecast archive.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.argv[2] ?? 'site';
const pages = ['index.html', 'forecast/index.html', 'electorates/index.html', 'polls/index.html', 'methodology/index.html', 'archive/index.html', '404.html'];
const problems = [];
for (const page of pages) if (!existsSync(join(root, page))) problems.push(`missing ${page}`);
const walk = dir => readdirSync(dir).flatMap(n => { const p = join(dir, n); return statSync(p).isDirectory() ? walk(p) : [p]; });
const files = existsSync(root) ? walk(root) : [];
const forbidden = [/claude/i, /anthropic/i, /\bgenerated (by|with)\b/i, /<meta[^>]+name=["']generator/i];
for (const file of files) {
  const rel = relative(root, file).split('\\').join('/');
  if (/\.map$/.test(rel) || /(^|\/)README\.md$/.test(rel)) problems.push(`${rel}: not part of the site`);
  if (!/\.(html|js|css|json|geojson|svg|txt|ico|png|woff2?)$/.test(rel)) problems.push(`${rel}: unexpected file type`);
  const text = readFileSync(file, 'utf8');
  for (const re of forbidden) if (re.test(text)) problems.push(`${rel}: matches ${re}`);
  if (rel.endsWith('.html') && /(?:src|href)=["']\/(?!\/)/.test(text) && rel !== '404.html') problems.push(`${rel}: root-absolute path`);
}
if (problems.length) { console.error(`Site check failed for ${root}:\n- ${problems.join('\n- ')}`); process.exit(1); }
console.log(`Site check passed for ${root}: ${files.length} files.`);
