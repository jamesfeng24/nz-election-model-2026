"""Separate consumed-source, numerical output and prior-preservation manifests."""
from .common import PREFIX,ROOT,digest,read,save,verify,arguments


def build():
    outputs=['inventory.json','scales.json','construction.json','evaluation.json','precision.json','independent-verification.json','specification.json','input-contract.json']
    paths=[PREFIX+'/'+p for p in outputs]+['docs/stage44-uncertainty-specification.md','docs/stage44-implementation-notes.md','docs/stage44-uncertainty-findings.md']
    paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts/uncertainty').glob('*.py'))]
    return {'stage':44,'consumedInputHashes':read(PREFIX+'/input-contract.json')['inputHashes'],
        'outputAndCodeHashes':{p:digest(p) for p in paths},'priorDataFilesVerified':verify(),
        'simulation':{'draws':512,'seed':20261005,'cache':'exact-signature case manifests with local archive digests; reconstruct without MCMC'},
        'historicalMeanFitsChanged':False,'sourceAcquisition':0,'liveForecastProduced':False,
        'operationalSelection':None,'māoriGeneralCoefficientExtension':False}


def main():
    args=arguments();value=build();save('manifest.json',value,args.check);print('Stage44 prior files preserved',value['priorDataFilesVerified'])


if __name__=='__main__':main()
