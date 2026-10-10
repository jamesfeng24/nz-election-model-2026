import { beforeAll, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { syntheticBankSnapshot } from '../dev/syntheticBank';
import { App } from './App';
import { pages } from './pages';
import { runSyntheticDryRun } from '../dev/syntheticSnapshot';
import bank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import config from '../../config/nowcast-2026.json';
import { buildNowcastSnapshot } from '../models/nowcast/fromBank';
import { ForecastSnapshotSchema } from '../types/export';
import { fireEvent } from '@testing-library/react';
import type { IndexResult, LoadResult } from '../data/loader';
const none = () => Promise.resolve<LoadResult>({ status: 'unavailable', reason: 'test' });
const noIndex = () => Promise.resolve<IndexResult>({ status: 'unavailable', reason: 'test' });
const mmp = (config as any).mmp;
const footer = 'Licensed under CC BY 4.0';
describe('public site', () => {
  const scrollTo = vi.fn();
  beforeAll(() => {
    window.scrollTo = scrollTo as unknown as typeof window.scrollTo;
  });
  it.each(pages)('renders $label with navigation, title and the licence footer', async (page) => {
    render(<App page={page.path} source={none} indexSource={noIndex} />);
    expect(screen.getByRole('heading', { level: 1, name: page.title })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: page.label })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: footer })).toHaveAttribute(
      'href',
      'https://creativecommons.org/licenses/by/4.0/',
    );
    expect(await screen.findByRole('navigation')).toBeInTheDocument();
  });
  it('lists the owner links on the About page, only those with an address', () => {
    render(<App page="about" source={none} indexSource={noIndex} />);
    expect(screen.getByRole('link', { name: 'github.com/jamesfeng24' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^https:\/\/github\.com\//),
    );
    expect(screen.queryByText('Ko-fi')).toBeNull();
  });
  it('links pages with relative addresses', () => {
    render(<App page="forecast" source={none} indexSource={noIndex} />);
    expect(screen.getByRole('link', { name: 'Archive' })).toHaveAttribute('href', '../archive/');
    expect(screen.getByRole('link', { name: 'Methodology' })).toHaveAttribute('href', '../methodology/');
  });
  it('says no forecast is published when none loads, and never shows a partial one', async () => {
    render(<App page="forecast" source={none} indexSource={noIndex} />);
    expect(await screen.findByText('No forecast published yet')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
  it('says the forecast could not be loaded, not that none is published, when loading fails', async () => {
    const failed = () => Promise.resolve<LoadResult>({ status: 'unavailable', reason: 'HTTP 500', cause: 'failed' });
    render(<App page="forecast" source={failed} indexSource={noIndex} />);
    expect(await screen.findByText('The forecast could not be loaded')).toBeInTheDocument();
    expect(screen.queryByText('No forecast published yet')).not.toBeInTheDocument();
  });
  it('names the data sources on the methodology page', () => {
    render(<App page="methodology" source={none} indexSource={noIndex} />);
    expect(screen.getByRole('heading', { name: 'Data sources' })).toBeInTheDocument();
    expect(screen.getByText(/Electoral Commission official results/)).toBeInTheDocument();
  });
  it('shows a loaded snapshot with the as-of banner and the synthetic warning', async () => {
    const snapshot = await runSyntheticDryRun({ draws: 50 });
    render(
      <App page="forecast" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('SYNTHETIC DATA');
    expect(screen.getByText(/Updated 6 October 2026/)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /Median with 80% range/ })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: /50% range|90% range/ })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Electorates' })).toBeNull();
    expect(screen.queryByText('No forecast published yet')).not.toBeInTheDocument();
  });
  it('lists archive entries newest first and marks corrections', async () => {
    const index: IndexResult = {
      status: 'loaded',
      index: {
        schemaVersion: 1,
        snapshots: [
          {
            snapshotId: 'a',
            createdAt: '2026-10-08T00:00:00+13:00',
            dataCutoff: '2026-10-08T00:00:00+13:00',
            provenanceKind: 'model',
            path: 'a/snapshot.json',
            sha256: '0'.repeat(64),
            supersedes: null,
            status: 'published',
            withdrawnReason: null,
          },
          {
            snapshotId: 'b',
            createdAt: '2026-10-09T00:00:00+13:00',
            dataCutoff: '2026-10-09T00:00:00+13:00',
            provenanceKind: 'model',
            path: 'b/snapshot.json',
            sha256: '1'.repeat(64),
            supersedes: 'a',
            status: 'published',
            withdrawnReason: null,
          },
        ],
      },
    };
    render(<App page="archive" source={none} indexSource={() => Promise.resolve(index)} />);
    const rows = await screen.findAllByRole('row');
    expect(rows[1]).toHaveTextContent('9 October 2026');
    expect(rows[1]).toHaveTextContent('Correction of a');
    expect(rows[2]).toHaveTextContent('Replaced by a correction');
    expect(screen.getAllByRole('link', { name: 'JSON' })[0]).toHaveAttribute('href', '../forecasts/b/snapshot.json');
    // Only the current entry opens as a frozen site; the replaced one keeps its JSON.
    expect(screen.getAllByRole('link', { name: 'Site' })).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Site' })).toHaveAttribute('href', '../archive/2026-10-09/');
  });
  it('shows a frozen copy with a banner and links back to the live site', async () => {
    const index: IndexResult = {
      status: 'loaded',
      index: {
        schemaVersion: 1,
        snapshots: [
          {
            snapshotId: 'a',
            createdAt: '2026-10-08T00:00:00+13:00',
            dataCutoff: '2026-10-08',
            provenanceKind: 'model',
            path: 'a/snapshot.json',
            sha256: '0'.repeat(64),
            supersedes: null,
            status: 'published',
            withdrawnReason: null,
          },
        ],
      },
    };
    render(<App page="archive" archivedOn="2026-10-08" source={none} indexSource={() => Promise.resolve(index)} />);
    const banner = await screen.findByRole('note');
    expect(banner).toHaveTextContent('You’re viewing the forecast from 8 October 2026.');
    expect(within(banner).getByRole('link', { name: 'See the latest' })).toHaveAttribute('href', '../../../');
    expect(screen.getByRole('link', { name: 'Site' })).toHaveAttribute('href', '../../../archive/2026-10-08/');
    expect(screen.getByRole('link', { name: 'JSON' })).toHaveAttribute('href', '../forecasts/a/snapshot.json');
  });
  it('shows no banner on the live site', async () => {
    render(<App page="about" source={none} />);
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
  });
  it('shows the chance of a majority for each group, no-majority and the electorate table from a full 71-seat snapshot', async () => {
    const snapshot = await buildNowcastSnapshot(bank, {
      snapshotId: 'synthetic-nowcast-1',
      createdAt: '2026-10-07T00:00:00+00:00',
      dataCutoff: '2026-10-06T00:00:00+00:00',
      electionId: 'nz-general-2026',
      electionDate: '2026-11-07',
      boundaryVersionId: 'stats-nz-electorates-final-2025',
      modelVersion: 'synthetic-model',
      codeRevision: 'synthetic-revision',
      bankSha256: 'a'.repeat(64),
      mmp: {
        rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only',
        rulesSourceIds: ['synthetic-rules'],
        blocs: mmp.blocs,
        hungParliament: mmp.hungParliament,
      },
      nationalBasis: 'Synthetic draws',
      limitations: ['SYNTHETIC FIXTURE: not a nowcast.'],
    });
    render(
      <App page="forecast" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    expect(await screen.findByRole('heading', { name: 'Chance of a majority' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /Chance each group wins more than half/ })).toHaveTextContent(
      'Labour + Greens + Te Pāti Māori',
    );
    expect(screen.getByRole('table', { name: /Chance each group wins more than half/ })).toHaveTextContent(
      'No majority',
    );
    ['Chance of a majority', 'Median seats', '80% range'].forEach((h) =>
      expect(
        within(screen.getByRole('table', { name: /Chance each group wins more than half/ })).getByRole('columnheader', {
          name: h,
        }),
      ).toBeInTheDocument(),
    );
    const majorityRows = within(
      screen.getByRole('table', { name: /Chance each group wins more than half/ }),
    ).getAllByRole('row');
    expect(majorityRows[1].querySelectorAll('td')[2].textContent).toMatch(/^\d+$/);
    expect(majorityRows[1].querySelectorAll('td')[3].textContent).toMatch(/^\d+ – \d+$/);
    expect(screen.queryByText(/combined/)).toBeNull();
    expect(screen.queryByText(/kingmaker/i)).toBeNull();
    const seatTable = screen.getByRole('table', { name: /Seats by party across simulated elections/ });
    ['Median', '80% range', 'Electorate', 'List', 'Overhang'].forEach((h) =>
      expect(within(seatTable).getByRole('columnheader', { name: h })).toBeInTheDocument(),
    );
    expect(seatTable.querySelectorAll('.seatbar').length).toBeGreaterThan(3);
    expect(screen.getByRole('heading', { name: 'Overhang' })).toBeInTheDocument();
    expect(screen.getByText(/Chance of at least one overhang seat/)).toBeInTheDocument();
    expect(screen.queryByText('All 71 electorates')).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Electorates' })).toBeNull();
  });
  it('marks the sitting MP on the seat page and in the seat list, and rejects inconsistent incumbent flags', async () => {
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
    const plain = await buildNowcastSnapshot(bank, options);
    expect(plain.incumbency).toBeUndefined();
    const seatId = plain.directory.electorates[0].electorateId;
    const sitting = plain.directory.candidates.find((c) => c.electorateId === seatId)!;
    const snapshot = await buildNowcastSnapshot(bank, {
      ...options,
      incumbents: {
        source: { label: 'Invented list of MPs', url: 'https://example.org/mps', asOf: '2026-09-23' },
        incumbents: [{ targetOccurrenceId: sitting.candidateId }, { targetOccurrenceId: 'not-in-this-bank' }],
      },
    });
    expect(snapshot.directory.candidates.filter((c) => c.incumbent).map((c) => c.candidateId)).toEqual([
      sitting.candidateId,
    ]);
    expect(snapshot.incumbency?.asOf).toBe('2026-09-23');
    const noSource = structuredClone(snapshot);
    delete noSource.incumbency;
    expect(() => ForecastSnapshotSchema.parse(noSource)).toThrow(/need their source/);
    const two = structuredClone(snapshot);
    two.directory.candidates.find(
      (c) => c.electorateId === seatId && c.candidateId !== sitting.candidateId,
    )!.incumbent = true;
    expect(() => ForecastSnapshotSchema.parse(two)).toThrow(/only one incumbent/);
    window.location.hash = `#seat=${seatId}`;
    render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    const row = (await screen.findAllByRole('row')).find((r) => r.textContent?.startsWith(sitting.name))!;
    expect(within(row).getByText('Incumbent')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Expected margin' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Incumbent' })).toBeNull();
    window.location.hash = '';
  });
  it('filters the seat list by winner party, flips, seat type and close contests', async () => {
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
    const plain = await buildNowcastSnapshot(bank, options);
    const incumbents = plain.directory.electorates.flatMap((e, i) =>
      i % 4 === 3
        ? []
        : [
            {
              targetOccurrenceId: plain.directory.candidates.filter((c) => c.electorateId === e.electorateId)[
                i % 4 === 2 ? 1 : 0
              ].candidateId,
            },
          ],
    );
    const snapshot = await buildNowcastSnapshot(bank, {
      ...options,
      incumbents: {
        source: { label: 'Invented list', url: 'https://example.org/mps', asOf: '2026-09-23' },
        incumbents,
      },
    });
    window.location.hash = '';
    render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    expect(await screen.findByText(/All 71 electorates \(71 shown\)/)).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Type' }), { target: { value: 'maori' } });
    expect(screen.getByText(/Electorates matching the filters \(7 shown\)/)).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Type' }), { target: { value: 'any' } });
    fireEvent.click(screen.getByRole('checkbox', { name: /Projected flips/ }));
    const flips = screen.getAllByText('Flip').length;
    expect(flips).toBeGreaterThan(0);
    // A projected flip is a seat whose projected winner is from a different party than the standing sitting MP.
    const partyOf = (candidateId: string | undefined) =>
      snapshot.directory.candidates.find((c) => c.candidateId === candidateId)?.partyId ?? 'independent';
    const expectedFlips = snapshot.directory.electorates.filter((e) => {
      const sitting = snapshot.directory.candidates.find((c) => c.electorateId === e.electorateId && c.incumbent);
      const prediction = snapshot.simulation.electoratePredictions.find((p) => p.electorateId === e.electorateId);
      if (!sitting || !prediction) return false;
      const leader = [...prediction.candidates].sort((a, b) => b.winProbability - a.winProbability)[0];
      return partyOf(leader.candidateId) !== partyOf(sitting.candidateId);
    }).length;
    expect(flips).toBe(expectedFlips);
    expect(screen.getByText(new RegExp(`\\(${flips} shown\\)`))).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox', { name: /Projected flips/ }));
    const party = screen.getByRole('combobox', { name: "Projected winner's party" }) as HTMLSelectElement;
    fireEvent.change(party, { target: { value: party.options[1].value } });
    const byParty = Number(/\((\d+) shown\)/.exec(document.querySelector('.seatlist caption')!.textContent!)![1]);
    expect(byParty).toBeGreaterThan(0);
    expect(byParty).toBeLessThan(71);
    fireEvent.change(party, { target: { value: 'any' } });
    const inc = screen.getByRole('combobox', { name: "Incumbent's party" }) as HTMLSelectElement;
    fireEvent.change(inc, { target: { value: inc.options[1].value } });
    const byIncumbent = Number(/\((\d+) shown\)/.exec(document.querySelector('.seatlist caption')!.textContent!)![1]);
    expect(byIncumbent).toBeGreaterThan(0);
    expect(byIncumbent).toBeLessThan(71);
    expect(screen.queryByRole('option', { name: /Widest uncertainty/ })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    fireEvent.click(screen.getByRole('checkbox', { name: /Close contests/ }));
    const close = Number(/\((\d+) shown\)/.exec(document.querySelector('.seatlist caption')!.textContent!)![1]);
    expect(close).toBeLessThan(71);
    window.location.hash = '';
  });
  it('opens a seat inside the list, glides to it, and closes it again', async () => {
    const snapshot = await syntheticBankSnapshot();
    window.location.hash = '';
    render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    const first = (await screen.findAllByRole('button', { name: /^[A-Z]/ })).find((b) => b.closest('.seatlist'))!;
    expect(first).toHaveAttribute('aria-expanded', 'false');
    expect(document.querySelector('.seatdetail')).toBeNull();
    scrollTo.mockClear();
    fireEvent.click(first);
    const detail = document.querySelector('.seatlist .seatdetail')!;
    expect(detail).not.toBeNull();
    expect(within(detail as HTMLElement).getByRole('heading', { level: 2 })).toBeInTheDocument();
    expect(first).toHaveAttribute('aria-expanded', 'true');
    // The detail sits directly under the row that opened it.
    expect(first.closest('tr')!.nextElementSibling).toBe(detail);
    await waitFor(() => expect(scrollTo).toHaveBeenCalled());
    fireEvent.click(first);
    // It folds shut before it is removed, and the address is cleared at once.
    expect(first).toHaveAttribute('aria-expanded', 'false');
    expect(window.location.hash).toBe('');
    await waitFor(() => expect(document.querySelector('.seatdetail')).toBeNull());
  });
  it('suggests seats in a styled list while typing, and opens the one picked', async () => {
    const snapshot = await syntheticBankSnapshot();
    window.location.hash = '';
    const name = snapshot.directory.electorates[0].name;
    render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    const box = await screen.findByRole('combobox', { name: 'Find a seat' });
    fireEvent.focus(box);
    fireEvent.change(box, { target: { value: name.slice(0, 3) } });
    const option = screen.getAllByRole('option').find((o) => o.textContent?.startsWith(name))!;
    expect(option).toBeTruthy();
    expect(document.querySelector('datalist')).toBeNull();
    fireEvent.click(option.querySelector('button')!);
    expect(await screen.findByRole('heading', { level: 2, name: new RegExp(name) })).toBeInTheDocument();
    expect(screen.queryByRole('listbox')).toBeNull();
    window.location.hash = '';
  });
  it('shows the 50% range on the solid bar, the 80% range on the light bar and always the median', async () => {
    const snapshot = await syntheticBankSnapshot();
    window.location.hash = `#seat=${snapshot.directory.electorates[0].electorateId}`;
    const { container } = render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    await screen.findByRole('heading', { level: 2, name: new RegExp(snapshot.directory.electorates[0].name) });
    const bar = container.querySelector('.rangebar')!;
    fireEvent.mouseEnter(bar.querySelector('.r50')!, { clientX: 10 });
    expect(bar.querySelector('.rangetip')!.textContent).toMatch(/^50% range .*median/);
    fireEvent.mouseEnter(bar.querySelector('.r80')!, { clientX: 10 });
    expect(bar.querySelector('.rangetip')!.textContent).toMatch(/^80% range .*median/);
    fireEvent.mouseLeave(bar);
    expect(bar.querySelector('.rangetip')).toBeNull();
    expect(container.querySelector('.shareaxis')!.textContent).toMatch(/0%.*%/);
    expect(screen.getByRole('columnheader', { name: 'Median share' })).toBeInTheDocument();
    window.location.hash = '';
  });
  it('shows a seat page with odds, shaded ranges and the polls attached to the seat', async () => {
    const base = await buildNowcastSnapshot(bank, {
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
    });
    const snapshot = structuredClone(base);
    const seat = snapshot.electorateDetail[0];
    const candidate = snapshot.directory.candidates.find((c) => c.electorateId === seat.electorateId)!;
    const poll = {
      pollster: 'Invented Research',
      commissioner: 'An invented client',
      fieldworkStart: null,
      fieldworkEnd: '2026-09-27',
      published: null,
      sampleSize: 500,
      marginOfError: 4.5,
      usedInModel: false,
      note: null,
      sources: [{ label: 'Invented Herald', url: 'https://example.org/poll' }],
      results: [{ candidateId: candidate.candidateId, name: candidate.name, party: null, percent: 40 }],
    };
    seat.evidence = { basis: 'Invented basis text', polls: [poll] };
    expect(() => ForecastSnapshotSchema.parse(snapshot)).not.toThrow();
    const bad = structuredClone(snapshot);
    bad.electorateDetail[0].evidence!.polls[0].results[0].candidateId = 'nobody';
    expect(() => ForecastSnapshotSchema.parse(bad)).toThrow(/unknown candidate/);
    window.location.hash = `#seat=${seat.electorateId}`;
    render(
      <App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />,
    );
    const name = snapshot.directory.electorates.find((e) => e.electorateId === seat.electorateId)!.name;
    expect(await screen.findByRole('heading', { level: 2, name: new RegExp(name) })).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: /50% range .* 80% range/ }).length).toBeGreaterThan(1);
    expect(screen.getByText('Invented basis text')).toBeInTheDocument();
    expect(screen.getByText(/Not used in this forecast/)).toBeInTheDocument();
    fireEvent.change(screen.getByRole('combobox', { name: 'Find a seat' }), { target: { value: 'zzzz' } });
    expect(screen.getByText(/0 shown/)).toBeInTheDocument();
    window.location.hash = '';
  });
});
