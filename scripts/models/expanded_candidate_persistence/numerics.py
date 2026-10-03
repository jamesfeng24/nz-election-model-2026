"""Unrestricted equal-record OLS; numerical requirements, not replication gates."""
from math import isfinite, sqrt
from fractions import Fraction
import numpy as np
from scripts.models.asymmetric_response_test.numerics import checked_ols
from scripts.checkpoints.complete_share_feature_rank import rank_details


def fit(x, y):
    if len(x)!=len(y):raise ValueError('Unequal solver input lengths')
    if len(x)<2:return {'status':'abstain','reason':'fewer_than_two_training_rows'}
    if not all(isfinite(v) for v in x+y):return {'status':'abstain','reason':'nonfinite_training_input'}
    mean=float(sum(map(Fraction,x))/len(x))
    centered=[v-mean for v in x]
    scale=sqrt(sum(v*v for v in centered)/len(x))
    if scale==0:return {'status':'abstain','reason':'zero_predictor_variation'}
    design=[[1.0,v/scale] for v in centered]
    try:rank=rank_details(np.asarray(design),[0,1])
    except np.linalg.LinAlgError:return {'status':'abstain','reason':'numerical_rank_failure'}
    if rank['rank']!=2 or rank['weakCondition']:
        return {'status':'abstain','reason':'rank_or_condition_failure','design':rank}
    result=checked_ols(design,y)
    if result['status']!='available':return result
    a,b=result['coefficients'];beta=b/scale;alpha=a-beta*mean
    independent=np.linalg.lstsq(np.asarray([[1,v] for v in x]),np.asarray(y),rcond=None)[0]
    difference=max(abs(float(independent[0])-alpha),abs(float(independent[1])-beta),
                   max(abs(float(independent[0]+independent[1]*v)-(alpha+beta*v)) for v in x))
    if not isfinite(difference) or difference>1e-8:
        return {'status':'abstain','reason':'independent_original_parameter_disagreement'}
    return {'status':'available','alpha':alpha,'beta':beta,'design':rank,
            'numericalPredictorMean':mean,'numericalPredictorRms':scale,
            'independentAgreementWithin1eMinus8':True}


def mean_fit(y):
    if not y:return {'status':'abstain','reason':'no_permitted_training_responses'}
    if not all(isfinite(v) for v in y):return {'status':'abstain','reason':'nonfinite_training_input'}
    return {'status':'available','mean':float(sum(map(Fraction,y))/len(y))}
