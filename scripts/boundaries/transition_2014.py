"""Source-specific Level B adapter producing the common transition contract."""
import argparse
import hashlib
import json
from fractions import Fraction
from scripts.boundaries.census_2013 import ROOT
from scripts.boundaries.inputs_2014 import load
from scripts.boundaries.coupled import PopulationSystem
from scripts.boundaries.feasible import fraction_json


def scope_output(inputs):
    p=PopulationSystem(inputs['groups'],inputs['controls'])
    edges=[]
    sources=[]
    for s,name in sorted(inputs['names']['source'].items()):
        lo,hi=p.bounds(p.vector(s))
        sources.append({'code':s,'name':name,'populationLower':lo,'populationUpper':hi,
                        'outgoingWeightSum':1,'sumInterpretation':'every joint feasible allocation'})
    for s,t in p.edge_inventory():
        a,b=p.vector(s,t),p.vector(s)
        lo,hi=p.bounds(a)
        wl,wu=p.ratio(a,b),p.ratio(a,b,True)
        edges.append({'source':s,'target':t,'lower':lo,'upper':hi,
                      'populationPointEstimate':lo if lo==hi else None,
                      'weightLower':fraction_json(wl),'weightUpper':fraction_json(wu),
                      'weight':float(wl) if wl==wu else None,
                      'weightIntervalWidth':float(wu-wl),'uniquelyIdentified':wl==wu})
    targets=[]
    for t,name in sorted(inputs['names']['target'].items()):
        incoming=[e for e in edges if e['target']==t]
        total=inputs['controls'][t]
        certain=[]
        for e in incoming:
            if all(p.bounds(p.vector(e['source'],t)-p.vector(other['source'],t))[0]>0
                   for other in incoming if other is not e):certain.append(e['source'])
        dl=Fraction(max(e['lower'] for e in incoming),total)
        du=Fraction(max(e['upper'] for e in incoming),total)
        targets.append({'code':t,'name':name,'populationControl':total,
            'officialChangeStatus':None,'officialChangeStatusAvailability':'report control not yet transcribed',
            'membershipIdentity':len(incoming)==1 and inputs['names']['source'][incoming[0]['source']]==name,
            'dominantPredecessor':certain[0] if len(certain)==1 else None,
            'dominantPredecessorShareLower':fraction_json(dl),
            'dominantPredecessorShareUpper':fraction_json(du),
            'nonDominantPopulationShareLower':fraction_json(1-du),
            'nonDominantPopulationShareUpper':fraction_json(1-dl),
            'dominantShareBoundsType':'conservative enclosure; dominance identity tested in global system',
            'predecessorCount':len(incoming),
            'composition':[{'source':e['source'],'shareLower':fraction_json(Fraction(e['lower'],total)),
                            'shareUpper':fraction_json(Fraction(e['upper'],total))} for e in incoming]})
    return {'sources':sources,'targets':targets,'edges':edges,
        'constraints':{'populationVariables':p.variables,'groups':inputs['groups'],
            'destinationEquations':[{'target':k,'sumIncomingPopulation':v} for k,v in sorted(inputs['controls'].items())],
            'domain':'nonnegative real electoral-population contributions; network extrema are integral',
            'sourcePopulation':'sum of all source group contributions',
            'outgoingWeights':'flow population / source population',
            'jointConstraintWarning':'All group bounds and destination equations apply simultaneously; marginal endpoints are not independent.'}}


def build():
    inputs=load()
    return {'schemaVersion':1,'transition':{'id':'2011-2014','sourceElectionYear':2011,'targetElectionYear':2014,
        'sourceBoundaryVersion':'2007','targetBoundaryVersion':'2014','populationVintage':'2013 Census',
        'adapter':'inputs_2014','populationBasisLevel':'B'},
        'status':'validated_population_feasible_set_change_audit_pending',
        'dataClass':'synthetic_reconstruction_constraints_not_observed_votes',
        'nominalAllocation':None,'inputHashes':inputs['inputHashes'],
        'scopes':{k:scope_output(v) for k,v in inputs['scopes'].items()},
        'splitEvidence':inputs['splitEvidence'],
        'splitPublishedResidentTotal':inputs['splitPublishedResidentTotal'],
        'outsideWithoutCensus':inputs['outsideWithoutCensus'],
        'outsideTargetRecords':inputs['outsideTargetRecords'],
        'method':{'electoralDescent':'Y <= D <= U-N, with rounded category/partition constraints',
            'unknownRollProportion':'0 <= r <= 1; no national or island ratio substituted locally',
            'generalBounds':'N <= G <= U','maoriBounds':'0 <= M <= D',
            'scopeSeparation':'G and M are separate geographic calculation universes, not a forced common-ratio partition',
            'solver':'SciPy 1.16.0 HiGHS dual simplex; integral network witnesses; exact rational fractional objectives',
            'identification':'Sharp flow/source/weight bounds conditional on this necessary-constraint outer feasible set; not recovery of the unpublished official calculation'},
        'limitations':['Absent local roll counts and individual imputation leave broad uncertainty, not a statistical confidence interval.',
            '22 parent meshblocks retain coupled descendant allocations; no whole-parent assignment or nominal population.',
            'Two zero-published-resident units become officially outside the final electoral universe. Their resident bounds remain in separate evidence, not silently changed to observed zero.',
            'No candidate-person linking, geography harmonization, fitted model or observed-result modification.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    result=build()
    raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    paths=['scripts/boundaries/'+x+'.py' for x in ['transition_2014','inputs_2014','census_2013','coupled']]
    manifest={'schemaVersion':1,'transitionId':'2011-2014','inputHashes':result['inputHashes'],
        'codeHashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'outputSha256':hashlib.sha256(raw).hexdigest(),
        'coverage':{k:{'sources':len(v['sources']),'targets':len(v['targets']),'edges':len(v['edges'])} for k,v in result['scopes'].items()}}
    folder=ROOT/'data/processed/boundaries/2011-2014'
    for name,content in {'crosswalk.json':raw,'manifest.json':(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()}.items():
        path=folder/name
        if args.check:
            if not path.exists() or path.read_bytes()!=content:raise ValueError('Stale '+str(path))
        else:
            folder.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    print(json.dumps(manifest['coverage']))


if __name__=='__main__':main()
