"""Stage64 test: 2026 electorate set, old-to-new mapping, national reconciliation of the notional baseline and the cross-check."""
import unittest
from collections import Counter

from scripts.electorate_baseline import build
from scripts.electorate_baseline.common import ARTICLE, PREFIX, REGISTRY, ROOT, SHEET, digest, equivalent, read, verify


def load(name):
    return read(PREFIX + '/' + name)


class Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regenerated = build.outputs()

    def test_saved_artifacts_are_deterministic_regeneration(self):
        verify()
        for name, value in self.regenerated.items():
            self.assertTrue(equivalent(load(name), value), name)

    def test_manifest_pins_derived_artifacts(self):
        manifest = load('manifest.json')
        for path, expected in manifest['derivedArtifacts'].items():
            self.assertEqual(digest(path), expected, path)
        self.assertFalse(manifest['dataSourcesJsonTouched'])
        self.assertFalse(manifest['modelOrScaleChanged'])


class ElectorateSet(unittest.TestCase):
    register = load('register.json')['targets']

    def test_counts_and_ids(self):
        scopes = Counter(r['scope'] for r in self.register)
        self.assertEqual((scopes['general'], scopes['maori'], len(self.register)), (64, 7, 71))
        ids = [r['targetElectorateId'] for r in self.register]
        self.assertEqual(len(set(ids)), 71)
        self.assertEqual(sum(1 for i in ids if i.startswith('nz-general-2026-boundary-')), 64)
        self.assertEqual(sum(1 for i in ids if i.startswith('nz-maori-2026-boundary-')), 7)

    def test_official_roster_and_quota(self):
        roster = build.schedule()
        self.assertEqual(Counter(r['island'] for r in roster), {'N': 48, 'S': 16, 'M': 7})
        self.assertTrue(all(r['withinTolerance'] for r in roster))
        names = {(r['scope'], r['code'], build.nfc(r['name'])) for r in roster}
        self.assertEqual(names, {(r['scope'], r['boundaryCode'], build.nfc(r['name'])) for r in self.register})
        self.assertTrue(all(r['populationControlMatchesScheduleC'] for r in self.register))

    def test_every_target_has_a_complete_party_baseline(self):
        for record in self.register:
            shares = record['partyBaseline']['partyShares']
            self.assertEqual(len(shares), 17, record['name'])
            self.assertAlmostEqual(sum(v['scenario'] for v in shares.values()), 1.0, places=9)
            for party, v in shares.items():
                self.assertLessEqual(v['lower'] - 1e-9, v['scenario'], (record['name'], party))
                self.assertLessEqual(v['scenario'], v['upper'] + 1e-9, (record['name'], party))
            self.assertTrue(record['predecessors'])

    def test_maori_seats_have_no_candidate_layer_quantity(self):
        for record in (r for r in self.register if r['scope'] == 'maori'):
            self.assertTrue(record['candidateLayer'].startswith('not computed'))
            self.assertNotIn('candidate', ' '.join(k for k in record['partyBaseline']).lower())

    def test_exact_seats_match_stage40(self):
        exact = Counter(r['scope'] for r in self.register if r['exactSourceElectorateId'])
        self.assertEqual(dict(exact), {'general': 14, 'maori': 2})
        for record in self.register:
            if record['exactSourceElectorateId']:
                self.assertEqual(len(record['predecessors']), 1)
                self.assertEqual(record['pluralityPredecessor']['sourceElectorateId'], record['exactSourceElectorateId'])


class Mapping(unittest.TestCase):
    mapping = load('mapping.json')

    def test_edges_and_source_seats(self):
        edges = Counter(e['scope'] for e in self.mapping['edges'])
        self.assertEqual(dict(edges), {'general': 123, 'maori': 10})
        fates = Counter(f['scope'] for f in self.mapping['sourceSeatFates'])
        self.assertEqual(dict(fates), {'general': 65, 'maori': 7})
        for edge in self.mapping['edges']:
            self.assertTrue(edge['sourceElectorateId'].startswith(('nz-general-2023-electorate-', 'nz-maori-2023-electorate-')))
            self.assertLessEqual(edge['jointPopulationLower'], edge['jointPopulationUpper'])

    def test_only_ohariu_has_no_target_plurality(self):
        lost = [f['sourceName'] for f in self.mapping['sourceSeatFates'] if f['fate'] == 'no_target_plurality']
        self.assertEqual(lost, ['Ōhāriu'])
        renamed = {f['sourceName']: f['pluralityPredecessorOf'] for f in self.mapping['sourceSeatFates'] if f['fate'] == 'renamed_plurality'}
        self.assertEqual(renamed, {'Bay of Plenty': ['Mt Maunganui'], 'East Coast': ['East Cape'], 'Kelston': ['Glendene'], 'Mana': ['Kenepuru'],
                                   'New Lynn': ['Waitākere'], 'Panmure-Ōtāhuhu': ['Ōtāhuhu'], 'Rongotai': ['Wellington Bays'],
                                   'Te Atatū': ['Henderson'], 'Wellington Central': ['Wellington North'], 'Ōtaki': ['Kapiti']})

    def test_codes_are_vintage_specific(self):
        collisions = self.mapping['codeNamespaceCollisions']
        self.assertGreater(len(collisions), 0)
        self.assertEqual({c['scope'] for c in collisions}, {'general'})
        botany = [c for c in collisions if c['targetName'] == 'Botany']
        self.assertEqual([(c['code'], c['sourceName']) for c in botany], [('003', 'Bay of Plenty')])

    def test_name_join_normalises_unicode(self):
        self.assertEqual(build.nfc('Ōtāhuhu'), build.nfc('Ōtāhuhu'))
        self.assertNotEqual('Ōtāhuhu', 'Otahuhu')  # the Stage10 macron failure mode: unnormalised or stripped names do not join


