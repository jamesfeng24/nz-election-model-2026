"""Seat-name-key audit: macron-insensitive seat identity, additive Stage 10 supplement, preserved pinned outputs."""
import unittest
from hashlib import sha256

from scripts.audits import seat_name_keys as audit


def load(name):
    return audit.read(audit.PREFIX + '/' + name)


class SeatIdentity(unittest.TestCase):
    def test_fold_ignores_case_and_diacritics_but_keeps_word_boundaries(self):
        self.assertEqual(audit.fold('Te Atatū'), audit.fold('Te Atatu'))
        self.assertEqual(audit.fold('Ōhāriu'), audit.fold('Ohariu'))
        self.assertEqual(audit.fold('Ikaroa-Rāwhiti'), 'ikaroa-rawhiti')
        self.assertNotEqual(audit.fold('Te Atatū'), 'teatatu')

    def test_spelling_families_are_the_nine_general_and_three_maori_seats(self):
        families = load('audit.json')['spellingFamilies']
        general = {f['foldedName'] for f in families if f['electorateType'] == 'general'}
        self.assertEqual(general, {'kaikoura', 'mangere', 'ohariu', 'otaki', 'rangitikei', 'tamaki', 'taupo',
                                   'te atatu', 'whangarei'})
        self.assertEqual({f['foldedName'] for f in families if f['electorateType'] == 'maori'},
                         {'ikaroa-rawhiti', 'tamaki makaurau', 'te tai hauauru'})
        whangarei = next(f for f in families if f['foldedName'] == 'whangarei')
        self.assertEqual(whangarei['spellings'], {'Whangarei': [2008, 2011, 2014, 2017], 'Whangārei': [2020, 2023]})

    def test_folded_name_is_unique_within_every_election(self):
        occurrences = audit.read(audit.OCCURRENCES)['records']
        seats = {}
        for row in occurrences:
            seats.setdefault((row['year'], row['electorateType'], audit.fold(row['electorateName'])), set()).add(row['electorateName'])
        self.assertTrue(all(len(names) == 1 for names in seats.values()))


class Stage10Supplement(unittest.TestCase):
    def test_pinned_inventory_is_untouched_and_fully_reproduced(self):
        summary = load('audit.json')['stage10']
        self.assertEqual(summary['pinnedRecordsDiffering'], 0)
        self.assertEqual((summary['pinnedRecords'], summary['foldedRecords'], summary['additionalRecords']), (1433, 1485, 52))
        pinned = audit.read(audit.INVENTORY)
        self.assertEqual(len(pinned['records']), 1433)
        # the byte hash that Stage 55's input contract pins for the Stage 10 inventory
        contract = audit.read('data/processed/replacement-effect/input-contract.json')['inputHashes']
        self.assertEqual(audit.digest(audit.INVENTORY), contract[audit.INVENTORY])

    def test_additions_are_new_events_in_the_macron_seats_and_two_are_primary_eligible(self):
        additions = load('stage10-keyed-additions.json')['records']
        pinned = {row['eventId'] for row in audit.read(audit.INVENTORY)['records']}
        self.assertTrue(all(row['eventId'] not in pinned for row in additions))
        seats = {audit.fold(row['electorateName']) for row in additions if row['electorateType'] == 'general'}
        self.assertEqual(seats, {'kaikoura', 'mangere', 'ohariu', 'otaki', 'rangitikei', 'tamaki', 'taupo', 'te atatu', 'whangarei'})
        eligible = sorted((row['sourceName'], row['electorateName'], row['sourceYear'], row['targetYear'])
                          for row in additions if row['primaryEligible'])
        self.assertEqual(eligible, [('DUNNE, Peter Francis', 'Ohariu', 2008, 2011), ('KING, Colin McDonald', 'Kaikoura', 2008, 2011)])
        self.assertEqual(load('audit.json')['stage10']['foldedPrimaryEligible'], 46)

    def test_records_use_the_source_election_spelling_and_stable_occurrence_ids(self):
        raw = {row['candidateOccurrenceId']: row['electorateName'] for row in audit.read(audit.OCCURRENCES)['records']}
        for row in load('stage10-keyed-additions.json')['records']:
            self.assertEqual(row['electorateName'], raw[row['sourceOccurrenceId']])
            self.assertEqual(row['eventId'], row['sourceOccurrenceId'] + '->' + row['targetOccurrenceId'])


class Stage8Chains(unittest.TestCase):
    def test_exact_name_chains_miss_adjacent_links_and_misflag_pairs(self):
        stage8 = load('audit.json')['stage8']
        self.assertEqual((stage8['adjacentChainLinksExact'], stage8['adjacentChainLinksFolded']), (517, 534))
        flagged = stage8['pairsFlaggedOnlyByNameSpelling']
        self.assertEqual(len(flagged), 3)
        self.assertTrue(all('different_electorate_or_scope' in row['exclusionReasons'] for row in flagged))
        self.assertEqual(sorted(row['sourceElectorate'] for row in flagged if row['primaryTransition']), ['Kaikoura', 'Ohariu'])


class Determinism(unittest.TestCase):
    def test_saved_artifacts_regenerate_and_manifest_hashes_hold(self):
        outputs = audit.build()
        for name, value in outputs.items():
            self.assertEqual((audit.ROOT / audit.PREFIX / name).read_bytes(), audit.encode(value), name)
        manifest = load('manifest.json')
        self.assertFalse(manifest['frozenOutputsChanged'])
        for name, value in outputs.items():
            self.assertEqual(manifest['outputHashes'][name], sha256(audit.encode(value)).hexdigest())
        for path, value in {**manifest['inputHashes'], **manifest['codeHashes']}.items():
            self.assertEqual(audit.digest(path), value, path)


if __name__ == '__main__':
    unittest.main()
