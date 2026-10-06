"""Serial bounded supervisor for the Stage62 fits; resumes completed signatures only. Never run in CI."""
import os
import subprocess
import sys
import time
from .common import ROOT, OUT, ARMS, ENV_CHECK, read, save

ORDER = [ENV_CHECK, 'A', 'A2', 'B1', 'B2', 'E', 'T']
CAP_PER_ARM = 2 * 3600
CAP_TOTAL = 8 * 3600


def run():
    from .inference import validate_runtime
    validate_runtime()
    history = read(OUT / 'batch.json') if (OUT / 'batch.json').exists() else {'attempts': []}
    spent = sum(x['wallSeconds'] for x in history['attempts'])
    for arm in ORDER:
        used = sum(x['wallSeconds'] for x in history['attempts'] if x['arm'] == arm)
        for attempt in (1, 2):
            output = OUT / f'fits/{arm}/attempt{attempt}.json'
            if output.exists():
                if read(output)['status'] == 'accepted':
                    break
                continue
            if any(x['arm'] == arm and x['attempt'] == attempt for x in history['attempts']):
                break  # an interrupted attempt is never silently repeated
            if attempt == 2 and (not (OUT / f'fits/{arm}/attempt1.json').exists() or read(OUT / f'fits/{arm}/attempt1.json')['status'] != 'numerical_failure'):
                break
            remaining = min(CAP_TOTAL - spent, CAP_PER_ARM - used)
            if remaining <= 0:
                history['capReached'] = True; save('batch.json', history); return
            env = {**os.environ, 'XLA_FLAGS': '--xla_force_host_platform_device_count=4', 'JAX_ENABLE_X64': 'True', 'OMP_NUM_THREADS': '1',
                   'OPENBLAS_NUM_THREADS': '1', 'MPLCONFIGDIR': str(ROOT / '.cache/stage62/matplotlib')}
            log = OUT / f'fits/{arm}/attempt{attempt}.txt'; log.parent.mkdir(parents=True, exist_ok=True); t = time.monotonic()
            with log.open('w') as f:
                try:
                    done = subprocess.run([sys.executable, '-m', 'scripts.polling.live_fit.inference', '--arm', arm, '--attempt', str(attempt)],
                                          cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=remaining)
                    status = 'finished' if done.returncode == 0 else 'runtime_error'; code = done.returncode
                except subprocess.TimeoutExpired:
                    status = 'compute_cap'; code = None
            elapsed = time.monotonic() - t; spent += elapsed; used += elapsed
            history['attempts'].append({'arm': arm, 'attempt': attempt, 'wallSeconds': elapsed, 'status': status, 'returncode': code, 'log': str(log.relative_to(OUT))})
            save('batch.json', history); print('ARM_ATTEMPT', arm, attempt, status, elapsed, flush=True)
            if status == 'runtime_error':
                raise RuntimeError('Inspect implementation/runtime failure ' + str(log))
            if status == 'compute_cap':
                break
            if read(output)['status'] == 'accepted':
                break
    history['complete'] = True; history['summedWallSeconds'] = spent; save('batch.json', history)


if __name__ == '__main__':
    run()
