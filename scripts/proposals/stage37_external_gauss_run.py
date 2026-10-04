"""Future-only narrow national archive run; default is an offline proposal.

Stage37 never calls --execute. Execution requires separately authorized, pinned
upstream checkout and prepared poll/result inputs; this script fetches nothing.
No ensemble, seat simulation, forecast score or publication pipeline is called.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = 'ef76cf6562e1d028b4fff46d063f4b93945299de'


def proposal():
    return {'stage':37, 'executionAuthorizedNow':False, 'variant':'gauss', 'commit':PIN,
            'cases':[{'year':2017,'cutoff':'2017-07-29'}, {'year':2020,'cutoff':'2020-08-22'}, {'year':2023,'cutoff':'2023-08-19'}],
            'settings':{'chains':4,'warmup':2000,'samples':2000,'target_accept':.95,'max_tree_depth':12,'seed':2026},
            'estimatedRuntimeHours':[.5,3], 'priorRuntimeEvidenceSeconds':[110.1,151.2,240.6],
            'requiredBeforeExecution':['separate_authorization','pinned_prepared_poll_snapshot_and_result_inputs','isolated_transitive_dependency_lock','frozen_category_contract_for_2020_MRI','expanded_all_coordinate_diagnostics'],
            'categoryLimitation':'unchanged upstream2020 folds MRI into Other; three-case six/seven-category comparison still requires a separate schema decision',
            'comparisonType':'external_system_reference; matched_input_architecture requires a separately frozen data adapter',
            'licence':'GPL-3.0-or-later upstream; preserve attribution/notices and distribution obligations',
            'convergenceRequirements':'Rhat<=1.01; bulk/tail ESS>=400; zero divergences; all relevant coordinates, no scores from failed fits',
            'cache':'exact dataset/priors/variant/model/settings/dependency signature; one archive per case; no whole suite',
            'politicalAcquisitionNow':False, 'operationalSelection':None}


def execute(root, cache):
    from datetime import date
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!=PIN:
        raise ValueError('Upstream checkout not pinned')
    sys.path.insert(0,str(root/'src'))
    from pollofpolls.config import Config
    from pollofpolls.pipeline import load_prepped
    from pollofpolls.prep.marshal import build_dataset
    from pollofpolls.eval.backtest import fit_fingerprint
    from pollofpolls.model.fit import FitResult, fit
    cfg=Config(root);polls,results=load_prepped(cfg)
    plan=proposal();settings=plan['settings'];variant=cfg.variant('gauss')
    versions=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
    cache.mkdir(parents=True,exist_ok=True)
    for case in plan['cases']:
        ds=build_dataset(polls,results,cfg,case['year'],date.fromisoformat(case['cutoff']),lagged=True)
        fp=fit_fingerprint(cfg,ds,variant,settings)+hashlib.sha256(versions.encode()).hexdigest()
        prefix=cache/f"gauss_{case['year']}_h8"
        stamp=prefix.with_suffix('.stamp')
        if stamp.exists():
            if stamp.read_text()!=fp or not prefix.with_suffix('.npz').exists():
                raise ValueError('Incompatible/incomplete cached fit')
            fitted=FitResult.load(prefix)
        else:
            ds.save(cache/f"dataset_{case['year']}_h8")
            fitted=fit(ds,variant,cfg.priors,settings,cfg.model_cfg.get('election_obs_sd',.01),seed=2034,progress=True)
            fitted.save(prefix);stamp.write_text(fp)
        # Save raw evidence; no posterior quality claim or forecast scoring here.
        (cache/f"manifest_{case['year']}.json").write_text(json.dumps({'case':case,'signature':fp,'dependencies':versions,'parties':ds.parties,'diagnostics':fitted.diagnostics,'distribution':'pi_target','furtherAllCoordinateAuditRequired':True},sort_keys=True,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--root',type=Path);p.add_argument('--cache',type=Path)
    a=p.parse_args()
    if a.execute:
        if a.root is None or a.cache is None:p.error('--root and --cache required')
        execute(a.root.resolve(),a.cache.resolve())
    else:print(json.dumps(proposal(),sort_keys=True,indent=2))
