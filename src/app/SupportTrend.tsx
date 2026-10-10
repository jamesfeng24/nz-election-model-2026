import type { ForecastSnapshot } from '../types/export';
import { longDate } from './format';
import { COLOURS, FALLBACK } from './partyColours';
import { partyLabel } from './partyNames';

const WIDTH = 720;
const HEIGHT = 360;
const MARGIN = { left: 40, right: 104, top: 14, bottom: 34 };
/** End labels closer than this are nudged apart. */
const MIN_LABEL_GAP = 12;

const fieldworkMidpoint = (start: string | null, end: string) =>
  start ? (Date.parse(start) + Date.parse(end)) / 2 : Date.parse(end);

/** The national model's weekly estimate of support since the 2023 election, with each poll it used as a faint dot. */
export function SupportTrend({ snapshot }: { snapshot: ForecastSnapshot }) {
  const trend = snapshot.evidence?.trend;
  if (!trend) return null;
  const polls = snapshot.evidence!.nationalPolls.filter((poll) => poll.usedInModel);
  const colour = (id: string, index: number) => COLOURS[id] ?? FALLBACK[index % FALLBACK.length];

  const firstWeek = Date.parse(trend.weeks[0]);
  const lastWeek = Date.parse(trend.weeks[trend.weeks.length - 1]);
  const yMax = Math.ceil((Math.max(...trend.parties.flatMap((p) => p.upper90)) + 1) / 10) * 10;
  const x = (time: number) =>
    MARGIN.left + ((time - firstWeek) / (lastWeek - firstWeek)) * (WIDTH - MARGIN.left - MARGIN.right);
  const y = (value: number) => MARGIN.top + (1 - value / yMax) * (HEIGHT - MARGIN.top - MARGIN.bottom);
  const pointAt = (week: string, value: number) => `${x(Date.parse(week))},${y(value)}`;
  const line = (values: number[]) => trend.weeks.map((week, k) => pointAt(week, values[k])).join(' ');
  const band = (party: (typeof trend.parties)[number]) =>
    [
      line(party.upper90),
      [...trend.weeks]
        .reverse()
        .map((week, k) => pointAt(week, party.lower90[trend.weeks.length - 1 - k]))
        .join(' '),
    ].join(' ');

  const gridValues = Array.from({ length: yMax / 10 + 1 }, (_, k) => k * 10);
  const yearStarts = [2024, 2025, 2026]
    .map((year) => Date.UTC(year, 0, 1))
    .filter((t) => t > firstWeek && t < lastWeek);

  const endLabels = trend.parties
    .map((party, index) => ({ party, index, at: y(party.mean[party.mean.length - 1]) }))
    .sort((a, b) => a.at - b.at);
  endLabels.forEach((label, k) => {
    if (k > 0 && label.at - endLabels[k - 1].at < MIN_LABEL_GAP) label.at = endLabels[k - 1].at + MIN_LABEL_GAP;
  });

  const summary = trend.parties
    .map((p) => `${partyLabel(snapshot, p.partyId)} ${p.mean[p.mean.length - 1].toFixed(1)}%`)
    .join(', ');
  const plotRight = WIDTH - MARGIN.right;
  const axisBottom = HEIGHT - MARGIN.bottom;

  return (
    <figure className="trend">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Weekly support since the 2023 election, ${longDate(trend.weeks[0])} to ${longDate(trend.weeks[trend.weeks.length - 1])}: ${summary}`}
      >
        {gridValues.map((value) => (
          <g key={value}>
            <line x1={MARGIN.left} x2={plotRight} y1={y(value)} y2={y(value)} className="grid" />
            <text x={MARGIN.left - 6} y={y(value) + 4} textAnchor="end" className="tick">
              {value}%
            </text>
          </g>
        ))}
        {yearStarts.map((time) => (
          <g key={time}>
            <line x1={x(time)} x2={x(time)} y1={MARGIN.top} y2={axisBottom} className="grid" />
            <text x={x(time)} y={HEIGHT - 12} textAnchor="middle" className="tick">
              {new Date(time).getUTCFullYear()}
            </text>
          </g>
        ))}
        {trend.parties.map((party, index) =>
          polls.map((poll) => {
            const share = poll.shares.find((s) => s.partyId === party.partyId)?.percent;
            if (share == null) return null;
            return (
              <circle
                key={`${party.partyId}-${poll.id}`}
                cx={x(fieldworkMidpoint(poll.fieldworkStart, poll.fieldworkEnd))}
                cy={y(share)}
                r="1.8"
                fill={colour(party.partyId, index)}
                opacity="0.35"
              />
            );
          }),
        )}
        {trend.parties.map((party, index) => (
          <g key={party.partyId}>
            <polygon points={band(party)} fill={colour(party.partyId, index)} opacity="0.12" />
            <polyline fill="none" stroke={colour(party.partyId, index)} strokeWidth="2" points={line(party.mean)} />
          </g>
        ))}
        {endLabels.map(({ party, index, at }) => (
          <text
            key={party.partyId}
            x={plotRight + 6}
            y={at + 4}
            fill={colour(party.partyId, index)}
            className="endlabel"
          >
            {partyLabel(snapshot, party.partyId)}
          </text>
        ))}
      </svg>
      <figcaption>
        {trend.basis} Dots are individual polls the model used. <a href="../polls/">Every poll, with sources</a>.
      </figcaption>
    </figure>
  );
}
