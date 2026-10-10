"""Stage77 release rehearsal: the full live chain at production settings, with labelled SYNTHETIC stand-ins.

python -m scripts.release_rehearsal.run [--national 4096] [--replicates 16] [--workers 4] [--check]

Real inputs: the national refresh the configuration adopts (lastDataSupport; read from the config's `national.source`, so the report follows each
adoption), the Stage69 voting-place baseline the config points to (D103), the Stage72 scales, the Stage75 candidate fit, the Stage66 Maori layer
for the polled seats, the 2026 frame. SYNTHETIC stand-ins, kept so the rehearsal never depends on the real roster or classification: the general-seat
candidate list (Stage50 stand-in: announcements plus invented Labour and independent candidates) and a classification that marks every eighth
general seat exceptional. The unpolled Maori seats use the real registered Stage78 fallback (Stage80, D118) with the official Maori roster, not a stand-in.

Writes the bank and the rehearsal publication inputs under the gitignored `.release-build/rehearsal/` only (never
`public/`), and a deterministic report `data/processed/release-rehearsal/report.json` (no timings).
"""
import argparse
import copy
import json
import os
import time
from scripts.balance_scale.common import equivalent
from scripts.nominations_2026 import refresh, synthetic
from scripts.nowcast_assembly import assemble as A, maori
from scripts.nowcast_assembly.common import CONFIG, ROOT, encode, read

REPORT = 'data/processed/release-rehearsal/report.json'
BUILD = '.release-build/rehearsal/'
STAND_INS = ['general-seat candidate list (Stage50 stand-in: announcements plus invented Labour/independent rows; the official list exists and is not used here)',
             'ordinary/exceptional classification (every eighth general seat; the real 64-seat classification exists and is not used here)',
             'MMP rules-version label (placeholder; the blocs are the configured ones)']
NOT_USED = ['the official general-seat candidate list and the real ordinary/exceptional classification (the rehearsal stays independent of them; the real inputs are used by the development gate and the production run)']


def synthetic_classification(general):
    """SYNTHETIC: every eighth general seat exceptional. Not a judgement and not the draft for James."""
    return {seat: 'exceptional' if i % 8 == 0 else 'ordinary' for i, seat in enumerate(general)}


def rehearse(national, replicates, workers):
    started = time.time()
    outputs = synthetic.refreshed()
    features = outputs[refresh.output_dir(synthetic.ACQUISITION) + 'features-raw.json']
    centred = outputs[refresh.output_dir(synthetic.ACQUISITION) + 'features-centred.json']
    config = copy.deepcopy(read(CONFIG))
    national_input = read(os.path.join(os.path.dirname(os.path.dirname(config['national']['source'])), 'estimate.json'))['nowcastInput']
    if (config['national']['source'], config['national']['modelStateAsOf'], config['national']['dataCutoff']) != (
            national_input['source'], national_input['modelStateAsOf'], national_input['dataCutoff']):
        raise SystemExit("the config's national input does not match its refresh's estimate.json (nowcastInput); adopt it with weekly_refresh.adopt")
    as_of = config['national']['dataCutoff']
    config['roster']['snapshotId'] = 'synthetic-rehearsal-roster'
    config['pending'].pop('roster.snapshotId', None)
    slates, _ = A.live_slates(config, features, centred)
    general = sorted(slates)
    total = national * replicates
    records = maori.simulate(config, total)
    bank = A.assemble(config, national, slates=slates, classification=synthetic_classification(general),
                      maori_records=records, workers=workers, replicates=replicates)
    passed, checks = A.gate(bank, config)
    elapsed = time.time() - started
    report = {'stage': 77, 'label': 'REHEARSAL with labelled synthetic stand-ins; not a nowcast and never published',
              'configVersion': config['configVersion'], 'asOf': as_of, 'nationalDraws': national, 'layerReplicates': replicates,
              'rows': bank['draws'], 'provenance': bank['provenance'], 'syntheticStandIns': STAND_INS, 'realInputsNotYetAvailable': NOT_USED,
              'nationalInput': {'source': national_input['source'], 'modelStateAsOf': national_input['modelStateAsOf'],
                                'dataCutoff': national_input['dataCutoff'], 'note': 'the national refresh the configuration adopts'},
              'seats': {'simulated': sum(s['status'] == 'simulated' for s in bank['seats']), 'total': len(bank['seats'])},
              'gate': {'passed': passed, 'checks': checks},
              'reconciliation': bank['diagnostics']['reconciliation'], 'bankDigest': A.bank_digest(bank)}
    options = {'snapshotId': 'synthetic-rehearsal-' + as_of, 'createdAt': as_of + 'T00:00:00+00:00',
               'dataCutoff': config['national']['dataCutoff'] + 'T00:00:00+00:00', 'electionId': 'nz-general-2026',
               'electionDate': config['electionDate'], 'boundaryVersionId': 'stats-nz-electorates-final-2025',
               'modelVersion': 'rehearsal-' + config['configVersion'], 'codeRevision': 'rehearsal',
               'mmp': {'rulesVersion': 'UNVERIFIED-PLACEHOLDER-synthetic-only', 'rulesSourceIds': ['synthetic-rules'],
                       'blocs': config['mmp']['blocs'], 'hungParliament': config['mmp']['hungParliament']},
               'nationalBasis': 'Stage70 ' + config['national']['dataCutoff'] + ' refresh, lastDataSupport (latent state, week of ' + config['national']['modelStateAsOf'] + ')',
               'limitations': ['SYNTHETIC REHEARSAL: stand-in general-seat candidate list and classification; not a nowcast.'],
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
