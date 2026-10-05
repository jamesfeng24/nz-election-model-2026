"""Frozen first/last-seat 512 versus1024 numerical precision diagnostic."""
import numpy as np
from .common import PREFIX, read, save, verify, arguments
from .construction import scale_for,national_case
from .simulation import component,compose
from .metrics import crps,interval


def comparison(row,small,large):
    y=np.array(row['actual']);a=small.mean(axis=0);b=large.mean(axis=0)
    return {'id':row['targetElectorateId'],'maximumExpectedShareDifferencePP':float(np.max(np.abs(a-b))*100),
        'meanCRPSDifferencePP':float(np.mean(crps(100*large,100*y)-crps(100*small,100*y))),
        'maximum90WidthDifferencePP':float(np.max(np.abs(np.array(interval(100*large,100*y,.9)['widths'])-
            np.array(interval(100*small,100*y,.9)['widths'])))),
        'changed90CoverageCoordinates':sum(a!=b for a,b in zip(interval(large,y,.9)['covered'],interval(small,y,.9)['covered']))}


def build():
    inv=read(PREFIX+'/inventory.json');scales=read(PREFIX+'/scales.json');construction=read(PREFIX+'/construction.json')
    parties={r['targetElectorateId']:r for r in inv['partyRecords']};results=[]
    for case in construction['cases']:
        rows=inv['partyRecords'] if case['layer']=='local_party' else inv['candidateRecords']
        eligible=sorted([r for r in rows if r['targetYear']==case['year']],key=lambda r:r['targetElectorateId'])
        small=read(case['drawCache']['path'])['vectors']
        if case['layer']=='composed':
            national,ids,provenance=national_case(case['year'],parties[eligible[0]['targetElectorateId']]['ids'],1024)
        for row in (eligible[0],eligible[-1]):
            if case['layer']=='composed':
                p=parties[row['targetElectorateId']]
                large,m=compose(p,row,national,case['partyScaleFit']['scales'],case['candidateScaleFit']['scales'])
            else:large,m=component(row,case['scaleFit']['scales'],1024)
            results.append({'case':case['id'],**comparison(row,np.array(small[row['targetElectorateId']]),large)})
    return {'stage':44,'draws':[512,1024],'selection':'first/last stable electorate ID in every component/composed case; frozen before scores',
        'records':results,'precisionIsNotCalibration':True,'configurationChangedAfterScores':False}


def main():
    args=arguments();verify();result=build();save('precision.json',result,args.check);print('Frozen precision records',len(result['records']))


if __name__=='__main__':main()
