"""Stage79: seat-poll update on the candidate National/Labour balance. Pure formulas, the transcription, the leave-one-out
scoring and the assembly hook. Assembly tests use SYNTHETIC slates over the real 2026 ids; no bank here is a forecast."""
import copy
import unittest
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.manual_adjustment.schema import seat_frame
from scripts.nowcast_assembly import assemble as A, general, national, streams, summaries
from scripts.nowcast_assembly.common import CONFIG, read
from scripts.nowcast_config.validate import check_config, ConfigError
from scripts.seat_polls import apply as seat_apply, data, historical, live, model, run, score
from scripts.seat_polls.common import DESIGN, PREFIX, parameters
from scripts.uncertainty_revision.coordinates import mean_logit_location

GENERAL = sorted(seat_frame()['general'])
MAORI = sorted(seat_frame()['maori'])
DESIGN_DOC = read(DESIGN)


class Contract(unittest.TestCase):
    def test_frozen_numbers_parse_from_the_contract(self):
        self.assertEqual(parameters(DESIGN_DOC), {'cap': 0.6, 'halfLifeWeeks': 6.0, 'gainNats': 1.0, 'coverageBand': [0.65, 0.95], 'later': 1.5, 'mergeDays': 14})
        self.assertIn('frozen before', DESIGN_DOC['status'])


