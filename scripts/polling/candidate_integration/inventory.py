"""Freeze raw-schema mappings, allocation evidence and exact saved-fit samples."""
import argparse
from copy import deepcopy
from datetime import date
from collections import Counter
from math import sqrt
from scripts.polling.category_interface.inventory import poll_weight, observation
from scripts.polling.national_foundation.timing import select
from .common import *

EXPLICIT = {'National': 'nationalparty', 'Labour': 'labourparty', 'Green': 'greenparty',
            'ACT': 'actnewzealand', 'NZ First': 'newzealandfirstparty',
            'Te Pāti Māori': 'maoriparty', 'TOP': 'theopportunitiespartytop',
            'New Conservative': 'conservative', 'United Future': 'unitedfuture'}


def maori_reports(case, polls):
    """Apply existing Stage37 eligible-report arithmetic to newly nonexplicit MRI."""
    selected, _ = select(polls, case['cutoff'], 5)
    cutoff = date.fromisoformat(case['cutoff'][:10])
    rows = []
    for record in selected:
        if record['cycle'] != case['electionYear']:
            continue
        age = (cutoff - date.fromisoformat(record['fieldworkEndBounds'][1])).days
        if not 0 <= age <= 180 or 'MRI' not in record['estimates']:
            continue
        adapted = deepcopy(record)
        adapted['additionalPublishedCategories']['MRI'] = record['estimates']['MRI']
        obs = observation(adapted, 'MRI')
        if obs is None:
            continue
        rows.append({'pollId': record['id'], 'categoryId': 'maoriparty', 'code': 'MRI',
                     'pollster': record['pollsterCode'], 'ageDays': age,
                     'rawWeight': 2 ** (-age / 30) * sqrt(min(record['sampleSize'] or 750, 1500) / 1000),
                     'publication': record['publication'], 'publicationConfidence': record['publicationConfidence'],
                     'provenance': record['provenance'], **obs})
    return rows


def weights(fine, explicit, reports, policy):
    if policy not in POLICIES:
        raise ValueError('Unknown fixed allocation policy')
    rows = []
    for c in fine:
        if c['categoryId'] in explicit:
            continue
        prior = c['priorShare'] if c['relationship'] == 'continuing' else None
        poll = poll_weight([r for r in reports if r['categoryId'] == c['categoryId']])
        if policy == 'recent_report_prior' and poll is not None:
            value, basis = poll['weight'], 'recent_published_working_approximation'
        else:
            value, basis = (prior, 'supported_prior') if prior is not None and prior > 0 else (.001, 'neutral_seed_assumption')
        rows.append({'categoryId': c['categoryId'], 'weight': value, 'basis': basis,
                     'pollEvidence': poll, 'priorShare': prior})
    from math import fsum
    if rows and fsum(r['weight'] for r in rows) == 0:
        for r in rows:
            r['weight'] = r['priorShare'] if r['priorShare'] is not None and r['priorShare'] > 0 else .001
            r['basis'] = 'all_zero_report_prior_seed_fallback'
    total = fsum(r['weight'] for r in rows)
    for r in rows:
        r['allocationFraction'] = r['weight'] / total
    return rows


