"""Bounded numerical accuracy/cost pilot, never predictive scoring."""
import time
import numpy as np
from scripts.uncertainty_revision.coordinates import partition
from scripts.uncertainty_revision.estimation import labels
from scripts.uncertainty.construction import scale_for, national_case
from scripts.polling.candidate_integration.propagation import local_vectors, candidate_vectors
from scripts.uncertainty.simulation import candidate_inputs
from scripts.uncertainty_tails.streams import noise, permutation
from scripts.uncertainty_tails.integration import conditional_inverse, conditional_offsets, within_nodes
from scipy.special import softmax
from .common import read, save, verify, arguments, INVENTORY, SCALES
from .integration import solve_locations, rule, expectation


def component_solve(row, scale):
    other = partition(row['groups'])[2]
    raw = np.array(row['mean'])[other]
    if len(other)<2 or raw.sum()==0:
        return np.zeros(len(other)), []
    p = raw/raw.sum()
    return solve_locations(p, [labels(row)[i] for i in other], scale['within']['shared'], scale['within']['seat'])


def build():
    inventory = read(INVENTORY)
    scales = read(SCALES)
    records = []
    started = time.monotonic()
    for key,layer in (('partyRecords','local_party'),('candidateRecords','candidate')):
        for row in inventory[key]:
            fit = scale_for(scales,layer,row['targetYear'])['scales']
            t = time.monotonic()
            offset,audit = component_solve(row,fit)
            records.append({'id':row['targetElectorateId'],'layer':layer,'offset':offset.tolist(),'checks':audit,
                            'elapsedSeconds':time.monotonic()-t})
            if time.monotonic()-started>1200:
                break
    # Recover the exact input responsible for Stage46's reported maximum.
    year = 2023; candidate = next(r for r in inventory['candidateRecords'] if r['targetElectorateId']=='nz-general-2023-electorate-17')
    party = next(r for r in inventory['partyRecords'] if r['targetElectorateId']==candidate['targetElectorateId'])
    national,_,_ = national_case(year,party['ids'],4096)
    national = national[permutation(4096,'national:2023')]
    select = [0,0,4095]  # Stage46 count32768 first/middle/last -> base0/base0/base4095.
    stage46_scales=read('data/processed/uncertainty-tails/scales.json')['methods']['robust_gaussian']
    ps=scale_for(stage46_scales,'local_party',year)['scales'];cs=scale_for(stage46_scales,'candidate',year)['scales']
    eta,total=noise(party,ps,32768)
    eta={key:value[[0,16384,32767]] for key,value in eta.items()}
    deterministic=local_vectors(national[select],party['affinities'])
    local,_=conditional_inverse(deterministic,party['groups'],eta,total,tags=labels(party))
    destinations,exponent,floor=candidate_inputs(candidate,party)
    base=candidate_vectors(local,destinations,exponent,floor)
    other=partition(candidate['groups'])[2]
    p=base[:,other];mass=p.sum(axis=1);p=p/mass[:,None];tags=[labels(candidate)[i] for i in other]
    shared,seat=cs['within']['shared'],cs['within']['seat'];sd=float(np.hypot(shared,seat))
    original=conditional_offsets(p,sd,tags=tags,shared=shared,seat=seat)
    rows=[]
    for i,probability in enumerate(p):
        # Independent larger quadratures assess the old low-node reference itself.
        refs=[]
        for size in (131072,262144):
            for seed in (470147,470247):
                nodes,w=rule(tuple(tags),shared,seat,size,seed)
                refs.append({'size':size,'seed':seed,'expectation':expectation(probability,original[i],nodes,w).tolist()})
        corrected,audit=solve_locations(probability,tags,shared,seat)
        values=np.array([r['expectation'] for r in refs])
        old_refs={}
        for size in (128,256):
            z=within_nodes(len(tags),sd,size,tags,shared,seat,460146+size)
            old_refs[str(size)]=(100*np.max(np.abs(softmax(np.log(probability)+original[i]+z,axis=-1).mean(axis=0)-probability))*mass[i])
        rows.append({'inputIndex':[0,16384,32767][i],'probability':probability.tolist(),'remainderMass':float(mass[i]),'labels':tags,
                     'oldOffset':original[i].tolist(),'oldReportedReferencesGapPP':old_refs,'higherPrecisionReferences':refs,
                     'referenceSpreadPP':float(100*np.max(np.ptp(values,axis=0))*mass[i]),
                     'oldLocationHigherReferenceGapPP':float(100*np.max(np.abs(values-probability))*mass[i]),
                     'correctedOffset':corrected.tolist(),'correctedChecks':audit})
    failures=[{'id':r['id'],'checks':r['checks']} for r in records if any(not c['passed'] for c in r['checks'])]
    return {'stage':47,'numericalOnly':True,'componentRecords':records,'componentRecordsChecked':len(records),
            'componentFailures':failures,'originalWorstReference':rows,'predictiveScoresCalculated':False,
            'elapsedSeconds':time.monotonic()-started,'timingIsNotPortableReproductionField':True}


def main():
    args=arguments();verify();value=build()
    # Clock costs are observations, not a deterministic statistical output.
    if args.check:
        old=read('data/processed/uncertainty-expectation/pilot.json')
        for row in value['componentRecords']:
            row.pop('elapsedSeconds')
        for row in old['componentRecords']:
            row.pop('elapsedSeconds')
        value.pop('elapsedSeconds');old.pop('elapsedSeconds')
        from scripts.uncertainty_revision.common import equivalent
        if not equivalent(value,old):raise ValueError('Changed Stage47 numerical pilot')
    else:save('pilot.json',value)
    print('Pilot checked',value['componentRecordsChecked'],'constant vectors; failures',len(value['componentFailures']),flush=True)


if __name__=='__main__':main()
