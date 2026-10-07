"""Stage72: 2026 scales by the frozen Stage45 rule, the live nowcast config and the fail-closed D107 classification."""
import copy
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


class Config(unittest.TestCase):
    def setUp(self):
        self.config = read(V.CONFIG)

    def test_live_config_is_valid_with_explicit_pending_fields(self):
        pending = V.check_config(self.config)
        self.assertIn('release.policyApprovedBy', pending)
        self.assertIn('roster.snapshotId', pending)
        with self.assertRaises(V.ConfigError):
            V.check_config(self.config, require_complete=True)

    def test_config_rejects_forecast_semantics_and_other_multipliers(self):
        for edit in (lambda c: c.update(estimand='forecast'),
                     lambda c: c['national'].update(stateKey='electionDay'),
                     lambda c: c['national'].update(forbiddenStateKeys=[]),
                     lambda c: c['uncertainty'].update(candidateBalanceSeatMultiplier={'ordinary': 0.79, 'exceptional': 1.0}),
                     lambda c: c['uncertainty'].update(candidateBalanceSeatMultiplier={'ordinary': 0.60, 'exceptional': 1.5}),
                     lambda c: c.update(intervalLevels=[0.9]),
                     lambda c: c['national'].update(modelStateAsOf='2026-10-07'),
                     lambda c: c['roster'].update(snapshotId='set-while-pending')):
            config = copy.deepcopy(self.config); edit(config)
            with self.assertRaises(V.ConfigError):
                V.check_config(config)


class Classification(unittest.TestCase):
    def test_a_complete_classification_passes(self):
        result = V.check_classification(synthetic_classification(), stage56_exceptional=[GENERAL[0]])
        self.assertEqual(len(result), 64)

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
