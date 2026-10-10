import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import type { ReleasePoint } from '../data/loader';
import { syntheticBankSnapshot } from '../dev/syntheticBank';
import type { ForecastSnapshot } from '../types/export';
import { SupportTrend } from './SupportTrend';
import { TrendChart } from './TrendChart';

// jsdom has no layout, so the pointer position is read as chart coordinates (the chart's own viewBox).
const move = (svg: Element, x: number, y: number) => fireEvent.pointerMove(svg, { clientX: x, clientY: y });

async function withTrend(): Promise<ForecastSnapshot> {
  const snapshot = await syntheticBankSnapshot();
  const weeks = ['2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26'];
  return {
    ...snapshot,
    evidence: {
      source: { label: 's', url: 'https://example.org/', revision: 'r', retrieved: '2026-10-07' },
      nationalPolls: [],
      trend: {
        basis: 'Test trend.',
        weeks,
        parties: [
          { partyId: 'nationalparty', mean: [30, 31, 32, 33], lower90: [28, 29, 30, 31], upper90: [32, 33, 34, 35] },
          {
            partyId: 'labourparty',
            mean: [28, 28.5, 29, 29.5],
            lower90: [26, 26.5, 27, 27.5],
            upper90: [30, 30.5, 31, 31.5],
          },
        ],
      },
    },
  } as ForecastSnapshot;
}

// The chart's own layout (see SupportTrend.tsx): 720 x 360, margins 40 / 104 / 14 / 34, y axis 0 to 40.
const px = (week: number) => 40 + (week / 3) * (720 - 40 - 104);
const py = (value: number) => 14 + (1 - value / 40) * (360 - 14 - 34);

describe('support trend hover', () => {
  it('names the party, date and exact figure for the band under the pointer', async () => {
    const snapshot = await withTrend();
    const { container } = render(<SupportTrend snapshot={snapshot} />);
    const svg = container.querySelector('svg')!;
    move(svg, px(2), py(32.2));
    expect(container.querySelector('.charttip')).toHaveTextContent('National');
    expect(container.querySelector('.charttip')).toHaveTextContent('19 January 2026');
    expect(container.querySelector('.charttip')).toHaveTextContent('32.0% (90% range 30.0–34.0%)');
  });
  it('picks the party whose estimate is closer where bands overlap', async () => {
    const snapshot = await withTrend();
    const { container } = render(<SupportTrend snapshot={snapshot} />);
    const svg = container.querySelector('svg')!;
    // At the third week both bands cover 30 to 31; Labour (29) is nearer 30.2, National (32) is nearer 30.9.
    move(svg, px(2), py(30.2));
    expect(container.querySelector('.charttip')).toHaveTextContent('Labour');
    move(svg, px(2), py(31.2));
    expect(container.querySelector('.charttip')).toHaveTextContent('National');
  });
  it('shows nothing away from every band, and clears when the pointer leaves', async () => {
    const snapshot = await withTrend();
    const { container } = render(<SupportTrend snapshot={snapshot} />);
    const svg = container.querySelector('svg')!;
    move(svg, px(1), py(10));
    expect(container.querySelector('.charttip')).toBeNull();
    move(svg, px(1), py(28.5));
    expect(container.querySelector('.charttip')).not.toBeNull();
    fireEvent.pointerLeave(svg);
    expect(container.querySelector('.charttip')).toBeNull();
  });
});

describe('support trend range', () => {
  const earlier = (snapshot: ForecastSnapshot): ForecastSnapshot => {
    const trend = snapshot.evidence!.trend!;
    const pad = (values: number[]) => [values[0] - 2, values[0] - 1, ...values];
    return {
      ...snapshot,
      evidence: {
        ...snapshot.evidence!,
        trend: {
          ...trend,
          weeks: ['2025-11-03', '2025-12-01', ...trend.weeks],
          parties: trend.parties.map((p) => ({
            ...p,
            mean: pad(p.mean),
            lower90: pad(p.lower90),
            upper90: pad(p.upper90),
          })),
        },
      },
    };
  };
  it('opens at the start of 2026 and shows the whole run with the tick box', async () => {
    const snapshot = earlier(await withTrend());
    const { container } = render(<SupportTrend snapshot={snapshot} />);
    expect(container.querySelector('svg')!.getAttribute('aria-label')).toContain('5 January 2026 to 26 January 2026');
    fireEvent.click(screen.getByRole('checkbox', { name: /Since the 2023 election/ }));
    expect(container.querySelector('svg')!.getAttribute('aria-label')).toContain('3 November 2025 to 26 January 2026');
  });
  it('has no tick box when the series already starts in 2026', async () => {
    render(<SupportTrend snapshot={await withTrend()} />);
    expect(screen.queryByRole('checkbox')).toBeNull();
  });
});

describe('odds chart hover', () => {
  const release = (n: number, nat: number, lab: number, hung: number): ReleasePoint =>
    ({
      snapshotId: `r${n}`,
      dataCutoff: `2026-10-${String(6 + n * 7).padStart(2, '0')}T00:00:00+00:00`,
      blocMajority: { 'nat-act-nzf': { p: nat, label: 'A' }, 'lab-grn-tpm': { p: lab, label: 'B' } },
      scenarios: { hung: { p: hung, label: 'C' } },
    }) as unknown as ReleasePoint;
  it('names the line, date and chance of the nearest point', () => {
    const history = [release(0, 0.2, 0.1, 0.7), release(1, 0.3, 0.1, 0.6), release(2, 0.4, 0.1, 0.5)];
    const { container } = render(<TrendChart history={history} />);
    const svg = container.querySelector('svg')!;
    // Layout: 640 x 300, margins 44 / 230 / 16 / 40; the last release sits at the right edge of the plot.
    const x = (k: number) => 44 + (k / 2) * (640 - 230 - 44);
    const y = (p: number) => 16 + (1 - p) * (300 - 16 - 40);
    move(svg, x(2) - 3, y(0.4));
    expect(container.querySelector('.charttip')).toHaveTextContent('National + ACT + NZ First');
    expect(container.querySelector('.charttip')).toHaveTextContent('20 October 2026: 40%');
    move(svg, x(0), y(0.68));
    expect(container.querySelector('.charttip')).toHaveTextContent('No majority');
    expect(screen.getAllByRole('img').length).toBeGreaterThan(0);
  });
});
