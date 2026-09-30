"""Reproduce Stage 20's preserved-source feature and provenance ledger."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from scripts.checkpoints.complete_share_features import (
    SOURCE_YEARS, TARGET_YEARS, build_feature_inventory)
from scripts.checkpoints.complete_share_feature_rank import build as rank_build
from scripts.validate.source_files import verify_source_files


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/complete-share-feature-applicability'
FRAME = 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json'
MAPPING = 'data/processed/models/conditional-candidate-share/inventory.json'
CONTINUITY = 'data/processed/models/party-vote-transform/party-continuity.json'
STAGE11_SOURCES = 'data/source-plans/stage11-local-split-sources.json'
STAGE18_SOURCES = 'data/source-plans/stage18-conditional-candidate-share-sources.json'
ELECTIONS = {year: f'data/processed/elections/{year}.json'
             for year in (*SOURCE_YEARS, *TARGET_YEARS)}
SPLITS = {year: f'data/processed/split-votes/{year}.json' for year in SOURCE_YEARS}
INPUTS = (FRAME, MAPPING, CONTINUITY, STAGE11_SOURCES, STAGE18_SOURCES,
          *ELECTIONS.values(), *SPLITS.values())


def read(path):
    return json.loads((ROOT / path).read_bytes())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def source_snapshot(frame, elections, splits, registry, stage11, stage18):
    live = registry['sources']
    by_id = {row['id']: row for row in live}
    if len(by_id) != len(live):
        raise ValueError('Ambiguous live source ID')
    prior = {}
    for plan in (stage11, stage18):
        for row in plan['sources']:
            if row['id'] in prior and prior[row['id']] != row:
                raise ValueError('Conflicting inherited source records')
            prior[row['id']] = row
    ids = set()
    for record in frame['records']:
        if record['scope'] != 'general':
            continue
        source_year, source_id = record['sourceYear'], record['sourceElectorateId']
        target_year, target_id = record['targetYear'], record['targetElectorateId']
        source_seat = next(s for s in elections[source_year]['electorates']
                           if s['id'] == source_id)
        target_seat = next(s for s in elections[target_year]['electorates']
                           if s['id'] == target_id)
        ids.update(source_seat['sourceIds'])
        ids.update(target_seat['sourceIds'])
        matching = [m for m in splits[source_year]['matrices']
                    if m['electorateId'] == source_id]
        if len(matching) != 1:
            raise ValueError('Missing or ambiguous required source split matrix')
        ids.update(matching[0]['sourceIds'])
    if any(sid not in prior or sid not in by_id or by_id[sid] != prior[sid]
           for sid in ids):
        raise ValueError('Changed, missing or unregistered required source record')
    selected = [by_id[sid] for sid in sorted(ids)]
    verify_source_files(ROOT, {'schemaVersion': 1, 'sources': selected})
    return {'schemaVersion': 1, 'stage': 20,
            'selection': 'actually consumed source/target general election seats and source local split matrices on fixed frame',
            'sources': selected}


def build():
    frame, mapping, continuity = (read(path) for path in (FRAME, MAPPING, CONTINUITY))
    elections = {year: read(path) for year, path in ELECTIONS.items()}
    splits = {year: read(path) for year, path in SPLITS.items()}
    sources = source_snapshot(frame, elections, splits, read('data/sources.json'),
                              read(STAGE11_SOURCES), read(STAGE18_SOURCES))
    features = build_feature_inventory(frame, mapping, elections, splits,
                                       continuity['records'])
    outputs = {'source-contract.json': sources, 'feature-inventory.json': features,
               'design-audit.json': rank_build(features)}
    outputs['manifest.json'] = {
        'schemaVersion': 1, 'stage': 20,
        'phase': 'preserved_evidence_applicability_before_any_fit_or_score',
        'generatorSha256': {name: digest('scripts/checkpoints/' + name)
                            for name in ('complete_share_features.py',
                                         'complete_share_feature_rank.py',
                                         'complete_share_feature_run.py')},
        'inputSha256': {path: digest(path) for path in INPUTS},
        'requiredRawSourceCount': len(sources['sources']),
        'outputSha256': {name: sha256(encode(value)).hexdigest()
                         for name, value in outputs.items()}}
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != encode(data):
                raise ValueError(f'Changed Stage 20 {name}')
        else:
            path.write_bytes(encode(data))
    print(outputs['feature-inventory.json']['summary'])


if __name__ == '__main__':
    main()
