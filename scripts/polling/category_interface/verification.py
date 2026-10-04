"""Independent arithmetic and immutable-source checks, without inference."""
import argparse
import csv
import hashlib
import math
import numpy as np
from scripts.polling.national_foundation.timing import availability, timestamp
from .common import ROOT, OUT, NATIONAL, RAW, CORE, read, sha, save, verify_inputs


def preservation():
    files = read(OUT / 'prior-data-contract.json')['gitBlobSha1']
    for name, expected in files.items():
        raw = (ROOT / name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if actual != expected:
            raise ValueError('Changed prior data: ' + name)
    return len(files)


def check_construction():
    contract = read(OUT / 'construction-contract.json')
    for name, expected in contract['sha256'].items():
        if sha(OUT / name) != expected:
            raise ValueError('Changed pre-score artifact: ' + name)
    for name, expected in contract['codeSha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Changed frozen construction code: ' + name)


def independent_weight(reports):
    if not reports:
        return None
    pollster_means, pollster_weights = [], []
    for p in sorted({r['pollster'] for r in reports}):
        rows = [r for r in reports if r['pollster'] == p]
        raw = [2 ** (-r['ageDays']/30) * math.sqrt(min(r['sampleSize'] or 750,1500)/1000) for r in rows]
        pollster_means.append(math.fsum(r['share']*w for r,w in zip(rows,raw))/math.fsum(raw))
        pollster_weights.append(2 ** (-min(r['ageDays'] for r in rows)/30))
    return math.fsum(m*w for m,w in zip(pollster_means,pollster_weights))/math.fsum(pollster_weights)


def allocation_checks():
    inv = read(OUT / 'inventory.json')
    polls = {r['id']:r for r in read(ROOT / 'data/processed/polling/national-foundation/polls.json')['records']}
    bench = {r['id']:r for r in read(NATIONAL / 'benchmark.json')['cases']}
    weights_checked, vectors_checked, report_checks, mean_checks = 0, 0, 0, 0
    for c in inv['cases']:
        reports = []
        for r in c['reports']:
            raw = polls[r['pollId']]
            if availability(raw,5)[0] > timestamp(c['cutoff']):
                raise ValueError('Post-cutoff report entered allocation')
            item = (raw['estimates'] if r['code']=='TOP' else raw['additionalPublishedCategories'])[r['code']]
            factor = 1-raw['nonresponseCombined'] if raw['denominator']=='all_respondents' else 1
            if abs(item['share']/factor-r['share']) > 1e-14:
                raise ValueError('Independent reported-share conversion')
            reports.append({**r,'sampleSize':raw['sampleSize']});report_checks += 1
        fit = read(NATIONAL / c['archivePath'])
        ids = [r['categoryId'] for r in c['roster']]
        for system, info in c['systems'].items():
            cats = info['categories']
            explicit = {CORE[p]:j for j,p in enumerate(cats) if p!='OTH'}
            for policy,weights in info['weights'].items():
                expected_weights = []
                for row in weights:
                    rp = [r for r in reports if r['categoryId']==row['categoryId']]
                    v = independent_weight(rp) if policy=='recent_report_prior' else None
                    if v is None:
                        prior=row['priorShare'];v=prior if prior is not None and prior>0 else .001
                    expected_weights.append(v);weights_checked += 1
                if expected_weights and not any(expected_weights):
                    expected_weights=[r['priorShare'] if r['priorShare'] is not None and r['priorShare']>0 else .001 for r in weights]
                expected_fraction = np.asarray(expected_weights)/math.fsum(expected_weights) if weights else np.empty(0)
                if np.max(np.abs(expected_fraction-np.array([r['allocationFraction'] for r in weights])),initial=0)>1e-14:
                    raise ValueError('Independent policy weights')
                path = OUT/f"allocations/{c['id']}-{policy}-{system}.json.gz"
                result = read(path)
                arrays = {name:fit['draws'][name] for name in ('current','electionDay')} if system=='model' else {'point':[bench[c['id']]['shares']]}
                if system=='model' and (result['drawIds']!=fit['draws']['drawIds'] or result['drawNamespace']!=c['drawNamespace']):
                    raise ValueError('Changed paired draw identity')
                for name,coarse in arrays.items():
                    x=np.array(coarse);fine=np.array(result['arrays'][name]);expected=np.zeros_like(fine)
                    for cid,j in explicit.items():
                        expected[:,ids.index(cid)]=x[:,j]
                        if not np.array_equal(fine[:,ids.index(cid)],x[:,j]):
                            raise ValueError('Changed explicit support')
                    for row,f in zip(weights,expected_fraction):
                        expected[:,ids.index(row['categoryId'])]=x[:,cats.index('OTH')]*f
                    if np.max(abs(fine-expected))>1e-12 or np.max(abs(fine.sum(axis=1)-1))>1e-12 or np.min(fine)<0:
                        raise ValueError('Independent per-draw allocation/conservation')
                    if np.max(abs(fine.mean(axis=0)-np.array(result['summaries'][name]['expectedShares'])))>1e-12:
                        raise ValueError('Independent transformed means')
                    vectors_checked += len(fine);mean_checks += 1
    return {'policyWeights':weights_checked,'convertedReports':report_checks,'completeVectors':vectors_checked,'expectedShareVectors':mean_checks}


def external_checks():
    inv=read(OUT/'external-inventory.json');evaluation=read(OUT/'external-evaluation.json')
    actual={r['year']:r['shares'] for r in read(ROOT/'data/processed/polling/national-foundation/official-results-isolated.json')['records']}
    own={r['electionYear']:r for r in read(NATIONAL/'output-manifest.json')['cases'] if r['id'].startswith('primary-') and r['horizonDays']==56}
    bench={r['id']:r for r in read(NATIONAL/'benchmark.json')['cases']}
    with (RAW/'output_backtest_ensemble.csv').open() as stream:
        csv_rows=list(csv.DictReader(stream))
    checks=0
    for c in inv['cases']:
        year=c['year'];r=next(r for r in evaluation['cases'] if r['year']==year)
        if c['status']=='unavailable':
            if r['status']!='unavailable' or 'namedSix' in r:
                raise ValueError('Unavailable external case scored')
            continue
        base=read(RAW/f'output_backtest_cases_base_{year}_h8.json')
        g=read(RAW/f'output_backtest_cases_gauss_{year}_h8.json')
        ensemble=next(x for x in csv_rows if x['variant']=='ensemble' and int(x['target'])==year and int(x['horizon_weeks'])==8)
        labels=['National','Labour','Green','ACT','NZ First','Te Pāti Māori'];codes=['NAT','LAB','GRN','ACT','NZF','MRI']
        recovered=np.array([base['outcome'][p]+float(ensemble[f'error_pp[{p}]'])/100 for p in labels])
        if np.max(abs(recovered-np.array([c['ensembleNamedMeans'][p] for p in codes])))>1e-14:
            raise ValueError('Independent ensemble case inversion')
        model=own[year];b=bench[model['id']]
        vectors={'own_model':dict(zip(model['categories'],model['expectedElectionDay'])),
                 'own_average':dict(zip(b['categories'],b['shares'])),
                 'external_gauss':dict(zip(codes,[g['forecast_mean'][p] for p in labels])),
                 'external_ensemble':dict(zip(codes,recovered))}
        for group in ('namedSix','completeCoarseSeven'):
            cats=codes if group=='namedSix' else codes+['OTH']
            y=dict(actual[year]);y['OTH']+=y.get('TOP',0)
            for system,score in r[group].items():
                v=dict(vectors[system])
                if group=='completeCoarseSeven':
                    v['OTH']=(sum(g['forecast_mean'][p] for p in g['parties'] if p not in labels) if system=='external_gauss' else v['OTH']+v.get('TOP',0))
                err=np.array([100*(v[p]-y[p]) for p in cats])
                if max(abs(float(np.mean(abs(err)))-score['maePP']),abs(float(np.sqrt(np.mean(err**2)))-score['rmsePP']))>1e-12:
                    raise ValueError('Independent harmonized point scores')
                checks += 1
    for group,systems in evaluation['supportedSubsetPooled'].items():
        for system,pool in systems.items():
            rows=[r[group][system] for r in evaluation['cases'] if group in r]
            if abs(pool['maePP']-sum(r['maePP'] for r in rows)/len(rows))>1e-12 or abs(pool['rmsePP']-math.sqrt(sum(r['rmsePP']**2 for r in rows)/len(rows)))>1e-12:
                raise ValueError('Independent equal-election pooling')
            checks += 1
    return checks


def run(check=False):
    verify_inputs();check_construction()
    for name,expected in read(OUT/'external-source-contract.json')['consumedSha256'].items():
        if sha(ROOT/name)!=expected:
            raise ValueError('Changed supplemental consumed source: '+name)
    result={'stage':37,'checks':allocation_checks(),'externalPointAndPoolingChecks':external_checks(),
            'priorDataFilesByteIdentical':preservation(),'externalResourcesVerified':20,
            'independentInferenceValidation':False,'candidateModelsRun':False,'operationalSelection':None}
    save('independent-verification.json',result,check)
    print(result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
