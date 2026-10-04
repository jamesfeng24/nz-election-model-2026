"""Cutoff-first evidence inventory; target result values never enter allocation."""
from collections import Counter
from datetime import date
from math import sqrt, fsum
from scripts.polling.national_foundation.timing import select
from .common import CORE, ROOT, NATIONAL, read

POLL_KEYS = {'NCP': 'conservative', 'UNF': 'unitedfuture', 'INM': 'internetmana',
             'MNA': 'manamovement', 'INT': 'internetparty', 'TOP': 'theopportunitiespartytop'}


def roster(relationships, year):
    rows = [r for r in relationships if r['targetYear'] == year]
    if len(rows) != 1:
        raise ValueError('Missing or duplicate target roster')
    output = []
    for c in rows[0]['categories']:
        if c['relationship'] == 'exit':
            continue
        output.append({'categoryId': c['categoryId'], 'ballotGroupKey': c['targetPartyKey'],
                       'relationship': c['relationship'], 'priorShare': c['sourceNationalShare'],
                       'continuityEvidence': c['continuityEvidence'],
                       'rosterAvailability': 'retrospective_not_verified_at_cutoff',
                       'priorAvailability': 'completed_election_retrospective_source; assumed_by_next_Jan1'})
    if len({c['categoryId'] for c in output}) != len(output):
        raise ValueError('Duplicate fine category')
    if len({c['ballotGroupKey'] for c in output}) != len(output):
        raise ValueError('Duplicate ballot group')
    return output


def observation(record, code):
    obj = (record['estimates'] if code == 'TOP' else record['additionalPublishedCategories']).get(code)
    if obj is None or obj['status'] not in ('rounded', 'rounded_zero'):
        return None
    factor = 1.
    if record['denominator'] == 'all_respondents':
        if record['nonresponseCombined'] is None or not 0 <= record['nonresponseCombined'] < 1:
            return None
        factor -= record['nonresponseCombined']
    return {'share': obj['share'] / factor, 'bounds': [v / factor for v in obj['bounds']],
            'published': obj['published'], 'status': obj['status'],
            'denominator': record['denominator'], 'denominatorFactor': factor}


def report_rows(case, polls, fine):
    selected, exclusions = select(polls, case['cutoff'], 5)
    roster_ids = {c['categoryId'] for c in fine}
    rows, rejected = [], []
    cutoff = date.fromisoformat(case['cutoff'][:10])
    for r in selected:
        if r['cycle'] != case['electionYear']:
            continue
        age = (cutoff - date.fromisoformat(r['fieldworkEndBounds'][1])).days
        if not 0 <= age <= 180:
            continue
        for code, cid in POLL_KEYS.items():
            raw = (r['estimates'] if code == 'TOP' else r['additionalPublishedCategories']).get(code)
            if raw is None:
                continue
            valid_context = (code != 'INM' or case['electionYear'] == 2014) and (
                code not in ('MNA', 'INT') or case['electionYear'] == 2017)
            o = observation(r, code)
            reason = ('no_target_whole_group_mapping' if not valid_context or cid not in roster_ids else
                      'nonpoint_report_or_unresolved_denominator' if o is None else None)
            if reason:
                rejected.append({'pollId': r['id'], 'code': code, 'reason': reason, 'observation': raw})
                continue
            rows.append({'pollId': r['id'], 'categoryId': cid, 'code': code, 'pollster': r['pollsterCode'],
                         'ageDays': age, 'rawWeight': 2 ** (-age / 30) * sqrt(min(r['sampleSize'] or 750, 1500) / 1000),
                         'publication': r['publication'], 'publicationConfidence': r['publicationConfidence'],
                         'provenance': r['provenance'], **o})
    return rows, rejected, exclusions


def poll_weight(rows):
    if not rows:
        return None
    pollsters = sorted({r['pollster'] for r in rows})
    outer = {p: 2 ** (-min(r['ageDays'] for r in rows if r['pollster'] == p) / 30) for p in pollsters}
    contributions = []
    for p in pollsters:
        same = [r for r in rows if r['pollster'] == p]
        for r in same:
            weight = r['rawWeight'] / fsum(x['rawWeight'] for x in same) * outer[p] / fsum(outer.values())
            contributions.append({'pollId': r['pollId'], 'share': r['share'], 'weight': weight})
    return {'weight': fsum(r['share'] * r['weight'] for r in contributions), 'contributions': contributions}


def allocation_weights(fine, categories, reports, policy):
    if policy not in ('recent_report_prior', 'prior_only'):
        raise ValueError('Unknown allocation policy')
    if any(p not in CORE and p != 'OTH' for p in categories):
        raise ValueError('Unknown explicit national category')
    explicit = {CORE[p] for p in categories if p != 'OTH'}
    if not explicit <= {c['categoryId'] for c in fine}:
        raise ValueError('Explicit national category absent from roster')
    output = []
    for c in fine:
        if c['categoryId'] in explicit:
            continue
        prior = c['priorShare'] if c['relationship'] == 'continuing' else None
        poll = poll_weight([r for r in reports if r['categoryId'] == c['categoryId']])
        if policy == 'recent_report_prior' and poll is not None:
            weight, basis = poll['weight'], 'recent_published_working_approximation'
        else:
            weight, basis = (prior, 'supported_prior') if prior is not None and prior > 0 else (.001, 'neutral_seed_assumption')
        output.append({'categoryId': c['categoryId'], 'weight': weight, 'basis': basis,
                       'pollEvidence': poll, 'priorShare': prior})
    if output and fsum(r['weight'] for r in output) == 0:
        for r in output:
            r['weight'] = r['priorShare'] if r['priorShare'] is not None and r['priorShare'] > 0 else .001
            r['basis'] = 'all_zero_report_prior_seed_fallback'
    total = fsum(r['weight'] for r in output)
    for r in output:
        r['allocationFraction'] = r['weight'] / total
    return output


def build(manifests=None, relationships=None, polls=None):
    manifests = read(NATIONAL / 'output-manifest.json')['cases'] if manifests is None else manifests
    relationships = read(ROOT / 'data/processed/models/expanded-party-substitution/input-inventory.json')['categoryRelationships'] if relationships is None else relationships
    polls = read(ROOT / 'data/processed/polling/national-foundation/polls.json')['records'] if polls is None else polls
    cases = []
    for case in manifests:
        if not case['id'].startswith('primary-'):
            continue
        fine = roster(relationships, case['electionYear'])
        rows, rejected, exclusions = report_rows(case, polls, fine)
        cases.append({'id': case['id'], 'electionYear': case['electionYear'], 'cutoff': case['cutoff'],
                      'horizonDays': case['horizonDays'], 'archivePath': case['archivePath'],
                      'drawNamespace': case['drawNamespace'], 'roster': fine, 'reports': rows,
                      'rejectedReports': rejected, 'cutoffExclusions': exclusions,
                      'systems': {system: {'categories': categories, 'weights': {
                          policy: allocation_weights(fine, categories, rows, policy)
                          for policy in ('recent_report_prior', 'prior_only')}}
                          for system, categories in (('model', case['categories']), ('average', ['NAT', 'LAB', 'GRN', 'ACT', 'NZF', 'MRI', 'OTH']))},
                      'availabilityCounts': dict(Counter(r['publicationConfidence'] for r in rows))})
    return {'stage': 37, 'cases': cases, 'informationSet': 'cutoff minor reports; earlier national shares; retrospective target roster',
            'minorEvidenceAlreadyUsedByNationalModel': True, 'targetResultsUsed': False, 'operationalSelection': None}
