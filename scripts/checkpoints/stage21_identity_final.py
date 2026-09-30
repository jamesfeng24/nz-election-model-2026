"""Reproduce the bounded Stage 21 relationship pilot and its evidence audit."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256

from scripts.checkpoints.stage21_identity_pilot import DEST, digest, encode, read


CLAIMS = 'data/processed/checkpoints/stage21-identity-pilot/claim-ledger.json'
PLAN = 'data/processed/checkpoints/stage21-identity-pilot/acquisition-plan.json'
PRESERVED = 'data/processed/checkpoints/stage21-identity-pilot/preserved-review.json'
SEARCHES = 'data/processed/checkpoints/stage21-identity-pilot/search-attempts.json'
VOTES = 'data/processed/models/candidate-overperformance/occurrences.json'
SOURCE_IDS = (
    'stage21-identity-act-david-seymour-2026-09-30',
    'stage21-identity-labour-willow-jean-prime-2026-09-30',
)
CAREER_PASSAGES = {
    SOURCE_IDS[0]: {
        'casePosition': 10,
        'historicalFact': 'First elected to the Epsom electorate in 2014; later elected four times.',
        'factDateOrInterval': '2014 election; subsequent election dates not specified on page',
        'exactPassage': 'First elected by his Epsom Electorate neighbours in 2014, he has now been elected four times.',
    },
    SOURCE_IDS[1]: {
        'casePosition': 19,
        'historicalFact': 'List MP in 2017 and Northland electorate winner in 2020.',
        'factDateOrInterval': '2017 list service; 2020 electorate victory',
        'exactPassage': 'I was a Labour List Member of Parliament in 2017, and won the seat of Northland in the 2020 election.',
    },
}


def source_contract(registry):
    """Select only consumed records; unrelated source registrations are immaterial."""
    records = []
    for source_id in SOURCE_IDS:
        matches = [r for r in registry['sources'] if r['id'] == source_id]
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous pilot source: {source_id}')
        record = matches[0]
        if digest(record['rawPath']) != record['sha256']:
            raise ValueError(f'Changed pilot raw source: {source_id}')
        passage = CAREER_PASSAGES[source_id]['exactPassage']
        if passage not in (DEST.parents[3] / record['rawPath']).read_text():
            raise ValueError(f'Pilot evidence passage not present: {source_id}')
        records.append(record)
    return records


def observed_winners(vote_records):
    """Derive later outcome diagnostics from official candidate counts, never eligibility."""
    contests = defaultdict(list)
    for row in vote_records:
        if row['candidateContestStatus'] != 'held':
            continue
        contests[row['electorateId']].append(row)
    result = {}
    for rows in contests.values():
        peak = max(r['sourcePublishedCandidateVotes'] for r in rows)
        winners = [r for r in rows if r['sourcePublishedCandidateVotes'] == peak]
        if len(winners) != 1:
            continue
        for row in rows:
            result[row['candidateOccurrenceId']] = (
                row['candidateOccurrenceId'] == winners[0]['candidateOccurrenceId'])
    return result


def adjudicate(claims, plan, preserved, searches, winners, sources):
    selected = plan['selection']['selectedCaseIds']
    by_claim = {r['caseId']: r for r in claims['cases']}
    by_preserved = {r['caseId']: r for r in preserved['records']}
    if len(by_claim) != len(claims['cases']) or len(by_preserved) != len(preserved['records']):
        raise ValueError('Duplicate claim or preserved evidence case ID')
    if len(selected) != 24 or len(set(selected)) != 24:
        raise ValueError('Changed fixed pilot cohort')
    if len(searches['collectionQueries']) > 8 or len(searches['resources']) > 30:
        raise ValueError('Pilot collection or resource budget exceeded')
    if set(searches['caseQueries']) != set(selected):
        raise ValueError('Searches do not cover the fixed cohort')
    if len(sources) != len(SOURCE_IDS):
        raise ValueError('Incomplete stage-specific source contract')
    results = []
    for position, case_id in enumerate(selected, 1):
        case = by_claim[case_id]
        review = by_preserved[case_id]
        attempts = searches['caseQueries'][case_id]
        if len(attempts) != 2 or [a['attempt'] for a in attempts] != [1, 2]:
            raise ValueError(f'Incomplete or excessive fixed searches: {case_id}')
        if review['relationshipFinding'] != 'unresolved_explicit_cross_occurrence_bridge':
            raise ValueError(f'Preserved review changed: {case_id}')
        career = []
        for source in sources:
            passage = CAREER_PASSAGES[source['id']]
            if passage['casePosition'] != position:
                continue
            career.append({
                'claim': passage['historicalFact'],
                'historicalFactDateOrInterval': passage['factDateOrInterval'],
                'exactSupportingPassage': passage['exactPassage'],
                'sourceId': source['id'], 'rawSha256': source['sha256'],
                'sourceType': 'official_party_biography',
                'publicationDate': None, 'retrievedAt': source['retrievedAt'],
                'availableBeforeTargetNominationClose': 'unknown',
                'careerHistoryCompleteness': 'unknown',
                'scopeLimit': 'Historical service only; not an exact source-to-target nomination bridge.',
            })
        results.append({
            'position': position, 'caseId': case_id,
            'sourceOccurrenceId': case['sourceOccurrenceId'],
            'targetOccurrenceId': case['targetOccurrenceId'],
            'transition': case['transition'], 'scope': case['scope'],
            'partyKey': case['partyKey'], 'ambiguityType': case['ambiguityType'],
            'personExistence': {'source': case['existingEvidence']['sourcePersonExistence'],
                                'target': case['existingEvidence']['targetPersonExistence']},
            'occurrenceLink': {
                'sourceInherited': review['sourceStage8']['confidence'],
                'targetInherited': review['targetStage8']['confidence'],
                'sourceOfficialCandidature': 'established_election_local_only',
                'targetOfficialCandidature': 'established_election_local_only',
                'newCrossElectionOccurrenceConfirmation': False,
            },
            'relationship': 'unresolved',
            'relationshipConfidence': 'unresolved',
            'relationshipEvidence': [],
            'careerClaims': career,
            'careerHistoryCompleteness': 'unknown',
            'searchState': 'investigated_unresolved',
            'searchAttempts': 2,
            'sourceWinnerDiagnosticOnly': winners.get(case['sourceOccurrenceId']),
            'targetWinnerDiagnosticOnly': winners.get(case['targetOccurrenceId']),
            'availability': 'election-local facts known after official count; new biographies retrospective with unknown publication dates',
            'adjudicationReason': 'Neither preserved nor newly retrieved evidence explicitly connects both exact election-local nominations or independently establishes two distinct people.',
        })
    return results


def coverage(rows, claims, searches):
    counts = Counter((r['transition'], r['scope']) for r in rows)
    by_party = Counter((r['transition'], r['partyKey']) for r in rows)
    by_outcome = Counter((r['transition'], str(r['sourceWinnerDiagnosticOnly']),
                          str(r['targetWinnerDiagnosticOnly'])) for r in rows)
    role_outcomes = Counter((r['transition'], r['scope'], role,
                             str(r[role + 'WinnerDiagnosticOnly']))
                            for r in rows for role in ('source', 'target'))
    full_strata = Counter((r['transition'], r['ambiguityType']) for r in claims['cases'])
    pilot_strata = Counter((r['transition'], r['ambiguityType']) for r in rows)
    return {
        'fullPairFrame': len(claims['cases']),
        'selected': len(rows),
        'selectedByTransitionScope': [{'transition': t, 'scope': s, 'count': n}
                                      for (t, s), n in sorted(counts.items())],
        'selectedByTransitionParty': [{'transition': t, 'partyKey': p, 'count': n}
                                      for (t, p), n in sorted(by_party.items())],
        'selectedByObservedSourceTargetOutcome': [
            {'transition': t, 'sourceWinner': s, 'targetWinner': u, 'count': n}
            for (t, s, u), n in sorted(by_outcome.items())],
        'selectedByRoleScopeObservedOutcome': [
            {'transition': t, 'scope': s, 'role': role, 'winner': winner, 'count': n}
            for (t, s, role, winner), n in sorted(role_outcomes.items())],
        'samplingFractionsByStratum': [
            {'transition': t, 'ambiguityType': a, 'fullFrame': n,
             'selected': pilot_strata.get((t, a), 0),
             'fraction': pilot_strata.get((t, a), 0) / n}
            for (t, a), n in sorted(full_strata.items())],
        'sourceOccurrencesElectionLocalEstablished': len(rows),
        'targetOccurrencesElectionLocalEstablished': len(rows),
        'confirmedNewCrossElectionRelations': 0,
        'differentPersonNewRelations': 0,
        'unresolvedRelations': sum(r['relationship'] == 'unresolved' for r in rows),
        'careerClaimsFromNewResources': sum(len(r['careerClaims']) for r in rows),
        'collectionQueries': len(searches['collectionQueries']),
        'targetedQueries': sum(map(len, searches['caseQueries'].values())),
        'newUniqueResources': len(searches['resources']),
        'resourcesPerUsableNewRelation': None,
        'scopeWarning': 'Stratified pilot fractions differ from the full pair frame; unweighted pilot coverage is not representative. Party biographies are retrospective and availability can depend on later prominence.',
    }


def build():
    claims, plan, preserved, searches, votes, registry = map(read, (
        CLAIMS, PLAN, PRESERVED, SEARCHES, VOTES, 'data/sources.json'))
    sources = source_contract(registry)
    rows = adjudicate(claims, plan, preserved, searches,
                      observed_winners(votes['records']), sources)
    adjudication = {'schemaVersion': 1, 'stage': 21, 'selectedRecords': rows,
                    'interpretation': 'New career facts are separate from unresolved exact cross-election relationship claims. No earlier adjudication is overwritten.'}
    report = {'schemaVersion': 1, 'stage': 21, 'coverage': coverage(rows, claims, searches),
              'unresolvedCaseIds': [r['caseId'] for r in rows], 'conflicts': [],
              'rejectedLeadClasses': ['matching labels', 'result snippets',
                                      'single-election nomination',
                                      'retrospective party biography without exact two-occurrence bridge'],
              'sourceRoutes': {'official_party_biography': {'resources': 2,
                                                            'careerFacts': 2,
                                                            'exactRelations': 0}}}
    contract = {'schemaVersion': 1, 'stage': 21,
                'sourceRecords': sources,
                'inputSha256': {p: digest(p) for p in (CLAIMS, PLAN, PRESERVED, SEARCHES, VOTES)},
                'generatorSha256': digest('scripts/checkpoints/stage21_identity_final.py'),
                'outputSha256': {'adjudication.json': sha256(encode(adjudication)).hexdigest(),
                                 'coverage.json': sha256(encode(report)).hexdigest()}}
    return {'adjudication.json': adjudication, 'coverage.json': report,
            'final-source-contract.json': contract}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, output in build().items():
        path = DEST / name
        if args.check:
            if path.read_bytes() != encode(output):
                raise ValueError(f'Changed Stage21 final pilot artifact: {name}')
        else:
            path.write_bytes(encode(output))
    print('Stage21 identity pilot: 24 reviewed; no new exact relation bridge')


if __name__ == '__main__':
    main()
