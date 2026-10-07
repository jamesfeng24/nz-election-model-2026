"""Stage75: the live S+R fit uses every completed election with the unchanged Stage33 design, and the 2026 features
are centred on its training-only means."""
import unittest
from scripts.candidate_fit_2026 import common as C, run
from scripts.nowcast_assembly import general
from scripts.nowcast_assembly.common import CONFIG, read


class LiveFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit = read(C.FIT)
        cls.features = read(C.FEATURES)
        cls.latest, cls.records = C.design()

    def test_builder_reproduces_the_saved_stage33_payload(self):
        self.assertEqual(run.verify_builder(self.latest, self.records), run.saved_latest()['fits'][C.METHOD]['fitId'])

    def test_training_adds_the_2023_contests_and_nothing_else(self):
        fold = self.fit['folds'][0]
        self.assertEqual(fold['trainingIds'], self.latest['trainingIds'] + self.latest['evaluationIds'])
        self.assertEqual(fold['trainingTargetYears'], [2011, 2014, 2017, 2020, 2023])
        self.assertEqual(fold['trainingContests'], 245)
        live, rows = C.live_fold(self.latest, self.records)
        self.assertEqual(fold['trainingOnlyMeans'], live['trainingOnlyMeans'])
        self.assertEqual(C.job(live, rows)['signature'], fold['fits'][C.METHOD]['fitId'])
        self.assertEqual(fold['fits'][C.METHOD]['parameters']['status'], 'fitted')

    def test_features_are_recentred_exactly_and_the_assembly_uses_them(self):
        readiness = read(C.READINESS)
        new = self.features['trainingOnlyMeans']
        old = self.features['previousTrainingOnlyMeans']
        self.assertEqual(new, self.fit['folds'][0]['trainingOnlyMeans'])
        for c in readiness['candidateRecords']:
            value = self.features['candidates'][c['targetOccurrenceId']]
            for name in ('S', 'R'):
                record = c['continuous'][name]
                expected = record['contribution'] + record['supportedWeight'] * (old[name] - new[name])
                self.assertAlmostEqual(value[name], expected, places=12)
        config = read(CONFIG)
        parameters, fit_id = general.fold_parameters(config)
        self.assertEqual(fit_id, self.fit['folds'][0]['fits'][C.METHOD]['fitId'])
        self.assertEqual(parameters['coefficients'], self.fit['comparison']['live']['coefficients'])


if __name__ == '__main__':
    unittest.main()
