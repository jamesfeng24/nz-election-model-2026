"""Synthetic arithmetic and preserved-input adapter checks; no candidate fitting."""
from copy import deepcopy
from unittest.mock import patch
from statistics import mean
import unittest
import csv
import io
import xml.etree.ElementTree as ET
from scripts.diagnostics.s_r_robustness.presentation import scatter, csv_table
from scripts.models.party_vote_transform.inputs import Inputs
from scripts.models.complete_party_vector.inventory import evidence
from scripts.diagnostics.s_r_robustness import alignment, movement, statistics as stats, analysis, inventory
from scripts.diagnostics.s_r_robustness.common import *


def cats():
    return [{'categoryId': 'same', 'relationship': 'continuing', 'sourcePartyKey': 'oldlabel', 'targetPartyKey': 'renamed', 'continuityEvidence': 'synthetic_registered_rename'},
        {'categoryId': 'exit', 'relationship': 'exit', 'sourcePartyKey': 'departing', 'targetPartyKey': None, 'continuityEvidence': 'synthetic_roster'},
        {'categoryId': 'entry', 'relationship': 'entrant', 'sourcePartyKey': None, 'targetPartyKey': 'newgroup', 'continuityEvidence': 'synthetic_roster'}]


class AlignmentTests(unittest.TestCase):
    def test_rename_and_entry_exit_tv(self):
        x, y = alignment.align(cats(), {'same': .8, 'exit': .2}, {'same': .7, 'entry': .3})
        self.assertAlmostEqual(alignment.total_variation(x, y), .3)
        self.assertEqual(x['entry'], 0); self.assertEqual(y['exit'], 0)
        self.assertTrue(alignment.category_audit(cats())[0]['renamedContinuingGroup'])
    def test_pure_rename_has_no_movement(self):
        row = cats()[:1]; x, y = alignment.align(row, {'same': 1}, {'same': 1})
        self.assertEqual(alignment.total_variation(x, y), 0)
    def test_missing_evidence_is_not_zero(self):
        with self.assertRaises(ValueError): alignment.align(cats(), {'same': 1}, {'same': .7, 'entry': .3})
        with self.assertRaises(ValueError): alignment.align(cats(), {'same': .8, 'exit': .2}, {'same': 1})
    def test_duplicates_and_ambiguous_continuity_rejected(self):
        with self.assertRaises(ValueError): alignment.category_audit(cats()+cats()[:1])
        row = deepcopy(cats()); row[0]['relationship'] = 'shared_unresolved'
        with self.assertRaises(ValueError): alignment.category_audit(row)
        row = deepcopy(cats()); row[2]['targetPartyKey'] = 'renamed'
        with self.assertRaises(ValueError): alignment.category_audit(row)
    def test_true_zero_simplex_and_inconsistent_mass(self):
        x, y = alignment.align(cats(), {'same': 1, 'exit': 0}, {'same': .9, 'entry': .1})
        self.assertAlmostEqual(alignment.total_variation(x, y), .1)
        with self.assertRaises(ValueError): alignment.total_variation({'a': .4}, {'a': 1})
    def test_shared_group_not_partitioned(self):
        row = {'categoryId': 'joint', 'relationship': 'entrant', 'sourcePartyKey': None, 'targetPartyKey': 'shared', 'continuityEvidence': 'synthetic_alliance_ballot'}
        c = [cats()[0], row]
        x, y = alignment.align(c, {'same': 1}, {'same': .8, 'joint': .2})
        self.assertEqual(set(x), {'same', 'joint'}); self.assertAlmostEqual(alignment.total_variation(x, y), .2)


