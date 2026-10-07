"""Command line for the manual-adjustment interface and the Stage57 labelling tools.

  python3 -m scripts.manual_adjustment.run build-template [--check]
  python3 -m scripts.manual_adjustment.run init-labels
  python3 -m scripts.manual_adjustment.run validate-labels [--labels PATH] [--complete]
  python3 -m scripts.manual_adjustment.run freeze-labels --labeller NAME --attest-no-residuals
  python3 -m scripts.manual_adjustment.run check-freeze
  python3 -m scripts.manual_adjustment.run validate-adjustments [--root DIR]
  python3 -m scripts.manual_adjustment.run add-adjustment --seat ID --entry FILE.json [--root DIR]
  python3 -m scripts.manual_adjustment.run apply --forecast FILE --as-of ISO --out FILE [--root DIR]

Offline; fits and estimates nothing. Every failure is an AdjustmentError with a message that names the field.
"""
import argparse
import shutil
import sys
from pathlib import Path

from .common import ROOT, AdjustmentError, canonical, read_json, require
from . import replay, schema, layer


def _template():
    rows = replay.build_template()
    return rows, replay.to_csv(rows), replay.template_manifest(rows)


def build_template(check):
    rows, text, manifest = _template()
    paths = {ROOT / replay.TEMPLATE: text, ROOT / replay.TEMPLATE_MANIFEST: canonical(manifest)}
    for path, content in paths.items():
        if check:
            require(path.exists() and path.read_text(encoding='utf-8') == content, f'stale or missing artifact: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8', newline='')
    print(f'{"checked" if check else "wrote"} labelling template: {len(rows)} seat-elections, prefilled {manifest["prefilled"]}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('build-template').add_argument('--check', action='store_true')
    sub.add_parser('init-labels')
    p = sub.add_parser('validate-labels')
    p.add_argument('--labels', default=str(ROOT / replay.LABELS))
    p.add_argument('--complete', action='store_true')
    p = sub.add_parser('freeze-labels')
    p.add_argument('--labels', default=str(ROOT / replay.LABELS))
    p.add_argument('--labeller', required=True)
    p.add_argument('--attest-no-residuals', action='store_true')
    p.add_argument('--frozen-at')
    sub.add_parser('check-freeze')
    p = sub.add_parser('validate-adjustments')
    p.add_argument('--root')
    p = sub.add_parser('add-adjustment')
    p.add_argument('--seat', required=True)
    p.add_argument('--entry', required=True)
    p.add_argument('--root')
    p = sub.add_parser('apply')
    p.add_argument('--forecast', required=True)
    p.add_argument('--as-of', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--root')
    args = parser.parse_args(argv)
    try:
        if args.command == 'build-template':
            build_template(args.check)
        elif args.command == 'init-labels':
            target = ROOT / replay.LABELS
            require(not target.exists(), f'{replay.LABELS} already exists; refusing to overwrite hand-entered labels')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / replay.TEMPLATE, target)
            print(f'copied the template to {replay.LABELS}; fill the empty cells (see docs/stage56-manual-adjustment-interface.md)')
        elif args.command == 'validate-labels':
            rows = replay.parse_csv(Path(args.labels).read_text(encoding='utf-8'))
            print(replay.validate_labels(rows, replay.build_template(), complete=args.complete))
        elif args.command == 'freeze-labels':
            record = replay.freeze(args.labels, args.labeller, args.attest_no_residuals, args.frozen_at)
            target = ROOT / replay.FREEZE
            require(not target.exists(), f'{replay.FREEZE} exists; a frozen labelling is never overwritten')
            target.write_text(canonical(record), encoding='utf-8')
            print(f'froze {record["seatElections"]} labels, sha256 {record["labelsSha256"]}')
        elif args.command == 'check-freeze':
            print(f'{len(replay.require_frozen_labels())} labels match the freeze record')
        elif args.command == 'validate-adjustments':
            documents = schema.load_directory(args.root)
            print(f'{len(documents)} seat adjustment file(s) valid')
        elif args.command == 'add-adjustment':
            path = schema.seat_path(args.seat, args.root)
            existing = read_json(path) if path.exists() else None
            document = schema.new_entry(existing, args.seat, read_json(args.entry))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(canonical(document), encoding='utf-8')
            print(f'appended {document["entries"][-1]["entryId"]} to {path}')
        elif args.command == 'apply':
            forecast = read_json(args.forecast)
            result = layer.apply_layer(forecast, schema.load_directory(args.root), args.as_of)
            Path(args.out).write_text(canonical(result), encoding='utf-8')
            print(f'adjusted {len(result["adjustedSeats"])} seat(s); exceptional {result["exceptionalSeats"]}; automatic forecast untouched')
    except AdjustmentError as problem:
        print(f'INVALID: {problem}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
