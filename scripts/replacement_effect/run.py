"""Stage55 pipeline: sample, fits, layer scores, descriptive inference and the Stage10 inventory-gap audit.

python -m scripts.replacement_effect.run [--check]

Recommendation only: nothing is adopted and selectedOperationalReplacementEffectPP stays null.
"""
from .analysis import SAMPLES, descriptive, materiality, neutrality, run_sample, s_overlap, standardised_context
from .common import PREFIX, ROOT, arguments, design, digest, pin, read, save, verify
from .sample import rows, stage10_gap, summarise


def build():
    table = rows()
    results = {name: run_sample(table, name) for name in SAMPLES}
    primary = results['primary']
    scores = {name: {k: v for k, v in r.items() if k != 'seatScores'} for name, r in results.items()}
    summary = {
        'stage': 55, 'question': design()['question'], 'finding': primary['finding'],
        'sensitivityFindings': {n: results[n]['finding'] for n in SAMPLES if n != 'primary'},
        'sample': summarise(table), 'primaryComparisons': primary['comparisons'],
        'affectedSeats': primary['affectedSeats'], 'affectedSeatsByElection': primary['affectedSeatsByElection'],
        'descriptive': descriptive(table), 'sOverlap': s_overlap(table),
        'materiality': materiality(primary['seatScores']), 'neutrality': neutrality(table),
        'standardisedContext': standardised_context(primary['seatScores']),
        'selectedOperationalReplacementEffectPP': None, 'stage10ShiftMinus6p64ppDeployed': False,
        'adopted': False}
    return table, results, scores, summary


def main():
    args = arguments()
    if args.check:
        verify()
    table, results, scores, summary = build()
    sample = {'rows': table, 'summary': summary['sample']}
    outputs = {'sample.json': sample, 'scores.json': scores, 'seat-scores.json': {n: r['seatScores'] for n, r in results.items()},
               'summary.json': summary, 'stage10-gap.json': stage10_gap(table)}
    if not args.check:
        save('input-contract.json', {'inputHashes': pin(), 'newResources': 0, 'dataSourcesJsonTouched': False})
    for name, value in outputs.items():
        save(name, value, args.check)
    code = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/replacement_effect').glob('*.py'))
    manifest = {'stage': 55, 'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
                'derivedArtifacts': {f'{PREFIX}/{n}': digest(f'{PREFIX}/{n}') for n in outputs} if not args.check else None,
                'code': {p: digest(p) for p in code}, 'dataSourcesJsonTouched': False, 'newSourcesOrAcquisition': False,
                'newNationalInference': False, 'hashesAreNotProofOfLinuxReproduction': True}
    if args.check:
        manifest['derivedArtifacts'] = {f'{PREFIX}/{n}': digest(f'{PREFIX}/{n}') for n in outputs}
    save('manifest.json', manifest, args.check)


if __name__ == '__main__':
    main()
