"""Consumed inputs, derived artifacts and code hashes for the Stage63 layer-replication study."""
from .common import ROOT, PREFIX, arguments, digest, read, save, verify


def build():
    artifacts = sorted(str(p.relative_to(ROOT)) for p in (ROOT / PREFIX).glob('*.json') if p.name != 'manifest.json')
    code = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/layer_replication').glob('*.py'))
    tests = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts/tests').glob('test_stage63*.py'))
    return {'stage': 63, 'derivedArtifacts': {p: digest(p) for p in artifacts},
            'frozenDesign': {p: digest(p) for p in ('docs/stage63-layer-replication-design.md', PREFIX + '/design-contract.json')},
            'newCodeAndTests': {p: digest(p) for p in code + tests},
            'consumedInputs': read(PREFIX + '/input-contract.json')['inputHashes'],
            'dataSourcesJsonTouched': False, 'newSourcesOrAcquisition': False, 'newNationalInference': False,
            'timingIsHardwareDependent': True, 'hashesAreNotProofOfLinuxReproduction': True}


def main():
    args = arguments()
    verify()
    save('manifest.json', build(), args.check)


if __name__ == '__main__':
    main()
