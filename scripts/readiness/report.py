"""Human-readable dated readiness companion, not a forecast report."""
import argparse
import csv
import io
from .common import ROOT, load, save

BASE='data/processed/forecast-readiness/snapshots/2026-10-05/'


def registry_tsv(snapshot, links, features):
    edges={r['targetOccurrenceId']:r for r in links}; feat={r['targetOccurrenceId']:r for r in features}
    stream=io.StringIO();writer=csv.writer(stream,delimiter='\t',lineterminator='\n')
    writer.writerow(['occurrence_id','electorate_id','displayed_name','affiliation','ballot_group','status','link_tier','strict_link','S_status','R_status','source_ids'])
    for row in snapshot['occurrences']:
        oid=row['targetOccurrenceId'];edge=edges[oid];f=feat[oid]
        writer.writerow([oid,row['targetElectorateId'],row['displayedName'],row['originalAffiliation'],row['ballotGroupKey'] or 'unknown',
            row['status'],edge['label'],edge['strictAccepted'],f['S']['status'],f['R']['status'],';'.join(sorted({c['sourceId'] for c in row['claims']}))])
    return stream.getvalue()


def findings(counts,snapshot,frame,ready):
    seats={s['targetElectorateId']:s for s in frame}
    party_rows='\n'.join(f'| {party} | {n} |' for party,n in sorted(counts['candidatesByParty'].items()))
    seat_rows='\n'.join(f'| {seats[r["targetElectorateId"]]["officialName"]} | {r["scope"]} | {r["knownCandidateCount"]} | {r["slateStatus"]} | {seats[r["targetElectorateId"]]["geographyStatus"]} | {r["SCounts"]["supported"]} | {r["RCounts"]["supported"]} |' for r in ready)
    return f'''# Stage40: 2026 target-boundary and slate readiness

## Dated official frame

Acquisition cutoff **{snapshot['acquisitionCutoffUTC']}**, NZ snapshot **2026-10-05**. Official election day is **7 November 2026**. Electoral Commission guidance gives **noon 8 October NZDT** as the nomination deadline and publishes candidate details after close. This snapshot establishes no final nomination slate.

The current 2025 Representation Commission report still governs 2026. The current official Schedule C readable extraction accounts for all **64 general + 7 Māori** targets, matching preserved names, codes and population controls exactly. Direct Electoral Commission downloads returned protection pages (including Schedule C); these raw failures are preserved separately from tool-rendered readable extracts. We do not claim byte-for-byte verification of the current PDF.

## Slate coverage

**{counts['candidateOccurrences']} real electorate occurrences**, all party assertions: **205 announced, one explicitly selected**, **zero verified official nominations**. These are a finite-source coverage count, not all candidates in New Zealand. **70 partial seats, one unknown (Hauraki-Waikato); zero complete slates.** All general seats have at least one supported assertion; six Māori seats do. There are no fictional candidate records or normalized partial-slate forecasts.

| Party/context | Known electorate candidates |
| --- | ---: |
{party_rows}

National includes only its explicitly labelled 2026 candidate section, excluding incumbent-only MP cards. ACT includes qualified main-directory seat assertions, excluding incumbent-only Seymour and the mixed electorate-only/retiring section; those remain context. Green list-only Marama Davidson remains context. NZ First admits explicit candidate-for-seat roles. Opportunity uses candidate cards. TPM admits two explicit 2026 confirmations (Haley Maxwell, Lisa Marie Murch), not current MPs inferred to stand again.

Labour's current candidate page and two linked official PDFs expose party-list names without electorate assignments. That material is preserved, but supplies no electorate records. The directory code route supplied no bulk seat table. Current MPs are not a nomination substitute. Minor registered parties/independents are incomplete. Source absence never means a party will not stand. Nicola Willis's dated list-only decision remains separate context, without a guessed target electorate.

## Geography and features

**16 certified two-sided exact targets: 14 general + 2 Māori.** Port Waikato's 2023 candidate contest was cancelled, leaving **13 held exact general predecessors**. Official unchanged names, incoming membership alone and rounded overlap are not sufficient: Te Tai Tokerau loses a suppressed 0–5 population edge; East Cape and Tāmaki Makaurau have suppressed extra incoming edges. **55 targets remain changed or technically uncertain**. Population overlap does not bound candidate-share error.

All 71 targets reference preserved complete notional party inputs and joint population/party constraints. Exact seats can reference their source local shares. Changed-seat party reconstruction is an explicit population transport assumption with coupled bounds; no midpoint, independently mixed endpoints or new point scenario is selected. Party reconstruction is distinct from candidate-feature transport.

The current register has **17 parties**, with **11 supported source group relationships** and six not established to a 2023 ballot group. Opportunity and Conservative renames preserve documented registration lineage. New registrations (including similarly named Alliance/Loyal/TTTP) and former Freedoms constituents are not silently treated as prior ballot categories. Registration does not prove participation in the 2026 party ballot. All mappings are provisional pending the actual ballot roster.

**41 provisional algorithmic same-person links**, **14 strict exact-name links**. Five accepted edges use frozen nicknames; middle-name concessions are recorded individually. These links are unique within the full preserved 2023 occurrence universe and the observed 2026 assertions. An incomplete target slate means uniqueness must be rechecked at nomination refresh. No link is promoted to documentary evidence, no person IDs/adjudications are overwritten, and no transitive grouping is performed.

For known candidates: **S supported for30 across13 held exact general seats**; **R supported for8 (strict4)**. No changed-seat R transfer is admitted. Missing features have a labelled neutral exponent fallback where the existing contract permits it; this is not known zero strength. Party/seat-change leads and conflicting/unparseable names remain explicit. Two Māori candidate records have missing named-candidate split evidence; they need a separate Māori baseline/poll contract.

Independently of candidate announcements, **70 party-seat S records** are supported on held exact general geography. The 13 held exact source contests contain106 historical candidates/86 finite residuals; exact Māori predecessors contain six/four. Source availability alone does not establish target identity or authorized transport. Cancelled Port Waikato has no behavioral S/R evidence, although its party votes remain substantive. Printed split percentages are working approximations; complete coupled-row witnesses are retained, not independent endpoints.

## Per-seat readiness

Counts below describe known candidates only, not complete slates. S/R are source-evidence readiness; no prediction is calculated.

| Official seat | Scope | Known candidates | Slate | Geography | S supported | R supported |
| --- | --- | ---: | --- | --- | ---: | ---: |
{seat_rows}

## Refresh and invalidation

Use `python -m scripts.readiness.run --check` and `python -m scripts.readiness.report --check` for this frozen snapshot. A separately authorized refresh preserves new raw bytes under a new dated directory and source manifest, then runs `--manifest NEW.json --previous OLD/snapshot.json --output NEW_DIRECTORY`. Source assertions can be provided with `--claim-events LEDGER.json`; official completeness assertions with `--completeness DECLARATIONS.json`. Every override and previous snapshot is hash-pinned. Never overwrite old raw bytes or snapshots.

Previously supported assertions are retained with original provenance until explicit dated evidence changes status. Omission is not withdrawal. Unordered selection/withdrawal claims, competing candidates and ambiguous party mappings remain conflicts. Complete slates require post-close preserved official nomination publication, exact membership and no conflicts; a party list cannot certify completeness. New register/component changes trigger an explicit factual overlay requirement, not guessed continuity. Changes record affected seats; any new identity collision requires the global country-wide linkage check and invalidates candidate features conservatively. Party-schema changes invalidate all local party inputs.

## Māori readiness and next bounded task

All seven Māori seats have roster/geography/readiness records. National TPM party-vote support is not Māori candidate-vote support. No poll campaign or Māori model is run. The later layer must preserve actual question, denominator, fieldwork/publication dates, sample, candidate/boundary IDs, uncertainty and dependence, with an explicit Māori baseline and wider unpolled/stale fallback.

**Recommended next implementation:** construct a coherent joint local-party/candidate-error simulation layer around the existing deterministic adapters, with a separately frozen residual-error specification, common national draws propagated once, explicit parameter/transport uncertainty and no calibrated win claims before validation. Refresh official nominations after8October in a bounded bulk pass. Then implement the separately designed Māori electorate-poll layer and unpolled baseline, reconciliation/turnout/valid denominators, MMP and publication. This recommendation does not begin any of those tasks.

## Validation and limitations

Focused tests cover official roster matching/two-sided geography, complete versus partial slates, source-only R, exact and nickname matches, collisions/compound names, withdrawals/conflicts, publication/fact timestamps and NZ dates, source authority, party/group ambiguity, coherent rounding witnesses, preservation and actual-pipeline target-outcome independence. Deterministic generation and the independent geography/slate audit agree on counts. Final test/CI status is recorded in PROJECT_STATE.md.

All1686 prior datafiles and926 prior source records are byte/record-identical. Twenty-four distinct requested URLs and12 queries exhaust the frozen budgets; five direct official responses are failures, with readable official extractions explicitly separate. Repeat reading of the same URL is not another distinct source; two Labour document URLs count twice even though their bytes match. No further sources, historical fitting, MCMC, candidate predictions, win probabilities or operational-selection changes occur. Externalgauss remains provisional, S+R preferred, S active and baseline mandatory, separately from historical operational nulls.
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    snapshot=load(BASE+'snapshot.json');counts=load(BASE+'coverage.json')
    outputs={'data/processed/forecast-readiness/snapshots/2026-10-05/review-table.tsv':registry_tsv(snapshot,load(BASE+'identity-links.json')['records'],load(BASE+'candidate-feature-readiness.json')['records']),
        'docs/stage40-target-boundary-slate-readiness.md':findings(counts,snapshot,load(BASE+'target-frame.json')['records'],load(BASE+'seat-readiness.json')['records'])}
    for relative,text in outputs.items():
        path=ROOT/relative
        if args.check:
            if path.read_text()!=text:raise ValueError('Readiness report differs: '+relative)
        else:path.write_text(text)


if __name__=='__main__':main()
