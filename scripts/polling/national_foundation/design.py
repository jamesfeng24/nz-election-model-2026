"""Machine contract and isolated official anchors; not national predictions."""
import json
from .run import ROOT,DATES,save
from .timing import day_end

NAMES={'NAT':'National Party','LAB':'Labour Party','GRN':'Green Party','ACT':'ACT New Zealand',
       'NZF':'New Zealand First Party','MRI':'Māori Party','TOP':'The Opportunities Party (TOP)'}
ALIASES={'New Zealand National Party':'NAT','New Zealand Labour Party':'LAB',
         'New Zealand First':'NZF','Maori Party':'MRI','Te Pāti Māori':'MRI',
         'The Opportunities Party':'TOP','Opportunities Party':'TOP'}


def category(name):
    reverse={v:k for k,v in NAMES.items()}
    return ALIASES.get(name,reverse.get(name,'OTH'))


def anchors():
    out=[]
    for year in (2011,2014,2017,2020,2023):
        data=json.loads((ROOT/f'data/processed/elections/{year}.json').read_text())
        counts={p:0 for p in (*NAMES,'OTH')}
        detailed=[]
        for row in data['nationalControls']['parties']:
            if row['partyVotes'] is None:
                detailed.append({'publishedGroup':row['name'],'modelCategory':None,'count':None,'status':'candidate_affiliation_not_party_ballot_group','sourceId':row['sourceId']});continue
            p=category(row['name']);counts[p]+=row['partyVotes']
            detailed.append({'publishedGroup':row['name'],'modelCategory':p,'count':row['partyVotes'],'sourceId':row['sourceId']})
        total=sum(counts.values())
        if total!=data['nationalControls']['party']['national']['validVotes']:raise ValueError('National denominator')
        election=DATES.get(year,'2011-11-26')
        out.append({'year':year,'electionAt':day_end(election).isoformat(),
          'availableAt':day_end(f'{year+1}-01-01').isoformat(),'availabilityQuality':'conservative_next_year_assumption',
          'role':'earlier_training_anchor_or_separate_heldout_evaluation; selection must precede access',
          'validPartyVotes':total,'shares':{p:n/total for p,n in counts.items()},'categoryEvidence':detailed})
    return out


def specification():
    return {'schemaVersion':1,'stage':35,'status':'frozen_design_no_fit',
      'evidenceLayers':['component_validation','fixed_fit_input_substitution','dated_end_to_end_replay'],
      'activeCandidateAlternatives':['S','S+R','R','baseline'],
      'model':'weekly_isotropic_ilr_random_walk_with_centered_house_and_cycle_bias',
      'outputs':['current_latent_support','election_day_support'],
      'categories':{str(y):['NAT','LAB','GRN','ACT','NZF','MRI']+(['TOP'] if y>=2017 else [])+['OTH'] for y in DATES},
      'initialization':{'entryMeanShare':0.002,'entryContrastSD':1.0,'continuingContrastSD':0.01,
                        'mean':'H.T @ log(seeded_previous_simplex)',
                        'covariance':'H.T @ diag(category_variance) @ H; entrant1.0^2, continuing0.01^2',
                        'unsupportedContinuingZero':'construction_abstention_no_undeclared_seed',
                        'completedElectionShareObservationSD':0.0005},
      'likelihood':{'name':'conditional_independent_gaussian_interval_probability',
        'variance':'2*mu*(1-mu)/n_decided + 0.005^2','rounding':'published cell intervals, no pseudo-counts',
        'fieldwork':'uniform day-weighted probability vector average','missing':'unobserved, not zero',
        'aggregate':'exclusive supported group once; unidentified subcategories not duplicated'},
      'priors':{'sigmaWeeklyHalfNormal':0.035,'houseScaleHalfNormal':0.12,
        'methodBreakNormalSD':0.05,'commonCycleBiasScaleHalfNormal':0.08,
        'innovationCovariance':'fixed identity in orthonormal Helmert coordinates'},
      'assumptions':{'samplingInflation':2,'unknownDecidedFraction':0.85,'missingNominalN':750,
        'unverifiedDenominator':'decided_voters','publicationLagDays':5,
        'historicalResultAvailability':'next January1 NZ end-of-day assumed'},
      'branches':['primary','publication_lag10','missing_n1000'],
      'verifiedOnly':'coverage audit; evaluate only if estimable, never replace primary inferred quality label',
      'inference':{'dependencyPins':{'numpyro':'0.19.0','jax':'0.6.2','jaxlib':'0.6.2'},
        'dependencyAudit':'preserved PyPI metadata; declared Python3.12/numpy2.2.6/scipy1.16.0 compatibility, not runtime-tested',
        'method':'NumPyro NUTS CPU64','chains':4,'warmup':2000,'drawsPerChain':2000,
        'targetAccept':0.95,'maxTreeDepth':12,'chainSeeds':[3501,3502,3503,3504],
        'maxRhat':1.01,'minBulkTailESS':400,'maxDivergences':0,
        'failureRetry':{'targetAccept':0.99,'maxTreeDepth':15,'warmup':4000,'limit':1}},
      'benchmark':{'schema':['NAT','LAB','GRN','ACT','NZF','MRI','OTH'],'halfLifeDays':30,
        'maxAgeDays':180,'sampleWeight':'sqrt(min(n,1500)/1000)','missingN':750,
        'pollsterWeight':'recency of latest wave, no volume weight','overlap':'latest wave only',
        'pollVector':'unique constrained least squares within rounding bounds; complete six-core only',
        'forecast':'cutoff mean carried forward; no probability distribution'},
      'evaluation':{'elections':[2014,2017,2020,2023],'horizonsDays':[14,56],
        'weights':'equal elections; half weight per horizon','point':['MAE','RMSE','party_bias'],
        'probability':['marginal_CRPS','50/90_coverage_and_width','joint_energy_score'],
        'benchmarkComparison':'coarsen TOP into Other on same available cases'},
      'stopping':'one primary model/benchmark/finite branches; no score-guided variants or candidate replay',
      'exactNext':'single national implementation and eight chronological national cases; then separately authorized fixed-alternative end-to-end replay'}


def run(check=False):
    save('specification.json',specification(),check)
    save('official-results-isolated.json',{'schemaVersion':1,'records':anchors()},check)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