class Isolation(unittest.TestCase):
    def test_the_live_path_never_imports_the_historical_flags(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        for name in ('live', 'apply', 'readout', 'data', 'model', 'common'):
            text = (root / 'scripts/seat_polls' / f'{name}.py').read_text(encoding='utf-8')
            self.assertNotRegex(text, r'import[^\n]*\bhistorical\b|from \.historical|seat_polls\.historical|\bhistorical\.', name)
            self.assertNotIn('exceptional-balance-scale', text, name)
        assemble = (root / 'scripts/nowcast_assembly/assemble.py').read_text(encoding='utf-8')
        self.assertNotIn('seat_polls.historical', assemble)


class Formulas(unittest.TestCase):
    def test_uncapped_update_is_the_precision_weighted_posterior(self):
        centre, var, w = model.update(0.0, 0.09, 0.01, 1.0, 0.09, 1.0, 1.0)
        self.assertAlmostEqual(w, 0.5)
        self.assertAlmostEqual(centre, 0.5)
        self.assertAlmostEqual(var, 0.045)

    def test_cap_decay_and_floor(self):
        _, _, w = model.update(0, 0.09, 0.01, 1, 0.001, 1.0, 0.6)
        self.assertAlmostEqual(w, 0.6)
        centre, var, _ = model.update(0.2, 0.09, 0.01, 1.0, 0.09, 0.0, 0.6)
        self.assertAlmostEqual(centre, 0.2)
        self.assertAlmostEqual(var, 0.09)
        _, var, _ = model.update(0, 0.04, 0.0327, 1, 0.001, 1.0, 0.6)
        self.assertGreaterEqual(var, 0.0327)
        self.assertAlmostEqual(model.age_factor(6, 6), 0.5)
        self.assertEqual(model.age_factor(-3, 6), 1.0)

    def test_decayed_variance_is_the_stationary_ar1_posterior(self):
        sigma2, s2, rho = 0.09, 0.05, 0.5
        w = sigma2 / (sigma2 + s2)
        _, var, _ = model.update(0, sigma2, 0.0, 0.3, s2, rho, 1.0)
        self.assertAlmostEqual(var, sigma2 * (1 - rho ** 2 * w))

    def test_eligibility_uses_the_polls_top_two(self):
        self.assertTrue(model.eligible({'NAT': 44, 'LAB': 21, 'NZF': 18}))
        self.assertTrue(model.eligible({'LAB': 33, 'NAT': 32, 'GRN': 14}))
        self.assertFalse(model.eligible({'GRN': 29, 'LAB': 29, 'NAT': 15}))
        self.assertFalse(model.eligible({'NAT': 30, 'GRN': 25, 'LAB': 23}))
        self.assertFalse(model.eligible({'NAT': 30, 'LAB': 25, 'GRN': 25}))
        self.assertFalse(model.eligible({'NAT': 40, 'ACT': 38}))

    def test_merge_inflates_the_later_poll(self):
        y, v = model.merge_same_source([(0.0, 0.04), (1.0, 0.04)], 1.5)
        self.assertAlmostEqual(v, 1 / (1 / 0.04 + 1 / 0.06))
        self.assertAlmostEqual(y, v * (0 / 0.04 + 1 / 0.06))

    def test_logit_normal_mean_inverts_the_location(self):
        p = np.array([0.1, 0.4, 0.5, 0.8])
        for sd in (0.2, 0.35):
            loc = mean_logit_location(p, sd)
            self.assertTrue(np.allclose(model.logit_normal_mean(loc, sd), p, atol=1e-9))


class Transcription(unittest.TestCase):
    def test_every_number_is_in_the_preserved_tables_and_a_change_is_caught(self):
        rows = data.polls()
        data.verify_transcription(rows)
        bad = copy.deepcopy(rows)
        bad[0]['candidateVotePct']['NAT'] = 31
        with self.assertRaises(ValueError):
            data.verify_transcription(bad)

    def test_inventory_and_eligibility(self):
        units = historical.historical_units(DESIGN_DOC)
        self.assertEqual(len(units), 14)
        self.assertTrue(all(u['status'] == 'ok' for u in units))
        eligible = [u for u in units if u['eligible']]
        self.assertEqual((len(eligible), len({u['seatElection'] for u in eligible})), (9, 7))
        self.assertFalse(any(u['election'] == 2014 for u in units))
        northland = next(u for u in units if u['id'].startswith('2020:Northland'))
        self.assertAlmostEqual(northland['value'], np.log(46 / 31))
        self.assertAlmostEqual(northland['actual'], np.log(37.74 / 38.11), delta=0.01)


class Scoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        units = historical.historical_units(DESIGN_DOC)
        cls.eligible = [u for u in units if u['eligible']]
        cls.arm = score.run_arm(cls.eligible, cls.eligible, DESIGN_DOC)

    def test_inflation_never_sees_the_held_out_seat_election(self):
        napier = [r for r in self.arm['records'] if r['seatElection'] == '2023:Napier']
        self.assertEqual(len(napier), 2)
        self.assertEqual(napier[0]['inflation'], napier[1]['inflation'])
        pool = [u for u in self.eligible if u['seatElection'] != '2023:Napier']
        expected = model.fit_inflation([u['value'] - u['actual'] for u in pool], [u['samplingVariance'] for u in pool])
        self.assertAlmostEqual(napier[0]['inflation'], expected)
        everything = model.fit_inflation([u['value'] - u['actual'] for u in self.eligible], [u['samplingVariance'] for u in self.eligible])
        self.assertNotAlmostEqual(napier[0]['inflation'], everything)

    def test_finding_follows_the_frozen_rule(self):
        decision = score.decide(self.arm, DESIGN_DOC)
        self.assertEqual(decision['finding'], 'adopt' if decision['gainMet'] and decision['coverageMet'] else 'not_established')
        stored = read(PREFIX + '/findings.json')
        self.assertEqual(stored['decisions']['primary']['finding'], decision['finding'])
        self.assertEqual(stored['summary']['finding'], decision['finding'])
        self.assertGreaterEqual(min(r['inflation'] for r in self.arm['records']), 1.0)

    def test_saved_artifacts_reproduce(self):
        for name, value in run.build().items():
            self.assertTrue(equivalent(read(PREFIX + '/' + name), value, 1e-9), name)
        self.assertTrue(equivalent(read(PREFIX + '/manifest.json'), run.manifest(list(run.build())), 1e-9))


class Live(unittest.TestCase):
    def test_eligible_seats_merge_and_age(self):
        inputs = live.inputs('2026-10-07')
        ids = live.seat_ids()
        self.assertEqual(sorted(inputs), sorted(ids[k] for k in ('huttsouth', 'kapiti', 'mtalbert', 'waitaki', 'westcoasttasman')))
        mt_albert = inputs[ids['mtalbert']]
        self.assertEqual(len(mt_albert['pollIds']), 2)
        self.assertAlmostEqual(mt_albert['ageWeeks'], 2 / 7)
        self.assertAlmostEqual(inputs[ids['kapiti']]['rho'], 0.5 ** (68 / 7 / 6))
        self.assertNotIn(ids['aucklandcentral'], inputs)
        self.assertEqual(sorted(live.inputs('2026-09-01')), [ids['kapiti']])

    def test_undefined_cases_fail_closed(self):
        rows = copy.deepcopy(data.polls())
        two = [r for r in rows if r['electorate'] == 'Mt Albert' and r['election'] == 2026]
        two[1]['pollster'] = 'Another'
        with self.assertRaises(ValueError):
            live.inputs('2026-10-07', rows=rows)
        rows = copy.deepcopy(data.polls())
        two = [r for r in rows if r['electorate'] == 'Mt Albert' and r['election'] == 2026]
        two[1]['fieldworkStart'] = '2026-12-01'
        with self.assertRaises(ValueError):
            live.inputs('2026-12-31', rows=rows)


def slate(seat):
    return [{'id': f'synthetic-{seat}-{i}', 'group': g, 'name': f'Synthetic candidate {i}', 'S': 0.0, 'R': 0.0}
            for i, g in enumerate(('nationalparty', 'labourparty', 'greenparty', None))]


class Apply(unittest.TestCase):
    def test_the_unchanged_inversion_recovers_the_shifted_location_and_sd(self):
        rng = np.random.default_rng(79)
        shared, seat = 0.18, 0.30
        scales = {'balance': {'shared': shared, 'seat': seat}}
        candidate = {'groups': ['national', 'labour', 'other', 'other']}
        p = rng.uniform(0.2, 0.7, 50)
        b = np.column_stack([0.8 * p, 0.8 * (1 - p), np.full(50, 0.1), np.full(50, 0.1)])
        poll = {'value': 0.5, 'variance': 0.07, 'rho': 0.8, 'cap': 0.6, 'ageWeeks': 2.0, 'pollIds': ['x']}
        out, new_scales, record = seat_apply.apply(b, candidate, scales, 0.6, poll)
        total = (shared ** 2 + (seat * 0.6) ** 2) ** 0.5
        before = mean_logit_location(p, total)
        after_sd = record['posteriorSD']
        new_p = out[:, 0] / (out[:, 0] + out[:, 1])
        self.assertTrue(np.allclose(mean_logit_location(new_p, after_sd), before + record['shift'], atol=1e-8))
        self.assertTrue(np.allclose(out[:, 0] + out[:, 1], 0.8) and np.allclose(out[:, 2:], b[:, 2:]))
        self.assertAlmostEqual(np.hypot(shared, new_scales['balance']['seat'] * 0.6), after_sd)
        self.assertGreaterEqual(after_sd, shared)
        with self.assertRaises(ValueError):
            seat_apply.apply(b[:, [0, 2, 3]], {'groups': ['national', 'other', 'other']}, scales, 0.6, poll)

    def test_a_polled_seat_moves_only_its_balance(self):
        c = copy.deepcopy(read(CONFIG))
        draws, _, groups = national.load(c, 256)
        keys, national2023, base = general.baseline(c)
        continuing = general.relationships(c)
        fine = general.fine_national(draws, groups, keys, national2023, continuing)
        parameters_, _ = general.fold_parameters(c)
        scales = read(c['uncertainty']['scales'])['layers']
        seat_id = GENERAL[3]
        party = general.party_row(seat_id, keys, base[seat_id], national2023, continuing)
        candidate = general.candidate_row(seat_id, slate(seat_id), party, parameters_)
        poll = {'value': 0.9, 'variance': 0.06, 'rho': 1.0, 'cap': 0.6, 'ageWeeks': 0.0, 'pollIds': ['t']}
        with streams.substituted([party, candidate], 256, 'synthetic-test'):
            _, plain, none = general.simulate_with_poll(party, candidate, fine, scales['local_party']['scales'], scales['candidate']['scales'], 1.0, None)
            _, polled, record = general.simulate_with_poll(party, candidate, fine, scales['local_party']['scales'], scales['candidate']['scales'], 1.0, poll)
        self.assertIsNone(none)
        self.assertTrue(np.allclose(plain[:, 2:], polled[:, 2:], atol=1e-12))
        self.assertTrue(np.allclose(plain[:, 0] + plain[:, 1], polled[:, 0] + polled[:, 1], atol=1e-12))
        moved = np.mean(np.log(polled[:, 0] / polled[:, 1]) - np.log(plain[:, 0] / plain[:, 1]))
        self.assertAlmostEqual(moved, record['shift'], delta=0.06)
        self.assertGreater(record['shift'], 0.05)


class Switch(unittest.TestCase):
    def test_config_switch_is_fail_closed(self):
        c = copy.deepcopy(read(CONFIG))
        self.assertEqual(c['seatPolls'], {'enabled': True, 'decision': 'D117'})  # James switched it on (D117)
        self.assertIn('D117', c['decisions'])
        check_config(c)
        c.pop('seatPolls')
        check_config(c)
        for bad in ({'enabled': 'yes', 'decision': 'D117'}, {'enabled': True}, {'enabled': True, 'decision': 'D117', 'x': 1}):
            d = copy.deepcopy(c)
            d['seatPolls'] = bad
            with self.assertRaises(ConfigError):
                check_config(d)
        d = copy.deepcopy(c)
        d['seatPolls'] = {'enabled': True, 'decision': 'D117'}
        self.assertEqual(read(PREFIX + '/findings.json')['summary']['finding'], 'adopt')
        check_config(d)

    def test_enabled_bank_changes_only_polled_seats(self):
        c = copy.deepcopy(read(CONFIG))
        c.pop('seatPolls')
        slates = {s: slate(s) for s in GENERAL}
        classes = {s: 'exceptional' if i % 8 == 0 else 'ordinary' for i, s in enumerate(GENERAL)}
        maori = {s: {'status': 'simulated', 'class': 'maori-layer', 'source': 'synthetic-test', 'candidates': ['a', 'b'], 'candidateNames': ['A', 'B'],
                     'candidateParty': ['labourparty', 'tepatimaori'], 'candidateShares': summaries.share_summaries(['a', 'b'], np.array([[0.6, 0.4]] * 8)),
                     'winners': [0] * 8} for s in MAORI}
        off = A.assemble(c, 8, slates=slates, classification=classes, maori_records=maori)
        c['seatPolls'] = {'enabled': True, 'decision': 'D117'}
        on = A.assemble(c, 8, slates=slates, classification=classes, maori_records=maori)
        polled = set(live.inputs(c['national']['dataCutoff']))
        self.assertTrue(polled)
        for a, b in zip(off['seats'], on['seats']):
            if a['electorateId'] in polled:
                self.assertIn('seatPoll', b)
                self.assertNotIn('seatPoll', a)
            else:
                self.assertEqual(a, b)
        self.assertEqual(off['partyVote'], on['partyVote'])


if __name__ == '__main__':
    unittest.main()
