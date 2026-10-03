"""Complete standing-slate/source-only feature inventory; no historical predictions."""
from collections import Counter
from scripts.models.expanded_party_substitution.parties import ballot_vector
from .common import local, read, keyed, PARTY, GEO, LINK, RES
from .residuals import link_index, resolve

S_FIELDS = ('s0Reported','coupledSamePartyPercent','s0CoupledBounds','reportedSamePartyPercent',
            'sourceCandidateId','sourceMatrixId','sourcePartyKey','sourcePartyRowMass',
            'sEvidenceTier','fallbackReasons','splitSourceIds','sourcePublicationByTargetNominationCutoff')


def candidates_for(row, vector, links, occurrences, residuals):
    shares = ballot_vector(vector); result = []; seen_groups = set()
    for original in row['candidates']:
        cid = original['targetOccurrenceId']; group = original['targetPartyKey']
        if group is None:
            if not original['mappingStatus'].startswith('verified_no_party_group_') or original['targetPartySupport'] != 0:
                raise ValueError('Unconfirmed no-group classification')
            constructed = 0.0
        else:
            if group in seen_groups or group not in shares:
                raise ValueError('Duplicate or missing mapped ballot group')
            seen_groups.add(group); constructed = shares[group]
        out = {k:original.get(k) for k in S_FIELDS}
        out.update(targetOccurrenceId=cid, originalAffiliation=original['originalAffiliation'],
                   partyBallotGroupKey=group, mappingStatus=original['mappingStatus'],
                   originalName=occurrences[cid]['sourceCandidateName'],
                   constructedPartySupport=constructed, observedPartySupport=original['targetPartySupport'],
                   R={v:resolve(cid,row,v,links,occurrences,residuals) for v in ('broad','strict')},
                   careerHistoryRequired=False, missingContribution='zero_exponent_not_zero_candidate_strength')
        for view in ('broad','strict'):
            out['R'][view]['availabilityPattern'] = ('both_features' if out['s0Reported'] is not None and out['R'][view]['valueFraction'] is not None
                else 'S_only' if out['s0Reported'] is not None else 'R_only' if out['R'][view]['valueFraction'] is not None else 'neither_feature')
        result.append(out)
    keyed(result,'targetOccurrenceId')
    return result