class Reconciliation(unittest.TestCase):
    reconciliation = load('reconciliation.json')

    def test_totals_equal_official_2023(self):
        votes = self.reconciliation['validVotes']
        self.assertEqual(votes['officialCombined'], 2851211)
        self.assertEqual(votes['sumOfElectorateRows'], votes['officialCombined'])
        self.assertEqual(votes['boundsSourceGeneral'] + votes['boundsSourceMaori'], votes['officialCombined'])
        self.assertEqual(self.reconciliation['electorateRows'], {'general': 65, 'maori': 7})

    def test_every_party_reconciles(self):
        parties = self.reconciliation['parties']
        self.assertEqual(len(parties), 17)
        for row in parties:
            self.assertTrue(row['sourceEqualsOfficial'], row['partyKey'])
            self.assertTrue(row['scenarioConservesGeneral'] and row['scenarioConservesMaori'], row['partyKey'])
            self.assertTrue(row['boundsEncloseGeneralTotal'], row['partyKey'])
            self.assertEqual(row['officialCombinedTotal'], row['officialPartyListVotes'])
        national = next(r for r in parties if r['partyKey'] == 'nationalparty')
        self.assertEqual(national['officialCombinedTotal'], 1085851)


class CrossCheck(unittest.TestCase):
    cross = load('audit.json')['thirdPartyCrossCheck']

    def test_sheet_matches_its_article_and_all_seats_join(self):
        self.assertEqual(self.cross['newSeatsMatched'], 71)
        self.assertTrue(self.cross['headlineMatchesArticle'])
        self.assertEqual(self.cross['abolishedOldSeat'], 'Ōhāriu')

    def test_exact_seats_agree_to_rounding_and_changed_seats_do_not(self):
        self.assertLess(self.cross['exactSeats']['maxAbs'], build.CONSISTENT)
        self.assertGreater(self.cross['changedSeats']['maxAbs'], build.LARGE)

    def test_only_kapiti_disagrees_on_the_top_two_parties(self):
        self.assertEqual(self.cross['topTwoPartyAgreement']['disagree'], ['Kapiti'])
        self.assertEqual(self.cross['pluralityPredecessorVersusThirdPartyOldSeat']['disagreements'], [])


class Provenance(unittest.TestCase):
    def test_registry_hashes_match_preserved_raw_files(self):
        registry = read(REGISTRY)
        self.assertEqual({s['rawPath'] for s in registry['sources']}, {SHEET, ARTICLE})
        for source in registry['sources']:
            self.assertEqual(digest(source['rawPath']), source['sha256'])
            self.assertEqual(source['role'], 'comparison_only_not_model_input')
        self.assertIn('Not found', registry['boundedSearchForOfficialNotionalResults']['outcome'])

    def test_frozen_sources_registry_untouched(self):
        text = (ROOT / 'data/sources.json').read_text(encoding='utf-8')
        self.assertNotIn('stage64', text)
        self.assertNotIn('tallyroom', text)

    def test_third_party_data_is_not_read_by_model_code(self):
        needle = 'electorate-baseline'
        for path in (ROOT / 'scripts').rglob('*.py'):
            if 'electorate_baseline' in path.parts or path.name == 'test_stage64_electorate_baseline.py':
                continue
            self.assertNotIn(needle, path.read_text(encoding='utf-8'), str(path))
        for path in (ROOT / 'src').rglob('*'):
            if path.is_file() and path.suffix in {'.ts', '.tsx'}:
                self.assertNotIn(needle, path.read_text(encoding='utf-8'), str(path))


if __name__ == '__main__':
    unittest.main()
