"""Generate/check the frozen Stage 16 review without changing earlier stages."""
import argparse
import hashlib
from . import analysis, inventory
from .common import DEST, INPUTS, ROOT, YEARS, digest, encode, read, write_or_check


def build():
    current = inventory.build()
    if encode(current) != (DEST / 'inventory.json').read_bytes():
        raise ValueError('Pre-fit inventory changed')
    spec = read(str((DEST / 'specification.json').relative_to(ROOT)))
    if spec['status'] != 'frozen_before_new_fits_and_scores' or spec['inventoryCommit'] != '20c9012':
        raise ValueError('Changed specification freeze')
    rows = analysis.assemble(current, {year: read(f'data/processed/elections/{year}.json') for year in YEARS},
             read('data/processed/models/party-vote-transform/backtest-records.json')['records'])
    results = analysis.analyses(rows, spec)
    comparison = analysis.comparisons(results, rows, spec)
    stage15 = read('data/processed/models/conditional-candidate-ledger/diagnostics.json')['records']
    overlap = []
    for year in (2011, 2017, 2023):
        own = [r for r in rows if r['targetYear'] == year]
        contests = {r['targetElectorateId'] for r in stage15 if r['targetYear'] == year}
        overlap.append({'targetYear': year, 'responsePartySeats': len(own),
            'responseContests': len({r['electorateId'] for r in own}),
            'stage15CommonContests': len(contests & {r['electorateId'] for r in own}),
            'pointComparisonAvailable': False,
            'reason': 'Stage15 has no point predictions; only shared conditional frame is compared.'})
    outputs = {'analysis.json': results, 'comparisons.json': comparison,
               'numerical-inputs.json': {'schemaVersion': 1, 'records': rows,
                   'roles': 'c1/y are outcomes; actual target local/national party inputs are conditional; sourceWon is source-election status.'},
               'stage15-overlap.json': {'records': overlap}}
    outputs['manifest.json'] = {'schemaVersion': 1, 'stage': 16,
        'inputHashes': {p: digest(p) for p in INPUTS},
        'inventoryHash': digest(str((DEST/'inventory.json').relative_to(ROOT))),
        'specificationHash': digest(str((DEST/'specification.json').relative_to(ROOT))),
        'codeHashes': {str(p.relative_to(ROOT)): digest(str(p.relative_to(ROOT)))
                       for p in sorted((ROOT/'scripts/models/conditional_nat_lab_response').glob('*.py'))},
        'outputHashes': {name: hashlib.sha256(encode(value)).hexdigest() for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    write_or_check(build(), args.check)
    print('Stage 16 chronological response review reproducible; operational selections null')


if __name__ == '__main__':
    main()
