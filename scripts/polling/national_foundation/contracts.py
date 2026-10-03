"""Small compositional/output contracts; all examples are synthetic."""
import math


def simplex(values):
    if not values or any(not math.isfinite(x) or x<0 for x in values) or abs(sum(values)-1)>1e-10:
        raise ValueError('Invalid joint simplex')


def output_contract(value):
    required=('modelVersion','partySchemaVersion','cutoff','electionDate','informationSet',
              'sourceIds','assumptionFlags','expectedCurrentShares','expectedElectionDayShares','draws')
    if any(k not in value for k in required):raise ValueError('Output metadata')
    from .timing import timestamp
    timestamp(value['cutoff'])
    keys=set(value['expectedCurrentShares'])
    if keys!=set(value['expectedElectionDayShares']):raise ValueError('Output party schema')
    simplex(list(value['expectedCurrentShares'].values()));simplex(list(value['expectedElectionDayShares'].values()))
    seen=set()
    for draw in value['draws']:
        if draw['drawId'] in seen:raise ValueError('Duplicate draw ID')
        seen.add(draw['drawId'])
        for name in ('currentShares','electionDayShares'):
            if set(draw[name])!=keys:raise ValueError('Draw party schema')
            simplex(list(draw[name].values()))
    if not seen:raise ValueError('No joint draws')
    for mean_name,draw_name in [('expectedCurrentShares','currentShares'),('expectedElectionDayShares','electionDayShares')]:
        for k in keys:
            avg=sum(d[draw_name][k] for d in value['draws'])/len(seen)
            if abs(avg-value[mean_name][k])>1e-10:raise ValueError('Expected shares must average transformed draws')


def reported_rows(record, categories):
    """Keep a partial observation operator; never make missing parties zero."""
    rows=[]
    for p in categories:
        obs=record['estimates'].get(p)
        if obs and obs['status']!='not_reported':rows.append({'category':p,**obs})
    if record['publishedOther']['status']!='not_reported':
        rows.append({'category':'OTH','requiresExclusiveDefinition':True,**record['publishedOther']})
    return rows


def build_inputs(records,cutoff,completed_results,lag=5):
    from .timing import select,timestamp
    admitted,excluded=select(records,cutoff,lag)
    anchors=[r for r in completed_results if timestamp(r['availableAt'])<=timestamp(cutoff) and
             timestamp(r['electionAt'])<timestamp(cutoff)]
    return {'polls':admitted,'exclusions':excluded,'completedAnchors':anchors,'cutoff':cutoff}
