"""Adopt a published weekly refresh as the nowcast national input (an explicit, reviewed step; the routine never runs it).

    python3 -m scripts.polling.weekly_refresh.adopt --date YYYY-MM-DD [--check]

Sets config/nowcast-2026.json national.source, modelStateAsOf and dataCutoff to the values recorded in that run's
estimate.json (`nowcastInput`) and bumps configVersion (text edits of those four values only), then validates the result with scripts.nowcast_config.validate.
Nothing else in the configuration changes. `--check` verifies that the config already carries the run's values.
"""
import argparse
import json
from scripts.nowcast_config.validate import check_config
from .common import ROOT, OUT, load_index, read

CONFIG = ROOT / 'config/nowcast-2026.json'


def target(date):
    if date not in {r['date'] for r in load_index()['runs']}:
        raise ValueError('Not a published refresh: ' + date)
    est = read(OUT / date / 'estimate.json')
    return est['nowcastInput']


def next_version(old, day):
    base, _, n = old.rpartition('.')
    return f'{day}.{int(n) + 1 if base == day else 1}'


def adopt(date, check=False):
    want = target(date)
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    n = config['national']
    current = (n['source'], n['modelStateAsOf'], n['dataCutoff'])
    wanted = (want['source'], want['modelStateAsOf'], want['dataCutoff'])
    if check:
        if current != wanted:
            raise ValueError(f'config national input {current} differs from the {date} refresh {wanted}')
        return current
    # Surgical text edits keep the diff to the fields adopted (other work edits this file concurrently; a re-dump would reformat it).
    text = CONFIG.read_text(encoding='utf-8')
    version = next_version(config['configVersion'], date)
    for key, old_value, new_value in (('source', n['source'], wanted[0]), ('modelStateAsOf', n['modelStateAsOf'], wanted[1]), ('dataCutoff', n['dataCutoff'], wanted[2]),
                                      ('configVersion', config['configVersion'], version)):
        needle = f'"{key}": "{old_value}"'
        if text.count(needle) != 1:
            raise ValueError(f'Expected exactly one {needle} in the config')
        text = text.replace(needle, f'"{key}": "{new_value}"')
    config['national']['source'], config['national']['modelStateAsOf'], config['national']['dataCutoff'], config['configVersion'] = *wanted, version
    if json.loads(text) != config:
        raise ValueError('Surgical edit changed more than the adopted fields')
    check_config(config)
    CONFIG.write_text(text, encoding='utf-8')
    return wanted


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', required=True); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    print(('ok ' if a.check else 'adopted ') + str(adopt(a.date, a.check)))


if __name__ == '__main__':
    main()
