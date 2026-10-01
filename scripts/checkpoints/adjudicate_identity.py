"""Reproduce the final fixed-cohort evidence adjudication without fitting effects."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import html
import json
from pathlib import Path
import re

from scripts.checkpoints.acquired_sources import OLDER_PLANS, PLAN, validate_sources
from scripts.checkpoints.identity_evidence_pass import (
    BASE, COHORT, IDENTITY_PLANS, IDENTITY_SNAPSHOT, LEDGER, OCCURRENCES,
    PRESERVED, REGISTRY, ROOT, SNAPSHOT, _read, ordered_occurrences,
    verify_identity_snapshot, verify_snapshot,
)
from scripts.checkpoints.profile_supplement import OUTPUT as SUPPLEMENT
from scripts.checkpoints.search_identity import ACTIVE, BATCHES, merge_batches
from scripts.models.replacement_candidate.maori_winners import key as official_key
from scripts.transform.historical import candidate_table as historical_candidates
from scripts.transform.modern_tables import candidate_table as modern_candidates


CLAIMS = Path('data/source-plans/stage13-identity-adjudications.json')
NEW_SOURCES = PLAN
PREFLIGHT = BASE / 'tooling-preflight-audit.json'
OUT = BASE / 'final'
PRIMARY = {'primary_party', 'primary_official'}
ANCILLARY = {'candidate_submitted', 'journalistic_interview'}


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def compact(text):
    return re.sub(r'\s+', ' ', html.unescape(text)).casefold()


def validate_claims(claims, audit, sources):
    """Check each manually reviewed occurrence/source assertion and source tier."""
    by_id = {source['id']: source for source in sources}
    if len(by_id) != len(sources):
        raise ValueError('Ambiguous adjudication source ID')
    seen = set()
    new_ids = {source['id'] for source in read(NEW_SOURCES)['sources']}
    for claim in claims:
        order = claim['order']
        if not 1 <= order <= 415 or audit[order - 1]['candidateOccurrenceId'] != claim['candidateOccurrenceId']:
            raise ValueError('Adjudication occurrence/order mismatch')
        marker = (order, claim['sourceId'])
        if marker in seen:
            raise ValueError('Duplicate or conflicting occurrence/source claim')
        seen.add(marker)
        source = by_id.get(claim['sourceId'])
        if source is None:
            raise ValueError('Unregistered adjudication source')
        if (claim['evidenceOrigin'] == 'new_pass') != (claim['sourceId'] in new_ids):
            raise ValueError('Incorrect inherited/new evidence origin')
        tier, decision = claim['sourceTier'], claim['decision']
        if tier in ANCILLARY and decision != 'ancillary_only':
            raise ValueError('Ancillary source cannot confirm primary identity')
        if tier not in PRIMARY | ANCILLARY or decision not in {
                'confirmed', 'probable_alias', 'unresolved_name_conflict', 'ancillary_only'}:
            raise ValueError('Unknown source tier or adjudication')
        if tier in PRIMARY and decision == 'ancillary_only':
            raise ValueError('Primary source has no primary adjudication')
        raw = compact((ROOT / source['rawPath']).read_bytes().decode('utf-8', errors='replace'))
        if compact(claim['evidenceNeedle']) not in raw:
            raise ValueError(f'Adjudication evidence absent from raw source: {order}')
        if decision == 'confirmed' and not claim.get('sourceCandidateLabel'):
            raise ValueError('Confirmed claim lacks source-local candidate label')
    return by_id


def validate_ledger(audit, ledger, preflight, new_sources):
    if len(ledger['records']) != 415 or ledger['nextOrder'] != 416:
        raise ValueError('Acquisition is not complete')
    if len(new_sources) > 60:
        raise ValueError('Resource budget exceeded')
    acquired = set()
    searches = 0
    preflight_ids = set(preflight['occurrenceIds'])
    if len(preflight_ids) != 4:
        raise ValueError('Changed preflight deviation set')
    allowed = {'searched_unresolved', 'searched_unresolved_preflight',
               'preserved_direct_evidence_sufficient', 'source_acquired_pending_adjudication'}
    for original, item in zip(audit, ledger['records']):
        if original['order'] != item['order'] or original['candidateOccurrenceId'] != item['candidateOccurrenceId']:
            raise ValueError('Acquisition order changed')
        if item['state'] not in allowed or len(item['searchAttempts']) > 2:
            raise ValueError('Invalid acquisition state/search limit')
        searches += len(item['searchAttempts'])
        acquired.update(item['resourceIds'])
        if (item['state'] == 'searched_unresolved_preflight') != (item['candidateOccurrenceId'] in preflight_ids):
            raise ValueError('Preflight deviation omitted or added')
    if acquired != {source['id'] for source in new_sources}:
        raise ValueError('New source not traceable to acquisition ledger')
    return searches


def observed_outcomes(audit, occurrence_index):
    """Read results solely for post-adjudication coverage diagnostics."""
    general = {}
    for year in (2008, 2011, 2014, 2017, 2020, 2023):
        election = read(Path(f'data/processed/elections/{year}.json'))
        for seat in election['electorates']:
            for candidate in seat['candidates']:
                general[candidate['id']] = bool(candidate['elected'])
    selected_maori = [row for row in audit if row['scope'] == 'maori']
    by_seat = defaultdict(list)
    for row in selected_maori:
        occurrence = occurrence_index[row['candidateOccurrenceId']]
        by_seat[(occurrence['year'], occurrence['electorateName'])].append(occurrence)
    outcome = dict(general)
    for (year, _), candidates in by_seat.items():
        paths = {candidate['provenance']['inputPath'] for candidate in candidates}
        if len(paths) != 1:
            raise ValueError('Ambiguous official Māori candidate table')
        raw = (ROOT / paths.pop()).read_bytes()
        if year <= 2014:
            parsed = historical_candidates(raw)
        else:
            names = {row['electorateName'] for row in occurrence_index.values() if row['year'] == year}
            parsed = modern_candidates(raw, electorate_names=names)
        if len(parsed['candidates']) != len(candidates):
            raise ValueError('Māori candidate count does not match published table')
        winner_ids = []
        for candidate in candidates:
            matches = [row for row in parsed['candidates']
                       if row['name'] == candidate['sourceCandidateName']
                       and row['votes'] == candidate['sourcePublishedCandidateVotes']]
            if len(matches) != 1:
                raise ValueError('Māori candidate name/votes join is not unique')
            is_winner = official_key(candidate['sourceCandidateName']) == official_key(parsed['winnerName'])
            outcome[candidate['candidateOccurrenceId']] = is_winner
            if is_winner:
                winner_ids.append(candidate['candidateOccurrenceId'])
        if len(winner_ids) != 1:
            raise ValueError('Māori winner join is not unique')
    if set(row['candidateOccurrenceId'] for row in audit) - outcome.keys():
        raise ValueError('Missing observed outcome diagnostic')
    return outcome


def build_records(audit, supplement, ledger, claims, source_index, preflight):
    by_claim = defaultdict(list)
    for claim in claims:
        by_claim[claim['candidateOccurrenceId']].append(claim)
    supplement_by_id = {row['candidateOccurrenceId']: row for row in supplement}
    if len(supplement_by_id) != 415:
        raise ValueError('Incomplete preserved profile supplement')
    preflight_ids = set(preflight['occurrenceIds'])
    records, people, unresolved = [], [], []
    for row, item in zip(audit, ledger['records']):
        occurrence_id = row['candidateOccurrenceId']
        own_claims = by_claim[occurrence_id]
        confirmed = [claim for claim in own_claims if claim['decision'] == 'confirmed']
        if len(confirmed) > 1:
            raise ValueError('Two independent person assignments need manual relation review')
        primary = confirmed[0] if confirmed else None
        if primary:
            confidence = 'confirmed'
        elif any(claim['decision'] == 'probable_alias' for claim in own_claims):
            confidence = 'probable'
        else:
            confidence = 'unresolved'
        # An occurrence witness does not establish that another election's
        # same-named candidate is this person, or that they are different.
        person_claim_id = f"stage13:person-claim:{occurrence_id}" if primary else None
        evidence = []
        for claim in own_claims:
            source = source_index[claim['sourceId']]
            evidence.append({'sourceId': claim['sourceId'], 'origin': claim['evidenceOrigin'],
                             'sourceTier': claim['sourceTier'], 'decision': claim['decision'],
                             'sourceCandidateLabel': claim['sourceCandidateLabel'],
                             'historicalFactDate': None,
                             'factKnownByDate': source.get('publishedDate'),
                             'publicationDate': source.get('publishedDate'),
                             'retrievalDate': source.get('retrievedAt'),
                             'targetNominationCutoffVerified': False,
                             'reason': claim['reason']})
        if primary:
            people.append({'personEvidenceClaimId': person_claim_id,
                           'personId': None, 'sourceCandidateLabel': primary['sourceCandidateLabel'],
                           'establishedOccurrenceIds': [occurrence_id],
                           'sourceIds': [primary['sourceId']],
                           'careerHistoryCompleteness': 'unknown',
                           'crossElectionIdentityEstablished': False})
        supplement_row = supplement_by_id[occurrence_id]
        note = 'primary_occurrence_corroborated' if primary else (
            'alias_requires_bridge' if confidence == 'probable' else
            'name_conflict' if any(c['decision'] == 'unresolved_name_conflict' for c in own_claims)
            else 'no_primary_occurrence_specific_person_evidence')
        record = {'order': row['order'], 'candidateOccurrenceId': occurrence_id,
                  'sourceYear': row['sourceYear'], 'targetYear': row['targetYear'],
                  'role': row['role'], 'scope': row['scope'],
                  'sourceCandidateName': row['sourceCandidateName'],
                  'electorateName': row['electorateName'],
                  'sourceAffiliation': row['sourceAffiliation'],
                  'officialCandidatureSourceIds': row['preservedCandidacySourceIds'],
                  'personExistence': 'individually_corroborated' if primary else 'not_independently_resolved',
                  'primaryOccurrenceConfidence': confidence, 'personId': None,
                  'personEvidenceClaimId': person_claim_id,
                  'primaryAdjudicationReason': note,
                  'crossElectionRelation': 'unresolved',
                  'careerHistoryCompleteness': 'unknown',
                  'inheritedEvidence': row['inheritedEvidence'],
                  'inheritedReassessedConfidence': row['reassessedOccurrenceConfidence'],
                  'inheritedCareerHistory': row['careerHistory'],
                  'preservedProfileSupplement': supplement_row,
                  'adjudicatedEvidence': evidence,
                  'acquisitionState': item['state'],
                  'finalAdjudicationCompleted': True,
                  'searchAttempts': len(item['searchAttempts']),
                  'acquiredResourceIds': item['resourceIds'],
                  'preflightOverSearchDeviation': occurrence_id in preflight_ids,
                  'strictPreTargetCutoffAvailability': 'unknown',
                  'retrospectiveReconstruction': True}
        records.append(record)
        if confidence != 'confirmed':
            unresolved.append({'candidateOccurrenceId': occurrence_id, 'order': row['order'],
                               'confidence': confidence, 'reason': note,
                               'acquisitionState': item['state'],
                               'preflightOverSearchDeviation': occurrence_id in preflight_ids})
    return records, people, unresolved


def build_relations(records, cohort, occurrences):
    """Keep inherited same-person hypotheses separate from verified primary links."""
    by_id = {row['candidateOccurrenceId']: row for row in records}
    occurrence_by_id = {row['candidateOccurrenceId']: row for row in occurrences}
    relations = []
    for seat in cohort['frame']:
        if not seat['selected']:
            continue
        for source_id in seat['sourceOccurrenceIds']:
            source = occurrence_by_id[source_id]
            for target_id in seat['targetOccurrenceIds']:
                target = occurrence_by_id[target_id]
                if source['candidateAffiliationKey'] != target['candidateAffiliationKey']:
                    continue
                left, right = by_id[source_id], by_id[target_id]
                inherited_ids = [{route['personId'] for route in row['inheritedEvidence'].values()
                                  if route and route['personId']}
                                 for row in (left, right)]
                shared = sorted(inherited_ids[0] & inherited_ids[1])
                two_direct_winner_anchors = bool(shared and all(
                    row['inheritedEvidence']['stage8']['confidence'] == 'confirmed'
                    and row['inheritedEvidence']['stage8']['outcomeCoverage'] == 'retrospective_winner_anchor'
                    for row in (left, right)))
                relations.append({'sourceOccurrenceId': source_id,
                                  'targetOccurrenceId': target_id,
                                  'sourceYear': seat['sourceYear'], 'targetYear': seat['targetYear'],
                                  'scope': seat['scope'], 'samePartyKey': source['candidateAffiliationKey'],
                                  'verifiedRelation': 'unresolved',
                                  'retrospectiveInheritedRelation': (
                                      'same_profile_two_direct_winner_anchors' if two_direct_winner_anchors else
                                      'unverified_same_person_hypothesis' if shared else 'none'),
                                  'inheritedSamePersonHypothesisIds': shared,
                                  'nameStringEqual': source['sourceCandidateName'] == target['sourceCandidateName'],
                                  'reason': 'No occurrence-specific cross-election relation corroboration; names and party do not prove continuity or replacement.'})
    return relations


def coverage(records, outcomes, searches, new_sources):
    grouped = defaultdict(list)
    for row in records:
        group = (f"{row['sourceYear']}→{row['targetYear']}", row['scope'], row['role'],
                 'later_observed_winner' if outcomes[row['candidateOccurrenceId']] else 'later_observed_loser')
        grouped[group].append(row)
    groups = []
    for key, rows in sorted(grouped.items()):
        ordinary = [row for row in rows if not row['preflightOverSearchDeviation']]
        groups.append({'transition': key[0], 'scope': key[1], 'role': key[2], 'observedOutcome': key[3],
                       'n': len(rows), 'primaryConfirmed': sum(r['primaryOccurrenceConfidence'] == 'confirmed' for r in rows),
                       'primaryProbable': sum(r['primaryOccurrenceConfidence'] == 'probable' for r in rows),
                       'primaryUnresolved': sum(r['primaryOccurrenceConfidence'] == 'unresolved' for r in rows),
                       'withoutPreflightDeviationN': len(ordinary),
                       'withoutPreflightDeviationConfirmed': sum(r['primaryOccurrenceConfidence'] == 'confirmed' for r in ordinary)})
    ordinary = [row for row in records if not row['preflightOverSearchDeviation']]
    return {'schemaVersion': 1, 'stage': 13, 'cohortSize': len(records),
            'acquisitionStates': dict(sorted(Counter(row['acquisitionState'] for row in records).items())),
            'primaryIdentityConfidence': dict(sorted(Counter(row['primaryOccurrenceConfidence'] for row in records).items())),
            'inheritedReassessedConfidence': dict(sorted(Counter(row['inheritedReassessedConfidence'] for row in records).items())),
            'preservedSupplementStatuses': dict(sorted(Counter(row['preservedProfileSupplement']['status'] for row in records).items())),
            'adjudicationReasons': dict(sorted(Counter(row['primaryAdjudicationReason'] for row in records).items())),
            'adjudicatedSourceTiers': dict(sorted(Counter(evidence['sourceTier']
                for row in records for evidence in row['adjudicatedEvidence']).items())),
            'formalSearchAttempts': searches, 'newUniqueResources': len(new_sources),
            'preflightDeviationCases': len(records) - len(ordinary),
            'withoutPreflightDeviation': {'n': len(ordinary),
                'primaryConfirmed': sum(row['primaryOccurrenceConfidence'] == 'confirmed' for row in ordinary)},
            'notReachedBudgetExhausted': 0, 'groups': groups,
            'interpretation': 'Fixed unequal-probability seat sample; descriptive coverage only. Outcome groups are post-acquisition diagnostics, not selection or proof of prospective availability.'}


def build():
    audit = read(PRESERVED)['records']
    cohort = read(COHORT)
    occurrences = read(OCCURRENCES)['records']
    occurrence_index = {row['candidateOccurrenceId']: row for row in occurrences}
    if len(audit) != 415 or [row['candidateOccurrenceId'] for row in audit] != ordered_occurrences(cohort):
        raise ValueError('Changed fixed cohort or adjudication order')
    initial = read(LEDGER)
    batches = [read(path.relative_to(ROOT)) for path in sorted((ROOT / BATCHES).glob('*.json'))]
    ledger = merge_batches(initial, batches)
    if ledger != read(ACTIVE):
        raise ValueError('Replayed search batches disagree with saved ledger')
    preflight, supplement = read(PREFLIGHT), read(SUPPLEMENT)['records']
    new_plan = read(NEW_SOURCES)
    older = [read(path) for path in OLDER_PLANS]
    validate_sources(new_plan, older, lambda path: (ROOT / path).read_bytes())
    verify_snapshot(read(SNAPSHOT), read(REGISTRY))
    verify_identity_snapshot(read(IDENTITY_SNAPSHOT), [read(path) for path in IDENTITY_PLANS])
    searches = validate_ledger(audit, ledger, preflight, new_plan['sources'])
    claims = read(CLAIMS)['claims']
    source_index = validate_claims(claims, audit,
                                   new_plan['sources'] + [source for plan in older for source in plan['sources']])
    records, people, unresolved = build_records(audit, supplement, ledger, claims, source_index, preflight)
    relations = build_relations(records, cohort, occurrences)
    outcomes = observed_outcomes(audit, occurrence_index)
    outputs = {'occurrence-evidence.json': {'schemaVersion': 1, 'stage': 13, 'records': records},
               'person-evidence.json': {'schemaVersion': 1, 'stage': 13, 'records': people},
               'relations.json': {'schemaVersion': 1, 'stage': 13, 'records': relations},
               'unresolved-conflicts.json': {'schemaVersion': 1, 'stage': 13, 'records': unresolved},
               'coverage.json': coverage(records, outcomes, searches, new_plan['sources'])}
    inputs = [PRESERVED, SUPPLEMENT, ACTIVE, PREFLIGHT, COHORT, OCCURRENCES,
              CLAIMS, NEW_SOURCES, SNAPSHOT, IDENTITY_SNAPSHOT]
    inputs += [path.relative_to(ROOT) for path in sorted((ROOT / BATCHES).glob('*.json'))]
    inputs += [Path(f'data/processed/elections/{year}.json') for year in (2008, 2011, 2014, 2017, 2020, 2023)]
    outputs['manifest.json'] = {'schemaVersion': 1, 'stage': 13,
         'inputSha256': {str(path): digest(path) for path in inputs},
         'outputSha256': {name: sha256(encode(value)).hexdigest() for name, value in outputs.items()},
         'generatorSha256': digest(Path('scripts/checkpoints/adjudicate_identity.py'))}
    return outputs


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = build()
    for name, payload in outputs.items():
        path = ROOT / OUT / name
        expected = encode(payload)
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit(f'Changed or missing Stage 13 output: {name}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    counts = outputs['coverage.json']['primaryIdentityConfidence']
    print(f'Stage 13 final evidence: 415 occurrences, {counts.get("confirmed", 0)} confirmed, '
          f'{counts.get("probable", 0)} probable, {counts.get("unresolved", 0)} unresolved')


if __name__ == '__main__':
    main()
