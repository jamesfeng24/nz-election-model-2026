"""Adopt a published weekly refresh as the nowcast national input (an explicit, reviewed step; the routine never runs it).

    python3 -m scripts.polling.weekly_refresh.adopt --date YYYY-MM-DD [--electorate-date YYYY-MM-DD] [--check]

Sets config/nowcast-2026.json national.source, modelStateAsOf and dataCutoff to the values recorded in that run's
estimate.json (`nowcastInput`), pins seatPolls.electorateRun to a Stage82 electorate-poll run (`--electorate-date`, default the newest run: a
refresh writes an electorate run only when the electorate polls changed; the assembly still reads only polls ending by the data cutoff; audit
J2) and bumps configVersion (text edits of those values only), then validates the result with scripts.nowcast_config.validate. Nothing else
in the configuration changes. `--check` verifies that the config already carries the run's national values and, when `--electorate-date` is
given, that electorate run (the validator checks any pinned run against the electorate-poll index).
"""
import argparse
import json
from scripts.nowcast_config.validate import check_config
from scripts.polling import electorate_live
from .common import ROOT, OUT, load_index, read

CONFIG = ROOT / 'config/nowcast-2026.json'


def target(date):
    if date not in {r['date'] for r in load_index()['runs']}:
        raise ValueError('Not a published refresh: ' + date)
    est = read(OUT / date / 'estimate.json')
    return est['nowcastInput']


def electorate_target(date=None):
    """{date, pollsSha256} of the Stage82 electorate-poll run on `date` (the newest when None), or None when there is none yet."""
    run = electorate_live.run_entry(date)
    return None if run is None else {'date': run['date'], 'pollsSha256': run['pollsSha256']}


def run_text(run):
    return 'null' if run is None else f'{{"date": "{run["date"]}", "pollsSha256": "{run["pollsSha256"]}"}}'


def next_version(old, day):
    base, _, n = old.rpartition('.')
    return f'{day}.{int(n) + 1 if base == day else 1}'


def adopt(date, check=False, electorate_date=None):
    want = target(date)
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    n = config['national']
    current = (n['source'], n['modelStateAsOf'], n['dataCutoff'])
    wanted = (want['source'], want['modelStateAsOf'], want['dataCutoff'])
    run_now, run_wanted = config['seatPolls']['electorateRun'], electorate_target(electorate_date)
    if check:
        if current != wanted:
            raise ValueError(f'config national input {current} differs from the {date} refresh {wanted}')
        if electorate_date is not None and run_now != run_wanted:
            raise ValueError(f'config electorate-poll run {run_now} differs from the {date} refresh {run_wanted}')
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
    needle = f'"electorateRun": {run_text(run_now)}'
    if text.count(needle) != 1:
        raise ValueError(f'Expected exactly one {needle} in the config')
    text = text.replace(needle, f'"electorateRun": {run_text(run_wanted)}')
    config['national']['source'], config['national']['modelStateAsOf'], config['national']['dataCutoff'], config['configVersion'] = *wanted, version
    config['seatPolls']['electorateRun'] = run_wanted
    if json.loads(text) != config:
        raise ValueError('Surgical edit changed more than the adopted fields')
    check_config(config)
    CONFIG.write_text(text, encoding='utf-8')
    return wanted


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', required=True); ap.add_argument('--electorate-date'); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    print(('ok ' if a.check else 'adopted ') + str(adopt(a.date, a.check, a.electorate_date)))


if __name__ == '__main__':
    main()
