"""Paired original-only versus expanded training on identical 2017/2023 targets."""
from .evaluation import candidate_summary, response_summary
from .common import OLD_RESPONSE, read


def compare(results):
    candidates, responses = [], []
    for protocol in ('expanding_window', 'more_separated'):
        for year in (2017, 2023):
            cases = {r['trainingVariant']: r for r in results['candidateCases']
                     if r['chronologyProtocol'] == protocol and r['targetYear'] == year}
            for scenario in ('printed', 'selected_lower', 'selected_upper'):
                before = {r['targetElectorateId']: r for r in cases['original_only']['scenarios'][scenario]['records']}
                after = cases['expanded']['scenarios'][scenario]['records']
                if set(before) != {r['targetElectorateId'] for r in after}:
                    raise ValueError('Training comparison evaluation IDs differ')
                scores = {}
                for model in ('baseline', 'baseline_plus_S'):
                    rows = []
                    for r in after:
                        # Alias method names solely for the existing paired reporting kernel.
                        rows.append({'targetElectorateId': r['targetElectorateId'],
                                     'methods': {'baseline': before[r['targetElectorateId']]['methods'][model],
                                                 'baseline_plus_S': r['methods'][model],
                                                 'uniform': r['methods']['uniform'],
                                                 'restrictedZeroFloor': r['methods']['restrictedZeroFloor']}})
                    summary = candidate_summary(rows)
                    scores[model] = {'expandedTraining': summary['methods']['baseline_plus_S'],
                                    'originalTraining': summary['methods']['baseline'],
                                    'expandedMinusOriginalPaired': summary['S_vs_baseline']}
                candidates.append({'chronologyProtocol': protocol, 'targetYear': year,
                                   'scenario': scenario, 'methods': scores})
            definitions = read(OLD_RESPONSE + 'specification.json')['models']
            for party in ('nationalparty', 'labourparty'):
                rcases = {r['trainingVariant']: r for r in results['responseCases'] if r['targetYear'] == year
                          and r['chronologyProtocol'] == protocol and r['party'] == party}
                before = {r['id']: r for r in rcases['original_only']['records']}
                after = rcases['expanded']['records']
                if set(before) != {r['id'] for r in after}:
                    raise ValueError('Response training comparison sample differs')
                scores = {}
                for model in definitions:
                    rows = [{**r, 'predictions': {'expanded': r['predictions'][model],
                            'original': before[r['id']]['predictions'][model]}} for r in after]
                    scores[model] = response_summary(rows, ('expanded', 'original'), [('expanded', 'original')])
                responses.append({'chronologyProtocol': protocol, 'targetYear': year, 'party': party, 'methods': scores})
    return {'candidate': candidates, 'response': responses}
