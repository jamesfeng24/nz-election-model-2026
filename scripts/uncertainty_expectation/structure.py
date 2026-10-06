"""Preserved-evidence structural continuity; outcomes enter only retrospective diagnostics."""
from collections import Counter
from fractions import Fraction
import re
import numpy as np
from scripts.evidence.practical_candidate_linkage.names import strict_member
from scripts.transport.continuous.features import source_r
from .audits import raw_residual
from .common import ROOT, PREFIX, INVENTORY, read, save, verify, arguments, digest

LINKS = 'data/processed/evidence/practical-candidate-linkage/'
GEO = 'data/processed/checkpoints/stage25-historical-geography/geography.json'
FLOW = 'data/processed/forecast-transport/party-construction.json'
DESIGN = 'data/processed/checkpoints/joint-candidate-share-design/inventory.json'
CONTINUOUS = 'data/processed/continuous-transport/inventory.json'
SUPPLEMENT = 'data/processed/continuous-transport/supplemental-links.json'
SAVED = 'data/processed/models/joint-candidate-share/construction.json'
RAW_FACT = 'data/raw/polling/stage38/2017.html'
LEDGER = 'data/raw/polling/stage38/acquisition-ledger.json'
YEARS = (2011, 2014, 2017, 2020, 2023)
MAJOR = {'nationalparty', 'labourparty'}
MODELS = ('baseline', 'baseline_plus_S', 'baseline_plus_R', 'baseline_plus_S_plus_R')
INPUTS = [INVENTORY, GEO, FLOW, DESIGN, CONTINUOUS, SUPPLEMENT, SAVED,
          LINKS+'occurrences.json', LINKS+'proposed-links.json', LINKS+'accepted-relationships.json',
          LINKS+'documentary-claims.json', 'data/processed/models/candidate-overperformance/occurrences.json',
          'data/processed/uncertainty-tails/construction.json', RAW_FACT, LEDGER,
          *[f'data/processed/elections/{y}.json' for y in YEARS]]


def specification():
    return {'stage': 47, 'scope': 'all257 fixed candidate seats, no new accepted identity or prediction',
        'sourceSupport': 'Every held non-NAT/LAB source occurrence; source candidate valid-vote share times target-incoming population fraction from ONE frozen Stage41 point. Sum is a continuous source-support proxy, not target reconstructed candidate votes; no viability threshold.',
        'identity': 'Stage26 accepted IDs plus saved Stage42 geographic-only supplemental accepted edges; strict_member sensitivity. Nonmatch unresolved; documentary distinct people alone neither departure nor new strength.',
        'sourceS': 'Existing party/geography S survives person change where recorded; source split destination and supported mass retained, never reset here.',
        'R': 'Existing source_r guard and saved residualEvidence; no outgoing-person transfer. Zero unsupported contribution not proof of zero strength.',
        'datedEvidence': 'Preserved occurrence-specific distinct claims carry dates/retrieval references; one preserved secondary documentary retirement statement for Dunne21Aug2017. Publication unknown, fact AFTER actual29Jul2017 cutoff. No new challenger-strength evidence inferred from final target votes.',
        'cutoffs': 'Actual cached56-day nationalProvenance for2017/2020/2023;2014 conditional comparison has no historical as-of claim. Final candidate roster and retrospective identity not verified cutoff availability.',
        'savedComparators': 'Four independently fitted Stage33 primary_fixed_to_observed predictions only when complete IDs match; unavailable outside canonical exact samples. No new mean prediction, including no fabricated changed-seat baseline/R.',
        'diagnostics': 'Inventory fully constructed before reading target candidate outcomes for raw-log N/L balance, majors/remainder mass and pp actual-minus-frozen-mean errors; no labels determined by these.',
        'hypotheses': ['Epsom', 'Ohariu', 'Auckland Central', 'Tamaki'], 'acquiredResources': 0,
        'prohibited': ['new identity adjudication', 'departure from nonmatch', 'strength from target result', 'new variance or mean fit', 'S reset', 'historical override']}


