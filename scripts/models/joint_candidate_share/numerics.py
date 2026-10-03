"""Explicit S/R columns using the unchanged Stage22 generic profile family."""
from itertools import product
from decimal import Decimal,localcontext
from math import isfinite
import numpy as np
from scipy.optimize import minimize
from scripts.checkpoints.stage22_fit import Profile as GenericProfile,fit,choose_tied,THETA_BOUNDS
from scripts.checkpoints.complete_share_feature_rank import rank_details,PROBES
from .common import METHODS
from .adapters import arrays


def projected(gradient,theta):
    g=np.array(gradient,copy=True)
    for i,x in enumerate(theta):
        if x<=-4+1e-8 and g[i]>0:g[i]=0
        if x>=4-1e-8 and g[i]<0:g[i]=0
    return float(np.max(np.abs(g),initial=0))


class Profile(GenericProfile):
    """The generic loss consumes selected S/R columns directly, with no V relabel."""
    def __init__(self,payload):
        self.base=np.array(payload['base']);self.features=np.array(payload['features']).reshape(len(self.base),len(METHODS[payload['method']]))
        self.starts=np.array(payload['starts'],dtype=int);self.actual=np.array(payload['actual']);self.contests=len(self.starts)
        if not self.contests or len(self.actual)!=len(self.base) or abs(sum(self.actual)-self.contests)>1e-8:raise ValueError('Invalid complete training population')
        self.cache={};self.optimizerCalls=0;self.maxProjected=0.;self.maxStartSpread=0.;self.precisionRetries=0.
        self.preciseBase=self.base.astype(np.longdouble);self.preciseFeatures=self.features.astype(np.longdouble)
        self.preciseActual=self.actual.astype(np.longdouble)

    def stable_objective(self,kappa,theta,relative=False):
        """Same cross entropy; extended precision and a theta-constant shift for line search."""
        if not .0001<=kappa<=.1:raise ValueError('Floor outside frozen bounds')
        base=self.preciseBase+np.longdouble(kappa)
        movement=np.einsum('ij,j->i',self.preciseFeatures,np.asarray(theta,dtype=np.longdouble),optimize=False)
        z=np.log(base)+movement
        lengths=np.diff(np.r_[self.starts,len(base)]);highest=np.maximum.reduceat(z,self.starts)
        shifted=np.exp(z-np.repeat(highest,lengths));totals=np.add.reduceat(shifted,self.starts)
        q=shifted/np.repeat(totals,lengths)
        if relative:
            highest=np.maximum.reduceat(movement,self.starts)
            relative_sum=np.add.reduceat(base*np.exp(movement-np.repeat(highest,lengths)),self.starts)
            loss=highest+np.log(relative_sum/np.add.reduceat(base,self.starts))-np.add.reduceat(self.preciseActual*movement,self.starts)
        else:
            logq=z-np.repeat(highest+np.log(totals),lengths)
            loss=-np.add.reduceat(self.preciseActual*logq,self.starts)
        gradient=np.einsum('ij,i->j',self.preciseFeatures,q-self.preciseActual,optimize=False)/self.contests
        value=float(np.mean(loss));gradient=np.asarray(gradient,dtype=float)
        if not isfinite(value) or not np.all(np.isfinite(gradient)):raise ValueError('Nonfinite objective')
        return value,gradient

    def decimal_objective(self,kappa,theta):
        """Same fixed-kappa shifted loss and gradient at Decimal50 precision."""
        with localcontext() as context:
            context.prec=50
            dk=Decimal(str(kappa));dt=[Decimal(str(v)) for v in theta]
            loss=Decimal(0);gradient=[Decimal(0)]*len(dt)
            for lo,hi in zip(self.starts,np.r_[self.starts[1:],len(self.base)]):
                b=[Decimal(str(v))+dk for v in self.base[lo:hi]]
                x=[[Decimal(str(v)) for v in row] for row in self.features[lo:hi]]
                y=[Decimal(str(v)) for v in self.actual[lo:hi]]
                movements=[sum((v*t for v,t in zip(row,dt)),Decimal(0)) for row in x]
                w=[v*t.exp() for v,t in zip(b,movements)];total=sum(w);ysum=sum(y)
                loss+=ysum*(total/sum(b)).ln()-sum((v*t for v,t in zip(y,movements)),Decimal(0))
                for row,q,a in zip(x,w,y):
                    for j,v in enumerate(row):gradient[j]+=v*(q/total*ysum-a)
            return float(loss/self.contests),np.array([float(g/self.contests) for g in gradient])

    def value_gradient(self,kappa,theta):
        return self.stable_objective(kappa,theta)

    def theta_optimum(self,kappa):
        key=float(kappa)
        if key in self.cache:return self.cache[key]
        if not self.features.shape[1]:
            result=(self.value_gradient(key,np.empty(0))[0],np.empty(0),0.)
        else:
            options=[]
            for start in product((-2.,0.,2.),repeat=self.features.shape[1]):
                solution=minimize(lambda theta:self.stable_objective(key,theta,relative=True),np.array(start),method='L-BFGS-B',jac=True,
                    bounds=[THETA_BOUNDS]*len(start),options={'ftol':1e-15,'gtol':1e-11,'maxiter':2000,'maxls':50})
                self.optimizerCalls+=1
                if not solution.success:
                    self.precisionRetries+=1
                    solution=minimize(lambda theta:self.decimal_objective(key,theta),np.array(start),method='L-BFGS-B',jac=True,
                        bounds=[THETA_BOUNDS]*len(start),options={'ftol':1e-15,'gtol':1e-11,'maxiter':2000,'maxls':50})
                    self.optimizerCalls+=1
                if not solution.success or not isfinite(solution.fun):raise ValueError('Theta optimizer unsuccessful: '+str(solution.message))
                loss,g=self.value_gradient(key,solution.x);norm=projected(g,solution.x)
                if norm>1e-7:raise ValueError('Theta projected gradient failed')
                self.maxProjected=max(self.maxProjected,norm);options.append((loss,solution.x,norm))
            spread=max(x[0] for x in options)-min(x[0] for x in options)
            self.maxStartSpread=max(self.maxStartSpread,spread)
            if spread>1e-8:raise ValueError('Theta fixed-start objectives disagree')
            result=choose_tied(options,lambda x:tuple(x))
        self.cache[key]=result;return result


