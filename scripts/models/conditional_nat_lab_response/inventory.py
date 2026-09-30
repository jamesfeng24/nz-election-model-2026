"""Pre-fit party-seat frame and evidence audit, independent of target results."""
import argparse
from collections import Counter

from .common import DEST, INPUTS, PARTIES, YEARS, digest, read, validate_inputs, write_or_check


def unique(rows, field):
    result = {row[field]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate {field}')
    return result


def evidence_bundle():
    return {
        'occurrences': read('data/processed/models/candidate-overperformance/occurrences.json')['records'],
        'links': read('data/processed/models/candidate-persistence/person-links.json')['links'],
        'pairs': read('data/processed/models/candidate-persistence/pairs.json')['pairs'],
        'tenure': read('data/processed/models/freshman-incumbency/inventory.json')['records'],
        'replacement': read('data/processed/models/replacement-candidate/inventory.json')['records'],
        'stage13': read('data/processed/checkpoints/identity-evidence-pass/final/occurrence-evidence.json')['records'],
        'relations13': read('data/processed/checkpoints/identity-evidence-pass/final/relations.json')['records'],
    }


def endpoint(occurrence_id, links, stage13):
    link = links.get(occurrence_id)
    fresh = stage13.get(occurrence_id)
    return {
        'occurrenceId': occurrence_id,
        'stage8': ({key: link[key] for key in ('status', 'method', 'personId', 'evidence')}
                   if link else None),
        'stage13': ({key: fresh[key] for key in (
            'primaryOccurrenceConfidence', 'crossElectionRelation', 'careerHistoryCompleteness',
            'adjudicatedEvidence', 'strictPreTargetCutoffAvailability',
            'preflightOverSearchDeviation')} if fresh else None),
        'strictAsOfIdentityAvailability': 'unverified',
    }


def build_inventory(base, stage6, elections, evidence):
    """Source victory is historical; later outcomes never determine admission/status."""
    occurrences = {}
    for row in evidence['occurrences']:
        k = (row['year'], row['electorateType'], row['sourceElectorateNumber'], row['candidateAffiliationKey'])
        occurrences.setdefault(k, []).append(row)
    links = unique(evidence['links'], 'candidateOccurrenceId')
    fresh = unique(evidence['stage13'], 'candidateOccurrenceId')
    pairs = unique(evidence['pairs'], 'pairId')
    tenure = unique(evidence['tenure'], 'pairId')
    replacement = unique(evidence['replacement'], 'eventId')
    relations13 = {(r['sourceOccurrenceId'], r['targetOccurrenceId']): r for r in evidence['relations13']}
    candidates = {c['id']: c for election in elections.values()
                  for seat in election['electorates'] for c in seat['candidates']}
    original = {r['id'] for r in stage6['records'] if r['scope'] == 'general'}
    records = []
    for row in base:
        if not row['primary'] or row['canonicalPartyId'] not in PARTIES or row['electorateType'] != 'general':
            continue
        ids, reasons = [], []
        for year in (row['sourceYear'], row['targetYear']):
            matches = occurrences.get((year, 'general', int(row['electorateId'].rsplit('-', 1)[1]), row['canonicalPartyId']), [])
            if len(matches) != 1:
                reasons.append('missing_or_ambiguous_candidature')
                ids.append(None)
            else:
                occurrence = matches[0]
                ids.append(occurrence['candidateOccurrenceId'])
                if occurrence['candidateContestStatus'] != 'held':
                    reasons.append('cancelled_contest')
        eligible = not reasons
        if eligible != (row['id'] in original):
            raise ValueError(f'Stage 16 frame disagrees with original Stage 6 eligibility: {row["id"]} {reasons}')
        left, right = ids
        pair_id = f'{left}->{right}'
        p, t, r = pairs.get(pair_id), tenure.get(pair_id), replacement.get(pair_id)
        relation13 = relations13.get((left, right))
        records.append({
            'id': row['id'], 'party': row['canonicalPartyId'],
            'sourceYear': row['sourceYear'], 'targetYear': row['targetYear'],
            'electorateId': row['electorateId'], 'electorateName': row['electorateName'],
            'boundaryRegime': row['boundaryRegime'], 'eligible': eligible,
            'exclusionReasons': sorted(set(reasons)),
            'sourceOccurrenceId': left, 'targetOccurrenceId': right,
            'sourcePartySeatWon': bool(candidates[left]['elected']) if left else None,
            'sourceStatusInterpretation': 'source general-election winner only; not proof target candidate is incumbent or same person',
            'primaryCrossElectionRelation': 'unresolved',
            'targetCandidateIncumbency': 'unknown', 'strictAsOfStatusEligible': False,
            'sourceEvidence': endpoint(left, links, fresh),
            'targetEvidence': endpoint(right, links, fresh),
            'inheritedStage8Pair': ({key: p[key] for key in ('personId', 'sourceIdentityStatus',
                'targetIdentityStatus', 'outcomeDependencies', 'validationEligible')} if p else None),
            'inheritedStage9Tenure': ({key: t[key] for key in ('tenureCategory', 'tenureReason',
                'tenureEvidenceStatus', 'serviceRows', 'priorListService', 'sourceProfileId',
                'profilePublishedDate', 'profileRetrievedAt')} if t else None),
            'inheritedStage10': ({key: r[key] for key in ('identityClass', 'identityMethod',
                'sourceCareerHistory', 'incomingCareerHistory', 'sourceIdentityEvidence',
                'targetIdentityEvidence', 'stage10IdentityEvidence',
                'identityDependsOnTargetResult', 'identityDependsOnLaterOutcomeCoverage',
                'candidateStatusKnownBeforeTarget')} if r else None),
            'inheritedStage13Relation': relation13,
            'evidenceLimitation': 'Retrospective Stage8/9 winner/profile coverage; Stage10 outcome-related acquisition priority; Stage13 limited fixed pilot and deviations. No inherited class admits or stratifies a primary fit.',
        })
    records.sort(key=lambda r: r['id'])
    eligible = [r for r in records if r['eligible']]
    if len(records) != 384 or len(eligible) != 382:
        raise ValueError('Changed comparable general party-seat frame')
    counts = []
    for party in PARTIES:
        for year in (2011, 2017, 2023):
            rows = [r for r in eligible if r['party'] == party and r['targetYear'] == year]
            counts.append({'party': party, 'targetYear': year, 'n': len(rows),
                'sourceWon': sum(r['sourcePartySeatWon'] for r in rows),
                'sourceLost': sum(not r['sourcePartySeatWon'] for r in rows),
                'stage10Classes': dict(sorted(Counter(r['inheritedStage10']['identityClass']
                     if r['inheritedStage10'] else 'not_in_inventory' for r in rows).items())),
                'stage13PairRecords': sum(r['inheritedStage13Relation'] is not None for r in rows),
                'verifiedPrimaryRelations': sum(r['primaryCrossElectionRelation'] != 'unresolved' for r in rows)})
    return {'schemaVersion': 1, 'stage': 16, 'records': records, 'coverage': counts,
        'originalMaoriCoverageOnly': {'pairedLabour': 21, 'pairedNational': 0,
            'reason': 'Original descriptive scope preserved; no new Maori fit.'},
        'originalExclusions': stage6['excluded'],
        'conditioningDecision': 'No broad defensible prospective turnover/tenure cohort. Source party-seat victory is observed before target and complete, so a source-victory conditional association can be tested on the entire frame, not interpreted as a returning-incumbent effect.'}


def build():
    validate_inputs()
    return build_inventory(read('data/processed/models/party-vote-transform/backtest-records.json')['records'],
        read('data/processed/models/nat-lab-elasticity/records.json'),
        {year: read(f'data/processed/elections/{year}.json') for year in YEARS}, evidence_bundle())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    write_or_check({'inventory.json': result}, args.check)
    print('Stage 16 pre-fit inventory: 384 general pairs, 382 eligible')
    for row in result['coverage']:
        print(row)


if __name__ == '__main__':
    main()
