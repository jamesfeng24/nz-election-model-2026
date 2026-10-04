"""Canonical target frame and two-sided membership certification, not name matching."""
from fractions import Fraction
import re


def fraction(value):
    return Fraction(value['numerator'], value['denominator'])


def exact_source(target, edges):
    incoming = [e for e in edges if e['target'] == target['code'] and e['upper'] > 0]
    if target['unchangedMembershipStatus'] != 'identity' or len(incoming) != 1:
        return None
    edge = incoming[0]
    outgoing = [e for e in edges if e['source'] == edge['source'] and e['upper'] > 0]
    composition = target['composition']
    if len(outgoing) != 1 or len(composition) != 1:
        return None
    if any(fraction(v) != 1 for v in (edge['weightLower'], edge['weightUpper'], composition[0]['shareLower'], composition[0]['shareUpper'])):
        return None
    return edge['source']


def official_roster(text):
    plain = re.sub(r'L\d+(?:@P[\d-]+)?:\s*', '', text)
    rows = re.findall(r'\b([NSM]\d{2})\s+(\d{1,3})\s+(.+?)\s+([\d,]{5,})\s+[+-]', plain, re.S)
    result = []
    for display_code, code, name, population in rows:
        scope = 'maori' if display_code.startswith('M') else 'general'
        result.append({'officialDisplayCode': display_code, 'code': str(int(code)) if scope == 'maori' else code.zfill(3),
                       'scope': scope, 'officialName': ' '.join(name.split()), 'population': int(population.replace(',', ''))})
    if len(result) != 71 or len({(r['scope'], r['code']) for r in result}) != 71:
        raise ValueError('Official schedule does not uniquely account for 71 target seats')
    return result



def source_electorate(scope, source_name, occurrences):
    ids = {o['electorateId'] for o in occurrences if o['year'] == 2023 and o['electorateType'] == scope and o['electorateName'] == source_name}
    if len(ids) != 1:
        raise ValueError(f'Missing/ambiguous source election-local join: {scope} {source_name}')
    return ids.pop()


def build_frame(crosswalk, party, occurrences, official):
    current = {(r['scope'], r['code']): r for r in official}
    result = []
    for scope, data in crosswalk['scopes'].items():
        sources = {s['code']: s for s in data['sources']}
        party_targets = {t['targetCode']: t for t in party['scopes'][scope]['targets']}
        for target in data['targets']:
            row = current.pop((scope, target['code']))
            if row['officialName'] != target['name'] or row['population'] != target['populationControl']:
                raise ValueError(f'Current official target discrepancy: {target["name"]}')
            sid = exact_source(target, data['edges'])
            predecessors = []
            for member in target['composition']:
                edge = next(e for e in data['edges'] if e['source'] == member['source'] and e['target'] == target['code'])
                source = sources[member['source']]
                predecessors.append({'sourceBoundaryCode': source['code'], 'sourceName': source['name'],
                    'sourceElectorateId': source_electorate(scope, source['name'], occurrences),
                    'targetIncomingPopulationShareBounds': [member['shareLower'], member['shareUpper']],
                    'sourceRetainedPopulationShareBounds': [edge['weightLower'], edge['weightUpper']],
                    'jointPopulationEdgeBounds': [edge['lower'], edge['upper']]})
            exact_id = source_electorate(scope, sources[sid]['name'], occurrences) if sid else None
            source_status = sorted({o['candidateContestStatus'] for o in occurrences if o['electorateId'] == exact_id})
            result.append({'targetElectorateId': f'nz-{scope}-2026-boundary-{target["code"]}',
                'scope': scope, 'boundaryCode': target['code'], 'officialName': row['officialName'],
                'canonicalName': target['name'], 'officialDisplayCode': row['officialDisplayCode'],
                'boundaryVersionId': crosswalk['transition']['targetBoundaryVersionId'] if 'targetBoundaryVersionId' in crosswalk['transition'] else 'stats-nz-electorates-final-2025',
                'officialChangeStatus': target['officialChangeStatus'], 'incomingMembershipStatus': target['unchangedMembershipStatus'],
                'geographyStatus': 'certified_two_sided_exact' if sid else 'changed_or_technically_uncertain',
                'exactSourceBoundaryCode': sid, 'exactSourceElectorateId': exact_id,
                'sourceCandidateContestStatus': source_status, 'predecessors': predecessors,
                'dominantPredecessor': target['dominantPredecessor'],
                'dominantPredecessorIncomingBounds': [target['dominantPredecessorShareLower'], target['dominantPredecessorShareUpper']],
                'partyReconstruction': {'status': 'exact_source_geography' if sid else 'joint_bounded_notional_party_transport',
                    'artifactPath': 'data/processed/boundaries/2023-2026/party-votes.json',
                    'recordKey': f'scopes/{scope}/targets/{target["code"]}', 'categories': len(party_targets[target['code']]['parties']),
                    'nominalAllocation': None, 'basis': 'population-weighted source party vote transport; not candidate ballots',
                    'jointConstraintPath': 'data/processed/boundaries/2023-2026/crosswalk.json',
                    'pointOutputPermitted': bool(sid)},
                'candidateFeatureTransport': 'existing_exact_contract' if sid else 'neutral_fallback_only; predecessor_flat_unselected',
                'evidencePaths': ['data/raw/forecast-readiness/2026-10-05/schedule-c-readable.json',
                    'data/processed/boundaries/2023-2026/crosswalk.json']})
    if current:
        raise ValueError('Unconsumed official target seats')
    return sorted(result, key=lambda r: r['targetElectorateId'])
