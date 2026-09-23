"""Rebuild identity with target/later winner flags removed for each holdout."""

import json

from scripts.models.candidate_persistence.identity import build_identity
from scripts.models.candidate_persistence.official import parse_members, project_members
from scripts.models.replacement_candidate.inventory import ADJACENT, build_inventory


INDEX_PATHS = ('data/raw/identity-parliament-former.html',
               'data/raw/identity-parliament-current.html')


def audit(root, inventory, occurrences, continuity, profiles, winners_by_year):
    """Check event class and eligibility with candidate/tenure records held fixed."""
    source_plan = json.loads((root / 'data/source-plans/candidate-persistence-sources.json').read_bytes())
    metadata = {item['id']: item for item in source_plan['sources']}
    members = [member for name in INDEX_PATHS
               for member in parse_members((root / name).read_bytes())]
    records = []
    for source_year, target_year in ADJACENT.items():
        earlier_winners = set().union(*(ids for year, ids in winners_by_year.items()
                                        if year < target_year))
        projected = project_members(occurrences, members, earlier_winners, metadata)
        links = build_identity(occurrences, projected)['links']
        changed = {row['eventId']: row for row in build_inventory(
            occurrences, links, continuity, earlier_winners, profiles)['records']
            if row['sourceYear'] == source_year}
        original = {row['eventId']: row for row in inventory
                    if row['sourceYear'] == source_year}
        if set(changed) != set(original):
            raise ValueError('Candidate comparison universe changed with winner flags')
        for event_id, row in sorted(original.items()):
            alternative = changed[event_id]
            stable = all(row[field] == alternative[field]
                         for field in ('sourceWasElected', 'outgoingStatus', 'identityClass',
                                       'primaryEligible', 'exclusionReasons'))
            records.append({'eventId': event_id, 'sourceYear': source_year,
                            'originalIdentityClass': row['identityClass'],
                            'counterfactualIdentityClass': alternative['identityClass'],
                            'originalPrimaryEligible': row['primaryEligible'],
                            'classificationAndEligibilityStable': stable})
    return {'schemaVersion': 1,
            'method': 'Rebuild Stage 8 profile projections and Stage 10 inventory after removing target/later winner flags, with candidacies, preserved raw indexes, dated profiles and earlier winners fixed.',
            'records': records,
            'counts': {'total': len(records),
                       'unstable': sum(not row['classificationAndEligibilityStable'] for row in records),
                       'unstablePrimary': sum(row['originalPrimaryEligible'] and
                                              not row['classificationAndEligibilityStable']
                                              for row in records)},
            'limitation': 'A stable flag counterfactual does not establish unbiased retrospective profile acquisition, publication or survival.'}
