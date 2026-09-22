"""Three pre-specified, parameter-free national-to-local transformations."""
import math

METHODS=('additive','proportional','log_odds')


def transform(method,p,p0,p1):
    if method not in METHODS or not all(math.isfinite(x) for x in (p,p0,p1)):
        raise ValueError('Invalid transformation input')
    if not 0<=p<=1 or not 0<p0<1 or not 0<p1<1:
        raise ValueError('Ineligible share domain; no smoothing')
    if method=='additive':raw=p+p1-p0
    elif method=='proportional':raw=p*(p1/p0)
    else:
        odds=p1*(1-p0)/(p0*(1-p1))
        raw=p*odds/(1-p+p*odds)
    return {'raw':raw,'prediction':min(1.,max(0.,raw)),'clipped':raw<0 or raw>1}


def prediction_bounds(method,lower,upper,p0,p1,actual):
    if not 0<=lower<=upper<=1 or not 0<=actual<=1:raise ValueError('Invalid source/target share')
    lo,hi=(transform(method,p,p0,p1) for p in (lower,upper))
    a,b=lo['prediction'],hi['prediction']
    minimum=max(a-actual,actual-b,0.)
    maximum=max(abs(a-actual),abs(b-actual))
    return {'lower':a,'upper':b,'rawLower':lo['raw'],'rawUpper':hi['raw'],
            'clippingPossible':lo['clipped'] or hi['clipped'],
            'clippingCertain':lo['raw']<0 and hi['raw']<0 or lo['raw']>1 and hi['raw']>1,
            'absoluteErrorLower':minimum,'absoluteErrorUpper':maximum,
            'squaredErrorLower':minimum**2,'squaredErrorUpper':maximum**2,
            'signedErrorLower':a-actual,'signedErrorUpper':b-actual}
