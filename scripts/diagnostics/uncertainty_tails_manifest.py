"""Consumed outputs/code integrity, separate from explicit full reproduction."""
from scripts.uncertainty_tails.common import PREFIX,ROOT,read,save,verify,arguments,digest


def build():
    files=sorted((ROOT/PREFIX).glob('*.json'))
    paths=[str(p.relative_to(ROOT)) for p in files if p.name!='manifest.json']
    paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts/uncertainty_tails').glob('*.py'))]
    paths += [PREFIX+'/initial-failure.txt','scripts/diagnostics/uncertainty_tails_report.py','scripts/diagnostics/uncertainty_tails_reference.py','scripts/diagnostics/uncertainty_tails_manifest.py',
              'docs/stage46-uncertainty-specification.md','docs/stage46-uncertainty-findings.md','docs/stage46-development-assessment.md','requirements-boundaries.txt']
    return {'stage':46,'hashes':{p:digest(p) for p in paths},'priorPreservation':digest(PREFIX+'/preservation.json'),
            'fullReproduction':'python -m scripts.uncertainty_tails.construction --check',
            'integrityIsNotProofOfLinuxReproduction':True,'expensiveNationalInferenceRequired':False}


def main():
    args=arguments();verify();save('manifest.json',build(),args.check)


if __name__=='__main__':main()