def freeze():
    spec_path = ROOT/PREFIX/'structural-specification.json'
    if spec_path.exists() and read(PREFIX+'/structural-specification.json') != specification():
        raise ValueError('Frozen structural specification changed')
    save('structural-specification.json', specification())
    value = {'inputHashes': {p: digest(p) for p in INPUTS}, 'newResources': 0, 'wholeSourceRegistryCoupling': False}
    pin = ROOT/PREFIX/'structure-input-contract.json'
    if pin.exists() and read(PREFIX+'/structure-input-contract.json') != value:
        raise ValueError('Structural consumed evidence changed')
    save('structure-input-contract.json', value)


def population_predecessors(row, geo, flow):
    if geo['certifiedTwoSidedExact']:
        return [{'sourceElectorateId': geo['dominantPredecessorId'], 'incomingFraction': 1., 'incomingFractionExact': '1'}]
    transition = f"{row['sourceYear']}-{row['targetYear']}"
    scenario = flow['transitions'][transition]['scopes']['general']
    code = str(int(row['targetElectorateId'].split('-')[-1])).zfill(3)
    denominator = scenario['targetPopulationControls'][code]
    records = []
    for edge in scenario['aggregatedEdges']:
        if edge['targetCode'] != code:
            continue
        weight = Fraction(edge['population'], denominator)
        sid = f"nz-general-{row['sourceYear']}-electorate-{int(edge['sourceCode']):02d}"
        if sid not in {p['sourceElectorateId'] for p in geo['predecessors']}:
            raise ValueError('Population point outside canonical predecessor graph')
        records.append({'sourceElectorateId': sid, 'incomingFraction': float(weight), 'incomingFractionExact': str(weight)})
    if sum(Fraction(p['incomingFractionExact']) for p in records) != 1:
        raise ValueError('Population incoming fractions do not conserve')
    return records


def evidence_context():
    occurrences = read(LINKS+'occurrences.json')['records']
    accepted = read(LINKS+'accepted-relationships.json')
    broad, strict = set(accepted['broadEdgeIds']), set(accepted['strictEdgeIds'])
    edges = {e['edgeId']: e for e in read(LINKS+'proposed-links.json')['records'] if e['edgeId'] in broad}
    for e in read(SUPPLEMENT)['records']:
        if e['label'] not in ('documentary_same_person', 'accepted_algorithmic_same_person'):
            continue
        edges[e['edgeId']] = e
        broad.add(e['edgeId'])
        if strict_member(e):
            strict.add(e['edgeId'])
    return {'occurrences': {o['candidateOccurrenceId']: o for o in occurrences},
            'bySeat': {s: [o for o in occurrences if o['electorateId'] == s] for s in {o['electorateId'] for o in occurrences}},
            'edges': list(edges.values()), 'strict': strict,
            'distinct': read(LINKS+'documentary-claims.json')['records'],
            'geo': {g['targetElectorateId']: g for g in read(GEO)['records']}, 'flow': read(FLOW),
            'design': {r['targetElectorateId']: r for r in read(DESIGN)['contestRecords']},
            'continuous': {r['targetElectorateId']: r for r in read(CONTINUOUS)['records']},
            'elections': {y: read(f'data/processed/elections/{y}.json') for y in YEARS},
            'cutoffs': {c['year']: c['nationalProvenance']['cutoff'] for c in read('data/processed/uncertainty-tails/construction.json')['cases'] if c['layer'] == 'composed'}}


def dated_claim(claim, cutoff):
    e = claim['evidence']
    fields = {k: e.get(k) for k in ('sourceFactDate', 'sourcePublicationDate', 'sourceRetrievalAt', 'targetFactDate', 'targetPublicationDate', 'targetRetrievalAt')}
    publication = fields['targetPublicationDate']
    status = 'conditional_no_asof_claim' if cutoff is None else 'unverified_publication' if publication is None else 'after_cutoff' if publication[:10] > cutoff else 'reported_publication_pre_cutoff'
    return {'label': 'documentary_distinct_people', 'sourceOccurrenceId': claim['sourceOccurrenceId'],
            'targetOccurrenceId': claim['targetOccurrenceId'], 'evidenceArtifact': claim['evidenceArtifact'],
            'evidencePointer': claim['evidencePointer'], 'dates': fields, 'cutoffAvailability': status,
            'departureEstablished': False, 'newChallengerStrengthEstablished': False}


