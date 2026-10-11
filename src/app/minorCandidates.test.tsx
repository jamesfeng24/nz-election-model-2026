import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import bank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import { buildNowcastSnapshot } from '../models/nowcast/fromBank';
import type { IndexResult } from '../data/loader';
import { App } from './App';
import { candidatePartyName } from './partyNames';
import { COLOURS, medianColour } from './partyColours';

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

/** A general seat whose last `count` candidates are minor-party and independent candidates with tiny chances and shares (extras are copies of its last candidate). */
async function seatWithMinors(count: number) {
  const snapshot = await buildNowcastSnapshot(bank, options);
  const seatId = snapshot.simulation.electoratePredictions.find(
    (p) => snapshot.directory.electorates.find((e) => e.electorateId === p.electorateId)?.kind === 'general',
  )!.electorateId;
  const prediction = snapshot.simulation.electoratePredictions.find((p) => p.electorateId === seatId)!;
  const detail = snapshot.electorateDetail.find((d) => d.electorateId === seatId)!;
  const last = [...prediction.candidates].sort((a, b) => a.winProbability - b.winProbability)[0];
  const lastDirectory = snapshot.directory.candidates.find((c) => c.candidateId === last.candidateId)!;
  const lastDetail = detail.candidates.find((c) => c.candidateId === last.candidateId)!;
  const minorIds = [last.candidateId];
  for (let i = 1; i < count; i++) {
    const id = `${last.candidateId}-extra${i}`;
    minorIds.push(id);
    snapshot.directory.candidates.push({ ...lastDirectory, candidateId: id, name: `Extra MINOR${i}` });
    prediction.candidates.push({ ...structuredClone(last), candidateId: id });
    detail.candidates.push({ ...structuredClone(lastDetail), candidateId: id });
  }
  const slugs = ['newzealandloyal', 'aotearoalegalisecannabisparty', 'conservativepartynz', null];
  minorIds.forEach((id, i) => {
    const directory = snapshot.directory.candidates.find((c) => c.candidateId === id)!;
    directory.partyId = null;
    directory.partyLabel = slugs[i % slugs.length];
    prediction.candidates.find((c) => c.candidateId === id)!.winProbability = 0.002;
    for (const interval of detail.candidates.find((c) => c.candidateId === id)!.share) {
      interval.lower = 0.005;
      interval.median = 0.008;
      interval.upper = 0.012;
    }
  });
  const name = snapshot.directory.electorates.find((e) => e.electorateId === seatId)!.name;
  return { snapshot, seatId, name, minorIds };
}

async function show(snapshot: Awaited<ReturnType<typeof seatWithMinors>>['snapshot'], seatId: string, name: string) {
  window.location.hash = `#seat=${seatId}`;
  render(
    <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
  );
  await screen.findByRole('heading', { level: 2, name: new RegExp(name) });
  return screen.getByRole('table', { name: /Chance of winning and share/ });
}

