"""Structural audit safeguards exercise preserved evidence and actual feature paths."""
from copy import deepcopy
import unittest
from scripts.uncertainty_expectation import structure
from scripts.uncertainty_expectation.common import read, INVENTORY
from scripts.transport.continuous.features import source_r


class StructuralAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read(INVENTORY)
        cls.ctx = structure.evidence_context()
        cls.records = structure.continuity_inventory(cls.inventory, cls.ctx)

    def test_complete_fixed_frame_keeps_all_257_and_all_source_options(self):
        self.assertEqual(len(self.records), 257)
        self.assertEqual({r['id'] for r in self.records}, {r['targetElectorateId'] for r in self.inventory['candidateRecords']})
        for r in self.records:
            total = sum(p['incomingFraction'] for p in r['predecessors'])
            self.assertAlmostEqual(total, 1)
            self.assertAlmostEqual(r['sourceNonmajorSupportProxy'], sum(c['supportProxyContribution'] or 0 for c in r['sourceContenders']))
            self.assertTrue(all(c['ballotGroup'] not in structure.MAJOR for c in r['sourceContenders']))

    def test_actual_pipeline_target_outcome_mutation_changes_no_structural_fields(self):
        inv, ctx = deepcopy(self.inventory), deepcopy(self.ctx)
        for r in inv['candidateRecords']:
            if r['targetYear'] == 2023:
                r['actual'] = list(reversed(r['actual']))
                r['winnerId'] = 'counterfactual'
        for seat in ctx['elections'][2023]['electorates']:
            seat['winnerCandidateId'] = 'counterfactual'
            for c in seat['candidates']:
                c['votes'], c['elected'] = 99999999, not c['elected']
        self.assertEqual(structure.continuity_inventory(inv, ctx), self.records)

    def test_nonmatch_unresolved_not_departure_or_new_strength(self):
        unmatched = [c for r in self.records for c in r['sourceContenders'] if not c['acceptedTargetOccurrenceIds'] and c['documentaryDeparture'] is None]
        self.assertGreater(len(unmatched), 0)
        self.assertTrue(all(c['status'] == 'unresolved' for c in unmatched))
        self.assertTrue(all(c['newChallengerStrengthEvidence'].startswith('unavailable') for r in self.records for c in r['targets']))

    def test_dunne_documentary_event_after_actual_cutoff(self):
        facts = [c['documentaryDeparture'] for r in self.records for c in r['sourceContenders'] if c['documentaryDeparture']]
        self.assertEqual(len(facts), 1)
        f = facts[0]
        self.assertEqual(f['cutoff'], '2017-07-29')
        self.assertGreater(f['factDate'], f['cutoff'])
        self.assertIsNone(f['publicationDate'])
        self.assertEqual(f['forecastTimeStructuralClassification'], 'unresolved')

    def test_documentary_distinct_does_not_establish_departure(self):
        claim = self.ctx['distinct'][4]
        result = structure.dated_claim(claim, '2017-07-29')
        self.assertFalse(result['departureEstablished'])
        self.assertFalse(result['newChallengerStrengthEstablished'])
        self.assertEqual(result['label'], 'documentary_distinct_people')

    def test_S_can_survive_person_change_without_outgoing_R(self):
        epsom = next(r for r in self.records if r['year'] == 2014 and r['name'] == 'Epsom')
        seymour = next(c for c in epsom['targets'] if c['name'].startswith('SEYMOUR'))
        self.assertTrue(seymour['S']['SDespiteNoAcceptedPersonLink'])
        self.assertTrue(any(name and name.startswith('BANKS') for name in seymour['sourceSNames']))
        self.assertEqual(seymour['R']['supportedMass'], 0)
        self.assertTrue(seymour['R']['outgoingTransferGuardPassed'])

    def test_actual_source_R_constructor_rejects_outgoing_and_wrong_predecessor(self):
        values = read('data/processed/models/candidate-overperformance/occurrences.json')['records']
        r = next(r for r in values if r['year'] == 2011 and r['candidateContestStatus'] == 'held' and r['normalizedPremium'] is not None)
        ctx = {'residuals': {r['candidateOccurrenceId']: r}}
        edge = {'sourceElectorateId': r['electorateId'], 'sourceOccurrenceId': r['candidateOccurrenceId'],
                'sourceYear': r['year'], 'edgeId': 'synthetic-accepted', 'label': 'accepted_algorithmic_same_person', 'ruleFlags': ['exact_name']}
        value, _, _ = source_r(ctx, r['electorateId'], edge)
        self.assertEqual(value, r['normalizedPremium'])
        self.assertIsNone(source_r(ctx, r['electorateId'], None)[0])
        self.assertIsNone(source_r(ctx, 'wrong-predecessor', edge)[0])

    def test_no_changed_seat_comparators_are_manufactured(self):
        saved = read(structure.SAVED)
        row = next(r for r in self.inventory['candidateRecords'] if r['targetYear'] == 2014 and r['geography'] == 'fallback')
        result = structure.saved_comparators(row, saved)
        self.assertTrue(all(v['status'].startswith('unavailable') for v in result.values()))
        row = next(r for r in self.inventory['candidateRecords'] if r['targetYear'] == 2017)
        result = structure.saved_comparators(row, saved)
        self.assertTrue(all(v['status'] == 'saved_matching_complete_slate' for v in result.values()))


if __name__ == '__main__':
    unittest.main()