def retirement_fact(ctx, row, source):
    if row['targetYear'] != 2017 or 'DUNNE, Peter' not in source['sourceCandidateName'] or row['name'].casefold() not in ('ohariu', 'ōhāriu'):
        return None
    text = (ROOT/RAW_FACT).read_text()
    plain = re.sub('<[^>]+>', '', text)
    if '21 Aug 2017 – Ōhāriu Incumbent Peter Dunne' not in plain or 'announces that he will now be retiring from politics.' not in plain:
        raise ValueError('Preserved documentary fact no longer present')
    resource = next(r for r in read(LEDGER)['resources'] if r['rawPath'] == RAW_FACT)
    cutoff = ctx['cutoffs'][2017]
    return {'status': 'documented_departure_from_target_contest', 'factDate': '2017-08-21', 'publicationDate': None,
            'retrievedAt': resource['retrievedAt'], 'rawSource': RAW_FACT, 'url': resource['url'],
            'rawSHA256': resource['sha256'], 'excerpt': 'announces that he will now be retiring from politics.', 'eventContext': '21 Aug2017, Ōhāriu incumbent Peter Dunne; context and excerpt verified in preserved secondary chronology',
            'evidenceTier': 'preserved secondary event chronology; original linked publication not acquired',
            'cutoff': cutoff, 'factBeforeCutoff': False, 'cutoffAvailability': 'after_cutoff_fact_and_unverified_publication',
            'forecastTimeStructuralClassification': 'unresolved', 'noNewIdentityAdjudication': True}


def target_features(row, ctx):
    cid = row['targetElectorateId']
    detail = ctx['continuous'].get(cid) if row['targetYear'] in (2014, 2020) else ctx['design'].get(cid)
    details = {c['targetOccurrenceId']: c for c in detail['candidates']} if detail else {}
    results = []
    for f in row['features']:
        o = ctx['occurrences'][f['id']]
        links = [e for e in ctx['edges'] if e['targetOccurrenceId'] == f['id'] and e['sourceYear'] == row['sourceYear']]
        c = details.get(f['id'], {})
        if 'continuous' in c:
            s_evidence = [p['evidence'] for p in c['continuous']['S']['components'] if p.get('evidence')]
        else:
            s_evidence = [{'sourceCandidateId': c.get('sourceCandidateId'), 'sourceMatrixId': c.get('sourceMatrixId'), 'splitSourceIds': c.get('splitSourceIds', [])}] if c.get('s0Reported') is not None else []
        source_ids = [p.get('sourceCandidateId') for p in s_evidence]
        accepted_sources = {e['sourceOccurrenceId'] for e in links}
        distinct = [dated_claim(d, ctx['cutoffs'].get(row['targetYear'])) for d in ctx['distinct'] if d['targetOccurrenceId'] == f['id']]
        major = o['ballotGroupKey'] in MAJOR
        state = 'accepted_contender_continuation' if links else 'major_party_turnover_supported_by_evidence' if major and distinct else 'unresolved'
        evidence_sources = {e.get('sourceOccurrenceId') for e in f['residualEvidence'] if e.get('sourceOccurrenceId')}
        if f['supportedMass']['R'] > 0 and not evidence_sources <= accepted_sources:
            raise ValueError('Saved R evidence outside accepted same-person links')
        results.append({'targetOccurrenceId': f['id'], 'name': o['sourceCandidateName'], 'originalAffiliation': o['sourceAffiliation'],
            'ballotGroup': f['group'], 'structuralStatus': state, 'links': [{'edgeId': e['edgeId'], 'sourceOccurrenceId': e['sourceOccurrenceId'],
                'label': e['label'], 'strict': e['edgeId'] in ctx['strict'], 'publicationByForecastCutoff': e.get('publicationByForecastCutoff', 'unknown')} for e in links],
            'documentaryDistinct': distinct, 'newChallengerStrengthEvidence': 'unavailable_not_inferred_from_target_results',
            'targetRosterCutoffAvailability': o['publicationByForecastCutoff'], 'S': {'supportedMass': f['supportedMass']['S'], 'centeredContribution': f['centered'][0],
                'sourceEvidence': s_evidence, 'SDespiteNoAcceptedPersonLink': not links and f['supportedMass']['S'] > 0,
                'notPersonalHistory': True}, 'R': {'supportedMass': f['supportedMass']['R'], 'centeredContribution': f['centered'][1],
                'residualEvidence': f['residualEvidence'], 'outgoingTransferGuardPassed': not evidence_sources or evidence_sources <= accepted_sources},
            'sourceSNames': [ctx['occurrences'][i]['sourceCandidateName'] if i in ctx['occurrences'] else None for i in source_ids]})
    return results


