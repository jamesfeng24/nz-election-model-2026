"""Read-only common audit of transition-specific feasible crosswalks."""
import argparse
import hashlib
import json
from fractions import Fraction
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.coupled import PopulationSystem

TRANSITIONS=('2011-2014','2017-2020','2023-2026')


def fraction(value):
    return Fraction(value['numerator'],value['denominator'])


def system(scope):
    constraints=scope['constraints']
    groups=constraints.get('groups')
    if groups is None:
        groups=[{'id':e['source']+'-'+e['target'],'source':e['source'],'targets':[e['target']],
                 'lower':e['lower'],'upper':e['upper']} for e in scope['edges']]
    controls={r['target']:r['sumIncomingPopulation'] for r in constraints['destinationEquations']}
    return PopulationSystem(groups,controls)


def audit_scope(scope):
    p=system(scope)
    sources={r['code']:r for r in scope['sources']}
    targets={r['code']:r for r in scope['targets']}
    if len(sources)!=len(scope['sources']) or len(targets)!=len(scope['targets']):
        raise ValueError('Duplicate electorate identity')
    if {s for _,s,_ in p.variables}!=set(sources) or set(p.controls)!=set(targets):
        raise ValueError('Incomplete electorate coverage')
    edges={(e['source'],e['target']):e for e in scope['edges']}
    if len(edges)!=len(scope['edges']) or set(edges)!=set(p.edge_inventory()):
        raise ValueError('Invalid flow inventory')
    for s,r in sources.items():
        if p.bounds(p.vector(s))!=(r['populationLower'],r['populationUpper']):
            raise ValueError('Source population bounds do not match global system')
    for (s,t),e in edges.items():
        a,b=p.vector(s,t),p.vector(s)
        if p.bounds(a)!=(e['lower'],e['upper']):raise ValueError('Incorrect global flow bounds')
        if (p.ratio(a,b),p.ratio(a,b,True))!=(fraction(e['weightLower']),fraction(e['weightUpper'])):
            raise ValueError('Incorrect global weight bounds')
        if e['weight'] is not None and fraction(e['weightLower'])!=fraction(e['weightUpper']):
            raise ValueError('Unidentified weight replaced with a point')
    for t,r in targets.items():
        if r['populationControl']!=p.controls[t]:raise ValueError('Control mismatch')
        for c in r['composition']:
            e=edges[c['source'],t]
            if (fraction(c['shareLower']),fraction(c['shareUpper']))!=(Fraction(e['lower'],p.controls[t]),Fraction(e['upper'],p.controls[t])):
                raise ValueError('Invalid predecessor composition')
    witness=p.solve(p.vector())
    for s in sources:
        denominator=sum(witness*p.vector(s))
        weights=[sum(witness*p.vector(s,t))/denominator for t in targets]
        if abs(sum(weights)-1)>1e-12:raise ValueError('Source weight conservation')
    return {'sources':len(sources),'targets':len(targets),'edges':len(edges),
            'controlsSatisfied':len(p.controls),'maximumWeightIntervalWidth':max(float(fraction(e['weightUpper'])-fraction(e['weightLower'])) for e in edges.values()),
            'globalExtremaAndWitnessChecks':'passed'}


def build():
    results={}
    for transition in TRANSITIONS:
        path=ROOT/f'data/processed/boundaries/{transition}/crosswalk.json'
        raw=path.read_bytes();value=json.loads(raw)
        manifest=json.loads(path.with_name('manifest.json').read_bytes())
        if hashlib.sha256(raw).hexdigest()!=manifest['outputSha256']:raise ValueError('Crosswalk integrity')
        for p,digest in manifest['inputHashes'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest:raise ValueError('Changed crosswalk input '+p)
        results[transition]={'crosswalkSha256':hashlib.sha256(raw).hexdigest(),
                             'scopes':{k:audit_scope(s) for k,s in value['scopes'].items()}}
    return {'schemaVersion':1,'status':'passed','transitions':results,
            'conservation':'Every feasible assignment conserves source population and outgoing weight; marginal interval endpoints must not be summed as an assignment.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    raw=(json.dumps(build(),ensure_ascii=False,indent=2)+'\n').encode()
    path=ROOT/'data/processed/boundaries/validation.json'
    if args.check:
        if not path.exists() or path.read_bytes()!=raw:raise ValueError('Stale common boundary audit')
    else:path.write_bytes(raw)
    print('Three-transition global contract audit passed')


if __name__=='__main__':main()
