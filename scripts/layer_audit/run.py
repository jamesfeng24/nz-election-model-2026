"""Stage61 pipeline: layer calibration audit from frozen Stage45 to Stage47 inputs.

python -m scripts.layer_audit.run [--check]

Diagnostic only: nothing is adopted, refit or rescaled, and no national inference runs.
"""
from .analysis import layer_scale_audit, narrowing, stored_block
from .common import PREFIX, ROOT, arguments, design, digest, pin, read, save, verify


def build():
    contract = design()
    boot = contract['statistics']['bootstrap']
    estimated = dict(contract['scope']['estimatedFoldYears'])
    estimated['composed'] = [2017, 2020, 2023]
    scale = {layer: layer_scale_audit(layer) for layer in ('local_party', 'candidate')}
    shared = {layer: {c: scale[layer]['components'][c]['shared']['pooledStatistic'] for c in ('balance', 'mass')} for layer in scale}
    inventory = read('data/processed/uncertainty/inventory.json')
    frame = {'generalFrameRowsScored': {'party': len(inventory['partyRecords']), 'candidate': len(inventory['candidateRecords'])},
             'maoriFrameRowsNotScored': sum(r['scope'] == 'maori' for r in inventory['fullFrame']),
             'filter': 'electorate type (scope), never party'}
    return {'stage': 61, 'question': contract['question'], 'frame': frame, 'seatScale': scale,
            'storedIntervalCoverage': stored_block(boot, estimated), 'narrowing': narrowing(scale, shared),
            'adopted': False, 'refit': False, 'nationalMcmc': False}


def main():
    args = arguments()
    if args.check:
        verify()
    summary = build()
    if not args.check:
        save('input-contract.json', {'inputHashes': pin(), 'newResources': 0, 'dataSourcesJsonTouched': False})
    save('summary.json', summary, args.check)
    code = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/layer_audit').glob('*.py'))
    manifest = {'stage': 61, 'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
                'derivedArtifacts': {f'{PREFIX}/summary.json': digest(f'{PREFIX}/summary.json')} if (ROOT / PREFIX / 'summary.json').exists() else None,
                'code': {p: digest(p) for p in code}, 'dataSourcesJsonTouched': False, 'newSourcesOrAcquisition': False,
                'newNationalInference': False, 'hashesAreNotProofOfLinuxReproduction': True}
    save('manifest.json', manifest, args.check)


if __name__ == '__main__':
    main()
