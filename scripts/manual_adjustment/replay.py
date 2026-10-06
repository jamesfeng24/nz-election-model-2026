"""Stage57 replay tooling: the labelling template, label validation and the freeze.

James labels each historical general-electorate seat-election (2014-2023) `ordinary` or `exceptional` knowing the
outcomes; he accepts the selection-bias risk (2026-10-06) and the design does not relitigate it. The guards are
mechanical instead:

* A fixed checklist of pre-election facts per seat-election (candidate change, boundary change, scandal, tactical
  arrangement, new strong challenger, other), each answered yes/no, a one-line reason for every yes, and a
  one-line reason for the label itself.
* The labelling view is outcome-free and residual-free. The template builder reads four input families only
  (boundary crosswalk, election candidate lists and source-election winners, the Stage51 ledger and its transition
  table); it never opens a model, score, residual or scale file, and every column is on an allow-list.
* Labels are frozen (hashed, with a statement that no residual was viewed) before any ordinary-seat scale is
  estimated. `require_frozen_labels` is the only supported way to read labels in an estimation stage.
"""
import csv
import io
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from .common import ROOT, AdjustmentError, require, sha256_bytes, sha256_text, sha256_file, parse_time, read_json

TEMPLATE_VERSION = 1
GEOGRAPHY = 'data/processed/forecast-transport/geography.json'
ELECTION_PATH = 'data/processed/elections/{year}.json'
LEDGER = 'data/processed/evidence/candidate-transitions/incumbent-seat-ledger.json'
TRANSITIONS = 'data/processed/evidence/candidate-transitions/transition-table.json'
INPUT_FAMILIES = (GEOGRAPHY, LEDGER, TRANSITIONS, *(ELECTION_PATH.format(year=y) for y in (2011, 2014, 2017, 2020, 2023)))
TEMPLATE = 'data/processed/manual-replay/labelling-template.csv'
TEMPLATE_MANIFEST = 'data/processed/manual-replay/template-manifest.json'
LABELS = 'data/manual-replay/labels.csv'
FREEZE = 'data/manual-replay/labels-freeze.json'
YEARS = (2014, 2017, 2020, 2023)
FACTS = ('candidate_change', 'boundary_change', 'scandal', 'tactical_arrangement', 'new_strong_challenger', 'other')
SCANDAL_TAGS = ('scandal_context', 'travel_entitlement_scandal', 'expelled_from_party')
READ_ONLY = ('seat_election_id', 'election_year', 'electorate', 'previous_election_winner', 'national_candidate', 'labour_candidate',
             'other_candidates', 'boundary_evidence', 'candidate_change_evidence', 'facts_prefilled')
HUMAN = tuple(c for f in FACTS for c in (f, f + '_reason')) + ('label', 'label_reason', 'labeller', 'labelled_at')
COLUMNS = READ_ONLY + HUMAN
LABELS_ALLOWED = ('ordinary', 'exceptional')
ANSWERS = ('yes', 'no')
# Never a column here, and never a model or score input: the labelling view stays blind to the model's errors.
FORBIDDEN_TOKENS = ('residual', 'error', 'crps', 'score', 'sigma', 'scale', 'prediction', 'predicted', 'probability', 'forecast',
                    'actual', 'result', 'votes', 'majority', 'margin', 'bias', 'mean_share', 'standardised', 'pit')
READ_LOG = []


def _read(relative):
    READ_LOG.append(relative)
    return read_json(ROOT / relative)


def _fraction(value):
    return Fraction(value['numerator'], value['denominator'])


def _pct(value):
    return f'{float(value) * 100:.1f}%'


def _elections():
    """{year: {electorateId: {name, candidates, winner}}} from candidate lists; vote counts are dropped on read."""
    out = {}
    for year in (2011, 2014, 2017, 2020, 2023):
        out[year] = {}
        for e in _read(ELECTION_PATH.format(year=year))['electorates']:
            if e['kind'] != 'general':
                continue
            out[year][e['id']] = {'name': e['name'], 'winner': e['winnerCandidateId'],
                                  'candidates': {c['id']: (c['name'], c['party'], c['partyKey']) for c in e['candidates']}}
    return out


