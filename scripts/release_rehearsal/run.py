"""Stage77 release rehearsal: the full live chain at production settings, with labelled SYNTHETIC stand-ins.

python -m scripts.release_rehearsal.run [--national 4096] [--replicates 16] [--workers 4] [--check]

Real inputs: the Stage70 2026-10-07 national refresh (lastDataSupport; adopted into the config by #94), the Stage64 population-flat baseline, the Stage72 scales,
the Stage75 candidate fit, the Stage66 Maori layer for the three polled seats, the 2026 frame. SYNTHETIC stand-ins
(because the real inputs do not exist yet): the official candidate list (Stage50 stand-in: announcements plus
invented Labour and independent candidates), the D107 classification, and winners for the four unpolled Maori seats.
The Stage69 baseline (merged, not adopted) is not used.

Writes the bank and the rehearsal publication inputs under the gitignored `.release-build/rehearsal/` only (never
`public/`), and a deterministic report `data/processed/release-rehearsal/report.json` (no timings).
"""
import argparse
import copy
import json
import os
import time
import numpy as np
from scripts.balance_scale.common import equivalent
from scripts.nominations_2026 import refresh, synthetic
from scripts.nowcast_assembly import assemble as A, maori
from scripts.nowcast_assembly.common import CONFIG, ROOT, encode, read, namespace_seed

REPORT = 'data/processed/release-rehearsal/report.json'
BUILD = '.release-build/rehearsal/'
AS_OF = '2026-10-07'
STAND_INS = ['official candidate list (Stage50 not yet run; announcements + invented Labour/independent rows)',
             'ordinary/exceptional classification (James has not entered it)',
             'winners for the four unpolled Maori seats (James has not chosen a fallback)',
             'MMP rules-version label (placeholder; the blocs are the configured ones)']
NOT_USED = ["Stage69 voting-place notional baseline (merged as #96 but not adopted; adoption is James's decision; the configured Stage64 population-flat baseline is used)"]
STAGE70 = 'data/processed/polling/weekly-refresh/2026-10-07/estimate.json'


def synthetic_classification(general):
    """SYNTHETIC: every eighth general seat exceptional. Not a judgement and not the draft for James."""
    return {seat: 'exceptional' if i % 8 == 0 else 'ordinary' for i, seat in enumerate(general)}


def synthetic_unpolled(records, total, namespace):
    """SYNTHETIC: two invented candidates per unpolled Maori seat with seeded coin-flip winners."""
    out = dict(records)
    for seat, record in records.items():
        if record['status'] != 'unavailable':
            continue
        rng = np.random.default_rng(namespace_seed(namespace, 'synthetic-unpolled:' + seat))
        ids = [f'synthetic-{seat}-a', f'synthetic-{seat}-b']
        out[seat] = {'status': 'simulated', 'class': 'maori-layer', 'source': 'SYNTHETIC stand-in for an unpolled seat',
                     'candidates': ids, 'candidateNames': ['Synthetic A', 'Synthetic B'], 'candidateParty': ['labourparty', 'tepatimaori'],
                     'candidateShares': [{'candidateId': i, 'mean': 0.5, 'intervals': [{'level': v, 'lower': 0.5, 'median': 0.5, 'upper': 0.5}
                                                                                       for v in (0.5, 0.8, 0.9)]} for i in ids],
                     'winners': rng.integers(0, 2, total).tolist()}
    return out


