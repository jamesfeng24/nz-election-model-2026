"""The Stage82 electorate-poll runs (`data/processed/polling/electorate-live/`, append-only) and the run the configuration pins (audit J2).

`seatPolls.electorateRun` in config/nowcast-2026.json names one run by date and polls.json hash; the nowcast assembly, its evidence and the
Stage79 readout read that run, so merging a poll refresh changes nothing until the run is adopted (`weekly_refresh.adopt`). Without a pinned
run (`date=None`) the newest run is read, as the Stage79 and Stage86 development checks did before the pin.
Fails closed: an unknown date, or a polls.json that does not match its index entry (or the pinned hash), raises.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = 'data/processed/polling/electorate-live'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def runs():
    return read(LIVE + '/index.json')['runs']


def run_entry(date=None):
    """The index entry of the run on `date` (the newest when None); None when no run exists and no date is asked for."""
    entries = runs()
    if date is None:
        return entries[-1] if entries else None
    found = [r for r in entries if r['date'] == date]
    if len(found) != 1:
        raise ValueError(f'No electorate-live run dated {date}')
    return found[0]


def polls(date=None, sha256=None):
    """All polls of a run (empty when there is none); polls.json must match its index entry and, when given, the pinned hash."""
    run = run_entry(date)
    if run is None:
        return []
    path = f"{LIVE}/{run['date']}/polls.json"
    payload = read(path)
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    if len(payload['polls']) != run['pollCount'] or digest != run['pollsSha256']:
        raise ValueError('electorate-live polls.json does not match its index entry')
    if sha256 is not None and digest != sha256:
        raise ValueError(f"electorate-live run {run['date']} does not match the pinned hash")
    return payload['polls']


def newest_date():
    """The date of the newest electorate-poll run, or None when there is none (the index only; no poll is read)."""
    entries = runs()
    return entries[-1]['date'] if entries else None


def forecast_cutoff(config):
    """The date the whole forecast is as of: the seat polls are read up to it and aged from it, and it is the release's data cutoff.

    `seatPolls.pollCutoff` when set, else the national data cutoff. It is the national cutoff unless an electorate-poll refresh arrived after the
    last national one: the national state needs no refit when no national poll is new, but the seat polls (and their decay) move with the refresh
    date. `weekly_refresh.adopt` sets it to the later of the adopted national cutoff and the adopted electorate-poll run's date."""
    return (config.get('seatPolls') or {}).get('pollCutoff') or config['national']['dataCutoff']


def pinned(config):
    """(date, sha256) of the configured run, or (None, None) when seat polls are off or the configuration pins no run."""
    run = (config.get('seatPolls') or {}).get('electorateRun')
    return (run['date'], run['pollsSha256']) if run else (None, None)
