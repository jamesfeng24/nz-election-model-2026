"""Seal consumed helper code and derived companions without rerunning inference."""
import argparse
from .common import ROOT, PREFIX, digest, save, verify_inputs, preserve

OUTPUTS = ('input-contract','specification','sample-manifest','historical-inventory','geography',
           'construction','evaluation','party-construction','readiness-2026','relationship-inventory','independent-verification')
HELPERS = ('scripts/boundaries/contract.py','scripts/boundaries/coupled.py',
           'scripts/checkpoints/stage25_geography.py','scripts/checkpoints/stage25_availability.py',
           'scripts/checkpoints/complete_share_features.py','scripts/checkpoints/stage22_fit.py',
           'scripts/checkpoints/joint_candidate_share/kernel.py',
           'scripts/models/joint_candidate_share/adapters.py','scripts/models/joint_candidate_share/numerics.py',
           'scripts/evidence/practical_candidate_linkage/names.py','scripts/evidence/practical_candidate_linkage/components.py',
           'scripts/readiness/features.py','requirements-boundaries.txt','pyproject.toml')


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify_inputs()
    code=[str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts/transport').glob('*.py'))]+list(HELPERS)
    output={PREFIX+'/'+n+'.json':digest(PREFIX+'/'+n+'.json') for n in OUTPUTS}
    output['docs/stage41-transport-findings.md']=digest('docs/stage41-transport-findings.md')
    save('implementation-manifest.json',{'stage':41,'codeHashes':{p:digest(p) for p in code},
        'outputHashes':output,'priorDataFilesUnchanged':preserve(),
        'inferencePerformed':False,'frozenPolicyCommit':'5bcdd4f','predictionBeforeScoreCommit':'8ec3c23',
        'regeneration':'python -m scripts.transport.{freeze,party,construction,evaluation,readiness,verification,report,manifest} --check'},a.check)


if __name__=='__main__':main()