def rank_at(profile,kappa):
    rows=[]
    values=np.column_stack([1/(profile.base+kappa),profile.features])
    for start,stop in zip(profile.starts,np.r_[profile.starts[1:],len(values)]):
        block=values[start:stop];rows.extend((block-block.mean(axis=0))/np.sqrt(len(block)))
    return rank_details(np.asarray(rows),list(range(values.shape[1])))


def checked_saved(job,saved):
    if saved['signature']!=job['signature']:raise ValueError('Wrong training cache signature')
    fit_record=saved['fit']
    if fit_record['status']!='fitted':return saved
    profile=Profile(job['payload']);loss,g=profile.value_gradient(fit_record['kappa'],np.array(fit_record['theta']))
    if abs(loss-fit_record['objective'])>1e-12 or projected(g,fit_record['theta'])>1e-7:raise ValueError('Saved objective/gradient inconsistent')
    if rank_at(profile,fit_record['kappa'])!=fit_record['fittedPointRank']:raise ValueError('Saved rank inconsistent')
    if abs(fit_record['objective']-fit_record['independentObjective'])>1e-8:raise ValueError('Saved independent check inconsistent')
    return saved


def calculate(job):
    profile=Profile(job['payload'])
    try:
        for k in PROBES:
            if rank_at(profile,k)['rank']!=profile.features.shape[1]+1:raise ValueError('Unidentified training design')
        result=fit(profile);rank=rank_at(profile,result['kappa'])
        if rank['rank']!=profile.features.shape[1]+1:raise ValueError('Unidentified fitted-point design')
        result.update(coefficients=dict(zip(METHODS[job['payload']['method']],result['theta'])),fittedPointRank=rank,
                      thetaOptimizerCalls=profile.optimizerCalls,profilePoints=len(profile.cache),
                      maximumProjectedGradient=profile.maxProjected,maximumFixedStartObjectiveSpread=profile.maxStartSpread,
                      optimizerSuccess=True,independentAgreement=True,precisionRetries=profile.precisionRetries)
    except ValueError as error:
        result={'status':'abstain','reason':'numerical_or_rank_failure','detail':str(error),
                'thetaOptimizerCalls':profile.optimizerCalls,'profilePoints':len(profile.cache)}
    return {'signature':job['signature'],'method':job['payload']['method'],
            'trainingIds':job['payload']['trainingIds'],'fit':result}


def predict(rows,fold,method,parameters):
    if parameters['status']!='fitted':return []
    base,x,starts=arrays(rows,fold,method);theta=parameters['theta'];result=[]
    with localcontext() as context:
        context.prec=50
        for row,start,stop in zip(rows,starts,np.r_[starts[1:],len(base)]):
            weights=[]
            for i in range(start,stop):
                exponent=sum((Decimal(str(t))*Decimal(str(v)) for t,v in zip(theta,x[i])),Decimal(0))
                weights.append((Decimal(str(base[i]))+Decimal(str(parameters['kappa'])))*exponent.exp())
            total=sum(weights);q=[float(w/total) for w in weights]
            if any(not isfinite(v) or v<0 for v in q) or abs(sum(q)-1)>1e-12:raise ValueError('Candidate simplex failure')
            result.append({'targetElectorateId':row['targetElectorateId'],'candidateShares':{
                c['targetOccurrenceId']:v for c,v in zip(row['candidates'],q)},
                'candidateFeatureStates':{c['targetOccurrenceId']:{'S':c['s0Reported'] is not None,
                    'R':c['R'][fold['view']]['valueFraction'] is not None,'RSourceOccurrenceId':c['R'][fold['view']]['sourceOccurrenceId'],
                    'pattern':c['R'][fold['view']]['availabilityPattern']} for c in row['candidates']}})
    return result
