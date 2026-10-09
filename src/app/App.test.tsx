import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';
import { pages } from './pages';
import { runSyntheticDryRun } from '../dev/syntheticSnapshot';
import bank from '../../data/fixtures/synthetic/nowcast-draw-bank.json';
import config from '../../config/nowcast-2026.json';
import { buildNowcastSnapshot } from '../models/nowcast/fromBank';
import type { IndexResult, LoadResult } from '../data/loader';
const none = () => Promise.resolve<LoadResult>({ status: 'unavailable', reason: 'test' });
const noIndex = () => Promise.resolve<IndexResult>({ status: 'unavailable', reason: 'test' });
const mmp = (config as any).mmp;
const footer = 'Free to share with credit (CC BY 4.0)';
describe('public site', () => {
  it.each(pages)('renders $label with navigation, title and the licence footer', async page => {
    render(<App page={page.path} source={none} indexSource={noIndex} />);
    expect(screen.getByRole('heading', { level: 1, name: page.title })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: page.label })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: footer })).toHaveAttribute('href', 'https://creativecommons.org/licenses/by/4.0/');
    expect(await screen.findByRole('navigation')).toBeInTheDocument();
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
  it('names the data sources on the methodology page', () => {
    render(<App page="methodology" source={none} indexSource={noIndex} />);
    expect(screen.getByRole('heading', { name: 'Data sources' })).toBeInTheDocument();
    expect(screen.getByText(/Electoral Commission official results/)).toBeInTheDocument();
  });
  it('shows a loaded snapshot with the as-of banner and the synthetic warning', async () => {
    const snapshot = await runSyntheticDryRun({ draws: 50 });
    render(<App page="forecast" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('SYNTHETIC DATA');
    expect(screen.getByText(/Forecast if the election were held today, as of 6 October 2026/)).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /Median with 80% \(primary\), 50% and 90% ranges/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Electorates' })).toBeInTheDocument();
    expect(screen.queryByText('No forecast published yet')).not.toBeInTheDocument();
  });
  it('lists archive entries newest first and marks corrections', async () => {
    const index: IndexResult = { status: 'loaded', index: { schemaVersion: 1, snapshots: [
      { snapshotId: 'a', createdAt: '2026-10-08T00:00:00+13:00', dataCutoff: '2026-10-08T00:00:00+13:00', provenanceKind: 'model', path: 'a/snapshot.json', sha256: '0'.repeat(64), supersedes: null, status: 'published', withdrawnReason: null },
      { snapshotId: 'b', createdAt: '2026-10-09T00:00:00+13:00', dataCutoff: '2026-10-09T00:00:00+13:00', provenanceKind: 'model', path: 'b/snapshot.json', sha256: '1'.repeat(64), supersedes: 'a', status: 'published', withdrawnReason: null },
    ] } };
    render(<App page="archive" source={none} indexSource={() => Promise.resolve(index)} />);
    const rows = await screen.findAllByRole('row');
    expect(rows[1]).toHaveTextContent('9 October 2026');
    expect(rows[1]).toHaveTextContent('Correction of a');
    expect(rows[2]).toHaveTextContent('Replaced by a correction');
    expect(screen.getAllByRole('link', { name: 'JSON' })[0]).toHaveAttribute('href', '../forecasts/b/snapshot.json');
  });
  it('shows seats for each group, hung scenarios and the electorate table from a full 71-seat snapshot', async () => {
    const snapshot = await buildNowcastSnapshot(bank, {
      snapshotId: 'synthetic-nowcast-1', createdAt: '2026-10-07T00:00:00+00:00', dataCutoff: '2026-10-06T00:00:00+00:00',
      electionId: 'nz-general-2026', electionDate: '2026-11-07', boundaryVersionId: 'stats-nz-electorates-final-2025',
      modelVersion: 'synthetic-model', codeRevision: 'synthetic-revision', bankSha256: 'a'.repeat(64),
      mmp: { rulesVersion: 'UNVERIFIED-PLACEHOLDER-synthetic-only', rulesSourceIds: ['synthetic-rules'], blocs: mmp.blocs, hungParliament: mmp.hungParliament },
      nationalBasis: 'Synthetic draws', limitations: ['SYNTHETIC FIXTURE: not a nowcast.'],
    });
    render(<App page="forecast" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />);
    expect(await screen.findByRole('heading', { name: 'Seats for each group of parties' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: /Chance each group wins more than half/ })).toHaveTextContent('LAB+GRN+TPM');
    expect(screen.getByRole('table', { name: 'Hung parliament scenarios' })).toBeInTheDocument();
    expect(screen.getByText('All 71 electorates')).toBeInTheDocument();
    expect(screen.getAllByText(/Wider/).length).toBeGreaterThan(0);
  });
});
