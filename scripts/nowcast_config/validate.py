"""Stage72: fail-closed validation of the live nowcast configuration and the 2026 ordinary/exceptional classification.

python -m scripts.nowcast_config.validate [--classification PATH] [--require-complete]

The configuration may carry explicitly pending fields (owned by Stage50, Stage63, Stage69/70 or James); assembly
runs with --require-complete, which fails while any remain. The classification must cover every 2026 general seat
exactly once, keyed by 2026 boundary id, with a dated, sourced reason (D107). A missing file or seat is an error,
never a default to the ordinary scale.
"""
import argparse
import datetime
import json
import sys
from scripts.manual_adjustment.schema import seat_frame
from scripts.polling import electorate_live
from scripts.uncertainty_revision.common import ROOT, read

CONFIG = 'config/nowcast-2026.json'
INTERVAL_LEVELS = [0.5, 0.8, 0.9]
CLASSES = ('ordinary', 'exceptional')
ENTRY_FIELDS = {'electorateId', 'class', 'reason', 'sources', 'author', 'recordedAt', 'extraSdOptIn'}


class ConfigError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ConfigError(message)


def is_date(value):
    try:
        datetime.date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def check_config(config, require_complete=False):
    """Return the list of pending field paths; raise ConfigError on any invalid or forbidden setting."""
    require(config.get('schemaVersion') == 1, 'config schemaVersion must be 1')
    require(config.get('estimand') == 'nowcast', 'the primary product is a nowcast (D106)')
    national = config['national']
    require(national['stateKey'] == 'lastDataSupport', 'the nowcast national input is lastDataSupport (D106)')
    require(national['stateKey'] not in national['forbiddenStateKeys'] and 'electionDay' in national['forbiddenStateKeys'],
            'election-week draws must be forbidden for the nowcast')
    require(all(is_date(config[k]) for k in ('electionDate',)) and is_date(national['modelStateAsOf']) and is_date(national['dataCutoff']),
            'dates must be ISO dates')
    require(national['modelStateAsOf'] <= national['dataCutoff'] <= config['electionDate'],
            'modelStateAsOf <= dataCutoff <= electionDate')
    multipliers = config['uncertainty']['candidateBalanceSeatMultiplier']
    require(multipliers == {'ordinary': 0.60, 'exceptional': 1.00}, 'D107 multipliers are 0.60 ordinary and 1.00 exceptional')
    within = config['uncertainty']['candidateWithinSeatMultiplier']
    require(within == {'ordinary': 0.55, 'exceptional': 1.00}, 'Stage83 within-remainder multipliers are 0.55 ordinary and 1.00 exceptional (D121)')
    mass = config['uncertainty']['candidateMassSeatMultiplier']
    require(mass == {'ordinary': 0.91, 'exceptional': 1.00}, 'Stage83 major-mass multipliers are 0.91 ordinary and 1.00 exceptional (D121)')
    require(config['uncertainty']['extraSdOnExceptionalRequiresOptIn'] is True, 'extra sd on 1.00 seats needs an explicit opt-in (D107)')
    require(config['intervalLevels'] == INTERVAL_LEVELS and config['primaryIntervalLevel'] == 0.8, 'intervals are 50/80/90 with 80% primary')
    require(config['maori']['unpolledSeats'] in (None, 'labelled-fallback', 'withhold'),
            'maori.unpolledSeats is a labelled fallback or withhold (D114), or still pending')
    model = config['maori']['unpolledFallbackModel']
    require(model in (None, 'stage78-f'), 'maori.unpolledFallbackModel is stage78-f (Stage78 arm F, D115) or still pending')
    require(model is None or config['maori']['unpolledSeats'] == 'labelled-fallback', 'a registered fallback model needs maori.unpolledSeats = labelled-fallback')
    require(model is not None or config['maori']['unpolledSeats'] != 'labelled-fallback' or 'maori.unpolledFallbackModel' in config.get('pending', {}),
            'a labelled fallback without a registered model must be listed as pending')
    require(0 < config['release']['probabilityMcseMax'] < 0.5 and config['release']['reconciliationTolerancePP'] > 0,
            'release thresholds must be positive and the MCSE limit below 0.5')
    for path in ('national.source', 'uncertainty.scales', 'baseline.source'):
        section, key = path.split('.')
        require((ROOT / config[section][key]).exists(), f'{path} does not exist: {config[section][key]}')
    seat_polls = config.get('seatPolls')
    if seat_polls is not None:
        require(set(seat_polls) == {'enabled', 'decision', 'electorateRun'} and isinstance(seat_polls['enabled'], bool),
                'seatPolls is {enabled: bool, decision, electorateRun}')
        run = seat_polls['electorateRun']
        require(run is None or (isinstance(run, dict) and set(run) == {'date', 'pollsSha256'}), 'seatPolls.electorateRun is {date, pollsSha256} or null')
        if run is not None:
            entry = [r for r in electorate_live.runs() if r['date'] == run['date']]
            require(len(entry) == 1 and entry[0]['pollsSha256'] == run['pollsSha256'],
                    'seatPolls.electorateRun must name an electorate-live run and its polls.json hash (audit J2)')
        if seat_polls['enabled']:
            require(run is not None, 'enabled seat polls need a pinned seatPolls.electorateRun (audit J2)')
            findings = 'data/processed/seat-polls/findings.json'
            require((ROOT / findings).exists() and read(findings)['summary']['finding'] == 'adopt',
                    'seat polls can be enabled only when the frozen Stage79 finding is adopt (D117)')
    pending = config.get('pending', {})
    for path in pending:
        section, key = path.split('.')
        require(config.get(section, {}).get(key) is None, f'{path} is listed as pending but has a value')
    if config['roster']['snapshotId'] is not None:
        for path in ('candidate.features', 'candidate.centredFeatures', 'partyRelationships'):
            value = config['partyRelationships'] if path == 'partyRelationships' else config['candidate'][path.split('.')[1]]
            require((ROOT / value).exists(), f'{path} does not exist: {value}')
    else:
        require('roster.snapshotId' in pending, 'roster.snapshotId is null but not listed as pending')
    if require_complete:
        require(not pending, 'pending fields must be filled before assembly: ' + ', '.join(sorted(pending)))
    return sorted(pending)


