"""Synthetic byte fixtures only; no external election data or network calls."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.validate.source_files import verify_source_files


class SourceFilesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.raw = self.root / "data/raw/synthetic.bin"
        self.raw.parent.mkdir(parents=True)
        self.raw.write_bytes(b"synthetic fixture\x00\xff")
        self.source = {"id": "synthetic", "rawPath": "data/raw/synthetic.bin",
                       "sha256": hashlib.sha256(self.raw.read_bytes()).hexdigest()}

    def check(self, source):
        verify_source_files(self.root, {"schemaVersion": 1, "sources": [source]})

    def test_accepts_empty_registry(self):
        verify_source_files(self.root, {"schemaVersion": 1, "sources": []})

    def test_preserves_and_verifies_exact_bytes(self):
        before = self.raw.read_bytes()
        self.check(self.source)
        self.assertEqual(self.raw.read_bytes(), before)

    def test_rejects_changed_bytes(self):
        self.raw.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            self.check(self.source)

    def test_rejects_missing_file(self):
        with self.assertRaisesRegex(ValueError, "Missing raw file"):
            self.check({**self.source, "rawPath": "data/raw/missing.bin"})

    def test_rejects_traversal(self):
        for path in ["data/raw/../secret", "/tmp/secret", "data/raw\\secret"]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "Unsafe raw path"):
                self.check({**self.source, "rawPath": path})

    def test_rejects_symlink_escape(self):
        outside = self.root / "outside.bin"
        outside.write_bytes(b"outside")
        (self.raw.parent / "link.bin").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escapes raw directory"):
            self.check({**self.source, "rawPath": "data/raw/link.bin"})

    def test_rejects_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, "Duplicate source id"):
            verify_source_files(self.root, {"schemaVersion": 1, "sources": [self.source, self.source]})

    def test_rejects_unknown_registry_version(self):
        with self.assertRaisesRegex(ValueError, "version-1"):
            verify_source_files(self.root, {"schemaVersion": 2, "sources": []})


if __name__ == "__main__":
    unittest.main()
