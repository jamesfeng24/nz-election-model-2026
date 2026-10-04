"""Reproduce a dated target/slate readiness snapshot, never forecast votes.

python -m scripts.readiness.run [--check]
Refresh: --manifest NEW.json --previous OLD/snapshot.json --output NEW_DIRECTORY
"""
import argparse
from collections import Counter
from pathlib import Path
from scripts.evidence.practical_candidate_linkage.names import alias_pairs
from .common import ROOT, load, save, digest, verify_sources, verify_preservation
from .geography import official_roster, build_frame
from .registry import party_relationships, build_registry, snapshot_changes, verify_register, utc
from .slate_sources import extract_claims
from .linkage import build_links
from .features import candidate_features, seat_readiness, s_feature

INPUTS = ['data/processed/boundaries/2023-2026/crosswalk.json',
    'data/processed/boundaries/2023-2026/party-votes.json',
    'data/processed/evidence/practical-candidate-linkage/occurrences.json',
    'data/processed/evidence/practical-candidate-linkage/aliases.json',
    'data/processed/models/candidate-overperformance/occurrences.json',
    'data/processed/split-votes/2023.json']


def retain_prior_claims(claims, previous, sources):
    """Keep previously supported assertions until explicit evidence changes status."""
    current = list(claims)
    signatures = {(sources[c['sourceKey']]['id'], c.get('locator'),c['displayName'],c['sourceElectorateLabel'],c['status']) for c in current}
    for old in previous.get('claimHistory',[]) if previous else []:
        signature=(old['sourceId'],old.get('locator'),old['displayName'],old['sourceElectorateLabel'],old['status'])
        if signature in signatures:
            continue
        if digest(old['rawPath'])!=old['rawSha256']:
            raise ValueError('Prior snapshot raw evidence changed during refresh')
        lookup='prior:'+old['sourceId']
        sources[lookup]={'id':old['sourceId'],'originalKey':old['sourceKey'],'url':old['sourceURL'],
            'retrievedAt':old['retrievalDate'],'rawPath':old['rawPath'],'sha256':old['rawSha256']}
        current.append(dict(old,sourceKey=lookup))
    return current


