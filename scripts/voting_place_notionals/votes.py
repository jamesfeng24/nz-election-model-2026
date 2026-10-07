"""Unified vote-column spaces: candidate votes by candidate party label, party votes by registered party."""
import numpy as np

from .parse import nfc


def candidate_labels(tables):
    """Sorted union of candidate party labels (NFC, stripped) over the given general tables."""
    labels = set()
    for table in tables.values():
        for entry in table['result']:
            labels.add(entry['party'].strip())
    return sorted(labels)


def candidate_projection(table, labels):
    """[C_file x L] 0/1 matrix mapping a file's candidate columns (valid-vote columns only) to party labels."""
    columns = [nfc(c) for c in table['columns']]
    by_name = {entry['name']: entry['party'].strip() for entry in table['result']}
    valid = [c for c in columns if c in by_name]
    if len(valid) != len(by_name):
        raise ValueError('Candidate columns and result block disagree in ' + table['name'])
    projection = np.zeros((len(columns), len(labels)))
    for k, name in enumerate(columns):
        if name in by_name:
            projection[k, labels.index(by_name[name])] = 1.0
    return projection


def project_table(sites, matrix, other, unlocated, projection):
    return matrix @ projection, other @ projection, unlocated @ projection


def is_cancelled(table):
    return sum(table['total']) == 0
