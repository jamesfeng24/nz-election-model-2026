"""Stage62 inference: the pinned upstream `gauss` model, Stage38 PRIMARY settings, full-coordinate diagnostics.
Runs only inside .venv-external with four CPU devices; never invoked in CI."""
import os
os.environ.setdefault('XLA_FLAGS', '--xla_force_host_platform_device_count=4')
os.environ.setdefault('JAX_ENABLE_X64', 'True')
import argparse
import gc
import importlib.metadata
import platform
import sys
import time
import numpy as np
from .common import (ROOT, OUT, EXT, UPSTREAM, CACHE, PIN, PRIMARY, RETRY, ARMS, DATASET_OF, ENV_CHECK, SEED, read, save, sha, digest,
                     lock_versions)

SAVED_SCALARS = ('house_cycle_sd', 'industry_start_sd', 'industry_end_sd', 'kappa')
QUANTILES = (.05, .25, .5, .75, .95)


def environment():
    pkgs = {d.metadata['Name'].lower().replace('_', '-'): d.version for d in importlib.metadata.distributions()}
    return {'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(), 'cpuChainDevices': 4,
            'precision': 'jax64', 'packages': {k: pkgs.get(k) for k in sorted(lock_versions())}, 'lockSha256': sha(ROOT / 'requirements-external.lock'),
            'note': 'x86-64 Linux, Python 3.12.3; Stage38 ran on macOS 15.6 arm64 with Python 3.12.2 and the same package pins. NUTS draws are not expected to bit-match.'}


def validate_runtime():
    env = environment(); lock = lock_versions()
    bad = {k: (v, env['packages'].get(k)) for k, v in lock.items() if env['packages'].get(k) != v}
    if bad:
        raise ValueError('Installed packages differ from requirements-external.lock: ' + str(bad))
    contract = read(OUT / 'input-contract.json')
    for path, h in contract['numericalCode'].items():
        if sha(ROOT / path) != h:
            raise ValueError('Frozen numerical code changed ' + path)
    return env


def load_dataset(arm):
    sys.path.insert(0, str(UPSTREAM / 'src'))
    from pollofpolls.prep.marshal import Dataset
    return Dataset.load(EXT / 'datasets/2017') if arm == ENV_CHECK else Dataset.load(OUT / 'datasets' / DATASET_OF[arm])


def settings_of(arm, attempt):
    return {**(PRIMARY if attempt == 1 else RETRY), 'seed': ARMS[arm]['seed'] if arm in ARMS else SEED}


def signature(arm, ds, settings, env):
    cfgs = {str(p.relative_to(UPSTREAM)): sha(p) for p in sorted((UPSTREAM / 'config').glob('*.yml'))}
    return {'arm': arm, 'dataset': ds.fingerprint(), 'cutoff': ds.cutoff.isoformat(), 'pin': PIN, 'variant': 'gauss', 'settings': settings,
            'environment': env, 'upstreamConfig': cfgs, 'inputContract': sha(OUT / 'input-contract.json'), 'runnerSha256': sha(__file__)}


def house_offsets(samples, ds):
    """Per-draw 2026-cycle offset (house_base + house_cycle) of every pollster with 2026-cycle polls: (chains, draws, P, K)."""
    C = ds.n_cycles; last = C - 1; names = []; rows = []
    for j, name in enumerate(ds.pollsters):
        mask = (ds.pollster_idx == j) & (ds.cycle_idx == last)
        if not mask.any():
            continue
        houses = set(int(h) for h in ds.house_idx[mask])
        if len(houses) != 1:
            raise ValueError('Pollster with several method segments in the current cycle: ' + name)
        h = houses.pop()
        rows.append(samples['house_base'][:, :, h, :] + samples['house_cycle'][:, :, j * C + last, :]); names.append(name)
    return names, np.stack(rows, axis=2)


def path_summary(pi, ds):
    start = int(ds.elections_t[-1]) if len(ds.elections_t) else 0
    sub = pi[:, :, start:, :].reshape(-1, pi.shape[2] - start, pi.shape[3])
    q = np.quantile(sub, QUANTILES, axis=0)
    return {'weeks': [d.isoformat() for d in ds.weeks[start:]], 'q': np.moveaxis(q, 0, -1), 'mean': sub.mean(0), 'sd': sub.std(0, ddof=1)}


