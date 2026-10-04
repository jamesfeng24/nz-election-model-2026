"""Serial, bounded inference supervisor; resumes completed cases only."""
import os
from pathlib import Path
import subprocess
import sys
import time
from .common import ROOT,OUT,CASES,read,save


def run():
    from .runtime import validate_runtime,validate_cached_record
    validate_runtime()
    spec=read(OUT/'specification.json')['numerical'];started=time.monotonic();history=read(OUT/'batch.json') if (OUT/'batch.json').exists() else {'attempts':[]}
    spent=sum(x['wallSeconds'] for x in history['attempts']);limit=spec['maxTotalWorkerSeconds']
    for year,_ in CASES:
        used=sum(x['wallSeconds'] for x in history['attempts'] if x['year']==year)
        for attempt in (1,2):
            output=OUT/f'fits/{year}/attempt{attempt}.json'
            if output.exists():
                record=read(output)
                validate_cached_record(record,year,attempt)
                if record['status']=='accepted':break
                continue
            prior=[x for x in history['attempts'] if x['year']==year and x['attempt']==attempt]
            if prior:break  # interrupted/timeout attempts are never silently repeated
            if attempt==2 and (not (OUT/f'fits/{year}/attempt1.json').exists() or read(OUT/f'fits/{year}/attempt1.json')['status']!='numerical_failure'):break
            remaining=min(limit-spent,spec['maxCaseWorkerSeconds']-used)
            if remaining<=0:
                history['capReached']=True;save('batch.json',history);return
            env={**os.environ,'XLA_FLAGS':'--xla_force_host_platform_device_count=4','JAX_ENABLE_X64':'True','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MPLCONFIGDIR':str(ROOT/'.cache/stage38/matplotlib')}
            log=OUT/f'fits/{year}/attempt{attempt}.txt';log.parent.mkdir(parents=True,exist_ok=True);t=time.monotonic()
            with log.open('w') as f:
                try:
                    done=subprocess.run([sys.executable,'-m','scripts.polling.external_comparison.guarded','--year',str(year),'--attempt',str(attempt)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=remaining)
                    status='finished' if done.returncode==0 else 'runtime_error';code=done.returncode
                except subprocess.TimeoutExpired:status='compute_cap';code=None
            elapsed=time.monotonic()-t;spent+=elapsed;used+=elapsed
            history['attempts'].append({'year':year,'attempt':attempt,'wallSeconds':elapsed,'status':status,'returncode':code,'log':str(log.relative_to(OUT))});save('batch.json',history)
            print('CASE_ATTEMPT',year,attempt,status,elapsed,flush=True)
            if status=='runtime_error':raise RuntimeError('Inspect implementation/runtime failure '+str(log))
            if status=='compute_cap':break
            if read(output)['status']=='accepted':break
    history['complete']=True;history['summedWorkerSeconds']=spent;save('batch.json',history)


if __name__=='__main__':run()
