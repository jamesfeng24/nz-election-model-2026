import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import bank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import evidenceFile from '../../data/processed/site-evidence/2026-10-07/evidence.json';
import { buildNowcastSnapshot } from '../models/nowcast/fromBank';
import { ForecastSnapshotSchema } from '../types/export';
import { syntheticBankSnapshot } from '../dev/syntheticBank';
import { App } from './App';
import type { LoadResult } from '../data/loader';

const options = (evidence: unknown) => ({
  snapshotId: 'synthetic-nowcast-1', createdAt: '2026-10-08T00:00:00+00:00', dataCutoff: '2026-10-07T00:00:00+00:00',
  electionId: 'nz-general-2026', electionDate: '2026-11-07', boundaryVersionId: 'stats-nz-electorates-final-2025',
  modelVersion: 'synthetic-model', codeRevision: 'synthetic-revision', bankSha256: 'a'.repeat(64),
  mmp: null, nationalBasis: 'Synthetic draws', limitations: ['SYNTHETIC FIXTURE: not a nowcast.'], evidence,
});
const loaded = (snapshot: unknown): (() => Promise<LoadResult>) => () => Promise.resolve({ status: 'loaded', snapshot: snapshot as never });

describe('site evidence in the snapshot', () => {
  it('embeds the produced polls, trend and seat polls and shows them on the polls page', async () => {
    // The synthetic bank's model state (2026-09-27) matches the evidence file; its directory has the real seat names.
    const snapshot = await buildNowcastSnapshot(bank, options(evidenceFile));
    expect(snapshot.evidence!.nationalPolls).toHaveLength(124);
    expect(snapshot.evidence!.nationalPolls.filter(p => p.usedInModel)).toHaveLength(121);
    expect(snapshot.evidence!.trend!.weeks).toHaveLength(156);
    const detailWithPolls = snapshot.electorateDetail.filter(d => (d.evidence?.polls.length ?? 0) > 0).length;
    expect(detailWithPolls).toBe(6);
    expect(snapshot.electorateDetail.every(d => d.evidence?.basis)).toBe(true);
    expect(() => ForecastSnapshotSchema.parse(snapshot)).not.toThrow();

    render(<App page="polls" source={loaded(snapshot)} />);
    expect(await screen.findByRole('heading', { name: 'National polls' })).toBeInTheDocument();
    expect(screen.getByText(/121 of the 124 national polls/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Wikipedia, Opinion polling/ })).toHaveAttribute('href', expect.stringContaining('oldid=1378865337'));
    const table = screen.getByRole('table', { name: /National polls, newest first/ });
    expect(within(table).getAllByRole('row')).toHaveLength(125);
    expect(screen.getAllByRole('link', { name: 'Te Ao Maori News (Whakaata Maori)' })[0]).toHaveAttribute('href', expect.stringMatching(/^https:\/\//));
    expect(screen.getAllByText(/Found but not used in this forecast/).length).toBe(3);
  });
  it('draws the support trend on the forecast page', async () => {
    const snapshot = await buildNowcastSnapshot(bank, options(evidenceFile));
    render(<App page="forecast" source={loaded(snapshot)} />);
    expect(await screen.findByRole('heading', { name: 'How support has moved' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Weekly support since the 2023 election/ })).toBeInTheDocument();
  });
  it('fails closed on a seat poll for an electorate that is not in the directory, and on a poll after the cutoff', async () => {
    const wrong = structuredClone(evidenceFile) as typeof evidenceFile;
    wrong.seatPolls[0].electorateName = 'Nowhere';
    await expect(buildNowcastSnapshot(bank, options(wrong))).rejects.toThrow(/not in the directory/);
    const late = structuredClone(evidenceFile) as typeof evidenceFile;
    late.nationalPolls[0].fieldworkEnd = '2026-10-08';
    await expect(buildNowcastSnapshot(bank, options(late))).rejects.toThrow(/postdate the data cutoff/);
  });
  it('keeps snapshots without evidence valid', async () => {
    const snapshot = await syntheticBankSnapshot();
    expect(snapshot.evidence).toBeUndefined();
  });
});