def build(manifest, *, evidence=None, occurrences=None, residuals=None, claims=None, previous=None, completeness=()):
    occurrences = load(INPUTS[2])['records'] if occurrences is None else occurrences
    residuals = load(INPUTS[4])['records'] if residuals is None else residuals
    crosswalk, party = load(INPUTS[0]), load(INPUTS[1])
    raw_root = ROOT / Path(manifest['sources'][0]['rawPath']).parent
    evidence = extract_claims(raw_root) if evidence is None else evidence
    sources = {s['key']:s for s in manifest['sources'] if not s['rawPath'].endswith('.pdf')}
    schedule = load(str((raw_root / 'schedule-c-readable.json').relative_to(ROOT)))
    frame = build_frame(crosswalk,party,occurrences,official_roster(schedule))
    parties = party_relationships()
    # Register current schema against the actual current official extraction, not guessed party labels.
    register = load(str((raw_root / 'party-register-readable.json').relative_to(ROOT)))
    verify_register(register)
    register_path = str((raw_root/'party-register-readable.json').relative_to(ROOT))
    schedule_path = str((raw_root/'schedule-c-readable.json').relative_to(ROOT))
    for p in parties:p['evidencePath']=register_path
    for seat in frame:seat['evidencePaths'][0]=schedule_path
    claims = retain_prior_claims(evidence['claims'] if claims is None else claims,previous,sources)
    registry = build_registry(claims,frame,sources,
                              manifest['acquisitionCutoffUTC'],completeness)
    links = build_links(registry['occurrences'],occurrences,alias_pairs(load(INPUTS[3])),frame,parties)
    res = {r['candidateOccurrenceId']:r for r in residuals if r['year']==2023}
    splits = load(INPUTS[5])['matrices']
    features = candidate_features(registry['occurrences'],links,frame,parties,occurrences,res,splits)
    readiness = seat_readiness(frame,registry['occurrences'],features,registry['completeSlateDeclarations'])
    relationships = {p['targetGroupKey']:p for p in parties}
    source_features = [{'targetElectorateId':seat['targetElectorateId'], 'partyGroupKey':p['targetGroupKey'],
        'targetCandidateIdentityRequired':False, 'S':s_feature({'originalAffiliation':p['targetGroupKey']},seat,relationships,occurrences,splits)}
        for seat in frame for p in parties]
    for seat in readiness:
        source_rows = [r for r in source_features if r['targetElectorateId']==seat['targetElectorateId']]
        seat['sourcePartySeatSCounts'] = dict(Counter(r['S']['status'] for r in source_rows))
        source_id = next(r['exactSourceElectorateId'] for r in frame if r['targetElectorateId']==seat['targetElectorateId'])
        local_residuals = [r for r in res.values() if r['electorateId']==source_id]
        seat['sourceResidualEvidenceCounts'] = {'occurrences':len(local_residuals), 'finiteResiduals':sum(r.get('normalizedPremium') is not None for r in local_residuals), 'targetIdentityStillRequired':True}
    snapshot = dict(registry, stage=40,schemaVersion=1,snapshotDateNZ=manifest['snapshotDateNZ'],
        acquisitionCutoffUTC=manifest['acquisitionCutoffUTC'],
        electionDay='2026-11-07',nominationCloseNZ='2026-10-08T12:00:00+13:00',
        officialNominationStatus='open_at_cutoff; final_candidate_publication_after_close' if utc(manifest['acquisitionCutoffUTC']) < utc('2026-10-07T23:00:00Z') else 'closed; completeness_requires_preserved_official_publication',
        context=evidence['context'],sourceGaps=evidence['gaps']+manifest['unresolved'],
        sourceCounts=evidence['sourceCounts'], operationalSelection=None,
        forecastProduced=False,developmentPreferences={'national':'external_gauss_provisional','candidate':'S+R_preferred','activeAlternative':'S','control':'baseline'})
    changes = snapshot_changes(previous or {},snapshot)
    counts = {'seatsByScope':dict(Counter(s['scope'] for s in frame)),
        'exactSeatsByScope':dict(Counter(s['scope'] for s in frame if s['exactSourceElectorateId'])),
        'heldExactGeneralSeats':sum(s['scope']=='general' and s['sourceCandidateContestStatus']==['held'] for s in frame),
        'candidateOccurrences':len(registry['occurrences']),
        'claims':len(registry['claimHistory']), 'unmatchedClaims':len(registry['unmatchedClaims']),
        'candidateStatuses':dict(Counter(c['status'] for c in registry['occurrences'])),
        'candidatesByParty':dict(Counter(c['originalAffiliation'] for c in registry['occurrences'])),
        'candidateSeatsByScope':dict(Counter(s['scope'] for s in readiness if s['knownCandidateCount'])),
        'slateStatuses':dict(Counter(s['slateStatus'] for s in readiness)),
        'broadLinks':sum(e['broadAccepted'] for e in links),'strictLinks':sum(e['strictAccepted'] for e in links),
        'linkExceptions':dict(Counter(reason for e in links for reason in e['exceptionReasons'])),
        'SReadiness':dict(Counter(r['S']['status'] for r in features)),
        'sourcePartySeatSReadiness':dict(Counter(r['S']['status'] for r in source_features)),
        'RReadiness':dict(Counter(r['R']['status'] for r in features)),
        'strictRReadiness':dict(Counter(r['RStrict']['status'] for r in features)),
        'sourceBudget':{'resources':len(manifest['sources']),'resourceCap':manifest['resourceCap'],'queries':len(manifest['queries']),'queryCap':manifest['queryCap']}}
    return {'snapshot.json':snapshot,'target-frame.json':{'records':frame},
        'party-relationships.json':{'records':parties,'actualBallotRosterConfirmed':False},
        'identity-links.json':{'records':links,'automaticTransitiveMerging':False},
        'party-seat-feature-readiness.json':{'records':source_features},'candidate-feature-readiness.json':{'records':features},'seat-readiness.json':{'records':readiness},
        'changes.json':{'comparison':'no_previous_live_snapshot' if previous is None else 'previous_dated_snapshot',
            'records':changes,'affectedSeatIds':sorted({c['targetElectorateId'] for c in changes}),
            'refreshRequiresGlobalIdentityCollisionCheck':True,
            'candidateFeatureInvalidationSeatIds':sorted(s['targetElectorateId'] for s in frame) if changes else [],
            'sourceSchemaChangeInvalidatesAllPartyInputs':True},'coverage.json':counts}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--manifest',default='data/processed/forecast-readiness/acquisition-manifest.json')
    parser.add_argument('--previous')
    parser.add_argument('--output',default='data/processed/forecast-readiness/snapshots/2026-10-05')
    parser.add_argument('--claim-events',help='complete source-assertion ledger override, not identity adjudications')
    parser.add_argument('--completeness',help='dated official complete nomination declarations only')
    args=parser.parse_args();manifest=load(args.manifest);verify_sources(manifest)
    results=build(manifest,previous=load(args.previous) if args.previous else None,
        claims=load(args.claim_events)['claims'] if args.claim_events else None,
        completeness=load(args.completeness)['records'] if args.completeness else ())
    results['provenance.json']={'stage':40,'manifestPath':args.manifest,'manifestSha256':digest(args.manifest),
        'consumedInputs':{p:digest(p) for p in INPUTS},
        'refreshInputs':{p:digest(p) for p in (args.previous,args.claim_events,args.completeness) if p},
        'reusedHelperCode':{p:digest(p) for p in ('scripts/evidence/practical_candidate_linkage/names.py','scripts/checkpoints/complete_share_features.py','scripts/transform/historical.py')},
        'consumedCode':{str(p.relative_to(ROOT)):digest(str(p.relative_to(ROOT))) for p in sorted((ROOT/'scripts/readiness').glob('*.py'))},
        'preservation':verify_preservation(), 'noPredictionsOrFitting':True,
        'dataAvailability':'raw responses and declared tool-rendered extraction; undated publication not certified'}
    for name,value in results.items(): save(args.output+'/'+name,value,args.check)
    print(results['coverage.json'])


if __name__=='__main__':main()
