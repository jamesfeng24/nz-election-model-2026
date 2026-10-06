"""Stage56: adjustment files, the model + James layer and the Stage57 labelling tools. Synthetic draws are labelled and stay in tests."""
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.manual_adjustment import layer, replay, schema, run
from scripts.manual_adjustment.common import ROOT, AdjustmentError, canonical, read_json, sha256_text

SEATS = sorted(schema.seat_frame()['general'])
SEAT = SEATS[0]
T0, T1, T2 = '2026-10-10T09:00:00+13:00', '2026-10-12T09:00:00+13:00', '2026-10-20T09:00:00+13:00'
EXPIRY = '2026-10-18T09:00:00+13:00'
SYNTHETIC_GROUPS = ['nationalparty', 'labourparty', 'actnewzealand', 'other']


def synthetic_draws(n=4000, seed=7):
    """SYNTHETIC logistic-normal candidate shares around 0.42/0.38/0.12/0.08; never an application result."""
    rng = np.random.default_rng(seed)
    z = np.log([0.42, 0.38, 0.12, 0.08]) + rng.normal(0, [0.12, 0.12, 0.2, 0.2], size=(n, 4))
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def forecast(draws=None):
    draws = synthetic_draws() if draws is None else draws
    return {'schemaVersion': 1, 'kind': 'automatic-seat-forecast', 'forecastId': 'synthetic-test-forecast', 'electionId': 'nz-general-2026',
            'synthetic': True, 'seats': [{'electorateId': s, 'groups': SYNTHETIC_GROUPS, 'draws': draws.tolist()} for s in SEATS[:3]]}


def fields(adjustment=..., flag=True, **over):
    shares = dict(zip(SYNTHETIC_GROUPS, synthetic_draws().mean(axis=0).round(4)))
    shares['other'] = round(1 - sum(v for k, v in shares.items() if k != 'other'), 4)
    base = {'author': 'James', 'recordedAt': T0, 'expiresAt': EXPIRY, 'reason': 'Sitting MP retired late; local reports of a strong rival',
            'sources': [{'description': 'Synthetic test source', 'date': '2026-10-09', 'url': None}],
            'exceptionalSeat': {'flag': flag, 'reason': 'New strong challenger announced' if flag else None},
            'adjustment': {'target': {'kind': 'nl_balance'}, 'meanShiftPp': 3.0, 'extraSdPp': 1.5} if adjustment is ... else adjustment,
            'unadjusted': {'forecastId': 'synthetic-test-forecast', 'snapshotSha256': 'a' * 64, 'candidateShares': shares}}
    base.update(over)
    return base


def document(**over):
    return schema.new_entry(None, SEAT, fields(**over))


