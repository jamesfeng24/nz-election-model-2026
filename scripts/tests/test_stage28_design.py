"""Stage28 feasibility tests; all artificial values below are SYNTHETIC, not fits."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.checkpoints import stage28_design as run
from scripts.checkpoints import stage25_availability as availability
from scripts.models.asymmetric_response.design import (
    initial_direction, national_regime, source_state_classifier, anchor_guard, regime_rank_guard)
from scripts.models.asymmetric_response.inputs import election_inputs, fold_inventory


class Stage28DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elections = {y:run.read(f'data/processed/elections/{y}.json')
                         for y in (2008,2011,2014,2017,2020,2023)}
        cls.folds = run.read(run.GEO+'fold-plan.json')['folds']
        cls.responses = run.read(run.RESPONSE)['responseRecords']
        cls.aggregates = [r for d in cls.elections.values() for r in election_inputs(d)]

    def test_synthetic_constant_response_can_cross_parity_without_asymmetry(self):
        candidate = lambda n: Fraction('0.18')+Fraction('0.6')*n
        anchor = Fraction('0.45')
        self.assertEqual(candidate(anchor)-anchor, 0)
        self.assertGreater(candidate(Fraction('.3'))-Fraction('.3'), 0)
        self.assertLess(candidate(Fraction('.7'))-Fraction('.7'), 0)
        for source,target in ((Fraction('.3'),Fraction('.4')),
                              (Fraction('.7'),Fraction('.8'))):
            self.assertEqual((candidate(target)-candidate(source))/(target-source), Fraction('.6'))
        self.assertEqual(initial_direction('.3','.4',anchor)['T'], 1)
        self.assertEqual(initial_direction('.7','.8',anchor)['T'], 0)

    def test_initial_direction_ties_and_overshoot(self):
        self.assertEqual(initial_direction('.3','.3','.45')['T'], None)
        self.assertEqual(initial_direction('.45','.4','.45')['T'], 0)
        self.assertEqual(initial_direction('.45','.5','.45')['T'], 0)
        overshoot = initial_direction('.3','.8','.45')
        self.assertEqual(overshoot['T'], 1)
        self.assertTrue(overshoot['crossesAnchor'])
        self.assertGreater(abs(Fraction('.8')-Fraction('.45')), abs(Fraction('.3')-Fraction('.45')))
        with self.assertRaises(ValueError):
            initial_direction('-0.1','.3','.4')

    def test_national_local_disagreement_is_reported_not_reclassified(self):
        row = {'nationalSource':'.3','nationalTarget':'.4','partySource':'.4','partyTarget':'.3'}
        result = national_regime(row, ['.45'])
        self.assertEqual(result['T'],1)
        self.assertTrue(result['nationalLocalOppose'])
        neutral = {**row,'nationalTarget':'.3'}
        self.assertEqual(national_regime(neutral,['.45'])['reason'],'zero_national_movement')

    def test_missing_and_uncertain_anchors_abstain(self):
        row = {'nationalSource':'.3','nationalTarget':'.4','partySource':'.4','partyTarget':'.5'}
        self.assertEqual(national_regime(row,[])['reason'],'missing_anchor')
        self.assertEqual(national_regime(row,['.2','.45'])['reason'],'anchor_stability_disagreement')
        self.assertEqual(national_regime(row,['.4','.45'])['T'],1)

    def test_classifier_input_whitelist_ignores_target_outcomes_and_identity(self):
        row = {'nationalSource':'.3','nationalTarget':'.4','partySource':'.4','partyTarget':'.5',
               'c0':'.35','c1':'.6','targetWinner':True,'identity':'confirmed'}
        mutated = {**row,'c0':'.8','c1':'.1','targetWinner':False,'identity':'unresolved',
                   'targetResidual':99,'targetCandidateDenominator':1}
        self.assertEqual(national_regime(row,['.45']),national_regime(mutated,['.45']))

    def test_deferred_source_state_classifier_exposes_mechanical_dependence(self):
        low = source_state_classifier('.35','.05','.4')
        high = source_state_classifier('.45','.05','.4')
        self.assertEqual((low['T'],high['T']),(1,0))
        self.assertEqual(low['sharedOutcomeAndClassifierInput'],'C0')
        # The same perturbed C0 also changes C1-C0; no causal inference follows.
        self.assertNotEqual(Fraction('.5')-Fraction('.35'), Fraction('.5')-Fraction('.45'))

    def synthetic_anchor_case(self):
        snapshots = [{'year':i,'nationalSupport':n,'generalPremium':g}
            for i,n,g in ((1,'.2','.02'),(2,'.3','.01'),(3,'.6','-.01'),(4,'.7','-.02'))]
        estimates = [{'omittedYear':omitted,'slope':-.1,'anchor':.45,'rank':2,'scaledCondition':2}
                     for omitted in (None,1,2,3,4)]
        return snapshots,estimates

    def test_anchor_support_uncertainty_and_ratio_gates(self):
        snapshots,estimates = self.synthetic_anchor_case()
        self.assertEqual(anchor_guard(snapshots,estimates)['status'],'available')
        self.assertEqual(anchor_guard(snapshots[:3],estimates)['reason'],'fewer_than_four_completed_elections')
        weak = deepcopy(estimates);weak[1]['slope']=0
        self.assertEqual(anchor_guard(snapshots,weak)['status'],'abstain')
        crossing = deepcopy(estimates);crossing[1]['anchor']=.1
        self.assertEqual(anchor_guard(snapshots,crossing)['reason'],'extrapolated_crossing')
        unstable = deepcopy(estimates);unstable[2]['slope']=.1
        self.assertEqual(anchor_guard(snapshots,unstable)['reason'],'slope_sign_unstable')
        positive = [{**r,'generalPremium':'.01'} for r in snapshots]
        self.assertEqual(anchor_guard(positive,estimates)['reason'],'no_observed_premium_sign_bracket')
        with self.assertRaises(ValueError):
            anchor_guard(snapshots+[snapshots[0]],estimates)

    def synthetic_regime_rows(self):
        return [{'environmentId':f'synthetic-{i}', 'T':i%2,'x':(.01,.03,.05,.08,.1)[j]}
                for i in range(4) for j in range(5)]

    def test_regime_environment_counts_and_rank(self):
        rows = self.synthetic_regime_rows()
        self.assertEqual(regime_rank_guard(rows)['status'],'available')
        many_seats = [{**r,'environmentId':'single-'+str(r['T'])} for r in rows]*20
        self.assertEqual(regime_rank_guard(many_seats)['reason'],'fewer_than_two_transition_environments_per_regime')
        deficient = [{**r,'x':.01} for r in rows]
        self.assertEqual(regime_rank_guard(deficient)['reason'],'rank_deficient_or_weak_condition')
        conflict = deepcopy(rows);conflict[0]['T']=1
        with self.assertRaises(ValueError):
            regime_rank_guard(conflict)

    def test_population_and_denominator_accounting(self):
        for y in self.elections:
            rows = election_inputs(self.elections[y])
            self.assertEqual(rows[0]['generalContestIds'],rows[1]['generalContestIds'])
            for r in rows:
                self.assertEqual(Fraction(r['generalPremium']),
                    Fraction(r['candidateVotes'],r['validCandidateVotes'])-
                    Fraction(r['partyVotesMatchedGeneral'],r['validPartyVotesMatchedGeneral']))
                self.assertEqual(Fraction(r['nationalSupport']),
                    Fraction(r['nationalPartyVotes'],r['nationalValidPartyVotes']))
                self.assertEqual(r['publicationByForecastCutoff'],'unknown_not_verified')
        r=next(r for r in self.aggregates if r['year']==2023)
        self.assertEqual(r['partyPopulationOmittedVotes'],42399)
        self.assertEqual(r['excludedGeneralContestIds'],['nz-general-2023-electorate-39'])
        self.assertNotEqual(r['validPartyVotesMatchedGeneral'],r['nationalValidPartyVotes'])

    def test_ambiguous_missing_aggregate_is_not_zero_or_selected_subset(self):
        missing=deepcopy(self.elections[2008]);missing['electorates'][0]['candidates']=[
            c for c in missing['electorates'][0]['candidates'] if c['partyKey']!='nationalparty']
        with self.assertRaises(ValueError):election_inputs(missing)
        population=deepcopy(self.elections[2008]);population['nationalControls']['party']['national']['validVotes']+=1
        with self.assertRaises(ValueError):election_inputs(population)

    def test_fold_counts_and_chronology_no_future_anchor(self):
        folds=fold_inventory(self.folds,self.responses,self.aggregates)
        for protocol,expected in (('expanding_window',[0,63,83,147,181]),
                                  ('more_separated',[0,0,63,83,147])):
            selected=[f for f in folds if f['party']=='nationalparty' and f['protocol']==protocol]
            self.assertEqual([f['trainingCount'] for f in selected],expected)
            self.assertEqual([f['evaluationCount'] for f in selected],[63,20,64,34,64])
            self.assertEqual([f['anchorSnapshotCount'] for f in selected],
                             [1,2,3,4,5] if protocol=='expanding_window' else [0,1,2,3,4])
            for f in selected:
                self.assertTrue(all(int(i.split(':')[0])<=f['sourceYear'] for i in f['permittedAnchorSnapshotIds']))
        possible=[f for f in folds if f['countGatesPotentiallyFeasible']]
        self.assertEqual([(f['targetYear'],f['protocol']) for f in possible],[(2023,'expanding_window')]*2)
        bad=deepcopy(self.folds)
        f=next(f for f in bad if f['family']=='nat_lab_response' and f['targetYear']==2014)
        f['trainingIds']=[f['evaluationIds'][0]]
        with self.assertRaises(ValueError):fold_inventory(bad,self.responses,self.aggregates)

    def test_actual_dependency_path_heldout_candidate_results_do_not_change_fold_inputs(self):
        baseline=fold_inventory(self.folds,self.responses,self.aggregates)
        changed=deepcopy(self.elections[2023])
        for seat in changed['electorates']:
            seat['winnerCandidateId']='mutated'
            for c in seat['candidates']:
                c['votes']=1;c['identity']='mutated';c['residual']=999
        updated=[r for r in self.aggregates if r['year']!=2023]+election_inputs(changed)
        self.assertEqual(fold_inventory(self.folds,self.responses,updated),baseline)
        earlier=deepcopy(self.elections[2008])
        next(c for c in earlier['electorates'][0]['candidates'] if c['partyKey']=='nationalparty')['votes']+=100
        self.assertNotEqual(election_inputs(earlier),election_inputs(self.elections[2008]))

    def test_required_sources_allow_additions_reject_changes_duplicates_and_raw_bytes(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);raw=root/'raw';raw.write_bytes(b'synthetic')
            record={'id':'required','rawPath':'raw','sha256':run.sha256(b'synthetic').hexdigest()}
            def verify(records):
                with patch.object(availability,'ROOT',root),patch.object(availability,'read',return_value={'sources':records}):
                    availability.verify_contract({'requiredSources':[record]})
            verify([record,{'id':'unrelated'}])
            for records in ([],[{**record,'metadata':'changed'}],[record,record]):
                with self.assertRaises(ValueError):verify(records)
            raw.write_bytes(b'altered')
            with self.assertRaises(ValueError):verify([record])

    def test_deterministic_generation_and_prior_preservation(self):
        first,second=run.outputs(),run.outputs()
        self.assertEqual(first,second)
        for name,value in first.items():
            self.assertEqual(run.encode(value),(run.DEST/name).read_bytes())
        # The appendable live registry is checked by required-record contracts.
        self.assertEqual(run.verify_preservation(include_registry=False),1376)


if __name__=='__main__':unittest.main()
