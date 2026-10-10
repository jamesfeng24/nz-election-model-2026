"""Stage72: 2026 scales by the frozen Stage45 rule, the live nowcast config and the fail-closed D107 classification."""
import copy
import datetime
import unittest
from scripts.balance_scale.common import equivalent
from scripts.manual_adjustment.schema import seat_frame
from scripts.nowcast_config import scales, validate as V
from scripts.uncertainty_revision.common import read

GENERAL = sorted(seat_frame()['general'])


def synthetic_classification():
    """SYNTHETIC TEST FIXTURE: an invented classification over the real 2026 general seat ids; never a real input."""
    seats = [{'electorateId': s, 'class': 'ordinary', 'reason': 'synthetic test fixture, not a judgement', 'sources': [],
              'author': 'synthetic-test', 'recordedAt': '2026-10-07', 'extraSdOptIn': False} for s in GENERAL]
    seats[0].update({'class': 'exceptional', 'sources': ['synthetic-source']})
    return {'schemaVersion': 1, 'asOf': '2026-10-07', 'seats': seats}


class Scales2026(unittest.TestCase):
    def test_scales_reproduce_and_equal_the_stage45_all_election_fit(self):
        saved = read(scales.OUTPUT)
        self.assertTrue(equivalent(saved, scales.build(), 1e-12))
        self.assertEqual(saved['layers']['candidate']['trainingYears'], [2014, 2017, 2020, 2023])
        self.assertEqual(saved['layers']['local_party']['trainingYears'], [2011, 2014, 2017, 2020, 2023])

    def test_d107_changes_only_the_candidate_seat_balance_scale(self):
        by_class = read(scales.OUTPUT)['candidateBalanceByClass']
        self.assertAlmostEqual(by_class['ordinary']['seat'], 0.60 * by_class['exceptional']['seat'], places=12)
        self.assertEqual(by_class['ordinary']['shared'], by_class['exceptional']['shared'])
        self.assertEqual(by_class['exceptional']['multiplier'], 1.0)

    def test_d121_changes_only_the_candidate_within_scales(self):
        saved = read(scales.OUTPUT)
        within = saved['layers']['candidate']['scales']['within']
        by_class = saved['candidateWithinByClass']
        for part in ('seat', 'shared'):
            self.assertAlmostEqual(by_class['ordinary'][part], 0.55 * within[part], places=12)
            self.assertEqual(by_class['exceptional'][part], within[part])
        mass = saved['layers']['candidate']['scales']['mass']
        for part in ('seat', 'shared'):
            self.assertAlmostEqual(saved['candidateMassByClass']['ordinary'][part], 0.91 * mass[part], places=12)
            self.assertEqual(saved['candidateMassByClass']['exceptional'][part], mass[part])
        self.assertEqual(saved['layers']['candidate']['scales']['balance'], read(scales.STAGE45)['descriptive']['candidate']['scales']['balance'])