class AdjustmentFileTests(unittest.TestCase):
    def test_valid_entry_validates_and_chains(self):
        doc = document()
        second = schema.new_entry(doc, SEAT, fields(recordedAt=T1, supersedes=doc['entries'][0]['entryId'],
                                                    adjustment={'target': {'kind': 'party_share', 'partyKey': 'actnewzealand'}, 'meanShiftPp': -1.0, 'extraSdPp': 0.0}))
        self.assertEqual(second['entries'][1]['previousDigest'], second['entries'][0]['digest'])
        self.assertEqual(len(second['entries']), 2)
        self.assertEqual(len(doc['entries']), 1)  # input not modified

    def test_edit_after_the_fact_is_detected(self):
        doc = document()
        doc['entries'][0]['reason'] = 'Quietly rewritten after the fact'
        with self.assertRaisesRegex(AdjustmentError, 'digest mismatch'):
            schema.validate_file(doc)

    def test_unknown_or_missing_fields_fail_and_no_way_to_reduce_uncertainty(self):
        doc = document()
        for edit in ({'sdMultiplier': 0.8}, {'extraSdPp': -1}):
            broken = copy.deepcopy(doc)
            if 'sdMultiplier' in edit:
                broken['entries'][0]['adjustment'].update(edit)
            else:
                broken['entries'][0]['adjustment']['extraSdPp'] = -1
            with self.assertRaises(AdjustmentError):
                schema.validate_file(broken)
        with self.assertRaisesRegex(AdjustmentError, r'extraSdPp must be >= 0'):
            document(adjustment={'target': {'kind': 'nl_balance'}, 'meanShiftPp': 1.0, 'extraSdPp': -0.1})
        with self.assertRaisesRegex(AdjustmentError, 'unknown fields'):
            document(adjustment={'target': {'kind': 'nl_balance'}, 'meanShiftPp': 1.0, 'extraSdPp': 0.0, 'sdMultiplier': 0.8})

    def test_invalid_entries_fail_loudly(self):
        cases = [
            ({'recordedAt': '2026-10-10T09:00:00'}, 'explicit UTC offset'),
            ({'expiresAt': T0}, 'after recordedAt'),
            ({'reason': 'two\nlines of text here'}, 'one line'),
            ({'reason': 'short'}, '10 to 300'),
            ({'sources': []}, 'at least one dated source'),
            ({'sources': [{'description': 'x', 'date': '9 Oct', 'url': None}]}, 'YYYY-MM-DD'),
            ({'exceptionalSeat': {'flag': True, 'reason': None}}, 'string'),
            ({'adjustment': {'target': {'kind': 'nl_balance'}, 'meanShiftPp': 0.0, 'extraSdPp': 0.0}}, 'changes nothing'),
            ({'adjustment': {'target': {'kind': 'nl_balance'}, 'meanShiftPp': 30.0, 'extraSdPp': 0.0}}, '<= 25'),
            ({'adjustment': {'target': {'kind': 'party_share', 'partyKey': 'madeuppartykey'}, 'meanShiftPp': 1.0, 'extraSdPp': 0.0}}, 'not a 2026 party'),
            ({'adjustment': {'target': {'kind': 'median_shift'}, 'meanShiftPp': 1.0, 'extraSdPp': 0.0}}, 'kind'),
            ({'adjustment': {'target': {'kind': 'nl_balance'}, 'meanShiftPp': 1.0, 'extraSdPp': float('nan')}}, 'finite'),
            ({'adjustment': {'target': {'kind': 'nl_balance'}, 'meanShiftPp': True, 'extraSdPp': 0.0}}, 'finite number'),
        ]
        for over, message in cases:
            with self.subTest(over=over), self.assertRaisesRegex(AdjustmentError, message):
                document(**over)

    def test_shift_cannot_exceed_the_recorded_shares(self):
        low = fields()
        low['unadjusted']['candidateShares'] = {'nationalparty': 0.5, 'labourparty': 0.1, 'actnewzealand': 0.2, 'other': 0.2}
        low['adjustment'] = {'target': {'kind': 'nl_balance'}, 'meanShiftPp': 12.0, 'extraSdPp': 0.0}
        with self.assertRaisesRegex(AdjustmentError, 'below zero'):
            schema.new_entry(None, SEAT, low)
        low['adjustment'] = {'target': {'kind': 'party_share', 'partyKey': 'actnewzealand'}, 'meanShiftPp': -21.0, 'extraSdPp': 0.0}
        with self.assertRaisesRegex(AdjustmentError, 'outside 0-100%'):
            schema.new_entry(None, SEAT, low)

    def test_a_mean_shift_requires_the_exceptional_flag(self):
        with self.assertRaisesRegex(AdjustmentError, 'not ordinary'):
            document(flag=False)
        flag_only = document(adjustment={'target': {'kind': 'nl_balance'}, 'meanShiftPp': 0.0, 'extraSdPp': 2.0}, flag=False)
        self.assertEqual(flag_only['entries'][0]['exceptionalSeat']['flag'], False)  # extra uncertainty alone may leave a seat unflagged

    def test_unadjusted_forecast_must_be_complete(self):
        bad = fields()
        bad['unadjusted']['candidateShares']['other'] += 0.2
        with self.assertRaisesRegex(AdjustmentError, 'sum to 1'):
            schema.new_entry(None, SEAT, bad)
        bad = fields()
        bad['unadjusted']['snapshotSha256'] = 'xyz'
        with self.assertRaisesRegex(AdjustmentError, 'SHA-256'):
            schema.new_entry(None, SEAT, bad)

    def test_seat_must_be_a_general_2026_electorate_and_maori_seats_are_refused(self):
        frame = schema.seat_frame()
        self.assertEqual((len(frame['general']), len(frame['maori'])), (64, 7))
        maori = sorted(frame['maori'])[0]
        with self.assertRaisesRegex(AdjustmentError, 'Māori electorate'):
            schema.new_entry(None, maori, fields())
        with self.assertRaisesRegex(AdjustmentError, 'not a 2026 general electorate'):
            schema.new_entry(None, 'nz-general-2026-boundary-999', fields())
        self.assertTrue({schema.NATIONAL_KEY, schema.LABOUR_KEY} <= schema.party_keys())

    def test_history_is_append_only_with_explicit_supersession(self):
        doc = document()
        with self.assertRaisesRegex(AdjustmentError, 'must supersede'):
            schema.new_entry(doc, SEAT, fields(recordedAt=T1))  # entry 1 is still active
        with self.assertRaisesRegex(AdjustmentError, 'later than the previous entry'):
            schema.new_entry(doc, SEAT, fields(recordedAt='2026-10-09T09:00:00+13:00', supersedes=doc['entries'][0]['entryId']))
        with self.assertRaisesRegex(AdjustmentError, 'earlier entry'):
            schema.new_entry(doc, SEAT, fields(recordedAt=T1, supersedes='nope#009'))
        later = schema.new_entry(doc, SEAT, fields(recordedAt=T1, supersedes=doc['entries'][0]['entryId']))
        with self.assertRaisesRegex(AdjustmentError, 'already superseded'):
            schema.new_entry(later, SEAT, fields(recordedAt=T2, expiresAt='2026-10-30T09:00:00+13:00', supersedes=later['entries'][0]['entryId']))
        # an expired entry needs no supersession
        after_expiry = schema.new_entry(doc, SEAT, fields(recordedAt=T2, expiresAt='2026-10-30T09:00:00+13:00'))
        self.assertEqual(len(after_expiry['entries']), 2)

    def test_active_entry_respects_recording_time_expiry_and_supersession(self):
        doc = document()
        doc = schema.new_entry(doc, SEAT, fields(recordedAt=T1, supersedes=doc['entries'][0]['entryId'],
                                                 adjustment={'target': {'kind': 'nl_balance'}, 'meanShiftPp': -2.0, 'extraSdPp': 1.0}))
        pick = lambda when: (schema.active_entry(doc, when) or {}).get('entryId')
        self.assertIsNone(pick('2026-10-09T00:00:00+13:00'))
        self.assertEqual(pick('2026-10-11T00:00:00+13:00'), f'{SEAT}#001')
        self.assertEqual(pick('2026-10-13T00:00:00+13:00'), f'{SEAT}#002')
        self.assertIsNone(pick('2026-10-19T00:00:00+13:00'))

    def test_directory_loader_checks_names_and_validates_every_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = schema.seat_path(SEAT, root)
            path.parent.mkdir(parents=True)
            path.write_text(canonical(document()), encoding='utf-8')
            self.assertEqual(list(schema.load_directory(root)), [SEAT])
            (path.parent / (SEATS[1] + '.json')).write_text(canonical(document()), encoding='utf-8')
            with self.assertRaisesRegex(AdjustmentError, 'file name must equal'):
                schema.load_directory(root)

    def test_repo_adjustment_directory_is_empty_or_valid(self):
        schema.load_directory()  # no real adjustment exists yet; any later file must validate


