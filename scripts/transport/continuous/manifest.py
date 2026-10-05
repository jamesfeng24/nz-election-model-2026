"""Seal consumed helper code, specifications and saved Stage42 outputs."""
import argparse
from .common import ROOT,PREFIX,read,save,digest,verify


def build():
    paths=[str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts/transport/continuous').glob('*.py'))]
    # Explicit reused numerical/evidence adapters, not a whole registry/framework dependency.
    paths+=['scripts/transport/geography.py','scripts/transport/common.py',
        'scripts/checkpoints/stage25_geography.py','scripts/checkpoints/stage25_availability.py',
        'scripts/checkpoints/complete_share_features.py','scripts/checkpoints/joint_candidate_share/kernel.py',
        'scripts/readiness/features.py','scripts/evidence/practical_candidate_linkage/names.py',
        'scripts/evidence/practical_candidate_linkage/components.py',
        'docs/stage42-continuous-transport-specification.md','docs/stage42-implementation-plan.md',
        'docs/stage42-within-seat-evidence-audit.md','docs/stage42-continuous-transport-findings.md']
    outputs=[str(p.relative_to(ROOT)) for p in sorted((ROOT/PREFIX).glob('*.json')) if p.name!='implementation-manifest.json']
    return {'stage':42,'codeAndSpecificationHashes':{p:digest(p) for p in sorted(paths)},
        'outputHashes':{p:digest(p) for p in outputs},'reproduction':'freeze, construction, evaluation, readiness, verification, report, manifest --check',
        'inferencePerformed':False,'newSources':0,'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();verify();save('implementation-manifest.json',build(),a.check)
    print('Stage42 implementation and outputs sealed')


if __name__=='__main__':main()
