"""Outcome-blind complete category and electorate inventory."""
import argparse
from collections import Counter

from scripts.models.party_vote_transform.inputs import Inputs
from scripts.transform.historical import key
from scripts.models.complete_party_vector.common import (
    ROOT, FRAME, CONTINUITY, ALLIANCE, STAGE5_CONTRACT,
    digest, read_json, verify_contract, write_or_check,
)

TRANSITIONS = ((2008, 2011), (2014, 2017), (2020, 2023))


def evidence():
    stage5 = read_json(STAGE5_CONTRACT)['inputHashes']
    for path, expected in stage5.items():
        if digest(path) != expected:
            raise ValueError(f'Changed Stage5 input: {path}')
    inputs = Inputs()
    elections = inputs.elections()
    paths = dict(inputs.hashes)
    for path in (FRAME, CONTINUITY, ALLIANCE, STAGE5_CONTRACT):
        paths[path] = digest(path)
    return elections, paths


def category_rows(elections, source_year, target_year, continuity):
    rows = [r for r in continuity if (r['sourceYear'], r['targetYear']) == (source_year, target_year)]
    source = elections[source_year]['parties']
    target = elections[target_year]['parties']
    if {r['canonicalPartyId'] for r in rows} != set(source) | set(target):
        raise ValueError('Incomplete national category continuity')
    output = []
    for r in sorted(rows, key=lambda row: row['canonicalPartyId']):
        cid = r['canonicalPartyId']
        expected = 'continuing' if cid in source and cid in target else 'entrant' if cid in target else 'exit'
        if (r['status'] == 'eligible') != (expected == 'continuing'):
            raise ValueError('Ambiguous category continuity')
        output.append({
            'categoryId': cid, 'relationship': expected,
            'sourcePartyKey': source[cid]['sourceKey'] if cid in source else None,
            'targetPartyKey': target[cid]['sourceKey'] if cid in target else None,
            'sourceNationalShare': source[cid]['share'] if cid in source else None,
            'suppliedTargetNationalShare': target[cid]['share'] if cid in target else None,
            'sourceNationalVotes': source[cid]['votes'] if cid in source else None,
            'targetNationalVotesScenario': target[cid]['votes'] if cid in target else None,
            'continuityEvidence': r['identityEvidence'],
        })
    return output


def frame_rows(elections, frame, categories):
    output = []
    for r in frame:
        source_year, target_year = r['sourceYear'], r['targetYear']
        if (source_year, target_year) not in TRANSITIONS:
            raise ValueError('Unexpected evaluation transition')
        source = elections[source_year]['scopes'][r['scope']][key(r['sourceSeatLabel'])]
        target = elections[target_year]['scopes'][r['scope']][key(r['targetSeatLabel'])]
        if source['id'] != r['sourceElectorateId'] or target['id'] != r['targetElectorateId']:
            # Māori IDs are source-table placeholders in Stage 5; validated
            # geography is represented by the Stage 14 frame ID and labels.
            if r['scope'] != 'maori':
                raise ValueError('Unvalidated general seat join')
        ids = {c['categoryId'] for c in categories[(source_year, target_year)]}
        if set(source['parties']) - ids or set(target['parties']) - ids:
            raise ValueError('Seat contains unaccounted party category')
        local = []
        for c in categories[(source_year, target_year)]:
            cid = c['categoryId']
            if c['relationship'] == 'exit':
                continue
            row = source['parties'].get(cid)
            local.append({
                'categoryId': cid,
                'sourceLocalShare': row['share'] if row is not None else None,
                'sourceLocalVotes': row['votes'] if row is not None else None,
                'sourceLocalStatus': 'entrant_no_source_category' if row is None else
                    'observed_zero' if row['votes'] == 0 else 'observed_positive',
            })
        output.append({
            'sourceYear': source_year, 'targetYear': target_year,
            'scope': r['scope'], 'contestStatus': r['contestStatus'],
            'sourceElectorateId': r['sourceElectorateId'],
            'targetElectorateId': r['targetElectorateId'],
            'sourceSeatLabel': r['sourceSeatLabel'],
            'targetSeatLabel': r['targetSeatLabel'],
            'sourceValidPartyVotes': source['validVotes'],
            'targetObservedValidPartyVotesEvaluationOnly': target['validVotes'],
            'sourceCategories': local,
            'constructionInputsExclude': ['targetLocalPartyVotes', 'candidateResults', 'winnerFlags'],
        })
    return sorted(output, key=lambda r: (r['targetYear'], r['scope'], r['targetElectorateId']))


def build():
    elections, paths = evidence()
    continuity = read_json(CONTINUITY)['records']
    frame = read_json(FRAME)['records']
    read_json(ALLIANCE)
    categories = {pair: category_rows(elections, *pair, continuity) for pair in TRANSITIONS}
    seats = frame_rows(elections, frame, categories)
    counts = Counter((r['targetYear'], r['scope'], r['contestStatus']) for r in seats)
    inventory = {
        'schemaVersion': 1, 'stage': 23, 'role': 'preconstruction_inventory_no_predictions_or_scores',
        'informationSet': 'source local party counts and supplied target national party result; target local denominator evaluation-only',
        'categoryRelationships': [
            {'sourceYear': pair[0], 'targetYear': pair[1], 'categories': categories[pair]}
            for pair in TRANSITIONS
        ],
        'nationalPopulations': [
            {'year': y, 'generalElectorates': len(elections[y]['scopes']['general']),
             'maoriElectorates': len(elections[y]['scopes']['maori']),
             'validPartyVotes': elections[y]['nationalValidVotes']}
            for y in sorted(elections)
        ],
        'frame': seats,
        'coverage': [{'targetYear': y, 'scope': scope, 'contestStatus': status, 'n': n}
                     for (y, scope, status), n in sorted(counts.items())],
        'sourceNotes': [
            'Stage5 official party tables validate all general/Māori seats and national totals.',
            'Internet MANA (2014) and Freedoms NZ (2023) remain election-local shared ballot groups; no constituent continuity is inferred.',
            'A zero count in a printed complete party table is observed zero, not a missing row.',
            'The 2023 Port Waikato candidate contest was cancelled, but its party ballot remains in the national party population.',
        ],
    }
    return inventory, {'schemaVersion': 1, 'inputHashes': dict(sorted(paths.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--init-contract', action='store_true')
    args = parser.parse_args()
    inventory, contract = build()
    if args.init_contract:
        write_or_check('source-contract.json', contract)
    else:
        verify_contract()
    write_or_check('input-inventory.json', inventory, args.check)
    print('Stage23 frame:', len(inventory['frame']))


if __name__ == '__main__':
    main()
