"""National-only interface companion; archived inference is never rewritten."""
import argparse
from .common import OUT,read,save,digest


def build():
    inventory={r['id']:r for r in read(OUT/'inventory.json')['cases']}
    rows=[]
    for record in read(OUT/'construction.json')['cases']:
        entry=inventory[record['id']];branch=entry['branch']
        row={'id':record['id'],'status':record['status'],'reason':record.get('reason'),
             'electionYear':entry['year'],'cutoff':entry['cutoff'],'horizonDays':entry['horizonDays'],
             'publicationPolicy':'verified_only' if branch=='verified_only' else 'verified_plus_'+str(10 if branch=='publication_lag10' else 5)+'_day_inference',
             'availabilityFlags':['retrospective_source_versions','earlier_result_availability_assumed'],
             'sampleSizePolicy':'missing_n1000' if branch=='missing_n1000' else 'missing_n750',
             'fineOtherAllocationAvailable':False}
        if branch!='verified_only':row['availabilityFlags'].append('inferred_publication_admitted')
        if record['status']=='accepted':
            path=record['attempts'][-1];fit=read(OUT/path)
            row.update({'schemaVersion':'stage35-national-categories','categories':fit['categories'],
                        'fitKey':fit['fitKey'],'archivePath':path,'drawNamespace':fit['fitKey'],
                        'drawIdsField':'draws.drawIds','drawCount':len(fit['draws']['drawIds']),
                        'currentDrawsField':'draws.current','electionDayDrawsField':'draws.electionDay',
                        'expectedCurrent':fit['draws']['expectedCurrent'],
                        'expectedElectionDay':fit['draws']['expectedElectionDay'],
                        'configurationDigest':fit['signature']['configurationDigest'],
                        'codeAndDependenciesField':'signature',
                        'sharedDrawRule':'one paired draw ID across all later electorates; no second common-error draw'})
        rows.append(row)
    return {'stage':36,'forecastContractDigest':digest(read(OUT/'forecast-contract.json')),
            'metadataCompanion':'authoritative branch-specific availability; original fit archives unchanged',
            'cases':rows}


def run(check=False):
    value=build();save('output-manifest.json',value,check)
    print('National interface manifest:',len(value['cases']),'cases; no scores or inference')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
