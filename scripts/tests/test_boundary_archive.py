"""Synthetic byte segments exercise immutable archive reconstruction failures."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.boundaries.archive import archive_bytes


class ArchiveTests(unittest.TestCase):
    def test_reconstruction_rejects_corruption_order_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data/raw').mkdir(parents=True)
            (root/'data/raw/a').write_bytes(b'abc');(root/'data/raw/b').write_bytes(b'def')
            manifest={'originalBytes':6,'originalSha256':hashlib.sha256(b'abcdef').hexdigest(),'parts':[
                {'rawPath':'data/raw/'+name,'offset':offset,'bytes':3,'sha256':hashlib.sha256(raw).hexdigest()}
                for name,offset,raw in [('a',0,b'abc'),('b',3,b'def')]]}
            self.assertEqual(archive_bytes(manifest,root),b'abcdef')
            for field,value in [('offset',1),('rawPath','../outside'),('sha256','0'*64),('bytes',4)]:
                changed=copy.deepcopy(manifest);changed['parts'][0][field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):archive_bytes(changed,root)
            (root/'data/raw/a').write_bytes(b'xyz')
            with self.assertRaises(ValueError):archive_bytes(manifest,root)
