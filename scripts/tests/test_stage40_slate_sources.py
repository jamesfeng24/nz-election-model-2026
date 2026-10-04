"""Synthetic parser safeguards plus counts on the pinned Stage40 bulk pages."""
from pathlib import Path
import tempfile
import unittest

from scripts.readiness.slate_sources import (
    Document, act, card_claims, extract_claims, maori, national, nzfirst, willis,
)


RAW = Path(__file__).resolve().parents[2] / 'data/raw/forecast-readiness/2026-10-05'


class SyntheticSourceTests(unittest.TestCase):
    def test_static_visible_unicode_and_no_script_hydration_duplicates(self):
        root = Document('<article class="people"><h4>Hūhana Lyndon</h4>'
                        '<p>Te Tai Tokerau</p></article><script>Hūhana Lyndon</script>').root
        self.assertEqual(root.text(), 'Hūhana Lyndon Te Tai Tokerau')

    def test_national_only_2026_section_not_incumbent_seat(self):
        root = Document('<a href="/old"><h3>Old MP</h3><p>MP for Old Seat</p></a>'
                        '<h2>Candidates for 2026</h2><a href="/new"><h3>New Name</h3>'
                        '<p>Candidate for New Seat</p></a>').root
        claims, context, gaps = national(root)
        self.assertEqual([(r['displayName'], r['sourceElectorateLabel']) for r in claims],
                         [('New Name', 'New Seat')])
        self.assertIsNone(context[0]['sourceElectorateLabel'])
        self.assertFalse(gaps)
        self.assertIsNone(claims[0]['publicationDate'])

    def test_missing_national_section_abstains(self):
        claims, _, gaps = national(Document('<p>Candidate for New Seat</p>').root)
        self.assertFalse(claims)
        self.assertEqual(gaps[0]['reason'], 'missing_or_ambiguous_2026_section')

    def test_nzfirst_list_mp_not_electorate_candidate(self):
        root = Document('<article class="card-team"><h3>List Person</h3>'
                        '<h4>List MP - Kaikoura</h4></article>'
                        '<article class="card-team"><h3>Selected Person</h3>'
                        '<h4>Candidate for Kaikoura</h4></article>').root
        claims, context, _ = nzfirst(root)
        self.assertEqual(len(claims), 1)
        self.assertIsNone(context[0]['sourceElectorateLabel'])

    def test_act_mixed_retirement_and_incumbency_do_not_create_claims(self):
        root = Document('<h3>Intro text</h3>'
                        '<a href="./people/first"><h3>First Person</h3><p>Seat A</p></a>'
                        '<a href="./people/incumbent"><h3>Incumbent Person</h3><p>MP for Seat B</p></a>'
                        '<h2>Electorate Only &amp; Retiring MPs</h2>'
                        '<a href="./people/retiring"><h3>Retiring Person</h3><p>Seat C</p></a>'
                        '<h2>Local Government Representatives</h2>'
                        '<a href="./people/local"><h3>Local Person</h3><p>Councillor</p></a>').root
        claims, context, gaps = act(root)
        self.assertEqual([r['displayName'] for r in claims], ['First Person'])
        self.assertEqual(len(context), 2)
        self.assertEqual(len(gaps), 1)
        self.assertIn('generic headline', claims[0]['qualification'])

    def test_missing_card_seat_is_context_not_invented_electorate(self):
        root = Document('<article class="candidate"><h3 class="name">List Person</h3></article>'
                        '<article class="candidate"><p class="seat">Seat A</p></article>').root
        claims, context, gaps = card_claims(root, 'synthetic', 'syntheticparty',
                                           'candidate', 'name', 'seat')
        self.assertFalse(claims)
        self.assertIsNone(context[0]['sourceElectorateLabel'])
        self.assertEqual(gaps[0]['reason'], 'candidate_card_missing_name')

    def test_party_nomination_is_not_official_nomination_and_date_is_supported(self):
        root = Document('<p>Published by Te Pāti Māori July 27, 2025</p>'
                        '<p>Te Pāti Māori is proud to announce the nomination of Haley Maxwell '
                        'as its candidate for Ikaroa-Rāwhiti in the 2026 General Election.</p>').root
        claims, _, gaps = maori(root, 'maori-haley')
        self.assertFalse(gaps)
        self.assertEqual(claims[0]['status'], 'party_selected')
        self.assertEqual(claims[0]['publicationDate'], '2025-07-27')
        self.assertIn('not an official nomination', claims[0]['qualification'])

    def test_confirmation_requires_exact_seat_and_year(self):
        root = Document('<p>Te Pāti Māori is proud to announce Lisa Marie Murch '
                        'as its candidate for A Different Seat.</p>').root
        claims, _, gaps = maori(root, 'maori-lisa')
        self.assertFalse(claims)
        self.assertTrue(gaps)

    def test_list_only_confirmation_has_no_guessed_seat(self):
        root = Document('<p>22 December 2025</p><p>Deputy Leader of the National Party, Nicola Willis '
                        'has today been confirmed as a List-Only candidate for the 2026 election.</p>').root
        claims, context, gaps = willis(root)
        self.assertFalse(claims)
        self.assertFalse(gaps)
        self.assertIsNone(context[0]['sourceElectorateLabel'])

    def test_missing_resources_are_explicit_and_reproduction_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            first = extract_claims(temp)
            self.assertEqual(first, extract_claims(temp))
            self.assertFalse(first['claims'])
            self.assertEqual(sum(g['reason'] == 'preserved_resource_missing' for g in first['gaps']), 8)


class PreservedSourceTests(unittest.TestCase):
    def test_all_pinned_cards_and_unresolved_groups(self):
        result = extract_claims(RAW)
        counts = {key: value['claims'] for key, value in result['sourceCounts'].items()}
        self.assertEqual(counts, {'national-team': 25, 'nzfirst-team': 40,
                                 'act-people': 43, 'green-candidates': 54,
                                 'opportunity-team': 42, 'maori-haley': 1,
                                 'maori-lisa': 1, 'national-willis': 0})
        self.assertEqual(len(result['claims']), 206)
        self.assertEqual(len([g for g in result['gaps']
                              if g['sourceKey'] == 'act-people']), 5)
        self.assertFalse(any(r['displayName'] in {'Brooke van Velden', 'David Seymour'}
                             for r in result['claims']))
        self.assertEqual(result, extract_claims(RAW))

    def test_unicode_original_labels_dates_and_no_nomination_promotion(self):
        claims = extract_claims(RAW)['claims']
        self.assertTrue(any(r['displayName'] == 'Chlöe Swarbrick' for r in claims))
        self.assertTrue(any(r['displayName'] == 'Qiulae (Q) Wong' for r in claims))
        self.assertEqual({r['status'] for r in claims}, {'party_announced', 'party_selected'})
        self.assertEqual(next(r['publicationDate'] for r in claims if r['sourceKey'] == 'maori-lisa'),
                         '2026-06-15')
        self.assertTrue(all(r['passage'] and r['locator'] and r['affiliationKey'] for r in claims))


if __name__ == '__main__':
    unittest.main()
