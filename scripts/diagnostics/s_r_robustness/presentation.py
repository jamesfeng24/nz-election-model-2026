"""Deterministic scatter panels and complete flat diagnostic tables."""
import csv
import io
from html import escape
from math import ceil
from .common import METHODS, S, R, JOINT


def csv_table(folds):
    out = io.StringIO(newline=''); fields = ['branch', 'target_year', 'contest_id', 'seat_name', 'slate_size', 'movement_status',
        'constructed_TV_fraction', 'observed_TV_fraction', 'G_pp', 'J_pp', 'R_broad_count', 'R_strict_count',
        'constructed_party_input_MAE_pp', 'constructed_National_party_error_pp', 'constructed_Labour_party_error_pp']
    fields += [m+'_MAE_pp' for m in METHODS]; writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n'); writer.writeheader()
    for f in folds:
        for r in f['records']:
            party = r['constructedPartyInputErrorEvaluationOnly']
            row = {'branch': f['branch'], 'target_year': f['targetYear'], 'contest_id': r['targetElectorateId'],
                'seat_name': r['targetSeatName'], 'slate_size': r['slateSize'], 'movement_status': r['movementStatus'],
                'constructed_TV_fraction': r['constructedLocalDistance'], 'observed_TV_fraction': r['observedLocalDistance'],
                'G_pp': r['Gpp'], 'J_pp': r['Jpp'], 'R_broad_count': r['RSupportedCounts']['broad'],
                'R_strict_count': r['RSupportedCounts']['strict'], 'constructed_party_input_MAE_pp': party['completeVectorMaePP'] if party else None,
                'constructed_National_party_error_pp': party['majorParty']['nationalparty']['signedErrorPP'] if party and party['majorParty']['nationalparty'] else None,
                'constructed_Labour_party_error_pp': party['majorParty']['labourparty']['signedErrorPP'] if party and party['majorParty']['labourparty'] else None}
            row.update({m+'_MAE_pp': r['errors'][m]['maePP'] for m in METHODS}); writer.writerow(row)
    return out.getvalue()


def scatter(folds, field):
    panels = [f for f in folds if f['branch']=='primary' and f['records']]
    limit = max(1, ceil(max(abs(r['Gpp']) for f in panels for r in f['records'])))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 830" role="img">',
        '<title>Post-result local party movement versus saved S/R error differences</title>',
        '<rect width="1240" height="830" fill="white"/>',
        '<g font-family="sans-serif" font-size="14" fill="#243447">',
        f'<text x="30" y="28">{escape(field)}: full-party TV versus G = MAE_R − MAE_S (pp); positive favors S</text>',
        '<text x="30" y="52">Primary saved predictions; no smoothing, clipping, weighting model or causal claim.</text>']
    for i, f in enumerate(panels):
        left = 70+(i%2)*610; top = 110+(i//2)*355; width = 510; height = 260
        svg.append(f'<text x="{left}" y="{top-18}">{f["targetYear"]} — {len(f["records"])} complete contests</text>')
        for v in (0, 25, 50, 75, 100):
            x = left+width*v/100
            svg.extend([f'<path d="M{x} {top}V{top+height}" stroke="#e3e8ec"/>',
                f'<text x="{x}" y="{top+height+22}" text-anchor="middle">{v}</text>'])
        for value in (-limit, 0, limit):
            y = top+height*(limit-value)/(2*limit)
            svg.extend([f'<path d="M{left} {y}H{left+width}" stroke="{"#8996a0" if value==0 else "#e3e8ec"}"/>',
                f'<text x="{left-12}" y="{y+5}" text-anchor="end">{value}</text>'])
        for r in f['records']:
            if r['movementStatus']!='available':
                continue
            x = left+width*r[field]; y = top+height*(limit-r['Gpp'])/(2*limit)
            title = escape(f"{r['targetSeatName']} ({r['targetElectorateId']}); TV={100*r[field]:.4f}pp; G={r['Gpp']:.4f}pp")
            svg.append(f'<circle cx="{x:.5f}" cy="{y:.5f}" r="3.5" fill="#216a97" fill-opacity="0.7"><title>{title}</title></circle>')
        svg.append(f'<text x="{left+width/2}" y="{top+height+47}" text-anchor="middle">Party TV (100D, displaced-share pp)</text>')
    svg.append('</g></svg>\n'); return '\n'.join(svg)
