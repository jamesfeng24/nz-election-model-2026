"""Independent anchor arithmetic, bounded classification diagnostics and preservation."""
import argparse
from collections import Counter
from fractions import Fraction
import json

import numpy as np
from scripts.models.asymmetric_response.design import initial_direction
from .common import ROOT, DEST, DESIGN, read, digest, verify_inputs, preserve, phase_write, phase_manifest, prefit


def verify_prefit():
    manifest=json.loads((DEST/'prefit-manifest.json').read_bytes())
    for name,expected in manifest['outputSha256'].items():
        if digest(str((DEST/name).relative_to(ROOT)))!=expected:
            raise ValueError('Frozen pre-calculation bytes changed: '+name)
    for path,expected in manifest['generatorSha256'].items():
        if digest(path)!=expected:
            raise ValueError('Frozen inventory generator changed: '+path)
    if prefit()!=json.loads((DEST/'sample-inventory.json').read_bytes()):
        raise ValueError('Frozen sample reproduction failed')


def anchor_audit(case, snapshots, responses):
    estimates=case['anchor']['estimates']
    checks=[]
    details=[]
    for estimate in estimates:
        rows=[r for r in snapshots if r['id'] in estimate['retainedSnapshotIds']]
        n=np.array([float(Fraction(r['nationalSupport'])) for r in rows])
        g=np.array([float(Fraction(r['generalPremium'])) for r in rows])
        b=float(np.sum((n-n.mean())*(g-g.mean()))/np.sum((n-n.mean())*(n-n.mean())))
        a=float(g.mean()); crossing=float(n.mean()-a/b)
        passed=(abs(b-estimate['slope'])<=1e-8 and abs(a-estimate['interceptAtMean'])<=1e-8
                and abs(crossing-estimate['anchor'])<=1e-8)
        if not passed:
            raise ValueError('Independent centered covariance anchor mismatch')
        checks.append({'omittedYear':estimate['omittedYear'],'independentCovarianceAgreementWithin1eMinus8':passed})
        details.append({'omittedYear':estimate['omittedYear'],'crossingPercent':round(crossing*100,6),
                        'slope':round(b,6),'extrapolated':estimate['extrapolated'],
                        'rank':estimate['rank'],'scaledCondition':estimate['scaledCondition']})
    classifications=[]
    # Use full six raw inputs for classifying source/target environments; anchor fits retain their own earlier subsets.
    national=read(DESIGN+'input-inventory.json')['electionAggregateInputs']
    by_key={(r['party'],r['year']):r for r in national}
    transitions=sorted({(r['sourceYear'],r['targetYear']) for r in responses})
    for sy,ty in transitions:
        n0=by_key[(case['party'],sy)]['nationalSupport']; n1=by_key[(case['party'],ty)]['nationalSupport']
        labels=[]
        for e in estimates:
            root=e['anchor']
            if root is not None and 0<=root<=1:
                labels.append({'omittedYear':e['omittedYear'],**initial_direction(n0,n1,str(root)),
                               'rootMeetsRangeGate':not e['extrapolated']})
        central=next((r for r in labels if r['omittedYear'] is None),None)
        classifications.append({'sourceYear':sy,'targetYear':ty,'records':sum(r['sourceYear']==sy and r['targetYear']==ty for r in responses),
            'centralRegime':central['regime'] if central else None,
            'stableAcrossDiagnosticRoots':bool(labels) and len({r['T'] for r in labels})==1,
            'diagnosticRoots':labels,'admittedToResponseFit':case['status']=='available'})
    counts=Counter(c['centralRegime'] for c in classifications if c['centralRegime'] is not None)
    record_counts=Counter()
    for c in classifications:
        if c['centralRegime'] is not None:record_counts[c['centralRegime']]+=c['records']
    return {'party':case['party'],'id':case.get('id',case['party']), 'anchorStatus':case['anchor']['status'],
            'anchorFailure':case['anchor'].get('reason'),'independentChecks':checks,'snapshotDeletionDiagnostics':details,
            'centralRootEnvironmentCounts':dict(counts),'centralRootRecordCounts':dict(record_counts),
            'transitionClassificationDiagnostics':classifications,
            'interpretation':'diagnostic_only_when_anchor_guard_fails; no_accepted_anchor_set_no_response_estimate; finite_deletions_not_confidence_interval'}


def build():
    inputs=read(DESIGN+'input-inventory.json')
    aggs={r['id']:r for r in inputs['electionAggregateInputs']}
    records=read('data/processed/models/exact-geography-retests/inventory.json')['responseRecords']
    by_id={r['id']:r for r in records}
    chronological=json.loads((DEST/'chronological-construction.json').read_bytes())
    descriptive=json.loads((DEST/'descriptive-construction.json').read_bytes())
    cases=[]
    for case in chronological['cases']:
        snapshots=[aggs[i] for i in case['anchor']['snapshotIds']]
        rows=[by_id[i] for i in case['trainingIds']+case['evaluationIds']]
        cases.append(anchor_audit(case,snapshots,rows))
    full=[]
    for case in descriptive['cases']:
        snapshots=[aggs[i] for i in case['anchor']['snapshotIds']]
        full.append(anchor_audit(case,snapshots,[by_id[i] for i in case['responseIds']]))
    return {'chronologicalAnchorDiagnostics':cases,'descriptiveAnchorDiagnostics':full,
            'independentAnchorChecks':sum(len(c['independentChecks']) for c in cases+full),
            'historicalResponseChecks':'not_applicable_no_admitted_fit_or_error; synthetic_response_arithmetic_tested',
            'operationalSelection':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--verify-preservation',action='store_true')
    args=p.parse_args();verify_inputs();verify_prefit()
    result=build();phase_write('independent-anchor-audit.json',result,args.check)
    phase_manifest('independent',['independent-anchor-audit.json'],['scripts/models/asymmetric_response_test/verification.py'],args.check)
    print({'independentAnchorChecks':result['independentAnchorChecks']})
    if args.verify_preservation:print({'preservedPriorArtifacts':preserve()})


if __name__=='__main__':
    main()