describe('minor candidates on a seat page', () => {
  it('folds them under a collapsed Other row, with proper party names once opened', async () => {
    const { snapshot, seatId, name, minorIds } = await seatWithMinors(3);
    const table = await show(snapshot, seatId, name);
    const other = within(table).getByRole('button', { name: /Other/ });
    expect(other).toHaveAttribute('aria-expanded', 'false');
    expect(other).toHaveTextContent('(3 candidates)');
    // Collapsed: none of the minor candidates, and no raw ballot-group key, is on the page.
    for (const id of minorIds) {
      const candidate = snapshot.directory.candidates.find((c) => c.candidateId === id)!;
      expect(within(table).queryByText(candidate.name)).toBeNull();
    }
    expect(table.textContent).not.toMatch(/newzealandloyal|aotearoalegalisecannabisparty|conservativepartynz/);
    fireEvent.click(other);
    expect(other).toHaveAttribute('aria-expanded', 'true');
    for (const id of minorIds) {
      const candidate = snapshot.directory.candidates.find((c) => c.candidateId === id)!;
      expect(within(table).getByText(candidate.name)).toBeInTheDocument();
    }
    expect(within(table).getByText('NZ Loyal')).toBeInTheDocument();
    expect(within(table).getByText('Legalise Cannabis')).toBeInTheDocument();
    expect(within(table).getByText('Conservative')).toBeInTheDocument();
    expect(table.textContent).not.toMatch(/newzealandloyal|aotearoalegalisecannabisparty|conservativepartynz/);
    fireEvent.click(other);
    expect(within(table).queryByText('NZ Loyal')).toBeNull();
    window.location.hash = '';
  });

  it('lists a single minor candidate in place, with no Other row', async () => {
    const { snapshot, seatId, name, minorIds } = await seatWithMinors(1);
    const table = await show(snapshot, seatId, name);
    expect(within(table).queryByRole('button', { name: /Other/ })).toBeNull();
    const candidate = snapshot.directory.candidates.find((c) => c.candidateId === minorIds[0])!;
    expect(within(table).getByText(candidate.name)).toBeInTheDocument();
    window.location.hash = '';
  });

  it('keeps a minor candidate with a real chance or a real share out of Other', async () => {
    const { snapshot, seatId, name, minorIds } = await seatWithMinors(3);
    const prediction = snapshot.simulation.electoratePredictions.find((p) => p.electorateId === seatId)!;
    prediction.candidates.find((c) => c.candidateId === minorIds[0])!.winProbability = 0.04; // a 4% chance stays listed
    const detail = snapshot.electorateDetail.find((d) => d.electorateId === seatId)!;
    for (const interval of detail.candidates.find((c) => c.candidateId === minorIds[1])!.share) interval.median = 0.08; // an 8% share stays listed
    const table = await show(snapshot, seatId, name);
    // Only one candidate is left to fold, so there is no Other row at all.
    expect(within(table).queryByRole('button', { name: /Other/ })).toBeNull();
    for (const id of minorIds) {
      expect(
        within(table).getByText(snapshot.directory.candidates.find((c) => c.candidateId === id)!.name),
      ).toBeInTheDocument();
    }
    window.location.hash = '';
  });
});

describe('minor party names', () => {
  it('maps every nominated minor party to a short name, never a raw ballot-group key', async () => {
    const snapshot = await buildNowcastSnapshot(bank, options);
    const named = (partyLabel: string | null) =>
      candidatePartyName(snapshot, { candidateId: 'c', name: 'N', electorateId: 'e', partyId: null, partyLabel });
    expect(named('nzoutdoorsfreedomparty')).toBe('Outdoors & Freedom');
    expect(named('alliancepartyofaotearoanewzealand')).toBe('Alliance');
    expect(named('animaljusticeparty')).toBe('Animal Justice');
    expect(named('visionnewzealand')).toBe('Vision NZ');
    expect(named('freepalestine')).toBe('Free Palestine');
    expect(named('tetaitokerauparty')).toBe('Te Tai Tokerau Party');
    expect(named('aSomethingNewparty')).toBe('aSomethingNewparty'); // already readable
    expect(named('somethingnewparty')).toBe('Other party');
    expect(named(null)).toBe('Independent');
  });
});

describe('median line colour', () => {
  it('stays near-black where it shows and turns white on the darkest party colours', () => {
    expect(COLOURS.newzealandfirstparty).not.toBe('#222222'); // NZ First is no longer full black
    expect(medianColour(COLOURS.newzealandfirstparty)).toBe('#222');
    expect(medianColour(COLOURS.labourparty)).toBe('#222');
    expect(medianColour(COLOURS.actnewzealand)).toBe('#222');
    expect(medianColour(COLOURS.tepatimaori)).toBe('#fff');
    expect(medianColour(COLOURS.nationalparty)).toBe('#fff');
    expect(medianColour('#222222')).toBe('#fff');
  });
});
