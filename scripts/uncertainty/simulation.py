"""Reusable frozen-mean simulation; outcomes never read by this adapter."""
import numpy as np
from scripts.polling.candidate_integration.propagation import local_vectors, candidate_vectors
from .streams import noise
from .transforms import preserve_mean


def candidate_inputs(candidate, party):
    if len(set(candidate['ids']))!=len(candidate['ids']):raise ValueError('Duplicate candidate ID')
    if [c['id'] for c in candidate['features']]!=candidate['ids']:raise ValueError('Candidate feature order differs')
    lookup = {g:i for i,g in enumerate(party['ballotGroupKeys'])}
    if len(lookup)!=len(party['ids']):raise ValueError('Duplicate party group')
    dest, exponent = [], []
    parameters=candidate['parameters']
    if parameters['status']!='fitted' or len(parameters['theta'])!=2:raise ValueError('Frozen joint fit unavailable')
    if not np.isfinite(parameters['kappa']) or not .0001<=parameters['kappa']<=.1:raise ValueError('Invalid frozen floor')
    if parameters['coefficients']!={'S':parameters['theta'][0],'R':parameters['theta'][1]}:raise ValueError('Coefficient semantics differ')
    if not all(np.isfinite(t) and -4<=t<=4 for t in parameters['theta']):raise ValueError('Invalid frozen coefficient')
    for c in candidate['features']:
        if len(c['centered'])!=2 or not all(np.isfinite(z) for z in c['centered']):raise ValueError('Invalid frozen feature')
        g=c['group']
        if g is not None and g not in lookup:raise ValueError('Missing complete candidate group destination')
        dest.append(-1 if g is None else lookup[g])
        exponent.append(sum(t*z for t,z in zip(parameters['theta'],c['centered'])))
    mapped=[d for d in dest if d>=0]
    if len(set(mapped))!=len(mapped):raise ValueError('Duplicate standing group destination')
    return dest,exponent,parameters['kappa']


def component(row, scales, draws, stress=False):
    eta=noise(row,scales,draws,stress)
    q,location=preserve_mean(row['mean'],eta)
    return q,{'meanModel':row['mean'],'simulatedMean':q.mean(axis=0).tolist(),
        'location':location,'scales':scales,'draws':draws,
        'expectedShareShiftPP':(100*(q.mean(axis=0)-np.array(row['mean']))).tolist()}


def compose(party,candidate,national,party_scales,candidate_scales,stress=False,batch_size=128):
    if type(batch_size)!=int or batch_size<=0:raise ValueError('Invalid batch size')
    x=np.asarray(national,dtype=float)
    deterministic=local_vectors(x,party['affinities'])
    local,local_location=preserve_mean(deterministic,noise(party,party_scales,len(x)))
    dest,exponent,kappa=candidate_inputs(candidate,party)
    base=np.concatenate([candidate_vectors(local[i:i+batch_size],dest,exponent,kappa) for i in range(0,len(x),batch_size)])
    q,candidate_location=preserve_mean(base,noise(candidate,candidate_scales,len(x),stress))
    control=candidate_vectors(deterministic,dest,exponent,kappa)
    return q,{'deterministicNationalOnlyMean':control.mean(axis=0).tolist(),
        'candidateConditionalMeanAfterLocalUncertainty':base.mean(axis=0).tolist(),
        'simulatedMean':q.mean(axis=0).tolist(),'localLocation':local_location,'candidateLocation':candidate_location,
        'nonlinearUpstreamMeanShiftPP':(100*(base.mean(axis=0)-control.mean(axis=0))).tolist(),
        'candidateAdjustmentMeanShiftPP':(100*(q.mean(axis=0)-base.mean(axis=0))).tolist(),
        'localMarginalMeanShiftPP':(100*(local.mean(axis=0)-deterministic.mean(axis=0))).tolist(),
        'nationalRedrawn':False,'crossLayerIndependenceAssumed':True}
