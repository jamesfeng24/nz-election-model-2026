"""Paired complete-slate metrics, fixed groups and geographic reporting."""
import argparse
from math import sqrt
from statistics import mean
from scripts.models.joint_candidate_share.metrics import score, aggregate
from scripts.checkpoints.stage24_evaluation import range_without_one
from .common import BRANCHES, PREFIX, read, save, verify

GROUPS = ('national', 'labour', 'other_mapped', 'affirmative_no_party_group',
          'R_supported', 'R_unsupported')


def score_row(row):
    candidates = []
    for c in row['candidates']:
        s = c['continuous']['S']['supportedWeight'] > 0
        views = {}
        for view, key in (('broad', 'R'), ('strict', 'RStrict')):
            r = c['continuous'][key]['supportedWeight'] > 0
            pattern = 'both_features' if s and r else 'S_only' if s else 'R_only' if r else 'neither_feature'
            views[view] = {'availabilityPattern': pattern}
        candidates.append({'targetOccurrenceId': c['targetOccurrenceId'],
            'partyBallotGroupKey': c['partyBallotGroupKey'], 'R': views})
    return {'candidates': candidates}


def group_summary(rows, name):
    methods = {}
    counts = {}
    for branch in BRANCHES:
        values = []
        present = 0
        for row in rows:
            selected = []
            for c in row['scores'][branch]['candidateErrors']:
                supported = row['candidateSupport'][c['candidateOccurrenceId']]['R'] > 0
                member = supported if name == 'R_supported' else not supported if name == 'R_unsupported' else name in c['groups']
                if member:
                    selected.append(c['errorPP'])
            present += bool(selected)
            values.extend(selected)
        counts[branch] = {'candidates': len(values), 'presentContests': present}
        methods[branch] = None if not values else {'maePP': mean(abs(v) for v in values),
            'rmsePP': sqrt(mean(v*v for v in values)), 'biasPP': mean(values)}
    return {'counts': counts, 'metrics': methods,
        'denominator': 'equal member candidate; R groups fixed to broad support across all branches; group means not additive whole-slate metrics'}


def summarize(rows):
    if not rows:
        return {'contests': 0, 'candidates': 0, 'metrics': None, 'pairs': None, 'groups': None}
    metrics = {b: aggregate([r['scores'][b] for r in rows]) for b in BRANCHES}
    pairs = {}
    for branch in ('joint', 'joint_strict'):
        effects = [{'targetElectorateId': r['targetElectorateId'], 'targetName': r['targetName'],
            'jointMinusSMaePP': r['scores'][branch]['contestMaePP'] - r['scores']['S']['contestMaePP'],
            'jointMinusSMsePP2': r['scores'][branch]['contestMsePP2'] - r['scores']['S']['contestMsePP2']}
            for r in rows]
        values = [e['jointMinusSMaePP'] for e in effects]
        pairs[branch] = {'jointMinusSMaePP': mean(values),
            'jointMinusSRmsePP': metrics[branch]['contestEqualRmsePP'] - metrics['S']['contestEqualRmsePP'],
            'improvedContests': sum(v < 0 for v in values), 'worsenedContests': sum(v > 0 for v in values),
            'unchangedContests': sum(v == 0 for v in values),
            'leaveOneContestOutDifferenceRangePP': range_without_one(values),
            'largestFiveGains': sorted([e for e in effects if e['jointMinusSMaePP'] < 0], key=lambda e: (e['jointMinusSMaePP'], e['targetElectorateId']))[:5],
            'largestFiveLosses': sorted([e for e in effects if e['jointMinusSMaePP'] > 0], key=lambda e: (-e['jointMinusSMaePP'], e['targetElectorateId']))[:5],
            'pairedContests': effects}
    support = {}
    for key in ('S', 'R', 'RStrict'):
        blocks = [[c[key] for c in r['candidateSupport'].values()] for r in rows]
        values = [v for block in blocks for v in block]
        support[key] = {'candidatesWithSupportedMass': sum(v > 0 for v in values),
            'candidateEqualMeanSupportedMass': mean(values),
            'contestEqualMeanSupportedMass': mean(mean(block) for block in blocks),
            'contestsWithAnySupportedMass': sum(any(v > 0 for v in block) for block in blocks)}
    return {'contests': len(rows), 'candidates': metrics['S']['candidates'], 'metrics': metrics,
        'pairs': pairs, 'groups': {g: group_summary(rows, g) for g in GROUPS}, 'support': support}


