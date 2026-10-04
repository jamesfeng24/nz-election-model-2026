"""Reversible dated candidate claims; missing candidates never imply absence."""
from collections import defaultdict
from datetime import datetime
import hashlib
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from scripts.evidence.practical_candidate_linkage.names import normalize

# Explicit typographic/abbreviation correspondences, not geographic continuity evidence.
SEAT_ALIASES = {'mt albert': 'mount albert', 'mt roskill': 'mount roskill',
    'mt maunganui': 'mount maunganui', 'mt. albert': 'mount albert', 'mt. roskill': 'mount roskill',
    'kāpiti': 'kapiti', 'tamaki': 'tāmaki', 'whangarei': 'whangārei', 'mangere': 'māngere', 'rangitikei': 'rangitīkei', 'otāhuhu': 'ōtāhuhu', 'ikaroa rāwhiti': 'ikaroa-rāwhiti', 'kaipara ki mahurangi': 'kaipara ki mahurangi'}

PARTIES = [
 ('actnewzealand','ACT New Zealand','actnewzealand'),
 ('alliancepartyofaotearoanewzealand','Alliance Party of Aotearoa New Zealand',None),
 ('animaljusticeparty','Animal Justice Party Aotearoa New Zealand','animaljusticeparty'),
 ('aotearoalegalisecannabisparty','Aotearoa Legalise Cannabis Party','aotearoalegalisecannabisparty'),
 ('conservativepartynz','Conservative Party NZ','newconservatives'),
 ('freepalestine','Free Palestine',None),
 ('newzealandfirstparty','New Zealand First Party','newzealandfirstparty'),
 ('labourparty','New Zealand Labour Party','labourparty'),
 ('newzealandloyal','New Zealand Loyal',None),
 ('nzoutdoorsfreedomparty','NZ Outdoors & Freedom Party',None),
 ('opportunity','Opportunity Party','theopportunitiespartytop'),
 ('tepatimaori','Te Pāti Māori','tepatimaori'),
 ('tetaitokerauparty','Te Tai Tokerau Party',None),
 ('greenparty','The Green Party of Aotearoa New Zealand','greenparty'),
 ('nationalparty','The New Zealand National Party','nationalparty'),
 ('visionnewzealand','Vision New Zealand',None),
 ('womensrightsparty',"Women's Rights Party",'womensrightsparty')]


def party_relationships():
    return [{'targetGroupKey': key, 'registeredName': name, 'sourceBallotGroupKey': source,
        'ballotGroupId': 'nz-general-2026-party-group-' + key,
        'membershipStatus': 'registered_at_cutoff; actual_2026_ballot_participation_unconfirmed',
        'componentParties': [], 'sharedGroup': False,
        'continuity': 'documented_registration_lineage_or_unchanged_party' if source else 'not_established_to_2023_ballot_group',
        'evidencePath': 'data/raw/forecast-readiness/2026-10-05/party-register-readable.json',
        'note': 'Previous registered logos/names document rename; no constituent allocation.' if key in ('opportunity','conservativepartynz') else
                '2023 shared Freedoms ballot group cannot become this constituent row.' if key in ('visionnewzealand','nzoutdoorsfreedomparty') else
                'New registration is not continuity from a similarly named historical party.' if key=='alliancepartyofaotearoanewzealand' else None}
        for key, name, source in PARTIES]


def verify_register(text):
    headings = re.findall(r'(?:^|\n)L\d+: ## ([^\n]+)', text)
    parties = [name for name in headings if name != 'Table of registered parties']
    expected = {name for _,name,_ in PARTIES}
    if set(parties) != expected or len(parties) != len(expected):
        raise ValueError('Registered-party schema changed; explicit relationship overlay amendment required')
    components = re.findall(r'L\d+: ### Component parties:\s*(?:L\d+:\s*)*L\d+: ([^\n]+)', text)
    if len(components)!=len(expected) or any(value!='None' for value in components):
        raise ValueError('Registered component/alliance structure changed; explicit overlay required')


