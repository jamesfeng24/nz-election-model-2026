"""Bounded parallel verified-only queue; statistical code/signatures unchanged."""
from . import inference
from .common import OUT,read,save


def run():
    queue=OUT/'queues/verified-only-construction.json'
    original_read=inference.read;original_save=inference.save
    def queue_read(path):
        if path==OUT/'construction.json':return read(queue) if queue.exists() else {'cases':[]}
        return original_read(path)
    def queue_save(path,value,check=False):
        return original_save('queues/verified-only-construction.json' if path=='construction.json' else path,value,check)
    inference.read=queue_read;inference.save=queue_save
    inference.run(['verified_only'],[2014,2017,2020,2023],[14,56])
    print('Verified queue complete; main runner reuses these exact shared fit signatures.',flush=True)


if __name__=='__main__':run()
