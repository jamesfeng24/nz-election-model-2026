"""Consumed inputs, derived artifacts and code hashes for the Stage48 comparison."""
from .common import ROOT, PREFIX, arguments, digest, read, save, verify


def build():
    artifacts = sorted(str(p.relative_to(ROOT)) for p in (ROOT / PREFIX).glob('*.json') if p.name != 'manifest.json')
    code = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/balance_scale').glob('*.py'))
    tests = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/tests').glob('test_stage48*.py'))
    return {'stage': 48, 'derivedArtifacts': {p: digest(p) for p in artifacts},
            'frozenDesign': {p: digest(p) for p in ('docs/stage48-balance-scale-design.md', PREFIX + '/design-contract.json')},
            'newCodeAndTests': {p: digest(p) for p in code + tests},
            'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
            'dataSourcesJsonTouched': False, 'newSourcesOrAcquisition': False, 'newNationalInference': False,
            'hashesAreNotProofOfLinuxReproduction': True}


def main():
    args = arguments()
    verify()
    save('manifest.json', build(), args.check)


if __name__ == '__main__':
    main()
