"""Fixed unsmoothed exploratory scatterplots of frozen paired errors."""

from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


COLORS = {2011: '#64748b', 2017: '#2563eb', 2023: '#c2410c'}


def scatter(rows, x_field, title, x_label, filename, *, xmin=None, xmax=None):
    fig, ax = plt.subplots(figsize=(7.2, 4.4), layout='constrained')
    for year in (2011, 2017, 2023):
        subset = [r for r in rows if r['targetYear'] == year]
        if subset:
            ax.scatter([r[x_field] for r in subset],
                       [r['deltaAbsolutePP'] for r in subset],
                       s=14, alpha=.42, color=COLORS[year], edgecolors='none',
                       label=f'{year} · {len(subset)}')
    ax.axhline(0, color='#111827', lw=.9)
    ax.set(title=title, xlabel=x_label,
           ylabel='Model minus control absolute error (pp)')
    if xmin is not None and xmax is not None:
        ax.set_xlim(xmin, xmax)
    ax.grid(alpha=.16)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(frameon=False, fontsize=8)
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=150, metadata={'Software': 'matplotlib'})
    plt.close(fig)
    return filename, buffer.getvalue()


def build(rows):
    floor = [r for r in rows if r['component'] == 'stage18' and
             r['comparison'] == 'fitted_floor_vs_restricted_zero_floor']
    response = [r for r in rows if r['component'] == 'stage16' and
                r['comparison'] == 'source_victory_vs_common_intercept' and
                r['mode'] == 'actual_observed_local_party']
    return dict([
        scatter(floor, 'controlShare',
                'Incremental common floor on its supported subset',
                'Zero-floor control candidate share', 'stage18-floor-vs-zero.png',
                xmin=0, xmax=1),
        scatter(response, 'observedPartyMovement',
                'Source-victory response versus party movement',
                'Observed local party-share movement', 'stage16-party-movement.png'),
        scatter(response, 'sourceCandidatePartyGap',
                'Source-victory response versus source share gap',
                'Source candidate share minus party share', 'stage16-source-gap.png')])