def build(base=None, party=None, geography=None, occurrences=None, edges=None, accepted=None, residuals=None):
    base = read(PARTY+'input-inventory.json') if base is None else base
    party = read(PARTY+'party-vectors.json') if party is None else party
    geography = read(GEO+'geography.json')['records'] if geography is None else geography
    occurrences = read(LINK+'occurrences.json')['records'] if occurrences is None else occurrences
    edges = read(LINK+'proposed-links.json')['records'] if edges is None else edges
    accepted = read(LINK+'accepted-relationships.json') if accepted is None else accepted
    residuals = read(RES+'occurrences.json')['records'] if residuals is None else residuals
    occ = keyed(occurrences,'candidateOccurrenceId'); res = keyed(residuals,'candidateOccurrenceId')
    vectors = keyed(party['records'],'targetElectorateId'); geo = keyed(geography,'geographyId')
    links = link_index(edges,accepted); rows = []
    for r in base['candidateRecords']:
        g = geo[r['geographyId']]
        if not g['certifiedTwoSidedExact'] or g['scope'] != 'general' or (g['sourceYear'],g['targetYear'],g['dominantPredecessorId'],g['targetElectorateId']) != (r['sourceYear'],r['targetYear'],r['sourceElectorateId'],r['targetElectorateId']):
            raise ValueError('Canonical geography mismatch')
        vector = vectors.get(r['targetElectorateId'])
        row = {k:r[k] for k in ('geographyId','sourceYear','targetYear','sourceElectorateId','targetElectorateId','scope','originalFrame')}
        row.update(status='available',exclusionReasons=[],candidates=[])
        if vector is None:
            row.update(status='abstain',exclusionReasons=['missing_complete_party_vector'])
        else:
            try:
                row['candidates'] = candidates_for(r,vector,links,occ,res)
            except ValueError as error:
                row.update(status='abstain',exclusionReasons=['mapping_or_input_conflict:'+str(error)])
        if row['status']=='abstain':
            # Retain each original standing occurrence even if the entire contest abstains.
            row['candidates']=[{'targetOccurrenceId':c['targetOccurrenceId'],'originalAffiliation':c['originalAffiliation'],
                                'mappingStatus':c['mappingStatus'],'partyBallotGroupKey':c['targetPartyKey'],
                                'status':'contest_abstains','exclusionReasons':row['exclusionReasons']} for c in r['candidates']]
        rows.append(row)
    candidate_ids=[c['targetOccurrenceId'] for r in rows for c in r['candidates']]
    if len(candidate_ids)!=len(set(candidate_ids)):
        raise ValueError('Repeated target occurrence in complete frame')
    all_rows=keyed(rows,'targetElectorateId'); coverage=[]
    for g in geography:
        r=all_rows.get(g['targetElectorateId']); occs=[o for o in occurrences if o['electorateId']==g['targetElectorateId']]
        reason = ('maori_coverage_only' if g['scope']=='maori' else 'not_certified_two_sided_exact' if not g['certifiedTwoSidedExact'] else
                  'cancelled_or_unheld' if g['contestStatus']=='cancelled_or_unheld' else r['exclusionReasons'][0] if r and r['status']!='available' else None if r else 'missing_complete_slate')
        coverage.append({'geographyId':g['geographyId'],'targetElectorateId':g['targetElectorateId'],
                         'sourceYear':g['sourceYear'],'targetYear':g['targetYear'],'scope':g['scope'],
                         'status':'available' if reason is None else 'coverage_only','reason':reason,
                         'standingOccurrenceIds':[o['candidateOccurrenceId'] for o in occs],
                         'candidateCount':len(occs),'modelRecordId':r['targetElectorateId'] if r else None})
    candidate_coverage = []
    for g in geography:
        model = all_rows.get(g['targetElectorateId'])
        reason = next(f['reason'] for f in coverage if f['geographyId']==g['geographyId'])
        for o in occurrences:
            if o['electorateId'] != g['targetElectorateId']:
                continue
            row = {'geographyId':g['geographyId'],'sourceYear':g['sourceYear'],'targetYear':g['targetYear'],
                   'targetElectorateId':g['targetElectorateId'],'targetOccurrenceId':o['candidateOccurrenceId'],
                   'scope':g['scope'],'originalName':o['sourceCandidateName'],'originalAffiliation':o['sourceAffiliation'],
                   'partyBallotGroupKey':o['ballotGroupKey'],'mappingEvidence':o['ballotGroupMapping'],
                   'modelEligibility':reason is None,'exclusionReason':reason,
                   'featureRecordRef':{'contestId':model['targetElectorateId'],'occurrenceId':o['candidateOccurrenceId']} if reason is None else None,
                   'SStatus':'reference_available_model_record' if reason is None else 'not_assessed_outside_general_contract'}
            if reason is not None:
                if g['scope']=='maori' and g['certifiedTwoSidedExact']:
                    context = {'sourceYear':g['sourceYear'],'targetYear':g['targetYear'],
                               'sourceElectorateId':g['dominantPredecessorId'],'targetElectorateId':g['targetElectorateId'],
                               'geographyId':g['geographyId']}
                    row['residualEvidenceAuditOnly']={v:resolve(o['candidateOccurrenceId'],context,v,links,occ,res) for v in ('broad','strict')}
                else:
                    row['RStatus']='not_assessed_cancelled_or_nonexact; no_transport_assumed'
            candidate_coverage.append(row)
    return {'stage':32,'contestRecords':rows,'fullFrame':coverage,'candidateCoverageFrame':candidate_coverage,
            'frameSource':GEO+'geography.json','targetResidualRequired':False,'operationalSelection':None}


def counts(rows, view='broad'):
    cs=[c for r in rows for c in r['candidates'] if r['status']=='available']
    return {'contests':len(rows),'candidates':len(cs),'S':sum(c['s0Reported'] is not None for c in cs),
            'R':sum(c['R'][view]['valueFraction'] is not None for c in cs),
            'patterns':dict(sorted(Counter(c['R'][view]['availabilityPattern'] for c in cs).items())),
            'rFallbackReasons':dict(sorted(Counter(c['R'][view]['reason'] for c in cs if c['R'][view]['valueFraction'] is None).items()))}
