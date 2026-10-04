"""Bounded second inference queue with a separate resumable index."""
import argparse
from . import inference
from .common import OUT,read


def run(branch):
    if branch not in ('missing_n1000','publication_lag10'):raise ValueError('Only registered sensitivity queues')
    queue=OUT/f'queues/{branch}-construction.json'
    original_read=inference.read;original_save=inference.save
    def queue_read(path):
        if path==OUT/'construction.json':return read(queue) if queue.exists() else {'cases':[]}
        return original_read(path)
    def queue_save(path,value,check=False):
        name=f'queues/{branch}-construction.json' if path=='construction.json' else path
        return original_save(name,value,check)
    inference.read=queue_read;inference.save=queue_save
    inference.run([branch],[2014,2017,2020,2023],[14,56])
    print(branch,'queue complete; main runner reuses exact shared fit signatures.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('branch',choices=['missing_n1000','publication_lag10']);run(p.parse_args().branch)
