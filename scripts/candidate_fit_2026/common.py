"""Stage75 paths and the training-fold builder shared by the fit and its reproduction check."""
from hashlib import sha256
from scripts.checkpoints.joint_candidate_share import kernel
from scripts.checkpoints.stage22_fit import earlier_actuals
from scripts.checkpoints.stage25_availability import ELECTIONS
from scripts.models.joint_candidate_share.adapters import arrays
from scripts.models.joint_candidate_share.common import read, encode, keyed, DESIGN, METHODS

PREFIX = 'data/processed/candidate-fit-2026/'
FIT = PREFIX + 'fit.json'
FEATURES = PREFIX + 'features-2026.json'
IMPACT = PREFIX + 'impact.json'
CONSTRUCTION = 'data/processed/models/joint-candidate-share/construction.json'
READINESS = 'data/processed/continuous-transport/readiness-2026.json'
METHOD = 'baseline_plus_S_plus_R'
LIVE_BRANCH = 'live_all_elections'
LIVE_YEAR = 2026


def design():
    plan = read(DESIGN + 'fold-plan.json')['folds']
    inventory = read(DESIGN + 'inventory.json')
    latest = next(f for f in plan if f['branch'] == 'primary' and f['targetYear'] == 2023)
    return latest, keyed(inventory['contestRecords'], 'targetElectorateId')


def rows_for(ids, records):
    rows = [records[i] for i in ids]
    if any(r['status'] != 'available' for r in rows):
        raise ValueError('Training contest is not available')
    return rows


def live_fold(latest, records):
    """The Stage33 primary design extended by its own 2023 evaluation contests: every completed election trains."""
    ids = latest['trainingIds'] + latest['evaluationIds']
    if len(set(ids)) != len(ids):
        raise ValueError('Training and evaluation contests overlap')
    rows = rows_for(ids, records)
    return {'id': f'{LIVE_BRANCH}:complete_share_baseline_s:2011-2023:two_sided_exact', 'branch': LIVE_BRANCH,
            'targetYear': LIVE_YEAR, 'view': latest['view'], 'roundingScenario': latest['roundingScenario'],
            'partyInput': latest['partyInput'], 'reusePrimaryFitId': None, 'trainingIds': ids,
            'trainingCandidateIds': [c['targetOccurrenceId'] for r in rows for c in r['candidates']],
            'trainingOnlyMeans': kernel.means(rows, latest['view'], latest['roundingScenario'])}, rows


def job(fold, rows, method=METHOD):
    """The Stage33 `prepare` payload for explicit training rows (same arrays, actuals and signature)."""
    if fold['trainingOnlyMeans'] != kernel.means(rows, fold['view'], fold['roundingScenario']):
        raise ValueError('Training-only means differ from the training rows')
    base, features, starts = arrays(rows, fold, method, fold['partyInput'])
    elections = {y: read(path) for y, path in ELECTIONS.items()}
    actual = earlier_actuals(rows, {y: elections[y] for y in {r['targetYear'] for r in rows}})
    payload = {'method': method, 'trainingIds': fold['trainingIds'], 'candidateIds': fold['trainingCandidateIds'],
               'base': base.tolist(), 'features': features.tolist(), 'starts': starts.tolist(), 'actual': actual.tolist(),
               'selectedMeans': {n: fold['trainingOnlyMeans'][n] for n in METHODS[method]}}
    return {'signature': sha256(encode(payload)).hexdigest(), 'payload': payload}