def build(construction=None, design=None, party=None, categories=None, polls=None):
    construction = read(CANDIDATE / 'construction.json') if construction is None else construction
    design = read(DESIGN / 'inventory.json') if design is None else design
    party = read(PARTY / 'input-inventory.json') if party is None else party
    categories = read(CATEGORY / 'inventory.json') if categories is None else categories
    polls = read(ROOT / 'data/processed/polling/national-foundation/polls.json')['records'] if polls is None else polls
    rows = {r['targetElectorateId']: r for r in design['contestRecords']}
    if len(rows) != len(design['contestRecords']):
        raise ValueError('Duplicate candidate inventory')
    cases = []
    for year in YEARS:
        fold = next(f for f in construction['folds'] if f['branch'] == 'primary' and f['targetYear'] == year)
        case = next(c for c in categories['cases'] if c['electionYear'] == year and c['horizonDays'] == 56)
        national = read(EXTERNAL / f'fits/{year}/attempt1.json')
        if str(national['signature']['cutoff'])[:10] != case['cutoff'][:10] or case['horizonDays'] != 56:
            raise ValueError('External/allocation cutoff mismatch')
        if national['status'] != 'accepted' or national['signature']['variant'] != 'gauss':
            raise ValueError('Missing accepted fixed gauss archive')
        explicit = {label: EXPLICIT[label] for label in national['parties'] if label != 'Other'}
        if len(set(explicit.values())) != len(explicit) or national['parties'].count('Other') != 1:
            raise ValueError('Ambiguous raw national schema')
        fine = case['roster']
        if not set(explicit.values()) <= {r['categoryId'] for r in fine}:
            raise ValueError('Explicit national group absent from retrospective roster')
        reports = list(case['reports'])
        if 'maoriparty' not in explicit.values():
            reports += maori_reports(case, polls)
        ids = fold['evaluationIds']
        candidates = [c['targetOccurrenceId'] for cid in ids for c in rows[cid]['candidates']]
        if candidates != fold['evaluationCandidateIds'] or any(rows[cid]['status'] != 'available' for cid in ids):
            raise ValueError('Complete saved candidate slate differs')
        fits = {m: deepcopy(fold['fits'][m]) for m in METHODS}
        if any(v['parameters']['status'] != 'fitted' for v in fits.values()):
            raise ValueError('No saved primary fit')
        target_groups = {r['ballotGroupKey'] for r in fine}
        for cid in ids:
            groups = [c['partyBallotGroupKey'] for c in rows[cid]['candidates'] if c['partyBallotGroupKey'] is not None]
            if len(groups) != len(set(groups)) or not set(groups) <= target_groups:
                raise ValueError('Missing or multiple candidate destinations')
        cases.append({'year': year, 'foldId': fold['id'], 'cutoff': national['signature']['cutoff'],
                      'allocationCutoff': case['cutoff'], 'horizonDays': 56, 'rawCategories': national['parties'],
                      'explicitMapping': explicit, 'roster': fine, 'allocationReports': reports,
                      'weights': {p: weights(fine, set(explicit.values()), reports, p) for p in POLICIES},
                      'evaluationIds': ids, 'evaluationCandidateIds': candidates, 'trainingIds': fold['trainingIds'],
                      'trainingOnlyMeans': fold['trainingOnlyMeans'], 'fits': fits,
                      'featuresReferenced': 'Stage32 inventory; broad/printed source-only S/R',
                      'nationalDrawIds': national['drawIds'], 'nationalSignature': national['signature'],
                      'drawNamespace': f'gauss-{year}-attempt1', 'chainShape': national['savedDrawChainShape'],
                      'forecastTarget': 'election-week support; Sunday-start weekly approximation',
                      'currentSupportField': 'lastDataSupport_not_exact_cutoff_nowcast',
                      'scope': 'general_two_sided_exact', 'retrospectiveRoster': True})
    if [len(c['evaluationIds']) for c in cases] != [64, 34, 64]:
        raise ValueError('Expected saved candidate coverage differs; stop before construction')
    ids = {cid for c in cases for cid in c['evaluationIds']}
    wider = [{k: r[k] for k in ('geographyId', 'targetElectorateId', 'sourceYear', 'targetYear', 'scope', 'contestStatus', 'partyInputStatus', 'reason')}
             | {'stage39Status': 'included' if r['targetElectorateId'] in ids else 'excluded',
                'stage39Reason': None if r['targetElectorateId'] in ids else 'outside_three_cached_fitted_cases' if r['partyInputStatus'] == 'available' else r['reason']}
             for r in party['partyFrame']]
    return {'stage': 39, 'cases': cases, 'widerFrame': wider, 'coverage': {
            str(c['year']): {'contests': len(c['evaluationIds']), 'candidates': len(c['evaluationCandidateIds']),
            'S': sum(rows[i]['candidates'][j]['s0Reported'] is not None for i in c['evaluationIds'] for j in range(len(rows[i]['candidates']))),
            'R': sum(x['R']['broad']['valueFraction'] is not None for i in c['evaluationIds'] for x in rows[i]['candidates'])} for c in cases},
            'widerExclusions': dict(Counter(r['stage39Reason'] for r in wider if r['stage39Status'] == 'excluded')),
            'targetCandidateOutcomesUsed': False, 'operationalSelection': None}


def run(check=False):
    verify_inputs()
    result = build()
    save('inventory.json', result, check)
    print('Frozen candidate coverage', result['coverage'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); run(p.parse_args().check)