def equal_election(folds):
    full = [f['samples']['full'] for f in folds]
    metrics = {}
    for branch in BRANCHES:
        ms = [s['metrics'][branch] for s in full]
        metrics[branch] = {'maePP': mean(m['contestEqualMaePP'] for m in ms),
            'rmsePP': sqrt(mean(m['contestEqualRmsePP']**2 for m in ms)),
            'foldMaePP': [m['contestEqualMaePP'] for m in ms]}
    return {'elections': len(full), 'metrics': metrics,
        'jointMinusSMaePP': {b: mean(s['pairs'][b]['jointMinusSMaePP'] for s in full) for b in ('joint', 'joint_strict')},
        'weighting': '1/2 per election; RMSE root of mean election MSE; not future-stability estimate'}


def build(construction=None, inventory=None, elections=None):
    construction = read(PREFIX + '/construction.json') if construction is None else construction
    inventory = read('data/processed/continuous-transport/inventory.json') if inventory is None else inventory
    elections = {y: read(f'data/processed/elections/{y}.json') for y in (2014, 2020)} if elections is None else elections
    originals = {r['targetElectorateId']: r for r in inventory['records']}
    folds = []
    all_rows = []
    for fold in construction['folds']:
        targets = {s['id']: s for s in elections[fold['targetYear']]['electorates']}
        ps = {b: {p['targetElectorateId']: p['candidateShares'] for p in fold['predictions'][b]} for b in BRANCHES}
        ids = list(ps['S'])
        if any(list(p) != ids for p in ps.values()):
            raise ValueError('Paired contest IDs differ')
        rows = []
        for cid in ids:
            row = originals[cid]
            target = targets[cid]
            actual = {'candidateShares': {c['id']: c['votes']/target['validCandidateVotes'] for c in target['candidates']},
                'winnerCandidateId': target['winnerCandidateId']}
            support = {c['targetOccurrenceId']: {k: c['continuous'][k]['supportedWeight'] for k in ('S', 'R', 'RStrict')} for c in row['candidates']}
            rows.append({'targetElectorateId': cid, 'targetName': target['name'], 'tier': row['transportTier'],
                'candidateSupport': support, 'scores': {b: score(p[cid], actual, score_row(row), 'strict' if b == 'joint_strict' else 'broad') for b, p in ps.items()}})
        samples = {'full': rows, **{t: [r for r in rows if r['tier'] == t] for t in ('exact', 'approximate_95', 'approximate_90', 'fallback')}}
        samples['cumulative95'] = [r for r in rows if r['tier'] in ('exact', 'approximate_95')]
        for key in ('R', 'RStrict'):
            for has in (True, False):
                samples[key + ('_any' if has else '_none')] = [r for r in rows if any(c[key] > 0 for c in r['candidateSupport'].values()) == has]
        folds.append({'targetYear': fold['targetYear'], 'records': rows,
            'samples': {name: summarize(rs) for name, rs in samples.items()},
            'exclusions': [r for r in inventory['fullFrame'] if r['targetYear'] == fold['targetYear'] and r['status'] != 'available']})
        all_rows.extend(rows)
    return {'stage': 43, 'folds': folds, 'pooled': summarize(all_rows), 'equalElection': equal_election(folds),
        'pairedSign': 'joint-minus-S; negative joint better', 'pooledWeighting': 'equal contest; election weights64/129 and65/129',
        'operationalSelection': None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    verify()
    result = build()
    save('evaluation.json', result, args.check)
    for fold in result['folds']:
        print(fold['targetYear'], {b: round(m['contestEqualMaePP'], 6) for b, m in fold['samples']['full']['metrics'].items()})


if __name__ == '__main__':
    main()
