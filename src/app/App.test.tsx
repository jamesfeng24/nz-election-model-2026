import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import { pages } from './pages';
describe('website shell', () => {
 it.each(pages)('renders $label on direct entry', page => { render(<MemoryRouter initialEntries={[page.path]}><App /></MemoryRouter>); expect(screen.getByRole('heading', { level: 1, name: page.title })).toBeInTheDocument(); expect(screen.getByText('No forecast published')).toBeInTheDocument(); expect(screen.getByRole('link', {name: page.label})).toHaveAttribute('aria-current', 'page'); });
 it('navigates between pages and updates the title', () => { render(<MemoryRouter><App /></MemoryRouter>); fireEvent.click(screen.getByRole('link', {name:'Polls'})); expect(screen.getByRole('heading', {name:'The national picture.'})).toBeInTheDocument(); expect(document.title).toBe('Polls | NZ Election Model 2026'); });
 it('handles unknown routes', () => { render(<MemoryRouter initialEntries={['/missing']}><App /></MemoryRouter>); expect(screen.getByRole('heading', {name:'Page not found'})).toBeInTheDocument(); });
});
