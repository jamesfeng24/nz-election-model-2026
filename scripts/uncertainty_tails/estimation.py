"""Earlier-only robust central scale; shared effects and other directions unchanged."""
import copy
import numpy as np
from scipy.stats import norm, t
from scripts.uncertainty_revision.coordinates import coordinates
from scripts.uncertainty_revision.estimation import environment
from .diagnosis import weighted_quantile
from .common import PREFIX, CONTROL, INVENTORY, read, save, verify, arguments


def central_fit(rows, target, specification):
    eligible = [r for r in rows if r['targetYear'] < target]
    years = sorted({r['targetYear'] for r in eligible}); moments = []
    for year in years:
        subset = [r for r in eligible if r['targetYear'] == year]
        effect = environment(subset)['moments']['balance'].get('descriptiveElectionEffect')
        if effect is None: continue
        values = [float(coordinates(r['actual'],r['groups'])['balance']-coordinates(r['mean'],r['groups'])['balance']-effect)
                  for r in subset if coordinates(r['actual'],r['groups'])['balance'] is not None]
        if not values: continue
        x = np.asarray(values); weights = np.ones(len(x))
        median = float(weighted_quantile(x,weights,[.5])[0])
        mad = float(weighted_quantile(np.abs(x-median),weights,[.5])[0])
        moments.append({'year':year,'records':len(x),'sharedEffect':effect,'median':median,'mad':mad,
                        'rms':float(np.sqrt(np.mean(x*x))), 'allObservationsRetained':True})
    prior_mad = specification['priorMADGaussianSD']*norm.ppf(.75)
    pseudo = specification['pseudoEnvironments']; denominator = len(moments)+pseudo
    historical = sum(m['mad']**2 for m in moments)/denominator
    prior = pseudo*prior_mad**2/denominator
    mad = float(np.sqrt(historical+prior)); nu = specification['nu']
    student_scale = mad/t.ppf(.75,nu)
    return {'targetYear':target,'trainingYears':years,'trainingIds':[r['targetElectorateId'] for r in eligible],
            'moments':moments,'pooledMAD':mad,'centralHistoricalSquaredContribution':historical,
            'centralPriorSquaredContribution':prior,'priorMAD':float(prior_mad),
            'gaussianSD':float(mad/norm.ppf(.75)), 'studentScale':float(student_scale),
            'studentSD':float(student_scale*np.sqrt(nu/(nu-2))), 'nu':nu,'nuEstimated':False,
            'status':'prior_only' if not moments else 'strongly_pooled_earlier_election_centre'}


def build():
    old = read(CONTROL+'/scales.json'); inventory = read(INVENTORY); spec = read(PREFIX+'/specification.json')
    central = [central_fit(inventory['candidateRecords'],f['targetYear'],spec) for f in old['folds']['candidate']]
    methods = {'stage45':copy.deepcopy(old)}
    for method in ('robust_gaussian','student'):
        value = copy.deepcopy(old)
        for fold, scale in zip(value['folds']['candidate'],central):
            fold['scales']['balance']['seat'] = scale['gaussianSD'] if method=='robust_gaussian' else scale['studentScale']
            fold['centralScale'] = scale
            fold['seatBalanceDistribution'] = method
        methods[method] = value
    return {'stage':46,'methods':methods,'centralFits':central,'distributionScope':'candidate seat balance only',
            'descriptiveStage45EntriesAreNotUsedInForecasts':True}


def main():
    args=arguments();verify();save('scales.json',build(),args.check)
    print('Stage46 earlier-only central scales reproduced; tail nu assumed')


if __name__=='__main__':main()
