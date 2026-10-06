"""Individual forecast-leading option widths, distinct from their margin width."""
from .common import PREFIX, arguments, read, save, verify
from .audits import width_summary


def selected_options(row):
    pair = row['ranking']['predictionTimePair']['ids']
    indices = [row['ids'].index(i) for i in pair]
    return {'id': row['id'], 'year': row['year'], 'ids': pair,
        'groups': ['forecast_selected']*2, 'crpsPP': [row['crpsPP'][i] for i in indices],
        **{'interval'+str(level): {k: [row['interval'+str(level)][k][i] for i in indices]
            for k in ('covered','widths','scores')} for level in (50,80,90)}}


def build():
    original = read(PREFIX+'/original-audit.json')['sources']['originalStage45_8000']['cases']
    evaluation = read(PREFIX+'/evaluation.json')['cases']
    sources = {'originalStage45_8000': original}
    for method in ('common_control','corrected'):
        sources[method] = [{'id': c['id'], 'year': c['year'], 'layer': c['layer'], 'records': c['methods'][method]['records']}
                           for c in evaluation if c['layer'] != 'local_party']
    results = {}
    for source,cases in sources.items():
        records = {c['id']: [selected_options(r) for r in c['records']] for c in cases}
        results[source] = {'cases': [{'id': c['id'], 'year': c['year'], 'layer': c['layer'],
                'summary': width_summary(records[c['id']], 'forecast_selected')} for c in cases],
            'pooled': {layer: {weights: width_summary([r for c in cases if c['layer'] == layer for r in records[c['id']]],
                        'forecast_selected', weights=='equalElection') for weights in ('contestWeighted','equalElection')}
                       for layer in ('candidate','composed')}}
    return {'stage':47,'sources':results,'noNewForecastOrScoreBank':True,
        'denominator':'two prediction-time selected candidates per contest; average their widths/scores within contest, then declared weights',
        'notMarginWidth':'Individual share spans are separate from correlated difference intervals; no renormalization of the pair.',
        'originalSelectionCaveat':'Original8000bank keeps own saved prediction-time pair; common-control/corrected share identical fixed512 composed selections.'}


def main():
    args=arguments()
    verify()
    save('leading-pair-options.json',build(),args.check)


if __name__=='__main__':
    main()