def _boundary(record):
    """(answer, evidence): 'no' only when both lower bounds say identical membership, 'yes' only when an upper bound is below one."""
    inh_l, inh_u = _fraction(record['dominantTargetInheritanceLower']), _fraction(record['dominantTargetInheritanceUpper'])
    ret_l, ret_u = _fraction(record['dominantSourceRetentionLower']), _fraction(record['dominantSourceRetentionUpper'])
    first = next((p for p in record['predecessors'] if p['sourceElectorateId'] == record['dominantPredecessorId']), None)
    name = first['sourceElectorateName'] if first else record['dominantPredecessorId']
    lo_hi = lambda a, b: _pct(a) if a == b else f'{_pct(min(a, b))}-{_pct(max(a, b))}'
    evidence = (f'dominant predecessor {name} ({record["sourceYear"]}); {len(record["predecessors"])} predecessor(s); '
                f'target electors from it {lo_hi(inh_l, inh_u)}; its electors retained {lo_hi(ret_l, ret_u)}; '
                f'tier {record["exclusiveTier"]} (electoral-population bounds, not ballots)')
    if inh_l == 1 and ret_l == 1:
        return 'no', evidence
    if min(inh_u, ret_u) < 1:
        return 'yes', evidence
    return '', evidence + '; population bounds do not decide whether membership changed'


def build_template():
    """Deterministic rows for every general-electorate seat-election 2014-2023, pre-filled from repo evidence only."""
    del READ_LOG[:]
    geography = [r for r in _read(GEOGRAPHY)['records'] if r['scope'] == 'general' and r['targetYear'] in YEARS
                 and r['geographyId'].split(':')[0] == f'{r["sourceYear"]}-{r["targetYear"]}' and r.get('contestStatus') != 'cancelled_or_unheld']
    elections = _elections()
    ledger = {}
    for r in _read(LEDGER)['records']:
        if r['scope'] == 'general':
            for s in r['successorSeats'][:1]:
                ledger.setdefault(s['id'], []).append(r)
    transitions = {t['key']: t['transition'] for t in _read(TRANSITIONS)['records']}
    rows = []
    for record in sorted(geography, key=lambda r: (r['targetYear'], r['targetElectorateId'])):
        seat, year = record['targetElectorateId'], record['targetYear']
        target = elections[year][seat]
        source = elections.get(record['sourceYear'], {}).get(record['dominantPredecessorId'])
        winner = ''
        if source:
            name, party, _ = source['candidates'][source['winner']]
            winner = f'{name} ({party}, {record["sourceYear"]})'
        by_party = lambda key: '; '.join(n for n, _, k in target['candidates'].values() if k == key)
        others = '; '.join(f'{n} ({p})' for n, p, k in target['candidates'].values() if k not in ('nationalparty', 'labourparty'))
        row = {c: '' for c in COLUMNS}
        row.update(seat_election_id=seat, election_year=str(year), electorate=target['name'], previous_election_winner=winner,
                   national_candidate=by_party('nationalparty'), labour_candidate=by_party('labourparty'), other_candidates=others)
        prefilled = []
        answer, evidence = _boundary(record)
        row['boundary_evidence'] = evidence
        if answer:
            row['boundary_change'], prefilled = answer, prefilled + ['boundary_change']
            if answer == 'yes':
                row['boundary_change_reason'] = 'Crosswalk shows the seat is not identical to its dominant predecessor (see boundary_evidence)'
        entries = ledger.get(seat, [])
        if not entries:
            row['candidate_change_evidence'] = 'Not covered by Stage51 (source-election winner was not National or Labour, or no ledger mapping)'
        notes, tags = [], set()
        for entry in entries:
            t = transitions.get(entry['key']) if entry['relation'] == 'candidate_change' else None
            if t:
                incoming = entry['primaryTargetCandidate']['name'] if entry.get('primaryTargetCandidate') else 'unresolved'
                notes.append(f'{entry["party"]} {t["transitionType"]}: {entry["sourceWinner"]["name"]} -> {incoming}'
                             + (f' [{", ".join(t["tags"])}]' if t['tags'] else ''))
                tags |= set(t['tags'])
            else:
                notes.append(f'{entry["party"]} incumbent {entry["sourceWinner"]["name"]} recontested (Stage51 continuation)')
        if entries:
            row['candidate_change_evidence'] = ' | '.join(notes)
            changed = any(e['relation'] == 'candidate_change' for e in entries)
            row['candidate_change'] = 'yes' if changed else 'no'
            prefilled.append('candidate_change')
            if changed:
                row['candidate_change_reason'] = 'Stage51 documented incumbent-party candidate change (see candidate_change_evidence)'
            if tags & set(SCANDAL_TAGS):
                row['scandal'] = 'yes'
                row['scandal_reason'] = 'Stage51 tags: ' + ', '.join(sorted(tags & set(SCANDAL_TAGS)))
                prefilled.append('scandal')
        row['facts_prefilled'] = '; '.join(f for f in FACTS if f in prefilled)
        rows.append(row)
    require(len(rows) == len({r['seat_election_id'] for r in rows}), 'duplicate seat-election in the template')
    check_blind(COLUMNS)
    return rows


