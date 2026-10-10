"""Stage77: layer replication, grouped noise banks, the release gate checks and the rehearsal stand-ins."""
import copy
import unittest
import numpy as np
from scripts.nowcast_assembly import assemble as A, streams
from scripts.nowcast_assembly.common import CONFIG, read
from scripts.release_rehearsal import run as rehearsal
from scripts.tests.test_stage73_nowcast_assembly import GENERAL, MAORI, synthetic_classification, synthetic_slates


def synthetic_maori(total):
    """SYNTHETIC TEST FIXTURE: invented Maori winners."""
    return {seat: {'status': 'simulated', 'class': 'maori-layer', 'source': 'synthetic-test', 'candidates': ['synthetic-a', 'synthetic-b'],
                   'candidateNames': ['Synthetic A', 'Synthetic B'], 'candidateParty': ['labourparty', 'tepatimaori'],
                   'candidateShares': [], 'winners': [d % 2 for d in range(total)]} for seat in MAORI}


class Noise(unittest.TestCase):
    def test_shared_keys_share_one_bank_and_seat_keys_are_grouped(self):
        names = ['candidate:2026:shared:balance', 'candidate:2026:seat:a:balance', 'candidate:2026:seat:b:balance',
                 'local_party:2026:shared:within:greenparty', 'local_party:2026:seat:a:within:greenparty']
        bank = streams.GroupedBank(names, 64, 'synthetic-test')
        self.assertEqual(streams.group_of(names[0]), 'shared')
        self.assertEqual(streams.group_of(names[1]), 'candidate:a')
        columns = [bank[:, i] for i in range(len(names))]
        self.assertTrue(all(c.shape == (64,) and (c > 0).all() and (c < 1).all() for c in columns))
        self.assertFalse(np.allclose(columns[1], columns[2]))
        self.assertTrue(np.array_equal(bank[:, 0], streams.GroupedBank(names, 64, 'synthetic-test')[:, 0]))
        with self.assertRaises(ValueError):
            streams.GroupedBank(names, 48, 'synthetic-test')


class Replication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(CONFIG)
        cls.bank = A.assemble(cls.config, 8, slates=synthetic_slates(), classification=synthetic_classification(),
                              maori_records=synthetic_maori(16), workers=2, replicates=2)

    def test_rows_are_national_draws_times_replicates(self):
        bank = self.bank
        self.assertEqual((bank['draws'], bank['nationalDraws'], bank['layerReplicates']), (16, 8, 2))
        self.assertEqual(len(bank['drawIds']), 8)
        self.assertEqual(len(bank['partyVote']['shares']), 8)
        self.assertTrue(all(len(s['winners']) == 16 for s in bank['seats']))
        passed, checks = A.gate(bank, self.config)
        self.assertEqual({c['check'] for c in checks if not c['passed']}, {'provenanceLive'})

    def test_replicates_draw_independent_layer_noise(self):
        general = [s for s in self.bank['seats'] if s['scope'] == 'general']
        differ = sum(any(s['winners'][2 * i] != s['winners'][2 * i + 1] for i in range(8)) for s in general)
        self.assertGreater(differ, 0)
        with self.assertRaises(ValueError):
            A.assemble(self.config, 8, slates=synthetic_slates(), classification=synthetic_classification(),
                       maori_records=synthetic_maori(24), replicates=3)


class Blocs(unittest.TestCase):
    def test_james_blocs_use_listed_parties_and_the_hung_definition_is_closed(self):
        mmp = read(CONFIG)['mmp']
        listed = set(read(CONFIG)['national']['categoryMap'].values()) - {'other'}
        self.assertEqual([b['label'] for b in mmp['blocs']], ['NAT+ACT', 'NAT+ACT+NZF', 'LAB+GRN', 'LAB+GRN+TPM'])
        self.assertTrue(all(set(b['partyIds']) <= listed for b in mmp['blocs']))
        ids = {b['id'] for b in mmp['blocs']}
        hung = mmp['hungParliament']
        self.assertTrue(set(hung['blocs']) <= ids and hung['kingmaker'] == 'opportunity')
        self.assertFalse(any(hung['kingmaker'] in b['partyIds'] for b in mmp['blocs']))


class Gate(unittest.TestCase):
    def test_reconciliation_tolerance_is_an_internal_gate_check(self):
        config = read(CONFIG)
        self.assertFalse(hasattr(A, 'staleness'))
        strict = copy.deepcopy(config)
        strict['release']['reconciliationTolerancePP'] = 0.1
        bank = A.assemble(config, 8, slates=synthetic_slates(), classification=synthetic_classification(),
                          maori_records=synthetic_maori(8))
        failed = {c['check'] for c in A.gate(bank, strict)[1] if not c['passed']}
        self.assertIn('nationalReconciliation', failed)

    def test_rehearsal_labels_every_stand_in(self):
        self.assertEqual(len(rehearsal.STAND_INS), 3)   # Stage80: the unpolled Maori seats now use the real fallback
        self.assertTrue(all('real' in n for n in rehearsal.NOT_USED))
        self.assertFalse([t for t in rehearsal.STAND_INS + rehearsal.NOT_USED if 'Stage64' in t or 'not yet run' in t or 'has not entered' in t])  # audit C4: no stale claims
        self.assertFalse(hasattr(rehearsal, 'AS_OF') or hasattr(rehearsal, 'STAGE70'))  # the report follows the config's adopted refresh
        classes = rehearsal.synthetic_classification(GENERAL)
        self.assertEqual(set(classes), set(GENERAL))


if __name__ == '__main__':
    unittest.main()
