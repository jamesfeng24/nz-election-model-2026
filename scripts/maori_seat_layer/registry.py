"""Dated Stage66 source registry (never data/sources.json), built from the fetch log and the preserved bytes."""
import argparse
from scripts.maori_seat_layer.common import ROOT, RAW, digest, save

ROLE = {
    'wikipedia-opinion-polling': ('Wikipedia', 'Electorate-poll compilation (secondary, volunteer-edited); transcribed into historical-polls.json and spot-checked against primary reporting where listed.'),
    'rnz-2023': ('RNZ', 'News report of a 2023 Whakaata Maori-Curia electorate poll; used to verify listed shares and the undecided share.'),
    'scoop-2023': ('Scoop', 'Media-release mirror of the 2023 Whakaata Maori-Curia Tamaki Makaurau poll; used to verify shares and undecided share.'),
    'whakaata-2023': ('Whakaata Maori', 'Whakaata Maori media release for the 2023 Te Tai Tonga poll; used to verify shares and undecided share.'),
    'maoritv-2017': ('Maori Television', 'Context page for the 2017 Maori TV-Reid Research polls; it does not itself list the seat figures (they come from the Wikipedia compilation).'),
    'herald-2020': ('NZ Herald', 'News report of the 2020 Maori TV-Curia Waiariki poll; used to verify Coffey 38, Waititi 26 and undecided 24.'),
}


def build():
    rows = [line.rstrip('\n').split('\t') for line in (ROOT / RAW / 'fetch-log.tsv').read_text().splitlines()]
    sources = []
    for stamp, status, name, url in sorted(rows, key=lambda r: r[2]):
        if not status.startswith('200 '):
            raise ValueError('Unexpected fetch status for ' + name)
        organisation, role = next(v for k, v in ROLE.items() if name.startswith(k))
        sources.append({
            'id': 'stage66-' + name, 'organisation': organisation, 'url': url, 'dateOrElection': 'Maori electorate polls 2014-2023',
            'resource': name, 'retrievedAt': stamp, 'rawPath': RAW + '/' + name, 'processingScript': 'scripts/maori_seat_layer/run.py',
            'limitations': [role, 'Page bytes preserved as served at retrieval; responses headers in the .headers sidecar. Bytes are not a parsed dataset.'],
            'sha256': digest(RAW + '/' + name),
            'licence': 'Publisher copyright (Wikipedia text CC BY-SA); preserved unchanged for research provenance only, not redistributed in application results.',
            'schemaVersion': 1})
    return {'schemaVersion': 1, 'note': 'Dated standalone registry for Stage66. data/sources.json is frozen and untouched.', 'sources': sources}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    save('source-registry.json', build(), args.check)
    print('Stage66 registry ok' if args.check else 'wrote source-registry.json')


if __name__ == '__main__':
    main()