def check_blind(columns):
    """The labelling view may never carry model residuals, errors, scores, scales, predictions or election results."""
    for column in columns:
        require(column in COLUMNS, f'column {column!r} is not on the allow-list of the labelling view')
        bad = [t for t in FORBIDDEN_TOKENS if t in column]
        require(not bad, f'column {column!r} looks like a model or outcome field ({bad}); the labelling view is outcome- and residual-free')


def to_csv(rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text, newline=''))
    require(reader.fieldnames is not None and list(reader.fieldnames) == list(COLUMNS),
            'labels file header must match the template exactly (no added, removed or renamed columns)')
    rows = []
    for number, row in enumerate(reader, start=2):
        require(None not in row and None not in row.values(), f'line {number}: wrong number of cells')
        rows.append({k: (v or '').strip() for k, v in row.items()})
    return rows


def template_manifest(rows):
    text = to_csv(rows)
    return {'schemaVersion': TEMPLATE_VERSION, 'kind': 'stage57-labelling-template', 'columns': list(COLUMNS),
            'templateSha256': sha256_text(text), 'seatElections': len(rows),
            'byYear': {str(y): sum(1 for r in rows if r['election_year'] == str(y)) for y in YEARS},
            'prefilled': {f: sum(1 for r in rows if f in r['facts_prefilled'].split('; ')) for f in FACTS},
            'prefilledYes': {f: sum(1 for r in rows if r[f] == 'yes' and f in r['facts_prefilled'].split('; ')) for f in FACTS},
            'inputHashes': {p: sha256_file(ROOT / p) for p in INPUT_FAMILIES},
            'inputsRead': sorted(set(READ_LOG)),
            'blindness': 'reads only boundary crosswalk, candidate lists and source-election winners, and the Stage51 ledger; no model, score, residual or scale file',
            'labelsFrozen': False, 'scaleEstimated': False}


