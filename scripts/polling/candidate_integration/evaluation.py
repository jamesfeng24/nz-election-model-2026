"""Post-construction held-out scoring; outcomes never alter integration inputs."""
import argparse
from math import sqrt
from statistics import mean
from scripts.models.joint_candidate_share.evaluation import actuals_for
from scripts.models.joint_candidate_share.metrics import score, aggregate, GROUPS
from scripts.checkpoints.stage24_evaluation import range_without_one
from scripts.checkpoints.stage25_availability import ELECTIONS
from .common import *

CODE = ['scripts/polling/candidate_integration/evaluation.py']
REPORT_GROUPS = ('national', 'labour', 'national_labour', 'other_mapped', 'affirmative_no_party_group')


def summary(records):
    if not records:
        return {'contests': 0, 'methods': None, 'groups': None, 'pairs': None}
    metrics = {m: aggregate([r['scores'][m] for r in records]) for m in METHODS}
    pairs = {}
    for model, control in PAIRS:
        gains = [r['scores'][control]['contestMaePP'] - r['scores'][model]['contestMaePP'] for r in records]
        pairs[model + '__versus__' + control] = {
            'maeImprovementPP': mean(gains), 'rmseImprovementPP': metrics[control]['contestEqualRmsePP'] - metrics[model]['contestEqualRmsePP'],
            'candidateEqualMaeImprovementPP': metrics[control]['candidateEqualMaePP'] - metrics[model]['candidateEqualMaePP'],
            'improvedContests': sum(v > 0 for v in gains), 'worsenedContests': sum(v < 0 for v in gains),
            'fixedFitLeaveOneContestOutMaeGainRangePP': range_without_one(gains),
            'fiveLargestAbsoluteEffects': sorted([{'targetElectorateId': r['targetElectorateId'], 'maeImprovementPP': g} for r,g in zip(records,gains)], key=lambda r: (-abs(r['maeImprovementPP']), r['targetElectorateId']))[:5]}
    groups = {}
    for group in REPORT_GROUPS:
        selected = [r for r in records if any(group in c['groups'] for c in r['scores']['baseline']['candidateErrors'])]
        methods = {}
        count = 0
        for method in METHODS:
            errors = [c['errorPP'] for r in selected for c in r['scores'][method]['candidateErrors'] if group in c['groups']]
            count = len(errors)
            methods[method] = {'candidateEqualMaePP': mean(abs(v) for v in errors), 'candidateEqualRmsePP': sqrt(mean(v*v for v in errors)),
                               'candidateEqualSignedBiasPP': mean(errors)} if errors else None
        groups[group] = {'candidates': count, 'presentContests': len(selected), 'weighting': 'one_per_candidate_in_group; groups_do_not_sum_to_contest_equal_total', 'methods': methods}
    return {'contests': len(records), 'candidates': metrics['baseline']['candidates'], 'methods': metrics, 'pairs': pairs, 'groups': groups}


def build(construction=None, design=None, elections=None):
    construction = read(OUT / 'construction.json') if construction is None else construction
    design = read(DESIGN / 'inventory.json') if design is None else design
    elections = {y: read(ROOT / p) for y,p in ELECTIONS.items()} if elections is None else elections
    actuals = actuals_for(design, elections)
    rows = {r['targetElectorateId']: r for r in design['contestRecords']}
    saved = {f['targetYear']: f for f in read(CANDIDATE / 'construction.json')['folds'] if f['branch'] == 'primary'}
    cases = []
    for case in construction['cases']:
        expected = case['expectedIds']
        if [r['targetElectorateId'] for r in case['records']] != expected or case['abstentions']:
            raise ValueError('Unexpected incomplete/model-specific replay scoring sample')
        reference = {m: {r['targetElectorateId']: r['candidateShares'] for r in saved[case['year']]['predictions'][m]} for m in METHODS}
        if any(set(p) != set(expected) for p in reference.values()):
            raise ValueError('Conditional context sample differs')
        records, conditional = [], []
        for r in case['records']:
            cid = r['targetElectorateId']; row = rows[cid]
            scores = {m: score(r['methods'][m]['candidateShares'], actuals[cid], row, 'broad') for m in METHODS}
            old = {m: score(reference[m][cid], actuals[cid], row, 'broad') for m in METHODS}
            records.append({'targetYear': case['year'], 'targetElectorateId': cid, 'originalFrame': r['originalFrame'], 'scores': scores,
                            'conditionalMaeChangePP': {m: scores[m]['contestMaePP'] - old[m]['contestMaePP'] for m in METHODS}})
            conditional.append({'targetElectorateId': cid, 'scores': old})
        new = summary(records); context = summary(conditional)
        cases.append({'year': case['year'], 'policy': case['policy'], 'records': records, 'abstentions': case['abstentions'],
                      **new, 'conditionalContext': context,
                      'replayMinusConditionalMaePP': {m: new['methods'][m]['contestEqualMaePP'] - context['methods'][m]['contestEqualMaePP'] for m in METHODS},
                      'meanInputShortcutMaximumGapPP': {m: max(r['methods'][m]['meanInputShortcutMaximumGapPP'] for r in case['records']) for m in METHODS}})
    pooled = []
    for policy in POLICIES:
        records = [r for c in cases if c['policy'] == policy for r in c['records']]
        pooled.append({'policy': policy, 'weighting': 'one_per_contest over162; election counts64/34/64', **summary(records),
                       'original2017_2023': summary([r for r in records if r['originalFrame']]),
                       'added2020': summary([r for r in records if not r['originalFrame']])})
    return {'stage': 39, 'cases': cases, 'pooled': pooled, 'operationalSelection': None,
            'information': 'retrospective conditional dated-input replay; national-input-only draws; no calibrated electorate probabilities',
            'comparisonEffect': 'forecast national inputs plus nonlinear averaging, not a causal/additive error decomposition'}


def run(check=False):
    verify_inputs(); verify_phase('construction')
    save('evaluation.json', build(), check)
    seal('evaluation', ['evaluation.json'], CODE, check)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); run(p.parse_args().check)