def seat_key(label):
    key = normalize(label)
    return SEAT_ALIASES.get(key, key)


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def claim_available(claim, source, cutoff):
    instant = utc(cutoff)
    if utc(source['retrievedAt']) > instant:
        return False
    local_day = instant.astimezone(ZoneInfo('Pacific/Auckland')).date().isoformat()
    for field in ('publicationDate','factDate'):
        value = claim.get(field)
        if value is None:
            continue
        if 'T' in value:
            if utc(value).tzinfo is None:
                raise ValueError('Timestamp lacks publication timezone')
            if utc(value) > instant:
                return False
        elif value > local_day:
            return False
    return True


def occurrence_id(seat_id, party, name):
    signature = party + '|' + normalize(name)
    return seat_id + '-candidate-' + hashlib.sha256(signature.encode()).hexdigest()[:16]


def build_registry(claims, frame, sources, cutoff, completeness=()):
    seats = {seat_key(s['canonicalName']): s for s in frame}
    groups = {p['targetGroupKey']: p for p in party_relationships()}
    occurrences = {}; unmatched = []; history = []
    for n, claim in enumerate(claims):
        source = sources[claim['sourceKey']]
        signature='|'.join(str(claim.get(k,'')) for k in ('displayName','sourceElectorateLabel','affiliationKey','status','factDate','publicationDate','locator'))
        event = dict(claim, claimId=source['id']+'-claim-'+hashlib.sha256(signature.encode()).hexdigest()[:16], sourceId=source['id'],sourceURL=source['url'],
            sourceKey=source.get('originalKey',claim['sourceKey']), rawPath=source['rawPath'], rawSha256=source['sha256'], retrievalDate=source['retrievedAt'],
            acquisitionCutoff=cutoff, publicationAvailability='dated_publication' if claim.get('publicationDate') else 'retrieved_by_cutoff; publication_unknown')
        if not claim_available(claim, source, cutoff):
            unmatched.append(dict(event, reason='post_cutoff_claim')); continue
        if claim['status']=='official_nomination' and urlparse(source['url']).hostname not in ('elections.nz','vote.nz','www.vote.nz'):
            raise ValueError('Party assertions cannot be promoted to official nominations')
        seat = seats.get(seat_key(claim['sourceElectorateLabel']))
        if seat is None:
            unmatched.append(dict(event, reason='unresolved_target_seat_label')); continue
        party = claim['affiliationKey']; group = groups.get(party)
        oid = occurrence_id(seat['targetElectorateId'], party, claim['displayName'])
        row = occurrences.setdefault(oid, {'targetOccurrenceId': oid, 'targetElectorateId': seat['targetElectorateId'],
            'displayedName': claim['displayName'], 'originalAffiliation': party,
            'normalizedName': normalize(claim['displayName']), 'ballotGroupKey': party if group else None,
            'ballotGroupMappingStatus': 'provisional_unique_registered_party; actual_ballot_pending' if group else 'ambiguous_or_missing_not_no_group',
            'sharedGroup': bool(group and group['sharedGroup']), 'hypothetical': False, 'claims': []})
        row['claims'].append(event); history.append(event)
    conflicts = defaultdict(list)
    for row in occurrences.values():
        events = row['claims']; withdrawn = [c for c in events if c['status']=='withdrawn']
        active = [c for c in events if c['status']!='withdrawn']
        # Latest status is allowed only where every relevant fact date orders it; undated conflicts remain unresolved.
        if withdrawn and active:
            dated = all(c.get('factDate') for c in events)
            if dated:
                latest_day = max(c['factDate'][:10] if 'T' not in c['factDate'] else utc(c['factDate']).astimezone(ZoneInfo('Pacific/Auckland')).date().isoformat() for c in events)
                recent = [c for c in events if (c['factDate'][:10] if 'T' not in c['factDate'] else utc(c['factDate']).astimezone(ZoneInfo('Pacific/Auckland')).date().isoformat())==latest_day]
                if all('T' in c['factDate'] for c in recent):
                    latest_time = max(utc(c['factDate']) for c in recent)
                    recent = [c for c in recent if utc(c['factDate'])==latest_time]
                latest = {c['status'] for c in recent}
                state = next(iter(latest)) if len(latest)==1 else 'conflicting_status'
            else:
                state = 'conflicting_status'
        else:
            state = 'withdrawn' if withdrawn else 'official_nomination' if any(c['status']=='official_nomination' for c in active) else 'party_selected' if any(c['status']=='party_selected' for c in active) else 'party_announced'
        row.update(status=state, active=state not in ('withdrawn','conflicting_status'), confidence='official_nomination' if state=='official_nomination' else 'party_assertion_not_verified_nomination', conflict=state=='conflicting_status')
        if row['active'] and row['ballotGroupKey']:
            conflicts[(row['targetElectorateId'],row['ballotGroupKey'])].append(row['targetOccurrenceId'])
    for ids in conflicts.values():
        if len(ids)>1:
            for oid in ids:
                occurrences[oid].update(conflict=True, ballotGroupMappingStatus='multiple_active_group_destinations_contest_abstention', competingOccurrenceIds=sorted(set(ids)-{oid}))
    complete = {}
    for declaration in completeness:
        if declaration['status']!='official_complete_nominations' or not declaration.get('sourceId'):
            raise ValueError('Party announcements cannot certify complete slates')
        if utc(declaration['publishedAt']) > utc(cutoff) or utc(declaration['publishedAt']) < utc('2026-10-07T23:00:00Z'):
            raise ValueError('Complete nomination assertion outside permitted publication window')
        if any(r['conflict'] for r in occurrences.values() if r['targetElectorateId']==declaration['targetElectorateId']):
            raise ValueError('Unresolved conflicts prevent complete-slate certification')
        seat_ids = {r['targetOccurrenceId'] for r in occurrences.values() if r['targetElectorateId']==declaration['targetElectorateId'] and r['active']}
        if set(declaration.get('candidateOccurrenceIds', [])) != seat_ids or not seat_ids:
            raise ValueError('Official complete-slate membership does not match known active records')
        if any(r['status']!='official_nomination' or r['conflict'] for r in occurrences.values() if r['targetOccurrenceId'] in seat_ids):
            raise ValueError('Complete slates require uncontested official nominations')
        if declaration['sourceId'] not in {s['id'] for s in sources.values()}:
            raise ValueError('Unpreserved complete nomination source')
        complete[declaration['targetElectorateId']] = declaration
    return {'occurrences': sorted(occurrences.values(),key=lambda r:r['targetOccurrenceId']),
            'claimHistory': history, 'unmatchedClaims': unmatched, 'completeSlateDeclarations': complete,
            'deduplicatedRepresentations': len(history)-len(occurrences)}


def mapping_readiness(candidates):
    if any(c['conflict'] for c in candidates):
        return 'abstain_mapping_conflict_or_missing'
    active = [c for c in candidates if c['active']]
    groups = [c['ballotGroupKey'] for c in active if c['ballotGroupKey']]
    if any(c['conflict'] or c['ballotGroupKey'] is None for c in active) or len(groups)!=len(set(groups)):
        return 'abstain_mapping_conflict_or_missing'
    return 'known_destinations_unique; unknown_slate_members_pending'


def snapshot_changes(previous, current):
    old = {r['targetOccurrenceId']:r for r in previous.get('occurrences',[])}
    new = {r['targetOccurrenceId']:r for r in current['occurrences']}
    changes=[]
    for oid in sorted(old.keys()|new.keys()):
        if old.get(oid)==new.get(oid):continue
        row=new.get(oid,old.get(oid))
        changes.append({'targetOccurrenceId':oid,'targetElectorateId':row['targetElectorateId'],
            'change':'added_supported_occurrence' if oid not in old else 'no_longer_in_snapshot_not_proof_of_withdrawal' if oid not in new else 'evidence_or_status_changed',
            'invalidate':['slate','identity_competitor_checks','S_R_readiness','downstream_candidate_outputs']})
    return changes