def check_classification(document, general_ids=None, stage56_exceptional=()):
    """Validate the D107 classification document; return {electorateId: class}."""
    general_ids = set(general_ids if general_ids is not None else seat_frame()['general'])
    require(document.get('schemaVersion') == 1, 'classification schemaVersion must be 1')
    require(is_date(document.get('asOf')), 'classification asOf must be an ISO date')
    entries = document.get('seats')
    require(isinstance(entries, list), 'classification seats must be a list')
    seen = {}
    for i, entry in enumerate(entries):
        require(set(entry) == ENTRY_FIELDS, f'seat {i}: fields must be exactly {sorted(ENTRY_FIELDS)}')
        seat = entry['electorateId']
        require(seat in general_ids, f'{seat} is not a 2026 general electorate id')
        require(seat not in seen, f'{seat} is classified more than once')
        require(entry['class'] in CLASSES, f'{seat}: class must be ordinary or exceptional')
        require(isinstance(entry['reason'], str) and 10 <= len(entry['reason'].strip()) <= 500, f'{seat}: a reason is required')
        require(isinstance(entry['sources'], list) and all(isinstance(s, str) and s for s in entry['sources']), f'{seat}: sources must be a list')
        require(entry['class'] == 'ordinary' or entry['sources'], f'{seat}: an exceptional seat needs at least one source')
        require(isinstance(entry['author'], str) and entry['author'].strip(), f'{seat}: author is required')
        require(is_date(entry['recordedAt']), f'{seat}: recordedAt must be an ISO date')
        require(isinstance(entry['extraSdOptIn'], bool), f'{seat}: extraSdOptIn must be true or false')
        require(entry['class'] == 'exceptional' or not entry['extraSdOptIn'], f'{seat}: extraSdOptIn only applies to exceptional seats')
        seen[seat] = entry['class']
    missing = sorted(general_ids - set(seen))
    require(not missing, f'{len(missing)} general seats are unclassified (no default to 0.60): {missing[:5]}')
    clash = sorted(s for s in stage56_exceptional if seen.get(s) != 'exceptional')
    require(not clash, f'Stage56 flags these seats exceptional but the classification does not: {clash}')
    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--classification', default=None)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    config = read(CONFIG)
    try:
        pending = check_config(config, args.require_complete)
        path = args.classification or config['uncertainty']['classification']
        if (ROOT / path).exists():
            seats = check_classification(json.loads((ROOT / path).read_text(encoding='utf-8')))
            print(f'classification valid: {sum(c == "exceptional" for c in seats.values())} exceptional of {len(seats)} general seats')
        elif args.require_complete:
            raise ConfigError(f'classification file missing: {path}')
        else:
            print(f'classification not yet written: {path} (required before assembly)')
    except ConfigError as error:
        print('INVALID:', error)
        sys.exit(1)
    print('config valid; pending:', ', '.join(pending) if pending else 'none')


if __name__ == '__main__':
    main()
