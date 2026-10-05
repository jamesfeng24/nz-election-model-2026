"""Frozen mean family with explicit reuse of mathematically identical arrays."""
import numpy as np
from scipy.special import expit
from scripts.uncertainty_revision.coordinates import inverse,partition,binary_draw
from scripts.uncertainty.simulation import candidate_inputs
from scripts.polling.candidate_integration.propagation import local_vectors,candidate_vectors
from .streams import noise
from scripts.uncertainty_revision.estimation import labels
from .integration import conditional_inverse,conditional_check,student_location


def invert(base,row,scales,count,method):
    student=method=='student' and row['layer']=='candidate'
    eta,total=noise(row,scales,count,student)
    if method=='stage45':q,location=inverse(base,row['groups'],eta,total)
    else:q,location=conditional_inverse(base,row['groups'],eta,total,student,tags=labels(row))
    return q,location,total


def component(row,scales,count,method):
    q,location,total=invert(row['mean'],row,scales,count,method)
    check=conditional_check(row['mean'],row['groups'],total,method=='student' and row['layer']=='candidate',tags=labels(row)) if method!='stage45' else None
    return q,{'deterministicMean':row['mean'],'simulatedMean':q.mean(axis=0).tolist(),
              'meanShiftPP':(100*(q.mean(axis=0)-row['mean'])).tolist(),'location':location,'conditionalCheck':check}


def compose_inputs(party,candidate,national,party_scales,method):
    deterministic=local_vectors(national,party['affinities'])
    local,location,total=invert(deterministic,party,party_scales,len(national),method)
    destinations,exponent,floor=candidate_inputs(candidate,party)
    conditional=candidate_vectors(local,destinations,exponent,floor)
    control=candidate_vectors(deterministic,destinations,exponent,floor)
    return deterministic,conditional,control,location,total


def compose_metadata(party,candidate,prepared,q,location,total,method):
    deterministic,conditional,control,plocation,ptotal=prepared;count=len(q)
    indices=[0,count//2,count-1]
    check={'local':conditional_check(deterministic[indices],party['groups'],ptotal,tags=labels(party)),
           'candidate':conditional_check(conditional[indices],candidate['groups'],total,method=='student',tags=labels(candidate))} if method!='stage45' else None
    return {'deterministicNationalOnlyMean':control.mean(axis=0).tolist(),
            'candidateConditionalMeanAfterLocalUncertainty':conditional.mean(axis=0).tolist(),
            'simulatedMean':q.mean(axis=0).tolist(),'meanShiftPP':(100*(q.mean(axis=0)-control.mean(axis=0))).tolist(),
            'nonlinearShiftPP':(100*(conditional.mean(axis=0)-control.mean(axis=0))).tolist(),
            'localLocation':plocation,'candidateLocation':location,'conditionalCheck':check,
            'nationalRedrawn':False,'crossLayerIndependenceAssumed':True}


def compose(party,candidate,national,party_scales,candidate_scales,method):
    prepared=compose_inputs(party,candidate,national,party_scales,method)
    q,location,total=invert(prepared[1],candidate,candidate_scales,len(national),method)
    return q,compose_metadata(party,candidate,prepared,q,location,total,method)


def student_from_gaussian(base,row,scales,gaussian):
    """Only balance changes; identical mass and remainder are reused."""
    count=len(base);eta,total=noise(row,scales,count,True);q=gaussian.copy();n,l,other=partition(row['groups'])
    if n and l:
        original=base[:,n+l].sum(axis=1)
        ratio=np.divide(base[:,n[0]],original,out=np.zeros(count),where=original>0)
        location=student_location(ratio,total['balanceShared'],total['balanceSeat'])
        varied=expit(location+eta['balance']);ratio=np.where(ratio==0,0,np.where(ratio==1,1,varied))
        mass=binary_draw(original,eta['mass'],total['mass']) if other else np.ones(count)
        q[:,n[0]],q[:,l[0]]=mass*ratio,mass*(1-ratio)
    location={'scope':'conditional outcome-free quadrature for every supplied vector','nodes':64,
              'zeroLock':bool(np.all(q[:,np.all(base==0,axis=0)]==0))}
    return q,location,total


def compose_pair(party,candidate,national,gaussian_party,gaussian_candidate,student_party,student_candidate):
    if gaussian_party!=student_party:raise ValueError('Different local input scales cannot be reused')
    for name in ('mass','within'):
        if gaussian_candidate[name]!=student_candidate[name]:raise ValueError('Different candidate directions cannot be reused')
    if gaussian_candidate['balance']['shared']!=student_candidate['balance']['shared']:raise ValueError('Different shared balance cannot be reused')
    prepared=compose_inputs(party,candidate,national,gaussian_party,'robust_gaussian')
    gaussian,location,total=invert(prepared[1],candidate,gaussian_candidate,len(national),'robust_gaussian')
    student,slocation,stotal=student_from_gaussian(prepared[1],candidate,student_candidate,gaussian)
    return {'robust_gaussian':(gaussian,compose_metadata(party,candidate,prepared,gaussian,location,total,'robust_gaussian')),
            'student':(student,compose_metadata(party,candidate,prepared,student,slocation,stotal,'student'))}
