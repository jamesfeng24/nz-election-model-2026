import tempfile
from pathlib import Path
import unittest
from scripts.ingest.historical_sources import register, destination
from scripts.transform.historical import read_csv, split_rows, count, ratio


class HistoricalInfrastructureTest(unittest.TestCase):
    def test_rejects_negative_and_missing_counts(self):
        for value in ('', '-1', '1.2'):
            with self.assertRaises(ValueError):
                count(value)
        self.assertEqual(count('1,234'), 1234)
        self.assertIsNone(ratio(0, 0))

    def test_preserves_macrons(self):
        rows, _ = read_csv('name,votes\nTe Atatū,2\n'.encode())
        self.assertEqual(rows[1][0], 'Te Atatū')

    def test_split_percentages_are_not_invented_counts(self):
        parsed = split_rows(b'01 Synthetic,Total Party Votes,Candidate,Total %\nSynthetic,3,100.00,100.00\n')
        self.assertEqual(parsed['rows'][0]['cells'][0]['reportedPercent'], 100)
        self.assertIsNone(parsed['rows'][0]['cells'][0]['count'])

    def test_import_is_immutable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            url = 'https://www.electionresults.govt.nz/electionresults_2008/test.csv'
            first = register(root, 2008, url, b'a,b\r\n1,2\r\n', '2026-09-07T00:00:00Z', 'synthetic test')
            second = register(root, 2008, url, b'a,b\r\n1,2\r\n', '2026-09-08T00:00:00Z', 'synthetic test')
            self.assertEqual(first, second)
            with self.assertRaises(ValueError):
                register(root, 2008, url, b'changed', '2026-09-07T00:00:00Z', 'test')

    def test_rejects_unapproved_source_and_error_page(self):
        with self.assertRaises(ValueError):
            destination(Path('.'), 2023, 'https://example.org/file.csv')
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            register(Path(directory), 2008, 'https://www.electionresults.govt.nz/electionresults_2008/test.csv', b'<html>Forbidden</html>', '2026-09-07T00:00:00Z', 'test')
