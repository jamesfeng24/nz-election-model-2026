"""Stage70 fit: the Stage62 inference (pinned gauss model, Stage38 PRIMARY settings, seed 2034, full-coordinate diagnostics)
on one dated dataset. Needs .venv-external and four CPU devices; never run in CI."""
import os
os.environ.setdefault('XLA_FLAGS', '--xla_force_host_platform_device_count=4')
os.environ.setdefault('JAX_ENABLE_X64', 'True')
import gc
import sys
import time
import numpy as np
from scripts.polling.live_fit import inference as I
from scripts.polling.live_fit.common import UPSTREAM, PIN, PRIMARY, RETRY, SEED, sha, digest
from .common import write, read, rel


def settings_of(attempt):
    return {**(PRIMARY if attempt == 1 else RETRY), 'seed': SEED}


def signature(run_date, ds, settings, env, contract_sha):
    cfgs = {str(p.relative_to(UPSTREAM)): sha(p) for p in sorted((UPSTREAM / 'config').glob('*.yml'))}
    return {'refreshDate': run_date, 'dataset': ds.fingerprint(), 'cutoff': ds.cutoff.isoformat(), 'pin': PIN, 'variant': 'gauss', 'settings': settings,
            'environment': env, 'upstreamConfig': cfgs, 'inputContract': contract_sha, 'runnerSha256': sha(__file__)}


def run_attempt(run_dir, run_date, ds, attempt, contract_sha):
    env = I.validate_runtime()
    sys.path.insert(0, str(UPSTREAM / 'src'))
    from pollofpolls.config import Config
    from pollofpolls.model.numpyro_model import ModelData, poll_model
    import jax
    from numpyro.infer import MCMC, NUTS, init_to_median
    from scripts.polling.external_comparison.inference import diagnose
    cfg = Config(UPSTREAM); settings = settings_of(attempt); sig = signature(run_date, ds, settings, env, contract_sha)
    fit_dir = run_dir / 'fit'; fit_dir.mkdir(parents=True, exist_ok=True)
    prefix = fit_dir / f'attempt{attempt}'
    if len(jax.devices()) < 4 or not jax.config.jax_enable_x64:
        raise ValueError('Require four CPU chains and x64')
    data = ModelData.from_dataset(ds, cfg.variant('gauss')); start = time.monotonic()
    kernel = NUTS(poll_model, max_tree_depth=settings['max_tree_depth'], target_accept_prob=settings['target_accept'],
                  init_strategy=init_to_median(num_samples=20), dense_mass=False)
    mcmc = MCMC(kernel, num_warmup=settings['warmup'], num_samples=settings['samples'], num_chains=settings['chains'], chain_method='parallel', progress_bar=False)
    print('START', run_date, attempt, digest(sig), flush=True)
    try:
        mcmc.run(jax.random.PRNGKey(settings['seed']), data, cfg.variant('gauss'), cfg.priors, cfg.model_cfg['election_obs_sd'],
                 extra_fields=('diverging', 'num_steps', 'accept_prob', 'energy'))
        samples = {k: np.asarray(v) for k, v in mcmc.get_samples(group_by_chain=True).items()}
        extra = {k: np.asarray(v) for k, v in mcmc.get_extra_fields(group_by_chain=True).items()}
        pi = samples['pi']; C = ds.n_cycles
        names, offsets = I.house_offsets(samples, ds)
        path_q = I.path_summary(pi, ds)
        n_path = ds.last_data_t - int(ds.elections_t[-1] if len(ds.elections_t) else 0) + 1   # weeks up to the latest model state only; later weeks are drift
        # Nowcast input (D106): the latent state at the last-data week. The election-week state (`electionDay`) is deliberately not saved:
        # it adds only future drift and the config forbids it. `lastDataSupport` already integrates the industry polling-error uncertainty.
        saved = {'lastDataSupport': pi[:, :, ds.last_data_t, :], 'houseOffset2026': offsets.astype(np.float32),
                 **{k: samples[k].astype(np.float32) for k in I.SAVED_SCALARS},
                 'pathQuantiles': path_q['q'][:n_path], 'pathMean': path_q['mean'][:n_path], 'pathSd': path_q['sd'][:n_path], 'extra__diverging': extra['diverging']}
        tmp = prefix.with_name(prefix.name + '-writing.npz'); np.savez_compressed(tmp, **saved); tmp.replace(prefix.with_suffix('.npz'))
        diag = diagnose(samples, extra, ds, settings['max_tree_depth'])
        diag_path = fit_dir / f'attempt{attempt}-diagnostics.json.gz'
        import gzip
        from scripts.polling.live_fit.common import encode
        raw = bytearray(gzip.compress(encode(diag), mtime=0)); raw[9] = 255; diag_path.write_bytes(bytes(raw))
        brief = {k: v for k, v in diag.items() if k != 'variables'}
        result = {'refreshDate': run_date, 'attempt': attempt, 'signature': sig, 'status': 'accepted' if diag['passed'] else 'numerical_failure',
                  'settings': settings, 'parties': ds.parties, 'pollsters2026': names, 'diagnostics': brief,
                  'diagnosticsSha256': sha(diag_path), 'npzSha256': sha(prefix.with_suffix('.npz')), 'runtimeSeconds': time.monotonic() - start,
                  'drawIds': [f'weekly-{run_date}-attempt{attempt}-chain{c + 1}-draw{i:04d}' for c in range(settings['chains']) for i in range(settings['samples'])],
                  'stateKey': 'lastDataSupport', 'modelStateAsOf': ds.weeks[ds.last_data_t].isoformat(),
                  'expectedLastData': pi[:, :, ds.last_data_t, :].mean((0, 1)).tolist(),
                  'savedDrawChainShape': [settings['chains'], settings['samples'], ds.K]}
    except (FloatingPointError, ValueError) as e:
        if isinstance(e, ValueError) and 'Cannot find valid initial parameters' not in str(e):
            raise
        result = {'refreshDate': run_date, 'attempt': attempt, 'signature': sig, 'status': 'numerical_failure', 'exception': str(e),
                  'runtimeSeconds': time.monotonic() - start}
    write(fit_dir / f'attempt{attempt}.json', result)
    print('FINISHED', run_date, attempt, result['status'], 'seconds', result['runtimeSeconds'], flush=True)
    del mcmc; gc.collect(); jax.clear_caches()
    return result


def fit(run_dir, run_date, ds, contract_sha):
    """Attempt 1 with the PRIMARY settings; one numerical retry with the frozen RETRY settings; nothing else."""
    r = run_attempt(run_dir, run_date, ds, 1, contract_sha)
    if r['status'] != 'accepted':
        r = run_attempt(run_dir, run_date, ds, 2, contract_sha)
    return r
