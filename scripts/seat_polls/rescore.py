"""Development check for the all-candidates seat-poll rule: how far are historical polls from the result on every candidate contrast?

For each preserved historical seat poll (2017, 2020, 2023; excluded polls dropped) the matched candidates' published shares and the
actual candidate shares are each rescaled over the matched candidates and compared as log-odds against the poll's leader. `ratio`
is mean(error^2 / multinomial sampling variance): 1 would be sampling error alone, the Stage79 National/Labour fit gave 5.29.
In-sample and small (13 polls, 40 contrasts, several with an assumed sample of 400): it sets the inflation constant, it is not a test.
python3 -m scripts.seat_polls.rescore
"""
import math
import numpy as np
from .common import read, fold, POLLS

CODES = {'nationalparty': 'NAT', 'labourparty': 'LAB', 'greenparty': 'GRN', 'actnewzealand': 'ACT', 'newzealandfirstparty': 'NZF',
         'unitedfuture': 'UF', 'theopportunitiespartytop': 'TOP'}
YEARS = (2017, 2020, 2023)


def contrasts():
    elections = {y: read(f'data/processed/elections/{y}.json') for y in YEARS}
    rows = []
    for p in read(POLLS)['polls']:
        if p['election'] not in elections or p['excluded']:
            continue
        found = [e for e in elections[p['election']]['electorates'] if fold(e['name']) == fold(p['electorate'])]
        if not found:
            continue
        actual = {CODES.get(c['partyKey'], c['partyKey']): c['share'] for c in found[0]['candidates']}
        shares = p['candidateVotePct']
        keys = [k for k in shares if actual.get(k, 0) > 0]
        n = p['sampleSize'] or 400
        total_poll, total_actual = sum(shares[k] for k in keys), sum(actual[k] for k in keys)
        leader = max(keys, key=lambda k: shares[k])
        for k in keys:
            if k == leader:
                continue
            error = math.log(actual[k] / actual[leader]) - math.log(shares[k] / shares[leader])
            variance = 1 / (n * shares[k] / 100) + 1 / (n * shares[leader] / 100)
            rows.append({'poll': p['id'], 'candidate': k, 'leader': leader, 'error': error, 'variance': variance, 'major': k in ('NAT', 'LAB')})
    return rows


def summary(rows=None):
    rows = rows or contrasts()
    e, v = np.array([r['error'] for r in rows]), np.array([r['variance'] for r in rows])
    major = np.array([r['major'] for r in rows])
    return {'contrasts': len(rows), 'polls': len({r['poll'] for r in rows}), 'ratio': float(np.mean(e ** 2 / v)), 'rms': float(np.sqrt(np.mean(e ** 2))),
            'ratioNationalLabour': float(np.mean(e[major] ** 2 / v[major])), 'ratioOther': float(np.mean(e[~major] ** 2 / v[~major])),
            'meanErrorOther': float(e[~major].mean())}


if __name__ == '__main__':
    for key, value in summary().items():
        print(f'{key}: {value:.3f}' if isinstance(value, float) else f'{key}: {value}')