def continuity_inventory(inventory=None, ctx=None):
    inventory = read(INVENTORY) if inventory is None else inventory
    ctx = evidence_context() if ctx is None else ctx
    seats = {y: {s['id']: s for s in e['electorates']} for y, e in ctx['elections'].items()}
    results = []
    for row in inventory['candidateRecords']:
        g = ctx['geo'][row['targetElectorateId']]
        predecessors = population_predecessors(row, g, ctx['flow'])
        contenders = []
        for p in predecessors:
            source = seats[row['sourceYear']][p['sourceElectorateId']]
            votes = {c['id']: c['votes'] for c in source['candidates']}
            denominator = source['validCandidateVotes']
            for o in ctx['bySeat'][p['sourceElectorateId']]:
                if o['ballotGroupKey'] in MAJOR:
                    continue
                support = votes[o['candidateOccurrenceId']]/denominator if denominator > 0 else None
                links = [e for e in ctx['edges'] if e['sourceOccurrenceId'] == o['candidateOccurrenceId'] and e['targetElectorateId'] == row['targetElectorateId']]
                departure = retirement_fact(ctx, row, o)
                contenders.append({'sourceOccurrenceId': o['candidateOccurrenceId'], 'sourceElectorateId': o['electorateId'],
                    'name': o['sourceCandidateName'], 'originalAffiliation': o['sourceAffiliation'], 'ballotGroup': o['ballotGroupKey'],
                    'sourceContestStatus': o['candidateContestStatus'], 'sourceCandidateShare': support,
                    'incomingPopulationFraction': p['incomingFraction'], 'supportProxyContribution': None if support is None else support*p['incomingFraction'],
                    'status': 'accepted_contender_continuation' if links else 'documented_departure_from_target_contest' if departure else 'unresolved',
                    'acceptedTargetOccurrenceIds': [e['targetOccurrenceId'] for e in links], 'strictTargetOccurrenceIds': [e['targetOccurrenceId'] for e in links if e['edgeId'] in ctx['strict']],
                    'documentaryDeparture': departure, 'forecastTimeAvailability': 'unverified_retrospective_linkage_and_roster',
                    'sourceCandidatureEvidence': o['officialSourceIds'], 'nonmatchIsNotDeparture': True})
        results.append({'id': row['targetElectorateId'], 'name': row['name'], 'year': row['targetYear'],
            'scope': 'general', 'geography': row['geography'], 'predecessors': predecessors,
            'sourceNonmajorSupportProxy': sum(c['supportProxyContribution'] for c in contenders if c['supportProxyContribution'] is not None),
            'sourceProxyUnavailableOccurrences': sum(c['supportProxyContribution'] is None for c in contenders),
            'sourceContenders': contenders, 'targets': target_features(row, ctx), 'cutoff': ctx['cutoffs'].get(row['targetYear']),
            'historicalAvailability': 'conditional_no_asof_claim' if row['targetYear'] == 2014 else 'retrospective_roster_not_verified_at_cutoff'})
    return results