class LayerTests(unittest.TestCase):
    def apply(self, adjustment, draws=None):
        base = synthetic_draws() if draws is None else draws
        seat = {'electorateId': SEAT, 'groups': SYNTHETIC_GROUPS, 'draws': base.tolist()}
        return base, layer.adjust_seat(seat, adjustment)

    def test_nl_shift_moves_the_national_mean_exactly_and_preserves_everything_else(self):
        base, (new, report) = self.apply({'target': {'kind': 'nl_balance'}, 'meanShiftPp': 3.0, 'extraSdPp': 0.0})
        self.assertAlmostEqual(100 * (new[:, 0].mean() - base[:, 0].mean()), 3.0, places=7)
        self.assertAlmostEqual(100 * (new[:, 1].mean() - base[:, 1].mean()), -3.0, places=7)
        np.testing.assert_allclose(new[:, 0] + new[:, 1], base[:, 0] + base[:, 1], atol=1e-12)
        np.testing.assert_array_equal(new[:, 2:], base[:, 2:])
        np.testing.assert_allclose(new.sum(axis=1), 1.0, atol=1e-12)
        self.assertAlmostEqual(report['coordinate']['sdAfter'], report['coordinate']['sdBefore'], places=12)  # shift alone, same coordinate sd

    def test_extra_uncertainty_adds_in_quadrature_and_a_shift_alone_never_narrows(self):
        for shift in (-9.0, -3.0, 0.0, 3.0, 9.0):
            for extra in (0.0, 1.0, 4.0):
                if shift == 0 and extra == 0:
                    continue
                with self.subTest(shift=shift, extra=extra):
                    _, (_, report) = self.apply({'target': {'kind': 'nl_balance'}, 'meanShiftPp': shift, 'extraSdPp': extra})
                    c = report['coordinate']
                    self.assertGreaterEqual(c['sdAfter'], c['sdBefore'] - 1e-12)
                    self.assertAlmostEqual(c['sdAfter'], c['sdExpected'], places=9)

    def test_party_share_shift_rescales_the_others_proportionally(self):
        base, (new, report) = self.apply({'target': {'kind': 'party_share', 'partyKey': 'actnewzealand'}, 'meanShiftPp': 2.0, 'extraSdPp': 1.0})
        self.assertAlmostEqual(100 * (new[:, 2].mean() - base[:, 2].mean()), 2.0, places=7)
        ratio = new[:, [0, 1, 3]] / base[:, [0, 1, 3]]
        np.testing.assert_allclose(ratio[:, 0], ratio[:, 1], rtol=1e-12)
        np.testing.assert_allclose(ratio[:, 0], ratio[:, 2], rtol=1e-12)
        np.testing.assert_allclose(new.sum(axis=1), 1.0, atol=1e-12)
        self.assertGreaterEqual(report['coordinate']['sdAfter'], report['coordinate']['sdBefore'])

    def test_infeasible_or_degenerate_requests_fail(self):
        with self.assertRaisesRegex(AdjustmentError, 'not reachable'):
            self.apply({'target': {'kind': 'party_share', 'partyKey': 'actnewzealand'}, 'meanShiftPp': -25.0, 'extraSdPp': 0.0})
        with self.assertRaisesRegex(AdjustmentError, 'exactly once'):
            seat = {'electorateId': SEAT, 'groups': ['nationalparty', 'nationalparty', 'actnewzealand', 'other'], 'draws': synthetic_draws().tolist()}
            layer.adjust_seat(seat, {'target': {'kind': 'nl_balance'}, 'meanShiftPp': 1.0, 'extraSdPp': 0.0})
        bad = synthetic_draws()
        bad[0, 0] += 0.1
        with self.assertRaisesRegex(AdjustmentError, 'summing to 1'):
            self.apply({'target': {'kind': 'nl_balance'}, 'meanShiftPp': 1.0, 'extraSdPp': 0.0}, bad)
        flat = np.tile([0.4, 0.4, 0.1, 0.1], (10, 1))
        with self.assertRaisesRegex(AdjustmentError, 'zero spread'):
            self.apply({'target': {'kind': 'nl_balance'}, 'meanShiftPp': 1.0, 'extraSdPp': 1.0}, flat)

    def test_layer_leaves_the_automatic_forecast_untouched_and_keeps_both_outputs(self):
        auto = forecast()
        before = sha256_text(canonical(auto))
        doc = document()
        out = layer.apply_layer(auto, {SEAT: doc}, '2026-10-11T00:00:00+13:00')
        self.assertEqual(sha256_text(canonical(auto)), before)
        self.assertEqual(out['automaticSha256'], before)
        self.assertEqual(out['exceptionalSeats'], [SEAT])
        self.assertEqual([a['entryId'] for a in out['adjustedSeats']], [f'{SEAT}#001'])
        by_id = {s['electorateId']: s for s in out['seats']}
        self.assertNotEqual(by_id[SEAT]['draws'], auto['seats'][0]['draws'])
        for seat in auto['seats'][1:]:  # seats without an entry are byte-identical copies
            self.assertEqual(by_id[seat['electorateId']], seat)
        self.assertAlmostEqual(by_id[SEAT]['adjustment']['report']['achievedMeanShiftPp'], 3.0, places=7)

    def test_entries_outside_their_dates_and_flag_only_entries(self):
        auto = forecast()
        doc = document()
        for when in ('2026-10-09T00:00:00+13:00', '2026-10-19T00:00:00+13:00'):
            out = layer.apply_layer(auto, {SEAT: doc}, when)
            self.assertEqual(out['seats'], auto['seats'])
            self.assertEqual(out['adjustedSeats'], [])
        flag = schema.new_entry(None, SEAT, fields(adjustment=None))
        out = layer.apply_layer(auto, {SEAT: flag}, '2026-10-11T00:00:00+13:00')
        self.assertEqual(out['exceptionalSeats'], [SEAT])
        self.assertEqual(out['seats'][0]['draws'], auto['seats'][0]['draws'])  # flag-only: distribution unchanged

    def test_adjustment_for_a_seat_missing_from_the_forecast_fails(self):
        auto = forecast()
        auto['seats'] = auto['seats'][1:]
        with self.assertRaisesRegex(AdjustmentError, 'absent from the automatic forecast'):
            layer.apply_layer(auto, {SEAT: document()}, '2026-10-11T00:00:00+13:00')

    def test_drift_is_reported_against_the_recorded_automatic_shares(self):
        out = layer.apply_layer(forecast(), {SEAT: document()}, '2026-10-11T00:00:00+13:00')
        drift = out['adjustedSeats'][0]['automaticDriftSinceEntryPp']
        self.assertLess(max(abs(v) for v in drift.values()), 0.01)  # recorded shares were rounded to 4 decimals of the same draws

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'entry.json').write_text(json.dumps(fields()), encoding='utf-8')
            (tmp / 'auto.json').write_text(canonical(forecast()), encoding='utf-8')
            root = str(tmp / 'adjustments')
            self.assertEqual(run.main(['add-adjustment', '--seat', SEAT, '--entry', str(tmp / 'entry.json'), '--root', root]), 0)
            self.assertEqual(run.main(['validate-adjustments', '--root', root]), 0)
            self.assertEqual(run.main(['apply', '--forecast', str(tmp / 'auto.json'), '--as-of', '2026-10-11T00:00:00+13:00',
                                       '--out', str(tmp / 'out.json'), '--root', root]), 0)
            self.assertEqual(read_json(tmp / 'out.json')['kind'], 'model-plus-james-seat-forecast')
            maori = sorted(schema.seat_frame()['maori'])[0]
            (tmp / 'bad.json').write_text(json.dumps(fields()), encoding='utf-8')
            self.assertEqual(run.main(['add-adjustment', '--seat', maori, '--entry', str(tmp / 'bad.json'), '--root', root]), 1)


class LabellingTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = replay.build_template()
        cls.reads = list(replay.READ_LOG)

    def test_universe_is_every_general_seat_election_2014_to_2023(self):
        self.assertEqual(len(self.rows), 257)
        self.assertEqual({y: sum(1 for r in self.rows if r['election_year'] == str(y)) for y in replay.YEARS}, {2014: 64, 2017: 64, 2020: 65, 2023: 64})
        inventory = read_json(ROOT / 'data/processed/uncertainty/inventory.json')
        self.assertEqual({r['seat_election_id'] for r in self.rows}, {r['targetElectorateId'] for r in inventory['candidateRecords']})
        maori = {'Hauraki-Waikato', 'Ikaroa-Rāwhiti', 'Tāmaki Makaurau', 'Te Tai Hauāuru', 'Te Tai Tokerau', 'Te Tai Tonga', 'Waiariki'}
        self.assertFalse(maori & {r['electorate'] for r in self.rows})  # Māori seats are out of scope, filtered by electorate type
        self.assertEqual(len({r['seat_election_id'] for r in self.rows}), 257)

    def test_committed_template_and_manifest_regenerate_exactly(self):
        text = replay.to_csv(self.rows)
        self.assertEqual((ROOT / replay.TEMPLATE).read_text(encoding='utf-8'), text)
        self.assertEqual(read_json(ROOT / replay.TEMPLATE_MANIFEST), replay.template_manifest(self.rows))
        self.assertEqual(replay.template_manifest(self.rows)['templateSha256'], sha256_text(text))

    def test_view_is_blind_to_model_output_and_results(self):
        self.assertTrue(set(self.reads) <= set(replay.INPUT_FAMILIES), sorted(set(self.reads) - set(replay.INPUT_FAMILIES)))
        for column in replay.COLUMNS:
            self.assertFalse([t for t in replay.FORBIDDEN_TOKENS if t in column], column)
        with self.assertRaisesRegex(AdjustmentError, 'allow-list'):
            replay.check_blind(['seat_election_id', 'balance_residual'])
        text = replay.to_csv(self.rows)
        for forbidden in ('Stage47', 'Stage48', 'CRPS', 'sigma', 'residual'):
            self.assertNotIn(forbidden, text)

    def test_prefilled_facts_follow_the_repo_evidence(self):
        inventory = read_json(ROOT / 'data/processed/uncertainty/inventory.json')['candidateRecords']
        exact = sum(1 for r in inventory if r['geography'] == 'exact')
        self.assertEqual(sum(1 for r in self.rows if r['boundary_change'] == 'no'), exact)
        self.assertEqual(sum(1 for r in self.rows if r['boundary_change'] == 'yes'), 257 - exact)
        by_electorate = {(r['election_year'], r['electorate']): r for r in self.rows}
        self.assertEqual(by_electorate[('2014', 'Bay of Plenty')]['candidate_change'], 'yes')  # Ryall retired, Muller succeeded
        self.assertIn('retirement', by_electorate[('2014', 'Bay of Plenty')]['candidate_change_evidence'])
        self.assertEqual(by_electorate[('2014', 'Auckland Central')]['candidate_change'], 'no')
        for row in self.rows:
            for fact in replay.FACTS:
                self.assertEqual(bool(row[fact]), fact in row['facts_prefilled'].split('; ') if row['facts_prefilled'] else not row[fact])
                if row[fact] == 'yes':
                    self.assertTrue(row[fact + '_reason'])
            self.assertEqual(row['label'] + row['label_reason'] + row['labeller'] + row['labelled_at'], '')  # James fills the label
        self.assertTrue(any(r['scandal'] == 'yes' for r in self.rows))
        self.assertTrue(all(not r['tactical_arrangement'] and not r['new_strong_challenger'] and not r['other'] for r in self.rows))


