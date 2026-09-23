"""Required historical source records are stable while registry additions are allowed."""

from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.models.source_provenance import validated_supporting_sources
from scripts.models.nat_lab_elasticity.run import build as stage6_build
from scripts.models.candidate_overperformance.run import build as stage7_build


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = json.loads((ROOT / 'data/source-plans/stage6-7-supporting-candidate-sources.json').read_text())
REGISTRY = json.loads((ROOT / 'data/sources.json').read_text())


def raw(path):
    return (ROOT / path).read_bytes()


def unrelated_record():
    return {'id': 'future-unrelated-source', 'url': 'https://example.invalid/unrelated',
            'rawPath': 'data/raw/unrelated', 'sha256': '0' * 64}


def patched_bytes(registry=None, changed_raw_path=None):
    original = Path.read_bytes

    def read(path):
        if registry is not None and str(path).endswith('data/sources.json'):
            return json.dumps(registry).encode()
        content = original(path)
        return content + b'changed' if changed_raw_path and str(path).endswith(changed_raw_path) else content

    return read


class SourceProvenanceTests(TestCase):
    def test_unrelated_addition_preserves_stage6_and_stage7_outputs(self):
        registry = deepcopy(REGISTRY)
        registry['sources'].append(unrelated_record())
        validated_supporting_sources(SNAPSHOT, registry, raw)
        before6, before7 = stage6_build(), stage7_build()
        with patch.object(Path, 'read_bytes', patched_bytes(registry=registry)):
            self.assertEqual(stage6_build(), before6)
            self.assertEqual(stage7_build(), before7)

    def test_altered_and_deleted_required_records_rejected(self):
        source_id = SNAPSHOT['requiredSourceRecords'][0]['id']
        altered = deepcopy(REGISTRY)
        next(row for row in altered['sources'] if row['id'] == source_id)['resource'] = 'altered'
        with self.assertRaisesRegex(ValueError, 'Changed or deleted required source record'):
            validated_supporting_sources(SNAPSHOT, altered, raw)
        with patch.object(Path, 'read_bytes', patched_bytes(registry=altered)):
            with self.assertRaisesRegex(ValueError, 'Changed or deleted required source record'):
                stage6_build()
            with self.assertRaisesRegex(ValueError, 'Changed or deleted required source record'):
                stage7_build()
        deleted = deepcopy(REGISTRY)
        deleted['sources'] = [row for row in deleted['sources'] if row['id'] != source_id]
        with self.assertRaisesRegex(ValueError, 'Changed or deleted required source record'):
            validated_supporting_sources(SNAPSHOT, deleted, raw)
        with patch.object(Path, 'read_bytes', patched_bytes(registry=deleted)):
            with self.assertRaisesRegex(ValueError, 'Changed or deleted required source record'):
                stage6_build()
            with self.assertRaisesRegex(ValueError, 'Changed or deleted required source record'):
                stage7_build()

    def test_altered_required_raw_bytes_rejected(self):
        changed_path = SNAPSHOT['requiredSourceRecords'][0]['rawPath']

        def changed(path):
            content = raw(path)
            return content + b'changed' if path == changed_path else content

        with self.assertRaisesRegex(ValueError, 'Changed required raw source'):
            validated_supporting_sources(SNAPSHOT, REGISTRY, changed)
        with patch.object(Path, 'read_bytes', patched_bytes(changed_raw_path=changed_path)):
            with self.assertRaises(ValueError):
                stage6_build()
            with self.assertRaises(ValueError):
                stage7_build()


if __name__ == '__main__':
    import unittest
    unittest.main()