class SummaryTests(unittest.TestCase):
    def test_rank_ties_and_spearman(self):
        self.assertEqual(stats.ranks([10, 10, 5]), [2.5, 2.5, 1])
        self.assertAlmostEqual(stats.correlation(stats.ranks([1, 2, 3]), stats.ranks([3, 2, 1])), -1)
    def test_undefined_variation(self):
        rows = [{'movementStatus':'available', 'constructedLocalDistance': .1, 'Gpp': x} for x in (1, 2)]
        r = stats.association(rows, 'constructedLocalDistance')
        self.assertIsNone(r['spearman']); self.assertIsNone(r['slopeGainPPPer10ppMovement'])
        self.assertIsNone(stats.correlation([1], [2])); self.assertIsNone(stats.slope([], []))
    def test_centering_removes_between_environment_offset(self):
        rows = [{'targetYear': y, 'movementStatus':'available', 'constructedLocalDistance': offset+x, 'Gpp': level+2*x}
            for y, offset, level in [(1, 0, 10), (2, .5, -10)] for x in (.1, .2)]
        r = stats.centered_association(rows, 'constructedLocalDistance')
        self.assertAlmostEqual(r['slopeGainPPPer10ppMovement'], .2); self.assertAlmostEqual(r['pearson'], 1)
    def test_equal_election_not_equal_contest(self):
        rows = [{'targetYear': 1, 'movementStatus':'available', 'x': x, 'Gpp': x} for x in (0, 1)]
        rows += [{'targetYear': 2, 'movementStatus':'available', 'x': x, 'Gpp': -3*x} for x in (0, 1)]*3
        r = stats.centered_association(rows, 'x')
        self.assertAlmostEqual(r['slopeGainPPPer10ppMovement'], -.1)
        self.assertNotAlmostEqual(stats.slope([r['x'] for r in rows], [r['Gpp'] for r in rows])*.1, -.1)
    def test_population_sd_not_sample_sd(self):
        d = stats.dispersion([1, 3], [2014, 2023])
        self.assertEqual(d['populationSDPP'], 1); self.assertEqual(d['worstTargetYears'], [2023])
    def test_paired_signs_and_full_slate_denominator(self):
        ids = ['a', 'b', 'c']; actual = {'candidateShares':dict(zip(ids, [.6, .3, .1]))}
        q = {'baseline':[.4, .4, .2], S:[.5, .35, .15], R:[.45, .35, .2], JOINT:[.6, .3, .1]}
        predictions = {m:{'candidateShares':dict(zip(ids, v))} for m, v in q.items()}
        errors = analysis.errors_for(predictions, actual, ids); pairs = analysis.paired(errors)
        self.assertGreater(pairs['Gpp'], 0); self.assertGreater(pairs['Jpp'], 0)
        self.assertAlmostEqual(errors['baseline']['maePP'], 40/3)
        predictions[R]['candidateShares'].pop('c')
        with self.assertRaises(ValueError): analysis.errors_for(predictions, actual, ids)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.movement = movement.build(); cls.analysis = analysis.build()
    def test_actual_party_reader_ignores_candidate_results(self):
        original = Inputs.json
        def changed(reader, path):
            d = original(reader, path)
            if path.startswith('data/processed/elections/'):
                d = deepcopy(d)
                for seat in d['electorates']:
                    seat['winnerCandidateId'] = 'synthetic_changed_winner'
                    seat['validCandidateVotes'] = 1
                    for c in seat['candidates']:
                        c['votes'] = 999; c['winner'] = False
            return d
        with patch.object(Inputs, 'json', changed):
            self.assertEqual(movement.build(), self.movement)
    def test_outcomes_change_only_error_diagnostics(self):
        actuals = deepcopy(read(S33+'evaluation.json')['evaluationOnlyActuals'])
        cid = next(iter(next(f for f in self.analysis['folds'] if f['branch']=='primary' and f['targetYear']==2023)['records']))['targetElectorateId']
        a = actuals[cid]; ids = list(a['candidateShares']); a['candidateShares'] = dict.fromkeys(ids, 1/len(ids)); a['winnerCandidateId'] = ids[-1]
        changed = analysis.build(actuals=actuals)
        self.assertNotEqual(changed, self.analysis)
        self.assertEqual(movement.build(), self.movement)
        self.assertEqual([(f['foldId'], [r['targetElectorateId'] for r in f['records']]) for f in changed['folds']],
                         [(f['foldId'], [r['targetElectorateId'] for r in f['records']]) for f in self.analysis['folds']])
    def test_saved_four_model_samples_and_no_fit(self):
        data = inventory.build(); fitted = [f for f in data['sampleManifest'] if f['branch']=='primary']
        self.assertEqual(sum(len(f['commonFittedIds']) for f in fitted), 182)
        for f in data['sampleManifest']:
            if f['targetYear']==2011 or f['branch']=='separated' and f['targetYear']==2014:
                self.assertFalse(f['commonFittedIds'])
    def test_diagnostic_exclusion_does_not_remove_performance(self):
        d = deepcopy(self.movement); cid = next(r['targetElectorateId'] for r in d['records'] if r['targetYear']==2023 and r['status']=='available')
        r = next(r for r in d['records'] if r['targetElectorateId']==cid); r.update(status='diagnostic_exclusion', diagnosticExclusion='synthetic_missing_source_row')
        changed = analysis.build(movement=d)
        f = next(f for f in changed['folds'] if f['branch']=='primary' and f['targetYear']==2023)
        old = next(f for f in self.analysis['folds'] if f['branch']=='primary' and f['targetYear']==2023)
        self.assertEqual(f['methods'], old['methods']); self.assertEqual(f['contests'], 64)
        self.assertEqual(f['associations']['constructedLocalDistance']['excludedContests'], 1)
    def test_all_distances_can_be_unavailable(self):
        d = deepcopy(self.movement)
        for r in d['records']:
            if r['status']=='available': r.update(status='diagnostic_exclusion', diagnosticExclusion='synthetic_unavailable')
        result = analysis.build(movement=d)
        b = next(b for b in result['branches'] if b['branch']=='primary')
        self.assertIsNone(b['withinElectionCentered']['constructedLocalDistance']['pearson'])
        self.assertTrue(all(r['meanPartyInputMAEpp'] is None for r in b['environmentRows']))
    def test_geography_join_and_party_denominator_rejection(self):
        data = read(S31+'input-inventory.json'); f = next(r for r in data['partyFrame'] if r['partyInputStatus']=='available')
        vector = next(r for r in read(S31+'party-vectors.json')['records'] if r['targetElectorateId']==f['targetElectorateId'])
        audit = next(a for a in local('inventory.json')['categoryAudit'] if a['targetYear']==f['targetYear'])
        geo = next(r for r in read(GEO+'geography.json')['records'] if r['geographyId']==f['geographyId']); changed = deepcopy(geo); changed['dominantPredecessorId']='wrong'
        with self.assertRaises(ValueError): movement.contest_record(f, vector, audit, evidence()[0], changed)
        with self.assertRaises(ValueError): movement.shares({'validVotes': 99, 'parties': {'x': {'votes':100, 'share':1}}})
    def test_readable_plots_and_flat_table_keep_all_rows(self):
        svg = ET.fromstring(scatter(self.analysis['folds'], 'constructedLocalDistance'))
        self.assertEqual(len(svg.findall('.//{http://www.w3.org/2000/svg}circle')), 182)
        rows = list(csv.DictReader(io.StringIO(csv_table(self.analysis['folds']))))
        self.assertEqual(len(rows), sum(len(f['records']) for f in self.analysis['folds']))
        self.assertEqual(len({(r['branch'], r['contest_id']) for r in rows}), len(rows))
    def test_winner_flags_alone_cannot_change_errors(self):
        actuals = deepcopy(read(S33+'evaluation.json')['evaluationOnlyActuals'])
        for a in actuals.values(): a['winnerCandidateId']='synthetic_changed_flag'
        self.assertEqual(analysis.build(actuals=actuals), self.analysis)
    def test_R_supported_and_unsupported_groups_reconcile(self):
        for b in self.analysis['branches']:
            folds = [f for f in self.analysis['folds'] if f['branch']==b['branch']]
            self.assertEqual(sum(r['candidates'] for r in b['Rgroups'].values()), sum(f['candidates'] for f in folds))
    def test_determinism_provenance_preservation(self):
        self.assertEqual(movement.build(), self.movement); self.assertEqual(analysis.build(), self.analysis)
        verify_inputs(); self.assertEqual(preserve(), 1447)
        with patch('scripts.diagnostics.s_r_robustness.common.digest', return_value='corrupt'):
            with self.assertRaises(ValueError): verify_inputs()


if __name__ == '__main__':
    unittest.main()
