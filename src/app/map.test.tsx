import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { syntheticBankSnapshot } from '../dev/syntheticBank';
import { App } from './App';
import { opacityFor } from './ElectorateMap';
import { partyLabel } from './partyNames';

const noIndex = () => Promise.reject(new Error('no archive'));

describe('party names', () => {
  it('uses one set of names everywhere', async () => {
    const snapshot = await syntheticBankSnapshot();
    expect(['nationalparty', 'labourparty', 'greenparty', 'actnewzealand', 'newzealandfirstparty', 'opportunity', 'tepatimaori'].map(id => partyLabel(snapshot, id)))
      .toEqual(['National', 'Labour', 'Greens', 'ACT', 'NZ First', 'TOP', 'Te Pāti Māori']);
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
    fireEvent.click(screen.getByRole('button', { name: /^Māori/ }));
    const maori = screen.getByRole('group', { name: /Map of the Māori electorates/ });
    expect(within(maori).getAllByRole('link')).toHaveLength(7);
    expect(container.querySelectorAll('.mapinsets svg')).toHaveLength(0);
    fireEvent.click(within(maori).getAllByRole('link')[0]);
    expect(await screen.findByRole('heading', { level: 2, name: /Māori electorate/ })).toBeInTheDocument();
    window.location.hash = '';
  });
});