def complete_rows(rows, label=None):
    """SYNTHETIC filled labels for tests: answers every blank fact 'no' and labels each seat."""
    out = []
    for r in rows:
        r = dict(r)
        for fact in replay.FACTS:
            r[fact] = r[fact] or 'no'
        yes = any(r[f] == 'yes' for f in replay.FACTS)
        r['label'] = label or ('exceptional' if yes else 'ordinary')
        r['label_reason'] = 'Test reason that is long enough'
        r['labeller'], r['labelled_at'] = 'James', '2026-10-10T20:00:00+13:00'
        out.append(r)
    return out


class LabelValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = replay.build_template()
        cls.filled = complete_rows(cls.template)

    def test_complete_labels_validate_and_the_template_itself_is_valid_but_incomplete(self):
        summary = replay.validate_labels(self.filled, self.template, complete=True)
        self.assertEqual(summary['complete'], 257)
        self.assertEqual(sum(summary['byLabel'].values()), 257)
        blank = replay.validate_labels(self.template, self.template)
        self.assertEqual(blank['complete'], 0)
        self.assertEqual(blank['untouched'], 257)
        with self.assertRaisesRegex(AdjustmentError, 'incomplete'):
            replay.validate_labels(self.template, self.template, complete=True)

    def mutate(self, index, **over):
        rows = [dict(r) for r in self.filled]
        rows[index].update(over)
        return rows

    def test_every_rule_fails_loudly(self):
        plain = next(i for i, r in enumerate(self.filled) if r['label'] == 'ordinary' and all(r[f] == 'no' for f in replay.FACTS))
        cases = [
            (dict(label='exceptional'), 'at least one checklist fact'),
            (dict(label='maybe'), 'ordinary or exceptional'),
            (dict(label_reason=''), 'one-line reason'),
            (dict(label_reason='short'), 'one-line reason'),
            (dict(scandal='yes'), 'needs a one-line reason'),
            (dict(scandal='unknown'), 'yes or no'),
            (dict(other='yes', other_reason='two\nlines'), 'one line'),
            (dict(labelled_at='yesterday'), 'ISO 8601'),
            (dict(labelled_at='2026-10-10T20:00:00'), 'UTC offset'),
            (dict(electorate='Renamed'), 'read-only column electorate'),
            (dict(previous_election_winner='Someone else'), 'read-only column previous_election_winner'),
            (dict(labeller=''), 'incomplete'),
        ]
        for over, message in cases:
            with self.subTest(over=over), self.assertRaisesRegex(AdjustmentError, message):
                replay.validate_labels(self.mutate(plain, **over), self.template, complete=True)
        with self.assertRaisesRegex(AdjustmentError, 'template order'):
            replay.validate_labels(self.filled[::-1], self.template)

    def test_csv_header_must_match_exactly(self):
        text = replay.to_csv(self.filled)
        self.assertEqual(len(replay.parse_csv(text)), 257)
        with self.assertRaisesRegex(AdjustmentError, 'header must match'):
            replay.parse_csv(text.replace('label_reason', 'label_residual', 1))
        extra = io.StringIO()
        writer = csv.writer(extra, lineterminator='\n')
        writer.writerow(list(replay.COLUMNS) + ['model_residual'])
        with self.assertRaisesRegex(AdjustmentError, 'header must match'):
            replay.parse_csv(extra.getvalue())


class FreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = replay.build_template()
        cls.filled = complete_rows(cls.template)

    def write(self, directory, rows=None):
        path = Path(directory) / 'labels.csv'
        path.write_text(replay.to_csv(rows or self.filled), encoding='utf-8', newline='')
        return path

    def test_freeze_needs_attestation_and_complete_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp)
            with self.assertRaisesRegex(AdjustmentError, 'attestation'):
                replay.freeze(path, 'James', False, template=self.template)
            partial = self.write(tmp, [dict(self.filled[0])] + [dict(r) for r in self.template[1:]])
            with self.assertRaisesRegex(AdjustmentError, 'incomplete'):
                replay.freeze(partial, 'James', True, template=self.template)

    def test_freeze_record_pins_the_labels_and_detects_later_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp)
            record = replay.freeze(path, 'James', True, frozen_at='2026-10-11T10:00:00+13:00', template=self.template)
            self.assertEqual(record['seatElections'], 257)
            self.assertFalse(record['attestation']['modelResidualsOrErrorsViewedWhileLabelling'])
            self.assertTrue(record['attestation']['outcomesKnownWhileLabelling'])
            self.assertFalse(record['attestation']['ordinarySeatScaleEstimatedBeforeFreeze'])
            freeze_path = Path(tmp) / 'freeze.json'
            freeze_path.write_text(canonical(record), encoding='utf-8')
            self.assertEqual(len(replay.require_frozen_labels(freeze_path, path)), 257)
            changed = [dict(r) for r in self.filled]
            changed[0]['label'] = 'exceptional' if changed[0]['label'] == 'ordinary' else 'ordinary'
            self.write(tmp, changed)
            with self.assertRaisesRegex(AdjustmentError, 'changed after the freeze'):
                replay.require_frozen_labels(freeze_path, path)
            with self.assertRaisesRegex(AdjustmentError, 'no label freeze record'):
                replay.require_frozen_labels(Path(tmp) / 'absent.json', path)

    def test_estimation_cannot_read_labels_that_are_not_frozen(self):
        if not (ROOT / replay.FREEZE).exists():
            with self.assertRaisesRegex(AdjustmentError, 'no label freeze record'):
                replay.require_frozen_labels()


if __name__ == '__main__':
    unittest.main()
