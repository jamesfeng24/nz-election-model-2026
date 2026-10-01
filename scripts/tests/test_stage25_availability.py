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
        self.assertEqual(sum(r['splitTicket'].get('supportedMatchedCategories', 0)
                             for r in rows if r['targetYear'] == 2014), 99)
        self.assertTrue(all(r['identityEvidence']['crossElectionRelation'] == 'not_adjudicated_here'
                            for r in rows))
        relationships = {r['relationshipId']: r for r in self.output['partyCategoryRelationships']}
        self.assertEqual(len(relationships), 5)
        self.assertEqual(len(relationships['2011-2014']['categories']), 15)
        self.assertEqual(len(relationships['2017-2020']['categories']), 17)
        self.assertTrue(all(r['partyVector']['categoryRelationshipId'] in relationships
                            for r in rows if r['partyVector']['status'] ==
                            'source_and_target_party_categories_present'))
        for row in rows:
            if row['scope'] == 'general':
                self.assertEqual(sum(row['identityEvidence']['inheritedTargetStatusCounts'].values()),
                                 len(row['candidateOccurrenceIds']))
                self.assertLessEqual(row['identityEvidence']['targetLeftCensoredCount'],
                                     len(row['candidateOccurrenceIds']))

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

    def test_target_local_party_votes_do_not_select_same_holdout(self):
        elections = {year: copy.deepcopy(stage.read(path)) for year, path in stage.ELECTIONS.items()}
        for seat in elections[2020]['electorates']:
            seat['validPartyVotes'] = 123456
            for party in seat['parties']:
                party['votes'] = 0
                party['share'] = 0
        mutated = stage.build(elections=elections)
        def selected(data):
            return [(r['geographyId'], r['completeShare']['status'], r['sOnly']['status'],
                     r['partyVector']['status'], tuple(p['status'] for p in r['natLab']))
                    for r in data['records'] if r['targetYear'] == 2020]
        self.assertEqual(selected(self.output), selected(mutated))

    def test_target_and_later_candidate_outcomes_cannot_change_2020_features(self):
        elections = {year: copy.deepcopy(stage.read(path)) for year, path in stage.ELECTIONS.items()}
        for year in (2020, 2023):
            for seat in elections[year]['electorates']:
                seat['winnerCandidateId'] = None
                seat['validCandidateVotes'] = 88888
                for candidate in seat['candidates']:
                    candidate['votes'] = 777
                    candidate['elected'] = not candidate['elected']
        changed = stage.build(elections=elections)
        earlier = [r for r in self.output['records'] if r['targetYear'] == 2020]
        later = [r for r in changed['records'] if r['targetYear'] == 2020]
        self.assertEqual(earlier, later)

    def test_ambiguous_mapping_and_missing_or_zero_split_are_distinct(self):
        seat = stage.read(stage.ELECTIONS[2014])['electorates'][0]
        roster = {p['partyKey'] for s in stage.read(stage.ELECTIONS[2014])['electorates']
                  for p in s['parties']}
        mapping = copy.deepcopy(stage.read(stage.MAPPING)['trainingGeneralContests'][126])
        self.assertEqual(mapping['year'], 2014)
        self.assertEqual(mapping['electorateId'], seat['id'])
        accepted, reason = stage.target_candidates(mapping, seat, roster)
        self.assertIsNotNone(accepted)
        self.assertIsNone(reason)
        omitted_zero_row = copy.deepcopy(seat)
        omitted_zero_row['parties'] = [p for p in omitted_zero_row['parties']
                                       if p['partyKey'] != 'nationalparty']
        accepted, reason = stage.target_candidates(mapping, omitted_zero_row, roster)
        self.assertIsNotNone(accepted)
        self.assertIsNone(reason)  # Ballot-group membership is not a local vote outcome.
        mapping['candidates'][0]['partyKey'] = 'not_a_ballot_group'
        accepted, reason = stage.target_candidates(mapping, seat, roster)
        self.assertIsNone(accepted)
        self.assertEqual(reason, 'missing_or_duplicate_target_party_group')
        candidate = next(c for c in stage.read(stage.MAPPING)['trainingGeneralContests'][126]['candidates']
                         if c['partyKey'] == 'nationalparty')
        source_seat = stage.read(stage.ELECTIONS[2011])['electorates'][0]
        source_matrix = stage.read(stage.SPLITS[2011])['matrices'][0]
        relation = next(r for r in stage.read(stage.CONTINUITY)['records']
                        if r['sourceYear'] == 2011 and r['targetYear'] == 2014 and
                        (r.get('target') or {}).get('sourceKey') == 'nationalparty')
        continuity = {(2011, 2014, 'nationalparty'): relation}
        missing = stage.source_feature(candidate, source_seat, None, continuity, 2011, 2014)
        self.assertEqual((missing['sStatus'], missing['vStatus']),
                         ('missing_source_split_table', 'supported_source_gap'))
        zero_seat, zero_matrix = copy.deepcopy(source_seat), copy.deepcopy(source_matrix)
        next(p for p in zero_seat['parties'] if p['partyKey'] == 'nationalparty')['votes'] = 0
        next(r for r in zero_matrix['rows'] if r['partyLabel'] == 'National Party')['totalPartyVotes'] = 0
        zero = stage.source_feature(candidate, zero_seat, zero_matrix, continuity, 2011, 2014)
        self.assertEqual((zero['sStatus'], zero['vStatus']),
                         ('zero_mass_source_row', 'supported_source_gap'))

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
