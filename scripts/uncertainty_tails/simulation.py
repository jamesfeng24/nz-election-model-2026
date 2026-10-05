"""Frozen mean family, only specified distribution/location corrections."""
import numpy as np
from scripts.uncertainty_revision.coordinates import inverse
from scripts.uncertainty.simulation import candidate_inputs
from scripts.polling.candidate_integration.propagation import local_vectors,candidate_vectors
from .streams import noise
from .integration import conditional_inverse,conditional_check


def invert(base,row,scales,count,method):
    student=method=='student' and row['layer']=='candidate'
    eta,total=noise(row,scales,count,student)
    if method=='stage45':q,location=inverse(base,row['groups'],eta,total)
    else:q,location=conditional_inverse(base,row['groups'],eta,total,student)
    return q,location,total


def component(row,scales,count,method):
    q,location,total=invert(row['mean'],row,scales,count,method)
    check=conditional_check(row['mean'],row['groups'],total,method=='student' and row['layer']=='candidate') if method!='stage45' else None
    return q,{'deterministicMean':row['mean'],'simulatedMean':q.mean(axis=0).tolist(),
              'meanShiftPP':(100*(q.mean(axis=0)-row['mean'])).tolist(),'location':location,'conditionalCheck':check}


def compose(party,candidate,national,party_scales,candidate_scales,method):
    count=len(national);deterministic=local_vectors(national,party['affinities'])
    local,location,ptotal=invert(deterministic,party,party_scales,count,method)
    destinations,exponent,floor=candidate_inputs(candidate,party)
    conditional=candidate_vectors(local,destinations,exponent,floor)
    q,clocation,ctotal=invert(conditional,candidate,candidate_scales,count,method)
    control=candidate_vectors(deterministic,destinations,exponent,floor)
    indices=[0,count//2,count-1]
    check={'local':conditional_check(deterministic[indices],party['groups'],ptotal),
           'candidate':conditional_check(conditional[indices],candidate['groups'],ctotal,method=='student')} if method!='stage45' else None
    return q,{'deterministicNationalOnlyMean':control.mean(axis=0).tolist(),
              'candidateConditionalMeanAfterLocalUncertainty':conditional.mean(axis=0).tolist(),
              'simulatedMean':q.mean(axis=0).tolist(),'meanShiftPP':(100*(q.mean(axis=0)-control.mean(axis=0))).tolist(),
              'nonlinearShiftPP':(100*(conditional.mean(axis=0)-control.mean(axis=0))).tolist(),
              'localLocation':location,'candidateLocation':clocation,'conditionalCheck':check,
              'nationalRedrawn':False,'crossLayerIndependenceAssumed':True}