def saved_comparators(row, saved):
    folds = [f for f in saved['folds'] if f['targetYear'] == row['targetYear'] and f['branch'] == 'primary_fixed_to_observed']
    result = {}
    for model in MODELS:
        matches = [p for f in folds for p in f['predictions'].get(model, []) if p['targetElectorateId'] == row['targetElectorateId']]
        if len(matches) != 1 or set(matches[0]['candidateShares']) != set(row['ids']):
            result[model] = {'status': 'unavailable_no_matching_saved_complete_prediction'}
        else:
            shares = [matches[0]['candidateShares'][i] for i in row['ids']]
            diagnostic = dict(row, mean=shares)
            result[model] = {'status': 'saved_matching_complete_slate', 'shares': shares,
                'balanceRawLogError': raw_residual(diagnostic, 'balance'), 'majorMassRawLogError': raw_residual(diagnostic, 'mass'),
                'actualMinusPredictionPP': [100*(a-m) for a, m in zip(row['actual'], shares)],
                'reference': SAVED, 'input': 'observed_local_party', 'noRecalculation': True, 'errorsRetrospectiveOnly': True}
    return result


def build():
    inventory = read(INVENTORY)
    structure = continuity_inventory(inventory)
    # Structural classification is fully materialized before any target outcome analysis.
    rows = {r['targetElectorateId']: r for r in inventory['candidateRecords']}
    saved = read(SAVED)
    outcomes = []
    for item in structure:
        row = rows[item['id']]
        outcomes.append({'id': item['id'], 'balanceRawLogError': raw_residual(row, 'balance'), 'majorMassRawLogError': raw_residual(row, 'mass'),
            'candidateErrorsPP': [{'id': i, 'group': g, 'actualMinusMeanPP': 100*(a-m)} for i, g, a, m in zip(row['ids'], row['groups'], row['actual'], row['mean'])],
            'savedFourModelContext': saved_comparators(row, saved), 'diagnosticOnlyNotUsedForStructuralState': True})
    contenders = [c for r in structure for c in r['sourceContenders']]
    targets = [c for r in structure for c in r['targets']]
    names = lambda name: re.sub('[^a-z]', '', name.casefold().replace('ō', 'o').replace('ā', 'a'))
    return {'stage': 47, 'structuralRecords': structure, 'retrospectiveDiagnostics': outcomes,
        'summary': {'seats': len(structure), 'sourceOccurrenceRepresentations': len(contenders),
            'sourceStatusCounts': dict(Counter(c['status'] for c in contenders)), 'targetStatusCounts': dict(Counter(c['structuralStatus'] for c in targets)),
            'SDespiteNoAcceptedPersonLinkCandidates': sum(c['S']['SDespiteNoAcceptedPersonLink'] for c in targets),
            'newDatedStrengthFacts': 0, 'verifiedCompleteRostersAt56Days': 0, 'externalResources': 0},
        'namedHypotheses': {name: [r['id'] for r in structure if names(r['name']) == names(name)] for name in ('Epsom', 'Ohariu', 'Auckland Central', 'Tamaki')},
        'scope': 'every successful and unsuccessful prediction retained; no thresholds, exception labels, resets or new identity adjudications',
        'varianceDesignBoundary': 'May replace at most one of the two audited characteristics in a separately frozen future design; no fitted structural predictor here',
        'manualAdjustmentBoundary': 'Dated preserved evidence plus unadjusted output required; neither mean adjustment nor known historical miss establishes reduced variance'}


def main():
    args = arguments()
    verify()
    if args.check:
        if read(PREFIX+'/structural-specification.json') != specification():
            raise ValueError('Structural specification changed')
    else:
        freeze()
    for p, expected in read(PREFIX+'/structure-input-contract.json')['inputHashes'].items():
        if digest(p) != expected:
            raise ValueError('Changed structural consumed input '+p)
    save('structure.json', build(), args.check)
    print('Stage47 structural audit complete; preserved sources only, no new fitting or predictions')


if __name__ == '__main__':
    main()
