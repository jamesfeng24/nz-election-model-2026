import type { ReleasePoint } from '../data/loader';
import { longDate, prob } from './format';

export const MIN_RELEASES = 3;

const WIDTH = 640;
const HEIGHT = 300;
const MARGIN = { left: 44, right: 230, top: 16, bottom: 40 };
const GRID_VALUES = [0, 0.25, 0.5, 0.75, 1];

const LINES = [
  { kind: 'bloc', id: 'nat-act-nzf', colour: '#00529f', label: 'National + ACT + NZ First' },
  { kind: 'bloc', id: 'lab-grn-tpm', colour: '#d82a20', label: 'Labour + Greens + Te Pāti Māori' },
  { kind: 'scenario', id: 'hung', colour: '#6b6b6b', label: 'No majority' },
] as const;

/** How the chance of each majority has moved across the weekly releases. */
export function TrendChart({ history }: { history: ReleasePoint[] }) {
  if (history.length < MIN_RELEASES) return null;
  const time = (release: ReleasePoint) => Date.parse(release.dataCutoff);
  const first = time(history[0]);
  const last = time(history[history.length - 1]);
  const plotRight = WIDTH - MARGIN.right;
  const x = (release: ReleasePoint) =>
    MARGIN.left + (last === first ? 0 : (time(release) - first) / (last - first)) * (plotRight - MARGIN.left);
  const y = (chance: number) => MARGIN.top + (1 - chance) * (HEIGHT - MARGIN.top - MARGIN.bottom);

  // A line is drawn only if every release has a value for it.
  const series = LINES.flatMap((line) => {
    const points = history.flatMap((release) => {
      const value = (line.kind === 'bloc' ? release.blocMajority : release.scenarios)[line.id];
      return value ? [{ release, chance: value.p, label: value.label }] : [];
    });
    return points.length === history.length ? [{ line, points }] : [];
  });
  if (series.length === 0) return null;

  const summary = series
    .map(
      ({ points }) => `${points[0].label} from ${prob(points[0].chance)} to ${prob(points[points.length - 1].chance)}`,
    )
    .join('; ');
  return (
    <figure className="trend">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Chance over ${history.length} releases: ${summary}`}
      >
        {GRID_VALUES.map((value) => (
          <g key={value}>
            <line x1={MARGIN.left} x2={plotRight} y1={y(value)} y2={y(value)} className="grid" />
            <text x={MARGIN.left - 6} y={y(value) + 4} textAnchor="end" className="tick">
              {Math.round(value * 100)}%
            </text>
          </g>
        ))}
        {series.map(({ line, points }) => {
          const end = points[points.length - 1];
          return (
            <g key={line.id}>
              <polyline
                fill="none"
                stroke={line.colour}
                strokeWidth="2.5"
                points={points.map((p) => `${x(p.release)},${y(p.chance)}`).join(' ')}
              />
              {points.map((p) => (
                <circle key={p.release.snapshotId} cx={x(p.release)} cy={y(p.chance)} r="3.5" fill={line.colour} />
              ))}
              <text x={plotRight + 8} y={y(end.chance) + 4} fill={line.colour} className="endlabel">
                {line.label} {prob(end.chance)}
              </text>
            </g>
          );
        })}
        <text x={MARGIN.left} y={HEIGHT - 12} className="tick">
          {longDate(history[0].dataCutoff)}
        </text>
        <text x={plotRight} y={HEIGHT - 12} textAnchor="end" className="tick">
          {longDate(history[history.length - 1].dataCutoff)}
        </text>
      </svg>
      <figcaption>
        Chance of a majority, and of no majority, at each weekly release. Each point is a separate forecast; the lines
        show how the picture has changed, not a prediction.
      </figcaption>
    </figure>
  );
}
