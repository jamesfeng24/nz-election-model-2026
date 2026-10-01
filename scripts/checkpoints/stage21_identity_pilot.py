"""Freeze Stage 21's complete claim ledger and bounded pilot before searching."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata


ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data/processed/checkpoints/stage21-identity-pilot'
FRAME = 'data/processed/checkpoints/complete-candidate-baseline/input-inventory.json'
OCCURRENCES = 'data/processed/models/candidate-overperformance/occurrences.json'
CONTINUITY = 'data/processed/models/party-vote-transform/party-continuity.json'
STAGE10 = 'data/processed/models/replacement-candidate/inventory.json'
STAGE13 = 'data/processed/checkpoints/identity-evidence-pass/final/relations.json'
INPUTS = (FRAME, OCCURRENCES, CONTINUITY, STAGE10, STAGE13)
SEED = 'nz-election-model-2026-stage21-relationship-pilot-v1'
TRANSITIONS = ((2008, 2011), (2014, 2017), (2020, 2023))
QUOTAS = {'exact_same_label_general': 3, 'name_variant_general': 2,
          'different_label_general': 2, 'different_label_maori': 1}


def read(path):
    return json.loads((ROOT / path).read_text())


def encode(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()


def digest(path):
    return sha256((ROOT / path).read_bytes()).hexdigest()


def _fold(text):
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return re.sub('[^a-z]', '', ascii_text.lower())


def ambiguity(source_name, target_name, scope):
    if source_name == target_name:
        name_type = 'exact_same_label'
    elif (_fold(source_name) == _fold(target_name) or
          _fold(source_name.split(',')[0]) == _fold(target_name.split(',')[0])):
        name_type = 'name_variant'
    else:
        name_type = 'different_label'
    return name_type + '_' + scope


def _evidence_summary(record):
    if record is None:
        return {'stage10Event': 'no_prior_event_join', 'sourceLink': None,
                'targetLink': None, 'relationLead': None, 'career': 'unknown',
                'sourcePersonExistence': 'unknown', 'targetPersonExistence': 'unknown'}
    adjudication = record.get('stage10IdentityEvidence')
    return {
        'stage10Event': record['identityClass'],
        'sourceLink': {'status': record['sourceIdentityStatus'],
                       'sourceIds': (record.get('sourceIdentityEvidence') or {}).get('sourceIds', [])},
        'targetLink': {'status': record['targetIdentityStatus'],
                       'sourceIds': (record.get('targetIdentityEvidence') or {}).get('sourceIds', [])},
        'relationLead': ({'route': adjudication.get('role'),
                          'sourceEvidenceId': adjudication.get('sourceEvidenceId'),
                          'targetEvidenceId': adjudication.get('targetEvidenceId'),
                          'laterOutcomeDependent': adjudication.get('laterOutcomeCoverageDependent')}
                         if adjudication else None),
        'career': record['incomingCareerHistory']['status'],
        'sourcePersonExistence': ('retrospective_official_profile' if
                                  record.get('sourceProfileId') else 'unknown'),
        'targetPersonExistence': ('retrospective_official_profile' if
                                  record.get('incomingProfileId') else 'unknown')}


def _insufficiency(category, proven):
    if proven:
        return 'A preserved Stage10 distinct-person route exists; retained in the full ledger but outside the unresolved pilot.'
    if category.startswith('exact_same_label'):
        return 'Matching election-local labels or a prior winner/profile anchor do not independently bridge this target candidacy to the source person.'
    if category.startswith('name_variant'):
        return 'The lexical name variant is an alias lead only; no exact-occurrence bridge is established by the string.'
    return 'Different election-local labels do not establish that two distinct people stood; an explicit bridge or independently corroborated distinct-person evidence is needed.'


def claim_ledger(frame, occurrences, continuity, stage10, stage13):
    by_occurrence = {r['candidateOccurrenceId']: r for r in occurrences['records']}
    if len(by_occurrence) != len(occurrences['records']):
        raise ValueError('Duplicate candidate occurrence ID')
    old = {r['eventId']: r for r in stage10['records']}
    inherited = {(r['sourceOccurrenceId'], r['targetOccurrenceId']): r
                 for r in stage13['records']}
    party_pairs = defaultdict(list)
    for row in continuity['records']:
        if row['status'] == 'eligible' and (row['sourceYear'], row['targetYear']) in TRANSITIONS:
            party_pairs[row['sourceYear'], row['targetYear']].append(row)
    records = []
    for seat in frame['records']:
        years = seat['sourceYear'], seat['targetYear']
        if years not in TRANSITIONS or seat['contestStatus'] != 'held_both':
            continue
        source_groups, target_groups = defaultdict(list), defaultdict(list)
        for occurrence_id in seat['sourceOccurrenceIds']:
            row = by_occurrence[occurrence_id]
            source_groups[row['partyKey']].append(row)
        for occurrence_id in seat['targetOccurrenceIds']:
            row = by_occurrence[occurrence_id]
            target_groups[row['partyKey']].append(row)
        for party in party_pairs[years]:
            sources = source_groups.get(party['source']['sourceKey'], [])
            targets = target_groups.get(party['target']['sourceKey'], [])
            if not sources or not targets:
                continue
            if len(sources) != 1 or len(targets) != 1:
                raise ValueError('Ambiguous same-party candidate multiplicity')
            source, target = sources[0], targets[0]
            event_id = source['candidateOccurrenceId'] + '->' + target['candidateOccurrenceId']
            former = old.get(event_id)
            stage13_relation = inherited.get((source['candidateOccurrenceId'],
                                              target['candidateOccurrenceId']))
            evidence = _evidence_summary(former)
            category = ambiguity(source['sourceCandidateName'],
                                 target['sourceCandidateName'], seat['scope'])
            proven = bool(former and former.get('stage10IdentityEvidence') and
                          former['identityClass'] in ('supported_replacement',
                                                      'supported_by_election_successor',
                                                      'retrospective_alias_replacement'))
            records.append({
                'caseId': event_id, 'transition': f'{years[0]}-{years[1]}',
                'sourceYear': years[0], 'targetYear': years[1], 'scope': seat['scope'],
                'sourceElectorateId': seat['sourceElectorateId'],
                'targetElectorateId': seat['targetElectorateId'],
                'partyKey': party['canonicalPartyId'],
                'sourceOccurrenceId': source['candidateOccurrenceId'],
                'targetOccurrenceId': target['candidateOccurrenceId'],
                'sourceOriginalName': source['sourceCandidateName'],
                'targetOriginalName': target['sourceCandidateName'],
                'sourceOriginalAffiliation': source['sourceAffiliation'],
                'targetOriginalAffiliation': target['sourceAffiliation'],
                'sourceOfficialIds': source['provenance']['sourceIds'],
                'targetOfficialIds': target['provenance']['sourceIds'],
                'ambiguityType': category,
                'existingEvidence': evidence,
                'whyExistingEvidenceIsInsufficient': _insufficiency(category, proven),
                'stage13SelectedCohortRelation': (stage13_relation['verifiedRelation']
                                                 if stage13_relation else None),
                'relationshipClaim': ('preserved_distinct_person_route_review_separately'
                                      if proven else 'unresolved_cross_election_relation'),
                'evidenceNeeded': 'A source explicitly connecting these exact election-local candidacies to one person, an authoritative prior-name bridge, or independently established distinct people; a nomination of one occurrence alone is insufficient.',
                'potentialAnalysis': ['candidate_persistence_if_same_person',
                                      'replacement_if_distinct_person',
                                      'freshman_tenure_only_if_separately_dated_service'],
                'careerCompleteness': evidence['career'],
                'selectedForPilot': False,
                'observedOutcomeDiagnosticOnly': {
                    'sourceWon': former.get('sourceWasElected') if former else None,
                    'targetWon': None},
            })
    records.sort(key=lambda row: row['caseId'])
    if len({r['caseId'] for r in records}) != len(records):
        raise ValueError('Duplicate relationship case')
    return records


def select_cases(records):
    selected = []
    for source_year, target_year in TRANSITIONS:
        transition = f'{source_year}-{target_year}'
        for category, count in QUOTAS.items():
            eligible = [r for r in records if r['transition'] == transition and
                        r['ambiguityType'] == category and
                        r['relationshipClaim'] == 'unresolved_cross_election_relation']
            eligible.sort(key=lambda row: (sha256((SEED + '|' + row['caseId']).encode()).hexdigest(),
                                           row['caseId']))
            if len(eligible) < count:
                raise ValueError(f'Insufficient unresolved {transition} {category}')
            selected.extend(r['caseId'] for r in eligible[:count])
    if len(selected) != 24 or len(set(selected)) != 24:
        raise ValueError('Pilot must contain exactly 24 unique cases')
    return selected


def build(frame=None, occurrences=None, continuity=None, stage10=None, stage13=None):
    frame = frame or read(FRAME)
    occurrences = occurrences or read(OCCURRENCES)
    continuity = continuity or read(CONTINUITY)
    stage10 = stage10 or read(STAGE10)
    stage13 = stage13 or read(STAGE13)
    records = claim_ledger(frame, occurrences, continuity, stage10, stage13)
    selected = select_cases(records)
    selected_set = set(selected)
    for row in records:
        row['selectedForPilot'] = row['caseId'] in selected_set
    selected_rows = [next(r for r in records if r['caseId'] == case_id) for case_id in selected]
    plan = {
        'schemaVersion': 1, 'stage': 21, 'phase': 'committed_before_external_search',
        'frame': 'all observed same-party candidature pairs on Stage14 certified unchanged-boundary held source/target contests and eligible Stage5 party continuity; every case retained',
        'selection': {'seed': SEED, 'score': 'SHA256(seed|caseId) ascending with caseId tie-break, separately within transition and lexical ambiguity/scope quota',
                      'quotasPerTransition': QUOTAS, 'selectedCaseIds': selected,
                      'forbiddenPriorityFields': ['sourceOrTargetWinner', 'laterWinner',
                                                  'premiumOrResidual', 'modelError',
                                                  'profileOrSearchAvailability',
                                                  'inheritedIdentityConfidence'],
                      'lexicalCategoriesAreQuestionsNotAdjudications': True},
        'preservedAudit': 'review underlying Stage8/10/13 evidence for all selected claims before external queries; keep those channels separate and do not promote inherited confidence',
        'sourceHierarchy': ['official election-local candidature plus explicit cross-election bridge',
                            'official Electoral Commission or Parliament historical person/constituency record with explicit link',
                            'dated party-authored selection, prior-name or candidacy-history statement',
                            'contemporaneous authoritative archive of a party-authored statement with clear author/date'],
        'ancillaryNotPrimary': 'journalist interviews, candidate-submitted profiles, snippets and unverified same-name profiles may be preserved as leads but cannot alone confirm a relation',
        'searchProcedure': {'collectionQueriesMaximum': 8,
                            'targetedQueriesPerSelectedCaseMaximum': 2,
                            'newUniqueResourceMaximum': 30,
                            'allEndpointTestsAndFailuresLogged': True,
                            'collectionRoute': 'test search mechanics with noncandidate queries if needed; then seek official archived candidate lists and dated party collections spanning selected cases',
                            'caseQueryTemplates': ['"{sourceName}" "{targetName}" {seat} election candidate',
                                                   '"{sourceName}" OR "{targetName}" {party} {sourceYear} {targetYear} selection former name'],
                            'resultDecision': 'accept only retrieved authoritative content that supplies an exact relationship or dated service passage; a result snippet is a lead, not confirmation',
                            'deduplication': 'one canonical URL or identical raw SHA256 is one new resource, shared across cases only after case-specific passage review',
                            'failedRetrieval': 'log query and URL/failure; counts against query limit, not resource cap',
                            'stop': 'stop at each query cap or 30 new unique resources; no replacement cases, third query, success top-up or need to exhaust budget'},
        'adjudication': 'person existence, each occurrence, same/different-person relation and dated electorate/list career are separate; exact passage and source checksum required; unresolved stays unresolved',
        'time': 'historical fact date or interval, original publication date, retrieval timestamp and strict pre-target availability are separate; unknown remains null; later retrospective evidence may corroborate history without becoming prospective evidence',
        'scopeExclusions': ['no effect fitting or earlier adjudication overwrite',
                            'no cohort expansion from shared-resource leads'],
    }
    ledger = {'schemaVersion': 1, 'stage': 21, 'cases': records,
              'selectedCaseIdsInFixedSearchOrder': selected,
              'summary': {'allClaimCases': len(records),
                          'unresolvedRelationCases': sum(r['relationshipClaim'] ==
                                                         'unresolved_cross_election_relation'
                                                         for r in records),
                          'selected': len(selected),
                          'byTransition': dict(sorted(Counter(r['transition'] for r in records).items())),
                          'selectedByType': dict(sorted(Counter(r['ambiguityType'] for r in selected_rows).items()))}}
    searches = {'schemaVersion': 1, 'stage': 21,
                'collectionQueries': [], 'caseQueries': {case_id: [] for case_id in selected},
                'newResourceIds': [], 'state': 'pre_acquisition'}
    outputs = {'claim-ledger.json': ledger, 'acquisition-plan.json': plan,
               'search-ledger.json': searches}
    outputs['manifest.json'] = {'schemaVersion': 1, 'stage': 21,
                                'phase': 'pre_acquisition',
                                'inputSha256': {path: digest(path) for path in INPUTS},
                                'generatorSha256': digest('scripts/checkpoints/stage21_identity_pilot.py'),
                                'outputSha256': {name: sha256(encode(data)).hexdigest()
                                                 for name, data in outputs.items()}}
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
                raise ValueError(f'Changed Stage21 pre-acquisition {name}')
        else:
            path.write_bytes(encode(data))
    print(outputs['claim-ledger.json']['summary'])


if __name__ == '__main__':
    main()
