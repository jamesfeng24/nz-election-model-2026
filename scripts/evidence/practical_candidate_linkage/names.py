"""Explicit, accent-preserving names and the frozen finite nickname pairs."""
import unicodedata

GLYPHS = str.maketrans({'’': "'", '‘': "'", 'ʼ': "'", '‐': '-', '‑': '-', '–': '-', '.': ''})


def normalize(value):
    return ' '.join(unicodedata.normalize('NFC', value).casefold().translate(GLYPHS).split())


def parse_name(label, order='surname_comma_given', surname=None):
    if order == 'surname_comma_given' and label.count(',') == 1:
        family, rest = label.split(',')
    elif order == 'given_surname' and ',' not in label:
        parts = label.split()
        if surname is not None and normalize(label).endswith(' ' + normalize(surname)):
            family, rest = surname, label[:len(label)-len(surname)]
        elif len(parts) == 2:
            rest, family = parts
        else:
            return {'status': 'unresolved', 'reason': 'ambiguous_name_order'}
    else:
        return {'status': 'unresolved', 'reason': 'ambiguous_name_order'}
    family, rest = normalize(family), normalize(rest)
    tokens = rest.split()
    if not family or not tokens or any(not (c.isalpha() or c in " '-") for c in family + rest):
        return {'status': 'unresolved', 'reason': 'unsupported_name_tokens'}
    return {'status': 'parsed', 'surname': family, 'given': tokens[0], 'middle': tokens[1:],
            'givenSubstantive': sum(c.isalpha() for c in tokens[0]) > 1,
            'order': order}


def alias_pairs(document):
    pairs = set()
    for left, right in document['pairs']:
        a, b = normalize(left), normalize(right)
        if a == b or (a, b) in pairs or (b, a) in pairs:
            raise ValueError('Duplicate/invalid frozen alias pair')
        pairs.add((a, b))
    return pairs


def name_match(left, right, aliases):
    if left['status'] != 'parsed' or right['status'] != 'parsed':
        return {'compatible': False, 'reason': 'ambiguous_name_parse', 'flags': []}
    if left['surname'] != right['surname']:
        return {'compatible': False, 'reason': 'name_difference', 'flags': []}
    if not left['givenSubstantive'] or not right['givenSubstantive']:
        return {'compatible': False, 'reason': 'given_initial_only', 'flags': []}
    a, b = left['given'], right['given']
    nickname = a != b and ((a, b) in aliases or (b, a) in aliases)
    if a != b and not nickname:
        return {'compatible': False, 'reason': 'name_difference', 'flags': []}
    flags = ['frozen_nickname'] if nickname else []
    lm, rm = left['middle'], right['middle']
    for a, b in zip(lm, rm):
        if a == b:
            continue
        if (len(a) == 1 and b.startswith(a)) or (len(b) == 1 and a.startswith(b)):
            flags.append('middle_initial')
        else:
            return {'compatible': False, 'reason': 'middle_conflict', 'flags': sorted(set(flags))}
    if len(lm) != len(rm):
        flags.append('middle_omission')
    if not flags:
        flags.append('exact_name')
    return {'compatible': True, 'reason': None, 'flags': sorted(set(flags))}


def strict_member(edge):
    return edge['label'] == 'documentary_same_person' or (
        edge['label'] == 'accepted_algorithmic_same_person' and
        edge['ruleFlags'] == ['exact_name'])
