"""Gaussian-law numerical companion; covariance conditioning is explicit."""
import numpy as np
from scipy.special import softmax
from scripts.uncertainty_revision.coordinates import partition, binary_draw
from scripts.uncertainty_revision.estimation import labels
from scripts.uncertainty_tails.streams import noise
from scripts.polling.candidate_integration.propagation import local_vectors, candidate_vectors
from scripts.uncertainty.simulation import candidate_inputs
from scripts.uncertainty.transforms import validate
from .integration import solve_locations


def diagnostics(checks):
    return {'checkedInputs':len(checks),'passed':all(c['passed'] for c in checks),
            'failedInputs':[c['index'] for c in checks if not c['passed']],
            'maximumConditionalGapPP':max((c['conditionalGapPP'] for c in checks),default=0.),
            'maximumReferenceChangePP':max((c['referenceChangePP'] for c in checks),default=0.),
            'maximumReferenceDisagreementPP':max((c['referenceDisagreementPP'] for c in checks),default=0.),
            'maximumSolverGapPP':max((c['solverGapPP'] for c in checks),default=0.),
            'nodeCounts':{str(k):sum(c['size']==k for c in checks) for k in sorted({c['size'] for c in checks})},
            'referenceIsFiniteApproximation':True}


def invert(base, row, scales, count):
    b=validate(base)
    constant=b.ndim==1
    if constant:b=np.broadcast_to(b,(count,len(b)))
    if len(b)!=count:raise ValueError('Conditional vector count mismatch')
    eta,total=noise(row,scales,count)
    n,l,other=partition(row['groups']);major=n+l
    result=np.zeros_like(b)
    mass=b[:,major].sum(axis=1) if major else np.zeros(count)
    if major and other:mass=binary_draw(mass,eta['mass'],total['mass'])
    elif major:mass=np.ones(count)
    if n and l:
        original=b[:,major].sum(axis=1)
        ratio=np.divide(b[:,n[0]],original,out=np.zeros(count),where=original>0)
        ratio=binary_draw(ratio,eta['balance'],total['balance'])
        result[:,n[0]],result[:,l[0]]=mass*ratio,mass*(1-ratio)
    elif major:result[:,major[0]]=mass
    checks=[]
    if other:
        raw=b[:,other];amount=raw.sum(axis=1)
        within=np.divide(raw,amount[:,None],out=np.zeros_like(raw),where=amount[:,None]>0)
        within[amount==0,0]=1
        tags=[labels(row)[i] for i in other]
        # Exact row reuse only; a varying conditional mean never shares one offset.
        unique,lookup=np.unique(within,axis=0,return_inverse=True)
        offsets,checks=solve_locations(unique,tags,scales['within']['shared'],scales['within']['seat'])
        logs=np.full(within.shape,-np.inf);np.log(within,out=logs,where=within>0)
        result[:,other]=(1-mass)[:,None]*softmax(logs+offsets[lookup]+eta['within'],axis=-1)
    validate(result)
    return result,{'conditionalIntegration':diagnostics(checks),'distinctConditionalRemainderInputs':len(checks),
                   'zeroFacePreserved':bool(np.all(result[b==0]==0)),
                   'statisticalLaw':'Stage45 Gaussian; numerical conditional-location repair only'}


def component(row, scales, count):
    q,meta=invert(row['mean'],row,scales,count)
    return q,{**meta,'deterministicMean':row['mean'],'simulatedMean':q.mean(axis=0).tolist(),
              'meanShiftPP':(100*(q.mean(axis=0)-row['mean'])).tolist()}


def upstream(party,candidate,national,party_scales):
    deterministic=local_vectors(national,party['affinities'])
    local,local_meta=invert(deterministic,party,party_scales,len(national))
    destinations,exponent,floor=candidate_inputs(candidate,party)
    conditional=candidate_vectors(local,destinations,exponent,floor)
    control=candidate_vectors(deterministic,destinations,exponent,floor)
    return local,conditional,control,local_meta


def composed(party,candidate,national,party_scales,candidate_scales):
    local,conditional,control,local_meta=upstream(party,candidate,national,party_scales)
    q,candidate_meta=invert(conditional,candidate,candidate_scales,len(national))
    return q,{'local':local_meta,'candidate':candidate_meta,
              'deterministicNationalOnlyMean':control.mean(axis=0).tolist(),
              'conditionalCandidateMeanAfterLocalUncertainty':conditional.mean(axis=0).tolist(),
              'simulatedMean':q.mean(axis=0).tolist(),'meanShiftPP':(100*(q.mean(axis=0)-control.mean(axis=0))).tolist(),
              'genuineNonlinearShiftPP':(100*(conditional.mean(axis=0)-control.mean(axis=0))).tolist(),
              'candidateFiniteBankShiftPP':(100*(q.mean(axis=0)-conditional.mean(axis=0))).tolist(),
              'nationalUncertaintyEnteredOnce':True}
