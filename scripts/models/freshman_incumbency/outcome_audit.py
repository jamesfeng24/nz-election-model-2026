"""Rebuild inherited identity links under target/later winner counterfactuals."""

import json

from scripts.models.candidate_persistence.identity import build_identity
from scripts.models.candidate_persistence.official import parse_members, project_members
from scripts.models.candidate_persistence.pairs import build_pairs
from scripts.models.freshman_incumbency.inventory import build_inventory


TRANSITIONS = ((2008, 2011), (2014, 2017), (2020, 2023))
INDEX_PATHS = ('data/raw/identity-parliament-former.html',
               'data/raw/identity-parliament-current.html')


def _elected_by_year(root):
    result = {}
    for year in (2008, 2011, 2014, 2017, 2020, 2023):
        election = json.loads((root / f'data/processed/elections/{year}.json').read_bytes())
        result[year] = {candidate['id'] for seat in election['electorates']
                        for candidate in seat['candidates'] if candidate['elected']}
    return result


def _comparable_source_winner(row):
    return row['sourceWasElected'] and 'not_comparable_stage8_pair' not in row['exclusionReasons']


def audit(root, inventory, profiles):
    """Hold records/tenure fixed and remove target/later wins for each transition."""
    occurrences = json.loads((root / 'data/processed/models/candidate-overperformance/occurrences.json').read_bytes())['records']
    source_plan = json.loads((root / 'data/source-plans/candidate-persistence-sources.json').read_bytes())
    source_metadata = {item['id']: item for item in source_plan['sources']}
    members = [member for name in INDEX_PATHS
               for member in parse_members((root / name).read_bytes())]
    by_year = _elected_by_year(root)
    records = []
    newly_comparable = []
    for source_year, target_year in TRANSITIONS:
        # Winners before the target remain. Target and every later winner flag is removed.
        counterfactual_elected = set().union(*(ids for year, ids in by_year.items()
                                               if year < target_year))
        projected = project_members(occurrences, members, counterfactual_elected, source_metadata)
        links = build_identity(occurrences, projected)['links']
        pairs = build_pairs(occurrences, links)['pairs']
        counterfactual = {row['pairId']: row for row in
                          build_inventory(pairs, occurrences, profiles, counterfactual_elected)['records']
                          if row['sourceYear'] == source_year}
        original_ids = {row['pairId'] for row in inventory if row['sourceYear'] == source_year
                        and _comparable_source_winner(row)}
        newly_comparable.extend(sorted(pair_id for pair_id, row in counterfactual.items()
                                     if _comparable_source_winner(row) and pair_id not in original_ids))
        for original in inventory:
            if original['sourceYear'] != source_year or not _comparable_source_winner(original):
                continue
            changed = counterfactual.get(original['pairId'])
            still_comparable = bool(changed and _comparable_source_winner(changed))
            classification_stable = bool(still_comparable and all(
                original[field] == changed[field]
                for field in ('tenureCategory', 'tenureReason', 'sourceProfileId',
                              'primaryEligible', 'exclusionReasons')))
            records.append({'pairId': original['pairId'], 'sourceYear': source_year,
                            'originalPrimaryEligible': original['primaryEligible'],
                            'counterfactualPairPresent': changed is not None,
                            'counterfactualSourceWinnerComparable': still_comparable,
                            'classificationStable': classification_stable,
                            'correctedEvaluationEligible': original['primaryEligible'] and classification_stable,
                            'reason': ('outcome_independent' if classification_stable else
                                       'inherited_link_or_classification_depends_on_target_or_later_winner')})
    records.sort(key=lambda row: (row['sourceYear'], row['pairId']))
    kept = {row['pairId'] for row in records if row['classificationStable']}
    evaluated = {row['pairId'] for row in records if row['correctedEvaluationEligible']}
    return {'schemaVersion': 1, 'method': 'Rebuild Stage 8 person links and pairs after setting target/later elected flags false in memory for each transition; candidate records, prior winners, official indexes and parsed tenure evidence remain fixed.',
            'records': records,
            'counts': {'sourceWinnerComparableBefore': len(records),
                       'sourceWinnerComparableCounterfactualStable': len(kept),
                       'primaryBefore': sum(row['originalPrimaryEligible'] for row in records),
                       'correctedEvaluation': len(evaluated),
                       'counterfactualNewComparablePairIds': newly_comparable,
                       'lostPrimaryPairIds': [row['pairId'] for row in records
                                              if row['originalPrimaryEligible'] and not row['correctedEvaluationEligible']]},
            'limitation': 'This flag counterfactual does not prove retrospective profile publication or initial source acquisition was independent of later career success.'}, kept, evaluated
