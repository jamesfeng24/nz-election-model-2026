"""Pre-association category audit and exact saved-prediction common samples."""
import argparse
from scripts.models.complete_party_vector.inventory import evidence
from scripts.models.complete_party_vector.common import CONTINUITY, ALLIANCE
from .common import *
from .alignment import category_audit, align


def samples(construction, evaluation, features):
    actuals = evaluation['evaluationOnlyActuals']
    rows = keyed(features['contestRecords'], 'targetElectorateId')
    result = []
    for fold in construction['folds']:
        if fold['branch'] not in BRANCHES:
            continue
        ids = fold['evaluationIds']
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate fold contest')
        predictions = {m: keyed(fold['predictions'][m], 'targetElectorateId') for m in METHODS}
        sets = [set(p) for p in predictions.values()]
        if any(s != sets[0] for s in sets) or sets[0] not in (set(), set(ids)):
            raise ValueError('Model-specific/partial sample')
        candidates = {}
        for cid in ids:
            r = rows[cid]
            expected = [c['targetOccurrenceId'] for c in r['candidates']]
            if not expected or len(expected) != len(set(expected)):
                raise ValueError('Duplicate/incomplete standing slate')
            a = actuals[cid]['candidateShares']
            if set(a) != set(expected) or abs(sum(a.values())-1) > 1e-12:
                raise ValueError('Actual candidate-share denominator mismatch')
            for m, p in predictions.items():
                if cid in p:
                    q = p[cid]['candidateShares']
                    if set(q) != set(expected) or abs(sum(q.values())-1) > 1e-12 or any(v < 0 for v in q.values()):
                        raise ValueError('Prediction slate/denominator mismatch')
            candidates[cid] = expected
        result.append({'foldId': fold['id'], 'branch': fold['branch'], 'targetYear': fold['targetYear'],
            'sourceYear': fold['sourceYear'], 'view': fold['view'], 'trainingIds': fold['trainingIds'],
            'trainingEnvironments': fold['trainingTransitionEnvironments'], 'evaluationIds': ids,
            'commonFittedIds': sorted(sets[0]), 'candidateIds': candidates,
            'noFitIds': sorted(set(ids)-sets[0])})
    return result


def category_inventory(party_inventory, elections):
    result = []
    for r in party_inventory['categoryRelationships']:
        sy, ty = r['sourceYear'], r['targetYear']
        audit = category_audit(r['categories'])
        align(audit, {k: p['share'] for k, p in elections[sy]['parties'].items()},
              {k: p['share'] for k, p in elections[ty]['parties'].items()})
        result.append({'sourceYear': sy, 'targetYear': ty, 'categories': audit,
            'sourceNationalValidVotes': elections[sy]['nationalValidVotes'],
            'targetNationalValidVotes': elections[ty]['nationalValidVotes'],
            'diagnosticStatus': 'complete_whole_group_alignment',
            'warning': 'alliance_reorganization_counted_as_whole_group_entry_exit_not_constituent_switching'})
    return result


def build():
    elections, _ = evidence()
    party = read(S31+'input-inventory.json')
    return {'stage': 34, 'role': 'preanalysis_no_movement_error_associations',
        'categoryAudit': category_inventory(party, elections),
        'sampleManifest': samples(read(S33+'construction.json'), read(S33+'evaluation.json'), read(S32+'inventory.json')),
        'fullGeographyFrame': [{'geographyId': r['geographyId'], 'targetElectorateId': r['targetElectorateId'],
            'sourceYear': r['sourceYear'], 'targetYear': r['targetYear'], 'scope': r['scope'],
            'certifiedTwoSidedExact': r['certifiedTwoSidedExact'], 'contestStatus': r['contestStatus']}
            for r in read(GEO+'geography.json')['records']],
        'performanceSampleUnaffectedByMovementMissingness': True,
        'prospectivePublicationByCutoff': 'not_established_retrospective_preserved_evidence',
        'operationalSelection': None}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    result = build()
    save('inventory.json', result, a.check)
    if not a.check:
        _, paths = evidence()
        inputs = set(paths) | {CONTINUITY, ALLIANCE, 'scripts/transform/panel_config.py',
            'docs/stage34-analysis-contract.md', 'scripts/models/party_vote_transform/inputs.py',
            'scripts/models/complete_party_vector/inventory.py', 'scripts/models/complete_party_vector/construction.py'}
        inputs |= {S33+n for n in ('construction.json', 'evaluation.json', 'input-contract.json',
            'construction-manifest.json', 'evaluation-manifest.json', 'numerical-audit-manifest.json', 'verification-manifest.json')}
        inputs |= {S31+n for n in ('input-inventory.json', 'party-vectors.json', 'input-contract.json', 'construction-manifest.json')}
        inputs |= {S32+n for n in ('inventory.json', 'specification.json', 'fold-plan.json')}
        inputs |= {GEO+n for n in ('geography.json', 'source-contract.json', 'fold-plan.json')}
        save('input-contract.json', {'inputSha256': {p: digest(p) for p in sorted(inputs)},
            'wholeRegistryPinned': False, 'role': 'consumed_scientific_dependencies; prior_byte_snapshot_separate'})
        save('prior-data-contract.json', snapshot())
    phase('preanalysis', ['inventory.json', 'input-contract.json', 'prior-data-contract.json'],
          ['common', 'alignment', 'inventory'], a.check)
    verify_inputs()
    print('Stage34 preanalysis: mappings', len(result['categoryAudit']), 'folds', len(result['sampleManifest']), 'prior', preserve())


if __name__ == '__main__':
    main()
