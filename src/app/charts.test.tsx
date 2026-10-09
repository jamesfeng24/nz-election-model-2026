import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { addToArchive } from '../models/simulation/exporter';
import { loadReleaseHistory } from '../data/loader';
import { syntheticBankSnapshot } from '../dev/syntheticBank';
import { SeatChart } from './SeatChart';
import { TrendChart } from './TrendChart';
import { ForecastView } from './ForecastViews';

async function archive(n: number) {
  const files = new Map<string, string>();
  let index = null;
  for (let i = 0; i < n; i++) {
    const snapshot = await syntheticBankSnapshot({ snapshotId: `synthetic-nowcast-${i + 1}`, dataCutoff: `2026-10-${String(6 + i * 7).padStart(2, '0')}T00:00:00+00:00` });
    const added = await addToArchive(snapshot, index, null);
    added.files.forEach(f => files.set(f.path, f.content));
    index = JSON.parse(files.get('index.json')!);
  }
  return async (url: string) => { const v = files.get(url.replace('../forecasts/', '')); if (v === undefined) throw new Error('HTTP 404'); return v; };
}

describe('headline seat chart', () => {
  it('lists parties in the required left-to-right order and one dot per seat', async () => {
    const snapshot = await syntheticBankSnapshot();
    const { container } = render(<SeatChart snapshot={snapshot} />);
    const labels = [...container.querySelectorAll('.seatchart-key li b')].map(b => b.textContent);
    const abbreviations = ['Te Pāti Māori', 'Greens', 'Labour', 'TOP', 'NZ First', 'National', 'ACT'];
    expect(labels.slice(0, abbreviations.length)).toEqual(abbreviations);
    const total = Number(container.querySelector('.seatchart-total')!.textContent);
    expect(container.querySelectorAll('circle')).toHaveLength(total);
    expect(screen.getByRole('img', { name: /Expected seats, left to right/ })).toBeInTheDocument();
  });
});

describe('trend chart', () => {
  it('switches on only after three verified releases', async () => {
    const options = (n: Promise<(u: string) => Promise<string>>) => n.then(fetchText => ({ fetchText, baseUrl: '../forecasts/', allowSynthetic: true }));
    const three = await loadReleaseHistory(await options(archive(3)));
    expect(three.map(p => p.snapshotId)).toEqual(['synthetic-nowcast-1', 'synthetic-nowcast-2', 'synthetic-nowcast-3']);
    const { container, rerender } = render(<TrendChart history={three} />);
    expect(container.querySelectorAll('polyline').length).toBeGreaterThan(0);
    rerender(<TrendChart history={three.slice(0, 2)} />);
    expect(container.querySelector('svg')).toBeNull();
  });
  it('drops the history when a file does not match its index hash', async () => {
    const good = await archive(3);
    const tampered = async (url: string) => { const t = await good(url); return url.endsWith('synthetic-nowcast-2/snapshot.json') ? t.replace('Synthetic draws', 'Synthetic drawz') : t; };
    expect(await loadReleaseHistory({ fetchText: tampered, baseUrl: '../forecasts/', allowSynthetic: true })).toEqual([]);
  });
  it('is hidden on the forecast page unless a chart is supplied', async () => {
    const snapshot = await syntheticBankSnapshot();
    render(<ForecastView snapshot={snapshot} trend={null} />);
    expect(screen.queryByText('How the odds have moved')).not.toBeInTheDocument();
  });
});