def run_arm(arm, attempt=1):
    env = validate_runtime()
    sys.path.insert(0, str(UPSTREAM / 'src'))
    from pollofpolls.config import Config
    from pollofpolls.model.numpyro_model import ModelData, poll_model
    import jax
    from numpyro.infer import MCMC, NUTS, init_to_median
    from scripts.polling.external_comparison.inference import diagnose
    cfg = Config(UPSTREAM); ds = load_dataset(arm); settings = settings_of(arm, attempt); sig = signature(arm, ds, settings, env)
    path = f'fits/{arm}/attempt{attempt}.json'; prefix = OUT / f'fits/{arm}/attempt{attempt}'
    if (OUT / path).exists():
        prior = read(OUT / path)
        if prior['signature'] != sig:
            raise ValueError('Incompatible cached signature')
        print('REUSE', arm, attempt, prior['status'], flush=True); return prior
    if attempt == 2 and read(OUT / f'fits/{arm}/attempt1.json')['status'] != 'numerical_failure':
        raise ValueError('Retry requires a recorded numerical failure')
    if len(jax.devices()) < 4 or not jax.config.jax_enable_x64:
        raise ValueError('Require four CPU chains and x64')
    data = ModelData.from_dataset(ds, cfg.variant('gauss')); start = time.monotonic(); prefix.parent.mkdir(parents=True, exist_ok=True)
    kernel = NUTS(poll_model, max_tree_depth=settings['max_tree_depth'], target_accept_prob=settings['target_accept'],
                  init_strategy=init_to_median(num_samples=20), dense_mass=False)
    mcmc = MCMC(kernel, num_warmup=settings['warmup'], num_samples=settings['samples'], num_chains=settings['chains'], chain_method='parallel', progress_bar=False)
    print('START', arm, attempt, digest(sig), flush=True)
    try:
        mcmc.run(jax.random.PRNGKey(settings['seed']), data, cfg.variant('gauss'), cfg.priors, cfg.model_cfg['election_obs_sd'],
                 extra_fields=('diverging', 'num_steps', 'accept_prob', 'energy'))
        samples = {k: np.asarray(v) for k, v in mcmc.get_samples(group_by_chain=True).items()}
        extra = {k: np.asarray(v) for k, v in mcmc.get_extra_fields(group_by_chain=True).items()}
        pi = samples['pi']; C = ds.n_cycles
        names, offsets = house_offsets(samples, ds)
        path_q = path_summary(pi, ds)
        saved = {'electionDay': pi[:, :, ds.target_t, :], 'lastDataSupport': pi[:, :, ds.last_data_t, :],
                 'houseOffset2026': offsets.astype(np.float32), 'industryStart2026': samples['industry_start'][:, :, C - 1, :].astype(np.float32),
                 'industryEnd2026': samples['industry_end'][:, :, C - 1, :].astype(np.float32), 'sigma': samples['sigma'].astype(np.float32),
                 'designEffect': samples['design_effect'].astype(np.float32), **{k: samples[k].astype(np.float32) for k in SAVED_SCALARS},
                 'pathQuantiles': path_q['q'], 'pathMean': path_q['mean'], 'pathSd': path_q['sd'], **{'extra__' + k: v for k, v in extra.items()}}
        tmp = prefix.with_name(prefix.name + '-writing.npz'); np.savez_compressed(tmp, **saved); tmp.replace(prefix.with_suffix('.npz'))
        if arm == 'A':
            cache = CACHE / 'raw-samples'; cache.mkdir(parents=True, exist_ok=True)
            for k, v in samples.items():
                np.save(cache / f'{arm}-attempt{attempt}-{k}.npy', v)
        diag = diagnose(samples, extra, ds, settings['max_tree_depth'])
        save(f'fits/{arm}/attempt{attempt}-diagnostics.json.gz', diag)
        brief = {k: v for k, v in diag.items() if k != 'variables'}
        brief['variables'] = [{'variable': r['variable'], 'active': len(r['coordinates']), 'failed': len(r['failedCoordinates']),
                               'maxRhat': max([x for x in r['rhat'] if x is not None] or [0]), 'minBulkESS': min([x for x in r['bulkESS'] if x is not None] or [0]),
                               'minTailESS': min([x for x in r['tailESS'] if x is not None] or [0])} for r in diag['variables']]
        result = {'arm': arm, 'attempt': attempt, 'signature': sig, 'status': 'accepted' if diag['passed'] else 'numerical_failure', 'settings': settings,
                  'parties': ds.parties, 'pollsters2026': names, 'diagnostics': brief, 'diagnosticsSha256': sha(OUT / f'fits/{arm}/attempt{attempt}-diagnostics.json.gz'),
                  'npzSha256': sha(prefix.with_suffix('.npz')), 'runtimeSeconds': time.monotonic() - start,
                  'drawIds': [f'live-{arm}-attempt{attempt}-chain{c + 1}-draw{i:04d}' for c in range(settings['chains']) for i in range(settings['samples'])],
                  'expectedElectionDay': pi[:, :, ds.target_t, :].mean((0, 1)).tolist(), 'expectedLastData': pi[:, :, ds.last_data_t, :].mean((0, 1)).tolist(),
                  'savedDrawChainShape': [settings['chains'], settings['samples'], ds.K],
                  'distribution': 'latent support at the last-data week (no polling error) and at the election week (includes the common polling-error draw); no extra bias draw; internal only'}
    except (FloatingPointError, ValueError) as e:
        if isinstance(e, ValueError) and 'Cannot find valid initial parameters' not in str(e):
            raise
        result = {'arm': arm, 'attempt': attempt, 'signature': sig, 'status': 'numerical_failure', 'exception': str(e), 'runtimeSeconds': time.monotonic() - start}
    save(path, result); print('FINISHED', arm, attempt, result['status'], 'seconds', result['runtimeSeconds'], flush=True)
    del mcmc; gc.collect(); jax.clear_caches(); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--arm', required=True); p.add_argument('--attempt', type=int, choices=[1, 2], default=1)
    a = p.parse_args(); run_arm(a.arm, a.attempt)
