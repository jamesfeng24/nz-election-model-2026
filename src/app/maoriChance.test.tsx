import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import bank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import { buildNowcastSnapshot } from '../models/nowcast/fromBank';
import { ForecastSnapshotSchema } from '../types/export';
import type { IndexResult } from '../data/loader';
import { App } from './App';
import { prob } from './format';

const noIndex = () => Promise.resolve<IndexResult>({ status: 'unavailable', reason: 'test' });
const options = {
  snapshotId: 'synthetic-nowcast-1',
  createdAt: '2026-10-07T00:00:00+00:00',
  dataCutoff: '2026-10-06T00:00:00+00:00',
  electionId: 'nz-general-2026',
  electionDate: '2026-11-07',
  boundaryVersionId: 'stats-nz-electorates-final-2025',
  modelVersion: 'synthetic-model',
  codeRevision: 'synthetic-revision',
  bankSha256: 'a'.repeat(64),
  mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: [] },
  nationalBasis: 'Synthetic draws',
  limitations: ['SYNTHETIC FIXTURE: not a nowcast.'],
};

describe('Māori seat win chance', () => {
  it('shows one figure, the one the seat totals use, even when the export carries a second estimate', async () => {
    const snapshot = await buildNowcastSnapshot(bank, options);
    const seat = snapshot.electorateDetail.find((d) => d.uncertaintyClass === 'maori-layer')!;
    const leaderId = [...seat.candidates].sort((a, b) => b.winProbability.p - a.winProbability.p)[0].candidateId;
    for (const c of seat.candidates) {
      const p =
        c.candidateId === leaderId ? Math.max(0, c.winProbability.p - 0.2) : Math.min(1, c.winProbability.p + 0.1);
      c.winProbabilityInflation = { ...c.winProbability, p };
    }
    expect(() => ForecastSnapshotSchema.parse(snapshot)).not.toThrow();

    const name = snapshot.directory.electorates.find((e) => e.electorateId === seat.electorateId)!.name;
    window.location.hash = `#seat=${seat.electorateId}`;
    render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    expect(await screen.findByRole('heading', { level: 2, name: new RegExp(name) })).toBeInTheDocument();
    const lead = seat.candidates.find((c) => c.candidateId === leaderId)!;
    const table = screen.getByRole('table', { name: /Chance of winning and share/ });
    expect(within(table).getByText(prob(lead.winProbability.p))).toBeInTheDocument();
    expect(within(table).queryByText(/–/)).toBeNull();
    expect(screen.queryByText(/range between two estimates/)).toBeNull();
    const listRow = screen.getAllByRole('row').find((r) => r.closest('.seatlist') && r.textContent?.startsWith(name))!;
    expect(listRow).toHaveTextContent(prob(lead.winProbability.p));
    expect(listRow.textContent).not.toMatch(/\d+–\d+%/);
    window.location.hash = '';
  });
});