def validate_labels(rows, template, complete=False):
    """Check a labels file against the regenerated template. Returns a summary; raises AdjustmentError listing problems."""
    errors = []
    require(len(rows) == len(template) and [r['seat_election_id'] for r in rows] == [t['seat_election_id'] for t in template],
            'labels file must list exactly the template seat-elections in the template order')
    done = partial = untouched = 0
    for row, base in zip(rows, template):
        here = row['seat_election_id']
        for column in READ_ONLY:
            if row[column] != base[column]:
                errors.append(f'{here}: read-only column {column} was changed')
        filled = [c for c in HUMAN if row[c]]
        if not filled or filled == [c for c in HUMAN if base[c]]:
            untouched += 1
        for fact in FACTS:
            if row[fact] and row[fact] not in ANSWERS:
                errors.append(f'{here}: {fact} must be yes or no, got {row[fact]!r}')
            if row[fact] == 'yes' and not row[fact + '_reason']:
                errors.append(f'{here}: {fact} is yes and needs a one-line reason')
            if row[fact + '_reason'] and row[fact] != 'yes' and row[fact] != 'no':
                errors.append(f'{here}: {fact}_reason given without an answer')
        if row['label'] and row['label'] not in LABELS_ALLOWED:
            errors.append(f'{here}: label must be ordinary or exceptional, got {row["label"]!r}')
        if row['label'] == 'exceptional' and not any(row[f] == 'yes' for f in FACTS):
            errors.append(f'{here}: an exceptional seat must cite at least one checklist fact marked yes')
        if row['label'] and not (10 <= len(row['label_reason']) <= 300):
            errors.append(f'{here}: every label needs a one-line reason of 10 to 300 characters')
        for column in HUMAN:
            if '\n' in row[column] or '\r' in row[column]:
                errors.append(f'{here}: {column} must be one line')
        if row['labelled_at']:
            try:
                parse_time(row['labelled_at'], 'labelled_at')
            except AdjustmentError as problem:
                errors.append(f'{here}: {problem}')
        needed = [f for f in FACTS if not row[f]] + [c for c in ('label', 'label_reason', 'labeller', 'labelled_at') if not row[c]]
        if not needed:
            done += 1
        elif row['label'] or any(row[f] and f not in base['facts_prefilled'].split('; ') for f in FACTS):
            partial += 1
        if complete and needed:
            errors.append(f'{here}: incomplete, missing {needed}')
    require(not errors, f'{len(errors)} problem(s) in the labels file; first {min(len(errors), 20)}:\n  ' + '\n  '.join(errors[:20]))
    return {'seatElections': len(rows), 'complete': done, 'partlyFilled': partial, 'untouched': untouched,
            'byLabel': {k: sum(1 for r in rows if r['label'] == k) for k in LABELS_ALLOWED}}


def freeze(labels_path, labeller, attest_no_residuals, frozen_at=None, template=None):
    """Write the freeze record for a complete, valid labels file. Refuses without the no-residuals attestation."""
    require(attest_no_residuals, 'freezing requires the attestation that no model residual or error was viewed while labelling')
    rows_template = template or build_template()
    raw = Path(labels_path).read_bytes()
    rows = parse_csv(raw.decode('utf-8'))
    summary = validate_labels(rows, rows_template, complete=True)
    stamp = frozen_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    parse_time(stamp, 'frozenAt')
    overrides = sum(1 for r, t in zip(rows, rows_template) for f in FACTS if t[f] and r[f] != t[f])
    return {'schemaVersion': TEMPLATE_VERSION, 'kind': 'stage57-label-freeze', 'frozenAt': stamp, 'labeller': labeller,
            'labelsSha256': sha256_bytes(raw), 'templateSha256': sha256_text(to_csv(rows_template)),
            'seatElections': summary['seatElections'], 'byLabel': summary['byLabel'],
            'byYearExceptional': {str(y): sum(1 for r in rows if r['election_year'] == str(y) and r['label'] == 'exceptional') for y in YEARS},
            'prefilledFactsChangedByLabeller': overrides,
            'attestation': {'modelResidualsOrErrorsViewedWhileLabelling': False,
                            'outcomesKnownWhileLabelling': True,
                            'selectionBiasAcceptedByLabeller': True,
                            'ordinarySeatScaleEstimatedBeforeFreeze': False},
            'rule': 'Labels are frozen. A relabel after any scale estimate is a new, separately recorded design, never an edit.'}


def require_frozen_labels(freeze_path=None, labels_path=None):
    """Return {seatElectionId: row} only if the labels file still matches its freeze record. Estimation stages call this."""
    record_path, file_path = Path(freeze_path or ROOT / FREEZE), Path(labels_path or ROOT / LABELS)
    require(record_path.exists(), f'no label freeze record at {record_path}: labels must be frozen before any ordinary-seat scale is estimated')
    record = read_json(record_path)
    require(record.get('kind') == 'stage57-label-freeze', 'not a label freeze record')
    require(file_path.exists() and sha256_file(file_path) == record['labelsSha256'], 'labels file differs from its frozen hash: labels changed after the freeze')
    rows = parse_csv(file_path.read_text(encoding='utf-8'))
    template = build_template()
    require(sha256_text(to_csv(template)) == record['templateSha256'], 'the pre-filled template evidence changed since the freeze')
    validate_labels(rows, template, complete=True)
    return {r['seat_election_id']: r for r in rows}
