// Checks the built site (default site/): every page present with relative asset paths, nothing synthetic,
// nothing that names the tooling, and nothing but the site and the published forecast archive.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.argv[2] ?? 'site';
const problems = [];

// The page list lives in src/app/pages.ts; read it here so a new page cannot be forgotten.
const pagePaths = [...readFileSync('src/app/pages.ts', 'utf8').matchAll(/path: '([a-z]+)'/g)].map((m) => m[1]);
if (pagePaths.length === 0) problems.push('could not read the page list from src/app/pages.ts');
const requiredFiles = ['index.html', ...pagePaths.map((path) => `${path}/index.html`), '404.html'];
for (const file of requiredFiles) if (!existsSync(join(root, file))) problems.push(`missing ${file}`);

const walk = (dir) =>
  readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
const files = existsSync(root) ? walk(root) : [];

const forbidden = [/claude/i, /anthropic/i, /\bgenerated (by|with)\b/i, /<meta[^>]+name=["']generator/i];
const rootAbsolute = /(?:src|href)=["'](\/(?!\/)[^"']*)["']/g;

for (const file of files) {
  const rel = relative(root, file).split('\\').join('/');
  if (/\.map$/.test(rel) || /(^|\/)README\.md$/.test(rel)) problems.push(`${rel}: not part of the site`);
  if (!/\.(html|js|css|json|geojson|svg|txt|ico|png|woff2?)$/.test(rel)) problems.push(`${rel}: unexpected file type`);
  const text = readFileSync(file, 'utf8');
  for (const pattern of forbidden) if (pattern.test(text)) problems.push(`${rel}: matches ${pattern}`);
  if (!rel.endsWith('.html')) continue;
  // 404.html is served from any address, so it may link to pages from the site root; nothing else may use root paths.
  for (const [, href] of text.matchAll(rootAbsolute)) {
    const isPageLink = rel === '404.html' && pagePaths.some((path) => href === `/${path}/`);
    if (!isPageLink) problems.push(`${rel}: root-absolute path ${href}`);
  }
}

if (problems.length) {
  console.error(`Site check failed for ${root}:\n- ${problems.join('\n- ')}`);
  process.exit(1);
}
console.log(`Site check passed for ${root}: ${files.length} files.`);
