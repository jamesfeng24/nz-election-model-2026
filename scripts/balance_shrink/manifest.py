"""Consumed inputs, derived artifacts and code hashes for the Stage60 comparison."""
from .common import ROOT, PREFIX, DESIGN, DESIGN_DOC, arguments, digest, read, save, verify


def build():
    artifacts = sorted(str(p.relative_to(ROOT)) for p in (ROOT / PREFIX).glob('*.json') if p.name != 'manifest.json')
    code = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/balance_shrink').glob('*.py'))
    tests = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/tests').glob('test_stage60*.py'))
    return {'stage': 60, 'derivedArtifacts': {p: digest(p) for p in artifacts},
            'frozenDesign': {p: digest(p) for p in (DESIGN_DOC, DESIGN)},
            'newCodeAndTests': {p: digest(p) for p in code + tests},
            'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
            'dataSourcesJsonTouched': False, 'newSourcesOrAcquisition': False, 'newNationalInference': False, 'newComposedBank': False,
            'operationalAdoption': None, 'hashesAreNotProofOfLinuxReproduction': True}


def main():
    args = arguments()
    verify()
    save('manifest.json', build(), args.check)


if __name__ == '__main__':
    main()