class Config(unittest.TestCase):
    def setUp(self):
        self.config = read(V.CONFIG)

    def test_live_config_is_valid_with_explicit_pending_fields(self):
        self.assertEqual(V.check_config(self.config), [])   # Stage80 registered the last pending field
        self.assertEqual(V.check_config(self.config, require_complete=True), [])
        self.assertEqual(self.config['roster']['snapshotId'], 'nz-2026-official-nominations-2026-10-10')   # Stage50 part 2
        self.assertEqual(self.config['maori']['unpolledFallbackModel'], 'stage78-f')   # Stage80 / D118: Stage78 arm F, James 2026-10-09
        pending = copy.deepcopy(self.config)
        pending['roster']['snapshotId'] = None
        pending['pending'] = {'roster.snapshotId': 'test'}
        self.assertEqual(V.check_config(pending), ['roster.snapshotId'])
        with self.assertRaises(V.ConfigError):
            V.check_config(pending, require_complete=True)

    def test_fallback_model_is_registered_or_explicitly_pending(self):
        for edit in (lambda c: c['maori'].update(unpolledFallbackModel='stage78-fc'),       # not a registered model
                     lambda c: c['maori'].update(unpolledFallbackModel=None),               # null but not listed as pending
                     lambda c: c['maori'].update(unpolledSeats='withhold')):                # a model needs the labelled-fallback decision
            broken = copy.deepcopy(self.config); edit(broken)
            with self.assertRaises(V.ConfigError):
                V.check_config(broken)
        pending = copy.deepcopy(self.config)
        pending['maori']['unpolledFallbackModel'] = None
        pending['pending'] = {'maori.unpolledFallbackModel': 'test'}
        self.assertEqual(V.check_config(pending), ['maori.unpolledFallbackModel'])

    def test_release_policy_is_recorded_as_james_decided(self):
        """D114 (James, 2026-10-07): no calibration label or staleness windows, internal reconciliation gate, MCSE 0.01."""
        config = self.config
        release = config['release']
        self.assertEqual(release['policyApprovedBy'], 'James, 2026-10-07 (D114)')
        self.assertEqual(release['probabilityMcseMax'], 0.01)
        self.assertNotIn('staleDays', release)
        self.assertEqual(config['mmp']['rulesVersion'], 'electoral-act-1993-2026-01-01')
        self.assertEqual(config['maori']['unpolledSeats'], 'labelled-fallback')
        self.assertEqual(config['maori']['presentation'], 'labelled-range')
        broken = copy.deepcopy(config); broken['maori']['unpolledSeats'] = 'guess'
        with self.assertRaises(V.ConfigError):
            V.check_config(broken)

    def test_config_rejects_forecast_semantics_and_other_multipliers(self):
        for edit in (lambda c: c.update(estimand='forecast'),
                     lambda c: c['national'].update(stateKey='electionDay'),
                     lambda c: c['national'].update(forbiddenStateKeys=[]),
                     lambda c: c['uncertainty'].update(candidateBalanceSeatMultiplier={'ordinary': 0.79, 'exceptional': 1.0}),
                     lambda c: c['uncertainty'].update(candidateBalanceSeatMultiplier={'ordinary': 0.60, 'exceptional': 1.5}),
                     lambda c: c['uncertainty'].update(candidateWithinSeatMultiplier={'ordinary': 0.80, 'exceptional': 1.0}),
                     lambda c: c['uncertainty'].update(candidateWithinSeatMultiplier={'ordinary': 0.55, 'exceptional': 0.9}),
                     lambda c: c['uncertainty'].update(candidateMassSeatMultiplier={'ordinary': 0.75, 'exceptional': 1.0}),
                     lambda c: c['uncertainty'].update(candidateMassSeatMultiplier={'ordinary': 0.91, 'exceptional': 0.9}),
                     lambda c: c.update(intervalLevels=[0.9]),
                     lambda c: c['national'].update(modelStateAsOf=(datetime.date.fromisoformat(c['national']['dataCutoff']) + datetime.timedelta(days=1)).isoformat()),   # state dated after the cutoff
                     lambda c: c['roster'].update(snapshotId=None),   # null roster without a pending entry
                     lambda c: c['candidate'].update(features='data/processed/nominations-2026/missing.json')):
            config = copy.deepcopy(self.config); edit(config)
            with self.assertRaises(V.ConfigError):
                V.check_config(config)


class Classification(unittest.TestCase):
    def test_a_complete_classification_passes(self):
        result = V.check_classification(synthetic_classification(), stage56_exceptional=[GENERAL[0]])
        self.assertEqual(len(result), 64)

    def test_the_recorded_2026_classification_is_valid_and_pinned(self):
        document = read('config/general-seat-classification-2026.json')
        result = V.check_classification(document)
        self.assertEqual(set(result), set(GENERAL))
        self.assertTrue(all(e['author'] == 'James' and e['recordedAt'] == '2026-10-10' and not e['extraSdOptIn'] for e in document['seats']))
        exceptional = sorted(seat[-3:] for seat, kind in result.items() if kind == 'exceptional')
        self.assertEqual(exceptional, ['001', '010', '011', '020', '025', '033', '037', '038', '047', '058', '059', '063', '064'])

    def test_every_gap_or_conflict_fails_closed(self):
        def broken(edit):
            doc = synthetic_classification(); edit(doc); return doc
        cases = [
            broken(lambda d: d['seats'].pop()),                                        # missing seat: never defaults to 0.60
            broken(lambda d: d['seats'].append(dict(d['seats'][1]))),                  # duplicate
            broken(lambda d: d['seats'][1].update(electorateId='nz-maori-2026-boundary-1')),  # not a general seat
            broken(lambda d: d['seats'][1].update(**{'class': 'tbd'})),
            broken(lambda d: d['seats'][1].update(**{'class': 'exceptional'})),         # exceptional without a source
            broken(lambda d: d['seats'][1].update(extraSdOptIn=True)),                  # opt-in only for exceptional
            broken(lambda d: d['seats'][1].update(reason='')),
            broken(lambda d: d['seats'][1].pop('author')),
            broken(lambda d: d.update(asOf='soon')),
        ]
        for doc in cases:
            with self.assertRaises(V.ConfigError):
                V.check_classification(doc)
        with self.assertRaises(V.ConfigError):  # a Stage56 exceptional flag must be exceptional here
            V.check_classification(synthetic_classification(), stage56_exceptional=[GENERAL[1]])


if __name__ == '__main__':
    unittest.main()
