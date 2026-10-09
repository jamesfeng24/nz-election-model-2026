/**
 * Node entry for publication (built with `npm run release:build`, run with `npm run release:publish -- ...`).
 *
 *   --bank PATH        draw bank written by `python -m scripts.nowcast_assembly.run --require-complete ...`
 *   --options PATH     JSON: snapshotId, createdAt, dataCutoff, electionId, electionDate, boundaryVersionId,
 *                      modelVersion, codeRevision, mmp {rulesVersion, rulesSourceIds, blocs}, nationalBasis,
 *                      limitations, probabilityMcseMax
 *   --archive DIR      public/forecasts for a model release; a non-public directory for a rehearsal
 *   --incumbents PATH  optional sitting-MP flags from `python -m scripts.site_incumbents.build`
 *   --evidence PATH    optional site evidence (polls used and national trend) from `python -m scripts.site_evidence.build`
 *   --supersedes ID    optional earlier snapshot this one corrects
 *   --rehearsal        allow a synthetic-fixture bank (never under public/)
 *
 * Not part of the site bundle: nothing in the app imports it.
 */
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { publish } from './publish';

function argument(args: string[], name: string): string | undefined {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
}

export async function main(args: string[]): Promise<number> {
  const bankPath = argument(args, '--bank'), optionsPath = argument(args, '--options'), archiveDir = argument(args, '--archive');
  if (!bankPath || !optionsPath || !archiveDir) {
    console.error('Usage: --bank PATH --options PATH --archive DIR [--evidence PATH] [--incumbents PATH] [--supersedes ID] [--rehearsal]');
    return 2;
  }
  const options = JSON.parse(await readFile(optionsPath, 'utf8'));
  const evidencePath = argument(args, '--evidence');
  if (evidencePath) options.evidence = JSON.parse(await readFile(evidencePath, 'utf8'));
  const incumbentsPath = argument(args, '--incumbents');
  if (incumbentsPath) options.incumbents = JSON.parse(await readFile(incumbentsPath, 'utf8'));
  const { probabilityMcseMax, ...snapshotOptions } = options;
  const result = await publish({
    bankText: await readFile(bankPath, 'utf8'), options: snapshotOptions, archiveDir,
    policy: { probabilityMcseMax, allowSynthetic: args.includes('--rehearsal') },
    supersedes: argument(args, '--supersedes') ?? null,
  }, {
    readText: async path => { try { return await readFile(path, 'utf8'); } catch { return null; } },
    writeText: async (path, content) => { await mkdir(dirname(path), { recursive: true }); await writeFile(path, content, 'utf8'); },
  });
  if (result.status === 'refused') {
    console.error('REFUSED:\n- ' + result.failures.join('\n- '));
    return 1;
  }
  console.log(`Published ${result.snapshot.snapshotId}:\n` + result.files.join('\n'));
  return 0;
}

if (typeof process !== 'undefined' && process.argv[1] && /cli\.(m?js|ts)$/.test(process.argv[1])) {
  main(process.argv.slice(2)).then(code => { process.exitCode = code; });
}
