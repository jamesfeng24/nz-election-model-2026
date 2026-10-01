"""Stage22 outcome-blind shared-group amendment and exact-sample checks."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.checkpoints import stage22_prefit as prefit
from scripts.checkpoints.stage22_mapping import amend_inventory, apply_group
from scripts.checkpoints.complete_share_features import build_feature_inventory
from scripts.validate.source_files import verify_source_files


class Stage22PrefitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = prefit.read(prefit.ORIGINAL_MAPPING)
        cls.overlay = prefit.read(prefit.OVERLAY)
        cls.elections = {year: prefit.read(path) for year, path in prefit.ELECTIONS.items()}

    def test_exact_amended_population_and_no_alliance_continuity(self):
        outputs = prefit.build()
        changes = outputs['coverage-differences.json']['differences']
        summary = outputs['amended-features.json']['summary']
        self.assertEqual(len(changes['newlyAdmittedContestIds']), 20)
        self.assertEqual(len(changes['newlyAdmittedCandidateOccurrenceIds']), 147)
        self.assertEqual(len(changes['correctedExistingCandidateInputs']), 6)
        self.assertTrue(all(row['oldTargetPartySupport'] == 0 and
                            row['newTargetPartySupport'] > 0
                            for row in changes['correctedExistingCandidateInputs']))
        self.assertEqual([summary[str(y)]['constructedContests'] for y in (2011, 2017, 2023)],
                         [63, 64, 64])
        self.assertEqual([summary[str(y)]['constructedCandidates'] for y in (2011, 2017, 2023)],
                         [423, 431, 459])
        self.assertEqual([summary[str(y)]['withS'] for y in (2011, 2017, 2023)],
                         [280, 285, 271])
        self.assertEqual(outputs['coverage-differences.json']['mappingsByYear']['2014'],
                         {'single_local_destination': 26})
        self.assertEqual(outputs['coverage-differences.json']['mappingsByYear']['2023'],
                         {'cancelled_unchanged': 1, 'single_local_destination': 26})
        self.assertEqual(outputs['coverage-differences.json']['continuityAudit']
                         ['eligibleSharedSourceContinuities'], [])
        self.assertTrue(outputs['amended-design-audit.json']['allFittingGatesPass'])

    def test_single_group_share_once_and_no_group_remains_distinct(self):
        mapping, _ = amend_inventory(self.old, self.overlay, self.elections)
        training = next(r for r in mapping['trainingGeneralContests']
                        if r['year'] == 2023 and r['electorateId'] ==
                        'nz-general-2023-electorate-09')
        assigned = [c for c in training['candidates'] if c['partyKey'] == 'freedomsnz']
        self.assertEqual(len(assigned), 1)
        self.assertFalse(assigned[0]['noRegisteredPartyGroup'])
        self.assertNotEqual(assigned[0]['sourcePartyKey'], assigned[0]['partyKey'])
        self.assertTrue(any(c['noRegisteredPartyGroup'] for c in training['candidates']))
        features = prefit.build()['amended-features.json']
        seat = next(r for r in features['records'] if r['targetElectorateId'] ==
                    'nz-general-2023-electorate-09')
        candidate = next(c for c in seat['candidates'] if c['targetPartyKey'] == 'freedomsnz')
        party = next(p for p in self.elections[2023]['electorates'][8]['parties']
                     if p['partyKey'] == 'freedomsnz')
        self.assertAlmostEqual(candidate['targetPartySupport'],
                               party['votes'] / self.elections[2023]['electorates'][8]
                               ['validPartyVotes'])
        self.assertIsNone(candidate['s0Reported'])
        self.assertIn('documented_party_category_entry', candidate['fallbackReasons'])

    def test_zero_and_multiple_destinations_and_conflicts(self):
        record = next(r for r in self.overlay['records'] if r['held'])
        source = next(r for r in self.old['trainingGeneralContests']
                      if r['year'] == record['year'] and r['electorateId'] == record['electorateId'])
        seat = next(r for r in self.elections[record['year']]['electorates']
                    if r['id'] == record['electorateId'])
        empty = deepcopy(record)
        empty['candidates'] = []
        empty['candidateCountInGroup'] = 0
        self.assertEqual(apply_group(deepcopy(source), seat, empty), 'no_local_destination')
        duplicate = deepcopy(record)
        duplicate['candidates'].append(deepcopy(duplicate['candidates'][0]))
        duplicate['candidateCountInGroup'] = 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            apply_group(deepcopy(source), seat, duplicate)
        second = deepcopy(source)
        second_candidate = next(c for c in second['candidates']
                                if c['candidateOccurrenceId'] !=
                                record['candidates'][0]['candidateOccurrenceId'])
        second_candidate['partyKey'] = None
        multiple = deepcopy(record)
        multiple['candidates'].append({
            'candidateOccurrenceId': second_candidate['candidateOccurrenceId'],
            'sourcePartyKey': second_candidate['sourcePartyKey'],
            'sourceAffiliation': second_candidate['sourceAffiliation']})
        multiple['candidateCountInGroup'] = 2
        self.assertEqual(apply_group(second, seat, multiple),
                         'multiple_destinations_abstain')
        self.assertEqual(second['status'], 'ambiguous_mapping')
        changed = deepcopy(record)
        changed['sharedPartyVotes'] += 1
        with self.assertRaisesRegex(ValueError, 'changed'):
            apply_group(deepcopy(source), seat, changed)

    def test_target_outcomes_and_person_labels_do_not_change_actual_adapter(self):
        mapping, _ = amend_inventory(self.old, self.overlay, self.elections)
        frame = prefit.read(prefit.FRAME)
        splits = {year: prefit.read(path) for year, path in prefit.SPLITS.items()}
        continuity = prefit.read(prefit.CONTINUITY)['records']
        before = build_feature_inventory(frame, mapping, self.elections, splits, continuity)
        changed = deepcopy(self.elections)
        for year in (2011, 2017, 2023):
            for seat in changed[year]['electorates']:
                for candidate in seat['candidates']:
                    candidate['votes'] = 0
                    candidate['winner'] = not candidate.get('winner', False)
                    candidate['personId'] = 'synthetic changed identity'
        after = build_feature_inventory(frame, mapping, changed, splits, continuity)
        self.assertEqual(before, after)

    def test_required_source_registry_contract(self):
        registry = prefit.read('data/sources.json')
        parents = (prefit.read(prefit.STAGE20_SOURCES),
                   prefit.read(prefit.STAGE21_SOURCES))
        snapshot = prefit.source_contract(registry, parents)
        appended = deepcopy(registry)
        appended['sources'].append({'id': 'synthetic-unrelated-source'})
        self.assertEqual(snapshot, prefit.source_contract(appended, parents))
        altered = deepcopy(registry)
        required = snapshot['sources'][0]['id']
        next(r for r in altered['sources'] if r['id'] == required)['limitations'] = ['altered']
        with self.assertRaisesRegex(ValueError, 'Changed or missing'):
            prefit.source_contract(altered, parents)
        deleted = deepcopy(registry)
        deleted['sources'] = [r for r in deleted['sources'] if r['id'] != required]
        with self.assertRaisesRegex(ValueError, 'Changed or missing'):
            prefit.source_contract(deleted, parents)
        ambiguous = deepcopy(registry)
        ambiguous['sources'].append(deepcopy(ambiguous['sources'][0]))
        with self.assertRaisesRegex(ValueError, 'Ambiguous live'):
            prefit.source_contract(ambiguous, parents)
        with TemporaryDirectory() as directory:
            selected = snapshot['sources'][0]
            path = Path(directory) / selected['rawPath']
            path.parent.mkdir(parents=True)
            path.write_bytes(b'synthetic altered source')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                verify_source_files(Path(directory), {'schemaVersion': 1,
                                                      'sources': [selected]})


if __name__ == '__main__':
    unittest.main()
