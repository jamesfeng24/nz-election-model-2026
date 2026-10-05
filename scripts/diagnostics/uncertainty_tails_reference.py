"""Independent low-dimensional conditional covariance/expectation reference."""
import argparse
import numpy as np
from scipy.special import roots_hermitenorm,softmax
from scripts.uncertainty_tails.common import save,verify
from scripts.uncertainty_tails.integration import conditional_offsets,within_factor


def expectation(probability,offset,labels,shared,seat,order):
    # Construct the covariance separately from the implementation factor.
    k=len(labels);raw=np.array([[shared**2*(a==b)+seat**2*(i==j) for j,b in enumerate(labels)] for i,a in enumerate(labels)])
    difference=np.column_stack((np.eye(k-1),-np.ones(k-1)))
    covariance=np.einsum('ij,jk,lk->il',difference,raw,difference,optimize=False)
    chol=np.linalg.cholesky(covariance)
    x,w=roots_hermitenorm(order);w=w/np.sqrt(2*np.pi)
    nodes=np.stack(np.meshgrid(*([x]*(k-1)),indexing='ij'),axis=-1).reshape(-1,k-1)
    weights=np.prod(np.stack(np.meshgrid(*([w]*(k-1)),indexing='ij'),axis=-1),axis=-1).ravel()
    contrasts=np.einsum('ij,kj->ik',nodes,chol,optimize=False)
    noise=np.column_stack((contrasts,np.zeros(len(contrasts))))
    q=softmax(np.log(probability)+offset+noise,axis=-1)
    return np.sum(q*weights[:,None],axis=0)


def build():
    records=[]
    for labels in (['a','b','c'],['a','a','c'],['a','a','a']):
        for p in ([.5,.3,.2],[.97,.02,.01]):
            shared,seat=.30,.25;sd=float(np.hypot(shared,seat))
            offset=conditional_offsets(p,sd,tags=labels,shared=shared,seat=seat)
            a=expectation(p,offset,labels,shared,seat,41);b=expectation(p,offset,labels,shared,seat,81)
            records.append({'synthetic':True,'labels':labels,'probability':p,'sharedSD':shared,'seatSD':seat,
                            'expectationGH81':b.tolist(),'maximumReferenceChangePP':float(100*np.max(np.abs(a-b))),
                            'maximumConditionalGapPP':float(100*np.max(np.abs(b-p))),
                            'offset':offset.tolist()})
    return {'stage':46,'purpose':'independent contrast-covariance Gauss-Hermite reference, synthetic only',
            'orders':[41,81],'records':records,'maximumReferenceChangePP':max(r['maximumReferenceChangePP'] for r in records),
            'maximumConditionalGapPP':max(r['maximumConditionalGapPP'] for r in records),
            'conditionalGatePP':.05,'noToleranceRelaxation':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args();verify();save('conditional-reference.json',build(),args.check)


if __name__=='__main__':main()
