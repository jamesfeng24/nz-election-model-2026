"""Stage35 data/cutoff contracts; synthetic fixtures are never historical results."""
import copy
import json
from pathlib import Path
import unittest
from scripts.polling.national_foundation.records import observation,date_bounds,record,parse_bulk,deduplicate
from scripts.polling.national_foundation.timing import select,timestamp,select_revisions
from scripts.polling.national_foundation.contracts import build_inputs,output_contract,reported_rows
from scripts.polling.national_foundation.run import construct,verify_sources,preservation,ROOT,RAW
from scripts.polling.national_foundation.design import anchors,category,specification


def synthetic(**updates):
    r=record(2023,{'date':['2023-09-01','2023-09-05'],'org':'COL','n':'1000',
                   'NAT':'40','LAB':'30','MRI':'0'}, {'sourceId':'synthetic'})
    r.update(updates);return r


class Stage35Polling(unittest.TestCase):
    def test_rounded_not_integer_counts(self):
        o=observation('31.2');self.assertEqual(o['bounds'],[.3115,.3125]);self.assertEqual(o['roundingUnit'],.001)
        self.assertNotIn('respondents',o)

    def test_missing_not_zero(self):
        self.assertIsNone(observation('~')['bounds']);self.assertEqual(observation('0')['bounds'],[0,.005])

    def test_threshold_not_midpoint(self):
        x=observation('<1');self.assertIsNone(x['share']);self.assertEqual(x['bounds'],[0,.01])

    def test_bad_values(self):
        for x in ('NaN','-1','101','<0'):
            with self.assertRaises(ValueError):observation(x)

    def test_unknown_days_and_bad_calendar(self):
        self.assertEqual(date_bounds('2020-02-00'),['2020-02-01','2020-02-29'])
        with self.assertRaises(ValueError):date_bounds('2015-09-31')

    def test_bulk_rejects_date_and_skips_results(self):
        text="'2017':\n- {date: [2017-09-23], NAT: 44.4}\n- {date: [2015-09-31], org: ROY, NAT: 50}\n"
        r,a=parse_bulk(text,'synthetic');self.assertEqual(r,[]);self.assertEqual(len(a),2)
        self.assertEqual(a[1]['role'],'parse_error')

    def test_publication_not_field_completion(self):
        r=synthetic();got,_=select([r],'2023-09-07T23:59:59+12:00');self.assertFalse(got)
        got,_=select([r],'2023-09-11T00:00:00+12:00');self.assertTrue(got)
        self.assertEqual(r['publicationConfidence'],'unresolved')

    def test_timezone_boundary(self):
        r=synthetic(publication='2023-09-28T05:01:11Z',publicationConfidence='verified')
        self.assertFalse(select([r],'2023-09-28T18:01:10+13:00')[0])
        self.assertTrue(select([r],'2023-09-28T18:01:11+13:00')[0])
        with self.assertRaises(ValueError):timestamp('2023-09-28T18:00:00')

    def test_verified_only_does_not_promote_lag(self):
        self.assertFalse(select([synthetic()],'2023-10-01T00:00:00Z',verified_only=True)[0])

    def test_future_publication_excluded(self):
        r=synthetic(publication='2023-10-02T00:00:00Z',publicationConfidence='verified')
        self.assertFalse(select([r],'2023-10-01T00:00:00Z')[0])

    def test_revision_selection_before_cutoff(self):
        a=synthetic(publication='2023-09-07T00:00:00Z');b=copy.deepcopy(a);b['publication']='2023-09-20T00:00:00Z';b['sampleSize']=2000
        self.assertEqual(select_revisions([a,b],'2023-09-10T00:00:00Z'),[a])

    def test_duplicate_and_conflict(self):
        a=synthetic();b=copy.deepcopy(a);r,audit=deduplicate([a,b]);self.assertEqual(len(r),1);self.assertEqual(len(audit),1)
        a=synthetic();b=copy.deepcopy(a);b['sampleSize']=900;r,_=deduplicate([a,b]);self.assertEqual(r[0]['status'],'conflicting_reports')

    def test_overlapping_wave_only_once(self):
        a=synthetic();b=record(2023,{'date':['2023-09-04','2023-09-08'],'org':'COL','NAT':'41'}, {'sourceId':'synthetic'})
        got,excluded=select([a,b],'2023-10-01T00:00:00Z');self.assertEqual(len(got),1)
        self.assertEqual(excluded[0]['reason'],'overlapping_sample_conservative_latest')

    def test_partial_model_rows_not_zero_fill(self):
        rows=reported_rows(synthetic(),['NAT','LAB','TOP','MRI']);self.assertEqual([r['category'] for r in rows],['NAT','LAB','MRI'])

    def test_schema_other_and_alliance(self):
        self.assertEqual(category('Internet MANA'),'OTH');self.assertEqual(category('Vision New Zealand'),'OTH')
        self.assertEqual(category('Te Pāti Māori'),'MRI');s=specification()
        self.assertNotIn('TOP',s['categories']['2014']);self.assertIn('TOP',s['categories']['2017'])

    def test_real_panel_coverage_and_invalid_retention(self):
        records,audit=construct();self.assertEqual(len(records),496);self.assertEqual(len({r['id'] for r in records}),496)
        self.assertEqual(sum(r['cycle']==2014 for r in records),136)
        self.assertEqual(sum(x['role']=='parse_error' for x in audit['nonPollAndInvalidRows']),1)
        self.assertEqual(sum(r['status']=='conflicting_reports' for r in records),0)

    def test_real_original_publication_separate_from_aggregator(self):
        records,_=construct();r=next(r for r in records if r['fieldworkRaw']==['2023-08-00','2023-09-00'] and r['pollsterCode']=='ROY')
        self.assertEqual(r['fieldworkEndBounds'],['2023-08-31','2023-08-31']);self.assertTrue(r['publication'].startswith('2023-09-05'))
        self.assertEqual(r['fieldworkRaw'],['2023-08-00','2023-09-00'])

    def test_actual_pipeline_heldout_result_independence(self):
        polls,_=construct();results=anchors();cutoff='2017-09-09T23:59:59+12:00'
        before=build_inputs(polls,cutoff,results)
        altered=copy.deepcopy(results)
        for r in altered:
            if r['year']>=2017:r['shares']={'NAT':999};r['winner']='fiction';r['candidateVotes']=-1
        after=build_inputs(polls,cutoff,altered);self.assertEqual(before,after)
        self.assertEqual([r['year'] for r in before['completedAnchors']],[2011,2014])

    def test_earlier_result_legitimately_available(self):
        a=anchors();out=build_inputs([], '2020-10-03T23:59:59+13:00', a)
        self.assertEqual([r['year'] for r in out['completedAnchors']],[2011,2014,2017])

    def test_original_counts_denominator(self):
        r=next(r for r in anchors() if r['year']==2014)
        self.assertEqual(r['validPartyVotes'],2405622);self.assertAlmostEqual(r['shares']['NAT'],1131501/2405622)
        self.assertAlmostEqual(sum(r['shares'].values()),1)

    def test_source_integrity_and_prior_preservation(self):
        ledger=verify_sources();self.assertLessEqual(len(ledger['resources']),60);self.assertEqual(preservation(),1461)

    def test_coherent_synthetic_output(self):
        x={'modelVersion':'synthetic','partySchemaVersion':'synthetic','cutoff':'2023-09-01T00:00:00Z',
          'electionDate':'2023-10-14','informationSet':'synthetic','sourceIds':[], 'assumptionFlags':['synthetic'],
          'expectedCurrentShares':{'NAT':.4,'OTH':.6},'expectedElectionDayShares':{'NAT':.5,'OTH':.5},
          'draws':[{'drawId':'synthetic-1','currentShares':{'NAT':.3,'OTH':.7},'electionDayShares':{'NAT':.4,'OTH':.6}},
                   {'drawId':'synthetic-2','currentShares':{'NAT':.5,'OTH':.5},'electionDayShares':{'NAT':.6,'OTH':.4}}]}
        output_contract(x)
        y=copy.deepcopy(x);y['draws'][1]['drawId']='synthetic-1'
        with self.assertRaises(ValueError):output_contract(y)
        y=copy.deepcopy(x);y['expectedCurrentShares']={'NAT':.7,'OTH':.3}
        with self.assertRaises(ValueError):output_contract(y)


if __name__=='__main__':unittest.main()
