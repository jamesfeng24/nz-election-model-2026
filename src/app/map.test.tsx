import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { syntheticBankSnapshot } from '../dev/syntheticBank';
import { App } from './App';
import { incumbentNote, opacityFor, type MapForecast } from './ElectorateMap';
import { partyLabel } from './partyNames';

const noIndex = () => Promise.reject(new Error('no archive'));

describe('party names', () => {
  it('uses one set of names everywhere', async () => {
    const snapshot = await syntheticBankSnapshot();
    expect(['nationalparty', 'labourparty', 'greenparty', 'actnewzealand', 'newzealandfirstparty', 'opportunity', 'tepatimaori'].map(id => partyLabel(snapshot, id)))
      .toEqual(['National', 'Labour', 'Greens', 'ACT', 'NZ First', 'TOP', 'Te Pāti Māori']);
  });
});

describe('incumbent note', () => {
  const seat: MapForecast = { id: 'a', name: 'Seat', kind: 'general', leaderParty: null, leaderPartyName: 'Independent', leaderName: 'A B', leaderP: 0.6, available: true, incumbent: 'A B', incumbentStatus: 'leads', candidates: [] };
  it('names the sitting MP and whether they are the favourite', () => {
    expect(incumbentNote(seat)).toBe('. Incumbent: A B (most likely winner)');
    expect(incumbentNote({ ...seat, incumbentStatus: 'trails' })).toBe('. Incumbent: A B (not the most likely winner)');
    expect(incumbentNote({ ...seat, incumbentStatus: 'standing' })).toBe('. Incumbent: A B');
    expect(incumbentNote({ ...seat, incumbent: null, incumbentStatus: 'open' })).toBe('. No sitting MP is standing');
  });
  it('says nothing when no incumbency data is attached', () => {
    expect(incumbentNote({ ...seat, incumbent: null, incumbentStatus: 'unknown' })).toBe('');
  });
});

describe('electorate map', () => {
  it('is paler for close seats', () => {
    expect(opacityFor(0.4)).toBeCloseTo(0.2);
    expect(opacityFor(1)).toBeCloseTo(1);
    expect(opacityFor(0.7)).toBeGreaterThan(opacityFor(0.5));
  });

  it('draws every seat as a link to its page, with a Māori toggle, and selects a seat when clicked', async () => {
    const snapshot = await syntheticBankSnapshot();
    const { container } = render(<App page="electorates" source={() => Promise.resolve({ status: 'loaded', snapshot })} indexSource={noIndex} />);
    const general = await screen.findByRole('group', { name: /Map of the general electorates/ });
    const links = within(general).getAllByRole('link');
    expect(links.length).toBeGreaterThan(40);
    expect(links[0].getAttribute('href')).toMatch(/^#seat=/);
    expect(container.querySelectorAll('.mapinsets svg')).toHaveLength(4);
    fireEvent.mouseEnter(links[0]);
    const card = container.querySelector('.mapcard')!;
    expect(within(card as HTMLElement).getByText(/Most likely winner:/)).toBeInTheDocument();
    expect(card.querySelectorAll('tbody tr').length).toBeGreaterThan(1);
    expect(card.textContent).toMatch(/\d+\.\d%/);
    fireEvent.mouseLeave(links[0]);
    expect(card.textContent).toMatch(/Hover over or select a seat/);
    fireEvent.click(screen.getByRole('button', { name: /^Māori/ }));
    const maori = screen.getByRole('group', { name: /Map of the Māori electorates/ });
    expect(within(maori).getAllByRole('link')).toHaveLength(7);
    expect(container.querySelectorAll('.mapinsets svg')).toHaveLength(0);
    fireEvent.click(within(maori).getAllByRole('link')[0]);
    expect(await screen.findByRole('heading', { level: 2, name: /Māori electorate/ })).toBeInTheDocument();
    window.location.hash = '';
  });
});
