import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import { pages } from './pages';
import { runSyntheticDryRun } from '../dev/syntheticSnapshot';
import type { LoadResult } from '../data/loader';
const none = () => Promise.resolve<LoadResult>({ status: 'unavailable', reason: 'test' });
describe('website shell', () => {
 it.each(pages)('renders $label on direct entry', page => { render(<MemoryRouter initialEntries={[page.path]}><App source={none} /></MemoryRouter>); expect(screen.getByRole('heading', { level: 1, name: page.title })).toBeInTheDocument(); expect(screen.getByText('No forecast published')).toBeInTheDocument(); expect(screen.getByRole('link', {name: page.label})).toHaveAttribute('aria-current', 'page'); });
 it('navigates between pages and updates the title', () => { render(<MemoryRouter><App source={none} /></MemoryRouter>); fireEvent.click(screen.getByRole('link', {name:'Polls'})); expect(screen.getByRole('heading', {name:'The national picture.'})).toBeInTheDocument(); expect(document.title).toBe('Polls | NZ Election Model 2026'); });
 it('handles unknown routes', () => { render(<MemoryRouter initialEntries={['/missing']}><App source={none} /></MemoryRouter>); expect(screen.getByRole('heading', {name:'Page not found'})).toBeInTheDocument(); });
 it('shows a loaded snapshot with the synthetic banner', async () => {
  const snapshot = await runSyntheticDryRun({ draws: 50 });
  render(<MemoryRouter initialEntries={['/']}><App source={() => Promise.resolve({ status: 'loaded', snapshot })} /></MemoryRouter>);
  expect(await screen.findByRole('alert')).toHaveTextContent('SYNTHETIC DATA');
  expect(screen.queryByText(/ncalibrated/)).not.toBeInTheDocument();
  expect(screen.getByRole('table', { name: /Median with 80% \(primary\), 50% and 90% ranges/ })).toBeInTheDocument();
  expect(screen.getByText(/not margins of error/)).toHaveTextContent('Forecast if the election were held today, as of 2026-10-06');
  expect(screen.queryByText('No forecast published')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('link', { name: 'Electorates' }));
  expect(screen.getByRole('heading', { name: 'Synthetic Electorate 1' })).toBeInTheDocument();
  expect(screen.getByText(/No forecast available: No candidate model/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('link', { name: 'MMP / Overhang' }));
  expect(screen.getAllByRole('alert')[1]).toHaveTextContent('Placeholder seat rules');
 });
});