def rehearse(national, replicates, workers):
    started = time.time()
    outputs = synthetic.refreshed()
    features = outputs[refresh.output_dir(synthetic.ACQUISITION) + 'features-raw.json']
    centred = outputs[refresh.output_dir(synthetic.ACQUISITION) + 'features-centred.json']
    config = copy.deepcopy(read(CONFIG))
    national_input = read(STAGE70)['nowcastInput']
    if (config['national']['source'], config['national']['dataCutoff']) != (national_input['source'], national_input['dataCutoff']):
        raise SystemExit('the config no longer carries the adopted Stage70 2026-10-07 refresh; update the rehearsal')
    config['roster']['snapshotId'] = 'synthetic-rehearsal-roster'
    config['pending'].pop('roster.snapshotId', None)
    slates, _ = A.live_slates(config, features, centred)
    general = sorted(slates)
    total = national * replicates
    records = synthetic_unpolled(maori.simulate(config, total), total, config['simulation']['seedNamespace'])
    bank = A.assemble(config, national, slates=slates, classification=synthetic_classification(general),
                      maori_records=records, workers=workers, replicates=replicates)
    passed, checks = A.gate(bank, config)
    elapsed = time.time() - started
    report = {'stage': 77, 'label': 'REHEARSAL with labelled synthetic stand-ins; not a nowcast and never published',
              'configVersion': config['configVersion'], 'asOf': AS_OF, 'nationalDraws': national, 'layerReplicates': replicates,
              'rows': bank['draws'], 'provenance': bank['provenance'], 'syntheticStandIns': STAND_INS, 'realInputsNotYetAvailable': NOT_USED,
              'nationalInput': {'source': national_input['source'], 'modelStateAsOf': national_input['modelStateAsOf'],
                                'dataCutoff': national_input['dataCutoff'], 'note': 'Stage70 2026-10-07 refresh, adopted into the config (#94)'},
              'seats': {'simulated': sum(s['status'] == 'simulated' for s in bank['seats']), 'total': len(bank['seats'])},
              'gate': {'passed': passed, 'checks': checks},
              'reconciliation': bank['diagnostics']['reconciliation'], 'bankDigest': A.bank_digest(bank)}
    options = {'snapshotId': 'synthetic-rehearsal-' + AS_OF, 'createdAt': AS_OF + 'T00:00:00+00:00',
               'dataCutoff': config['national']['dataCutoff'] + 'T00:00:00+00:00', 'electionId': 'nz-general-2026',
               'electionDate': config['electionDate'], 'boundaryVersionId': 'stats-nz-electorates-final-2025',
               'modelVersion': 'rehearsal-' + config['configVersion'], 'codeRevision': 'rehearsal',
               'mmp': {'rulesVersion': 'UNVERIFIED-PLACEHOLDER-synthetic-only', 'rulesSourceIds': ['synthetic-rules'],
                       'blocs': config['mmp']['blocs'], 'hungParliament': config['mmp']['hungParliament']},
               'nationalBasis': 'Stage70 2026-10-07 refresh, lastDataSupport (latent state, week of ' + config['national']['modelStateAsOf'] + ')',
               'limitations': ['SYNTHETIC REHEARSAL: stand-in candidate list, classification and unpolled Maori seats; not a nowcast.'],
               'probabilityMcseMax': config['release']['probabilityMcseMax']}
    return report, bank, options, elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--national', type=int, default=4096)
    parser.add_argument('--replicates', type=int, default=16)
    parser.add_argument('--workers', type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report, bank, options, elapsed = rehearse(args.national, args.replicates, args.workers)
    (ROOT / BUILD).mkdir(parents=True, exist_ok=True)
    (ROOT / (BUILD + 'bank.json')).write_text(json.dumps(bank, separators=(',', ':')), encoding='utf-8')
    (ROOT / (BUILD + 'options.json')).write_text(json.dumps(options, indent=2), encoding='utf-8')
    if args.check:
        if not equivalent(read(REPORT), report, 1e-9):
            raise SystemExit('Stale ' + REPORT)
    else:
        (ROOT / REPORT).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / REPORT).write_bytes(encode(report))
    size = (ROOT / (BUILD + 'bank.json')).stat().st_size
    print(f"rehearsal {'reproduced' if args.check else 'written'}: {report['rows']} rows, {report['seats']['simulated']}/71 seats, "
          f"gate passed={report['gate']['passed']}, bank {size / 1e6:.1f} MB, {elapsed:.0f} s on {args.workers} workers")


if __name__ == '__main__':
    main()
