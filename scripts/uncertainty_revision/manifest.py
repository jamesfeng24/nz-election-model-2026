"""Consumed-input and output integrity, separate from numerical reproduction."""
from .common import ROOT, PREFIX, read, save, verify, arguments, digest


def build():
    files = ('specification.json', 'input-contract.json', 'diagnosis.json', 'prior-implications.json',
             'scales.json', 'convergence.json', 'construction.json', 'evaluation.json',
             'mean-audit.json', 'independent-verification.json')
    return {'stage': 45, 'outputHashes': {PREFIX + '/' + f: digest(PREFIX + '/' + f) for f in files},
            'priorFilesPreserved': len(read(PREFIX + '/preservation.json')['priorDataHashes']),
            'noMeanRefit': True, 'noMCMC': True, 'noAcquisition': True,
            'operationalSelection': None, 'reproductionCommand': 'scripts.uncertainty_revision modules --check',
            'integrityIsNotIndependentNumericalReproduction': True}


def main():
    args = arguments(); verify(); save('manifest.json', build(), args.check)
    print('Stage45 consumed inputs and1774 earlier datafiles preserved')


if __name__ == '__main__':
    main()
