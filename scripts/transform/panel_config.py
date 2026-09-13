"""Integration-only identities; aliases never rewrite per-election source fields."""
YEARS = (2008, 2011, 2014, 2017, 2020, 2023)
COUNTS = {2008: (63,1197,499), 2011: (63,819,423), 2014: (64,960,451),
          2017: (64,1024,431), 2020: (65,1105,561), 2023: (65,1105,468)}
DEST = 'data/processed/historical/2008-2023'
CONTRACT = 'data/source-plans/historical-panel.json'
LEGACY_ALIASES = {'conservativeparty': 'conservative', 'mana': 'manamovement'}
ALIAS_SOURCE = 'https://elections.nz/assets/2014-general-election/report-of-the-electoral-commission-on-the-2014-general-election.pdf'
ALIASES = {**LEGACY_ALIASES, 'newconservative': 'conservative', 'newconservatives': 'conservative',
           'tepatimaori': 'maoriparty', 'newzeal': 'oneparty',
           'nzoutdoorsfreedomparty': 'nzoutdoorsparty', 'socialcredit': 'democratsforsocialcredit'}
ALIAS_EVIDENCE = [
    {'keys': ['socialcredit'], 'url': 'https://elections.nz/media-and-news/2019/application-to-substitute-a-political-party-name-abbreviation-and-register-a-substitute-party-logo', 'approvalUrl': 'https://elections.nz/assets/pagecomponent-file-files/Register-of-Political-Parties-and-Logos-12-Sept-2023-v2.pdf', 'basis': 'Application identifies both abbreviations; registration history confirms approval on 15 October 2019'},
    {'keys': ['newconservative'], 'url': 'https://elections.nz/media-and-news/2018/change-to-conservative-party-name-and-logo', 'basis': 'Approved party name change, 8 August 2018'},
    {'keys': ['newconservatives','tepatimaori','newzeal'], 'url': 'https://elections.nz/assets/2023-General-Election/Report-on-the-2023-General-Election.pdf', 'basis': 'Party registrations section, PDF page 113: three approved name changes'},
    {'keys': ['nzoutdoorsfreedomparty'], 'url': 'https://elections.nz/media-and-news/2022/change-to-nz-outdoors-and-freedom-party-name-and-logo', 'basis': 'Approved rename from NZ Outdoors Party, 6 April 2022'},
]


def canonical(key):
    return None if key == 'independent' else ALIASES.get(key,key)
