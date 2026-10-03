"""Verify previously committed construction bytes before downstream evaluation."""
from hashlib import sha256
from .common import local, DEST, digest


def verify_phase(name):
    manifest = local(name + '-manifest.json')
    for filename, expected in manifest['outputSha256'].items():
        if sha256((DEST / filename).read_bytes()).hexdigest() != expected:
            raise ValueError('Changed ' + name + ' artifact ' + filename)
    for path, expected in manifest['generatorSha256'].items():
        if digest(path) != expected:
            raise ValueError('Changed ' + name + ' generator ' + path)
