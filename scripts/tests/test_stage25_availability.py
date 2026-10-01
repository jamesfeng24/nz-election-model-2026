"""Stage25 linked availability and pinned source dependencies."""
import copy
import unittest
from unittest.mock import patch

from scripts.checkpoints import stage25_availability as stage


class Stage25AvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = stage.build()

    def test_complete_geographic_frame_and_original_candidate_coverage(self):
        rows = self.output['records']
        self.assertEqual(len(rows), 356)
        self.assertEqual(len({r['geographyId'] for r in rows}), 356)
        years = {r['targetYear']: r for r in self.output['summary']}
        self.assertEqual([(years[y]['completeShareAvailable'], years[y]['sOnlyAvailable'])
                          for y in (2011, 2014, 2017, 2020, 2023)],
                         [(63, 63), (20, 20), (64, 64), (34, 34), (64, 64)])
        self.assertEqual(sum(r['completeShare']['status'] == 'available' for r in rows), 245)
        self.assertEqual(sum(r['scope'] == 'maori' for r in rows), 35)

    def test_model_specific_missingness_not_geographic_eligibility(self):
        rows = self.output['records']
        not_exact = [r for r in rows if r['scope'] == 'general' and not r['primaryExactGeography']]
        self.assertTrue(not_exact)
        self.assertTrue(all(r['completeShare']['status'] == 'abstain' and
                            r['partyVector']['status'] == 'abstain' for r in not_exact))
        cancelled = next(r for r in rows if r['targetElectorateId'] == 'nz-general-2023-electorate-39')
        self.assertTrue(cancelled['primaryExactGeography'])
        self.assertEqual(cancelled['completeShare']['status'], 'abstain')

    def test_outcome_and_identity_changes_do_not_change_applicability(self):
        elections = {year: copy.deepcopy(stage.read(path)) for year, path in stage.ELECTIONS.items()}
        original = self.output
        for document in elections.values():
            for seat in document['electorates']:
                seat['winnerCandidateId'] = None
                seat['validCandidateVotes'] = 99999
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['elected'] = not candidate['elected']
        links = copy.deepcopy(stage.read(stage.LINKS)['links'])
        for link in links:
            link['status'] = 'unresolved'
        changed = stage.build(elections=elections, links=links)
        def eligibility(data):
            return [(r['geographyId'], r['completeShare']['status'],
                     r['sOnly']['status'], r['partyVector']['status'],
                     tuple(p['status'] for p in r['natLab'])) for r in data['records']]
        self.assertEqual(eligibility(original), eligibility(changed))
        self.assertNotEqual(original, changed)  # Source victories and identity audit legitimately differ.

    def test_source_contract_allows_unrelated_addition_and_rejects_required_change(self):
        elections = {year: stage.read(path) for year, path in stage.ELECTIONS.items()}
        splits = {year: stage.read(path) for year, path in stage.SPLITS.items()}
        contract = stage.source_contract(elections, splits)
        live = stage.read
        registry = copy.deepcopy(live('data/sources.json'))
        registry['sources'].append({'id': 'unrelated-test', 'rawPath': 'not-consumed'})
        with patch.object(stage, 'read', side_effect=lambda p: registry if p == 'data/sources.json' else live(p)):
            stage.verify_contract(contract)
        registry['sources'][0]['organisation'] = 'altered'
        with patch.object(stage, 'read', side_effect=lambda p: registry if p == 'data/sources.json' else live(p)):
            with self.assertRaisesRegex(ValueError, 'Changed or deleted required'):
                stage.verify_contract(contract)

    def test_required_raw_bytes_and_duplicate_source_id_fail(self):
        contract = stage.read('data/processed/checkpoints/stage25-historical-geography/source-contract.json')
        live_read = stage.read
        registry = copy.deepcopy(live_read('data/sources.json'))
        registry['sources'].append(copy.deepcopy(registry['sources'][0]))
        with patch.object(stage, 'read', side_effect=lambda p: registry if p == 'data/sources.json' else live_read(p)):
            with self.assertRaisesRegex(ValueError, 'Duplicate id'):
                stage.verify_contract(contract)
        original = stage.sha256
        with patch.object(stage, 'sha256') as altered:
            altered.return_value.hexdigest.return_value = '0' * 64
            with self.assertRaisesRegex(ValueError, 'Changed required raw source'):
                stage.verify_contract(contract)


if __name__ == '__main__':
    unittest.main()
