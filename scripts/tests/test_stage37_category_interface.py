"""Synthetic contracts plus actual source-only adapters; no inference."""
import copy
import unittest
from math import fsum
from scripts.polling.category_interface.common import ROOT, OUT, NATIONAL, RAW, read
from scripts.polling.category_interface.inventory import build, roster, allocation_weights, report_rows, observation
from scripts.polling.category_interface.allocation import allocate
from scripts.polling.category_interface.external import validate_case, coarsen_means, named_means, point_score, pooled, audit


def fine():
    return [{'categoryId':'nationalparty','ballotGroupKey':'nationalparty','relationship':'continuing','priorShare':.4},
            {'categoryId':'oneparty','ballotGroupKey':'newzeal','relationship':'continuing','priorShare':.02},
            {'categoryId':'freedomsnz','ballotGroupKey':'freedomsnz','relationship':'entrant','priorShare':None}]


class AllocationContractTests(unittest.TestCase):
    def test_explicit_and_other_mass_and_draw_dependence(self):
        weights = allocation_weights(fine(), ['NAT','OTH'], [], 'recent_report_prior')
        a = allocate([.8,.2], ['NAT','OTH'], fine(), weights)
        b = allocate([.6,.4], ['NAT','OTH'], fine(), weights)
        self.assertEqual(a[0], .8)
        self.assertAlmostEqual(fsum(a), 1)
        self.assertAlmostEqual(fsum(a[1:]), .2)
        self.assertAlmostEqual(b[1], 2*a[1])
        self.assertGreater(a[2], 0)
        self.assertEqual(weights[0]['basis'], 'supported_prior')
        self.assertEqual(weights[1]['basis'], 'neutral_seed_assumption')

    def test_zero_other_and_unresolved_remainder(self):
        weights = allocation_weights(fine(), ['NAT','OTH'], [], 'prior_only')
        self.assertEqual(allocate([1,0], ['NAT','OTH'], fine(), weights), [1,0,0])
        only = fine()[:1]
        self.assertEqual(allocate([1,0], ['NAT','OTH'], only, []), [1])
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            allocate([.9,.1], ['NAT','OTH'], only, [])

    def test_missing_duplicate_and_shared_group_rejected(self):
        weights = allocation_weights(fine(), ['NAT','OTH'], [], 'prior_only')
        with self.assertRaises(ValueError):
            allocate([.8,.2], ['NAT','OTH'], fine(), weights[:-1])
        with self.assertRaises(ValueError):
            allocate([.8,.2], ['NAT','OTH'], fine()+fine()[-1:], weights)
        conflict = fine();conflict[2]['ballotGroupKey']='newzeal'
        with self.assertRaises(ValueError):
            allocate([.8,.2], ['NAT','OTH'], conflict, weights)

    def test_rename_prior_and_no_alliance_transfer(self):
        weights = allocation_weights(fine(), ['NAT','OTH'], [], 'prior_only')
        self.assertEqual(weights[0]['weight'], .02)
        self.assertEqual(weights[1]['weight'], .001)
        # A shared group receives one allocation, not its constituents' past mass.
        self.assertEqual([r['categoryId'] for r in weights], ['oneparty','freedomsnz'])

    def test_rounded_zero_is_not_missing_and_all_zero_fallback(self):
        f = fine()[1:]
        reports = [{'categoryId':r['categoryId'], 'pollster':'P','pollId':r['categoryId'], 'ageDays':10,'rawWeight':1,'share':0} for r in f]
        w = allocation_weights(f, ['OTH'], reports, 'recent_report_prior')
        self.assertTrue(all(r['basis']=='all_zero_report_prior_seed_fallback' for r in w))
        reports[0]['share']=.05
        w = allocation_weights(f, ['OTH'], reports, 'recent_report_prior')
        self.assertEqual(w[1]['allocationFraction'], 0)
        missing = allocation_weights(f, ['OTH'], reports[:1], 'recent_report_prior')
        self.assertGreater(missing[1]['allocationFraction'], 0)

    def test_own_top_not_used_by_benchmark(self):
        f = fine() + [{'categoryId':'theopportunitiespartytop','ballotGroupKey':'theopportunitiespartytop','relationship':'entrant','priorShare':None}]
        wm = allocation_weights(f, ['NAT','TOP','OTH'], [], 'prior_only')
        wa = allocation_weights(f, ['NAT','OTH'], [], 'prior_only')
        m = allocate([.7,.2,.1], ['NAT','TOP','OTH'], f, wm)
        a = allocate([.7,.3], ['NAT','OTH'], f, wa)
        self.assertEqual(m[-1], .2)
        self.assertNotEqual(a[-1], m[-1])
        self.assertAlmostEqual(fsum(a[1:]), .3)

    def test_denominator_and_censoring(self):
        r={'estimates':{'TOP':{'status':'rounded','share':.02,'bounds':[.015,.025],'published':'2'}},'denominator':'all_respondents','nonresponseCombined':.2}
        self.assertAlmostEqual(observation(r,'TOP')['share'], .025)
        r['nonresponseCombined']=None
        self.assertIsNone(observation(r,'TOP'))
        r['denominator']='unknown';r['estimates']['TOP']['status']='upper_censored'
        self.assertIsNone(observation(r,'TOP'))


class ActualAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.relationships=read(ROOT/'data/processed/models/expanded-party-substitution/input-inventory.json')['categoryRelationships']
        cls.polls=read(ROOT/'data/processed/polling/national-foundation/polls.json')['records']
        cls.manifests=read(NATIONAL/'output-manifest.json')['cases']
        cls.inventory=build(cls.manifests,cls.relationships,cls.polls)

    def test_heldout_results_and_candidate_outcomes_not_inputs(self):
        changed=copy.deepcopy(self.relationships)
        for r in changed:
            for c in r['categories']:
                c['suppliedTargetNationalShare']=.999
                c['targetNationalVotesScenario']=123
                c['winner']=False;c['candidateVotes']=98765
        self.assertEqual(build(self.manifests,changed,self.polls),self.inventory)

    def test_postcutoff_poll_and_revision_do_not_enter(self):
        p=copy.deepcopy(self.polls)
        for r in p:
            # Preserve existing future rows; add an invented future report only.
            if r['cycle']==2014:
                r['publication']='2099-01-01T00:00:00+13:00'
        future=copy.deepcopy(p[0]);future['id']='synthetic-future';future['cycle']=2014
        future['publication']='2099-01-01T00:00:00+13:00'
        base=build(self.manifests,self.relationships,self.polls)
        plus=build(self.manifests,self.relationships,self.polls+[future])
        for a,b in zip(base['cases'],plus['cases']):
            # Audit exclusion ledger may legitimately add the rejected future record.
            for k in ('roster','reports','systems'):
                self.assertEqual(a[k],b[k])

    def test_shared_alliance_context_and_exit_inventory(self):
        c=next(c for c in self.inventory['cases'] if c['id']=='primary-2014-14')
        self.assertEqual(sum(r['categoryId']=='internetmana' for r in c['roster']),1)
        self.assertFalse(any(r['categoryId']=='manamovement' for r in c['roster']))
        self.assertTrue(all(r['code'] not in ('INT','MNA') for r in c['reports']))
        self.assertTrue(any(r['code']=='MNA' for r in c['rejectedReports']))
        c=next(c for c in self.inventory['cases'] if c['id']=='primary-2023-14')
        prior={r['categoryId']:r for r in c['systems']['model']['weights']['prior_only']}
        self.assertEqual(prior['freedomsnz']['basis'],'neutral_seed_assumption')
        self.assertEqual(prior['oneparty']['basis'],'supported_prior')

    def test_actual_draw_ids_roundtrip_and_explicit_preservation(self):
        for c in self.inventory['cases']:
            original=read(NATIONAL/c['archivePath'])
            for policy in ('recent_report_prior','prior_only'):
                result=read(OUT/f"allocations/{c['id']}-{policy}-model.json.gz")
                self.assertEqual(result['drawIds'],original['draws']['drawIds'])
                self.assertEqual(result['drawNamespace'],c['drawNamespace'])
                mapping={r['categoryId']:j for j,r in enumerate(c['roster'])}
                from scripts.polling.category_interface.common import CORE
                for name in ('current','electionDay'):
                    for i in (0,3999,7999):
                        a=result['arrays'][name][i];b=original['draws'][name][i]
                        self.assertAlmostEqual(fsum(a),1,places=12)
                        for j,p in enumerate(original['categories']):
                            if p!='OTH':self.assertEqual(a[mapping[CORE[p]]],b[j])
                        rest=fsum(a[mapping[w['categoryId']]] for w in c['systems']['model']['weights'][policy])
                        self.assertAlmostEqual(rest,b[-1],places=12)


class ExternalContractTests(unittest.TestCase):
    def test_subset_is_not_renormalized(self):
        score=point_score({'A':.4,'B':.2},{'A':.3,'B':.2},['A','B'])
        self.assertAlmostEqual(score['maePP'],5)
        self.assertAlmostEqual(score['rmsePP'],50**.5)
        self.assertEqual(score['categoryCount'],2)
        p=pooled([score,point_score({'A':.3,'B':.3},{'A':.3,'B':.2},['A','B'])],['A','B'])
        self.assertAlmostEqual(p['maePP'],5)
        self.assertAlmostEqual(p['partyBiasPP']['A'],5)

    def test_external_exact_dates_and_absent_category(self):
        inventory=audit()
        self.assertEqual(inventory['pointMatchedCases'],2)
        c=next(c for c in inventory['cases'] if c['year']==2020)
        self.assertEqual(c['status'],'unavailable')
        self.assertIn('MRI',c['reason'])
        external=read(RAW/'output_backtest_cases_gauss_2017_h8.json')
        own={'electionYear':2017,'horizonDays':56,'cutoff':'2017-07-29T23:59:59+12:00'}
        validate_case(external,2017,own)
        changed=copy.deepcopy(external);changed['cutoff']='2017-07-30'
        with self.assertRaises(ValueError):validate_case(changed,2017,own)
        missing=read(RAW/'output_backtest_cases_gauss_2020_h8.json')
        with self.assertRaises(ValueError):coarsen_means(missing)

    def test_recover_signed_case_means_not_aggregate_score(self):
        from scripts.polling.category_interface.external import ALIASES
        c={'parties':list(ALIASES),'outcome':{p:.1 for p in ALIASES}}
        row={f'error_pp[{p}]':str(2) for p in ALIASES};row['mae_pp']='99'
        result=named_means(c,row)
        self.assertTrue(all(abs(v-.12)<1e-15 for v in result.values()))
        row['mae_pp']='0'
        self.assertEqual(result,named_means(c,row))

    def test_coarse_top_and_small_parties_no_duplicate(self):
        from scripts.polling.category_interface.external import ALIASES
        case={'parties':list(ALIASES)+['TOP','Other'],'forecast_mean':{p:.1 for p in ALIASES}}
        case['forecast_mean'].update({'TOP':.1,'Other':.3})
        result=coarsen_means(case)
        self.assertAlmostEqual(result['OTH'],.4)
        self.assertAlmostEqual(fsum(result.values()),1)
