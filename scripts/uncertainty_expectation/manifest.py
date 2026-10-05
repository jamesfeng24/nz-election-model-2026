"""Consumed dependency closure, derived companions and untouched historical evidence."""
from .common import ROOT, PREFIX, arguments, digest, read, save, verify
from .construction import signature


def build():
    paths = sorted(str(p.relative_to(ROOT)) for p in (ROOT/PREFIX).glob('*.json') if p.name != 'manifest.json')
    code = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'scripts/uncertainty_expectation').glob('*.py'))
    tests = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'scripts/tests').glob('test_*expectation*.py'))
    return {'stage': 47, 'producerSignature': signature(),
        'derivedArtifacts': {p: digest(p) for p in paths}, 'newCodeAndTests': {p: digest(p) for p in code+tests},
        'consumedPriorInputs': read(PREFIX+'/input-contract.json')['inputHashes'],
        'structuralConsumedEvidence': read(PREFIX+'/structure-input-contract.json')['inputHashes'],
        'preservedPriorDataFiles': len(read(PREFIX+'/preservation.json')['priorDataHashes']),
        'wholeRegistryCoupling': False, 'numericalEnvironment': 'requirements-boundaries.txt; runtime included in producer signature',
        'hashesAreNotProofOfLinuxReproduction': True, 'newNationalInferenceOrSources': False}


def main():
    args = arguments()
    verify()
    for p, expected in read(PREFIX+'/structure-input-contract.json')['inputHashes'].items():
        if digest(p) != expected:
            raise ValueError('Changed structural evidence: '+p)
    save('manifest.json', build(), args.check)


if __name__ == '__main__':
    main()
